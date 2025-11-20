#!/usr/bin/env python3
"""
Unified Configuration Management System
Extends the existing ConfigurationManager to handle ALL configuration formats
and provides migration tools for legacy .info files.

This addresses the critical configuration management issues identified in CLAUDE.md:
- Multiple transfer.info and me.info files scattered
- Configuration duplicates causing confusion
- Hard-coded values across 80+ locations
"""

import json
import logging
import os
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Import the existing ConfigurationManager
# from Shared.config_manager import ConfigurationManager

logger = logging.getLogger(__name__)


@dataclass
class ConfigurationMigration:
    """Track configuration migration from legacy formats."""

    source_file: str
    target_key: str
    value: Any
    migrated_at: datetime = field(default_factory=datetime.now)
    backup_created: bool = False


class LegacyConfigurationAdapter:
    """
    Adapter for legacy configuration formats (.info files, hardcoded values).
    Provides unified access while maintaining backward compatibility.
    """

    def __init__(self, base_path: str = "."):
        """
        Initialize the legacy configuration adapter.

        Args:
            base_path: Base directory for finding configuration files
        """
        self.base_path = Path(base_path)
        self.legacy_configs: dict[str, Any] = {}
        self.migrations: list[ConfigurationMigration] = []
        self.lock = threading.RLock()

        logger.info(f"LegacyConfigurationAdapter initialized with base_path: {self.base_path}")

    def read_transfer_info(self, file_path: str | None = None) -> dict[str, str] | None:
        """
        Read transfer.info file in the legacy 3-line format.

        Args:
            file_path: Path to transfer.info file. If None, searches common locations.

        Returns:
            Dictionary with server_address, username, file_path or None if not found
        """
        if file_path is None:
            # Search common locations for transfer.info
            search_paths = [
                self.base_path / "transfer.info",
                self.base_path / "build" / "Release" / "transfer.info",
                self.base_path / "client" / "transfer.info",
                Path.cwd() / "transfer.info",
            ]
        else:
            search_paths = [Path(file_path)]

        for path in search_paths:
            try:
                if path.exists():
                    with open(path, encoding="utf-8") as f:
                        lines = [line.strip() for line in f.readlines()]

                    if len(lines) >= 3:
                        # Parse server:port format
                        server_parts = lines[0].split(":")
                        if len(server_parts) == 2:
                            server_host = server_parts[0]
                            server_port = int(server_parts[1])
                        else:
                            server_host = lines[0]
                            server_port = 1256  # Default

                        config = {
                            "server_address": lines[0],
                            "server_host": server_host,
                            "server_port": server_port,
                            "username": lines[1],
                            "file_path": lines[2],
                        }

                        logger.info(f"Successfully read transfer.info from: {path}")
                        return config
                    else:
                        logger.warning(
                            f"Invalid transfer.info format in {path}: expected 3 lines, got {len(lines)}"
                        )

            except Exception as e:
                logger.warning(f"Failed to read transfer.info from {path}: {e}")

        logger.warning("No valid transfer.info file found in search paths")
        return None

    def read_port_info(self, file_path: str | None = None) -> int | None:
        """
        Read port.info file containing a single port number.

        Args:
            file_path: Path to port.info file. If None, searches common locations.

        Returns:
            Port number or None if not found
        """
        if file_path is None:
            search_paths = [self.base_path / "server" / "port.info", self.base_path / "port.info"]
        else:
            search_paths = [Path(file_path)]

        for path in search_paths:
            try:
                if path.exists():
                    with open(path, encoding="utf-8") as f:
                        port_str = f.read().strip()

                    port = int(port_str)
                    if 1 <= port <= 65535:
                        logger.info(f"Successfully read port.info from: {path}")
                        return port
                    else:
                        logger.warning(f"Invalid port in {path}: {port}")

            except Exception as e:
                logger.warning(f"Failed to read port.info from {path}: {e}")

        return None

    def scan_hardcoded_values(self) -> dict[str, list[str]]:
        """
        Scan source files for hardcoded configuration values.

        Returns:
            Dictionary mapping config keys to files containing hardcoded values
        """
        hardcoded_patterns = {
            "server_port_1256": [r"\b1256\b", r"port.*1256", r"1256.*port"],
            "api_port_9090": [r"\b9090\b", r"port.*9090", r"9090.*port"],
            "localhost_host": [r"127\.0\.0\.1", r"localhost"],
            "received_files_dir": [r"received_files"],
            "defensive_db": [r"defensive\.db"],
            "transfer_info": [r"transfer\.info"],
            "me_info": [r"me\.info"],
        }

        results: dict[str, list[str]] = {}
        source_extensions = [".py", ".cpp", ".h", ".js", ".html"]

        for config_key, patterns in hardcoded_patterns.items():
            results[config_key] = []

            # Search through source files
            for ext in source_extensions:
                for file_path in self.base_path.rglob(f"*{ext}"):
                    try:
                        if "vcpkg" in str(file_path):  # Skip vcpkg directory
                            continue

                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                results[config_key].append(str(file_path))
                                break  # Found in this file, no need to check other patterns

                    except Exception as e:
                        logger.debug(f"Could not scan {file_path}: {e}")

        return results

    def create_migration_plan(self) -> list[ConfigurationMigration]:
        """
        Create a migration plan for converting legacy configurations to unified format.

        Returns:
            List of ConfigurationMigration objects
        """
        migrations: list[ConfigurationMigration] = []

        # Migrate transfer.info
        transfer_config = self.read_transfer_info()
        if transfer_config:
            migrations.extend(
                [
                    ConfigurationMigration(
                        "transfer.info", "client.default_server_host", transfer_config["server_host"]
                    ),
                    ConfigurationMigration(
                        "transfer.info", "client.default_server_port", transfer_config["server_port"]
                    ),
                    ConfigurationMigration(
                        "transfer.info", "client.default_username", transfer_config["username"]
                    ),
                    ConfigurationMigration(
                        "transfer.info", "client.last_file_path", transfer_config["file_path"]
                    ),
                ]
            )

        # Migrate port.info
        port = self.read_port_info()
        if port:
            migrations.append(ConfigurationMigration("server/port.info", "server.port", port))

        # Migrate hardcoded values
        hardcoded = self.scan_hardcoded_values()
        for config_key, files in hardcoded.items():
            if files:  # Only migrate if hardcoded values found
                if config_key == "server_port_1256":
                    migrations.append(
                        ConfigurationMigration(f"hardcoded_in_{len(files)}_files", "server.port", 1256)
                    )
                elif config_key == "api_port_9090":
                    migrations.append(
                        ConfigurationMigration(f"hardcoded_in_{len(files)}_files", "api.port", 9090)
                    )
                elif config_key == "localhost_host":
                    migrations.append(
                        ConfigurationMigration(f"hardcoded_in_{len(files)}_files", "server.host", "127.0.0.1")
                    )
                elif config_key == "received_files_dir":
                    migrations.append(
                        ConfigurationMigration(
                            f"hardcoded_in_{len(files)}_files", "server.file_storage_dir", "received_files"
                        )
                    )
                elif config_key == "defensive_db":
                    migrations.append(
                        ConfigurationMigration(
                            f"hardcoded_in_{len(files)}_files", "server.database_name", "defensive.db"
                        )
                    )

        return migrations


class UnifiedConfigurationManager:
    """
    Unified Configuration Manager that extends ConfigurationManager
    to handle all configuration formats and provide migration capabilities.
    """

    def __init__(self, config_dir: str = "config", environment: str = "development", base_path: str = "."):
        """
        Initialize the unified configuration manager.

        Args:
            config_dir: Directory containing JSON configuration files
            environment: Current environment (development/production/testing)
            base_path: Base path for finding legacy configuration files
        """
        # Store configuration directory and environment
        self.config_dir = Path(config_dir)
        self.environment = environment

        # Initialize configuration data with defaults
        self.config_data: dict[str, Any] = {
            "server": {
                "host": "127.0.0.1",
                "port": 1256,
                "database_name": "defensive.db",
                "file_storage_dir": "data/storage",
                "max_clients": 10,
                "timeout": 30.0
            },
            "api": {
                "host": "127.0.0.1",
                "port": 9090
            },
            "logging": {
                "level": "INFO"
            },
            "client": {}
        }

        # Load from JSON configuration files if they exist
        self._load_json_config()

        # Initialize legacy adapter
        self.legacy_adapter = LegacyConfigurationAdapter(base_path)

        # Configuration cache and monitoring
        self.config_cache: dict[str, Any] = {}
        self.config_watchers: list[Callable[[str, Any, Any], None]] = []
        self.lock = threading.RLock()

        # Load all configurations
        self._load_unified_configuration()

        logger.info(f"UnifiedConfigurationManager initialized for environment: {environment}")

    def _load_json_config(self):
        """Load configuration from JSON files."""
        if not self.config_dir.exists():
            logger.info(f"Config directory {self.config_dir} does not exist, using defaults")
            return

        # Load environment-specific config file
        config_file = self.config_dir / f"{self.environment}.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # Deep merge the loaded config into config_data
                self._deep_merge(self.config_data, loaded_config)
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load config from {config_file}: {e}")

    def _deep_merge(self, base: dict, updates: dict):
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _load_unified_configuration(self):
        """Load configuration from all sources with proper precedence."""
        with self.lock:
            # Start with base JSON configuration
            self.config_cache = dict(self.config_data)

            # Apply legacy configurations (lower precedence)
            self._apply_legacy_configurations()

            # Apply environment variables (highest precedence)
            self._apply_environment_variables()

    def _apply_legacy_configurations(self):
        """Apply configuration from legacy sources."""
        # transfer.info overrides for client defaults
        transfer_config = self.legacy_adapter.read_transfer_info()
        if transfer_config:
            self._safe_set("client.last_server_host", transfer_config["server_host"])
            self._safe_set("client.last_server_port", transfer_config["server_port"])
            self._safe_set("client.last_username", transfer_config["username"])
            self._safe_set("client.last_file_path", transfer_config["file_path"])

        # port.info overrides server port
        port = self.legacy_adapter.read_port_info()
        if port:
            self._safe_set("server.port", port)

    def _apply_environment_variables(self):
        """Apply configuration from environment variables."""
        env_mappings = {
            "BACKUP_SERVER_HOST": "server.host",
            "BACKUP_SERVER_PORT": "server.port",
            "BACKUP_API_PORT": "api.port",
            "BACKUP_DATABASE_NAME": "server.database_name",
            "BACKUP_FILE_STORAGE_DIR": "server.file_storage_dir",
            "BACKUP_LOG_LEVEL": "logging.level",
            "BACKUP_MAX_CLIENTS": "server.max_clients",
            "BACKUP_ENVIRONMENT": "environment",
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Type conversion based on config key
                if "port" in config_key or "max_clients" in config_key:
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {env_value}")
                        continue
                elif config_key == "server.timeout":
                    try:
                        env_value = float(env_value)
                    except ValueError:
                        logger.warning(f"Invalid float value for {env_var}: {env_value}")
                        continue

                self._safe_set(config_key, env_value)
                logger.info(f"Applied environment variable {env_var} -> {config_key}")

    def _safe_set(self, key: str, value: Any):
        """Safely set a configuration value with dot notation."""
        keys = key.split(".")
        target = self.config_cache

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        old_value = target.get(keys[-1])
        target[keys[-1]] = value

        # Notify watchers
        for watcher in self.config_watchers:
            try:
                watcher(key, old_value, value)
            except Exception as e:
                logger.error(f"Configuration watcher failed: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation with unified precedence.

        Precedence order (highest to lowest):
        1. Environment variables
        2. JSON configuration files
        3. Legacy .info files
        4. Default values
        """
        with self.lock:
            keys = key.split(".")
            value = self.config_cache

            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default

    def set(self, key: str, value: Any, persist: bool = True):
        """
        Set configuration value and optionally persist to file.

        Args:
            key: Configuration key in dot notation
            value: Value to set
            persist: Whether to save to configuration file
        """
        with self.lock:
            self._safe_set(key, value)

            if persist:
                # Update the config_data and save to file
                keys = key.split(".")
                target = self.config_data
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                target[keys[-1]] = value
                self._save_configuration()

    def add_watcher(self, callback: Callable[[str, Any, Any], None]):
        """
        Add a configuration change watcher.

        Args:
            callback: Function called with (key, old_value, new_value) on changes
        """
        with self.lock:
            self.config_watchers.append(callback)

    def remove_watcher(self, callback: Callable[[str, Any, Any], None]):
        """Remove a configuration change watcher."""
        with self.lock:
            if callback in self.config_watchers:
                self.config_watchers.remove(callback)

    def migrate_legacy_configurations(self, create_backups: bool = True) -> list[ConfigurationMigration]:
        """
        Migrate all legacy configurations to unified format.

        Args:
            create_backups: Whether to create backup files before migration

        Returns:
            List of completed migrations
        """
        migration_plan = self.legacy_adapter.create_migration_plan()
        completed_migrations: list[ConfigurationMigration] = []

        logger.info(f"Starting migration of {len(migration_plan)} configuration items")

        for migration in migration_plan:
            try:
                # Create backup if requested
                if create_backups and migration.source_file.endswith(".info"):
                    source_path = Path(migration.source_file)
                    if source_path.exists():
                        backup_path = source_path.with_suffix(
                            f".info.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        source_path.rename(backup_path)
                        migration.backup_created = True
                        logger.info(f"Created backup: {backup_path}")

                # Apply the migration
                self.set(migration.target_key, migration.value, persist=True)
                migration.migrated_at = datetime.now()
                completed_migrations.append(migration)

                logger.info(f"Migrated {migration.source_file} -> {migration.target_key} = {migration.value}")

            except Exception as e:
                logger.error(f"Migration failed for {migration.source_file}: {e}")

        logger.info(f"Migration completed: {len(completed_migrations)}/{len(migration_plan)} successful")
        return completed_migrations

    def generate_transfer_info(
        self, username: str, file_path: str, output_path: str = "transfer.info"
    ) -> str:
        """
        Generate transfer.info file from current configuration.

        Args:
            username: Username for the transfer
            file_path: Path to file being transferred
            output_path: Where to write the transfer.info file

        Returns:
            Path to generated transfer.info file
        """
        server_host = self.get("server.host", "127.0.0.1")
        server_port = self.get("server.port", 1256)

        content = f"{server_host}:{server_port}\n{username}\n{file_path}\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated transfer.info at: {output_path}")
        return output_path

    def validate_all_configurations(self) -> dict[str, list[str]]:
        """
        Validate all configuration sources and return detailed results.

        Returns:
            Dictionary with validation results by source
        """
        results: dict[str, list[str]] = {
            "json_config": [],
            "legacy_config": [],
            "environment_vars": [],
            "overall": [],
        }

        # Validate JSON configuration (basic validation)
        # Check for required fields
        if "server" not in self.config_data:
            results["json_config"].append("Missing 'server' configuration section")
        if "api" not in self.config_data:
            results["json_config"].append("Missing 'api' configuration section")

        # Validate legacy configurations
        transfer_config = self.legacy_adapter.read_transfer_info()
        if transfer_config:
            try:
                port = int(transfer_config["server_port"])
                if not (1 <= port <= 65535):
                    results["legacy_config"].append(
                        f"Invalid server port in transfer.info: {transfer_config['server_port']}"
                    )
            except (ValueError, TypeError):
                results["legacy_config"].append(
                    f"Invalid server port format in transfer.info: {transfer_config['server_port']}"
                )

            if not str(transfer_config.get("username", "")).strip():
                results["legacy_config"].append("Empty username in transfer.info")

        # Check for configuration conflicts
        json_port = self.get("server.port")
        legacy_port = self.legacy_adapter.read_port_info()
        if json_port and legacy_port and json_port != legacy_port:
            results["overall"].append(
                f"Port conflict: JSON config ({json_port}) vs port.info ({legacy_port})"
            )

        # Validate critical paths
        file_storage_dir = self.get("server.file_storage_dir")
        if file_storage_dir and not os.path.exists(file_storage_dir):
            results["overall"].append(f"File storage directory does not exist: {file_storage_dir}")

        return results

    def _save_configuration(self):
        """Save current configuration to JSON file."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

        config_file = self.config_dir / f"{self.environment}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_file}: {e}")

    def get_configuration_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of current configuration."""
        return {
            "environment": self.environment,
            "config_sources": {
                "json_files": list(self.config_dir.glob("*.json")),
                "legacy_files": {
                    "transfer_info": self.legacy_adapter.read_transfer_info() is not None,
                    "port_info": self.legacy_adapter.read_port_info() is not None,
                },
                "environment_variables": [k for k in os.environ.keys() if k.startswith("BACKUP_")],
            },
            "key_configurations": {
                "server_host": self.get("server.host"),
                "server_port": self.get("server.port"),
                "api_port": self.get("api.port", 9090),
                "database_name": self.get("server.database_name"),
                "file_storage_dir": self.get("server.file_storage_dir"),
                "log_level": self.get("logging.level"),
            },
            "hardcoded_analysis": self.legacy_adapter.scan_hardcoded_values(),
        }


# Global unified configuration manager instance
_global_unified_config = None
_config_lock = threading.Lock()


def get_unified_config(environment: str = "development") -> UnifiedConfigurationManager:
    """Get the global unified configuration manager instance (singleton)."""
    global _global_unified_config
    with _config_lock:
        if _global_unified_config is None:
            _global_unified_config = UnifiedConfigurationManager(environment=environment)
        return _global_unified_config


# Convenience functions for easy access
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value from the global unified config."""
    return get_unified_config().get(key, default)


def set_config(key: str, value: Any, persist: bool = True):
    """Set configuration value in the global unified config."""
    get_unified_config().set(key, value, persist)


# Example usage and testing
def test_unified_configuration():
    """Test the unified configuration system."""
    print("Testing Unified Configuration System...")

    config = UnifiedConfigurationManager()

    # Test basic functionality
    print(f"Server host: {config.get('server.host')}")
    print(f"Server port: {config.get('server.port')}")
    print(f"Database name: {config.get('server.database_name')}")

    # Test legacy integration
    transfer_config = config.legacy_adapter.read_transfer_info()
    print(
        f"Legacy transfer.info found: {transfer_config}"
        if transfer_config
        else "No legacy transfer.info found"
    )

    # Test hardcoded value detection
    hardcoded = config.legacy_adapter.scan_hardcoded_values()
    hardcoded_files = [
        f"Hardcoded {key} found in {len(files)} files" for key, files in hardcoded.items() if files
    ]
    print("\n".join(hardcoded_files) if hardcoded_files else "No hardcoded values found")

    # Test configuration summary
    summary = config.get_configuration_summary()
    print(f"Configuration summary: {json.dumps(summary, indent=2, default=str)}")

    print("Unified Configuration System test completed!")


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    test_unified_configuration()
