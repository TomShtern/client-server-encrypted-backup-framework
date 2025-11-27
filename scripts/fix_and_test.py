#!/usr/bin/env python3
"""
Fix and Test Script - Addresses the real issues found by investigation
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Fix Unicode encoding issues for Windows
if os.name == "nt":
    import contextlib

    # Set console to UTF-8
    with contextlib.suppress(Exception):
        os.system("chcp 65001 >nul 2>&1")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

# Change to project root
project_root = Path(__file__).parent.parent
os.chdir(project_root)
print(f"Working directory: {project_root}")


def check_port(port: int) -> bool:
    """Check if a port is listening"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def test_imports():
    """Test critical imports"""
    print("\n=== TESTING IMPORTS ===")

    tests = [
        ("Unified Config", "from Shared.config.unified_config import get_config"),
        (
            "GUI Integration",
            "from python_server.server.gui_integration import GUIManager",
        ),
        ("API Server", "from api_server.cyberbackup_api_server import app"),
        (
            "Real Backup Executor",
            "from api_server.real_backup_executor import RealBackupExecutor",
        ),
    ]

    for name, import_code in tests:
        try:
            exec(import_code)
            print(f"✅ {name}: SUCCESS")
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")


def check_files():
    """Check critical files exist"""
    print("\n=== CHECKING CRITICAL FILES ===")

    files = [
        "transfer.info",
        "python_server/server/server.py",
        "api_server/cyberbackup_api_server.py",
        "requirements.txt",
        "scripts/one_click_build_and_run.py",
    ]

    for file_path in files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}: EXISTS")
        else:
            print(f"❌ {file_path}: MISSING")


def install_dependencies():
    """Install missing dependencies"""
    print("\n=== INSTALLING DEPENDENCIES ===")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
        else:
            print(f"⚠️ Some dependencies had issues: {result.stderr}")

    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")


def test_server_startup():
    """Test server startup without full launch"""
    print("\n=== TESTING SERVER STARTUP ===")

    # Set PYTHONPATH to ensure imports work
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    env["CYBERBACKUP_TEST_MODE"] = "1"  # Signal test mode

    # Test backup server import and basic initialization
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, '.'); from python_server.server.server import main; print('Backup server imports OK')",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            env=env,
            cwd=project_root,
        )

        if result.returncode == 0:
            print("✅ Backup server imports: SUCCESS")
        else:
            print(f"❌ Backup server imports: FAILED - {result.stderr}")

    except Exception as e:
        print(f"❌ Backup server test: EXCEPTION - {e}")

    # Test API server import
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, '.'); from api_server.cyberbackup_api_server import app; print('API server imports OK')",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            env=env,
            cwd=project_root,
        )

        if result.returncode == 0:
            print("✅ API server imports: SUCCESS")
        else:
            print(f"❌ API server imports: FAILED - {result.stderr}")

    except Exception as e:
        print(f"❌ API server test: EXCEPTION - {e}")


def check_configuration():
    """Check configuration is working"""
    print("\n=== CHECKING CONFIGURATION ===")

    try:
        # Test the config system that was causing issues
        sys.path.insert(0, str(project_root))
        from Shared.config.unified_config import get_config

        # Test config loading
        server_port = get_config("server.port", 1256)
        api_port = get_config("api.port", 9090)

        print(f"✅ Server port config: {server_port}")
        print(f"✅ API port config: {api_port}")

        # Check if transfer.info is now found
        if Path("transfer.info").exists():
            print("✅ transfer.info file: EXISTS")
            with open("transfer.info") as f:
                content = f.read().strip()
                lines = content.split("\n")
                if len(lines) == 3:
                    print(
                        f"✅ transfer.info format: VALID ({lines[0]}, {lines[1]}, {lines[2]})"
                    )
                else:
                    print(f"⚠️ transfer.info format: INVALID ({len(lines)} lines)")
        else:
            print("❌ transfer.info file: MISSING")

    except Exception as e:
        print(f"❌ Configuration test: FAILED - {e}")


def run_launcher_test() -> subprocess.Popen | None:
    """Test the canonical launcher with proper environment"""
    print("\n=== TESTING CANONICAL LAUNCHER ===")
    print("Running one-click launcher with proper environment setup...")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    try:
        # Launch the canonical script
        process = subprocess.Popen(
            [sys.executable, "scripts/one_click_build_and_run.py"],
            env=env,
            cwd=project_root,
        )

        print(f"✅ Launcher started with PID: {process.pid}")
        print("Waiting 15 seconds for services to start...")

        # Wait and check if services start
        for i in range(15):
            backup_running = check_port(1256)
            api_running = check_port(9090)

            if backup_running and api_running:
                print(f"✅ Both services running after {i + 1} seconds!")
                break
            elif backup_running:
                print(f"⚠️ Only backup server running after {i + 1} seconds")
            elif api_running:
                print(f"⚠️ Only API server running after {i + 1} seconds")

            time.sleep(1)

        # Final status
        backup_final = check_port(1256)
        api_final = check_port(9090)

        print("\nFinal Status:")
        print(
            f"  Backup Server (1256): {'✅ RUNNING' if backup_final else '❌ NOT RUNNING'}"
        )
        print(f"  API Server (9090): {'✅ RUNNING' if api_final else '❌ NOT RUNNING'}")

        if backup_final and api_final:
            print("🎉 SUCCESS! System is fully operational")
            print("You can now use the web interface at http://127.0.0.1:9090/")
        else:
            print("⚠️ System partially working - check console windows for errors")

        return process

    except Exception as e:
        print(f"❌ Launcher test failed: {e}")
        return None


def main():
    print("=" * 70)
    print("   FIX AND TEST - CyberBackup System Diagnostics")
    print("=" * 70)

    # Run all diagnostics
    test_imports()
    check_files()
    install_dependencies()
    check_configuration()
    test_server_startup()

    print("\n" + "=" * 70)
    print("   DIAGNOSIS COMPLETE - LAUNCHING SYSTEM")
    print("=" * 70)

    # Try to run the actual launcher
    launcher_process = run_launcher_test()

    if launcher_process:
        print("\n📋 NEXT STEPS:")
        print("1. Check the console windows that opened")
        print("2. Try uploading a file at http://127.0.0.1:9090/")
        print("3. If issues persist, check the error messages in console windows")
        print("4. Press Ctrl+C here to stop this diagnostic script")

        try:
            # Keep diagnostic running
            while True:
                time.sleep(10)
                backup_running = check_port(1256)
                api_running = check_port(9090)
                status = f"Backup: {'✅' if backup_running else '❌'} | API: {'✅' if api_running else '❌'}"
                print(f"[Health Check] {status}")

        except KeyboardInterrupt:
            print(
                "\n🛑 Diagnostic script stopped. Services may still be running in console windows."
            )


if __name__ == "__main__":
    main()
