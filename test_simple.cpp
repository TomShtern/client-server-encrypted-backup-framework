#include <iostream>
#include <windows.h>

int main() {
    // Allocate a console window
    AllocConsole();
    
    // Redirect stdout to console
    freopen_s((FILE**)stdout, "CONOUT$", "w", stdout);
    freopen_s((FILE**)stderr, "CONOUT$", "w", stderr);
    freopen_s((FILE**)stdin, "CONIN$", "r", stdin);
    
    std::cout << "HELLO WORLD - SIMPLE TEST!" << std::endl;
    std::cout << "This is a minimal test program." << std::endl;
    std::cout << "Press Enter to exit..." << std::endl;
    
    std::cin.get();
    
    FreeConsole();
    return 0;
}
