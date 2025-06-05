#pragma once

#include <string>
#include <vector>
#include <windows.h>
#include <wincrypt.h>

class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 80; // Reduced for 512-bit keys
    static const unsigned int BITS = 512; // Reduced for faster testing

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

class RSAPrivateWrapper {
public:
    static const unsigned int BITS = 512; // Reduced for faster testing

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
