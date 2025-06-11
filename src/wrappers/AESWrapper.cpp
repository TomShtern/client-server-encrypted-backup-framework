#include "../../include/wrappers/AESWrapper.h"
#include "../../third_party/crypto++/aes.h"
#include "../../third_party/crypto++/modes.h"
#include "../../third_party/crypto++/filters.h"
#include "../../third_party/crypto++/hex.h"
#include <stdexcept>
#include <cstring>
#include <random>

using namespace CryptoPP;

AESWrapper::AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV) {
    if (!key || keyLength != AESWrapper::DEFAULT_KEYLENGTH) {
        throw std::invalid_argument("Invalid key or key length");
    }
    
    keyData.assign(key, key + keyLength);
    
    iv.resize(AES::BLOCKSIZE);
    if (useStaticZeroIV) {
        std::fill(iv.begin(), iv.end(), 0);
    } else {        // Generate random IV using standard library
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<int> dist(0, 255);
        for (size_t i = 0; i < iv.size(); ++i) {
            iv[i] = static_cast<unsigned char>(dist(gen));
        }
    }
}

AESWrapper::~AESWrapper() {
    // Clear sensitive data
    std::fill(keyData.begin(), keyData.end(), 0);
    std::fill(iv.begin(), iv.end(), 0);
}

const unsigned char* AESWrapper::getKey() const {
    return keyData.empty() ? nullptr : keyData.data();
}

std::string AESWrapper::encrypt(const char* plain, size_t length) {
    if (!plain || length == 0) {
        throw std::invalid_argument("Invalid input data");
    }
    
    try {
        std::string ciphertext;
        
        CBC_Mode<AES>::Encryption encryption;
        encryption.SetKeyWithIV(keyData.data(), keyData.size(), iv.data());
        
        StringSource ss(reinterpret_cast<const unsigned char*>(plain), length, true,
            new StreamTransformationFilter(encryption,
                new StringSink(ciphertext)
            )
        );
        
        // Prepend IV to ciphertext
        std::string result;
        result.reserve(iv.size() + ciphertext.size());
        result.append(reinterpret_cast<const char*>(iv.data()), iv.size());
        result.append(ciphertext);
        
        return result;
    } catch (const Exception& e) {
        throw std::runtime_error("AES encryption failed: " + std::string(e.what()));
    }
}

std::string AESWrapper::decrypt(const char* cipher, size_t length) {
    if (!cipher || length < AES::BLOCKSIZE) {
        throw std::invalid_argument("Invalid cipher data or length too short");
    }
    
    try {
        // Extract IV from the beginning of cipher
        std::vector<unsigned char> extractedIv(cipher, cipher + AES::BLOCKSIZE);
        
        // Extract actual ciphertext
        const char* actualCipher = cipher + AES::BLOCKSIZE;
        size_t actualLength = length - AES::BLOCKSIZE;
        
        std::string plaintext;
        
        CBC_Mode<AES>::Decryption decryption;
        decryption.SetKeyWithIV(keyData.data(), keyData.size(), extractedIv.data());
        
        StringSource ss(reinterpret_cast<const unsigned char*>(actualCipher), actualLength, true,
            new StreamTransformationFilter(decryption,
                new StringSink(plaintext)
            )
        );
        
        return plaintext;
    } catch (const Exception& e) {
        throw std::runtime_error("AES decryption failed: " + std::string(e.what()));
    }
}

void AESWrapper::generateKey(unsigned char* buffer, size_t length) {
    if (!buffer || length != AESWrapper::DEFAULT_KEYLENGTH) {
        throw std::invalid_argument("Invalid buffer or length");
    }    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist(0, 255);
    for (size_t i = 0; i < length; ++i) {
        buffer[i] = static_cast<unsigned char>(dist(gen));
    }
}