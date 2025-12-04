# CyberBackup 3.0 – AI Agent Guide

> Comprehensive guide for AI coding agents. Architecture, critical patterns, and conventions.

| Component |   Version  |              Notes                |
|-----------|------------|-----------------------------------|
| Python    | 3.13.7     | Required for type hints           |
| Flet      | 0.28.3     | See limitations table             |
| Protocol  | 3          | Hardcoded in client/server        |
| SQLite    | 3.x        | File-level locking                |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  FletV2 Desktop ──→ ServerBridge ──→ BackupServer (port 1256)       │
│  (Admin GUI)         (Direct Python)         ↑                      │
│                                              ├──← C++ Client        │
│  Web GUI ──→ Flask API (9090) ──→ C++ subprocess                    │
│                                              ↓                      │
│                                    SQLite defensive.db              │
└─────────────────────────────────────────────────────────────────────┘
```

| Component        | Port  | Purpose                              |
|------------------|-------|--------------------------------------|
| FletV2 Desktop   |   -   | Admin GUI via ServerBridge           |
| BackupServer     | 1256  | TCP binary protocol, file storage    |
| Flask API        | 9090  | REST bridge for web GUI              |
| C++ Client       |   -   | Encrypted file transfers             |

---

## 🚨 Critical Rules

### 1. Network Listener Must Start

**MUST call `server_instance.start()`** in `FletV2/start_with_server.py`:

```python
server_instance = BackupServer(config)
server_instance.start()  # Without this, C++ clients cannot connect!
```

**Symptom if missing**: GUI works but no files received from C++ clients.

### 2. UTF-8 Bootstrap First

**First import** in entry-point files:

```python
# FletV2/main.py, python_server/server/server.py, api_server/cyberbackup_api_server.py
from Shared.filesystem.utf8_solution import configure_utf8
configure_utf8()
# Then other imports...
```

**Symptom if missing**: `UnicodeEncodeError` on Windows console.

### 3. Async/Sync Boundary (99% of GUI Freezes)

ServerBridge methods are sync. Calling from async **blocks the event loop**.

```python
from FletV2.utils.async_helpers import run_sync_in_executor

# ❌ WRONG - Freezes UI
async def load_data(self):
    result = self.server_bridge.get_clients()

# ✅ CORRECT - No arguments
async def load_data(self):
    result = await run_sync_in_executor(self.server_bridge.get_clients)

# ✅ CORRECT - With arguments
async def load_client(self, client_id: str):
    result = await run_sync_in_executor(
        self.server_bridge.get_client_by_id, client_id
    )
```

**Real Bug Example (Dashboard Deadlock, October 2024)**:
```python
# BEFORE - Caused deadlock
async def check_status(self):
    if server_bridge.is_connected():  # BLOCKS EVENT LOOP
        await self.refresh()

# AFTER - Fixed
async def check_status(self):
    connected = await run_sync_in_executor(server_bridge.is_connected)
    if connected:
        await self.refresh()
```

### 4. Use time.monotonic() for Durations

```python
start = time.monotonic()  # ✅ Immune to system clock changes
duration = time.monotonic() - start
# Never use time.time() - can go negative if clock adjusts!
```

### 5. Protocol Version Lock

Protocol v3 is hardcoded. Changes require updating:
- `python_server/server/protocol.py` (REQ_*/RESP_* codes)
- `Client/cpp/include/ProtocolEnums.h`
- Rebuild C++ client, update `tests/test_protocol.py`

### 6. C++ Client Subprocess

Always use `--batch` flag to prevent interactive hangs:

```python
subprocess.Popen(["EncryptedBackupClient.exe", "--batch"], ...)
```

### 7. Resource Cleanup

Always use context managers and `finally` blocks:

```python
temp_file = None
try:
    temp_file = create_temp_file()
    process(temp_file)
finally:
    if temp_file and temp_file.exists():
        temp_file.unlink()
```

---

## FletV2 Patterns

### View Architecture (5-Section Pattern)

**ALL views MUST follow this structure**:

```python
def create_my_view(server_bridge, page, state_manager=None):
    """
    Standard view creation pattern.
    Returns: tuple (content_control, dispose_fn, setup_fn)
    """
    # ═══════════════════════════════════════════════════════════════
    # SECTION 1: Local State & Refs
    # ═══════════════════════════════════════════════════════════════
    data_ref = ft.Ref[ft.Column]()
    loading_ref = ft.Ref[ft.ProgressRing]()
    subscriptions = []
    cached_data = []

    # ═══════════════════════════════════════════════════════════════
    # SECTION 2: Data Fetching (async with executor)
    # ═══════════════════════════════════════════════════════════════
    async def load_data():
        loading_ref.current.visible = True
        loading_ref.current.update()

        result = await run_sync_in_executor(server_bridge.get_data)

        if result['success']:
            cached_data.clear()
            cached_data.extend(result['data'])
            render_data()
        else:
            show_error(page, result['error'])

        loading_ref.current.visible = False
        loading_ref.current.update()

    def render_data():
        data_ref.current.controls = [build_card(item) for item in cached_data]
        data_ref.current.update()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 3: Event Handlers
    # ═══════════════════════════════════════════════════════════════
    def on_refresh(e):
        page.run_task(load_data)

    def on_item_click(item_id):
        def handler(e):
            page.run_task(lambda: handle_item(item_id))
        return handler

    # ═══════════════════════════════════════════════════════════════
    # SECTION 4: Dispose Function (cleanup)
    # ═══════════════════════════════════════════════════════════════
    def dispose_fn():
        for sub in subscriptions:
            state_manager.unsubscribe(sub)
        if hasattr(page, 'overlay') and page.overlay:
            page.overlay.clear()
        cached_data.clear()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 5: Setup Function (runs AFTER view attached to page)
    # ═══════════════════════════════════════════════════════════════
    def setup_fn():
        page.run_task(load_data)
        if state_manager:
            sub = state_manager.subscribe('data_changed', lambda: page.run_task(load_data))
            subscriptions.append(sub)

    # ═══════════════════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════════════════
    content = ft.Column(
        ref=data_ref,
        controls=[ft.ProgressRing(ref=loading_ref, visible=False)],
        expand=True,
    )

    return content, dispose_fn, setup_fn
```

**CRITICAL**: `setup_fn()` runs AFTER view is attached to page. Calling `page.run_task()` before attachment causes "Control must be added to the page first" error.

### UI Update Hierarchy

```python
my_text.value = "Updated"; my_text.update()  # ✅ Targeted (fastest, ~1ms)
my_column.controls.append(item); my_column.update()  # ✅ Container
page.update()  # ⚠️ Only for themes/dialogs/overlays (slowest, 16ms+)

# ❌ NEVER - Loop with page.update() causes frame drops
for item in items:
    container.controls.append(item)
    page.update()  # DON'T!

# ✅ CORRECT - Batch then update once
container.controls.extend([create_item(i) for i in items])
container.update()
```

### Flet 0.28.3 Limitations

| Missing/Wrong                | Workaround                       |
|------------------------------|----------------------------------|
| `ft.SelectableText`          | `ft.Text(selectable=True)`       |
| `ft.Colors.SURFACE_VARIANT`  | `ft.Colors.SURFACE`              |
| `ft.Positioned`              | `ft.Container` with alignment    |
| `Dropdown(height=...)`       | Not supported                    |
| `ft.Icons.SAVE_AS_OUTLINE`   | `ft.Icons.SAVE_OUTLINED`         |
| `ft.Icons.DATABASE`          | `ft.Icons.DATASET`               |

---

## ServerBridge API

### Response Contract

**ALL methods return this structure**:
```python
{"success": bool, "data": Any, "error": str | None}
```

### Response Handling Pattern

```python
async def load_clients(self):
    result = await run_sync_in_executor(self.server_bridge.get_all_clients_from_db)

    if result['success']:
        clients = result['data']
        self.render_clients(clients)
    else:
        self.show_error(f"Failed to load: {result['error']}")
```

### Core Methods

```python
# Clients
get_all_clients_from_db()      # List all clients
get_client_by_id(id: str)      # Single client
add_client(data: dict)         # Create client
delete_client(id: str)         # Delete client
update_client(id: str, data: dict)
disconnect_client(id: str)     # Force disconnect

# Files
get_files()                    # All files across all clients
get_client_files(id: str)      # Files for specific client
delete_file(id: str)
download_file(id: str)         # Returns bytes or Path
verify_file(id: str)           # CRC32 verification

# Database
get_database_info()            # Schema, stats, size
get_table_data(table: str)     # Raw table data
update_row(table: str, id: str, data: dict)

# Server
get_server_status_async()      # Health, uptime, connections
get_system_status()            # CPU, memory, disk
test_connection()
start_server() / stop_server()
get_logs(offset: int, limit: int)
```

### Mock vs Real Mode

```python
if server_bridge.is_real():
    # Connected to BackupServer - operations persist
    result = server_bridge.delete_client(client_id)
else:
    # Mock mode - returns empty structures, NO persistence
    logger.warning("Running in mock mode")
```

---

## Database Patterns

### Always Use Context Managers

```python
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (id,))
    result = cursor.fetchone()
    # Connection auto-closes after block
```

### Retry for SQLite Locks

SQLite uses file-level locking. Use exponential backoff on locks:

```python
import sqlite3
import time

def execute_with_retry(query: str, params: tuple, max_attempts: int = 3):
    """Execute query with retry on database lock."""
    for attempt in range(max_attempts):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_attempts - 1:
                wait_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                time.sleep(wait_time)
                continue
            raise
    return None
```

### Thread Safety

Use `threading.RLock()` (not `Lock`) for check-then-act patterns:

```python
class ClientManager:
    def __init__(self):
        self._lock = threading.RLock()  # Allows same thread to re-acquire
        self.clients = {}

    def get_or_create(self, client_id: str):
        with self._lock:
            if client_id not in self.clients:
                self.clients[client_id] = Client(client_id)
            return self.clients[client_id]
```

### Schema Reference

```sql
CREATE TABLE clients (
    id TEXT PRIMARY KEY,           -- UUID as text
    client_id BLOB,                -- UUID as 16-byte blob (legacy)
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP,
    total_files INTEGER DEFAULT 0,
    total_bytes INTEGER DEFAULT 0
);

CREATE TABLE files (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    path_hash TEXT,                -- SHA-256 of original path
    original_name TEXT,
    size_bytes INTEGER,
    checksum_crc32 INTEGER,
    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transfers (
    id TEXT PRIMARY KEY,
    file_id TEXT REFERENCES files(id),
    status TEXT CHECK(status IN ('pending','in_progress','completed','failed')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    failure_reason TEXT
);
```

---

## Binary Protocol (v3)

### Frame Structure

```
│ UUID (16) │ Version (1) │ Opcode (2, LE) │ Size (4, LE) │ Payload │ CRC32 │
```

- All multi-byte integers are **little-endian**
- UUID is 16 bytes binary (not string)
- CRC32 uses `cksum` algorithm that is the same as in Lynox.

### Security

- **Key Exchange**: RSA-1024, OAEP-SHA256
- **File Encryption**: AES-256-CBC, zero IV
- **Integrity**: CRC32 on entire frame

### transfer.info Format

Exactly 3 lines, no blanks:
```
127.0.0.1:1256
username
C:\absolute\path\to\file.ext
```

---

## Memory-Efficient Transfers

```python
from Shared.filesystem.memory_efficient_file_transfer import get_transfer_manager

manager = get_transfer_manager()  # Singleton

# Create bounded transfer
manager.create_transfer(
    client_id=client_uuid,
    filename="backup.zip",
    total_packets=100,
    original_size=file_size
)

# Add packets (auto memory management)
for packet_num, chunk in enumerate(chunks, 1):
    success = manager.add_packet(client_id, filename, packet_num, chunk)
    if not success:
        logger.warning("Memory limit reached")
        break

# Monitor health
stats = manager.get_statistics()
# Returns: {active_transfers: int, current_memory_mb: float, ...}
```

**Defaults**: 10 concurrent transfers, 100MB/transfer, 30min timeout.

---

## Configuration

```python
from Shared.config.unified_config import get_config

config = get_config()
host = config.get('server.host', '127.0.0.1')
port = config.get('server.port', 1256)
db_path = config.get('database.path', 'data/database/defensive.db')
```

### Environment Variables

| Variable                               | Purpose                                 |
|----------------------------------------|-----------------------------------------|
| `PYTHONNOUSERSITE=1`                   | Prevent site-packages conflicts         |
| `CYBERBACKUP_DISABLE_INTEGRATED_GUI=1` | Use FletV2 instead of embedded GUI      |
| `FLET_V2_DEBUG=1`                      | Verbose GUI logging                     |
| `FLET_DASHBOARD_DEBUG=1`               | Dashboard logging (performance hit)     |
| `REAL_SERVER_URL`                      | API base URL (else mock mode)           |
| `BACKUP_SERVER_TOKEN`                  | Bearer token for API auth               |

---

## Common Code Generation Scenarios

### Adding a New View

1. Create file in `FletV2/views/my_view.py`
2. Use 5-Section Pattern (see above)
3. Register in `FletV2/main.py` navigation
4. Add route handling

### Adding a Database Query

```python
def get_active_clients():
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, last_seen
            FROM clients
            WHERE last_seen > datetime('now', '-7 days')
            ORDER BY last_seen DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
```

### Adding a Server Operation

```python
# In server_bridge.py or view
async def perform_operation(self, item_id: str):
    result = await run_sync_in_executor(
        self.server_bridge.some_method, item_id
    )
    if result['success']:
        return result['data']
    else:
        raise OperationError(result['error'])
```

---

## Key Files Reference

| File                                   | Purpose                           |
|----------------------------------------|-----------------------------------|
| `FletV2/main.py`                       | GUI entry point, navigation        |
| `FletV2/utils/server_bridge.py`        | All server communication           |
| `FletV2/utils/async_helpers.py`        | `run_sync_in_executor` lives here  |
| `FletV2/utils/state_manager.py`        | Event bus (subscribe/publish)      |
| `python_server/server/server.py`       | BackupServer main class            |
| `python_server/server/database.py`     | DatabaseManager, connection pool   |
| `python_server/server/protocol.py`     | Binary protocol constants          |
| `Shared/config/unified_config.py`      | Configuration management           |
| `Shared/filesystem/utf8_solution.py`   | UTF-8 bootstrap                    |
| `api_server/cyberbackup_api_server.py` | Flask API server                   |

---

## Debugging Guide

### GUI Freezes
1. Search for sync calls in async functions
2. Wrap with `run_sync_in_executor`

### Port 1256 Conflict
```powershell
taskkill /f /im python.exe
# Or find specific process:
netstat -ano | findstr :1256
taskkill /f /pid <PID>
```

### Mock Mode Confusion
Operations succeed but don't persist? Check:
```python
if not server_bridge.is_real():
    print("WARNING: Mock mode - no persistence!")
```

### C++ Client Not Connecting
1. ✅ `server_instance.start()` called?
2. ✅ Firewall allows port 1256?
3. ✅ `transfer.info` has exactly 3 lines?
4. ✅ Protocol version matches (both = 3)?

### Database Locked Errors
- Use retry with exponential backoff
- Check for unclosed connections
- Ensure context managers are used

---

## Code Quality

- **Files**: <500 lines (1000 max for views)
- **Functions**: <100 lines
- **Logging**: Use `logger`, never `print()`
- **Errors**: Return `{"success": bool, "data": ..., "error": ...}`
- **Validate first**: Check inputs before processing

```python
# ✅ Validate before use
client_id = data[:16]
if client_id == b'\x00' * 16:
    logger.warning("Invalid null client ID")
    return None
process_client(client_id)
```

---

## Testing

```bash
# Fast tests
pytest tests/test_protocol.py tests/test_comprehensive_database.py

# All tests
pytest tests/

# Lint
ruff check FletV2 Shared python_server api_server

# Type check
pyright
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│ Launch Full System:    python scripts/one_click_build_and_run.py    │
│ Launch FletV2+Server:  python FletV2/start_with_server.py           │
│ Launch API Server:     python api_server/cyberbackup_api_server.py  │
├─────────────────────────────────────────────────────────────────────┤
│ Ports: BackupServer=1256, Flask API=9090, Protocol=v3               │
├─────────────────────────────────────────────────────────────────────┤
│ CRITICAL: Always use run_sync_in_executor for sync calls in async!  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## VS Code Tasks

| Task                               | Purpose             |
|------------------------------------|---------------------|
| Run FletV2 App with Server (PS1)   | Launch full system  |
| Run Python Server                  | BackupServer only   |
| Lint/Format Python Code            | ruff check/format   |
| Client Web GUI + API Server        | Web GUI with API    |

---

## Pre-Commit Checklist

- [ ] Sync ServerBridge calls wrapped in `run_sync_in_executor`
- [ ] Database connections use context managers
- [ ] Durations use `time.monotonic()`
- [ ] Resources cleaned in `finally` blocks
- [ ] Input validated before processing
- [ ] No `page.update()` in loops
- [ ] No `print()` - use logger
- [ ] Files under 500 lines

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - Non-negotiable rules
- [AGENTS.md](../AGENTS.md) - Project overview
- [FletV2/docs/architecture_guide.md](../FletV2/docs/architecture_guide.md) - Full architecture
