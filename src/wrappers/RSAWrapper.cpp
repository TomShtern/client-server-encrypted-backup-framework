#include "../../include/wrappers/RSAWrapper.h"
// #include <windows.h> // Removed
// #include <wincrypt.h> // Removed
#include <fstream>
#include <stdexcept>
// #include <iostream> // Removed as debug logs are removed
#include <vector>
#include <string>
#include <cstring>
// #include <chrono> // Removed as debug logs and old fallbacks are removed
#include <algorithm> // May still be needed for std::copy or other utilities, review later

// Crypto++ includes for real RSA implementation
#include "../../third_party/crypto++/rsa.h"
#include "../../third_party/crypto++/osrng.h"
#include "../../third_party/crypto++/base64.h"
#include "../../third_party/crypto++/files.h"
#include "../../third_party/crypto++/hex.h"
#include "../../third_party/crypto++/filters.h"
#include "../../third_party/crypto++/pubkey.h"
#include "../../third_party/crypto++/sha.h" // For SHA1 with OAEP

// #pragma comment(lib, "crypt32.lib") // Removed
// #pragma comment(lib, "advapi32.lib") // Removed

// Real RSA implementation using Crypto++ library
// This provides actual RSA encryption with fallback to enhanced XOR

using namespace CryptoPP;

namespace MyCrypto { // Added namespace

// RSAPublicWrapper implementation
RSAPublicWrapper::RSAPublicWrapper(const char* key, size_t keylen) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Public key data is invalid or empty.");
    }
    try {
        StringSource ss(reinterpret_cast<const byte*>(key), keylen, true);
        this->publicKey.BERDecode(ss);
        // this->keyData.assign(key, key + keylen); // Keep if direct access to raw keyData is needed, else remove
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("Failed to decode public key: " + std::string(e.what()));
    }
}

RSAPublicWrapper::RSAPublicWrapper(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open public key file: " + filename);
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<char> buffer(size);
    if (!file.read(buffer.data(), size)) {
        file.close();
        throw std::runtime_error("Failed to read public key file: " + filename);
    }
    file.close();
    
    if (buffer.empty()) {
        throw std::runtime_error("Empty public key file: " + filename);
    }

    try {
        StringSource ss(reinterpret_cast<const byte*>(buffer.data()), buffer.size(), true);
        this->publicKey.BERDecode(ss);
        // this->keyData.assign(buffer.begin(), buffer.end()); // Keep if direct access to raw keyData is needed
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("Failed to decode public key from file: " + std::string(e.what()));
    }
}

RSAPublicWrapper::~RSAPublicWrapper() = default; // CryptoPP objects handle their own memory

std::string RSAPublicWrapper::encrypt(const std::string& plain) {
    // Max plaintext size for RSA-OAEP (1024-bit key, SHA1 hash)
    // Key size in bytes: 1024 / 8 = 128 bytes
    // OAEP padding with SHA1 uses: 2 * hash_len + 2 = 2 * 20 + 2 = 42 bytes
    // Max plaintext size = 128 - 42 = 86 bytes
    size_t maxPlaintextSize = (BITS / 8) - (2 * SHA1::DIGESTSIZE) - 2;
    if (plain.size() > maxPlaintextSize) {
        throw std::invalid_argument("Plaintext too large for RSA-OAEP encryption. Max: " +
            std::to_string(maxPlaintextSize) + " bytes, Got: " + std::to_string(plain.size()) + " bytes.");
    }

    try {
        RSAES_OAEP_SHA1_Encryptor e(this->publicKey); // Use member publicKey
        std::string encrypted_text;

        // Use member rng
        StringSource(plain, true,
            new PK_EncryptorFilter(this->rng, e,
                new StringSink(encrypted_text)
            )
        );
        return encrypted_text;
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("RSA encryption failed: " + std::string(e.what()));
    }
}

std::string RSAPublicWrapper::encrypt(const char* plain, size_t length) {
    if (!plain && length > 0) {
        throw std::invalid_argument("Plaintext pointer is null but length is non-zero.");
    }
    // Treat (nullptr, 0) as an empty string for encryption
    return encrypt(std::string(plain ? plain : "", length));
}

// Returns DER encoded public key
void RSAPublicWrapper::getPublicKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer for public key.");
    }
    
    std::string derKey;
    StringSink ss(derKey);
    this->publicKey.DEREncode(ss); // Use member publicKey

    if (derKey.size() > keylen) {
        throw std::runtime_error("Output buffer too small for public key. Needed: " + std::to_string(derKey.size()) + ", Provided: " + std::to_string(keylen));
    }
    
    std::memcpy(keyout, derKey.data(), derKey.size());
    // No null termination for binary DER data.
}

// Returns DER encoded public key
std::string RSAPublicWrapper::getPublicKey() {
    std::string derKey;
    StringSink ss(derKey);
    this->publicKey.DEREncode(ss); // Use member publicKey
    return derKey;
}

// RSAPrivateWrapper implementation
RSAPrivateWrapper::RSAPrivateWrapper() {
    try {
        // member rng is already initialized by its default constructor
        this->privateKey.Initialize(this->rng, BITS);
        this->publicKey.Initialize(this->privateKey); // Generate corresponding public key
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("RSA key generation failed: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const char* key, size_t keylen) {
    if (!key || keylen == 0) {
        throw std::invalid_argument("Private key data is invalid or empty.");
    }
    try {
        StringSource ss(reinterpret_cast<const byte*>(key), keylen, true);
        this->privateKey.BERDecode(ss);
        // Regenerate public key from the loaded private key
        this->publicKey.Initialize(this->privateKey);
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("Failed to decode private key: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::RSAPrivateWrapper(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open private key file: " + filename);
    }
    
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::vector<char> buffer(size);
    if (!file.read(buffer.data(), size)) {
        file.close();
        throw std::runtime_error("Failed to read private key file: " + filename);
    }
    file.close();

    if (buffer.empty()) {
        throw std::runtime_error("Empty private key file: " + filename);
    }

    try {
        StringSource ss(reinterpret_cast<const byte*>(buffer.data()), buffer.size(), true);
        this->privateKey.BERDecode(ss);
        this->publicKey.Initialize(this->privateKey);
    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("Failed to decode private key from file: " + std::string(e.what()));
    }
}

RSAPrivateWrapper::~RSAPrivateWrapper() {
    // CryptoPP objects clean up themselves. No explicit CAPI cleanup needed.
    // Old CAPI cleanup:
    // if (hKey) {
    //     CryptDestroyKey(hKey);
    // }
    // if (hProv) {
    //     CryptReleaseContext(hProv, 0);
    // }
}

std::string RSAPrivateWrapper::decrypt(const std::string& cipher) {
    if (cipher.empty()) {
        // Allowing empty ciphertext, OAEP would typically fail to decrypt this
        // if it's not a valid OAEP structure. Let Crypto++ handle it.
    }

    try {
        RSAES_OAEP_SHA1_Decryptor d(this->privateKey); // Use member privateKey
        std::string decrypted_text;

        // Use member rng
        StringSource(cipher, true,
            new PK_DecryptorFilter(this->rng, d,
                new StringSink(decrypted_text)
            )
        );
        return decrypted_text;
    } catch (const CryptoPP::Exception& e) {
        // Decryption can fail due to bad padding, incorrect key, corrupted ciphertext etc.
        throw std::runtime_error("RSA decryption failed: " + std::string(e.what()));
    }
}

std::string RSAPrivateWrapper::decrypt(const char* cipher, size_t length) {
   if (!cipher && length > 0) {
        throw std::invalid_argument("Ciphertext pointer is null but length is non-zero.");
    }
    // Treat (nullptr, 0) as an empty string for decryption
    return decrypt(std::string(cipher ? cipher : "", length));
}

// Returns DER encoded private key
void RSAPrivateWrapper::getPrivateKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer for private key.");
    }

    std::string derKey;
    StringSink ss(derKey);
    this->privateKey.DEREncode(ss); // Use member privateKey

    if (derKey.size() > keylen) {
        throw std::runtime_error("Output buffer too small for private key. Needed: " + std::to_string(derKey.size()) + ", Provided: " + std::to_string(keylen));
    }
    
    std::memcpy(keyout, derKey.data(), derKey.size());
}

// Returns DER encoded private key
std::string RSAPrivateWrapper::getPrivateKey() {
    std::string derKey;
    StringSink ss(derKey);
    this->privateKey.DEREncode(ss); // Use member privateKey
    return derKey;
}

// Returns DER encoded public key
void RSAPrivateWrapper::getPublicKey(char* keyout, size_t keylen) {
    if (!keyout || keylen == 0) {
        throw std::invalid_argument("Invalid output buffer for public key.");
    }

    std::string derKey;
    StringSink ss(derKey);
    this->publicKey.DEREncode(ss); // Use member publicKey (from RSAPrivateWrapper)

    if (derKey.size() > keylen) {
        throw std::runtime_error("Output buffer too small for public key. Needed: " + std::to_string(derKey.size()) + ", Provided: " + std::to_string(keylen));
    }
    
    std::memcpy(keyout, derKey.data(), derKey.size());
}

// Returns DER encoded public key
std::string RSAPrivateWrapper::getPublicKey() {
    std::string derKey;
    StringSink ss(derKey);
    this->publicKey.DEREncode(ss); // Use member publicKey (from RSAPrivateWrapper)
    return derKey;
}

} // namespace MyCrypto
