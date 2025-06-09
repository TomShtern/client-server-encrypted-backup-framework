#include <iostream>
#include <chrono>
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"
#include "crypto++/integer.h"

using namespace CryptoPP;

/**
 * @brief Generates and validates a 128-bit RSA private key using the Crypto++ library.
 *
 * Measures the time taken to generate the key, validates the generated key, and outputs the results.
 * Handles and reports exceptions from Crypto++ and standard libraries.
 *
 * @return int Returns 0 on success, or 1 if an exception occurs.
 */
int main() {
    try {
        std::cout << "Testing 128-bit RSA key generation..." << std::endl;
        
        auto start = std::chrono::steady_clock::now();
        
        AutoSeededRandomPool rng;
        std::cout << "Random pool created" << std::endl;
        
        RSA::PrivateKey privateKey;
        std::cout << "Private key object created" << std::endl;
        
        // Test with 128-bit keys using Initialize method
        Integer e = 65537;
        std::cout << "Attempting Initialize with 128 bits..." << std::endl;
        privateKey.Initialize(rng, 128, e);
        
        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        
        std::cout << "SUCCESS! 128-bit RSA key generated in " << duration << "ms" << std::endl;
        
        // Test validation
        if (privateKey.Validate(rng, 1)) {
            std::cout << "Key validation: PASSED" << std::endl;
        } else {
            std::cout << "Key validation: FAILED" << std::endl;
        }
        
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
