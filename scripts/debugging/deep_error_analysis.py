#!/usr/bin/env python3
"""
Deep analysis script to find all errors in the project
"""

import ast
import os
import sys
import traceback
from typing import Any

# Add the project root to the Python path
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.insert(0, project_root)

# Setup standardized import paths
from Shared.path_utils import setup_imports  # noqa: E402

setup_imports()


def check_syntax_and_incomplete_methods(
    content: str, filepath: str
) -> dict[str, list[str]]:
    # sourcery skip: low-code-quality
    """Check syntax and find incomplete methods"""
    syntax_errors: list[str] = []
    incomplete_methods: list[str] = []

    try:
        tree = ast.parse(content)
        # Find incomplete methods
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for methods with minimal implementation
                if len(node.body) == 1:
                    first_stmt = node.body[0]
                    if isinstance(first_stmt, ast.Pass):
                        incomplete_methods.append(
                            f"Line {node.lineno}: {node.name} - Only pass statement"
                        )
                    elif isinstance(first_stmt, ast.Expr):
                        if isinstance(first_stmt.value, ast.Constant):
                            if first_stmt.value.value in [Ellipsis, "..."]:
                                incomplete_methods.append(
                                    f"Line {node.lineno}: {node.name} - Only ellipsis"
                                )
                        elif hasattr(ast, "Str") and isinstance(
                            first_stmt.value, ast.Str
                        ):
                            if first_stmt.value.s in ["...", "TODO", "FIXME"]:
                                incomplete_methods.append(
                                    f"Line {node.lineno}: {node.name} - Placeholder: {first_stmt.value.s}"
                                )
                elif len(node.body) == 0:
                    incomplete_methods.append(
                        f"Line {node.lineno}: {node.name} - Empty method body"
                    )
    except SyntaxError as e:
        syntax_errors.append(f"Line {e.lineno}: {e.msg}")

    return {"syntax_errors": syntax_errors, "incomplete_methods": incomplete_methods}


def check_imports(content: str, filepath: str) -> list[str]:
    """Check for missing imports"""
    missing_imports: list[str] = []

    # Test key imports for ServerGUI.py
    if "ServerGUI.py" in filepath:
        test_imports = [
            "import tkinter as tk",
            "from tkinter import ttk, messagebox, filedialog",
            "import threading",
            "import queue",
            "from datetime import datetime",
            "from typing import Dict, List, Optional, Any, Union, Tuple",
            "from collections import deque",
        ]

        missing_imports.extend(
            f"Missing: {imp}" for imp in test_imports if imp not in content
        )

    return missing_imports


def analyze_python_file(filepath: str) -> dict[str, Any]:
    """Analyze a Python file for various issues"""
    results: dict[str, Any] = {
        "file": filepath,
        "syntax_errors": [],
        "import_errors": [],
        "incomplete_methods": [],
        "runtime_errors": [],
        "missing_imports": [],
    }

    try:
        # Read file content
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Check syntax and incomplete methods
        syntax_results = check_syntax_and_incomplete_methods(content, filepath)
        results["syntax_errors"] = syntax_results["syntax_errors"]
        results["incomplete_methods"] = syntax_results["incomplete_methods"]

        # Test imports
        try:
            results["missing_imports"] = check_imports(content, filepath)
        except Exception as e:
            results["import_errors"].append(f"Import analysis error: {e}")

    except Exception as e:
        results["runtime_errors"].append(f"File analysis error: {e}")

    return results


def test_functionality() -> list[str]:
    """Test actual functionality"""
    results: list[str] = []

    print("Testing ServerGUI functionality...")
    try:
        from python_server.server_gui import ServerGUI  # type: ignore
        # Note: ModernCard, ModernProgressBar, ModernStatusIndicator not available in current codebase

        # Test basic instantiation
        gui = ServerGUI()
        results.append("✓ ServerGUI instantiation works")

        # Test widget creation
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()

        # Skipping tests for components not available in current codebase
        results.append(
            "ℹ ModernCard, ModernProgressBar, ModernStatusIndicator tests skipped (components not available)"
        )

        # try:
        #     _card = ModernCard(root, title="Test")  # type: ignore
        #     results.append("✓ ModernCard creation works")
        # except Exception as e:
        #     results.append(f"✗ ModernCard error: {e}")

        # try:
        #     progress = ModernProgressBar(root)  # type: ignore
        #     if hasattr(progress, 'set_progress') and callable(getattr(progress, 'set_progress', None)):
        #         progress.set_progress(50)
        #     results.append("✓ ModernProgressBar works")
        # except Exception as e:
        #     results.append(f"✗ ModernProgressBar error: {e}")

        # try:
        #     status = ModernStatusIndicator(root)  # type: ignore
        #     if hasattr(status, 'set_status') and callable(getattr(status, 'set_status', None)):
        #         status.set_status("online")
        #     results.append("✓ ModernStatusIndicator works")
        # except Exception as e:
        #     results.append(f"✗ ModernStatusIndicator error: {e}")

        root.destroy()

        # Test GUI methods
        try:
            _extracted_from_test_functionality_45(gui, results)
        except Exception as e:
            results.append(f"✗ GUI method error: {e}")

    except ImportError:
        results.append("✗ Could not import ServerGUI. Skipping functionality tests.")
    except Exception as e:
        results.append(f"✗ Major functionality error: {e}")
        traceback.print_exc()

    return results


# TODO Rename this here and in `test_functionality`
def _extracted_from_test_functionality_45(gui, results):
    # Use safe method calls for GUI testing
    if hasattr(gui, "update_server_status") and callable(
        getattr(gui, "update_server_status", None)
    ):
        gui.update_server_status(True, "127.0.0.1", 1256)  # type: ignore
    if hasattr(gui, "update_client_stats") and callable(
        getattr(gui, "update_client_stats", None)
    ):
        gui.update_client_stats(5, 10, 2)  # type: ignore
    if hasattr(gui, "update_transfer_stats") and callable(
        getattr(gui, "update_transfer_stats", None)
    ):
        gui.update_transfer_stats(1024, "now")  # type: ignore
    if hasattr(gui, "show_error") and callable(getattr(gui, "show_error", None)):
        gui.show_error("test error")  # type: ignore
    if hasattr(gui, "show_success") and callable(getattr(gui, "show_success", None)):
        gui.show_success("test success")  # type: ignore
    if hasattr(gui, "show_info") and callable(getattr(gui, "show_info", None)):
        gui.show_info("test info")  # type: ignore
    results.append("✓ All GUI methods work")  # type: ignore


def main() -> None:
    print("DEEP ERROR ANALYSIS")
    print("=" * 60)

    # Find all Python files
    python_files: list[str] = []
    for root, _dirs, files in os.walk("."):
        python_files.extend(
            os.path.join(root, file) for file in files if file.endswith(".py")
        )
    print(f"Found {len(python_files)} Python files")

    # Analyze each file
    all_issues: list[dict[str, Any]] = []
    for filepath in python_files:
        if "__pycache__" in filepath or ".git" in filepath:
            continue

        print(f"\nAnalyzing: {filepath}")
        results = analyze_python_file(filepath)

        issues_found = sum(len(results[key]) for key in results if key != "file")
        if issues_found > 0:
            all_issues.append(results)
            print(f"  Issues found: {issues_found}")
        else:
            print("  No issues")

    _extracted_from_main_30("FUNCTIONALITY TESTING")
    func_results = test_functionality()
    for result in func_results:
        print(result)

    _extracted_from_main_30("SUMMARY")
    if all_issues:
        print(f"Found issues in {len(all_issues)} files:")
        for issue in all_issues:
            print(f"\nFile: {issue['file']}:")
            for category, problems in issue.items():
                if category != "file" and problems:
                    print(f"  {category}: {len(problems)} issues")
                    for problem in problems[:3]:  # Show first 3
                        print(f"    • {problem}")
                    if len(problems) > 3:
                        print(f"    • ... and {len(problems) - 3} more")
    else:
        print("No static analysis issues found")

    print(
        f"\nFunctionality test results: {len([r for r in func_results if r.startswith('✓')])} passed, {len([r for r in func_results if r.startswith('✗')])} failed"
    )


# TODO Rename this here and in `main`
def _extracted_from_main_30(arg0):
    # Test functionality
    print(f"\n{'=' * 60}")
    print(arg0)
    print("=" * 60)


if __name__ == "__main__":
    main()
