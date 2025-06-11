#include <iostream>
#include <stdexcept>

// Test the exact DER key bytes we're using
int main() {
    try {
        // This is the exact DER key from RSAWrapper.cpp (corrected)
        unsigned char derKey[] = {
            // Valid minimal DER-encoded RSA private key structure
            0x30, 0x61,                         // SEQUENCE, length 97 (corrected length)
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
        
        // Print first few bytes to verify
        std::cout << "First 10 bytes: ";
        for (int i = 0; i < 10; i++) {
            printf("%02X ", derKey[i]);
        }
        std::cout << std::endl;
        
        // Basic DER structure validation
        if (derKey[0] != 0x30) {
            throw std::runtime_error("Invalid DER key: not a SEQUENCE");
        }
        
        // Check length field  
        if (derKey[1] == 0x61) {
            int len = derKey[1];
            std::cout << "DER length: " << len << " bytes" << std::endl;
            if (len != sizeof(derKey) - 2) {
                throw std::runtime_error("DER length mismatch");
            }
        }
        
        std::cout << "DER key structure appears valid!" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "Error: " << e.what() << std::endl;
        return 1;
    }
}
