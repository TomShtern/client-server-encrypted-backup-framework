#include "RSAWrapper.h"
#include <cryptopp/rsa.h>
#include <cryptopp/osrng.h>
#include <cryptopp/pssr.h>
#include <cryptopp/oaep.h>
#include <cryptopp/filters.h>
#include <cryptopp/hex.h>
#include <cryptopp/queue.h>
#include <cryptopp/integer.h>
#include <cryptopp/base64.h>
#include <fstream>
#include <stdexcept>

using namespace CryptoPP;

// RSAPublicWrapper implementation
RSAPublicWrapper::RSAPublicWrapper(const char* key, size_t keylen) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Invalid key data");
    }
    
    try {
        // Parse the key from DER format
        StringSource ss(reinterpret_cast<const unsigned char*>(key), keylen, true);
        publicKey.Load(ss);
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to load RSA public key: " + std::string(e.what()));
    }
}

RSAPublicWrapper::RSAPublicWrapper(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    
    // Read file content
    std::string keyData((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    file.close();
    
    if (keyData.empty()) {
        throw std::runtime_error("Empty key file: " + filename);
    }
    
    try {
        // Try to decode as Base64 first
        std::string decoded;
        StringSource ss(keyData, true,
            new Base64Decoder(new StringSink(decoded))
        );
        
        // Load the decoded key
        StringSource keySource(decoded, true);
        publicKey.Load(keySource);
    } catch (const Exception&) {
        try {
            // If Base64 decoding fails, try direct DER
            StringSource ss(keyData, true);
            publicKey.Load(ss);
        } catch (const Exception& e) {
            throw std::runtime_error("Failed to load RSA public key from file: " + std::string(e.what()));
        }
    }
}

RSAPublicWrapper::~RSAPublicWrapper() = default;

std::string RSAPublicWrapper::encrypt(const std::string& plain) {
    if (plain.empty()) {
        throw std::invalid_argument("Cannot encrypt empty data");
    }
    
    try {
        AutoSeededRandomPool rng;
        std::string ciphertext;
        
        RSAES_OAEP_SHA_Encryptor encryptor(publicKey);
        
        StringSource ss(plain, true,
            new PK_EncryptorFilter(rng, encryptor,
                new StringSink(ciphertext)
            )
        );
        
        return ciphertext;
    } catch (const Exception& e) {
        throw std::runtime_error("RSA encryption failed: " + std::string(e.what()));
    }
}

std::string RSAPublicWrapper::encrypt(const char* plain, size_t length) {
    if (!plain || length == 0) {
        throw std::invalid_argument("Cannot encrypt empty data");
    }
    
    try {
        AutoSeededRandomPool rng;
        std::string ciphertext;
        
        RSAES_OAEP_SHA_Encryptor encryptor(publicKey);
        
        StringSource ss(reinterpret_cast<const unsigned char*>(plain), length, true,
            new PK_EncryptorFilter(rng, encryptor,
                new StringSink(ciphertext)
            )
        );
        
        return ciphertext;
    } catch (const Exception& e) {
        throw std::runtime_error("RSA encryption failed: " + std::string(e.what()));
    }
}

void RSAPublicWrapper::getPublicKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer");
    }
    
    try {
        std::string keyData;
        StringSink ss(keyData);
        publicKey.Save(ss);
        
        if (keyData.size() > keylen) {
            throw std::runtime_error("Output buffer too small");
        }
        
        std::memcpy(keyout, keyData.c_str(), keyData.size());
        if (keyData.size() < keylen) {
            keyout[keyData.size()] = '\0';
        }
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export public key: " + std::string(e.what()));
    }
}

std::string RSAPublicWrapper::getPublicKey() {
    try {
        std::string keyData;
        StringSink ss(keyData);
        publicKey.Save(ss);
        return keyData;
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export public key: " + std::string(e.what()));
    }
}

// RSAPrivateWrapper implementation
RSAPrivateWrapper::RSAPrivateWrapper() {
    try {
        AutoSeededRandomPool rng;
        privateKey.GenerateRandomWithKeySize(rng, RSAPrivateWrapper::BITS);
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to generate RSA key pair: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const char* key, size_t keylen) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Invalid key data");
    }
    
    try {
        // Parse the key from DER format
        StringSource ss(reinterpret_cast<const unsigned char*>(key), keylen, true);
        privateKey.Load(ss);
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to load RSA private key: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    
    // Read file content
    std::string keyData((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    file.close();
    
    if (keyData.empty()) {
        throw std::runtime_error("Empty key file: " + filename);
    }
    
    try {
        // Try to decode as Base64 first
        std::string decoded;
        StringSource ss(keyData, true,
            new Base64Decoder(new StringSink(decoded))
        );
        
        // Load the decoded key
        StringSource keySource(decoded, true);
        privateKey.Load(keySource);
    } catch (const Exception&) {
        try {
            // If Base64 decoding fails, try direct DER
            StringSource ss(keyData, true);
            privateKey.Load(ss);
        } catch (const Exception& e) {
            throw std::runtime_error("Failed to load RSA private key from file: " + std::string(e.what()));
        }
    }
}

RSAPrivateWrapper::~RSAPrivateWrapper() = default;

std::string RSAPrivateWrapper::decrypt(const std::string& cipher) {
    if (cipher.empty()) {
        throw std::invalid_argument("Cannot decrypt empty data");
    }
    
    try {
        AutoSeededRandomPool rng;
        std::string plaintext;
        
        RSAES_OAEP_SHA_Decryptor decryptor(privateKey);
        
        StringSource ss(cipher, true,
            new PK_DecryptorFilter(rng, decryptor,
                new StringSink(plaintext)
            )
        );
        
        return plaintext;
    } catch (const Exception& e) {
        throw std::runtime_error("RSA decryption failed: " + std::string(e.what()));
    }
}

std::string RSAPrivateWrapper::decrypt(const char* cipher, size_t length) {
    if (!cipher || length == 0) {
        throw std::invalid_argument("Cannot decrypt empty data");
    }
    
    try {
        AutoSeededRandomPool rng;
        std::string plaintext;
        
        RSAES_OAEP_SHA_Decryptor decryptor(privateKey);
        
        StringSource ss(reinterpret_cast<const unsigned char*>(cipher), length, true,
            new PK_DecryptorFilter(rng, decryptor,
                new StringSink(plaintext)
            )
        );
        
        return plaintext;
    } catch (const Exception& e) {
        throw std::runtime_error("RSA decryption failed: " + std::string(e.what()));
    }
}

void RSAPrivateWrapper::getPrivateKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer");
    }
    
    try {
        std::string keyData;
        StringSink ss(keyData);
        privateKey.Save(ss);
        
        if (keyData.size() > keylen) {
            throw std::runtime_error("Output buffer too small");
        }
        
        std::memcpy(keyout, keyData.c_str(), keyData.size());
        if (keyData.size() < keylen) {
            keyout[keyData.size()] = '\0';
        }
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export private key: " + std::string(e.what()));
    }
}

std::string RSAPrivateWrapper::getPrivateKey() {
    try {
        std::string keyData;
        StringSink ss(keyData);
        privateKey.Save(ss);
        return keyData;
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export private key: " + std::string(e.what()));
    }
}

void RSAPrivateWrapper::getPublicKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer");
    }
    
    try {
        RSA::PublicKey derivedPublicKey(privateKey);
        std::string keyData;
        StringSink ss(keyData);
        derivedPublicKey.Save(ss);
        
        if (keyData.size() > keylen) {
            throw std::runtime_error("Output buffer too small");
        }
        
        std::memcpy(keyout, keyData.c_str(), keyData.size());
        if (keyData.size() < keylen) {
            keyout[keyData.size()] = '\0';
        }
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export public key: " + std::string(e.what()));
    }
}

std::string RSAPrivateWrapper::getPublicKey() {
    try {
        RSA::PublicKey derivedPublicKey(privateKey);
        std::string keyData;
        StringSink ss(keyData);
        derivedPublicKey.Save(ss);
        return keyData;
    } catch (const Exception& e) {
        throw std::runtime_error("Failed to export public key: " + std::string(e.what()));
    }
}