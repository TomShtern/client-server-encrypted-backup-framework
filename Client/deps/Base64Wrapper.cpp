#include "../../include/wrappers/Base64Wrapper.h"
#include <stdexcept>
#include <iostream>
#include <string>
#include <algorithm>

// Real Base64 implementation using Crypto++ library
#include <cryptopp/base64.h>

// Base64Wrapper implementation with real Crypto++ functionality
std::string Base64Wrapper::encode(const std::string& str) {
    try {
        std::string encoded;
        CryptoPP::StringSource ss(str, true,
            new CryptoPP::Base64Encoder(
                new CryptoPP::StringSink(encoded)
            ) // Base64Encoder
        ); // StringSource
        
        // Remove newlines that Crypto++ Base64 encoder adds
        encoded.erase(std::remove(encoded.begin(), encoded.end(), '\n'), encoded.end());
        encoded.erase(std::remove(encoded.begin(), encoded.end(), '\r'), encoded.end());
        
        return encoded;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Base64Wrapper::encode failed: " << e.what() << std::endl;
        throw std::runtime_error("Base64 encoding failed");
    }
}

std::string Base64Wrapper::decode(const std::string& str) {
    try {
        std::string decoded;
        CryptoPP::StringSource ss(str, true,
            new CryptoPP::Base64Decoder(
                new CryptoPP::StringSink(decoded)
            ) // Base64Decoder
        ); // StringSource
        
        return decoded;
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Base64Wrapper::decode failed: " << e.what() << std::endl;
        throw std::runtime_error("Base64 decoding failed");
    }
}
