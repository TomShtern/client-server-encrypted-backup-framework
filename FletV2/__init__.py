#!/usr/bin/env python3
"""
FletV2 Package Init
Main package init file for FletV2.
"""

import os
import sys

# Add the package directory to the Python path if needed
package_dir = os.path.dirname(__file__)
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

# Import main application components
# Import views package
# Import utils package
from . import utils, views  # noqa: E402
from .main import FletV2App  # noqa: E402
from .theme import (  # noqa: E402
    create_modern_card,
    get_design_tokens,
    setup_sophisticated_theme,
    themed_button,
    toggle_theme_mode,
)

# Define what should be imported with "from FletV2 import *"
__all__ = [
    "FletV2App",
    "create_modern_card",
    "get_design_tokens",
    "setup_sophisticated_theme",
    "themed_button",
    "toggle_theme_mode",
    "utils",
    "views",
]
