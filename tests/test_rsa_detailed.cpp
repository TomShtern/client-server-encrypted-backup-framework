// Test to isolate exactly where RSA failure occurs
#include <iostream>
#include <exception>
#include <chrono>
#include <functional>
#include "../client/include/RSAWrapper.h"

void testStep(const std::string& stepName, std::function<void()> testFunc) {
    std::cout << "Testing: " << stepName << "..." << std::endl;
    try {
        auto start = std::chrono::steady_clock::now();
        testFunc();
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << "  ✓ SUCCESS in " << duration << "ms" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "  ✗ FAILED: " << e.what() << std::endl;
        throw;
    } catch (...) {
        std::cout << "  ✗ FAILED: Unknown exception" << std::endl;
        throw;
    }
}

int main() {
    try {
        std::cout << "=== Detailed RSA Testing ===" << std::endl;
        
        RSAPrivateWrapper* rsaPrivate = nullptr;
        
        // Test 1: RSA Constructor
        testStep("RSA Constructor", [&]() {
            rsaPrivate = new RSAPrivateWrapper();
        });
        
        // Test 2: Get Private Key
        testStep("Get Private Key", [&]() {
            std::string privKey = rsaPrivate->getPrivateKey();
            std::cout << "    Private key size: " << privKey.size() << " bytes" << std::endl;
        });
        
        // Test 3: Get Public Key
        testStep("Get Public Key", [&]() {
            std::string pubKey = rsaPrivate->getPublicKey();
            std::cout << "    Public key size: " << pubKey.size() << " bytes" << std::endl;
        });
        
        // Test 4: Simple Encryption/Decryption
        testStep("Encrypt/Decrypt Test", [&]() {
            std::string testMessage = "Hello, RSA!";
            
            // Create public key wrapper from the private key's public part
            std::string pubKeyData = rsaPrivate->getPublicKey();
            RSAPublicWrapper pubWrapper(pubKeyData.c_str(), pubKeyData.size());
            
            // Encrypt with public key
            std::string encrypted = pubWrapper.encrypt(testMessage);
            std::cout << "    Encrypted size: " << encrypted.size() << " bytes" << std::endl;
            
            // Decrypt with private key
            std::string decrypted = rsaPrivate->decrypt(encrypted);
            std::cout << "    Decrypted: \"" << decrypted << "\"" << std::endl;
            
            if (decrypted != testMessage) {
                throw std::runtime_error("Decrypted text doesn't match original");
            }
        });
        
        // Test 5: Cleanup
        testStep("Cleanup", [&]() {
            delete rsaPrivate;
            rsaPrivate = nullptr;
        });
        
        std::cout << "\n✓ All RSA tests passed successfully!" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "\n✗ RSA test failed: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cout << "\n✗ RSA test failed: Unknown exception" << std::endl;
        return 1;
    }
}
