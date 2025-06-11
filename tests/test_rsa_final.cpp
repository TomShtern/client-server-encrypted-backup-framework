#include <iostream>
#include <stdexcept>
#include "../client/include/RSAWrapper.h"

int main() {
    try {
        std::cout << "=== RSA Key Generation and Encryption Test ===" << std::endl;
        
        // Test RSA key generation
        std::cout << "1. Testing RSA key generation..." << std::endl;
        RSAPrivateWrapper rsa;
        std::cout << "   ✓ RSA key generation successful!" << std::endl;
        
        // Test getting public key
        std::cout << "2. Testing public key extraction..." << std::endl;
        std::string pubKey = rsa.getPublicKey();
        std::cout << "   ✓ Public key size: " << pubKey.size() << " bytes" << std::endl;
        
        // Test getting private key
        std::cout << "3. Testing private key extraction..." << std::endl;
        std::string privKey = rsa.getPrivateKey();
        std::cout << "   ✓ Private key size: " << privKey.size() << " bytes" << std::endl;
        
        // Test encryption/decryption
        std::cout << "4. Testing RSA encryption/decryption..." << std::endl;
        
        // Create public key wrapper from the generated public key
        RSAPublicWrapper pubWrapper(pubKey.c_str(), pubKey.size());
        
        // Test data
        std::string testData = "Hello, RSA encryption!";
        std::cout << "   Original data: \"" << testData << "\"" << std::endl;
        
        // Encrypt
        std::string encrypted = pubWrapper.encrypt(testData);
        std::cout << "   ✓ Encrypted data size: " << encrypted.size() << " bytes" << std::endl;
        
        // Decrypt
        std::string decrypted = rsa.decrypt(encrypted);
        std::cout << "   ✓ Decrypted data: \"" << decrypted << "\"" << std::endl;
        
        // Verify
        if (testData == decrypted) {
            std::cout << "   ✓ Encryption/Decryption verification PASSED!" << std::endl;
        } else {
            std::cout << "   ✗ Encryption/Decryption verification FAILED!" << std::endl;
            return 1;
        }
        
        std::cout << "\n=== ALL TESTS PASSED! ===" << std::endl;
        std::cout << "RSA implementation is working correctly." << std::endl;
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "ERROR: Unknown exception occurred" << std::endl;
        return 1;
    }
}
