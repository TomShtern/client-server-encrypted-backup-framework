// Simple RSA key generator using only minimal crypto operations
#include <iostream>
#include <string>
#include <iomanip>

// Use the same include approach as the main project
#include "crypto++/rsa.h"
#include "crypto++/osrng.h"
#include "crypto++/filters.h"

using namespace CryptoPP;
using namespace std;

void printAsHexArray(const string& data, const string& varName) {
    cout << "unsigned char " << varName << "[] = {" << endl;
    for (size_t i = 0; i < data.size(); i++) {
        if (i % 16 == 0) cout << "    ";
        cout << "0x" << hex << setfill('0') << setw(2) << (unsigned char)data[i];
        if (i < data.size() - 1) cout << ", ";
        if (i % 16 == 15 || i == data.size() - 1) cout << endl;
    }
    cout << "};" << endl;
    cout << "// Size: " << dec << data.size() << " bytes" << endl;
}

int main() {
    try {
        cout << "=== Generating Valid RSA Key for Hardcoding ===" << endl;
        
        // Use a very simple approach - create a minimal key with known small primes
        // This avoids the hanging issue by using predictable small values
        
        RSA::PrivateKey privateKey;
        
        // Use small but valid primes to avoid computational issues
        // p=61, q=53, n=3233, φ(n)=3120
        // e=17 (common choice), d=2753 (calculated: 17 * 2753 ≡ 1 mod 3120)
        
        Integer p("61");    // Small prime
        Integer q("53");    // Small prime  
        Integer n = p * q;  // n = 3233
        Integer phi = (p-1) * (q-1);  // φ(n) = 3120
        Integer e("17");    // Common small exponent
        
        cout << "Computing private exponent..." << endl;
        Integer d = e.InverseMod(phi);  // Calculate d
        
        cout << "  p = " << p << endl;
        cout << "  q = " << q << endl;
        cout << "  n = " << n << endl;
        cout << "  e = " << e << endl;
        cout << "  d = " << d << endl;
        
        // Calculate CRT values
        Integer dp = d % (p-1);
        Integer dq = d % (q-1);
        Integer qinv = q.InverseMod(p);
        
        cout << "Initializing RSA key..." << endl;
        privateKey.Initialize(n, e, d, p, q, dp, dq, qinv);
        
        cout << "✓ RSA key initialized successfully" << endl;
        
        // Export to DER format
        string derData;
        StringSink ss(derData);
        privateKey.Save(ss);
        
        cout << "✓ DER export successful" << endl;
        cout << "DER size: " << derData.size() << " bytes" << endl;
        
        // Print as C array
        cout << "\n=== VALID RSA KEY FOR HARDCODING ===" << endl;
        printAsHexArray(derData, "validRSAKey");
        
        // Test loading it back
        cout << "\n=== Testing Key Loading ===" << endl;
        RSA::PrivateKey testKey;
        StringSource source(derData, true);
        testKey.Load(source);
        cout << "✓ Key loading test successful" << endl;
        
        cout << "\n✓ SUCCESS: This key data can be used to replace the invalid hardcoded key!" << endl;
        
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
