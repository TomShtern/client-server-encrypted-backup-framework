# Building the C++ Client

This document describes all available methods to build the C++ EncryptedBackupClient.

## 📋 Prerequisites

- **CMake** 3.15+ ([download](https://cmake.org/download/))
- **Visual Studio 2022** with C++ desktop development workload
- **vcpkg** (included in this repository at `vcpkg/`)

## 🚀 Build Methods (Choose One)

### Method 1: CMake Presets (Recommended) ⭐

**Modern, IDE-friendly, zero-configuration approach**

```bash
# Configure and build in one command
cmake --preset default
cmake --build --preset default

# Or for release build
cmake --preset release
cmake --build --preset release
```

**Advantages:**
- ✅ Works with all modern IDEs (VS Code, Visual Studio, CLion)
- ✅ No need to specify toolchain file
- ✅ Automatic vcpkg integration
- ✅ Industry standard approach

**Available Presets:**
- `default` - Debug build with Visual Studio generator
- `release` - Release build with Visual Studio generator
- `debug` - Explicit debug build
- `ninja-release` - Fast release build with Ninja generator

---

### Method 2: Auto-Detection (Simple)

**CMake automatically finds vcpkg**

```bash
# CMake will auto-detect vcpkg toolchain
cmake -B build

# Build
cmake --build build --config Release
```

**How it works:**
- CMakeLists.txt searches for vcpkg in:
  1. `${PROJECT_ROOT}/vcpkg/scripts/buildsystems/vcpkg.cmake`
  2. `$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake`
  3. `C:/vcpkg/scripts/buildsystems/vcpkg.cmake`

---

### Method 3: Build Script (Easiest)

**Simple batch script wrapper**

```bash
# Release build (default)
.\build.bat

# Debug build
.\build.bat debug

# Clean rebuild
.\build.bat clean

# Fast build with Ninja
.\build.bat ninja
```

---

### Method 4: Explicit Toolchain (Advanced)

**Full control over configuration**

```bash
# Clean previous build
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue

# Configure
cmake -B build -S . `
  -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake `
  -DVCPKG_TARGET_TRIPLET=x64-windows `
  -A x64

# Build
cmake --build build --config Release
```

---

### Method 5: One-Click Full System (Complete)

**Builds C++ client + launches entire system**

```bash
python scripts/one_click_build_and_run.py
```

This script:
1. Builds C++ client
2. Starts Python backup server
3. Starts Flask API server
4. Launches FletV2 desktop GUI
5. Opens web UI in browser

---

## 🔧 Common Tasks

### Installing Dependencies

```bash
# vcpkg installs dependencies automatically during CMake configure
# Or manually install:
vcpkg\vcpkg.exe install --triplet x64-windows
```

### Clean Build

```bash
# Method 1: Using build script
.\build.bat clean

# Method 2: Manual
Remove-Item -Recurse -Force build, build-ninja -ErrorAction SilentlyContinue
cmake --preset release
cmake --build --preset release
```

### Changing Build Type

```cmake
# Debug build
cmake --preset debug
cmake --build --preset debug

# Release build
cmake --preset release
cmake --build --preset release
```

### Using Ninja for Faster Builds

```bash
# Install Ninja first (if not already installed)
# winget install Ninja-build.Ninja

# Use Ninja preset
cmake --preset ninja-release
cmake --build --preset ninja-release
```

---

## 📍 Output Locations

After building, the executable will be at:

- **Visual Studio builds:**
  - Debug: `build/Debug/EncryptedBackupClient.exe`
  - Release: `build/Release/EncryptedBackupClient.exe`

- **Ninja builds:**
  - `build-ninja/EncryptedBackupClient.exe`

---

## 🐛 Troubleshooting

### Error: "Boost not found"

**Cause:** vcpkg dependencies not installed or toolchain file not specified

**Solution:**
```bash
# Use CMake presets (automatically handles toolchain)
cmake --preset default

# Or manually install dependencies
vcpkg\vcpkg.exe install --triplet x64-windows
```

### Error: "vcpkg install failed"

**Cause:** File locking issues (common on Windows)

**Solutions:**
1. Close Visual Studio and any file explorers
2. Temporarily disable antivirus
3. Move project to shorter path (e.g., `C:\cyberbackup`)
4. Clean and retry:
   ```bash
   Remove-Item -Recurse -Force vcpkg_installed -ErrorAction SilentlyContinue
   vcpkg\vcpkg.exe install --triplet x64-windows
   ```

### Error: "CMake not found"

**Solution:**
```bash
# Install CMake
winget install Kitware.CMake

# Or download from https://cmake.org/download/
```

### Build is slow

**Solution:** Use Ninja generator
```bash
# Install Ninja
winget install Ninja-build.Ninja

# Build with Ninja
cmake --preset ninja-release
cmake --build --preset ninja-release
```

---

## 💡 IDE Integration

### Visual Studio Code

1. Install **CMake Tools** extension
2. Open project folder
3. VS Code automatically detects `CMakePresets.json`
4. Select preset from status bar
5. Build with `F7` or click "Build" button

### Visual Studio 2022

1. Open folder in Visual Studio
2. VS automatically detects `CMakePresets.json`
3. Select preset from dropdown
4. Build → Build All

### CLion

1. Open project
2. CLion automatically loads presets
3. Select configuration from dropdown
4. Build → Build Project

---

## 📚 Additional Information

### vcpkg Dependencies

Defined in `vcpkg.json`:
- `boost-asio` - Networking
- `boost-beast` - HTTP/WebSocket
- `boost-iostreams` - Compression
- `cryptopp` - Encryption (RSA, AES)
- `zlib` - Compression
- `sentry-native` - Error tracking

### Build Configuration

- **C++ Standard:** C++17
- **Platform:** Windows x64
- **Compiler:** MSVC (Visual Studio 2022)
- **Dependencies:** Managed by vcpkg

### Project Structure

```
Client/
├── cpp/               # Source files
│   ├── main.cpp
│   ├── client.cpp
│   └── WebServerBackend.cpp
└── deps/              # Crypto wrappers
    ├── RSAWrapper.cpp
    ├── AESWrapper.cpp
    └── crc.cpp

build/                 # Build output (Visual Studio)
build-ninja/           # Build output (Ninja)
vcpkg/                 # Package manager
vcpkg_installed/       # Installed packages
CMakeLists.txt         # Build configuration
CMakePresets.json      # Build presets
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Configure (presets) | `cmake --preset release` |
| Build (presets) | `cmake --build --preset release` |
| Configure (manual) | `cmake -B build` |
| Build (manual) | `cmake --build build --config Release` |
| Clean build | `.\build.bat clean` |
| Install deps | `vcpkg\vcpkg.exe install --triplet x64-windows` |
| Full system | `python scripts/one_click_build_and_run.py` |

---

**For issues, see:** [Troubleshooting](#-troubleshooting)
**For full system deployment, see:** `scripts/one_click_build_and_run.py`
