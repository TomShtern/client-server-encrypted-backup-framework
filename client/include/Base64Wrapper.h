#pragma once

#include <string>
#include "../../crypto++/base64.h"

/**
 * @brief Encodes a string into its Base64 representation.
 *
 * @param str The input string to encode.
 * @return std::string The Base64-encoded string.
 */

/**
 * @brief Decodes a Base64-encoded string back to its original form.
 *
 * @param str The Base64-encoded string to decode.
 * @return std::string The decoded original string.
 */
class Base64Wrapper
{
public:
    static std::string encode(const std::string& str);
    static std::string decode(const std::string& str);
};
