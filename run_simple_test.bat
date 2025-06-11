@echo off
echo === SIMPLE CONSOLE TEST ===
echo.
echo Compiling test_simple.cpp...

REM Set up the environment variables for the compiler
set "CL_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe"
set "LIB_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64"
set "INCLUDE_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include"
set "WIN_SDK_LIB=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\um\x64"
set "WIN_SDK_UCRT=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\ucrt\x64"
set "WIN_SDK_INCLUDE=C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0"

REM Set environment variables for the compiler
set "LIB=%LIB_PATH%;%WIN_SDK_LIB%;%WIN_SDK_UCRT%;%LIB%"
set "INCLUDE=%INCLUDE_PATH%;%WIN_SDK_INCLUDE%\um;%WIN_SDK_INCLUDE%\shared;%WIN_SDK_INCLUDE%\ucrt;%INCLUDE%"

"%CL_PATH%" /EHsc /MT test_simple.cpp /Fe:test_simple.exe user32.lib kernel32.lib

if exist "test_simple.exe" (
    echo.
    echo Compilation successful! Running test...
    echo === TEST OUTPUT START ===
    test_simple.exe
    echo === TEST OUTPUT END ===
    echo.
    echo Test completed.
) else (
    echo.
    echo ERROR: Compilation failed!
)

echo.
echo Press any key to close...
pause > nul
