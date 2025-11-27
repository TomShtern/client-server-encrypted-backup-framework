#!/usr/bin/env python3
"""
Test script to demonstrate terminal debugging capabilities.
Shows how all logging output goes to terminal including exceptions.
"""

import flet as ft

# Import terminal debugging setup
from utils.debug_setup import setup_terminal_debugging

logger = setup_terminal_debugging(logger_name="FletV2.test")


def main(page: ft.Page):
    """Simple test app to demonstrate logging."""
    page.title = "FletV2 Logging Test"
    page.window_width = 600
    page.window_height = 400

    logger.info("Test application started")
    logger.debug("Page configured with title and dimensions")

    def on_info_click(e):
        logger.info("Info button clicked - this is normal operation")
        page.snack_bar = ft.SnackBar(content=ft.Text("Info logged to terminal"))
        page.snack_bar.open = True
        page.update()

    def on_warning_click(e):
        logger.warning("Warning button clicked - something unexpected happened")
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Warning logged to terminal"), bgcolor=ft.Colors.ORANGE
        )
        page.snack_bar.open = True
        page.update()

    def on_error_click(e):
        try:
            # Intentionally cause an error to demonstrate exception logging
            _ = 1 / 0
        except Exception as ex:
            logger.error(f"Intentional error for testing: {ex}", exc_info=True)
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Error logged with full traceback"),
                bgcolor=ft.Colors.RED,
            )
            page.snack_bar.open = True
            page.update()

    def on_uncaught_error_click(e):
        logger.info("About to trigger uncaught exception...")
        # This will be caught by the global exception handler
        raise ValueError("This uncaught exception will be logged by sys.excepthook")

    page.add(
        ft.Column(
            [
                ft.Text(
                    "FletV2 Terminal Debugging Test", size=20, weight=ft.FontWeight.BOLD
                ),
                ft.Divider(),
                ft.Text("Click buttons below to test different log levels:"),
                ft.ElevatedButton("Log INFO message", on_click=on_info_click),
                ft.ElevatedButton("Log WARNING message", on_click=on_warning_click),
                ft.ElevatedButton("Log ERROR with traceback", on_click=on_error_click),
                ft.ElevatedButton(
                    "Trigger uncaught exception", on_click=on_uncaught_error_click
                ),
                ft.Divider(),
                ft.Text(
                    "Watch the terminal output for all logging messages!",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=15,
            expand=True,
        )
    )

    logger.info("Test UI created successfully")


if __name__ == "__main__":
    logger.info("Starting Flet logging test application")
    ft.app(target=main, view=ft.AppView.FLET_APP)
