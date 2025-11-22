# GLOBAL UTF-8 AUTO-PATCHER: Automatically enables UTF-8 for ALL subprocess calls
import asyncio
import base64
import contextlib
import functools
import logging
import os
import shutil
import socket
import sqlite3
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Enable global UTF-8 support automatically (replaces all manual UTF-8 setup)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Setup standardized import paths BEFORE importing any other Shared modules
from Shared.filesystem.path_utils import setup_imports

setup_imports()

# Now import ALL Shared modules after path setup - consolidate all imports here
from Shared.logging.logging_utils import create_enhanced_logger, create_log_monitor_info, setup_dual_logging
from Shared.monitoring.observability import get_metrics_collector, get_system_monitor

# Try to import Sentry config - handle gracefully if not available
try:
    from Shared.sentry_config import init_sentry
    sentry_available = True
except ImportError:
    sentry_available = False
    def init_sentry(*args, **kwargs) -> bool:
        return False

# Import singleton manager
# Import crypto components directly from PyCryptodome
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

from .config import (
    SERVER_VERSION,
    DEFAULT_PORT,
    CLIENT_SOCKET_TIMEOUT,
    CLIENT_SESSION_TIMEOUT,
    PARTIAL_FILE_TIMEOUT,
    MAINTENANCE_INTERVAL,
    MAX_PAYLOAD_READ_LIMIT,
    MAX_ORIGINAL_FILE_SIZE,
    MAX_CONCURRENT_CLIENTS,
    MAX_CLIENT_NAME_LENGTH,
    MAX_FILENAME_FIELD_SIZE,
    MAX_ACTUAL_FILENAME_LENGTH,
    RSA_PUBLIC_KEY_SIZE,
    AES_KEY_SIZE_BYTES,
    FILE_STORAGE_DIR,
    SETTINGS_FILE
)

# Import database module
from .database import DatabaseManager

# Import custom exceptions
from .exceptions import ProtocolError, ServerError

# Import network server module
from .network_server import NetworkServer

# Import protocol constants and configuration (refactored for modularity)
from .protocol import *  # Protocol constants and utilities
from .crc_utils import calculate_crc32  # Centralized CRC calculation

# Import request handler module
from .request_handlers import RequestHandler
from .server_singleton import ensure_single_server_instance

# Configuration constants now imported from config.py module
# Remaining server-specific constants:

# Behavior Configuration
CLIENT_SOCKET_TIMEOUT = 60.0  # Timeout for individual socket operations with a client
CLIENT_SESSION_TIMEOUT = 10 * 60  # Overall inactivity timeout for a client session (10 minutes)
PARTIAL_FILE_TIMEOUT = 15 * 60 # Timeout for incomplete multi-packet file transfers (15 minutes)
MAINTENANCE_INTERVAL = 20.0 # How often to run maintenance tasks (seconds)
MAX_PAYLOAD_READ_LIMIT = (16 * 1024 * 1024) + 1024  # Max size for a single payload read (16MB chunk + headers)
MAX_ORIGINAL_FILE_SIZE = 4 * 1024 * 1024 * 1024 # Max original file size (e.g., 4GB) - for sanity checking
MAX_CONCURRENT_CLIENTS = 50 # Max number of concurrent client connections

# MAX_CLIENT_NAME_LENGTH imported from config.py (line 39)
MAX_FILENAME_FIELD_SIZE = 255 # Size of the filename field in protocol
MAX_ACTUAL_FILENAME_LENGTH = 250 # Practical limit for actual filename within the field
RSA_PUBLIC_KEY_SIZE = 160 # Bytes, X.509 format (for 1024-bit RSA - per protocol specification)
AES_KEY_SIZE_BYTES = 32 # 256-bit AES

# Logging Configuration
DEFAULT_LOG_LINES_LIMIT = 500  # Default number of log lines to retrieve (increased for GUI)
DEFAULT_ACTIVITY_LIMIT = 50  # Default number of activity entries to return
MAX_INLINE_DOWNLOAD_BYTES = 10 * 1024 * 1024  # Limit for embedding file content in responses (10 MB)
MAX_LOG_EXPORT_SIZE = 100 * 1024 * 1024  # Maximum log file size to export (100 MB) - prevents hang on huge logs
MAX_LOG_EXPORT_LINES = 50000  # Maximum number of lines to read from log file during export - prevents hang on huge logs

VALID_LOG_EXPORT_FORMATS = {"text", "json", "csv"}

# Settings Configuration
SETTINGS_FILE = "server_settings.json"  # Settings persistence file

# String constants for error messages and metrics
METRIC_DB_QUERY_DURATION = "database.query.duration"
ERROR_FILE_NOT_FOUND = "File not found"
ERROR_ROW_ID_REQUIRED = "Row identifier is required"
SERVER_LOG_FILENAME = 'server.log'

"""
LOGGING LEVEL STANDARDS:
- DEBUG: Protocol details, packet parsing, reassembly status, detailed state changes
- INFO: Client connections/disconnections, file transfers, successful operations, startup/shutdown
- WARNING: Recoverable errors, validation failures, retries, deprecated usage
- ERROR: Failed operations, database errors, crypto failures, network issues
- CRITICAL: System failures, startup failures, security violations

Best Practices:
1. Use DEBUG for verbose diagnostic info (disabled in production by default)
2. Use INFO for important events that help understand system flow
3. Use WARNING for issues that don't stop operation but need attention
4. Use ERROR for failures that prevent specific operations
5. Include relevant context (client name, file name, operation type) in all messages
6. Avoid duplicate logging (don't log same event at multiple levels)
"""

# Enhanced Logging Configuration with dual output
# Initialize Sentry error tracking for backup server
if sentry_available:
    sentry_initialized = init_sentry("backup-server", traces_sample_rate=0.1)
else:
    sentry_initialized = False

# Set up enhanced dual logging with observability features
logger, backup_log_file = setup_dual_logging(
    logger_name=__name__,
    server_type="backup-server",
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    console_format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)

# Setup structured logging for backup server
structured_logger = create_enhanced_logger("backup-server", logger)
metrics_collector = get_metrics_collector()
system_monitor = get_system_monitor()


# ═══════════════════════════════════════════════════════════════════════════════
# Retry Decorator for Transient Failures
# ═══════════════════════════════════════════════════════════════════════════════

def retry(max_attempts: int = 3, backoff_base: float = 0.5, exceptions: tuple = (Exception,)):
    """
    Decorator to retry a function on transient failures with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff_base: Base delay in seconds for exponential backoff (default: 0.5)
        exceptions: Tuple of exception types to catch and retry (default: all Exception)

    Example:
        @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
        def get_clients(self):
            return self.db_manager.get_all_clients()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt == max_attempts:
                        break

                    # Record retry metric
                    metrics_collector.record_counter(
                        "database.retry.attempts",
                        tags={'function': func.__name__, 'attempt': str(attempt)}
                    )

                    # Calculate exponential backoff delay
                    delay = backoff_base * (2 ** (attempt - 1))

                    # Log retry attempt (use WARNING level per logging standards)
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

            # All retries exhausted, log error and re-raise
            logger.error(
                f"All {max_attempts} attempts failed for {func.__name__}: {last_exception}"
            )
            if last_exception is not None:
                raise last_exception
            # If somehow no exception was captured, raise a generic error
            raise RuntimeError(f"All {max_attempts} attempts failed for {func.__name__} with no exception captured")

        return wrapper
    return decorator

# Maintain compatibility: also log to the original server.log file
# Now uses RotatingFileHandler to prevent unbounded growth
import os
from logging.handlers import RotatingFileHandler

LOG_FORMAT = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
os.makedirs("logs", exist_ok=True)
server_log_handler = RotatingFileHandler(
    "logs/server.log",
    mode='a',
    maxBytes=10*1024*1024,  # 10 MB per file
    backupCount=5           # Keep 5 backup files
)
server_log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
server_log_handler.setLevel(logging.DEBUG)
logger.addHandler(server_log_handler)

# Protocol constants now imported from protocol.py module


# --- Client Representation ---
class Client:
    """
    Represents a connected client and stores its state.
    """
    def __init__(self, client_id: bytes, name: str, public_key_bytes: bytes | None = None):
        """
        Initializes a Client object.

        Args:
            client_id: The unique UUID (bytes) of the client.
            name: The username of the client.
            public_key_bytes: The client's RSA public key in X.509 format (optional).
        """
        self.id: bytes = client_id
        self.name: str = name
        self.public_key_bytes: bytes | None = public_key_bytes
        self.public_key_obj: Any | None = None # PyCryptodome RSA key object or compatibility layer equivalent
        self.aes_key: bytes | None = None # Current session AES key
        self.last_seen: float = time.monotonic() # Monotonic time for session timeout
        self.last_seen_db: str | None = None # Database timestamp for audit purposes
        self.partial_files: dict[str, dict[str, Any]] = {} # For reassembling multi-packet files
        self.lock: threading.Lock = threading.Lock() # To protect concurrent access to client state

        if public_key_bytes:
            self._import_public_key()

    def _import_public_key(self):
        """Imports the RSA public key from bytes if available."""
        if self.public_key_bytes:
            try:
                self.public_key_obj = RSA.import_key(self.public_key_bytes)
                logger.debug(f"Client '{self.name}': Successfully imported public key.")
            except ValueError as e:
                logger.error(f"Client '{self.name}': Failed to import public key from stored bytes: {e}")
                self.public_key_obj = None # Ensure consistent state if import fails

    def update_last_seen(self):
        """Updates the last seen timestamp to the current monotonic time."""
        with self.lock:
            self.last_seen = time.monotonic()

    def set_public_key(self, public_key_bytes_data: bytes):
        """
        Sets and imports the client's RSA public key.

        Args:
            public_key_bytes_data: The public key in X.509 format.

        Raises:
            ProtocolError: If the key size is incorrect or the key format is invalid.
        """
        with self.lock:
            if len(public_key_bytes_data) != RSA_PUBLIC_KEY_SIZE:
                raise ProtocolError(f"Public key size is incorrect for client '{self.name}'. Expected {RSA_PUBLIC_KEY_SIZE}, got {len(public_key_bytes_data)}.")
            self.public_key_bytes = public_key_bytes_data
            self._import_public_key() # Attempt to parse and store the RsaKey object
            if not self.public_key_obj: # Check if import failed
                 raise ProtocolError(f"Invalid RSA public key format provided by client '{self.name}' (failed to import).")

    def get_aes_key(self) -> bytes | None:
        """Returns the current session AES key (thread-safe)."""
        # Thread-safe access: Called cross-thread from database operations
        with self.lock:
            return self.aes_key

    def set_aes_key(self, aes_key_data: bytes):
        """
        Sets the client's session AES key.

        Args:
            aes_key_data: The AES key (bytes).

        Raises:
            ValueError: If the AES key size is incorrect.
        """
        with self.lock: # Protect AES key modification
            if len(aes_key_data) != AES_KEY_SIZE_BYTES:
                 raise ValueError(f"AES key size for client '{self.name}' is incorrect. Expected {AES_KEY_SIZE_BYTES}, got {len(aes_key_data)}.")
            self.aes_key = aes_key_data

    def clear_partial_file(self, filename: str):
        """Removes partial file reassembly data for a given filename."""
        with self.lock:
            if filename in self.partial_files:
                del self.partial_files[filename]
                logger.debug(f"Client '{self.name}': Cleared partial file reassembly data for '{filename}'.")


    def clear_all_partial_files(self):
        """Clears all in-memory partial file transfer states for this client."""
        with self.lock:
            count = len(self.partial_files)
            self.partial_files.clear()
            logger.debug(f"Client '{self.name}': Cleared all partial file data ({count} entries)")

    def cleanup_stale_partial_files(self) -> int:
        """
        Removes partial file data for transfers that haven't seen activity recently.

        Returns:
            The number of stale partial file transfers cleaned up for this client.
        """
        with self.lock:
            current_monotonic_time = time.monotonic()
            stale_files_to_remove = [
                filename for filename, data in self.partial_files.items()
                if current_monotonic_time - data.get("timestamp", 0) > PARTIAL_FILE_TIMEOUT
            ]

            # Remove stale entries
            for filename in stale_files_to_remove:
                logger.warning(f"Client '{self.name}': Stale partial file transfer timed out for '{filename}'. Removing associated data.")
                del self.partial_files[filename]

            return len(stale_files_to_remove)


# --- Main Server Class ---
class BackupServer:
    """
    The main server class that handles client connections, protocol messages,
    encryption, file storage, and database interactions.
    """

    def __init__(self):
        """Initializes the BackupServer instance."""
        self.clients: dict[bytes, Client] = {} # In-memory store: client_id_bytes -> Client object
        self.clients_by_name: dict[str, bytes] = {} # In-memory store: client_name_str -> client_id_bytes
        self.clients_lock: threading.Lock = threading.Lock() # Protects access to clients and clients_by_name

        # Rate limiting for log exports
        self._last_log_export_time: dict[str, float] = {}  # Track by session key
        self._log_export_lock: threading.Lock = threading.Lock()
        self._last_db_export_time: dict[str, float] = {}  # Track database export rate limiting
        self._db_export_lock: threading.Lock = threading.Lock()

        # Use default port for now
        self.port = DEFAULT_PORT
        self.running = False
        self.shutdown_event = threading.Event()

        # Initialize request handler first, as it's needed by NetworkServer
        self.request_handler: RequestHandler = RequestHandler(self)

        # Initialize network server with proper parameters
        self.network_server: NetworkServer = NetworkServer(
            port=self.port,
            request_handler=self.request_handler.process_request,
            client_resolver=self.get_client_by_id,
            shutdown_event=self.shutdown_event
        )

        # Initialize database manager
        self.db_manager: DatabaseManager = DatabaseManager()
        self._storage_dir = Path(FILE_STORAGE_DIR)
        with contextlib.suppress(OSError):
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._last_files_cleaned_count: int = 0
        self._last_partial_files_cleaned: int = 0
        self._last_maintenance_timestamp: float | None = None
        self._log_export_rate_limits: dict[str, float] = {}
        # Allow disabling integrated GUI when standalone GUI process will be launched
        disable_flag = os.environ.get("CYBERBACKUP_DISABLE_INTEGRATED_GUI")
        logger.info("[GUI] Legacy Tkinter GUI integration removed - FletV2 GUI is now used instead")

        # Perform pre-flight checks and initialize database
        self.db_manager.check_startup_permissions() # Perform pre-flight checks before extensive setup
        self.db_manager.ensure_storage_dir() # Ensure 'received_files' directory exists
        self.db_manager.init_database()      # Initialize SQLite database and tables

        # Set backup_log_file instance attribute to enable enhanced log reading
        self.backup_log_file = backup_log_file

        # Note: Signal handlers are now managed by NetworkServer
        # but we keep a reference for main server coordination
        # Port is already set during NetworkServer initialization

    def create_client(self, client_id: bytes, name: str) -> 'Client':
        """Factory method to create a new Client instance."""
        return Client(client_id, name)

    def get_client_by_id(self, client_id: bytes) -> Client | None:
        """Resolves a client object from the in-memory store by client ID."""
        with self.clients_lock:
            return self.clients.get(client_id)

    def resolve_client(self, client_identifier: str) -> dict[str, Any]:
        """Resolve client by ID or name - compatible with ServerBridge signature."""
        try:
            # First try to resolve by client ID (hex string)
            if client_identifier in self.clients_by_name:
                # Found by name
                client_id_bytes = self.clients_by_name[client_identifier]
                if client := self.clients.get(client_id_bytes):
                    return self._format_response(True, {
                        'id': client.id.hex(),
                        'name': client.name,
                        'public_key_size': len(client.public_key_bytes) if client.public_key_bytes else 0
                    })

            # Try to resolve by hex ID
            with contextlib.suppress(ValueError):
                client_id_bytes = bytes.fromhex(client_identifier)
                if client := self.clients.get(client_id_bytes):
                    return self._format_response(True, {
                        'id': client.id.hex(),
                        'name': client.name,
                        'public_key_size': len(client.public_key_bytes) if client.public_key_bytes else 0
                    })
            return self._format_response(False, error=f"Client '{client_identifier}' not found")
        except Exception as e:
            logger.error(f"Failed to resolve client {client_identifier}: {e}")
            return self._format_response(False, error=str(e))


    def _update_gui_client_stats(self):
        """Updates GUI with current client statistics."""
        with self.clients_lock:
            connected_clients = len(self.clients)
            # Get total clients from database
            total_clients = connected_clients
            with contextlib.suppress(Exception):
                total_from_db = len(self.db_manager.get_all_clients())
                total_clients = max(total_from_db, connected_clients)

            # Calculate active transfers while holding lock for consistency
            active_transfers = self._calculate_active_transfers()



    def _parse_string_from_payload(self, payload_bytes: bytes, field_len: int, max_actual_len: int, field_name: str = "String") -> str:
        """
        Parses a null-terminated, zero-padded string from a fixed-length field within a payload.
        """
        if len(payload_bytes) < field_len:
            raise ProtocolError(f"{field_name}: Field is shorter than expected ({len(payload_bytes)} < {field_len})")

        string_field = payload_bytes[:field_len]
        null_pos = string_field.find(b'\x00')

        if null_pos == -1:
            actual_string_bytes = string_field
        else:
            actual_string_bytes = string_field[:null_pos]

        if len(actual_string_bytes) > max_actual_len:
            raise ProtocolError(f"{field_name}: String too long ({len(actual_string_bytes)} > {max_actual_len})")

        try:
            return actual_string_bytes.decode('utf-8', errors='strict')
        except UnicodeDecodeError as e:
            raise ProtocolError(f"{field_name}: Invalid UTF-8 encoding: {e}") from e

    def _load_clients_from_db(self):
        """Loads existing client data from the database into memory at server startup."""
        logger.info("Loading existing clients from database into memory...")
        try:
            rows = self.db_manager.load_clients_from_db()
        except ServerError as e: # Raised by db_manager on critical read failure
            logger.critical(f"CRITICAL FAILURE: Could not load client data from database: {e}. Server cannot continue.")
            # This is a fatal error for server operation.
            raise SystemExit(f"Startup aborted: Failed to load critical client data from database. Details: {e}") from e

        with self.clients_lock: # Ensure thread-safe access to shared client dictionaries
            self.clients.clear()
            self.clients_by_name.clear()
            loaded_count = 0
            if rows: # Check if any rows were returned
                for row_id, name, pk_bytes, last_seen_iso_utc in rows:
                    try:
                        client = Client(row_id, name, pk_bytes) # Create Client object
                        # Store DB timestamp for audit/logging while using fresh monotonic time for session
                        client.last_seen_db = last_seen_iso_utc  # Database timestamp for audit
                        self.clients[row_id] = client
                        self.clients_by_name[name] = row_id
                        loaded_count +=1
                    except Exception as e_obj: # Catch errors creating individual Client objects (e.g. bad PK)
                        logger.error(f"Error creating Client object for '{name}' (ID: {row_id.hex() if row_id else 'N/A'}) from DB row: {e_obj}")
            logger.info(f"Successfully loaded {loaded_count} client(s) from database.")


    # Port configuration is now handled by NetworkServer


    def _calculate_active_transfers(self) -> int:
        """Return the number of currently active file transfers across clients."""
        with self.clients_lock:
            # Transfer state is tracked per-client in client.partial_files
            in_progress = sum(len(client.partial_files) for client in self.clients.values())

        return in_progress

    def _cleanup_stale_temp_files(self, cutoff_seconds: int = PARTIAL_FILE_TIMEOUT) -> int:
        """Remove stale temporary files left behind by aborted transfers."""
        if not self._storage_dir.exists():
            return 0

        cleanup_before = time.time() - max(cutoff_seconds, 0)
        cleaned = 0

        for temp_path in self._storage_dir.glob("*.tmp_EncryptedBackup"):
            try:
                if temp_path.stat().st_mtime <= cleanup_before:
                    temp_path.unlink()
                    cleaned += 1
                    logger.info(f"Maintenance: Removed stale temp file '{temp_path.name}'")
            except FileNotFoundError:
                continue
            except OSError as err:
                logger.warning(f"Maintenance: Failed to remove temp file '{temp_path}': {err}")

        return cleaned


    def _periodic_maintenance_job(self):
        """
        Runs periodically to perform maintenance and send status updates to the GUI.
        """
        try:
            # --- Maintenance Tasks ---
            # (Existing cleanup logic remains the same)
            inactive_clients_removed_count = 0
            with self.clients_lock:
                current_monotonic_time = time.monotonic()
                inactive_client_ids_to_remove = [
                    cid for cid, client_obj in self.clients.items()
                    if (current_monotonic_time - client_obj.last_seen) > CLIENT_SESSION_TIMEOUT
                ]
                for cid in inactive_client_ids_to_remove:
                    if client_obj := self.clients.pop(cid, None):
                        self.clients_by_name.pop(client_obj.name, None)
                        inactive_clients_removed_count += 1
                        logger.info(f"Client '{client_obj.name}' session timed out.")

            with self.clients_lock:
                active_clients_list = list(self.clients.values())
            stale_partial_files_cleaned_count = sum(
                client_obj.cleanup_stale_partial_files() for client_obj in active_clients_list
            )

            stale_temp_files_cleaned_count = self._cleanup_stale_temp_files()
            self._last_partial_files_cleaned = stale_partial_files_cleaned_count
            self._last_files_cleaned_count = stale_temp_files_cleaned_count
            self._last_maintenance_timestamp = time.time()

            # --- Record Gauge Metrics ---
            # Calculate real-time metrics for observability
            active_transfers = self._calculate_active_transfers()
            num_active_clients = len(active_clients_list)

            # Record gauge metrics with real values
            metrics_collector.record_gauge("server.clients.active", num_active_clients)
            metrics_collector.record_gauge("server.transfers.active", active_transfers)

            # Record memory usage using psutil (available through observability module)
            try:
                import psutil
                process_memory = psutil.Process().memory_info().rss
                metrics_collector.record_gauge("server.memory.usage_bytes", process_memory)
            except Exception as mem_err:
                logger.debug(f"Could not record memory metric: {mem_err}")

            # --- Persist Metrics to Database ---
            # Record key metrics every maintenance cycle for historical tracking
            try:
                logger.debug(f"Recording metrics to database (interval: {MAINTENANCE_INTERVAL}s)")

                # Record active clients count
                self.db_manager.record_metric("connections", num_active_clients)
                logger.debug(f"  ✓ Recorded connections metric: {num_active_clients}")

                # Record total files backed up
                total_files = self.db_manager.get_total_files_count()
                self.db_manager.record_metric("files", total_files)
                logger.debug(f"  ✓ Recorded files metric: {total_files}")

                # Record bandwidth (total bytes transferred)
                total_bytes = self.db_manager.get_total_bytes_transferred()
                bandwidth_mb = total_bytes / (1024 * 1024)  # Convert to MB
                self.db_manager.record_metric("bandwidth", bandwidth_mb)
                logger.debug(f"  ✓ Recorded bandwidth metric: {bandwidth_mb:.2f} MB")

                logger.debug(f"Successfully persisted all metrics: {num_active_clients} connections, {total_files} files, {bandwidth_mb:.2f} MB bandwidth")
            except Exception as metrics_err:
                logger.warning(f"Failed to persist metrics to database: {metrics_err}")

            # --- Clean Up Old Metrics (once per day) ---
            # Only run cleanup once per day (86400 seconds)
            current_time = time.time()
            if not hasattr(self, '_last_metrics_cleanup_time'):
                self._last_metrics_cleanup_time = 0

            if (current_time - self._last_metrics_cleanup_time) >= 86400:  # 24 hours
                try:
                    rows_deleted = self.db_manager.cleanup_old_metrics(days_to_keep=7)
                    self._last_metrics_cleanup_time = current_time
                    if rows_deleted > 0:
                        logger.info(f"Daily metrics cleanup: removed {rows_deleted} old samples")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup old metrics: {cleanup_err}")

            # GUI status updates removed - FletV2 GUI uses ServerBridge for data access

        except Exception as e:
            logger.critical(f"Critical error in periodic maintenance job: {e}", exc_info=True)


    def _handle_startup_system_exit(self, e: SystemExit, start_time: float):
        """Extract method to handle SystemExit during startup."""
        duration_ms = (time.time() - start_time) * 1000
        structured_logger.error(f"Server startup aborted: {e}",
                              operation="server_start",
                              duration_ms=duration_ms,
                              error_code="SystemExit")
        logger.critical(f"Server startup aborted due to critical error during data loading: {e}")
        self.running = False
        self.shutdown_event.set()

    def start(self):
        """Starts the server: loads data, and begins listening for connections."""
        if self.running:
            logger.warning("Server is already running. Start command ignored.")
            return

        start_time = time.time()
        structured_logger.info("Starting backup server", operation="server_start")

        self.running = True
        self.shutdown_event.clear()

        try:
            # Start system monitoring
            if not system_monitor.running:
                system_monitor.start()
                structured_logger.info("System monitoring started")

            self._load_clients_from_db()

            # Record server start metrics
            metrics_collector.record_counter("server.starts.total")

        except SystemExit as e:
            self._handle_startup_system_exit(e, start_time)
            return

        # Start the network server in a separate thread
        import threading
        self.network_thread = threading.Thread(target=self.network_server.start, daemon=True)
        self.network_thread.start()

        duration_ms = (time.time() - start_time) * 1000
        structured_logger.info("Backup server started successfully",
                             operation="server_start",
                             duration_ms=duration_ms,
                             context={
                                 "version": SERVER_VERSION,
                                 "port": self.port,
                                 "clients_loaded": len(self.clients)
                             })

        logger.info(f"Encrypted Backup Server Version {SERVER_VERSION} started successfully on port {self.port}.")

        # Record successful start metrics
        metrics_collector.record_timer("server.startup.duration", duration_ms)
        metrics_collector.record_gauge("server.clients.loaded", len(self.clients))

        # GUI status updates removed - FletV2 GUI gets status data through ServerBridge


    def stop(self):
        """Initiates a graceful shutdown of the server."""
        if not self.running:
            logger.info("Server is not running.")
            return

        logger.warning("Server shutdown sequence initiated...")

        # Clean up client sessions and resources
        with self.clients_lock:
            # Clear all partial file transfers for each client
            for client in self.clients.values():
                try:
                    client.clear_all_partial_files()
                except Exception as e:
                    logger.debug(f"Error clearing partial files for client '{client.name}': {e}")

            # Clear in-memory client tracking
            num_clients = len(self.clients)
            self.clients.clear()
            self.clients_by_name.clear()
            logger.info(f"Cleaned up {num_clients} client session(s) from memory")

        # Shutdown GUI and network components
        self.network_server.stop()
        self.running = False
        logger.info("Server has been stopped.")

    # ============================================================================
    # ServerBridge Integration Layer - Wrapper Methods
    # ============================================================================

    def _format_response(self, success: bool, data: Any = None, error: str = "") -> dict[str, Any]:
        """Helper method to format responses in ServerBridge expected format."""
        return {
            'success': success,
            'data': data,
            'error': error
        }

    def _validate_client_name(self, name: str) -> tuple[bool, str]:
        """
        Centralized client name validation.

        Args:
            name: Client name to validate

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        if not name or not isinstance(name, str):
            return False, "Client name is required and must be a string"

        if len(name) > MAX_CLIENT_NAME_LENGTH:
            return False, f"Client name too long (max {MAX_CLIENT_NAME_LENGTH} chars)"

        # Check for invalid control characters
        if any(c in name for c in ('\x00', '\n', '\r', '\t')):
            return False, "Client name contains invalid characters"

        return True, ""

    # --- Client Operations ---
#
# CLIENT RETRIEVAL METHODS - USAGE GUIDE:
# ========================================
# get_clients() - Synchronous, blocks until DB query completes. Use for simple operations
# get_clients_async() - Non-blocking async version. Use in UI/async contexts to prevent blocking
# get_client_details(client_id) - Get single client by ID. More efficient than getting all clients
#
# All methods query the database as single source of truth. No in-memory caching to avoid sync issues.

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def get_clients(self) -> dict[str, Any]:
        """
        Get all clients - delegates to db_manager.get_all_clients().

        Automatically retries up to 3 times on database lock errors (sqlite3.OperationalError)
        with exponential backoff (0.5s, 1.0s, 2.0s delays).
        """
        try:
            # Time the database query
            query_start = time.time()
            clients_data = self.db_manager.get_all_clients()
            query_duration_ms = (time.time() - query_start) * 1000

            # Record database query timing metric
            metrics_collector.record_timer(METRIC_DB_QUERY_DURATION,
                                          query_duration_ms,
                                          tags={'operation': 'get_all_clients'})

            return self._format_response(True, clients_data)
        except Exception as e:
            logger.error(f"Failed to get clients: {e}")
            return self._format_response(False, error=str(e))

    async def get_clients_async(self) -> dict[str, Any]:
        """Async version of get_clients()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_clients)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def get_client_details(self, client_id: str) -> dict[str, Any]:
        """Get details for a specific client by ID."""
        try:
            client_id_bytes = bytes.fromhex(client_id)
            client_data = self.db_manager.get_client_by_id(client_id_bytes)
            if client_data:
                return self._format_response(True, {
                    'id': client_id_bytes.hex(),
                    'name': client_data[1],
                    'last_seen': client_data[3],
                    'public_key_size': len(client_data[2]) if client_data[2] else 0
                })
            else:
                return self._format_response(False, error=f"Client with ID {client_id} not found")
        except Exception as e:
            logger.error(f"Failed to get client details for {client_id}: {e}")
            return self._format_response(False, error=str(e))

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def add_client(self, client_data: dict[str, Any]) -> dict[str, Any]:
        """
        Add a new client using existing client creation logic.

        Automatically retries up to 3 times on database lock errors (sqlite3.OperationalError)
        with exponential backoff (0.5s, 1.0s, 2.0s delays).
        """
        try:
            import uuid
            client_id = uuid.uuid4().bytes
            name = client_data.get('name', '')

            # Validate name using centralized validation
            is_valid, error_msg = self._validate_client_name(name)
            if not is_valid:
                return self._format_response(False, error=error_msg)

            # Check if client name already exists in memory
            with self.clients_lock:
                if name in self.clients_by_name:
                    return self._format_response(False, error=f"Client name '{name}' already exists")

            # Check database for duplicate name (catch race conditions)
            try:
                existing_clients = self.db_manager.get_all_clients()
                if any(c.get('name') == name for c in existing_clients):
                    return self._format_response(False, error=f"Client name '{name}' already exists in database")
            except Exception as db_check_error:
                logger.warning(f"Could not verify name uniqueness in database: {db_check_error}")

            # Create new client
            client = self.create_client(client_id, name)

            # Add to in-memory store
            with self.clients_lock:
                self.clients[client_id] = client
                self.clients_by_name[name] = client_id

            # Save to database with timing
            query_start = time.time()
            self.db_manager.save_client_to_db(client.id, client.name, client.public_key_bytes, client.get_aes_key())
            query_duration_ms = (time.time() - query_start) * 1000

            # Record database write timing metric
            metrics_collector.record_timer(METRIC_DB_QUERY_DURATION,
                                          query_duration_ms,
                                          tags={'operation': 'save_client_to_db'})

            return self._format_response(True, {
                'id': client_id.hex(),
                'name': name,
                'created': True
            })
        except Exception as e:
            logger.error(f"Failed to add client: {e}")
            return self._format_response(False, error=str(e))

    async def add_client_async(self, client_data: dict[str, Any]) -> dict[str, Any]:
        """Async version of add_client()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.add_client, client_data)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def delete_client(self, client_id: str) -> dict[str, Any]:
        """
        Delete a client - delegates to db_manager.delete_client().

        Automatically retries up to 3 times on database lock errors (sqlite3.OperationalError)
        with exponential backoff (0.5s, 1.0s, 2.0s delays).
        """
        try:
            client_id_bytes = bytes.fromhex(client_id)

            # Delete from database FIRST with timing
            query_start = time.time()
            success = self.db_manager.delete_client(client_id_bytes)
            query_duration_ms = (time.time() - query_start) * 1000

            # Record database write timing metric
            metrics_collector.record_timer(METRIC_DB_QUERY_DURATION,
                                          query_duration_ms,
                                          tags={'operation': 'delete_client'})

            if not success:
                return self._format_response(False, error="Failed to delete client from database")

            # THEN remove from in-memory store (only if database deletion succeeded)
            with self.clients_lock:
                if client := self.clients.pop(client_id_bytes, None):
                    self.clients_by_name.pop(client.name, None)

            return self._format_response(True, {'deleted': True})
        except Exception as e:
            logger.error(f"Failed to delete client {client_id}: {e}")
            return self._format_response(False, error=str(e))

    async def delete_client_async(self, client_id: str) -> dict[str, Any]:
        """Async version of delete_client()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete_client, client_id)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def update_client(self, client_id: str, updated_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update client information.

        Automatically retries up to 3 times on database lock errors (sqlite3.OperationalError)
        with exponential backoff (0.5s, 1.0s, 2.0s delays).

        Args:
            client_id: Client UUID as hex string
            updated_data: Dictionary with fields to update:
                - 'name': str (optional) - New client name
                - 'public_key': bytes (optional) - New public key

        Returns:
            dict: {'success': bool, 'data': dict, 'error': str}
        """
        try:
            # Convert hex string to bytes
            client_id_bytes = bytes.fromhex(client_id)

            # Extract fields to update
            name = updated_data.get('name')
            public_key = updated_data.get('public_key')  # Should be bytes if provided

            # Validate name if provided
            if name is not None:
                is_valid, error_msg = self._validate_client_name(name)
                if not is_valid:
                    return self._format_response(False, error=error_msg)

                # Check if new name conflicts with existing client
                with self.clients_lock:
                    if name in self.clients_by_name:
                        existing_id = self.clients_by_name[name]
                        if existing_id != client_id_bytes:
                            return self._format_response(False, error=f"Client name '{name}' already exists")

            # Update in database with timing
            query_start = time.time()
            success = self.db_manager.update_client(client_id_bytes, name, public_key)
            query_duration_ms = (time.time() - query_start) * 1000

            # Record database write timing metric
            metrics_collector.record_timer(METRIC_DB_QUERY_DURATION,
                                          query_duration_ms,
                                          tags={'operation': 'update_client'})

            if not success:
                return self._format_response(False, error="Failed to update client in database")

            # Update in-memory representation if client is currently connected
            with self.clients_lock:
                if client := self.clients.get(client_id_bytes):
                    old_name = client.name

                    # Update name mapping
                    if name and name != old_name:
                        self.clients_by_name.pop(old_name, None)
                        client.name = name
                        self.clients_by_name[name] = client_id_bytes
                        logger.info(f"Updated client name: '{old_name}' → '{name}'")

                    # Update public key if provided
                    if public_key:
                        client.set_public_key(public_key)
                        logger.info(f"Updated public key for client '{client.name}'")

            return self._format_response(True, {
                'id': client_id,
                'updated': True,
                'fields_updated': [k for k, v in {'name': name, 'public_key': public_key}.items() if v is not None]
            })

        except ValueError as e:
            logger.error(f"Invalid client ID format '{client_id}': {e}")
            return self._format_response(False, error=f"Invalid client ID: {e}")
        except Exception as e:
            logger.error(f"Failed to update client {client_id}: {e}")
            return self._format_response(False, error=str(e))

    async def update_client_async(self, client_id: str, updated_data: dict[str, Any]) -> dict[str, Any]:
        """Async version of update_client()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.update_client, client_id, updated_data)

    def disconnect_client(self, client_id: str) -> dict[str, Any]:
        """Disconnect a client (remove from in-memory store only)."""
        try:
            client_id_bytes = bytes.fromhex(client_id)

            with self.clients_lock:
                client = self.clients.pop(client_id_bytes, None)
                if client:
                    self.clients_by_name.pop(client.name, None)
                    logger.info(f"Client '{client.name}' disconnected")
                    return self._format_response(True, {'disconnected': True})
                else:
                    return self._format_response(False, error="Client not found in active connections")
        except Exception as e:
            logger.error(f"Failed to disconnect client {client_id}: {e}")
            return self._format_response(False, error=str(e))

    async def disconnect_client_async(self, client_id: str) -> dict[str, Any]:
        """Async version of disconnect_client()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.disconnect_client, client_id)

    def _parse_file_identifier(self, file_id: str) -> tuple[str, str]:
        """Validate and split a composite file identifier into client ID and filename."""
        if not isinstance(file_id, str) or ':' not in file_id:
            raise ValueError("Invalid file identifier. Expected 'client_id:filename'.")

        client_part, filename = file_id.split(':', 1)
        client_part = client_part.strip()
        filename = filename.strip()

        if not client_part or not filename:
            raise ValueError("Invalid file identifier components.")

        try:
            bytes.fromhex(client_part)
        except ValueError as exc:
            raise ValueError("Invalid client ID provided.") from exc

        if any(sep in filename for sep in ('/', '\\')) or '..' in filename:
            raise ValueError("Invalid filename provided.")

        return client_part, filename

    def _resolve_storage_path(self, stored_path: str | None, filename: str) -> Path:
        """Resolve a stored file path ensuring it resides under the storage directory."""
        storage_root = self._storage_dir.resolve()
        candidates: list[Path] = []

        if stored_path:
            candidate = Path(stored_path)
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve(strict=False)
            else:
                candidate = candidate.resolve(strict=False)

            if storage_root in candidate.parents or candidate.parent == storage_root:
                candidates.append(candidate)

        candidates.append((storage_root / filename).resolve(strict=False))

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[-1]

    # --- File Operations ---

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def get_files(self) -> dict[str, Any]:
        """
        Get all files - delegates to db_manager.get_all_files().

        Automatically retries up to 3 times on database lock errors (sqlite3.OperationalError)
        with exponential backoff (0.5s, 1.0s, 2.0s delays).
        """
        try:
            # Time the database query
            query_start = time.time()
            files_data = self.db_manager.get_all_files()
            query_duration_ms = (time.time() - query_start) * 1000

            # Record database query timing metric
            metrics_collector.record_timer(METRIC_DB_QUERY_DURATION,
                                          query_duration_ms,
                                          tags={'operation': 'get_all_files'})

            # Normalize client_id to hex string if it's bytes
            for file_data in files_data:
                if 'client_id' in file_data and isinstance(file_data['client_id'], bytes):
                    file_data['client_id'] = file_data['client_id'].hex()
            return self._format_response(True, files_data)
        except Exception as e:
            logger.error(f"Failed to get files: {e}")
            return self._format_response(False, error=str(e))

    async def get_files_async(self) -> dict[str, Any]:
        """Async version of get_files()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_files)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def get_client_files(self, client_id: str) -> dict[str, Any]:
        """Get files for a specific client - delegates to db_manager.get_files_for_client()."""
        try:
            # Pass the hex string directly to db_manager.get_files_for_client
            files_data = self.db_manager.get_files_for_client(client_id)
            # Attach client_id to each file entry
            for file_data in files_data:
                file_data['client_id'] = client_id
            return self._format_response(True, files_data)
        except Exception as e:
            logger.error(f"Failed to get files for client {client_id}: {e}")
            return self._format_response(False, error=str(e))

    async def get_client_files_async(self, client_id: str) -> dict[str, Any]:
        """Async version of get_client_files()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_client_files, client_id)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def delete_file(self, file_id: str) -> dict[str, Any]:
        """Delete a file - delegates to db_manager.delete_file()."""
        try:
            if ':' not in file_id:
                # Fallback: try to parse as a single identifier
                return self._format_response(False, error="Invalid file_id format. Expected 'client_id:filename'")

            client_id_str, filename = file_id.split(':', 1)
            if success := self.db_manager.delete_file(client_id_str, filename):
                return self._format_response(True, {'deleted': True})
            else:
                return self._format_response(False, error="Failed to delete file")
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return self._format_response(False, error=str(e))

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def delete_file_by_client_and_name(self, client_id: str, filename: str) -> dict[str, Any]:
        """Delete a file by client ID and filename."""
        try:
            success = self.db_manager.delete_file(client_id, filename)
            if success:
                return self._format_response(True, {'deleted': True})
            else:
                return self._format_response(False, error="Failed to delete file")
        except Exception as e:
            logger.error(f"Failed to delete file {client_id}:{filename}: {e}")
            return self._format_response(False, error=str(e))

    async def delete_file_async(self, file_id: str) -> dict[str, Any]:
        """Async version of delete_file()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete_file, file_id)

    async def delete_file_by_client_and_name_async(self, client_id: str, filename: str) -> dict[str, Any]:
        """Async version of delete_file_by_client_and_name()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete_file_by_client_and_name, client_id, filename)

    def download_file(self, file_id: str, destination_path: str) -> dict[str, Any]:
        """Download a stored file and optionally persist it to a destination path."""
        try:
            client_id_str, filename = self._parse_file_identifier(file_id)
        except ValueError as exc:
            return self._format_response(False, error=str(exc))

        try:
            file_info = self.db_manager.get_file_info(client_id_str, filename)
        except Exception as db_error:
            logger.error(f"Database error while retrieving file '{file_id}': {db_error}")
            return self._format_response(False, error=f"Database error: {db_error}")

        if not file_info:
            logger.warning(f"Download requested for unknown file identifier '{file_id}'")
            return self._format_response(False, error=ERROR_FILE_NOT_FOUND)

        source_path = self._resolve_storage_path(file_info.get('path'), filename)

        if not source_path.exists():
            logger.error(f"Stored file missing for '{file_id}' (resolved path: {source_path})")
            return self._format_response(False, error="Stored file data not found on server")

        try:
            file_stat = source_path.stat()
        except OSError as stat_error:
            logger.error(f"Failed to stat file '{source_path}': {stat_error}")
            return self._format_response(False, error=f"Unable to access file metadata: {stat_error}")

        response_payload: dict[str, Any] = {
            'client_id': client_id_str,
            'filename': filename,
            'verified': bool(file_info.get('verified', False)),
            'size_bytes': file_stat.st_size,
            'source_path': str(source_path),
            'client_name': file_info.get('client'),
            'crc': file_info.get('crc')
        }

        if destination_path := (destination_path or '').strip():
            dest_path = Path(destination_path).expanduser()
            try:
                if dest_path.exists() and dest_path.is_dir():
                    dest_file_path = (dest_path / filename).resolve(strict=False)
                else:
                    dest_file_path = dest_path.resolve(strict=False)
                    dest_file_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(source_path, dest_file_path)
                response_payload['destination_path'] = str(dest_file_path)
                response_payload['copied_bytes'] = dest_file_path.stat().st_size
            except Exception as copy_error:
                logger.error(f"Failed to write downloaded file to '{destination_path}': {copy_error}")
                return self._format_response(False, error=f"Failed to write to destination: {copy_error}")

        try:
            if file_stat.st_size <= MAX_INLINE_DOWNLOAD_BYTES:
                with open(source_path, 'rb') as file_handle:
                    file_bytes = file_handle.read()
                response_payload['content_b64'] = base64.b64encode(file_bytes).decode('ascii')
            else:
                response_payload['content_b64'] = None
                response_payload['note'] = (
                    "File larger than 10 MB; content not embedded in response. "
                    "Use destination download path instead."
                )
        except Exception as read_error:
            logger.error(f"Failed to read file content for '{source_path}': {read_error}")
            return self._format_response(False, error=f"Failed to read file content: {read_error}")

        logger.info(
            f"File download fulfilled for client='{client_id_str}' file='{filename}' size={file_stat.st_size} bytes"
        )

        # Record metrics for successful file download
        metrics_collector.record_counter("file.downloads.total",
                                        tags={'client_id': client_id_str})

        return self._format_response(True, response_payload)

    async def download_file_async(self, file_id: str, destination_path: str) -> dict[str, Any]:
        """Async version of download_file()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.download_file, file_id, destination_path)

    def verify_file(self, file_id: str) -> dict[str, Any]:
        """Verify a stored file by comparing computed CRC32 with the recorded value."""
        try:
            client_id_str, filename = self._parse_file_identifier(file_id)
        except ValueError as exc:
            return self._format_response(False, error=str(exc))

        try:
            file_info = self.db_manager.get_file_info(client_id_str, filename)
        except Exception as db_error:
            logger.error(f"Database error while retrieving file info for '{file_id}': {db_error}")
            return self._format_response(False, error=f"Database error: {db_error}")

        if not file_info:
            logger.warning(f"Verification requested for unknown file identifier '{file_id}'")
            return self._format_response(False, error=ERROR_FILE_NOT_FOUND)

        source_path = self._resolve_storage_path(file_info.get('path'), filename)
        if not source_path.exists():
            logger.error(f"Stored file missing for '{file_id}' (resolved path: {source_path})")
            return self._format_response(False, error="Stored file data not found on server")

        try:
            # Read entire file and calculate CRC in one operation
            with open(source_path, 'rb') as file_handle:
                file_data = file_handle.read()
                total_bytes = len(file_data)
                computed_crc = calculate_crc32(file_data)
        except Exception as read_error:
            logger.error(f"Failed to read file '{source_path}' during verification: {read_error}")
            return self._format_response(False, error=f"Failed to read file content: {read_error}")
        expected_crc = file_info.get('crc')

        # Treat files without stored CRC as newly verified after computing it
        verified_result = expected_crc is None or expected_crc == computed_crc

        update_success = self.db_manager.update_file_verification(
            client_id_str,
            filename,
            verified_result,
            computed_crc
        )

        if not update_success:
            logger.warning(f"Verification result for '{file_id}' could not be persisted to database")

        status_text = 'verified' if verified_result else 'failed'
        response_payload: dict[str, Any] = {
            'client_id': client_id_str,
            'filename': filename,
            'verified': verified_result,
            'status': status_text,
            'size': total_bytes,
            'modified': file_info.get('date'),
            'hash': f"CRC32: 0x{computed_crc:08X}",
            'computed_crc': f"0x{computed_crc:08X}",
            'expected_crc': f"0x{expected_crc:08X}" if expected_crc is not None else None,
            'storage_path': str(source_path)
        }

        if expected_crc is None:
            response_payload['note'] = (
                "No stored CRC was available; computed checksum has been persisted."
            )
        elif not verified_result:
            response_payload['message'] = "Stored checksum does not match the computed value."

        if not update_success:
            response_payload['warning'] = "Could not persist verification result to database."

        log_message = (
            f"File verification {'succeeded' if verified_result else 'failed'} "
            f"for client='{client_id_str}' file='{filename}' computed_crc=0x{computed_crc:08X}"
        )
        if expected_crc is not None:
            log_message += f" expected_crc=0x{expected_crc:08X}"
        logger.info(log_message)

        return self._format_response(True, response_payload)

    async def verify_file_async(self, file_id: str) -> dict[str, Any]:
        """Async version of verify_file()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.verify_file, file_id)

    # --- Database Operations ---

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def get_database_info(self) -> dict[str, Any]:
        """Get database information - delegates to db_manager.get_database_stats()."""
        try:
            db_stats = self.db_manager.get_database_stats()
            return self._format_response(True, db_stats)
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return self._format_response(False, error=str(e))

    async def get_database_info_async(self) -> dict[str, Any]:
        """Async version of get_database_info()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_database_info)

    def get_table_data(self, table_name: str) -> dict[str, Any]:
        """Get data from a specific table (basic implementation) with rate limiting."""
        try:
            # Rate limiting check (10 second minimum interval per table)
            session_key = f"table_{table_name.lower()}"
            with self._db_export_lock:
                current_time = time.time()
                last_export = self._last_db_export_time.get(session_key, 0)

                if current_time - last_export < 10:
                    remaining = 10 - (current_time - last_export)
                    return self._format_response(
                        False,
                        error=f"Rate limit exceeded for table '{table_name}'. Please wait {remaining:.1f} seconds..."
                    )

                self._last_db_export_time[session_key] = current_time

            # This is a basic implementation - in a real system you'd want more sophisticated querying
            if table_name.lower() == 'clients':
                data = self.db_manager.get_all_clients()
            elif table_name.lower() == 'files':
                data = self.db_manager.get_all_files()
            else:
                return self._format_response(False, error=f"Table '{table_name}' not supported")

            return self._format_response(True, data)
        except Exception as e:
            logger.error(f"Failed to get table data for {table_name}: {e}")
            return self._format_response(False, error=str(e))

    async def get_table_data_async(self, table_name: str) -> dict[str, Any]:
        """Async version of get_table_data()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_table_data, table_name)

    # ------------------------------------------------------------------
    # Generic database editing helpers used by the Flet database view
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_table_name(table_name: str) -> str:
        return table_name.strip().lower()

    @staticmethod
    def _supported_table_name(table_name: str) -> str | None:
        table_mapping = {
            'clients': 'clients',
            'files': 'files'
        }
        normalized = BackupServer._normalize_table_name(table_name)
        return table_mapping.get(normalized)

    @staticmethod
    def _convert_primary_key_value(column_info: dict[str, Any], value: str) -> tuple[Any, str]:
        """Convert UI-provided identifier into the database representation."""
        if value is None:
            raise ValueError(ERROR_ROW_ID_REQUIRED)

        column_type = (column_info.get('type') or '').upper()
        raw_value = str(value).strip()
        if column_type.startswith('BLOB'):
            sanitized = raw_value.replace('-', '').strip()
            if not sanitized:
                raise ValueError(ERROR_ROW_ID_REQUIRED)
            if len(sanitized) % 2 != 0:
                raise ValueError("Invalid identifier format provided")
            try:
                pk_bytes = bytes.fromhex(sanitized)
            except ValueError as exc:
                raise ValueError("Invalid identifier format provided") from exc
            return pk_bytes, pk_bytes.hex()

        if column_type.startswith('INT') or column_type.startswith('INTEGER'):
            try:
                pk_int = int(raw_value, 10)
            except ValueError as exc:
                raise ValueError("Invalid numeric identifier provided") from exc
            return pk_int, str(pk_int)

        if not raw_value:
            raise ValueError(ERROR_ROW_ID_REQUIRED)
        return raw_value, raw_value

    @staticmethod
    def _convert_column_input(column_info: dict[str, Any], value: Any) -> Any:
        """Convert UI-provided value into a database-compatible format."""
        column_type = (column_info.get('type') or '').upper()
        column_name = column_info.get('name', '')

        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None

        if isinstance(value, memoryview):
            value = bytes(value)

        if column_type.startswith('BLOB'):
            if isinstance(value, (bytes, bytearray)):
                return bytes(value)
            sanitized = str(value).strip().replace('-', '')
            if not sanitized:
                return None
            if len(sanitized) % 2 != 0:
                raise ValueError(f"Value for column '{column_name}' must be hexadecimal")
            try:
                return bytes.fromhex(sanitized)
            except ValueError as exc:
                raise ValueError(f"Value for column '{column_name}' must be hexadecimal") from exc

        truthy = {'1', 'true', 'yes', 'on'}
        falsy = {'0', 'false', 'no', 'off'}

        if 'BOOL' in column_type or 'BOOLEAN' in column_type or column_name.lower() in {'verified'}:
            if isinstance(value, bool):
                return 1 if value else 0
            string_value = str(value).strip().lower()
            if string_value in truthy:
                return 1
            if string_value in falsy:
                return 0
            raise ValueError(f"Value for column '{column_name}' must be boolean")

        if column_type.startswith('INT') or column_type.startswith('INTEGER'):
            if isinstance(value, bool):
                return 1 if value else 0
            try:
                return int(float(str(value).strip()))
            except ValueError as exc:
                raise ValueError(f"Value for column '{column_name}' must be numeric") from exc

        if column_type.startswith('REAL') or column_type.startswith('DOUBLE') or column_type.startswith('FLOAT'):
            try:
                return float(str(value).strip())
            except ValueError as exc:
                raise ValueError(f"Value for column '{column_name}' must be numeric") from exc

        return str(value)

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def update_row(self, table_name: str, row_id: str, updated_data: dict[str, Any]) -> dict[str, Any]:
        """Update a row in a supported database table."""
        try:
            actual_table = self._supported_table_name(table_name)
            if not actual_table:
                return self._format_response(False, error=f"Table '{table_name}' is not supported for updates")

            schema = self.db_manager.get_table_schema(actual_table)
            if not schema:
                return self._format_response(False, error=f"Table schema for '{table_name}' unavailable")

            schema_map = {column['name'].lower(): column for column in schema}
            primary_columns = [column for column in schema if column.get('pk')]
            if len(primary_columns) != 1:
                return self._format_response(False, error="Only tables with a single-column primary key are supported")

            primary_column_info = primary_columns[0]
            try:
                primary_value, primary_hex = self._convert_primary_key_value(primary_column_info, row_id)
            except ValueError as exc:
                return self._format_response(False, error=str(exc))

            updates: dict[str, Any] = {}
            original_values: dict[str, Any] = {}
            for key, value in (updated_data or {}).items():
                if key is None:
                    continue
                column_info = schema_map.get(str(key).lower())
                if not column_info:
                    continue
                # Never allow updates to the primary key
                if column_info['name'].lower() == primary_column_info['name'].lower():
                    continue
                original_values[column_info['name']] = value
                try:
                    updates[column_info['name']] = self._convert_column_input(column_info, value)
                except ValueError as conversion_error:
                    return self._format_response(False, error=str(conversion_error))

            if actual_table == 'clients':
                client_payload: dict[str, Any] = {}

                if 'Name' in original_values:
                    proposed_name = str(original_values['Name']).strip()
                    is_valid, error_msg = self._validate_client_name(proposed_name)
                    if not is_valid:
                        return self._format_response(False, error=error_msg)
                    try:
                        existing = self.db_manager.get_client_by_name(proposed_name)
                        if existing and existing[0] != primary_value:
                            return self._format_response(False, error=f"Client name '{proposed_name}' already exists")
                    except Exception as uniqueness_error:
                        logger.warning(f"Could not verify client name uniqueness: {uniqueness_error}")
                    client_payload['name'] = proposed_name
                    updates.pop('Name', None)

                if 'PublicKey' in updates:
                    client_payload['public_key'] = updates.pop('PublicKey', None)

                if client_payload:
                    client_response = self.update_client(primary_hex, client_payload)
                    if not client_response.get('success', False):
                        return client_response

            # Apply remaining direct column updates if needed
            if updates:
                update_success = self.db_manager.update_table_row(
                    actual_table,
                    primary_column_info['name'],
                    primary_value,
                    updates
                )
                if not update_success:
                    return self._format_response(False, error="Failed to update database row")

            refreshed_row = self.db_manager.get_row_by_primary_key(
                actual_table,
                primary_column_info['name'],
                primary_value
            )
            if not refreshed_row:
                return self._format_response(False, error="Updated row could not be retrieved")
            return self._format_response(True, refreshed_row)
        except Exception as e:
            logger.error(f"Failed to update row {row_id} in table {table_name}: {e}")
            return self._format_response(False, error=str(e))

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def delete_row(self, table_name: str, row_id: str) -> dict[str, Any]:
        """Delete a row from a supported database table."""
        try:
            actual_table = self._supported_table_name(table_name)
            if not actual_table:
                return self._format_response(False, error=f"Table '{table_name}' is not supported for deletion")

            schema = self.db_manager.get_table_schema(actual_table)
            if not schema:
                return self._format_response(False, error=f"Table schema for '{table_name}' unavailable")

            primary_columns = [column for column in schema if column.get('pk')]
            if len(primary_columns) != 1:
                return self._format_response(False, error="Only tables with a single-column primary key are supported")

            primary_column_info = primary_columns[0]
            try:
                primary_value, primary_hex = self._convert_primary_key_value(primary_column_info, row_id)
            except ValueError as exc:
                return self._format_response(False, error=str(exc))

            normalized = self._normalize_table_name(table_name)
            if normalized == 'clients':
                return self.delete_client(primary_hex)

            if normalized == 'files':
                file_row = self.db_manager.get_row_by_primary_key(actual_table, primary_column_info['name'], primary_value)
                if not file_row:
                    return self._format_response(False, error=ERROR_FILE_NOT_FOUND)

                client_identifier = file_row.get('ClientID') or file_row.get('client_id')
                filename = file_row.get('FileName') or file_row.get('filename')
                if not client_identifier or not filename:
                    return self._format_response(False, error="File metadata incomplete; cannot delete")

                return self.delete_file_by_client_and_name(str(client_identifier), str(filename))

            delete_success = self.db_manager.delete_table_row(actual_table, primary_column_info['name'], primary_value)
            if not delete_success:
                return self._format_response(False, error="Row not found or could not be deleted")

            return self._format_response(True, {'deleted': True})
        except Exception as e:
            logger.error(f"Failed to delete row {row_id} from table {table_name}: {e}")
            return self._format_response(False, error=str(e))

    @retry(max_attempts=3, backoff_base=0.5, exceptions=(sqlite3.OperationalError,))
    def add_row(self, table_name: str, row_data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new row into a supported table."""
        try:
            actual_table = self._supported_table_name(table_name)
            if not actual_table:
                return self._format_response(False, error=f"Table '{table_name}' is not supported for inserts")

            if actual_table == 'clients':
                proposed_name = str(row_data.get('name') or row_data.get('Name') or '').strip()
                if not proposed_name:
                    return self._format_response(False, error="Client name is required")

                add_response = self.add_client({'name': proposed_name})
                if not add_response.get('success', False):
                    return add_response

                if client_id := add_response.get('data', {}).get('id'):
                    try:
                        client_bytes = bytes.fromhex(client_id)
                        if refreshed_row := self.db_manager.get_row_by_primary_key('clients', 'ID', client_bytes):
                            return self._format_response(True, refreshed_row)
                    except ValueError:
                        logger.warning("Failed to fetch inserted client row for return payload")
                return add_response

            if actual_table == 'files':
                return self._format_response(False, error="Adding files via GUI is not supported")

            return self._format_response(False, error=f"Table '{table_name}' does not support inserts")
        except Exception as e:
            logger.error(f"Failed to add row to table {table_name}: {e}")
            return self._format_response(False, error=str(e))

    async def update_row_async(self, table_name: str, row_id: str, updated_data: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.update_row, table_name, row_id, updated_data)

    async def delete_row_async(self, table_name: str, row_id: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete_row, table_name, row_id)

    async def add_row_async(self, table_name: str, row_data: dict[str, Any]) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.add_row, table_name, row_data)

    # --- Server Status & Monitoring ---

    def is_connected(self) -> bool:
        """Check if server is connected and operational - required by ServerBridge."""
        try:
            # Server is considered connected if it's running and has a healthy database connection
            if not self.running:
                return False

            # Check database health
            try:
                # Quick database health check
                health = self.db_manager.get_database_health()
                return health.get('integrity_check', False) if isinstance(health, dict) else False
            except Exception:
                return False

        except Exception as e:
            logger.debug(f"is_connected check failed: {e}")
            return False

    def get_server_status(self) -> dict[str, Any]:
        """Get current server status including running state, port, uptime."""
        try:
            uptime = time.time() - self.network_server.start_time if self.running else 0
            status_data = {
                'running': self.running,
                'port': self.port,
                'host': self.network_server.host,
                'uptime_seconds': uptime,
                'uptime_formatted': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
                'version': SERVER_VERSION,
                'last_error': self.network_server.last_error or ''
            }
            return self._format_response(True, status_data)
        except Exception as e:
            logger.error(f"Failed to get server status: {e}")
            return self._format_response(False, error=str(e))

    async def get_server_status_async(self) -> dict[str, Any]:
        """Async version of get_server_status()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_server_status)

    def get_detailed_server_status(self) -> dict[str, Any]:
        """Get comprehensive server metrics including connection stats."""
        try:
            basic_status = self.get_server_status()['data']

            # Get connection statistics
            connection_stats = self.network_server.get_connection_stats()

            # Get client statistics
            with self.clients_lock:
                connected_clients = len(self.clients)

            total_clients = self.db_manager.get_total_clients_count()

            detailed_data = {
                **basic_status,
                'connections': {
                    'active_connections': connection_stats.get('active_connections', connected_clients),
                    'total_connections': connection_stats.get('total_connections', 0),
                    'peak_connections': connection_stats.get('peak_connections', 0)
                },
                'clients': {
                    'connected': connected_clients,
                    'total_registered': total_clients
                },
                'database': {
                    'total_files': self.db_manager.get_total_files_count()
                }
            }

            return self._format_response(True, detailed_data)
        except Exception as e:
            logger.error(f"Failed to get detailed server status: {e}")
            return self._format_response(False, error=str(e))

    async def get_detailed_server_status_async(self) -> dict[str, Any]:
        """Async version of get_detailed_server_status()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_detailed_server_status)

    def get_server_health(self) -> dict[str, Any]:
        """Get server health metrics including connection pool status."""
        try:
            health_data = {
                'status': 'healthy' if self.running else 'stopped',
                'database_accessible': True,  # Basic check
                'network_server_running': self.network_server.running,
                'fletv2_gui_active': True,  # FletV2 GUI is the current interface
                'errors': []
            }

            # Perform basic health checks
            try:
                self.db_manager.get_total_clients_count()
            except Exception as e:
                health_data['database_accessible'] = False
                health_data['errors'].append(f"Database error: {e!s}")
                health_data['status'] = 'unhealthy'

            # Add connection pool metrics if database is accessible
            if health_data['database_accessible']:
                try:
                    # Check if connection_pool exists
                    pool = self.db_manager.connection_pool
                    if pool:

                        pool_status = pool.get_pool_status()
                        health_data['connection_pool'] = {
                            'active': pool_status.get('active_connections', 0),
                            'available': pool_status.get('available_connections', 0),
                            'total': pool_status.get('total_connections', 0),
                            'peak_active': pool_status.get('peak_active_connections', 0),
                            'exhaustion_events': pool_status.get('pool_exhaustion_events', 0),
                            'cleanup_thread_alive': pool_status.get('cleanup_thread_alive', False)
                        }

                        # Check for pool exhaustion issues
                        if pool_status.get('pool_exhaustion_events', 0) > 0:
                            health_data['errors'].append(
                                f"Connection pool exhausted {pool_status['pool_exhaustion_events']} times"
                            )
                            if health_data['status'] == 'healthy':
                                health_data['status'] = 'degraded'

                        # Check cleanup thread health
                        if not pool_status.get('cleanup_thread_alive', False):
                            health_data['errors'].append("Connection pool cleanup thread is dead")
                            if health_data['status'] == 'healthy':
                                health_data['status'] = 'degraded'

                        # Check for emergency connection leaks
                        leak_count = len(pool.emergency_connections)
                        if leak_count > 0:
                            health_data['errors'].append(f"{leak_count} emergency connections leaked")
                            if health_data['status'] == 'healthy':
                                health_data['status'] = 'degraded'
                    else:
                        # Connection pool not available or incomplete
                        health_data['connection_pool'] = {'status': 'unavailable'}

                except Exception as pool_err:
                    logger.debug(f"Could not get connection pool metrics: {pool_err}")
                    health_data['connection_pool'] = {'error': str(pool_err)}

            return self._format_response(True, health_data)
        except Exception as e:
            logger.error(f"Failed to get server health: {e}")
            return self._format_response(False, error=str(e))

    async def get_server_health_async(self) -> dict[str, Any]:
        """Async version of get_server_health()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_server_health)

    def start_server(self) -> dict[str, Any]:
        """Start the server (wrapper for existing start method)."""
        try:
            if self.running:
                return self._format_response(False, error="Server is already running")

            self.start()
            return self._format_response(True, {'started': True})
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return self._format_response(False, error=str(e))

    async def start_server_async(self) -> dict[str, Any]:
        """Async version of start_server()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.start_server)

    def stop_server(self) -> dict[str, Any]:
        """Stop the server (wrapper for existing stop method)."""
        try:
            if not self.running:
                return self._format_response(False, error="Server is not running")

            self.stop()
            return self._format_response(True, {'stopped': True})
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            return self._format_response(False, error=str(e))

    async def stop_server_async(self) -> dict[str, Any]:
        """Async version of stop_server()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.stop_server)

    def test_connection(self) -> dict[str, Any]:
        """Test server connection status."""
        try:
            test_data = {
                'server_accessible': self.running,
                'database_accessible': True,
                'response_time_ms': None
            }

            # Basic database connectivity test
            start_time = time.perf_counter()
            try:
                self.db_manager.get_total_clients_count()
                test_data['response_time_ms'] = round((time.perf_counter() - start_time) * 1000, 2)
            except Exception as e:
                test_data['database_accessible'] = False
                test_data['database_error'] = str(e)

            return self._format_response(True, test_data)
        except Exception as e:
            logger.error(f"Failed to test connection: {e}")
            return self._format_response(False, error=str(e))

    async def test_connection_async(self) -> dict[str, Any]:
        """Async version of test_connection()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.test_connection)

    # --- Analytics & System ---

    def get_system_status(self) -> dict[str, Any]:
        """Get system-level status information."""
        try:
            import psutil
            system_data = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
                'python_version': sys.version.split()[0],
                'platform': sys.platform
            }
            return self._format_response(True, system_data)
        except ImportError:
            # Fallback if psutil is not available
            system_data = {
                'python_version': sys.version.split()[0],
                'platform': sys.platform,
                'note': 'Limited system info available (psutil not installed)'
            }
            return self._format_response(True, system_data)
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return self._format_response(False, error=str(e))

    async def get_system_status_async(self) -> dict[str, Any]:
        """Async version of get_system_status()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_system_status)

    def get_analytics_data(self) -> dict[str, Any]:
        """Get analytics information."""
        try:
            total_files = self.db_manager.get_total_files_count()
            # Prefer verified-only aggregates for real storage and average size
            total_bytes = self.db_manager.get_total_storage_bytes(True)
            avg_bytes = self.db_manager.get_average_backup_size_bytes(True)

            # Fallbacks: if verified-only produce zero on small datasets, try all files via storage statistics
            if (not total_bytes) or (not avg_bytes):
                try:
                    storage_stats = self.db_manager.get_storage_statistics()
                    fs = (storage_stats or {}).get('file_stats') or {}
                    si = (storage_stats or {}).get('storage_info') or {}
                    if not total_bytes:
                        # file_stats.total_size_gb → convert back to bytes if present
                        total_size_gb = fs.get('total_size_gb')
                        if isinstance(total_size_gb, (int, float)) and total_size_gb > 0:
                            total_bytes = int(total_size_gb * 1024 * 1024 * 1024)
                        else:
                            total_size_mb_val = si.get('total_size_mb')
                            if isinstance(total_size_mb_val, (int, float)) and total_size_mb_val > 0:
                                total_bytes = int(float(total_size_mb_val) * 1024 * 1024)
                    if not avg_bytes:
                        avg_mb = fs.get('average_file_size_mb')
                        if isinstance(avg_mb, (int, float)) and avg_mb > 0:
                            avg_bytes = float(avg_mb) * 1024 * 1024
                        else:
                            # Try deriving from filesystem directory size / file count
                            total_size_mb_val = si.get('total_size_mb')
                            total_files_fs = si.get('total_files')
                            if isinstance(total_size_mb_val, (int, float)) and isinstance(total_files_fs, int) and total_files_fs > 0:
                                avg_bytes = (float(total_size_mb_val) / float(total_files_fs)) * 1024 * 1024
                except Exception:
                    # Last resort: leave zeros
                    pass

            # Calculate success rate from verified files
            verified_count = 0
            with contextlib.suppress(Exception):
                all_files = self.db_manager.get_all_files()
                verified_count = sum(f.get('verified', False) for f in all_files)
            success_rate = (verified_count / total_files * 100.0) if total_files > 0 else 100.0

            # Get client storage breakdown
            client_storage = []
            with contextlib.suppress(Exception):
                all_files = self.db_manager.get_all_files()
                # Group files by client and calculate storage
                client_stats = {}
                for f in all_files:
                    client_name = f.get('client', 'Unknown')
                    if client_name not in client_stats:
                        client_stats[client_name] = {'size': 0, 'count': 0}
                    client_stats[client_name]['size'] += f.get('size', 0) or 0
                    client_stats[client_name]['count'] += 1

                # Sort by storage size and take top 10
                sorted_clients = sorted(client_stats.items(), key=lambda x: x[1]['size'], reverse=True)[:10]
                client_storage = [{
                    'client': name[:20],
                    'storage_gb': round(stats['size'] / (1024 * 1024 * 1024), 3) if stats['size'] else 0.0,
                    'file_count': stats['count']
                } for name, stats in sorted_clients]

            # Get file type distribution
            file_type_distribution = []
            with contextlib.suppress(Exception):
                all_files = self.db_manager.get_all_files()
                type_counts = {}
                for f in all_files:
                    filename = f.get('filename', '')
                    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'no_ext'
                    ext = ext[:10]  # Limit extension length
                    type_counts[ext] = type_counts.get(ext, 0) + 1

                # Top 8 file types
                sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:8]
                file_type_distribution = [{'type': t, 'count': c} for t, c in sorted_types]

            # Generate backup trend (last 7 days simulated from current data)
            backup_trend = []
            with contextlib.suppress(Exception):
                from datetime import timedelta
                import random
                files_per_day = max(1, total_files // 7) if total_files > 0 else 0
                for i in range(7):
                    date = (datetime.now() - timedelta(days=6-i)).strftime('%m/%d')
                    # Simulate variation: ±20% around average
                    count = int(files_per_day * random.uniform(0.8, 1.2))
                    backup_trend.append({'date': date, 'count': count})

            analytics_data = {
                'total_clients': self.db_manager.get_total_clients_count(),
                'total_files': total_files,
                'server_uptime_seconds': time.time() - self.network_server.start_time if self.running else 0,
                'database_stats': self.db_manager.get_database_stats(),
                # New canonical analytics fields for UI
                'total_storage_bytes': total_bytes,
                'avg_backup_size_bytes': avg_bytes,
                # Back-compat convenience (GB values)
                'total_storage_gb': round(float(total_bytes) / (1024 * 1024 * 1024), 2) if total_bytes else 0.0,
                'avg_backup_size_gb': round(float(avg_bytes) / (1024 * 1024 * 1024), 2) if avg_bytes else 0.0,
                # Rich visualization data
                'success_rate': round(success_rate, 1),
                'backup_trend': backup_trend,
                'client_storage': client_storage,
                'file_type_distribution': file_type_distribution,
            }
            return self._format_response(True, analytics_data)
        except Exception as e:
            logger.error(f"Failed to get analytics data: {e}")
            return self._format_response(False, error=str(e))

    async def get_analytics_data_async(self) -> dict[str, Any]:
        """Async version of get_analytics_data()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_analytics_data)

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance data with real system metrics."""
        try:
            metrics_data = {
                'active_connections': len(self.clients),
                'database_response_time_ms': 0,
                'memory_usage_mb': 0.0,
                'cpu_usage_percent': 0.0
            }

            # Test database response time
            start_time = time.time()
            try:
                self.db_manager.get_total_clients_count()
                metrics_data['database_response_time_ms'] = int((time.time() - start_time) * 1000)
            except Exception:
                metrics_data['database_response_time_ms'] = -1

            # Get real system metrics
            try:
                import psutil
                process = psutil.Process(os.getpid())

                # Memory usage in MB
                memory_info = process.memory_info()
                metrics_data['memory_usage_mb'] = round(memory_info.rss / (1024 * 1024), 2)

                # CPU usage percent (non-blocking, interval=None uses cached value)
                metrics_data['cpu_usage_percent'] = round(process.cpu_percent(interval=None), 2)

            except ImportError:
                logger.debug("psutil not available, system metrics unavailable")
                # Leave as 0 if psutil not installed
            except Exception as e:
                logger.warning(f"Failed to get system metrics: {e}")
                # Leave as 0 on error

            return self._format_response(True, metrics_data)
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return self._format_response(False, error=str(e))

    async def get_performance_metrics_async(self) -> dict[str, Any]:
        """Async version of get_performance_metrics()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_performance_metrics)

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get dashboard data."""
        try:
            dashboard_data = {
                'server_status': 'running' if self.running else 'stopped',
                'total_clients': self.db_manager.get_total_clients_count(),
                'connected_clients': len(self.clients),
                'total_files': self.db_manager.get_total_files_count(),
                'server_version': SERVER_VERSION,
                'uptime': time.time() - self.network_server.start_time if self.running else 0
            }
            return self._format_response(True, dashboard_data)
        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            return self._format_response(False, error=str(e))

    async def get_dashboard_summary_async(self) -> dict[str, Any]:
        """Async version of get_dashboard_summary()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_dashboard_summary)

    def get_server_statistics(self) -> dict[str, Any]:
        """Get detailed statistics."""
        try:
            stats_data = {
                'server': {
                    'version': SERVER_VERSION,
                    'running': self.running,
                    'uptime_seconds': time.time() - self.network_server.start_time if self.running else 0,
                    'port': self.port
                },
                'clients': {
                    'total_registered': self.db_manager.get_total_clients_count(),
                    'currently_connected': len(self.clients)
                },
                'files': {
                    'total_files': self.db_manager.get_total_files_count()
                },
                'database': self.db_manager.get_database_stats()
            }
            return self._format_response(True, stats_data)
        except Exception as e:
            logger.error(f"Failed to get server statistics: {e}")
            return self._format_response(False, error=str(e))

    async def get_server_statistics_async(self) -> dict[str, Any]:
        """Async version of get_server_statistics()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_server_statistics)

    async def get_recent_activity_async(self, limit: int = DEFAULT_ACTIVITY_LIMIT) -> dict[str, Any]:
        """
        Get recent system activity from server logs.

        Args:
            limit: Maximum number of activity entries to return (default 50)

        Returns:
            dict: {'success': bool, 'data': list[dict], 'error': str}
                Each activity dict contains:
                - 'timestamp': ISO timestamp string
                - 'type': Activity type (info/warning/error/client/file)
                - 'message': Human-readable message
                - 'details': Optional additional context
        """

        try:
            # Run log parsing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            activities = await loop.run_in_executor(None, self._parse_recent_logs, limit)

            return self._format_response(True, activities)
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return self._format_response(False, error=str(e))

    def _parse_recent_logs(self, limit: int) -> list[dict[str, Any]]:
        """
        Parse recent log entries into structured activity records.

        Args:
            limit: Maximum number of entries to return

        Returns:
            list: Activity records sorted by timestamp (most recent first)
        """
        activities = []

        # Determine which log file to read
        log_file = self.backup_log_file
        if not log_file or not os.path.exists(log_file):
            log_file = SERVER_LOG_FILENAME

        if not os.path.exists(log_file):
            logger.warning(f"Log file not found: {log_file}")
            return []

        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                # Read last N*2 lines (we'll filter and limit after parsing)
                lines = f.readlines()[-(limit * 2):]

            # Parse log format: "timestamp - thread - level - message"
            for line in lines:
                try:
                    parts = line.strip().split(' - ', 3)
                    if len(parts) < 4:
                        continue

                    timestamp_str, thread_name, log_level, message = parts

                    # Determine activity type based on message content
                    activity_type = self._classify_activity(message, log_level)

                    # Skip debug/verbose entries unless specifically requested
                    if log_level.upper() == 'DEBUG':
                        continue

                    activities.append({
                        'timestamp': timestamp_str,
                        'type': activity_type,
                        'level': log_level.upper(),
                        'message': message,
                        'thread': thread_name
                    })

                except (ValueError, IndexError) as e:
                    # Skip malformed log lines
                    logger.debug(f"Skipped malformed log line: {e}")
                    continue

            # Sort by timestamp (most recent first) and limit
            activities.reverse()
            return activities[:limit]

        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
            return []

    def _classify_activity(self, message: str, log_level: str) -> str:
        """
        Classify activity type based on message content.

        Args:
            message: Log message text
            log_level: Log level (INFO/WARNING/ERROR)

        Returns:
            str: Activity type (client/file/server/error/warning/info)
        """
        message_lower = message.lower()

        # Client-related activities
        if any(keyword in message_lower for keyword in ['client', 'connected', 'disconnected', 'registered']):
            return 'client'

        # File-related activities
        if any(keyword in message_lower for keyword in ['file', 'upload', 'backup', 'download', 'verified']):
            return 'file'

        # Server-related activities
        if any(keyword in message_lower for keyword in ['server', 'started', 'stopped', 'shutdown', 'startup']):
            return 'server'

        # Error/warning based on log level
        if log_level.upper() == 'ERROR':
            return 'error'
        if log_level.upper() == 'WARNING':
            return 'warning'

        # Default
        return 'info'

    def get_historical_data(self, metric: str = "connections", hours: int = 24) -> dict[str, Any]:
        """
        Get historical data for metrics from persistent storage.

        Retrieves time-series metrics data from the metrics_history database table.
        Metrics are automatically collected every maintenance cycle (default: 20 seconds).

        Args:
            metric: Metric type to retrieve ("connections", "files", or "bandwidth")
            hours: Number of hours of history (1-168, max 1 week)

        Returns:
            dict: {'success': bool, 'data': dict with 'points': [{'timestamp': str, 'value': float}], 'error': str}
        """
        try:
            # Validate metric parameter
            VALID_METRICS = {"connections", "files", "bandwidth"}
            if metric not in VALID_METRICS:
                return self._format_response(
                    False,
                    error=f"Invalid metric '{metric}'. Supported metrics: {sorted(VALID_METRICS)}"
                )

            # Validate hours parameter
            if not isinstance(hours, int) or hours < 1 or hours > 168:  # Max 1 week
                return self._format_response(
                    False,
                    error="Hours must be an integer between 1 and 168 (1 week maximum)"
                )

            # Retrieve real historical data from database
            points = self.db_manager.get_metrics_history(metric, hours)

            # If no data available, return empty points with note
            if not points:
                logger.debug(f"No historical data available for metric '{metric}' (last {hours} hours)")
                return self._format_response(
                    True,
                    {
                        'points': [],
                        'note': f'No data yet. Metrics recorded every {MAINTENANCE_INTERVAL:.0f} seconds starting from server start. First data point will appear in {MAINTENANCE_INTERVAL:.0f}s.'
                    }
                )

            logger.debug(f"Retrieved {len(points)} historical data points for '{metric}' (last {hours} hours)")
            return self._format_response(True, {'points': points})

        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return self._format_response(False, error=str(e))

    async def get_historical_data_async(self, metric: str = "connections", hours: int = 24) -> dict[str, Any]:
        """Async version of get_historical_data()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_historical_data, metric, hours)

    # --- Log Operations ---

    def _read_log_file(self, filepath: str, limit: int = DEFAULT_LOG_LINES_LIMIT) -> list[str]:
        """
        Read last N lines from a log file.

        Args:
            filepath: Path to the log file
            limit: Maximum number of lines to return

        Returns:
            List of log lines (stripped), or empty list if file doesn't exist
        """
        if not os.path.exists(filepath):
            return []

        try:
            with open(filepath, encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                return [line.strip() for line in recent_lines]
        except Exception as e:
            logger.debug(f"Error reading log file '{filepath}': {e}")
            return []

    def get_logs(self) -> dict[str, Any]:
        """Get system logs (enhanced to include multiple log files)."""
        try:
            all_logs = []
            current_log_path = None

            # Get primary log file
            log_paths = [
                self.backup_log_file,  # Instance variable
                backup_log_file,  # Module variable
                SERVER_LOG_FILENAME  # Fallback
            ]

            # Read from current log file (NO BREAK - removed to allow multi-file aggregation)
            for log_path in log_paths:
                if log_path and os.path.exists(log_path):  # Skip None values and check existence
                    if logs := self._read_log_file(log_path, limit=500):  # Increased limit
                        all_logs.extend(logs)
                        current_log_path = os.path.abspath(log_path)  # Store absolute path
                        break  # Only read from ONE current log file

            # Also try to read from rotated log files in logs/ directory
            import glob
            logs_dir = os.path.dirname(self.backup_log_file)
            if not logs_dir or not os.path.exists(logs_dir):
                logs_dir = 'logs'  # Fallback to default logs directory

            if os.path.exists(logs_dir):
                # Find all backup-server_*.log files and sort by modification time (newest first)
                log_files = glob.glob(os.path.join(logs_dir, 'backup-server_*.log'))
                log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

                # Read from up to 5 most recent log files (excluding current one already read)
                for log_file in log_files[:5]:
                    abs_log_file = os.path.abspath(log_file)
                    # Skip the current log file (already read above)
                    if current_log_path and abs_log_file == current_log_path:
                        continue
                    if rotated_logs := self._read_log_file(log_file, limit=100):
                        all_logs.extend(rotated_logs)

            log_data = {
                'logs': all_logs,
                'count': len(all_logs),
                'note': f'Retrieved {len(all_logs)} log entries from current and {len(log_files[:5]) if "log_files" in locals() else 0} historical log files'
            }

            return self._format_response(True, log_data)
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return self._format_response(False, error=str(e))

    async def get_logs_async(self) -> dict[str, Any]:
        """Async version of get_logs()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_logs)

    async def clear_logs_async(self) -> dict[str, Any]:
        """
        Rotate/clear system logs safely by moving current logs to archive.

        Instead of deleting logs, this creates a backup and starts fresh log files.
        """
        try:

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._rotate_logs_sync)
        except Exception as e:
            logger.error(f"Failed to clear/rotate logs: {e}")
            return self._format_response(False, error=str(e))

    def _rotate_logs_sync(self) -> dict[str, Any]:
        """Synchronous log rotation implementation."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_files = []

            # Rotate enhanced log file
            if os.path.exists(self.backup_log_file):
                archive_name = f"{self.backup_log_file}.{timestamp}"
                try:
                    os.rename(self.backup_log_file, archive_name)
                    rotated_files.append(archive_name)
                    logger.info(f"Rotated enhanced log to: {archive_name}")
                except OSError as e:
                    logger.warning(f"Could not rotate enhanced log: {e}")

            # Rotate legacy server.log
            if os.path.exists(SERVER_LOG_FILENAME):
                archive_name = f"{SERVER_LOG_FILENAME}.{timestamp}"
                try:
                    os.rename(SERVER_LOG_FILENAME, archive_name)
                    rotated_files.append(archive_name)
                    logger.info(f"Rotated server log to: {archive_name}")
                except OSError as e:
                    logger.warning(f"Could not rotate server.log: {e}")

            if rotated_files:
                return self._format_response(True, {
                    'rotated': True,
                    'archived_files': rotated_files,
                    'timestamp': timestamp
                })
            else:
                return self._format_response(False, error="No log files found to rotate")

        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
            return self._format_response(False, error=str(e))

    async def export_logs_async(self, export_format: str = "text", filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Export logs with optional filtering to a file.

        Args:
            export_format: Format for export ("text", "json", "csv")
            filters: Optional filters dict with keys:
                - 'level': Minimum log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
                - 'start_date': Start date for log entries (ISO format)
                - 'end_date': End date for log entries (ISO format)
                - 'search_term': Search term to filter messages
                - 'limit': Maximum number of entries (default: 1000)

        Returns:
            dict: {'success': bool, 'data': dict with 'file_path' and 'entries_exported', 'error': str}
        """
        try:
            import json

            # Rate limiting check (10 second minimum interval)
            session_key = "global"  # Global rate limit for now
            with self._log_export_lock:
                current_time = time.time()
                last_export = self._last_log_export_time.get(session_key, 0)

                if current_time - last_export < 10:  # 10 second minimum interval
                    remaining = 10 - (current_time - last_export)
                    return self._format_response(
                        False,
                        error=f"Rate limit exceeded. Please wait {remaining:.1f} seconds before exporting again."
                    )

                self._last_log_export_time[session_key] = current_time

            normalized_format = (export_format or "").lower()
            if normalized_format not in VALID_LOG_EXPORT_FORMATS:
                return self._format_response(
                    False,
                    error=f"Invalid format. Supported formats: {sorted(VALID_LOG_EXPORT_FORMATS)}"
                )

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._export_logs_sync, normalized_format, filters or {})
        except Exception as e:
            logger.error(f"Failed to export logs: {e}")
            return self._format_response(False, error=str(e))

    def _export_logs_sync(self, export_format: str, filters: dict[str, Any]) -> dict[str, Any]:
        """Synchronous log export implementation."""
        import json

        try:
            # Determine log file to read
            log_file = self.backup_log_file
            if not log_file or not os.path.exists(log_file):
                log_file = SERVER_LOG_FILENAME

            if not os.path.exists(log_file):
                return self._format_response(False, error="Log file not found")

            # Check file size to prevent hang on huge logs
            try:
                file_size = os.path.getsize(log_file)
                if file_size > MAX_LOG_EXPORT_SIZE:
                    size_mb = file_size / (1024 * 1024)
                    max_mb = MAX_LOG_EXPORT_SIZE / (1024 * 1024)
                    return self._format_response(
                        False,
                        error=f"Log file too large ({size_mb:.1f} MB). Maximum: {max_mb:.0f} MB"
                    )
            except OSError as size_err:
                logger.warning(f"Could not check log file size: {size_err}")
                # Continue anyway - file exists, so size check failure shouldn't block export

            # Extract filter parameters
            level_filter = filters.get('level', '').upper()
            start_date = filters.get('start_date', '')
            end_date = filters.get('end_date', '')
            search_term = filters.get('search_term', '').lower()
            limit = filters.get('limit', 1000)

            # Read and filter log entries
            filtered_entries: list[str] = []
            lines_read = 0
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        lines_read += 1

                        # Hard cap on total lines read to prevent processing huge files
                        if lines_read > MAX_LOG_EXPORT_LINES:
                            logger.warning(
                                f"Log export stopped at {MAX_LOG_EXPORT_LINES} lines. "
                                f"File has more lines, use more specific filters."
                            )
                            break

                        stripped = line.strip()
                        if not stripped:
                            continue
                        lower_line = stripped.lower()
                        if level_filter and level_filter not in line:
                            continue
                        if search_term and search_term not in lower_line:
                            continue
                        # (Date filtering simplified for now)
                        filtered_entries.append(stripped)
                        if len(filtered_entries) >= limit:
                            break
            except Exception as read_exc:
                return self._format_response(False, error=f"Error reading log file: {read_exc}")

            # Generate export filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"logs_export_{timestamp}.{export_format}"

            # Export based on format
            try:
                if export_format == "json":
                    # Export as JSON array
                    log_entries = []
                    for line in filtered_entries:
                        parts = line.split(' - ', 3)
                        if len(parts) >= 4:
                            log_entries.append({
                                'timestamp': parts[0],
                                'thread': parts[1],
                                'level': parts[2],
                                'message': parts[3]
                            })
                        else:
                            log_entries.append({'raw': line})

                    with open(export_filename, 'w', encoding='utf-8') as f:
                        json.dump(log_entries, f, indent=2, ensure_ascii=False)

                elif export_format == "csv":
                    import csv
                    with open(export_filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Timestamp', 'Thread', 'Level', 'Message'])
                        for entry in filtered_entries:
                            parts = entry.split(' - ', 3)
                            writer.writerow(parts if len(parts) >= 4 else ['', '', '', entry])
                else:  # text format (default)
                    with open(export_filename, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(filtered_entries) + ('\n' if filtered_entries else ''))

                logger.info(f"Logs exported to {export_filename}: {len(filtered_entries)} entries")
                return self._format_response(True, {
                    'exported': True,
                    'file_path': os.path.abspath(export_filename),
                    'entries_exported': len(filtered_entries),
                    'format': export_format,
                    'filters_applied': filters
                })

            except Exception as e:
                return self._format_response(False, error=f"Error writing export file: {e}")

        except Exception as e:
            logger.error(f"Log export failed: {e}")
            return self._format_response(False, error=str(e))

    # --- Settings Management ---

    def _validate_settings(self, settings: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate settings structure and value ranges.

        Args:
            settings: Settings dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Define settings schema with (type, min_value, max_value) or (type, allowed_values)
        SETTINGS_SCHEMA = {
            # Server settings (int with ranges)
            'server_port': (int, 1024, 65535),
            'max_concurrent_clients': (int, 1, 1000),
            'client_timeout': (int, 60, 7200),  # 1 min to 2 hours

            # Interface settings (str with allowed values)
            'theme': (str, ['light', 'dark', 'system']),
            'language': (str, ['en', 'es', 'fr', 'de', 'zh']),

            # Monitoring settings
            'enable_monitoring': (bool,),
            'metrics_retention_days': (int, 1, 365),

            # Logging settings
            'log_level': (str, ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
            'log_to_file': (bool,),
            'log_rotation_size_mb': (int, 1, 1000),

            # Security settings
            'encryption_enabled': (bool,),
            'key_size': (int, [1024, 2048, 4096]),  # Only specific key sizes

            # Backup settings
            'auto_backup_interval': (int, 300, 86400),  # 5 min to 24 hours
            'backup_retention_days': (int, 1, 3650),  # 1 day to 10 years
            'compression_enabled': (bool,)
        }

        for key, value in settings.items():
            # Skip unknown keys (forward compatibility)
            if key not in SETTINGS_SCHEMA:
                continue

            schema = SETTINGS_SCHEMA[key]
            expected_type = schema[0]

            # Type validation
            if not isinstance(value, expected_type):
                return False, f"Invalid type for '{key}': expected {expected_type.__name__}, got {type(value).__name__}"

            # Range/enum validation
            if expected_type == int and len(schema) == 3:
                min_val, max_val = schema[1], schema[2]
                if not (min_val <= value <= max_val):
                    return False, f"Value for '{key}' out of range: must be between {min_val} and {max_val}, got {value}"

            elif expected_type == str and len(schema) == 2:
                allowed_values = schema[1]
                if value not in allowed_values:
                    return False, f"Invalid value for '{key}': must be one of {allowed_values}, got '{value}'"

            elif expected_type == int and len(schema) == 2 and isinstance(schema[1], list):
                allowed_values = schema[1]
                if value not in allowed_values:
                    return False, f"Invalid value for '{key}': must be one of {allowed_values}, got {value}"

        return True, ""

    def save_settings(self, settings_data: dict[str, Any]) -> dict[str, Any]:
        """
        Save application settings to JSON file.

        Args:
            settings_data: Dictionary containing all settings to save

        Returns:
            dict: {'success': bool, 'data': dict, 'error': str}
        """
        try:
            import json

            # Validate settings structure
            if not isinstance(settings_data, dict):
                return self._format_response(False, error="Settings must be a dictionary")

            # Validate settings values
            is_valid, error_msg = self._validate_settings(settings_data)
            if not is_valid:
                logger.warning(f"Settings validation failed: {error_msg}")
                return self._format_response(False, error=f"Invalid settings: {error_msg}")

            # Add metadata
            settings_with_metadata = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'server_version': SERVER_VERSION,
                'settings': settings_data
            }

            # Write to file with atomic operation (write to temp, then rename)
            temp_file = f"{SETTINGS_FILE}.tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(settings_with_metadata, f, indent=2, ensure_ascii=False)

                # Atomic rename
                if os.path.exists(SETTINGS_FILE):
                    os.replace(temp_file, SETTINGS_FILE)
                else:
                    os.rename(temp_file, SETTINGS_FILE)

                logger.info(f"Settings saved successfully to {SETTINGS_FILE}")
                return self._format_response(True, {
                    'saved': True,
                    'file': SETTINGS_FILE,
                    'timestamp': settings_with_metadata['saved_at']
                })

            finally:
                # Clean up temp file if it still exists
                with contextlib.suppress(OSError):
                    os.remove(temp_file)

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return self._format_response(False, error=str(e))

    async def save_settings_async(self, settings_data: dict[str, Any]) -> dict[str, Any]:
        """Async version of save_settings()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.save_settings, settings_data)

    def load_settings(self) -> dict[str, Any]:
        """
        Load application settings from JSON file.

        Returns:
            dict: {'success': bool, 'data': dict, 'error': str}
                If file doesn't exist, returns default settings
        """
        try:
            import json

            # Return defaults if no saved settings exist
            if not os.path.exists(SETTINGS_FILE):
                default_settings = self._get_default_settings()
                return self._format_response(True, default_settings)

            # Read settings file
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings_with_metadata = json.load(f)

            # Validate structure
            if not isinstance(settings_with_metadata, dict):
                logger.warning("Invalid settings file format, returning defaults")
                return self._format_response(True, self._get_default_settings())

            # Extract settings (handle both old and new format)
            if 'settings' in settings_with_metadata:
                settings = settings_with_metadata['settings']
            else:
                # Old format - entire file is settings
                settings = settings_with_metadata

            # Merge with defaults to ensure all keys exist
            default_settings = self._get_default_settings()
            merged_settings = {**default_settings, **settings}

            # Validate loaded settings
            is_valid, error_msg = self._validate_settings(merged_settings)
            if not is_valid:
                logger.warning(f"Invalid settings in file, using defaults: {error_msg}")
                return self._format_response(True, default_settings)

            logger.info(f"Settings loaded successfully from {SETTINGS_FILE}")
            return self._format_response(True, merged_settings)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse settings file: {e}")
            return self._format_response(False, error=f"Invalid JSON in settings file: {e}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return self._format_response(False, error=str(e))

    def _get_default_settings(self) -> dict[str, Any]:
        """
        Get default server settings.

        Returns:
            dict: Default settings structure matching FletV2/views/settings.py expectations
        """
        return {
            # Server settings
            'server_port': self.port,
            'max_concurrent_clients': MAX_CONCURRENT_CLIENTS,
            'client_timeout': CLIENT_SESSION_TIMEOUT,

            # Interface settings
            'theme': 'dark',
            'language': 'en',

            # Monitoring settings
            'enable_monitoring': True,
            'metrics_retention_days': 30,

            # Logging settings
            'log_level': 'INFO',
            'log_to_file': True,
            'log_rotation_size_mb': 10,

            # Security settings
            'encryption_enabled': True,
            'key_size': 1024,

            # Backup settings
            'auto_backup_interval': 3600,
            'backup_retention_days': 90,
            'compression_enabled': True
        }

    async def load_settings_async(self) -> dict[str, Any]:
        """Async version of load_settings()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load_settings)


# --- Main Execution Guard ---
if __name__ == "__main__":
    server_instance = None  # Initialize to ensure it's always bound
    try:
        # Display a startup banner for the server console
        print("=====================================================================")
        print(f"      Secure Encrypted File Backup Server - Version {SERVER_VERSION}      ")
        print(f"      Process ID: {os.getpid()}                                     ")
        print("=====================================================================")

        # Display logging information
        try:
            log_monitor_info = create_log_monitor_info(backup_log_file, "Backup Server")
            print("Logging Information:")
            print(f"  Enhanced Log: {log_monitor_info['file_path']}")
            print(f"  Legacy Log:   {os.path.abspath(SERVER_LOG_FILENAME)}")
            print(f"  Live Monitor: {log_monitor_info['powershell_cmd']}")
            print("  Console:      Visible in this window (dual output enabled)")
            print("=====================================================================")
        except Exception as e:
            print(f"  [WARNING] Could not display logging info: {e}")
            print("=====================================================================")

        # Perform basic pre-flight checks before attempting to start the server
        if sys.version_info < (3, 7): # PyCryptodome generally works better with Python 3.7+
            print("Warning: Python 3.7 or newer is recommended for optimal server performance and security library compatibility.", file=sys.stderr)

        # Quick check to ensure PyCryptodome is available and basic operations work
        try:
            # Test RSA key generation functionality
            RSA.generate(1024, randfunc=get_random_bytes)
            # Test AES cipher creation functionality
            AES.new(get_random_bytes(AES_KEY_SIZE_BYTES), AES.MODE_CBC, iv=get_random_bytes(16))  # type: ignore[misc]
            logger.info("PyCryptodome library check passed: Basic crypto operations are available.")
        except Exception as e_crypto_check:
            print(f"CRITICAL FAILURE: PyCryptodome library is not installed correctly or is non-functional: {e_crypto_check}", file=sys.stderr)
            print("Please ensure PyCryptodome is properly installed (e.g., via 'pip install pycryptodomex'). Server cannot start.", file=sys.stderr)
            sys.exit(1) # Exit if essential crypto library is missing/broken

        logger.info("Verifying cryptography library availability...")
        # Ensure only one server instance runs at a time
        logger.info("Ensuring single server instance...")
        ensure_single_server_instance("BackupServer", 1256)

        # Instantiate the server
        logger.info("Creating BackupServer instance...")
        server_instance = BackupServer()
        logger.info("BackupServer instance created successfully")

        # Legacy GUIManager removed - FletV2 GUI is now used instead
        # The main thread can now wait for a shutdown signal or simply keep alive.
        # FletV2 GUI handles user interaction through the ServerBridge pattern.

        # Skip legacy GUI initialization - FletV2 GUI is launched separately
        logger.info("Skipping legacy GUI initialization - FletV2 GUI is used instead")
        gui_ready = False  # Legacy GUI not applicable
        logger.info("Proceeding without legacy GUI integration")

        # Start the server
        logger.info("Starting backup server on port 1256...")
        server_instance.start()
        logger.info("Backup server started successfully")

        # Console-only mode - FletV2 GUI runs separately
        logger.info("Server running in headless mode. FletV2 GUI launched separately via start_with_server.py")
        while server_instance.running and not server_instance.shutdown_event.is_set():
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected in main execution block. Initiating shutdown.")
    except SystemExit as e_sys_exit:
        logger.critical(f"Server startup process was aborted: {e_sys_exit}")
    except Exception as e_main_fatal:
        logger.critical(f"Server encountered a fatal unhandled exception in main execution: {e_main_fatal}", exc_info=True)
    finally:
        if server_instance:
            logger.info("Ensuring server shutdown is called from __main__ 'finally' block...")
            server_instance.stop()

        logger.info("Server application has completed its full termination sequence.")
        print("Server shutdown process complete. Exiting.")
