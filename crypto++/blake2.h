// blake2.h - written and placed in the public domain by Jeffrey Walton
//            and Zooko Wilcox-O'Hearn. Based on Aumasson, Neves,
//            Wilcox-O'Hearn and Winnerlein's reference BLAKE2
//            implementation at http://github.com/BLAKE2/BLAKE2.

/// \file blake2.h
/// \brief Classes for BLAKE2b and BLAKE2s message digests and keyed message digests
/// \details This implementation follows Aumasson, Neves, Wilcox-O'Hearn and Winnerlein's
///   <A HREF="http://blake2.net/blake2.pdf">BLAKE2: simpler, smaller, fast as MD5</A> (2013.01.29).
///   Static algorithm name return either "BLAKE2b" or "BLAKE2s". An object algorithm name follows
///   the naming described in <A HREF="http://tools.ietf.org/html/rfc7693#section-4">RFC 7693, The
///   BLAKE2 Cryptographic Hash and Message Authentication Code (MAC)</A>.
/// \since C++ since Crypto++ 5.6.4, SSE since Crypto++ 5.6.4, NEON since Crypto++ 6.0,
///   Power8 since Crypto++ 8.0

#ifndef CRYPTOPP_BLAKE2_H
#define CRYPTOPP_BLAKE2_H

#include "cryptlib.h"
#include "secblock.h"
#include "seckey.h"

NAMESPACE_BEGIN(CryptoPP)

/// \brief BLAKE2s hash information
/// \since Crypto++ 5.6.4
struct BLAKE2s_Info : public VariableKeyLength<32,0,32,1,SimpleKeyingInterface::NOT_RESYNCHRONIZABLE>
{
    typedef VariableKeyLength<32,0,32,1,SimpleKeyingInterface::NOT_RESYNCHRONIZABLE> KeyBase;
    CRYPTOPP_CONSTANT(MIN_KEYLENGTH = KeyBase::MIN_KEYLENGTH);
    CRYPTOPP_CONSTANT(MAX_KEYLENGTH = KeyBase::MAX_KEYLENGTH);
    CRYPTOPP_CONSTANT(DEFAULT_KEYLENGTH = KeyBase::DEFAULT_KEYLENGTH);

    CRYPTOPP_CONSTANT(BLOCKSIZE = 64);
    CRYPTOPP_CONSTANT(DIGESTSIZE = 32);
    CRYPTOPP_CONSTANT(SALTSIZE = 8);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = 8);

    /**
 * @brief Returns the static algorithm name for BLAKE2s.
 *
 * @return The string "BLAKE2s".
 */
CRYPTOPP_STATIC_CONSTEXPR const char* StaticAlgorithmName() {return "BLAKE2s";}
};

/// \brief BLAKE2b hash information
/// \since Crypto++ 5.6.4
struct BLAKE2b_Info : public VariableKeyLength<64,0,64,1,SimpleKeyingInterface::NOT_RESYNCHRONIZABLE>
{
    typedef VariableKeyLength<64,0,64,1,SimpleKeyingInterface::NOT_RESYNCHRONIZABLE> KeyBase;
    CRYPTOPP_CONSTANT(MIN_KEYLENGTH = KeyBase::MIN_KEYLENGTH);
    CRYPTOPP_CONSTANT(MAX_KEYLENGTH = KeyBase::MAX_KEYLENGTH);
    CRYPTOPP_CONSTANT(DEFAULT_KEYLENGTH = KeyBase::DEFAULT_KEYLENGTH);

    CRYPTOPP_CONSTANT(BLOCKSIZE = 128);
    CRYPTOPP_CONSTANT(DIGESTSIZE = 64);
    CRYPTOPP_CONSTANT(SALTSIZE = 16);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = 16);

    /**
 * @brief Returns the static algorithm name for BLAKE2b.
 *
 * @return The string "BLAKE2b".
 */
CRYPTOPP_STATIC_CONSTEXPR const char* StaticAlgorithmName() {return "BLAKE2b";}
};

/**
     * @brief Represents the parameter block for BLAKE2s configuration.
     *
     * Encapsulates digest size, salt, and personalization parameters for BLAKE2s hashing, providing initialization and reset functionality.
     *
     * @param digestSize Optional digest size to initialize the parameter block with a specific output length.
     */
struct CRYPTOPP_NO_VTABLE BLAKE2s_ParameterBlock
{
    CRYPTOPP_CONSTANT(SALTSIZE = BLAKE2s_Info::SALTSIZE);
    CRYPTOPP_CONSTANT(DIGESTSIZE = BLAKE2s_Info::DIGESTSIZE);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = BLAKE2s_Info::PERSONALIZATIONSIZE);

    BLAKE2s_ParameterBlock()
    {
        Reset();
    }

    BLAKE2s_ParameterBlock(size_t digestSize)
    {
        Reset(digestSize);
    }

    BLAKE2s_ParameterBlock(size_t digestSize, size_t keyLength, const byte* salt, size_t saltLength,
        const byte* personalization, size_t personalizationLength);

    void Reset(size_t digestLength=DIGESTSIZE, size_t keyLength=0);

    /**
     * @brief Returns a pointer to the underlying data buffer.
     *
     * @return Pointer to the internal byte array.
     */
    byte* data() {
        return m_data.data();
    }

    /**
     * @brief Returns a pointer to the underlying parameter block data.
     *
     * @return Pointer to the parameter block's byte array.
     */
    const byte* data() const {
        return m_data.data();
    }

    /**
     * @brief Returns the number of bytes in the parameter block.
     *
     * @return size_t The size of the underlying data buffer in bytes.
     */
    size_t size() const {
        return m_data.size();
    }

    /**
     * @brief Returns a pointer to the salt field within the parameter block.
     *
     * @return byte* Pointer to the start of the salt data.
     */
    byte* salt() {
        return m_data + SaltOff;
    }

    /**
     * @brief Returns a pointer to the personalization field within the parameter block.
     *
     * @return Pointer to the personalization bytes.
     */
    byte* personalization() {
        return m_data + PersonalizationOff;
    }

    // Offsets into the byte array
    enum {
        DigestOff = 0, KeyOff = 1, FanoutOff = 2, DepthOff = 3, LeafOff = 4, NodeOff = 8,
        NodeDepthOff = 14, InnerOff = 15, SaltOff = 16, PersonalizationOff = 24
    };

    FixedSizeAlignedSecBlock<byte, 32, true> m_data;
};

/**
     * @brief Represents the parameter block for BLAKE2b hash configuration.
     *
     * Encapsulates configuration parameters for BLAKE2b, including digest size, key length, salt, and personalization, as specified in RFC 7693. Used to initialize or reset the hash function's parameters.
     *
     * @param digestSize Optional digest size in bytes to initialize the parameter block.
     */
struct CRYPTOPP_NO_VTABLE BLAKE2b_ParameterBlock
{
    CRYPTOPP_CONSTANT(SALTSIZE = BLAKE2b_Info::SALTSIZE);
    CRYPTOPP_CONSTANT(DIGESTSIZE = BLAKE2b_Info::DIGESTSIZE);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = BLAKE2b_Info::PERSONALIZATIONSIZE);

    BLAKE2b_ParameterBlock()
    {
        Reset();
    }

    BLAKE2b_ParameterBlock(size_t digestSize)
    {
        Reset(digestSize);
    }

    BLAKE2b_ParameterBlock(size_t digestSize, size_t keyLength, const byte* salt, size_t saltLength,
        const byte* personalization, size_t personalizationLength);

    void Reset(size_t digestLength=DIGESTSIZE, size_t keyLength=0);

    /**
     * @brief Returns a pointer to the underlying data buffer.
     *
     * @return Pointer to the internal byte array.
     */
    byte* data() {
        return m_data.data();
    }

    /**
     * @brief Returns a pointer to the underlying parameter block data.
     *
     * @return Pointer to the parameter block's byte array.
     */
    const byte* data() const {
        return m_data.data();
    }

    /**
     * @brief Returns the number of bytes in the parameter block.
     *
     * @return size_t The size of the underlying data buffer in bytes.
     */
    size_t size() const {
        return m_data.size();
    }

    /**
     * @brief Returns a pointer to the salt field within the parameter block.
     *
     * @return byte* Pointer to the start of the salt data.
     */
    byte* salt() {
        return m_data + SaltOff;
    }

    /**
     * @brief Returns a pointer to the personalization field within the parameter block.
     *
     * @return Pointer to the personalization bytes.
     */
    byte* personalization() {
        return m_data + PersonalizationOff;
    }

    // Offsets into the byte array
    enum {
        DigestOff = 0, KeyOff = 1, FanoutOff = 2, DepthOff = 3, LeafOff = 4, NodeOff = 8,
        NodeDepthOff = 16, InnerOff = 17, RfuOff = 18, SaltOff = 32, PersonalizationOff = 48
    };

    FixedSizeAlignedSecBlock<byte, 64, true> m_data;
};

/// \brief BLAKE2s state information
/**
 * @brief Maintains the internal state for a BLAKE2s hash computation.
 *
 * Holds the chaining values, counters, finalization flags, input buffer, and buffer length required for BLAKE2s hashing. Provides methods to reset the state and access internal arrays for hash state, counters, flags, and data buffer.
 */
struct CRYPTOPP_NO_VTABLE BLAKE2s_State
{
    BLAKE2s_State() {
        Reset();
    }

    void Reset();

    /**
     * @brief Returns a pointer to the internal hash state array.
     *
     * @return word32* Pointer to the beginning of the hash state data.
     */
    inline word32* h() {
        return m_hft.data();
    }

    /**
     * @brief Returns a pointer to the counter array within the internal state.
     *
     * @return word32* Pointer to the first element of the counter array.
     */
    inline word32* t() {
        return m_hft.data() + 8;
    }

    /**
     * @brief Returns a pointer to the finalization flag field in the internal state array.
     *
     * @return word32* Pointer to the finalization flag within the state data.
     */
    inline word32* f() {
        return m_hft.data() + 10;
    }

    /**
     * @brief Returns a pointer to the underlying data buffer.
     *
     * @return byte* Pointer to the start of the internal buffer.
     */
    inline byte* data() {
        return m_buf.data();
    }

    // SSE4, Power7 and NEON depend upon t[] and f[] being side-by-side
    CRYPTOPP_CONSTANT(BLOCKSIZE = BLAKE2s_Info::BLOCKSIZE);
    FixedSizeAlignedSecBlock<word32, 8+2+2, true> m_hft;
    FixedSizeAlignedSecBlock<byte, BLOCKSIZE, true> m_buf;
    size_t m_len;
};

/// \brief BLAKE2b state information
/**
 * @brief Maintains the internal state for BLAKE2b hash computations.
 *
 * Holds the chaining values, counters, finalization flags, input buffer, and buffer length for BLAKE2b. Provides accessors for the internal state arrays and buffer, and a method to reset the state to its initial values.
 */
struct CRYPTOPP_NO_VTABLE BLAKE2b_State
{
    BLAKE2b_State() {
        Reset();
    }

    void Reset();

    /**
     * @brief Returns a pointer to the internal hash state array.
     *
     * @return word64* Pointer to the beginning of the hash state, counter, and flag array.
     */
    inline word64* h() {
        return m_hft.data();
    }

    /**
     * @brief Returns a pointer to the counter array within the internal state.
     *
     * @return word64* Pointer to the start of the 2-element counter array.
     */
    inline word64* t() {
        return m_hft.data() + 8;
    }

    /**
     * @brief Returns a pointer to the finalization flag array within the internal state.
     *
     * @return word64* Pointer to the finalization flag field.
     */
    inline word64* f() {
        return m_hft.data() + 10;
    }

    /**
     * @brief Returns a pointer to the underlying data buffer.
     *
     * @return byte* Pointer to the start of the internal buffer.
     */
    inline byte* data() {
        return m_buf.data();
    }

    // SSE4, Power8 and NEON depend upon t[] and f[] being side-by-side
    CRYPTOPP_CONSTANT(BLOCKSIZE = BLAKE2b_Info::BLOCKSIZE);
    FixedSizeAlignedSecBlock<word64, 8+2+2, true> m_hft;
    FixedSizeAlignedSecBlock<byte, BLOCKSIZE, true> m_buf;
    size_t m_len;
};

/// \brief The BLAKE2s cryptographic hash function
/// \details BLAKE2s can function as both a hash and keyed hash. If you want only the hash,
///   then use the BLAKE2s constructor that accepts no parameters or digest size. If you
///   want a keyed hash, then use the constructor that accpts the key as a parameter.
///   Once a key and digest size are selected, its effectively immutable. The Restart()
///   method that accepts a ParameterBlock does not allow you to change it.
/// \sa Aumasson, Neves, Wilcox-O'Hearn and Winnerlein's
///   <A HREF="http://blake2.net/blake2.pdf">BLAKE2: simpler, smaller, fast as MD5</A> (2013.01.29).
/// \since C++ since Crypto++ 5.6.4, SSE since Crypto++ 5.6.4, NEON since Crypto++ 6.0,
///   Power8 since Crypto++ 8.0
class BLAKE2s : public SimpleKeyingInterfaceImpl<MessageAuthenticationCode, BLAKE2s_Info>
{
public:
    CRYPTOPP_CONSTANT(DEFAULT_KEYLENGTH = BLAKE2s_Info::DEFAULT_KEYLENGTH);
    CRYPTOPP_CONSTANT(MIN_KEYLENGTH = BLAKE2s_Info::MIN_KEYLENGTH);
    CRYPTOPP_CONSTANT(MAX_KEYLENGTH = BLAKE2s_Info::MAX_KEYLENGTH);

    CRYPTOPP_CONSTANT(DIGESTSIZE = BLAKE2s_Info::DIGESTSIZE);
    CRYPTOPP_CONSTANT(BLOCKSIZE = BLAKE2s_Info::BLOCKSIZE);
    CRYPTOPP_CONSTANT(SALTSIZE = BLAKE2s_Info::SALTSIZE);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = BLAKE2s_Info::PERSONALIZATIONSIZE);

    typedef BLAKE2s_State State;
    typedef BLAKE2s_ParameterBlock ParameterBlock;

    /**
 * @brief Returns the static algorithm name for BLAKE2s.
 *
 * @return The string "BLAKE2s".
 */
CRYPTOPP_STATIC_CONSTEXPR const char* StaticAlgorithmName() {return "BLAKE2s";}

    /**
 * @brief Destroys the BLAKE2s object and securely clears sensitive data.
 */
virtual ~BLAKE2s() {}

    /// \brief Construct a BLAKE2s hash
    /// \param digestSize the digest size, in bytes
    /// \param treeMode flag indicating tree mode
    /// \since Crypto++ 5.6.4
    BLAKE2s(bool treeMode=false, unsigned int digestSize = DIGESTSIZE);

    /// \brief Construct a BLAKE2s hash
    /// \param digestSize the digest size, in bytes
    /// \details treeMode flag is set to false
    /// \since Crypto++ 8.2
    BLAKE2s(unsigned int digestSize);

    /// \brief Construct a BLAKE2s hash
    /// \param key a byte array used to key the cipher
    /// \param keyLength the size of the byte array
    /// \param salt a byte array used as salt
    /// \param saltLength the size of the byte array
    /// \param personalization a byte array used as personalization string
    /// \param personalizationLength the size of the byte array
    /// \param treeMode flag indicating tree mode
    /// \param digestSize the digest size, in bytes
    /// \since Crypto++ 5.6.4
    BLAKE2s(const byte *key, size_t keyLength, const byte* salt = NULLPTR, size_t saltLength = 0,
        const byte* personalization = NULLPTR, size_t personalizationLength = 0,
        bool treeMode=false, unsigned int digestSize = DIGESTSIZE);

    /// \brief Retrieve the object's name
    /// \return the object's algorithm name following RFC 7693
    /// \details Object algorithm name follows the naming described in
    ///   <A HREF="http://tools.ietf.org/html/rfc7693#section-4">RFC 7693, The BLAKE2 Cryptographic Hash and
    /// Message Authentication Code (MAC)</A>. For example, "BLAKE2b-512" and "BLAKE2s-256".
    std::string AlgorithmName() const {return std::string(BLAKE2s_Info::StaticAlgorithmName()) + "-" + IntToString(DigestSize()*8);}

    /**
 * @brief Returns the block size used by the hash function in bytes.
 *
 * @return The block size in bytes.
 */
unsigned int BlockSize() const {return BLOCKSIZE;}
    /**
 * @brief Returns the digest size in bytes for the current BLAKE2 instance.
 *
 * @return The number of bytes in the hash output.
 */
unsigned int DigestSize() const {return m_digestSize;}
    /**
     * @brief Returns the optimal data alignment for BLAKE2s operations.
     *
     * @return The alignment, in bytes, required for optimal performance.
     */
    unsigned int OptimalDataAlignment() const;

    void Update(const byte *input, size_t length);
    void Restart();

    /// \brief Restart a hash with parameter block and counter
    /// \param block parameter block
    /// \param counter counter array
    /// \details Parameter block is persisted across calls to Restart().
    void Restart(const BLAKE2s_ParameterBlock& block, const word32 counter[2]);

    /// \brief Set tree mode
    /// \param mode the new tree mode
    /// \details BLAKE2 has two finalization flags, called State::f[0] and State::f[1].
    ///   If <tt>treeMode=false</tt> (default), then State::f[1] is never set. If
    ///   <tt>treeMode=true</tt>, then State::f[1] is set when State::f[0] is set.
    ///   Tree mode is persisted across calls to Restart().
    void SetTreeMode(bool mode) {m_treeMode=mode;}

    /// \brief Get tree mode
    /// \return the current tree mode
    /**
 * @brief Returns whether tree hashing mode is enabled.
 *
 * Tree mode determines if the BLAKE2 instance operates in tree hashing mode, which is preserved across restarts.
 *
 * @return true if tree mode is enabled; false otherwise.
 */
    bool GetTreeMode() const {return m_treeMode;}

    void TruncatedFinal(byte *hash, size_t size);

    std::string AlgorithmProvider() const;

protected:
    // Operates on state buffer and/or input. Must be BLOCKSIZE, final block will pad with 0's.
    void Compress(const byte *input);
    inline void IncrementCounter(size_t count=BLOCKSIZE);

    void UncheckedSetKey(const byte* key, unsigned int length, const CryptoPP::NameValuePairs& params);

private:
    State m_state;
    ParameterBlock m_block;
    AlignedSecByteBlock m_key;
    word32 m_digestSize, m_keyLength;
    bool m_treeMode;
};

/// \brief The BLAKE2b cryptographic hash function
/// \details BLAKE2b can function as both a hash and keyed hash. If you want only the hash,
///   then use the BLAKE2b constructor that accepts no parameters or digest size. If you
///   want a keyed hash, then use the constructor that accpts the key as a parameter.
///   Once a key and digest size are selected, its effectively immutable. The Restart()
///   method that accepts a ParameterBlock does not allow you to change it.
/// \sa Aumasson, Neves, Wilcox-O'Hearn and Winnerlein's
///   <A HREF="http://blake2.net/blake2.pdf">BLAKE2: simpler, smaller, fast as MD5</A> (2013.01.29).
/// \since C++ since Crypto++ 5.6.4, SSE since Crypto++ 5.6.4, NEON since Crypto++ 6.0,
///   Power8 since Crypto++ 8.0
class BLAKE2b : public SimpleKeyingInterfaceImpl<MessageAuthenticationCode, BLAKE2b_Info>
{
public:
    CRYPTOPP_CONSTANT(DEFAULT_KEYLENGTH = BLAKE2b_Info::DEFAULT_KEYLENGTH);
    CRYPTOPP_CONSTANT(MIN_KEYLENGTH = BLAKE2b_Info::MIN_KEYLENGTH);
    CRYPTOPP_CONSTANT(MAX_KEYLENGTH = BLAKE2b_Info::MAX_KEYLENGTH);

    CRYPTOPP_CONSTANT(DIGESTSIZE = BLAKE2b_Info::DIGESTSIZE);
    CRYPTOPP_CONSTANT(BLOCKSIZE = BLAKE2b_Info::BLOCKSIZE);
    CRYPTOPP_CONSTANT(SALTSIZE = BLAKE2b_Info::SALTSIZE);
    CRYPTOPP_CONSTANT(PERSONALIZATIONSIZE = BLAKE2b_Info::PERSONALIZATIONSIZE);

    typedef BLAKE2b_State State;
    typedef BLAKE2b_ParameterBlock ParameterBlock;

    /**
 * @brief Returns the static algorithm name for BLAKE2b.
 *
 * @return The string "BLAKE2b".
 */
CRYPTOPP_STATIC_CONSTEXPR const char* StaticAlgorithmName() {return "BLAKE2b";}

    /**
 * @brief Destroys the BLAKE2b object and securely clears sensitive data.
 */
virtual ~BLAKE2b() {}

    /// \brief Construct a BLAKE2b hash
    /// \param digestSize the digest size, in bytes
    /// \param treeMode flag indicating tree mode
    /// \since Crypto++ 5.6.4
    BLAKE2b(bool treeMode=false, unsigned int digestSize = DIGESTSIZE);

    /// \brief Construct a BLAKE2s hash
    /// \param digestSize the digest size, in bytes
    /// \details treeMode flag is set to false
    /// \since Crypto++ 8.2
    BLAKE2b(unsigned int digestSize);

    /// \brief Construct a BLAKE2b hash
    /// \param key a byte array used to key the cipher
    /// \param keyLength the size of the byte array
    /// \param salt a byte array used as salt
    /// \param saltLength the size of the byte array
    /// \param personalization a byte array used as personalization string
    /// \param personalizationLength the size of the byte array
    /// \param treeMode flag indicating tree mode
    /// \param digestSize the digest size, in bytes
    /// \since Crypto++ 5.6.4
    BLAKE2b(const byte *key, size_t keyLength, const byte* salt = NULLPTR, size_t saltLength = 0,
        const byte* personalization = NULLPTR, size_t personalizationLength = 0,
        bool treeMode=false, unsigned int digestSize = DIGESTSIZE);

    /// \brief Retrieve the object's name
    /// \return the object's algorithm name following RFC 7693
    /// \details Object algorithm name follows the naming described in
    ///   <A HREF="http://tools.ietf.org/html/rfc7693#section-4">RFC 7693, The BLAKE2 Cryptographic Hash and
    /// Message Authentication Code (MAC)</A>. For example, "BLAKE2b-512" and "BLAKE2s-256".
    std::string AlgorithmName() const {return std::string(BLAKE2b_Info::StaticAlgorithmName()) + "-" + IntToString(DigestSize()*8);}

    /**
 * @brief Returns the block size used by the hash function in bytes.
 *
 * @return The block size in bytes.
 */
unsigned int BlockSize() const {return BLOCKSIZE;}
    /**
 * @brief Returns the digest size in bytes for the current BLAKE2 instance.
 *
 * @return The number of bytes in the hash output.
 */
unsigned int DigestSize() const {return m_digestSize;}
    /**
     * @brief Sets the tree hashing mode for BLAKE2b.
     *
     * @param mode If true, enables tree hashing mode; if false, uses sequential mode.
     *
     * Tree mode affects the handling of the internal finalization flags. When enabled, both State::f[0] and State::f[1] are set during finalization; otherwise, only State::f[0] is set. The selected mode persists across hash restarts.
     */
    unsigned int OptimalDataAlignment() const;

    void Update(const byte *input, size_t length);
    void Restart();

    /// \brief Restart a hash with parameter block and counter
    /// \param block parameter block
    /// \param counter counter array
    /// \details Parameter block is persisted across calls to Restart().
    void Restart(const BLAKE2b_ParameterBlock& block, const word64 counter[2]);

    /// \brief Set tree mode
    /// \param mode the new tree mode
    /// \details BLAKE2 has two finalization flags, called State::f[0] and State::f[1].
    ///   If <tt>treeMode=false</tt> (default), then State::f[1] is never set. If
    ///   <tt>treeMode=true</tt>, then State::f[1] is set when State::f[0] is set.
    ///   Tree mode is persisted across calls to Restart().
    void SetTreeMode(bool mode) {m_treeMode=mode;}

    /// \brief Get tree mode
    /// \return the current tree mode
    /**
 * @brief Returns whether tree hashing mode is enabled.
 *
 * Tree mode determines if the BLAKE2 instance operates in tree hashing mode, which is preserved across restarts.
 *
 * @return true if tree mode is enabled; false otherwise.
 */
    bool GetTreeMode() const {return m_treeMode;}

    void TruncatedFinal(byte *hash, size_t size);

    std::string AlgorithmProvider() const;

protected:

    // Operates on state buffer and/or input. Must be BLOCKSIZE, final block will pad with 0's.
    void Compress(const byte *input);
    inline void IncrementCounter(size_t count=BLOCKSIZE);

    void UncheckedSetKey(const byte* key, unsigned int length, const CryptoPP::NameValuePairs& params);

private:
    State m_state;
    ParameterBlock m_block;
    AlignedSecByteBlock m_key;
    word32 m_digestSize, m_keyLength;
    bool m_treeMode;
};

NAMESPACE_END

#endif
