@echo off
echo Setting up Visual Studio environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

echo Building simple test client...
cl.exe /EHsc simple_test_client.cpp /Fe:simple_test_client.exe /link ws2_32.lib

if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo Build successful!
echo Running test from client directory...
cd client
..\simple_test_client.exe
pause