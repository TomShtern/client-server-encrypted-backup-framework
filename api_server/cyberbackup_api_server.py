#!/usr/bin/env python3
"""
CyberBackup 3.0 API Server - CANONICAL IMPLEMENTATION
=====================================================

This is the OFFICIAL and ONLY API server for CyberBackup 3.0.

Features:
- Complete Flask API backend for NewGUIforClient.html interface
- Real integration with C++ backup client and Python backup server
- Enhanced observability and structured logging
- Performance monitoring and metrics collection
- WebSocket support for real-time communication
- File receipt monitoring and health checks
- Singleton management and comprehensive error handling
- Sentry error tracking and monitoring

Usage:
- Direct: python cyberbackup_api_server.py
- Recommended: python one_click_build_and_run.py

Port: 9090
Endpoints: /api/*, /health, /api/observability/*

NO SIMULATION - REAL INTEGRATION ONLY

Note: Other API server files have been archived to eliminate duplicates.
See API_SERVER_UNIFICATION.md for details.
"""

# Standard library imports
print("DEBUG: Starting server...", flush=True)
import contextlib
import logging
import os
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

# CRITICAL: Set up paths and UTF-8 encoding before any other imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
print("DEBUG: sys.path done", flush=True)

# Third-party imports
from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_file,
    send_from_directory,
    session,
)

print("DEBUG: flask imported", flush=True)
from flask_cors import CORS

print("DEBUG: flask_cors imported", flush=True)
from flask_socketio import SocketIO, emit

print("DEBUG: flask_socketio imported", flush=True)

print("DEBUG: Importing Shared explicitly...", flush=True)
import Shared

print(
    f"DEBUG: Shared imported explicitly. File: {getattr(Shared, '__file__', 'unknown')}",
    flush=True,
)

# First-party imports (ensure_imports() must be called first)
from Shared.path_utils import setup_imports

setup_imports()  # This must be called before any other first-party imports
print("DEBUG: setup_imports done", flush=True)

from python_server.server.connection_health import (
    get_connection_health_monitor,  # noqa: E402 # Moved from global scope
)
from python_server.server.server_singleton import (
    ensure_single_server_instance,  # noqa: E402
)
from Shared.config.unified_config import get_config  # noqa: E402
from Shared.logging.logging_utils import (  # noqa: E402
    create_enhanced_logger,
    create_log_monitor_info,
    log_performance_metrics,
    setup_dual_logging,
)
from Shared.monitoring.performance_monitor import (
    get_performance_monitor,  # noqa: E402 # Moved from api_perf_job()
)
from Shared.monitoring.unified_monitor import UnifiedFileMonitor  # noqa: E402
from Shared.observability_middleware import setup_observability_for_flask  # noqa: E402
from Shared.sentry_config import capture_error, init_sentry  # noqa: E402

# Define PROJECT_ROOT for consistent path resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global paths for static file serving
CLIENT_GUI_PATH = os.path.join(PROJECT_ROOT, "api_server", "web_ui")
PYTHON_SERVER_PATH = os.path.join(PROJECT_ROOT, "python_server")

# Initialize Sentry error tracking (after all imports)
SENTRY_INITIALIZED = init_sentry("api-server", traces_sample_rate=0.5)

# Configure enhanced dual logging (console + file) with observability
print("DEBUG: setup_dual_logging start", flush=True)
logger, api_log_file = setup_dual_logging(
    logger_name=__name__,
    server_type="api-server",
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    console_format="%(asctime)s - %(levelname)s - %(message)s",
)
print("DEBUG: setup_dual_logging done", flush=True)

# Import our real backup executor (needs to be after setup_imports and logging)
try:
    from .real_backup_executor import RealBackupExecutor
except ImportError:
    from real_backup_executor import RealBackupExecutor

# Performance monitoring singleton
perf_monitor = get_performance_monitor()
# Connection health monitoring
conn_health = get_connection_health_monitor()

# Connection management
MAX_CONNECTIONS = 10  # Increased - allow more WebSocket connections for better UX
MAX_CONNECTIONS_PER_IP = 12  # Increased to allow more concurrent connections for assets
connected_clients: set[str] = set()  # Track connected client IDs
connection_locks: dict[str, threading.Lock] = {}  # Per-IP connection limits
ip_connection_counts: dict[str, int] = {}  # Track connections per IP
active_sessions: dict[
    str, Any
] = {}  # Track active sessions per IP to prevent multiple browser instances

# File path constants (DRY principle - defined once, used multiple times)
CLIENT_GUI_HTML_FILE = "index.html"
FAVICON_PREFIX = "favicon_stuff/"
PROGRESS_CONFIG_FILE = "progress_config.json"

app: Flask = Flask(__name__)
CORS(app)  # Enable CORS for local development


# Force connection close on all HTTP responses to prevent keepalive
@app.after_request
def force_connection_close(response: Response) -> Response:
    """Force HTTP connections to close after each request"""
    response.headers["Connection"] = "close"
    response.headers["Keep-Alive"] = "timeout=1, max=1"
    return response


# Add per-IP connection limiting middleware
@app.before_request
def limit_connections_per_ip():
    """Limit the number of concurrent connections per IP address"""
    client_ip = request.remote_addr or "127.0.0.1"

    # Track connection count per IP (simplified tracking)
    current_count = ip_connection_counts.get(client_ip, 0)

    # Allow static file requests and essential endpoints with more lenient limits
    if request.endpoint in ["serve_client", "serve_client_assets"]:
        max_allowed = MAX_CONNECTIONS_PER_IP + 4  # Allow more connections for assets
    else:
        max_allowed = MAX_CONNECTIONS_PER_IP

    if current_count >= max_allowed:
        logger.warning(
            f"Connection limit exceeded for IP {client_ip}: {current_count}/{max_allowed}"
        )
        return jsonify({"error": "Too many concurrent connections"}), 429

    # Increment counter
    ip_connection_counts[client_ip] = current_count + 1


@app.after_request
def decrement_ip_connections(response: Response) -> Response:
    """Decrement connection count after request completes"""
    client_ip = request.remote_addr or "127.0.0.1"
    current_count = ip_connection_counts.get(client_ip, 0)
    if current_count > 0:
        ip_connection_counts[client_ip] = current_count - 1
    return response


# Initialize SocketIO with aggressive connection management
api_port = get_config("api.port", 9090)
socketio: SocketIO = SocketIO(
    app,
    cors_allowed_origins=[
        f"http://localhost:{api_port}",
        f"http://127.0.0.1:{api_port}",
    ],
    ping_interval=10,  # More frequent pings to detect disconnections faster
    ping_timeout=20,  # Shorter timeout to close dead connections quickly
    async_mode="threading",  # Use threading for better performance
    logger=False,  # Disable SocketIO debug logging to reduce overhead
    engineio_logger=False,  # Disable Engine.IO debug logging
    always_connect=False,  # Don't keep connections alive unnecessarily
    max_http_buffer_size=1024 * 1024,  # 1MB limit for HTTP buffer
)

# Setup enhanced observability middleware and structured logging (after app creation)
observability_middleware = setup_observability_for_flask(app, "api-server")
structured_logger = create_enhanced_logger("api-server", logger)

# --- Global Singleton Monitor ---
# This monitor will be shared across all requests.
file_monitor: UnifiedFileMonitor = UnifiedFileMonitor(
    os.path.join(PROJECT_ROOT, "received_files")
)

# Add Sentry error handlers
if SENTRY_INITIALIZED:

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors with Sentry"""
        capture_error(
            error,
            "api-server",
            {
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            },
        )
        return jsonify(
            {
                "error": "Internal server error",
                "message": "An error occurred while processing your request",
            }
        ), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors with Sentry"""
        capture_error(
            error,
            "api-server",
            {
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
                "user_agent": request.headers.get("User-Agent"),
            },
        )
        logger.error(f"Unexpected error in {request.endpoint}: {error}")
        return jsonify(
            {"error": "Unexpected error", "message": "An unexpected error occurred"}
        ), 500


# Performance monitoring singleton and Connection health monitoring are already initialized above


# --- CallbackMultiplexer for concurrent request handling ---
class CallbackMultiplexer:
    """Thread-safe callback multiplexer to prevent race conditions in concurrent requests."""

    def __init__(self) -> None:
        self._job_callbacks: dict[str, Callable[[str, Any], None]] = {}
        self._lock = threading.Lock()
        self._registered_executor: RealBackupExecutor | None = None

    def register_job_callback(
        self, job_id: str, callback: Callable[[str, Any], None]
    ) -> None:
        """Register a callback for a specific job."""
        with self._lock:
            self._job_callbacks[job_id] = callback
            # If this is the first callback and no executor registered yet, set up the multiplexer
            if self._registered_executor is None and len(self._job_callbacks) == 1:
                self._setup_global_callback()

    def remove_job_callback(self, job_id: str) -> None:
        """Remove callback for a specific job."""
        with self._lock:
            self._job_callbacks.pop(job_id, None)

    def route_callback(self, phase: str, data: Any) -> None:
        """Route callback to all active jobs (used as the global callback)."""
        callbacks_copy = {}
        with self._lock:
            callbacks_copy = self._job_callbacks.copy()

        # Call all registered callbacks
        for job_id, callback in callbacks_copy.items():
            try:
                callback(phase, data)
            except Exception as e:
                print(f"[CALLBACK_ERROR] Error in callback for job {job_id}: {e}")

    def set_executor(self, executor: "RealBackupExecutor") -> None:
        """Set the backup executor for callback registration."""
        with self._lock:
            self._registered_executor = executor

    def _setup_global_callback(self) -> None:
        """Set up the global callback on the registered executor."""
        if self._registered_executor:
            self._registered_executor.set_status_callback(self.route_callback)


# Global callback multiplexer instance
callback_multiplexer = CallbackMultiplexer()

# --- Initialize global variables & Locks ---
# For job-specific data
active_backup_jobs: dict[str, dict[str, Any]] = {}
active_backup_jobs_lock = threading.Lock()
# Keep executors in a dedicated registry so they never leak into JSON responses
job_executors: dict[str, RealBackupExecutor] = {}


def _make_json_safe(value: Any, depth: int = 0, max_depth: int = 6) -> Any:
    """Best-effort conversion of Python objects to JSON-serializable structures."""
    if depth >= max_depth:
        return str(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode("utf-8", errors="replace")

    if isinstance(value, dict):
        return {
            str(k): _make_json_safe(v, depth + 1, max_depth)
            for k, v in value.items()
            if k != "executor"
        }

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item, depth + 1, max_depth) for item in value]

    return str(value)


def _sanitize_job_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe representation of a job snapshot without executors."""
    return {
        key: _make_json_safe(value)
        for key, value in snapshot.items()
        if key != "executor"
    }


# For general, non-job-specific server status
def get_default_server_status() -> dict[str, Any]:
    return {
        "connected": False,
        "backing_up": False,
        "phase": "READY",
        "status": "ready",
        "message": "Ready for backup",
        "last_updated": datetime.now().isoformat(),
    }


server_status: dict[str, Any] = get_default_server_status()
server_status_lock = threading.Lock()
last_known_status: dict[str, Any] = get_default_server_status()

# Other globals
connection_established: bool = False
connection_timestamp: datetime | None = None
websocket_enabled: bool = True

# Server configuration with fallback error handling
try:
    server_config: dict[str, Any] = {
        "host": get_config("server.host", "127.0.0.1"),
        "port": get_config("server.port", 1256),
        "username": get_config("client.default_username", "default_user"),
    }
except Exception as e:
    logger.warning(f"get_config failed, using fallback values: {e}")
    server_config = {"host": "127.0.0.1", "port": 1256, "username": "default_user"}


def broadcast_file_receipt(event_type: str, data: dict):
    """Broadcast file receipt events to all connected clients"""
    try:
        if websocket_enabled and connected_clients:
            cast(Any, socketio).emit(
                "file_receipt",
                {"event_type": event_type, "data": data, "timestamp": time.time()},
            )
            print(f"[WEBSOCKET] Broadcasted file receipt event: {event_type}")
    except Exception as e:
        print(f"[WEBSOCKET] Error broadcasting file receipt: {e}")


def update_server_status(phase: str, message: str) -> None:
    """Update general server status with thread safety"""
    global last_known_status
    with server_status_lock:
        server_status["phase"] = phase
        server_status["message"] = message
        server_status["last_updated"] = datetime.now().isoformat()
        last_known_status = _sanitize_job_snapshot(server_status)
    print(f"[SERVER_STATUS] {phase}: {message}")


def check_backup_server_status(host: str | None = None, port: int | None = None):
    """Check if the Python backup server is reachable.

    Uses dynamic server_config host/port unless explicitly overridden.
    Backwards compatible: callers without args still work (defaults applied).
    """
    try:
        import socket

        target_host: str = host or cast(str, server_config.get("host", "127.0.0.1"))
        port_value: Any = port if port is not None else server_config.get("port", 1256)
        target_port: int = int(port_value or 1256)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((target_host, target_port))
        sock.close()
        return result == 0
    except Exception:
        return False


# --- WebSocket Event Handlers ---


@socketio.on("connect")
def handle_connect():
    """Handle WebSocket client connection with limits"""
    # Check connection limit
    if len(connected_clients) >= MAX_CONNECTIONS:
        print(f"[WEBSOCKET] Connection rejected - limit reached ({MAX_CONNECTIONS})")
        return False  # Reject connection

    # Generate a unique client ID and store it in the session
    import uuid as uuid_lib

    client_id = str(uuid_lib.uuid4())
    session["client_id"] = client_id
    connected_clients.add(client_id)
    print(
        f"[WEBSOCKET] Client connected: {client_id} (Total: {len(connected_clients)})"
    )

    # Send initial status to new client
    emit(
        "status",
        {
            "connected": check_backup_server_status(),  # dynamic via server_config
            "server_running": True,
            "timestamp": time.time(),
            "message": "WebSocket connected - real-time updates enabled",
        },
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    if client_id := session.get("client_id"):
        connected_clients.discard(client_id)
        print(
            f"[WEBSOCKET] Client disconnected: {client_id} (Total: {len(connected_clients)})"
        )


@socketio.on("request_status")
def handle_status_request(data: dict[str, Any] | None) -> None:
    """Handle client status requests via WebSocket"""
    job_id = data.get("job_id") if data else None

    if job_id:
        with active_backup_jobs_lock:
            job_snapshot = active_backup_jobs.get(job_id)
            status = (
                _sanitize_job_snapshot(job_snapshot)
                if isinstance(job_snapshot, dict)
                else dict(last_known_status)
            )
    else:
        status = dict(last_known_status)

    # Always provide the latest connection status
    status["connected"] = check_backup_server_status() and connection_established
    status["isConnected"] = status["connected"]

    emit(
        "status_response",
        {"status": status, "job_id": job_id, "timestamp": time.time()},
    )


@socketio.on("ping")
def handle_ping():
    """Handle WebSocket ping for connection testing"""
    emit("pong", {"timestamp": time.time()})


# Connection cleanup background task with proper shutdown signaling
def cleanup_stale_connections(stop_event: threading.Event | None = None) -> None:
    """Clean up stale connections periodically with graceful shutdown support"""
    logger.info("WebSocket cleanup thread started")

    while True:
        try:
            # Check for shutdown signal
            if stop_event and stop_event.is_set():
                logger.info("WebSocket cleanup thread received shutdown signal")
                break

            # Sleep with shutdown awareness (15 second intervals)
            if stop_event:
                if stop_event.wait(15):  # Wait 15 seconds or until stop signal
                    logger.info(
                        "WebSocket cleanup thread stopping due to shutdown signal"
                    )
                    break
            else:
                time.sleep(15)

            # Clean up stale clients based on connection count vs active clients
            initial_count = len(connected_clients)

            # Force disconnect any clients that exceed our limit
            if len(connected_clients) > MAX_CONNECTIONS:
                excess_clients = list(connected_clients)[MAX_CONNECTIONS:]
                for client_id in excess_clients:
                    connected_clients.discard(client_id)
                    logger.debug(f"[WEBSOCKET] Removed excess client: {client_id}")

            # Also clear out any old clients every few cycles
            if (
                len(connected_clients) > MAX_CONNECTIONS // 2
            ):  # If more than half our limit
                # Remove oldest 25% of clients to keep connections fresh
                clients_to_remove = list(connected_clients)[
                    : len(connected_clients) // 4
                ]
                for client_id in clients_to_remove:
                    connected_clients.discard(client_id)
                    logger.debug(f"[WEBSOCKET] Removed aging client: {client_id}")

            # Clean up IP connection counters (reset periodically to prevent memory leaks)
            if len(ip_connection_counts) > 50:  # If too many IPs tracked
                ip_connection_counts.clear()
                logger.debug("[HTTP] Cleared IP connection counters")

            if (
                len(connected_clients) != initial_count
                or len(ip_connection_counts) > 10
            ):
                logger.debug(
                    f"[WEBSOCKET] Cleanup complete. Active clients: {len(connected_clients)}, IP counters: {len(ip_connection_counts)}"
                )

        except Exception as e:
            logger.error(f"[WEBSOCKET] Cleanup error: {e}")
            if stop_event and stop_event.is_set():
                break

    logger.info("WebSocket cleanup thread finished")


# WebSocket cleanup thread will be started in main execution block to avoid import-time race conditions
cleanup_thread_name = None
cleanup_thread = None


def start_websocket_cleanup_thread():
    """Start the WebSocket cleanup thread after full initialization"""
    global cleanup_thread_name, cleanup_thread

    def cleanup_websocket_resources():
        """Cleanup function for WebSocket resources"""
        logger.info("Performing WebSocket resource cleanup...")
        try:
            connected_clients.clear()
            ip_connection_counts.clear()
            logger.info("WebSocket resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during WebSocket cleanup: {e}")

    try:
        # Import thread manager for proper shutdown coordination
        import os
        import sys

        sys.path.append(
            os.path.join(os.path.dirname(__file__), "..", "Shared", "utils")
        )
        from Shared.monitoring.thread_manager import create_managed_thread

        # Create managed cleanup thread
        cleanup_thread_name = create_managed_thread(
            target=cleanup_stale_connections,
            name="websocket_cleanup",
            component="flask_api_server",
            daemon=True,
            cleanup_callback=cleanup_websocket_resources,
            auto_start=True,
        )

        if cleanup_thread_name:
            logger.info(
                f"WebSocket cleanup thread registered as: {cleanup_thread_name}"
            )
        else:
            logger.warning(
                "Failed to register WebSocket cleanup thread with thread manager, falling back to basic thread"
            )
            cleanup_thread = threading.Thread(
                target=cleanup_stale_connections, daemon=True
            )
            cleanup_thread.start()

    except ImportError:
        logger.warning("Thread manager not available, using basic thread management")
        cleanup_thread = threading.Thread(target=cleanup_stale_connections, daemon=True)
        cleanup_thread.start()


# Static file serving
@app.route("/")
def serve_client():
    """Serve the main client HTML interface"""
    try:
        # Use absolute path to handle working directory issues
        # Get the absolute path to this file, then go up to api_server, then up to project root
        html_path = os.path.join(CLIENT_GUI_PATH, CLIENT_GUI_HTML_FILE)

        # Debug logging
        logger.debug(f"HTML path: {html_path}")
        logger.debug(f"HTML exists: {os.path.exists(html_path)}")

        return send_file(html_path)
    except FileNotFoundError as e:
        logger.error(f"HTML file not found: {e}")
        return (
            f"<h1>Client GUI not found</h1><p>Please ensure Client/Client-gui/{CLIENT_GUI_HTML_FILE} exists</p>",
            404,
        )
    except Exception as e:
        logger.error(f"Error serving HTML: {e}")
        return f"<h1>Server Error</h1><p>Error serving client: {e}</p>", 500


@app.route("/<path:filename>")
def serve_client_assets(filename: str):
    """Serve client assets (CSS, JS, images, etc.)"""
    # Don't serve the main HTML file through this route
    if filename in {CLIENT_GUI_HTML_FILE, "index.html"}:
        return (
            "<h1>Not Found</h1><p>The requested URL was not found on the server.</p>",
            404,
        )

    try:
        # Handle favicon requests specially - check both locations
        if (
            filename.startswith(FAVICON_PREFIX)
            or filename.startswith("favicon")
            or filename.endswith(".ico")
            or filename.endswith(".svg")
            or "favicon" in filename
        ):
            # Centralize favicon lookup to avoid duplicated logic
            favicon_dir = os.path.join(PROJECT_ROOT, FAVICON_PREFIX.rstrip("/"))
            if filename.startswith(FAVICON_PREFIX):
                actual_filename = filename[len(FAVICON_PREFIX) :]
            else:
                actual_filename = filename

            # First try project-level favicon_stuff directory
            favicon_path = os.path.join(favicon_dir, actual_filename)
            if os.path.exists(favicon_path):
                logger.debug(f"Serving favicon {actual_filename} from favicon_stuff")
                response = send_from_directory(favicon_dir, actual_filename)
                # Set proper MIME types for favicons
                if actual_filename.endswith(".svg"):
                    response.headers["Content-Type"] = "image/svg+xml"
                return response

            # Then try client directory
            client_path = os.path.join(CLIENT_GUI_PATH, filename)
            if os.path.exists(client_path):
                logger.debug(f"Serving favicon {filename} from client-gui")
                response = send_from_directory(CLIENT_GUI_PATH, filename)
                # Set proper MIME types for favicons
                if filename.endswith(".svg"):
                    response.headers["Content-Type"] = "image/svg+xml"
                return response

            # If not found, return a proper 404 without logging as error
            logger.debug(f"Favicon not found: {filename}")
            return "", 404  # Return 404 instead of 204 for missing favicons

        # Use absolute path to handle working directory issues
        client_dir = CLIENT_GUI_PATH

        # Security check: ensure the requested file is within the client directory
        requested_path = os.path.join(client_dir, filename)
        if not os.path.abspath(requested_path).startswith(os.path.abspath(client_dir)):
            logger.error(f"Attempt to access file outside client directory: {filename}")
            return "<h1>Forbidden</h1><p>Access denied</p>", 403

        logger.debug(f"Serving asset {filename} from {client_dir}")

        # Explicitly set MIME type for JavaScript modules to fix ES6 import issues
        response = send_from_directory(client_dir, filename)
        if filename.endswith((".js", ".mjs")):
            response.headers["Content-Type"] = "application/javascript; charset=utf-8"
        elif filename.endswith(".css"):
            response.headers["Content-Type"] = "text/css; charset=utf-8"

        return response
    except FileNotFoundError:
        logger.debug(f"Asset not found: {filename}")  # Changed from error to debug
        return "", 404
    except Exception as e:
        logger.debug(
            f"Error serving asset {filename}: {e}"
        )  # Debug level to reduce noise
        return "", 404  # Return 404 instead of 500 for missing assets


@app.route(f"/{PROGRESS_CONFIG_FILE}")
def serve_progress_config():
    """Serve the progress configuration file"""
    # Check several locations for progress_config.json and serve the first that exists.
    # Use contextlib.suppress to avoid race conditions where a file disappears between exists() and send_file().
    progress_config_path = os.path.join(PYTHON_SERVER_PATH, PROGRESS_CONFIG_FILE)
    root_config_path = os.path.join(PROJECT_ROOT, PROGRESS_CONFIG_FILE)
    candidate_paths = [
        progress_config_path,
        root_config_path,
        os.path.join(os.getcwd(), PROGRESS_CONFIG_FILE),
    ]

    for p in candidate_paths:
        with contextlib.suppress(Exception):
            if os.path.exists(p):
                return send_file(p)

    return jsonify({"error": f"{PROGRESS_CONFIG_FILE} not found"}), 404


@app.route("/favicon.ico")
def serve_favicon():
    """Serve favicon with better error handling"""
    try:
        # Try to serve favicon from Client-gui directory if it exists
        favicon_path = os.path.join(CLIENT_GUI_PATH, "favicon.ico")

        # Return favicon if it exists, otherwise return 204
        return send_file(favicon_path) if os.path.exists(favicon_path) else ("", 204)
    except Exception as e:
        logger.debug(f"Favicon serving error (non-critical): {e}")
        return "", 204


# API Endpoints for CyberBackup 3.0


@app.route("/api/test", methods=["POST"])
def api_test():
    """Simple test endpoint to debug POST requests"""
    print("[DEBUG] Test POST endpoint called!")
    return jsonify({"success": True, "message": "POST test successful"})


@app.route("/api/status")
def api_status():
    """Get current backup status with proper connection state management and timeout protection"""
    global connection_established

    job_id = request.args.get("job_id")
    status = None

    if job_id:
        with active_backup_jobs_lock:
            if job_status := active_backup_jobs.get(job_id):
                events_to_send = job_status.get("events", [])
                # Clear events after pulling snapshot
                active_backup_jobs[job_id]["events"] = []
                snapshot = dict(job_status)
                snapshot["events"] = events_to_send
                status = _sanitize_job_snapshot(snapshot)

    if status is None:
        # No job_id provided or job_id not found, return general server status
        with server_status_lock:
            status = _sanitize_job_snapshot(server_status)
        status["backing_up"] = False  # General status is never "backing up"

    # Always provide the latest connection status
    server_reachable = check_backup_server_status()
    if server_reachable and not connection_established:
        connection_established = True
        logger.info("Connection to backup server established via /api/status")

    status["connected"] = server_reachable and connection_established
    status["isConnected"] = status["connected"]

    return jsonify(status)


@app.route("/health")
def health_check():
    """Enhanced health check endpoint with timeout protection"""
    import psutil

    try:
        # Quick health check with timeout protection
        server_running = check_backup_server_status()

        # Get system metrics
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            active_connections = (
                len(connected_clients) if "connected_clients" in globals() else 0
            )
        except Exception:
            cpu_usage = memory_usage = active_connections = 0

        with active_backup_jobs_lock:
            active_jobs_count = len(active_backup_jobs)

        return jsonify(
            {
                "status": "healthy" if server_running else "degraded",
                "backup_server_status": "running" if server_running else "not_running",
                "backup_server": "running" if server_running else "not_running",
                "api_server": "running",
                "system_metrics": {
                    "cpu_usage_percent": cpu_usage,
                    "memory_usage_percent": memory_usage,
                    "active_websocket_connections": active_connections,
                    "active_backup_jobs": active_jobs_count,
                },
                "timestamp": datetime.now().isoformat(),
                "uptime_info": "API server responsive",
            }
        )
    except Exception as e:
        # Even health check can fail - provide minimal response
        return jsonify(
            {
                "status": "error",
                "api_server": "running_with_errors",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        ), 500


# Add /api/health as an alias to the same function
@app.route("/api/health")
def api_health_check():
    """Alias for health check endpoint that browser expects"""
    return health_check()


@app.route("/api/connect", methods=["POST"])
def api_connect():
    """Connect to backup server with configuration using real backup protocol"""
    global server_config, connection_established, connection_timestamp

    print("[DEBUG] /api/connect endpoint called")
    print(f"[DEBUG] Request method: {request.method}")
    print(f"[DEBUG] Request headers: {dict(request.headers)}")
    print(f"[DEBUG] Request data: {request.get_data()}")

    try:
        # Handle both JSON and form data
        if request.is_json:
            config = request.get_json()
            print(f"[DEBUG] JSON data received: {config}")
        else:
            config = request.form.to_dict()
            print(f"[DEBUG] Form data received: {config}")

        if not config:
            return jsonify(
                {"success": False, "error": "No configuration data provided"}
            ), 400

        # Normalize field naming (accept legacy 'server' alias for 'host')
        if "server" in config:
            if "host" not in config:
                config["host"] = config["server"]
            elif config["server"] != config["host"]:
                logger.warning(
                    f"Both 'server' ({config['server']}) and 'host' ({config['host']}) provided; using 'host'."
                )
            config.pop("server")

        # Validate required fields
        required_fields = ["host", "port", "username"]

        if missing_fields := [
            field
            for field in required_fields
            if field not in config or not config[field]
        ]:
            return jsonify(
                {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                }
            ), 400

        # Update server configuration
        if config:
            server_config.update(cast(dict[str, Any], config))

        update_server_status(
            "CONNECT",
            f"Testing connection to {server_config['host']}:{server_config['port']}...",
        )

        # Test if backup server is reachable
        server_reachable = check_backup_server_status(
            server_config["host"], server_config["port"]
        )

        message = ""
        if server_reachable:
            connection_established = True
            connection_timestamp = datetime.now()
            message = f"Connected to backup server at {server_config['host']}:{server_config['port']}"
            update_server_status("READY", "Connected successfully. Ready for backup.")
            print(
                f"[DEBUG] Connection established at {connection_timestamp.isoformat()}"
            )
        else:
            connection_established = False
            connection_timestamp = None
            message = "Connection failed: Backup server not responding"
            update_server_status(
                "ERROR", "Connection test failed: Backup server not responding"
            )
            print("[DEBUG] Connection failed - server not reachable")

        return jsonify(
            {
                "success": server_reachable,
                "connected": server_reachable,
                "message": message,
                "server_config": server_config,
            }
        )

    except Exception as e:
        error_msg = f"Connection error: {e!s}"
        print(f"[ERROR] {error_msg}")
        update_server_status("ERROR", error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    """Disconnect from backup server"""
    global connection_established, connection_timestamp

    print("[DEBUG] /api/disconnect called")

    try:
        connection_established = False
        connection_timestamp = None

        update_server_status("READY", "Disconnected from backup server")
        print("[DEBUG] Connection terminated")

        return jsonify(
            {
                "success": True,
                "connected": False,
                "message": "Disconnected successfully",
            }
        )

    except Exception as e:
        error_msg = f"Disconnect error: {e!s}"
        print(f"[ERROR] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/start_backup", methods=["POST"])
def api_start_backup_working():
    """Start backup using REAL backup executor with enhanced observability"""
    start_time = time.time()

    structured_logger.info("Backup request received", operation="start_backup")

    # Generate unique job ID for this backup operation
    job_id = f"job_{int(time.time() * 1000000)}"

    # Initialize job tracking
    with active_backup_jobs_lock:
        active_backup_jobs[job_id] = {
            "phase": "INITIALIZING",
            "message": "Initializing backup job...",
            "progress": {
                "percentage": 0,
                "current_file": "",
                "bytes_transferred": 0,
                "total_bytes": 0,
            },
            "status": "initializing",
            "events": [],
            "connected": True,
            "backing_up": True,
            "last_updated": datetime.now().isoformat(),
        }

    # Create a new, dedicated backup executor for this specific job.
    try:
        api_server_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(api_server_dir)
        client_exe_path = os.path.join(
            project_root, "build", "Release", "EncryptedBackupClient.exe"
        )

        backup_executor = RealBackupExecutor(client_exe_path)
        with active_backup_jobs_lock:
            job_executors[job_id] = backup_executor

        # Register executor with callback multiplexer for thread-safe callback routing
        callback_multiplexer.set_executor(backup_executor)
        print(
            f"[Job {job_id}] RealBackupExecutor instance created with client: {client_exe_path}"
        )
    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Failed to initialize backup executor: {e}"}
        ), 500

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    try:
        temp_dir = tempfile.mkdtemp()
        original_filename = file.filename or f"backup_file_{int(time.time())}"
        safe_temp_name = f"upload_{int(time.time() * 1000000)}_{original_filename}"
        temp_file_path = os.path.join(temp_dir, safe_temp_name)

        total_bytes = None
        with contextlib.suppress(Exception):
            total_bytes = os.path.getsize(temp_file_path)
        with contextlib.suppress(Exception):
            perf_monitor.start_job(job_id, total_bytes=total_bytes)

        print(f"[DEBUG] Original filename: {original_filename}")
        print(f"[DEBUG] Temp file path: {temp_file_path}")

        file.save(temp_file_path)

        username: str = str(
            request.form.get("username")
            or server_config.get("username", "default_user")
        )
        server_ip: str = str(
            request.form.get("host")
            or request.form.get("server")
            or server_config.get("host", "127.0.0.1")
        )
        server_port_val: Any = request.form.get("port", server_config.get("port", 1256))
        server_port: int = int(server_port_val or 1256)

        def status_handler(phase: str, data: Any) -> None:
            global last_known_status
            with active_backup_jobs_lock:
                if job_id not in active_backup_jobs:
                    return

                job_data = active_backup_jobs[job_id]
                safe_event_data = _make_json_safe(data)
                job_data["events"].append({"phase": phase, "data": safe_event_data})
                job_data["phase"] = phase
                job_data["last_updated"] = datetime.now().isoformat()

                if isinstance(data, dict):
                    data_dict = cast(dict[str, Any], data)
                    job_data["message"] = str(data_dict.get("message", phase))
                    if "progress" in data_dict:
                        job_data["progress"]["percentage"] = data_dict["progress"]
                    if "bytes_transferred" in data_dict:
                        job_data["progress"]["bytes_transferred"] = data_dict[
                            "bytes_transferred"
                        ]
                    if "total_bytes" in data_dict:
                        job_data["progress"]["total_bytes"] = data_dict["total_bytes"]
                else:
                    job_data["message"] = str(safe_event_data)

                last_known_status = _sanitize_job_snapshot(job_data)

            # Real-time WebSocket broadcasting
            if websocket_enabled and connected_clients:
                try:
                    cast(Any, socketio).emit(
                        "progress_update",
                        {
                            "job_id": job_id,
                            "phase": phase,
                            "data": data,
                            "timestamp": time.time(),
                        },
                    )
                except Exception as e:
                    print(f"[WEBSOCKET] Broadcast failed: {e}")

        # Register job-specific callback with multiplexer (prevents race conditions)
        callback_multiplexer.register_job_callback(job_id, status_handler)

        with active_backup_jobs_lock:
            active_backup_jobs[job_id]["backing_up"] = True
            active_backup_jobs[job_id]["phase"] = "BACKUP_IN_PROGRESS"
            active_backup_jobs[job_id]["progress"]["current_file"] = original_filename
            active_backup_jobs[job_id]["message"] = (
                f"Starting backup of {original_filename}..."
            )

        def run_backup(
            executor: RealBackupExecutor,
            temp_file_path_for_thread: str,
            filename_for_thread: str,
            temp_dir_for_thread: str,
        ) -> None:
            try:
                expected_size = os.path.getsize(temp_file_path_for_thread)
                # Use streaming hash calculation to prevent memory overflow on large files
                from Shared.filesystem.streaming_file_utils import (
                    calculate_file_hash_streaming,
                )

                expected_hash = calculate_file_hash_streaming(
                    temp_file_path_for_thread, "sha256"
                )
                if expected_hash is None:
                    raise RuntimeError(
                        "Failed to calculate file hash - file may be inaccessible"
                    )
                logger.info(
                    f"[Job {job_id}] Calculated verification data: Size={expected_size}, Hash={expected_hash[:8]}..."
                )

                def on_completion(_result: Any) -> None:
                    logger.info(
                        f"[Job {job_id}] Received VERIFIED COMPLETION signal for '{filename_for_thread}'. Forcing 100%."
                    )
                    with active_backup_jobs_lock:
                        if job_id in active_backup_jobs:
                            active_backup_jobs[job_id]["phase"] = "COMPLETED_VERIFIED"
                            active_backup_jobs[job_id]["message"] = (
                                "Backup complete and cryptographically verified."
                            )
                            active_backup_jobs[job_id]["progress"]["percentage"] = 100
                            active_backup_jobs[job_id]["backing_up"] = False

                def on_failure(reason: str) -> None:
                    logger.error(
                        f"[Job {job_id}] Received VERIFICATION FAILED signal for '{filename_for_thread}': {reason}"
                    )
                    with active_backup_jobs_lock:
                        if job_id in active_backup_jobs:
                            active_backup_jobs[job_id]["phase"] = "VERIFICATION_FAILED"
                            active_backup_jobs[job_id]["message"] = (
                                f"CRITICAL: {reason}"
                            )
                            active_backup_jobs[job_id]["backing_up"] = False

                monitor = file_monitor
                if monitor:
                    monitor.register_job(
                        filename=filename_for_thread,
                        job_id=job_id,
                        expected_size=expected_size,
                        expected_hash=expected_hash,
                        completion_callback=on_completion,
                        failure_callback=on_failure,
                    )
                else:
                    logger.warning(
                        f"[Job {job_id}] File receipt monitor not available. Verification will be skipped."
                    )

                result = executor.execute_real_backup(
                    username=username,
                    file_path=temp_file_path_for_thread,
                    server_ip=server_ip,
                    server_port=server_port,
                )

                with active_backup_jobs_lock:
                    if job_id in active_backup_jobs:
                        if result and result.get("success"):
                            active_backup_jobs[job_id]["phase"] = "COMPLETED"
                            active_backup_jobs[job_id]["message"] = (
                                "Backup completed successfully!"
                            )
                            active_backup_jobs[job_id]["progress"]["percentage"] = 100
                        else:
                            error_msg = (
                                result.get("error", "Unknown error")
                                if result
                                else "Backup executor returned None"
                            )
                            active_backup_jobs[job_id]["phase"] = "FAILED"
                            active_backup_jobs[job_id]["message"] = (
                                f"Backup failed: {error_msg}"
                            )
                        active_backup_jobs[job_id]["backing_up"] = False

            except Exception as e:
                with active_backup_jobs_lock:
                    if job_id in active_backup_jobs:
                        active_backup_jobs[job_id]["phase"] = "FAILED"
                        active_backup_jobs[job_id]["message"] = f"Backup error: {e!s}"
                        active_backup_jobs[job_id]["backing_up"] = False
                print(f"[ERROR] Backup thread error: {e!s}")
            finally:
                # Clean up callback registration to prevent memory leaks
                callback_multiplexer.remove_job_callback(job_id)
                with active_backup_jobs_lock:
                    job_executors.pop(job_id, None)
                print(f"[DEBUG] Removed callback for job {job_id}")

                if os.path.exists(temp_file_path_for_thread):
                    os.remove(temp_file_path_for_thread)
                if os.path.exists(temp_dir_for_thread):
                    os.rmdir(temp_dir_for_thread)
                print(f"[DEBUG] Cleanup successful for: {temp_file_path_for_thread}")
                update_server_status("READY", "Ready for new backup.")

        backup_thread = threading.Thread(
            target=run_backup,
            args=(backup_executor, temp_file_path, original_filename, temp_dir),
        )
        backup_thread.daemon = True
        backup_thread.start()

        duration_ms = (time.time() - start_time) * 1000
        structured_logger.info(
            f"Backup job {job_id} started successfully",
            operation="start_backup",
            duration_ms=duration_ms,
            context={
                "job_id": job_id,
                "username": username,
                "filename": original_filename,
            },
        )

        log_performance_metrics(
            logger, "start_backup", duration_ms, True, job_id=job_id, username=username
        )

        return jsonify(
            {
                "success": True,
                "message": f"Backup started for {original_filename}",
                "filename": original_filename,
                "username": username,
                "job_id": job_id,
            }
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Backup start error: {e!s}"

        structured_logger.error(
            error_msg,
            operation="start_backup",
            duration_ms=duration_ms,
            error_code=type(e).__name__,
            context={"exception": str(e)},
        )

        log_performance_metrics(
            logger, "start_backup", duration_ms, False, error=str(e)
        )

        print(f"[ERROR] {error_msg}")
        update_server_status("ERROR", error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/stop", methods=["POST"])
def api_stop_backup():
    """Stop the current backup operation"""
    try:
        # Note: The C++ client doesn't support stop/pause/resume directly
        # This endpoint provides compatibility with the web GUI but has limited functionality
        logger.info("Stop backup requested via API")
        return jsonify(
            {
                "success": True,
                "message": "Stop command sent (note: C++ client handles connection lifecycle independently)",
            }
        )
    except Exception as e:
        error_msg = f"Error stopping backup: {e!s}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/pause", methods=["POST"])
def api_pause_backup():
    """Pause the current backup operation"""
    try:
        # Note: The C++ client doesn't support pause directly
        # This endpoint provides compatibility with the web GUI
        logger.info("Pause backup requested via API")
        return jsonify(
            {
                "success": True,
                "message": "Pause command acknowledged (note: C++ client handles transfers atomically)",
            }
        )
    except Exception as e:
        error_msg = f"Error pausing backup: {e!s}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/resume", methods=["POST"])
def api_resume_backup():
    """Resume a paused backup operation"""
    try:
        # Note: The C++ client doesn't support resume directly
        # This endpoint provides compatibility with the web GUI
        logger.info("Resume backup requested via API")
        return jsonify({"success": True, "message": "Resume command acknowledged"})
    except Exception as e:
        error_msg = f"Error resuming backup: {e!s}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/server_info", methods=["GET"])
def api_server_info():
    """Get server information and status"""
    try:
        # Get server configuration and status
        backup_server_port = get_config("server.port", 1256)
        return jsonify(
            {
                "success": True,
                "server": {
                    "version": "3.0",
                    "name": "CyberBackup API Server",
                    "port": 9090,
                    "backup_server_port": backup_server_port,
                    "uptime": "N/A",  # Could be calculated from start time
                    "status": "running",
                },
            }
        )
    except Exception as e:
        error_msg = f"Error getting server info: {e!s}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/check_receipt/<filename>")
def api_check_file_receipt(filename: str):
    """Check if a specific file has been received by the server"""
    try:
        monitor = file_monitor
        if not monitor:
            return jsonify(
                {
                    "success": False,
                    "error": "File receipt monitoring not available",
                    "received": False,
                }
            ), 503

        receipt_info = monitor.check_file_receipt(filename)

        return jsonify({"success": True, "filename": filename, **receipt_info})

    except Exception as e:
        error_msg = f"Error checking file receipt: {e!s}"
        print(f"[ERROR] {error_msg}")
        return jsonify({"success": False, "error": error_msg, "received": False}), 500


@app.route("/api/received_files")
def api_list_received_files():
    """List all files that have been received by the server"""
    try:
        monitor = file_monitor
        if not monitor:
            return jsonify(
                {"success": False, "error": "File receipt monitoring not available"}
            ), 503

        files_info = monitor.list_received_files()
        return jsonify(files_info)

    except Exception as e:
        error_msg = f"Error listing received files: {e!s}"
        print(f"[ERROR] {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/api/monitor_status")
def api_monitor_status():
    """Get file receipt monitoring status"""
    try:
        monitor = file_monitor
        if not monitor:
            return jsonify(
                {
                    "monitoring_active": False,
                    "error": "File receipt monitoring not initialized",
                }
            )

        status = monitor.get_monitoring_status()
        return jsonify(status)

    except Exception as e:
        error_msg = f"Error getting monitor status: {e!s}"
        print(f"[ERROR] {error_msg}")
        return jsonify({"monitoring_active": False, "error": error_msg}), 500


@app.route("/api/server/connection_health")
def api_server_connection_health():
    """Get server connection health status"""
    try:
        return jsonify({"success": True, "connections": conn_health.get_summary()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Enhanced server startup with WebSocket support ---

if __name__ == "__main__":
    print("=" * 70)
    print("* CyberBackup 3.0 API Server - REAL Integration")
    print("=" * 70)
    print("* API Server: http://localhost:9090")
    print("* Client GUI: http://localhost:9090/")
    print("* Health Check: http://localhost:9090/health")
    print()

    # Display logging information
    log_monitor_info = create_log_monitor_info(api_log_file, "API Server")
    print("* Logging Information:")
    print(f"* Log File: {log_monitor_info.get('file_path', api_log_file)}")
    print(
        f"* Live Monitor (PowerShell): {log_monitor_info.get('powershell_cmd', 'N/A')}"
    )
    print("* Console Output: Visible in this window (dual output enabled)")
    print()

    # Check components
    print("Component Status:")

    # Check HTML client
    client_html = os.path.join(CLIENT_GUI_PATH, CLIENT_GUI_HTML_FILE)
    if os.path.exists(client_html):
        print(f"[OK] HTML Client: {client_html}")
    else:
        print(f"[MISSING] HTML Client: {client_html} NOT FOUND")

    # Check C++ client
    client_exe = os.path.join(
        PROJECT_ROOT, "build", "Release", "EncryptedBackupClient.exe"
    )
    if os.path.exists(client_exe):
        print(f"[OK] C++ Client: {client_exe}")
    else:
        print(f"[MISSING] C++ Client: {client_exe} NOT FOUND")

    # Check backup server
    if server_running := check_backup_server_status():
        print("[OK] Backup Server: Running on port 1256")
    else:
        print("[WARNING] Backup Server: Not running on port 1256")

    print()

    print("[ROCKET] Starting Flask API server with WebSocket support...")

    # Initialize and start the UnifiedFileMonitor
    try:
        file_monitor.start_monitoring()
        print(f"[OK] Unified File Monitor: Watching {file_monitor.watched_directory}")
    except Exception as e:
        print(f"[WARNING] Unified File Monitor: Failed to initialize - {e}")

    # Ensure only one API server instance runs at a time
    print("Ensuring single API server instance...")
    ensure_single_server_instance("APIServer", 9090)
    print("Singleton lock acquired for API server")

    # Start WebSocket cleanup thread after full initialization
    print("Starting WebSocket cleanup thread...")
    start_websocket_cleanup_thread()

    try:
        print("[WEBSOCKET] Starting Flask-SocketIO server with real-time support...")
        print("[DEBUG] About to call socketio.run()...")
        cast(Any, socketio).run(
            app,
            host=get_config("api.host", "127.0.0.1"),
            port=get_config("api.port", 9090),
            debug=False,
            allow_unsafe_werkzeug=True,  # Allow threading with SocketIO
            use_reloader=False,
        )
        print("[DEBUG] socketio.run() returned normally")
    except KeyboardInterrupt:
        print("\n[INFO] API Server shutdown requested")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("[DEBUG] Entering finally block...")
        # Cleanup the unified monitor
        try:
            file_monitor.stop_monitoring()
            print("[INFO] Unified file monitor stopped")
        except Exception as e:
            print(f"[WARNING] Error stopping unified file monitor: {e}")
        print("[DEBUG] API Server process ending...")


# --- Performance Monitoring Endpoints (after primary routes) ---
@app.route("/api/perf/<job_id>")
def api_perf_job(job_id: str):
    try:
        if not (summary := perf_monitor.get_job_summary(job_id)):
            return jsonify(
                {"success": False, "error": f"No performance data for job_id={job_id}"}
            ), 404
        return jsonify({"success": True, "job": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Cancellation Endpoint ---
@app.route("/api/cancel/<job_id>", methods=["POST"])
def api_cancel_job(job_id: str):
    try:
        with active_backup_jobs_lock:
            job = active_backup_jobs.get(job_id)
            executor = job_executors.get(job_id)
        if not job:
            return jsonify({"success": False, "error": f"Unknown job_id={job_id}"}), 404
        if not executor:
            return jsonify(
                {"success": False, "error": "No executor associated with this job"}
            ), 400
        ok = False
        try:
            # executor is dynamically attached; cast to Any for type checker
            ok = cast(Any, executor).cancel("API cancellation")
        except Exception as e:
            return jsonify({"success": False, "error": f"Cancel failed: {e}"}), 500
        # Update job state
        # Attach optional cancel reason to job record for UI consumption
        cancel_reason = None
        try:
            if request and request.is_json:
                if data := cast(dict[str, Any] | None, request.get_json(silent=True)):
                    cancel_reason = data.get("reason")
        except Exception:
            cancel_reason = None
        job_snapshot: dict[str, Any] | None = None
        with active_backup_jobs_lock:
            if job_id in active_backup_jobs:
                job_ref = active_backup_jobs[job_id]
                job_ref["phase"] = "CANCELLED" if ok else "CANCEL_REQUESTED"
                job_ref["message"] = (
                    "Backup cancelled" if ok else "Cancellation requested"
                )
                if cancel_reason:
                    job_ref["cancel_reason"] = cancel_reason
                if ok:
                    job_ref["progress"]["percentage"] = max(
                        job_ref["progress"].get("percentage", 0), 0
                    )
                job_snapshot = _sanitize_job_snapshot(job_ref)
                global last_known_status
                last_known_status = job_snapshot
        # Broadcast over WebSocket if enabled
        try:
            if websocket_enabled and connected_clients:
                payload = {
                    "job_id": job_id,
                    "success": ok,
                    "timestamp": time.time(),
                }
                if job_snapshot:
                    payload["phase"] = job_snapshot.get("phase")
                    payload["reason"] = job_snapshot.get("cancel_reason")
                cast(Any, socketio).emit("job_cancelled", payload)
        except Exception as be:
            print(f"[WEBSOCKET] Cancel broadcast failed: {be}")
        response_payload = {"success": ok, "job_id": job_id}
        if job_snapshot:
            response_payload["phase"] = job_snapshot.get("phase")
            if "cancel_reason" in job_snapshot:
                response_payload["reason"] = job_snapshot["cancel_reason"]
        return jsonify(response_payload)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Cancel All Endpoint ---
@app.route("/api/cancel_all", methods=["POST"])
def api_cancel_all_jobs():
    try:
        results: dict[str, bool] = {}
        job_snapshots: dict[str, dict[str, Any]] = {}
        # Iterate directly over job_executors.items(). Removed unnecessary list() wrapper.
        for jid, executor in job_executors.items():
            try:
                ok = cast(Any, executor).cancel("API cancel all")
            except Exception:
                ok = False
            with active_backup_jobs_lock:
                job_ref = active_backup_jobs.get(jid)
                if job_ref:
                    job_ref["phase"] = (
                        "CANCELLED" if ok else job_ref.get("phase", "UNKNOWN")
                    )
                    job_ref["message"] = (
                        "Backup cancelled" if ok else job_ref.get("message", "")
                    )
                    job_snapshots[jid] = _sanitize_job_snapshot(job_ref)
            results[jid] = ok
        # Broadcast
        try:
            if websocket_enabled and connected_clients:
                cast(Any, socketio).emit(
                    "jobs_cancelled",
                    {
                        "results": results,
                        "jobs": job_snapshots,
                        "timestamp": time.time(),
                    },
                )
        except Exception as be:
            print(f"[WEBSOCKET] Cancel-all broadcast failed: {be}")
        return jsonify({"success": True, "results": results, "jobs": job_snapshots})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- Cancelable Jobs Endpoint ---
@app.route("/api/cancelable_jobs", methods=["GET"])
def api_cancelable_jobs():
    try:
        items: list[dict[str, Any]] = []
        with active_backup_jobs_lock:
            for jid, job in active_backup_jobs.items():
                # A job is cancelable if we have an executor and it is not in a terminal phase
                has_executor = jid in job_executors
                phase = job.get("phase")
                if not has_executor or phase in [
                    "COMPLETED",
                    "FAILED",
                    "ERROR",
                    "CANCELLED",
                ]:
                    continue
                snapshot = _sanitize_job_snapshot(job)
                items.append(
                    {
                        "job_id": jid,
                        "phase": snapshot.get("phase"),
                        "file": snapshot.get("progress", {}).get("current_file")
                        if isinstance(snapshot.get("progress"), dict)
                        else None,
                        "progress": snapshot.get("progress", {}).get("percentage")
                        if isinstance(snapshot.get("progress"), dict)
                        else None,
                        "message": snapshot.get("message"),
                    }
                )
        return jsonify({"success": True, "jobs": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/perf")
def api_perf_all():
    try:
        return jsonify({"success": True, "jobs": perf_monitor.get_all_summaries()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
