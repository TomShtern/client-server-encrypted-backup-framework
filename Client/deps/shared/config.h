/**
 * @file config.h
 * @brief Canonical configuration constants for the Client-Server Encrypted Backup Framework
 * 
 * This header provides centralized configuration constants that ensure
 * consistency across all C++ components in the system.
 * 
 * Compatible with the Python server configuration for cross-language consistency.
 */

#ifndef CLIENT_SHARED_CONFIG_H
#define CLIENT_SHARED_CONFIG_H

#include <cstdint>
#include <string>

namespace client {
namespace shared {
namespace config {

// Protocol version and basic constants
constexpr int PROTOCOL_VERSION = 3;
constexpr int DEFAULT_SERVER_PORT = 1256;
constexpr int DEFAULT_API_PORT = 9090;

// Buffer and size limits
constexpr size_t DEFAULT_BUFFER_SIZE = 8192;
constexpr size_t MAX_FILENAME_FIELD_SIZE = 255;
constexpr size_t MAX_ACTUAL_FILENAME_LENGTH = 200;
constexpr size_t MIN_FILENAME_LENGTH = 1;
constexpr size_t MAX_PAYLOAD_SIZE = 1024 * 1024;  // 1MB
constexpr size_t CHUNK_SIZE = 64 * 1024;          // 64KB

// Timeout values (in seconds)
constexpr int DEFAULT_TIMEOUT = 30;
constexpr int HEADER_TIMEOUT = 10;
constexpr int UPLOAD_TIMEOUT = 300;

// Cryptographic constants
constexpr int RSA_KEY_SIZE = 2048;
constexpr int AES_KEY_SIZE = 256;
constexpr uint32_t CRC_POLYNOMIAL = 0x04C11DB7;

// Protocol request codes
constexpr uint16_t REQ_REGISTER = 1025;
constexpr uint16_t REQ_PUBLIC_KEY = 1026;
constexpr uint16_t REQ_SEND_FILE = 1027;
constexpr uint16_t REQ_CRC_OK = 1028;
constexpr uint16_t REQ_CRC_FAIL = 1029;

// Protocol response codes
constexpr uint16_t RESP_REGISTER_SUCCESS = 1600;
constexpr uint16_t RESP_REGISTER_FAIL = 1601;
constexpr uint16_t RESP_PUBLIC_KEY = 1602;
constexpr uint16_t RESP_FILE_CRC = 1603;
constexpr uint16_t RESP_FILE_RECEIVED = 1604;
constexpr uint16_t RESP_GENERIC_SERVER_ERROR = 1605;

// File paths (relative to client working directory)
namespace paths {
    constexpr const char* PRIVATE_KEY_FILE = "priv.key";
    constexpr const char* PUBLIC_KEY_FILE = "valid_public_key.der";
    constexpr const char* TRANSFER_INFO_FILE = "transfer.info";
    constexpr const char* STATUS_LOG_FILE = "status_log.json";
    constexpr const char* CLIENT_INFO_FILE = "me.info";
}

// Server connection defaults
namespace server {
    constexpr const char* DEFAULT_HOST = "127.0.0.1";
    constexpr int DEFAULT_PORT = DEFAULT_SERVER_PORT;
    constexpr int MAX_CONNECTIONS = 10;
    constexpr bool ENABLE_LOGGING = true;
}

// Client configuration
namespace client {
    constexpr bool ENABLE_COMPRESSION = true;
    constexpr bool VERIFY_SSL = false;  // For development
    constexpr int MAX_RETRY_ATTEMPTS = 3;
    constexpr int RETRY_DELAY_MS = 1000;
}

// Validation constants
namespace validation {
    // Allowed filename characters pattern (for reference)
    constexpr const char* ALLOWED_FILENAME_PATTERN = "^[a-zA-Z0-9._\\-\\s&#]+$";
    
    // Reserved OS names
    constexpr const char* RESERVED_NAMES[] = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    };
    
    constexpr size_t RESERVED_NAMES_COUNT = sizeof(RESERVED_NAMES) / sizeof(RESERVED_NAMES[0]);
}

// Logging configuration
namespace logging {
    constexpr const char* DEFAULT_LOG_LEVEL = "INFO";
    constexpr bool ENABLE_CONSOLE_OUTPUT = true;
    constexpr bool ENABLE_FILE_OUTPUT = false;
    constexpr const char* LOG_FILE = "client.log";
}

// Network configuration
namespace network {
    constexpr int SOCKET_TIMEOUT_MS = 30000;
    constexpr int CONNECT_TIMEOUT_MS = 10000;
    constexpr int SEND_TIMEOUT_MS = 30000;
    constexpr int RECV_TIMEOUT_MS = 30000;
    constexpr bool ENABLE_KEEPALIVE = true;
}

// Error codes for client operations
namespace error_codes {
    constexpr int SUCCESS = 0;
    constexpr int NETWORK_ERROR = 1;
    constexpr int FILE_ERROR = 2;
    constexpr int CRYPTO_ERROR = 3;
    constexpr int PROTOCOL_ERROR = 4;
    constexpr int VALIDATION_ERROR = 5;
    constexpr int TIMEOUT_ERROR = 6;
    constexpr int AUTHENTICATION_ERROR = 7;
    constexpr int CRC_MISMATCH_ERROR = 8;
    constexpr int UNKNOWN_ERROR = 99;
}

/**
 * @brief Get configuration value as string
 * 
 * @param key Configuration key
 * @param default_value Default value if key not found
 * @return Configuration value
 */
std::string get_config_string(const std::string& key, const std::string& default_value = "");

/**
 * @brief Get configuration value as integer
 * 
 * @param key Configuration key
 * @param default_value Default value if key not found
 * @return Configuration value
 */
int get_config_int(const std::string& key, int default_value = 0);

/**
 * @brief Get configuration value as boolean
 * 
 * @param key Configuration key
 * @param default_value Default value if key not found
 * @return Configuration value
 */
bool get_config_bool(const std::string& key, bool default_value = false);

/**
 * @brief Load configuration from file
 * 
 * @param config_file Path to configuration file
 * @return true if loaded successfully, false otherwise
 */
bool load_config_file(const std::string& config_file = "client_config.json");

/**
 * @brief Get server address from transfer.info file
 * 
 * @param transfer_file Path to transfer.info file
 * @return Server address string (host:port format)
 */
std::string get_server_address(const std::string& transfer_file = paths::TRANSFER_INFO_FILE);

/**
 * @brief Validate configuration parameters
 * 
 * @return true if configuration is valid, false otherwise
 */
bool validate_config();

} // namespace config
} // namespace shared
} // namespace client

#endif // CLIENT_SHARED_CONFIG_H
