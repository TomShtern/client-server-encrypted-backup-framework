"""
Shim module for backward compatibility.
Redirects imports from Shared.observability_middleware to Shared.monitoring.observability_middleware.
"""

from .monitoring.observability_middleware import *  # noqa: F403
