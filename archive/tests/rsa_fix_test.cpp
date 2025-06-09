#include <iostream>
#include <fstream>
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"
#include "crypto++/base64.h"
#include "crypto++/files.h"

using namespace CryptoPP;

int main() {
    try {
        std::cout << "Attempting alternative RSA key generation..." << std::endl;
        
        // Try different approach - use InvertibleRSAFunction
        AutoSeededRandomPool rng;
        
        InvertibleRSAFunction params;
        std::cout << "Created InvertibleRSAFunction" << std::endl;
        
        params.GenerateRandomWithKeySize(rng, 1024);
        std::cout << "Generated parameters successfully" << std::endl;
        
        RSA::PrivateKey privateKey(params);
        std::cout << "Created private key from parameters" << std::endl;
        
        RSA::PublicKey publicKey(params);
        std::cout << "Created public key from parameters" << std::endl;
        
        // Test save to file
        FileSink fs("test_private.key", true /*binary*/);
        privateKey.Save(fs);
        std::cout << "Saved private key to file" << std::endl;
        
        // Test load from file
        RSA::PrivateKey loadedKey;
        FileSource fs2("test_private.key", true /*pump all*/);
        loadedKey.Load(fs2);
        std::cout << "Loaded private key from file" << std::endl;
        
        std::cout << "RSA key generation test successful!" << std::endl;
        return 0;
        
    } catch (const Exception& e) {
        std::cerr << "Crypto++ Exception: " << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Standard Exception: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "Unknown exception" << std::endl;
        return 1;
    }
}
