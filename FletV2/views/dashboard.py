#!/usr/bin/env python3
"""Professional dashboard view with Material 3 styling for Flet 0.28.3."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from collections import Counter
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import flet as ft

try:  # pragma: no cover - UTF-8 bootstrap required by project
    pass
except Exception:  # pragma: no cover - allow running in isolation
    pass

try:
    from ..theme import create_skeleton_loader
    from ..utils.async_helpers import run_sync_in_executor
    from ..utils.data_export import export_to_csv, generate_export_filename
    from ..utils.formatters import (
        as_float,
        as_int,
        format_timestamp,
        format_uptime,
        normalize_text,
    )
    from ..utils.loading_states import (
        create_error_display,
    )
    from ..utils.ui_builders import (
        create_action_button,
        create_status_chip,
        create_view_header,
    )
    from ..utils.ui_components import AppCard, create_pulsing_status_indicator
    from ..utils.user_feedback import show_error_message, show_success_message
except Exception:  # pragma: no cover - fallback when executing directly
    from FletV2.theme import create_skeleton_loader
    from FletV2.utils.async_helpers import run_sync_in_executor
    from FletV2.utils.data_export import (  # type: ignore
        export_to_csv,
        generate_export_filename,
    )
    from FletV2.utils.formatters import (
        as_float,
        as_int,
        format_timestamp,
        format_uptime,
        normalize_text,
    )
    from FletV2.utils.loading_states import (
        create_error_display,
    )
    from FletV2.utils.ui_builders import (
        create_action_button,
        create_status_chip,
        create_view_header,
    )
    from FletV2.utils.ui_components import AppCard, create_pulsing_status_indicator
    from FletV2.utils.user_feedback import show_error_message, show_success_message


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass(slots=True)
class DashboardSnapshot:
    total_clients: int = 0
    connected_clients: int = 0
    total_files: int = 0
    uptime_seconds: float = 0.0
    server_status: str = "offline"
    server_version: str = ""
    port: int | None = None
    cpu_usage: float | None = None
    memory_usage_mb: float | None = None
    db_response_ms: int | None = None
    active_connections: int = 0
    recent_activity: list[dict[str, Any]] | None = None
    errors: list[str] | None = None


# Removed MetricBlock dataclass - using simple dict instead for metric tracking

# Formatters moved to FletV2.utils.formatters module:
# - normalize_text, format_uptime, format_timestamp, as_float, as_int


STATUS_CURRENTLY_CONNECTED = "Currently connected"


# ============================================================================
# SECTION 2: BUSINESS LOGIC HELPERS
# Severity inference, color palettes, data transformations
# ============================================================================


def _infer_severity(entry: dict[str, Any]) -> str:
    if not isinstance(entry, dict):
        return "info"

    priority = ("severity", "level", "status", "type", "category")

    severity_map = {
        "critical": {"critical", "fatal"},
        "error": {"error", "err", "failed", "failure"},
        "warning": {"warn", "warning", "degraded", "maintenance"},
        "success": {"success", "ok", "completed"},
        "audit": {"audit", "policy"},
        "info": {"info", "information", "event"},
    }

    for key in priority:
        if raw := entry.get(key):
            normalized = str(raw).strip().lower()
            if not normalized:
                continue

            for severity, keywords in severity_map.items():
                if normalized in keywords:
                    return severity

    return "error" if entry.get("success") is False else "info"


def _activity_palette(
    severity: str, scheme: ft.ColorScheme | None = None
) -> dict[str, Any]:
    base_palette = {
        "critical": {
            "accent": ft.Colors.RED_ACCENT_200,
            "icon": ft.Icons.ERROR_OUTLINE,
            "text": ft.Colors.RED_900,
        },
        "error": {
            "accent": ft.Colors.RED_ACCENT_100,
            "icon": ft.Icons.ERROR_OUTLINE,
            "text": ft.Colors.RED_900,
        },
        "warning": {
            "accent": ft.Colors.AMBER_ACCENT_100,
            "icon": ft.Icons.WARNING_AMBER,
            "text": ft.Colors.AMBER_900,
        },
        "success": {
            "accent": ft.Colors.GREEN_ACCENT_100,
            "icon": ft.Icons.CHECK_CIRCLE_OUTLINE,
            "text": ft.Colors.GREEN_900,
        },
        "audit": {
            "accent": ft.Colors.PURPLE_ACCENT_100,
            "icon": ft.Icons.ASSIGNMENT_OUTLINED,
            "text": ft.Colors.PURPLE_900,
        },
        "info": {
            "accent": ft.Colors.BLUE_ACCENT_100,
            "icon": ft.Icons.INFO_OUTLINE,
            "text": ft.Colors.BLUE_900,
        },
    }

    def _resolve(attr: str, fallback: str) -> str:
        value = getattr(scheme, attr, None) if scheme else None
        return value if isinstance(value, str) and value.strip() else fallback

    palette = {
        "critical": {
            "accent": _resolve("error_container", base_palette["critical"]["accent"]),
            "icon": ft.Icons.ERROR_OUTLINE,
            "text": _resolve("on_error_container", base_palette["critical"]["text"]),
        },
        "error": {
            "accent": _resolve("error", base_palette["error"]["accent"]),
            "icon": ft.Icons.ERROR_OUTLINE,
            "text": _resolve("on_error", base_palette["error"]["text"]),
        },
        "warning": {
            "accent": _resolve("tertiary_container", base_palette["warning"]["accent"]),
            "icon": ft.Icons.WARNING_AMBER,
            "text": _resolve("on_tertiary_container", base_palette["warning"]["text"]),
        },
        "success": {
            "accent": _resolve(
                "secondary_container", base_palette["success"]["accent"]
            ),
            "icon": ft.Icons.CHECK_CIRCLE_OUTLINE,
            "text": _resolve("on_secondary_container", base_palette["success"]["text"]),
        },
        "audit": {
            "accent": _resolve("primary_container", base_palette["audit"]["accent"]),
            "icon": ft.Icons.ASSIGNMENT_OUTLINED,
            "text": _resolve("on_primary_container", base_palette["audit"]["text"]),
        },
        "info": {
            "accent": _resolve("surface_variant", base_palette["info"]["accent"]),
            "icon": ft.Icons.INFO_OUTLINE,
            "text": _resolve("on_surface_variant", base_palette["info"]["text"]),
        },
    }

    return palette.get(severity, palette["info"])


# ============================================================================
# SECTION 1: DATA FETCHING
# Async wrappers for ServerBridge calls with proper run_in_executor
# ============================================================================


async def _call_bridge(
    server_bridge: Any | None, method_name: str, *args: Any
) -> dict[str, Any]:
    DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
    if not server_bridge:
        if DEBUG:
            print(f"[DASH] _call_bridge('{method_name}') skipped - no server bridge")
        return {"success": False, "data": None, "error": "Server bridge unavailable"}

    method = getattr(server_bridge, method_name, None)
    if method is None:
        return {
            "success": False,
            "data": None,
            "error": f"Method {method_name} not found",
        }

    try:
        if DEBUG:
            print(
                f"[DASH] _call_bridge → calling {method_name} ({'async' if asyncio.iscoroutinefunction(method) else 'sync'}) with args={args}"
            )
        if asyncio.iscoroutinefunction(method):
            result = await method(*args)
        else:
            # Keep the current run_sync_in_executor pattern as it's working and proven
            result = await run_sync_in_executor(method, *args)
    except Exception as exc:  # pragma: no cover - defensive guard
        if DEBUG:
            print(f"[DASH] _call_bridge('{method_name}') raised: {exc}")
        return {"success": False, "data": None, "error": str(exc)}

    if isinstance(result, dict):
        if DEBUG:
            print(
                f"[DASH] _call_bridge('{method_name}') returned (dict): success={result.get('success')} keys={list(result.keys())}"
            )
        return result
    if DEBUG:
        print(
            f"[DASH] _call_bridge('{method_name}') returned (raw): type={type(result)}"
        )
    return {"success": True, "data": result, "error": None}


async def _fetch_snapshot(server_bridge: Any | None) -> DashboardSnapshot:
    DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
    snapshot = DashboardSnapshot()
    issues: list[str] = []

    # Gracefully handle GUI-only mode (no real server/bridge). In this case, don't
    # spam errors; return neutral, empty snapshot so the UI renders clean placeholders.
    if not server_bridge or (
        hasattr(server_bridge, "real_server") and not server_bridge.real_server
    ):
        snapshot.server_status = "offline"
        snapshot.errors = None
        snapshot.recent_activity = []
        return snapshot

    if DEBUG:
        print("[DASH] _fetch_snapshot → fetching get_dashboard_summary")
    summary = await _call_bridge(server_bridge, "get_dashboard_summary")
    if summary.get("success"):
        payload = summary.get("data") or {}
        snapshot.total_clients = int(payload.get("total_clients") or 0)
        snapshot.connected_clients = int(payload.get("connected_clients") or 0)
        snapshot.total_files = int(payload.get("total_files") or 0)
        snapshot.uptime_seconds = float(payload.get("uptime") or 0.0)
        snapshot.server_status = str(payload.get("server_status") or "offline")
        snapshot.server_version = str(
            payload.get("server_version") or snapshot.server_version
        )
    else:
        issues.append(summary.get("error") or "Dashboard summary unavailable")

    if DEBUG:
        print("[DASH] _fetch_snapshot → fetching get_performance_metrics")
    performance = await _call_bridge(server_bridge, "get_performance_metrics")
    if performance.get("success"):
        payload = performance.get("data") or {}
        snapshot.cpu_usage = as_float(payload.get("cpu_usage_percent"))
        snapshot.memory_usage_mb = as_float(payload.get("memory_usage_mb"))
        snapshot.db_response_ms = as_int(payload.get("database_response_time_ms"))
        active = as_int(payload.get("active_connections"))
        if active is not None:
            snapshot.active_connections = max(active, 0)
    else:
        issues.append(performance.get("error") or "Performance metrics unavailable")

    if DEBUG:
        print("[DASH] _fetch_snapshot → fetching get_server_statistics")
    stats = await _call_bridge(server_bridge, "get_server_statistics")
    if stats.get("success"):
        payload = stats.get("data") or {}
        server_block = payload.get("server") if isinstance(payload, dict) else {}
        clients_block = payload.get("clients") if isinstance(payload, dict) else {}
        files_block = payload.get("files") if isinstance(payload, dict) else {}

        if isinstance(server_block, dict):
            port = as_int(server_block.get("port"))
            if port is not None:
                snapshot.port = port
            uptime = as_float(server_block.get("uptime_seconds"))
            if uptime is not None and uptime > snapshot.uptime_seconds:
                snapshot.uptime_seconds = uptime
            version = server_block.get("version")
            if version and not snapshot.server_version:
                snapshot.server_version = str(version)

        if isinstance(clients_block, dict):
            current = as_int(clients_block.get("currently_connected"))
            if current is not None:
                snapshot.connected_clients = current

        if isinstance(files_block, dict):
            totals = as_int(files_block.get("total_files"))
            if totals is not None:
                snapshot.total_files = totals
    else:
        issues.append(stats.get("error") or "Server statistics unavailable")

    if DEBUG:
        print("[DASH] _fetch_snapshot → fetching get_recent_activity_async (limit=12)")
    activity = await _call_bridge(server_bridge, "get_recent_activity_async", 12)
    if not activity.get("success"):
        if DEBUG:
            print(
                "[DASH] _fetch_snapshot → async activity failed, trying sync get_recent_activity"
            )
        activity = await _call_bridge(server_bridge, "get_recent_activity", 12)

    if not activity.get("success"):
        issues.append(activity.get("error") or "Recent activity unavailable")
    else:
        data = activity.get("data")
        snapshot.recent_activity = data if isinstance(data, list) else []

    snapshot.errors = issues or None
    return snapshot


# ============================================================================
# SECTION 3: UI COMPONENTS
# Flet control builders for metrics, activity, status displays
# ============================================================================


def _build_metric_block(
    title: str,
    subtitle: str,
    icon: str,
    accent: str,
    column_span: dict[str, int],
    navigate_callback: Callable[[str], None] | None,
    route: str | None,
) -> dict[str, ft.Control]:
    """Build enhanced metric block with neumorphic styling and hover effects."""
    # Use ft.Ref for controls that need to be updated
    value_text_ref = ft.Ref[ft.Text]()
    footnote_text_ref = ft.Ref[ft.Text]()

    # Create Text controls with refs
    value_text = ft.Text(
        "—",
        size=30,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.ON_SURFACE,
        ref=value_text_ref,
    )
    footnote_text = ft.Text(
        subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT, ref=footnote_text_ref
    )

    body = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(icon, size=22, color=accent),
                    ft.Text(title, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            value_text,
            footnote_text,
        ],
        spacing=6,
    )

    # Clean card with subtle shadow and color accent
    card_content = ft.Container(
        content=body,
        padding=ft.padding.all(20),
        bgcolor=ft.Colors.SURFACE,
        border_radius=12,
        border=ft.border.only(top=ft.BorderSide(3, accent)),
        shadow=[
            ft.BoxShadow(
                blur_radius=8,
                spread_radius=1,
                color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            )
        ],
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    # Add hover effect
    def on_hover(e, target=card_content):
        target.scale = 1.02 if e.data == "true" else 1.0
        target.update()

    card_content.on_hover = on_hover

    is_clickable = bool(route and navigate_callback)

    def on_click_handler(_):
        if navigate_callback and route:
            navigate_callback(route)

    wrapper = ft.Container(
        content=card_content,
        col=column_span,
        on_click=on_click_handler if is_clickable else None,
        ink=is_clickable,
    )

    # Return refs for direct access to controls
    return {
        "wrapper": wrapper,
        "value_text": value_text,
        "value_text_ref": value_text_ref,
        "footnote_text": footnote_text,
        "footnote_text_ref": footnote_text_ref,
    }


# ============================================================================
# SECTION 5: MAIN VIEW
# Dashboard composition, setup, and lifecycle management
# ============================================================================


def create_dashboard_view(
    server_bridge: Any | None,
    page: ft.Page,
    _state_manager: Any | None,
    navigate_callback: Callable[[str], None] | None = None,
    global_search: ft.Control | None = None,
) -> tuple[ft.Control, Callable[[], None], Callable[[], Coroutine[Any, Any, None]]]:
    """Create the dashboard view with Material 3 + subtle neumorphism."""

    snapshot_ref: DashboardSnapshot | None = None
    disposed = False
    refresh_lock = asyncio.Lock()
    background_tasks: set[asyncio.Task[Any]] = set()
    # Fallback uptime tracking when server reports 0 but direct bridge is active
    fallback_uptime_start: float | None = None
    # Do not modify page.scroll; keep page-level scroll behavior unchanged

    metrics_config = [
        (
            "total_clients",
            "Clients",
            "Registered endpoints",
            ft.Icons.PEOPLE_OUTLINED,
            ft.Colors.PRIMARY,
            "clients",
        ),
        (
            "active_clients",
            "Active",
            STATUS_CURRENTLY_CONNECTED,
            ft.Icons.CAST_CONNECTED,
            ft.Colors.TEAL,
            "clients",
        ),
        (
            "total_files",
            "Files",
            "Backed-up assets",
            ft.Icons.INSERT_DRIVE_FILE_OUTLINED,
            ft.Colors.BLUE,
            "files",
        ),
        (
            "uptime",
            "Uptime",
            "Since last restart",
            ft.Icons.SCHEDULE,
            ft.Colors.GREEN,
            None,
        ),
    ]

    metric_blocks: dict[str, dict[str, ft.Control]] = {}
    metric_controls: list[ft.Control] = []
    for key, title, subtitle, icon, accent, route in metrics_config:
        block = _build_metric_block(
            title,
            subtitle,
            icon,
            accent,
            {"xs": 12, "sm": 6, "md": 3},
            navigate_callback,
            route,
        )
        metric_blocks[key] = block
        metric_controls.append(block["wrapper"])

    metrics_row = ft.ResponsiveRow(metric_controls, spacing=12, run_spacing=12)

    # --- Live-updated controls used in the header panel
    status_chip_holder = ft.Container(
        content=create_pulsing_status_indicator("neutral", "Server: Unknown")
    )
    uptime_value_text = ft.Text("—", size=13, weight=ft.FontWeight.W_600)

    # Simple text displays for CPU and Memory
    cpu_value_text = ft.Text("—", size=12, weight=ft.FontWeight.W_600)
    cpu_bar = ft.ProgressBar(value=0.0, bar_height=8)
    memory_value_text = ft.Text("—", size=12, weight=ft.FontWeight.W_600)

    db_value_text = ft.Text("—", size=12, weight=ft.FontWeight.W_600)
    connections_value_text = ft.Text("—", size=12, weight=ft.FontWeight.W_600)
    version_value_text = ft.Text("—", size=12, color=ft.Colors.ON_SURFACE)
    port_value_text = ft.Text("—", size=12, color=ft.Colors.ON_SURFACE)

    # --- Modernized status chips using native Material Design 3 components

    # --- New 2025-style compact status header (glass + pills)
    header_status_left = ft.Column(
        [
            status_chip_holder,
            ft.Row(
                [
                    create_status_chip(
                        ft.Icons.HOURGLASS_BOTTOM,
                        uptime_value_text,
                        ft.Colors.PRIMARY,
                        ft.Colors.ON_PRIMARY,
                    ),
                    create_status_chip(
                        ft.Icons.HUB,
                        connections_value_text,
                        ft.Colors.SECONDARY,
                        ft.Colors.ON_SECONDARY,
                    ),
                    create_status_chip(
                        ft.Icons.STORAGE,
                        db_value_text,
                        ft.Colors.PRIMARY_CONTAINER,
                        ft.Colors.ON_PRIMARY_CONTAINER,
                    ),
                ],
                spacing=8,
                wrap=True,
            ),
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
    )

    header_status_right = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.TRENDING_UP,
                        size=16,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text("CPU", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(expand=True),
                    cpu_value_text,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            cpu_bar,
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.MEMORY, size=16, color=ft.Colors.ON_SURFACE_VARIANT
                    ),
                    ft.Text("Memory", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(expand=True),
                    memory_value_text,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    create_status_chip(
                        ft.Icons.BUILD_OUTLINED,
                        version_value_text,
                        ft.Colors.PRIMARY,
                        ft.Colors.ON_PRIMARY,
                    ),
                    create_status_chip(
                        ft.Icons.SETTINGS_ETHERNET,
                        port_value_text,
                        ft.Colors.SECONDARY,
                        ft.Colors.ON_SECONDARY,
                    ),
                ],
                spacing=8,
                wrap=True,
            ),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
    )

    # Clean status header with subtle depth
    status_header_panel = ft.Container(
        content=ft.Row(
            [
                ft.Container(content=header_status_left, expand=True),
                ft.Container(width=12),
                ft.Container(content=header_status_right, width=340),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.padding.all(16),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.SURFACE_TINT),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.OUTLINE)),
    )

    # Loading indicator for dashboard refresh
    loading_ring = ft.ProgressRing(width=20, height=20, visible=False)
    loading_indicator_slot = ft.Container(
        content=loading_ring,
        width=24,
        height=24,
        alignment=ft.alignment.center,
    )

    refresh_button = create_action_button("Refresh", None, icon=ft.Icons.REFRESH)
    export_button = create_action_button(
        "Export activity", None, icon=ft.Icons.DOWNLOAD, primary=False
    )

    header_actions: list[ft.Control] = [
        ft.Row(
            [loading_indicator_slot, refresh_button],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        export_button,
    ]

    # Note: Global search is already in the app-level header (main.py)
    # No need to add it here as it would create a duplicate

    header = ft.Column(
        [
            create_view_header(
                "System dashboard",
                icon=ft.Icons.DASHBOARD,
                description="Live overview of clients, throughput, and operational health.",
                actions=header_actions,
            ),
            status_header_panel,
        ],
        spacing=12,
    )

    activity_full_data: list[dict[str, Any]] = []

    activity_summary_text = ft.Text(
        "No activity", size=12, color=ft.Colors.ON_SURFACE_VARIANT
    )

    # Use ListView instead of Column for automatic scrolling and height management
    activity_list = ft.ListView(
        spacing=12, padding=ft.padding.symmetric(vertical=6), expand=True
    )

    # Add skeleton loaders matching final content structure
    for _ in range(4):  # Show 4 skeleton tiles
        skeleton_tile = ft.Container(
            content=ft.Row(
                [
                    create_skeleton_loader(
                        height=40, width=40, radius=20
                    ),  # Icon placeholder
                    ft.Column(
                        [
                            create_skeleton_loader(height=16, width=200),  # Title
                            create_skeleton_loader(height=12, width=300),  # Subtitle
                            create_skeleton_loader(height=10, width=150),  # Timestamp
                        ],
                        spacing=4,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.all(12),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.SURFACE),
            border_radius=12,
        )
        activity_list.controls.append(skeleton_tile)

    # Activity section with summary text in the header
    activity_header = ft.Row(
        [
            ft.Text("Recent activity", size=16, weight=ft.FontWeight.W_600),
            ft.Container(expand=True),
            activity_summary_text,
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    activity_section = ft.Column(
        [
            activity_header,
            activity_list,  # ListView handles its own container
        ],
        spacing=12,
        expand=True,
    )

    footer_text = ft.Text(
        "Last updated: —", size=12, color=ft.Colors.ON_SURFACE_VARIANT
    )
    # The footer should be part of the main content column, not a separate container that might cause layout issues.
    # It should also be aligned to the end of the column, not necessarily the bottom right of a separate container.
    footer_container = ft.Container(
        content=footer_text, alignment=ft.alignment.center_right
    )

    error_panel = ft.Container(visible=False)

    content_column = ft.Column(
        [
            header,
            metrics_row,
            activity_section,  # Activity section without filters
            footer_container,
            error_panel,
        ],
        spacing=18,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        scroll=ft.ScrollMode.AUTO,  # Enable scrolling on the column itself
    )

    # Main layout container with proper scrolling support
    root = ft.Container(
        content=content_column,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        expand=True,  # Allow container to fill available space
    )

    # Store content_column in a closure for _apply_snapshot to access
    def get_content_column():
        """Return the main content column for external access."""
        return content_column

    def _derive_status(snapshot: DashboardSnapshot) -> tuple[str, str]:
        # If there's no server bridge or no real server behind it, we're in GUI-only
        # standalone mode. Show a neutral banner instead of critical/offline.
        if not server_bridge or (
            hasattr(server_bridge, "real_server") and not server_bridge.real_server
        ):
            return "neutral", "GUI: Standalone mode"

        # Check if bridge has real server instance (but DON'T call is_connected() - it blocks!)
        direct_bridge_present = False
        if hasattr(server_bridge, "real_server"):
            try:
                direct_bridge_present = bool(server_bridge.real_server)
            except Exception:
                direct_bridge_present = False

        raw_status = normalize_text(snapshot.server_status).lower()

        # Additional evidence that the server is live even if status says stopped
        evidence_connected = any(
            [
                snapshot.uptime_seconds and snapshot.uptime_seconds > 0,
                (snapshot.total_clients or 0) > 0,
                (snapshot.total_files or 0) > 0,
                bool(snapshot.server_version),
                snapshot.port is not None,
            ]
        )

        # Priority 1: Check actual server running status from snapshot
        if raw_status in {"running", "online", "active", "operational"}:
            return "excellent", f"Server: {snapshot.server_status.title()}"

        # Priority 2: Server in degraded/warning state
        if raw_status in {"degraded", "warning", "maintenance"}:
            return "warning", f"Server: {snapshot.server_status.title()}"

        # Priority 3: Server explicitly offline/stopped
        if raw_status in {"offline", "stopped", "disconnected"}:
            # In integrated GUI mode, network listener may be stopped while direct bridge is alive.
            # Reflect that as Connected (Direct) to avoid alarming red statuses.
            if direct_bridge_present or evidence_connected:
                return "excellent", "Server: Connected (Direct)"
            return "critical", f"Server: {snapshot.server_status.title()}"

        # Priority 4: Direct bridge present but no clear status
        if direct_bridge_present:
            return "excellent", "Server: Connected (Direct)"

        if evidence_connected:
            return "warning", STATUS_CURRENTLY_CONNECTED

        if snapshot.server_status:
            return "neutral", f"Server: {snapshot.server_status.title()}"

        return "neutral", "Server: Unknown"

    def _safe_update(control: ft.Control | None) -> None:
        if not control:
            return
        with contextlib.suppress(Exception):
            if getattr(control, "page", None):
                control.update()

    def _register_task(task: asyncio.Task[Any] | None) -> asyncio.Task[Any] | None:
        if not task:
            return None

        background_tasks.add(task)

        def _cleanup(completed: asyncio.Task[Any]) -> None:
            background_tasks.discard(completed)
            if (
                os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
                and not completed.cancelled()
            ):
                with contextlib.suppress(Exception):
                    exc = completed.exception()
                    if exc:
                        print(f"[DASH] Background task finished with error: {exc}")

        task.add_done_callback(_cleanup)
        return task

    def _schedule_task(
        coro_func: Callable[[], Coroutine[Any, Any, Any]],
    ) -> asyncio.Task[Any] | None:
        if disposed:
            return None
        try:
            return _register_task(page.run_task(coro_func))
        except RuntimeError as e:
            # Executor already shut down during app closure - this is expected
            DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
            if DEBUG:
                print(f"[DASH] Task scheduling skipped during shutdown: {e}")
            return None

    async def _set_loading_visible(visible: bool) -> None:
        """Toggle the dashboard loading indicator without risking attachment errors."""
        if disposed:
            return

        if getattr(loading_ring, "visible", None) == visible:
            return

        loading_ring.visible = visible

        if not getattr(loading_ring, "page", None):
            return

        await asyncio.sleep(0)
        _safe_update(loading_ring)

    def _set_text(control: Any, value: str, parent: ft.Control | None = None) -> None:
        if getattr(control, "value", None) == value:
            return
        control.value = value
        _safe_update(control)
        if parent:
            _safe_update(parent)

    def _update_metric_block(key: str, value: str, subtitle: str | None = None) -> bool:
        block = metric_blocks.get(key)
        if not block:
            return False

        changed = False

        value_ref = block.get("value_text_ref")
        value_control = None
        if value_ref and getattr(value_ref, "current", None):
            value_control = value_ref.current
        elif block.get("value_text"):
            value_control = block.get("value_text")

        if value_control and getattr(value_control, "value", None) != value:
            value_control.value = value
            _safe_update(value_control)
            changed = True

        if subtitle is not None:
            footnote_ref = block.get("footnote_text_ref")
            footnote_control = None
            if footnote_ref and getattr(footnote_ref, "current", None):
                footnote_control = footnote_ref.current
            elif block.get("footnote_text"):
                footnote_control = block.get("footnote_text")

            if (
                footnote_control
                and getattr(footnote_control, "value", None) != subtitle
            ):
                footnote_control.value = subtitle
                _safe_update(footnote_control)
                changed = True

        return changed

    async def _apply_snapshot(snapshot: DashboardSnapshot) -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        if disposed:
            if DEBUG:
                print("[DASH] _apply_snapshot skipped because view is disposed")
            return

        nonlocal snapshot_ref, fallback_uptime_start, metrics_row, activity_full_data
        snapshot_ref = snapshot

        total_clients = max(0, int(snapshot.total_clients or 0))
        connected_clients = max(0, int(snapshot.connected_clients or 0))
        total_files = max(0, int(snapshot.total_files or 0))

        # Determine display uptime with monotonic fallback when server reports zero
        display_uptime_seconds = float(snapshot.uptime_seconds or 0.0)
        status_level, status_label = _derive_status(snapshot)
        evidence_active = status_level in {"excellent", "warning"} or bool(
            total_clients or total_files or connected_clients
        )

        if display_uptime_seconds > 0:
            fallback_uptime_start = None
        elif evidence_active:
            if fallback_uptime_start is None:
                fallback_uptime_start = time.monotonic()
            display_uptime_seconds = max(0.0, time.monotonic() - fallback_uptime_start)
        else:
            fallback_uptime_start = None

        if DEBUG:
            print(
                "[DASH] _apply_snapshot → clients=%s active=%s files=%s uptime=%.1f status=%s",
                total_clients,
                connected_clients,
                total_files,
                display_uptime_seconds,
                status_level,
            )

        # Update metric cards
        metrics_changed = False

        clients_value = f"{total_clients:,}" if total_clients else "0"
        metrics_changed |= _update_metric_block("total_clients", clients_value)

        active_value = f"{connected_clients:,}" if connected_clients else "0"
        if total_clients > 0:
            ratio = f"{(connected_clients / total_clients) * 100:.0f}% online"
        else:
            ratio = STATUS_CURRENTLY_CONNECTED
        metrics_changed |= _update_metric_block("active_clients", active_value, ratio)

        files_value = f"{total_files:,}" if total_files else "0"
        metrics_changed |= _update_metric_block("total_files", files_value)

        uptime_text = format_uptime(display_uptime_seconds)
        metrics_changed |= _update_metric_block("uptime", uptime_text, status_label)

        if metrics_changed and getattr(metrics_row, "page", None):
            _safe_update(metrics_row)

        await asyncio.sleep(0)

        # Update status chip and header tokens
        status_chip_holder.content = create_pulsing_status_indicator(
            status_level, status_label
        )
        _safe_update(status_chip_holder)

        _set_text(uptime_value_text, uptime_text, status_header_panel)

        if snapshot.cpu_usage is None:
            cpu_percentage = "—"
            cpu_bar_value = 0.0
        else:
            cpu_percentage = f"{snapshot.cpu_usage:.1f}%"
            cpu_bar_value = max(0.0, min(snapshot.cpu_usage / 100.0, 1.0))

        cpu_bar.value = cpu_bar_value
        _safe_update(cpu_bar)
        _set_text(cpu_value_text, cpu_percentage, status_header_panel)

        if snapshot.memory_usage_mb is None:
            memory_display = "—"
        else:
            memory_display = f"{snapshot.memory_usage_mb:.1f} MB"
        _set_text(memory_value_text, memory_display, status_header_panel)

        if snapshot.db_response_ms is None or snapshot.db_response_ms < 0:
            db_display = "—"
        else:
            db_display = f"{snapshot.db_response_ms} ms"
        _set_text(db_value_text, db_display, status_header_panel)

        connections_display = str(
            max(snapshot.active_connections or 0, connected_clients)
        )
        _set_text(connections_value_text, connections_display, status_header_panel)

        server_version = snapshot.server_version or "—"
        _set_text(version_value_text, server_version, status_header_panel)

        port_display = str(snapshot.port) if snapshot.port is not None else "—"
        _set_text(port_value_text, port_display, status_header_panel)

        _safe_update(status_header_panel)

        # Apply activity list updates
        activity_full_data = snapshot.recent_activity or []
        try:
            _apply_activity_filters()
        except Exception as exc:  # pragma: no cover - defensive guard
            if DEBUG:
                print(f"[DASH][WARN] activity filter failed: {exc}")

        footer_text.value = (
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        _safe_update(footer_text)

        if snapshot.errors:
            error_message = "\n".join(snapshot.errors)
            error_panel.content = AppCard(
                create_error_display(error_message),
                title="Dashboard issues",
                expand_content=False,
                disable_hover=True,
            )
            error_panel.visible = True
        else:
            error_panel.content = None
            error_panel.visible = False
        _safe_update(error_panel)

        _safe_update(root)

    async def _refresh() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        if disposed:
            return
        async with refresh_lock:
            try:
                if DEBUG:
                    print("[DASH] _refresh → calling _fetch_snapshot()")
                snapshot = await _fetch_snapshot(server_bridge)
            except Exception as exc:  # pragma: no cover - defensive guard
                show_error_message(page, f"Dashboard refresh failed: {exc}")
                return

            if disposed:
                return

            await _apply_snapshot(snapshot)
            if DEBUG:
                print("[DASH] _refresh → snapshot applied")

    def _on_refresh(_: ft.ControlEvent) -> None:
        if disposed:
            return

        async def refresh_with_loading():
            try:
                await _set_loading_visible(True)
                await _refresh()

            finally:
                await _set_loading_visible(False)

        _schedule_task(refresh_with_loading)

    def _on_export(_: ft.ControlEvent) -> None:
        if disposed:
            return

        async def export_with_loading():
            try:
                await _set_loading_visible(True)

                if not snapshot_ref or not snapshot_ref.recent_activity:
                    show_error_message(page, "No activity available for export")
                    return

                try:
                    export_rows = []
                    for item in snapshot_ref.recent_activity[:100]:
                        if not isinstance(item, dict):
                            continue
                        export_rows.append(
                            {
                                "timestamp": format_timestamp(
                                    item.get("timestamp") or item.get("time")
                                ),
                                "category": str(
                                    item.get("type") or item.get("level") or "info"
                                ),
                                "message": str(
                                    item.get("message") or item.get("details") or ""
                                ),
                            }
                        )

                    if not export_rows:
                        show_error_message(page, "No activity entries to export")
                        return

                    filename = generate_export_filename("dashboard_activity", "csv")
                    export_to_csv(
                        export_rows,
                        filename,
                        fieldnames=["timestamp", "category", "message"],
                    )
                    show_success_message(page, f"Activity exported to {filename}")
                except Exception as exc:  # pragma: no cover - defensive guard
                    show_error_message(page, f"Export failed: {exc}")

            finally:
                await _set_loading_visible(False)

        _schedule_task(export_with_loading)

    refresh_button.on_click = _on_refresh
    export_button.on_click = _on_export

    def _open_activity_details(entry: dict[str, Any]) -> None:
        pretty = json.dumps(entry, indent=2, default=str)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Event details"),
            content=ft.Container(
                content=ft.ListView(
                    controls=[ft.Text(pretty, size=12, selectable=True)],
                    spacing=6,
                    padding=ft.padding.all(6),
                    expand=True,
                ),
                width=600,
                height=420,
            ),
            actions=[ft.TextButton("Close", on_click=lambda e: _close_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open = True
        # Note: page.update() not needed due to page.auto_update = True

    def _close_dialog() -> None:
        if page.dialog:
            page.dialog.open = False
            # Note: page.update() not needed due to page.auto_update = True

    def _build_activity_tile(entry: dict[str, Any]) -> ft.Control:
        """Build enhanced activity tile with strong color coding and hover effects."""
        severity = _infer_severity(entry)
        scheme = (
            page.theme.color_scheme
            if getattr(page, "theme", None)
            and getattr(page.theme, "color_scheme", None)
            else None
        )
        palette = _activity_palette(severity, scheme)

        timestamp = format_timestamp(entry.get("timestamp") or entry.get("time"))
        category = (
            normalize_text(
                entry.get("type") or entry.get("category") or "event"
            ).title()
            or "Event"
        )
        message = normalize_text(
            entry.get("message")
            or entry.get("details")
            or entry.get("description")
            or "—"
        )

        # Build subtitle with timestamp and metadata
        subtitle_parts = [timestamp]
        if component := normalize_text(
            entry.get("component") or entry.get("origin") or ""
        ):
            subtitle_parts.append(f"Component: {component}")
        if client_id := normalize_text(
            entry.get("client_id") or entry.get("client") or ""
        ):
            subtitle_parts.append(f"Client: {client_id}")

        # Build tile with severity badge pill for quick visual scanning
        tile = ft.ListTile(
            leading=ft.Container(
                content=ft.Icon(palette["icon"], size=20, color=palette["text"]),
                width=40,
                height=40,
                bgcolor=ft.Colors.with_opacity(0.18, palette["accent"]),
                border_radius=20,
                alignment=ft.alignment.center,
            ),
            title=ft.Row(
                [
                    # Severity badge pill
                    ft.Container(
                        content=ft.Text(
                            severity.upper(),
                            size=10,
                            weight=ft.FontWeight.W_700,
                            color=palette["text"],
                        ),
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        bgcolor=ft.Colors.with_opacity(0.2, palette["accent"]),
                        border_radius=8,
                    ),
                    ft.Text(f" • {category}", size=14, weight=ft.FontWeight.W_600),
                ]
            ),
            subtitle=ft.Column(
                [
                    ft.Text(
                        message, size=13, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    ft.Text(
                        " • ".join(subtitle_parts),
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            trailing=ft.Icon(
                ft.Icons.CHEVRON_RIGHT, size=20, color=ft.Colors.ON_SURFACE_VARIANT
            ),
        )

        # Enhanced container with stronger colors, left border, hover animation, and click handling
        tile_container = ft.Container(
            content=tile,
            bgcolor=ft.Colors.with_opacity(0.10, palette["accent"]),
            border_radius=12,
            border=ft.border.only(left=ft.BorderSide(4, palette["accent"])),
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            ink=True,
            on_click=lambda e: _open_activity_details(entry),
        )

        # Add hover effect for interactivity
        def on_tile_hover(e):
            tile_container.scale = 1.01 if e.data == "true" else 1.0
            tile_container.update()

        tile_container.on_hover = on_tile_hover

        return ft.Card(
            content=tile_container,
            elevation=2,
        )

    def _apply_activity_filters() -> None:
        """Display all activity without filtering.

        IMPORTANT: Do not call control.update() here. Let the caller batch and
        flush updates once to avoid render thrashing in Flet 0.28.3.
        """
        activity_list.controls.clear()

        if not activity_full_data:
            # Empty state
            activity_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.HISTORY,
                                size=48,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "No recent activity",
                                size=16,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                "Operational events will appear here once the server receives requests.",
                                size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    padding=40,
                    alignment=ft.alignment.center,
                )
            )
            activity_summary_text.value = "No activity"
            with contextlib.suppress(Exception):
                activity_summary_text.update()
            with contextlib.suppress(Exception):
                activity_list.update()
        else:
            # Show all events
            for entry in activity_full_data:
                activity_list.controls.append(_build_activity_tile(entry))

            # Update summary with severity counts
            severity_counter = Counter(
                _infer_severity(entry) for entry in activity_full_data
            )
            summary_bits = [f"{len(activity_full_data)} events"]
            for key in ("critical", "error", "warning", "info"):
                if severity_counter.get(key):
                    summary_bits.append(f"{severity_counter[key]} {key}")
            activity_summary_text.value = " • ".join(summary_bits)
            with contextlib.suppress(Exception):
                activity_summary_text.update()
            with contextlib.suppress(Exception):
                activity_list.update()

    auto_refresh_task: asyncio.Task[Any] | None = None
    stop_event = asyncio.Event()

    async def _auto_refresh_loop() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        try:
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=45)
                except TimeoutError:
                    if disposed or stop_event.is_set():
                        continue
                    if DEBUG:
                        print("[DASH] _auto_refresh_loop → triggering periodic refresh")
                    await _refresh()
        except asyncio.CancelledError:
            if DEBUG:
                print("[DASH] _auto_refresh_loop cancelled")
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            if DEBUG:
                print(f"[DASH] _auto_refresh_loop error: {exc}")

    async def setup() -> None:
        nonlocal auto_refresh_task
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        # CRITICAL: Wait for CanvasKit to fully render controls before updating them
        # Flet 0.28.3 requires delay for proper control attachment
        await asyncio.sleep(0.3)  # Reasonable delay for control attachment
        if DEBUG:
            print("[DASH] setup → controls should now be fully attached")

        if not disposed:
            # Start progressive loading with page.run_task to avoid blocking UI
            if DEBUG:
                print("[DASH] setup → scheduling _start_progressive_loading")
            _schedule_task(_start_progressive_loading)

        if not disposed:
            if DEBUG:
                print("[DASH] setup → scheduling _auto_refresh_loop")
            auto_refresh_task = _schedule_task(_auto_refresh_loop)

        # Proactively force an initial full refresh to populate all sections
        if not disposed:
            if DEBUG:
                print("[DASH] setup → scheduling initial _refresh")
            _schedule_task(_refresh)

    async def _start_progressive_loading() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        """Start progressive loading of dashboard data with phased updates."""
        if disposed:
            return

        try:
            if DEBUG:
                print("[DASH] _start_progressive_loading → Phase 1: critical metrics")
            # Phase 1: Critical metrics (server status, basic stats)
            await _load_critical_metrics()

            # Phase 2: Performance data (CPU, memory, database)
            if DEBUG:
                print("[DASH] _start_progressive_loading → Phase 2: performance data")
            await _load_performance_data()

            # Phase 3: Activity data (recent events)
            if DEBUG:
                print("[DASH] _start_progressive_loading → Phase 3: activity data")
            await _load_activity_data()

            if DEBUG:
                print("[DASH] _start_progressive_loading → Completed all phases")
        except Exception as e:
            show_error_message(page, f"Dashboard loading failed: {e}")

    async def _load_critical_metrics() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        """Load critical metrics without blocking UI."""
        if disposed:
            return

        try:
            # _call_bridge is already async, so we just await it
            if DEBUG:
                print("[DASH] _load_critical_metrics → calling get_dashboard_summary")
            summary = await _call_bridge(server_bridge, "get_dashboard_summary")

            if summary and summary.get("success"):
                # Update UI with critical metrics
                payload = summary.get("data") or {}
                snapshot = DashboardSnapshot(
                    total_clients=int(payload.get("total_clients") or 0),
                    connected_clients=int(payload.get("connected_clients") or 0),
                    total_files=int(payload.get("total_files") or 0),
                    uptime_seconds=float(payload.get("uptime") or 0.0),
                    server_status=str(payload.get("server_status") or "offline"),
                    server_version=str(payload.get("server_version") or ""),
                )

                # Apply critical metrics to UI
                if DEBUG:
                    print("[DASH] _load_critical_metrics → applying snapshot")
                await _apply_snapshot(snapshot)
                if DEBUG:
                    print("[DASH] _load_critical_metrics → snapshot applied")
            else:
                if DEBUG:
                    print(f"[DASH] _load_critical_metrics → FAILED: {summary}")

        except Exception as e:
            print(f"Failed to load critical metrics: {e}")

    async def _load_performance_data() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        """Load performance data without blocking UI."""
        if disposed:
            return

        try:
            # _call_bridge is already async, so we just await it
            if DEBUG:
                print("[DASH] _load_performance_data → calling get_performance_metrics")
            performance = await _call_bridge(server_bridge, "get_performance_metrics")

            if performance and performance.get("success"):
                # Merge performance data into a snapshot and apply via unified updater
                payload = performance.get("data") or {}

                # Build partial snapshot based on latest snapshot_ref to preserve existing values
                base = snapshot_ref or DashboardSnapshot()
                merged = DashboardSnapshot(
                    total_clients=base.total_clients,
                    connected_clients=base.connected_clients,
                    total_files=base.total_files,
                    uptime_seconds=base.uptime_seconds,
                    server_status=base.server_status,
                    server_version=base.server_version,
                    port=base.port,
                    cpu_usage=as_float(payload.get("cpu_usage_percent")),
                    memory_usage_mb=as_float(payload.get("memory_usage_mb")),
                    db_response_ms=as_int(payload.get("database_response_time_ms")),
                    active_connections=max(
                        0, as_int(payload.get("active_connections")) or 0
                    ),
                    recent_activity=base.recent_activity,
                    errors=base.errors,
                )

                await _apply_snapshot(merged)
            else:
                if DEBUG:
                    print(f"[DASH] _load_performance_data → FAILED: {performance}")

        except Exception as e:
            print(f"Failed to load performance data: {e}")

    async def _load_activity_data() -> None:
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"
        """Load activity data without blocking UI."""
        if disposed:
            return

        try:
            # Try async version first
            if DEBUG:
                print("[DASH] _load_activity_data → calling get_recent_activity_async")
            activity = await _call_bridge(
                server_bridge, "get_recent_activity_async", 12
            )

            if not activity or not activity.get("success"):
                # Fallback to sync version
                if DEBUG:
                    print(
                        "[DASH] _load_activity_data → async failed, trying sync get_recent_activity"
                    )
                activity = await _call_bridge(server_bridge, "get_recent_activity", 12)

            if activity and activity.get("success"):
                data = activity.get("data")
                if isinstance(data, list):
                    # Merge activity into a snapshot and apply via unified updater
                    base = snapshot_ref or DashboardSnapshot()
                    merged = DashboardSnapshot(
                        total_clients=base.total_clients,
                        connected_clients=base.connected_clients,
                        total_files=base.total_files,
                        uptime_seconds=base.uptime_seconds,
                        server_status=base.server_status,
                        server_version=base.server_version,
                        port=base.port,
                        cpu_usage=base.cpu_usage,
                        memory_usage_mb=base.memory_usage_mb,
                        db_response_ms=base.db_response_ms,
                        active_connections=base.active_connections,
                        recent_activity=list(data[:12]),
                        errors=base.errors,
                    )
                    await _apply_snapshot(merged)
                else:
                    if DEBUG:
                        print("[DASH] _load_activity_data → success but no data")
            else:
                if DEBUG:
                    print(f"[DASH] _load_activity_data → FAILED: {activity}")

        except Exception as e:
            print(f"Failed to load activity data: {e}")

    def dispose() -> None:
        nonlocal disposed, auto_refresh_task
        disposed = True
        stop_event.set()
        for task in tuple(background_tasks):
            if not task.done():
                task.cancel()
        background_tasks.clear()
        if auto_refresh_task and not auto_refresh_task.done():
            auto_refresh_task.cancel()
        auto_refresh_task = None

    # ============================================================================
    # SECTION 2.5: AGGRESSIVE VISIBILITY FIXES
    # Workarounds for Flet 0.28.3 rendering issues
    # ============================================================================

    def _force_rebuild_metrics_row(
        snapshot: DashboardSnapshot,
        metrics_config: list[tuple],
        metric_blocks: dict[str, dict[str, ft.Control]],
        navigate_callback: Callable[[str], None] | None,
        display_uptime_seconds: float,
    ) -> ft.ResponsiveRow:
        """Force complete rebuild of metrics row to ensure visibility in Flet 0.28.3."""
        DEBUG = os.environ.get("FLET_DASHBOARD_DEBUG") == "1"

        if DEBUG:
            print("[DASH] _force_rebuild_metrics_row → rebuilding all metric blocks")

        # Create new metric blocks with actual values
        new_metric_controls = []

        for key, title, subtitle, icon, accent, route in metrics_config:
            # Get the actual value to display
            if key == "total_clients":
                display_value = (
                    f"{snapshot.total_clients:,}" if snapshot.total_clients else "0"
                )
                display_subtitle = subtitle
            elif key == "active_clients":
                display_value = (
                    f"{snapshot.connected_clients:,}"
                    if snapshot.connected_clients
                    else "0"
                )
                ratio_text = (
                    f"{(snapshot.connected_clients / snapshot.total_clients) * 100:.0f}% online"
                    if snapshot.total_clients > 0
                    else STATUS_CURRENTLY_CONNECTED
                )
                display_subtitle = ratio_text
            elif key == "total_files":
                display_value = (
                    f"{snapshot.total_files:,}" if snapshot.total_files else "0"
                )
                display_subtitle = subtitle
            elif key == "uptime":
                display_value = format_uptime(display_uptime_seconds)
                _chip_level, chip_label = _derive_status(snapshot)
                display_subtitle = chip_label
            else:
                display_value = "0"
                display_subtitle = subtitle

            # Create Text control with the actual value (not placeholder)
            value_text = ft.Text(
                display_value,
                size=30,
                weight=ft.FontWeight.W_700,
                color=ft.Colors.ON_SURFACE,
            )

            footnote_text = ft.Text(
                display_subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT
            )

            # Build the metric block with real values
            body = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, size=22, color=accent),
                            ft.Text(title, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    value_text,
                    footnote_text,
                ],
                spacing=6,
            )

            card_content = ft.Container(
                content=body,
                padding=ft.padding.all(20),
                bgcolor=ft.Colors.SURFACE,
                border_radius=12,
                border=ft.border.only(top=ft.BorderSide(3, accent)),
                shadow=[
                    ft.BoxShadow(
                        blur_radius=8,
                        spread_radius=1,
                        color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                        offset=ft.Offset(0, 2),
                    )
                ],
                animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            )

            # Add hover effect
            def on_hover(e, target=card_content):
                target.scale = 1.02 if e.data == "true" else 1.0
                target.update()

            card_content.on_hover = on_hover

            wrapper = ft.Container(
                content=card_content,
                col={"xs": 12, "sm": 6, "md": 3},
                on_click=(lambda _, destination=route: navigate_callback(destination))
                if route and navigate_callback
                else None,
                ink=True if route and navigate_callback else False,
            )

            new_metric_controls.append(wrapper)

            # Update the metric_blocks reference
            block_data = {
                "wrapper": wrapper,
                "value_text": value_text,
                "footnote_text": footnote_text,
            }
            metric_blocks[key] = block_data

        # Create and return new ResponsiveRow
        new_metrics_row = ft.ResponsiveRow(
            new_metric_controls, spacing=12, run_spacing=12
        )

        if DEBUG:
            print(
                f"[DASH] _force_rebuild_metrics_row → created new row with {len(new_metric_controls)} blocks"
            )

        return new_metrics_row

    return root, dispose, setup
