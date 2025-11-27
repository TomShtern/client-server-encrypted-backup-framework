#!/usr/bin/env python3
"""
Quick test of the server bridge with real BackupServer
"""

import os
import sys

# Add proper paths
repo_root = os.path.dirname(os.path.abspath("."))
sys.path.insert(0, repo_root)

# Import required modules
from FletV2.utils.server_bridge import create_server_bridge  # noqa: E402
from python_server.server.server import BackupServer  # noqa: E402


def test_database_access(real_server):
    """
    Test direct access to the server's database manager.
    Extracts database testing logic for better modularity and error handling.
    """
    print("5. Testing direct server database access...")
    if not hasattr(real_server, "db_manager") or not real_server.db_manager:
        print("   - No db_manager available on real_server.")
        return

    db_manager = real_server.db_manager
    print(f"   - db_manager type: {type(db_manager)}")

    # Inspect available methods for debugging
    available_methods = [
        method for method in dir(db_manager) if not method.startswith("_")
    ]
    print(f"   - Available db_manager methods: {available_methods}")

    # Safely attempt to get clients (check if method exists first)
    if hasattr(db_manager, "get_clients"):
        try:
            clients = db_manager.get_clients()
            print(f"   Direct clients: {len(clients) if clients else 0} clients")
            if clients:
                print(
                    f"   First client: {clients[0] if isinstance(clients, list) else clients}"
                )
        except Exception as e:
            print(f"   Error accessing clients: {e}")
    else:
        print("   - get_clients method not available on db_manager.")

    # Safely attempt to get files (check if method exists first)
    if hasattr(db_manager, "get_files"):
        try:
            files = db_manager.get_files()
            print(f"   Direct files: {len(files) if files else 0} files")
            if files:
                print(
                    f"   First file: {files[0] if isinstance(files, list) else files}"
                )
        except Exception as e:
            print(f"   Error accessing files: {e}")
    else:
        print("   - get_files method not available on db_manager.")


def test_bridge():
    print("=== Testing BackupServer + ServerBridge Integration ===")

    # Create real server instance
    print("1. Creating BackupServer instance...")
    real_server = BackupServer()
    print(f"   - BackupServer created: {type(real_server)}")

    # Create bridge with real server
    print("2. Creating ServerBridge with real server...")
    bridge = create_server_bridge(real_server=real_server)
    print(f"   - Bridge created: {type(bridge)}")
    print(f"   - Bridge connected: {bridge.is_connected()}")

    # Test data retrieval
    print("3. Testing data retrieval...")

    print("   - Getting clients...")
    clients_result = bridge.get_clients()
    print(f"     Result: {clients_result}")

    print("   - Getting files...")
    files_result = bridge.get_files()
    print(f"     Result: {files_result}")

    print("   - Getting status...")
    try:
        status_result = bridge.get_server_status()
        print(f"     Result: {status_result}")
    except AttributeError as e:
        print(f"     Error: {e}")

    # Test what methods the real server actually has
    print("4. Checking real server methods...")
    server_methods = [
        method for method in dir(real_server) if not method.startswith("_")
    ]
    print(f"   Available methods: {server_methods}")

    # 5. Testing direct BackupServer get_clients method...
    print("5. Testing direct BackupServer get_clients method...")
    try:
        clients_result = real_server.get_clients()
        print(f"   Direct get_clients result: {clients_result}")
        print(f"   Result type: {type(clients_result)}")
        if isinstance(clients_result, dict) and "data" in clients_result:
            clients_data = clients_result["data"]
            if isinstance(clients_data, list):
                print(f"   Number of clients: {len(clients_data)}")
                if clients_data:
                    print(f"   First client: {clients_data[0]}")

        # Also test get_files
        files_result = real_server.get_files()
        print(f"   Direct get_files result: {files_result}")
        print(f"   Files result type: {type(files_result)}")
        if isinstance(files_result, dict) and "data" in files_result:
            files_data = files_result["data"]
            if isinstance(files_data, list):
                print(f"   Number of files: {len(files_data)}")
                if files_data:
                    print(f"   First file: {files_data[0]}")

    except Exception as e:
        print(f"   Direct server error: {e}")

    # Call the extracted database testing function
    test_database_access(real_server)


if __name__ == "__main__":
    test_bridge()
