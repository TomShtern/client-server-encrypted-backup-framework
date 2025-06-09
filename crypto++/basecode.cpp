// basecode.cpp - originally written and placed in the public domain by Wei Dai

#include "pch.h"
#include "config.h"

#ifndef CRYPTOPP_IMPORTS

#include "basecode.h"
#include "fltrimpl.h"
#include <ctype.h>

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Initializes the BaseN encoder with encoding parameters.
 *
 * Retrieves the encoding alphabet, bits per character, and optional padding byte from the provided parameters. Validates that the bits per character value is between 1 and 7 inclusive. Calculates the output block size to ensure proper alignment for encoding. Initializes internal buffers and state for encoding operations.
 */
void BaseN_Encoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	parameters.GetRequiredParameter("BaseN_Encoder", Name::EncodingLookupArray(), m_alphabet);

	parameters.GetRequiredIntParameter("BaseN_Encoder", Name::Log2Base(), m_bitsPerChar);
	if (m_bitsPerChar <= 0 || m_bitsPerChar >= 8)
		throw InvalidArgument("BaseN_Encoder: Log2Base must be between 1 and 7 inclusive");

	byte padding;
	bool pad;
	if (parameters.GetValue(Name::PaddingByte(), padding))
		pad = parameters.GetValueWithDefault(Name::Pad(), true);
	else
		pad = false;
	m_padding = pad ? padding : -1;

	m_bytePos = m_bitPos = 0;

	int i = 8;
	while (i%m_bitsPerChar != 0)
		i += 8;
	m_outputBlockSize = i/m_bitsPerChar;

	m_outBuf.New(m_outputBlockSize);
}

/**
 * @brief Encodes input bytes into BaseN representation and outputs encoded blocks.
 *
 * Processes the input buffer, converting bytes into BaseN-encoded characters using the configured alphabet and bits per character. Handles bit alignment across input and output, manages output buffering, and applies padding if enabled. On message end, outputs any remaining encoded data and finalizes the block.
 *
 * @param begin Pointer to the input byte buffer.
 * @param length Number of bytes to encode from the input buffer.
 * @param messageEnd Nonzero if this is the final input segment.
 * @param blocking Indicates whether the operation should block (implementation-dependent).
 * @return Number of input bytes processed.
 */
size_t BaseN_Encoder::Put2(const byte *begin, size_t length, int messageEnd, bool blocking)
{
	FILTER_BEGIN;
	while (m_inputPosition < length)
	{
		if (m_bytePos == 0)
			std::memset(m_outBuf, 0, m_outputBlockSize);

		{
		unsigned int b = begin[m_inputPosition++], bitsLeftInSource = 8;
		while (true)
		{
			CRYPTOPP_ASSERT(m_bitsPerChar-m_bitPos >= 0);
			unsigned int bitsLeftInTarget = (unsigned int)(m_bitsPerChar-m_bitPos);
			m_outBuf[m_bytePos] |= b >> (8-bitsLeftInTarget);
			if (bitsLeftInSource >= bitsLeftInTarget)
			{
				m_bitPos = 0;
				++m_bytePos;
				bitsLeftInSource -= bitsLeftInTarget;
				if (bitsLeftInSource == 0)
					break;
				b <<= bitsLeftInTarget;
				b &= 0xff;
			}
			else
			{
				m_bitPos += bitsLeftInSource;
				break;
			}
		}
		}

		CRYPTOPP_ASSERT(m_bytePos <= m_outputBlockSize);
		if (m_bytePos == m_outputBlockSize)
		{
			int i;
			for (i=0; i<m_bytePos; i++)
			{
				CRYPTOPP_ASSERT(m_outBuf[i] < (1 << m_bitsPerChar));
				m_outBuf[i] = m_alphabet[m_outBuf[i]];
			}
			FILTER_OUTPUT(1, m_outBuf, m_outputBlockSize, 0);

			m_bytePos = m_bitPos = 0;
		}
	}
	if (messageEnd)
	{
		if (m_bitPos > 0)
			++m_bytePos;

		int i;
		for (i=0; i<m_bytePos; i++)
			m_outBuf[i] = m_alphabet[m_outBuf[i]];

		if (m_padding != -1 && m_bytePos > 0)
		{
			std::memset(m_outBuf+m_bytePos, m_padding, m_outputBlockSize-m_bytePos);
			m_bytePos = m_outputBlockSize;
		}
		FILTER_OUTPUT(2, m_outBuf, m_bytePos, messageEnd);
		m_bytePos = m_bitPos = 0;
	}
	FILTER_END_NO_MESSAGE_END;
}

/**
 * @brief Initializes the BaseN decoder with decoding parameters.
 *
 * Retrieves and validates the decoding lookup array and bits per character from the provided parameters. Calculates the output block size based on the bits per character and prepares internal buffers for decoding operations.
 */
void BaseN_Decoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	parameters.GetRequiredParameter("BaseN_Decoder", Name::DecodingLookupArray(), m_lookup);

	parameters.GetRequiredIntParameter("BaseN_Decoder", Name::Log2Base(), m_bitsPerChar);
	if (m_bitsPerChar <= 0 || m_bitsPerChar >= 8)
		throw InvalidArgument("BaseN_Decoder: Log2Base must be between 1 and 7 inclusive");

	m_bytePos = m_bitPos = 0;

	int i = m_bitsPerChar;
	while (i%8 != 0)
		i += m_bitsPerChar;
	m_outputBlockSize = i/8;

	m_outBuf.New(m_outputBlockSize);
}

/**
 * @brief Decodes BaseN-encoded input bytes into their original binary representation.
 *
 * Processes input characters using a lookup table to convert each character to its corresponding value, accumulating bits into output bytes according to the configured bits per character. Outputs decoded bytes in blocks when the output buffer is full. At message end, outputs any remaining decoded bytes.
 *
 * @param begin Pointer to the input buffer containing BaseN-encoded data.
 * @param length Number of bytes to process from the input buffer.
 * @param messageEnd Nonzero if this is the final input segment.
 * @param blocking Indicates whether the operation should block (implementation-dependent).
 * @return Number of input bytes processed.
 */
size_t BaseN_Decoder::Put2(const byte *begin, size_t length, int messageEnd, bool blocking)
{
	FILTER_BEGIN;
	while (m_inputPosition < length)
	{
		unsigned int value;
		value = m_lookup[begin[m_inputPosition++]];
		if (value >= 256)
			continue;

		if (m_bytePos == 0 && m_bitPos == 0)
			std::memset(m_outBuf, 0, m_outputBlockSize);

		{
			int newBitPos = m_bitPos + m_bitsPerChar;
			if (newBitPos <= 8)
				m_outBuf[m_bytePos] |= value << (8-newBitPos);
			else
			{
				m_outBuf[m_bytePos] |= value >> (newBitPos-8);
				m_outBuf[m_bytePos+1] |= value << (16-newBitPos);
			}

			m_bitPos = newBitPos;
			while (m_bitPos >= 8)
			{
				m_bitPos -= 8;
				++m_bytePos;
			}
		}

		if (m_bytePos == m_outputBlockSize)
		{
			FILTER_OUTPUT(1, m_outBuf, m_outputBlockSize, 0);
			m_bytePos = m_bitPos = 0;
		}
	}
	if (messageEnd)
	{
		FILTER_OUTPUT(2, m_outBuf, m_bytePos, messageEnd);
		m_bytePos = m_bitPos = 0;
	}
	FILTER_END_NO_MESSAGE_END;
}

/**
 * @brief Initializes a lookup table for decoding BaseN-encoded characters.
 *
 * Populates the lookup array so that each entry maps a character code to its corresponding value in the provided BaseN alphabet. If case insensitivity is enabled, both uppercase and lowercase alphabetic characters are mapped to the same value.
 *
 * @param lookup Pointer to an array of 256 integers to be filled with decoding values.
 * @param alphabet Pointer to the BaseN alphabet array.
 * @param base Number of unique characters in the alphabet.
 * @param caseInsensitive If true, mapping is case-insensitive for alphabetic characters.
 */
void BaseN_Decoder::InitializeDecodingLookupArray(int *lookup, const byte *alphabet, unsigned int base, bool caseInsensitive)
{
	std::fill(lookup, lookup+256, -1);

	for (unsigned int i=0; i<base; i++)
	{
		// Debug asserts for 'lookup[alphabet[i]] == -1' removed because the self tests
		// have unusual tests that try to break the encoders and decoders. Tests include
		// a string of the same characters. I.,e., a string of stars like '********...'.
		if (caseInsensitive && isalpha(alphabet[i]))
		{
			lookup[toupper(alphabet[i])] = i;
			lookup[tolower(alphabet[i])] = i;
		}
		else
		{
			lookup[alphabet[i]] = i;
		}
	}
}

/**
 * @brief Initializes the Grouper filter with grouping, separator, and terminator parameters.
 *
 * Retrieves the group size, separator, and terminator from the provided parameters. If grouping is enabled (group size > 0), the separator is required; otherwise, it is optional. Initializes internal buffers and resets the group counter.
 */
void Grouper::IsolatedInitialize(const NameValuePairs &parameters)
{
	m_groupSize = parameters.GetIntValueWithDefault(Name::GroupSize(), 0);
	ConstByteArrayParameter separator, terminator;
	if (m_groupSize)
		parameters.GetRequiredParameter("Grouper", Name::Separator(), separator);
	else
		parameters.GetValue(Name::Separator(), separator);
	parameters.GetValue(Name::Terminator(), terminator);

	m_separator.Assign(separator.begin(), separator.size());
	m_terminator.Assign(terminator.begin(), terminator.size());
	m_counter = 0;
}

size_t Grouper::Put2(const byte *begin, size_t length, int messageEnd, bool blocking)
{
	FILTER_BEGIN;
	if (m_groupSize)
	{
		while (m_inputPosition < length)
		{
			if (m_counter == m_groupSize)
			{
				FILTER_OUTPUT(1, m_separator, m_separator.size(), 0);
				m_counter = 0;
			}

			size_t len;
			FILTER_OUTPUT2(2, (len = STDMIN(length-m_inputPosition, m_groupSize-m_counter)),
				begin+m_inputPosition, len, 0);
			m_inputPosition += len;
			m_counter += len;
		}
	}
	else
		FILTER_OUTPUT(3, begin, length, 0);

	if (messageEnd)
	{
		FILTER_OUTPUT(4, m_terminator, m_terminator.size(), messageEnd);
		m_counter = 0;
	}
	FILTER_END_NO_MESSAGE_END
}

NAMESPACE_END

#endif
