import json
import os

import pytest

import python_server.server.server
from python_server.server.server import BackupServer


@pytest.fixture
def server(tmp_path):
    """Create a BackupServer instance in a temporary directory."""
    # Save current CWD
    old_cwd = os.getcwd()
    # Change to temp directory
    os.chdir(tmp_path)

    # Redirect SETTINGS_FILE to temp dir
    original_settings_file = python_server.server.server.SETTINGS_FILE
    python_server.server.server.SETTINGS_FILE = os.path.join(
        tmp_path, "server_settings.json"
    )

    try:
        # Initialize server
        # This will create necessary directories and database in tmp_path
        server = BackupServer()
        # Set a test port
        server.port = 12560
        return server
    finally:
        # Restore SETTINGS_FILE
        python_server.server.server.SETTINGS_FILE = original_settings_file
        # Restore CWD
        os.chdir(old_cwd)


def test_settings_management(server):
    """Test loading, validating, and saving settings using real files."""

    # 1. Test _validate_settings
    valid_settings = {
        "server_port": 1234,
        "max_concurrent_clients": 10,
        "theme": "dark",
        "enable_monitoring": True,
    }
    result = server._validate_settings(valid_settings)
    assert result[0] is True, f"Validation failed: {result[1]}"

    invalid_settings = {
        "server_port": "not_an_int",  # Invalid type
        "max_concurrent_clients": 10,
    }
    assert server._validate_settings(invalid_settings)[0] is False

    # 2. Test load_settings
    # Create a real settings file
    with open("server_settings.json", "w") as f:
        json.dump(valid_settings, f)

    loaded = server.load_settings()
    assert loaded["success"] is True
    assert loaded["data"]["server_port"] == 1234
    assert loaded["data"]["theme"] == "dark"

    # 3. Test save_settings (Atomic Write)
    new_settings = {"server_port": 5555}

    success = server.save_settings(new_settings)
    assert success["success"] is True

    # Verify the file was updated
    with open("server_settings.json", "r") as f:
        saved_data = json.load(f)
    # Settings are wrapped in "settings" key
    assert saved_data["settings"]["server_port"] == 5555


def test_log_export(tmp_path):
    """Test log export functionality using real log files."""
    # Save current CWD
    old_cwd = os.getcwd()
    # Change to temp directory
    os.chdir(tmp_path)

    # Redirect SETTINGS_FILE to temp dir (good practice to avoid side effects)
    original_settings_file = python_server.server.server.SETTINGS_FILE
    python_server.server.server.SETTINGS_FILE = os.path.join(
        tmp_path, "server_settings.json"
    )

    try:
        # Create logs directory and pre-seed log file
        os.makedirs("logs", exist_ok=True)

        # Note: Added 'MainThread' to match server's log pattern
        log_content = """2023-10-27 10:00:00,000 - MainThread - INFO - Server started
2023-10-27 10:00:01,000 - MainThread - DEBUG - Connection from 127.0.0.1
2023-10-27 10:00:02,000 - MainThread - ERROR - Database connection failed
"""
        with open("logs/server.log", "w") as f:
            f.write(log_content)

        # Initialize server AFTER writing logs
        server = BackupServer()
        server.port = 12560

        # Force server to read OUR log file, not the global one set at import time
        server.backup_log_file = os.path.abspath("logs/server.log")

        # 1. Test JSON export
        json_export = server._export_logs_sync("json", {"limit": 10})
        assert json_export["success"] is True
        assert json_export["data"]["count"] >= 3

        # 2. Test CSV export
        csv_export = server._export_logs_sync("csv", {"limit": 10})
        assert csv_export["success"] is True
        assert csv_export["data"]["count"] >= 3

        # 3. Test Filtering (Level) - verify exported JSON file contains error entry
        error_export = server._export_logs_sync("json", {"level": "ERROR"})
        assert error_export["success"] is True
        assert error_export["data"]["count"] >= 1
        error_file = error_export["data"]["file_path"]
        with open(error_file, "r", encoding="utf-8") as f:
            error_entries = json.load(f)
        found_error = any(
            entry.get("message") == "Database connection failed"
            for entry in error_entries
        )
        assert found_error, "Did not find expected error log in exported JSON file"

        # 4. Test Filtering (Search) - verify exported JSON file contains connection entry
        search_export = server._export_logs_sync("json", {"search_term": "Connection"})
        assert search_export["success"] is True
        assert search_export["data"]["count"] >= 1
        search_file = search_export["data"]["file_path"]
        with open(search_file, "r", encoding="utf-8") as f:
            search_entries = json.load(f)
        found_conn = any(
            "Connection" in entry.get("message", "") for entry in search_entries
        )
        assert found_conn, "Did not find expected connection log in exported JSON file"

    finally:
        # Restore SETTINGS_FILE and CWD
        python_server.server.server.SETTINGS_FILE = original_settings_file
        os.chdir(old_cwd)
