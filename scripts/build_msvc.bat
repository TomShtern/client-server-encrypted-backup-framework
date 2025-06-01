@echo off
setlocal enabledelayedexpansion

:: Default values
set "CONFIG=Debug"
set "CLEAN=false"
set "RUN_CLANG_TIDY=false"
set "RUN_CLANG_FORMAT=false"
set "USE_NINJA=false"

:: Parse command line arguments
:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--config" (
    set "CONFIG=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--clean" (
    set "CLEAN=true"
    shift
    goto :parse_args
)
if /i "%~1"=="--clang-tidy" (
    set "RUN_CLANG_TIDY=true"
    shift
    goto :parse_args
)
if /i "%~1"=="--clang-format" (
    set "RUN_CLANG_FORMAT=true"
    shift
    goto :parse_args
)
if /i "%~1"=="--ninja" (
    set "USE_NINJA=true"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    echo Usage: build_msvc.bat [options]
    echo Options:
    echo   --config ^<Debug^|Release^>  Build configuration (default: Debug)
    echo   --clean                    Clean build directory before building
    echo   --clang-tidy              Run clang-tidy after building
    echo   --clang-format            Run clang-format after building
    echo   --ninja                   Use Ninja generator instead of Visual Studio
    echo   --help                    Show this help message
    exit /b 0
)
shift
goto :parse_args

:done_parsing

:: Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo Building Encrypted Backup Client with MSVC...
echo Configuration: %CONFIG%
echo Project Root: %PROJECT_ROOT%

:: Change to project root
cd /d "%PROJECT_ROOT%"

:: Determine preset name
if "%USE_NINJA%"=="true" (
    if /i "%CONFIG%"=="Debug" (
        set "PRESET_NAME=msvc-ninja-debug"
    ) else (
        set "PRESET_NAME=msvc-ninja-release"
    )
) else (
    if /i "%CONFIG%"=="Debug" (
        set "PRESET_NAME=msvc-debug"
    ) else (
        set "PRESET_NAME=msvc-release"
    )
)

echo Using preset: %PRESET_NAME%

:: Clean if requested
if "%CLEAN%"=="true" (
    echo Cleaning build directory...
    set "BUILD_DIR=build\%PRESET_NAME%"
    if exist "!BUILD_DIR!" (
        rmdir /s /q "!BUILD_DIR!"
        echo Cleaned !BUILD_DIR!
    )
)

:: Configure the project
echo Configuring project...
cmake --preset %PRESET_NAME%
if errorlevel 1 (
    echo Configuration failed!
    exit /b 1
)
echo Configuration completed successfully!

:: Build the project
echo Building project...
cmake --build --preset %PRESET_NAME% --config %CONFIG%
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)
echo Build completed successfully!

:: Run clang-format if requested
if "%RUN_CLANG_FORMAT%"=="true" (
    echo Running clang-format...
    cmake --build "build\%PRESET_NAME%" --target clang-format
    if errorlevel 1 (
        echo Warning: clang-format failed or not available
    ) else (
        echo clang-format completed!
    )
)

:: Run clang-tidy if requested
if "%RUN_CLANG_TIDY%"=="true" (
    echo Running clang-tidy...
    cmake --build "build\%PRESET_NAME%" --target clang-tidy
    if errorlevel 1 (
        echo Warning: clang-tidy failed or not available
    ) else (
        echo clang-tidy completed!
    )
)

echo All operations completed successfully!
echo Executable location: build\%PRESET_NAME%\bin\client.exe

endlocal
