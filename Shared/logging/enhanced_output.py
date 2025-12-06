#!/usr/bin/env python3
"""
Enhanced Output System - Consistent Emojis and Colors for CyberBackup Framework

Provides centralized emoji definitions and color-enhanced logging that integrates
with the existing logging infrastructure. Safe fallbacks ensure compatibility.

USAGE:
# Self-contained module, no external Shared.utils imports needed for these classes


    # Enhanced logging with emojis and colors
    logger = EmojiLogger.get_logger("my-component")
    logger.success("Backup completed successfully")  # ✅ in green
    logger.error("Connection failed")               # ❌ in red
    logger.warning("Low disk space")                # ⚠️ in yellow

    # Direct emoji usage
    print(f"{Emojis.FILE} Processing file: {filename}")
    print(f"{Emojis.NETWORK} Connecting to server...")
"""

import logging
import os
import sys
from enum import Enum
from typing import Any, Protocol, cast

# Protocol for enhanced logger with custom methods


class EnhancedLogger(Protocol):
    """Protocol for logger with enhanced methods."""

    def success(self, msg: str, *args, **kwargs) -> None: ...
    def failure(self, msg: str, *args, **kwargs) -> None: ...
    def network(self, msg: str, *args, **kwargs) -> None: ...
    def file_op(self, msg: str, *args, **kwargs) -> None: ...
    def security(self, msg: str, *args, **kwargs) -> None: ...
    def startup(self, msg: str, *args, **kwargs) -> None: ...
    def progress(self, msg: str, *args, **kwargs) -> None: ...


# Try to detect terminal color support
def _supports_color() -> bool:
    """Detect if terminal supports ANSI color codes."""
    print("DEBUG: _supports_color() called", flush=True)
    try:
        # Check environment variables
        if os.getenv("NO_COLOR"):
            return False
        if os.getenv("FORCE_COLOR"):
            return True

        # Check if we're in a terminal
        print("DEBUG: checking isatty", flush=True)
        if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
            return False

        # Windows 10+ supports ANSI colors
        if sys.platform == "win32":
            # SAFEMODE: Disable native console mode setting to prevent hangs
            # We rely on terminals supporting ANSI by default or not at all
            return False

        # Most Unix terminals support colors
        return True
    except Exception:
        return False


class Colors:
    """ANSI color codes with safe fallbacks."""

    _SUPPORTS_COLOR = _supports_color()

    # ANSI Color Codes
    RED = "\033[91m" if _SUPPORTS_COLOR else ""
    GREEN = "\033[92m" if _SUPPORTS_COLOR else ""
    YELLOW = "\033[93m" if _SUPPORTS_COLOR else ""
    BLUE = "\033[94m" if _SUPPORTS_COLOR else ""
    MAGENTA = "\033[95m" if _SUPPORTS_COLOR else ""
    CYAN = "\033[96m" if _SUPPORTS_COLOR else ""
    WHITE = "\033[97m" if _SUPPORTS_COLOR else ""
    GRAY = "\033[90m" if _SUPPORTS_COLOR else ""

    # Background colors
    BG_RED = "\033[101m" if _SUPPORTS_COLOR else ""
    BG_GREEN = "\033[102m" if _SUPPORTS_COLOR else ""
    BG_YELLOW = "\033[103m" if _SUPPORTS_COLOR else ""
    BG_BLUE = "\033[104m" if _SUPPORTS_COLOR else ""

    # Text styles
    BOLD = "\033[1m" if _SUPPORTS_COLOR else ""
    DIM = "\033[2m" if _SUPPORTS_COLOR else ""
    UNDERLINE = "\033[4m" if _SUPPORTS_COLOR else ""

    # Reset
    RESET = "\033[0m" if _SUPPORTS_COLOR else ""

    @classmethod
    def colorize(cls, text: str, color: str, bold: bool = False) -> str:
        """Apply color and optional bold to text."""
        if not cls._SUPPORTS_COLOR:
            return text

        style = cls.BOLD if bold else ""
        return f"{style}{color}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str, bold: bool = False) -> str:
        """Format text as success (green)."""
        return cls.colorize(text, cls.GREEN, bold)

    @classmethod
    def error(cls, text: str, bold: bool = True) -> str:
        """Format text as error (red, bold by default)."""
        return cls.colorize(text, cls.RED, bold)

    @classmethod
    def warning(cls, text: str, bold: bool = False) -> str:
        """Format text as warning (yellow)."""
        return cls.colorize(text, cls.YELLOW, bold)

    @classmethod
    def info(cls, text: str, bold: bool = False) -> str:
        """Format text as info (blue)."""
        return cls.colorize(text, cls.BLUE, bold)

    @classmethod
    def debug(cls, text: str, bold: bool = False) -> str:
        """Format text as debug (gray)."""
        return cls.colorize(text, cls.GRAY, bold)


class Emojis:
    """Centralized emoji definitions for consistent usage across the project."""

    # Status Emojis
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    DEBUG = "🔍"

    # Operation Emojis
    LOADING = "🔄"
    ROCKET = "🚀"
    GEAR = "⚙️"
    WRENCH = "🔧"
    HAMMER = "🔨"

    # File & Storage Emojis
    FILE = "📁"
    DOCUMENT = "📄"
    SAVE = "💾"
    UPLOAD = "📤"
    DOWNLOAD = "📥"
    BACKUP = "💿"
    ARCHIVE = "🗄️"

    # Network & Communication Emojis
    NETWORK = "🌐"
    WIFI = "📶"
    CONNECT = "🔗"
    DISCONNECT = "⛓️‍💥"
    SERVER = "🖥️"
    DATABASE = "🗃️"
    API = "🔌"

    # Security Emojis
    LOCK = "🔒"
    UNLOCK = "🔓"
    KEY = "🔑"
    SHIELD = "🛡️"
    CRYPTO = "🔐"

    # Process & System Emojis
    PROCESS = "⚡"
    MEMORY = "🧠"
    CPU = "🔥"
    DISK = "💽"
    MONITOR = "📊"

    # User Interface Emojis
    BUTTON = "🔘"
    MENU = "📋"
    WINDOW = "🪟"
    CURSOR = "👆"

    # Time & Progress Emojis
    CLOCK = "🕐"
    TIMER = "⏱️"
    PROGRESS = "📈"
    COMPLETE = "🏁"

    # Communication Emojis
    MESSAGE = "💬"
    MAIL = "📧"
    NOTIFICATION = "🔔"
    LOG = "📝"

    # Special Status Emojis
    THUMBS_UP = "👍"
    THUMBS_DOWN = "👎"
    PARTY = "🎉"
    TARGET = "🎯"
    FIRE = "🔥"
    STAR = "⭐"


class LogLevel(Enum):
    """Enhanced log levels with emoji and color mappings."""

    SUCCESS = ("SUCCESS", Emojis.SUCCESS, Colors.GREEN)
    ERROR = ("ERROR", Emojis.ERROR, Colors.RED)
    WARNING = ("WARNING", Emojis.WARNING, Colors.YELLOW)
    INFO = ("INFO", Emojis.INFO, Colors.BLUE)
    DEBUG = ("DEBUG", Emojis.DEBUG, Colors.GRAY)

    # Special operation levels
    STARTUP = ("STARTUP", Emojis.ROCKET, Colors.CYAN)
    SHUTDOWN = ("SHUTDOWN", Emojis.COMPLETE, Colors.MAGENTA)
    NETWORK = ("NETWORK", Emojis.NETWORK, Colors.CYAN)
    FILE_OP = ("FILE", Emojis.FILE, Colors.BLUE)
    SECURITY = ("SECURITY", Emojis.LOCK, Colors.MAGENTA)
    PERFORMANCE = ("PERF", Emojis.PROGRESS, Colors.GREEN)


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis and colors to log messages."""

    LEVEL_MAPPING = {
        logging.DEBUG: LogLevel.DEBUG,
        logging.INFO: LogLevel.INFO,
        logging.WARNING: LogLevel.WARNING,
        logging.ERROR: LogLevel.ERROR,
        logging.CRITICAL: LogLevel.ERROR,
    }

    def __init__(self, fmt=None, datefmt=None, use_colors=True, use_emojis=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and Colors._SUPPORTS_COLOR
        self.use_emojis = use_emojis

    def format(self, record):
        # Get emoji and color for this log level
        log_level = self.LEVEL_MAPPING.get(record.levelno, LogLevel.INFO)
        _, emoji, color = log_level.value  # Unpack but ignore level_name

        # Add emoji to the beginning of the message if enabled
        if self.use_emojis:
            record.msg = f"{emoji} {record.msg}"

        # Format the record normally first
        formatted = super().format(record)

        # Apply color if enabled
        if self.use_colors:
            formatted = Colors.colorize(formatted, color)

        return formatted


class EmojiLogger:
    """Enhanced logger with emoji and color support."""

    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(
        cls, name: str, use_colors: bool = True, use_emojis: bool = True
    ) -> logging.Logger:
        """Get or create an enhanced logger with emoji and color support."""

        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(f"emoji_{name}")
        logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        logger.handlers.clear()

        # Create console handler with emoji formatter
        handler = logging.StreamHandler()
        formatter = EmojiFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            use_colors=use_colors,
            use_emojis=use_emojis,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Add convenience methods
        cls._add_convenience_methods(logger)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def _add_convenience_methods(cls, logger: logging.Logger) -> None:
        """Add convenience methods to logger for common operations."""

        def success(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.SUCCESS} {msg}", *args, **kwargs)

        def failure(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.error(f"{Emojis.ERROR} {msg}", *args, **kwargs)

        def network(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.NETWORK} {msg}", *args, **kwargs)

        def file_op(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.FILE} {msg}", *args, **kwargs)

        def security(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.LOCK} {msg}", *args, **kwargs)

        def startup(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.ROCKET} {msg}", *args, **kwargs)

        def progress(msg: str, *args: Any, **kwargs: Any) -> None:
            logger.info(f"{Emojis.LOADING} {msg}", *args, **kwargs)

        # Add methods to logger instance (explicit cast for dynamic attributes)
        dynamic_logger = cast(Any, logger)
        dynamic_logger.success = success
        dynamic_logger.failure = failure
        dynamic_logger.network = network
        dynamic_logger.file_op = file_op
        dynamic_logger.security = security
        dynamic_logger.startup = startup
        dynamic_logger.progress = progress


def enhanced_print(
    message: str, level: LogLevel = LogLevel.INFO, prefix: str = ""
) -> None:
    """Enhanced print function with emoji and color support."""
    _, emoji, color = level.value  # Unpack but ignore level_name

    if prefix:
        full_message = f"[{prefix}] {emoji} {message}"
    else:
        full_message = f"{emoji} {message}"

    if Colors._SUPPORTS_COLOR:
        full_message = Colors.colorize(full_message, color)

    print(full_message)


def success_print(message: str, prefix: str = "") -> None:
    """Print success message with green color and checkmark emoji."""
    enhanced_print(message, LogLevel.SUCCESS, prefix)


def error_print(message: str, prefix: str = "") -> None:
    """Print error message with red color and X emoji."""
    enhanced_print(message, LogLevel.ERROR, prefix)


def warning_print(message: str, prefix: str = "") -> None:
    """Print warning message with yellow color and warning emoji."""
    enhanced_print(message, LogLevel.WARNING, prefix)


def info_print(message: str, prefix: str = "") -> None:
    """Print info message with blue color and info emoji."""
    enhanced_print(message, LogLevel.INFO, prefix)


def startup_print(message: str, prefix: str = "") -> None:
    """Print startup message with cyan color and rocket emoji."""
    enhanced_print(message, LogLevel.STARTUP, prefix)


def network_print(message: str, prefix: str = "") -> None:
    """Print network message with cyan color and network emoji."""
    enhanced_print(message, LogLevel.NETWORK, prefix)


# Integration with existing logging infrastructure
def enhance_existing_logger(
    logger: logging.Logger, use_colors: bool = True, use_emojis: bool = True
) -> logging.Logger:
    """Enhance an existing logger with emoji and color support."""

    # Find console handlers and enhance them
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            # Check if this is a stdout handler
            try:
                if getattr(handler, "stream", None) == sys.stdout:
                    # Replace formatter with emoji formatter
                    original_fmt = None
                    if handler.formatter and hasattr(handler.formatter, "_fmt"):
                        original_fmt = handler.formatter._fmt

                    handler.setFormatter(
                        EmojiFormatter(
                            fmt=original_fmt,
                            use_colors=use_colors,
                            use_emojis=use_emojis,
                        )
                    )
            except (AttributeError, TypeError):
                # Skip if we can't determine the stream
                continue

    # Add convenience methods
    EmojiLogger._add_convenience_methods(logger)

    return logger


# Export commonly used items
__all__ = [
    "Colors",
    "EmojiLogger",
    "Emojis",
    "LogLevel",
    "enhance_existing_logger",
    "enhanced_print",
    "error_print",
    "info_print",
    "network_print",
    "startup_print",
    "success_print",
    "warning_print",
]
