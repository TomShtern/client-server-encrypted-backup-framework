#!/usr/bin/env python3
"""
Logging Utilities for Client-Server Encrypted Backup Framework
Provides standardized logging setup, dual output, and enhanced logging capabilities
with emoji and color support integration.
"""

import contextlib
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

# Log rotation settings
LOG_ROTATION_MAX_FILES = 6  # Keep last 6 log files
LOG_ROTATION_MAX_SIZE_MB = 700  # Maximum total size in MB

# Default log format used across handlers
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Import the safe_print function to prevent console encoding errors
from Shared.filesystem.utf8_solution import safe_print  # noqa: E402

# Try to import enhanced output for emoji/color support
try:
    from Shared.logging.enhanced_output import Colors as EnhancedColors  # noqa: E402
    from Shared.logging.enhanced_output import Emojis as EnhancedEmojis  # noqa: E402
    from Shared.logging.enhanced_output import enhance_existing_logger  # noqa: E402

    ENHANCED_OUTPUT_AVAILABLE = True
except ImportError:
    ENHANCED_OUTPUT_AVAILABLE = False
    enhance_existing_logger = None
    EnhancedEmojis = None
    EnhancedColors = None

# Define emoji interface that works with both enhanced and fallback
if ENHANCED_OUTPUT_AVAILABLE and EnhancedEmojis is not None:
    Emojis = EnhancedEmojis  # type: ignore
else:
    # Fallback emoji definitions if enhanced output is not available
    class Emojis:
        SUCCESS = "✅"
        ERROR = "❌"
        WARNING = "⚠️"
        INFO = "ℹ️"
        ROCKET = "🚀"
        GEAR = "⚙️"


# Fallback Colors implementation (no-op colorization) when enhanced colors are not available
if ENHANCED_OUTPUT_AVAILABLE and EnhancedColors is not None:
    Colors = EnhancedColors  # type: ignore
else:

    class Colors:
        _SUPPORTS_COLOR = False

        # Provide attributes expected by callers (no-op strings)
        BOLD = ""
        DIM = ""
        UNDERLINE = ""
        RESET = ""

        @classmethod
        def colorize(cls, text: str, color: str, bold: bool = False) -> str:
            return text

        @classmethod
        def success(cls, text: str, bold: bool = False) -> str:
            return text

        @classmethod
        def error(cls, text: str, bold: bool = False) -> str:
            return text

        @classmethod
        def warning(cls, text: str, bold: bool = False) -> str:
            return text

        @classmethod
        def info(cls, text: str, bold: bool = False) -> str:
            return text

        @classmethod
        def debug(cls, text: str, bold: bool = False) -> str:
            return text


# Centralized CODE MAPS for maintainability and UI consumption.
# Each entry is either a section (has 'section') or an entry with code/text/emoji/level.
CODE_MAPS: dict[str, list[dict[str, str]]] = {
    "api": [
        {"section": "HTTP STATUS CODES"},
        {
            "code": "1xx",
            "text": "Informational (100 Continue, 101 Switching Protocols)",
            "emoji": Emojis.INFO,
            "level": "info",
        },
        {
            "code": "200",
            "text": "OK (Success)",
            "emoji": Emojis.SUCCESS,
            "level": "success",
        },
        {"code": "201", "text": "Created", "emoji": Emojis.SUCCESS, "level": "success"},
        {"code": "202", "text": "Accepted", "emoji": Emojis.INFO, "level": "info"},
        {"code": "204", "text": "No Content", "emoji": Emojis.INFO, "level": "info"},
        {
            "code": "3xx",
            "text": "Redirection (301/302)",
            "emoji": Emojis.ROCKET,
            "level": "info",
        },
        {
            "code": "400",
            "text": "Bad Request",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "401",
            "text": "Unauthorized",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "403",
            "text": "Forbidden",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {"code": "404", "text": "Not Found", "emoji": Emojis.ERROR, "level": "error"},
        {
            "code": "408",
            "text": "Request Timeout",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "409",
            "text": "Conflict",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "413",
            "text": "Payload Too Large",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "415",
            "text": "Unsupported Media Type",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "429",
            "text": "Too Many Requests",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "500",
            "text": "Internal Server Error",
            "emoji": Emojis.ERROR,
            "level": "error",
        },
        {"code": "502", "text": "Bad Gateway", "emoji": Emojis.ERROR, "level": "error"},
        {
            "code": "503",
            "text": "Service Unavailable",
            "emoji": Emojis.ERROR,
            "level": "error",
        },
        {
            "code": "504",
            "text": "Gateway Timeout",
            "emoji": Emojis.ERROR,
            "level": "error",
        },
    ],
    "backup": [
        {"section": "PROTOCOL CODES"},
        {
            "code": "PROTOCOL",
            "text": "Version 3",
            "emoji": Emojis.ROCKET,
            "level": "info",
        },
        {
            "code": "REQ_REGISTER (1025)",
            "text": "Client registration",
            "emoji": Emojis.ROCKET,
            "level": "info",
        },
        {
            "code": "REQ_SEND_FILE (1028)",
            "text": "File transfer start",
            "emoji": Emojis.SUCCESS,
            "level": "success",
        },
        {
            "code": "RESP_REG_OK (1600)",
            "text": "Registration success",
            "emoji": Emojis.SUCCESS,
            "level": "success",
        },
        {
            "code": "RESP_FILE_CRC (1603)",
            "text": "Transfer verification",
            "emoji": Emojis.INFO,
            "level": "info",
        },
        {"section": "ERROR CODES"},
        {
            "code": "CRC_MISMATCH",
            "text": "File integrity error",
            "emoji": Emojis.ERROR,
            "level": "error",
        },
        {
            "code": "AUTH_FAIL",
            "text": "Authentication failed",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {
            "code": "DISK_FULL",
            "text": "Storage full",
            "emoji": Emojis.WARNING,
            "level": "warning",
        },
        {"section": "SECURITY"},
        {"note": "RSA-1024 + AES-256 encryption"},
    ],
}


def get_code_map(server_type: str) -> list[dict[str, str]]:
    """Return the structured CODE MAP for a given server type.

    This makes the data easy to consume from UIs or other tools.
    """
    st = server_type.lower()
    return CODE_MAPS["api"] if "api" in st else CODE_MAPS["backup"]


def cleanup_old_logs(
    log_dir: str = "logs",
    max_files: int = LOG_ROTATION_MAX_FILES,
    max_size_mb: int = LOG_ROTATION_MAX_SIZE_MB,
) -> dict[str, int]:
    """
    Clean up old log files based on count and total size limits.

    Strategy:
    1. Keep only the last `max_files` log files
    2. If total size exceeds `max_size_mb`, delete oldest files until under limit

    Args:
        log_dir: Directory containing log files
        max_files: Maximum number of log files to keep (default: 6)
        max_size_mb: Maximum total size in MB (default: 700)

    Returns:
        Dictionary with cleanup statistics
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return {"deleted_count": 0, "deleted_bytes": 0, "remaining_count": 0}

    # Get all log files sorted by modification time (newest first)
    log_files = sorted(
        log_path.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True
    )

    if not log_files:
        return {"deleted_count": 0, "deleted_bytes": 0, "remaining_count": 0}

    deleted_count = 0
    deleted_bytes = 0

    # Step 1: Keep only max_files
    if len(log_files) > max_files:
        files_to_delete = log_files[max_files:]
        for f in files_to_delete:
            try:
                deleted_bytes += f.stat().st_size
                f.unlink()
                deleted_count += 1
            except OSError:
                pass  # Skip files that can't be deleted
        log_files = log_files[:max_files]

    # Step 2: Enforce size limit
    max_size_bytes = max_size_mb * 1024 * 1024
    while log_files:
        total_size = sum(f.stat().st_size for f in log_files if f.exists())
        if total_size <= max_size_bytes:
            break
        # Delete oldest file
        oldest = log_files.pop()
        try:
            deleted_bytes += oldest.stat().st_size
            oldest.unlink()
            deleted_count += 1
        except OSError:
            pass

    remaining_count = len(list(log_path.glob("*.log")))

    return {
        "deleted_count": deleted_count,
        "deleted_bytes": deleted_bytes,
        "remaining_count": remaining_count,
    }


def setup_dual_logging(
    logger_name: str,
    server_type: str,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    console_format: str = "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
    file_format: str | None = None,
    log_dir: str = "logs",
    enable_enhanced_output: bool = True,
) -> tuple[logging.Logger, str]:
    """
    Set up dual logging: console and file output with different levels.
    Now with enhanced emoji and color support!

    Args:
        logger_name: Name for the logger
        server_type: Type of server (e.g., "backup-server", "api-server")
        console_level: Logging level for console output
        file_level: Logging level for file output
        console_format: Format string for console messages
        file_format: Format string for file messages (defaults to console_format)
        log_dir: Directory to store log files
        enable_enhanced_output: Enable emoji and color output (default: True)

    Returns:
        Tuple of (logger, log_file_path)
    """
    if file_format is None:
        file_format = console_format

    # Check environment variable to disable enhanced output for cleaner terminal output
    disable_code_map = os.environ.get("DISABLE_CODE_MAP", "").lower() in (
        "true",
        "1",
        "yes",
    )
    fletv2_context = (
        "FletV2" in os.getcwd() or os.path.basename(os.getcwd()) == "FletV2"
    )

    if disable_code_map or fletv2_context:
        enable_enhanced_output = False

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Clean up old logs before creating new one (smart rotation)
    cleanup_old_logs(log_dir)

    # Generate log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{server_type}_{timestamp}.log"
    log_file_path = os.path.join(log_dir, log_filename)

    # Console handler with enhanced output support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Enhance logger with emoji and color support if available and enabled
    if (
        enable_enhanced_output
        and ENHANCED_OUTPUT_AVAILABLE
        and enhance_existing_logger is not None
    ):
        with contextlib.suppress(Exception):
            # Disable emojis on Windows to prevent Unicode encoding errors with cp1255
            use_emojis = sys.platform != "win32"
            enhance_existing_logger(logger, use_colors=True, use_emojis=use_emojis)

    # File handler
    file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(file_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Plain startup messages that will be logged to file (no ANSI/color sequences)
    file_startup_messages = [
        f"=== {server_type.upper()} LOGGING INITIALIZED ===",
        f"Console Level: {logging.getLevelName(console_level)}",
        f"File Level: {logging.getLevelName(file_level)}",
        f"Log File: {log_file_path}",
        "=" * 60,
        f"Live Monitoring: Get-Content {log_file_path} -Wait -Tail 50",
    ]

    # Console-only colored/emoji CODE-MAP (printed to stdout only so file logs remain plain)
    console_lines: list[str] = []
    console_lines.append(
        Colors.info(f"=== {server_type.upper()} LOGGING INITIALIZED ===", bold=True)
    )
    console_lines.append(
        Colors.info(f"Console Level: {logging.getLevelName(console_level)}")
    )
    console_lines.append(Colors.info(f"File Level: {logging.getLevelName(file_level)}"))
    console_lines.append(Colors.debug(f"Log File: {log_file_path}"))
    console_lines.append("")
    console_lines.append(
        Colors.BOLD
        + Colors.UNDERLINE
        + "CODE MAP: Common status / progress codes"
        + Colors.RESET
    )

    # Helper to build colored code lines with emoji
    def codeline(code: str, text: str, emoji: str, color_fn: Callable[..., str]) -> str:
        # color_fn is a Colors.<method> callable that accepts (text, bold=False)
        return color_fn(f" {emoji} {code} - {text}")

    # Render structured CODE_MAP for this server type
    for entry in get_code_map(server_type):
        if "section" in entry:
            console_lines.append(Colors.BOLD + entry["section"] + Colors.RESET)
            continue
        if "note" in entry:
            level = entry.get("level")
            note_text = entry["note"]
            if level == "warning":
                console_lines.append(Colors.warning(note_text, bold=True))
            else:
                console_lines.append(Colors.info(note_text))
            continue
        # Standard code entry (code/text/emoji/level)
        code = entry.get("code", "")
        text = entry.get("text", "")
        emoji = entry.get("emoji", "")
        lvl = entry.get("level", "info")
        color_fn = getattr(Colors, lvl, Colors.info)
        console_lines.append(codeline(code, text, emoji, color_fn))

    console_lines.append("")
    console_lines.append(Colors.debug("=" * 60))
    console_lines.append(
        Colors.debug(f"Live Monitoring: Get-Content {log_file_path} -Wait -Tail 50")
    )

    # Print the colorful console-only banner (keeps file logs plain)
    try:
        for line in console_lines:
            # Use safe_print to avoid console encoding errors
            safe_print(line)
    except Exception:
        # Fall back to logging plain lines if printing fails
        for line in console_lines:
            logger.info(line)

    # Log startup messages to file (plain text)
    for msg in file_startup_messages:
        logger.info(msg)

    return logger, log_file_path


def create_log_monitor_info(server_type: str, log_file_path: str) -> dict[str, Any]:
    """
    Create monitoring information for log files.

    Args:
        server_type: Type of server
        log_file_path: Path to the log file

    Returns:
        Dictionary with monitoring information
    """
    return {
        "server_type": server_type,
        "log_file": log_file_path,
        "created_at": datetime.now().isoformat(),
        "monitor_commands": {
            "tail_logs": f"tail -f {log_file_path}",
            "grep_errors": f"grep -i error {log_file_path}",
            "grep_warnings": f"grep -i warn {log_file_path}",
        },
    }


class EnhancedLogger:
    """
    Enhanced logger wrapper that provides structured logging capabilities.
    """

    def __init__(self, component: str, base_logger: logging.Logger):
        self.component = component
        self.base_logger = base_logger
        self._context: dict[str, Any] = {}

    def set_context(self, **kwargs: Any) -> None:
        """Set context variables for this logger."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context variables."""
        self._context.clear()

    def _log_structured(self, level: int, message: str, **kwargs: Any) -> None:
        """Log a structured message with context."""
        context = self._context.copy()
        context.update(kwargs)

        # Log as human-readable for console with context information
        structured_msg = f"[{self.component}] {message}"
        if context:
            structured_msg += f" | Context: {context}"

        self.base_logger.log(level, structured_msg)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with context."""
        self._log_structured(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with context."""
        self._log_structured(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with context."""
        self._log_structured(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with context."""
        self._log_structured(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with context."""
        self._log_structured(logging.CRITICAL, message, **kwargs)


def create_enhanced_logger(
    component: str, base_logger: logging.Logger
) -> EnhancedLogger:
    """
    Create an enhanced logger with structured logging capabilities.

    Args:
        component: Component name for logging context
        base_logger: Base Python logger to wrap

    Returns:
        Enhanced logger instance
    """
    return EnhancedLogger(component, base_logger)


def log_performance_metrics(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs: Any,
) -> None:
    """
    Log performance metrics for operations.

    Args:
        logger: Logger to use
        operation: Operation name
        duration_ms: Duration in milliseconds
        success: Whether the operation was successful
        **kwargs: Additional context
    """
    context: dict[str, Any] = kwargs | {
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        "performance_metric": True,
    }

    status = "completed" if success else "failed"
    logger.info(
        f"⚡ Performance: {operation} {status} in {duration_ms:.2f}ms", extra=context
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with standard configuration.

    Args:
        name: Logger name

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def configure_root_logger(level: int = logging.INFO):
    """
    Configure the root logger with basic settings.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=level,
        format=DEFAULT_LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Convenience functions for quick setup
def quick_console_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Quickly create a console-only logger.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Console logger
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # Only add handler if none exist
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


def quick_file_logger(
    name: str, filename: str, level: int = logging.DEBUG
) -> logging.Logger:
    """
    Quickly create a file-only logger.

    Args:
        name: Logger name
        filename: Log file name
        level: Logging level

    Returns:
        File logger
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # Only add handler if none exist
        handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


if __name__ == "__main__":
    # Test the logging utilities
    print("Testing logging utilities...")

    # Test dual logging setup
    logger, log_file = setup_dual_logging(
        logger_name="test_logger",
        server_type="test-server",
        console_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    # Test enhanced logger
    enhanced = create_enhanced_logger("test-component", logger)
    enhanced.set_context(user_id="test_user", session_id="test_session")

    # Test logging
    logger.info("Standard logger test message")
    enhanced.info("Enhanced logger test message")
    enhanced.error("Test error message", error_code="TEST_001")

    # Test performance logging
    log_performance_metrics(logger, "test_operation", 123.45, status="success")

    print("Logging utilities test completed!")
    print(f"Log file created: {log_file}")
