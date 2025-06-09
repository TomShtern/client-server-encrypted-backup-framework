#include <iostream>
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"

using namespace CryptoPP;

/**
 * @brief Tests RSA 512-bit key generation using the Crypto++ library.
 *
 * Initializes a cryptographically secure random number generator, generates 512-bit RSA parameters, assigns them to a private key, and reports the outcome. Handles Crypto++ and standard exceptions, returning 0 on success and 1 on failure.
 *
 * @return int 0 if the test passes, 1 if an exception occurs.
 */
int main() {
    try {
        std::cout << "Testing RSA key generation..." << std::endl;
        
        AutoSeededRandomPool rng;
        std::cout << "Random pool created" << std::endl;
        
        InvertibleRSAFunction rsaParams;
        std::cout << "About to generate 512-bit RSA parameters..." << std::endl;
        
        rsaParams.GenerateRandomWithKeySize(rng, 512);
        std::cout << "RSA parameters generated successfully!" << std::endl;
        
        RSA::PrivateKey privateKey;
        privateKey = rsaParams;
        std::cout << "Private key assigned successfully!" << std::endl;
        
        std::cout << "RSA key generation test PASSED!" << std::endl;
        return 0;
        
    } catch (const Exception& e) {
        std::cout << "Crypto++ Exception: " << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cout << "std::exception: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cout << "Unknown exception caught" << std::endl;
        return 1;
    }
}
