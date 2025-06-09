// blowfish.cpp - originally written and placed in the public domain by Wei Dai

#include "pch.h"
#include "blowfish.h"
#include "misc.h"

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Initializes the Blowfish key schedule with the provided key.
 *
 * Expands the user-supplied key into the Blowfish P-box and S-box arrays, preparing the cipher for encryption or decryption. The key bytes are cyclically XORed into the P-box, and the arrays are further processed by repeated encryption of zero blocks to fully diffuse the key material. If the cipher is set for decryption, the P-box entries are swapped to reverse the key schedule.
 *
 * @param key_string Pointer to the key material.
 * @param keylength Length of the key in bytes.
 */
void Blowfish::Base::UncheckedSetKey(const byte *key_string, unsigned int keylength, const NameValuePairs &)
{
	AssertValidKeyLength(keylength);

	unsigned i, j=0, k;
	word32 data, dspace[2] = {0, 0};

	std::memcpy(pbox, p_init, sizeof(p_init));
	std::memcpy(sbox, s_init, sizeof(s_init));

	// Xor key string into encryption key vector
	for (i=0 ; i<ROUNDS+2 ; ++i)
	{
		data = 0 ;
		for (k=0 ; k<4 ; ++k )
			data = (data << 8) | key_string[j++ % keylength];
		pbox[i] ^= data;
	}

	crypt_block(dspace, pbox);

	for (i=0; i<ROUNDS; i+=2)
		crypt_block(pbox+i, pbox+i+2);

	crypt_block(pbox+ROUNDS, sbox);

	for (i=0; i<4*256-2; i+=2)
		crypt_block(sbox+i, sbox+i+2);

	if (!IsForwardTransformation())
		for (i=0; i<(ROUNDS+2)/2; i++)
			std::swap(pbox[i], pbox[ROUNDS+1-i]);
}

/**
 * @brief Encrypts a 64-bit block using the Blowfish algorithm.
 *
 * Applies the Blowfish Feistel network to the input block using the current P-box and S-box values, producing an encrypted output block. The input and output are each represented as two 32-bit words.
 *
 * @param in Input block as two 32-bit words.
 * @param out Output block as two 32-bit words containing the encrypted result.
 */
void Blowfish::Base::crypt_block(const word32 in[2], word32 out[2]) const
{
	word32 left = in[0];
	word32 right = in[1];

	const word32 *const s=sbox;
	const word32 *p=pbox;

	left ^= p[0];

	for (unsigned i=0; i<ROUNDS/2; i++)
	{
		right ^= (((s[GETBYTE(left,3)] + s[256+GETBYTE(left,2)])
			  ^ s[2*256+GETBYTE(left,1)]) + s[3*256+GETBYTE(left,0)])
			  ^ p[2*i+1];

		left ^= (((s[GETBYTE(right,3)] + s[256+GETBYTE(right,2)])
			 ^ s[2*256+GETBYTE(right,1)]) + s[3*256+GETBYTE(right,0)])
			 ^ p[2*i+2];
	}

	right ^= p[ROUNDS+1];

	out[0] = right;
	out[1] = left;
}

/**
 * @brief Encrypts a 64-bit input block with Blowfish and XORs the result with another block.
 *
 * Reads a 64-bit input block in big-endian order, encrypts it using the Blowfish algorithm, XORs the encrypted output with the provided xorBlock, and writes the result to outBlock in big-endian format.
 *
 * @param inBlock Pointer to the 8-byte input block to encrypt.
 * @param xorBlock Pointer to the 8-byte block to XOR with the encrypted output.
 * @param outBlock Pointer to the 8-byte buffer where the result is written.
 */
void Blowfish::Base::ProcessAndXorBlock(const byte *inBlock, const byte *xorBlock, byte *outBlock) const
{
	typedef BlockGetAndPut<word32, BigEndian> Block;

	word32 left, right;
	Block::Get(inBlock)(left)(right);

	const word32 *const s=sbox;
	const word32 *p=pbox;

	left ^= p[0];

	for (unsigned i=0; i<ROUNDS/2; i++)
	{
		right ^= (((s[GETBYTE(left,3)] + s[256+GETBYTE(left,2)])
			  ^ s[2*256+GETBYTE(left,1)]) + s[3*256+GETBYTE(left,0)])
			  ^ p[2*i+1];

		left ^= (((s[GETBYTE(right,3)] + s[256+GETBYTE(right,2)])
			 ^ s[2*256+GETBYTE(right,1)]) + s[3*256+GETBYTE(right,0)])
			 ^ p[2*i+2];
	}

	right ^= p[ROUNDS+1];

	Block::Put(xorBlock, outBlock)(right)(left);
}

NAMESPACE_END
