#include "Base64Wrapper.h"

/**
 * @brief Encodes a string into its Base64 representation.
 *
 * @param str The input string to encode.
 * @return std::string The Base64-encoded version of the input string.
 */
std::string Base64Wrapper::encode(const std::string& str)
{
    std::string encoded;
    CryptoPP::StringSource ss(str, true,
        new CryptoPP::Base64Encoder(
            new CryptoPP::StringSink(encoded)
        ) // Base64Encoder
    ); // StringSource

    return encoded;
}

/**
 * @brief Decodes a Base64-encoded string to its original representation.
 *
 * @param str The Base64-encoded input string.
 * @return std::string The decoded original string.
 */
std::string Base64Wrapper::decode(const std::string& str)
{
    std::string decoded;
    CryptoPP::StringSource ss(str, true,
        new CryptoPP::Base64Decoder(
            new CryptoPP::StringSink(decoded)
        ) // Base64Decoder
    ); // StringSource

    return decoded;
}
