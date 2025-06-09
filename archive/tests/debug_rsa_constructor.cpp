#include <iostream>
#include <exception>
#include <chrono>

// Include necessary Crypto++ headers
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"
#include "crypto++/filters.h"

using namespace CryptoPP;

int main() {
    try {
        std::cout << "=== Testing RSA Hardcoded Key Constructor ===" << std::endl;
        
        // Test the exact hardcoded DER key from RSAWrapper.cpp
        unsigned char derKey[] = {
            // Valid minimal DER-encoded RSA private key structure
            0x30, 0x81, 0x9A,                   // SEQUENCE, length 154
            0x02, 0x01, 0x00,                   // INTEGER version = 0
            0x02, 0x11, 0x00,                   // INTEGER n (modulus) - 16 bytes + leading zero
            0xA5, 0x6E, 0x4A, 0x0E, 0x70, 0x10, 0x17, 0x58,
            0x9A, 0x51, 0x87, 0xDC, 0x7E, 0xA8, 0x41, 0xCB,
            0x02, 0x03, 0x01, 0x00, 0x01,       // INTEGER e (public exponent) = 65537
            0x02, 0x10,                         // INTEGER d (private exponent) - 16 bytes
            0x6D, 0x7F, 0xE1, 0x45, 0x83, 0x3F, 0x8A, 0x58,
            0x3E, 0x7B, 0x4C, 0x05, 0xBF, 0x7A, 0x32, 0xC1,
            0x02, 0x09,                         // INTEGER p (first prime) - 8 bytes + leading zero  
            0x00, 0xC7, 0xCD, 0x6E, 0x53, 0xFE, 0xC5, 0x4D, 0xD7,
            0x02, 0x09,                         // INTEGER q (second prime) - 8 bytes + leading zero
            0x00, 0xD7, 0x83, 0x6E, 0x5B, 0x95, 0xBB, 0x05, 0xED,
            0x02, 0x08,                         // INTEGER dp = d mod (p-1) - 8 bytes
            0x4F, 0x05, 0xB9, 0x48, 0x90, 0x2B, 0x16, 0x89,
            0x02, 0x08,                         // INTEGER dq = d mod (q-1) - 8 bytes  
            0x28, 0xFA, 0x13, 0x93, 0x86, 0x55, 0xBE, 0x1F,
            0x02, 0x08,                         // INTEGER qinv = q^(-1) mod p - 8 bytes
            0x56, 0x85, 0x8E, 0xDC, 0x6F, 0x34, 0x6F, 0xD4
        };
        
        std::cout << "DER key size: " << sizeof(derKey) << " bytes" << std::endl;
        
        // Test loading the key
        std::cout << "Testing key loading..." << std::endl;
        RSA::PrivateKey privateKey;
        
        StringSource ss(derKey, sizeof(derKey), true);
        privateKey.Load(ss);
        
        std::cout << "SUCCESS! Key loaded successfully!" << std::endl;
        
        // Test saving it back
        std::cout << "Testing key saving..." << std::endl;
        std::string keyData;
        StringSink sink(keyData);
        privateKey.Save(sink);
        
        std::cout << "Key save successful! Size: " << keyData.size() << " bytes" << std::endl;
        
        return 0;
    } catch (const Exception& e) {
        std::cerr << "Crypto++ Exception: " << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Standard Exception: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown exception occurred" << std::endl;
        return 1;
    }
}
