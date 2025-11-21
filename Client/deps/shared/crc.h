/**
 * @file crc.h
 * @brief Canonical CRC32 implementation for the Client-Server Encrypted Backup Framework
 * 
 * This header provides a centralized, POSIX cksum-compatible CRC32 implementation
 * that ensures consistency across all C++ components in the system.
 * 
 * Compatible with the Python server implementation for cross-language consistency.
 */

#ifndef CLIENT_SHARED_CRC_H
#define CLIENT_SHARED_CRC_H

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>

namespace client {
namespace shared {

/**
 * @brief Calculate CRC32 checksum compatible with POSIX cksum command
 * 
 * This is the canonical implementation that replaces all duplicate CRC
 * calculations throughout the codebase.
 * 
 * @param data Pointer to input data
 * @param size Size of input data in bytes
 * @return 32-bit CRC value
 */
uint32_t calculate_crc32(const uint8_t* data, size_t size);

/**
 * @brief Calculate CRC32 checksum from string
 * 
 * @param data Input string (will be converted to UTF-8 bytes)
 * @return 32-bit CRC value
 */
uint32_t calculate_crc32(const std::string& data);

/**
 * @brief Calculate CRC32 checksum from vector
 * 
 * @param data Input data vector
 * @return 32-bit CRC value
 */
uint32_t calculate_crc32(const std::vector<uint8_t>& data);

/**
 * @brief Verify data against expected CRC32 value
 * 
 * @param data Pointer to data to verify
 * @param size Size of data in bytes
 * @param expected_crc Expected CRC32 value
 * @return true if CRC matches, false otherwise
 */
bool verify_crc32(const uint8_t* data, size_t size, uint32_t expected_crc);

/**
 * @brief Streaming CRC32 calculator for large files or incremental processing
 * 
 * Maintains state between update() calls and provides final CRC calculation
 * that includes length processing.
 */
class CRC32Stream {
public:
    /**
     * @brief Initialize streaming CRC calculator
     */
    CRC32Stream();

    /**
     * @brief Update CRC with new data chunk
     * 
     * @param data Pointer to data chunk
     * @param size Size of data chunk in bytes
     */
    void update(const uint8_t* data, size_t size);

    /**
     * @brief Update CRC with string data
     * 
     * @param data String data chunk
     */
    void update(const std::string& data);

    /**
     * @brief Update CRC with vector data
     * 
     * @param data Vector data chunk
     */
    void update(const std::vector<uint8_t>& data);

    /**
     * @brief Finalize CRC calculation including length processing
     * 
     * @return 32-bit CRC value
     */
    uint32_t finalize();

    /**
     * @brief Reset the CRC calculator to initial state
     */
    void reset();

    /**
     * @brief Get current total length processed
     * 
     * @return Total bytes processed
     */
    size_t get_total_length() const { return total_length_; }

private:
    uint32_t crc_;
    size_t total_length_;
};

/**
 * @brief Get the CRC32 lookup table
 * 
 * @return Pointer to the 256-entry CRC32 table
 */
const uint32_t* get_crc32_table();

// Legacy compatibility functions for existing code
namespace legacy {
    /**
     * @brief Legacy CRC calculation function
     * 
     * @deprecated Use calculate_crc32() instead
     * This function is provided for backward compatibility during migration.
     */
    uint32_t calculateCRC(const uint8_t* data, size_t size);

    /**
     * @brief Legacy CRC32 calculation function
     * 
     * @deprecated Use calculate_crc32() instead
     * This function is provided for backward compatibility during migration.
     */
    uint32_t calculateCRC32(const uint8_t* data, size_t size);
}

} // namespace shared
} // namespace client

#endif // CLIENT_SHARED_CRC_H
