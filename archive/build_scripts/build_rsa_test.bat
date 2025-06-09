@echo off
set "CL_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe"
set "LIB_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64"
set "INCLUDE_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include"
set "WIN_SDK_LIB=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\um\x64"
set "WIN_SDK_UCRT=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\ucrt\x64"
set "WIN_SDK_INCLUDE=C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0"

set "LIB=%LIB_PATH%;%WIN_SDK_LIB%;%WIN_SDK_UCRT%;%LIB%"
set "INCLUDE=%INCLUDE_PATH%;%WIN_SDK_INCLUDE%\um;%WIN_SDK_INCLUDE%\shared;%WIN_SDK_INCLUDE%\ucrt;%INCLUDE%"

echo Compiling RSA test...
"%CL_PATH%" /EHsc /D_WIN32_WINNT=0x0601 /std:c++17 /DCRYPTOPP_DISABLE_ASM=1 /I"client\include" /I"client\config" /I"crypto++" /I"C:\Users\tom7s\Downloads\boost_1_88_0\boost_1_88_0" test_rsa_direct.cpp client\src\RSAWrapper.cpp client\src\Base64Wrapper.cpp build\crypto++\*.obj ws2_32.lib advapi32.lib user32.lib gdi32.lib shell32.lib /Fe:test_rsa_direct.exe

echo Test build complete.
