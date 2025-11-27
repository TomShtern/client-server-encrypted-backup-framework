#!/usr/bin/env python3
"""Enhanced analytics view with spectacular Flet charts and Material Design 3."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import os
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import flet as ft

# Constants for analytics messages
NO_DATA_TITLE = "No data"
NO_CHART_DATA_MSG = "No chart data available"
NO_FILE_TYPES_MSG = "No file types to display"
NO_TREND_DATA_MSG = "No trend data available"
NO_BACKUP_ACTIVITY_MSG = "No backup activity in this period"

# Ensure repository roots are on sys.path for runtime resolution
_views_dir = os.path.dirname(os.path.abspath(__file__))
_flet_v2_root = os.path.dirname(_views_dir)
_repo_root = os.path.dirname(_flet_v2_root)
for _path in (_flet_v2_root, _repo_root):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from FletV2.theme import create_skeleton_loader  # noqa: E402
from FletV2.utils.async_helpers import (  # noqa: E402
    run_sync_in_executor,
    safe_server_call,
)
from FletV2.utils.data_export import (  # noqa: E402
    export_to_csv,
    generate_export_filename,
)
from FletV2.utils.loading_states import (  # noqa: E402
    create_empty_state,
    create_error_display,
    create_loading_indicator,
)
from FletV2.utils.ui_builders import (  # noqa: E402
    create_action_button,
    create_view_header,
)
from FletV2.utils.ui_components import AppCard  # noqa: E402
from FletV2.utils.user_feedback import (  # noqa: E402
    show_error_message,
    show_success_message,
)

logger = logging.getLogger(__name__)

try:
    from theme import MODERATE_NEUMORPHIC_SHADOWS, PRONOUNCED_NEUMORPHIC_SHADOWS
except Exception:  # pragma: no cover - fallback for dev mode
    MODERATE_NEUMORPHIC_SHADOWS = []
    PRONOUNCED_NEUMORPHIC_SHADOWS = []


# ============================================================================
# SECTION 1: DATA FETCHING HELPERS
# ============================================================================


@dataclass(slots=True)
class AnalyticsData:
    total_backups: int = 0
    total_storage_gb: float = 0.0
    success_rate: float = 0.0
    avg_backup_size_gb: float = 0.0
    backup_trend: list[dict[str, Any]] | None = None
    client_storage: list[dict[str, Any]] | None = None
    file_type_distribution: list[dict[str, Any]] | None = None


async def fetch_analytics_data(bridge: Any | None) -> AnalyticsData:
    if not bridge:
        return AnalyticsData()

    result = await run_sync_in_executor(safe_server_call, bridge, "get_analytics_data")
    if not result.get("success"):
        logger.debug("Analytics fetch failed: %s", result.get("error"))
        return AnalyticsData()

    payload = result.get("data") or {}
    return AnalyticsData(
        total_backups=int(payload.get("total_backups", 0) or 0),
        total_storage_gb=float(payload.get("total_storage_gb", 0.0) or 0.0),
        success_rate=float(payload.get("success_rate", 0.0) or 0.0),
        avg_backup_size_gb=float(payload.get("avg_backup_size_gb", 0.0) or 0.0),
        backup_trend=list(payload.get("backup_trend") or []),
        client_storage=list(payload.get("client_storage") or []),
        file_type_distribution=list(payload.get("file_type_distribution") or []),
    )


# ============================================================================
# SECTION 3: UI BUILDERS
# ============================================================================


def _metric_card(
    title: str, value: str, subtitle: str, icon: str, color: str
) -> ft.Control:
    """Create enhanced metric card with gradient accent and hover effects."""
    card_content = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, size=22, color=ft.Colors.WHITE),
                            bgcolor=color,
                            padding=12,
                            border_radius=14,
                            shadow=[
                                ft.BoxShadow(
                                    blur_radius=12,
                                    spread_radius=0,
                                    color=ft.Colors.with_opacity(0.3, color),
                                    offset=ft.Offset(0, 2),
                                )
                            ],
                        ),
                        ft.Text(
                            title,
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.LEFT,
                        ),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(
                    content=ft.Text(
                        value,
                        size=34,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.padding.only(top=8, bottom=4),
                ),
                ft.Text(
                    subtitle,
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    opacity=0.8,
                ),
            ],
            spacing=10,
        ),
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.OUTLINE)),
        shadow=[
            ft.BoxShadow(
                blur_radius=16,
                spread_radius=0,
                color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            )
        ],
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )

    def on_hover(e):
        card_content.scale = 1.02 if e.data == "true" else 1.0
        card_content.shadow = [
            ft.BoxShadow(
                blur_radius=24 if e.data == "true" else 16,
                spread_radius=0,
                color=ft.Colors.with_opacity(
                    0.10 if e.data == "true" else 0.06, ft.Colors.BLACK
                ),
                offset=ft.Offset(0, 4 if e.data == "true" else 2),
            )
        ]
        card_content.update()

    card_content.on_hover = on_hover
    return card_content


def _create_bar_chart(
    data: list[dict[str, Any]], x_key: str, y_key: str, title: str, color: str
) -> ft.Control:
    """Create beautiful bar chart with gradients and animations."""
    if not data:
        return create_empty_state(NO_DATA_TITLE, NO_CHART_DATA_MSG)

    # Limit to 7 items for clean visualization
    data = data[:7]

    # Extract all values (in GB) and convert to MB for better readability
    values_gb = [float(item.get(y_key, 0)) for item in data]
    values_mb = [v * 1024 for v in values_gb]  # Convert GB to MB
    max_value_mb = max(values_mb, default=0)

    # Determine if we have real data or just zeros
    has_real_data = max_value_mb > 0

    # For visualization: use 10.0 MB as baseline if all values are zero
    chart_max = max_value_mb if has_real_data else 10.0

    bar_groups = []
    for idx, item in enumerate(data):
        value_gb = float(item.get(y_key, 0))
        value_mb = value_gb * 1024  # Convert to MB for display
        label_text = str(item.get(x_key, ""))

        # If all data is zero, show equal-height bars at 80% for visual consistency
        # If real data exists, show proportional bars with 10% minimum
        if not has_real_data:
            display_value = 8.0  # Equal bars at 8 MB when no data
        else:
            display_value = max(value_mb, chart_max * 0.10)  # Proportional with minimum

        bar_groups.append(
            ft.BarChartGroup(
                x=idx,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=display_value,
                        width=40,
                        color=color,
                        tooltip=f"{label_text}: {value_mb:.2f} MB",
                        border_radius=ft.border_radius.only(top_left=8, top_right=8),
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.bottom_center,
                            end=ft.alignment.top_center,
                            colors=[
                                color,
                                ft.Colors.with_opacity(0.7, color),
                            ],
                        ),
                    )
                ],
            )
        )

    # Create cleaner x-axis labels
    def create_clean_label(text: str) -> str:
        """Create clean, short labels for x-axis."""
        # Try to extract number from client name (e.g., "TestNumber5" -> "C5")
        import re

        match = re.search(r"\d+$", text)
        if match:
            return f"C{match.group()}"
        # Otherwise use short abbreviation
        if len(text) <= 4:
            return text
        return f"{text[:3]}..."

    chart = ft.BarChart(
        bar_groups=bar_groups,
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.OUTLINE)),
        left_axis=ft.ChartAxis(
            labels_size=32,
            show_labels=True,
            labels_interval=max(1, chart_max / 5),  # MB intervals (minimum 1 MB)
        ),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=idx,
                    label=ft.Text(
                        create_clean_label(str(item.get(x_key, ""))),
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
                for idx, item in enumerate(data)
            ],
            labels_size=40,
        ),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=max(1, chart_max / 5),  # MB intervals (minimum 1 MB)
            color=ft.Colors.with_opacity(0.08, ft.Colors.OUTLINE),
            width=1,
        ),
        tooltip_bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.SURFACE),
        max_y=chart_max * 1.2,
        interactive=True,
        expand=True,
        animate=1000,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    title,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(content=chart, height=220, expand=True),
            ],
            spacing=12,
        ),
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.OUTLINE)),
        shadow=MODERATE_NEUMORPHIC_SHADOWS,
    )


def _create_pie_chart(
    data: list[dict[str, Any]], label_key: str, value_key: str, title: str
) -> ft.Control:
    """Create colorful pie chart with interactive legend."""
    if not data:
        return create_empty_state(NO_DATA_TITLE, NO_CHART_DATA_MSG)

    # Enhanced color palette for pie sections
    colors = [
        ft.Colors.BLUE_400,
        ft.Colors.GREEN_400,
        ft.Colors.PURPLE_400,
        ft.Colors.ORANGE_400,
        ft.Colors.PINK_400,
        ft.Colors.CYAN_400,
        ft.Colors.TEAL_400,
        ft.Colors.AMBER_400,
    ]

    total = sum(float(item.get(value_key, 0)) for item in data)
    if total == 0:
        return create_empty_state(NO_DATA_TITLE, NO_FILE_TYPES_MSG)

    sections = []
    for idx, item in enumerate(data[:8]):  # Limit to 8 slices for clarity
        value = float(item.get(value_key, 0))
        percentage = (value / total) * 100
        sections.append(
            ft.PieChartSection(
                value=value,
                title=f"{percentage:.1f}%",
                title_style=ft.TextStyle(
                    size=11,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
                color=colors[idx % len(colors)],
                radius=85,
                badge=ft.Container(
                    content=ft.Icon(
                        ft.Icons.INSERT_DRIVE_FILE, size=18, color=ft.Colors.WHITE
                    ),
                    bgcolor=colors[idx % len(colors)],
                    padding=6,
                    border_radius=16,
                ),
                badge_position=0.98,
            )
        )

    chart = ft.PieChart(
        sections=sections,
        sections_space=2,
        center_space_radius=0,
        expand=True,
        animate=1200,
    )

    # Create enhanced legend with file extension formatting
    legend_items = []
    for idx, item in enumerate(data[:8]):
        raw_label = str(item.get(label_key, "Unknown"))
        # Format file extensions nicely (e.g., ".txt" -> "TXT")
        label = (
            raw_label.upper().replace(".", "")
            if raw_label.startswith(".")
            else raw_label[:12]
        )
        value = item.get(value_key, 0)
        percentage = (float(value) / total) * 100

        legend_item = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=16,
                        height=16,
                        bgcolor=colors[idx % len(colors)],
                        border_radius=4,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                label,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=ft.Colors.ON_SURFACE,
                            ),
                            ft.Text(
                                f"{value} files ({percentage:.1f}%)",
                                size=10,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=2,
                        tight=True,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=10),
            border_radius=10,
            ink=True,
            animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

        def on_legend_hover(e, target=legend_item):
            target.scale = 1.05 if e.data == "true" else 1.0
            target.bgcolor = (
                ft.Colors.with_opacity(0.08, ft.Colors.PRIMARY)
                if e.data == "true"
                else None
            )
            target.update()

        legend_item.on_hover = on_legend_hover
        legend_items.append(legend_item)

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    title,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=chart,
                            height=200,
                            width=200,
                            padding=10,
                        ),
                        ft.Container(
                            content=ft.Column(
                                legend_items, spacing=6, scroll=ft.ScrollMode.AUTO
                            ),
                            expand=True,
                        ),
                    ],
                    spacing=24,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=16,
        ),
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.OUTLINE)),
        shadow=MODERATE_NEUMORPHIC_SHADOWS,
    )


def _create_line_chart(
    data: list[dict[str, Any]], x_key: str, y_key: str, title: str, color: str
) -> ft.Control:
    """Create smooth line chart with gradient fills and animations."""
    if not data:
        return create_empty_state(NO_DATA_TITLE, NO_TREND_DATA_MSG)

    data_points = [
        ft.LineChartDataPoint(idx, float(item.get(y_key, 0)))
        for idx, item in enumerate(data)
    ]

    max_y = max((p.y for p in data_points), default=1)

    # Check if all values are zero
    if max_y < 0.001:
        return create_empty_state(NO_DATA_TITLE, NO_BACKUP_ACTIVITY_MSG)

    max_y = max_y * 1.2

    # Format date labels for better readability
    def format_date_label(date_str: str) -> str:
        """Format date string for x-axis (e.g., '10/25' -> '10/25')."""
        try:
            # Try to parse and format
            if "/" in date_str:
                parts = date_str.split("/")
                if len(parts) >= 2:
                    return f"{parts[0]}/{parts[1]}"
            return date_str[:5]  # Truncate to reasonable length
        except Exception:
            return str(date_str)[:5]

    chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=data_points,
                stroke_width=3,
                color=color,
                curved=True,
                stroke_cap_round=True,
                below_line_bgcolor=ft.Colors.with_opacity(0.15, color),
                below_line_cutoff_y=0,
            )
        ],
        border=ft.border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.OUTLINE)),
        horizontal_grid_lines=ft.ChartGridLines(
            interval=max(0.5, max_y / 5),
            color=ft.Colors.with_opacity(0.08, ft.Colors.OUTLINE),
            width=1,
        ),
        vertical_grid_lines=ft.ChartGridLines(
            interval=1,
            color=ft.Colors.with_opacity(0.05, ft.Colors.OUTLINE),
            width=1,
        ),
        left_axis=ft.ChartAxis(
            labels_size=40,
            show_labels=True,
            labels_interval=max(0.5, max_y / 5),
        ),
        bottom_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(
                    value=idx,
                    label=ft.Text(
                        format_date_label(str(item.get(x_key, ""))),
                        size=10,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
                for idx, item in enumerate(data)
            ],
            labels_size=32,
        ),
        tooltip_bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.SURFACE),
        max_y=max_y,
        min_y=0,
        interactive=True,
        expand=True,
        animate=1000,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    title,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.ON_SURFACE,
                ),
                ft.Container(content=chart, height=220, expand=True),
            ],
            spacing=12,
        ),
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.OUTLINE)),
        shadow=MODERATE_NEUMORPHIC_SHADOWS,
    )


# ============================================================================
# SECTION 4: MAIN VIEW
# ============================================================================


def create_analytics_view(
    server_bridge: Any | None,
    page: ft.Page,
    _state_manager: Any | None = None,
    navigate_callback: Callable[[str], None] | None = None,
    global_search: ft.Control | None = None,
) -> tuple[ft.Control, Callable[[], None], Callable[[], Coroutine[Any, Any, None]]]:
    """Create spectacular analytics view with real-time charts and insights."""
    _ = (_state_manager, navigate_callback)  # Unused but required by interface

    state = {
        "data": AnalyticsData(),
    }

    loading_overlay = create_loading_indicator("Loading analytics…")
    error_panel = ft.Container(visible=False)

    # Initial skeleton loaders for metrics
    skeleton_metrics = [
        ft.Container(
            content=ft.Column(
                [
                    create_skeleton_loader(height=20, width=120),
                    create_skeleton_loader(height=40, width=100),
                    create_skeleton_loader(height=16, width=80),
                ],
                spacing=12,
            ),
            padding=24,
            bgcolor=ft.Colors.SURFACE,
            border_radius=16,
            border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.OUTLINE)),
            col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
        )
        for _ in range(4)
    ]

    metrics_row = ft.ResponsiveRow(skeleton_metrics, spacing=16, run_spacing=16)
    trend_panel = ft.Container(content=create_skeleton_loader(height=200))
    storage_panel = ft.Container(content=create_skeleton_loader(height=200))
    file_type_panel = ft.Container(content=create_skeleton_loader(height=200))

    metrics_section = AppCard(metrics_row, title="Key metrics")
    trend_section = AppCard(trend_panel, title="Backup trend")
    storage_section = AppCard(storage_panel, title="Client storage")
    file_type_section = AppCard(file_type_panel, title="File types")

    trend_section.col = {"sm": 12, "md": 6, "lg": 4}
    storage_section.col = {"sm": 12, "md": 6, "lg": 4}
    file_type_section.col = {"sm": 12, "md": 12, "lg": 4}
    file_type_section.expand = True

    def apply_data(data: AnalyticsData) -> None:
        """Apply fetched data to all UI components with spectacular visualizations."""
        # Update enhanced metric cards
        metrics_row.controls = [
            ft.Container(
                _metric_card(
                    "Total Backups",
                    f"{data.total_backups:,}",
                    "Files secured",
                    ft.Icons.BACKUP_TABLE,
                    ft.Colors.BLUE,
                ),
                col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
            ),
            ft.Container(
                _metric_card(
                    "Total Storage",
                    f"{data.total_storage_gb:.2f} GB",
                    "Encrypted data",
                    ft.Icons.STORAGE,
                    ft.Colors.GREEN,
                ),
                col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
            ),
            ft.Container(
                _metric_card(
                    "Success Rate",
                    f"{data.success_rate:.1f}%",
                    "Verified backups",
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    ft.Colors.PURPLE,
                ),
                col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
            ),
            ft.Container(
                _metric_card(
                    "Avg Size",
                    f"{data.avg_backup_size_gb:.3f} GB",
                    "Per backup",
                    ft.Icons.PIE_CHART_OUTLINE,
                    ft.Colors.TEAL,
                ),
                col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
            ),
        ]
        metrics_row.update()

        # Update charts with real data visualizations
        trend_panel.content = _create_line_chart(
            data.backup_trend or [],
            "date",
            "count",
            "7-Day Backup Trend",
            ft.Colors.BLUE_400,
        )

        storage_panel.content = _create_bar_chart(
            data.client_storage or [],
            "client",
            "storage_gb",
            "Top Clients by Storage (MB)",
            ft.Colors.GREEN_400,
        )

        file_type_panel.content = _create_pie_chart(
            data.file_type_distribution or [], "type", "count", "File Type Distribution"
        )

        for panel in (trend_panel, storage_panel, file_type_panel):
            panel.update()

    async def refresh_data(toast: bool = False) -> None:
        error_panel.visible = False
        error_panel.update()
        overlay_container.visible = True
        overlay_container.update()

        try:
            data = await fetch_analytics_data(server_bridge)
            state["data"] = data
            apply_data(data)
            if toast:
                show_success_message(page, "Analytics refreshed")
        except Exception as exc:  # pragma: no cover - defensive UI feedback
            logger.exception("Analytics refresh failed")

            # Create error display with retry button
            error_content = ft.Column(
                [
                    create_error_display(str(exc)),
                    ft.Container(
                        content=ft.ElevatedButton(
                            "Retry",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda _: schedule_task(
                                lambda: refresh_data(toast=False)
                            ),
                        ),
                        padding=ft.padding.only(top=12),
                        alignment=ft.alignment.center,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            )

            error_panel.content = AppCard(error_content, title="Error")
            error_panel.visible = True
            error_panel.update()
            show_error_message(page, f"Analytics load failed: {exc}")
        finally:
            overlay_container.visible = False
            overlay_container.update()

    def schedule_task(task: Any) -> None:
        async def runner() -> None:
            if inspect.isawaitable(task):
                await task
                return
            result = task()
            if inspect.isawaitable(result):
                await result

        if hasattr(page, "run_task"):
            page.run_task(runner)
        else:
            asyncio.get_event_loop().create_task(runner())

    def on_refresh(_: ft.ControlEvent) -> None:
        """Handle refresh button click."""
        schedule_task(lambda: refresh_data(toast=True))

    def on_export(_: ft.ControlEvent) -> None:
        """Handle export button click."""
        try:
            data = state.get("data")
            if not data or not isinstance(data, AnalyticsData):
                show_error_message(page, "No analytics data available to export")
                return

            # Prepare export data
            export_rows = []

            # Add summary metrics
            export_rows.append(
                {
                    "Category": "Summary",
                    "Metric": "Total Backups",
                    "Value": f"{data.total_backups:,}",
                    "Unit": "files",
                }
            )
            export_rows.append(
                {
                    "Category": "Summary",
                    "Metric": "Total Storage",
                    "Value": f"{data.total_storage_gb:.2f}",
                    "Unit": "GB",
                }
            )
            export_rows.append(
                {
                    "Category": "Summary",
                    "Metric": "Success Rate",
                    "Value": f"{data.success_rate:.1f}",
                    "Unit": "%",
                }
            )
            export_rows.append(
                {
                    "Category": "Summary",
                    "Metric": "Average Backup Size",
                    "Value": f"{data.avg_backup_size_gb:.3f}",
                    "Unit": "GB",
                }
            )

            # Add trend data
            if data.backup_trend:
                for item in data.backup_trend:
                    export_rows.append(
                        {
                            "Category": "Backup Trend",
                            "Metric": item.get("date", "Unknown"),
                            "Value": str(item.get("count", 0)),
                            "Unit": "backups",
                        }
                    )

            # Add client storage data
            if data.client_storage:
                for item in data.client_storage:
                    export_rows.append(
                        {
                            "Category": "Client Storage",
                            "Metric": item.get("client", "Unknown"),
                            "Value": f"{item.get('storage_gb', 0):.2f}",
                            "Unit": "GB",
                        }
                    )

            # Add file type distribution
            if data.file_type_distribution:
                for item in data.file_type_distribution:
                    export_rows.append(
                        {
                            "Category": "File Types",
                            "Metric": item.get("type", "Unknown"),
                            "Value": str(item.get("count", 0)),
                            "Unit": "files",
                        }
                    )

            # Export to CSV
            filename = generate_export_filename("analytics", "csv")
            export_to_csv(
                export_rows,
                filename,
                fieldnames=["Category", "Metric", "Value", "Unit"],
            )
            show_success_message(page, f"Analytics exported to {filename}")

        except Exception as exc:
            logger.exception("Export failed")
            show_error_message(page, f"Export failed: {exc}")

    header_actions: list[ft.Control] = [
        create_action_button(
            "Export", on_export, icon=ft.Icons.DOWNLOAD, primary=False
        ),
        create_action_button("Refresh", on_refresh, icon=ft.Icons.REFRESH),
    ]
    # Note: Global search is in the app-level header (main.py), not view-level

    header = create_view_header(
        "Analytics",
        icon=ft.Icons.INSIGHTS,
        description="Understand backup performance and capacity usage.",
        actions=header_actions,
    )

    secondary_sections = ft.ResponsiveRow(
        [trend_section, storage_section, file_type_section],
        spacing=16,
        run_spacing=16,
    )

    content_column = ft.Column(
        [
            header,
            metrics_section,
            secondary_sections,
            error_panel,
        ],
        spacing=16,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    main_layout = ft.Container(
        content=content_column,
        padding=ft.padding.symmetric(horizontal=20, vertical=16),
        expand=True,
    )

    stack = ft.Stack(
        [
            main_layout,
            ft.Container(
                content=loading_overlay,
                alignment=ft.alignment.center,
                expand=True,
                visible=False,
            ),
        ],
        expand=True,
    )
    overlay_container = stack.controls[1]

    # Auto-refresh state
    auto_refresh_task: asyncio.Task[Any] | None = None
    stop_event = asyncio.Event()
    disposed = False

    async def auto_refresh_loop() -> None:
        """Auto-refresh analytics every 60 seconds."""
        try:
            while not stop_event.is_set() and not disposed:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=60)
                except TimeoutError:
                    # Double-check disposal state before attempting refresh
                    if disposed or stop_event.is_set():
                        logger.debug(
                            "Analytics view disposed during refresh cycle - stopping auto-refresh"
                        )
                        break
                    try:
                        await refresh_data()
                    except (RuntimeError, asyncio.CancelledError):
                        # Executor shutdown or task cancelled - stop gracefully
                        logger.debug("Auto-refresh stopped due to executor shutdown")
                        break
                    except Exception as exc:
                        logger.debug("Auto-refresh encountered error: %s", exc)
                        # Continue loop for transient errors, break for shutdown
                        if (
                            "shutdown" in str(exc).lower()
                            or "executor" in str(exc).lower()
                        ):
                            break
        except asyncio.CancelledError:
            # Expected during shutdown - exit cleanly
            logger.debug("Auto-refresh task cancelled")
            raise
        except Exception as exc:
            logger.debug("Auto-refresh loop stopped: %s", exc)

    async def setup() -> None:
        nonlocal auto_refresh_task
        overlay_container.visible = True
        overlay_container.update()
        await refresh_data()
        overlay_container.visible = False
        overlay_container.update()

        # Start auto-refresh loop
        if not disposed:
            auto_refresh_task = asyncio.create_task(auto_refresh_loop())

    def dispose() -> None:
        """Clean up resources and stop auto-refresh."""
        nonlocal disposed, auto_refresh_task
        disposed = True
        stop_event.set()

        # Cancel auto-refresh task if running
        if auto_refresh_task and not auto_refresh_task.done():
            with contextlib.suppress(Exception):
                auto_refresh_task.cancel()

        auto_refresh_task = None
        logger.debug("Analytics view disposed cleanly")

    return stack, dispose, setup
