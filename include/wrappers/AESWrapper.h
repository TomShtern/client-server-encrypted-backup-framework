#pragma once

#include <string>
#include <vector>

// It's good practice to include Crypto++ headers needed by the interface if any,
// or forward declare types. Here, no Crypto++ types are directly in the public interface.
// #include "modes.h" // For AES::BLOCKSIZE, if it were used in header
// #include "aes.h"   // For AES itself

namespace MyCrypto { // Added for consistency

class AESWrapper
{
public:
    static const unsigned int DEFAULT_KEYLENGTH = 32; // Changed to 32
    static const unsigned int BLOCKSIZE = 16; // AES block size is 16 bytes

private:
    std::vector<unsigned char> keyData;
    std::vector<unsigned char> iv; // IV will be static (all zeros) if useStaticZeroIV is true

    // Making class non-copyable is good practice if not intended.
    // The private copy constructor already achieves this.
    AESWrapper(const AESWrapper& aes);
    // AESWrapper& operator=(const AESWrapper&); // Also consider assignment operator

public:
    // Generates a key of specified length.
    static void generateKey(unsigned char* buffer, size_t length = DEFAULT_KEYLENGTH);

    AESWrapper() = default; // Default constructor might need adjustment if members can't be default-initialized meaningfully

    // Constructor: key is the symmetric key, keyLength is its size in bytes.
    // useStaticZeroIV: if true, uses an IV of all zeros (required by project spec).
    //                  if false (default, though spec says true), generates a random IV.
    AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV = true); // Defaulted useStaticZeroIV to true
    ~AESWrapper();

    const unsigned char* getKey() const; // Returns pointer to key data

    // Encrypts plain text, returns cipher text.
    std::string encrypt(const char* plain, size_t length);
    // Decrypts cipher text, returns plain text.
    std::string decrypt(const char* cipher, size_t length);
};

} // namespace MyCrypto
