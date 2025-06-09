// abstract_implementations.cpp - provides dummy implementations for abstract virtual methods
// These should never be called in practice as they should be overridden by concrete implementations

#include "pch.h"
#include "algebra.h"
#include "integer.h"
#include "ecp.h"
#include "ec2n.h"
#include "gf2n.h"
#include "strciphr.h"
#include "modes.h"

NAMESPACE_BEGIN(CryptoPP)

// AbstractGroup<Integer> implementations - these should be overridden by ModularArithmetic
template<>
/**
 * @brief Computes the scalar multiplication of an integer group element.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @param base The group element to be multiplied.
 * @param exponent The scalar multiplier.
 * @return The result of scalar multiplication.
 */
Integer AbstractGroup<Integer>::ScalarMultiply(const Integer &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<Integer>::ScalarMultiply should be overridden");
}

template<>
/**
 * @brief Placeholder for cascade scalar multiplication in an integer group.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for cascade scalar multiplication of two group elements raised to respective exponents.
 */
Integer AbstractGroup<Integer>::CascadeScalarMultiply(const Integer &x, const Integer &e1, const Integer &y, const Integer &e2) const
{
    throw NotImplemented("AbstractGroup<Integer>::CascadeScalarMultiply should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous group multiplication of integers.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for simultaneous group multiplication with multiple exponents.
 */
void AbstractGroup<Integer>::SimultaneousMultiply(Integer *results, const Integer &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<Integer>::SimultaneousMultiply should be overridden");
}

// AbstractRing<Integer> implementations - these should be overridden by ModularArithmetic
template<>
/**
 * @brief Raises an integer to a given exponent in the ring.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @param a The base integer.
 * @param e The exponent.
 * @return Integer The result of exponentiation.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
Integer AbstractRing<Integer>::Exponentiate(const Integer &a, const Integer &e) const
{
    throw NotImplemented("AbstractRing<Integer>::Exponentiate should be overridden");
}

template<>
/**
 * @brief Placeholder for cascade exponentiation in an integer ring.
 *
 * Computes a combined exponentiation of two integer elements, but this method must be overridden by a concrete implementation. Calling this function will throw a NotImplemented exception.
 */
Integer AbstractRing<Integer>::CascadeExponentiate(const Integer &x, const Integer &e1, const Integer &y, const Integer &e2) const
{
    throw NotImplemented("AbstractRing<Integer>::CascadeExponentiate should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous exponentiation of multiple exponents in an integer ring.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for computing multiple exponentiations of a base with different exponents.
 */
void AbstractRing<Integer>::SimultaneousExponentiate(Integer *results, const Integer &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractRing<Integer>::SimultaneousExponentiate should be overridden");
}

// AbstractEuclideanDomain<Integer> implementations - these should be overridden by ModularArithmetic
template<>
/**
 * @brief Computes the greatest common divisor (GCD) of two integers.
 *
 * This is a placeholder implementation that must be overridden by a concrete subclass. Calling this method will throw a NotImplemented exception.
 *
 * @return Reference to the GCD of a and b.
 */
const Integer& AbstractEuclideanDomain<Integer>::Gcd(const Integer &a, const Integer &b) const
{
    throw NotImplemented("AbstractEuclideanDomain<Integer>::Gcd should be overridden");
}

// AbstractGroup<ECPPoint> implementations - these should be overridden by ECP
template<>
/**
 * @brief Subtracts one elliptic curve point from another.
 *
 * This is a placeholder implementation that must be overridden by a concrete subclass. Calling this function will throw a NotImplemented exception.
 *
 * @param a The minuend elliptic curve point.
 * @param b The subtrahend elliptic curve point.
 * @return Reference to the result of the subtraction.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
const ECPPoint& AbstractGroup<ECPPoint>::Subtract(const ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Subtract should be overridden");
}

template<>
/**
 * @brief Placeholder for group accumulation operation on elliptic curve points.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for accumulating one ECPPoint into another.
 */
ECPPoint& AbstractGroup<ECPPoint>::Accumulate(ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Accumulate should be overridden");
}

template<>
/**
 * @brief Reduces the group element a by b.
 *
 * This is a placeholder implementation that must be overridden by a concrete subclass. Calling this function will throw a NotImplemented exception.
 *
 * @return Reference to the reduced group element.
 */
ECPPoint& AbstractGroup<ECPPoint>::Reduce(ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Reduce should be overridden");
}

template<>
/**
 * @brief Placeholder for cascade scalar multiplication of elliptic curve points.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for computing the sum of two scalar multiplications on elliptic curve points.
 *
 * @param element1 First elliptic curve point.
 * @param exponent1 Scalar multiplier for the first point.
 * @param element2 Second elliptic curve point.
 * @param exponent2 Scalar multiplier for the second point.
 * @return ECPPoint Result of the cascade scalar multiplication.
 * @throws NotImplemented Always thrown to indicate the method must be overridden.
 */
ECPPoint AbstractGroup<ECPPoint>::CascadeScalarMultiply(const ECPPoint &element1, const Integer &exponent1, const ECPPoint &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::CascadeScalarMultiply should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous scalar multiplication of elliptic curve points.
 *
 * Throws a NotImplemented exception to enforce that concrete ECP group implementations provide their own version of this method.
 */
void AbstractGroup<ECPPoint>::SimultaneousMultiply(ECPPoint *results, const ECPPoint &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::SimultaneousMultiply should be overridden");
}

// AbstractGroup<EC2NPoint> implementations - these should be overridden by EC2N  
template<>
/**
 * @brief Subtracts one EC2NPoint from another in the group.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @param a The minuend point.
 * @param b The subtrahend point.
 * @return Reference to the result of the subtraction.
 * @throws NotImplemented Always thrown by this default implementation.
 */
const EC2NPoint& AbstractGroup<EC2NPoint>::Subtract(const EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Subtract should be overridden");
}

template<>
/**
 * @brief Placeholder for group accumulation operation on EC2NPoint elements.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for accumulating two EC2NPoint elements in the group.
 */
EC2NPoint& AbstractGroup<EC2NPoint>::Accumulate(EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Accumulate should be overridden");
}

template<>
/**
 * @brief Placeholder for reducing an EC2NPoint group element.
 *
 * This method must be overridden by a concrete implementation. Calling this function will throw a NotImplemented exception.
 *
 * @param a The group element to be reduced.
 * @param b The group element used in the reduction operation.
 * @return EC2NPoint& Reference to the reduced group element.
 */
EC2NPoint& AbstractGroup<EC2NPoint>::Reduce(EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Reduce should be overridden");
}

template<>
/**
 * @brief Placeholder for scalar multiplication of an EC2NPoint.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for scalar multiplication in the EC2N group.
 *
 * @param base The EC2NPoint to be multiplied.
 * @param exponent The scalar multiplier.
 * @return EC2NPoint The result of the scalar multiplication.
 * @throws NotImplemented Always thrown to indicate the method must be overridden.
 */
EC2NPoint AbstractGroup<EC2NPoint>::ScalarMultiply(const EC2NPoint &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::ScalarMultiply should be overridden");
}

template<>
/**
 * @brief Computes a combined scalar multiplication of two EC2N points.
 *
 * This method must be overridden by a concrete implementation. The default implementation throws a NotImplemented exception.
 *
 * @param element1 The first EC2N point.
 * @param exponent1 The scalar multiplier for the first point.
 * @param element2 The second EC2N point.
 * @param exponent2 The scalar multiplier for the second point.
 * @return EC2NPoint The result of the cascade scalar multiplication.
 * @throws NotImplemented Always thrown by this default implementation.
 */
EC2NPoint AbstractGroup<EC2NPoint>::CascadeScalarMultiply(const EC2NPoint &element1, const Integer &exponent1, const EC2NPoint &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::CascadeScalarMultiply should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous scalar multiplication in EC2NPoint groups.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for simultaneous scalar multiplication of EC2NPoint elements.
 */
void AbstractGroup<EC2NPoint>::SimultaneousMultiply(EC2NPoint *results, const EC2NPoint &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::SimultaneousMultiply should be overridden");
}

// AbstractGroup<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
/**
 * @brief Computes the scalar multiple of a polynomial in the group.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @return The result of multiplying the given polynomial base by the specified integer exponent.
 */
PolynomialMod2 AbstractGroup<PolynomialMod2>::ScalarMultiply(const PolynomialMod2 &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::ScalarMultiply should be overridden");
}

template<>
/**
 * @brief Computes a combined scalar multiplication of two group elements.
 *
 * This method is a placeholder and must be overridden by a concrete implementation. It is intended to compute the result of multiplying two `PolynomialMod2` elements by their respective integer exponents and combining them according to the group operation.
 *
 * @return The result of the cascade scalar multiplication.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
PolynomialMod2 AbstractGroup<PolynomialMod2>::CascadeScalarMultiply(const PolynomialMod2 &element1, const Integer &exponent1, const PolynomialMod2 &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::CascadeScalarMultiply should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous multiplication in a polynomial group.
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses of AbstractGroup<PolynomialMod2> provide their own implementation for simultaneous multiplication of a base element by multiple exponents.
 */
void AbstractGroup<PolynomialMod2>::SimultaneousMultiply(PolynomialMod2 *results, const PolynomialMod2 &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::SimultaneousMultiply should be overridden");
}

// AbstractRing<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
/**
 * @brief Divides one polynomial by another in the ring of polynomials modulo 2.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @return Reference to the result of the division.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
const PolynomialMod2& AbstractRing<PolynomialMod2>::Divide(const PolynomialMod2 &a, const PolynomialMod2 &b) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::Divide should be overridden");
}

template<>
/**
 * @brief Raises a polynomial to a given integer exponent in the ring.
 *
 * This method must be overridden by a concrete implementation. Calling this default implementation will throw a NotImplemented exception.
 *
 * @return The result of raising the polynomial to the specified exponent.
 */
PolynomialMod2 AbstractRing<PolynomialMod2>::Exponentiate(const PolynomialMod2 &a, const Integer &e) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::Exponentiate should be overridden");
}

template<>
/**
 * @brief Placeholder for cascade exponentiation in a polynomial ring over GF(2).
 *
 * Throws a NotImplemented exception to enforce that concrete subclasses provide an implementation for computing the cascade exponentiation of two polynomials with given exponents.
 *
 * @throws NotImplemented Always thrown to indicate the method must be overridden.
 */
PolynomialMod2 AbstractRing<PolynomialMod2>::CascadeExponentiate(const PolynomialMod2 &x, const Integer &e1, const PolynomialMod2 &y, const Integer &e2) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::CascadeExponentiate should be overridden");
}

template<>
/**
 * @brief Placeholder for simultaneous exponentiation of polynomials in GF(2^n).
 *
 * Throws a NotImplemented exception to enforce that concrete GF2N classes provide an implementation for computing multiple exponentiations of a base polynomial with different exponents.
 */
void AbstractRing<PolynomialMod2>::SimultaneousExponentiate(PolynomialMod2 *results, const PolynomialMod2 &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::SimultaneousExponentiate should be overridden");
}

// AbstractEuclideanDomain<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
/**
 * @brief Computes the greatest common divisor (GCD) of two polynomials over GF(2).
 *
 * This is a placeholder implementation that must be overridden by a concrete subclass. Calling this method will throw a NotImplemented exception.
 *
 * @return Reference to the GCD of the input polynomials.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
const PolynomialMod2& AbstractEuclideanDomain<PolynomialMod2>::Gcd(const PolynomialMod2 &a, const PolynomialMod2 &b) const
{
    throw NotImplemented("AbstractEuclideanDomain<PolynomialMod2>::Gcd should be overridden");
}

// QuotientRing<EuclideanDomainOf<PolynomialMod2>> implementations - these should be overridden by GF2N classes
template<>
/**
 * @brief Returns the multiplicative inverse of a polynomial in the quotient ring.
 *
 * This is a placeholder implementation that must be overridden by a concrete subclass. Calling this function will throw a NotImplemented exception.
 *
 * @param a The polynomial for which to compute the multiplicative inverse.
 * @return The multiplicative inverse of the input polynomial.
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
const PolynomialMod2& QuotientRing<EuclideanDomainOf<PolynomialMod2>>::MultiplicativeInverse(const PolynomialMod2 &a) const
{
    throw NotImplemented("QuotientRing<EuclideanDomainOf<PolynomialMod2>>::MultiplicativeInverse should be overridden");
}

// CFB_CipherTemplate implementations - these should be overridden by concrete CFB implementations
template<>
/**
 * @brief Processes input data for CFB cipher mode.
 *
 * This method must be overridden by concrete CFB cipher implementations to perform encryption or decryption of the input data.
 *
 * @param outString Pointer to the output buffer.
 * @param inString Pointer to the input buffer.
 * @param length Number of bytes to process.
 *
 * @throws NotImplemented Always thrown to indicate the method is not implemented.
 */
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::ProcessData(byte *outString, const byte *inString, size_t length)
{
    throw NotImplemented("CFB_CipherTemplate::ProcessData should be overridden");
}

template<>
/**
 * @brief Resynchronizes the cipher with a new initialization vector (IV).
 *
 * This method must be overridden by concrete CFB cipher implementations to update the internal state using the provided IV.
 *
 * @param iv Pointer to the initialization vector.
 * @param length Length of the initialization vector in bytes.
 */
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::Resynchronize(const byte *iv, int length)
{
    throw NotImplemented("CFB_CipherTemplate::Resynchronize should be overridden");
}

template<>
/**
 * @brief Sets the key and parameters for the CFB cipher.
 *
 * This method must be overridden by concrete CFB cipher implementations to handle key setup and parameter configuration. Calling this base implementation will throw a NotImplemented exception.
 */
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::UncheckedSetKey(const byte *key, unsigned int length, const NameValuePairs &params)
{
    throw NotImplemented("CFB_CipherTemplate::UncheckedSetKey should be overridden");
}

template<>
/**
 * @brief Placeholder for combining message and shift register in CFB encryption.
 *
 * This method must be overridden by a concrete CFB encryption implementation. Calling this function will throw a NotImplemented exception.
 */
void CFB_EncryptionTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::CombineMessageAndShiftRegister(byte *output, byte *reg, const byte *message, size_t length)
{
    throw NotImplemented("CFB_EncryptionTemplate::CombineMessageAndShiftRegister should be overridden");
}

NAMESPACE_END
