/**
 * @file crc.cpp
 * @brief Implementation of canonical CRC32 functionality
 */

#include "crc.h"
#include <iostream>

namespace client {
namespace shared {

// Standard POSIX cksum CRC32 table for polynomial 0x04C11DB7
static const uint32_t CRC32_TABLE[256] = {
    0x00000000, 0x04C11DB7, 0x09823B6E, 0x0D4326D9,
    0x130476DC, 0x17C56B6B, 0x1A864DB2, 0x1E475005,
    0x2608EDB8, 0x22C9F00F, 0x2F8AD6D6, 0x2B4BCB61,
    0x350C9B64, 0x31CD86D3, 0x3C8EA00A, 0x384FBDBD,
    0x4C11DB70, 0x48D0C6C7, 0x4593E01E, 0x4152FDA9,
    0x5F15ADAC, 0x5BD4B01B, 0x569796C2, 0x52568B75,
    0x6A1936C8, 0x6ED82B7F, 0x639B0DA6, 0x675A1011,
    0x791D4014, 0x7DDC5DA3, 0x709F7B7A, 0x745E66CD,
    0x9823B6E0, 0x9CE2AB57, 0x91A18D8E, 0x95609039,
    0x8B27C03C, 0x8FE6DD8B, 0x82A5FB52, 0x8664E6E5,
    0xBE2B5B58, 0xBAEA46EF, 0xB7A96036, 0xB3687D81,
    0xAD2F2D84, 0xA9EE3033, 0xA4AD16EA, 0xA06C0B5D,
    0xD4326D90, 0xD0F37027, 0xDDB056FE, 0xD9714B49,
    0xC7361B4C, 0xC3F706FB, 0xCEB42022, 0xCA753D95,
    0xF23C8028, 0xF6FD9D9F, 0xFBBEBB46, 0xFF7FA6F1,
    0xE138F6F4, 0xE5F9EB43, 0xE8BACD9A, 0xEC7BD02D,
    0x68DDB3F8, 0x6C1CAE4F, 0x615F8896, 0x659E9521,
    0x7BD9C524, 0x7F18D893, 0x725BFE4A, 0x769AE3FD,
    0x4ED55640, 0x4A144BF7, 0x47576D2E, 0x43967099,
    0x5DD1209C, 0x59103D2B, 0x54531BF2, 0x50920645,
    0x246C6088, 0x20AD7D3F, 0x2DEE5BE6, 0x292F4651,
    0x37681654, 0x33A90BE3, 0x3EEA2D3A, 0x3A2B308D,
    0x02648D30, 0x06A59087, 0x0BE6B65E, 0x0F27ABE9,
    0x1160FBEC, 0x15A1E65B, 0x18E2C082, 0x1C23DD35,
    0xD06F6BAE, 0xD4AE7619, 0xD9ED50C0, 0xDD2C4D77,
    0xC36B1D72, 0xC7AA00C5, 0xCA69261C, 0xCEA83BAB,
    0xF6E78616, 0xF2269BA1, 0xFF65BD78, 0xFBA4A0CF,
    0xE5E3F0CA, 0xE122ED7D, 0xEC61CBA4, 0xE8A0D613,
    0x9C5EB4DE, 0x989FA969, 0x95DC8FB0, 0x911D9207,
    0x8F5AC202, 0x8B9BDFB5, 0x86D8F96C, 0x8219E4DB,
    0xBA565966, 0xBE9744D1, 0xB3D46208, 0xB7157FBF,
    0xA9522FBA, 0xAD93320D, 0xA0D014D4, 0xA4110963,
    0x1BB6D7F0, 0x1F77CA47, 0x1234EC9E, 0x16F5F129,
    0x08B2A12C, 0x0C73BC9B, 0x01309A42, 0x05F187F5,
    0x3DBE3A48, 0x397F27FF, 0x343C0126, 0x30FD1C91,
    0x2EBA4C94, 0x2A7B5123, 0x273877FA, 0x23F96A4D,
    0x57070880, 0x53C61537, 0x5E8533EE, 0x5A442E59,
    0x44037E5C, 0x40C263EB, 0x4D814532, 0x49405885,
    0x710FE538, 0x75CEF88F, 0x788DDE56, 0x7C4CC3E1,
    0x620B93E4, 0x66CA8E53, 0x6B89A88A, 0x6F48B53D,
    0x73B6D7F8, 0x7777CA4F, 0x7A34EC96, 0x7EF5F121,
    0x60B2A124, 0x6473BC93, 0x69309A4A, 0x6DF187FD,
    0x55BE3A40, 0x517F27F7, 0x5C3C012E, 0x58FD1C99,
    0x46BA4C9C, 0x427B512B, 0x4F3877F2, 0x4BF96A45,
    0x3F070888, 0x3BC6153F, 0x368533E6, 0x32442E51,
    0x2C037E54, 0x28C263E3, 0x2581453A, 0x2140588D,
    0x190FE530, 0x1DCEF887, 0x108DDE5E, 0x144CC3E9,
    0x0A0B93EC, 0x0ECA8E5B, 0x0389A882, 0x0748B535,
    0xE3A1CBC1, 0xE760D676, 0xEA23F0AF, 0xEEE2ED18,
    0xF0A5BD1D, 0xF464A0AA, 0xF9278673, 0xFDE69BC4,
    0xC5A92679, 0xC1683BCE, 0xCC2B1D17, 0xC8EA00A0,
    0xD6AD50A5, 0xD26C4D12, 0xDF2F6BCB, 0xDBEE767C,
    0xAF1014B1, 0xABD10906, 0xA6922FDF, 0xA2533268,
    0xBC14626D, 0xB8D57FDA, 0xB5965903, 0xB15744B4,
    0x8918F909, 0x8DD9E4BE, 0x809AC267, 0x845BDFD0,
    0x9A1C8FD5, 0x9EDD9262, 0x939EB4BB, 0x975FA90C,
    0x8B81CB89, 0x8F40D63E, 0x8203F0E7, 0x86C2ED50,
    0x9885BD55, 0x9C44A0E2, 0x9107863B, 0x95C69B8C,
    0xAD892631, 0xA9483B86, 0xA40B1D5F, 0xA0CA00E8,
    0xBE8D50ED, 0xBA4C4D5A, 0xB70F6B83, 0xB3CE7634,
    0xC73014F9, 0xC3F1094E, 0xCE922F97, 0xCA533220,
    0xD4146225, 0xD0D57F92, 0xDD96594B, 0xD95744FC,
    0xE118F941, 0xE5D9E4F6, 0xE89AC22F, 0xEC5BDF98,
    0xF21C8F9D, 0xF6DD922A, 0xFB9EB4F3, 0xFF5FA944
};

uint32_t calculate_crc32(const uint8_t* data, size_t size) {
    uint32_t crc = 0x00000000;
    
    // Process each byte of data
    for (size_t i = 0; i < size; i++) {
        crc = (crc << 8) ^ CRC32_TABLE[(crc >> 24) ^ data[i]];
    }
    
    // Process the length of the data (POSIX cksum requirement)
    size_t length = size;
    while (length > 0) {
        crc = (crc << 8) ^ CRC32_TABLE[(crc >> 24) ^ (length & 0xFF)];
        length >>= 8;
    }
    
    // Return one's complement
    return ~crc;
}

uint32_t calculate_crc32(const std::string& data) {
    return calculate_crc32(reinterpret_cast<const uint8_t*>(data.c_str()), data.length());
}

uint32_t calculate_crc32(const std::vector<uint8_t>& data) {
    return calculate_crc32(data.data(), data.size());
}

bool verify_crc32(const uint8_t* data, size_t size, uint32_t expected_crc) {
    uint32_t calculated_crc = calculate_crc32(data, size);
    return calculated_crc == expected_crc;
}

// CRC32Stream implementation
CRC32Stream::CRC32Stream() : crc_(0), total_length_(0) {}

void CRC32Stream::update(const uint8_t* data, size_t size) {
    for (size_t i = 0; i < size; i++) {
        crc_ = (crc_ << 8) ^ CRC32_TABLE[(crc_ >> 24) ^ data[i]];
    }
    total_length_ += size;
}

void CRC32Stream::update(const std::string& data) {
    update(reinterpret_cast<const uint8_t*>(data.c_str()), data.length());
}

void CRC32Stream::update(const std::vector<uint8_t>& data) {
    update(data.data(), data.size());
}

uint32_t CRC32Stream::finalize() {
    uint32_t final_crc = crc_;
    size_t length = total_length_;
    
    // Process the total length (POSIX cksum requirement)
    while (length > 0) {
        final_crc = (final_crc << 8) ^ CRC32_TABLE[(final_crc >> 24) ^ (length & 0xFF)];
        length >>= 8;
    }
    
    // Return one's complement
    return ~final_crc;
}

void CRC32Stream::reset() {
    crc_ = 0;
    total_length_ = 0;
}

const uint32_t* get_crc32_table() {
    return CRC32_TABLE;
}

// Legacy compatibility functions
namespace legacy {
    uint32_t calculateCRC(const uint8_t* data, size_t size) {
        std::cerr << "Warning: calculateCRC() is deprecated, use calculate_crc32() instead" << std::endl;
        return calculate_crc32(data, size);
    }

    uint32_t calculateCRC32(const uint8_t* data, size_t size) {
        std::cerr << "Warning: calculateCRC32() is deprecated, use calculate_crc32() instead" << std::endl;
        return calculate_crc32(data, size);
    }
}

} // namespace shared
} // namespace client
