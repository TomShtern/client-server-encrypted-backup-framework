"""
CLIENT MANAGEMENT - CLIENT STATE REPRESENTATION
==============================================

PURPOSE: Client class represents a connected client with thread-safe state management.
USED BY: BackupServer for tracking client sessions, keys, and file transfers.

CLIENT STATE:
- Cryptographic keys (RSA public, AES session)
- File transfer state (partial uploads, reassembly)
- Session management (last seen, timeouts)
- Thread-safe concurrent access

NOTE: ClientManager class was removed - all client management handled by BackupServer directly.
This eliminates architectural duplication and provides single source of truth for client state.
"""

import logging
import threading
import time
from typing import Any

# Import crypto components through compatibility layer
from Crypto.PublicKey import RSA

from .config import (
    AES_KEY_SIZE_BYTES,
    CLIENT_SESSION_TIMEOUT,
    PARTIAL_FILE_TIMEOUT,
    RSA_PUBLIC_KEY_SIZE,
)

# Import custom exceptions and configuration
from .exceptions import ProtocolError

logger = logging.getLogger(__name__)


class Client:
    """
    Represents a connected client and stores its state.
    Thread-safe client object with comprehensive state management.
    """

    def __init__(
        self, client_id: bytes, name: str, public_key_bytes: bytes | None = None
    ):
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
        self.public_key_obj: Any | None = (
            None  # Use flexible type for compatibility layer
        )
        self.aes_key: bytes | None = None  # Current session AES key
        self.last_seen: float = time.monotonic()  # Monotonic time for session timeout
        self.partial_files: dict[
            str, dict[str, Any]
        ] = {}  # For reassembling multi-packet files
        self.lock: threading.Lock = (
            threading.Lock()
        )  # To protect concurrent access to client state

        if public_key_bytes:
            self._import_public_key()

    def _import_public_key(self):
        """Imports the RSA public key from bytes if available."""
        if self.public_key_bytes:
            try:
                self.public_key_obj = RSA.import_key(self.public_key_bytes)
                logger.debug(f"Client '{self.name}': Successfully imported public key.")
            except ValueError as e:
                logger.error(
                    f"Client '{self.name}': Failed to import public key from stored bytes: {e}"
                )
                self.public_key_obj = None  # Ensure consistent state if import fails

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
                raise ProtocolError(
                    f"Public key size is incorrect for client '{self.name}'. Expected {RSA_PUBLIC_KEY_SIZE}, got {len(public_key_bytes_data)}."
                )
            self.public_key_bytes = public_key_bytes_data
            self._import_public_key()  # Attempt to parse and store the RsaKey object
            if not self.public_key_obj:  # Check if import failed
                raise ProtocolError(
                    f"Invalid RSA public key format provided by client '{self.name}' (failed to import)."
                )

    def get_aes_key(self) -> bytes | None:
        """Returns the current session AES key."""
        return self.aes_key

    def set_aes_key(self, aes_key_data: bytes):
        """
        Sets the client's session AES key.

        Args:
            aes_key_data: The AES key (bytes).

        Raises:
            ValueError: If the AES key size is incorrect.
        """
        with self.lock:  # Protect AES key modification
            if len(aes_key_data) != AES_KEY_SIZE_BYTES:
                raise ValueError(
                    f"AES key size for client '{self.name}' is incorrect. Expected {AES_KEY_SIZE_BYTES}, got {len(aes_key_data)}."
                )
            self.aes_key = aes_key_data

    def clear_partial_file(self, filename: str):
        """Removes partial file reassembly data for a given filename."""
        with self.lock:
            if filename in self.partial_files:
                del self.partial_files[filename]
                logger.debug(
                    f"Client '{self.name}': Cleared partial file reassembly data for '{filename}'."
                )

    def clear_all_partial_files(self) -> int:
        """Clears all in-memory partial file transfer states for this client.
        Returns the number of cleared partial entries.
        """
        with self.lock:
            count = len(self.partial_files)
            self.partial_files.clear()
            if count > 0:
                logger.info(
                    f"Client '{self.name}': Cleared all partial file data due to disconnect/cancellation ({count} entries)"
                )
            else:
                logger.debug(
                    f"Client '{self.name}': No partial file data to clear on disconnect/cancellation"
                )
            return count

    def cleanup_stale_partial_files(self) -> int:
        """
        Removes partial file data for transfers that haven't seen activity recently.

        Returns:
            The number of stale partial file transfers cleaned up for this client.
        """
        with self.lock:
            current_monotonic_time = time.monotonic()
            stale_files_to_remove = [
                filename
                for filename, data in self.partial_files.items()
                if current_monotonic_time - data.get("timestamp", 0)
                > PARTIAL_FILE_TIMEOUT
            ]

            # Remove stale entries
            for filename in stale_files_to_remove:
                logger.warning(
                    f"Client '{self.name}': Stale partial file transfer timed out for '{filename}'. Removing associated data."
                )
                del self.partial_files[filename]

            return len(stale_files_to_remove)

    def is_session_expired(self) -> bool:
        """
        Checks if the client session has expired based on inactivity.

        Returns:
            True if the session has expired, False otherwise.
        """
        with self.lock:
            return (time.monotonic() - self.last_seen) > CLIENT_SESSION_TIMEOUT

    def get_session_age(self) -> float:
        """
        Returns the age of the current session in seconds.

        Returns:
            The session age in seconds.
        """
        with self.lock:
            return time.monotonic() - self.last_seen

    def has_public_key(self) -> bool:
        """
        Checks if the client has a valid public key.

        Returns:
            True if the client has a valid public key, False otherwise.
        """
        with self.lock:
            return self.public_key_obj is not None

    def has_aes_key(self) -> bool:
        """
        Checks if the client has an AES key set.

        Returns:
            True if the client has an AES key, False otherwise.
        """
        return self.aes_key is not None

    def get_partial_file_count(self) -> int:
        """
        Returns the number of partial files currently being tracked.

        Returns:
            The number of partial files.
        """
        with self.lock:
            return len(self.partial_files)

    def __str__(self) -> str:
        """String representation of the client."""
        return f"Client(id={self.id.hex()[:8]}..., name='{self.name}', has_pk={self.has_public_key()}, has_aes={self.has_aes_key()})"


# Export only the Client class - ClientManager was removed as unused duplicate
__all__ = ["Client"]
