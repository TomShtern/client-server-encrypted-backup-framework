#include <windows.h>
#include <iostream>

int main() {
    // Allocate a console
    AllocConsole();
    FILE* pCout;
    freopen_s(&pCout, "CONOUT$", "w", stdout);
    
    // Show console
    HWND consoleWindow = GetConsoleWindow();
    if (consoleWindow) {
        ShowWindow(consoleWindow, SW_SHOW);
        SetForegroundWindow(consoleWindow);
    }
    
    std::cout << "Simple test - console is working!" << std::endl;
    
    // Create a simple message box
    MessageBoxA(nullptr, "Simple test window!", "Test", MB_OK);
    
    std::cout << "Message box shown. Press Enter to exit." << std::endl;
    std::cin.get();
    
    return 0;
}
