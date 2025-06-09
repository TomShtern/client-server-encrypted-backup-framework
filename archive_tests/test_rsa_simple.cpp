#include <iostream>
#include <chrono>
#include "client/include/RSAWrapper.h"

/**
 * @brief Entry point for testing RSA key generation using RSAPrivateWrapper.
 *
 * Measures the time taken to generate an RSA key pair, prints the key sizes, and reports success or errors.
 *
 * @return int Returns 0 on success, or 1 if an exception occurs.
 */
int main() {
    try {
        std::cout << "Testing RSA key generation with current settings..." << std::endl;
        std::cout << "Key size: " << RSAPrivateWrapper::BITS << " bits" << std::endl;
        
        auto start = std::chrono::steady_clock::now();
        
        std::cout << "Creating RSAPrivateWrapper..." << std::endl;
        RSAPrivateWrapper rsa;
        
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        
        std::cout << "RSA key generation successful!" << std::endl;
        std::cout << "Time taken: " << duration << " ms" << std::endl;
        
        // Test getting public key
        std::string pubKey = rsa.getPublicKey();
        std::cout << "Public key size: " << pubKey.size() << " bytes" << std::endl;
        
        // Test getting private key
        std::string privKey = rsa.getPrivateKey();
        std::cout << "Private key size: " << privKey.size() << " bytes" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
