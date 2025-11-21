#pragma once

#include <vector>
#include <string>
#include <cstdint>

/**
 * @brief Simple compression wrapper using zlib/deflate algorithm
 * 
 * This class provides compression and decompression functionality
 * to reduce file transfer sizes and improve performance.
 */
class CompressionWrapper {
public:
    /**
     * @brief Compress data using deflate algorithm
     * @param data Input data to compress
     * @param size Size of input data
     * @return Compressed data as vector, empty if compression failed
     */
    static std::vector<uint8_t> compress(const uint8_t* data, size_t size);
    
    /**
     * @brief Compress string data
     * @param data Input string to compress
     * @return Compressed data as vector, empty if compression failed
     */
    static std::vector<uint8_t> compress(const std::string& data);
    
    /**
     * @brief Decompress data using inflate algorithm
     * @param compressedData Compressed data to decompress
     * @return Decompressed data as vector, empty if decompression failed
     */
    static std::vector<uint8_t> decompress(const std::vector<uint8_t>& compressedData);
    
    /**
     * @brief Decompress data to string
     * @param compressedData Compressed data to decompress
     * @return Decompressed string, empty if decompression failed
     */
    static std::string decompressToString(const std::vector<uint8_t>& compressedData);
    
    /**
     * @brief Calculate compression ratio
     * @param originalSize Original data size
     * @param compressedSize Compressed data size
     * @return Compression ratio as percentage (0-100)
     */
    static double getCompressionRatio(size_t originalSize, size_t compressedSize);
    
    /**
     * @brief Check if compression would be beneficial
     * @param data Data to analyze
     * @param size Size of data
     * @return True if compression is recommended
     */
    static bool shouldCompress(const uint8_t* data, size_t size);

    static constexpr size_t MIN_COMPRESSION_SIZE = 1024; // Don't compress files smaller than 1KB
    static constexpr double MIN_COMPRESSION_RATIO = 0.9; // Must achieve at least 10% compression
    
private:
};

/**
 * @brief Performance metrics for compression operations
 */
struct CompressionMetrics {
    size_t originalSize = 0;
    size_t compressedSize = 0;
    double compressionRatio = 0.0;
    uint64_t compressionTimeMs = 0;
    uint64_t decompressionTimeMs = 0;
    bool compressionUsed = false;
};

/**
 * @brief Enhanced compression wrapper with performance tracking
 */
class EnhancedCompressionWrapper {
public:
    /**
     * @brief Compress data with performance tracking
     * @param data Input data
     * @param size Data size
     * @param metrics Output metrics
     * @return Compressed data, original data if compression not beneficial
     */
    static std::vector<uint8_t> compressWithMetrics(const uint8_t* data, size_t size, CompressionMetrics& metrics);
    
    /**
     * @brief Decompress data with performance tracking
     * @param compressedData Compressed data
     * @param wasCompressed Whether data was actually compressed
     * @param metrics Output metrics
     * @return Decompressed data
     */
    static std::vector<uint8_t> decompressWithMetrics(const std::vector<uint8_t>& compressedData, bool wasCompressed, CompressionMetrics& metrics);
};
