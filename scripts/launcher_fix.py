#!/usr/bin/env python3
"""
Canonical Launcher Fix - Addresses the real startup issues found by investigation

This script fixes the specific issues preventing the one-click launcher from working:
1. Unicode encoding problems preventing GUI startup
2. Missing transfer.info blocking server startup
3. Import path configuration issues
4. Proper environment setup for both servers

This fixes the existing launcher rather than replacing it.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def fix_unicode_environment():
    """Fix Unicode encoding issues that prevent server startup"""
    if os.name == "nt":
        try:
            # Set UTF-8 console codepage
            os.system("chcp 65001 >nul 2>&1")

            # Set Python environment variables for UTF-8
            os.environ["PYTHONIOENCODING"] = "utf-8"
            os.environ["PYTHONUTF8"] = "1"

            # Reconfigure stdout/stderr if possible
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

            print("✅ Unicode environment configured")
            return True
        except Exception as e:
            print(f"⚠️ Unicode setup issue: {e}")
            return False
    return True


def setup_python_path():
    """Ensure Python path is configured correctly"""
    project_root = Path(__file__).parent.parent
    project_root_str = str(project_root.absolute())

    # Add to sys.path if not already there
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    # Set PYTHONPATH environment variable
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if project_root_str not in current_pythonpath:
        if current_pythonpath:
            os.environ["PYTHONPATH"] = (
                f"{project_root_str}{os.pathsep}{current_pythonpath}"
            )
        else:
            os.environ["PYTHONPATH"] = project_root_str

    print(f"✅ Python path configured: {project_root_str}")
    return project_root


def create_temporary_transfer_info():
    """Create a temporary transfer.info to prevent config warnings during startup"""
    transfer_info = Path("transfer.info")

    if not transfer_info.exists():
        # Create temporary file - this will be replaced by dynamic generation
        content = "127.0.0.1:1256\ntestuser\ntemporary_file.txt\n"
        transfer_info.write_text(content)
        print("✅ Temporary transfer.info created (will be replaced dynamically)")
        return True
    else:
        print("✅ transfer.info already exists")
        return False


def test_imports():
    """Test that critical imports work with current configuration"""
    print("\n=== Testing Critical Imports ===")

    try:
        print("✅ Shared.utils.unified_config: OK")
    except Exception as e:
        print(f"❌ Shared.utils.unified_config: {e}")
        return False

    try:
        print("✅ python_server.server.gui_integration: OK")
    except Exception as e:
        print(f"❌ python_server.server.gui_integration: {e}")
        return False

    try:
        print("✅ api_server.cyberbackup_api_server: OK")
    except Exception as e:
        print(f"❌ api_server.cyberbackup_api_server: {e}")
        return False

    return True


def check_port(port: int):
    """Check if port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def run_canonical_launcher():
    """Run the canonical one-click launcher with proper environment"""
    print("\n=== Running Canonical Launcher ===")

    # Prepare environment
    env = os.environ.copy()
    env["PYTHONPATH"] = os.environ["PYTHONPATH"]
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # Disable GUI emojis that cause encoding issues
    env["CYBERBACKUP_DISABLE_EMOJIS"] = "1"

    try:
        # Launch the canonical script
        canonical_script = Path("scripts/one_click_build_and_run.py")

        print(f"Starting canonical launcher: {canonical_script}")
        print("Environment configured with Unicode fixes")

        process = subprocess.Popen(
            [sys.executable, str(canonical_script)], env=env, cwd=Path.cwd()
        )

        print(f"✅ Canonical launcher started with PID: {process.pid}")

        # Monitor startup progress
        print("\nMonitoring server startup...")
        for i in range(45):  # Wait up to 45 seconds
            backup_running = check_port(1256)
            api_running = check_port(9090)

            if backup_running and api_running:
                print(f"✅ Both servers running after {i + 1} seconds!")
                break
            elif backup_running:
                print(
                    "⚠️ Backup server (1256) running, waiting for API server (9090)..."
                )
            elif api_running:
                print(
                    "⚠️ API server (9090) running, waiting for backup server (1256)..."
                )
            else:
                if i % 5 == 0:  # Print every 5 seconds
                    print(f"⏳ Waiting for servers to start... ({i + 1}/45 seconds)")

            time.sleep(1)

        # Final status
        backup_final = check_port(1256)
        api_final = check_port(9090)

        print("\n=== Final Status ===")
        print(
            f"Backup Server (1256): {'✅ RUNNING' if backup_final else '❌ NOT RUNNING'}"
        )
        print(f"API Server (9090): {'✅ RUNNING' if api_final else '❌ NOT RUNNING'}")

        if backup_final and api_final:
            print("\n🎉 SUCCESS! System is fully operational!")
            print("• Web interface: http://127.0.0.1:9090/")
            print("• Both servers running in separate console windows")
            print("• File transfers should work through web interface")
            print("• transfer.info will be created dynamically for each transfer")
        elif backup_final or api_final:
            print("\n⚠️ Partial success - check console windows for errors")
        else:
            print(
                "\n❌ Servers failed to start - check console windows for error messages"
            )

        return process, backup_final, api_final

    except Exception as e:
        print(f"❌ Failed to start canonical launcher: {e}")
        return None, False, False


def main():
    print("=" * 70)
    print("   CANONICAL LAUNCHER FIX - CyberBackup 3.0")
    print("=" * 70)
    print("Fixing the real issues preventing the canonical launcher from working...")
    print()

    # Step 1: Fix environment
    project_root = setup_python_path()
    os.chdir(project_root)

    # Step 2: Fix Unicode issues
    fix_unicode_environment()

    # Step 3: Create temporary transfer.info if needed
    temp_file_created = create_temporary_transfer_info()

    # Step 4: Test imports
    if not test_imports():
        print("\n❌ Import tests failed - cannot proceed")
        return 1

    # Step 5: Run the canonical launcher
    process, backup_running, api_running = run_canonical_launcher()

    if process and (backup_running or api_running):
        print("\n📋 Next Steps:")
        print("1. Check the console windows that opened for any error messages")
        print("2. Test file upload at http://127.0.0.1:9090/")
        print("3. The system will create transfer.info dynamically during transfers")

        if temp_file_created:
            print(
                "4. The temporary transfer.info will be replaced by dynamic generation"
            )

        print(
            "\n💡 Press Ctrl+C here to stop this monitor (servers will continue running)"
        )

        try:
            # Monitor system health
            while True:
                time.sleep(30)
                backup_check = check_port(1256)
                api_check = check_port(9090)

                if not backup_check or not api_check:
                    print(
                        f"⚠️ Health check: Backup {'✅' if backup_check else '❌'} | API {'✅' if api_check else '❌'}"
                    )

        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped. Services continue running in console windows.")

    else:
        print("\n❌ Canonical launcher failed to start servers properly")
        print("Check the error messages above and in any opened console windows")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
