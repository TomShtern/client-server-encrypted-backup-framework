#pragma once

#include <cstdint>
#include <cstddef> // For size_t

namespace ClientProtocol {

// Protocol Version
constexpr uint8_t CLIENT_VERSION = 3;
constexpr uint8_t SERVER_VERSION = 3; // Used for validating server responses

// Request Codes
constexpr uint16_t REQ_REGISTER = 1025;
constexpr uint16_t REQ_SEND_PUBLIC_KEY = 1026;
constexpr uint16_t REQ_RECONNECT = 1027;
constexpr uint16_t REQ_SEND_FILE = 1028;
constexpr uint16_t REQ_CRC_OK = 1029;
constexpr uint16_t REQ_CRC_RETRY = 1030;
constexpr uint16_t REQ_CRC_ABORT = 1031;

// Response Codes
constexpr uint16_t RESP_REGISTER_OK = 1600;
constexpr uint16_t RESP_REGISTER_FAIL = 1601;
constexpr uint16_t RESP_PUBKEY_AES_SENT = 1602;
constexpr uint16_t RESP_FILE_OK = 1603;
constexpr uint16_t RESP_ACK = 1604;
constexpr uint16_t RESP_RECONNECT_AES_SENT = 1605;
constexpr uint16_t RESP_RECONNECT_FAIL = 1606;
constexpr uint16_t RESP_ERROR = 1607;

// Protocol-related Size Constants
constexpr size_t CLIENT_ID_SIZE = 16;
constexpr size_t MAX_NAME_SIZE = 255;
constexpr size_t RSA_PUBLIC_KEY_DER_SIZE = 162; // DER format of 1024-bit RSA public key
constexpr size_t AES_KEY_SPEC_SIZE = 32;      // AES-256 key size as per specification

// Protocol Structures
#pragma pack(push, 1)

struct RequestHeader {
    uint8_t client_id[CLIENT_ID_SIZE];
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};

struct ResponseHeader {
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};

#pragma pack(pop)

} // namespace ClientProtocol