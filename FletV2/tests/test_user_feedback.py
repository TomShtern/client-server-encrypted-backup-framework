#!/usr/bin/env python3
"""
Unit tests for the user feedback module.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock

# Add the FletV2 directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock flet for testing
sys.modules["flet"] = MagicMock()

from utils.user_feedback import (  # noqa: E402
    show_confirmation,
    show_error_message,
    show_info_message,
    show_input,
    show_success_message,
    show_warning_message,
)


class TestUserFeedback(unittest.TestCase):
    """Test cases for the user feedback module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock page
        self.mock_page = Mock()
        self.mock_page.snack_bar = Mock()
        self.mock_page.dialog = Mock()
        self.mock_page.update = Mock()

    def test_show_success_message(self):
        """Test showing a success message."""
        show_success_message(self.mock_page, "Test success message")
        self.mock_page.update.assert_called()

    def test_show_error_message(self):
        """Test showing an error message."""
        show_error_message(self.mock_page, "Test error message")
        self.mock_page.update.assert_called()

    def test_show_warning_message(self):
        """Test showing a warning message."""
        show_warning_message(self.mock_page, "Test warning message")
        self.mock_page.update.assert_called()

    def test_show_info_message(self):
        """Test showing an info message."""
        show_info_message(self.mock_page, "Test info message")
        self.mock_page.update.assert_called()

    def test_show_confirmation_dialog(self):
        """Test showing a confirmation dialog."""
        show_confirmation(self.mock_page, "Test title", "Test content", lambda e: None)
        self.mock_page.update.assert_called()

    def test_show_input_dialog(self):
        """Test showing an input dialog."""
        show_input(
            self.mock_page, "Test title", "Test content", "Test label", lambda x: None
        )
        self.mock_page.update.assert_called()


if __name__ == "__main__":
    unittest.main()
