#include <iostream>
#include <cryptopp/rsa.h>
#include <cryptopp/osrng.h>

using namespace CryptoPP;

int main() {
    try {
        std::cout << "Testing minimal RSA key generation..." << std::endl;
        
        AutoSeededRandomPool rng;
        std::cout << "Random pool created successfully" << std::endl;
        
        RSA::PrivateKey privateKey;
        std::cout << "Private key object created" << std::endl;
        
        std::cout << "Attempting to generate 1024-bit RSA key..." << std::endl;
        privateKey.GenerateRandomWithKeySize(rng, 1024);
        std::cout << "RSA key generation successful!" << std::endl;
        
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
