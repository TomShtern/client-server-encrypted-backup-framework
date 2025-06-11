@echo off
REM Clean build script - removes all build artifacts

echo Cleaning build artifacts...

REM Remove executable
if exist "client\EncryptedBackupClient.exe" (
    del /q "client\EncryptedBackupClient.exe"
    echo Removed EncryptedBackupClient.exe
)

REM Remove client object files
if exist "build\client\*.obj" (
    del /q "build\client\*.obj"
    echo Removed client object files
)

REM Remove crypto++ object files
if exist "build\crypto++\*.obj" (
    del /q "build\crypto++\*.obj"
    echo Removed crypto++ object files
)

REM Remove any remaining object files in root (cleanup old builds)
if exist "*.obj" (
    del /q "*.obj"
    echo Removed any remaining object files from root
)

if exist "*.o" (
    del /q "*.o"
    echo Removed any remaining .o files from root
)

echo Clean complete!
