@echo off
echo Starting client debug session...
echo Current directory: %CD%
echo.

echo Checking if client executable exists...
if exist "client\EncryptedBackupClient.exe" (
    echo Client executable found!
    echo File size: 
    dir "client\EncryptedBackupClient.exe" | find "EncryptedBackupClient.exe"
    echo.
    
    echo Attempting to run client...
    cd client
    echo Running from: %CD%
    
    echo --- CLIENT OUTPUT START ---
    EncryptedBackupClient.exe
    set ERRORLEVEL_VAR=%ERRORLEVEL%
    echo --- CLIENT OUTPUT END ---
    echo.
    echo Exit code: %ERRORLEVEL_VAR%
    
    echo Checking for debug log...
    if exist "client_debug.log" (
        echo Debug log found:
        type "client_debug.log"
    ) else (
        echo No debug log created.
    )
    
    cd ..
) else (
    echo ERROR: Client executable not found!
)

echo.
echo Debug session complete.
pause
