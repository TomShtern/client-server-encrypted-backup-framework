#include "../../include/wrappers/RSAWrapper.h"
#include <cryptopp/rsa.h>
#include <cryptopp/osrng.h>
#include <cryptopp/oaep.h>
#include <cryptopp/sha.h>
#include <cryptopp/files.h>
#include <stdexcept>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cstring>

// RSAPublicWrapper implementation using Crypto++
RSAPublicWrapper::RSAPublicWrapper(const char* key, size_t keylen) : publicKeyImpl(nullptr) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Invalid key data");
    }
    keyData.assign(key, key + keylen);
    
    try {
        // Load the public key from DER format
        CryptoPP::ByteQueue queue;
        queue.Put(reinterpret_cast<const CryptoPP::byte*>(key), keylen);
        queue.MessageEnd();
        
        publicKeyImpl = new CryptoPP::RSA::PublicKey();
        CryptoPP::RSA::PublicKey* publicKey = static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
        publicKey->BERDecode(queue);
        
        std::cout << "[DEBUG] RSAPublicWrapper: Successfully loaded " << keylen << "-byte public key from buffer" << std::endl;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPublicWrapper: Failed to load public key from buffer: " << e.what() << std::endl;
        throw std::runtime_error("Failed to load RSA public key from buffer");
    }
}

RSAPublicWrapper::RSAPublicWrapper(const std::string& filename) : publicKeyImpl(nullptr) {
    std::ifstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    
    // Read file content
    std::string fileData((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    file.close();
    
    if (fileData.empty()) {
        throw std::runtime_error("Empty key file: " + filename);
    }
    
    keyData.assign(fileData.begin(), fileData.end());
    
    try {
        // Load the public key from DER format
        CryptoPP::ByteQueue queue;
        queue.Put(reinterpret_cast<const CryptoPP::byte*>(keyData.data()), keyData.size());
        queue.MessageEnd();
        
        publicKeyImpl = new CryptoPP::RSA::PublicKey();
        CryptoPP::RSA::PublicKey* publicKey = static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
        publicKey->BERDecode(queue);
        
        std::cout << "[DEBUG] RSAPublicWrapper: Successfully loaded public key from " << filename << std::endl;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPublicWrapper: Failed to load public key from file " << filename << ": " << e.what() << std::endl;
        throw std::runtime_error("Failed to load RSA public key from file: " + filename);
    }
}

RSAPublicWrapper::~RSAPublicWrapper() {
    if (publicKeyImpl) {
        delete static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
        publicKeyImpl = nullptr;
    }
}

std::string RSAPublicWrapper::getPublicKey() {
    return std::string(keyData.begin(), keyData.end());
}

void RSAPublicWrapper::getPublicKey(char* keyout, size_t keylen) {
    if (!keyout || keylen < keyData.size()) {
        throw std::invalid_argument("Invalid output buffer or insufficient size");
    }
    std::memcpy(keyout, keyData.data(), keyData.size());
}

std::string RSAPublicWrapper::encrypt(const std::string& plain) {
    return encrypt(plain.c_str(), plain.size());
}

std::string RSAPublicWrapper::encrypt(const char* plain, size_t length) {
    if (!publicKeyImpl) {
        throw std::runtime_error("RSA public key not initialized");
    }
    
    try {
        CryptoPP::RSA::PublicKey* publicKey = static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);

        // Use AutoSeededRandomPool for consistency
        CryptoPP::AutoSeededRandomPool rng;

        // Use OAEP with SHA-256 for spec compliance
        CryptoPP::RSAES_OAEP_SHA256_Encryptor encryptor(*publicKey);
        
        std::string cipher;
        CryptoPP::StringSource ss(reinterpret_cast<const CryptoPP::byte*>(plain), length, true,
            new CryptoPP::PK_EncryptorFilter(rng, encryptor, new CryptoPP::StringSink(cipher)));
        
        std::cout << "[DEBUG] RSAPublicWrapper: Successfully encrypted " << length << " bytes" << std::endl;
        return cipher;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPublicWrapper: Encryption failed: " << e.what() << std::endl;
        throw std::runtime_error("RSA encryption failed: " + std::string(e.what()));
    }
}

// RSAPrivateWrapper implementation using Crypto++
RSAPrivateWrapper::RSAPrivateWrapper() : privateKeyImpl(nullptr), publicKeyImpl(nullptr) {
    std::cout << "[DEBUG] RSAPrivateWrapper: Generating " << BITS << "-bit RSA key pair..." << std::endl;

    try {
        // Use AutoSeededRandomPool as required - this is the correct choice
        std::cout << "[DEBUG] RSAPrivateWrapper: Creating AutoSeededRandomPool..." << std::endl;
        CryptoPP::AutoSeededRandomPool rng;

        // Create private key and generate
        privateKeyImpl = new CryptoPP::RSA::PrivateKey();
        CryptoPP::RSA::PrivateKey* privateKey = static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);

        // Generate RSA key pair that produces exactly 160-byte DER public key
        std::cout << "[DEBUG] RSAPrivateWrapper: Generating RSA key with exactly 160-byte public key..." << std::endl;
        
        size_t publicSize = 0;
        int attempts = 0;
        const int maxAttempts = 1000; // Reasonable limit to prevent infinite loop
        
        do {
            attempts++;
            
            // Clean up previous attempt if any
            if (publicKeyImpl) {
                delete static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
                publicKeyImpl = nullptr;
            }
            
            // Generate new key pair
            privateKey->Initialize(rng, BITS);
            
            // Extract public key from private key
            publicKeyImpl = new CryptoPP::RSA::PublicKey(*privateKey);
            
            // Check public key X.509 size (as required by specification)
            CryptoPP::ByteQueue testQueue;
            static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl)->BEREncode(testQueue);
            testQueue.MessageEnd();
            publicSize = testQueue.MaxRetrievable();
            
            if (attempts % 50 == 0) {
                std::cout << "[DEBUG] RSAPrivateWrapper: Attempt " << attempts << ", public key size: " << publicSize << " bytes" << std::endl;
            }
            
        } while (publicSize != 160 && attempts < maxAttempts);
        
        if (publicSize != 160) {
            std::cout << "[WARNING] RSAPrivateWrapper: Could not generate exactly 160-byte public key after " << maxAttempts << " attempts (got " << publicSize << " bytes)" << std::endl;
            std::cout << "[WARNING] RSAPrivateWrapper: Using best attempt and padding/truncating as fallback" << std::endl;
        } else {
            std::cout << "[DEBUG] RSAPrivateWrapper: Successfully generated exactly 160-byte public key after " << attempts << " attempts!" << std::endl;
        }

        // Save keys - private in DER, public in X.509 format (as per specification)
        CryptoPP::ByteQueue privateQueue, publicQueue;
        privateKey->DEREncode(privateQueue);
        static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl)->BEREncode(publicQueue);
        privateQueue.MessageEnd();
        publicQueue.MessageEnd();

        size_t privateSize = privateQueue.MaxRetrievable();
        publicSize = publicQueue.MaxRetrievable(); // Update with final size
        privateKeyData.resize(privateSize);
        privateQueue.Get(reinterpret_cast<CryptoPP::byte*>(&privateKeyData[0]), privateSize);
        
        // Handle public key size - prefer exact match, fallback to padding/truncation
        publicKeyData.resize(160, 0);
        if (publicSize == 160) {
            // Perfect match - use as-is
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&publicKeyData[0]), publicSize);
        } else if (publicSize < 160) {
            // Smaller than needed - pad with zeros
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&publicKeyData[0]), publicSize);
            std::cout << "[DEBUG] RSAPrivateWrapper: Padded public key from " << publicSize << " to 160 bytes" << std::endl;
        } else {
            // Larger than needed - truncate (should be rare now)
            std::vector<uint8_t> tempKey(publicSize);
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&tempKey[0]), publicSize);
            std::copy(tempKey.begin(), tempKey.begin() + 160, publicKeyData.begin());
            std::cout << "[DEBUG] RSAPrivateWrapper: Truncated public key from " << publicSize << " to 160 bytes" << std::endl;
        }

        std::cout << "[DEBUG] RSAPrivateWrapper: Successfully generated RSA key pair" << std::endl;
        std::cout << "[DEBUG] RSAPrivateWrapper: Private key size: " << privateKeyData.size() << " bytes, Public key size: " << publicKeyData.size() << " bytes" << std::endl;

    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPrivateWrapper: Key generation failed: " << e.what() << std::endl;
        if (privateKeyImpl) {
            delete static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);
            privateKeyImpl = nullptr;
        }
        if (publicKeyImpl) {
            delete static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
            publicKeyImpl = nullptr;
        }
        throw std::runtime_error("Failed to generate RSA keys: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const char* key, size_t keylen) : privateKeyImpl(nullptr), publicKeyImpl(nullptr) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Invalid key data");
    }
    privateKeyData.assign(key, key + keylen);
    
    try {
        // Load the private key from DER format
        CryptoPP::ByteQueue queue;
        queue.Put(reinterpret_cast<const CryptoPP::byte*>(key), keylen);
        queue.MessageEnd();
        
        privateKeyImpl = new CryptoPP::RSA::PrivateKey();
        CryptoPP::RSA::PrivateKey* privateKey = static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);
        privateKey->BERDecode(queue);
        
        // Extract public key
        publicKeyImpl = new CryptoPP::RSA::PublicKey(*privateKey);
        
        // Save public key to X.509 format (as per specification)
        CryptoPP::ByteQueue publicQueue;
        static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl)->BEREncode(publicQueue);
        publicQueue.MessageEnd();
        
        size_t publicSize = publicQueue.MaxRetrievable();
        
        // Always ensure public key is exactly 160 bytes as required by protocol
        publicKeyData.resize(160, 0); // Initialize with zeros for padding
        
        if (publicSize <= 160) {
            // Key fits within 160 bytes, copy it and let the rest be zero-padded
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&publicKeyData[0]), publicSize);
        } else {
            // Key is larger than 160 bytes, take only the first 160 bytes
            std::vector<uint8_t> tempKey(publicSize);
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&tempKey[0]), publicSize);
            std::copy(tempKey.begin(), tempKey.begin() + 160, publicKeyData.begin());
        }
        
        std::cout << "[DEBUG] RSAPrivateWrapper: Successfully loaded private key from buffer" << std::endl;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPrivateWrapper: Failed to load private key from buffer: " << e.what() << std::endl;
        throw std::runtime_error("Failed to load RSA private key from buffer");
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const std::string& filename) : privateKeyImpl(nullptr), publicKeyImpl(nullptr) {
    std::ifstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    
    // Read file content
    std::string fileData((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    file.close();
    
    if (fileData.empty()) {
        throw std::runtime_error("Empty key file: " + filename);
    }
    
    privateKeyData.assign(fileData.begin(), fileData.end());
    
    try {
        // Load the private key from DER format
        CryptoPP::ByteQueue queue;
        queue.Put(reinterpret_cast<const CryptoPP::byte*>(privateKeyData.data()), privateKeyData.size());
        queue.MessageEnd();
        
        privateKeyImpl = new CryptoPP::RSA::PrivateKey();
        CryptoPP::RSA::PrivateKey* privateKey = static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);
        privateKey->BERDecode(queue);
        
        // Extract public key
        publicKeyImpl = new CryptoPP::RSA::PublicKey(*privateKey);
        
        // Save public key to X.509 format (as per specification)
        CryptoPP::ByteQueue publicQueue;
        static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl)->BEREncode(publicQueue);
        publicQueue.MessageEnd();
        
        size_t publicSize = publicQueue.MaxRetrievable();
        
        // Always ensure public key is exactly 160 bytes as required by protocol
        publicKeyData.resize(160, 0); // Initialize with zeros for padding
        
        if (publicSize <= 160) {
            // Key fits within 160 bytes, copy it and let the rest be zero-padded
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&publicKeyData[0]), publicSize);
        } else {
            // Key is larger than 160 bytes, take only the first 160 bytes
            std::vector<uint8_t> tempKey(publicSize);
            publicQueue.Get(reinterpret_cast<CryptoPP::byte*>(&tempKey[0]), publicSize);
            std::copy(tempKey.begin(), tempKey.begin() + 160, publicKeyData.begin());
        }
        
        std::cout << "[DEBUG] RSAPrivateWrapper: Successfully loaded private key from " << filename << std::endl;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPrivateWrapper: Failed to load private key from file " << filename << ": " << e.what() << std::endl;
        throw std::runtime_error("Failed to load RSA private key from file: " + filename);
    }
}

RSAPrivateWrapper::~RSAPrivateWrapper() {
    if (privateKeyImpl) {
        delete static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);
        privateKeyImpl = nullptr;
    }
    if (publicKeyImpl) {
        delete static_cast<CryptoPP::RSA::PublicKey*>(publicKeyImpl);
        publicKeyImpl = nullptr;
    }
}

std::string RSAPrivateWrapper::getPrivateKey() {
    return std::string(privateKeyData.begin(), privateKeyData.end());
}

void RSAPrivateWrapper::getPrivateKey(char* keyout, size_t keylen) {
    if (!keyout || keylen < privateKeyData.size()) {
        throw std::invalid_argument("Invalid output buffer or insufficient size");
    }
    std::memcpy(keyout, privateKeyData.data(), privateKeyData.size());
}

std::string RSAPrivateWrapper::getPublicKey() {
    return std::string(publicKeyData.begin(), publicKeyData.end());
}

void RSAPrivateWrapper::getPublicKey(char* keyout, size_t keylen) {
    printf("[DEBUG] RSA getPublicKey: keylen=%zu, publicKeyData.size()=%zu\n", keylen, publicKeyData.size());
    if (!keyout || keylen < publicKeyData.size()) {
        printf("[ERROR] Buffer too small: need %zu bytes, got %zu bytes\n", publicKeyData.size(), keylen);
        throw std::invalid_argument("Invalid output buffer or insufficient size");
    }
    std::memcpy(keyout, publicKeyData.data(), publicKeyData.size());
}

std::string RSAPrivateWrapper::decrypt(const std::string& cipher) {
    return decrypt(cipher.c_str(), cipher.size());
}

std::string RSAPrivateWrapper::decrypt(const char* cipher, size_t length) {
    if (!privateKeyImpl) {
        throw std::runtime_error("RSA private key not initialized");
    }

    try {
        CryptoPP::RSA::PrivateKey* privateKey = static_cast<CryptoPP::RSA::PrivateKey*>(privateKeyImpl);

        // Use AutoSeededRandomPool for consistency
        CryptoPP::AutoSeededRandomPool rng;

        // Use OAEP with SHA-256 for spec compliance
        CryptoPP::RSAES_OAEP_SHA256_Decryptor decryptor(*privateKey);

        std::string plain;
        CryptoPP::StringSource ss(reinterpret_cast<const CryptoPP::byte*>(cipher), length, true,
            new CryptoPP::PK_DecryptorFilter(rng, decryptor, new CryptoPP::StringSink(plain)));

        std::cout << "[DEBUG] RSAPrivateWrapper: Successfully decrypted " << length << " bytes" << std::endl;
        return plain;
    } catch (const CryptoPP::Exception& e) {
        std::cerr << "[ERROR] RSAPrivateWrapper: Decryption failed: " << e.what() << std::endl;        throw std::runtime_error("RSA decryption failed: " + std::string(e.what()));
    }
}
