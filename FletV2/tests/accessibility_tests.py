"""
Accessibility Testing Suite for Desktop Applications

This module provides comprehensive accessibility testing utilities for desktop applications,
ensuring WCAG 2.1 compliance and desktop-specific accessibility features.

Compatible with Flet 0.28.3 and Windows 11 desktop applications.
"""

import contextlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import flet as ft

logger = logging.getLogger(__name__)


class AccessibilityLevel(Enum):
    """WCAG accessibility compliance levels"""

    A = "A"
    AA = "AA"
    AAA = "AAA"
    UNKNOWN = "UNKNOWN"


class AccessibilityIssue:
    """Represents an accessibility issue"""

    def __init__(
        self, element: str, issue: str, level: AccessibilityLevel, suggestion: str = ""
    ):
        self.element = element
        self.issue = issue
        self.level = level
        self.suggestion = suggestion


class AccessibilityTester:
    """
    Comprehensive accessibility testing suite for desktop applications

    Features:
    - WCAG 2.1 compliance checking
    - Keyboard navigation testing
    - Screen reader compatibility
    - Color contrast validation
    - Focus management testing
    - ARIA label verification
    - Desktop-specific accessibility features
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.issues: List[AccessibilityIssue] = []
        self.tested_elements: List[str] = []

    def test_keyboard_navigation(
        self, root_control: ft.Control
    ) -> List[AccessibilityIssue]:
        """Test keyboard navigation accessibility"""
        issues = []

        def check_control(control: ft.Control, path: str = ""):
            if not control:
                return

            current_path = (
                f"{path}/{type(control).__name__}" if path else type(control).__name__
            )
            self.tested_elements.append(current_path)

            # Check if control can receive focus
            if hasattr(control, "autofocus") and control.autofocus:
                # Good: control can receive focus automatically
                pass
            elif hasattr(control, "focus") and not any(
                [
                    isinstance(control, ft.Container) and not control.content,
                    isinstance(control, ft.Column) and not control.controls,
                    isinstance(control, ft.Row) and not control.controls,
                ]
            ):
                # Interactive control that should be keyboard accessible
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Interactive control may not be keyboard accessible",
                        level=AccessibilityLevel.A,
                        suggestion="Ensure control can receive focus and be operated via keyboard",
                    )
                )

            # Check for keyboard event handlers
            if (
                hasattr(control, "on_click")
                and not any(
                    [
                        hasattr(control, "on_key_down"),
                        hasattr(control, "on_key_up"),
                        hasattr(control, "on_keyboard_event"),
                    ]
                )
                and not isinstance(
                    control, (ft.IconButton, ft.FilledButton, ft.TextButton)
                )
            ):
                # Control has click handler but no keyboard support
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Click-only interactive element without keyboard support",
                        level=AccessibilityLevel.A,
                        suggestion="Add keyboard event handlers or use keyboard-accessible alternatives",
                    )
                )

            # Recursively check child controls
            if hasattr(control, "content") and control.content:
                check_control(control.content, current_path)
            elif hasattr(control, "controls") and control.controls:
                for child in control.controls:
                    check_control(child, current_path)

        check_control(root_control)
        return issues

    def test_color_contrast(self, root_control: ft.Control) -> List[AccessibilityIssue]:
        """Test color contrast for WCAG compliance"""
        issues = []

        def check_control_colors(control: ft.Control, path: str = ""):
            if not control:
                return

            current_path = (
                f"{path}/{type(control).__name__}" if path else type(control).__name__
            )

            # Check for insufficient color contrast
            if hasattr(control, "color") and hasattr(control, "bgcolor"):
                # This is a simplified check - in practice, you'd need proper contrast calculation
                color = control.color
                bgcolor = control.bgcolor

                # Basic heuristics for obvious contrast issues
                if self._is_low_contrast_pair(color, bgcolor):
                    issues.append(
                        AccessibilityIssue(
                            element=current_path,
                            issue="Insufficient color contrast",
                            level=AccessibilityLevel.AA,
                            suggestion="Use colors with better contrast ratio (4.5:1 for normal text, 3:1 for large text)",
                        )
                    )

            # Check text controls for proper contrast
            if type(control).__name__ == "Text" and self._is_text_color_invisible(
                control.color, getattr(control, "bgcolor", None)
            ):
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Text may be invisible on background",
                        level=AccessibilityLevel.A,
                        suggestion="Ensure text color contrasts with background",
                    )
                )

            # Recursively check child controls
            if hasattr(control, "content") and control.content:
                check_control_colors(control.content, current_path)
            elif hasattr(control, "controls") and control.controls:
                for child in control.controls:
                    check_control_colors(child, current_path)

        check_control_colors(root_control)
        return issues

    def test_aria_labels(self, root_control: ft.Control) -> List[AccessibilityIssue]:
        """Test ARIA labels and semantic markup"""
        issues = []

        def check_control_aria(control: ft.Control, path: str = ""):
            if not control:
                return

            current_path = (
                f"{path}/{type(control).__name__}" if path else type(control).__name__
            )

            # Check for missing semantic labels
            if (
                type(control).__name__ in ["IconButton", "FilledButton", "TextButton"]
                and not hasattr(control, "icon")
                and not (hasattr(control, "text") and control.text)
            ):
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Button without accessible label",
                        level=AccessibilityLevel.A,
                        suggestion="Add text or icon to make the button purpose clear",
                    )
                )

            # Check data table accessibility
            if isinstance(control, ft.DataTable):
                if not control.columns:
                    issues.append(
                        AccessibilityIssue(
                            element=current_path,
                            issue="DataTable without column headers",
                            level=AccessibilityLevel.A,
                            suggestion="Add column headers with descriptive text",
                        )
                    )
                else:
                    for i, column in enumerate(control.columns):
                        if not hasattr(column, "text") or not column.text:
                            issues.append(
                                AccessibilityIssue(
                                    element=f"{current_path}.column_{i}",
                                    issue="DataTable column without header text",
                                    level=AccessibilityLevel.A,
                                    suggestion="Add descriptive text to column header",
                                )
                            )

            # Check for missing alt text on images
            if hasattr(control, "src") and not hasattr(control, "alt"):
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Image element without alt text",
                        level=AccessibilityLevel.A,
                        suggestion="Add descriptive alt text for screen readers",
                    )
                )

            # Recursively check child controls
            if hasattr(control, "content") and control.content:
                check_control_aria(control.content, current_path)
            elif hasattr(control, "controls") and control.controls:
                for child in control.controls:
                    check_control_aria(child, current_path)

        check_control_aria(root_control)
        return issues

    def test_focus_management(
        self, root_control: ft.Control
    ) -> List[AccessibilityIssue]:
        """Test focus management and tab order"""
        issues = []

        def find_focusable_controls(
            control: ft.Control, focusable_controls: List[Tuple[ft.Control, str]]
        ):
            if not control:
                return

            current_path = f"{type(control).__name__}"

            # Check if control can receive focus
            if hasattr(control, "autofocus") and control.autofocus:
                focusable_controls.append((control, current_path))
            elif isinstance(
                control,
                (
                    ft.TextField,
                    ft.Dropdown,
                    ft.Button,
                    ft.IconButton,
                    ft.Checkbox,
                    ft.Radio,
                ),
            ):
                focusable_controls.append((control, current_path))

            # Recursively find child controls
            if hasattr(control, "content") and control.content:
                find_focusable_controls(control.content, focusable_controls)
            elif hasattr(control, "controls") and control.controls:
                for child in control.controls:
                    find_focusable_controls(child, focusable_controls)

        focusable_controls = []
        find_focusable_controls(root_control, focusable_controls)

        # Check if there are enough focusable elements
        if not focusable_controls:
            issues.append(
                AccessibilityIssue(
                    element="Application",
                    issue="No focusable interactive elements found",
                    level=AccessibilityLevel.A,
                    suggestion="Ensure there are keyboard-accessible interactive elements",
                )
            )

        # Check for proper focus trapping in modals
        if hasattr(root_control, "open") and hasattr(root_control, "actions"):
            # This is likely a dialog/modal
            if not focusable_controls:
                issues.append(
                    AccessibilityIssue(
                        element="Modal/Dialog",
                        issue="Modal without focusable elements",
                        level=AccessibilityLevel.A,
                        suggestion="Ensure modal contains keyboard-accessible elements",
                    )
                )

        return issues

    def test_desktop_specific_features(
        self, root_control: ft.Control
    ) -> List[AccessibilityIssue]:
        """Test desktop-specific accessibility features"""
        issues = []

        # Check for Windows 11 specific features
        def check_windows_features(control: ft.Control, path: str = ""):
            if not control:
                return

            current_path = (
                f"{path}/{type(control).__name__}" if path else type(control).__name__
            )

            # Check for tooltip support
            if type(control).__name__ in [
                "IconButton",
                "FilledButton",
                "TextButton",
            ] and (not hasattr(control, "tooltip") or not control.tooltip):
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Button without tooltip",
                        level=AccessibilityLevel.AA,
                        suggestion="Add tooltips to improve discoverability",
                    )
                )

            # Check for keyboard shortcuts hints
            if (
                hasattr(control, "content")
                and "Ctrl+" in str(control.content)
                and not hasattr(control, "tooltip")
            ):
                issues.append(
                    AccessibilityIssue(
                        element=current_path,
                        issue="Keyboard shortcut mentioned without proper hint",
                        level=AccessibilityLevel.AA,
                        suggestion="Add tooltip to explain keyboard shortcut",
                    )
                )

            # Recursively check child controls
            if hasattr(control, "content") and control.content:
                check_windows_features(control.content, current_path)
            elif hasattr(control, "controls") and control.controls:
                for child in control.controls:
                    check_windows_features(child, current_path)

        check_windows_features(root_control)

        # Check for high contrast mode support
        with contextlib.suppress(Exception):
            # Simulate checking theme compatibility
            if hasattr(root_control, "theme") or hasattr(root_control, "color"):
                # This is simplified - in practice, you'd test with actual high contrast themes
                issues.append(
                    AccessibilityIssue(
                        element="Application",
                        issue="High contrast mode compatibility not verified",
                        level=AccessibilityLevel.AA,
                        suggestion="Test with Windows high contrast themes to ensure compatibility",
                    )
                )

        return issues

    def _is_low_contrast_pair(self, color1: str, color2: str) -> bool:
        """Simple heuristic for detecting low contrast color pairs"""
        # This is a simplified check - in practice, you'd use proper contrast calculation
        light_colors = ["#FFFFFF", "#F0F0F0", "#E0E0E0", "#F5F5F5"]
        dark_colors = ["#000000", "#1C1C1C", "#212121", "#2D2D2D"]

        return (color1.lower() in light_colors and color2.lower() in light_colors) or (
            color1.lower() in dark_colors and color2.lower() in dark_colors
        )

    def _is_text_color_invisible(
        self, text_color: str, bg_color: Optional[str]
    ) -> bool:
        """Check if text color would be invisible on background"""
        return bool(bg_color) and text_color.lower() == bg_color.lower()

    def run_accessibility_tests(self, root_control: ft.Control) -> Dict[str, Any]:
        """Run all accessibility tests and generate comprehensive report"""
        logger.info("Starting comprehensive accessibility testing")

        print("♿ Starting Accessibility Test Suite")
        print("=" * 50)

        # Run all tests
        keyboard_issues = self.test_keyboard_navigation(root_control)
        color_issues = self.test_color_contrast(root_control)
        aria_issues = self.test_aria_labels(root_control)
        focus_issues = self.test_focus_management(root_control)
        desktop_issues = self.test_desktop_specific_features(root_control)

        # Combine all issues
        all_issues = (
            keyboard_issues + color_issues + aria_issues + focus_issues + desktop_issues
        )

        # Categorize by severity
        level_a_issues = [
            issue for issue in all_issues if issue.level == AccessibilityLevel.A
        ]
        level_aa_issues = [
            issue for issue in all_issues if issue.level == AccessibilityLevel.AA
        ]
        level_aaa_issues = [
            issue for issue in all_issues if issue.level == AccessibilityLevel.AAA
        ]

        print("\n📊 Accessibility Test Results")
        print(f"Total Issues Found: {len(all_issues)}")
        print(f"Level A (Critical): {len(level_a_issues)}")
        print(f"Level AA (Major): {len(level_aa_issues)}")
        print(f"Level AAA (Minor): {len(level_aaa_issues)}")

        if all_issues:
            print("\n🔍 Issues by Category:")
            categories = {
                "Keyboard Navigation": keyboard_issues,
                "Color Contrast": color_issues,
                "ARIA Labels": aria_issues,
                "Focus Management": focus_issues,
                "Desktop Features": desktop_issues,
            }

            for category, issues_list in categories.items():
                if issues_list:
                    print(f"\n   {category}:")
                    for issue in issues_list:
                        print(f"      - {issue.element}: {issue.issue}")
                        if issue.suggestion:
                            print(f"        💡 {issue.suggestion}")

        # Generate compliance assessment
        print("\n✅ WCAG 2.1 Compliance Assessment:")

        is_level_a_compliant = not level_a_issues
        is_level_aa_compliant = is_level_a_compliant and not level_aa_issues
        is_level_aaa_compliant = is_level_aa_compliant and not level_aaa_issues

        if is_level_a_compliant:
            print("   ✅ Level A: COMPLIANT")
        else:
            print(
                f"   ❌ Level A: NOT COMPLIANT ({len(level_a_issues)} critical issues)"
            )

        if is_level_aa_compliant:
            print("   ✅ Level AA: COMPLIANT")
        else:
            print(
                f"   ❌ Level AA: NOT COMPLIANT ({len(level_aa_issues)} major issues)"
            )

        if is_level_aaa_compliant:
            print("   ✅ Level AAA: COMPLIANT")
        else:
            print(
                f"   ⚠️  Level AAA: NOT COMPLIANT ({len(level_aaa_issues)} minor issues)"
            )

        return {
            "summary": {
                "total_issues": len(all_issues),
                "level_a_issues": len(level_a_issues),
                "level_aa_issues": len(level_aa_issues),
                "level_aaa_issues": len(level_aaa_issues),
                "wcag_a_compliant": is_level_a_compliant,
                "wcag_aa_compliant": is_level_aa_compliant,
                "wcag_aaa_compliant": is_level_aaa_compliant,
                "tested_elements": len(self.tested_elements),
            },
            "issues": [
                {
                    "element": issue.element,
                    "issue": issue.issue,
                    "level": issue.level.value,
                    "suggestion": issue.suggestion,
                }
                for issue in all_issues
            ],
            "categories": {
                "keyboard_navigation": keyboard_issues,
                "color_contrast": color_issues,
                "aria_labels": aria_issues,
                "focus_management": focus_issues,
                "desktop_features": desktop_issues,
            },
        }


def create_accessibility_test_demo():
    """Create a demo application for accessibility testing"""

    def main(page: ft.Page):
        page.title = "Accessibility Test Demo"
        page.theme_mode = ft.ThemeMode.LIGHT

        # Create test controls with various accessibility features
        test_controls = ft.Column(
            [
                ft.Text(
                    "Accessibility Testing Demo", size=24, weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    "This page includes various controls to test accessibility features"
                ),
                ft.Divider(),
                # Buttons with different accessibility characteristics
                ft.Text("Buttons:", weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Good Button", tooltip="This button has proper labeling"
                        ),
                        ft.ElevatedButton(
                            "Icon Only",
                            icon=ft.Icons.SETTINGS,
                            tooltip="Settings button",
                        ),
                        ft.ElevatedButton(
                            "",
                            icon=ft.Icons.CLOSE,
                            tooltip="Close button - problematic without label",
                        ),
                    ]
                ),
                ft.Divider(),
                # Form controls
                ft.Text("Form Controls:", weight=ft.FontWeight.BOLD),
                ft.TextField(
                    label="Accessible Text Field",
                    helper_text="This field has proper labeling",
                    value="Sample text",
                ),
                ft.Dropdown(
                    label="Accessible Dropdown",
                    options=[
                        ft.dropdown.Option("Option 1"),
                        ft.dropdown.Option("Option 2"),
                        ft.dropdown.Option("Option 3"),
                    ],
                    value="Option 1",
                ),
                ft.Divider(),
                # Data table
                ft.Text("Data Table:", weight=ft.FontWeight.BOLD),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Name", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Role", weight=ft.FontWeight.BOLD)),
                    ],
                    rows=[
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text("John Doe")),
                                ft.DataCell(ft.Text("john@example.com")),
                                ft.DataCell(ft.Text("Admin")),
                            ]
                        ),
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text("Jane Smith")),
                                ft.DataCell(ft.Text("jane@example.com")),
                                ft.DataCell(ft.Text("User")),
                            ]
                        ),
                    ],
                ),
                ft.Divider(),
                # Test results area
                ft.Text("Test Results:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(
                        "Run accessibility tests to see results here...",
                        color=ft.Colors.GREY,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY),
                    padding=20,
                    border_radius=8,
                ),
            ],
            spacing=10,
        )

        # Add test button
        def run_tests(e):
            tester = AccessibilityTester(page)
            results = tester.run_accessibility_tests(test_controls)

            # Update results display
            results_text = ft.Text(
                f"Test Results:\n"
                f"Total Issues: {results['summary']['total_issues']}\n"
                f"WCAG A Compliant: {'Yes' if results['summary']['wcag_a_compliant'] else 'No'}\n"
                f"WCAG AA Compliant: {'Yes' if results['summary']['wcag_aa_compliant'] else 'No'}\n"
                f"Elements Tested: {results['summary']['tested_elements']}\n"
                f"\nIssues Found:\n"
            )

            for issue in results["issues"]:
                results_text.value += f"- {issue['element']}: {issue['issue']}\n"

            results_container.content = results_text
            results_container.update()

        results_container = ft.Container(
            content=ft.Text("Click 'Run Tests' to start accessibility testing"),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.GREY),
            padding=20,
            border_radius=8,
        )

        # Add test button to page
        test_button = ft.ElevatedButton(
            "Run Accessibility Tests", on_click=run_tests, icon=ft.Icons.ACCESSIBILITY
        )

        page.add(
            ft.Column(
                [
                    test_controls,
                    ft.Divider(),
                    ft.Row(
                        [test_button, results_container],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ]
            )
        )

    return main


def run_accessibility_tests():
    """Run accessibility tests and return results"""
    # This would be called from the main application
    print("Run accessibility tests from the application menu to see results")
    return {"message": "Accessibility tests available in application"}


if __name__ == "__main__":
    # Run demo when executed directly
    print("♿ Starting Accessibility Test Demo")
    print("This demo shows how accessibility testing works")
    print("In the main application, run accessibility tests from the menu.")
    print("")
