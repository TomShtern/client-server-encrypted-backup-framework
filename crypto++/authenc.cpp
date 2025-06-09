// authenc.cpp - originally written and placed in the public domain by Wei Dai

#include "pch.h"

#ifndef CRYPTOPP_IMPORTS

#include "authenc.h"

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Authenticates input data in fixed-size blocks, buffering incomplete blocks.
 *
 * Processes the input data in blocks of the cipher's authentication block size, authenticating each full block. Any remaining partial block data is buffered for future calls. Handles leftover buffered data from previous calls to ensure all data is authenticated in block-aligned segments.
 *
 * @param input Pointer to the data to authenticate.
 * @param len Length of the input data in bytes.
 */
void AuthenticatedSymmetricCipherBase::AuthenticateData(const byte *input, size_t len)
{
	// UBsan finding with -std=c++03 using memcpy
	CRYPTOPP_ASSERT(input && len);
	if(!input || !len) return;

	unsigned int blockSize = AuthenticationBlockSize();
	unsigned int &num = m_bufferedDataLength;
	byte* data = m_buffer.begin();

	if (data && num)	// process left over data
	{
		if (num+len >= blockSize)
		{
			std::memcpy(data+num, input, blockSize-num);
			AuthenticateBlocks(data, blockSize);
			input += (blockSize-num);
			len -= (blockSize-num);
			num = 0;
			// drop through and do the rest
		}
		else
		{
			std::memcpy(data+num, input, len);
			num += (unsigned int)len;
			return;
		}
	}

	// now process the input data in blocks of blockSize bytes and save the leftovers to m_data
	if (len >= blockSize)
	{
		size_t leftOver = AuthenticateBlocks(input, len);
		input += (len - leftOver);
		len = leftOver;
	}

	if (data && len)
		std::memcpy(data, input, len);
	num = (unsigned int)len;
}

/**
 * @brief Sets the encryption key and initializes the cipher state.
 *
 * Initializes the cipher with the provided key and parameters, resets internal state and buffered data, and optionally resynchronizes with an IV if supplied in the parameters.
 */
void AuthenticatedSymmetricCipherBase::SetKey(const byte *userKey, size_t keylength, const NameValuePairs &params)
{
	m_bufferedDataLength = 0;
	m_state = State_Start;

	this->SetKeyWithoutResync(userKey, keylength, params);
	m_state = State_KeySet;

	size_t length;
	const byte *iv = GetIVAndThrowIfInvalid(params, length);
	if (iv)
		Resynchronize(iv, (int)length);
}

/**
 * @brief Reinitializes the cipher with a new initialization vector (IV).
 *
 * Resets internal state and counters, then calls Resync with the provided IV after validating its length. Throws an exception if called before the key is set.
 *
 * @param iv Pointer to the initialization vector.
 * @param length Length of the initialization vector in bytes.
 *
 * @throws BadState if the key has not been set prior to calling this method.
 */
void AuthenticatedSymmetricCipherBase::Resynchronize(const byte *iv, int length)
{
	if (m_state < State_KeySet)
		throw BadState(AlgorithmName(), "Resynchronize", "key is set");

	m_bufferedDataLength = 0;
	m_totalHeaderLength = m_totalMessageLength = m_totalFooterLength = 0;
	m_state = State_KeySet;

	Resync(iv, this->ThrowIfInvalidIVLength(length));
	m_state = State_IVSet;
}

/**
 * @brief Processes additional authenticated data (AAD) or footer data based on the current cipher state.
 *
 * Accepts input data for authentication as either header (AAD) or footer, depending on the internal state. Throws an exception if called before both key and IV are set. Transitions to footer authentication if called after message processing has begun.
 *
 * @param input Pointer to the data to authenticate.
 * @param length Number of bytes to authenticate.
 *
 * @throws BadState if called before key and IV are set.
 */
void AuthenticatedSymmetricCipherBase::Update(const byte *input, size_t length)
{
	// Part of original authenc.cpp code. Don't remove it.
	if (length == 0) {return;}

	switch (m_state)
	{
	case State_Start:
	case State_KeySet:
		throw BadState(AlgorithmName(), "Update", "setting key and IV");
	case State_IVSet:
		AuthenticateData(input, length);
		m_totalHeaderLength += length;
		break;
	case State_AuthUntransformed:
	case State_AuthTransformed:
		AuthenticateLastConfidentialBlock();
		m_bufferedDataLength = 0;
		m_state = State_AuthFooter;
		// fall through
	case State_AuthFooter:
		AuthenticateData(input, length);
		m_totalFooterLength += length;
		break;
	default:
		CRYPTOPP_ASSERT(false);
	}
}

/**
 * @brief Processes input data for authenticated encryption or decryption.
 *
 * Depending on the current state, this function authenticates and transforms the input data as required by the cipher mode. It enforces message length limits and correct state transitions, authenticating data either before or after transformation based on whether authentication is performed on plaintext or ciphertext. Throws an exception if called in an invalid state or if the message length exceeds the allowed maximum.
 *
 * @param outString Buffer to receive the processed output data.
 * @param inString Input data to be processed.
 * @param length Number of bytes to process.
 */
void AuthenticatedSymmetricCipherBase::ProcessData(byte *outString, const byte *inString, size_t length)
{
	if (m_state >= State_IVSet && length > MaxMessageLength()-m_totalMessageLength)
		throw InvalidArgument(AlgorithmName() + ": message length exceeds maximum");
	m_totalMessageLength += length;

reswitch:
	switch (m_state)
	{
	case State_Start:
	case State_KeySet:
		throw BadState(AlgorithmName(), "ProcessData", "setting key and IV");
	case State_AuthFooter:
		throw BadState(AlgorithmName(), "ProcessData was called after footer input has started");
	case State_IVSet:
		AuthenticateLastHeaderBlock();
		m_bufferedDataLength = 0;
		m_state = AuthenticationIsOnPlaintext()==IsForwardTransformation() ? State_AuthUntransformed : State_AuthTransformed;
		goto reswitch;
	case State_AuthUntransformed:
		AuthenticateData(inString, length);
		AccessSymmetricCipher().ProcessData(outString, inString, length);
		break;
	case State_AuthTransformed:
		AccessSymmetricCipher().ProcessData(outString, inString, length);
		AuthenticateData(outString, length);
		break;
	default:
		CRYPTOPP_ASSERT(false);
	}
}

/**
 * @brief Finalizes authentication and produces a truncated MAC.
 *
 * Validates the requested MAC size and ensures header and footer lengths do not exceed their maximum allowed values. Depending on the current state, finalizes authentication of any remaining header, message, or footer data, and writes the truncated MAC to the provided buffer. Resets the internal state to allow for new operations.
 *
 * @param mac Pointer to the buffer where the truncated MAC will be written.
 * @param macSize Number of bytes of the MAC to output.
 *
 * @throws InvalidArgument if the MAC size, header length, or footer length is invalid.
 * @throws BadState if called before key and IV are set.
 */
void AuthenticatedSymmetricCipherBase::TruncatedFinal(byte *mac, size_t macSize)
{
	// https://github.com/weidai11/cryptopp/issues/954
	this->ThrowIfInvalidTruncatedSize(macSize);

	if (m_totalHeaderLength > MaxHeaderLength())
		throw InvalidArgument(AlgorithmName() + ": header length of " + IntToString(m_totalHeaderLength) + " exceeds the maximum of " + IntToString(MaxHeaderLength()));

	if (m_totalFooterLength > MaxFooterLength())
	{
		if (MaxFooterLength() == 0)
			throw InvalidArgument(AlgorithmName() + ": additional authenticated data (AAD) cannot be input after data to be encrypted or decrypted");
		else
			throw InvalidArgument(AlgorithmName() + ": footer length of " + IntToString(m_totalFooterLength) + " exceeds the maximum of " + IntToString(MaxFooterLength()));
	}

	switch (m_state)
	{
	case State_Start:
	case State_KeySet:
		throw BadState(AlgorithmName(), "TruncatedFinal", "setting key and IV");

	case State_IVSet:
		AuthenticateLastHeaderBlock();
		m_bufferedDataLength = 0;
		// fall through

	case State_AuthUntransformed:
	case State_AuthTransformed:
		AuthenticateLastConfidentialBlock();
		m_bufferedDataLength = 0;
		// fall through

	case State_AuthFooter:
		AuthenticateLastFooterBlock(mac, macSize);
		m_bufferedDataLength = 0;
		break;

	default:
		CRYPTOPP_ASSERT(false);
	}

	m_state = State_KeySet;
}

NAMESPACE_END

#endif
