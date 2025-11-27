"""
Shared file operations utilities for CyberBackup 3.0
"""

import logging
import os

# Configure logger for this module
logger = logging.getLogger(__name__)


def resolve_file_path_for_client(
    client_id: str, filename: str, base_directory: str
) -> str | None:
    """
    Resolve the full file path for a client's file with security checks.

    Args:
        client_id: The client identifier
        filename: The filename to resolve
        base_directory: The base directory where client files are stored

    Returns:
        Full file path or None if validation fails
    """
    try:
        # Validate filename using the shared validation utility
        from Shared.validation.validation_utils import is_valid_filename_for_storage

        if not is_valid_filename_for_storage(filename):
            logger.warning(f"Invalid filename for client {client_id}: {filename}")
            return None

        # Construct the file path
        client_dir = os.path.join(base_directory, client_id)

        # Security: Prevent directory traversal
        full_path = os.path.abspath(os.path.join(client_dir, filename))
        expected_prefix = os.path.abspath(client_dir)

        if not full_path.startswith(expected_prefix):
            logger.error(
                f"Directory traversal attempt detected for client {client_id}, file {filename}"
            )
            return None

        return full_path
    except Exception as e:
        logger.error(
            f"Error resolving file path for client {client_id}, file {filename}: {e}"
        )
        return None


def validate_file_access(full_path: str, base_directory: str) -> bool:
    """
    Validate that the file path is within the allowed base directory.

    Args:
        full_path: The full file path to validate
        base_directory: The allowed base directory

    Returns:
        True if access is valid, False otherwise
    """
    try:
        abs_base = os.path.abspath(base_directory)
        abs_path = os.path.abspath(full_path)

        return abs_path.startswith(abs_base)
    except Exception as e:
        logger.error(f"Error validating file access for {full_path}: {e}")
        return False


def read_file_content_secure(
    file_path: str, max_size: int = 100 * 1024 * 1024
) -> bytes | None:  # 100MB default
    """
    Securely read file content with size validation.

    Args:
        file_path: Path to the file to read
        max_size: Maximum allowed file size in bytes

    Returns:
        File content as bytes or None if error occurs
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return None

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            logger.warning(
                f"File too large: {file_path} ({file_size} bytes, max {max_size})"
            )
            return None

        # Read file content safely
        with open(file_path, "rb") as f:
            content = f.read()

        logger.debug(f"Successfully read file: {file_path} ({len(content)} bytes)")
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def write_file_content_secure(
    file_path: str, content: bytes, base_directory: str
) -> bool:
    """
    Securely write file content with path validation.

    Args:
        file_path: Path where file should be written
        content: Content to write
        base_directory: Base directory that file_path must be within

    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate that the file path is within the allowed directory
        if not validate_file_access(file_path, base_directory):
            logger.error(f"File path outside allowed directory: {file_path}")
            return False

        # Ensure the directory exists
        directory = os.path.dirname(file_path)
        os.makedirs(directory, exist_ok=True)

        # Write the file content
        with open(file_path, "wb") as f:
            f.write(content)

        logger.debug(f"Successfully wrote file: {file_path} ({len(content)} bytes)")
        return True
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return False


def get_file_metadata(file_path: str) -> dict | None:
    """
    Get metadata for a file including size, modification time, etc.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file metadata or None if error
    """
    try:
        if not os.path.exists(file_path):
            return None

        stat = os.stat(file_path)

        return {
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "accessed": stat.st_atime,
        }
    except Exception as e:
        logger.error(f"Error getting metadata for {file_path}: {e}")
        return None


def list_client_files(client_id: str, base_directory: str) -> list[str]:
    """
    List all files for a specific client.

    Args:
        client_id: The client identifier
        base_directory: Base directory where client files are stored

    Returns:
        List of filenames for the client
    """
    try:
        client_dir = os.path.join(base_directory, client_id)

        if not os.path.exists(client_dir):
            return []

        files = []
        for filename in os.listdir(client_dir):
            file_path = os.path.join(client_dir, filename)
            if os.path.isfile(file_path):
                files.append(filename)

        logger.debug(f"Found {len(files)} files for client {client_id}")
        return files
    except Exception as e:
        logger.error(f"Error listing files for client {client_id}: {e}")
        return []


def delete_file_secure(file_path: str, base_directory: str) -> bool:
    """
    Securely delete a file after validating the path.

    Args:
        file_path: Path to the file to delete
        base_directory: Base directory that file_path must be within

    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate that the file path is within the allowed directory
        if not validate_file_access(file_path, base_directory):
            logger.error(f"File path outside allowed directory: {file_path}")
            return False

        if not os.path.exists(file_path):
            logger.warning(f"File does not exist for deletion: {file_path}")
            return False

        os.remove(file_path)
        logger.debug(f"Successfully deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False
