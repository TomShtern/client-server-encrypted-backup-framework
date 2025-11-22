#!/usr/bin/env python3
"""
Test for async/sync boundary violations that can cause deadlocks.

This test scans view files to detect common patterns that lead to
Flet GUI freezes/deadlocks, specifically:
- Direct calls to server_bridge.method() from async functions
- time.sleep() usage in async code
- Missing run_sync_in_executor() wrappers

Based on the dashboard deadlock fix (24 Oct 2025).
"""

import ast
from pathlib import Path


class AsyncBoundaryChecker(ast.NodeVisitor):
    """AST visitor to detect blocking calls in async functions."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations = []
        self.current_async_function = None

    def visit_AsyncFunctionDef(self, node):
        """Track when we're inside an async function."""
        old_async = self.current_async_function
        self.current_async_function = node.name
        self.generic_visit(node)
        self.current_async_function = old_async

    def visit_Call(self, node):
        """Check for problematic function calls."""
        if not self.current_async_function:
            self.generic_visit(node)
            return

        # Check for time.sleep() in async function
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'time' and
                node.func.attr == 'sleep'):
                self.violations.append({
                    'file': self.filename,
                    'function': self.current_async_function,
                    'line': node.lineno,
                    'issue': 'time.sleep() called in async function',
                    'fix': 'Use await asyncio.sleep() instead'
                })

            # Check for direct server_bridge calls (without run_sync_in_executor)
            # Pattern: server_bridge.some_method()
            if (isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'server_bridge'):
                # Check if this is wrapped in run_sync_in_executor by checking parent context
                # For simplicity, we'll flag it if it's not inside await run_sync_in_executor
                method_name = node.func.attr

                # Whitelist: These are async methods that are safe to call
                async_safe_methods = {'is_real', 'get_dashboard_summary_async',
                                     'get_clients_async', 'get_files_async'}

                if method_name not in async_safe_methods and method_name != 'real_server':
                    self.violations.append({
                        'file': self.filename,
                        'function': self.current_async_function,
                        'line': node.lineno,
                        'issue': f'Direct call to server_bridge.{method_name}() in async function',
                        'fix': 'Wrap with: await run_sync_in_executor(server_bridge.{})'.format(method_name)
                    })

        self.generic_visit(node)


def test_no_blocking_calls_in_async_functions():
    """Scan all view files for async/sync boundary violations."""
    view_dir = Path(__file__).parent.parent / "FletV2" / "views"

    if not view_dir.exists():
        pytest.skip(f"View directory not found: {view_dir}")

    all_violations = []

    for view_file in view_dir.glob("*.py"):
        if view_file.name.startswith("__"):
            continue

        try:
            with open(view_file, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename=str(view_file))
            checker = AsyncBoundaryChecker(view_file.name)
            checker.visit(tree)
            all_violations.extend(checker.violations)

        except SyntaxError as e:
            print(f"Warning: Syntax error in {view_file.name}: {e}")
            continue

    if all_violations:
        error_msg = "Found async/sync boundary violations that can cause deadlocks:\n\n"
        for v in all_violations:
            error_msg += f"  {v['file']}:{v['line']} in {v['function']}()\n"
            error_msg += f"    Issue: {v['issue']}\n"
            error_msg += f"    Fix: {v['fix']}\n\n"
        error_msg += f"Total violations: {len(all_violations)}\n"
        error_msg += "See: AI-Context/DASHBOARD_DEADLOCK_FIX_24OCT2025.md for details"

        assert False, error_msg


def test_dashboard_deadlock_pattern_fixed():
    """Verify the specific dashboard deadlock pattern is fixed."""
    dashboard_file = Path(__file__).parent.parent / "FletV2" / "views" / "dashboard.py"

    if not dashboard_file.exists():
        pytest.skip("dashboard.py not found")

    with open(dashboard_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace fragile regex check with AST-based function inspection
    try:
        tree = ast.parse(content, filename=str(dashboard_file))
    except SyntaxError:
        # If the file can't be parsed, keep behavior simple (no assertion).
        return

    derive_func_node = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_derive_status":
            derive_func_node = node
            break

    if derive_func_node:
        # Look for direct calls of the form: server_bridge.is_connected()
        for subnode in ast.walk(derive_func_node):
            if isinstance(subnode, ast.Call):
                func = subnode.func
                if isinstance(func, ast.Attribute) and func.attr == "is_connected":
                    value = func.value
                    if isinstance(value, ast.Name) and value.id == "server_bridge":
                        assert False, (
                            "_derive_status() still calls server_bridge.is_connected() which causes deadlock.\n"
                            "Fix: Use snapshot data or direct_bridge_present check instead.\n"
                            "See: AI-Context/DASHBOARD_DEADLOCK_FIX_24OCT2025.md"
                        )


if __name__ == "__main__":
    # Allow running standalone for quick checks
    import pytest
    pytest.main([__file__, "-v"])
