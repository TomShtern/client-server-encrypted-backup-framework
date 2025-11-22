#include "AESWrapper.h"
#include <stdexcept>
#include <iostream>
#include <string>
#include <cstring>

// Real AES implementation using Crypto++
#include <cryptopp/aes.h>
#include <cryptopp/modes.h>
#include <cryptopp/filters.h>
#include <cryptopp/osrng.h>

// AESWrapper implementation using Crypto++
AESWrapper::AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV) {
    if (!key || keyLength == 0) {
        throw std::invalid_argument("Invalid key data");
    }

    // Validate key length (AES supports 128, 192, 256 bit keys)
    if (keyLength != 16 && keyLength != 24 && keyLength != 32) {
        throw std::invalid_argument("Invalid AES key length. Must be 16, 24, or 32 bytes.");
    }

    std::cout << "[AES] Initialized with " << keyLength << "-byte key (" << (keyLength * 8) << "-bit AES)" << std::endl;
    keyData.assign(key, key + keyLength);

    if (useStaticZeroIV) {
        iv.assign(16, 0); // Static IV of all zeros for protocol compliance
        std::cout << "[AES] Using static zero IV for protocol compatibility" << std::endl;
    } else {
        // Generate random IV
        iv.resize(16);
        CryptoPP::AutoSeededRandomPool rng;
        rng.GenerateBlock(iv.data(), 16);
        std::cout << "[AES] Generated random IV" << std::endl;
    }
}

AESWrapper::~AESWrapper() {
}

void AESWrapper::generateKey(unsigned char* buffer, size_t length) {
    if (!buffer || length == 0) {
        throw std::invalid_argument("Invalid buffer for key generation");
    }

    // Validate key length
    if (length != 16 && length != 24 && length != 32) {
        throw std::invalid_argument("Invalid AES key length for generation. Must be 16, 24, or 32 bytes.");
    }

    CryptoPP::AutoSeededRandomPool rng;
    rng.GenerateBlock(buffer, length);
    std::cout << "[AES] Generated " << length << "-byte (" << (length * 8) << "-bit) random AES key" << std::endl;
}

const unsigned char* AESWrapper::getKey() const {
    return keyData.data();
}

std::string AESWrapper::encrypt(const char* plain, size_t length) {
    if (!plain || length == 0) {
        throw std::invalid_argument("Invalid plaintext data for encryption");
    }

    try {
        std::string ciphertext;

        // Create AES-CBC encryption object
        CryptoPP::CBC_Mode<CryptoPP::AES>::Encryption encryption;
        encryption.SetKeyWithIV(keyData.data(), keyData.size(), iv.data());

        // Encrypt with PKCS7 padding
        CryptoPP::StringSource ss(
            reinterpret_cast<const CryptoPP::byte*>(plain), length, true,
            new CryptoPP::StreamTransformationFilter(
                encryption,
                new CryptoPP::StringSink(ciphertext),
                CryptoPP::StreamTransformationFilter::PKCS_PADDING
            )
        );

        std::cout << "[AES] Encrypted " << length << " bytes to " << ciphertext.length() << " bytes (with padding)" << std::endl;
        return ciphertext;

    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("AES encryption failed: " + std::string(e.what()));
    }
}

std::string AESWrapper::decrypt(const char* cipher, size_t length) {
    if (!cipher || length == 0) {
        throw std::invalid_argument("Invalid ciphertext data for decryption");
    }

    try {
        std::string plaintext;

        // Create AES-CBC decryption object
        CryptoPP::CBC_Mode<CryptoPP::AES>::Decryption decryption;
        decryption.SetKeyWithIV(keyData.data(), keyData.size(), iv.data());

        // Decrypt with PKCS7 padding removal
        CryptoPP::StringSource ss(
            reinterpret_cast<const CryptoPP::byte*>(cipher), length, true,
            new CryptoPP::StreamTransformationFilter(
                decryption,
                new CryptoPP::StringSink(plaintext),
                CryptoPP::StreamTransformationFilter::PKCS_PADDING
            )
        );

        std::cout << "[AES] Decrypted " << length << " bytes to " << plaintext.length() << " bytes (padding removed)" << std::endl;
        return plaintext;

    } catch (const CryptoPP::Exception& e) {
        throw std::runtime_error("AES decryption failed: " + std::string(e.what()));
    }
}
