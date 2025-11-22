from unittest.mock import patch

import pytest

from python_server.server.server import BackupServer

# Constants for testing
TEST_PORT = 12560  # Use a non-standard port for testing
TEST_DB_PATH = ":memory:"  # Use in-memory DB for speed and isolation


@pytest.fixture
def mock_db_manager():
    """Mock the database manager to avoid actual DB file creation."""
    with patch("python_server.server.server.DatabaseManager") as MockDB:
        db_instance = MockDB.return_value
        # Setup default return values
        db_instance.get_all_clients.return_value = []
        db_instance.load_clients_from_db.return_value = []
        db_instance.get_total_files_count.return_value = 0
        db_instance.get_total_bytes_transferred.return_value = 0
        yield db_instance


@pytest.fixture
def server(mock_db_manager):
    """Create a BackupServer instance with mocked dependencies."""
    # Patch NetworkServer to prevent actual socket binding during init if needed
    # But BackupServer init doesn't bind, start() does.
    # We might need to patch ensure_single_server_instance to avoid lock file issues
    with patch("python_server.server.server.ensure_single_server_instance"):
        server = BackupServer()
        # Override port and db for testing
        server.port = TEST_PORT
        server.db_manager = mock_db_manager
        yield server
        # Cleanup
        if server.running:
            server.stop()


def test_server_initialization(server):
    """Test that the server initializes correctly."""
    assert server is not None
    assert server.port == TEST_PORT
    assert server.running is False
    assert server.clients == {}


def test_client_management(server):
    """Test adding, retrieving, and removing clients."""
    client_id_hex = "1234567890abcdef1234567890abcdef"
    client_id_bytes = bytes.fromhex(client_id_hex)
    client_name = "TestClient"

    # Add client
    # We need to mock the DB add_client call
    server.db_manager.add_client.return_value = True

    # Manually add to internal state since we are not running the full network loop
    # But we can test the helper methods

    # Test create_client
    client = server.create_client(client_id_bytes, client_name)
    assert client.id == client_id_bytes
    assert client.name == client_name

    # Manually add to internal state (simulating registration)
    server.clients[client_id_bytes] = client
    server.clients_by_name[client_name] = client_id_bytes

    # Verify it's in the server's client list
    assert client_id_bytes in server.clients
    assert server.clients_by_name[client_name] == client_id_bytes

    # Test get_client_by_id
    retrieved_client = server.get_client_by_id(client_id_bytes)
    assert retrieved_client == client

    # Test resolve_client (by name)
    resolved_resp = server.resolve_client(client_name)
    assert resolved_resp["success"] is True
    assert resolved_resp["data"]["id"] == client_id_hex
    assert resolved_resp["data"]["name"] == client_name

    # Test resolve_client (by ID string)
    resolved_resp_by_id = server.resolve_client(client_id_hex)
    assert resolved_resp_by_id["success"] is True
    assert resolved_resp_by_id["data"]["id"] == client_id_hex

    # Test disconnect_client
    disconnect_resp = server.disconnect_client(client_id_hex)
    assert disconnect_resp["success"] is True
    assert client_id_bytes not in server.clients
    assert client_name not in server.clients_by_name


def test_validate_client_name(server):
    """Test client name validation logic."""
    # Valid names
    assert server._validate_client_name("ValidName")[0] is True
    assert server._validate_client_name("Client_123")[0] is True
    assert server._validate_client_name("user-name")[0] is True

    # Invalid names
    # Invalid names
    assert server._validate_client_name("")[0] is False  # Empty
    assert server._validate_client_name("Invalid Name")[0] is False  # Spaces
    assert server._validate_client_name("Name!")[0] is False  # Special chars
    assert server._validate_client_name("A" * 256)[0] is False  # Too long


def test_format_response(server):
    """Test standard response formatting."""
    # Success response
    data = {"key": "value"}
    resp = server._format_response(True, data)
    assert resp == {"success": True, "data": data, "error": ""}

    # Error response
    error_msg = "Something went wrong"
    resp = server._format_response(False, error=error_msg)
    assert resp == {"success": False, "data": None, "error": error_msg}
