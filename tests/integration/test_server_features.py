import json
from unittest.mock import mock_open, patch

import pytest

from python_server.server.server import BackupServer


@pytest.fixture
def server():
    """Create a BackupServer instance with mocked dependencies."""
    with (
        patch("python_server.server.server.ensure_single_server_instance"),
        patch("python_server.server.server.DatabaseManager"),
    ):
        server = BackupServer()
        # Prevent actual network binding
        server.port = 12560
        return server


def test_settings_management(server):
    """Test loading, validating, and saving settings."""

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
    mock_settings_json = json.dumps(valid_settings)
    with (
        patch("builtins.open", mock_open(read_data=mock_settings_json)),
        patch("os.path.exists", return_value=True),
    ):
        loaded = server.load_settings()
        assert loaded["success"] is True
        assert loaded["data"]["server_port"] == 1234
        assert loaded["data"]["theme"] == "dark"

    # 3. Test save_settings (Atomic Write)
    new_settings = {"server_port": 5555}

    # Mock os.replace to simulate atomic move
    with (
        patch("builtins.open", mock_open()) as mock_file,
        patch("os.replace") as mock_replace,
        patch("os.rename") as mock_rename,
        patch("os.path.exists", return_value=True),
        patch("os.remove"),
        patch("json.dump"),
    ):
        success = server.save_settings(new_settings)

        assert success["success"] is True
        # Verify it opened a temp file
        mock_file.assert_called()
        # Verify it tried to replace temp file with target
        mock_replace.assert_called_once()


def test_log_export(server):
    """Test log export functionality."""

    # Mock log content
    log_content = """2023-10-27 10:00:00,000 - INFO - Server started
2023-10-27 10:00:01,000 - DEBUG - Connection from 127.0.0.1
2023-10-27 10:00:02,000 - ERROR - Database connection failed
"""

    # Mock file size check to pass
    with (
        patch("os.path.getsize", return_value=1024),
        patch("builtins.open", mock_open(read_data=log_content)) as mock_file,
    ):
        # 1. Test JSON export
        json_export = server._export_logs_sync("json", {"limit": 10})
        assert json_export["success"] is True
        assert json_export["data"]["count"] == 3

        # Verify write (JSON)
        handle = mock_file()
        handle.write.assert_called()

        # 2. Test CSV export
        csv_export = server._export_logs_sync("csv", {"limit": 10})
        assert csv_export["success"] is True
        assert csv_export["data"]["count"] == 3

        # 3. Test Filtering (Level)
        error_export = server._export_logs_sync("json", {"level": "ERROR"})
        assert error_export["success"] is True
        assert error_export["data"]["count"] == 1

        # 4. Test Filtering (Search)
        search_export = server._export_logs_sync("json", {"search_term": "Connection"})
        assert search_export["success"] is True
        assert search_export["data"]["count"] == 2
