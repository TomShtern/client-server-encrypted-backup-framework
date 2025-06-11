#include <iostream>
#include <chrono>
#include "client/include/RSAWrapper.h"

int main() {
    try {
        std::cout << "Testing mock RSA implementation..." << std::endl;
        
        auto start = std::chrono::steady_clock::now();
        
        std::cout << "Creating RSAPrivateWrapper..." << std::endl;
        RSAPrivateWrapper* rsa = new RSAPrivateWrapper();
        
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        
        std::cout << "SUCCESS! Mock RSA key created in " << duration << "ms" << std::endl;
        
        // Test getting public key
        try {
            std::string pubKey = rsa->getPublicKey();
            std::cout << "Public key retrieved, size: " << pubKey.size() << " bytes" << std::endl;
        } catch (const std::exception& e) {
            std::cout << "Public key retrieval failed: " << e.what() << std::endl;
        }
        
        delete rsa;
        std::cout << "Test completed successfully!" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown error occurred" << std::endl;
        return 1;
    }
}
