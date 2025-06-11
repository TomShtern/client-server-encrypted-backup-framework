#include <iostream>
#include <fstream>

int main() {
    // Create a log file
    std::ofstream log("simple_test.log");
    log << "Simple test started" << std::endl;
    log.close();
    
    // Try console output
    std::cout << "Hello from simple test!" << std::endl;
    
    // Keep window open
    std::cout << "Press Enter to exit..." << std::endl;
    std::cin.get();
    
    return 0;
}
