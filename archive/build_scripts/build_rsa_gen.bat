@echo off
REM Build RSA generator using MSVC like the main project
set "CL_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe"
set "LIB_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64"
set "INCLUDE_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include"
set "WIN_SDK_LIB=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\um\x64"
set "WIN_SDK_UCRT=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\ucrt\x64"
set "WIN_SDK_INCLUDE=C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0"

REM Set environment variables for the compiler
set "LIB=%LIB_PATH%;%WIN_SDK_LIB%;%WIN_SDK_UCRT%;%LIB%"
set "INCLUDE=%INCLUDE_PATH%;%WIN_SDK_INCLUDE%\um;%WIN_SDK_INCLUDE%\shared;%WIN_SDK_INCLUDE%\ucrt;%INCLUDE%"

echo Compiling RSA generator...
"%CL_PATH%" /EHsc /D_WIN32_WINNT=0x0601 /std:c++17 /DCRYPTOPP_DISABLE_ASM=1 /I"crypto++" /Fe:"simple_rsa_gen.exe" ^
simple_rsa_gen.cpp ^
build\crypto++\*.obj ^
ws2_32.lib advapi32.lib

echo RSA generator build complete.
