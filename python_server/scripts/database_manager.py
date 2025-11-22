#!/usr/bin/env python3
"""
Database Management Utility for Encrypted Backup Framework
Provides command-line interface for database operations, migrations, and maintenance.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Setup standardized import paths
# Add project root to sys.path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Shared.filesystem.path_utils import setup_imports

setup_imports()


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(message: str, status: str = "INFO") -> None:
    """Print a status message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {status}: {message}")


def cmd_status(args: argparse.Namespace) -> int | None:
    """Show database status and health information."""
    print_header("Database Status")

    try:
        # Import from python_server.server module with proper path
        from python_server.server.database import DatabaseManager
        from python_server.server.database_migrations import DatabaseMigrationManager

        # Initialize managers
        db = DatabaseManager(args.database, use_pool=True)
        migration_manager = DatabaseMigrationManager(args.database)

        # Basic database info
        if os.path.exists(args.database):
            size_mb = round(os.path.getsize(args.database) / (1024 * 1024), 2)
            print_status(
                f"Database file: {os.path.abspath(args.database)} ({size_mb} MB)"
            )
        else:
            print_status("Database file does not exist", "WARNING")
            return

        # Migration status
        migration_status = migration_manager.get_migration_status()
        print_status(
            f"Schema version: {migration_status['current_version']}/{migration_status['latest_version']}"
        )
        if migration_status["pending_migrations"] > 0:
            print_status(
                f"Pending migrations: {migration_status['pending_migrations']}",
                "WARNING",
            )
        else:
            print_status("All migrations applied")

        # Health check
        health = db.get_database_health()
        print_status(
            f"Database integrity: {'OK' if health['integrity_check'] else 'FAILED'}"
        )
        print_status(
            f"Foreign key constraints: {'OK' if health['foreign_key_check'] else 'FAILED'}"
        )
        print_status(
            f"Connection pool: {'Healthy' if health['connection_pool_healthy'] else 'Issues'}"
        )
        print_status(
            f"Tables: {health['table_count']}, Indexes: {health['index_count']}"
        )

        if health["issues"]:
            print_status("Issues detected:", "WARNING")
            for issue in health["issues"]:
                print_status(f"  - {issue}", "WARNING")

        # Storage statistics
        stats = db.get_storage_statistics()
        db_info = stats["database_info"]
        storage_info = stats.get("storage_info", {})
        client_stats = stats.get("client_stats", {})
        file_stats = stats.get("file_stats", {})

        print_status(
            f"Connection pooling: {'Enabled' if db_info['connection_pool_enabled'] else 'Disabled'}"
        )
        if storage_info:
            print_status(
                f"Storage directory: {storage_info.get('total_files', 0)} files, {storage_info.get('total_size_mb', 0)} MB"
            )
        if client_stats:
            print_status(f"Registered clients: {client_stats.get('total_clients', 0)}")
        if file_stats:
            print_status(
                f"Total files: {file_stats.get('total_files', 0)} ({file_stats.get('verification_rate', 0)}% verified)"
            )
            print_status(f"Total storage: {file_stats.get('total_size_gb', 0)} GB")

    except Exception as e:
        print_status(f"Error checking database status: {e}", "ERROR")
        return 1

    return 0


def cmd_migrate(args: argparse.Namespace) -> int | None:
    """Apply database migrations."""
    print_header("Database Migration")

    try:
        from python_server.server.database_migrations import DatabaseMigrationManager

        manager = DatabaseMigrationManager(args.database)

        # Check current status
        status = manager.get_migration_status()
        print_status(f"Current version: {status['current_version']}")
        print_status(f"Latest version: {status['latest_version']}")

        pending = manager.get_pending_migrations()
        if not pending:
            print_status("No pending migrations")
            return 0

        print_status(f"Found {len(pending)} pending migrations:")
        for migration in pending:
            print_status(f"  - Version {migration.version}: {migration.description}")

        # Confirm migration
        if not args.force:
            response = input(f"\nApply {len(pending)} migrations? [y/N]: ")
            if response.lower() != "y":
                print_status("Migration cancelled")
                return 0

        # Create backup
        print_status("Creating database backup...")
        backup_path = manager.backup_database()
        print_status(f"Backup created: {backup_path}")

        # Apply migrations
        print_status("Applying migrations...")
        success = manager.migrate_to_latest()

        if success:
            print_status("All migrations applied successfully!", "SUCCESS")

            # Validate database
            if manager.validate_database_integrity():
                print_status("Database integrity verified", "SUCCESS")
            else:
                print_status("Database integrity check failed", "ERROR")
                return 1

        else:
            print_status("Some migrations failed", "ERROR")
            print_status(f"Database backup available: {backup_path}", "INFO")
            return 1

    except Exception as e:
        print_status(f"Migration error: {e}", "ERROR")
        return 1

    return 0


def cmd_optimize(args: argparse.Namespace) -> int | None:
    """Optimize database performance."""
    print_header("Database Optimization")

    try:
        from python_server.server.database import DatabaseManager

        db = DatabaseManager(args.database, use_pool=True)

        print_status("Starting database optimization...")
        results = db.optimize_database()

        if results["vacuum_performed"]:
            print_status("VACUUM completed - reclaimed unused space")
        else:
            print_status("VACUUM failed", "WARNING")

        if results["analyze_performed"]:
            print_status("ANALYZE completed - updated query statistics")
        else:
            print_status("ANALYZE failed", "WARNING")

        if results["space_saved_mb"] > 0:
            print_status(f"Space saved: {results['space_saved_mb']} MB", "SUCCESS")
        else:
            print_status("No space reclaimed")

        print_status(
            f"Database size: {results['size_before_mb']} MB → {results['size_after_mb']} MB"
        )

        if results["errors"]:
            print_status("Optimization errors:", "WARNING")
            for error in results["errors"]:
                print_status(f"  - {error}", "WARNING")

    except Exception as e:
        print_status(f"Optimization error: {e}", "ERROR")
        return 1

    return 0


def cmd_backup(args: argparse.Namespace) -> int | None:
    """Create database backup."""
    print_header("Database Backup")

    try:
        from python_server.server.database import DatabaseManager

        db = DatabaseManager(args.database, use_pool=True)

        backup_path = db.backup_database_to_file(args.output)
        print_status(f"Backup created: {backup_path}", "SUCCESS")

        # Verify backup
        if os.path.exists(backup_path):
            backup_size = round(os.path.getsize(backup_path) / (1024 * 1024), 2)
            print_status(f"Backup size: {backup_size} MB")

    except Exception as e:
        print_status(f"Backup error: {e}", "ERROR")
        return 1

    return 0


def cmd_search(args: argparse.Namespace) -> int | None:
    """Search files with advanced filters."""
    print_header("Advanced File Search")

    try:
        from python_server.server.database import DatabaseManager

        db = DatabaseManager(args.database, use_pool=True)

        # Build search parameters
        search_params = {}
        if args.term:
            search_params["search_term"] = args.term
        if args.client:
            search_params["client_name"] = args.client
        if args.type:
            search_params["file_type"] = args.type
        if args.verified:
            search_params["verified_only"] = True
        if args.min_size:
            search_params["min_size"] = args.min_size
        if args.max_size:
            search_params["max_size"] = args.max_size

        print_status(f"Searching with filters: {search_params}")

        results = db.search_files_advanced(**search_params)

        print_status(f"Found {len(results)} files")

        if results and not args.quiet:
            print("\nResults:")
            print("-" * 80)
            for i, result in enumerate(results[: args.limit], 1):
                size_mb = round((result.get("size", 0) or 0) / (1024 * 1024), 2)
                verified = "YES" if result.get("verified") else "NO"
                print(f"{i:3d}. {result['filename']}")
                print(
                    f"     Client: {result['client']} | Size: {size_mb} MB | Verified: {verified}"
                )
                print(f"     Path: {result['path']}")
                print(f"     Date: {result.get('date', 'Unknown')}")
                if result.get("category"):
                    print(f"     Category: {result['category']}")
                print()

    except Exception as e:
        print_status(f"Search error: {e}", "ERROR")
        return 1

    return 0


def cmd_stats(args: argparse.Namespace) -> int | None:
    """Show detailed database statistics."""
    print_header("Database Statistics")

    try:
        from python_server.server.database import DatabaseManager

        db = DatabaseManager(args.database, use_pool=True)
        stats = db.get_storage_statistics()

        # Database information
        db_info = stats["database_info"]
        print_status("Database Information:")
        print(f"  File: {db_info['file_path']}")
        print(f"  Size: {db_info['file_size_mb']} MB")
        print(
            f"  Connection Pool: {'Enabled' if db_info['connection_pool_enabled'] else 'Disabled'}"
        )
        print(f"  Pool Size: {db_info['pool_size']}")

        # Storage information
        if "storage_info" in stats:
            storage_info = stats["storage_info"]
            print_status("Storage Information:")
            print(f"  Directory: {storage_info['directory']}")
            print(f"  Files: {storage_info['total_files']}")
            print(f"  Total Size: {storage_info['total_size_mb']} MB")

        # Client statistics
        if "client_stats" in stats:
            client_stats = stats["client_stats"]
            print_status("Client Statistics:")
            print(f"  Total Clients: {client_stats['total_clients']}")
            print(f"  Clients with Keys: {client_stats['clients_with_keys']}")
            print(f"  Avg Days Since Seen: {client_stats['average_days_since_seen']}")

        # File statistics
        if "file_stats" in stats:
            file_stats = stats["file_stats"]
            print_status("File Statistics:")
            print(f"  Total Files: {file_stats['total_files']}")
            print(f"  Verified Files: {file_stats['verified_files']}")
            print(f"  Verification Rate: {file_stats['verification_rate']}%")
            print(f"  Average File Size: {file_stats['average_file_size_mb']} MB")
            print(f"  Total Storage: {file_stats['total_size_gb']} GB")
            print(
                f"  Size Range: {file_stats['min_file_size_kb']} KB - {file_stats['max_file_size_mb']} MB"
            )

        # Performance information
        if "performance_info" in stats:
            perf_info = stats["performance_info"]
            print_status("Performance Information:")
            print(f"  Indexes: {perf_info['indexes_count']}")
            if perf_info["indexes"] and not args.quiet:
                print("  Index List:")
                for idx in perf_info["indexes"]:
                    print(f"    - {idx}")

        if args.json:
            print("\nFull Statistics (JSON):")
            print(json.dumps(stats, indent=2))

    except Exception as e:
        print_status(f"Statistics error: {e}", "ERROR")
        return 1

    return 0


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Database Management Utility for Encrypted Backup Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    # Show database status
  %(prog)s migrate                   # Apply pending migrations
  %(prog)s optimize                  # Optimize database performance
  %(prog)s backup                    # Create database backup
  %(prog)s search --term backup      # Search for files containing 'backup'
  %(prog)s stats --json             # Show detailed statistics in JSON format
        """,
    )

    parser.add_argument(
        "--database",
        "-d",
        default="defensive.db",
        help="Database file path (default: defensive.db)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show database status and health")

    # Migration command
    migrate_parser = subparsers.add_parser("migrate", help="Apply database migrations")
    migrate_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Apply migrations without confirmation",
    )

    # Optimization command
    subparsers.add_parser("optimize", help="Optimize database performance")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument(
        "--output", "-o", help="Backup file path (default: auto-generated)"
    )

    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search files with advanced filters"
    )
    search_parser.add_argument("--term", help="Search term for filename/path")
    search_parser.add_argument("--client", help="Client name filter")
    search_parser.add_argument("--type", help="File extension filter")
    search_parser.add_argument(
        "--verified", action="store_true", help="Only verified files"
    )
    search_parser.add_argument(
        "--min-size", type=int, help="Minimum file size in bytes"
    )
    search_parser.add_argument(
        "--max-size", type=int, help="Maximum file size in bytes"
    )
    search_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum results to show"
    )
    search_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only show count"
    )

    # Statistics command
    stats_parser = subparsers.add_parser(
        "stats", help="Show detailed database statistics"
    )
    stats_parser.add_argument(
        "--json", action="store_true", help="Output full statistics in JSON"
    )
    stats_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Command dispatch
    commands = {
        "status": cmd_status,
        "migrate": cmd_migrate,
        "optimize": cmd_optimize,
        "backup": cmd_backup,
        "search": cmd_search,
        "stats": cmd_stats,
    }

    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print_status("Operation cancelled", "WARNING")
        return 1
    except Exception as e:
        print_status(f"Unexpected error: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
