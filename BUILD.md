# Build Instructions for Encrypted Backup Client

This document describes how to build the Encrypted Backup Client using MSVC with Clang tools integration.

## Prerequisites

### Required Software
- **Visual Studio 2022** (or Visual Studio Build Tools 2022)
- **CMake 3.15+**
- **Git** (for version control)

### Optional Software (for Clang tools)
- **LLVM/Clang** (for clang-tidy and clang-format)
  - Download from: https://releases.llvm.org/
  - Make sure `clang-tidy` and `clang-format` are in your PATH

## Quick Start

### Using PowerShell (Recommended)
```powershell
# Debug build
.\scripts\build_msvc.ps1

# Release build
.\scripts\build_msvc.ps1 -Configuration Release

# Clean build with clang tools
.\scripts\build_msvc.ps1 -Clean -RunClangTidy -RunClangFormat

# Use Ninja generator for faster builds
.\scripts\build_msvc.ps1 -UseNinja
```

### Using Command Prompt
```cmd
# Debug build
scripts\build_msvc.bat

# Release build
scripts\build_msvc.bat --config Release

# Clean build with clang tools
scripts\build_msvc.bat --clean --clang-tidy --clang-format

# Use Ninja generator
scripts\build_msvc.bat --ninja
```

## Manual Build Process

### 1. Configure with CMake Presets
```bash
# List available presets
cmake --list-presets

# Configure for MSVC Debug
cmake --preset msvc-debug

# Configure for MSVC Release
cmake --preset msvc-release

# Configure for MSVC with Ninja (faster builds)
cmake --preset msvc-ninja-debug
```

### 2. Build the Project
```bash
# Build using preset
cmake --build --preset msvc-debug

# Or build manually
cmake --build build/msvc-debug --config Debug
```

### 3. Run Clang Tools (Optional)
```bash
# Run clang-format
cmake --build build/msvc-debug --target clang-format

# Run clang-tidy
cmake --build build/msvc-debug --target clang-tidy
```

## Build Configurations

### Available Presets
- `msvc-debug`: Debug build using Visual Studio generator
- `msvc-release`: Release build using Visual Studio generator
- `msvc-ninja-debug`: Debug build using Ninja generator (faster)
- `msvc-ninja-release`: Release build using Ninja generator (faster)

### Compiler Settings
The project is configured to use MSVC with the following settings:
- **C++ Standard**: C++17
- **Warning Level**: /W4 (high warning level)
- **Conformance**: /permissive- (strict conformance)
- **Multi-processor Compilation**: /MP (enabled)
- **UTF-8 Support**: /utf-8 (enabled)

## Clang Tools Integration

### clang-tidy
- **Configuration**: `.clang-tidy` file in project root
- **Automatic**: Runs during build if clang-tidy is found
- **Manual**: `cmake --build <build-dir> --target clang-tidy`

### clang-format
- **Configuration**: `.clang-format` file in project root
- **Style**: Based on Google style with modifications
- **Manual**: `cmake --build <build-dir> --target clang-format`

## Output Locations

### Executables
- Debug: `build/<preset>/bin/client.exe`
- Release: `build/<preset>/bin/client.exe`

### Compile Commands
- `build/<preset>/compile_commands.json` (for IDE integration)

## IDE Integration

### Visual Studio Code
1. Install the C/C++ extension
2. Install the CMake Tools extension
3. Open the project folder
4. Select a CMake preset when prompted
5. The `compile_commands.json` will be automatically used for IntelliSense

### Visual Studio 2022
1. Open the project folder (File → Open → Folder)
2. Visual Studio will automatically detect CMake
3. Select a preset from the configuration dropdown
4. Build using Ctrl+Shift+B

### CLion
1. Open the project folder
2. CLion will automatically import CMake configuration
3. Select a preset from the configuration dropdown
4. Build using Ctrl+F9

## Troubleshooting

### Common Issues

#### CMake can't find MSVC
```bash
# Make sure you're in a Visual Studio Developer Command Prompt
# Or run this before cmake:
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
```

#### clang-tidy not found
```bash
# Install LLVM and add to PATH, or disable clang-tidy in CMakeLists.txt
# Check if clang-tidy is available:
where clang-tidy
```

#### Ninja not found
```bash
# Install Ninja or use Visual Studio generator instead
# Download from: https://ninja-build.org/
```

### Clean Build
If you encounter build issues, try a clean build:
```bash
# Remove build directory
rmdir /s build

# Or use the clean option in scripts
.\scripts\build_msvc.ps1 -Clean
```

## Advanced Usage

### Custom CMake Options
```bash
cmake --preset msvc-debug -DCMAKE_VERBOSE_MAKEFILE=ON
```

### Running Tests
```bash
# After building, run tests
ctest --preset msvc-debug
```

### Installing
```bash
cmake --build build/msvc-debug --target install
```
