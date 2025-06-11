#include <iostream>
#include <stdexcept>
#include <functional>
#include <fstream>
#include <iomanip>

// Include Crypto++ headers
#include "cryptopp/cryptlib.h"
#include "cryptopp/rsa.h"
#include "cryptopp/osrng.h"
#include "cryptopp/files.h"
#include "cryptopp/hex.h"
#include "cryptopp/queue.h"

using namespace CryptoPP;
using namespace std;

void printByteArray(const unsigned char* data, size_t len) {
    cout << "unsigned char derKey[] = {" << endl << "    ";
    for (size_t i = 0; i < len; i++) {
        cout << "0x" << hex << setw(2) << setfill('0') << (unsigned int)data[i];
        if (i < len - 1) cout << ", ";
        if ((i + 1) % 16 == 0 && i < len - 1) cout << endl << "    ";
    }
    cout << endl << "};" << endl;
}

int main() {
    try {
        cout << "=== Generating Valid RSA Key ===" << endl;
        
        AutoSeededRandomPool rng;
        
        // Try to generate a minimal RSA key
        InvertibleRSAFunction privateKey;
        cout << "Generating 512-bit RSA key..." << endl;
        privateKey.GenerateRandomWithKeySize(rng, 512);
        
        cout << "Key generated successfully!" << endl;
        
        // Save to DER format
        string derData;
        StringSink ss(derData);
        privateKey.DEREncode(ss);
        
        cout << "DER encoding successful! Size: " << derData.size() << " bytes" << endl;
        
        // Print as C++ array
        cout << "\n=== C++ Array Format ===" << endl;
        printByteArray((const unsigned char*)derData.c_str(), derData.size());
        
        // Test loading the key back
        cout << "\n=== Testing Key Load ===" << endl;
        InvertibleRSAFunction testKey;
        StringSource testSS(derData, true);
        testKey.Load(testSS);
        cout << "✓ Key load test successful!" << endl;
        
        return 0;
        
    } catch (const Exception& e) {
        cout << "✗ Crypto++ Exception: " << e.what() << endl;
        return 1;
    } catch (const std::exception& e) {
        cout << "✗ std::exception: " << e.what() << endl;
        return 1;
    } catch (...) {
        cout << "✗ Unknown exception" << endl;
        return 1;
    }
}
