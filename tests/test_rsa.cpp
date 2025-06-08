#include <iostream>
#include <stdexcept>
#include "../client/include/RSAWrapper.h"

int main() {
    try {
        std::cout << "Testing RSA key generation..." << std::endl;
        RSAPrivateWrapper rsa;
        std::cout << "RSA key generation successful!" << std::endl;
        
        // Test getting public key
        std::string pubKey = rsa.getPublicKey();
        std::cout << "Public key size: " << pubKey.size() << " bytes" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
