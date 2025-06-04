@echo off
REM Project root build script (no CMake)
set "CL_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe"
set "LIB_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\lib\x64"
set "INCLUDE_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\include"
set "WIN_SDK_LIB=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\um\x64"
set "WIN_SDK_UCRT=C:\Program Files (x86)\Windows Kits\10\lib\10.0.22621.0\ucrt\x64"
set "WIN_SDK_INCLUDE=C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0"

REM Set environment variables for the compiler
set "LIB=%LIB_PATH%;%WIN_SDK_LIB%;%WIN_SDK_UCRT%;%LIB%"
set "INCLUDE=%INCLUDE_PATH%;%WIN_SDK_INCLUDE%\um;%WIN_SDK_INCLUDE%\shared;%WIN_SDK_INCLUDE%\ucrt;%INCLUDE%"

REM 2) Compile all client sources and required Crypto++ sources into EncryptedBackupClient.exe
"%CL_PATH%" /EHsc /D_WIN32_WINNT=0x0601 /std:c++17 /DCRYPTOPP_DISABLE_ASM=1 /DCRYPTOPP_MANUALLY_INSTANTIATE_TEMPLATES=1 /I"client\include" /I"client\config" /I"third_party\cryptopp" /I"C:\Users\tom7s\Downloads\boost_1_88_0\boost_1_88_0" /Fe:"client\EncryptedBackupClient.exe" ^
client\src\*.cpp ^
third_party\cryptopp\rijndael.cpp ^
third_party\cryptopp\base64.cpp ^
third_party\cryptopp\filters.cpp ^
third_party\cryptopp\osrng.cpp ^
third_party\cryptopp\modes.cpp ^
third_party\cryptopp\rsa.cpp ^
third_party\cryptopp\files.cpp ^
third_party\cryptopp\hex.cpp ^
third_party\cryptopp\sha.cpp ^
third_party\cryptopp\cryptlib.cpp ^
third_party\cryptopp\integer.cpp ^
third_party\cryptopp\nbtheory.cpp ^
third_party\cryptopp\algparam.cpp ^
third_party\cryptopp\default.cpp ^
third_party\cryptopp\pubkey.cpp ^
third_party\cryptopp\misc.cpp ^
third_party\cryptopp\queue.cpp ^
third_party\cryptopp\cpu.cpp ^
third_party\cryptopp\allocate.cpp ^
third_party\cryptopp\randpool.cpp ^
third_party\cryptopp\asn.cpp ^
third_party\cryptopp\gfpcrypt.cpp ^
third_party\cryptopp\eccrypto.cpp ^
third_party\cryptopp\ecp.cpp ^
third_party\cryptopp\ec2n.cpp ^
third_party\cryptopp\iterhash.cpp ^
third_party\cryptopp\basecode.cpp ^
third_party\cryptopp\oaep.cpp ^
third_party\cryptopp\algebra.cpp ^
third_party\cryptopp\polynomi.cpp ^
third_party\cryptopp\gf2n.cpp ^
third_party\cryptopp\hmac.cpp ^
third_party\cryptopp\des.cpp ^
third_party\cryptopp\fips140.cpp ^
third_party\cryptopp\pkcspad.cpp ^
third_party\cryptopp\hrtimer.cpp ^
third_party\cryptopp\mqueue.cpp ^
third_party\cryptopp\rdtables.cpp ^
third_party\cryptopp\primetab.cpp ^
third_party\cryptopp\dessp.cpp ^
third_party\cryptopp\strciphr.cpp ^
third_party\cryptopp\abstract_implementations.cpp ^
third_party\cryptopp\rdrand.cpp ^
third_party\cryptopp\rng.cpp ^
third_party\cryptopp\darn.cpp ^
third_party\cryptopp\eprecomp.cpp ^
third_party\cryptopp\algebra_complete_instantiations.cpp ^
third_party\cryptopp\algebra_instantiations.cpp ^
third_party\cryptopp\template_instantiations.cpp ^
third_party\cryptopp\simple.cpp ^
third_party\cryptopp\rijndael_simd.cpp ^
ws2_32.lib advapi32.lib user32.lib

echo Build complete. Executable at client\EncryptedBackupClient.exe
