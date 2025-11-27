#!/usr/bin/env python3
"""
Quick targeted error finder - focuses on specific runtime issues
"""

import importlib.util
import os
from typing import Any, cast

# Setup standardized import paths
from Shared.path_utils import setup_imports

setup_imports()


def test_server_gui_import() -> bool:
    """Test ServerGUI imports"""
    print("Testing ServerGUI imports...")
    try:
        print("✓ All ServerGUI imports successful")
        return True
    except Exception as e:
        print(f"✗ ServerGUI import error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_other_files() -> list[str]:
    """Test other Python files for import issues"""
    files_to_test = [
        "config_manager.py",
        "comprehensive_test_suite.py",
        "quick_validation.py",
    ]

    results: list[str] = []
    for file in files_to_test:
        if os.path.exists(file):
            print(f"Testing {file}...")
            try:
                spec = importlib.util.spec_from_file_location("test_module", file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    print(f"✓ {file} imports successfully")
                    results.append(f"✓ {file}")
                else:
                    print(f"? Could not create module spec for {file}")
                    results.append(f"? {file} spec creation failed")
            except Exception as e:
                print(f"✗ {file} error: {e}")
                results.append(f"✗ {file}: {e}")
        else:
            print(f"? {file} not found")
            results.append(f"? {file} not found")

    return results


def test_gui_methods(gui: Any) -> None:
    """Test basic GUI methods"""
    cast(Any, gui).update_server_status(True, "127.0.0.1", 1256)
    print("✓ update_server_status works")
    cast(Any, gui).update_client_stats(
        {"connected": 5, "total": 10, "active_transfers": 2}
    )
    print("✓ update_client_stats works")
    cast(Any, gui).update_transfer_stats({"bytes_transferred": 1024})
    print("✓ update_transfer_stats works")
    toast = getattr(gui, "toast_system", None)
    if toast is not None:
        cast(Any, toast).show_toast("test error", "error")
        cast(Any, toast).show_toast("test success", "success")
        cast(Any, toast).show_toast("test info", "info")


def test_minimal_functionality() -> bool:
    """Test minimal ServerGUI functionality"""
    print("\nTesting minimal ServerGUI functionality...")
    try:
        from python_server.server_gui import ServerGUI  # type: ignore

        gui: Any = ServerGUI()
        print("✓ ServerGUI instance created")
        # Test basic methods
        test_gui_methods(gui)
        return True
    except ImportError:
        print("✗ Could not import ServerGUI. Skipping functionality tests.")
        return False
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_syntax_errors() -> list[str]:
    """Check for syntax errors in Python files"""
    print("\nChecking Python files for syntax errors...")
    import py_compile

    python_files = [
        "python_server/server_gui/ServerGUI.py",
        "config_manager.py",
        "comprehensive_test_suite.py",
        "comprehensive_test_gui.py",
        "demo_server_gui.py",
        "find_gui_errors.py",
        "validate_server_gui.py",
        "test_server_gui.py",
    ]

    results: list[str] = []
    for file in python_files:
        if os.path.exists(file):
            try:
                py_compile.compile(file, doraise=True)
                print(f"✓ {file} - No syntax errors")
                results.append(f"✓ {file}")
            except py_compile.PyCompileError as e:
                print(f"✗ {file} - Syntax error: {e}")
                results.append(f"✗ {file}: {e}")
        else:
            print(f"? {file} not found")
            results.append(f"? {file} not found")

    return results


def print_results_list(title: str, results: list[str]) -> None:
    """Print a formatted list of results"""
    print(f"\n{title}:")
    for result in results:
        print(f"  {result}")


def main() -> None:
    print("🎯 TARGETED ERROR DETECTION")
    print("=" * 50)

    # Test 1: Check syntax errors
    syntax_results = check_syntax_errors()

    # Test 2: Test ServerGUI import
    import_success = test_server_gui_import()

    # Test 3: Test other files
    other_results = test_other_files()

    # Test 4: Test basic functionality (only if import successful)
    func_success = test_minimal_functionality() if import_success else False

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    print_results_list("Syntax check results", syntax_results)

    print(f"\nServerGUI import: {'✓ SUCCESS' if import_success else '✗ FAILED'}")

    print_results_list("Other files", other_results)

    print(f"\nFunctionality test: {'✓ SUCCESS' if func_success else '✗ FAILED'}")

    # Count issues
    syntax_errors = len([r for r in syntax_results if r.startswith("✗")])
    other_errors = len([r for r in other_results if r.startswith("✗")])

    total_errors = (
        syntax_errors
        + other_errors
        + (0 if import_success else 1)
        + (0 if func_success else 1)
    )

    if total_errors == 0:
        print("\n🎉 NO ERRORS FOUND! All tests passed.")
    else:
        print(f"\n❌ FOUND {total_errors} ERRORS that need to be fixed.")


if __name__ == "__main__":
    main()
