#pragma once

#include <string>
#include <vector>
#include <windows.h>
#include <wincrypt.h>

/**
 * @brief Wrapper for handling 1024-bit RSA public keys and encryption using Windows CryptoAPI.
 *
 * Provides methods to load a public key from a DER-encoded buffer or file, retrieve the key, and encrypt data using the loaded key.
 *
 * The class prevents copying to ensure secure key management.
 */
class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 162; // Correct size for 1024-bit keys in DER format
    static const unsigned int BITS = 1024; // Full 1024-bit keys as required by server

private:
    std::vector<char> keyData;

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

/**
 * @brief Wrapper for managing a 1024-bit RSA private key using Windows CryptoAPI.
 *
 * Provides functionality to generate, load, and manage RSA private keys, as well as retrieve public/private key data and decrypt ciphertexts. Keys can be generated, loaded from DER-encoded buffers, or loaded from files in DER or Base64 format.
 */
class RSAPrivateWrapper {
public:
    static const unsigned int BITS = 1024; // Full 1024-bit keys as required by server

private:
    HCRYPTPROV hProv;
    HCRYPTKEY hKey;
    std::vector<char> publicKeyData;
    std::vector<char> privateKeyData;

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
