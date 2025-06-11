#pragma once

#include <vector>
#include <string>
#include <cstdint>
#include <iomanip>

// Protocol constants
extern const uint8_t PROTOCOL_VERSION;
extern const size_t CLIENT_ID_SIZE;
extern const size_t HEADER_SIZE;
extern const size_t MAX_FILENAME_SIZE;

// Request codes
extern const uint16_t REQ_REGISTER;
extern const uint16_t REQ_SEND_PUBLIC_KEY;
extern const uint16_t REQ_RECONNECT;
extern const uint16_t REQ_SEND_FILE;
extern const uint16_t REQ_CRC_OK;
extern const uint16_t REQ_CRC_RETRY;
extern const uint16_t REQ_CRC_ABORT;

// Response codes
extern const uint16_t RESP_REGISTER_OK;
extern const uint16_t RESP_REGISTER_FAIL;
extern const uint16_t RESP_PUBKEY_AES_SENT;
extern const uint16_t RESP_FILE_CRC;
extern const uint16_t RESP_ACK;
extern const uint16_t RESP_RECONNECT_AES_SENT;
extern const uint16_t RESP_RECONNECT_FAIL;
extern const uint16_t RESP_ERROR;

// Endianness conversion functions
uint16_t hostToLittleEndian16(uint16_t value);
uint32_t hostToLittleEndian32(uint32_t value);
uint16_t littleEndianToHost16(uint16_t value);
uint32_t littleEndianToHost32(uint32_t value);

// Request creation functions
std::vector<uint8_t> createRegistrationRequest(const uint8_t* clientId, const std::string& username);
std::vector<uint8_t> createPublicKeyRequest(const uint8_t* clientId, const std::string& username, 
                                          const std::string& publicKey);
std::vector<uint8_t> createReconnectionRequest(const uint8_t* clientId, const std::string& username);
std::vector<uint8_t> createFileTransferRequest(const uint8_t* clientId, const std::string& filename,
                                              const std::vector<uint8_t>& encryptedData, 
                                              uint32_t originalSize);
std::vector<uint8_t> createCRCRequest(const uint8_t* clientId, uint16_t requestCode, 
                                     const std::string& filename);

// Response parsing functions
bool parseResponseHeader(const std::vector<uint8_t>& data, uint8_t& version, 
                        uint16_t& code, uint32_t& payloadSize);
std::vector<uint8_t> extractResponsePayload(const std::vector<uint8_t>& data);
bool parseRegistrationResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId);
bool parseKeyExchangeResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId,
                             std::vector<uint8_t>& encryptedAESKey);
bool parseFileTransferResponse(const std::vector<uint8_t>& payload, std::vector<uint8_t>& clientId,
                              uint32_t& contentSize, std::string& filename, uint32_t& checksum);

// CRC calculation
uint32_t calculateFileCRC(const std::vector<uint8_t>& data);

// Utility functions
void printHexDump(const std::vector<uint8_t>& data, const std::string& label);