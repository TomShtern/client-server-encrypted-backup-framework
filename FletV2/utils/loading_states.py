"""
Loading States for FletV2 - Standardized loading, error, and empty state displays.

This module provides consistent UI components for:
- Loading indicators
- Error displays
- Empty states
- Snackbar notifications
"""

from dataclasses import dataclass
from typing import Any

import flet as ft

from FletV2.utils.debug_setup import get_logger


def create_loading_indicator(message="Loading..."):
    """
    Create standardized loading indicator.

    Args:
        message: Message to display with the loading indicator

    Returns:
        Container with loading indicator and message
    """
    return ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(),
                ft.Text(message, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        padding=20,
    )


def create_error_display(error_message):
    """
    Create standardized error display.

    Args:
        error_message: Error message to display

    Returns:
        Container with error icon and message
    """
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.ERROR, size=48),
                ft.Text(
                    "Error", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.ERROR
                ),
                ft.Text(
                    error_message,
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.alignment.center,
        padding=20,
    )


def create_empty_state(title, message, icon=None):
    """
    Create standardized empty state display.

    Args:
        title: Title for the empty state
        message: Message for the empty state
        icon: Icon to display (default: INBOX_OUTLINED)

    Returns:
        Container with icon, title, and message for empty state
    """
    resolved_icon = icon or ft.Icons.INBOX_OUTLINED

    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(resolved_icon, color=ft.Colors.ON_SURFACE_VARIANT, size=64),
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(
                    message,
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.alignment.center,
        padding=40,
    )


# Snackbar functions removed - use user_feedback.py instead
# - show_success_message(page, message)
# - show_error_message(page, message)
# - show_info_message(page, message)
# - show_warning_message(page, message)


# ============================================================================
# Pattern 2 Consolidation: Loading State Management
# ============================================================================
"""
The following classes implement Pattern 2 from CONSOLIDATION_OPPORTUNITIES.md:
unified loading state management with automatic cleanup via context managers.

This consolidates 30-40 lines of duplicated loading state code per view
into a single 5-8 line pattern.
"""

logger = get_logger(__name__)


@dataclass
class LoadingStateConfig:
    """
    Configuration for loading state UI components.

    Attributes:
        loading_indicator: ProgressRing or ProgressBar to show during loading
        loading_text: Text control to display loading message
        error_banner: Banner control to display error messages
        success_banner: Optional banner for success messages
        page: Flet Page instance for updates (optional if auto_update is enabled)
    """

    loading_indicator: Any  # ft.ProgressRing | ft.ProgressBar
    loading_text: Any  # ft.Text
    error_banner: Any  # ft.Banner
    success_banner: Any | None = None  # ft.Banner
    page: Any | None = None  # ft.Page


class LoadingStateManager:
    """
    Manages loading, error, and success states for async operations.

    This class consolidates the duplicated loading state management pattern
    found across all views. It provides:
    - Automatic loading indicator show/hide
    - Structured error handling with banner display
    - Optional success feedback
    - Async context manager for automatic cleanup

    Example:
        manager = LoadingStateManager(LoadingStateConfig(...))

        # With context manager (automatic cleanup on success/error)
        async with manager.loading("Loading clients..."):
            result = await fetch_clients()
            if not result['success']:
                manager.show_error(result['error'])
                return
            manager.show_success("Clients loaded!")
            return result['data']

        # Manual control (for complex flows)
        manager.show_loading("Processing...")
        try:
            process_data()
            manager.show_success("Done!")
        except Exception as e:
            manager.show_error(str(e))
        finally:
            manager.hide_loading()
    """

    def __init__(self, config: LoadingStateConfig):
        """
        Initialize the loading state manager.

        Args:
            config: LoadingStateConfig with all UI components
        """
        self.config = config
        self._is_loading = False

    @property
    def is_loading(self) -> bool:
        """Check if currently in loading state."""
        return self._is_loading

    def loading(self, message: str) -> "_LoadingContext":
        """
        Create a context manager for loading operations.

        Args:
            message: Loading message to display

        Returns:
            Async context manager that handles show/hide automatically

        Example:
            async with manager.loading("Loading data..."):
                data = await fetch_data()
                # Errors are automatically caught and displayed
                # Loading state automatically cleaned up
        """
        return _LoadingContext(self, message)

    def show_loading(self, message: str) -> None:
        """
        Show loading state with message.

        Args:
            message: Loading message to display
        """
        self._is_loading = True
        self.config.loading_indicator.visible = True
        self.config.loading_text.value = message
        self.config.loading_text.visible = True

        # Hide any existing banners
        self.config.error_banner.open = False
        if self.config.success_banner:
            self.config.success_banner.open = False

        self._update_page()

    def hide_loading(self) -> None:
        """Hide loading state."""
        self._is_loading = False
        self.config.loading_indicator.visible = False
        self.config.loading_text.visible = False
        self._update_page()

    def show_error(self, error_message: str, _duration: int | None = None) -> None:
        """
        Show error banner with message.

        Args:
            error_message: Error message to display
            duration: Optional auto-dismiss duration in seconds
        """
        self.hide_loading()

        self.config.error_banner.content = ft.Text(
            error_message,
            color=ft.colors.ON_ERROR_CONTAINER,
        )
        self.config.error_banner.bgcolor = ft.colors.ERROR_CONTAINER
        self.config.error_banner.open = True

        self._update_page()
        logger.error(f"UI Error: {error_message}")

    def show_success(self, message: str, _duration: int | None = None) -> None:
        """
        Show success banner with message.

        Args:
            message: Success message to display
            duration: Optional auto-dismiss duration in seconds
        """
        self.hide_loading()

        if self.config.success_banner:
            self.config.success_banner.content = ft.Text(
                message,
                color=ft.colors.ON_TERTIARY_CONTAINER,
            )
            self.config.success_banner.bgcolor = ft.colors.TERTIARY_CONTAINER
            self.config.success_banner.open = True
            self._update_page()
            logger.info(f"UI Success: {message}")

    def clear_messages(self) -> None:
        """Clear all error and success messages."""
        self.config.error_banner.open = False
        if self.config.success_banner:
            self.config.success_banner.open = False
        self._update_page()

    def _update_page(self) -> None:
        """
        Update the page if available and not in auto_update mode.

        If page.auto_update is True, this is a no-op since Flet handles updates.
        """
        if self.config.page and not getattr(self.config.page, "auto_update", False):
            self.config.page.update()


class _LoadingContext:
    """
    Async context manager for loading operations.

    This provides automatic cleanup and error handling for async operations.
    Used internally by LoadingStateManager.loading() method.
    """

    def __init__(self, manager: LoadingStateManager, message: str):
        """
        Initialize the loading context.

        Args:
            manager: LoadingStateManager instance
            message: Loading message to display
        """
        self.manager = manager
        self.message = message

    async def __aenter__(self) -> LoadingStateManager:
        """Enter the context - show loading state."""
        self.manager.show_loading(self.message)
        return self.manager

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: Any,
    ) -> bool:
        """
        Exit the context - hide loading state.

        If an exception occurred, show it as an error.

        Returns:
            False to propagate exceptions (don't suppress)
        """
        if exc_type is not None:
            # Exception occurred during loading
            error_message = str(exc_val) if exc_val else f"{exc_type.__name__}"
            self.manager.show_error(f"Error: {error_message}")
            logger.exception(f"Loading context exception: {error_message}")
            return False  # Don't suppress the exception

        # Success - just hide loading (view can show success message if needed)
        self.manager.hide_loading()
        return False
