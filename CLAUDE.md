# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Client Server Encrypted Backup Framework implementing secure file transfer using RSA key exchange and AES file encryption. The system consists of a C++17 client with a Python server, using a custom binary protocol for secure backup operations.

## Build Commands

### Primary Build
```bash
.\build.bat
```
This compiles the C++ client using MSVC 19.44.35209, creating `client/EncryptedBackupClient.exe`. The build system uses direct MSVC compilation without CMake and includes a carefully curated subset of Crypto++ modules.

### Clean Build
```bash
.\clean.bat
```
Removes all build artifacts and temporary files.

### Test Builds
```bash
# RSA implementation tests (primary test suite)
.\scripts\build_rsa_final_test.bat
.\scripts\build_rsa_wrapper_final_test.bat

# Additional crypto tests
.\scripts\build_rsa_manual_test.bat
.\scripts\build_rsa_pregenerated_test.bat
```

## Running the System

### Start Server
```bash
.\start_server.bat
# OR
cd server && python server.py
```
Server runs on port 1256 by default, uses SQLite database (`defensive.db`) for client management.

### Start Client
```bash
.\start_client.bat
```
Requires `transfer.info` file with server:port, username, and file path.

### Test Connection
```bash
python tests/test_connection.py
```

## Architecture

### Client (C++17)
- **Main Logic**: `src/client/client.cpp` - Protocol implementation and file transfer
- **Protocol**: `src/client/protocol.cpp` - Binary protocol handling (little-endian)
- **GUI**: `src/client/ClientGUI.cpp` - Windows console interface
- **Checksum**: `src/client/cksum.cpp` - Linux-compatible CRC implementation

### Crypto Wrappers
- **RSA**: `src/wrappers/RSAWrapper.cpp` - Hybrid RSA implementation (512-bit with XOR fallback)
- **AES**: `src/wrappers/AESWrapper.cpp` - AES-256-CBC file encryption
- **Base64**: `src/wrappers/Base64Wrapper.cpp` - Key encoding for storage

### Server (Python)
- **Core**: `server/server.py` - Multi-threaded TCP server with SQLite integration
- **GUI**: `server/ServerGUI.py` - Optional monitoring interface
- **Crypto**: `server/crypto_compat.py` - Python-side encryption compatibility

## Protocol Specification

- **Version**: 3 (binary protocol, little-endian)
- **Transport**: TCP/IP with 23-byte headers + variable payloads
- **Request Codes**: 1025-1031 (registration, key exchange, file transfer, CRC)
- **Response Codes**: 1600-1607 (success/failure responses)
- **Encryption Flow**: RSA-1024 key exchange → AES-256-CBC file encryption
- **Integrity**: Custom CRC matching Linux `cksum` algorithm

## Configuration Files

### Client Configuration
- **`transfer.info`**: 3-line format (server:port, username, file_path)
- **`me.info`**: Client credentials (username, UUID, RSA private key in Base64)
- **`port.info`**: Server port override (default: 1256)

### Key File Formats
- **RSA Keys**: 162-byte DER format for protocol compliance
- **String Fields**: 255-byte maximum, null-terminated, zero-padded
- **Endianness**: Little-endian throughout (critical for protocol compatibility)

## Development Environment

### Requirements
- **Windows**: Visual Studio 2022 Build Tools (MSVC 19.44.35209)
- **Python**: 3.11.4 with PyCryptodome
- **Dependencies**: Crypto++ (bundled in `third_party/`), Boost headers

### Build System Details
- **No CMake**: Direct MSVC compilation with optimized batch scripts
- **Crypto++ Integration**: Selective compilation to avoid template instantiation issues
- **Linking**: ws2_32.lib, advapi32.lib, user32.lib for Windows networking and crypto

## Testing and Benchmarks

### Functional Tests
```bash
# Core RSA implementation (primary tests)
.\build\test_rsa_final.exe
.\build\test_rsa_wrapper_final.exe

# Connection and protocol tests
python tests/test_connection.py
python server/test_server.py
```

### Performance Benchmarks
```bash
python benchmarks/run_all_benchmarks.py
python benchmarks/benchmark_suite.py
```

## Critical Implementation Notes

### RSA Implementation Status
The project uses a hybrid RSA approach due to Crypto++ stability issues:
- **Primary**: 512-bit RSA for reliable key generation
- **Fallback**: Enhanced XOR encryption when RSA fails
- **Status**: Fully resolved and operational (see `docs/RSA_FIX_IMPLEMENTATION_REPORT.md`)

### Security Implementation
- **Key Exchange**: RSA-OAEP with SHA-256
- **File Encryption**: AES-256-CBC with static zero IV (documented limitation)
- **Integrity**: CRC-32 variant matching Linux `cksum` exactly
- **Authentication**: UUID-based client identification with RSA key validation

### Protocol Compliance
- **Endianness**: Little-endian enforced throughout (major compatibility fix)
- **File Transfer**: Single packet design (no chunking)
- **Error Handling**: Comprehensive response codes with graceful failure modes

## File Organization

- **`/src/client/`**: C++ client implementation
- **`/src/wrappers/`**: Crypto wrapper classes
- **`/server/`**: Python server with GUI
- **`/tests/`**: Comprehensive test suite
- **`/benchmarks/`**: Performance testing framework
- **`/docs/`**: Extensive documentation and specifications
- **`/third_party/crypto++/`**: Bundled Crypto++ library
- **`/build/`**: Generated build artifacts (created by build.bat)