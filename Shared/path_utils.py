"""
Shim module for backward compatibility.
Redirects imports from Shared.path_utils to Shared.filesystem.path_utils.
"""
from .filesystem.path_utils import *
