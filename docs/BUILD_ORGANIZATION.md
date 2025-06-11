# Build Organization

This project now uses an organized build structure to keep object files neat and separated.

## Directory Structure

```
project-root/
├── build/                  # Organized build output directory
│   ├── client/            # Client-specific object files (.obj)
│   ├── crypto++/          # Crypto++ library object files (.obj)
│   └── server/            # Server-specific object files (.obj)
├── client/                # Client source code and executable
│   ├── src/              # Client source files (.cpp)
│   ├── include/          # Client header files (.h)
│   ├── config/           # Client configuration files
│   └── EncryptedBackupClient.exe  # Final executable
├── crypto++/             # Crypto++ library source code
├── server/               # Server source code
└── build.bat             # Main build script
```

## Build Process

The build process is now organized into three stages:

1. **Compile Client Sources**: All client `.cpp` files are compiled to `build/client/`
2. **Compile Crypto++ Sources**: Required Crypto++ `.cpp` files are compiled to `build/crypto++/`
3. **Link Executable**: All object files are linked together to create the final executable

## Build Scripts

- `build.bat` - Main build script with organized output
- `clean.bat` - Cleans all build artifacts including organized directories

## Benefits

- **Cleaner Root Directory**: No more scattered `.obj` files in the project root
- **Better Organization**: Object files are separated by component (client, crypto++, server)
- **Easier Debugging**: Easier to identify which component has build issues
- **Faster Incremental Builds**: Only recompile what's needed
- **Better Version Control**: Build artifacts are properly separated from source code

## Usage

### Building:
```bash
build.bat
```

### Cleaning:
```bash
clean.bat
```

### VS Code Tasks:
- **Build with MSVC**: Builds the entire project
- **Clean Build**: Removes all build artifacts
- **Run Client**: Builds and runs the client application
