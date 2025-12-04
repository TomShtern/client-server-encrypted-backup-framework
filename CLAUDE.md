# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CyberBackup 3.0**: Encrypted file backup system with client-server architecture.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FletV2 Desktop GUI ──→ ServerBridge ──→ BackupServer (port 1256)       │
│  (Admin interface)       (Direct Python)        ↑                       │
│                                                 ├──← C++ Client         │
│  Web GUI (HTML/JS) ──→ Flask API (9090) ──→ C++ subprocess              │
│                                                 ↓                       │
│                                       SQLite defensive.db               │
└─────────────────────────────────────────────────────────────────────────┘
```

| Component            | Technology             | Port | Purpose                                       |
|----------------------|------------------------|------|-----------------------------------------------|
| Python Backup Server | Python 3.13            | 1256 | Binary protocol, file storage, encryption     |
| FletV2 Desktop GUI   | Flet 0.28.3            | -    | Admin interface via direct ServerBridge calls |
| Flask API Server     | Flask + Socket.IO      | 9090 | REST/WebSocket bridge for web GUI             |
| C++ Client           | C++17, Boost, Crypto++ | -    | Encrypted file uploads via binary protocol    |
| Web GUI              | Vanilla ES6, Socket.IO | -    | Browser interface for C++ client control      |

## Critical File Locations

**Server Core:**
- `python_server/server/server.py` - Main backup server (BackupServer class)
- `python_server/server/request_handlers.py` - Protocol message handlers
- `python_server/server/file_transfer.py` - Multi-packet transfer management
- `python_server/server/database.py` - SQLite with connection pooling
- `python_server/server/protocol.py` - Binary protocol definitions

**FletV2 GUI:**
- `FletV2/main.py` - Desktop GUI entry point (FletV2App class)
- `FletV2/server_adapter.py` - ServerBridge for direct server calls
- `FletV2/scripts/start_with_server.py` - Launcher with integrated server

**API & Web:**
- `api_server/cyberbackup_api_server.py` - Flask API server
- `api_server/web_ui/index.html` - Web GUI (production)
- `api_server/web_ui/js/app.js` - Web GUI main application

**C++ Client:**
- `Client/cpp/main.cpp` - Client entry point
- `Client/cpp/client.cpp` - Protocol implementation
- `Client/deps/RSAWrapper.cpp` - RSA-1024 encryption
- `Client/deps/AESWrapper.cpp` - AES-256-CBC encryption

**Shared Utilities:**
- `Shared/config/unified_config.py` - Configuration manager (MUST USE)
- `Shared/filesystem/memory_efficient_file_transfer.py` - Bounded memory transfers
- `Shared/filesystem/utf8_solution.py` - UTF-8 bootstrap for Windows
- `Shared/validation/validation_utils.py` - Centralized validators
- `Shared/crc.py` - CRC32 implementation (POSIX-compatible)

---

## Non-Negotiable Rules

### 1. UTF-8 Bootstrap First
**First import** in entry files (`FletV2/main.py`, `python_server/server/server.py`, `api_server/cyberbackup_api_server.py`):
```python
import Shared.filesystem.utf8_solution  # noqa: F401 - MUST BE FIRST
```
**Symptom if missing**: `UnicodeEncodeError` on Windows, GUI corruption with non-ASCII.

### 2. Configuration Access
```python
# ✅ ALWAYS use unified config
from Shared.config.unified_config import load_unified_config
config = load_unified_config()
port = config.server.port

# ❌ NEVER read JSON directly
with open('config.json') as f:  # WRONG!
    config = json.load(f)
```
**Precedence**: Environment variables → `config.local.json` → `config/config.json`

### 3. Async/Sync in Flet (99% of UI Freezes)
```python
# ❌ WRONG - Freezes UI permanently
async def load_data(self):
    clients = self.server_bridge.get_clients()  # BLOCKS EVENT LOOP!

# ✅ CORRECT - Use executor
from FletV2.utils.async_helpers import run_sync_in_executor
async def load_data(self):
    clients = await run_sync_in_executor(self.server_bridge.get_clients)
```
**Rule**: ALL sync `server_bridge.*()` calls in async functions MUST use `run_sync_in_executor`.

### 4. Time Measurement
```python
# ❌ WRONG - System clock can change
start = time.time()

# ✅ CORRECT - Monotonic for durations
start = time.monotonic()
duration = time.monotonic() - start
```
**Rule**: Use `time.monotonic()` for ALL durations, timeouts, performance measurements.

### 5. Resource Cleanup
```python
# ✅ ALWAYS use context managers
with db_manager.get_connection() as conn:
    cursor.execute("SELECT * FROM clients")

# ✅ ALWAYS use finally for cleanup
temp_file = None
try:
    temp_file = create_temp_file()
    process(temp_file)
finally:
    if temp_file:
        temp_file.unlink()
```

### 6. Validation Before Use
```python
# ❌ WRONG - Use before validation
client_id = data[:16]
self.process_client(client_id)
if client_id == b'\x00' * 16:  # Too late!
    return

# ✅ CORRECT - Validate first
client_id = data[:16]
if client_id == b'\x00' * 16:
    return
self.process_client(client_id)
```

### 7. No Silent Failures
```python
# ❌ WRONG - Swallows errors
try:
    critical_operation()
except Exception:
    pass

# ✅ CORRECT - Log and handle
try:
    critical_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    cleanup_partial_state()
    raise
```

---

## Binary Protocol (Version 3)

**Request Frame** (Client → Server):
```
[16 bytes] Client UUID (binary)
[1 byte]   Protocol Version (3)
[2 bytes]  Opcode (little-endian)
[4 bytes]  Payload Length (little-endian)
[N bytes]  Payload Data
```

**Response Frame** (Server → Client):
```
[1 byte]   Protocol Version (3)
[2 bytes]  Opcode (little-endian)
[4 bytes]  Payload Length (little-endian)
[N bytes]  Payload Data
```

**Request Opcodes:**
| Code | Name                | Purpose                             |
|------|---------------------|-------------------------------------|
| 1025 | REQ_REGISTER        | Client registration with username   |
| 1026 | REQ_SEND_PUBLIC_KEY | RSA public key for AES key exchange |
| 1027 | REQ_RECONNECT       | Session reconnection                |
| 1028 | REQ_SEND_FILE       | Encrypted file packet               |
| 1029 | REQ_CRC_OK          | CRC verification passed             |
| 1030 | REQ_CRC_RETRY       | CRC failed, retry transfer          |
| 1031 | REQ_CRC_ABORT       | Abort transfer                      |

**Response Opcodes:**
| Code | Name                    | Purpose                            |
|------|-------------------------|------------------------------------|
| 1600 | RESP_REG_OK             | Registration success + client UUID |
| 1601 | RESP_REG_FAIL           | Registration failed                |
| 1602 | RESP_PUBKEY_AES_SENT    | RSA-encrypted AES key returned     |
| 1603 | RESP_FILE_CRC           | File CRC32 for verification        |
| 1604 | RESP_ACK                | Generic acknowledgment             |
| 1605 | RESP_RECONNECT_AES_SENT | Reconnection success               |
| 1606 | RESP_RECONNECT_FAIL     | Reconnection failed                |
| 1607 | RESP_ERROR              | Generic error                      |

**Critical Protocol Rules:**
1. All multi-byte integers are **little-endian**
2. UUID is exactly 16 bytes (binary, not hex string)
3. Max payload: 16MB + 1KB overhead
4. Protocol version is hardcoded (changes require C++ rebuild)

**Encryption:**
- RSA-1024 (PKCS1_OAEP, SHA256) for AES key exchange
- AES-256-CBC for file encryption
- CRC32 (POSIX cksum polynomial) for integrity

---

## FletV2 Desktop GUI Patterns

### The Flet Simplicity Principle
**Favor built-in features over custom solutions.** Before implementing complex systems:
- Can `ft.Theme`/`ft.ColorScheme` handle styling?
- Can `expand=True`, `ResponsiveRow`, `GridView` solve layout?
- Can `control.update()` avoid full `page.update()`?
- Does a standard Flet control already do 90%?

### View Creation Pattern
All views return: `(content, dispose_fn, setup_fn)`
```python
def create_my_view(server_bridge, page, state_manager=None, async_manager=None):
    subscriptions = []

    # Dispose - cleanup resources
    def dispose_fn():
        for sub in subscriptions:
            state_manager.unsubscribe(sub)

    # Setup - called AFTER view attached to page
    async def setup_fn():
        result = await run_sync_in_executor(server_bridge.get_data)
        if result.get('success'):
            update_ui(result['data'])

    content = ft.Column([...])
    return content, dispose_fn, setup_fn
```
**Critical**: `setup_fn()` executes AFTER view attachment (prevents "Control must be added to page first" errors).

### Update Strategy
```python
# ✅ BEST - Automatic batching
page.auto_update = True

# ✅ GOOD - Targeted update (10x faster than page.update)
control.value = new_value
control.update()

# ⚠️ NECESSARY ONLY - For dialogs, overlays, theme changes
page.update()

# ❌ NEVER - Updates in loops
for i in range(100):
    page.add(ft.Text(str(i)))
    page.update()  # 100 WebSocket messages!
```

### Flet 0.28.3 Limitations
| Invalid API                                            | Correct Alternative                         |
|--------------------------------------------------------|---------------------------------------------|
| `ft.UserControl`                                       | Functions returning controls                |
| `ft.Expanded()`                                        | `expand=True` property                      |
| `ft.Colors.BACKGROUND`                                 | `ft.Colors.SURFACE`                         |
| `ft.Colors.SURFACE_VARIANT`                            | `ft.Colors.SURFACE` or `ft.Colors.GREY_100` |
| `ft.Positioned`                                        | `expand=True` on overlay stack layers       |
| `Dropdown(height=...)`                                 | Not supported                               |
| `ft.Text(selectable=True)` instead of `SelectableText` | ✅ Correct                                   |
| Icons: `SAVE_OUTLINED`                                 | Not `SAVE_AS_OUTLINE`                       |
| Icons: `DATASET`                                       | Not `DATABASE`                              |

### SQLite in Flet (Required)
```python
# ✅ REQUIRED - Flet runs on WebSocket architecture
conn = sqlite3.connect('app.db', check_same_thread=False)

# ❌ WRONG - Random "database is locked" errors
conn = sqlite3.connect('app.db')
```

---

## Web GUI Patterns (Vanilla ES6)

**Canonical file**: `api_server/web_ui/index.html` (production-ready)

### Architecture
- No frameworks, no build tools - pure ES6 modules
- Central state via `StateStore` with batched RAF updates
- DOM elements via `dom` registry (never direct `querySelector`)
- Error boundaries wrap ALL async operations

### Core Patterns
```javascript
// StateStore (reactive state)
this.state = new StateStore({ connected: false, progress: 0 });
this.state.subscribe((snapshot) => this.#render(snapshot));
this.state.update({ progress: 45 });

// Error Boundary (mandatory for async)
try {
  await operation();
} catch (error) {
  ErrorBoundary.handle(error, 'Operation Name', recoveryFn);
}

// DOM Registry (never querySelector)
import { dom } from './utils/dom.js';
dom.progressText.textContent = `${progress}%`;
```

### API Integration
- REST: `POST /api/connect`, `POST /api/start_backup`, `GET /api/status?job_id=X`
- WebSocket: `connect`, `disconnect`, `progress_update`, `status`, `file_receipt`
- Polling: 5s (active job), 15s (idle)

---

## C++ Client

### Build Commands
```bash
# CMake with vcpkg
cmake -B build -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release

# Using presets
cmake --preset default
cmake --build --preset default
```

### vcpkg Dependencies
`boost-asio`, `boost-beast`, `cryptopp`, `sentry-native`, `spdlog`, `nlohmann-json`, `zlib`

### Subprocess Pattern (Python)
```python
# ✅ CORRECT - Non-interactive mode
process = subprocess.Popen(
    ["EncryptedBackupClient.exe", "--batch"],
    cwd=client_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# ❌ WRONG - Will hang waiting for input
process = subprocess.Popen(["EncryptedBackupClient.exe"], ...)
```

### Key Classes
- `Client` - Main orchestrator (connect, transfer, encrypt)
- `ProperDynamicBufferManager` - Adaptive I/O performance
- `RSAPrivateWrapper` - RSA-1024 key management
- `AESWrapper` - AES-256-CBC encryption

---

## Database Schema

```sql
-- clients table
CREATE TABLE clients (
    ID BLOB(16) PRIMARY KEY,          -- 16-byte UUID
    Name VARCHAR(255) UNIQUE NOT NULL,
    PublicKey BLOB(160),              -- RSA-1024 public key
    LastSeen TEXT NOT NULL,           -- ISO8601 timestamp
    AESKey BLOB(32)                   -- Session AES-256 key
);

-- files table
CREATE TABLE files (
    ID BLOB(16) PRIMARY KEY,
    FileName VARCHAR(255) NOT NULL,
    PathName VARCHAR(255) NOT NULL,
    Verified BOOLEAN DEFAULT 0,
    FileSize INTEGER,
    ModificationDate TEXT,
    CRC INTEGER,
    ClientID BLOB(16) NOT NULL,
    FOREIGN KEY (ClientID) REFERENCES clients(ID) ON DELETE CASCADE
);
```

### Database Pattern
```python
# Context manager pattern (connection auto-returned to pool)
with db_manager.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    results = cursor.fetchall()

# Parallel queries for performance
async def load_data(self):
    loop = asyncio.get_running_loop()
    clients, files = await asyncio.gather(
        loop.run_in_executor(None, bridge.get_clients),
        loop.run_in_executor(None, bridge.get_files)
    )
```

---

## Critical Anti-Patterns

### Race Conditions
```python
# ❌ WRONG - Check-then-act without lock
if client_id not in self.clients:
    self.clients[client_id] = Client(...)

# ✅ CORRECT - Atomic with lock
with self.lock:
    if client_id not in self.clients:
        self.clients[client_id] = Client(...)
```

### Resource Leaks (Fixed in This Codebase)
1. Database connections not returned to pool
2. File handles not closed in exception paths
3. Task references not removed from tracking dicts
4. Temporary files not deleted on error

**Solution**: Context managers + finally blocks everywhere

### God Classes
- Keep files under 500 lines (1000 max for views)
- Keep functions under 100 lines
- One responsibility per module

---

## Development Workflow

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Launch GUI + Server (recommended)
python FletV2/scripts/start_with_server.py

# One-click build and run (C++ client + all services)
python scripts/one_click_build_and_run.py

# Development with hot reload
flet run -r FletV2/main.py
```

### Code Quality
```bash
# Lint and format
ruff check FletV2 Shared python_server api_server
ruff format FletV2 Shared python_server api_server

# Type checking
pyright

# Run tests
pytest tests/
```

### Key Scripts
| Script                                                 | Purpose                               |
|--------------------------------------------------------|---------------------------------------|
| `scripts/one_click_build_and_run.py`                   | Build C++ client, launch all services |
| `scripts/validate_database.py`                         | Database integrity check              |
| `scripts/migrate_database.py`                          | Consolidate DBs to canonical location |
| `scripts/testing/master_test_suite.py`                 | Comprehensive test suite              |
| `scripts/security/key-generation/generate_rsa_keys.py` | RSA key generation                    |

### Common Commands
```bash
# Database
python scripts/migrate_database.py
python scripts/validate_database.py

# C++ Build
cmake -B build -DCMAKE_TOOLCHAIN_FILE="vcpkg/scripts/buildsystems/vcpkg.cmake"
cmake --build build --config Release

# Single test
pytest tests/test_protocol.py::test_specific_function -v

# Find unused code
ruff check --select F401,F841 .

# Kill stale processes
taskkill /f /im python.exe
```

---

## Environment Variables

| Variable                               | Purpose                                   |
|----------------------------------------|-------------------------------------------|
| `PYTHONNOUSERSITE=1`                   | Prevent user site-packages conflicts      |
| `CYBERBACKUP_DISABLE_INTEGRATED_GUI=1` | Use FletV2 instead of embedded server GUI |
| `FLET_V2_DEBUG=1`                      | Verbose GUI logging                       |
| `BACKUP_SERVER_PORT`                   | Override server port                      |
| `BACKUP_API_PORT`                      | Override API port                         |
| `REAL_SERVER_URL`                      | API base URL for real server mode         |

---

## Logging Standards

| Level    | Usage                                                       |
|----------|-------------------------------------------------------------|
| DEBUG    | Protocol details, packet parsing, reassembly                |
| INFO     | Client connect/disconnect, file transfers, startup/shutdown |
| WARNING  | Recoverable errors, validation failures, retries            |
| ERROR    | Failed operations, database errors, crypto failures         |
| CRITICAL | System failures, startup failures, security violations      |

```python
# Use structured logging (never print())
logger.info(f"Client {client_id.hex()} connected from {address}")
logger.error(f"Database operation failed: {e}", exc_info=True)
```

---

## Troubleshooting

| Issue                           | Solution                                                       |
|---------------------------------|----------------------------------------------------------------|
| UI freeze                       | Check for sync calls in async without `run_sync_in_executor`   |
| Memory leak                     | Check transfer manager stats, ensure cleanup in finally blocks |
| Database lock                   | Use connection pooling context manager pattern                 |
| Config not loading              | Check precedence: env vars > config.local.json > config.json   |
| C++ client can't connect        | Verify `server_instance.start()` called, port 1256 open        |
| Race condition                  | Add locking around check-then-act patterns                     |
| UnicodeEncodeError              | Ensure UTF-8 bootstrap is first import                         |
| "Control must be added to page" | setup_fn must run AFTER view attached                          |

---

## Architecture Decisions

### Why Unified Config Manager?
**Problem**: 4 config sources with conflicts. **Solution**: Single manager with clear precedence.

### Why Memory-Efficient Transfer Manager?
**Problem**: Unbounded memory growth. **Solution**: LRU eviction, weak references, automatic cleanup (30min timeout).

### Why `time.monotonic()`?
**Problem**: System clock changes caused negative durations. **Solution**: Monotonic clock.

### Why RLock Not Lock?
**Problem**: Deadlocks in recursive calls. **Solution**: Reentrant locks.

---

## Pre-Commit Checklist

- [ ] No sync calls in async functions without `run_sync_in_executor`
- [ ] Database connections use context managers
- [ ] All external calls wrapped in try-except with logging
- [ ] Validation before processing untrusted input
- [ ] Resources cleaned up in finally blocks
- [ ] Use `time.monotonic()` for durations
- [ ] Use unified config manager for all config access
- [ ] No `page.update()` where `control.update()` works
- [ ] UTF-8 bootstrap is first import in entry files

---

**Version**: CyberBackup 3.0
**Status**: Production-ready Python stack, Flask API server active

**Key Documents**:
- `docs/reports/CODE_ISSUES_AND_FIXES.md` - 42 fixed issues
- `docs/reference/flet/` - Flet 0.28.3 documentation
- `.github/copilot-instructions.md` - Detailed patterns and ServerBridge API
- `FletV2/docs/CLAUDE.md` - FletV2-specific patterns
- `api_server/web_ui/CLAUDE.md` - Web GUI patterns
