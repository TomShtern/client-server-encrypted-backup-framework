// Minimal test to check if Crypto++ basic operations work
#include <iostream>
#include <string>

// Test includes - each one alone
#include "crypto++/cryptlib.h"
#include "crypto++/sha.h"

using namespace CryptoPP;
using namespace std;

int main() {
    try {
        cout << "Testing basic Crypto++ functionality..." << endl;
        
        // Test 1: Can we create a SHA256 object?
        SHA256 hasher;
        cout << "✓ SHA256 object creation successful" << endl;
        
        // Test 2: Can we hash something basic?
        string message = "test";
        byte digest[SHA256::DIGESTSIZE];
        
        hasher.Update(reinterpret_cast<const byte*>(message.c_str()), message.length());
        hasher.Final(digest);
        
        cout << "✓ SHA256 hash computation successful" << endl;
        
        // Print hash in hex
        cout << "Hash of 'test': ";
        for (int i = 0; i < SHA256::DIGESTSIZE; i++) {
            printf("%02x", digest[i]);
        }
        cout << endl;
        
        cout << "\n✓ BASIC CRYPTO++ OPERATIONS ARE WORKING!" << endl;
        cout << "The library build is OK. The problem is likely RSA-specific." << endl;
        
        return 0;
        
    } catch (const Exception& e) {
        cout << "✗ Crypto++ Exception: " << e.what() << endl;
        return 1;
    } catch (const exception& e) {
        cout << "✗ Standard Exception: " << e.what() << endl;
        return 1;
    } catch (...) {
        cout << "✗ Unknown Exception" << endl;
        return 1;
    }
}
