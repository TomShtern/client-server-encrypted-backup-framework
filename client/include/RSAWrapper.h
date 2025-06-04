#pragma once

#include <string>
#include <vector>
#include "../../crypto++/rsa.h"
#include "../../crypto++/osrng.h"

class RSAPublicWrapper {
public:
    static const unsigned int KEYSIZE = 160;
    static const unsigned int BITS = 1024;

private:
    CryptoPP::AutoSeededRandomPool _rng;
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
    static const unsigned int BITS = 1024;

private:
    CryptoPP::AutoSeededRandomPool _rng;
    CryptoPP::RSA::PrivateKey privateKey;

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
