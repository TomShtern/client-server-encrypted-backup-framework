#pragma once

#include <string>
#include <vector>

// Forward declarations for Crypto++ classes
namespace CryptoPP {
    class RSA;
    namespace RSA {
        class PublicKey;
        class PrivateKey;
    }
}

class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 162; // Size for 1024-bit keys in DER format
    static const unsigned int BITS = 1024; // 1024-bit keys as required by server

private:
    std::vector<char> keyData;
    CryptoPP::RSA::PublicKey publicKey;

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
    std::vector<char> publicKeyData;
    std::vector<char> privateKeyData;
    CryptoPP::RSA::PrivateKey privateKey;
    CryptoPP::RSA::PublicKey publicKey;

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
