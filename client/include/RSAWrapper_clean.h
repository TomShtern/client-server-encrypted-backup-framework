#pragma once

#include "../../crypto++/osrng.h"
#include "../../crypto++/rsa.h"
#include <string>

/**
 * @brief Encapsulates RSA public key operations using the Crypto++ library.
 *
 * Provides methods for initializing an RSA public key from serialized data, retrieving the public key, and encrypting data using the public key. Copy construction and assignment are disabled.
 */
class RSAPublicWrapper
{
public:
    static const unsigned int KEYSIZE = 160;
    static const unsigned int BITS = 1024;

private:
    CryptoPP::AutoSeededRandomPool _rng;
    CryptoPP::RSA::PublicKey publicKey;

    RSAPublicWrapper(const RSAPublicWrapper& rsapublic);
    RSAPublicWrapper& operator=(const RSAPublicWrapper& rsapublic);

public:
    RSAPublicWrapper(const char* key, size_t length);
    RSAPublicWrapper(const std::string& key);
    ~RSAPublicWrapper();

    std::string getPublicKey() const;
    void getPublicKey(char* keyout, size_t length) const;

    std::string encrypt(const std::string& plain);
    std::string encrypt(const char* plain, size_t length);
};

/**
 * @brief Encapsulates RSA private key operations, including key management and decryption.
 *
 * Provides functionality to generate or load an RSA private key, retrieve the private and corresponding public keys, and decrypt ciphertext using the private key. Keys can be serialized to or deserialized from strings or raw buffers.
 */
class RSAPrivateWrapper
{
public:
    static const unsigned int BITS = 1024;

private:
    CryptoPP::AutoSeededRandomPool _rng;
    CryptoPP::RSA::PrivateKey privateKey;

    RSAPrivateWrapper(const RSAPrivateWrapper& rsaprivate);
    RSAPrivateWrapper& operator=(const RSAPrivateWrapper& rsaprivate);

public:
    RSAPrivateWrapper();
    RSAPrivateWrapper(const char* key, size_t length);
    RSAPrivateWrapper(const std::string& key);
    ~RSAPrivateWrapper();

    std::string getPrivateKey() const;
    void getPrivateKey(char* keyout, size_t length) const;

    std::string getPublicKey() const;
    void getPublicKey(char* keyout, size_t length) const;

    std::string decrypt(const std::string& cipher);
    std::string decrypt(const char* cipher, size_t length);
};
