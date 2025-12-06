"""
print("DEBUG: Shared/__init__.py executing", flush=True)
Shared module for the Client-Server Encrypted Backup Framework.

This module contains shared utilities, configuration management,
logging utilities, observability features, and other common functionality
used across the client and server components.
"""

import os
import sys

# Enable global UTF-8 support automatically (replaces all manual UTF-8 setup)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Make commonly used modules easily accessible
from . import crc
from .config import unified_config as config
from .logging import logging_utils
from .monitoring import observability
from .validation import filename_validator

__all__ = ["config", "crc", "filename_validator", "logging_utils", "observability"]
