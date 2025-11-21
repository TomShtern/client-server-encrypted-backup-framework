#pragma once

#include <string>
#include <vector>
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")

class RSAPublicWrapperCNG {
public:
    static const unsigned int KEYSIZE = 160; // Spec-compliant: 160 bytes for RSA public key in DER format
    static const unsigned int BITS = 1024;   // 1024-bit keys as required by server

private:
    BCRYPT_KEY_HANDLE hPublicKey;
    std::vector<char> keyData;

    RSAPublicWrapperCNG(const RSAPublicWrapperCNG& other) = delete;
    RSAPublicWrapperCNG& operator=(const RSAPublicWrapperCNG& other) = delete;

public:
    // Construct from DER buffer
    RSAPublicWrapperCNG(const char* key, size_t keylen);
    // Construct from file (DER format)
    RSAPublicWrapperCNG(const std::string& filename);
    ~RSAPublicWrapperCNG();

    std::string getPublicKey();
    void getPublicKey(char* keyout, size_t keylen);

    std::string encrypt(const std::string& plain);
    std::string encrypt(const char* plain, size_t length);
};

class RSAPrivateWrapperCNG {
public:
    static const unsigned int BITS = 1024; // 1024-bit keys as required by server

private:
    BCRYPT_KEY_HANDLE hPrivateKey;
    BCRYPT_KEY_HANDLE hPublicKey;
    std::vector<char> publicKeyData;
    std::vector<char> privateKeyData;

    RSAPrivateWrapperCNG(const RSAPrivateWrapperCNG& other) = delete;
    RSAPrivateWrapperCNG& operator=(const RSAPrivateWrapperCNG& other) = delete;

public:
    // Generate new key
    RSAPrivateWrapperCNG();
    // Load from DER buffer
    RSAPrivateWrapperCNG(const char* key, size_t keylen);
    // Load from file (DER format)
    RSAPrivateWrapperCNG(const std::string& filename);
    ~RSAPrivateWrapperCNG();

    std::string getPrivateKey();
    void getPrivateKey(char* keyout, size_t keylen);

    std::string getPublicKey();
    void getPublicKey(char* keyout, size_t keylen);

    std::string decrypt(const std::string& cipher);
    std::string decrypt(const char* cipher, size_t length);
};
