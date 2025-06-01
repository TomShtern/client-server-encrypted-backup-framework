#pragma once

#include <cstdint>
#include <cstddef>

// CRC32 checksum functionality compatible with Linux cksum command
uint32_t calculateCRC(const uint8_t* data, size_t size);
uint32_t calculateCRC32(const uint8_t* data, size_t size);
