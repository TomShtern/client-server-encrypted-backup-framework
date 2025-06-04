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
Integer AbstractGroup<Integer>::ScalarMultiply(const Integer &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<Integer>::ScalarMultiply should be overridden");
}

template<>
Integer AbstractGroup<Integer>::CascadeScalarMultiply(const Integer &x, const Integer &e1, const Integer &y, const Integer &e2) const
{
    throw NotImplemented("AbstractGroup<Integer>::CascadeScalarMultiply should be overridden");
}

template<>
void AbstractGroup<Integer>::SimultaneousMultiply(Integer *results, const Integer &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<Integer>::SimultaneousMultiply should be overridden");
}

// AbstractRing<Integer> implementations - these should be overridden by ModularArithmetic
template<>
Integer AbstractRing<Integer>::Exponentiate(const Integer &a, const Integer &e) const
{
    throw NotImplemented("AbstractRing<Integer>::Exponentiate should be overridden");
}

template<>
Integer AbstractRing<Integer>::CascadeExponentiate(const Integer &x, const Integer &e1, const Integer &y, const Integer &e2) const
{
    throw NotImplemented("AbstractRing<Integer>::CascadeExponentiate should be overridden");
}

template<>
void AbstractRing<Integer>::SimultaneousExponentiate(Integer *results, const Integer &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractRing<Integer>::SimultaneousExponentiate should be overridden");
}

// AbstractEuclideanDomain<Integer> implementations - these should be overridden by ModularArithmetic
template<>
const Integer& AbstractEuclideanDomain<Integer>::Gcd(const Integer &a, const Integer &b) const
{
    throw NotImplemented("AbstractEuclideanDomain<Integer>::Gcd should be overridden");
}

// AbstractGroup<ECPPoint> implementations - these should be overridden by ECP
template<>
const ECPPoint& AbstractGroup<ECPPoint>::Subtract(const ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Subtract should be overridden");
}

template<>
ECPPoint& AbstractGroup<ECPPoint>::Accumulate(ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Accumulate should be overridden");
}

template<>
ECPPoint& AbstractGroup<ECPPoint>::Reduce(ECPPoint &a, const ECPPoint &b) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::Reduce should be overridden");
}

template<>
ECPPoint AbstractGroup<ECPPoint>::CascadeScalarMultiply(const ECPPoint &element1, const Integer &exponent1, const ECPPoint &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::CascadeScalarMultiply should be overridden");
}

template<>
void AbstractGroup<ECPPoint>::SimultaneousMultiply(ECPPoint *results, const ECPPoint &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<ECPPoint>::SimultaneousMultiply should be overridden");
}

// AbstractGroup<EC2NPoint> implementations - these should be overridden by EC2N  
template<>
const EC2NPoint& AbstractGroup<EC2NPoint>::Subtract(const EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Subtract should be overridden");
}

template<>
EC2NPoint& AbstractGroup<EC2NPoint>::Accumulate(EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Accumulate should be overridden");
}

template<>
EC2NPoint& AbstractGroup<EC2NPoint>::Reduce(EC2NPoint &a, const EC2NPoint &b) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::Reduce should be overridden");
}

template<>
EC2NPoint AbstractGroup<EC2NPoint>::ScalarMultiply(const EC2NPoint &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::ScalarMultiply should be overridden");
}

template<>
EC2NPoint AbstractGroup<EC2NPoint>::CascadeScalarMultiply(const EC2NPoint &element1, const Integer &exponent1, const EC2NPoint &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::CascadeScalarMultiply should be overridden");
}

template<>
void AbstractGroup<EC2NPoint>::SimultaneousMultiply(EC2NPoint *results, const EC2NPoint &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<EC2NPoint>::SimultaneousMultiply should be overridden");
}

// AbstractGroup<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
PolynomialMod2 AbstractGroup<PolynomialMod2>::ScalarMultiply(const PolynomialMod2 &base, const Integer &exponent) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::ScalarMultiply should be overridden");
}

template<>
PolynomialMod2 AbstractGroup<PolynomialMod2>::CascadeScalarMultiply(const PolynomialMod2 &element1, const Integer &exponent1, const PolynomialMod2 &element2, const Integer &exponent2) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::CascadeScalarMultiply should be overridden");
}

template<>
void AbstractGroup<PolynomialMod2>::SimultaneousMultiply(PolynomialMod2 *results, const PolynomialMod2 &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractGroup<PolynomialMod2>::SimultaneousMultiply should be overridden");
}

// AbstractRing<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
const PolynomialMod2& AbstractRing<PolynomialMod2>::Divide(const PolynomialMod2 &a, const PolynomialMod2 &b) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::Divide should be overridden");
}

template<>
PolynomialMod2 AbstractRing<PolynomialMod2>::Exponentiate(const PolynomialMod2 &a, const Integer &e) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::Exponentiate should be overridden");
}

template<>
PolynomialMod2 AbstractRing<PolynomialMod2>::CascadeExponentiate(const PolynomialMod2 &x, const Integer &e1, const PolynomialMod2 &y, const Integer &e2) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::CascadeExponentiate should be overridden");
}

template<>
void AbstractRing<PolynomialMod2>::SimultaneousExponentiate(PolynomialMod2 *results, const PolynomialMod2 &base, const Integer *exponents, unsigned int exponentsCount) const
{
    throw NotImplemented("AbstractRing<PolynomialMod2>::SimultaneousExponentiate should be overridden");
}

// AbstractEuclideanDomain<PolynomialMod2> implementations - these should be overridden by GF2N classes
template<>
const PolynomialMod2& AbstractEuclideanDomain<PolynomialMod2>::Gcd(const PolynomialMod2 &a, const PolynomialMod2 &b) const
{
    throw NotImplemented("AbstractEuclideanDomain<PolynomialMod2>::Gcd should be overridden");
}

// QuotientRing<EuclideanDomainOf<PolynomialMod2>> implementations - these should be overridden by GF2N classes
template<>
const PolynomialMod2& QuotientRing<EuclideanDomainOf<PolynomialMod2>>::MultiplicativeInverse(const PolynomialMod2 &a) const
{
    throw NotImplemented("QuotientRing<EuclideanDomainOf<PolynomialMod2>>::MultiplicativeInverse should be overridden");
}

// CFB_CipherTemplate implementations - these should be overridden by concrete CFB implementations
template<>
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::ProcessData(byte *outString, const byte *inString, size_t length)
{
    throw NotImplemented("CFB_CipherTemplate::ProcessData should be overridden");
}

template<>
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::Resynchronize(const byte *iv, int length)
{
    throw NotImplemented("CFB_CipherTemplate::Resynchronize should be overridden");
}

template<>
void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::UncheckedSetKey(const byte *key, unsigned int length, const NameValuePairs &params)
{
    throw NotImplemented("CFB_CipherTemplate::UncheckedSetKey should be overridden");
}

template<>
void CFB_EncryptionTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::CombineMessageAndShiftRegister(byte *output, byte *reg, const byte *message, size_t length)
{
    throw NotImplemented("CFB_EncryptionTemplate::CombineMessageAndShiftRegister should be overridden");
}

NAMESPACE_END
