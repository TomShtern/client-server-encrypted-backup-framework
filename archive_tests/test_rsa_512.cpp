#include <iostream>
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"

using namespace CryptoPP;

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
