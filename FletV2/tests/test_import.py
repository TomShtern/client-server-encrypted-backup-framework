#!/usr/bin/env python3
"""
Test script to verify that utils.debug_setup can be imported from anywhere.
"""

import os
import sys


def setup_path_correctly():
    """Set up the Python path correctly to find FletV2 modules."""
    # Get current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    # Look for FletV2 directory
    fletv2_path = os.path.join(current_dir, "FletV2")
    if os.path.exists(fletv2_path):
        print(f"Found FletV2 directory at: {fletv2_path}")
        if fletv2_path not in sys.path:
            sys.path.insert(0, fletv2_path)
            print(f"Added {fletv2_path} to Python path")
        return True
    else:
        print(f"FletV2 directory not found at: {fletv2_path}")
        return False


def test_import_directly():
    """Test importing utils.debug_setup directly."""
    try:
        from utils.debug_setup import setup_terminal_debugging  # noqa: F401

        print("[PASS] Direct import successful")
        return True
    except ImportError as e:
        print(f"[FAIL] Direct import failed: {e}")
        return False


def test_import_as_module():
    """Test importing FletV2.utils.debug_setup as a module."""
    try:
        import FletV2.utils.debug_setup  # noqa: F401

        print("[PASS] Module import successful")
        return True
    except ImportError as e:
        print(f"[FAIL] Module import failed: {e}")
        return False


def test_import_with_explicit_path():
    """Test importing with explicit path manipulation."""
    try:
        # Try importing the file directly
        fletv2_utils_path = os.path.join(os.getcwd(), "FletV2", "utils")
        if fletv2_utils_path not in sys.path:
            sys.path.insert(0, fletv2_utils_path)

        import debug_setup  # noqa: F401

        print("[PASS] Explicit path import successful")
        return True
    except ImportError as e:
        print(f"[FAIL] Explicit path import failed: {e}")
        return False


def test_import():
    """Test importing utils.debug_setup using different methods."""
    print("Method 1: Direct import")
    success1 = test_import_directly()

    print("\nMethod 2: Module import")
    success2 = test_import_as_module()

    print("\nMethod 3: Explicit path import")
    success3 = test_import_with_explicit_path()

    return success1 or success2 or success3


if __name__ == "__main__":
    print("Testing utils.debug_setup import...")
    print(f"Python path: {sys.path}")

    if success := test_import():
        print("\n[PASS] At least one import method worked!")
        sys.exit(0)
    else:
        print("\n[FAIL] All import methods failed!")
        print("\nTo fix this issue, you have several options:")
        print("1. Run from the FletV2 directory: cd FletV2 && python your_script.py")
        print("2. Use the run_tests.py script: python FletV2/run_tests.py")
        print("3. Set PYTHONPATH: PYTHONPATH=FletV2 python your_script.py")
        sys.exit(1)
