#!/usr/bin/env python3
"""
Simple Server Launcher
Starts the backup serv        # Start backup server         # Start API server with UTF-8 support
        startup_print("Starting API Bridge Server...", "API")
        api_server = Popen_utf8(
            [sys.executable, '-m', 'api_server.cyberbackup_api_server'],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        success_print(f"API server started with PID: {api_server.pid}", "PID")

        # Wait for API server to be ready
        info_print("Waiting for API server to be ready...", "WAIT")
        if wait_for_server(9090, timeout=30):
            success_print("API server is ready on port 9090", "API")
        else:
            error_print("API server failed to start on port 9090", "API")
            return 1ort
        startup_print("Starting Python Backup Server...", "SERVER")
        backup_server = Popen_utf8(
            [sys.executable, '-m', 'python_server.server.server'],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        success_print(f"Backup server started with PID: {backup_server.pid}", "PID")

        # Wait for backup server to be ready
        info_print("Waiting for backup server to be ready...", "WAIT")
        if wait_for_server(1256, timeout=30):
            success_print("Backup server is ready on port 1256", "SERVER")
        else:
            error_print("Backup server failed to start on port 1256", "SERVER")
            return 1er in separate console windows
"""

import os
import subprocess
import sys
import time
import webbrowser

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# UTF-8 support for subprocess operations
# Enhanced output with emojis and colors
from Shared.logging.enhanced_output import (
    Emojis,
    success_print,
    startup_print,
    error_print,
    info_print,
    warning_print,
)
from Shared.filesystem.utf8_solution import Popen_utf8


def check_port_available(port):
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def wait_for_server(port, timeout=30):
    """Wait for server to be ready"""
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("=" * 50)
    startup_print("CyberBackup Server Launcher", "LAUNCHER")
    print("=" * 50)

    # Check if ports are available
    if not check_port_available(1256):
        error_print("Port 1256 is in use. Please close other applications using this port.", "PORT")
        return 1

    if not check_port_available(9090):
        error_print("Port 9090 is in use. Please close other applications using this port.", "PORT")
        return 1

    success_print("Ports 1256 and 9090 are available", "PORT")

    # Set up environment with Python path
    env = os.environ.copy()
    env['PYTHONPATH'] = project_root

    try:
        # Start backup server with UTF-8 support
        print("\n1. Starting Python Backup Server...")
        backup_server = Popen_utf8(
            [sys.executable, '-m', 'python_server.server.server'],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        print(f"   Backup server started with PID: {backup_server.pid}")

        # Wait for backup server to start
        print("   Waiting for backup server to be ready...")
        if wait_for_server(1256, timeout=30):
            print("   ✓ Backup server is ready on port 1256")
        else:
            print("   ✗ Backup server failed to start on port 1256")
            return 1

        # Start API server with UTF-8 support
        print("\n2. Starting API Bridge Server...")
        api_server = Popen_utf8(
            [sys.executable, '-m', 'api_server.cyberbackup_api_server'],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        print(f"   API server started with PID: {api_server.pid}")

        # Wait for API server to start
        print("   Waiting for API server to be ready...")
        if wait_for_server(9090, timeout=30):
            print("   ✓ API server is ready on port 9090")
        else:
            print("   ✗ API server failed to start on port 9090")
            return 1

        # Open web browser
        gui_url = "http://127.0.0.1:9090/"
        info_print(f"Opening Web GUI: {gui_url}", "BROWSER")
        webbrowser.open(gui_url)

        print("\n" + "=" * 50)
        success_print("SUCCESS! All servers are running:", "COMPLETE")
        print(f"   {Emojis.SERVER} Backup Server: Port 1256 (PID: {backup_server.pid})")
        print(f"   {Emojis.API} API Server: Port 9090 (PID: {api_server.pid})")
        print(f"   {Emojis.NETWORK} Web GUI: {gui_url}")
        print("=" * 50)

        info_print("Servers are running in separate console windows.", "INFO")
        warning_print("Close the console windows to stop the servers.", "WARNING")
        info_print("Press Enter to exit this launcher...", "INPUT")
        input()

        return 0

    except Exception as e:
        error_print(f"Failed to start servers: {e}", "EXCEPTION")
        return 1

if __name__ == "__main__":
    sys.exit(main())
