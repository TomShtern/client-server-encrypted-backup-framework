#!/usr/bin/env python3
"""One-click build and run orchestrator for CyberBackup 3.0.

This script:
 1. Verifies environment & dependencies
 2. Builds the C++ client (via CMake & vcpkg toolchain)
 3. Launches FletV2 Desktop GUI with integrated BackupServer
 4. Launches API Bridge Server (for C++ client's web GUI)

ARCHITECTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Two Separate GUI Systems:

1. FletV2 Desktop GUI (Server Administration)
   • Direct Python method calls via ServerBridge
   • Integrated BackupServer with network listener (port 1256)
   • Material Design 3 interface for administrators

2. JavaScript Web GUI (End-User Backups)
   • API Server (port 9090) serves HTML/CSS/JS files
   • RealBackupExecutor launches C++ client subprocess
   • C++ client connects to BackupServer for file transfers

Both systems share the same SQLite database (defensive.db)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# IMMEDIATE UTF-8 SETUP - Must be FIRST to prevent Unicode errors
import contextlib
import os
import sys

# Apply UTF-8 console setup before any other imports
if sys.platform == 'win32':
    with contextlib.suppress(Exception):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONUTF8'] = '1'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
import json
import logging
import subprocess
import time
import traceback
import webbrowser
from pathlib import Path
from typing import Any
import shutil

from Shared.config.unified_config import get_config

try:
    import psutil
except ImportError:
    print("[WARNING] psutil not available - process cleanup may be limited")
    psutil = None

def setup_logging():
    """Setup basic logging for the build script"""
    # Determine project root directory (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    logs_dir = project_root / 'logs'

    # Ensure logs directory exists BEFORE creating file handler
    logs_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'build_script.log', mode='a'),
            logging.StreamHandler()  # Also log to console
        ]
    )

def setup_unicode_console():
    """UTF-8 console setup - enforces UTF-8 encoding exclusively"""
    if os.name == 'nt':  # Windows only
        with contextlib.suppress(Exception):
            # Set UTF-8 codepage
            os.system("chcp 65001 >nul 2>&1")
            logging.info("UTF-8 console setup completed - UTF-8 mode enforced")

def safe_print(message: str, fallback: str | None = None):
    """Print with automatic fallback for encoding issues"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Use provided fallback or strip non-ASCII characters
        fallback_msg = fallback or message.encode('ascii', 'ignore').decode()
        print(fallback_msg)

def print_phase(phase_num: int, total_phases: int, title: str):
    """Print phase header with timestamp"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print()
    print(f"[{timestamp}] [PHASE {phase_num}/{total_phases}] {title}...")
    print("-" * 50)

def print_build_failure_help():
    """Print common build failure solutions (extracted duplicate code)"""
    print_error_with_newline("[ERROR] C++ client build failed!")
    print("Check the compiler output above for details.")
    print()
    print("Common solutions:")
    print("1. Missing Boost dependencies:")
    print("   - Run: vcpkg\\vcpkg.exe install boost-iostreams:x64-windows")
    print("   - Or delete 'build' folder and run this script again")
    print("2. Outdated vcpkg cache:")
    print("   - Delete 'vcpkg_installed' folder and rebuild")
    print("3. CMake configuration issues:")
    print("   - Run: cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake")
    print()

def report_executable_status(found_exe, checked_locations):
    """Report the status of C++ executable search with standardized messaging."""
    if found_exe:
        print(f"[OK] C++ client found: {found_exe}")
    else:
        print("[ERROR] EncryptedBackupClient.exe was not created!")
        print("Checked locations:")
        for path in checked_locations:
            print(f"  - {path}")
        print("\nWeb uploads may not work without the C++ client.")
        print("Continuing with server-only mode...")

def print_server_not_found_help(server_path: Path, expected_location: str):
    """Print server file not found error with common guidance"""
    print(f"[ERROR] Server file not found: {server_path}")
    print(f"Expected location: {expected_location}")
    print("Please verify the server components are installed correctly.")

# TkInter GUI helper function removed - deprecated in favor of FletV2

def print_error_with_newline(error_message: str):
    """Print error message with preceding newline (extracted duplicate code)"""
    print()
    print(error_message)

def wait_for_exit():
    """Wait for user input before exit (extracted duplicate code)"""
    with contextlib.suppress(EOFError):
        input("Press Enter to exit...")

def print_success_with_spacing(success_message: str):
    """Print success message with spacing (extracted duplicate code)"""
    print()
    print(success_message)
    print()

def print_build_command_info(description: str, command: str):
    """Print build command information (extracted duplicate code)"""
    print(description)
    print(f"Command: {command}")

def print_spacing():
    """Print empty line for spacing (extracted duplicate code)"""
    print()

def install_additional_dependencies():
    """Install additional Python dependencies (extracted from main)"""
    print("Installing additional dependencies...")
    additional_deps = ["sentry-sdk", "flask-cors", "watchdog"]

    for dep in additional_deps:
        print(f"Installing {dep}...")
        if run_command(f"pip install {dep}", check_exit=False, timeout=60):
            print(f"[OK] {dep} installed successfully")
        else:
            print(f"[WARNING] Failed to install {dep} - continuing anyway")

    print_spacing()


def install_python_dependencies():
    """Install Python dependencies from requirements.txt or fall back to a minimal set."""
    print("Installing Python dependencies from requirements.txt...")
    print_spacing()
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        if not run_command("pip install -r requirements.txt", check_exit=False, timeout=180):
            print("[WARNING] Some Python dependencies failed to install")
            print("This may cause issues with the API server or GUI")
            print()
        else:
            print("[OK] Python dependencies installed successfully!")
    else:
        print("[WARNING] requirements.txt not found")
        print("Installing basic dependencies manually...")
        run_command("pip install cryptography pycryptodome psutil flask", check_exit=False, timeout=180)

def print_skip_build_info():
    """Standard message when CMake build phases are skipped"""
    print("[INFO] CMake not available - skipping build phases")
    print("Will use existing C++ client if available")

def print_port_in_use_warning(port: int):
    """Standardized message when a port appears to be in use"""
    print(f"[WARNING] Port {port} appears to be in use")
    print("This may cause the API server to fail to start.")
    print("You can:")
    print(f"  1. Close other applications using port {port}")
    print("  2. Continue anyway (server may fail to start)")

def print_api_server_troubleshooting():
    """Standard troubleshooting guidance when API server doesn't start"""
    print("\nTroubleshooting steps:")
    print("1. Check if port 9090 is being used by another application")
    print("2. Verify Flask and flask-cors are installed: pip install flask flask-cors")
    print("3. Try running manually: python api_server/cyberbackup_api_server.py")
    print("4. Check console windows for error messages")

def open_web_gui(gui_url: str):
    """Open the Web GUI in the default browser with a standard message"""
    print(f"\nOpening Web GUI in browser: {gui_url}")
    webbrowser.open(gui_url)

def print_api_start_failure():
    """Standardized message when API Bridge Server fails to start"""
    print("[ERROR] API Bridge Server failed to start properly")
    print_api_server_troubleshooting()

def print_backup_server_failure():
    """Standardized message when Python Backup Server fails to start"""
    print("[ERROR] Python Backup Server failed to start properly")
    print("The server is not responding on the expected port.")
    print("\nTroubleshooting steps:")
    print("1. Check if port 1256 is being used by another application")
    print("2. Verify Python dependencies are installed: pip install -r requirements.txt")
    print("3. Try running manually: python python_server/server/server.py")
    print("4. Check the server console window for error messages")
    print("5. Ensure RSA keys exist in the data/ directory")

def handle_error_and_exit(error_message: str, wait_for_input: bool = True):
    """Print error message and exit with status 1"""
    print(error_message)
    if wait_for_input:
        input("Press Enter to exit...")
    sys.exit(1)

def run_command(command: str | list[str], shell: bool = True, check_exit: bool = True, cwd: str | None = None, timeout: int = 60) -> bool:
    """Run a command and handle errors with better timeout and path handling"""
    print(f"Running: {command}")
    print()

    try:
        # For Windows batch files, ensure proper execution
        if isinstance(command, str) and command.endswith('.bat'):
            # Use absolute path and proper shell execution for batch files
            command = os.path.abspath(command)
            # For batch scripts, ensure we run from project root
            if cwd is None:
                script_dir = Path(__file__).parent.parent
                cwd = str(script_dir)

        result = subprocess.run(
            command,
            shell=shell,
            cwd=cwd or os.getcwd(),
            timeout=timeout,
            capture_output=False  # Show output in real-time
        )

        if check_exit and result.returncode != 0:
            print()
            print(f"[ERROR] Command failed with exit code: {result.returncode}")
            wait_for_exit()
            sys.exit(1)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print()
        print(f"[ERROR] Command timed out after {timeout} seconds: {command}")
        if check_exit:
            wait_for_exit()
            sys.exit(1)
        return False
    except Exception as e:
        print()
        print(f"[ERROR] Failed to run command: {e}")
        if check_exit:
            wait_for_exit()
            sys.exit(1)
        return False

def check_command_exists(command: str) -> tuple[bool, str]:
    """Check if a command exists"""
    # Special case for Python - if we're running this script, Python exists
    if command == "python":
        # Check Python version requirement (3.13+)
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 13:
            return True, f"Python {sys.version.split()[0]}"
        elif python_version.major == 3 and python_version.minor >= 8:
            logging.warning(f"Python {python_version.major}.{python_version.minor} detected - Python 3.13+ recommended")
            return True, f"Python {sys.version.split()[0]} (upgrade recommended)"
        else:
            return False, f"Python {python_version.major}.{python_version.minor} is too old - requires 3.13+"

    try:
        result = subprocess.run(f"{command} --version", shell=True,
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        print(f"[DEBUG] Command check failed for {command}: {e}")
        return False, ""

def check_appmap_available():
    """Check if AppMap is available for recording"""
    try:
        result = subprocess.run("appmap-python --help", shell=True,
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def check_api_server_status(host: str = get_config('api.host', '127.0.0.1'), port: int = get_config('api.port', 9090), timeout: int = 2) -> bool:
    """Check if the Flask API server is running and responsive"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_port_available(port: int = get_config('api.port', 9090)) -> bool:
    """Check if a port is available (not in use)"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except Exception:
        return False

def check_python_dependencies() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Check if required Python dependencies are available with version info"""
    required_modules = {
        'flask': 'Flask web framework',
        'flask_cors': 'CORS support for Flask API',
        'psutil': 'System process management',
        'sentry_sdk': 'Error monitoring (optional)',
        'cryptography': 'Cryptographic operations',
        'watchdog': 'File system monitoring'
    }
    missing_modules: list[tuple[str, str]] = []
    optional_missing: list[tuple[str, str]] = []

    for module, description in required_modules.items():
        try:
            imported_module = __import__(module)
            # Try to get version if available (use modern method for Flask)
            if module == 'flask':
                try:
                    import importlib.metadata
                    version = importlib.metadata.version('flask')
                except Exception:
                    version = 'unknown version'
            else:
                version = getattr(imported_module, '__version__', 'unknown version')
            print(f"[OK] {module} ({description}): {version}")
        except ImportError:
            if module in ['sentry_sdk', 'watchdog']:
                optional_missing.append((module, description))
                print(f"[INFO] {module} ({description}): Not installed (optional)")
            else:
                missing_modules.append((module, description))
                print(f"[ERROR] {module} ({description}): Missing (required)")

    return missing_modules, optional_missing

def check_and_fix_vcpkg_dependencies():
    """Check and fix vcpkg dependencies, especially boost-iostreams"""
    print("Checking vcpkg dependencies...")

    # Check if vcpkg.json exists and has required dependencies
    vcpkg_json_path = Path("vcpkg.json")
    if not vcpkg_json_path.exists():
        print("[ERROR] vcpkg.json not found!")
        return False

    try:
        with open(vcpkg_json_path) as f:
            vcpkg_config = json.load(f)

        required_deps = ["boost-asio", "boost-beast", "boost-iostreams", "cryptopp", "zlib"]
        current_deps = vcpkg_config.get("dependencies", [])

        if missing_deps := [dep for dep in required_deps if dep not in current_deps]:
            print(f"[WARNING] Missing vcpkg dependencies: {', '.join(missing_deps)}")
            print("Updating vcpkg.json...")

            # Update dependencies
            vcpkg_config["dependencies"] = required_deps

            with open(vcpkg_json_path, 'w') as f:
                json.dump(vcpkg_config, f, indent=2)

            print("[OK] vcpkg.json updated with missing dependencies")
        else:
            print("[OK] All required vcpkg dependencies are present")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to check vcpkg dependencies: {e}")
        return False

def force_vcpkg_reinstall():
    """Force reinstall of vcpkg dependencies"""
    print("Forcing vcpkg dependency reinstall...")

    # Remove vcpkg_installed directory to force fresh install
    vcpkg_installed_path = Path("vcpkg_installed")
    if vcpkg_installed_path.exists():
        print("Removing vcpkg_installed directory...")
        try:
            import shutil
            shutil.rmtree(vcpkg_installed_path)
            print("[OK] vcpkg_installed directory removed")
        except Exception as e:
            print(f"[WARNING] Failed to remove vcpkg_installed: {e}")

    # Run vcpkg install command
    print("Running vcpkg install...")
    return run_command("vcpkg\\vcpkg.exe install --triplet x64-windows --recurse", timeout=600)

def wait_for_server_startup(host: str = get_config('api.host', '127.0.0.1'), port: int = get_config('api.port', 9090), max_wait: int = 30, check_interval: int = 1) -> bool:
    """Wait for server to start with enhanced progress feedback and diagnostics"""
    print(f"Waiting for API server to start on {host}:{port}...")
    elapsed = 0
    last_error = None

    while elapsed < max_wait:
        try:
            if check_api_server_status(host, port):
                print(f"[OK] API server is responsive after {elapsed}s")
                return True
        except Exception as e:
            last_error = str(e)

        # Show progress with more frequent updates
        if elapsed % 3 == 0 and elapsed > 0:
            print(f"[INFO] Still waiting... ({elapsed}s/{max_wait}s)")

        time.sleep(check_interval)
        elapsed += check_interval

    print(f"[ERROR] API server failed to start within {max_wait} seconds")
    if last_error:
        print(f"[DEBUG] Last connection error: {last_error}")

    # Additional diagnostic information
    print("[DIAGNOSTIC] Checking system status...")
    if check_port_available(port):
        print(f"[DEBUG] Port {port} appears to be available (no process bound)")
    else:
        print(f"[DEBUG] Port {port} is in use by another process")

    return False

def check_backup_server_status():
    """Check if the Python backup server is running on port 1256"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((get_config('server.host', '127.0.0.1'), get_config('server.port', 1256)))
        sock.close()
        return result == 0
    except Exception:
        return False

def _report_terminated_processes(terminated_processes: list[str]):
    """Report terminated processes and wait for cleanup"""
    if terminated_processes:
        print(f"Successfully terminated {len(terminated_processes)} processes:")
        for process_info in terminated_processes:
            print(f"  - {process_info}")
        print()
        # Brief pause to allow processes to fully clean up
        time.sleep(1)
    else:
        print("No CyberBackup processes found running.")
        print()

def check_executable_locations(locations: list[Path] | None = None, _context: str = "C++ client") -> tuple[Path | None, list[Path]]:
    """Check multiple potential locations for the EncryptedBackupClient.exe file

    Args:
        locations: List of Path objects to check. Uses default locations if None.
        _context: Description of what we're looking for (for error messages) - currently unused

    Returns:
        tuple: (found_path, locations_checked) where found_path is Path object or None
    """
    if locations is None:
        locations = [
            Path("build/Release/EncryptedBackupClient.exe"),
            Path("build/EncryptedBackupClient.exe"),
            Path("Client/EncryptedBackupClient.exe"),
            Path("client/EncryptedBackupClient.exe")
        ]

    for exe_path in locations:
        if exe_path.exists():
            return exe_path, locations

    return None, locations

def _latest_mtime(paths: list[Path]) -> float:
    """Return latest modification time across all files under given paths."""
    latest = 0.0
    for p in paths:
        if p.is_file():
            try:
                latest = max(latest, p.stat().st_mtime)
            except Exception:
                pass
        elif p.is_dir():
            with contextlib.suppress(Exception):
                for root, _, files in os.walk(p):
                    for f in files:
                        fp = Path(root) / f
                        with contextlib.suppress(Exception):
                            latest = max(latest, fp.stat().st_mtime)
    return latest

def should_rebuild_cpp(exe_path: Path) -> bool:
    """Determine if the C++ client should be rebuilt based on source changes."""
    if not exe_path.exists():
        return True
    exe_mtime = exe_path.stat().st_mtime
    # Consider key inputs that affect the binary
    inputs = [
        Path("Client/src"),
        Path("Client/include"),
        Path("Client/CMakeLists.txt"),
        Path("CMakeLists.txt"),
    ]
    latest_input = _latest_mtime(inputs)
    return latest_input > exe_mtime

def cleanup_existing_processes():  # sourcery skip: low-code-quality
    """Clean up existing CyberBackup processes with improved reliability"""
    if not psutil:
        print("[WARNING] psutil not available - cannot perform automatic process cleanup")
        print("Please manually close any existing CyberBackup processes")
        return

    print("Cleaning up existing CyberBackup processes...")
    print()

    terminated_processes: list[str] = []

    # Define process patterns to look for
    process_patterns = {
        "API Server": ["cyberbackup_api_server.py", "api_server"],
        "Backup Server": ["python_server/server.py", "server.py", "backup_server"],
        "C++ Client": ["encryptedbackupclient.exe", "EncryptedBackupClient.exe"],
        "Server GUI": ["ServerGUI.py", "server_gui"]
    }

    try:
        # Get list of all running processes with better error handling
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):  # type: ignore
            try:
                process_info: dict[str, Any] = process.info
                cmdline: list[str] = process_info.get('cmdline', [])
                name: str = process_info.get('name', '').lower()

                if not cmdline:
                    continue

                cmdline_str: str = ' '.join(cmdline).lower()
                should_terminate: bool = False
                process_type: str = ""

                # Check against each pattern
                for ptype, patterns in process_patterns.items():
                    if any(pattern.lower() in cmdline_str for pattern in patterns):
                        should_terminate = True
                        process_type = ptype
                        break

                # Additional port-based detection with safer connection checking
                if not should_terminate:
                    with contextlib.suppress(AttributeError, psutil.AccessDenied, psutil.NoSuchProcess):
                        # Use psutil.net_connections() for port checking
                        for conn in psutil.net_connections():
                            if (hasattr(conn, 'laddr') and conn.laddr and
                                hasattr(conn, 'pid') and conn.pid == process_info['pid']):
                                # Safely get port from connection info
                                port: int | None = None
                                if hasattr(conn.laddr, 'port'):
                                    port = conn.laddr.port
                                elif len(conn.laddr) >= 2:
                                    port = conn.laddr[1]

                                if (port in [9090, 1256] and
                                    hasattr(conn, 'status') and conn.status == psutil.CONN_LISTEN and
                                    ('python' in name or 'flask' in cmdline_str)):
                                        should_terminate = True
                                        process_type = f"Port-bound Server ({port})"
                                        break

                if should_terminate:
                    print(f"Terminating {process_type} (PID: {process.info['pid']})")
                    try:
                        # Try graceful termination first
                        process.terminate()
                        process.wait(timeout=3)
                        terminated_processes.append(f"{process_type} (PID: {process.info['pid']})")
                    except psutil.TimeoutExpired:
                        # Force kill if graceful termination fails
                        print(f"  Force killing PID {process.info['pid']} (timeout)")
                        process.kill()
                        terminated_processes.append(f"{process_type} (PID: {process.info['pid']}) - Force killed")
                    except psutil.NoSuchProcess:
                        # Process already terminated
                        terminated_processes.append(f"{process_type} (PID: {process.info['pid']}) - Already terminated")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue  # Process may have disappeared or we don't have access

    except Exception as e:
        print(f"[WARNING] Error during process cleanup: {e}")

    _report_terminated_processes(terminated_processes)

    # Additional port cleanup with improved error handling
    if psutil:
        ports_to_clean = [get_config('api.port', 9090), get_config('server.port', 1256)]
        for port in ports_to_clean:
            try:
                print(f"Checking for processes on port {port}...")
                port_processes: list[int] = []

                for conn in psutil.net_connections():
                    conn_port: int | None = None
                    if hasattr(conn, 'laddr') and conn.laddr:
                        if hasattr(conn.laddr, 'port'):
                            conn_port = conn.laddr.port
                        elif len(conn.laddr) >= 2:
                            conn_port = conn.laddr[1]

                    if conn_port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
                        port_processes.append(conn.pid)

                for pid in port_processes:
                    with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        process = psutil.Process(pid)
                        process_name: str = process.name()
                        print(f"Terminating process using port {port}: {process_name} (PID: {pid})")
                        process.terminate()

                        # Give process time to terminate gracefully
                        try:
                            process.wait(timeout=3)
                            print(f"Process {pid} terminated gracefully")
                        except psutil.TimeoutExpired:
                            print(f"Force killing process {pid}")
                            process.kill()

            except Exception as e:
                print(f"[WARNING] Error cleaning port {port}: {e}")

    print("[OK] Process cleanup completed!")
    print()

def main():
    # Setup logging first
    setup_logging()
    server_port = get_config('server.port', 1256)
    api_port = get_config('api.port', 9090)
    gui_url = f"http://{get_config('api.host', '127.0.0.1')}:{api_port}/"
    logging.info("Starting CyberBackup 3.0 build and deployment process")

    # Enhanced Unicode console setup
    setup_unicode_console()

    print()
    print("=" * 72)
    safe_print("   [LAUNCH] ONE-CLICK BUILD AND RUN - CyberBackup 3.0")
    print("=" * 72)
    print()
    print("Starting complete build and deployment process...")
    print("This will configure, build, and launch the entire backup framework.")
    print()

    # Change to project root directory (parent of scripts directory)
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    print(f"Working directory: {os.getcwd()}")
    print()

    # ========================================================================
    # PHASE 0: CLEANUP EXISTING PROCESSES
    # ========================================================================
    print_phase(0, 7, "Cleaning Up Existing Processes")
    cleanup_existing_processes()

    # ========================================================================
    # PHASE 1: PREREQUISITES CHECK
    # ========================================================================
    print_phase(1, 7, "Checking Prerequisites")

    # Check Python
    exists, version = check_command_exists("python")
    if not exists:
        handle_error_and_exit("[ERROR] Python 3.13+ is not installed or not in PATH\nPlease install Python 3.13+ and add it to your PATH")
    print(f"[OK] Python found: {version.split()[1] if 'Python' in version else version}")

    # Check CMake
    exists, version = check_command_exists("cmake")
    if not exists:
        print("[WARNING] CMake is not installed or not in PATH")
        print("Skipping C++ build phases - will run existing components only")
        skip_build = True
    else:
        print(f"[OK] CMake found: {version.split()[2] if 'version' in version else version}")
        skip_build = False

    # Check Git (optional)
    exists, version = check_command_exists("git")
    if exists:
        print("[OK] Git found")
    else:
        print("[WARNING] Git not found (optional but recommended)")

    print()
    print("Prerequisites check completed successfully!")
    print()

    if not skip_build:
        # ========================================================================
        # PHASE 2: CMAKE CONFIGURATION AND VCPKG SETUP
        # ========================================================================
        print_phase(2, 7, "Configuring Build System")

        # Check and fix vcpkg dependencies first
        if not check_and_fix_vcpkg_dependencies():
            handle_error_and_exit("[ERROR] Failed to verify vcpkg dependencies!")

        print("Configuring CMake with vcpkg toolchain...")
        print()

        # Configure CMake directly to avoid batch script issues
        print("[1/4] Ensuring vcpkg is bootstrapped...")
        vcpkg_dir = Path("vcpkg")
        if vcpkg_dir.exists() and (vcpkg_dir / "vcpkg.exe").exists():
            print("[OK] vcpkg is already bootstrapped")
        else:
            print("[ERROR] vcpkg not found or not bootstrapped properly")
            wait_for_exit()
            sys.exit(1)

        # Enable/augment vcpkg binary caching to a repo-local cache as well
        try:
            vcpkg_cache = Path("vcpkg_cache")
            vcpkg_cache.mkdir(exist_ok=True)
            current_sources = os.environ.get("VCPKG_BINARY_SOURCES", "")
            local_files_source = f"files,{vcpkg_cache.resolve()},readwrite"
            # Prepend our local files cache while keeping defaults
            if current_sources:
                os.environ["VCPKG_BINARY_SOURCES"] = f"{local_files_source};{current_sources}"
            else:
                os.environ["VCPKG_BINARY_SOURCES"] = f"{local_files_source};default"
        except Exception:
            # Best-effort; safe to continue without
            pass

        # Optional flag to skip vcpkg install for faster iterations when deps are already present
        skip_vcpkg = ("--no-vcpkg" in sys.argv) or (os.environ.get("SKIP_VCPKG") == "1")
        if skip_vcpkg:
            print("[2/4] Skipping vcpkg install due to --no-vcpkg flag/SKIP_VCPKG=1")
        else:
            print("[2/4] Installing vcpkg dependencies...")

        # Retry mechanism for vcpkg install (handles file locking issues)
            max_retries = 3
            install_success = False

            for attempt in range(1, max_retries + 1):
                print(f"\\nAttempt {attempt}/{max_retries}...")

                if run_command(["vcpkg\\vcpkg.exe", "install", "--triplet", "x64-windows", "--recurse"], shell=False, timeout=600):
                    install_success = True
                    break

                if attempt < max_retries:
                    print(f"\\n[WARNING] vcpkg install failed (attempt {attempt}/{max_retries})")
                    print("Cleaning buildtrees to resolve file locks...")

                    # Clean problematic package buildtrees (common offenders on Windows)
                    import shutil
                    for pkg in ("boost-mpl", "zstd"):
                        bt = Path("vcpkg") / "buildtrees" / pkg
                        if bt.exists():
                            shutil.rmtree(bt, ignore_errors=True)
                            print(f"[OK] Cleaned {pkg} buildtree")

                    print("Waiting 3 seconds before retry...")
                    time.sleep(3)

            if not install_success:
                print("[ERROR] vcpkg dependency installation failed after all retries!")
                print("\\nPossible solutions:")
                print("1. Close any programs that might have files locked (antivirus, Windows Explorer)")
                print("2. Move the project to a shorter path (e.g., C:\\\\cyberbackup)")
                print("3. Manually run: vcpkg\\\\vcpkg.exe remove boost-mpl:x64-windows")
                print("   Then run this script again")
                wait_for_exit()
                sys.exit(1)

        print("[3/4] Preparing CMake build directory...")
        build_dir = Path("build")
        clean_build = ("--clean" in sys.argv) or (os.environ.get("CLEAN_BUILD") == "1")
        if clean_build and build_dir.exists():
            print("--clean detected: removing existing build directory...")
            shutil.rmtree(build_dir, ignore_errors=True)
        build_dir.mkdir(exist_ok=True)

        print("[4/4] Configuring CMake with vcpkg integration (incremental)...")
        cmake_cache = build_dir / "CMakeCache.txt"
        reconfigure = ("--reconfigure" in sys.argv) or clean_build or (not cmake_cache.exists())
        if reconfigure:
            if not run_command([
                "cmake", "-B", "build", "-S", ".",
                "-DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake",
                "-DVCPKG_TARGET_TRIPLET=x64-windows",
                "-A", "x64"
            ], shell=False, timeout=300):
                print_error_with_newline("[ERROR] CMake configuration failed!")
                wait_for_exit()
                sys.exit(1)
        else:
            print("CMake cache detected - skipping reconfigure. Use --reconfigure to force it.")

        print_success_with_spacing("[OK] CMake configuration completed successfully!")

        # ========================================================================
        # PHASE 3: BUILD C++ CLIENT
        # ========================================================================
        print_phase(3, 7, "Building C++ Client")

        # Determine if a rebuild is actually needed
        exe_path_default = Path("build/Release/EncryptedBackupClient.exe")
        exe_path_alt = Path("build/EncryptedBackupClient.exe")
        exe_path = exe_path_default if exe_path_default.exists() else exe_path_alt

        if not should_rebuild_cpp(exe_path):
            print("No C++ source changes detected since last build — skipping rebuild.")
        else:
            # Speed up builds by enabling parallelism
            try:
                os.environ.setdefault("CMAKE_BUILD_PARALLEL_LEVEL", str(os.cpu_count() or 4))
            except Exception:
                pass

            build_cmd = "cmake --build build --config Release --parallel"
            print_build_command_info("Building EncryptedBackupClient.exe with CMake...", build_cmd)
            print()

            if not run_command(build_cmd, timeout=600):
                print_build_failure_help()

                # Offer to try automatic fix
                try:
                    choice = input("Would you like to try automatic vcpkg dependency reinstall? (y/N): ").strip().lower()
                    if choice in ['y', 'yes']:
                        print("\nAttempting automatic fix...")
                        if force_vcpkg_reinstall():
                            print("Retrying build...")
                            if run_command(build_cmd, timeout=600):
                                print("[OK] Build succeeded after vcpkg reinstall!")
                            else:
                                handle_error_and_exit("[ERROR] Build still failed after vcpkg reinstall\nManual intervention may be required")
                        else:
                            handle_error_and_exit("[ERROR] vcpkg reinstall failed")
                    else:
                        handle_error_and_exit("", wait_for_input=True)
                except (EOFError, KeyboardInterrupt):
                    handle_error_and_exit("\nExiting...", wait_for_input=False)

        # Verify the executable was created with fallback locations
        found_exe, checked_locations = check_executable_locations()
        report_executable_status(found_exe, checked_locations)

        print_spacing()
        print("[OK] C++ client built successfully!")
        print(f"   Location: {found_exe}")
        print_spacing()
    else:
        print_spacing()
        print_phase(2, 7, "Skipping Build System Configuration")
        print_skip_build_info()
        print_spacing()

        print_phase(3, 7, "Checking Existing C++ Client")
        found_exe, checked_locations = check_executable_locations()

        if found_exe:
            print(f"[OK] Found existing C++ client: {found_exe}")
        else:
            print("[WARNING] No C++ client found - web uploads may not work")
            print("Checked locations:")
            for path in checked_locations:
                print(f"  - {path}")
            print("\nRecommendation: Run cmake --build build --config Release")
        print()

    # ========================================================================
    # PHASE 4: PYTHON ENVIRONMENT SETUP
    # ========================================================================
    print_phase(4, 7, "Setting up Python Environment")

    # Install Python dependencies (uses helper to avoid duplicate logic)
    install_python_dependencies()

    # Install additional dependencies with better error handling
    install_additional_dependencies()

    # ========================================================================
    # PHASE 5: CONFIGURATION VERIFICATION
    # ========================================================================
    print_phase(5, 7, "Verifying Configuration")

    # Check if RSA keys exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    private_key = data_dir / "valid_private_key.der"
    if private_key.exists():
        print("[OK] RSA private key found")
    else:
        print("[WARNING] RSA private key missing - generating keys...")
        run_command("python scripts\\security\\key-generation\\create_working_keys.py", check_exit=False, timeout=60)

    public_key = data_dir / "valid_public_key.der"
    if public_key.exists():
        print("[OK] RSA public key found")
    else:
        print("[WARNING] RSA public key missing - generating keys...")
        run_command("python scripts\\security\\key-generation\\create_working_keys.py", check_exit=False, timeout=60)

    # Check if transfer.info exists
    transfer_info = data_dir / "transfer.info"
    if transfer_info.exists():
        print("[OK] transfer.info configuration found")
    else:
        print("[WARNING] Creating default transfer.info...")
        with open(transfer_info, 'w') as f:
            f.write(f"{get_config('server.host', '127.0.0.1')}:{get_config('server.port', 1256)}\n")
            f.write("testuser\n")
            f.write("test_file.txt\n")

    print_success_with_spacing("[OK] Configuration verification completed!")

    # ========================================================================
    # PHASE 6: LAUNCH FLETV2 DESKTOP GUI WITH INTEGRATED SERVER
    # ========================================================================
    print_phase(6, 7, "Launching FletV2 Desktop GUI")

    print("Starting FletV2 Desktop GUI with integrated BackupServer...")
    print()
    print_multiline(
        "FletV2 Desktop GUI features:",
        "   • Material Design 3 interface",
        "   • Real-time server monitoring",
        "   • Client and file management",
        "   • Database administration panel",
        "   • Enhanced logging with search/export",
        "   • Analytics dashboard with charts",
        "   • Server settings management",
    )
    print()
    print_multiline(
        "Integrated BackupServer capabilities:",
        "   • Network listener on port 1256 (for C++ client connections)",
        "   • SQLite database (defensive.db)",
        "   • Client session management",
        "   • File encryption and storage",
    )
    print()

    # Validate FletV2 launcher exists
    fletv2_launcher = Path("FletV2/start_with_server.py")
    fletv2_running = False
    fletv2_process = None

    if not fletv2_launcher.exists():
        print_server_not_found_help(fletv2_launcher, "FletV2/start_with_server.py")
        handle_error_and_exit("[ERROR] FletV2 launcher not found - cannot start GUI", wait_for_input=True)

    print(f"Launching: {fletv2_launcher}")
    print(f"Command: python FletV2/start_with_server.py")
    print()

    # Prepare environment for FletV2
    fletv2_env = os.environ.copy()
    fletv2_env['PYTHONPATH'] = os.getcwd()  # Ensure module imports work
    fletv2_env['CYBERBACKUP_DISABLE_INTEGRATED_GUI'] = '1'  # Prevent dual GUI managers
    fletv2_env['CYBERBACKUP_DISABLE_GUI'] = '1'  # Force console mode for server
    fletv2_env['BACKUP_DATABASE_PATH'] = str(Path(os.getcwd()) / "defensive.db")  # Database location

    # Launch FletV2 in new console window
    try:
        fletv2_process = subprocess.Popen(
            [sys.executable, str(fletv2_launcher)],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
            env=fletv2_env,
            cwd=os.getcwd()
        )
        print(f"[OK] FletV2 Desktop GUI launched (PID: {fletv2_process.pid})")
        print("     Native desktop window will appear momentarily...")
        print()

        # Brief initialization delay
        print("Waiting for FletV2 initialization...")
        time.sleep(3)

        # Verify process didn't crash immediately
        if fletv2_process.poll() is None:
            print("[OK] FletV2 process is running")
            print("     BackupServer network listener starting on port 1256...")
            print("     Desktop GUI initialization in progress...")
            fletv2_running = True
        else:
            print("[ERROR] FletV2 process terminated unexpectedly")
            print("        Check the FletV2 console window for error details")
            print()
            print("Common issues:")
            print("  • Missing flet_venv virtual environment")
            print("  • Flet package not installed (pip install flet==0.28.3)")
            print("  • Database path issues (defensive.db not found)")
            print("  • Import errors (check PYTHONPATH)")
            fletv2_running = False

    except Exception as launch_err:
        print(f"[ERROR] Failed to launch FletV2: {launch_err}")
        print()
        print("Troubleshooting:")
        print("1. Verify FletV2/start_with_server.py exists")
        print("2. Check flet_venv is installed: cd FletV2 && ../flet_venv/Scripts/python --version")
        print("3. Try manual launch: python FletV2/start_with_server.py")
        print("4. Check logs in logs/build_script.log")
        fletv2_running = False

    print()

    # ========================================================================
    # API BRIDGE SERVER STARTUP (FOR C++ CLIENT WEB GUI)
    # ========================================================================
    # CRITICAL: This API server enables the C++ client's JavaScript web interface.
    # It is NOT used by FletV2 (which uses direct ServerBridge method calls).
    #
    # Architecture:
    #   Web GUI (browser) → API Server (port 9090) → RealBackupExecutor
    #     → C++ Client (subprocess) → BackupServer (port 1256 in FletV2 process)
    #
    # DO NOT REMOVE - The C++ backup client requires this API to function.

    print("Preparing API Bridge Server for C++ Client Web GUI...")
    print("[INFO] This API server is for C++ client operations, NOT FletV2 admin GUI")
    print("[INFO] FletV2 uses direct ServerBridge calls to BackupServer")
    print()

    # Step 1: Check Python dependencies with enhanced reporting
    print("\nChecking Python dependencies...")
    missing_deps, optional_missing = check_python_dependencies()

    if missing_deps:
        print_missing_and_optional_deps(
            "\n[ERROR] Missing required Python modules:",
            missing_deps,
            "\nInstall missing dependencies:",
        )
        for dep, _ in missing_deps:
            if dep == 'flask_cors':
                print("  pip install flask-cors")
            else:
                print(f"  pip install {dep}")
        print("\nOr install all at once:")
        dep_names = [dep for dep, _ in missing_deps]
        print(f"  pip install {' '.join(dep_names)}")
        print()
        with contextlib.suppress(EOFError):
            input("Press Enter to continue anyway (may cause startup failure)...")
    else:
        print("\n[OK] All required Python dependencies are available")

    if optional_missing:
        print_missing_and_optional_deps(
            "\n[INFO] Optional dependencies not installed:",
            optional_missing,
            "These are optional but recommended for full functionality.",
        )
    # Step 2: Check port availability
    print("\nChecking port availability...")
    if not check_port_available(9090):
        print_port_in_use_warning(9090)
        print()
        with contextlib.suppress(EOFError):
            input("Press Enter to continue...")
    else:
        print("[OK] Port 9090 is available")

    # Step 3: Start API server with enhanced error handling
    api_server_path = Path("api_server/cyberbackup_api_server.py")
    api_process = None
    server_started_successfully = False

    # Validate API server path exists
    if not api_server_path.exists():
        print_server_not_found_help(api_server_path, "api_server/cyberbackup_api_server.py")
        server_started_successfully = False
    elif api_server_path.exists():
        print(f"\nStarting API Bridge Server: {api_server_path}")

        try:
            # Start API server in new console window with visible output
            # Fixed: Use module syntax to avoid circular import issues
            # Set up API server environment with PYTHONPATH
            api_env = os.environ.copy()
            # CRITICAL: Set PYTHONPATH so Python can find project modules
            api_env['PYTHONPATH'] = os.getcwd()

            api_process = subprocess.Popen(
                [sys.executable, "-m", "api_server.cyberbackup_api_server"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                env=api_env
            )
            print(f"API Bridge Server started with PID: {api_process.pid}")

            # Step 4: Wait for server to become responsive
            server_started_successfully = wait_for_server_startup()

            if server_started_successfully:
                print("[OK] API Bridge Server is running and responsive!")
            else:
                print_api_start_failure()

        except Exception as e:
            print(f"[ERROR] Failed to start API server: {e!s}")
            server_started_successfully = False
    else:
        # Try alternative API server locations
        alt_api_locations = [
            Path("cyberbackup_api_server.py"),
            Path("src/api/cyberbackup_api_server.py"),
            Path("api/cyberbackup_api_server.py")
        ]

        found_alt_api = None
        for alt_path in alt_api_locations:
            if alt_path.exists():
                found_alt_api = alt_path
                print(f"[INFO] Found alternative API server: {alt_path}")
                api_server_path = alt_path
                break

        if not found_alt_api:
            print("[ERROR] API server file not found in any expected location:")
            print(f"  - {api_server_path}")
            for alt_path in alt_api_locations:
                print(f"  - {alt_path}")
            server_started_successfully = False

    # API Server status check (for C++ client connectivity)
    if server_started_successfully:
        print("[OK] API Bridge Server is operational")
        print(f"     C++ client web GUI available at: {gui_url}")
        print("     (Open in browser to perform backups via C++ client)")
        print()
        print("[INFO] FletV2 Desktop GUI handles its own window - no browser needed")
        print()

        # Automatically open web browser for C++ client GUI
        print(f"Opening C++ client web GUI in browser: {gui_url}")
        time.sleep(1)  # Brief delay to ensure server is fully ready
        try:
            webbrowser.open(gui_url)
            print("[OK] Web browser launched successfully")
        except Exception as e:
            print(f"[WARNING] Failed to open browser automatically: {e}")
            print(f"Please manually open: {gui_url}")
    else:
        print("[WARNING] API Bridge Server failed to start")
        print("          C++ client backups will not be available")
        print()
        print("Troubleshooting:")
        print("1. Check if port 9090 is already in use: netstat -an | findstr 9090")
        print("2. Verify Flask installed: pip install flask flask-cors")
        print("3. Try manual launch: python api_server/cyberbackup_api_server.py")
        print("4. Check API server console window for error messages")

    # Enhanced success/status message
    print()
    print("=" * 70)
    if fletv2_running and server_started_successfully:
        safe_print("   [SUCCESS] ONE-CLICK BUILD AND RUN COMPLETED SUCCESSFULLY!")
    else:
        safe_print("   [WARNING] ONE-CLICK BUILD AND RUN COMPLETED WITH ISSUES")
    print("=" * 70)
    print()
    print("CyberBackup 3.0 System Status:")
    print("=" * 70)
    print()

    # Check component status
    backup_server_running = check_backup_server_status()  # Port 1256 (in FletV2 process)
    api_server_running = check_api_server_status()  # Port 9090 (API server process)

    # Component status overview
    try:
        print("Components:")
        fletv2_pid_str = f"PID: {fletv2_process.pid}" if fletv2_process and fletv2_running else "Not started"
        print(f"   [FletV2] Desktop GUI:       {f'✅ Running ({fletv2_pid_str})' if fletv2_running else '❌ Process terminated'}")
        print(f"   [SERVER] BackupServer:      {f'✅ Listening on port {server_port}' if backup_server_running else '⚠️  Not responding on port {server_port}'}")
        print(f"   [API] C++ Client Bridge:    {f'✅ Running on port {api_port}' if api_server_running else '❌ Not responding on port {api_port}'}")
        print(f"   [WEB] Client Web GUI:       {f'✅ Available at {gui_url}' if api_server_running else '❌ API server down'}")
    except UnicodeEncodeError:
        # Fallback for terminals without emoji support
        print("Components:")
        fletv2_pid_str = f"PID: {fletv2_process.pid}" if fletv2_process and fletv2_running else "Not started"
        print(f"   [FletV2] Desktop GUI:       {f'[OK] Running ({fletv2_pid_str})' if fletv2_running else '[ERROR] Process terminated'}")
        print(f"   [SERVER] BackupServer:      {f'[OK] Listening on port {server_port}' if backup_server_running else '[WARNING] Not responding on port {server_port}'}")
        print(f"   [API] C++ Client Bridge:    {f'[OK] Running on port {api_port}' if api_server_running else '[ERROR] Not responding on port {api_port}'}")
        print(f"   [WEB] Client Web GUI:       {f'[OK] Available at {gui_url}' if api_server_running else '[ERROR] API server down'}")

    print()
    print("Component Details:")
    print("─" * 70)
    print()

    print("FletV2 Desktop GUI:")
    print("  Purpose:   Server administration and monitoring")
    print("  Interface: Native desktop window (Material Design 3)")
    print("  Status:    " + ("✅ Running" if fletv2_running else "❌ Not running"))
    print()

    print("BackupServer (integrated in FletV2):")
    print("  Purpose:   Accept encrypted file backups from C++ clients")
    print("  Protocol:  Binary protocol with AES-256-CBC encryption")
    print("  Network:   Port 1256 (TCP listener)")
    print("  Database:  defensive.db (SQLite)")
    print("  Status:    " + ("✅ Listening" if backup_server_running else "❌ Not listening"))
    print()

    print("API Bridge Server:")
    print("  Purpose:   Enable C++ client's JavaScript web interface")
    print("  Protocol:  HTTP + WebSocket")
    print("  Network:   Port 9090")
    print("  Features:  File upload, real-time progress, backup history")
    print("  Status:    " + ("✅ Running" if api_server_running else "❌ Not running"))
    print()

    print("=" * 70)
    print()

    if fletv2_running and api_server_running and backup_server_running:
        print_multiline(
            "✅ [SUCCESS] All components are running properly:",
            "",
            "   1. FletV2 Desktop GUI is open (native window for server admin)",
            "   2. BackupServer is accepting connections on port 1256",
            "   3. API Server is serving C++ client web GUI on port 9090",
            "   4. Both GUIs can manage backups and clients",
            "   5. Shared database: defensive.db (SQLite with file locking)",
        )
        print()
        print("Next Steps:")
        print("  • Use FletV2 Desktop GUI window for server administration")
        print(f"  • Open {gui_url} in browser for C++ client backup operations")
        print("  • All components share the same database and file storage")
        print()

    elif fletv2_running and backup_server_running:
        print_multiline(
            "⚠️  [PARTIAL SUCCESS] FletV2 running but API server has issues:",
            "",
            "   ✅ FletV2 Desktop GUI operational (server administration works)",
            "   ✅ BackupServer accepting client connections (port 1256)",
            "   ❌ API Server not responding (C++ client backups disabled)",
        )
        print()
        print("Impact:")
        print("  • Server administration via FletV2: FULLY FUNCTIONAL")
        print("  • C++ client backup operations: UNAVAILABLE")
        print()
        print("To fix API server:")
        print("  1. Check API server console window for errors")
        print("  2. Verify port 9090 not in use: netstat -an | findstr 9090")
        print("  3. Try manual start: python api_server/cyberbackup_api_server.py")
        print()

    elif fletv2_running:
        print_multiline(
            "⚠️  [PARTIAL SUCCESS] FletV2 GUI running but server issues:",
            "",
            "   ✅ FletV2 Desktop GUI operational",
            "   ❌ BackupServer not listening (C++ clients cannot connect)",
            "   " + ("✅" if api_server_running else "❌") + f" API Server {'operational' if api_server_running else 'not responding'}",
        )
        print()
        print("Impact:")
        print("  • GUI interface works but cannot accept file backups")
        print()
        print("To fix BackupServer:")
        print("  1. Check FletV2 console window for BackupServer errors")
        print("  2. Verify port 1256 available: netstat -an | findstr 1256")
        print("  3. Check database exists: defensive.db in project root")
        print()

    else:
        print_multiline(
            "❌ [SYSTEM FAILURE] Critical components not running:",
            "",
            "   ❌ FletV2 Desktop GUI process terminated or failed to start",
            "   " + ("✅" if backup_server_running else "❌") + " BackupServer " + ("operational" if backup_server_running else "not listening"),
            "   " + ("✅" if api_server_running else "❌") + " API Server " + ("operational" if api_server_running else "not responding"),
        )
        print()
        print("Troubleshooting Steps:")
        print("  1. Check FletV2 console window for error messages")
        print("  2. Verify virtual environment: cd FletV2 && ../flet_venv/Scripts/python --version")
        print("  3. Check database exists: defensive.db in project root")
        print("  4. Verify Flet installed: cd FletV2 && ../flet_venv/Scripts/pip list | grep flet")
        print("  5. Review build script logs: logs/build_script.log")
        print("  6. Try manual FletV2 launch: python FletV2/start_with_server.py")
        print()

    print("=" * 70)


def print_missing_and_optional_deps(header: str, deps: list[tuple[str, str]], footer: str):
    """Print missing or optional dependencies in a standardized format."""
    print(header)
    for dep, desc in deps:
        print(f"  - {dep}: {desc}")
    print(footer)


def print_multiline(*lines: str):
    """Print multiple lines passed as positional args."""
    for line in lines:
        print(line)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Build process interrupted by user")
        print("Attempting to clean up any started processes...")
        try:
            cleanup_existing_processes()
        except Exception as cleanup_error:
            print(f"[WARNING] Error during cleanup: {cleanup_error}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] An unexpected error occurred: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        print("[DEBUG] Stack trace:")
        traceback.print_exc()
        print("\nFor troubleshooting:")
        print("1. Check that all dependencies are installed: pip install -r requirements.txt")
        print("2. Verify Python and CMake are in PATH")
        print("3. Run individual components manually to isolate the issue")
        print("4. Check logs in the logs/ directory")
        with contextlib.suppress(EOFError):
            input("Press Enter to exit...")
        sys.exit(1)
