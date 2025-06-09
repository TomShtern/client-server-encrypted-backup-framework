// Test RSA key generation to isolate the issue
#include <iostream>
#include <exception>
#include <chrono>
#include "client/include/RSAWrapper.h"

int main() {
    try {
        std::cout << "Testing RSA key generation..." << std::endl;
        
        auto start = std::chrono::steady_clock::now();
        std::cout << "Creating RSAPrivateWrapper..." << std::endl;
        
        RSAPrivateWrapper* rsaPrivate = new RSAPrivateWrapper();
        
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        
        std::cout << "SUCCESS! RSA key created in " << duration << "ms" << std::endl;
        
        // Test getting public key
        std::cout << "Testing getPublicKey()..." << std::endl;
        std::string pubKey = rsaPrivate->getPublicKey();
        std::cout << "Public key retrieved, size: " << pubKey.size() << " bytes" << std::endl;
        
        // Test getting private key
        std::cout << "Testing getPrivateKey()..." << std::endl;
        std::string privKey = rsaPrivate->getPrivateKey();
        std::cout << "Private key retrieved, size: " << privKey.size() << " bytes" << std::endl;
        
        delete rsaPrivate;
        std::cout << "RSA wrapper test completed successfully!" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown exception occurred" << std::endl;
        return 1;
    }
}
