#!/usr/bin/env python3
"""
Start FletV2 GUI with Real BackupServer Integration

This launcher creates a BackupServer instance and integrates it directly with
the Flet GUI, enabling full CRUD operations and real-time server monitoring.

Usage:
    cd FletV2 && python start_with_server.py

Features:
    - Real server instance (not mock data)
    - Direct method calls (not API calls)
    - Full CRUD operations on clients/files
    - Real-time logs and metrics
    - Database integration
"""

import os
import socket
import sys

# Add repository root to path for imports
# Add repository root to path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_flet_v2_dir = os.path.dirname(_script_dir)
_repo_root = os.path.dirname(_flet_v2_dir)

for _path in (_script_dir, _flet_v2_dir, _repo_root):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Configure environment for GUI integration
os.environ["CYBERBACKUP_DISABLE_INTEGRATED_GUI"] = "1"  # Disable server's embedded GUI
os.environ["CYBERBACKUP_DISABLE_GUI"] = "1"  # Use standalone FletV2 GUI instead
os.environ["PYTHONNOUSERSITE"] = "1"  # Prevent package conflicts from user site-packages

# Debugging flags (disabled for production use - causes severe performance degradation)
# os.environ['FLET_DASHBOARD_DEBUG'] = '1'  # Uncomment only for dashboard diagnostics
# os.environ['FLET_DASHBOARD_CONTENT_DEBUG'] = '1'  # Uncomment only for content debugging

print("=" * 70)
print(">> Starting Flet GUI with Real BackupServer Integration")
print("=" * 70)

# Initialize log capture VERY EARLY (before any other imports)
# This ensures all Flet framework and application logs are captured
print("\n[0/4] Initializing log capture system...")
try:
    from Shared.logging.flet_log_capture import get_flet_log_capture

    _log_capture = get_flet_log_capture()
    print("[OK] Log capture initialized - ready to capture framework and app logs")
except Exception as e:
    print(f"[WARNING] Failed to initialize log capture: {e}")
    print("Logs view may not display Flet framework logs correctly.")

# Import the real server
print("\n[1/4] Importing BackupServer...")
try:
    from python_server.server.server import BackupServer

    print("[OK] BackupServer imported successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import BackupServer: {e}")
    print("\nMake sure python_server/ is in the correct location.")
    sys.exit(1)

# Import Flet
print("\n[2/4] Importing Flet...")
import flet as ft
import main

# Initialize BackupServer in MAIN thread (signal handlers require main thread)
print("\n[3/4] Initializing BackupServer (main thread)...")
server_instance = None
try:
    print("[INIT] Creating BackupServer instance in main thread (signals enabled)...")
    server_instance = BackupServer()
    print("[OK] BackupServer instance created successfully")

    # CRITICAL: Start network server to accept C++ client connections
    print("[INIT] Starting network server on port 1256...")
    server_instance.start()  # Launches NetworkServer in daemon thread (non-blocking)
    print("[OK] Network server started - ready for client connections")
    print("[INFO] C++ backup clients can now connect via API server")

except Exception as init_err:
    print(f"[ERROR] BackupServer initialization failed: {init_err}")
    import traceback as _tb

    _tb.print_exc()
    print("[WARN] Proceeding without real server (GUI-only mode)")
    server_instance = None

# Launch Flet GUI with server instance
print("\n[4/4] Launching Flet GUI...")
print("=" * 70)

# Store app instance to prevent multiple creations
_app_instance = None


def gui_with_server_main(page: ft.Page):
    """
    Initialize FletV2App with real server instance as native desktop application.

    Configures desktop window properties and integrates with BackupServer.
    The server object is passed to ServerBridge for direct method calls (no API layer).
    """
    global _app_instance

    # Configure desktop window (only works in FLET_APP mode)
    page.title = "CyberBackup 3.0 - Server Administration"
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 600
    page.window.resizable = True
    page.window.center()  # Center window on screen at launch
    page.update()  # Apply window configuration immediately

    print("🟢 [START] gui_with_server_main function ENTERED")
    print("🟢 [WINDOW] Desktop window configured: 1200x800, resizable, centered")
    print(f"🟢 [START] Page object: {page}")
    print(f"🟢 [START] Server instance available: {server_instance is not None}")

    print("\n[PAGE CONNECT] New page connection established")

    # Server already initialized (or failed) before ft.app launch
    print(f"   Server Instance: {'[OK] Connected' if server_instance else '[WARN]  Mock Mode'}")

    # Create FletV2App with real server
    app = main.FletV2App(page, real_server=server_instance)

    # Set up cleanup handler for when page disconnects
    def cleanup_on_disconnect(e):
        print("\n[PAGE DISCONNECT] Cleaning up resources...")
        try:
            # Call dispose function if it exists
            if hasattr(app, "dispose") and callable(app.dispose):
                app.dispose()
            # Clean up current view
            if hasattr(app, "_current_view_dispose") and app._current_view_dispose:
                app._current_view_dispose()
            print("[OK] Resources cleaned up")
        except Exception as cleanup_err:
            print(f"[WARN] Cleanup error: {cleanup_err}")

    page.on_disconnect = cleanup_on_disconnect

    # Initialize the app using Flet's task runner
    async def async_init():
        try:
            print("[INIT] Starting async initialization...")
            print(f"[DEBUG] App object: {app}")
            print(f"[DEBUG] App.initialize callable? {callable(getattr(app, 'initialize', None))}")
            print("[DEBUG] About to await app.initialize()...")
            await app.initialize()
            print("[DEBUG] app.initialize() returned successfully")
            print(f"\n{'=' * 70}")
            print(f"{'[READY] FletV2 GUI is Running':^70}")
            if server_instance:
                print(f"{'[OK] Real server connected - Full CRUD operational':^70}")
            else:
                print(f"{'[WARN]  Mock mode - Server connection failed':^70}")
            print(f"{'=' * 70}\n")
        except Exception as init_err:
            print(f"[ERROR] App initialization failed: {init_err}")
            import traceback

            traceback.print_exc()

    #  Schedule initialization
    print("[DEBUG] Scheduling async initialization task...")
    page.run_task(async_init)
    print("[DEBUG] Task scheduled")


if __name__ == "__main__":
    # Allow switching between desktop and web mode via environment variables for testing/automation
    view_mode = os.environ.get("FLET_VIEW", "DESKTOP").upper().strip()
    port_env = os.environ.get("FLET_PORT")
    try:
        port = int(port_env) if port_env else 8550
    except Exception:
        port = 8550

    def _pick_port(preferred: int) -> int:
        """Pick an available port, starting from preferred and trying a few fallbacks."""
        candidates = [preferred, preferred + 1, preferred + 2, preferred + 3, preferred + 4]
        for p in candidates:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind(("0.0.0.0", p))
                    return p
                except OSError:
                    continue
        # If somehow none are available, return preferred and let ft.app error loudly
        return preferred

    if view_mode == "WEB":
        print("[LAUNCH] Starting FletV2 as WEB application (browser)...")
        print(
            "[INFO] This mode enables Playwright/browser-based verification while keeping direct server integration."
        )
        chosen_port = _pick_port(port)
        if chosen_port != port:
            print(f"[INFO] Preferred port {port} is busy; auto-selected free port {chosen_port}")
        try:
            # Launch in WEB_BROWSER view so automated tools can capture screenshots
            ft.app(target=gui_with_server_main, view=ft.AppView.WEB_BROWSER, port=chosen_port)
            print("[OK] FletV2 web application closed normally")
        except Exception as launch_err:
            print(f"[FATAL] FletV2 failed to launch (web): {launch_err}")
            import traceback

            traceback.print_exc()
            raise SystemExit(1) from launch_err
    else:
        print("[LAUNCH] Starting FletV2 as native desktop application...")
        print("[INFO] FletV2 will open in a desktop window with:")
        print("       • Material Design 3 interface")
        print("       • Real-time server monitoring")
        print("       • 1200x800 resizable window")
        print("       • Native OS window controls")
        print()

        try:
            # Launch as native desktop application (default mode)
            ft.app(target=gui_with_server_main, view=ft.AppView.FLET_APP)
            print("[OK] FletV2 desktop application closed normally")

        except Exception as launch_err:
            print(f"[FATAL] FletV2 failed to launch: {launch_err}")
            import traceback

            traceback.print_exc()
            raise SystemExit(1) from launch_err

    # Cleanup on exit
    if server_instance:
        print("\n[STOP] Shutting down BackupServer (network + database)...")
        try:
            server_instance.stop()  # Stops network server and cleans up resources
            print("[OK] BackupServer stopped cleanly")
            print("[INFO] Network listener on port 1256 closed")
            print("[INFO] Database connections released")
        except Exception as e:
            print(f"[WARN] Server shutdown error: {e}")
            import traceback

            traceback.print_exc()
