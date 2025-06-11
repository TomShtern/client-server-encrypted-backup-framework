#include "../../include/wrappers/AESWrapper.h" // Should now be <MyCrypto/AESWrapper.h> or similar if path changes
#include "../../third_party/crypto++/aes.h"
#include "../../third_party/crypto++/modes.h" // For CBC_Mode
#include "../../third_party/crypto++/osrng.h"
#include "../../third_party/crypto++/filters.h"
#include "../../third_party/crypto++/hex.h"
#include <stdexcept>
#include <cstring>

using namespace CryptoPP;

namespace MyCrypto { // Added namespace

AESWrapper::AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV) {
    // DEFAULT_KEYLENGTH is now 32. This check is correct.
    if (!key || keyLength != AESWrapper::DEFAULT_KEYLENGTH) {
        throw std::invalid_argument("Invalid key or key length. Expected " + std::to_string(AESWrapper::DEFAULT_KEYLENGTH) + " bytes.");
    }
    
    keyData.assign(key, key + keyLength);
    
    // iv member should be initialized based on useStaticZeroIV
    // AES::BLOCKSIZE is 16 bytes. The header now also has MyCrypto::AESWrapper::BLOCKSIZE
    iv.resize(MyCrypto::AESWrapper::BLOCKSIZE);
    if (useStaticZeroIV) {
        std::fill(iv.begin(), iv.end(), 0); // Static zero IV
    } else {
        // This case should ideally not be used based on project spec, but implemented for completeness
        AutoSeededRandomPool rng;
        rng.GenerateBlock(iv.data(), iv.size()); // Random IV
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
        
        // Return ciphertext directly, IV is not prepended.
        return ciphertext;
    } catch (const CryptoPP::Exception& e) { // More specific catch
        throw std::runtime_error("AES encryption failed: " + std::string(e.what()));
    }
}

std::string AESWrapper::decrypt(const char* cipher, size_t length) {
    // Valid ciphertext (even of an empty message after padding) will be at least one block size.
    // If length is 0 and cipher is not null, it might be an empty string, which is invalid for block cipher.
    if (!cipher || length == 0 || length % MyCrypto::AESWrapper::BLOCKSIZE != 0) { // Cipher length must be multiple of block size
        throw std::invalid_argument("Invalid cipher data or length. Length must be multiple of block size.");
    }
    
    try {
        std::string plaintext;
        CBC_Mode<AES>::Decryption decryption;
        
        // Decrypt using this->iv (which should be static zero IV if constructor was called with useStaticZeroIV=true)
        decryption.SetKeyWithIV(keyData.data(), keyData.size(), this->iv.data());

        // Use original cipher and length
        StringSource ss(reinterpret_cast<const unsigned char*>(cipher), length, true,
            new StreamTransformationFilter(decryption,
                new StringSink(plaintext)
            )
        );
        
        return plaintext;
    } catch (const CryptoPP::Exception& e) { // More specific catch
        throw std::runtime_error("AES decryption failed: " + std::string(e.what()));
    }
}

// Static method, so it uses AESWrapper::DEFAULT_KEYLENGTH from the class scope
void AESWrapper::generateKey(unsigned char* buffer, size_t length) {
    // DEFAULT_KEYLENGTH is now 32. This check is correct.
    // The length parameter in the function signature for generateKey in .h was also updated to default to DEFAULT_KEYLENGTH
    if (!buffer || length == 0) { // Check if length is 0, or if it's not matching default if no specific length is passed.
                                  // If length has a default argument in .h, this check might simplify.
                                  // Assuming length passed here is the intended length.
        throw std::invalid_argument("Invalid buffer or key generation length specified.");
    }
    if (length != AESWrapper::DEFAULT_KEYLENGTH && length != 16 && length != 24 && length != 32) {
         throw std::invalid_argument("Invalid key length for AES. Must be 16, 24, or 32 bytes.");
    }
    
    AutoSeededRandomPool rng;
    rng.GenerateBlock(buffer, length);
}

} // namespace MyCrypto