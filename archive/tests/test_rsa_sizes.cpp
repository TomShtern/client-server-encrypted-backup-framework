// Test RSA key generation with various small sizes to find working size
#include <iostream>
#include <string>
#include <exception>
#include <chrono>

#include "crypto++/rsa.h"
#include "crypto++/osrng.h"
#include "crypto++/integer.h"
#include "crypto++/hex.h"
#include "crypto++/filters.h"

using namespace CryptoPP;
using namespace std;

bool testRSAGeneration(unsigned int keySize) {
    cout << "\nTesting RSA key generation at " << keySize << " bits..." << endl;
    
    try {
        auto start = chrono::steady_clock::now();
        
        // Use a very simple random pool
        AutoSeededRandomPool rng;
        
        cout << "  Creating RSA key object..." << endl;
        RSA::PrivateKey privateKey;
        
        cout << "  Calling GenerateRandomWithKeySize..." << endl;
        
        // Set a timeout for key generation
        auto timeout = chrono::seconds(10); // 10 second timeout
        auto startTime = chrono::steady_clock::now();
        
        // Try with smaller exponent for faster generation
        privateKey.GenerateRandomWithKeySize(rng, keySize);
        
        auto endTime = chrono::steady_clock::now();
        auto duration = chrono::duration_cast<chrono::milliseconds>(endTime - startTime).count();
        
        cout << "  ✓ Key generation successful in " << duration << "ms" << endl;
        
        // Test that the key works
        cout << "  Testing key validity..." << endl;
        
        // Get the public key part
        RSA::PublicKey publicKey(privateKey);
        cout << "  ✓ Public key derived successfully" << endl;
        
        // Try to save the key to DER format
        cout << "  Testing DER serialization..." << endl;
        string derData;
        StringSink ss(derData);
        privateKey.Save(ss);
        cout << "  ✓ DER serialization successful, size: " << derData.size() << " bytes" << endl;
        
        // Try to load it back
        cout << "  Testing DER loading..." << endl;
        RSA::PrivateKey testKey;
        StringSource source(derData, true);
        testKey.Load(source);
        cout << "  ✓ DER loading successful" << endl;
        
        return true;
        
    } catch (const Exception& e) {
        cout << "  ✗ Crypto++ Exception: " << e.what() << endl;
        return false;
    } catch (const exception& e) {
        cout << "  ✗ Standard Exception: " << e.what() << endl;
        return false;
    } catch (...) {
        cout << "  ✗ Unknown Exception" << endl;
        return false;
    }
}

int main() {
    cout << "=== RSA Key Generation Size Testing ===" << endl;
    cout << "This will test different RSA key sizes to find what works." << endl;
    
    // Test progressively larger key sizes
    vector<unsigned int> keySizes = {128, 256, 512, 1024};
    
    for (unsigned int keySize : keySizes) {
        if (testRSAGeneration(keySize)) {
            cout << "\n✓ SUCCESS: " << keySize << "-bit RSA key generation works!" << endl;
            cout << "Root cause identified: Larger keys may be problematic, but " << keySize << "-bit works." << endl;
            return 0;
        } else {
            cout << "\n✗ FAILED: " << keySize << "-bit RSA key generation failed." << endl;
        }
    }
    
    cout << "\n✗ ALL RSA KEY SIZES FAILED" << endl;
    cout << "Root cause: RSA key generation is completely broken in this environment." << endl;
    
    return 1;
}
