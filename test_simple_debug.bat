@echo off
echo Testing simple console program...
echo.

echo Compiling test_simple.cpp...
"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe" /EHsc /MT test_simple.cpp /Fe:test_simple.exe user32.lib kernel32.lib

if exist "test_simple.exe" (
    echo Compilation successful!
    echo Running simple test...
    echo --- SIMPLE TEST START ---
    test_simple.exe
    echo --- SIMPLE TEST END ---
) else (
    echo Compilation failed!
)

echo.
pause
