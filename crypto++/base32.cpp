// base32.cpp - written and placed in the public domain by Frank Palazzolo, based on hex.cpp by Wei Dai
//              extended hex alphabet added by JW in November, 2017.

#include "pch.h"
#include "base32.h"

NAMESPACE_BEGIN(CryptoPP)
ANONYMOUS_NAMESPACE_BEGIN

const byte s_stdUpper[] = "ABCDEFGHIJKMNPQRSTUVWXYZ23456789";
const byte s_stdLower[] = "abcdefghijkmnpqrstuvwxyz23456789";
const byte s_hexUpper[] = "0123456789ABCDEFGHIJKLMNOPQRSTUV";
const byte s_hexLower[] = "0123456789abcdefghijklmnopqrstuv";

const int s_array[256] = {
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, 24, 25, 26, 27, 28, 29, 30, 31, -1, -1, -1, -1, -1, -1,
	-1,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, -1, 11, 12, -1,
	13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, -1, -1, -1, -1, -1,
	-1,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, -1, 11, 12, -1,
	13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1
};

const int s_hexArray[256] = {
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, -1, -1, -1, -1, -1, -1,
	-1, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
	25, 26, 27, 28, 29, 30, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
	25, 26, 27, 28, 29, 30, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
	-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1
};

/**
 * @brief Initializes the Base32 encoder with specified parameters.
 *
 * Configures the encoder to use either uppercase or lowercase Base32 alphabet based on the "Uppercase" parameter (default is true).
 * Sets the encoding lookup array and the log2 base to 5 for Base32 encoding.
 */
ANONYMOUS_NAMESPACE_END

void Base32Encoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	bool uppercase = parameters.GetValueWithDefault(Name::Uppercase(), true);
	m_filter->Initialize(CombinedNameValuePairs(
		parameters,
		MakeParameters(Name::EncodingLookupArray(), uppercase ? &s_stdUpper[0] : &s_stdLower[0], false)(Name::Log2Base(), 5, true)));
}

/**
 * @brief Initializes the Base32 decoder with the specified parameters.
 *
 * Combines the provided parameters with the default Base32 decoding lookup array and a log2 base of 5,
 * then initializes the underlying BaseN decoder with these settings.
 */
void Base32Decoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	BaseN_Decoder::IsolatedInitialize(CombinedNameValuePairs(
		parameters,
		MakeParameters(Name::DecodingLookupArray(), GetDefaultDecodingLookupArray(), false)(Name::Log2Base(), 5, true)));
}

/**
 * @brief Returns the default decoding lookup array for standard Base32 decoding.
 *
 * @return Pointer to the integer array used for mapping ASCII characters to Base32 values.
 */
const int *Base32Decoder::GetDefaultDecodingLookupArray()
{
	return s_array;
}

/**
 * @brief Initializes the Base32Hex encoder with the specified parameters.
 *
 * Configures the encoder to use either uppercase or lowercase Base32Hex alphabet based on the "Uppercase" parameter (default is true).
 * Sets the encoding lookup array and the log2 base to 5 for Base32Hex encoding.
 */
void Base32HexEncoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	bool uppercase = parameters.GetValueWithDefault(Name::Uppercase(), true);
	m_filter->Initialize(CombinedNameValuePairs(
		parameters,
		MakeParameters(Name::EncodingLookupArray(), uppercase ? &s_hexUpper[0] : &s_hexLower[0], false)(Name::Log2Base(), 5, true)));
}

/**
 * @brief Initializes the Base32Hex decoder with the specified parameters.
 *
 * Combines the provided parameters with the default Base32Hex decoding lookup array and a log2 base of 5, then initializes the underlying BaseN decoder.
 */
void Base32HexDecoder::IsolatedInitialize(const NameValuePairs &parameters)
{
	BaseN_Decoder::IsolatedInitialize(CombinedNameValuePairs(
		parameters,
		MakeParameters(Name::DecodingLookupArray(), GetDefaultDecodingLookupArray(), false)(Name::Log2Base(), 5, true)));
}

/**
 * @brief Returns the default decoding lookup array for Base32Hex decoding.
 *
 * @return Pointer to the static integer array used for Base32Hex character decoding.
 */
const int *Base32HexDecoder::GetDefaultDecodingLookupArray()
{
	return s_hexArray;
}

NAMESPACE_END
