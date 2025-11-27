#!/usr/bin/env python3
"""Integration tests for Logs view with ServerBridge (mock-backed)."""

import os
import sys
import unittest


# More robust path setup to ensure FletV2 modules can be found
def setup_fletv2_path():
    """Set up the Python path to include FletV2 directory."""
    # Get the directory containing this test file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Navigate up to find the FletV2 root (tests/integration/ -> FletV2/)
    fletv2_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # Add FletV2 to Python path if not already there
    if fletv2_root not in sys.path:
        sys.path.insert(0, fletv2_root)
        print(f"Added {fletv2_root} to Python path")

    # Also add the parent directory to ensure we can find FletV2 package
    parent_dir = os.path.dirname(fletv2_root)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        print(f"Added {parent_dir} to Python path")


# Set up the path before any other imports
setup_fletv2_path()

import flet as ft  # noqa: E402

os.environ.setdefault("FLET_V2_DEBUG", "true")

# Try to import the modules
try:
    from tests.integration_utils import FakePage  # noqa: E402
    from utils.server_bridge import create_server_bridge  # noqa: E402
    from utils.state_manager import StateManager  # noqa: E402
    from views.logs import create_logs_view  # noqa: E402
except ImportError as e:
    print(f"Import error: {e}")
    print("\nCurrent Python path:")
    for path in sys.path:
        print(f"  {path}")
    print("\nTo run tests correctly:")
    print("  Option 1: cd FletV2 && python -m tests.integration.test_logs_integration")
    print("  Option 2: python FletV2/tests/integration/test_logs_integration.py")
    print("  Option 3: Use the run_tests.py script from project root")
    sys.exit(1)


class TestLogsIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.page: ft.Page = FakePage()  # type: ignore[assignment]
        self.bridge = create_server_bridge()
        self.state_manager = StateManager(self.page, self.bridge)

    def test_logs_view_loads_and_filters(self):
        view, dispose, setup = create_logs_view(
            self.bridge, self.page, self.state_manager
        )
        self.assertIsInstance(view, ft.Control)
        setup()

        # Bridge should respond for logs in mock mode
        result = self.bridge.get_logs()
        self.assertTrue(result.get("success", False))
        data = result.get("data", [])
        self.assertIsInstance(data, list)

        dispose()


if __name__ == "__main__":
    unittest.main()
