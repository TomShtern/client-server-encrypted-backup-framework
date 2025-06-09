#pragma once

#include <string>
#include <vector>

/**
 * @brief AES encryption and decryption utility class.
 *
 * Provides methods for AES key generation, encryption, and decryption using a configurable key and initialization vector (IV).
 *
 * The class supports generating random AES keys, encrypting and decrypting data buffers, and retrieving the internal key. Optionally, a static IV of all zeros can be used for protocol compliance.
 */
class AESWrapper
{
public:
    static const unsigned int DEFAULT_KEYLENGTH = 16;
private:
    std::vector<unsigned char> keyData;
    std::vector<unsigned char> iv;
    AESWrapper(const AESWrapper& aes);
public:
    static void generateKey(unsigned char* buffer, size_t length);

    AESWrapper() = default;
    // New: allow static IV of all zeros for protocol compliance
    AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV = false);
    ~AESWrapper();

    const unsigned char* getKey() const;

    std::string encrypt(const char* plain, size_t length);
    std::string decrypt(const char* cipher, size_t length);
};
