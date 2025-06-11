@echo off
echo Checking for running client processes and windows...
echo.

echo Listing all processes containing "Backup" or "Client":
tasklist | findstr /i "backup"
tasklist | findstr /i "client"
tasklist | findstr /i "encrypted"

echo.
echo Checking window titles:
tasklist /fi "imagename eq EncryptedBackupClient.exe" /fo table

echo.
echo Running client directly and checking for output:
cd client
echo Current directory: %CD%
echo.
echo --- ATTEMPTING TO RUN CLIENT ---
start /wait EncryptedBackupClient.exe
echo Client exit code: %ERRORLEVEL%

echo.
echo Checking for any created files:
dir *.log 2>nul
dir *.txt 2>nul

cd ..
echo.
echo Done.
pause
