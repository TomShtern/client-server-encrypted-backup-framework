# database.py
# Database operations module for the Secure File Transfer System
# Extracted from monolithic server.py for better modularity and maintainability
#
# This module provides a DatabaseManager class that handles all SQLite database
# operations for the backup server, including:
# - Client registration and persistence
# - File upload record management
# - Database schema initialization
# - Startup permission checks
#
# Usage:
#   from database import DatabaseManager
#   db_manager = DatabaseManager()
#   db_manager.init_database()
#   db_manager.save_client_to_db(client_id, name, public_key, aes_key)

import logging
import os
import queue
import sqlite3
import threading
import time
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Import configuration constants
from .config import DATABASE_NAME, FILE_STORAGE_DIR
from .exceptions import ServerError

# Import observability framework if available
try:
    import sys

    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    from Shared.monitoring.observability import MetricsCollector as _MetricsCollector
    from Shared.monitoring.observability import (
        StructuredLogger as _StructuredLogger,  # type: ignore
    )

    OBSERVABILITY_AVAILABLE = True
    StructuredLogger = _StructuredLogger  # type: ignore
    MetricsCollector = _MetricsCollector  # type: ignore
except ImportError:
    OBSERVABILITY_AVAILABLE = False

    # Create stub classes when observability is not available
    class StructuredLogger:
        def __init__(self, name: str, logger: logging.Logger) -> None:
            self.logger = logger

        def info(self, msg: str, **kwargs: Any) -> None:
            self.logger.info(msg)

        def error(self, msg: str, **kwargs: Any) -> None:
            self.logger.error(msg)

        def debug(self, msg: str, **kwargs: Any) -> None:
            self.logger.debug(msg)

    class MetricsCollector:
        def __init__(self) -> None:
            pass

    OBSERVABILITY_AVAILABLE = False

# Setup module logger
logger = logging.getLogger(__name__)

# Initialize observability components if available
if OBSERVABILITY_AVAILABLE:
    try:
        structured_logger = StructuredLogger("database", logger)
        metrics = MetricsCollector()
    except Exception as e:
        logger.warning(f"Failed to initialize observability components: {e}")
        structured_logger = None
        metrics = None
else:
    structured_logger = None
    metrics = None


@dataclass
class ConnectionInfo:
    """
    Information about a database connection for monitoring.

    Note: Uses time.monotonic() for all timestamps to avoid issues with
    system clock changes. Do not mix with time.time() values.
    """

    connection_id: str
    created_time: float  # time.monotonic() timestamp
    last_used_time: float  # time.monotonic() timestamp
    use_count: int = 0
    is_active: bool = True
    thread_id: int | None = None


@dataclass
class PoolMetrics:
    """Database connection pool metrics."""

    total_connections: int = 0
    active_connections: int = 0
    available_connections: int = 0
    connections_created: int = 0
    connections_closed: int = 0
    pool_exhaustion_events: int = 0
    cleanup_operations: int = 0
    average_connection_age: float = 0.0
    peak_active_connections: int = 0
    last_cleanup_time: float = 0.0
    stale_connections_cleaned: int = 0


class DatabaseConnectionPool:
    """
    Enhanced connection pool for SQLite database with comprehensive monitoring and cleanup capabilities.
    """

    def __init__(
        self,
        db_name: str,
        pool_size: int = 5,
        timeout: float = 30.0,
        max_connection_age: float = 3600.0,
        cleanup_interval: float = 300.0,
    ):
        self.db_name = db_name
        self.pool_size = pool_size
        self.timeout = timeout
        self.max_connection_age = (
            max_connection_age  # Max age in seconds (default: 1 hour)
        )
        self.cleanup_interval = (
            cleanup_interval  # Cleanup interval in seconds (default: 5 minutes)
        )

        # Connection pool and monitoring
        self.pool: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.connection_info: dict[
            int, ConnectionInfo
        ] = {}  # connection_id -> ConnectionInfo
        self.emergency_connections: dict[
            int, sqlite3.Connection
        ] = {}  # Track emergency connections separately
        self.metrics = PoolMetrics()

        # Monitoring flags
        self._monitoring_enabled = True
        self._cleanup_thread = None
        self._last_alert_time = 0.0

        # Initialize pool and start monitoring
        self._create_connections()
        self._start_monitoring_thread()

    def _create_connections(self):
        """Create initial pool of database connections with monitoring."""
        for i in range(self.pool_size):
            if conn := self._create_monitored_connection(f"initial_{i}"):
                self.pool.put(conn)
                self.metrics.total_connections += 1
                self.metrics.connections_created += 1

    def _create_monitored_connection(
        self, connection_id: str
    ) -> sqlite3.Connection | None:
        """Create a new database connection with monitoring."""
        try:
            conn = sqlite3.connect(
                self.db_name,
                timeout=10.0,
                check_same_thread=False,  # Allow connection sharing across threads
            )

            # Configure database for better performance while maintaining compatibility
            try:
                result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
                if result and result[0].upper() == "WAL":
                    logger.debug(f"WAL mode enabled for connection {connection_id}")
                else:
                    logger.warning(
                        f"WAL mode not available (got {result[0] if result else 'None'}), using default journaling"
                    )
            except sqlite3.OperationalError as e:
                logger.warning(f"WAL mode failed: {e}, using default journaling")
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety vs performance
            conn.execute("PRAGMA cache_size=10000")  # Increase cache size
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables

            # Add connection monitoring info
            current_time = time.monotonic()
            conn_id = id(conn)
            self.connection_info[conn_id] = ConnectionInfo(
                connection_id=connection_id,
                created_time=current_time,
                last_used_time=current_time,
                thread_id=threading.get_ident(),
            )

            logger.debug(f"Created new database connection: {connection_id}")
            return conn

        except Exception as e:
            logger.error(f"Failed to create database connection {connection_id}: {e}")
            return None

    def _start_monitoring_thread(self):
        """Start background monitoring and cleanup thread with proper management."""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return

        try:
            # Try to use managed thread system
            import os
            import sys

            # Ensure project root is in path (should be handled by top-level, but safe to ensure)
            project_root = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "..",
            )
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            try:
                from Shared.monitoring.thread_manager import create_managed_thread

                def cleanup_database_resources():
                    """Cleanup function for database monitoring resources"""
                    logger.info("Performing database monitoring cleanup...")
                    self._monitoring_enabled = False

                # Create managed thread
                thread_name = create_managed_thread(
                    target=self._monitoring_loop,
                    name=f"database_pool_monitor_{id(self)}",
                    component="database_manager",
                    daemon=True,
                    cleanup_callback=cleanup_database_resources,
                    auto_start=True,
                )

                if thread_name:
                    logger.info(
                        f"Database monitoring thread registered as: {thread_name}"
                    )
                    # Store reference for compatibility
                    self._cleanup_thread = threading.current_thread()  # Placeholder
                else:
                    raise ImportError("Thread manager registration failed")

            except ImportError:
                # Fallback to standard threading
                logger.debug(
                    "Thread manager not available, falling back to basic threading"
                )

                self._cleanup_thread = threading.Thread(
                    target=self._monitoring_loop,
                    name=f"database_pool_monitor_{id(self)}",
                    daemon=True,
                )
                self._cleanup_thread.start()
                logger.info(
                    f"Database monitoring thread started: {self._cleanup_thread.name}"
                )

        except ImportError:
            logger.debug("Thread manager not available, using basic thread management")
            self._cleanup_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="DatabasePoolMonitor"
            )
            self._cleanup_thread.start()
            logger.info("Database connection pool monitoring thread started")

    def _monitoring_loop(self, stop_event: threading.Event | None = None):
        """Background monitoring and cleanup loop with shutdown awareness."""
        logger.info("Database connection pool monitoring loop started")

        while self._monitoring_enabled:
            try:
                # Check for shutdown signal
                if stop_event and stop_event.is_set():
                    logger.info("Database monitoring received shutdown signal")
                    break

                self._perform_cleanup()
                self._update_metrics()
                self._check_pool_health()

                # Sleep with shutdown awareness
                if stop_event:
                    if stop_event.wait(self.cleanup_interval):
                        logger.info(
                            "Database monitoring stopping due to shutdown signal"
                        )
                        break
                else:
                    time.sleep(self.cleanup_interval)

            except Exception as e:
                logger.error(f"Error in connection pool monitoring loop: {e}")

                # Wait before retrying, with shutdown awareness
                if stop_event:
                    if stop_event.wait(30):
                        logger.info(
                            "Database monitoring stopping after error due to shutdown signal"
                        )
                        break
                else:
                    time.sleep(30)

        logger.info("Database connection pool monitoring loop finished")

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool with monitoring."""
        start_time = time.monotonic()

        try:
            conn = self.pool.get(timeout=self.timeout)

            # Validate connection is still alive by pinging it
            try:
                conn.execute("SELECT 1").fetchone()
            except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                logger.warning(
                    f"Connection {id(conn)} is stale or invalid ({e}), recreating"
                )
                self._close_connection_with_tracking(conn, f"Stale connection: {e}")
                # Create a new connection to replace the stale one
                new_conn = self._create_monitored_connection(
                    f"replacement_{int(time.monotonic())}"
                )
                if not new_conn:
                    raise ServerError(
                        "Failed to create replacement database connection"
                    ) from None
                conn = new_conn

            # Update connection tracking
            conn_id = id(conn)
            if conn_id in self.connection_info:
                with self.lock:
                    self.connection_info[conn_id].last_used_time = time.monotonic()
                    self.connection_info[conn_id].use_count += 1
                    self.connection_info[conn_id].thread_id = threading.get_ident()
                    self.metrics.active_connections += 1

                    # Update peak usage
                    if (
                        self.metrics.active_connections
                        > self.metrics.peak_active_connections
                    ):
                        self.metrics.peak_active_connections = (
                            self.metrics.active_connections
                        )

            # Log structured information
            if structured_logger:
                structured_logger.info(  # type: ignore
                    "Database connection acquired",
                    connection_id=conn_id,
                    wait_time_ms=(time.monotonic() - start_time) * 1000,
                    active_connections=self.metrics.active_connections,
                    pool_size=self.pool_size,
                )

            return conn

        except queue.Empty:
            # Pool exhaustion - create emergency connection
            self.metrics.pool_exhaustion_events += 1
            self._handle_pool_exhaustion()

            logger.warning("Connection pool exhausted, creating emergency connection")
            emergency_conn = self._create_monitored_connection(
                f"emergency_{int(time.monotonic())}"
            )

            if not emergency_conn:
                raise ServerError(
                    "Failed to create emergency database connection"
                ) from None

            # Track emergency connection separately for proper cleanup
            conn_id = id(emergency_conn)
            with self.lock:
                self.emergency_connections[conn_id] = emergency_conn
                self.metrics.connections_created += 1

            logger.debug(f"Emergency connection {conn_id} created and tracked")
            return emergency_conn

    def _handle_pool_exhaustion(self):
        """Handle connection pool exhaustion with alerts and cleanup."""
        current_time = time.monotonic()

        # Rate limit alerts (max 1 per minute)
        if current_time - self._last_alert_time > 60:
            self._last_alert_time = current_time

            # Log critical alert
            alert_message = f"Database connection pool exhausted! Pool size: {self.pool_size}, Active: {self.metrics.active_connections}"
            logger.critical(alert_message)

            # Structured logging with detailed context
            if structured_logger:
                structured_logger.error(  # type: ignore
                    "Connection pool exhaustion detected",
                    pool_size=self.pool_size,
                    active_connections=self.metrics.active_connections,
                    available_connections=self.pool.qsize(),
                    exhaustion_events=self.metrics.pool_exhaustion_events,
                    peak_active=self.metrics.peak_active_connections,
                    connection_ages=self._get_connection_ages_summary(),
                )

            # Force cleanup of stale connections
            cleaned = self._force_cleanup_stale_connections()
            if cleaned > 0:
                logger.info(f"Emergency cleanup: removed {cleaned} stale connections")

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool with enhanced stale connection detection."""
        conn_id = id(conn)

        # Check if this is an emergency connection - close instead of returning to pool
        with self.lock:
            if conn_id in self.emergency_connections:
                logger.info(
                    f"Closing emergency connection {conn_id} instead of returning to pool"
                )
                self._close_connection_with_tracking(
                    conn, "Emergency connection cleanup"
                )
                del self.emergency_connections[conn_id]
                return

        try:
            # Enhanced validation - detect stale/locked connections
            try:
                conn.execute("SELECT 1")
            except sqlite3.OperationalError as op_err:
                # Handle database locked or busy scenarios
                if "locked" in str(op_err).lower() or "busy" in str(op_err).lower():
                    logger.warning(
                        f"Connection {conn_id} is locked/busy, closing instead of returning"
                    )
                    self._close_connection_with_tracking(
                        conn, f"Database locked/busy: {op_err}"
                    )
                    return
                raise

            # Check if connection is stale based on age
            if conn_id in self.connection_info:
                current_time = time.monotonic()
                connection_age = (
                    current_time - self.connection_info[conn_id].created_time
                )

                # Close connections older than max age
                if connection_age > self.max_connection_age:
                    logger.debug(
                        f"Connection {conn_id} exceeded max age ({connection_age:.0f}s), closing"
                    )
                    self._close_connection_with_tracking(
                        conn, f"Exceeded max age: {connection_age:.0f}s"
                    )
                    return

                # Update tracking
                with self.lock:
                    self.connection_info[conn_id].last_used_time = current_time
                    self.metrics.active_connections = max(
                        0, self.metrics.active_connections - 1
                    )

            # Return to pool
            self.pool.put_nowait(conn)

            if structured_logger:
                structured_logger.debug(  # type: ignore
                    "Database connection returned to pool",
                    connection_id=conn_id,
                    active_connections=self.metrics.active_connections,
                    available_connections=self.pool.qsize(),
                )

        except (sqlite3.Error, queue.Full) as e:
            # Connection is invalid or pool is full, close it
            self._close_connection_with_tracking(conn, f"Invalid or pool full: {e}")

    def _close_connection_with_tracking(
        self, conn: sqlite3.Connection, reason: str = "Unknown"
    ):
        """Close a connection with proper tracking and logging."""
        conn_id = id(conn)

        try:
            conn.close()

            # Remove from tracking
            if conn_id in self.connection_info:
                with self.lock:
                    del self.connection_info[conn_id]
                    self.metrics.connections_closed += 1
                    self.metrics.active_connections = max(
                        0, self.metrics.active_connections - 1
                    )
                    self.metrics.total_connections = max(
                        0, self.metrics.total_connections - 1
                    )

            logger.debug(f"Closed database connection {conn_id}: {reason}")

        except Exception as e:
            logger.error(f"Error closing database connection {conn_id}: {e}")

    def _perform_cleanup(self):
        """Perform regular cleanup of stale connections."""
        current_time = time.monotonic()
        stale_connections: list[int] = []

        with self.lock:
            for conn_id, info in self.connection_info.items():
                connection_age = current_time - info.created_time
                idle_time = current_time - info.last_used_time

                # Mark connections as stale if they're too old or idle too long
                if connection_age > self.max_connection_age or idle_time > (
                    self.max_connection_age / 2
                ):
                    stale_connections.append(conn_id)

        # Clean up stale connections
        cleaned_count = len(
            [
                conn_id
                for conn_id in stale_connections
                if self._cleanup_stale_connection(conn_id)
            ]
        )

        if cleaned_count > 0:
            self.metrics.cleanup_operations += 1
            self.metrics.stale_connections_cleaned += cleaned_count
            self.metrics.last_cleanup_time = current_time
            logger.info(f"Regular cleanup: removed {cleaned_count} stale connections")

    def _cleanup_stale_connection(self, conn_id: int) -> bool:
        """Clean up a specific stale connection."""
        try:
            # Try to find and remove connection from pool
            temp_connections: list[sqlite3.Connection] = []
            found = False

            # Remove all connections from pool temporarily
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    if id(conn) == conn_id:
                        # Found the stale connection, close it
                        self._close_connection_with_tracking(
                            conn, "Stale connection cleanup"
                        )
                        found = True
                    else:
                        temp_connections.append(conn)
                except queue.Empty:
                    break

            # Put back the connections we want to keep
            for conn in temp_connections:
                self.pool.put_nowait(conn)

            return found

        except Exception as e:
            logger.error(f"Error cleaning up stale connection {conn_id}: {e}")
            return False

    def _force_cleanup_stale_connections(self) -> int:
        """Force cleanup of all stale connections during pool exhaustion."""
        current_time = time.monotonic()
        stale_connections: list[int] = []

        with self.lock:
            for conn_id, info in self.connection_info.items():
                idle_time = current_time - info.last_used_time

                # More aggressive cleanup during exhaustion (30 minutes idle)
                if idle_time > 1800:  # 30 minutes
                    stale_connections.append(conn_id)

        return len(
            [
                conn_id
                for conn_id in stale_connections
                if self._cleanup_stale_connection(conn_id)
            ]
        )

    def _update_metrics(self):
        """Update pool metrics."""
        with self.lock:
            self.metrics.available_connections = self.pool.qsize()

            # Calculate average connection age
            if self.connection_info:
                current_time = time.monotonic()
                total_age = sum(
                    current_time - info.created_time
                    for info in self.connection_info.values()
                )
                self.metrics.average_connection_age = total_age / len(
                    self.connection_info
                )
            else:
                self.metrics.average_connection_age = 0.0

    def _check_pool_health(self):
        """Check pool health and generate alerts if needed."""
        current_time = time.monotonic()

        # Check for potential issues
        issues: list[str] = []

        # Check pool utilization
        if self.metrics.active_connections > (self.pool_size * 0.8):
            issues.append(
                f"High pool utilization: {self.metrics.active_connections}/{self.pool_size}"
            )

        # Check for long-running connections
        long_running_connections = 0
        with self.lock:
            for info in self.connection_info.values():
                if current_time - info.last_used_time > 1800:  # 30 minutes
                    long_running_connections += 1

        if long_running_connections > 0:
            issues.append(
                f"Long-running connections detected: {long_running_connections}"
            )

        # Check for frequent pool exhaustion
        if self.metrics.pool_exhaustion_events > 10:
            issues.append(
                f"Frequent pool exhaustion: {self.metrics.pool_exhaustion_events} events"
            )

        # Log issues if found
        if issues:
            logger.warning(f"Database pool health issues detected: {', '.join(issues)}")

    def _get_connection_ages_summary(self) -> dict[str, Any]:
        """Get summary of connection ages for monitoring."""
        current_time = time.monotonic()
        ages: list[float] = []
        idle_times: list[float] = []

        with self.lock:
            for info in self.connection_info.values():
                ages.append(current_time - info.created_time)
                idle_times.append(current_time - info.last_used_time)

        return {
            "connection_count": len(ages),
            "avg_age_seconds": sum(ages) / len(ages) if ages else 0,
            "max_age_seconds": max(ages, default=0),
            "avg_idle_seconds": sum(idle_times) / len(idle_times) if idle_times else 0,
            "max_idle_seconds": max(idle_times, default=0),
        }

    def get_pool_status(self) -> dict[str, Any]:
        """Get comprehensive pool status information."""
        with self.lock:
            return {
                "pool_size": self.pool_size,
                "total_connections": self.metrics.total_connections,
                "active_connections": self.metrics.active_connections,
                "available_connections": self.pool.qsize(),
                "connections_created": self.metrics.connections_created,
                "connections_closed": self.metrics.connections_closed,
                "pool_exhaustion_events": self.metrics.pool_exhaustion_events,
                "cleanup_operations": self.metrics.cleanup_operations,
                "peak_active_connections": self.metrics.peak_active_connections,
                "average_connection_age_seconds": self.metrics.average_connection_age,
                "stale_connections_cleaned": self.metrics.stale_connections_cleaned,
                "last_cleanup_time": datetime.fromtimestamp(
                    self.metrics.last_cleanup_time
                ).isoformat()
                if self.metrics.last_cleanup_time > 0
                else None,
                "connection_details": self._get_connection_ages_summary(),
                "monitoring_enabled": self._monitoring_enabled,
                "cleanup_thread_alive": self._cleanup_thread.is_alive()
                if self._cleanup_thread
                else False,
            }

    def force_cleanup(self) -> dict[str, Any]:
        """Force immediate cleanup of all stale connections."""
        logger.info("Force cleanup of database connection pool initiated")

        before_total = self.metrics.total_connections
        before_active = self.metrics.active_connections

        # Perform aggressive cleanup
        cleaned = self._force_cleanup_stale_connections()

        # Update metrics
        self.metrics.cleanup_operations += 1
        self.metrics.last_cleanup_time = time.time()

        after_total = self.metrics.total_connections
        after_active = self.metrics.active_connections

        result = {
            "cleanup_performed": True,
            "connections_before": {"total": before_total, "active": before_active},
            "connections_after": {"total": after_total, "active": after_active},
            "connections_cleaned": cleaned,
            "cleanup_time": datetime.fromtimestamp(
                self.metrics.last_cleanup_time
            ).isoformat(),
        }

        logger.info(f"Force cleanup completed: removed {cleaned} connections")
        return result

    def _cleanup_emergency_connections(self):
        """Close all emergency connections that were created during pool exhaustion."""
        with self.lock:
            emergency_count = len(self.emergency_connections)
            if emergency_count == 0:
                return 0

            closed_count = 0
            for conn_id, conn in list(self.emergency_connections.items()):
                try:
                    conn.close()
                    closed_count += 1
                    logger.debug(f"Closed emergency connection {conn_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to close emergency connection {conn_id}: {e}"
                    )

            self.emergency_connections.clear()

            if closed_count > 0:
                logger.info(f"Cleaned up {closed_count} emergency connections")

            return closed_count

    def close_all(self):
        """Close all connections in the pool and stop monitoring."""
        logger.info("Closing all database connections and stopping monitoring")

        # Stop monitoring
        self._monitoring_enabled = False

        # Close all connections in pool
        closed_count = 0
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                self._close_connection_with_tracking(conn, "Pool shutdown")
                closed_count += 1
            except (queue.Empty, sqlite3.Error):
                break

        # Close emergency connections
        emergency_closed = self._cleanup_emergency_connections()

        # Clean up tracking
        with self.lock:
            self.connection_info.clear()

        logger.info(
            f"Database connection pool closed: {closed_count} regular + {emergency_closed} emergency connections closed"
        )


class DatabaseManager:
    """
    Manages all database operations for the backup server.
    Handles client persistence, file record management, and SQLite operations.
    """

    def __init__(self, db_name: str | None = None, use_pool: bool = True):
        """
        Initialize the DatabaseManager.

        Args:
            db_name: Optional database name override. Uses config default if None.
            use_pool: Whether to use connection pooling for better performance.
        """
        self.db_name = db_name or DATABASE_NAME
        self.use_pool = use_pool
        self.connection_pool = None

        if use_pool:
            try:
                self.connection_pool = DatabaseConnectionPool(self.db_name)
                logger.info(
                    f"DatabaseManager initialized with connection pool: {self.db_name}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize connection pool: {e}, falling back to direct connections"
                )
                self.use_pool = False

        if not self.use_pool:
            logger.info(
                f"DatabaseManager initialized with direct connections: {self.db_name}"
            )

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        commit: bool = False,
        fetchone: bool = False,
        fetchall: bool = False,
    ) -> Any:
        """
        Helper function for executing SQLite database operations.
        Manages connection, cursor, commit, and error handling

        Args:
            query: The SQL query string.
            params: A tuple of parameters for the query.
            commit: True if the transaction should be committed.
            fetchone: True to fetch a single row.
            fetchall: True to fetch all rows.

        Returns:
            Query result (row, list of rows, or cursor) or None on failure for non-SELECTs.

        Raises:
            ServerError: If a database read error occurs that prevents server operation.
        """
        try:
            if self.use_pool and self.connection_pool:
                # Use connection pool for better performance
                conn = self.connection_pool.get_connection()
                conn_returned = False  # Track if connection has been handled
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    if commit:
                        conn.commit()
                    if fetchone:
                        result = cursor.fetchone()
                        return result
                    if fetchall:
                        result = cursor.fetchall()
                        return result
                    # For cursor operations, we need to keep connection until cursor is used
                    # This is a design limitation - cursor operations should be avoided with pooling
                    result = cursor.lastrowid if hasattr(cursor, "lastrowid") else None
                    return result
                except Exception:
                    # Don't return potentially corrupted connection to pool
                    with suppress(Exception):
                        conn.close()
                    conn_returned = True  # Mark as handled to avoid double-return
                    raise
                finally:
                    # Only return connection if it wasn't already closed/handled
                    if conn and not conn_returned:
                        with suppress(Exception):
                            self.connection_pool.return_connection(conn)
            else:
                # Fallback to direct connection
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    if commit:
                        conn.commit()
                    return (
                        cursor.fetchone()
                        if fetchone
                        else cursor.fetchall()
                        if fetchall
                        else cursor
                    )
        except (
            sqlite3.OperationalError
        ) as e:  # Specific error for "database is locked", "no such table" etc.
            logger.error(
                f"Database operational error: {e} | Query: {query[:150]}... | Params: {params}"
            )
            # Depending on severity, re-raise or return specific error indicator
            if "locked" in str(e).lower():
                logger.warning(
                    "Database was locked during operation. This might indicate contention or a long-running transaction."
                )
            # If it's a critical read operation (e.g., loading clients), we might need to halt.
            if not commit and (fetchone or fetchall):  # This was a read operation
                raise ServerError(f"Critical database read error: {e}") from e
            return None  # Indicate failure for write operations
        except sqlite3.Error as e:  # Catch other, more general SQLite errors
            logger.error(
                f"General database error: {e} | Query: {query[:150]}... | Params: {params}"
            )
            if not commit and (fetchone or fetchall):
                raise ServerError(f"General database read error: {e}") from e
            return None

    def init_database(self):
        """Initializes the database schema and performs integrity checks."""
        logger.info(f"Initializing database schema in '{self.db_name}' if needed...")

        # Enable foreign key constraints
        try:
            self.execute("PRAGMA foreign_keys = ON", commit=True)
            logger.info("Foreign key constraints enabled")
        except Exception as e:
            logger.warning(f"Failed to enable foreign key constraints: {e}")

        # First ensure basic schema exists, then apply migrations
        self._create_basic_schema()
        self._apply_database_migrations()

        # Perform foreign key integrity check on startup
        self._check_foreign_key_integrity_on_startup()

        logger.info("Database schema initialization complete.")

    def _check_foreign_key_integrity_on_startup(self):
        """Check foreign key integrity during database initialization."""
        try:
            # Check for foreign key violations
            fk_violations = self.execute("PRAGMA foreign_key_check", fetchall=True)

            if fk_violations:
                logger.warning(
                    f"Foreign key violations detected: {len(fk_violations)} issues found"
                )
                for violation in fk_violations[:10]:  # Log first 10 violations
                    logger.warning(
                        f"FK violation: table={violation[0]}, rowid={violation[1]}, "
                        f"parent={violation[2]}, fkid={violation[3]}"
                    )

                # Check for orphaned files without valid client references
                orphaned_count = self._check_orphaned_files()
                if orphaned_count > 0:
                    logger.warning(
                        f"Found {orphaned_count} orphaned file records without valid client references"
                    )

            else:
                logger.debug("Foreign key integrity check passed - no violations found")

        except Exception as e:
            logger.error(f"Foreign key integrity check failed: {e}")

    def _check_orphaned_files(self) -> int:
        """
        Check for orphaned file records without valid client references.

        Returns:
            int: Number of orphaned file records found
        """
        try:
            result = self.execute(
                """
                SELECT COUNT(*) FROM files f
                LEFT JOIN clients c ON f.ClientID = c.ID
                WHERE c.ID IS NULL
            """,
                fetchone=True,
            )

            return result[0] if result else 0

        except Exception as e:
            logger.error(f"Failed to check for orphaned files: {e}")
            return 0

    def _check_and_fix_orphaned_files(self, auto_fix: bool = False) -> dict[str, Any]:
        """
        Check for orphaned file records and optionally clean them up.

        Args:
            auto_fix: If True, automatically delete orphaned records

        Returns:
            dict: {'orphaned_count': int, 'cleaned': int, 'action': str}
        """
        orphaned_count = self._check_orphaned_files()

        if orphaned_count == 0:
            return {"orphaned_count": 0, "cleaned": 0, "action": "none"}

        if auto_fix:
            try:
                self.execute(
                    "DELETE FROM files WHERE ClientID NOT IN (SELECT ID FROM clients)",
                    commit=True,
                )
                logger.info(f"Cleaned up {orphaned_count} orphaned file records")
                return {
                    "orphaned_count": orphaned_count,
                    "cleaned": orphaned_count,
                    "action": "cleaned",
                }
            except Exception as e:
                logger.error(f"Failed to clean orphaned files: {e}")
                return {
                    "orphaned_count": orphaned_count,
                    "cleaned": 0,
                    "action": "error",
                    "error": str(e),
                }
        else:
            logger.warning(
                f"Found {orphaned_count} orphaned files (auto_fix=False, not cleaning)"
            )
            return {
                "orphaned_count": orphaned_count,
                "cleaned": 0,
                "action": "detected",
            }

    def _create_basic_schema(self):
        """Create the basic schema tables if they don't exist."""
        # Client Table: Stores information about registered clients.
        # LastSeen is stored as ISO8601 UTC text for portability and readability.
        # AESKey is per spec, though session-based keys are usually not persisted this way.
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                ID BLOB(16) PRIMARY KEY,
                Name VARCHAR(255) UNIQUE NOT NULL,
                PublicKey BLOB(160),
                LastSeen TEXT NOT NULL,
                AESKey BLOB(32)
            )
        """,
            commit=True,
        )

        # Files Table: Stores information about files backed up by clients.
        # ON DELETE CASCADE ensures that if a client is deleted, their file records are also removed.
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                ID BLOB(16) PRIMARY KEY,
                FileName VARCHAR(255) NOT NULL,
                PathName VARCHAR(255) NOT NULL,
                Verified BOOLEAN DEFAULT 0,
                FileSize INTEGER,
                ModificationDate TEXT,
                CRC INTEGER,
                ClientID BLOB(16) NOT NULL,
                FOREIGN KEY (ClientID) REFERENCES clients(ID) ON DELETE CASCADE
            )
        """,
            commit=True,
        )

        # Metrics History Table: Stores time-series metrics for analytics and monitoring.
        # Simple design: timestamp + metric_name + value for flexible querying.
        # Automatic cleanup keeps only last 7 days of data.
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                value REAL NOT NULL
            )
        """,
            commit=True,
        )

        # Add missing columns to existing tables
        self._add_missing_columns()

        # Create performance indexes
        self._create_performance_indexes()

    def _create_performance_indexes(self):
        """Create indexes on frequently queried columns for better performance."""
        try:
            # Index on clients.Name for faster lookups by client name
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(Name)
            """,
                commit=True,
            )
            logger.debug("Created index on clients.Name")

            # Index on clients.LastSeen for sorting and filtering by last seen time
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_clients_lastseen ON clients(LastSeen)
            """,
                commit=True,
            )
            logger.debug("Created index on clients.LastSeen")

            # Index on files.ClientID for faster file lookups by client (most common query)
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_clientid ON files(ClientID)
            """,
                commit=True,
            )
            logger.debug("Created index on files.ClientID")

            # Index on files.FileName for faster file lookups by name
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_filename ON files(FileName)
            """,
                commit=True,
            )
            logger.debug("Created index on files.FileName")

            # Composite index on files(ClientID, FileName) for the common query pattern
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_client_filename ON files(ClientID, FileName)
            """,
                commit=True,
            )
            logger.debug("Created composite index on files(ClientID, FileName)")

            # Index on files.Verified for filtering verified files
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_verified ON files(Verified)
            """,
                commit=True,
            )
            logger.debug("Created index on files.Verified")

            # Index on files.ModificationDate for sorting and filtering by date
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_moddate ON files(ModificationDate)
            """,
                commit=True,
            )
            logger.debug("Created index on files.ModificationDate")

            # Index on files.FileSize for aggregate queries (SUM, AVG)
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_files_filesize ON files(FileSize)
            """,
                commit=True,
            )
            logger.debug("Created index on files.FileSize")

            # Composite index on metrics_history(metric_name, timestamp) for time-series queries
            self.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON metrics_history(metric_name, timestamp)
            """,
                commit=True,
            )
            logger.debug(
                "Created composite index on metrics_history(metric_name, timestamp)"
            )

            logger.info("Database performance indexes created successfully")

        except Exception as e:
            logger.warning(f"Some indexes may not have been created: {e}")

    def _add_missing_columns(self):
        """Add missing columns to existing tables for backward compatibility."""
        # Add FileSize and ModificationDate to older tables if they don't exist
        try:
            self.execute("SELECT FileSize FROM files LIMIT 1", fetchone=True)
        except (sqlite3.OperationalError, ServerError):
            logger.info("Adding FileSize column to files table")
            self.execute("ALTER TABLE files ADD COLUMN FileSize INTEGER", commit=True)
        try:
            self.execute("SELECT ModificationDate FROM files LIMIT 1", fetchone=True)
        except (sqlite3.OperationalError, ServerError):
            logger.info("Adding ModificationDate column to files table")
            self.execute(
                "ALTER TABLE files ADD COLUMN ModificationDate TEXT", commit=True
            )
        try:
            self.execute("SELECT CRC FROM files LIMIT 1", fetchone=True)
        except (sqlite3.OperationalError, ServerError):
            logger.info("Adding CRC column to files table")
            self.execute("ALTER TABLE files ADD COLUMN CRC INTEGER", commit=True)

        # Add ClientID column for proper foreign key relationship
        try:
            self.execute("SELECT ClientID FROM files LIMIT 1", fetchone=True)
        except (sqlite3.OperationalError, ServerError):
            logger.info("Adding ClientID column to files table and migrating data")
            self.execute("ALTER TABLE files ADD COLUMN ClientID BLOB(16)", commit=True)
            # Migrate existing data: move ID to ClientID and generate new unique IDs
            self._migrate_files_to_clientid_schema()

    def _apply_database_migrations(self):
        """Apply database migrations to enhance functionality."""
        try:
            from .database_migrations import DatabaseMigrationManager

            migration_manager = DatabaseMigrationManager(self.db_name)

            if pending := migration_manager.get_pending_migrations():
                logger.info(f"Applying {len(pending)} database migrations...")
                if migration_manager.migrate_to_latest():
                    logger.info("Database migrations applied successfully")
                else:
                    logger.warning(
                        "Some database migrations failed - system will continue with existing schema"
                    )
            else:
                logger.debug("No pending database migrations")
        except ImportError:
            logger.debug("Migration system not available - skipping migrations")
        except Exception as e:
            logger.warning(
                f"Migration system error: {e} - continuing with basic schema"
            )

    def _migrate_files_to_clientid_schema(self):
        """Migrate existing files table to use ClientID foreign key"""
        import uuid

        try:
            # Get all existing files
            existing_files = self.execute(
                "SELECT ID, FileName FROM files WHERE ClientID IS NULL", fetchall=True
            )

            for file_id, filename in existing_files:
                # The current ID is actually the client ID, so move it to ClientID
                new_file_id = uuid.uuid4().bytes  # Generate new unique file ID

                self.execute(
                    """
                    UPDATE files
                    SET ClientID = ?, ID = ?
                    WHERE ID = ? AND FileName = ? AND ClientID IS NULL
                """,
                    (file_id, new_file_id, file_id, filename),
                    commit=True,
                )

            logger.info(
                f"Migrated {len(existing_files)} file records to use ClientID schema"
            )

        except Exception as e:
            logger.error(f"Failed to migrate files to ClientID schema: {e}")
            raise

    def load_clients_from_db(self) -> list[tuple[bytes, str, bytes | None, str]]:
        """
        Loads existing client data from the database.

        Returns:
            List of tuples containing (client_id, name, public_key_bytes, last_seen_iso_utc)

        Raises:
            ServerError: If a critical database read error occurs.
        """
        logger.info("Loading existing clients from database...")
        try:
            if rows := self.execute(
                "SELECT ID, Name, PublicKey, LastSeen FROM clients", fetchall=True
            ):
                logger.info(f"Successfully loaded {len(rows)} client(s) from database.")
                return rows
            else:
                logger.info("No existing clients found in database.")
                return []
        except ServerError as e:  # Raised by execute on critical read failure
            logger.critical(
                f"CRITICAL FAILURE: Could not load client data from database: {e}"
            )
            raise

    def save_client_to_db(
        self,
        client_id: bytes,
        name: str,
        public_key_bytes: bytes | None,
        aes_key: bytes | None,
    ) -> None:
        """
        Saves or updates a client's information in the database.

        Args:
            client_id: The unique UUID (bytes) of the client.
            name: The username of the client.
            public_key_bytes: The client's RSA public key in X.509 format.
            aes_key: The client's current AES session key.
        """
        # Convert monotonic client.last_seen to a wall-clock datetime for storage.
        # For the DB's LastSeen, always use current UTC wall-clock time to reflect this update event.
        current_wall_time_utc_iso = (
            datetime.now(UTC).isoformat(timespec="seconds") + "Z"
        )

        self.execute(
            """
            INSERT OR REPLACE INTO clients (ID, Name, PublicKey, LastSeen, AESKey)
            VALUES (?, ?, ?, ?, ?)
        """,
            (client_id, name, public_key_bytes, current_wall_time_utc_iso, aes_key),
            commit=True,
        )

        logger.debug(
            f"Client '{name}' data saved/updated in database (Recorded LastSeen: {current_wall_time_utc_iso})."
        )

    def save_file_info_to_db(
        self,
        client_id: bytes,
        file_name: str,
        path_name: str,
        verified: bool,
        file_size: int,
        mod_date: str,
        crc: int | None = None,
    ) -> None:
        """
        Saves or updates file information in the database.

        Args:
            client_id: The unique UUID (bytes) of the client who uploaded the file.
            file_name: The original filename.
            path_name: The stored file path (relative or absolute).
            verified: Whether the file has been verified (checksum validated).
            file_size: The size of the file in bytes.
            mod_date: The modification date of the file as an ISO 8601 string.
            crc: The CRC32 checksum of the file.
        """
        import uuid

        # Generate unique file ID
        file_id = uuid.uuid4().bytes

        # Ensure path_name is stored consistently (e.g., relative to FILE_STORAGE_DIR or absolute)
        # Current implementation assumes path_name is the final, usable path.
        if crc is not None:
            self.execute(
                """
                INSERT OR REPLACE INTO files (ID, FileName, PathName, Verified, FileSize, ModificationDate, CRC, ClientID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_id,
                    file_name,
                    path_name,
                    verified,
                    file_size,
                    mod_date,
                    crc,
                    client_id,
                ),
                commit=True,
            )
        else:
            self.execute(
                """
                INSERT OR REPLACE INTO files (ID, FileName, PathName, Verified, FileSize, ModificationDate, ClientID)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_id,
                    file_name,
                    path_name,
                    verified,
                    file_size,
                    mod_date,
                    client_id,
                ),
                commit=True,
            )

        logger.debug(
            f"File info for '{file_name}' (Client ID: {client_id.hex()}) saved/updated in database. Verified status: {verified}."
        )

    def get_client_by_id(
        self, client_id: bytes
    ) -> tuple[bytes, str, bytes | None, str, bytes | None] | None:
        """
        Retrieves a client record by ID.

        Args:
            client_id: The unique UUID (bytes) of the client.

        Returns:
            Tuple containing (client_id, name, public_key_bytes, last_seen_iso_utc, aes_key) or None if not found.
        """
        try:
            return self.execute(
                "SELECT ID, Name, PublicKey, LastSeen, AESKey FROM clients WHERE ID = ?",
                (client_id,),
                fetchone=True,
            )
        except ServerError as e:
            logger.error(f"Error retrieving client by ID {client_id.hex()}: {e}")
            return None

    def get_client_by_name(
        self, name: str
    ) -> tuple[bytes, str, bytes | None, str, bytes | None] | None:
        """
        Retrieves a client record by name.

        Args:
            name: The username of the client.

        Returns:
            Tuple containing (client_id, name, public_key_bytes, last_seen_iso_utc, aes_key) or None if not found.
        """
        try:
            return self.execute(
                "SELECT ID, Name, PublicKey, LastSeen, AESKey FROM clients WHERE Name = ?",
                (name,),
                fetchone=True,
            )
        except ServerError as e:
            logger.error(f"Error retrieving client by name '{name}': {e}")
            return None

    def get_client_files(self, client_id: bytes) -> list[tuple[str, str, bool]]:
        """
        Retrieves all files for a specific client.

        Args:
            client_id: The unique UUID (bytes) of the client.

        Returns:
            List of tuples containing (file_name, path_name, verified) for each file.
        """
        try:
            results = self.execute(
                "SELECT FileName, PathName, Verified FROM files WHERE ClientID = ?",
                (client_id,),
                fetchall=True,
            )
            return results or []
        except ServerError as e:
            logger.error(f"Error retrieving files for client {client_id.hex()}: {e}")
            return []

    def delete_client(self, client_id: bytes) -> bool:
        """
        Deletes a client and all associated file records.

        Args:
            client_id: The unique UUID (bytes) of the client to delete.

        Returns:
            True if the client was deleted, False if an error occurred.
        """
        try:
            cursor = self.execute(
                "DELETE FROM clients WHERE ID = ?", (client_id,), commit=True
            )
            if cursor and cursor.rowcount > 0:
                logger.info(
                    f"Successfully deleted client {client_id.hex()} and associated files."
                )
                return True
            else:
                logger.warning(f"No client found with ID {client_id.hex()} to delete.")
                return False
        except Exception as e:
            logger.error(f"Error deleting client {client_id.hex()}: {e}")
            return False

    def update_client(
        self, client_id: bytes, name: str | None = None, public_key: bytes | None = None
    ) -> bool:
        """
        Update client information in database.

        Args:
            client_id: Client UUID as bytes (16 bytes)
            name: New client name (optional)
            public_key: New public key in X.509 format (optional)

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if self.use_pool and self.connection_pool:
                # Use connection pool for better performance
                conn = self.connection_pool.get_connection()
                try:
                    cursor = conn.cursor()

                    # Build dynamic UPDATE query based on provided fields
                    fields = []
                    params = []

                    if name is not None:
                        fields.append("Name = ?")
                        params.append(name)

                    if public_key is not None:
                        fields.append("PublicKey = ?")
                        params.append(public_key)

                    if not fields:
                        logger.warning("update_client called with no fields to update")
                        return False

                    # Add LastSeen timestamp update
                    fields.append("LastSeen = ?")
                    params.append(datetime.now(UTC).isoformat())

                    # Add client_id for WHERE clause
                    params.append(client_id)

                    query = f"UPDATE clients SET {', '.join(fields)} WHERE ID = ?"

                    cursor.execute(query, params)
                    conn.commit()

                    success = cursor.rowcount > 0
                    if success:
                        logger.info(f"Updated client {client_id.hex()}: {fields}")
                    else:
                        logger.warning(f"No client found with ID {client_id.hex()}")

                    return success

                finally:
                    self.connection_pool.return_connection(conn)
            else:
                # Fallback to direct connection
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()

                    # Build dynamic UPDATE query based on provided fields
                    fields = []
                    params = []

                    if name is not None:
                        fields.append("Name = ?")
                        params.append(name)

                    if public_key is not None:
                        fields.append("PublicKey = ?")
                        params.append(public_key)

                    if not fields:
                        logger.warning("update_client called with no fields to update")
                        return False

                    # Add LastSeen timestamp update
                    fields.append("LastSeen = ?")
                    params.append(datetime.now(UTC).isoformat())

                    # Add client_id for WHERE clause
                    params.append(client_id)

                    query = f"UPDATE clients SET {', '.join(fields)} WHERE ID = ?"

                    cursor.execute(query, params)
                    conn.commit()

                    success = cursor.rowcount > 0
                    if success:
                        logger.info(f"Updated client {client_id.hex()}: {fields}")
                    else:
                        logger.warning(f"No client found with ID {client_id.hex()}")

                    return success

        except sqlite3.Error as e:
            logger.error(f"Database error updating client {client_id.hex()}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating client: {e}")
            return False

    def delete_file_record(self, client_id: bytes, file_name: str) -> bool:
        """
        Deletes a specific file record for a client.

        Args:
            client_id: The unique UUID (bytes) of the client.
            file_name: The filename to delete from records.

        Returns:
            True if the file record was deleted, False if an error occurred.
        """
        try:
            cursor = self.execute(
                "DELETE FROM files WHERE ClientID = ? AND FileName = ?",
                (client_id, file_name),
                commit=True,
            )
            if cursor and cursor.rowcount > 0:
                logger.info(
                    f"Successfully deleted file record '{file_name}' for client {client_id.hex()}."
                )
                return True
            else:
                logger.warning(
                    f"No file record found for '{file_name}' and client {client_id.hex()}."
                )
                return False
        except Exception as e:
            logger.error(
                f"Error deleting file record '{file_name}' for client {client_id.hex()}: {e}"
            )
            return False

    def delete_file(self, client_id: str, filename: str) -> bool:
        """Deletes a file from the filesystem and the database."""
        try:
            # First, get the file path from the database
            file_info = self.execute(
                "SELECT PathName FROM files WHERE ID = ? AND FileName = ?",
                (bytes.fromhex(client_id), filename),
                fetchone=True,
            )
            if not file_info:
                logger.warning(
                    f"File '{filename}' not found in database for client {client_id}"
                )
                return False

            file_path = file_info[0]

            # Delete the file from the filesystem
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file from filesystem: {file_path}")
            else:
                logger.warning(
                    f"File not found on filesystem for deletion: {file_path}"
                )

            # Delete the file record from the database
            return self.delete_file_record(bytes.fromhex(client_id), filename)

        except Exception as e:
            logger.error(
                f"Error deleting file '{filename}' for client {client_id}: {e}"
            )
            return False

    def get_database_stats(self) -> dict[str, Any]:
        """
        Retrieves basic statistics about the database with 30-second caching.

        Returns:
            Dictionary containing database statistics.
        """
        # Initialize cache and lock on first call
        if not hasattr(self, "_stats_cache"):
            self._stats_cache = {"data": None, "timestamp": 0}
            self._stats_cache_ttl = 30  # seconds
            self._stats_cache_lock = threading.Lock()

        # Check cache with thread safety
        with self._stats_cache_lock:
            current_time = time.time()
            if self._stats_cache["data"] and (
                current_time - self._stats_cache["timestamp"] < self._stats_cache_ttl
            ):
                return self._stats_cache["data"]

        stats: dict[str, Any] = {
            "total_clients": 0,
            "total_files": 0,
            "verified_files": 0,
            "database_size_bytes": 0,
        }

        try:
            # Count clients
            if result := self.execute("SELECT COUNT(*) FROM clients", fetchone=True):
                stats["total_clients"] = result[0]

            # Count files
            if result := self.execute("SELECT COUNT(*) FROM files", fetchone=True):
                stats["total_files"] = result[0]

            # Count verified files
            if result := self.execute(
                "SELECT COUNT(*) FROM files WHERE Verified = 1", fetchone=True
            ):
                stats["verified_files"] = result[0]

            # Get database file size
            if os.path.exists(self.db_name):
                stats["database_size_bytes"] = os.path.getsize(self.db_name)

            # Update cache with thread safety
            with self._stats_cache_lock:
                self._stats_cache = {"data": stats, "timestamp": current_time}

        except Exception as e:
            logger.error(f"Error retrieving database statistics: {e}")

        return stats

    def get_all_clients(self) -> list[dict[str, Any]]:
        """Retrieves all clients from the database."""
        try:
            clients = self.execute(
                "SELECT ID, Name, LastSeen FROM clients", fetchall=True
            )
            if clients:
                return [
                    {"id": row[0].hex(), "name": row[1], "last_seen": row[2]}
                    for row in clients
                ]
            return []
        except Exception as e:
            logger.error(f"Database error while getting all clients: {e}")
            return []

    def get_files_for_client(self, client_id: str) -> list[dict[str, Any]]:
        """Retrieves all files for a given client."""
        try:
            files = self.execute(
                "SELECT FileName, PathName, Verified FROM files WHERE ClientID=?",
                (bytes.fromhex(client_id),),
                fetchall=True,
            )
            if files:
                return [
                    {"filename": row[0], "path": row[1], "verified": bool(row[2])}
                    for row in files
                ]
            return []
        except Exception as e:
            logger.error(
                f"Database error while getting files for client {client_id}: {e}"
            )
            return []

    def get_all_files(self) -> list[dict[str, Any]]:
        """Retrieves all files from the database."""
        try:
            files = self.execute(
                """
                SELECT f.FileName, f.PathName, f.Verified, c.Name, f.FileSize, f.ModificationDate, f.ClientID
                FROM files f JOIN clients c ON f.ClientID = c.ID
            """,
                fetchall=True,
            )
            if files:
                return [
                    {
                        "filename": row[0],
                        "path": row[1],
                        "verified": bool(row[2]),
                        "client": row[3],
                        "size": row[4],
                        "date": row[5],
                        "client_id": row[6],  # bytes
                    }
                    for row in files
                ]
            return []
        except Exception as e:
            logger.error(f"Database error while getting all files: {e}")
            return []

    def get_file_info(self, client_id: str, filename: str) -> dict[str, Any] | None:
        """Retrieves all information for a single file."""
        try:
            row = self.execute(
                """
                SELECT f.FileName, f.PathName, f.Verified, c.Name, f.FileSize, f.ModificationDate, f.CRC
                FROM files f JOIN clients c ON f.ClientID = c.ID
                WHERE f.ClientID = ? AND f.FileName = ?
            """,
                (bytes.fromhex(client_id), filename),
                fetchone=True,
            )
            if row:
                return {
                    "filename": row[0],
                    "path": row[1],
                    "verified": bool(row[2]),
                    "client": row[3],
                    "size": row[4],
                    "date": row[5],
                    "crc": row[6],
                }
            return None
        except Exception as e:
            logger.error(
                f"Database error while getting file info for {client_id}/{filename}: {e}"
            )
            return None

    def update_file_verification(
        self, client_id: str, filename: str, verified: bool, crc: int
    ) -> bool:
        """Update the verification status and CRC for a stored file."""
        try:
            client_id_bytes = bytes.fromhex(client_id)
        except ValueError as exc:
            logger.error(
                f"Invalid client ID '{client_id}' while updating verification: {exc}"
            )
            return False

        query = """
            UPDATE files
            SET Verified = ?, CRC = ?
            WHERE ClientID = ? AND FileName = ?
        """
        params = (1 if verified else 0, crc, client_id_bytes, filename)

        try:
            if self.use_pool and self.connection_pool:
                conn = self.connection_pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    rowcount = cursor.rowcount
                except Exception:
                    with suppress(Exception):
                        conn.close()
                    raise
                else:
                    self.connection_pool.return_connection(conn)
            else:
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    rowcount = cursor.rowcount

            return bool(rowcount)
        except Exception as e:
            logger.error(
                f"Failed to update verification for file '{filename}' (client {client_id}): {e}"
            )
            return False

    def get_total_clients_count(self) -> int:
        """Returns the total number of registered clients."""
        try:
            if result := self.execute("SELECT COUNT(*) FROM clients", fetchone=True):
                return result[0]
            return 0
        except Exception as e:
            logger.error(f"Database error while getting total client count: {e}")
            return 0

    def get_total_files_count(self) -> int:
        """
        Returns the total number of files in the database.

        This is more efficient than calling len(get_all_files()) as it uses
        a COUNT query instead of retrieving all file records.

        Returns:
            int: Total number of file records in the database
        """
        try:
            if result := self.execute("SELECT COUNT(*) FROM files", fetchone=True):
                return result[0]
            return 0
        except Exception as e:
            logger.error(f"Database error while getting total files count: {e}")
            return 0

    def get_total_storage_bytes(self, verified_only: bool = False) -> int:
        """Return total storage size (SUM of FileSize) in bytes.

        Args:
            verified_only: When True, only include files with Verified = 1

        Returns:
            int: Total number of bytes across matching files.
        """
        try:
            where = "WHERE FileSize IS NOT NULL"
            if verified_only:
                where += " AND Verified = 1"

            query = f"SELECT SUM(FileSize) FROM files {where}"
            if result := self.execute(query, fetchone=True):
                return int(result[0]) if result[0] is not None else 0
            return 0
        except Exception as e:
            logger.error(f"Database error while getting total storage bytes: {e}")
            return 0

    def get_average_backup_size_bytes(self, verified_only: bool = False) -> float:
        """Return average backup (file) size (AVG of FileSize) in bytes.

        Args:
            verified_only: When True, only include files with Verified = 1

        Returns:
            float: Average file size in bytes (0.0 if no data)
        """
        try:
            where = "WHERE FileSize IS NOT NULL"
            if verified_only:
                where += " AND Verified = 1"

            query = f"SELECT AVG(FileSize) FROM files {where}"
            if result := self.execute(query, fetchone=True):
                return float(result[0]) if result[0] is not None else 0.0
            return 0.0
        except Exception as e:
            logger.error(f"Database error while getting average backup size bytes: {e}")
            return 0.0

    def bulk_insert_clients(self, client_list: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Bulk insert multiple clients efficiently using executemany.

        Args:
            client_list: List of client dictionaries with keys:
                - 'id': bytes (optional, will generate UUID if missing)
                - 'name': str (required)
                - 'public_key': bytes (optional)
                - 'aes_key': bytes (optional)

        Returns:
            dict: {'success': bool, 'data': {'inserted': int}, 'error': str}

        Example:
            clients = [
                {'name': 'client1', 'id': uuid.uuid4().bytes},
                {'name': 'client2', 'id': uuid.uuid4().bytes}
            ]
            result = db.bulk_insert_clients(clients)
        """
        import uuid

        try:
            # Validate input
            if not client_list:
                return {"success": False, "data": None, "error": "Client list is empty"}

            # Prepare parameters with defaults
            params = []
            for c in client_list:
                if not isinstance(c, dict):
                    logger.warning(f"Skipping invalid client entry: {c}")
                    continue

                name = c.get("name", "")
                if not name:
                    logger.warning("Skipping client without name")
                    continue

                params.append(
                    (
                        c.get("id", uuid.uuid4().bytes),
                        name,
                        c.get("public_key"),
                        datetime.now(UTC).isoformat(),
                        c.get("aes_key"),
                    )
                )

            if not params:
                return {
                    "success": False,
                    "data": None,
                    "error": "No valid clients to insert",
                }
            # Count before insert for accurate reporting
            before_count = self.execute("SELECT COUNT(*) FROM clients", fetchone=True)
            before_count = before_count[0] if before_count else 0

            # Use executemany for efficient bulk insert
            success = self.execute_many(
                "INSERT OR IGNORE INTO clients (ID, Name, PublicKey, LastSeen, AESKey) VALUES (?, ?, ?, ?, ?)",
                params,
                commit=True,
            )

            if success:
                # Get actual insert count (some may have been ignored due to duplicates)
                after_count = self.execute(
                    "SELECT COUNT(*) FROM clients", fetchone=True
                )
                actual_inserted = (after_count[0] if after_count else 0) - before_count

                logger.info(
                    f"Bulk inserted {actual_inserted} clients successfully ({len(params) - actual_inserted} skipped as duplicates)"
                )
                return {
                    "success": True,
                    "data": {
                        "inserted": actual_inserted,
                        "attempted": len(params),
                        "skipped": len(params) - actual_inserted,
                    },
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": "Bulk insert operation failed",
                }

        except Exception as e:
            logger.error(f"Bulk client insert failed: {e}")
            return {"success": False, "data": None, "error": str(e)}

    def get_total_bytes_transferred(self) -> int:
        """Returns the total number of bytes transferred."""
        try:
            if result := self.execute(
                "SELECT SUM(FileSize) FROM files WHERE Verified = 1", fetchone=True
            ):
                return result[0] if result[0] is not None else 0
            return 0
        except Exception as e:
            logger.error(f"Database error while getting total bytes transferred: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════════════════════
    # Metrics Persistence Methods
    # ═══════════════════════════════════════════════════════════════════════════════

    def record_metric(self, metric_name: str, value: float) -> bool:
        """
        Record a single metric sample to the database.

        Args:
            metric_name: Name of the metric (e.g., "connections", "files", "bandwidth")
            value: Numeric value of the metric

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            timestamp = datetime.now(UTC).isoformat()
            self.execute(
                "INSERT INTO metrics_history (timestamp, metric_name, value) VALUES (?, ?, ?)",
                (timestamp, metric_name, value),
                commit=True,
            )
            logger.debug(f"Recorded metric '{metric_name}' = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to record metric '{metric_name}': {e}")
            return False

    def get_metrics_history(
        self, metric_name: str, hours: int = 24
    ) -> list[dict[str, Any]]:
        """
        Retrieve historical metrics data for a specific metric.

        Args:
            metric_name: Name of the metric to retrieve
            hours: Number of hours of history to retrieve (default: 24)

        Returns:
            list[dict]: List of {'timestamp': str, 'value': float} samples
        """
        try:
            # Calculate cutoff time
            cutoff = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff = cutoff.replace(hour=cutoff.hour - hours)
            cutoff_iso = cutoff.isoformat()

            # Query metrics within time range
            rows = self.execute(
                """
                SELECT timestamp, value
                FROM metrics_history
                WHERE metric_name = ? AND timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (metric_name, cutoff_iso),
                fetchall=True,
            )

            if not rows:
                return []

            return [{"timestamp": row[0], "value": row[1]} for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve metrics history for '{metric_name}': {e}")
            return []

    def cleanup_old_metrics(self, days_to_keep: int = 7) -> int:
        """
        Remove metrics older than specified days to prevent unbounded growth.

        Args:
            days_to_keep: Number of days of metrics to keep (default: 7)

        Returns:
            int: Number of rows deleted
        """
        try:
            # Calculate cutoff timestamp
            cutoff = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff = cutoff.replace(day=cutoff.day - days_to_keep)
            cutoff_iso = cutoff.isoformat()

            # Delete old metrics
            cursor = self.execute(
                "DELETE FROM metrics_history WHERE timestamp < ?",
                (cutoff_iso,),
                commit=True,
            )

            rows_deleted = cursor.rowcount if cursor else 0
            if rows_deleted > 0:
                logger.info(
                    f"Cleaned up {rows_deleted} old metric samples (older than {days_to_keep} days)"
                )
            else:
                logger.debug("No old metrics to clean up")

            return rows_deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic database transactions.

        Provides ACID guarantees for multi-step operations. Automatically commits
        on success and rolls back on exceptions. Handles nested transaction attempts
        gracefully by detecting existing transactions.

        Usage:
            with db_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM files WHERE ClientID = ?", (client_id,))
                cursor.execute("DELETE FROM clients WHERE ID = ?", (client_id,))
                # Both operations committed atomically

        Yields:
            sqlite3.Connection: Database connection for transaction operations

        Raises:
            Exception: Any exception that occurs during transaction (after rollback)

        Note:
            SQLite doesn't support true nested transactions. If called within an
            existing transaction, this will use the existing transaction context.
        """
        conn = None
        started_transaction = False

        try:
            # Get connection from pool or create new one
            if self.use_pool and self.connection_pool:
                conn = self.connection_pool.get_connection()
            else:
                conn = sqlite3.connect(self.db_name, timeout=10.0)

            # Check if already in a transaction (SQLite 3.7.11+)
            in_transaction = (
                conn.in_transaction if hasattr(conn, "in_transaction") else False
            )

            # Only begin if not already in transaction
            if not in_transaction:
                conn.execute("BEGIN")
                started_transaction = True
                logger.debug("Transaction started")
            else:
                logger.debug("Using existing transaction context (nested call)")

            # Yield connection for transaction operations
            yield conn

            # Only commit if we started the transaction
            if started_transaction:
                conn.commit()
                logger.debug("Transaction committed successfully")

        except Exception as e:
            # Only rollback if we started the transaction
            if conn and started_transaction:
                try:
                    conn.rollback()
                    logger.warning(f"Transaction rolled back due to error: {e}")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

            # Re-raise the original exception
            raise

        finally:
            # Return connection to pool or close it
            if conn:
                if self.use_pool and self.connection_pool:
                    with suppress(Exception):
                        self.connection_pool.return_connection(conn)
                else:
                    with suppress(Exception):
                        conn.close()

    def check_database_size_limits(self) -> dict[str, Any]:
        """
        Check database size against configured thresholds.

        Returns:
            dict: {
                'size_mb': float,
                'size_bytes': int,
                'status': str ('ok', 'warning', 'critical'),
                'threshold_warning_mb': int,
                'threshold_critical_mb': int,
                'message': str
            }
        """
        warning_threshold_mb = 500
        critical_threshold_mb = 1000

        try:
            if not os.path.exists(self.db_name):
                return {
                    "size_mb": 0.0,
                    "size_bytes": 0,
                    "status": "ok",
                    "threshold_warning_mb": warning_threshold_mb,
                    "threshold_critical_mb": critical_threshold_mb,
                    "message": "Database file not found",
                }

            size_bytes = os.path.getsize(self.db_name)
            size_mb = round(size_bytes / (1024 * 1024), 2)

            status = "ok"
            message = f"Database size is {size_mb}MB"

            if size_mb > critical_threshold_mb:
                status = "critical"
                message = f"CRITICAL: Database size {size_mb}MB exceeds critical threshold of {critical_threshold_mb}MB"
                logger.critical(message)
            elif size_mb > warning_threshold_mb:
                status = "warning"
                message = f"WARNING: Database size {size_mb}MB exceeds warning threshold of {warning_threshold_mb}MB"
                logger.warning(message)

            return {
                "size_mb": size_mb,
                "size_bytes": size_bytes,
                "status": status,
                "threshold_warning_mb": warning_threshold_mb,
                "threshold_critical_mb": critical_threshold_mb,
                "message": message,
            }

        except Exception as e:
            logger.error(f"Failed to check database size: {e}")
            return {
                "size_mb": 0.0,
                "size_bytes": 0,
                "status": "error",
                "threshold_warning_mb": warning_threshold_mb,
                "threshold_critical_mb": critical_threshold_mb,
                "message": f"Error checking database size: {e}",
            }

    # Enhanced Database Methods

    def execute_many(
        self, query: str, param_list: list[tuple[Any, ...]], commit: bool = True
    ) -> bool:
        """
        Execute a query multiple times with different parameters for bulk operations.

        Args:
            query: The SQL query string.
            param_list: List of parameter tuples.
            commit: Whether to commit the transaction.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if self.use_pool and self.connection_pool:
                conn = self.connection_pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.executemany(query, param_list)
                    if commit:
                        conn.commit()
                    self.connection_pool.return_connection(conn)
                    return True
                except Exception as e:
                    with suppress(Exception):
                        conn.close()
                    raise e
            else:
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, param_list)
                    if commit:
                        conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Bulk database operation failed: {e}")
            return False

    def search_files_advanced(
        self,
        search_term: str = "",
        file_type: str = "",
        client_name: str = "",
        date_from: str = "",
        date_to: str = "",
        min_size: int = 0,
        max_size: int = 0,
        verified_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Advanced file search with multiple filters.

        Args:
            search_term: Search in filename or path
            file_type: File extension to filter by
            client_name: Client name to filter by
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            verified_only: Only return verified files

        Returns:
            List of file dictionaries matching the criteria
        """
        conditions = ["1=1"]  # Base condition
        params: list[Any] = []

        if search_term:
            conditions.append("(f.FileName LIKE ? OR f.PathName LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        if file_type:
            # Try to match FileExtension if available, otherwise extract from filename
            conditions.append("(f.FileExtension = ? OR f.FileName LIKE ?)")
            params.extend([file_type, f"%.{file_type}"])

        if client_name:
            conditions.append("c.Name LIKE ?")
            params.append(f"%{client_name}%")

        if date_from:
            conditions.append("f.ModificationDate >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("f.ModificationDate <= ?")
            params.append(date_to)

        if min_size > 0:
            conditions.append("f.FileSize >= ?")
            params.append(min_size)

        if max_size > 0:
            conditions.append("f.FileSize <= ?")
            params.append(max_size)

        if verified_only:
            conditions.append("f.Verified = 1")

        # Build SELECT clause dynamically based on available columns
        base_columns = "f.FileName, f.PathName, f.FileSize, f.ModificationDate, f.Verified, f.CRC, c.Name as ClientName"
        extended_columns = ""

        # Check if extended columns exist (from migrations)
        with suppress(sqlite3.OperationalError, ServerError):
            self.execute("SELECT FileCategory FROM files LIMIT 1", fetchone=True)
            extended_columns = ", f.FileCategory, f.MimeType, f.FileExtension, f.TransferDuration, f.TransferSpeed"

        query = f"""
            SELECT {base_columns}{extended_columns}
            FROM files f
            JOIN clients c ON f.ClientID = c.ID
            WHERE {" AND ".join(conditions)}
            ORDER BY f.ModificationDate DESC
            LIMIT 1000
        """

        try:
            results = self.execute(query, tuple(params), fetchall=True)
            if results:
                return [
                    {
                        "filename": row[0],
                        "path": row[1],
                        "size": row[2],
                        "date": row[3],
                        "verified": bool(row[4]),
                        "crc": row[5],
                        "client": row[6],
                        "category": row[7] if len(row) > 7 else None,
                        "mime_type": row[8] if len(row) > 8 else None,
                        "extension": row[9] if len(row) > 9 else None,
                        "transfer_duration": row[10] if len(row) > 10 else None,
                        "transfer_speed": row[11] if len(row) > 11 else None,
                    }
                    for row in results
                ]
            return []
        except Exception as e:
            logger.error(f"Advanced file search failed: {e}")
            return []

    def get_storage_statistics(self) -> dict[str, Any]:
        """Get comprehensive storage and usage statistics."""
        stats: dict[str, Any] = {
            "database_info": {},
            "storage_info": {},
            "client_stats": {},
            "file_stats": {},
            "performance_info": {},
        }

        try:
            # Database information
            stats["database_info"] = {
                "file_path": os.path.abspath(self.db_name),
                "file_size_mb": round(os.path.getsize(self.db_name) / (1024 * 1024), 2)
                if os.path.exists(self.db_name)
                else 0,
                "connection_pool_enabled": self.use_pool,
                "pool_size": self.connection_pool.pool_size
                if self.connection_pool
                else 0,
            }

            # Storage directory information
            if os.path.exists(FILE_STORAGE_DIR):
                try:
                    total_size = sum(
                        os.path.getsize(os.path.join(FILE_STORAGE_DIR, f))
                        for f in os.listdir(FILE_STORAGE_DIR)
                        if os.path.isfile(os.path.join(FILE_STORAGE_DIR, f))
                    )
                except OSError as e:
                    logger.warning(f"Could not calculate storage directory size: {e}")
                    total_size = 0
                stats["storage_info"] = {
                    "directory": os.path.abspath(FILE_STORAGE_DIR),
                    "total_files": len(
                        [
                            f
                            for f in os.listdir(FILE_STORAGE_DIR)
                            if os.path.isfile(os.path.join(FILE_STORAGE_DIR, f))
                        ]
                    ),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                }

            # Client statistics
            if client_stats := self.execute(
                """
                SELECT
                    COUNT(*) as total_clients,
                    COUNT(CASE WHEN PublicKey IS NOT NULL THEN 1 END) as clients_with_keys,
                    AVG(CASE WHEN LastSeen IS NOT NULL THEN julianday('now') - julianday(LastSeen) END) as avg_days_since_seen
                FROM clients
            """,
                fetchone=True,
            ):
                stats["client_stats"] = {
                    "total_clients": client_stats[0],
                    "clients_with_keys": client_stats[1],
                    "average_days_since_seen": round(client_stats[2] or 0, 1),
                }

            # File statistics
            if file_stats := self.execute(
                """
                SELECT
                    COUNT(*) as total_files,
                    COUNT(CASE WHEN Verified = 1 THEN 1 END) as verified_files,
                    AVG(FileSize) as avg_file_size,
                    SUM(FileSize) as total_size,
                    MIN(FileSize) as min_size,
                    MAX(FileSize) as max_size
                FROM files
                WHERE FileSize IS NOT NULL
            """,
                fetchone=True,
            ):
                total_files = file_stats[0]
                verified_files = file_stats[1]
                avg_file_size = file_stats[2] if file_stats[2] is not None else 0
                total_size = file_stats[3] if file_stats[3] is not None else 0
                min_file_size = file_stats[4] if file_stats[4] is not None else 0
                max_file_size = file_stats[5] if file_stats[5] is not None else 0

                stats["file_stats"] = {
                    "total_files": total_files,
                    "verified_files": verified_files,
                    "verification_rate": round(
                        (verified_files / total_files * 100) if total_files > 0 else 0,
                        1,
                    ),
                    "average_file_size_mb": round(avg_file_size / (1024 * 1024), 2)
                    if avg_file_size is not None
                    else 0.0,
                    "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2)
                    if total_size is not None
                    else 0.0,
                    "min_file_size_kb": round(min_file_size / 1024, 2)
                    if min_file_size is not None
                    else 0.0,
                    "max_file_size_mb": round(max_file_size / (1024 * 1024), 2)
                    if max_file_size is not None
                    else 0.0,
                }

            # Performance info (if tables exist)
            try:
                index_info = self.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND sql IS NOT NULL
                    ORDER BY name
                """,
                    fetchall=True,
                )

                stats["performance_info"] = {
                    "indexes_count": len(index_info) if index_info else 0,
                    "indexes": [idx[0] for idx in index_info] if index_info else [],
                }
            except Exception as perf_error:
                logger.debug(
                    f"Failed to collect performance info for storage stats: {perf_error}"
                )
                stats["performance_info"] = {"indexes_count": 0, "indexes": []}

        except Exception as e:
            logger.error(f"Failed to collect storage statistics: {e}")
            stats["error"] = str(e)

        return stats

    def optimize_database(self) -> dict[str, Any]:
        """
        Perform database optimization tasks.

        Returns:
            Dictionary with optimization results
        """
        results: dict[str, Any] = {
            "vacuum_performed": False,
            "analyze_performed": False,
            "size_before_mb": 0,
            "size_after_mb": 0,
            "space_saved_mb": 0,
            "errors": [],
        }

        try:
            # Get initial size
            if os.path.exists(self.db_name):
                results["size_before_mb"] = round(
                    os.path.getsize(self.db_name) / (1024 * 1024), 2
                )

            # Perform VACUUM to reclaim space
            try:
                self.execute("VACUUM", commit=True)
                results["vacuum_performed"] = True
                logger.info("Database VACUUM completed")
            except Exception as e:
                results["errors"].append(f"VACUUM failed: {e}")
                logger.error(f"Database VACUUM failed: {e}")

            # Perform ANALYZE to update statistics
            try:
                self.execute("ANALYZE", commit=True)
                results["analyze_performed"] = True
                logger.info("Database ANALYZE completed")
            except Exception as e:
                results["errors"].append(f"ANALYZE failed: {e}")
                logger.error(f"Database ANALYZE failed: {e}")

            # Get final size
            if os.path.exists(self.db_name):
                results["size_after_mb"] = round(
                    os.path.getsize(self.db_name) / (1024 * 1024), 2
                )
                results["space_saved_mb"] = round(
                    results["size_before_mb"] - results["size_after_mb"], 2
                )

        except Exception as e:
            results["errors"].append(f"Optimization failed: {e}")
            logger.error(f"Database optimization failed: {e}")

        return results

    def backup_database_to_file(self, backup_path: str | None = None) -> str:
        """
        Create a backup of the database with proper connection pool handling.

        Args:
            backup_path: Optional custom backup path

        Returns:
            Path to the created backup file

        Raises:
            Exception: If backup fails for any reason
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_name}_backup_{timestamp}.db"

        conn = None
        backup_conn = None

        try:
            if self.use_pool and self.connection_pool:
                # Get connection from pool
                conn = self.connection_pool.get_connection()

                try:
                    # Create backup connection
                    backup_conn = sqlite3.connect(backup_path)

                    # Perform backup
                    conn.backup(backup_conn)

                    # Close backup connection before returning pool connection
                    backup_conn.close()
                    backup_conn = None

                    logger.info(f"Database backup created: {backup_path}")
                    return backup_path

                finally:
                    # Always ensure backup connection is closed
                    if backup_conn:
                        with suppress(Exception):
                            backup_conn.close()

                    # Always return connection to pool
                    if conn:
                        with suppress(Exception):
                            self.connection_pool.return_connection(conn)

            else:
                # Direct connection mode (no pool)
                with sqlite3.connect(self.db_name) as source_conn:
                    with sqlite3.connect(backup_path) as backup_conn:
                        source_conn.backup(backup_conn)

                logger.info(f"Database backup created: {backup_path}")
                return backup_path

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            # Clean up partial backup file
            with suppress(Exception):
                if backup_path and os.path.exists(backup_path):
                    os.remove(backup_path)
            raise

    def get_database_health(self) -> dict[str, Any]:
        """
        Check database health and integrity.

        Returns:
            Dictionary with health check results
        """
        health: dict[str, Any] = {
            "integrity_check": False,
            "foreign_key_check": False,
            "table_count": 0,
            "index_count": 0,
            "connection_pool_healthy": False,
            "issues": [],
        }

        try:
            # Integrity check
            result = self.execute("PRAGMA integrity_check", fetchone=True)
            if result and result[0] == "ok":
                health["integrity_check"] = True
            else:
                health["issues"].append(
                    f"Integrity check failed: {result[0] if result else 'Unknown error'}"
                )

            # Foreign key check
            if not (
                fk_results := self.execute("PRAGMA foreign_key_check", fetchall=True)
            ):  # Empty result means no foreign key violations
                health["foreign_key_check"] = True
            else:
                health["issues"].append(
                    f"Foreign key violations found: {len(fk_results)}"
                )

            # Count tables and indexes
            tables = self.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'", fetchone=True
            )
            indexes = self.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index'", fetchone=True
            )

            health["table_count"] = tables[0] if tables else 0
            health["index_count"] = indexes[0] if indexes else 0

            # Check connection pool health with detailed metrics
            if self.connection_pool:
                try:
                    # Try to get and return a connection
                    conn = self.connection_pool.get_connection()
                    conn.execute("SELECT 1")
                    self.connection_pool.return_connection(conn)
                    health["connection_pool_healthy"] = True

                    # Add detailed pool metrics
                    pool_status = self.connection_pool.get_pool_status()
                    pool_monitoring = self.monitor_connection_pool()

                    health["connection_pool_metrics"] = {
                        "enabled": True,
                        "pool_size": pool_status["pool_size"],
                        "active_connections": pool_status["active_connections"],
                        "available_connections": pool_status["available_connections"],
                        "utilization_percent": round(
                            (
                                pool_status["active_connections"]
                                / pool_status["pool_size"]
                                * 100
                            )
                            if pool_status["pool_size"] > 0
                            else 0,
                            2,
                        ),
                        "health_score": pool_monitoring.get("health_score", 100),
                        "exhaustion_events": pool_status["pool_exhaustion_events"],
                        "peak_active": pool_status["peak_active_connections"],
                        "warnings": pool_monitoring.get("warnings", []),
                        "recommendations": pool_monitoring.get("recommendations", []),
                    }

                    # Add warnings if pool health is degraded
                    if pool_monitoring.get("health_score", 100) < 70:
                        health["issues"].append(
                            f"Connection pool health degraded (score: {pool_monitoring.get('health_score')})"
                        )

                except Exception as e:
                    health["issues"].append(f"Connection pool issue: {e}")
                    health["connection_pool_metrics"] = {
                        "enabled": True,
                        "error": str(e),
                    }
            else:
                health["connection_pool_healthy"] = (
                    True  # Not using pool is also healthy
                )
                health["connection_pool_metrics"] = {"enabled": False}

        except Exception as e:
            health["issues"].append(f"Health check failed: {e}")

        return health

    def get_connection_pool_metrics(self) -> dict[str, Any] | None:
        """Get connection pool metrics and status."""
        if self.connection_pool:
            return self.connection_pool.get_pool_status()
        else:
            return {"pool_enabled": False, "message": "Connection pooling is disabled"}

    def monitor_connection_pool(self) -> dict[str, Any]:
        """Monitor connection pool for issues and return status."""
        if not self.connection_pool:
            return {
                "monitoring_enabled": False,
                "message": "Connection pooling is disabled",
                "recommendations": [
                    "Enable connection pooling for better resource management"
                ],
            }

        status = self.connection_pool.get_pool_status()
        recommendations: list[str] = []
        warnings: list[str] = []

        # Analyze pool status and generate recommendations
        pool_utilization = (
            status["active_connections"] / status["pool_size"]
            if status["pool_size"] > 0
            else 0
        )

        if pool_utilization > 0.8:
            warnings.append(f"High pool utilization: {pool_utilization:.1%}")
            recommendations.append("Consider increasing pool size")

        if status["pool_exhaustion_events"] > 5:
            warnings.append(
                f"Frequent pool exhaustion: {status['pool_exhaustion_events']} events"
            )
            recommendations.append("Investigate long-running database operations")

        if status["average_connection_age_seconds"] > 3600:  # 1 hour
            warnings.append(
                f"Long-lived connections detected: avg age {status['average_connection_age_seconds']:.0f}s"
            )
            recommendations.append("Consider reducing max_connection_age")

        return {
            "monitoring_enabled": True,
            "pool_status": status,
            "pool_utilization": pool_utilization,
            "warnings": warnings,
            "recommendations": recommendations,
            "health_score": self._calculate_pool_health_score(status),
        }

    def _calculate_pool_health_score(self, status: dict[str, Any]) -> float:
        """Calculate a health score (0-100) for the connection pool."""
        score = 100.0

        # Deduct points for various issues
        pool_utilization = (
            status["active_connections"] / status["pool_size"]
            if status["pool_size"] > 0
            else 0
        )
        if pool_utilization > 0.9:
            score -= 30
        elif pool_utilization > 0.7:
            score -= 15

        if status["pool_exhaustion_events"] > 10:
            score -= 25
        elif status["pool_exhaustion_events"] > 5:
            score -= 10

        if status["average_connection_age_seconds"] > 7200:  # 2 hours
            score -= 20
        elif status["average_connection_age_seconds"] > 3600:  # 1 hour
            score -= 10

        if not status["cleanup_thread_alive"]:
            score -= 40  # Major issue if monitoring thread is dead

        return max(0.0, score)

    def force_cleanup_connections(self) -> dict[str, Any]:
        """Force cleanup of database connections."""
        logger.info("Force cleanup of database connections requested")

        if not self.connection_pool:
            return {
                "cleanup_performed": False,
                "message": "Connection pooling is disabled",
                "recommendation": "Enable connection pooling for resource management",
            }

        result = self.connection_pool.force_cleanup()

        # Log to structured logger if available
        if structured_logger:
            structured_logger.info(  # type: ignore
                "Database connection pool force cleanup completed", **result
            )

        return result

    def check_pool_exhaustion(self) -> dict[str, Any]:
        """Check for pool exhaustion scenarios and potential issues."""
        if not self.connection_pool:
            return {"pool_enabled": False, "message": "Connection pooling is disabled"}

        status = self.connection_pool.get_pool_status()

        # Check for exhaustion indicators
        exhaustion_risk = "low"
        issues: list[str] = []

        pool_utilization = (
            status["active_connections"] / status["pool_size"]
            if status["pool_size"] > 0
            else 0
        )

        if pool_utilization > 0.9:
            exhaustion_risk = "high"
            issues.append("Pool utilization above 90%")
        elif pool_utilization > 0.7:
            exhaustion_risk = "medium"
            issues.append("Pool utilization above 70%")

        if status["pool_exhaustion_events"] > 0:
            if status["pool_exhaustion_events"] > 10:
                exhaustion_risk = "high"
            issues.append(
                f"Pool exhaustion events detected: {status['pool_exhaustion_events']}"
            )

        if status["available_connections"] == 0:
            exhaustion_risk = "critical"
            issues.append("No available connections in pool")

        return {
            "pool_enabled": True,
            "exhaustion_risk": exhaustion_risk,
            "pool_utilization": pool_utilization,
            "available_connections": status["available_connections"],
            "active_connections": status["active_connections"],
            "pool_size": status["pool_size"],
            "exhaustion_events": status["pool_exhaustion_events"],
            "issues": issues,
            "recommendations": self._get_exhaustion_recommendations(
                exhaustion_risk, issues
            ),
        }

    def _get_exhaustion_recommendations(
        self, risk_level: str, issues: list[str]
    ) -> list[str]:
        """Get recommendations based on exhaustion risk level."""
        recommendations: list[str] = []

        if risk_level == "critical":
            recommendations.extend(
                [
                    "URGENT: Force cleanup connections immediately",
                    "Investigate active database operations",
                    "Consider restarting the database service",
                ]
            )
        elif risk_level == "high":
            recommendations.extend(
                [
                    "Increase connection pool size",
                    "Force cleanup of stale connections",
                    "Review database query performance",
                ]
            )
        elif risk_level == "medium":
            recommendations.extend(
                [
                    "Monitor pool usage trends",
                    "Consider connection timeout adjustments",
                    "Review long-running operations",
                ]
            )

        return recommendations

    def cleanup_connection_pool(self):
        """Close and cleanup the connection pool."""
        if self.connection_pool:
            try:
                self.connection_pool.close_all()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")

    def check_startup_permissions(self):
        """
        Performs critical permission checks before the server starts.

        Raises:
            SystemExit: If critical permissions are not available.
        """
        logger.info("Performing database startup checks...")

        # Check write permissions for file storage directory
        if not os.access(FILE_STORAGE_DIR, os.W_OK):
            logger.critical(
                f"Fatal: No write permission for file storage directory: '{os.path.abspath(FILE_STORAGE_DIR)}'."
            )
            raise SystemExit(
                f"Startup failed: No write access to '{FILE_STORAGE_DIR}'."
            )

        # Check write permissions for the directory where the database file resides
        db_dir = os.path.dirname(os.path.abspath(self.db_name))
        if not os.access(
            db_dir or ".", os.W_OK
        ):  # Use current dir if DATABASE_NAME is relative with no path
            logger.critical(
                f"Fatal: No write permission for database directory: '{db_dir or os.path.abspath('.')}'."
            )
            raise SystemExit(
                f"Startup failed: No write access to database directory '{db_dir}'."
            )

        logger.info("Database startup permission checks passed.")

    def ensure_storage_dir(self):
        """
        Ensures that the file storage directory exists.

        Raises:
            OSError: If the directory cannot be created or accessed.
        """
        try:
            os.makedirs(
                FILE_STORAGE_DIR, exist_ok=True
            )  # exist_ok=True means no error if dir already exists
            logger.info(
                f"File storage directory is set to: '{os.path.abspath(FILE_STORAGE_DIR)}'"
            )
        except OSError as e:
            logger.critical(
                f"Fatal: Could not create or access file storage directory '{FILE_STORAGE_DIR}': {e}"
            )
            raise  # This is a critical failure, server cannot operate

    def get_table_names(self) -> list[str]:
        """
        Get list of all table names in the database.

        Returns:
            List of table names for database browser functionality.
        """
        try:
            result = self.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """,
                fetchall=True,
            )
            return [row[0] for row in result] if result else []
        except Exception as e:
            logger.error(f"Error getting table names: {e}")
            return []

    # ------------------------------------------------------------------
    # Generic table helpers used by server-side database management APIs
    # ------------------------------------------------------------------

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """Return PRAGMA table_info() details for the requested table."""
        try:
            result = self.execute(f"PRAGMA table_info({table_name})", fetchall=True)
            if not result:
                return []

            return [
                {
                    "cid": column[0],
                    "name": column[1],
                    "type": column[2] or "",
                    "notnull": bool(column[3]),
                    "default": column[4],
                    "pk": bool(column[5]),
                }
                for column in result
            ]
        except Exception as e:
            logger.error(f"Error retrieving schema for table {table_name}: {e}")
            return []

    @staticmethod
    def _row_to_dict(columns: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
        """Convert a raw SQLite row into a dictionary keyed by column name."""
        row_dict: dict[str, Any] = {}
        for index, column in enumerate(columns):
            value = row[index] if index < len(row) else None
            if isinstance(value, memoryview):
                value = bytes(value)
            if isinstance(value, (bytes, bytearray)):
                row_dict[column] = value.hex()
            elif value is None:
                row_dict[column] = ""
            else:
                row_dict[column] = value
        return row_dict

    def get_row_by_primary_key(
        self, table_name: str, primary_column: str, primary_value: Any
    ) -> dict[str, Any] | None:
        """Fetch a single row by its primary key value."""
        schema = self.get_table_schema(table_name)
        if not schema:
            return None

        columns = [col["name"] for col in schema]

        try:
            row = self.execute(
                f"SELECT * FROM {table_name} WHERE {primary_column} = ?",
                (primary_value,),
                fetchone=True,
            )
        except Exception as e:
            logger.error(f"Error fetching row from {table_name}: {e}")
            return None

        if not row:
            return None

        return self._row_to_dict(columns, row)

    def update_table_row(
        self,
        table_name: str,
        primary_column: str,
        primary_value: Any,
        updates: dict[str, Any],
    ) -> bool:
        """Execute an UPDATE against a table using the identified primary key."""
        if not updates:
            logger.warning(f"update_table_row called for {table_name} with no updates")
            return False

        set_clause = ", ".join(f"{column} = ?" for column in updates.keys())
        params: tuple[Any, ...] = tuple(updates.values()) + (primary_value,)

        query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_column} = ?"

        try:
            if self.use_pool and self.connection_pool:
                conn = self.connection_pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount > 0
                finally:
                    self.connection_pool.return_connection(conn)
            else:
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating row in {table_name}: {e}")
            return False

    def delete_table_row(
        self, table_name: str, primary_column: str, primary_value: Any
    ) -> bool:
        """Execute a DELETE statement on a table using its primary key."""
        try:
            query = f"DELETE FROM {table_name} WHERE {primary_column} = ?"
            if self.use_pool and self.connection_pool:
                conn = self.connection_pool.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, (primary_value,))
                    conn.commit()
                    return cursor.rowcount > 0
                finally:
                    self.connection_pool.return_connection(conn)
            else:
                with sqlite3.connect(self.db_name, timeout=10.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (primary_value,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting row from {table_name}: {e}")
            return False

    def get_table_content(
        self, table_name: str
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Get column names and data for a specific table.

        Args:
            table_name: Name of the table to query

        Returns:
            Tuple of (column_names, data_rows) where:
            - column_names: List of column names
            - data_rows: List of dictionaries, each representing a row
        """
        try:
            # First, get column information
            result = self.execute(f"PRAGMA table_info({table_name})", fetchall=True)
            if not result:
                return [], []

            columns = [row[1] for row in result]  # row[1] is the column name

            # Then get the table data
            data_result = self.execute(
                f"SELECT * FROM {table_name} LIMIT 1000", fetchall=True
            )  # Limit for performance
            if not data_result:
                return columns, []

            # Convert to list of dictionaries
            data_rows = [self._row_to_dict(columns, row) for row in data_result]

            return columns, data_rows

        except Exception as e:
            logger.error(f"Error getting table content for {table_name}: {e}")
            return [], []
            return [], []


# Module-level convenience functions for backward compatibility
def get_database_manager(db_name: str | None = None) -> DatabaseManager:
    """
    Factory function to get a DatabaseManager instance.

    Args:
        db_name: Optional database name override.

    Returns:
        DatabaseManager instance.
    """
    return DatabaseManager(db_name)


def init_database(db_name: str | None = None):
    """
    Initialize the database schema.

    Args:
        db_name: Optional database name override.
    """
    db_manager = DatabaseManager(db_name)
    db_manager.init_database()


def check_database_permissions():
    """Check database and storage directory permissions."""
    db_manager = DatabaseManager()
    db_manager.check_startup_permissions()
    db_manager.ensure_storage_dir()


def get_connection_pool_status(db_name: str | None = None) -> dict[str, Any]:
    """Get connection pool status for monitoring."""
    db_manager = DatabaseManager(db_name)
    result = db_manager.get_connection_pool_metrics()
    return result if result is not None else {}


def monitor_database_connections(db_name: str | None = None) -> dict[str, Any]:
    """Monitor database connections and return comprehensive status."""
    db_manager = DatabaseManager(db_name)
    return db_manager.monitor_connection_pool()
