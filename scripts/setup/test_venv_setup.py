#!/usr/bin/env python3
"""
Test script to verify virtual environment setup is working correctly
"""

import os
import sys
from pathlib import Path

# Import UTF-8 solution first
try:
    import Shared.filesystem.utf8_solution

    _ = Shared.filesystem.utf8_solution
    print("[INFO] UTF-8 solution imported successfully")
except ImportError:
    print("[WARNING] UTF-8 solution not available")


def test_environment():
    print("Virtual Environment Setup Test")
    print("=" * 50)

    # Check current Python executable
    current_python = Path(sys.executable)
    print(f"Current Python: {current_python}")

    # Check if we're in flet_venv
    if "flet_venv" in str(current_python):
        print("CORRECT: Running from flet_venv")
    else:
        print("INCORRECT: Not running from flet_venv")
        print("   Expected path should contain 'flet_venv'")

    # Check virtual environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV", "Not set")
    print(f"VIRTUAL_ENV: {virtual_env}")

    # Test key imports
    print("\nTesting Key Package Imports:")

    packages_to_test = [
        "flet",
        "flask",
        "requests",
        "psutil",
        "matplotlib",
        "pydantic",
        "aiofiles",
    ]

    for package in packages_to_test:
        try:
            __import__(package)
            print(f"  OK: {package}")
        except ImportError as e:
            print(f"  FAIL: {package} - {e}")

    # Check if this is the expected environment
    expected_path = Path(__file__).parent / "flet_venv" / "Scripts" / "python.exe"
    if current_python.resolve() == expected_path.resolve():
        print("\nPERFECT: Using correct unified environment!")
        print(f"   Path: {current_python}")
        return True
    else:
        print("\nWARNING: Environment mismatch")
        print(f"   Current:  {current_python}")
        print(f"   Expected: {expected_path}")
        return False


if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)
