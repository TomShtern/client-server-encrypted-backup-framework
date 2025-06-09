// 3way.cpp - modified by Wei Dai from Joan Daemen's 3way.c
// The original code and all modifications are in the public domain.

#include "pch.h"
#include "3way.h"
#include "misc.h"

NAMESPACE_BEGIN(CryptoPP)

#if defined(CRYPTOPP_DEBUG) && !defined(CRYPTOPP_DOXYGEN_PROCESSING)
void ThreeWay_TestInstantiations()
{
	ThreeWay::Encryption x1;
	ThreeWay::Decryption x2;
}
#endif

namespace
{
	const word32 START_E = 0x0b0b; // round constant of first encryption round
	const word32 START_D = 0xb1b1; // round constant of first decryption round
}

/**
 * @brief Reverses the order of bits in a 32-bit word.
 *
 * Each bit in the input word is mirrored to its opposite position in the output.
 *
 * @param a The 32-bit word to reverse.
 * @return word32 The input word with its bits in reverse order.
 */
static inline word32 reverseBits(word32 a)
{
	a = ((a & 0xAAAAAAAA) >> 1) | ((a & 0x55555555) << 1);
	a = ((a & 0xCCCCCCCC) >> 2) | ((a & 0x33333333) << 2);
	return ((a & 0xF0F0F0F0) >> 4) | ((a & 0x0F0F0F0F) << 4);
}

#define mu(a0, a1, a2)				\
{									\
	a1 = reverseBits(a1);			\
	word32 t = reverseBits(a0);		\
	a0 = reverseBits(a2);			\
	a2 = t;							\
}

#define pi_gamma_pi(a0, a1, a2)   \
{                                 \
	word32 b0, b2;                          \
	b2 = rotlConstant<1>(a2);               \
	b0 = rotlConstant<22>(a0);				\
	a0 = rotlConstant<1>(b0 ^ (a1|(~b2)));	\
	a2 = rotlConstant<22>(b2 ^ (b0|(~a1))); \
	a1 ^= (b2|(~b0));                       \
}

// thanks to Paulo Barreto for this optimized theta()
#define theta(a0, a1, a2)									\
{ 															\
	word32 b0, b1, c; 										\
	c = a0 ^ a1 ^ a2; 										\
	c = rotlConstant<16>(c) ^ rotlConstant<8>(c);			\
	b0 = (a0 << 24) ^ (a2 >> 8) ^ (a1 << 8) ^ (a0 >> 24); 	\
	b1 = (a1 << 24) ^ (a0 >> 8) ^ (a2 << 8) ^ (a1 >> 24); 	\
	a0 ^= c ^ b0; 											\
	a1 ^= c ^ b1; 											\
	a2 ^= c ^ (b0 >> 16) ^ (b1 << 16); 						\
}

#define rho(a0, a1, a2)			\
{								\
	theta(a0, a1, a2);			\
	pi_gamma_pi(a0, a1, a2);	\
}

/**
 * @brief Sets the ThreeWay cipher key and prepares round keys.
 *
 * Loads a 12-byte user key into internal state, validates its length, and determines the number of rounds from parameters. For decryption, applies the theta and mu transformations and reverses the byte order of the key words.
 */
void ThreeWay::Base::UncheckedSetKey(const byte *uk, unsigned int length, const NameValuePairs &params)
{
	AssertValidKeyLength(length);

	m_rounds = GetRoundsAndThrowIfInvalid(params, this);

	for (unsigned int i=0; i<3; i++)
		m_k[i] = (word32)uk[4*i+3] | ((word32)uk[4*i+2]<<8) | ((word32)uk[4*i+1]<<16) | ((word32)uk[4*i]<<24);

	if (!IsForwardTransformation())
	{
		theta(m_k[0], m_k[1], m_k[2]);
		mu(m_k[0], m_k[1], m_k[2]);
		m_k[0] = ByteReverse(m_k[0]);
		m_k[1] = ByteReverse(m_k[1]);
		m_k[2] = ByteReverse(m_k[2]);
	}
}

/**
 * @brief Encrypts a 12-byte block using the ThreeWay cipher and writes the result XORed with an optional mask.
 *
 * Reads a 12-byte input block in big-endian order, applies the ThreeWay encryption rounds with the configured key, and writes the encrypted output XORed with the provided xorBlock to outBlock in big-endian order.
 *
 * @param inBlock Pointer to the 12-byte input block to encrypt.
 * @param xorBlock Pointer to a 12-byte block to XOR with the encrypted output (may be null).
 * @param outBlock Pointer to the buffer where the 12-byte encrypted (and XORed) output will be written.
 */
void ThreeWay::Enc::ProcessAndXorBlock(const byte *inBlock, const byte *xorBlock, byte *outBlock) const
{
	typedef BlockGetAndPut<word32, BigEndian> Block;

	word32 a0, a1, a2;
	Block::Get(inBlock)(a0)(a1)(a2);

	word32 rc = START_E;

	for(unsigned i=0; i<m_rounds; i++)
	{
		a0 ^= m_k[0] ^ (rc<<16);
		a1 ^= m_k[1];
		a2 ^= m_k[2] ^ rc;
		rho(a0, a1, a2);

		rc <<= 1;
		if (rc&0x10000) rc ^= 0x11011;
	}
	a0 ^= m_k[0] ^ (rc<<16);
	a1 ^= m_k[1];
	a2 ^= m_k[2] ^ rc;
	theta(a0, a1, a2);

	Block::Put(xorBlock, outBlock)(a0)(a1)(a2);
}

/**
 * @brief Decrypts a 12-byte block using the ThreeWay cipher and writes the result XORed with an optional block.
 *
 * Reads a 12-byte input block in little-endian order, applies the ThreeWay decryption rounds, and outputs the decrypted block XORed with `xorBlock` in little-endian order.
 *
 * @param inBlock Pointer to the 12-byte ciphertext input block.
 * @param xorBlock Pointer to a 12-byte block to XOR with the decrypted output (may be null).
 * @param outBlock Pointer to the 12-byte buffer where the decrypted (and XORed) output will be written.
 */
void ThreeWay::Dec::ProcessAndXorBlock(const byte *inBlock, const byte *xorBlock, byte *outBlock) const
{
	typedef BlockGetAndPut<word32, LittleEndian> Block;

	word32 a0, a1, a2;
	Block::Get(inBlock)(a0)(a1)(a2);

	word32 rc = START_D;

	mu(a0, a1, a2);
	for(unsigned i=0; i<m_rounds; i++)
	{
		a0 ^= m_k[0] ^ (rc<<16);
		a1 ^= m_k[1];
		a2 ^= m_k[2] ^ rc;
		rho(a0, a1, a2);

		rc <<= 1;
		if (rc&0x10000) rc ^= 0x11011;
	}
	a0 ^= m_k[0] ^ (rc<<16);
	a1 ^= m_k[1];
	a2 ^= m_k[2] ^ rc;
	theta(a0, a1, a2);
	mu(a0, a1, a2);

	Block::Put(xorBlock, outBlock)(a0)(a1)(a2);
}

NAMESPACE_END
