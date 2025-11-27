#!/usr/bin/env python3
"""
Test the fletv2_import_fix module.
"""

import sys

# Now try to import the debug_setup module
try:
    import utils.debug_setup  # noqa: F401

    print("[PASS] Successfully imported utils.debug_setup after fix")
except ImportError as e:
    print(f"[FAIL] Failed to import utils.debug_setup: {e}")
    sys.exit(1)

print("[SUCCESS] Import fix is working correctly!")
