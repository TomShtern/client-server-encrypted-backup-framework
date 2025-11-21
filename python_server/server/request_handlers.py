"""
REQUEST HANDLERS - PROTOCOL MESSAGE PROCESSING
===============================================

PURPOSE: Process all incoming client protocol requests and coordinate responses.
USED BY: NetworkServer when handling client connections.
ARCHITECTURE: One handler method per protocol request type.

PROTOCOL HANDLERS:
- REQ_REGISTER: Client registration with RSA key exchange
- REQ_SEND_PUBLIC_KEY: Public key submission for new sessions
- REQ_RECONNECT: Client reconnection with AES key recovery
- REQ_SEND_FILE: Multi-packet file upload initiation
- REQ_CRC_OK/REQ_CRC_FAILED/REQ_CRC_INVALID_RETRY: File transfer completion

RESPONSES: All responses go through server.network_server.send_response() (no local _send_response).

DEPENDENCIES:
- server.client_manager.Client for client state management
- server.file_transfer.FileTransferManager for file operations
- server.network_server.send_response() for client communication
- server.db_manager for data persistence

SECURITY: All requests include authentication, validation, and proper error handling.
"""

import logging
import os
import re
import socket
import uuid
from datetime import datetime
from typing import Any

# Import crypto components through compatibility layer
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

# Import observability components
from Shared.monitoring.observability import get_metrics_collector

# Import error handling utilities
from Shared.logging.error_handling import handle_request_errors_detailed, handle_specific_request_errors

# Import validation utilities
from Shared.validation.validation_utils import is_valid_filename_for_storage

# Import configuration constants
from .config import (
    AES_KEY_SIZE_BYTES,
    FILE_STORAGE_DIR,
    MAX_ACTUAL_FILENAME_LENGTH,
    MAX_CLIENT_NAME_LENGTH,
    RSA_PUBLIC_KEY_SIZE,
)

# Import custom exceptions
from .exceptions import ProtocolError, ServerError

# Import protocol constants
from .protocol import (
    REQ_CRC_FAILED_ABORT,
    REQ_CRC_INVALID_RETRY,
    REQ_CRC_OK,
    REQ_RECONNECT,
    REQ_REGISTER,
    REQ_SEND_FILE,
    REQ_SEND_PUBLIC_KEY,
    RESP_ACK,
    RESP_GENERIC_SERVER_ERROR,
    RESP_PUBKEY_AES_SENT,
    RESP_RECONNECT_AES_SENT,
    RESP_RECONNECT_FAIL,
    RESP_REG_FAIL,
    RESP_REG_OK,
)

logger = logging.getLogger(__name__)


class RequestHandler:
    """
    Handles all client request processing for the backup server.

    This class contains all the request processing methods that were previously
    part of the monolithic Server class, providing better separation of concerns
    and modularity.
    """

    def __init__(self, server_instance: Any) -> None:
        """
        Initialize the RequestHandler with a reference to the server instance.

        Args:
            server_instance: The main Server instance containing shared resources
                           (client management, database, GUI, etc.)
        """
        self.server = server_instance

        # Initialize file transfer manager
        from .file_transfer import FileTransferManager
        self.file_transfer_manager = FileTransferManager(server_instance)

        # Request handler mapping - dispatches requests to appropriate handlers
        self.handler_map: dict[int, Any] = {
            REQ_REGISTER: self._handle_registration,
            REQ_SEND_PUBLIC_KEY: self._handle_send_public_key,
            REQ_RECONNECT: self._handle_reconnect,
            REQ_SEND_FILE: self._handle_send_file,
            REQ_CRC_OK: self._handle_crc_ok,
            REQ_CRC_INVALID_RETRY: self._handle_crc_invalid_retry,
            REQ_CRC_FAILED_ABORT: self._handle_crc_failed_abort,
        }

    def process_request(self, sock: socket.socket, client_id_from_header: bytes,
                       client: Any | None, code: int, payload: bytes) -> None:
        """
        Dispatches a client request to the appropriate handler method based on the request code.

        Args:
            sock: The client's socket.
            client_id_from_header: The Client ID received in the request header.
            client: The resolved Client object (None for registration requests).
            code: The request code.
            payload: The request payload.
        """
        logger.debug(f"Processing request - Code: {code}, Client ID: {client_id_from_header.hex()}, Payload size: {len(payload)}")

        handler_method = self.handler_map.get(code)

        if handler_method:
            if code == REQ_REGISTER:
                # Registration is special: client_id_from_header is all zeros, and `client` object is not yet created/resolved.
                # The handler itself will generate the new client ID and create the Client object.
                handler_method(sock, payload)
            elif client:
                # For all other requests, a valid `client` object (resolved by client_id_from_header) must exist.
                # The `client` object contains the authoritative client ID (client.id).
                handler_method(sock, client, payload)
            else:
                # This state (handler method exists, but `client` object is None for a non-registration request)
                # indicates a logic flaw in the calling sequence (e.g., _handle_client_connection did not resolve client).
                logger.critical(f"INTERNAL SERVER ERROR: Client object is None for a non-registration request (Code: {code}, Header ID: {client_id_from_header.hex()}). This should have been caught earlier.")
                self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
        else:
            # If the request code is not found in our handler_map
            client_name_for_log = client.name if client else client_id_from_header.hex()
            logger.warning(f"Unknown or unsupported request code {code} received from client '{client_name_for_log}'.")
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)

    def _handle_registration(self, sock: socket.socket, payload: bytes) -> None:
        """
        Handles client registration request (Code 1025).
        Payload: char name[255]; (null-terminated, zero-padded)
        """
        name_field_protocol_len = 255
        if len(payload) != name_field_protocol_len:
            raise ProtocolError(f"Registration Request (1025): Invalid payload size. Expected {name_field_protocol_len} bytes, got {len(payload)}.")

        # Parse client name from payload, enforcing max actual length and character set
        client_name = self._parse_string_from_payload(payload, name_field_protocol_len, MAX_CLIENT_NAME_LENGTH, "Client Name")

        with self.server.clients_lock:
            if client_name in self.server.clients_by_name:
                logger.warning(f"Registration attempt failed: Username '{client_name}' is already registered.")
                self.server.network_server.send_response(sock, RESP_REG_FAIL)
                return

            # Generate a new unique client ID (UUID version 4)
            new_client_id_bytes = uuid.uuid4().bytes
            # Use the server's factory method to create a new client
            new_client = self.server.create_client(new_client_id_bytes, client_name)

            # Add the new client to in-memory tracking structures
            self.server.clients[new_client_id_bytes] = new_client
            self.server.clients_by_name[client_name] = new_client_id_bytes

            self.server.db_manager.save_client_to_db(new_client.id, new_client.name, new_client.public_key_bytes, new_client.get_aes_key())

            logger.info(f"Client '{client_name}' successfully registered with New Client ID: {new_client_id_bytes.hex()}.")

            # Record metrics for client registration
            get_metrics_collector().record_counter("client.connections.total", tags={'type': 'registration'})

            # GUI updates removed - FletV2 GUI gets client registration data through ServerBridge

            # Send Registration Success (1600) response with the new client ID as payload
            # IMPORTANT: Response must be sent inside lock to prevent race condition
            # where two threads could both pass the name check and register duplicate clients
            if not self.server.network_server.send_response(sock, RESP_REG_OK, new_client_id_bytes):
                # Response send failed - client won't receive confirmation
                # Clean up the registration state to prevent orphaned entries
                logger.error(f"Failed to send registration response to '{client_name}', rolling back registration")
                self.server.clients.pop(new_client_id_bytes, None)
                self.server.clients_by_name.pop(client_name, None)
                # Note: Database record remains but will be cleaned up by maintenance

    def _handle_send_public_key(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        """
        Handles client's public key submission (Code 1026).
        Client object is already resolved by ID from request header.
        Payload: char name[255]; uint8_t public_key[160];
        """
        name_field_protocol_len = 255
        expected_payload_size = name_field_protocol_len + RSA_PUBLIC_KEY_SIZE
        if len(payload) != expected_payload_size:
            raise ProtocolError(f"SendPublicKey Request (1026): Invalid payload size. Expected {expected_payload_size} bytes, got {len(payload)}.")

        try:
            # Parse client name from the first part of the payload
            name_from_payload = self._parse_string_from_payload(payload, name_field_protocol_len, MAX_CLIENT_NAME_LENGTH, "Client Name")
            # Extract the public key bytes from the latter part of the payload
            public_key_bytes_from_payload = payload[name_field_protocol_len:]

            # Validate that the name in payload matches the name associated with the client ID from header
            if client.name != name_from_payload:
                logger.warning(f"SendPublicKey: Name mismatch for Client ID {client.id.hex()}. Client's known name: '{client.name}', Name in payload: '{name_from_payload}'. This indicates a protocol violation or client-side inconsistency.")
                self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
                return

            client.set_public_key(public_key_bytes_from_payload)

            # Generate a new AES session key for this client
            new_aes_key = get_random_bytes(AES_KEY_SIZE_BYTES)
            client.set_aes_key(new_aes_key)

            # Encrypt the new AES key using the client's RSA public key (PKCS1_OAEP padding)
            if not client.public_key_obj:
                raise ServerError("Internal Server Error: Client's public key object is not available for RSA encryption after an import attempt. This should not happen.")

            cipher_rsa = PKCS1_OAEP.new(client.public_key_obj, hashAlgo=SHA256)
            aes_key = client.get_aes_key()
            if aes_key is None:
                raise ServerError("Internal Server Error: Client's AES key is not available for encryption.")
            encrypted_aes_key = cipher_rsa.encrypt(aes_key)

            # Update client's record in the database (PublicKey, LastSeen, and new session AESKey)
            self.server.db_manager.save_client_to_db(client.id, client.name, client.public_key_bytes, client.get_aes_key())

            # Construct and send Response 1602 (Public Key ACK + AES Key)
            # Payload: client_id[16] (client's own ID), encrypted_aes_key[] (variable length from RSA encryption)
            response_payload = client.id + encrypted_aes_key
            self.server.network_server.send_response(sock, RESP_PUBKEY_AES_SENT, response_payload)
            logger.info(f"Public key successfully received and processed for client '{client.name}'. New AES session key has been sent (encrypted).")

        except (ProtocolError, ServerError, ValueError) as e:
            logger.error(f"Error processing SendPublicKey request for client '{client.name}': {e}")
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
        except Exception as e_crypto:
            logger.critical(f"Unexpected critical error during RSA encryption for client '{client.name}': {e_crypto}", exc_info=True)
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)

    def _handle_reconnect(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        """
        Handles client reconnection request (Code 1027).
        Client object is already resolved by ID from request header.
        Payload: char name[255]; (null-terminated, padded)
        """
        # Apply specific error handling with consistent response codes
        return self._handle_reconnect_with_error_handling(sock, client, payload)

    def _handle_reconnect_with_error_handling(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        name_field_protocol_len = 255
        if len(payload) != name_field_protocol_len:
            raise ProtocolError(f"Reconnect Request (1027): Invalid payload size. Expected {name_field_protocol_len} bytes, got {len(payload)}.")

        name_from_payload = self._parse_string_from_payload(payload, name_field_protocol_len, MAX_CLIENT_NAME_LENGTH, "Client Name")

        # Validate that name in payload matches the known name for this client ID
        if client.name != name_from_payload:
            logger.warning(f"Reconnect: Name mismatch for Client ID {client.id.hex()}. Client's known name: '{client.name}', Name in payload: '{name_from_payload}'. Sending Reconnect Failed response.")
            # Response Payload (1606): client_id[16] (client's ID from header, as per spec)
            self.server.network_server.send_response(sock, RESP_RECONNECT_FAIL, client.id)
            return

        # Client must have a public key on record from a previous session to encrypt a new AES key
        if not client.public_key_obj:
            logger.warning(f"Reconnect Failed: Client '{client.name}' (ID: {client.id.hex()}) attempting to reconnect, but has no public key on record. Cannot send a new AES key.")
            self.server.network_server.send_response(sock, RESP_RECONNECT_FAIL, client.id)
            return

        # Generate a new AES session key for this reconnected session
        new_aes_key = get_random_bytes(AES_KEY_SIZE_BYTES)
        client.set_aes_key(new_aes_key)

        # Encrypt the new AES key with the client's stored public RSA key
        cipher_rsa = PKCS1_OAEP.new(client.public_key_obj, hashAlgo=SHA256)
        aes_key = client.get_aes_key()
        if aes_key is None:
            raise ServerError("Internal Server Error: Client's AES key is not available for encryption.")
        encrypted_aes_key = cipher_rsa.encrypt(aes_key)

        # Update client's record in the database (updates LastSeen and current session AESKey)
        self.server.db_manager.save_client_to_db(client.id, client.name, client.public_key_bytes, client.get_aes_key())

        # Construct and send Response 1605 (Reconnect Success + AES Key)
        # Payload: client_id[16] (client's ID), encrypted_aes_key[]
        response_payload = client.id + encrypted_aes_key
        self.server.network_server.send_response(sock, RESP_RECONNECT_AES_SENT, response_payload)
        logger.info(f"Client '{client.name}' reconnected successfully. A new AES session key has been sent (encrypted).")

        # Record metrics for client reconnection
        get_metrics_collector().record_counter("client.reconnections.total", tags={'client_id': client.id.hex()})



    def _handle_send_file(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        self.file_transfer_manager.handle_send_file(sock, client, payload)

    def _handle_crc_ok(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        """
        Handles client's confirmation that CRC matches (Code 1029).
        Client object is already resolved.
        Payload: char filename[255]; (null-terminated, padded)
        """
        filename_field_protocol_len = 255
        if len(payload) != filename_field_protocol_len:
            raise ProtocolError(f"CRC OK Request (1029): Invalid payload size. Expected {filename_field_protocol_len} bytes, got {len(payload)}.")

        try:
            # Parse filename from payload
            filename_str = self._parse_string_from_payload(payload, filename_field_protocol_len, MAX_ACTUAL_FILENAME_LENGTH, "Filename")
        except ProtocolError as e_parse:
            logger.error(f"Client '{client.name}': CRC OK request error - {e_parse}")
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
            return

        logger.info(f"Client '{client.name}' confirmed CRC OK for file '{filename_str}'. File transfer is now successfully completed and verified.")

        # Determine the path where the file was saved
        final_save_path = os.path.join(FILE_STORAGE_DIR, filename_str)
        file_size = os.path.getsize(final_save_path) if os.path.exists(final_save_path) else 0
        mod_time = os.path.getmtime(final_save_path) if os.path.exists(final_save_path) else 0
        mod_date = datetime.fromtimestamp(mod_time).isoformat() if mod_time else datetime.now().isoformat()

        # Send Response 1604 (General ACK)
        # Payload: client_id[16] (client's own ID)
        self.server.network_server.send_response(sock, RESP_ACK, client.id)

        # Update the file's record in the database to mark it as verified
        self.server.db_manager.save_file_info_to_db(client.id, filename_str, final_save_path, True, file_size, mod_date)

    def _handle_crc_invalid_retry(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        """
        Handles client's report that CRC does not match and they will retry (Code 1030).
        Client object is already resolved.
        Payload: char filename[255]; (null-terminated, padded)
        """
        filename_field_protocol_len = 255
        if len(payload) != filename_field_protocol_len:
            raise ProtocolError(f"CRC Invalid Retry Request (1030): Invalid payload size. Expected {filename_field_protocol_len}, got {len(payload)}.")

        try:
            filename_str = self._parse_string_from_payload(payload, filename_field_protocol_len, MAX_ACTUAL_FILENAME_LENGTH, "Filename")
        except ProtocolError as e_parse:
            logger.error(f"Client '{client.name}': CRC Invalid Retry request error - {e_parse}")
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
            return

        logger.warning(f"Client '{client.name}' reported CRC invalid for file '{filename_str}'. Client will attempt to retry sending the entire file.")

        # Server-Side Action:
        # The file on disk (if it was saved from the previous attempt) is currently marked as unverified in the DB.
        # The client is expected to re-initiate the entire file transfer sequence (REQ_SEND_FILE from packet 1).
        # The server's in-memory partial file reassembly state for this filename (if any) was cleared
        # when the RESP_FILE_CRC was sent after the previous attempt.
        # If the file exists on disk from the failed attempt, it will be overwritten when the new transfer attempt succeeds.
        # Ensure the database record reflects the file is not verified.
        final_save_path = os.path.join(FILE_STORAGE_DIR, filename_str)
        self.server.db_manager.save_file_info_to_db(client.id, filename_str, final_save_path, False, 0, "", None)

        # Send Response 1604 (General ACK)
        self.server.network_server.send_response(sock, RESP_ACK, client.id)

    def _handle_crc_failed_abort(self, sock: socket.socket, client: Any, payload: bytes) -> None:
        """
        Handles client's report of final CRC failure and aborting transfer (Code 1031).
        Client object is already resolved.
        Payload: char filename[255]; (null-terminated, padded)
        """
        filename_field_protocol_len = 255
        if len(payload) != filename_field_protocol_len:
            raise ProtocolError(f"CRC Failed Abort Request (1031): Invalid payload size. Expected {filename_field_protocol_len}, got {len(payload)}.")

        try:
            filename_str = self._parse_string_from_payload(payload, filename_field_protocol_len, MAX_ACTUAL_FILENAME_LENGTH, "Filename")
        except ProtocolError as e_parse:
            logger.error(f"Client '{client.name}': CRC Failed Abort request error - {e_parse}")
            self.server.network_server.send_response(sock, RESP_GENERIC_SERVER_ERROR)
            return

        logger.error(f"Client '{client.name}' aborted transfer for file '{filename_str}' due to final CRC mismatch. Server will delete its copy of this file.")
        final_save_path = os.path.join(FILE_STORAGE_DIR, filename_str)

        try:
            if os.path.exists(final_save_path):
                os.remove(final_save_path)
                logger.info(f"Successfully removed aborted file from server storage: {final_save_path}")
            else:
                logger.warning(f"Aborted file '{final_save_path}' was not found on server for deletion (Client: '{client.name}'). It might have failed saving earlier.")
        except OSError as e_os_remove:
            logger.error(f"Error occurred while attempting to remove aborted file '{final_save_path}' from storage: {e_os_remove}")

        # Update Database: The file is confirmed as not verified.
        # Depending on specific requirements, one might choose to delete the file record from the database entirely,
        # or simply ensure its 'Verified' status is False. The specification implies keeping a record, so update Verified status.
        self.server.db_manager.save_file_info_to_db(client.id, filename_str, final_save_path, False, 0, "", None)

        # Send Response 1604 (General ACK)
        self.server.network_server.send_response(sock, RESP_ACK, client.id)

    def _parse_string_from_payload(self, payload_bytes: bytes, field_len: int, max_actual_len: int, field_name: str = "String") -> str:
        """
        Parses a null-terminated, zero-padded string from a fixed-length field within a payload.

        Args:
            payload_bytes: The bytes containing the string field.
            field_len: The total length of the field in the protocol.
            max_actual_len: The maximum allowed actual string length.
            field_name: Name of the field for error reporting.

        Returns:
            The parsed string.

        Raises:
            ProtocolError: If the string is invalid or too long.
        """
        return self.server._parse_string_from_payload(payload_bytes, field_len, max_actual_len, field_name)


    def _is_valid_filename_for_storage(self, filename_str: str) -> bool:
        """
        Validates a filename string for storage on the server.

        NOTE: This method now delegates to the shared validation utility
        (Shared.utils.validation_utils.is_valid_filename_for_storage) to ensure
        consistency across the entire codebase.

        Args:
            filename_str: The filename string to validate.

        Returns:
            True if the filename is considered valid and safe for storage, False otherwise.
        """
        return is_valid_filename_for_storage(filename_str)
