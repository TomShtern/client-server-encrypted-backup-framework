# config.py
# Server Configuration Constants and Settings
# Extracted from monolithic server.py for better modularity

import logging
import sys
from pathlib import Path

# --- Server Configuration Constants ---
SERVER_VERSION = 3
DEFAULT_PORT = 1256

# --- Protocol Version Compatibility Configuration ---
# Define version compatibility matrix for flexible client-server communication
# This fixes the rigid version checking that prevents client-server communication
MIN_SUPPORTED_CLIENT_VERSION = (
    2  # Minimum client version supported (enable backward compatibility)
)
MAX_SUPPORTED_CLIENT_VERSION = 4  # Maximum client version supported
COMPATIBLE_VERSIONS = [3]  # List of explicitly compatible versions
ALLOW_BACKWARD_COMPATIBILITY = True  # Allow clients with older compatible versions
VERSION_TOLERANCE_ENABLED = True  # Enable flexible version checking
PORT_CONFIG_FILE = "port.info"
# Database name is managed by the unified configuration helper
logger = logging.getLogger(__name__)

try:
    from config import database_config as _unified_database_config
except ImportError:  # pragma: no cover - fallback when config package unavailable
    _unified_database_config = None


def _resolve_database_name() -> str:
    """Resolve the database path using the unified configuration helpers."""

    if _unified_database_config is not None:
        try:
            database_name = _unified_database_config.get_database_path()
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Unified database configuration failed; falling back to legacy path: %s",
                exc,
            )
        else:
            if database_name:
                return database_name
            logger.warning(
                "Unified database configuration returned an empty path; using legacy fallback.",
            )
    else:  # pragma: no cover - executed when config package missing entirely
        logger.warning(
            "Unified database configuration package unavailable; falling back to 'defensive.db'.",
        )

    return "defensive.db"


DATABASE_NAME = _resolve_database_name()
FILE_STORAGE_DIR = "received_files"  # Directory to store received files

# Enhanced Database Configuration
DATABASE_CONNECTION_POOL_ENABLED = (
    True  # Enable connection pooling for better performance
)
DATABASE_CONNECTION_POOL_SIZE = 5  # Number of connections in pool
DATABASE_MIGRATION_ENABLED = True  # Enable automatic migrations on startup
DATABASE_BACKUP_ON_MIGRATION = True  # Create backup before applying migrations
DATABASE_OPTIMIZATION_ENABLED = True  # Enable database optimization features

# Session and timeout configuration
CLIENT_SOCKET_TIMEOUT = 60.0  # Timeout for individual socket operations with a client
CLIENT_SESSION_TIMEOUT = 600  # 10 minutes - Time in seconds before a client session expires due to inactivity
PARTIAL_FILE_TIMEOUT = (
    900  # 15 minutes - Time in seconds before partial file transfer data is cleaned up
)
MAINTENANCE_INTERVAL = 20.0  # How often to run maintenance tasks (seconds)

# Logging Configuration Filenames
SERVER_LOG_FILENAME = "logs/server.log"
BACKUP_LOG_FILENAME = "logs/backup_server.log"
MAX_PAYLOAD_READ_LIMIT = (
    16 * 1024 * 1024
) + 1024  # Max size for a single payload read (16MB chunk + headers)
MAX_ORIGINAL_FILE_SIZE = (
    4 * 1024 * 1024 * 1024
)  # Max original file size (e.g., 4GB) - for sanity checking
MAX_CONCURRENT_CLIENTS = 50  # Max number of concurrent client connections

MAX_CLIENT_NAME_LENGTH = 100  # As per spec (implicit from me.info and general limits)
MAX_FILENAME_FIELD_SIZE = 255  # Size of the filename field in protocol
MAX_ACTUAL_FILENAME_LENGTH = 250  # Practical limit for actual filename within the field
RSA_PUBLIC_KEY_SIZE = (
    160  # Bytes, X.509 format (for 1024-bit RSA - per protocol specification)
)
AES_KEY_SIZE_BYTES = 32  # 256-bit AES

# Compatibility with FletV2 GUI (for when python_server config is imported instead of FletV2 config)
# This ensures that FletV2 GUI can work even when this config module is loaded first
DEBUG_MODE = True  # Default for server debug mode
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_FILE = (
    _PROJECT_ROOT / "FletV2" / "data" / "fletv2_settings.json"
)  # Fallback settings file path aligned with FletV2

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"


def setup_logging():
    """Configure logging for the backup server."""
    import os
    from logging.handlers import RotatingFileHandler

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG for verbose output
        format=LOG_FORMAT,
        handlers=[
            RotatingFileHandler(
                "logs/server.log",
                mode="a",
                maxBytes=10 * 1024 * 1024,  # 10 MB per file
                backupCount=5,  # Keep 5 backup files
            ),
            logging.StreamHandler(sys.stdout),  # Also log to console
        ],
    )
    return logging.getLogger(__name__)


def _read_port_from_file(file_path: str) -> int:
    """Read and validate port number from a configuration file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file is empty, contains non-integer data, or the port is out of range.
    """
    with open(file_path) as f:
        port_str = f.read().strip()
    if not port_str:
        raise ValueError("Port configuration file is empty.")
    try:
        port = int(port_str)
    except ValueError:
        raise ValueError(f"Invalid port number '{port_str}' in configuration file.")
    # Typically, ports 0-1023 are privileged. Users should use >1023.
    if not (1024 <= port <= 65535):
        raise ValueError(
            f"Port number {port} is out of the recommended user range (1024-65535)."
        )
    logging.getLogger(__name__).info(
        f"Successfully read port {port} from configuration file '{file_path}'."
    )
    return port


def read_port_config() -> int:
    """Reads server port from `port.info`, defaults to `DEFAULT_PORT` on error."""
    logger = logging.getLogger(__name__)
    try:
        return _read_port_from_file(PORT_CONFIG_FILE)
    except FileNotFoundError:
        logger.warning(
            f"Port configuration file '{PORT_CONFIG_FILE}' not found. Using default port {DEFAULT_PORT}."
        )
        return DEFAULT_PORT
    except (
        ValueError
    ) as e:  # Catches empty file, non-integer content, and out-of-range errors
        logger.warning(
            f"Invalid port configuration in '{PORT_CONFIG_FILE}': {e}. Using default port {DEFAULT_PORT}."
        )
        return DEFAULT_PORT
    except Exception as e:  # Catch-all for other potential I/O errors
        logger.error(
            f"Unexpected error reading port configuration file '{PORT_CONFIG_FILE}': {e}. Using default port {DEFAULT_PORT}."
        )
        return DEFAULT_PORT


def get_database_path() -> str:
    """Return the active database path, refreshing from the unified helper when possible."""

    if _unified_database_config is not None:
        try:
            if path := _unified_database_config.get_database_path():
                return path
            logger.warning(
                "Unified database configuration returned an empty path during refresh; reusing cached value.",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Failed to refresh database path from unified configuration: %s. Reusing cached value.",
                exc,
            )
    return DATABASE_NAME
