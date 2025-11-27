#!/usr/bin/env python3
"""
GUI Launcher for CyberBackup 3.0
Automatically starts the API server and opens the GUI in browser
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any


def check_port_available(port: int):
    """Check if a port is available"""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def wait_for_server(port: int, timeout: int = 30):
    """Wait for server to be ready"""
    import socket

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                if result == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start_api_server():
    """Start the API server in a separate process"""
    try:
        # Start the API server
        server_process = subprocess.Popen(
            [sys.executable, "cyberbackup_api_server.py"],
            # Redirect stdout and stderr to the parent process's stdout/stderr
            # This makes API server output visible in the console for debugging
            stdout=sys.stdout,
            stderr=sys.stderr,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        )
        return server_process
    except Exception as e:
        print(f"Failed to start API server: {e}")
        return None


def open_gui():
    """Open the GUI in the default browser via the API server"""
    gui_url = "http://127.0.0.1:9090/"

    try:
        # Open the GUI via the API server (solves CORS issues)
        webbrowser.open(gui_url)
        print(f"GUI opened in browser: {gui_url}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to open GUI: {e}")
        return False


def get_log_monitoring_info() -> list[dict[str, Any]] | None:
    """Get information about available log files for monitoring"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None

    log_files: list[dict[str, Any]] = []
    for log_file in logs_dir.glob("*.log"):
        if log_file.name.startswith("latest-"):
            continue

        if "api-server" in log_file.name:
            server_type = "API Server"
        elif "backup-server" in log_file.name:
            server_type = "Backup Server"
        else:
            continue

        log_files.append(
            {
                "path": str(log_file.absolute()),
                "name": log_file.name,
                "server_type": server_type,
                "modified": log_file.stat().st_mtime if log_file.exists() else 0,
            }
        )

    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x["modified"], reverse=True)
    return log_files


def main():
    print("CyberBackup 3.0 - GUI Launcher")
    print("=" * 50)

    # Check if API server port is available
    if not check_port_available(9090):
        print("Port 9090 is already in use.")
        print("   The API server might already be running.")
        print("   Opening GUI anyway...")
    else:
        print("Starting API server...")
        server_process = start_api_server()

        if server_process:
            print("Waiting for API server to be ready...")
            if wait_for_server(9090):
                print("API server is ready!")
            else:
                print("API server may not be fully ready, but continuing...")
        else:
            print("[ERROR] Failed to start API server")
            return 1

    print("Opening GUI in browser...")
    if open_gui():
        print()
        print("GUI should now be open in your browser!")
        print()
        print("Instructions:")
        print("1. The GUI is now open in your web browser")
        print("2. Configure your server settings (Host: 127.0.0.1, Port: 1256)")
        print("3. Click 'CONNECT' to connect to the backup server")
        print("4. Select files to backup using the interface")
        print()

        # Display logging information
        log_files = get_log_monitoring_info()
        if log_files:
            print("Log Monitoring:")
            for lf in log_files[:2]:  # Show latest 2 files
                print(f"  - {lf['server_type']}: {lf['path']}")
            print("  - Live Monitor: python scripts/monitor_logs.py --follow")
            print(r"  - PowerShell: Get-Content logs\*.log -Wait -Tail 50")
            print()

        print("Note: Keep this window open while using the GUI")
        print("Press Ctrl+C to stop the API server when done")

        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            return 0
    else:
        print("Failed to open GUI")
        return 1


if __name__ == "__main__":
    sys.exit(main())
