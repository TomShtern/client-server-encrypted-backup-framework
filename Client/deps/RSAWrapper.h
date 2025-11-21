#pragma once

#include <string>
#include <vector>

// Forward declarations for Crypto++ classes
// Using opaque pointers to avoid header dependencies

class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 160; // Spec-compliant: 160 bytes for RSA public key in DER format
    static const unsigned int BITS = 1024; // 1024-bit keys as required by server

private:
    std::vector<char> keyData;
    void* publicKeyImpl; // Opaque pointer to CryptoPP::RSA::PublicKey

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
    static const unsigned int BITS = 1024; // 1024-bit keys as required by server

private:
    std::vector<char> privateKeyData;
    std::vector<char> publicKeyData;
    void* privateKeyImpl; // Opaque pointer to CryptoPP::RSA::PrivateKey
    void* publicKeyImpl;  // Opaque pointer to CryptoPP::RSA::PublicKey

    RSAPrivateWrapper(const RSAPrivateWrapper& other) = delete;
    RSAPrivateWrapper& operator=(const RSAPrivateWrapper& other) = delete;

    // Helper methods for key management
    bool loadExistingKeys();
    void saveKeysToData();
    void saveKeysToFiles();

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
