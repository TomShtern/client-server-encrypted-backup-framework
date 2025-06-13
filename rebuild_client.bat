@echo off
echo Rebuilding client with fixed main.cpp...

REM Set up VS environment
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

REM Remove old executable
if exist client\EncryptedBackupClient.exe (
    del /f /q client\EncryptedBackupClient.exe
)

REM Create build directories
if not exist "build" mkdir "build"
if not exist "build\client" mkdir "build\client"

echo Compiling updated main.cpp and client sources...
cl.exe /EHc= /D_WIN32_WINNT=0x0601 /std:c++14 /MT ^
   /I"include\client" /I"include\wrappers" ^   /c /Fo:"build\client\\" ^
   src\client\main.cpp ^
   src\client\client.cpp ^
   src\client\protocol.cpp ^
   src\client\cksum.cpp ^
   src\client\ClientGUI.cpp ^
   src\wrappers\RSAWrapper_stub.cpp ^
   src\wrappers\AESWrapper.cpp ^
   src\wrappers\Base64Wrapper.cpp

if %ERRORLEVEL% neq 0 (
    echo ERROR: Compilation failed
    pause
    exit /b 1
)

echo Linking executable...
cl.exe /EHc /D_WIN32_WINNT=0x0601 /std:c++14 /MT ^
   /Fe:"client\EncryptedBackupClient.exe" ^
   build\client\*.obj ^
   /link ws2_32.lib advapi32.lib user32.lib gdi32.lib shell32.lib crypt32.lib msimg32.lib comdlg32.lib bcrypt.lib

if %ERRORLEVEL% neq 0 (
    echo ERROR: Linking failed
    pause
    exit /b 1
)

echo Build successful!
echo Testing the client...
cd client
.\EncryptedBackupClient.exe
pause