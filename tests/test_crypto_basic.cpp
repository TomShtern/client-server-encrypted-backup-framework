// Test basic Crypto++ functionality to verify library is working
#include <iostream>
#include <string>
#include <exception>

// Include minimal Crypto++ headers
#include "crypto++/sha.h"
#include "crypto++/hex.h"
#include "crypto++/filters.h"
#include "crypto++/aes.h"
#include "crypto++/modes.h"
#include "crypto++/osrng.h"

using namespace CryptoPP;

void testSHA256() {
    std::cout << "Testing SHA256..." << std::endl;
    
    SHA256 hash;
    std::string message = "Hello, Crypto++!";
    std::string digest;
    
    StringSource ss(message, true,
        new HashFilter(hash,
            new HexEncoder(
                new StringSink(digest)
            )
        )
    );
    
    std::cout << "  Input: " << message << std::endl;
    std::cout << "  SHA256: " << digest << std::endl;
    
    // Expected hash for "Hello, Crypto++!" 
    if (digest.length() == 64) {
        std::cout << "  ✓ SHA256 working (64-char hex output)" << std::endl;
    } else {
        throw std::runtime_error("SHA256 produced wrong output length");
    }
}

void testAES() {
    std::cout << "\nTesting AES..." << std::endl;
    
    AutoSeededRandomPool rng;
    
    byte key[AES::DEFAULT_KEYLENGTH];
    byte iv[AES::BLOCKSIZE];
    
    rng.GenerateBlock(key, sizeof(key));
    rng.GenerateBlock(iv, sizeof(iv));
    
    std::string plaintext = "Test AES encryption";
    std::string ciphertext, recovered;
    
    // Encrypt
    CBC_Mode<AES>::Encryption encryption;
    encryption.SetKeyWithIV(key, sizeof(key), iv);
    
    StringSource ss1(plaintext, true,
        new StreamTransformationFilter(encryption,
            new StringSink(ciphertext)
        )
    );
    
    // Decrypt
    CBC_Mode<AES>::Decryption decryption;
    decryption.SetKeyWithIV(key, sizeof(key), iv);
    
    StringSource ss2(ciphertext, true,
        new StreamTransformationFilter(decryption,
            new StringSink(recovered)
        )
    );
    
    std::cout << "  Input: " << plaintext << std::endl;
    std::cout << "  Encrypted size: " << ciphertext.size() << " bytes" << std::endl;
    std::cout << "  Recovered: " << recovered << std::endl;
    
    if (recovered == plaintext) {
        std::cout << "  ✓ AES working (encrypt/decrypt successful)" << std::endl;
    } else {
        throw std::runtime_error("AES decrypt didn't match original");
    }
}

void testRandomNumberGenerator() {
    std::cout << "\nTesting Random Number Generator..." << std::endl;
    
    AutoSeededRandomPool rng;
    
    byte buffer[32];
    rng.GenerateBlock(buffer, sizeof(buffer));
    
    std::string hex;
    StringSource ss(buffer, sizeof(buffer), true,
        new HexEncoder(
            new StringSink(hex)
        )
    );
    
    std::cout << "  Random 32 bytes: " << hex << std::endl;
    
    // Check that we got some randomness (not all zeros)
    bool hasNonZero = false;
    for (size_t i = 0; i < sizeof(buffer); i++) {
        if (buffer[i] != 0) {
            hasNonZero = true;
            break;
        }
    }
    
    if (hasNonZero && hex.length() == 64) {
        std::cout << "  ✓ RNG working (generated non-zero random data)" << std::endl;
    } else {
        throw std::runtime_error("RNG appears to be broken");
    }
}

int main() {
    try {
        std::cout << "=== Crypto++ Library Basic Functionality Test ===" << std::endl;
        std::cout << "This will determine if the root problem is library-wide or RSA-specific.\n" << std::endl;
        
        testSHA256();
        testAES();
        testRandomNumberGenerator();
        
        std::cout << "\n✓ ALL BASIC CRYPTO++ OPERATIONS WORKING!" << std::endl;
        std::cout << "This means the library build is OK and the problem is RSA-specific." << std::endl;
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "\n✗ CRYPTO++ LIBRARY FAILURE: " << e.what() << std::endl;
        std::cout << "This confirms the root cause is a broken Crypto++ build." << std::endl;
        return 1;
    } catch (...) {
        std::cout << "\n✗ CRYPTO++ LIBRARY FAILURE: Unknown exception" << std::endl;
        std::cout << "This confirms the root cause is a broken Crypto++ build." << std::endl;
        return 1;
    }
}
