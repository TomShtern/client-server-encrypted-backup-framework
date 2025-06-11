#pragma once

#include <string>
#include <vector>
// #include <windows.h> // No longer needed
// #include <wincrypt.h> // No longer needed

// Crypto++ headers
#include "cryptlib.h"
#include "rsa.h"
#include "osrng.h"
#include "files.h"
#include "filters.h"
#include "sha.h"

// Forward declaration if necessary, or ensure MyCrypto namespace is used if these are part of it.
// For now, assuming they are in global or MyCrypto namespace is added in cpp.

namespace MyCrypto { // Assuming a namespace to match the original plan, if not, this can be removed.

class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 162; // Correct size for 1024-bit keys in DER format
    static const unsigned int BITS = 1024; // Full 1024-bit keys as required by server

private:
    CryptoPP::RSA::PublicKey publicKey; // Primary key storage
    CryptoPP::AutoSeededRandomPool rng;
    std::vector<char> keyData; // Can be used for loading or for temporary storage if needed.

    RSAPublicWrapper(const RSAPublicWrapper& other) = delete;
    RSAPublicWrapper& operator=(const RSAPublicWrapper& other) = delete;

public:
    // Construct from DER buffer
    RSAPublicWrapper(const char* key, size_t keylen);
    // Construct from file (DER or Base64)
    RSAPublicWrapper(const std::string& filename);
    ~RSAPublicWrapper();

    std::string getPublicKey();
    void getPublicKey(char* keyout, size_t keylen);

    std::string encrypt(const std::string& plain);
    std::string encrypt(const char* plain, size_t length);
};

class RSAPrivateWrapper {
public:
    static const unsigned int BITS = 1024; // Full 1024-bit keys as required by server

private:
    CryptoPP::RSA::PrivateKey privateKey;
    CryptoPP::RSA::PublicKey publicKey; // Corresponding public key
    CryptoPP::AutoSeededRandomPool rng;
    // HCRYPTPROV hProv; // Removed
    // HCRYPTKEY hKey; // Removed
    // std::vector<char> publicKeyData; // Removed
    // std::vector<char> privateKeyData; // Removed


    RSAPrivateWrapper(const RSAPrivateWrapper& other) = delete;
    RSAPrivateWrapper& operator=(const RSAPrivateWrapper& other) = delete;

public:
    // Generate new key
    RSAPrivateWrapper();
    // Load from DER buffer
    RSAPrivateWrapper(const char* key, size_t keylen);
    // Load from file (DER or Base64)
    RSAPrivateWrapper(const std::string& filename);
    ~RSAPrivateWrapper();

    std::string getPrivateKey();
    void getPrivateKey(char* keyout, size_t keylen);

    std::string getPublicKey();
    void getPublicKey(char* keyout, size_t keylen);

    std::string decrypt(const std::string& cipher);
    std::string decrypt(const char* cipher, size_t length);
};

} // namespace MyCrypto
