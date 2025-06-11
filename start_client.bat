@echo off
echo Building and starting Encrypted Backup Client...
call build.bat
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b %ERRORLEVEL%
)
echo Build successful! Starting client...
cd client
EncryptedBackupClient.exe
pause
