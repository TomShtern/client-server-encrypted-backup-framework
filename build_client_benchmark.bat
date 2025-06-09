@echo off
REM Build script for Client Benchmark Suite
REM Step 7: Performance Analysis Tools

echo ========================================
echo Building Client Benchmark Suite
echo ========================================

REM Check if Visual Studio Build Tools are available
where cl >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Setting up Visual Studio Build Tools...
    REM Try different Visual Studio paths
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
        call "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
    ) else (
        echo WARNING: Visual Studio Build Tools not found in standard locations
        echo Attempting to continue with existing environment...
    )
)

REM Create build directory for benchmark
if not exist "build\benchmark" mkdir "build\benchmark"

echo.
echo Compiling Crypto++ objects (if needed)...
if not exist "build\crypto++\*.obj" (
    echo Crypto++ objects not found, building them first...
    call build.bat
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to build Crypto++ dependencies
        echo Attempting to continue without full dependencies...
    )
)

echo.
echo Compiling client benchmark source...

REM Compile the benchmark executable
cl /EHsc /D_WIN32_WINNT=0x0601 /std:c++17 ^
   /I"client\include" ^
   /I"crypto++" ^
   /Fe:"build\benchmark\client_benchmark.exe" ^
   client_benchmark.cpp ^
   client\src\RSAWrapper.cpp ^
   client\src\AESWrapper.cpp ^
   client\src\Base64Wrapper.cpp ^
   client\src\protocol.cpp ^
   build\crypto++\*.obj ^
   ws2_32.lib advapi32.lib user32.lib

if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to compile client benchmark
    pause
    exit /b 1
)

echo.
echo ========================================
echo Client Benchmark Build Complete!
echo ========================================
echo Executable: build\benchmark\client_benchmark.exe
echo.
echo To run the benchmark:
echo   build\benchmark\client_benchmark.exe
echo.
pause
