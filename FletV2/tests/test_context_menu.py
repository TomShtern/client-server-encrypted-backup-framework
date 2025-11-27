#!/usr/bin/env python3
"""
Context Menu Solution Test - Bypass DataTable Button Serialization Bug
This uses right-click context menus instead of inline buttons to work around the Flet serialization bug.
"""

import flet as ft

# Global state for testing
action_count = {"count": 0}
feedback_text = ft.Text(
    "No actions yet - try right-clicking on a row", size=14, color=ft.Colors.BLUE
)


def view_details_action(client_id):
    """View details action via context menu"""
    action_count["count"] += 1
    print(f"VIEW DETAILS ACTION! Client: {client_id}, Count: {action_count['count']}")

    feedback_text.value = (
        f"VIEW DETAILS for {client_id} (action #{action_count['count']})"
    )
    feedback_text.update()

    return f"View Details: {client_id}"


def disconnect_action(client_id):
    """Disconnect action via context menu"""
    action_count["count"] += 1
    print(f"DISCONNECT ACTION! Client: {client_id}, Count: {action_count['count']}")

    feedback_text.value = (
        f"DISCONNECT for {client_id} (action #{action_count['count']})"
    )
    feedback_text.update()

    return f"Disconnect: {client_id}"


def create_context_menu(client_id, page):
    """Create context menu for a client row"""

    def on_view_details(e):
        message = view_details_action(client_id)
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def on_disconnect(e):
        message = disconnect_action(client_id)
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    return ft.MenuBar(
        controls=[
            ft.SubmenuButton(
                content=ft.Text("Actions"),
                controls=[
                    ft.MenuItemButton(
                        content=ft.Row(
                            [ft.Icon(ft.Icons.INFO, size=16), ft.Text("View Details")]
                        ),
                        on_click=on_view_details,
                    ),
                    ft.MenuItemButton(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.POWER_OFF, size=16, color=ft.Colors.RED
                                ),
                                ft.Text("Disconnect"),
                            ]
                        ),
                        on_click=on_disconnect,
                    ),
                ],
            )
        ]
    )


def main(page: ft.Page):
    page.title = "Context Menu Solution Test"

    # Mock clients data
    clients = [
        {
            "client_id": "client_001",
            "address": "192.168.1.101:5432",
            "status": "connected",
        },
        {
            "client_id": "client_002",
            "address": "192.168.1.102:5433",
            "status": "registered",
        },
        {
            "client_id": "client_003",
            "address": "192.168.1.103:5434",
            "status": "offline",
        },
    ]

    # Create DataTable with context menu rows
    def create_clickable_row(client):
        """Create a clickable row with context menu"""

        def on_row_long_press(e):
            """Handle long press (right click equivalent)"""
            print(f"Long press on {client['client_id']}")
            # Create and show context menu
            # menu = create_context_menu(client["client_id"], page)
            # For now, trigger view details directly
            message = view_details_action(client["client_id"])
            page.snack_bar = ft.SnackBar(ft.Text(f"Long press: {message}"))
            page.snack_bar.open = True
            page.update()

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(client["client_id"])),
                ft.DataCell(ft.Text(client["address"])),
                ft.DataCell(ft.Text(client["status"])),
                ft.DataCell(ft.Text("Right-click or long-press for actions")),
            ],
            on_long_press=on_row_long_press,  # This should work!
        )

    datatable = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Client ID", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Address", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
        ],
        rows=[create_clickable_row(client) for client in clients],
        heading_row_color=ft.Colors.SURFACE,
        data_row_min_height=50,
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=8,
    )

    # Alternative: Dropdown approach
    def create_dropdown_row(client):
        """Alternative: Use dropdown in each row"""

        def on_dropdown_change(e):
            action = e.control.value
            if action == "view_details":
                message = view_details_action(client["client_id"])
                page.snack_bar = ft.SnackBar(ft.Text(message))
                page.snack_bar.open = True
                page.update()
            elif action == "disconnect":
                message = disconnect_action(client["client_id"])
                page.snack_bar = ft.SnackBar(ft.Text(message))
                page.snack_bar.open = True
                page.update()
            # Reset dropdown
            e.control.value = None
            e.control.update()

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(client["client_id"])),
                ft.DataCell(ft.Text(client["address"])),
                ft.DataCell(ft.Text(client["status"])),
                ft.DataCell(
                    ft.Dropdown(
                        hint_text="Actions...",
                        options=[
                            ft.dropdown.Option("view_details", "View Details"),
                            ft.dropdown.Option("disconnect", "Disconnect"),
                        ],
                        on_change=on_dropdown_change,
                        width=120,
                    )
                ),
            ]
        )

    dropdown_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Client ID", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Address", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
        ],
        rows=[create_dropdown_row(client) for client in clients],
        heading_row_color=ft.Colors.SURFACE,
        data_row_min_height=50,
        border=ft.border.all(1, ft.Colors.OUTLINE),
        border_radius=8,
    )

    page.add(
        ft.Text(
            "Context Menu & Dropdown Solution Test", size=20, weight=ft.FontWeight.BOLD
        ),
        # Feedback text
        ft.Container(
            content=feedback_text,
            padding=ft.padding.all(10),
            bgcolor=ft.Colors.SURFACE,
            border_radius=4,
        ),
        ft.Divider(),
        ft.Text(
            "Approach 1: Long-press rows for context menu",
            size=16,
            weight=ft.FontWeight.BOLD,
        ),
        datatable,
        ft.Divider(),
        ft.Text(
            "Approach 2: Dropdown actions in each row",
            size=16,
            weight=ft.FontWeight.BOLD,
        ),
        dropdown_table,
    )


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)
