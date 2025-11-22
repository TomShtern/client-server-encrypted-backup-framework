#!/usr/bin/env python3
"""
Database Validation Script for CyberBackup 3.0

This script validates the unified database configuration and verifies that
all components can successfully access the canonical database.

Author: Claude Code
Date: 2025-11-07
Version: 1.0
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_unified_database():
    """
    Validate the unified database configuration and access.

    Returns:
        dict: Validation results
    """
    results = {
        'timestamp': datetime.now(),
        'status': 'unknown',
        'checks': {},
        'errors': [],
        'warnings': []
    }

    try:
        # Import unified config
        from config.database_config import DatabaseConfig, validate_database_environment

        logger.info("Validating unified database configuration...")

        # Get configuration
        config = DatabaseConfig()
        validation = validate_database_environment()

        results['checks']['config_import'] = {
            'status': 'success',
            'message': 'Successfully imported unified database configuration'
        }

        results['checks']['environment_detection'] = {
            'status': 'success',
            'environment': config.environment,
            'message': f'Detected environment: {config.environment}'
        }

        results['checks']['database_access'] = {
            'status': validation['status'],
            'path': validation['path'],
            'exists': validation['exists'],
            'readable': validation['readable'],
            'writable': validation['writable'],
            'size': validation['size']
        }

        if validation['status'] == 'valid':
            logger.info(f"✓ Database accessible: {validation['path']}")
            logger.info(f"  Size: {validation['size']} bytes")
            logger.info(f"  Readable: {validation['readable']}")
            logger.info(f"  Writable: {validation['writable']}")
        else:
            logger.warning(f"⚠ Database access issue: {validation['status']}")
            if validation.get('error'):
                results['warnings'].append(f"Database access error: {validation['error']}")

        # Test database operations
        if validation['exists'] and validation['readable']:
            test_results = test_database_operations(validation['path'])
            results['checks']['database_operations'] = test_results

            if test_results['status'] == 'success':
                logger.info("✓ Database operations test passed")
                logger.info(f"  Clients table: {test_results['clients_count']} records")
                logger.info(f"  Files table: {test_results['files_count']} records")
                logger.info(f"  Tables found: {test_results['tables']}")
            else:
                logger.error(f"✗ Database operations test failed: {test_results['error']}")
                results['errors'].append(f"Database operations failed: {test_results['error']}")

        # Validate component configurations
        component_results = validate_component_configurations()
        results['checks']['component_configurations'] = component_results

        # Check for remaining legacy databases
        legacy_check = check_remaining_legacy_databases(config)
        results['checks']['legacy_cleanup'] = legacy_check

        # Determine overall status
        if results['errors']:
            results['status'] = 'error'
        elif results['warnings']:
            results['status'] = 'warning'
        else:
            results['status'] = 'success'

    except ImportError as e:
        logger.error(f"Failed to import unified configuration: {e}")
        results['checks']['config_import'] = {
            'status': 'error',
            'error': str(e)
        }
        results['status'] = 'error'
        results['errors'].append(f"Configuration import failed: {e}")

    except Exception as e:
        logger.exception("Validation failed with unexpected error")
        results['status'] = 'error'
        results['errors'].append(f"Unexpected error: {e}")

    return results


def test_database_operations(db_path: str) -> dict:
    """
    Test basic database operations.

    Args:
        db_path: Path to database file

    Returns:
        dict: Test results
    """
    result = {
        'status': 'unknown',
        'error': None,
        'clients_count': 0,
        'files_count': 0,
        'tables': []
    }

    try:
        with sqlite3.connect(db_path, timeout=10.0) as conn:
            cursor = conn.cursor()

            # Get table list
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

            # Test database integrity
            cursor.execute("PRAGMA integrity_check;")
            integrity = cursor.fetchone()[0]
            if integrity == "ok":
                result['status'] = 'success'
            else:
                result['status'] = 'error'
                result['error'] = f"Integrity check failed: {integrity}"

    except sqlite3.Error as e:
        result['status'] = 'error'
        result['error'] = f"SQLite error: {e}"
    except Exception as e:
        result['status'] = 'error'
        result['error'] = f"Unexpected error: {e}"

    return result


def validate_component_configurations() -> dict:
    """
    Validate that components can access the unified database configuration.

    Returns:
        dict: Component validation results
    """
    results = {
        'status': 'unknown',
        'components': {},
        'issues': []
    }

    # Test server configuration
    try:
        # Add project root to path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from python_server.server.config import get_database_path as server_get_db_path
        server_db_path = server_get_db_path()

        results['components']['python_server'] = {
            'status': 'success',
            'database_path': server_db_path,
            'message': 'Server configuration accessible'
        }

    except ImportError as e:
        results['components']['python_server'] = {
            'status': 'error',
            'error': str(e)
        }
        results['issues'].append(f"Server config import failed: {e}")
    except Exception as e:
        results['components']['python_server'] = {
            'status': 'error',
            'error': str(e)
        }
        results['issues'].append(f"Server config error: {e}")

    # Test FletV2 configuration (simulated)
    try:
        # Simulate FletV2 main.py import
        fletv2_db_path = None
        try:
            from config.database_config import get_database_path
            fletv2_db_path = get_database_path()
            results['components']['fletv2'] = {
                'status': 'success',
                'database_path': fletv2_db_path,
                'message': 'FletV2 configuration accessible'
            }
        except ImportError:
            # Fallback to legacy path
            fletv2_db_path = os.path.join(project_root, "defensive.db")
            results['components']['fletv2'] = {
                'status': 'fallback',
                'database_path': fletv2_db_path,
                'message': 'Using fallback configuration'
            }
            results['issues'].append("FletV2 using fallback configuration")

    except Exception as e:
        results['components']['fletv2'] = {
            'status': 'error',
            'error': str(e)
        }
        results['issues'].append(f"FletV2 config error: {e}")

    # Determine overall status
    if results['issues']:
        results['status'] = 'warning' if len(results['issues']) == 1 else 'error'
    else:
        results['status'] = 'success'

    return results


def check_remaining_legacy_databases(config) -> dict:
    """
    Check for remaining legacy database files.

    Args:
        config: DatabaseConfig instance

    Returns:
        dict: Legacy cleanup status
    """
    legacy_paths = config.get_legacy_database_paths()
    canonical_path = config.get_canonical_database_path()

    remaining = []
    for path in legacy_paths:
        if path != canonical_path and os.path.exists(path):
            size = os.path.getsize(path)
            remaining.append({
                'path': path,
                'size': size,
                'empty': size == 0
            })

    result = {
        'legacy_paths_found': len(legacy_paths),
        'remaining_databases': len(remaining),
        'remaining_files': remaining,
        'cleanup_needed': len(remaining) > 0
    }

    if remaining:
        non_empty = [f for f in remaining if not f['empty']]
        if non_empty:
            logger.warning(f"Found {len(non_empty)} non-empty legacy database files")
            for file_info in non_empty:
                logger.warning(f"  {file_info['path']} ({file_info['size']} bytes)")
        else:
            logger.info(f"Found {len(remaining)} empty legacy database files (can be safely removed)")
    else:
        logger.info("✓ No remaining legacy database files found")

    return result


def print_validation_results(results: dict) -> None:
    """Print validation results in a readable format."""
    print("\n" + "=" * 60)
    print("DATABASE VALIDATION RESULTS")
    print("=" * 60)
    print(f"Timestamp: {results['timestamp']}")
    print(f"Overall Status: {results['status'].upper()}")
    print()

    # Print check results
    for check_name, check_result in results['checks'].items():
        status_icon = "✓" if check_result.get('status') == 'success' else "⚠" if check_result.get('status') == 'warning' else "✗"
        print(f"{status_icon} {check_name.replace('_', ' ').title()}: {check_result.get('status', 'unknown')}")

        if check_result.get('error'):
            print(f"   Error: {check_result['error']}")
        elif check_result.get('message'):
            print(f"   {check_result['message']}")

        # Special handling for detailed results
        if check_name == 'database_access':
            details = check_result
            print(f"   Path: {details['path']}")
            print(f"   Size: {details['size']} bytes")
            print(f"   Readable: {details['readable']}")
            print(f"   Writable: {details['writable']}")

        elif check_name == 'database_operations':
            if check_result.get('status') == 'success':
                print(f"   Tables: {', '.join(check_result['tables'])}")
                print(f"   Clients: {check_result['clients_count']} records")
                print(f"   Files: {check_result['files_count']} records")

        elif check_name == 'component_configurations':
            for component, comp_result in check_result.get('components', {}).items():
                comp_status = comp_result.get('status', 'unknown')
                comp_icon = "✓" if comp_status == 'success' else "⚠" if comp_status == 'fallback' else "✗"
                print(f"   {comp_icon} {component}: {comp_status}")
                if comp_result.get('database_path'):
                    print(f"      Database: {comp_result['database_path']}")

        elif check_name == 'legacy_cleanup':
            if check_result.get('cleanup_needed'):
                print(f"   {check_result['remaining_databases']} legacy files remain")
                for file_info in check_result.get('remaining_files', []):
                    status = "empty" if file_info['empty'] else f"{file_info['size']} bytes"
                    print(f"     {file_info['path']} ({status})")
            else:
                print("   ✓ No legacy files remaining")

        print()

    # Print errors and warnings
    if results['errors']:
        print("ERRORS:")
        for error in results['errors']:
            print(f"  ✗ {error}")
        print()

    if results['warnings']:
        print("WARNINGS:")
        for warning in results['warnings']:
            print(f"  ⚠ {warning}")
        print()


def main():
    """Main validation function."""
    print("CyberBackup Database Validation Tool")
    print("=" * 50)

    # Run validation
    results = validate_unified_database()

    # Print results
    print_validation_results(results)

    # Return appropriate exit code
    if results['status'] == 'success':
        print("✓ Database validation completed successfully!")
        return 0
    elif results['status'] == 'warning':
        print("⚠ Database validation completed with warnings")
        return 1
    else:
        print("✗ Database validation failed!")
        return 2


if __name__ == '__main__':
    sys.exit(main())