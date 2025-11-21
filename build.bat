@echo off
REM ============================================================================
REM CyberBackup 3.0 - C++ Client Build Script (Windows)
REM ============================================================================
REM Simple wrapper for CMake builds with vcpkg integration
REM
REM Usage:
REM   build.bat              - Build release (default)
REM   build.bat debug        - Build debug version
REM   build.bat clean        - Clean and rebuild
REM   build.bat --help       - Show this help
REM ============================================================================

setlocal enabledelayedexpansion

REM Parse arguments
set BUILD_TYPE=Release
set CLEAN_BUILD=0
set USE_NINJA=0

:parse_args
if "%1"=="" goto :end_parse
if /i "%1"=="debug" (
    set BUILD_TYPE=Debug
    set PRESET=debug
)
if /i "%1"=="release" (
    set BUILD_TYPE=Release
    set PRESET=release
)
if /i "%1"=="clean" set CLEAN_BUILD=1
if /i "%1"=="--clean" set CLEAN_BUILD=1
if /i "%1"=="ninja" set USE_NINJA=1
if /i "%1"=="--help" goto :show_help
if /i "%1"=="-h" goto :show_help
if /i "%1"=="/?" goto :show_help
shift
goto :parse_args
:end_parse

REM Set preset based on build type and generator
if %USE_NINJA%==1 (
    set PRESET=ninja-release
) else (
    if "%PRESET%"=="" set PRESET=release
)

echo ========================================
echo CyberBackup 3.0 - C++ Client Build
echo ========================================
echo Build Type: %BUILD_TYPE%
echo Preset: %PRESET%
echo ========================================
echo.

REM Clean if requested
if %CLEAN_BUILD%==1 (
    echo [CLEAN] Removing build directory...
    if exist build rmdir /s /q build
    if exist build-ninja rmdir /s /q build-ninja
    echo [OK] Build directories cleaned
    echo.
)

REM Check if CMake is available
where cmake >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake not found in PATH
    echo Please install CMake and add it to your PATH
    pause
    exit /b 1
)

REM Check if vcpkg is bootstrapped
if not exist "vcpkg\vcpkg.exe" (
    echo [ERROR] vcpkg not found at vcpkg\vcpkg.exe
    echo Please bootstrap vcpkg first:
    echo   cd vcpkg
    echo   .\bootstrap-vcpkg.bat
    pause
    exit /b 1
)

REM Install dependencies if vcpkg_installed doesn't exist
if not exist "vcpkg_installed" (
    echo [VCPKG] Installing dependencies...
    vcpkg\vcpkg.exe install --triplet x64-windows
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] vcpkg dependency installation failed
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
    echo.
)

REM Configure using CMake presets
echo [CMAKE] Configuring with preset: %PRESET%
cmake --preset %PRESET%
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CMake configuration failed
    echo.
    echo Try running with 'clean' flag: build.bat clean
    pause
    exit /b 1
)
echo [OK] Configuration complete
echo.

REM Build
echo [BUILD] Compiling C++ client...
cmake --build --preset %PRESET%
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Build completed successfully!
echo ========================================

REM Find the executable
if %USE_NINJA%==1 (
    set EXE_PATH=build-ninja\EncryptedBackupClient.exe
) else (
    set EXE_PATH=build\%BUILD_TYPE%\EncryptedBackupClient.exe
)

if exist "%EXE_PATH%" (
    echo Executable: %EXE_PATH%
    echo.
    echo Run it with: %EXE_PATH%
) else (
    echo [WARNING] Executable not found at expected location
)

pause
exit /b 0

:show_help
echo.
echo CyberBackup 3.0 - C++ Client Build Script
echo.
echo Usage: build.bat [options]
echo.
echo Options:
echo   debug       Build debug version
echo   release     Build release version (default)
echo   clean       Clean build directory before building
echo   ninja       Use Ninja generator for faster builds
echo   --help      Show this help message
echo.
echo Examples:
echo   build.bat              Build release version
echo   build.bat debug        Build debug version
echo   build.bat clean        Clean and rebuild
echo   build.bat ninja        Fast release build with Ninja
echo.
pause
exit /b 0
