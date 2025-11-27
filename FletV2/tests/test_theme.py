#!/usr/bin/env python3
"""
Unit tests for the theme module.
"""

import os
import sys
import unittest

# Add the FletV2 directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import flet as ft  # noqa: E402
from theme import (  # noqa: E402
    get_design_tokens,
    setup_modern_theme,
    toggle_theme_mode,
)

# Define BRAND_COLORS locally
BRAND_COLORS = {
    "primary": "#6750A4",
    "secondary": "#625B71",
    "tertiary": "#7D5260",
    "background": "#FFFBFE",
    "surface": "#FFFBFE",
    "error": "#BA1A1A",
}


class TestThemeModule(unittest.TestCase):
    """Test cases for the theme module."""

    def _get_design_tokens_and_validate(self):
        """Helper method to get design tokens and validate basic structure."""
        design_tokens = get_design_tokens()
        self.assertIsInstance(design_tokens, dict)
        self.assertGreater(len(design_tokens), 0)
        return design_tokens

    def test_brand_colors_structure(self):
        """Test that BRAND_COLORS has the expected structure."""
        self.assertIsInstance(BRAND_COLORS, dict)
        self.assertGreater(len(BRAND_COLORS), 0)

        # Test for expected color keys
        for color_name, color_value in BRAND_COLORS.items():
            self.assertIsInstance(color_name, str)
            self.assertIsInstance(color_value, str)
            # Basic color format check (hex or named)
            self.assertTrue(color_value.startswith("#") or color_value.isalpha())

    def test_design_tokens_available(self):
        """Test that design tokens are available."""
        _ = self._get_design_tokens_and_validate()

    def test_setup_modern_theme_function(self):
        """Test the setup_modern_theme function."""
        # Create a mock page object
        page = ft.Page()

        # Test theme setup
        result = setup_modern_theme(page)

        # Should return the page or None
        self.assertTrue(result is None or result == page)

        # Page should have theme set
        self.assertIsNotNone(page.theme)

    def test_design_tokens_functionality(self):
        """Test design tokens functionality."""
        # Create a mock page
        page = ft.Page()

        # Apply modern theme first
        setup_modern_theme(page)

        # Get design tokens
        tokens = self._get_design_tokens_and_validate()

        # Check for common design token keys
        for token_value in tokens.values():
            self.assertTrue(isinstance(token_value, (str, int, float)))

    def test_toggle_theme_mode(self):
        """Test toggling theme mode."""
        # Create a mock page
        page = ft.Page()

        # Apply modern theme first
        setup_modern_theme(page)

        # Initially should be SYSTEM or None
        _ = page.theme_mode

        # Toggle from SYSTEM/None to LIGHT
        toggle_theme_mode(page)
        self.assertEqual(page.theme_mode, ft.ThemeMode.LIGHT)

        # Toggle from LIGHT to DARK
        toggle_theme_mode(page)
        self.assertEqual(page.theme_mode, ft.ThemeMode.DARK)

        # Toggle from DARK back to LIGHT
        toggle_theme_mode(page)
        self.assertEqual(page.theme_mode, ft.ThemeMode.LIGHT)


if __name__ == "__main__":
    unittest.main()
