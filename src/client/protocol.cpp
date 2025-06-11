#include "../../include/client/protocol.h"
#include "../../include/client/cksum.h"
#include <iostream>
#include <vector>
#include <cstring>
#include <stdexcept>

// Protocol constants
constexpr uint8_t PROTOCOL_VERSION = 3;
constexpr size_t CLIENT_ID_SIZE = 16;
constexpr size_t HEADER_SIZE = 23;
constexpr size_t MAX_FILENAME_SIZE = 255;

// Request codes
constexpr uint16_t REQ_REGISTER = 1025;
constexpr uint16_t REQ_SEND_PUBLIC_KEY = 1026;
constexpr uint16_t REQ_RECONNECT = 1027;
constexpr uint16_t REQ_SEND_FILE = 1028;
constexpr uint16_t REQ_CRC_OK = 1029;
constexpr uint16_t REQ_CRC_RETRY = 1030;
constexpr uint16_t REQ_CRC_ABORT = 1031;

// Response codes
constexpr uint16_t RESP_REGISTER_OK = 1600;
constexpr uint16_t RESP_REGISTER_FAIL = 1601;
constexpr uint16_t RESP_PUBKEY_AES_SENT = 1602;
constexpr uint16_t RESP_FILE_CRC = 1603;
constexpr uint16_t RESP_ACK = 1604;
constexpr uint16_t RESP_RECONNECT_AES_SENT = 1605;
constexpr uint16_t RESP_RECONNECT_FAIL = 1606;
constexpr uint16_t RESP_ERROR = 1607;

// Protocol structures (packed)
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

// Helper function to convert multi-byte integers to little-endian
uint16_t hostToLittleEndian16(uint16_t value) {
    uint8_t bytes[2];
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
    return *reinterpret_cast<uint16_t*>(bytes);
}

uint32_t hostToLittleEndian32(uint32_t value) {
    uint8_t bytes[4];
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
    bytes[2] = (value >> 16) & 0xFF;
    bytes[3] = (value >> 24) & 0xFF;
    return *reinterpret_cast<uint32_t*>(bytes);
}

uint16_t littleEndianToHost16(uint16_t value) {
    const uint8_t* bytes = reinterpret_cast<const uint8_t*>(&value);
    return static_cast<uint16_t>(bytes[0]) | (static_cast<uint16_t>(bytes[1]) << 8);
}

uint32_t littleEndianToHost32(uint32_t value) {
    const uint8_t* bytes = reinterpret_cast<const uint8_t*>(&value);
    return static_cast<uint32_t>(bytes[0]) | 
           (static_cast<uint32_t>(bytes[1]) << 8) | 
           (static_cast<uint32_t>(bytes[2]) << 16) | 
           (static_cast<uint32_t>(bytes[3]) << 24);
}

// Helper function to create padded string fields
std::vector<uint8_t> createPaddedString(const std::string& str, size_t targetSize) {
    std::vector<uint8_t> result(targetSize, 0);
    size_t copySize = std::min(str.size(), targetSize - 1); // Leave room for null terminator
    std::memcpy(result.data(), str.c_str(), copySize);
    return result;
}

// Create registration request (Code 1025)
std::vector<uint8_t> createRegistrationRequest(const uint8_t* clientId, const std::string& username) {
    std::vector<uint8_t> request;
    
    // Create header
    RequestHeader header;
    std::memcpy(header.client_id, clientId, CLIENT_ID_SIZE);
    header.version = PROTOCOL_VERSION;
    header.code = hostToLittleEndian16(REQ_REGISTER);
    header.payload_size = hostToLittleEndian32(MAX_FILENAME_SIZE); // Username field size
    
    // Add header to request
    request.resize(sizeof(RequestHeader));
    std::memcpy(request.data(), &header, sizeof(RequestHeader));
    
    // Add username payload (255 bytes, null-terminated, zero-padded)
    std::vector<uint8_t> usernameField = createPaddedString(username, MAX_FILENAME_SIZE);
    request.insert(request.end(), usernameField.begin(), usernameField.end());
    
    std::cout << "[DEBUG] Created registration request: " << request.size() << " bytes" << std::endl;
    return request;
}

// Create public key submission request (Code 1026)
std::vector<uint8_t> createPublicKeyRequest(const uint8_t* clientId, const std::string& username, 
                                          const std::string& publicKey) {
    std::vector<uint8_t> request;
    
    // Calculate payload size: username (255) + public key (162)
    uint32_t payloadSize = MAX_FILENAME_SIZE + 162;
    
    // Create header
    RequestHeader header;
    std::memcpy(header.client_id, clientId, CLIENT_ID_SIZE);
    header.version = PROTOCOL_VERSION;
    header.code = hostToLittleEndian16(REQ_SEND_PUBLIC_KEY);
    header.payload_size = hostToLittleEndian32(payloadSize);
    
    // Add header to request
    request.resize(sizeof(RequestHeader));
    std::memcpy(request.data(), &header, sizeof(RequestHeader));
    
    // Add username field (255 bytes)
    std::vector<uint8_t> usernameField = createPaddedString(username, MAX_FILENAME_SIZE);
    request.insert(request.end(), usernameField.begin(), usernameField.end());
    
    // Add public key (exactly 162 bytes)
    if (publicKey.size() != 162) {
        throw std::invalid_argument("Public key must be exactly 162 bytes");
    }
    request.insert(request.end(), publicKey.begin(), publicKey.end());
    
    std::cout << "[DEBUG] Created public key request: " << request.size() << " bytes" << std::endl;
    return request;
}

// Create reconnection request (Code 1027)
std::vector<uint8_t> createReconnectionRequest(const uint8_t* clientId, const std::string& username) {
    std::vector<uint8_t> request;
    
    // Create header
    RequestHeader header;
    std::memcpy(header.client_id, clientId, CLIENT_ID_SIZE);
    header.version = PROTOCOL_VERSION;
    header.code = hostToLittleEndian16(REQ_RECONNECT);
    header.payload_size = hostToLittleEndian32(MAX_FILENAME_SIZE); // Username field size
    
    // Add header to request
    request.resize(sizeof(RequestHeader));
    std::memcpy(request.data(), &header, sizeof(RequestHeader));
    
    // Add username payload (255 bytes, null-terminated, zero-padded)
    std::vector<uint8_t> usernameField = createPaddedString(username, MAX_FILENAME_SIZE);
    request.insert(request.end(), usernameField.begin(), usernameField.end());
    
    std::cout << "[DEBUG] Created reconnection request: " << request.size() << " bytes" << std::endl;
    return request;
}

// Create file transfer request (Code 1028)
std::vector<uint8_t> createFileTransferRequest(const uint8_t* clientId, const std::string& filename,
                                              const std::vector<uint8_t>& encryptedData, 
                                              uint32_t originalSize) {
    std::vector<uint8_t> request;
    
    // Calculate payload size: content_size(4) + orig_file_size(4) + packet_number(2) + total_packets(2) + filename(255) + data
    uint32_t payloadSize = 4 + 4 + 2 + 2 + MAX_FILENAME_SIZE + static_cast<uint32_t>(encryptedData.size());
    
    // Create header
    RequestHeader header;
    std::memcpy(header.client_id, clientId, CLIENT_ID_SIZE);
    header.version = PROTOCOL_VERSION;
    header.code = hostToLittleEndian16(REQ_SEND_FILE);
    header.payload_size = hostToLittleEndian32(payloadSize);
    
    // Add header to request
    request.resize(sizeof(RequestHeader));
    std::memcpy(request.data(), &header, sizeof(RequestHeader));
    
    // Add payload fields
    // Content size (encrypted data size)
    uint32_t contentSize = hostToLittleEndian32(static_cast<uint32_t>(encryptedData.size()));
    request.insert(request.end(), reinterpret_cast<uint8_t*>(&contentSize), 
                   reinterpret_cast<uint8_t*>(&contentSize) + 4);
    
    // Original file size
    uint32_t origSize = hostToLittleEndian32(originalSize);
    request.insert(request.end(), reinterpret_cast<uint8_t*>(&origSize), 
                   reinterpret_cast<uint8_t*>(&origSize) + 4);
    
    // Packet number (always 1 - no chunking)
    uint16_t packetNum = hostToLittleEndian16(1);
    request.insert(request.end(), reinterpret_cast<uint8_t*>(&packetNum), 
                   reinterpret_cast<uint8_t*>(&packetNum) + 2);
    
    // Total packets (always 1 - no chunking)
    uint16_t totalPackets = hostToLittleEndian16(1);
    request.insert(request.end(), reinterpret_cast<uint8_t*>(&totalPackets), 
                   reinterpret_cast<uint8_t*>(&totalPackets) + 2);
    
    // Filename field (255 bytes)
    std::vector<uint8_t> filenameField = createPaddedString(filename, MAX_FILENAME_SIZE);
    request.insert(request.end(), filenameField.begin(), filenameField.end());
    
    // Encrypted file data
    request.insert(request.end(), encryptedData.begin(), encryptedData.end());
    
    std::cout << "[DEBUG] Created file transfer request: " << request.size() << " bytes" << std::endl;
    return request;
}

// Create CRC verification requests (Codes 1029, 1030, 1031)
std::vector<uint8_t> createCRCRequest(const uint8_t* clientId, uint16_t requestCode, 
                                     const std::string& filename) {
    std::vector<uint8_t> request;
    
    // Create header
    RequestHeader header;
    std::memcpy(header.client_id, clientId, CLIENT_ID_SIZE);
    header.version = PROTOCOL_VERSION;
    header.code = hostToLittleEndian16(requestCode);
    header.payload_size = hostToLittleEndian32(MAX_FILENAME_SIZE); // Filename field size
    
    // Add header to request
    request.resize(sizeof(RequestHeader));
    std::memcpy(request.data(), &header, sizeof(RequestHeader));
    
    // Add filename payload (255 bytes, null-terminated, zero-padded)
    std::vector<uint8_t> filenameField = createPaddedString(filename, MAX_FILENAME_SIZE);
    request.insert(request.end(), filenameField.begin(), filenameField.end());
    
    std::cout << "[DEBUG] Created CRC request (code " << requestCode << "): " << request.size() << " bytes" << std::endl;
    return request;
}

// Parse response header
bool parseResponseHeader(const std::vector<uint8_t>& data, uint8_t& version, 
                        uint16_t& code, uint32_t& payloadSize) {
    if (data.size() < sizeof(ResponseHeader)) {
        std::cerr << "[ERROR] Response data too small for header" << std::endl;
        return false;
    }
    
    const ResponseHeader* header = reinterpret_cast<const ResponseHeader*>(data.data());
    version = header->version;
    code = littleEndianToHost16(header->code);
    payloadSize = littleEndianToHost32(header->payload_size);
    
    std::cout << "[DEBUG] Parsed response: version=" << static_cast<int>(version) 
              << ", code=" << code << ", payload_size=" << payloadSize << std::endl;
    
    return true;
}

// Extract response payload
std::vector<uint8_t> extractResponsePayload(const std::vector<uint8_t>& data) {
    if (data.size() <= sizeof(ResponseHeader)) {
        return std::vector<uint8_t>(); // No payload
    }
    
    return std::vector<uint8_t>(data.begin() + sizeof(ResponseHeader), data.end());
}

// Parse registration success response (1600)
bool parseRegistrationResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId) {
    if (payload.size() < CLIENT_ID_SIZE) {
        std::cerr << "[ERROR] Registration response payload too small" << std::endl;
        return false;
    }
    
    clientId.assign(payload.begin(), payload.begin() + CLIENT_ID_SIZE);
    std::cout << "[DEBUG] Parsed registration response: received " << clientId.size() << "-byte client ID" << std::endl;
    return true;
}

// Parse public key/reconnection response (1602/1605) 
bool parseKeyExchangeResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId,
                             std::vector<uint8_t>& encryptedAESKey) {
    if (payload.size() < CLIENT_ID_SIZE) {
        std::cerr << "[ERROR] Key exchange response payload too small" << std::endl;
        return false;
    }
    
    // Extract client ID (first 16 bytes)
    clientId.assign(payload.begin(), payload.begin() + CLIENT_ID_SIZE);
    
    // Extract encrypted AES key (remaining bytes)
    if (payload.size() > CLIENT_ID_SIZE) {
        encryptedAESKey.assign(payload.begin() + CLIENT_ID_SIZE, payload.end());
    }
    
    std::cout << "[DEBUG] Parsed key exchange response: client ID " << clientId.size() 
              << " bytes, encrypted AES key " << encryptedAESKey.size() << " bytes" << std::endl;
    return true;
}

// Parse file transfer response (1603)
bool parseFileTransferResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId,
                              uint32_t& contentSize, std::string& filename, uint32_t& checksum) {
    // Expected structure: client_id(16) + content_size(4) + filename(255) + checksum(4)
    const size_t expectedSize = CLIENT_ID_SIZE + 4 + MAX_FILENAME_SIZE + 4;
    if (payload.size() < expectedSize) {
        std::cerr << "[ERROR] File transfer response payload too small: " << payload.size() 
                  << " < " << expectedSize << std::endl;
        return false;
    }
    
    size_t offset = 0;
    
    // Extract client ID
    clientId.assign(payload.begin() + offset, payload.begin() + offset + CLIENT_ID_SIZE);
    offset += CLIENT_ID_SIZE;
    
    // Extract content size
    contentSize = littleEndianToHost32(*reinterpret_cast<const uint32_t*>(payload.data() + offset));
    offset += 4;
    
    // Extract filename (null-terminated string from 255-byte field)
    const char* filenamePtr = reinterpret_cast<const char*>(payload.data() + offset);
    filename = std::string(filenamePtr);
    offset += MAX_FILENAME_SIZE;
    
    // Extract checksum
    checksum = littleEndianToHost32(*reinterpret_cast<const uint32_t*>(payload.data() + offset));
    
    std::cout << "[DEBUG] Parsed file transfer response: content_size=" << contentSize 
              << ", filename='" << filename << "', checksum=0x" << std::hex << checksum << std::dec << std::endl;
    return true;
}

// Calculate CRC using the Linux cksum compatible algorithm
uint32_t calculateFileCRC(const std::vector<uint8_t>& data) {
    return calculateCRC(data.data(), data.size());
}

// Utility function to print hex dump for debugging
void printHexDump(const std::vector<uint8_t>& data, const std::string& label) {
    std::cout << "[DEBUG] " << label << " (" << data.size() << " bytes):" << std::endl;
    for (size_t i = 0; i < data.size(); ++i) {
        if (i % 16 == 0) std::cout << "  ";
        std::cout << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(data[i]) << " ";
        if ((i + 1) % 16 == 0 || i == data.size() - 1) std::cout << std::endl;
    }
    std::cout << std::dec;
}