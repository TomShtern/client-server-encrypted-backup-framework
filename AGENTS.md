# Client-Server Encrypted Backup Framework - AGENTS Documentation

## Build & Test Commands

### C++ Client (Windows)
```bash
.\build.bat                    # Release build
.\build.bat debug             # Debug build
.\build.bat clean             # Clean rebuild
.\build.bat ninja             # Fast Ninja release
cmake --preset release        # Configure release
cmake --build --preset release # Build release
```

### Python System
```bash
python scripts/one_click_build_and_run.py  # Full system launch
cd FletV2 && ../flet_venv/Scripts/python start_with_server.py  # Flet GUI + Server
python api_server/cyberbackup_api_server.py  # API Server only
```

### Lint & Test
```bash
ruff check FletV2 Shared python_server api_server  # Lint
ruff format FletV2 Shared python_server api_server  # Format
pyright                                              # Type check
pytest tests/test_protocol.py tests/test_comprehensive_database.py  # Fast tests
pytest tests/                                        # All tests
pytest tests/test_protocol.py::TestClass::test_method -v  # Single test
```

## Code Style Guidelines

### Python
- Line length: 110 chars
- Imports: stdlib > 3rd-party > local (isort order)
- Type hints: All public functions
- Naming: snake_case vars/fns, PascalCase classes
- Error handling: Return `{"success": bool, "data": Any, "error": str|None}`
- Validation: Input checks, no path traversal

### Critical Patterns (Incorporates Copilot/Cursor Rules)
- Async boundaries: `await run_sync_in_executor(sync_func)`
- Database: `with db.get_connection() as conn:`
- UTF-8: First import `Shared.filesystem.utf8_solution as _utf8_solution; _utf8_solution.ensure_initialized()`
- Timing: `time.monotonic()` only (no `time.time()`)
- Logging: `logger` everywhere (no `print()`)
- Flet UI: `control.update()` (targeted), avoid `page.update()` loops
- Subprocess/C++: Always `--batch` flag + correct `cwd`
- Themes: Use `TOKENS['primary']`, no hardcoded colors
- ServerBridge: For FletV2 direct server calls

### File Structure
- Max file: 500 lines (views: 1000)
- Func size: <100 lines
- Security: AES-256-CBC (zero IV), RSA-1024 OAEP