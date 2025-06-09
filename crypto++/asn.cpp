// asn.cpp - originally written and placed in the public domain by Wei Dai
//           CryptoPP::Test namespace added by JW in February 2017

#include "pch.h"
#include "config.h"

#ifndef CRYPTOPP_IMPORTS

#include "cryptlib.h"
#include "asn.h"
#include "misc.h"

#include <iostream>
#include <iomanip>
#include <sstream>
#include <time.h>

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Encodes a length value in DER format and writes it to the output.
 *
 * Uses the short form for lengths ≤ 127 and the long form for larger values, as specified by ASN.1 DER encoding rules.
 *
 * @param length The length value to encode.
 * @return size_t The number of bytes written to the output.
 */
size_t DERLengthEncode(BufferedTransformation &bt, lword length)
{
	size_t i=0;
	if (length <= 0x7f)
	{
		bt.Put(byte(length));
		i++;
	}
	else
	{
		bt.Put(byte(BytePrecision(length) | 0x80));
		i++;
		for (int j=BytePrecision(length); j; --j)
		{
			bt.Put(byte(length >> (j-1)*8));
			i++;
		}
	}
	return i;
}

/**
 * @brief Decodes a BER-encoded length from the input stream.
 *
 * Reads a length field from the input `BufferedTransformation` according to BER rules, supporting both definite and indefinite forms. Sets `length` to the decoded value and `definiteLength` to indicate whether the length is definite (`true`) or indefinite (`false`). Returns `false` if insufficient data is available; throws on overflow.
 *
 * @return `true` if decoding succeeds or an indefinite length is detected; `false` if more data is needed.
 */
bool BERLengthDecode(BufferedTransformation &bt, lword &length, bool &definiteLength)
{
	byte b;

	if (!bt.Get(b))
		return false;

	if (!(b & 0x80))
	{
		definiteLength = true;
		length = b;
	}
	else
	{
		unsigned int lengthBytes = b & 0x7f;

		if (lengthBytes == 0)
		{
			definiteLength = false;
			return true;
		}

		definiteLength = true;
		length = 0;
		while (lengthBytes--)
		{
			if (length >> (8*(sizeof(length)-1)))
				BERDecodeError();	// length about to overflow

			if (!bt.Get(b))
				return false;

			length = (length << 8) | b;
		}
	}
	return true;
}

/**
 * @brief Decodes a BER-encoded length from the input and stores it as a size_t.
 *
 * Reads a BER length field from the input transformation, converts it to a size_t, and indicates whether the length is definite.
 * Throws BERDecodeError on decode failure or if the length cannot be safely represented as a size_t.
 *
 * @param length Reference to store the decoded length.
 * @return true if the length is definite, false if indefinite.
 */
bool BERLengthDecode(BufferedTransformation &bt, size_t &length)
{
	lword lw = 0;
	bool definiteLength = false;
	if (!BERLengthDecode(bt, lw, definiteLength))
		BERDecodeError();
	if (!SafeConvert(lw, length))
		BERDecodeError();
	return definiteLength;
}

/**
 * @brief Encodes an ASN.1 NULL value in DER format.
 *
 * Writes the ASN.1 NULL tag and zero length to the output transformation.
 */
void DEREncodeNull(BufferedTransformation &out)
{
	out.Put(TAG_NULL);
	out.Put(0);
}

/**
 * @brief Decodes an ASN.1 NULL value from the input stream.
 *
 * Reads and verifies the ASN.1 NULL tag and ensures the length is zero. Throws an exception if the tag or length is invalid.
 */
void BERDecodeNull(BufferedTransformation &in)
{
	byte b;
	if (!in.Get(b) || b != TAG_NULL)
		BERDecodeError();
	size_t length;
	if (!BERLengthDecode(in, length) || length != 0)
		BERDecodeError();
}

/**
 * @brief Encodes an ASN.1 OCTET STRING in DER format.
 *
 * Writes the OCTET STRING tag, DER-encoded length, and the provided byte sequence to the output.
 *
 * @param str Pointer to the byte sequence to encode.
 * @param strLen Number of bytes to encode.
 * @return size_t Total number of bytes written to the output.
 */
size_t DEREncodeOctetString(BufferedTransformation &bt, const byte *str, size_t strLen)
{
	bt.Put(OCTET_STRING);
	size_t lengthBytes = DERLengthEncode(bt, strLen);
	bt.Put(str, strLen);
	return 1+lengthBytes+strLen;
}

/**
 * @brief Encodes a SecByteBlock as an ASN.1 DER OCTET STRING.
 *
 * Writes the OCTET STRING tag, length, and content to the output transformation.
 *
 * @param str The byte block to encode as an OCTET STRING.
 * @return Number of bytes written to the output.
 */
size_t DEREncodeOctetString(BufferedTransformation &bt, const SecByteBlock &str)
{
	return DEREncodeOctetString(bt, ConstBytePtr(str), BytePtrSize(str));
}

/**
 * @brief Decodes an ASN.1 OCTET STRING from a buffered input into a SecByteBlock.
 *
 * Reads and verifies the OCTET STRING tag, decodes its length, and extracts the byte content into the provided SecByteBlock. Throws on tag mismatch, length errors, or insufficient input data.
 *
 * @param str Receives the decoded octet string bytes.
 * @return size_t Number of bytes decoded into str.
 */
size_t BERDecodeOctetString(BufferedTransformation &bt, SecByteBlock &str)
{
	byte b;
	if (!bt.Get(b) || b != OCTET_STRING)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	str.New(bc);
	if (bc != bt.Get(BytePtr(str), bc))
		BERDecodeError();
	return bc;
}

/**
 * @brief Decodes an ASN.1 OCTET STRING from a source and transfers its contents to a destination.
 *
 * Reads an OCTET STRING from the input transformation, verifies its tag and length, and transfers the decoded bytes to the output transformation. Throws on tag mismatch, length errors, or insufficient data.
 *
 * @return size_t Number of bytes transferred.
 */
size_t BERDecodeOctetString(BufferedTransformation &bt, BufferedTransformation &str)
{
	byte b;
	if (!bt.Get(b) || b != OCTET_STRING)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	bt.TransferTo(str, bc);
	return bc;
}

/**
 * @brief Encodes a text string as an ASN.1 type with the specified tag in DER format.
 *
 * The function writes the ASN.1 tag, encodes the length in DER format, and appends the string bytes to the output.
 *
 * @param str Pointer to the string data to encode.
 * @param strLen Length of the string data in bytes.
 * @param asnTag ASN.1 tag to use for the encoded string type.
 * @return Number of bytes written to the output.
 */
size_t DEREncodeTextString(BufferedTransformation &bt, const byte* str, size_t strLen, byte asnTag)
{
	bt.Put(asnTag);
	size_t lengthBytes = DERLengthEncode(bt, strLen);
	bt.Put(str, strLen);
	return 1+lengthBytes+strLen;
}

/**
 * @brief Encodes a SecByteBlock as an ASN.1 text string with the specified tag in DER format.
 *
 * @param str The byte block containing the text string to encode.
 * @param asnTag The ASN.1 tag indicating the string type (e.g., UTF8String, IA5String).
 * @return size_t The number of bytes written to the output.
 */
size_t DEREncodeTextString(BufferedTransformation &bt, const SecByteBlock &str, byte asnTag)
{
	return DEREncodeTextString(bt, ConstBytePtr(str), BytePtrSize(str), asnTag);
}

/**
 * @brief Encodes a std::string as an ASN.1 text string with the specified tag in DER format.
 *
 * @param str The string to encode.
 * @param asnTag The ASN.1 tag indicating the string type (e.g., UTF8String, IA5String).
 * @return Number of bytes written to the output.
 */
size_t DEREncodeTextString(BufferedTransformation &bt, const std::string &str, byte asnTag)
{
	return DEREncodeTextString(bt, ConstBytePtr(str), BytePtrSize(str), asnTag);
}

/**
 * @brief Decodes an ASN.1 text string with the specified tag into a SecByteBlock.
 *
 * Reads and verifies the ASN.1 tag from the input, decodes the length, and extracts the string content into the provided SecByteBlock. Throws on tag mismatch, length errors, or insufficient data.
 *
 * @param str Output buffer for the decoded string content.
 * @param asnTag Expected ASN.1 tag for the text string.
 * @return size_t Number of bytes decoded into the output buffer.
 */
size_t BERDecodeTextString(BufferedTransformation &bt, SecByteBlock &str, byte asnTag)
{
	byte b;
	if (!bt.Get(b) || b != asnTag)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	str.resize(bc);
	if (bc != bt.Get(BytePtr(str), BytePtrSize(str)))
		BERDecodeError();

	return bc;
}

/**
 * @brief Decodes an ASN.1 text string with the specified tag into a std::string.
 *
 * Reads and verifies the ASN.1 tag from the input, decodes the length, and extracts the string content into the provided std::string. Throws on tag mismatch, length errors, or insufficient data.
 *
 * @param str Output string to receive the decoded text.
 * @param asnTag Expected ASN.1 tag for the text string.
 * @return size_t Number of bytes decoded into the string.
 */
size_t BERDecodeTextString(BufferedTransformation &bt, std::string &str, byte asnTag)
{
	byte b;
	if (!bt.Get(b) || b != asnTag)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	str.resize(bc);
	if (bc != bt.Get(BytePtr(str), BytePtrSize(str)))
		BERDecodeError();

	return bc;
}

/**
 * @brief Encodes a date string as an ASN.1 object with the specified tag in DER format.
 *
 * The function writes the ASN.1 tag, encodes the length, and appends the date string bytes to the output transformation.
 *
 * @param str The date string to encode.
 * @param asnTag The ASN.1 tag to use for the date type (e.g., UTCTime or GeneralizedTime).
 * @return size_t Total number of bytes written to the output.
 */
size_t DEREncodeDate(BufferedTransformation &bt, const SecByteBlock &str, byte asnTag)
{
	bt.Put(asnTag);
	size_t lengthBytes = DERLengthEncode(bt, str.size());
	bt.Put(ConstBytePtr(str), BytePtrSize(str));
	return 1+lengthBytes+str.size();
}

/**
 * @brief Decodes an ASN.1 date string with the specified tag from a buffered input.
 *
 * Reads and verifies the ASN.1 tag, decodes the length, and extracts the date string into the provided SecByteBlock.
 * Throws BERDecodeError on tag mismatch, length errors, or insufficient data.
 *
 * @param str Receives the decoded date string bytes.
 * @param asnTag Expected ASN.1 tag for the date type (e.g., UTCTime or GeneralizedTime).
 * @return size_t Number of bytes decoded into the date string.
 */
size_t BERDecodeDate(BufferedTransformation &bt, SecByteBlock &str, byte asnTag)
{
	byte b;
	if (!bt.Get(b) || b != asnTag)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	str.resize(bc);
	if (bc != bt.Get(BytePtr(str), BytePtrSize(str)))
		BERDecodeError();

	return bc;
}

/**
 * @brief Encodes a BIT STRING in DER format and writes it to the output.
 *
 * The function writes the ASN.1 BIT STRING tag, encodes the length, the number of unused bits in the last byte, and the bit string data itself.
 *
 * @param str Pointer to the bit string data.
 * @param strLen Length of the bit string data in bytes.
 * @param unusedBits Number of unused bits in the final byte (must be between 0 and 7).
 * @return size_t Total number of bytes written to the output.
 */
size_t DEREncodeBitString(BufferedTransformation &bt, const byte *str, size_t strLen, unsigned int unusedBits)
{
	bt.Put(BIT_STRING);
	size_t lengthBytes = DERLengthEncode(bt, strLen+1);
	bt.Put((byte)unusedBits);
	bt.Put(str, strLen);
	return 2+lengthBytes+strLen;
}

/**
 * @brief Decodes an ASN.1 BIT STRING from a BER-encoded stream.
 *
 * Extracts the BIT STRING value from the input, sets the number of unused bits in the last byte, and stores the bit string content in the provided buffer. Throws on tag mismatch, invalid length, or if the unused bits count is not in the range 0–7.
 *
 * @param str Buffer to receive the decoded bit string content.
 * @param unusedBits Set to the number of unused bits in the last byte.
 * @return Number of bytes written to the buffer (excluding the unused bits byte).
 */
size_t BERDecodeBitString(BufferedTransformation &bt, SecByteBlock &str, unsigned int &unusedBits)
{
	byte b;
	if (!bt.Get(b) || b != BIT_STRING)
		BERDecodeError();

	size_t bc;
	if (!BERLengthDecode(bt, bc))
		BERDecodeError();
	if (bc == 0)
		BERDecodeError();
	if (bc > bt.MaxRetrievable()) // Issue 346
		BERDecodeError();

	// X.690, 8.6.2.2: "The number [of unused bits] shall be in the range zero to seven"
	byte unused;
	if (!bt.Get(unused) || unused > 7)
		BERDecodeError();
	unusedBits = unused;
	str.resize(bc-1);
	if ((bc-1) != bt.Get(BytePtr(str), bc-1))
		BERDecodeError();
	return bc-1;
}

/**
 * @brief Reads an ASN.1 object from a BER-encoded source and re-encodes it in DER format to the destination.
 *
 * Recursively processes definite and indefinite length ASN.1 objects, ensuring the output is DER-compliant.
 */
void DERReencode(BufferedTransformation &source, BufferedTransformation &dest)
{
	byte tag;
	source.Peek(tag);
	BERGeneralDecoder decoder(source, tag);
	DERGeneralEncoder encoder(dest, tag);
	if (decoder.IsDefiniteLength())
		decoder.TransferTo(encoder, decoder.RemainingLength());
	else
	{
		while (!decoder.EndReached())
			DERReencode(decoder, encoder);
	}
	decoder.MessageEnd();
	encoder.MessageEnd();
}

/**
 * @brief Peeks the length of the next ASN.1 object in a buffer without consuming input.
 *
 * Attempts to decode the length field of the next ASN.1 object in the provided buffer. Returns the decoded length, or 0 if the length cannot be determined (e.g., on failure or indefinite length).
 *
 * @param bt The input buffer to peek into.
 * @return size_t The length of the next ASN.1 object, or 0 if decoding fails or the length is indefinite.
 */
size_t BERDecodePeekLength(const BufferedTransformation &bt)
{
	lword count = (std::min)(bt.MaxRetrievable(), static_cast<lword>(16));
	if (count == 0) return 0;

	ByteQueue tagAndLength;
	bt.CopyTo(tagAndLength, count);

	// Skip tag
	tagAndLength.Skip(1);

	// BERLengthDecode fails for indefinite length.
	size_t length;
	if (!BERLengthDecode(tagAndLength, length))
		return 0;

	return length;
}

/**
 * @brief Encodes a single OID subidentifier using ASN.1 base-128 encoding.
 *
 * Encodes the given value as a sequence of bytes with continuation bits, as required for ASN.1 OBJECT IDENTIFIER subidentifiers.
 *
 * @param v The subidentifier value to encode.
 */
void OID::EncodeValue(BufferedTransformation &bt, word32 v)
{
	for (unsigned int i=RoundUpToMultipleOf(STDMAX(7U,BitPrecision(v)), 7U)-7; i != 0; i-=7)
		bt.Put((byte)(0x80 | ((v >> i) & 0x7f)));
	bt.Put((byte)(v & 0x7f));
}

/**
 * @brief Decodes a base-128 encoded OID subidentifier from the input stream.
 *
 * Reads bytes from the input, reconstructing a single OBJECT IDENTIFIER subidentifier using base-128 encoding with continuation bits. Throws on input failure or integer overflow.
 *
 * @param v Reference to store the decoded subidentifier value.
 * @return size_t Number of bytes consumed from the input.
 */
size_t OID::DecodeValue(BufferedTransformation &bt, word32 &v)
{
	byte b;
	size_t i=0;
	v = 0;
	while (true)
	{
		if (!bt.Get(b))
			BERDecodeError();
		i++;
		if (v >> (8*sizeof(v)-7))	// v about to overflow
			BERDecodeError();
		v <<= 7;
		v += b & 0x7f;
		if (!(b & 0x80))
			return i;
	}
}

/**
 * @brief Encodes the OID as an ASN.1 OBJECT IDENTIFIER in DER format.
 *
 * The first two OID values are combined as specified by ASN.1 rules, and subsequent values are encoded using base-128 encoding. The result is written to the provided output transformation.
 */
void OID::DEREncode(BufferedTransformation &bt) const
{
	CRYPTOPP_ASSERT(m_values.size() >= 2);
	ByteQueue temp;
	temp.Put(byte(m_values[0] * 40 + m_values[1]));
	for (size_t i=2; i<m_values.size(); i++)
		EncodeValue(temp, m_values[i]);
	bt.Put(OBJECT_IDENTIFIER);
	DERLengthEncode(bt, temp.CurrentSize());
	temp.TransferTo(bt);
}

/**
 * @brief Decodes an ASN.1 OBJECT IDENTIFIER from a BER-encoded stream.
 *
 * Reads and parses an OBJECT IDENTIFIER from the input, extracting its subidentifiers and storing them in the OID object. Throws an exception on tag mismatch, invalid length, or decoding errors.
 */
void OID::BERDecode(BufferedTransformation &bt)
{
	byte b;
	if (!bt.Get(b) || b != OBJECT_IDENTIFIER)
		BERDecodeError();

	size_t length;
	if (!BERLengthDecode(bt, length) || length < 1)
		BERDecodeError();

	if (!bt.Get(b))
		BERDecodeError();

	length--;
	m_values.resize(2);
	m_values[0] = b / 40;
	m_values[1] = b % 40;

	while (length > 0)
	{
		word32 v;
		size_t valueLen = DecodeValue(bt, v);
		if (valueLen > length)
			BERDecodeError();
		m_values.push_back(v);
		length -= valueLen;
	}
}

/**
 * @brief Decodes an OBJECT IDENTIFIER from the input and verifies it matches this OID.
 *
 * Throws a BERDecodeError if the decoded OID does not equal the current OID.
 */
void OID::BERDecodeAndCheck(BufferedTransformation &bt) const
{
	OID oid(bt);
	if (*this != oid)
		BERDecodeError();
}

/**
 * @brief Outputs the OID as a dot-separated decimal string to the given stream.
 *
 * @param out Output stream to write the OID representation.
 * @return Reference to the output stream.
 */
std::ostream& OID::Print(std::ostream& out) const
{
	std::ostringstream oss;
	for (size_t i = 0; i < m_values.size(); ++i)
	{
		oss << m_values[i];
		if (i+1 < m_values.size())
			oss << ".";
	}
	return out << oss.str();
}

/**
 * @brief Returns the current output target for processed ASN.1 objects.
 *
 * Selects the attached transformation if object output is enabled; otherwise, returns a discard sink.
 *
 * @return Reference to the current output BufferedTransformation.
 */
inline BufferedTransformation & EncodedObjectFilter::CurrentTarget()
{
	if (m_flags & PUT_OBJECTS)
		return *AttachedTransformation();
	else
		return TheBitBucket();
}

/**
 * @brief Processes and parses ASN.1 encoded objects from input bytes, forwarding decoded objects to the attached transformation.
 *
 * Accepts a stream of bytes containing one or more ASN.1 objects, parses each object by reading its identifier, length, and body, and transfers the decoded content to the attached transformation. Handles definite and indefinite lengths, nested constructed types, and manages message or series end signaling based on configured flags. Throws on decoding errors such as invalid tags or lengths.
 *
 * @param inString Pointer to the input byte array containing ASN.1 encoded data.
 * @param length Number of bytes in the input array to process.
 */
void EncodedObjectFilter::Put(const byte *inString, size_t length)
{
	if (m_nCurrentObject == m_nObjects)
	{
		AttachedTransformation()->Put(inString, length);
		return;
	}

	LazyPutter lazyPutter(m_queue, inString, length);

	while (m_queue.AnyRetrievable())
	{
		switch (m_state)
		{
		case IDENTIFIER:
			if (!m_queue.Get(m_id))
				return;
			m_queue.TransferTo(CurrentTarget(), 1);
			m_state = LENGTH;
		// fall through
		case LENGTH:
		{
			byte b;
			if (m_level > 0 && m_id == 0 && m_queue.Peek(b) && b == 0)
			{
				m_queue.TransferTo(CurrentTarget(), 1);
				m_level--;
				m_state = IDENTIFIER;
				break;
			}
			ByteQueue::Walker walker(m_queue);
			bool definiteLength = false;
			if (!BERLengthDecode(walker, m_lengthRemaining, definiteLength))
				return;
			m_queue.TransferTo(CurrentTarget(), walker.GetCurrentPosition());
			if (!((m_id & CONSTRUCTED) || definiteLength))
				BERDecodeError();
			if (!definiteLength)
			{
				if (!(m_id & CONSTRUCTED))
					BERDecodeError();
				m_level++;
				m_state = IDENTIFIER;
				break;
			}
			m_state = BODY;
		}
		// fall through
		case BODY:
			m_lengthRemaining -= m_queue.TransferTo(CurrentTarget(), m_lengthRemaining);

			if (m_lengthRemaining == 0)
				m_state = IDENTIFIER;
		// fall through
		case TAIL:
		case ALL_DONE:
		default: ;
		}

		if (m_state == IDENTIFIER && m_level == 0)
		{
			// just finished processing a level 0 object
			++m_nCurrentObject;

			if (m_flags & PUT_MESSANGE_END_AFTER_EACH_OBJECT)
				AttachedTransformation()->MessageEnd();

			if (m_nCurrentObject == m_nObjects)
			{
				if (m_flags & PUT_MESSANGE_END_AFTER_ALL_OBJECTS)
					AttachedTransformation()->MessageEnd();

				if (m_flags & PUT_MESSANGE_SERIES_END_AFTER_ALL_OBJECTS)
					AttachedTransformation()->MessageSeriesEnd();

				m_queue.TransferAllTo(*AttachedTransformation());
				return;
			}
		}
	}
}

/**
 * @brief Initializes a BERGeneralDecoder for decoding an ASN.1 object from the input queue using the default tag.
 *
 * Begins decoding by reading the ASN.1 tag and length from the provided input queue. Throws on tag or length errors.
 */
BERGeneralDecoder::BERGeneralDecoder(BufferedTransformation &inQueue)
	: m_inQueue(inQueue), m_length(0), m_finished(false)
{
	Init(DefaultTag);
}

/**
 * @brief Constructs a BERGeneralDecoder for an ASN.1 object with a specific tag.
 *
 * Initializes decoding from the provided input queue, reading and verifying the ASN.1 tag and decoding the object's length. Throws BERDecodeError on tag or length errors.
 */
BERGeneralDecoder::BERGeneralDecoder(BufferedTransformation &inQueue, byte asnTag)
	: m_inQueue(inQueue), m_length(0), m_finished(false)
{
	Init(asnTag);
}

/**
 * @brief Initializes a BERGeneralDecoder for a nested ASN.1 object with a specific tag.
 *
 * Constructs a decoder that reads from an existing BERGeneralDecoder, starting at the specified ASN.1 tag. The decoder parses the tag and determines the length of the nested object.
 *
 * @param inQueue The parent BERGeneralDecoder to read from.
 * @param asnTag The expected ASN.1 tag for the nested object.
 */
BERGeneralDecoder::BERGeneralDecoder(BERGeneralDecoder &inQueue, byte asnTag)
	: m_inQueue(inQueue), m_length(0), m_finished(false)
{
	Init(asnTag);
}

/**
 * @brief Initializes decoding of an ASN.1 object with the specified tag.
 *
 * Reads and verifies the ASN.1 tag from the input queue, decodes the length, and checks for valid definite or indefinite length encoding. Throws a BERDecodeError on tag mismatch, length decode failure, or if a primitive type uses indefinite length.
 *
 * @param asnTag The expected ASN.1 tag to verify.
 */
void BERGeneralDecoder::Init(byte asnTag)
{
	byte b;
	if (!m_inQueue.Get(b) || b != asnTag)
		BERDecodeError();

	if (!BERLengthDecode(m_inQueue, m_length, m_definiteLength))
		BERDecodeError();

	if (!m_definiteLength && !(asnTag & CONSTRUCTED))
		BERDecodeError();	// cannot be primitive and have indefinite length
}

/**
 * @brief Destructor for BERGeneralDecoder that ensures decoding is properly finalized.
 *
 * Calls MessageEnd() if decoding was not finished, suppressing any exceptions to prevent them from propagating out of the destructor.
 */
BERGeneralDecoder::~BERGeneralDecoder()
{
	try	// avoid throwing in destructor
	{
		if (!m_finished)
			MessageEnd();
	}
	catch (const Exception&)
	{
		// CRYPTOPP_ASSERT(0);
	}
}

/**
 * @brief Checks if the end of the ASN.1 object has been reached during BER decoding.
 *
 * For definite-length objects, returns true if all bytes have been consumed. For indefinite-length objects, returns true if the next two bytes are end-of-content octets (0x00 0x00).
 *
 * @return true if the end of the ASN.1 object is reached; false otherwise.
 */
bool BERGeneralDecoder::EndReached() const
{
	if (m_definiteLength)
		return m_length == 0;
	else
	{	// check end-of-content octets
		word16 i;
		return (m_inQueue.PeekWord16(i)==2 && i==0);
	}
}

/**
 * @brief Returns the next byte in the input without consuming it.
 *
 * @return The next byte available for decoding.
 * @throws BERDecodeError if no byte is available to peek.
 */
byte BERGeneralDecoder::PeekByte() const
{
	byte b;
	if (!Peek(b))
		BERDecodeError();
	return b;
}

/**
 * @brief Reads and verifies that the next byte matches the expected value.
 *
 * Throws a BERDecodeError if the next byte cannot be read or does not equal the specified value.
 *
 * @param check The expected byte value.
 */
void BERGeneralDecoder::CheckByte(byte check)
{
	byte b;
	if (!Get(b) || b != check)
		BERDecodeError();
}

/**
 * @brief Marks the end of ASN.1 BER decoding and verifies proper termination.
 *
 * For definite-length encodings, ensures all expected bytes have been consumed. For indefinite-length encodings, checks for the presence of end-of-content octets. Throws a BERDecodeError on length mismatch or missing end-of-content markers.
 */
void BERGeneralDecoder::MessageEnd()
{
	m_finished = true;
	if (m_definiteLength)
	{
		if (m_length != 0)
			BERDecodeError();
	}
	else
	{	// remove end-of-content octets
		word16 i;
		if (m_inQueue.GetWord16(i) != 2 || i != 0)
			BERDecodeError();
	}
}

/**
 * @brief Transfers bytes from the decoder to a target transformation, respecting ASN.1 definite length constraints.
 *
 * Transfers up to `transferBytes` from the internal input queue to the specified target. If the ASN.1 object has a definite length, the transfer is limited to the remaining length. The actual number of bytes transferred is subtracted from the decoder's remaining length.
 *
 * @param transferBytes On input, the requested number of bytes to transfer; on output, the actual number transferred.
 * @param channel The channel identifier for the transfer.
 * @param blocking Indicates whether the operation should block until completion.
 * @return The number of bytes that could not be transferred due to blocking.
 */
size_t BERGeneralDecoder::TransferTo2(BufferedTransformation &target, lword &transferBytes, const std::string &channel, bool blocking)
{
	if (m_definiteLength && transferBytes > m_length)
		transferBytes = m_length;
	size_t blockedBytes = m_inQueue.TransferTo2(target, transferBytes, channel, blocking);
	ReduceLength(transferBytes);
	return blockedBytes;
}

/**
 * @brief Copies a range of bytes from the decoder to the target transformation.
 *
 * Copies bytes from the current position up to the specified end position, limited by the remaining definite length if applicable. The data is written to the target transformation on the given channel.
 *
 * @param begin Reference to the starting offset; updated to reflect the new position after copying.
 * @param end The end offset (exclusive) for the copy operation.
 * @param channel The output channel name.
 * @param blocking Indicates whether the operation should block until completion.
 * @return size_t The number of bytes actually copied.
 */
size_t BERGeneralDecoder::CopyRangeTo2(BufferedTransformation &target, lword &begin, lword end, const std::string &channel, bool blocking) const
{
	if (m_definiteLength)
		end = STDMIN(m_length, end);
	return m_inQueue.CopyRangeTo2(target, begin, end, channel, blocking);
}

/**
 * @brief Decreases the remaining definite length by a specified amount.
 *
 * If the decoder is operating with a definite length, subtracts `delta` from the remaining length. Throws a BERDecodeError if the reduction would underflow.
 *
 * @param delta The number of bytes to subtract from the remaining length.
 * @return The value of `delta`.
 */
lword BERGeneralDecoder::ReduceLength(lword delta)
{
	if (m_definiteLength)
	{
		if (m_length < delta)
			BERDecodeError();
		m_length -= delta;
	}
	return delta;
}

/**
 * @brief Initializes a DERGeneralEncoder for ASN.1 encoding with the default tag.
 *
 * Sets up the encoder to write encoded ASN.1 data to the specified output queue using the default ASN.1 tag.
 */
DERGeneralEncoder::DERGeneralEncoder(BufferedTransformation &outQueue)
	: m_outQueue(outQueue), m_asnTag(DefaultTag), m_finished(false)
{
}

/**
 * @brief Initializes a DER encoder for an ASN.1 object with a specified tag.
 *
 * Prepares the encoder to write an ASN.1 object with the given tag to the provided output queue.
 *
 * @param outQueue Output destination for encoded data.
 * @param asnTag ASN.1 tag to use for the encoded object.
 */
DERGeneralEncoder::DERGeneralEncoder(BufferedTransformation &outQueue, byte asnTag)
	: m_outQueue(outQueue), m_asnTag(asnTag), m_finished(false)
{
}

/**
 * @brief Initializes a DERGeneralEncoder as a nested encoder with a specified ASN.1 tag.
 *
 * Constructs a DERGeneralEncoder that encodes ASN.1 data with the given tag, writing the encoded output to the provided parent encoder.
 *
 * @param outQueue Parent DERGeneralEncoder to which the encoded data will be written.
 * @param asnTag ASN.1 tag for the constructed object.
 */
DERGeneralEncoder::DERGeneralEncoder(DERGeneralEncoder &outQueue, byte asnTag)
	: m_outQueue(outQueue), m_asnTag(asnTag), m_finished(false)
{
}

/**
 * @brief Finalizes DER encoding if not already finished.
 *
 * Ensures that the encoded ASN.1 object is properly terminated by calling MessageEnd() if necessary. Catches and suppresses exceptions to prevent them from propagating during object destruction.
 */
DERGeneralEncoder::~DERGeneralEncoder()
{
	try	// avoid throwing in constructor
	{
		if (!m_finished)
			MessageEnd();
	}
	catch (const Exception&)
	{
		CRYPTOPP_ASSERT(0);
	}
}

/**
 * @brief Finalizes ASN.1 DER encoding by writing the tag, length, and encoded content to the output queue.
 *
 * Marks the encoding as finished, writes the ASN.1 tag and DER-encoded length, then transfers the encoded content to the output queue.
 */
void DERGeneralEncoder::MessageEnd()
{
	m_finished = true;
	lword length = CurrentSize();
	m_outQueue.Put(m_asnTag);
	DERLengthEncode(m_outQueue, length);
	TransferTo(m_outQueue);
}

/**
 * @brief Decodes an X.509 SubjectPublicKeyInfo structure from BER format.
 *
 * Parses the ASN.1 SEQUENCE containing the algorithm identifier and BIT STRING public key, verifies the algorithm OID, decodes algorithm parameters if present, and extracts the public key data. Throws on tag, length, or format errors.
 */

void X509PublicKey::BERDecode(BufferedTransformation &bt)
{
	BERSequenceDecoder subjectPublicKeyInfo(bt);
		BERSequenceDecoder algorithm(subjectPublicKeyInfo);
			GetAlgorithmID().BERDecodeAndCheck(algorithm);
			bool parametersPresent = algorithm.EndReached() ? false : BERDecodeAlgorithmParameters(algorithm);
		algorithm.MessageEnd();

		BERGeneralDecoder subjectPublicKey(subjectPublicKeyInfo, BIT_STRING);
			subjectPublicKey.CheckByte(0);	// unused bits
			BERDecodePublicKey(subjectPublicKey, parametersPresent, (size_t)subjectPublicKey.RemainingLength());
		subjectPublicKey.MessageEnd();
	subjectPublicKeyInfo.MessageEnd();
}

/**
 * @brief Encodes the X.509 SubjectPublicKeyInfo structure in DER format.
 *
 * Encodes the public key as a DER SEQUENCE containing the algorithm identifier and the public key as a BIT STRING, following the X.509 SubjectPublicKeyInfo specification.
 */
void X509PublicKey::DEREncode(BufferedTransformation &bt) const
{
	DERSequenceEncoder subjectPublicKeyInfo(bt);

		DERSequenceEncoder algorithm(subjectPublicKeyInfo);
			GetAlgorithmID().DEREncode(algorithm);
			DEREncodeAlgorithmParameters(algorithm);
		algorithm.MessageEnd();

		DERGeneralEncoder subjectPublicKey(subjectPublicKeyInfo, BIT_STRING);
			subjectPublicKey.Put(0);	// unused bits
			DEREncodePublicKey(subjectPublicKey);
		subjectPublicKey.MessageEnd();

	subjectPublicKeyInfo.MessageEnd();
}

/**
 * @brief Decodes a PKCS#8 PrivateKeyInfo structure from BER format.
 *
 * Parses the ASN.1 sequence containing the version, algorithm identifier (with optional parameters), private key OCTET STRING, and any optional attributes. Throws on tag, version, or format errors.
 */
void PKCS8PrivateKey::BERDecode(BufferedTransformation &bt)
{
	BERSequenceDecoder privateKeyInfo(bt);
		word32 version;
		BERDecodeUnsigned<word32>(privateKeyInfo, version, INTEGER, 0, 0);	// check version

		BERSequenceDecoder algorithm(privateKeyInfo);
			GetAlgorithmID().BERDecodeAndCheck(algorithm);
			bool parametersPresent = algorithm.EndReached() ? false : BERDecodeAlgorithmParameters(algorithm);
		algorithm.MessageEnd();

		BERGeneralDecoder octetString(privateKeyInfo, OCTET_STRING);
			BERDecodePrivateKey(octetString, parametersPresent, (size_t)privateKeyInfo.RemainingLength());
		octetString.MessageEnd();

		if (!privateKeyInfo.EndReached())
			BERDecodeOptionalAttributes(privateKeyInfo);
	privateKeyInfo.MessageEnd();
}

/**
 * @brief Encodes the PKCS#8 PrivateKeyInfo structure in DER format.
 *
 * Produces a DER-encoded ASN.1 sequence containing the version, algorithm identifier (with parameters), private key as an OCTET STRING, and any optional attributes.
 */
void PKCS8PrivateKey::DEREncode(BufferedTransformation &bt) const
{
	DERSequenceEncoder privateKeyInfo(bt);
		DEREncodeUnsigned<word32>(privateKeyInfo, 0);	// version

		DERSequenceEncoder algorithm(privateKeyInfo);
			GetAlgorithmID().DEREncode(algorithm);
			DEREncodeAlgorithmParameters(algorithm);
		algorithm.MessageEnd();

		DERGeneralEncoder octetString(privateKeyInfo, OCTET_STRING);
			DEREncodePrivateKey(octetString);
		octetString.MessageEnd();

		DEREncodeOptionalAttributes(privateKeyInfo);
	privateKeyInfo.MessageEnd();
}

/**
 * @brief Decodes optional PKCS#8 attributes from BER format and stores them internally.
 *
 * Reads optional attributes from the input and re-encodes them for internal storage.
 */
void PKCS8PrivateKey::BERDecodeOptionalAttributes(BufferedTransformation &bt)
{
	DERReencode(bt, m_optionalAttributes);
}

/**
 * @brief Writes the optional PKCS#8 attributes to the output stream.
 *
 * Copies the internally stored optional attributes to the provided output transformation in DER format.
 */
void PKCS8PrivateKey::DEREncodeOptionalAttributes(BufferedTransformation &bt) const
{
	m_optionalAttributes.CopyTo(bt);
}

NAMESPACE_END

#endif
