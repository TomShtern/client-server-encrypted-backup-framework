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

/**
 * @brief Prints binary data as a C-style unsigned char array in hexadecimal format.
 *
 * Formats the input data as a C array declaration with the specified variable name, displaying 16 bytes per line. Outputs the total size of the array as a comment.
 *
 * @param data Binary data to be printed as a hex array.
 * @param varName Name to use for the generated C array variable.
 */
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

/**
 * @brief Generates and exports a minimal valid RSA private key using fixed small primes.
 *
 * Constructs an RSA private key with small, known prime numbers to ensure fast and deterministic generation. The key is exported in DER format, printed as a C-style unsigned char array, and verified by reloading it. Designed for hardcoding a valid RSA key in test environments.
 *
 * @return int Returns 0 on success, or 1 if an exception occurs.
 */
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
