#include "../../include/utils/CompressionWrapper.h"
#include <iostream>
#include <chrono>
#include <algorithm>
#include <zlib.h>

// Helper function to log zlib errors
void log_zlib_error(int ret, z_stream* strm) {
    if (strm->msg) {
        std::cerr << "Zlib error: " << ret << " - " << strm->msg << std::endl;
    } else {
        std::cerr << "Zlib error: " << ret << std::endl;
    }
}

std::vector<uint8_t> CompressionWrapper::compress(const uint8_t* data, size_t size) {
    if (!data || size == 0) {
        return {};
    }

    z_stream strm;
    strm.zalloc = Z_NULL;
    strm.zfree = Z_NULL;
    strm.opaque = Z_NULL;

    if (deflateInit(&strm, Z_DEFAULT_COMPRESSION) != Z_OK) {
        return {};
    }

    strm.avail_in = static_cast<uInt>(size);
    strm.next_in = (Bytef*)data;

    uLong bound = deflateBound(&strm, static_cast<uLong>(size));
    std::vector<uint8_t> compressed(bound);

    strm.avail_out = bound;
    strm.next_out = (Bytef*)compressed.data();

    int ret = deflate(&strm, Z_FINISH);
    if (ret != Z_STREAM_END) {
        log_zlib_error(ret, &strm);
        deflateEnd(&strm);
        return {};
    }

    compressed.resize(strm.total_out);
    deflateEnd(&strm);
    return compressed;
}

std::vector<uint8_t> CompressionWrapper::compress(const std::string& data) {
    return compress(reinterpret_cast<const uint8_t*>(data.c_str()), data.size());
}

std::vector<uint8_t> CompressionWrapper::decompress(const std::vector<uint8_t>& compressedData) {
    if (compressedData.empty()) {
        return {};
    }

    z_stream strm;
    strm.zalloc = Z_NULL;
    strm.zfree = Z_NULL;
    strm.opaque = Z_NULL;

    if (inflateInit(&strm) != Z_OK) {
        return {};
    }

    strm.avail_in = static_cast<uInt>(compressedData.size());
    strm.next_in = (Bytef*)compressedData.data();

    // A starting buffer size for the decompressed data.
    // This will be expanded if needed.
    size_t buffer_size = compressedData.size() * 4;
    std::vector<uint8_t> decompressed(buffer_size);

    int ret;
    do {
        strm.avail_out = static_cast<uInt>(buffer_size - strm.total_out);
        strm.next_out = (Bytef*)decompressed.data() + strm.total_out;
        ret = inflate(&strm, Z_NO_FLUSH);
        if (ret != Z_OK && ret != Z_STREAM_END) {
            log_zlib_error(ret, &strm);
            inflateEnd(&strm);
            return {};
        }
        if (strm.avail_out == 0 && ret != Z_STREAM_END) {
            buffer_size *= 2;
            decompressed.resize(buffer_size);
        }
    } while (ret != Z_STREAM_END);

    decompressed.resize(strm.total_out);
    inflateEnd(&strm);
    return decompressed;
}

std::string CompressionWrapper::decompressToString(const std::vector<uint8_t>& compressedData) {
    auto decompressed = decompress(compressedData);
    if (decompressed.empty()) {
        return "";
    }
    
    return std::string(decompressed.begin(), decompressed.end());
}

double CompressionWrapper::getCompressionRatio(size_t originalSize, size_t compressedSize) {
    if (originalSize == 0) {
        return 0.0;
    }
    
    return static_cast<double>(compressedSize) / static_cast<double>(originalSize);
}

bool CompressionWrapper::shouldCompress(const uint8_t* data, size_t size) {
    if (!data || size < MIN_COMPRESSION_SIZE) {
        return false;
    }
    
    // With zlib, it's almost always beneficial to at least try to compress,
    // as it's fast and effective on a wide range of data.
    // The decision to use the compressed data will be made based on the result.
    return true;
}

std::vector<uint8_t> EnhancedCompressionWrapper::compressWithMetrics(const uint8_t* data, size_t size, CompressionMetrics& metrics) {
    auto start = std::chrono::high_resolution_clock::now();
    
    metrics.originalSize = size;
    
    std::vector<uint8_t> result;
    
    if (CompressionWrapper::shouldCompress(data, size)) {
        result = CompressionWrapper::compress(data, size);
        metrics.compressionUsed = result.size() < size;
    } else {
        metrics.compressionUsed = false;
    }

    if (!metrics.compressionUsed) {
        result.assign(data, data + size);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    metrics.compressionTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    metrics.compressedSize = result.size();
    metrics.compressionRatio = CompressionWrapper::getCompressionRatio(size, result.size());
    
    return result;
}

std::vector<uint8_t> EnhancedCompressionWrapper::decompressWithMetrics(const std::vector<uint8_t>& compressedData, bool wasCompressed, CompressionMetrics& metrics) {
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<uint8_t> result;
    
    if (wasCompressed) {
        result = CompressionWrapper::decompress(compressedData);
    } else {
        result = compressedData; // Data wasn't compressed
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    metrics.decompressionTimeMs = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    return result;
}