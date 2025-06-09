#include "AESWrapper.h"
#include "../../crypto++/aes.h"
#include "../../crypto++/modes.h"
#include "../../crypto++/osrng.h"
#include "../../crypto++/filters.h"
#include "../../crypto++/hex.h"
#include <stdexcept>
#include <cstring>

using namespace CryptoPP;

/**
 * @brief Constructs an AESWrapper instance with the specified key and IV configuration.
 *
 * Initializes the AES key from the provided buffer and sets the initialization vector (IV) to either a static zero vector or a randomly generated value, depending on the `useStaticZeroIV` flag.
 *
 * @param key Pointer to the AES key buffer. Must be non-null and of length `DEFAULT_KEYLENGTH`.
 * @param keyLength Length of the key buffer in bytes. Must equal `DEFAULT_KEYLENGTH`.
 * @param useStaticZeroIV If true, the IV is set to all zeros; otherwise, a random IV is generated.
 *
 * @throws std::invalid_argument if the key is null or the key length is invalid.
 */
AESWrapper::AESWrapper(const unsigned char* key, size_t keyLength, bool useStaticZeroIV) {
    if (!key || keyLength != AESWrapper::DEFAULT_KEYLENGTH) {
        throw std::invalid_argument("Invalid key or key length");
    }
    
    keyData.assign(key, key + keyLength);
    
    iv.resize(AES::BLOCKSIZE);
    if (useStaticZeroIV) {
        std::fill(iv.begin(), iv.end(), 0);
    } else {
        // Generate random IV
        AutoSeededRandomPool rng;
        rng.GenerateBlock(iv.data(), iv.size());
    }
}

/**
 * @brief Securely clears sensitive key and IV data from memory upon destruction.
 *
 * Overwrites the internal key and IV vectors with zeros to prevent sensitive information from remaining in memory after the object is destroyed.
 */
AESWrapper::~AESWrapper() {
    // Clear sensitive data
    std::fill(keyData.begin(), keyData.end(), 0);
    std::fill(iv.begin(), iv.end(), 0);
}

/**
 * @brief Returns a pointer to the internal AES key data.
 *
 * @return Pointer to the key data if available, or nullptr if the key is not set.
 */
const unsigned char* AESWrapper::getKey() const {
    return keyData.empty() ? nullptr : keyData.data();
}

/**
 * @brief Encrypts plaintext using AES in CBC mode and prepends the IV to the ciphertext.
 *
 * Encrypts the provided plaintext buffer using the internally stored AES key and IV.
 * The output consists of the IV followed by the ciphertext, both as a single string.
 *
 * @param plain Pointer to the plaintext buffer.
 * @param length Length of the plaintext buffer in bytes.
 * @return std::string The IV concatenated with the ciphertext.
 *
 * @throws std::invalid_argument If the input buffer is null or length is zero.
 * @throws std::runtime_error If encryption fails due to a cryptographic error.
 */
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

/**
 * @brief Decrypts AES-encrypted data using CBC mode.
 *
 * Extracts the initialization vector (IV) from the beginning of the input buffer, then decrypts the remaining ciphertext using the stored AES key and the extracted IV.
 *
 * @param cipher Pointer to the buffer containing the IV followed by the ciphertext.
 * @param length Length of the buffer in bytes; must be at least one AES block size.
 * @return Decrypted plaintext as a string.
 *
 * @throws std::invalid_argument If the input buffer is null or too short.
 * @throws std::runtime_error If decryption fails due to a cryptographic error.
 */
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

/**
 * @brief Fills the provided buffer with a randomly generated AES key.
 *
 * Generates a cryptographically secure random key of length `DEFAULT_KEYLENGTH` and writes it to the specified buffer.
 *
 * @param buffer Pointer to the buffer where the generated key will be stored. Must not be null.
 * @param length Length of the buffer. Must be equal to `DEFAULT_KEYLENGTH`.
 *
 * @throws std::invalid_argument If the buffer is null or the length does not match `DEFAULT_KEYLENGTH`.
 */
void AESWrapper::generateKey(unsigned char* buffer, size_t length) {
    if (!buffer || length != AESWrapper::DEFAULT_KEYLENGTH) {
        throw std::invalid_argument("Invalid buffer or length");
    }
    
    AutoSeededRandomPool rng;
    rng.GenerateBlock(buffer, length);
}