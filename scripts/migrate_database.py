#!/usr/bin/env python3
"""
Database Migration Script for CyberBackup 3.0

This script consolidates multiple database files into a single canonical database
located at data/database/defensive.db. It analyzes all legacy database files,
identifies the one with the most recent and complete data, and migrates it
to the canonical location.

Author: Claude Code
Date: 2025-11-07
Version: 1.0
"""

import os
import sys
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    from config.database_config import DatabaseConfig
except ImportError as e:
    print(f"Error importing database config: {e}")
    print("Make sure you're running this from the project root or config module is available.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigration:
    """
    Handles migration of multiple database files to a unified location.
    """

    def __init__(self, dry_run: bool = False):
        """
        Initialize migration process.

        Args:
            dry_run: If True, only analyze without making changes
        """
        self.dry_run = dry_run
        self.config = DatabaseConfig()
        self.legacy_paths = self.config.get_legacy_database_paths()
        self.canonical_path = self.config.get_canonical_database_path()

        # Migration results
        self.analysis_results = {}
        self.migration_plan = {}

    def analyze_database_file(self, db_path: str) -> Dict[str, Any]:
        """
        Analyze a database file to determine its contents and validity.

        Args:
            db_path: Path to database file

        Returns:
            dict: Analysis results
        """
        db_file = Path(db_path)
        result = {
            'path': db_path,
            'exists': False,
            'readable': False,
            'size': 0,
            'modified_time': None,
            'clients_count': 0,
            'files_count': 0,
            'tables': [],
            'error': None,
            'valid': False,
            'score': 0
        }

        try:
            # Check if file exists
            if not db_file.exists():
                result['error'] = "File does not exist"
                return result

            result['exists'] = True
            result['size'] = db_file.stat().st_size
            result['modified_time'] = datetime.fromtimestamp(db_file.stat().st_mtime)

            # Skip empty files
            if result['size'] == 0:
                result['error'] = "Empty file"
                return result

            # Try to open and analyze database
            try:
                with sqlite3.connect(str(db_file), timeout=10.0) as conn:
                    cursor = conn.cursor()

                    # Check if database is readable
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall()]
                    result['tables'] = tables

                    # Count records in key tables
                    if 'clients' in tables:
                        cursor.execute("SELECT COUNT(*) FROM clients")
                        result['clients_count'] = cursor.fetchone()[0]

                    if 'files' in tables:
                        cursor.execute("SELECT COUNT(*) FROM files")
                        result['files_count'] = cursor.fetchone()[0]

                    # Validate database integrity
                    cursor.execute("PRAGMA integrity_check;")
                    integrity_result = cursor.fetchone()[0]
                    if integrity_result == "ok":
                        result['readable'] = True
                        result['valid'] = True
                    else:
                        result['error'] = f"Database integrity check failed: {integrity_result}"

            except sqlite3.Error as e:
                result['error'] = f"SQLite error: {e}"
                return result

            # Calculate score for ranking databases
            score = 0
            if result['valid']:
                score += 100  # Base score for valid database
                score += result['clients_count'] * 2  # 2 points per client
                score += result['files_count'] * 1  # 1 point per file
                score += result['size'] / 1024  # 1 point per KB

            result['score'] = int(score)

        except Exception as e:
            result['error'] = f"Analysis error: {e}"
            logger.exception(f"Error analyzing database {db_path}")

        return result

    def analyze_all_databases(self) -> Dict[str, Any]:
        """
        Analyze all database files (legacy and canonical).

        Returns:
            dict: Complete analysis results
        """
        logger.info("Analyzing all database files...")

        all_paths = self.legacy_paths + [self.canonical_path]
        results = {}

        for db_path in all_paths:
            logger.info(f"Analyzing: {db_path}")
            result = self.analyze_database_file(db_path)
            results[db_path] = result

            # Log results
            if result['valid']:
                logger.info(f"  ✓ Valid: {result['clients_count']} clients, {result['files_count']} files, {result['size']} bytes, score: {result['score']}")
            else:
                logger.warning(f"  ✗ Invalid: {result['error']}")

        self.analysis_results = results
        return results

    def select_best_database(self) -> Optional[str]:
        """
        Select the best database file to use as the source.

        Returns:
            str or None: Path to the best database file, or None if no valid database found
        """
        valid_databases = []

        for db_path, result in self.analysis_results.items():
            if result['valid'] and result['clients_count'] > 0:
                valid_databases.append((db_path, result))

        if not valid_databases:
            logger.error("No valid databases with data found!")
            return None

        # Sort by score (highest first)
        valid_databases.sort(key=lambda x: x[1]['score'], reverse=True)

        # Select the best database
        best_db_path, best_result = valid_databases[0]

        logger.info(f"Selected best database: {best_db_path}")
        logger.info(f"  Score: {best_result['score']}")
        logger.info(f"  Clients: {best_result['clients_count']}")
        logger.info(f"  Files: {best_result['files_count']}")
        logger.info(f"  Size: {best_result['size']} bytes")
        logger.info(f"  Modified: {best_result['modified_time']}")

        return best_db_path

    def create_migration_plan(self) -> Dict[str, Any]:
        """
        Create a migration plan based on analysis results.

        Returns:
            dict: Migration plan
        """
        logger.info("Creating migration plan...")

        best_db_path = self.select_best_database()

        if not best_db_path:
            self.migration_plan = {
                'status': 'error',
                'message': 'No valid database found for migration',
                'actions': []
            }
            return self.migration_plan

        # Plan actions
        actions = []

        # 1. Backup canonical database if it exists and is different from best
        canonical_result = self.analysis_results.get(self.canonical_path, {})
        if canonical_result.get('exists') and best_db_path != self.canonical_path:
            backup_path = self._create_backup_path()
            actions.append({
                'action': 'backup_existing',
                'source': self.canonical_path,
                'destination': backup_path,
                'reason': 'Backup existing canonical database before migration'
            })

        # 2. Copy best database to canonical location
        if best_db_path != self.canonical_path:
            actions.append({
                'action': 'copy_best_database',
                'source': best_db_path,
                'destination': self.canonical_path,
                'reason': f'Copy best database ({best_db_path}) to canonical location'
            })
        else:
            actions.append({
                'action': 'keep_existing',
                'source': best_db_path,
                'destination': self.canonical_path,
                'reason': 'Best database is already at canonical location'
            })

        # 3. Archive other databases
        archive_dir = self.config.get_database_directory() / 'archive'
        for db_path, result in self.analysis_results.items():
            if (result.get('valid') and
                db_path != best_db_path and
                db_path != self.canonical_path and
                result['clients_count'] > 0):

                archive_path = archive_dir / f"legacy_{Path(db_path).name}"
                actions.append({
                    'action': 'archive_legacy',
                    'source': db_path,
                    'destination': str(archive_path),
                    'reason': f'Archive legacy database with {result["clients_count"]} clients'
                })

        # 4. Remove empty databases
        for db_path, result in self.analysis_results.items():
            if (result.get('exists') and
                result['size'] == 0 and
                db_path != self.canonical_path):

                actions.append({
                    'action': 'remove_empty',
                    'source': db_path,
                    'destination': None,
                    'reason': 'Remove empty database file'
                })

        self.migration_plan = {
            'status': 'ready',
            'best_database': best_db_path,
            'canonical_path': self.canonical_path,
            'actions': actions,
            'summary': {
                'total_databases_found': len([r for r in self.analysis_results.values() if r.get('exists')]),
                'valid_databases_found': len([r for r in self.analysis_results.values() if r.get('valid')]),
                'actions_planned': len(actions)
            }
        }

        return self.migration_plan

    def _create_backup_path(self) -> str:
        """Create a timestamped backup path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config.get_backup_directory()
        backup_path = backup_dir / f"defensive_backup_{timestamp}.db"
        return str(backup_path)

    def execute_migration(self) -> Dict[str, Any]:
        """
        Execute the migration plan.

        Returns:
            dict: Migration execution results
        """
        if not self.migration_plan:
            logger.error("No migration plan available. Run create_migration_plan() first.")
            return {'status': 'error', 'message': 'No migration plan available'}

        if self.migration_plan['status'] != 'ready':
            logger.error(f"Migration plan not ready: {self.migration_plan['status']}")
            return self.migration_plan

        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        execution_results = {
            'status': 'running',
            'actions_executed': [],
            'actions_failed': [],
            'start_time': datetime.now()
        }

        logger.info("Executing migration plan...")
        logger.info(f"Best database: {self.migration_plan['best_database']}")
        logger.info(f"Canonical path: {self.migration_plan['canonical_path']}")

        for i, action in enumerate(self.migration_plan['actions'], 1):
            action_type = action['action']
            source = action['source']
            destination = action['destination']
            reason = action['reason']

            logger.info(f"Action {i}/{len(self.migration_plan['actions'])}: {action_type}")
            logger.info(f"  Reason: {reason}")

            try:
                if self.dry_run:
                    logger.info(f"  [DRY RUN] Would execute: {action_type}")
                    execution_results['actions_executed'].append({
                        **action,
                        'status': 'dry_run_skipped',
                        'timestamp': datetime.now()
                    })
                    continue

                if action_type == 'backup_existing':
                    self._backup_database(source, destination)

                elif action_type == 'copy_best_database':
                    self._copy_database(source, destination)

                elif action_type == 'keep_existing':
                    logger.info(f"  Keeping existing database at: {source}")

                elif action_type == 'archive_legacy':
                    self._archive_database(source, destination)

                elif action_type == 'remove_empty':
                    self._remove_file(source)

                else:
                    raise ValueError(f"Unknown action type: {action_type}")

                execution_results['actions_executed'].append({
                    **action,
                    'status': 'success',
                    'timestamp': datetime.now()
                })
                logger.info("  ✓ Success")

            except Exception as e:
                logger.error(f"  ✗ Failed: {e}")
                execution_results['actions_failed'].append({
                    **action,
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now()
                })

        execution_results['status'] = 'completed' if not execution_results['actions_failed'] else 'partial'
        execution_results['end_time'] = datetime.now()
        execution_results['duration'] = execution_results['end_time'] - execution_results['start_time']

        logger.info(f"Migration completed in {execution_results['duration']}")
        logger.info(f"Actions executed: {len(execution_results['actions_executed'])}")
        logger.info(f"Actions failed: {len(execution_results['actions_failed'])}")

        return execution_results

    def _backup_database(self, source: str, destination: str) -> None:
        """Backup database file."""
        logger.info(f"  Backing up: {source} → {destination}")
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)

    def _copy_database(self, source: str, destination: str) -> None:
        """Copy database file."""
        logger.info(f"  Copying: {source} → {destination}")
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)

    def _archive_database(self, source: str, destination: str) -> None:
        """Archive database file."""
        logger.info(f"  Archiving: {source} → {destination}")
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)
        os.remove(source)  # Remove original after archiving

    def _remove_file(self, file_path: str) -> None:
        """Remove file."""
        logger.info(f"  Removing: {file_path}")
        os.remove(file_path)

    def print_summary(self) -> None:
        """Print a summary of the migration process."""
        print("\n" + "=" * 60)
        print("DATABASE MIGRATION SUMMARY")
        print("=" * 60)

        if not self.analysis_results:
            print("No analysis results available.")
            return

        print(f"Total databases found: {len([r for r in self.analysis_results.values() if r['exists']])}")
        print(f"Valid databases found: {len([r for r in self.analysis_results.values() if r['valid']])}")
        print()

        # Show analysis results
        print("Database Analysis Results:")
        print("-" * 40)
        for db_path, result in sorted(self.analysis_results.items()):
            if result['exists']:
                status = "✓ VALID" if result['valid'] else "✗ INVALID"
                print(f"{status:8} {result['clients_count']:3} clients, {result['files_count']:3} files, {result['size']:8} bytes")
                print(f"         {db_path}")
                if result['error']:
                    print(f"         Error: {result['error']}")
                print()

        # Show migration plan
        if self.migration_plan:
            print("Migration Plan:")
            print("-" * 40)
            print(f"Status: {self.migration_plan['status']}")
            if self.migration_plan['status'] == 'ready':
                print(f"Best database: {self.migration_plan['best_database']}")
                print(f"Canonical path: {self.migration_plan['canonical_path']}")
                print(f"Actions planned: {self.migration_plan['summary']['actions_planned']}")
                print()

                for i, action in enumerate(self.migration_plan['actions'], 1):
                    print(f"{i}. {action['action'].replace('_', ' ').title()}")
                    print(f"   From: {action['source']}")
                    if action['destination']:
                        print(f"   To: {action['destination']}")
                    print(f"   Reason: {action['reason']}")
                    print()


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate CyberBackup databases to unified location')
    parser.add_argument('--dry-run', action='store_true', help='Analyze and plan without making changes')
    parser.add_argument('--auto', action='store_true', help='Automatically execute migration without prompting')
    args = parser.parse_args()

    print("CyberBackup Database Migration Tool")
    print("=" * 50)

    # Initialize migration
    migration = DatabaseMigration(dry_run=args.dry_run)

    # Analyze databases
    print("Step 1: Analyzing database files...")
    migration.analyze_all_databases()

    # Create migration plan
    print("Step 2: Creating migration plan...")
    migration.create_migration_plan()

    # Print summary
    migration.print_summary()

    if migration.migration_plan['status'] != 'ready':
        print(f"Migration plan not ready: {migration.migration_plan['message']}")
        return 1

    if args.dry_run:
        print("\nDRY RUN MODE - No changes made")
        return 0

    # Ask for confirmation unless auto mode
    if not args.auto:
        response = input("\nDo you want to execute this migration plan? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Migration cancelled.")
            return 0

    # Execute migration
    print("Step 3: Executing migration...")
    results = migration.execute_migration()

    if results['status'] == 'completed':
        print("\n✓ Migration completed successfully!")
        return 0
    else:
        print(f"\n⚠ Migration completed with issues: {results['status']}")
        return 1


if __name__ == '__main__':
    sys.exit(main())