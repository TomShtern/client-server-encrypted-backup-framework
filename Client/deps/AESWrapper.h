#pragma once

#include <string>
#include <vector>

class AESWrapper
{
public:
    static const unsigned int DEFAULT_KEYLENGTH = 32;  // AES-256 requires 32-byte keys
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
