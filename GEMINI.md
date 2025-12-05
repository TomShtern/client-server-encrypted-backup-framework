# GEMINI Code Context for Client-Server Encrypted Backup Framework

> **CRITICAL**: For extremely important AI guidance, rules, and design reference materials, first consult the `AI-CONTEXT-IMPORTANT/` folder for critical decisions.

## 🎯 Project Overview

A **production-ready encrypted backup system** with multi-component architecture featuring:

- **Security**: RSA-1024 key exchange + AES-256-CBC file encryption
- **C++ Client**: Native EncryptedBackupClient.exe with custom binary protocol (RSA + AES + CRC32)
- **Python Backup Server**: Multi-threaded network listener (port 1256) with SQLite database
- **Flask API Server**: HTTP/WebSocket bridge (port 9090) for web UI and coordination
- **FletV2 Desktop GUI**: Material Design 3 admin interface with real-time monitoring
- **Web UI**: Browser-based backup interface for end-users
- **Shared Library**: Modular sub-packages for cross-cutting concerns

The system prioritizes **security** (encryption + CRC verification), **robustness** (subprocess lifecycle management, file monitoring), and **modern UX** (Material Design 3, Neumorphism, Glassmorphism).

Current development focus: **FletV2 desktop GUI stabilization and enhancement**.

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       FletV2 Desktop GUI                        │
│  (Admin Interface - Direct Python calls via ServerBridge)       │
└────────────┬───────────────────────────┬────────────────────────┘
             │                           │
             │ ServerBridge              │ Direct DB Access
             ▼                           ▼
┌────────────────────┐        ┌─────────────────────┐
│  Python Server     │◄──────►│   SQLite Database   │
│  (Port 1256)       │        │   (defensive.db)    │
│  Network Listener  │        └─────────────────────┘
└────────────────────┘                  ▲
             ▲                          │
             │ Binary Protocol          │ File-level locking
             │ (RSA+AES+CRC32)          │
┌────────────────────┐        ┌─────────────────────┐
│  C++ Client        │        │  Flask API Server   │
│  (.exe subprocess) │◄───────│  (Port 9090)        │
└────────────────────┘        └─────────────────────┘
                                       ▲
                                       │ HTTP/WebSocket
                              ┌────────────────────┐
                              │     Web UI         │
                              │  (Browser-based)   │
                              └────────────────────┘
```

### 1. **C++ Client (`Client/`)**
   - **Purpose**: Native encryption engine with custom binary protocol
   - **Build**: CMake + vcpkg (C++17)
   - **Dependencies**: Crypto++ (RSA + AES), Boost.Asio (networking), ZLIB (compression), Sentry (error tracking)
   - **Executable**: `build/Release/EncryptedBackupClient.exe`
   - **CRITICAL**: Must be run with `--batch` flag to prevent hanging in subprocess mode
   - **Transfer Format**: `transfer.info` (3-line format: server:port, username, file_path)

### 2. **Python Backup Server (`python_server/`)**
   - **Purpose**: Core backend - network listener, encryption/decryption, file storage, database management
   - **Key Files**:
     - `python_server/server/server.py` - Main server with network listener thread
     - `python_server/server/database.py` - SQLite interactions
     - `python_server/server/protocol.py` - Binary protocol implementation
     - `python_server/server/network_server.py` - TCP network layer
     - `python_server/server/request_handlers.py` - Request processing
     - `python_server/server/file_transfer.py` - File transfer logic
   - **Features**: Multi-threaded, integrated GUI (`GUIManager`), periodic maintenance (session timeouts, partial file cleanup)
   - **Port**: 1256 (configurable)
   - **Database**: SQLite3 (`data/database/defensive.db`)

### 3. **Flask API Server (`api_server/`)**
   - **Purpose**: HTTP/WebSocket bridge coordinating web UI, FletV2 GUI, and C++ client
   - **Key File**: `api_server/cyberbackup_api_server.py`
   - **Key Component**: `api_server/real_backup_executor.py` - Manages C++ client subprocess lifecycle
   - **Features**: RESTful API, WebSocket (flask-socketio), web UI asset serving, performance monitoring, Sentry integration
   - **Port**: 9090 (configurable)
   - **CRITICAL**: Uses `RealBackupExecutor` to spawn C++ client with proper working directory and `--batch` flag

### 4. **FletV2 Desktop GUI (`FletV2/`)**
   - **Purpose**: Cross-platform Material Design 3 admin interface for server management
   - **Key Files**:
     - `FletV2/main.py` - Application entry point (~1.6K lines)
     - `FletV2/theme.py` - Sophisticated theming (Material Design 3, Neumorphism, Glassmorphism)
     - `FletV2/server_adapter.py` - ServerBridge for Python server interaction
     - `FletV2/fletv2_gui_manager.py` - GUI lifecycle management
     - `FletV2/views/dashboard.py` - Server overview
     - `FletV2/views/settings.py` - Configuration management
   - **Design**: Material Design 3 with Neumorphism and Glassmorphism
   - **Communication**: Direct Python calls via `ServerBridge` (no network overhead)
   - **Launcher**: `FletV2/start_with_server.py` - Integrated server + GUI startup

### 5. **Web UI (`Client/Client-gui/`)**
   - **Purpose**: Browser-based file selection and backup initiation
   - **Served by**: Flask API server (port 9090)

### 6. **Shared Library (`Shared/`)**
   - **Purpose**: Cross-cutting utilities organized into focused sub-packages
   - **CRITICAL SUB-PACKAGES**:
     - `Shared/filesystem/` - UTF-8 handling, file operations, path utilities, streaming file utils
       - `utf8_solution.py` - **CRITICAL** for subprocess and console I/O
       - `file_operations.py`, `path_utils.py`, `streaming_file_utils.py`
       - `file_lifecycle.py` - Managed file lifecycle (SynchronizedFileManager)
     - `Shared/logging/` - Enhanced logging, error handling, output formatting
       - `logging_utils.py`, `enhanced_output.py`, `error_handler.py`, `error_handling.py`
       - `flet_log_capture.py` - Flet GUI log integration
     - `Shared/monitoring/` - Performance, process, and file monitoring
       - `observability.py`, `performance_monitor.py`, `process_monitor.py`
       - `unified_monitor.py` - UnifiedFileMonitor for backup verification
       - `thread_manager.py` - Thread lifecycle management
     - `Shared/config/` - Configuration management
       - `unified_config.py` - **CRITICAL** unified configuration system (JSON + .info + env vars)
     - `Shared/validation/` - Validation utilities
       - `client_validation.py` - Client name and data validation
   - `Shared/sentry_config.py` - Sentry error tracking initialization
   - `Shared/crc.py` - CRC32 verification
   - `Shared/canonicalize.py` - Canonical data representations

## 🚀 Building and Running

### Quick Start

**Option 1: One-Click System Launch (Recommended)**
```bash
python scripts/one_click_build_and_run.py
```
This will:
1. Build the C++ client via CMake + vcpkg
2. Launch Python backup server with network listener (port 1256)
3. Launch Flask API server (port 9090)
4. Launch FletV2 desktop GUI
5. Open Web UI in browser

**Option 2: FletV2 GUI Development (Hot-Reload)**
```bash
cd FletV2
flet run main.py
# or use the flet_venv:
..\flet_venv\Scripts\python main.py
```

### Prerequisites

- **Windows**: MSVC Build Tools
- **Python**: 3.13+ (project tested with 3.13.7)
- **C++ Compiler**: MSVC with C++17 support
- **Build Tools**: CMake 3.15+
- **Package Manager**: vcpkg (integrated via `vcpkg.json`)
- **Flet Environment**: Dedicated venv (`flet_venv/`)

### C++ Client Build

The C++ client uses `CMakeLists.txt` with vcpkg dependency management:

```bash
# Configure with vcpkg toolchain
cmake -B build -DCMAKE_TOOLCHAIN_FILE="vcpkg\scripts\buildsystems\vcpkg.cmake"
# Build
cmake --build build --config Release
```

**Dependencies** (managed via `vcpkg.json`):
- `boost-asio`, `boost-beast`, `boost-iostreams`
- `cryptopp` (Crypto++)
- `zlib`
- `sentry-native`

## 💻 Core Technologies

- **Languages**: Python 3.13.7, C++17, JavaScript
- **C++ Libraries**: Crypto++ (crypto), Boost.Asio (networking), Sentry Native (error tracking)
- **Python Libraries**: Flask, Flask-SocketIO, Flet 0.28.3, PyCryptodome, psutil, watchdog, loguru, rich, python-bidi, wcwidth
- **GUI Frameworks**:
  - Flet 0.28.3 (FletV2 desktop GUI - Material Design 3)
  - HTML/CSS/JavaScript (Web UI)
- **Build System**: CMake + vcpkg (C++), setuptools (Python)
- **Database**: SQLite3
- **Real-time**: Flask-SocketIO (WebSocket)
- **Observability**: Sentry (Python + C++), loguru, rich

## 📁 Key Directories (UPDATED)

**CRITICAL**: Recent cleanup reorganized the project structure

```
├── Client/                    # C++ client source and build artifacts
│   ├── cpp/                   # C++ source files (main.cpp, client.cpp, etc.)
│   ├── deps/                  # Crypto wrappers (RSAWrapper, AESWrapper, crc.cpp)
│   └── Client-gui/            # Web UI assets (HTML/CSS/JavaScript)
├── api_server/                # Flask API server
│   ├── cyberbackup_api_server.py  # Main API server
│   └── real_backup_executor.py    # CRITICAL: C++ client subprocess manager
├── python_server/             # Python backup server
│   ├── server/
│   │   ├── server.py          # Main server logic with network listener
│   │   ├── database.py        # SQLite database manager
│   │   ├── protocol.py        # Binary protocol
│   │   ├── network_server.py  # TCP network layer
│   │   ├── request_handlers.py # Request processing
│   │   └── file_transfer.py   # File transfer logic
│   └── scripts/               # Utility scripts
├── FletV2/                    # Material Design 3 desktop GUI (CURRENT FOCUS)
│   ├── main.py                # Entry point (73K lines)
│   ├── theme.py               # Theming system (Material Design 3)
│   ├── server_adapter.py      # ServerBridge for Python server
│   ├── fletv2_gui_manager.py  # GUI lifecycle
│   ├── views/                 # UI views (dashboard, settings, clients, files, etc.)
│   ├── utils/                 # UI utilities and components
│   └── components/            # Reusable UI components
├── Shared/                    # Shared utilities (REORGANIZED)
│   ├── filesystem/            # UTF-8, file ops, path utils, streaming
│   │   ├── utf8_solution.py   # CRITICAL: UTF-8 subprocess/console handling
│   │   ├── file_lifecycle.py  # SynchronizedFileManager
│   │   └── streaming_file_utils.py
│   ├── logging/               # Logging, error handling, output
│   │   ├── logging_utils.py
│   │   ├── enhanced_output.py
│   │   └── error_handler.py
│   ├── monitoring/            # Performance, process, file monitoring
│   │   ├── unified_monitor.py # UnifiedFileMonitor
│   │   └── process_monitor.py
│   ├── config/                # Configuration management
│   │   └── unified_config.py  # CRITICAL: Unified config system
│   └── validation/            # Validation utilities
│       └── client_validation.py
├── scripts/                   # Automation and build scripts
│   └── one_click_build_and_run.py  # Complete system launcher
├── config/                    # Centralized JSON configuration files
│   ├── config.json            # Main configuration
│   ├── development.json       # Development overrides
│   └── database_config.py     # Database configuration
├── data/                      # UPDATED: Runtime data (REORGANIZED)
│   ├── received_files/        # Received backup files
│   ├── database/              # Database files (defensive.db, backups)
│   ├── keys/                  # RSA key storage
│   ├── security/              # Security-related data
│   └── transfer.info          # Active transfer configuration
├── logs/                      # Application log files
├── tests/                     # Test suite
├── docs/                      # Documentation
├── AI-CONTEXT-IMPORTANT/      # CRITICAL: AI guidance, rules, and design docs
├── build/                     # C++ build artifacts
├── vcpkg/                     # vcpkg package manager
├── CMakeLists.txt             # C++ build configuration
├── requirements.txt           # Python dependencies (root)
└── vcpkg.json                 # C++ dependencies
```

**IMPORTANT PATH CHANGES**:

- ❌ `Database/` → ✅ `data/database/`
- ❌ `Shared/utils/` → ✅ `Shared/filesystem/`, `Shared/logging/`, `Shared/monitoring/`, `Shared/config/`

## ⚙️ Development Conventions

### Unified Configuration Management

**CRITICAL**: All configuration is managed through `Shared/config/unified_config.py`

```python
# Modern approach - unified configuration
from Shared.config.unified_config import get_config

server_host = get_config('server.host', '127.0.0.1')
server_port = get_config('server.port', 1256)
api_port = get_config('api.port', 9090)
storage_dir = get_config('server.file_storage_dir', 'data/storage')
```

**Configuration precedence** (highest to lowest):
1. Environment variables (`BACKUP_SERVER_HOST`, `BACKUP_SERVER_PORT`, etc.)
2. JSON configuration files (`config/config.json`, `config/development.json`)
3. Legacy `.info` files (`transfer.info`, `port.info`)
4. Default values

### UTF-8 Support (CRITICAL)

**ALWAYS** import `utf8_solution` in any file that handles subprocess execution or console I/O:

```python
# CRITICAL: Import early for UTF-8 subprocess/console support
from Shared.filesystem.utf8_solution import Popen_utf8, safe_print, get_env

# For subprocess execution
process = Popen_utf8(
    [exe_path, "--batch"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=working_dir
)

# For console output with UTF-8
safe_print("✅ Backup completed!")

# For environment with UTF-8 encoding
env = get_env()
```

### Subprocess Management (CRITICAL)

When spawning the C++ client from Python, follow these **CRITICAL** patterns:

```python
# 1. ALWAYS use --batch flag to prevent interactive prompts
command = [client_exe, "--batch"]

# 2. ALWAYS set correct working directory (where transfer.info is)
cwd = os.path.dirname(client_exe)  # Usually build/Release/

# 3. ALWAYS use Popen_utf8 for proper encoding
from Shared.filesystem.utf8_solution import Popen_utf8
process = Popen_utf8(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=cwd  # CRITICAL: Must be where transfer.info is located
)

# 4. ALWAYS use adaptive timeout based on file size
timeout = calculate_adaptive_timeout(file_size_mb)

# 5. ALWAYS handle subprocess lifecycle properly
# See api_server/real_backup_executor.py for reference implementation
```

### transfer.info Format (CRITICAL)

The C++ client expects `transfer.info` in **exact 3-line format**:

```
# Line 1: Server address and port (colon-separated)
127.0.0.1:1256

# Line 2: Username
testuser

# Line 3: Absolute file path to backup
C:\path\to\file.txt
```

**Generation pattern**:
```python
def generate_transfer_info(server_ip, server_port, username, file_path):
    # ALWAYS use absolute path
    absolute_file_path = os.path.abspath(file_path)
    content = f"{server_ip}:{server_port}\n{username}\n{absolute_file_path}\n"

    with open("transfer.info", 'w', encoding='utf-8') as f:
        f.write(content)
```

### File Transfer Verification (CRITICAL)

**ALWAYS** verify file transfers by checking actual files in `data/storage/`:

```python
# Use UnifiedFileMonitor for verification
from Shared.monitoring.unified_monitor import UnifiedFileMonitor

monitor = UnifiedFileMonitor("data/storage")
monitor.start_monitoring()

# Register job with expected file characteristics
monitor.register_job(
    filename=os.path.basename(file_path),
    job_id=f"backup_{username}_{filename}",
    expected_size=os.path.getsize(file_path),
    expected_hash=calculate_file_hash_streaming(file_path, "sha256"),
    completion_callback=on_complete,
    failure_callback=on_failure
)

# Wait for verification
job_completed.wait(timeout=30)
```

### FletV2 Design Principles

**Framework Harmony**:
- Favor Flet's built-in features over custom solutions
- Use native theming via `ft.Theme` and color constants

**Modular Views**:
```python
def create_dashboard_view(page: ft.Page) -> ft.Control:
    """View-creation function returning ft.Control"""
    return ft.Container(
        content=ft.Column([...]),
        # Use TOKENS for colors
        bgcolor=TOKENS['surface'],
    )
```

**Theming**:
```python
# Import comprehensive theming
from FletV2.theme import TOKENS, get_theme, apply_theme

# Apply theme to page
apply_theme(page, theme_name="Teal", dark_mode=True)

# Use TOKENS for colors
ft.Container(bgcolor=TOKENS['surface'])
```

**ServerBridge**:
```python
# Abstract backend communication
from FletV2.server_adapter import ServerBridge

bridge = ServerBridge(server_instance)
clients = await bridge.get_all_clients()
```

### Async Task Management in Flet (CRITICAL)

```python
# Pattern 1: Simple async method calls
# ❌ INCORRECT - Calling the coroutine instead of passing it
self.page.run_task(self.action_handlers.clear_logs())

# ✅ CORRECT - Pass the coroutine function itself
self.page.run_task(self.action_handlers.clear_logs)

# Pattern 2: Parameterized async method calls
# ❌ INCORRECT - Calling coroutine with parameters
self.page.run_task(self.export_logs(filter_level, search_query))

# ✅ CORRECT - Create wrapper function
async def export_logs_wrapper():
    await self.export_logs(filter_level, search_query)
self.page.run_task(export_logs_wrapper)
```

### Logging & Observability

The project uses **dual logging** (console + file) with enhanced output:

```python
# Import enhanced logging
from Shared.logging.logging_utils import setup_logging, get_logger
from Shared.logging.enhanced_output import enhance_existing_logger

# Setup logging
setup_logging(
    log_file="logs/app.log",
    log_level="INFO",
    component_name="MyComponent"
)

logger = get_logger(__name__)
enhanced_logger = enhance_existing_logger(logger)

# Use enhanced logging with emojis and colors
enhanced_logger.success("✅ Operation completed")
enhanced_logger.error("❌ Operation failed")
enhanced_logger.warning("⚠️ Warning message")
```

**Sentry Integration**:
```python
from Shared.sentry_config import init_sentry

init_sentry(
    dsn=os.getenv("SENTRY_DSN"),
    environment="production",
    traces_sample_rate=0.1
)
```

## 🛠 Critical Patterns & Pitfalls

### ✅ DO: Proper C++ Client Subprocess Execution

```python
from Shared.filesystem.utf8_solution import Popen_utf8
import os

# 1. Locate executable
client_exe = "build/Release/EncryptedBackupClient.exe"

# 2. Generate transfer.info in correct location
client_dir = os.path.dirname(os.path.abspath(client_exe))
transfer_info_path = os.path.join(client_dir, "transfer.info")
# ... write transfer.info content ...

# 3. Execute with --batch flag and correct cwd
process = Popen_utf8(
    [client_exe, "--batch"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=client_dir  # MUST be where transfer.info is
)

# 4. Use adaptive timeout
timeout = 30 + (file_size_mb * 2)  # Base + size-based
stdout, stderr = process.communicate(timeout=timeout)
```

### ❌ DON'T: Common Mistakes

1. **Running C++ client without `--batch` flag** → Hangs waiting for interactive input
2. **Wrong working directory** → Client can't find `transfer.info`
3. **Relative file paths in transfer.info** → Client fails to locate files
4. **Not using `Popen_utf8`** → Encoding errors with non-ASCII characters
5. **Hardcoded timeouts** → Large files time out
6. **Not verifying file transfer** → Silent failures
7. **Importing `Shared.utils.utf8_solution`** → Module not found (use `Shared.filesystem.utf8_solution`)
8. **Referencing `received_files/`** → Use `data/storage/` instead

### File Lifecycle Management

Use `SynchronizedFileManager` for managed temporary files:

```python
from Shared.filesystem.file_lifecycle import SynchronizedFileManager

file_manager = SynchronizedFileManager(temp_dir)

# Create managed file
file_id, managed_path = file_manager.create_managed_file(
    "transfer.info",
    content
)

# Mark file as in use by subprocess
file_manager.mark_in_subprocess_use(file_id)

# Release when subprocess completes
file_manager.release_subprocess_use(file_id)

# Safe cleanup (waits for subprocess)
file_manager.safe_cleanup(file_id, wait_timeout=30.0)
```

## 📦 Dependency Management

**Python**:
- Root: `requirements.txt` (core dependencies)
- FletV2: `FletV2/requirements.txt` (Flet-specific)

**C++**:
- `vcpkg.json` (Crypto++, Boost, Sentry)
- CMake toolchain: `vcpkg/scripts/buildsystems/vcpkg.cmake`

## 🧪 Testing

**Python Tests**:
```bash
pytest tests/
```

**Integration Tests**:
```bash
python tests/integration/run_integration_tests.py
```

**C++ Client Testing**:
```bash
# Manual test with transfer.info
cd build/Release
# Create transfer.info
.\EncryptedBackupClient.exe
```

## 🐛 Troubleshooting

### C++ Client Hangs
- ✅ Add `--batch` flag
- ✅ Check `transfer.info` exists in working directory
- ✅ Verify file paths are absolute

### UTF-8 Encoding Errors
- ✅ Import `Shared.filesystem.utf8_solution` early
- ✅ Use `Popen_utf8` for subprocesses
- ✅ Use `safe_print` for console output

### File Transfer Failures
- ✅ Check Python server is running on port 1256
- ✅ Verify network listener started: "Network server started - ready for client connections"
- ✅ Check actual files in `data/storage/` directory
- ✅ Use `UnifiedFileMonitor` for verification

### Import Errors After Reorganization
- ❌ `from Shared.utils.utf8_solution` → ✅ `from Shared.filesystem.utf8_solution`
- ❌ `from Shared.utils.unified_config` → ✅ `from Shared.config.unified_config`
- ❌ `from Shared.utils.enhanced_output` → ✅ `from Shared.logging.enhanced_output`

## 📋 AI Context Files & Global Rules

The project includes multiple AI-specific context files tailored for different AI coding assistants:

- **`GEMINI.md`** (this file) - Google Gemini/Antigravity IDE context
- **`CLAUDE.md`** - Anthropic Claude context with historical decisions
- **`AGENTS.md`** - Multi-agent coordination and workflow patterns
- **`QWEN.md`** - Qwen model-specific context
- **`copilot-instructions.md`** - GitHub Copilot instructions

**CRITICAL**: These files contain AI-specific guidance, architectural decisions, and development conventions that should be consulted when making significant changes.

### Available System Tools

The development environment includes powerful CLI tools for code analysis and refactoring:

**Search & Analysis**:
- `ripgrep` (rg) v14.1.0 - Ultra-fast regex search
- `fd` v10.3.0 - Fast file finder
- `fzf` v0.67.0 - Fuzzy finder
- `tokei` v12.1.2 - Code statistics (LOC counter)
- `ast-grep` (sg) v0.40.0 - AST-based code search/refactoring
- `semgrep` v1.140.0 - Semantic code analysis and SAST

**File Operations**:
- `bat` v0.26.0 - Syntax-highlighted file viewer
- `eza` v0.23.4 - Modern ls replacement
- `sd` v1.0.0 - Intuitive find & replace

**Data Processing**:
- `jq` v1.8.1 - JSON processor
- `yq` v4.48.2 - YAML/TOML/XML processor

**Python Tools** (3.13.7):
- `ruff` v0.14.1 - Fast linter/formatter
- `pyright` v1.1.407 - Static type checker
- `black` - Code formatter
- `uv` - Ultra-fast package installer

**Usage Examples**:
```bash
# Search for pattern across codebase
rg "from Shared" --type python

# Find files with pattern
fd "test_.*\.py$" tests/

# Code statistics
tokei

# AST-based refactoring
sg --pattern 'from Shared.utils.$X' --rewrite 'from Shared.filesystem.$X'

# Check Python code quality
ruff check .
pyright
```

## 🔗 Additional Resources

- **AI Guidance**: `AI-CONTEXT-IMPORTANT/` - Critical design decisions and fixes
- **FletV2 Docs**: `FletV2/docs/` - Component usage and patterns
- **README**: `README.md` - Quick start and architecture overview
- **Project Documentation**: `docs/` - Comprehensive project documentation