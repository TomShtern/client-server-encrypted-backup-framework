// algebra_instantiations.cpp - explicit template instantiations for Crypto++ abstract algebra classes

#include "pch.h"
#include "algebra.h"
#include "integer.h"
#include "ecp.h"
#include "ec2n.h"
#include "gf2n.h"
#include "strciphr.h"
#include "modes.h"

NAMESPACE_BEGIN(CryptoPP)

// Forward declarations for types used in instantiations
struct ECPPoint;
struct EC2NPoint;
class PolynomialMod2;

// AbstractGroup<Integer> explicit instantiations
template class AbstractGroup<Integer>;
template Integer AbstractGroup<Integer>::ScalarMultiply(const Integer&, const Integer&) const;
template Integer AbstractGroup<Integer>::CascadeScalarMultiply(const Integer&, const Integer&, const Integer&, const Integer&) const;
template void AbstractGroup<Integer>::SimultaneousMultiply(Integer*, const Integer&, const Integer*, unsigned int) const;

// AbstractRing<Integer> explicit instantiations
template class AbstractRing<Integer>;
template Integer AbstractRing<Integer>::Exponentiate(const Integer&, const Integer&) const;
template Integer AbstractRing<Integer>::CascadeExponentiate(const Integer&, const Integer&, const Integer&, const Integer&) const;
template void AbstractRing<Integer>::SimultaneousExponentiate(Integer*, const Integer&, const Integer*, unsigned int) const;

// AbstractEuclideanDomain<Integer> explicit instantiations
template class AbstractEuclideanDomain<Integer>;
template const Integer& AbstractEuclideanDomain<Integer>::Gcd(const Integer&, const Integer&) const;

// AbstractGroup<ECPPoint> explicit instantiations
template class AbstractGroup<ECPPoint>;
template const ECPPoint& AbstractGroup<ECPPoint>::Subtract(const ECPPoint&, const ECPPoint&) const;
template ECPPoint& AbstractGroup<ECPPoint>::Accumulate(ECPPoint&, const ECPPoint&) const;
template ECPPoint& AbstractGroup<ECPPoint>::Reduce(ECPPoint&, const ECPPoint&) const;
template ECPPoint AbstractGroup<ECPPoint>::CascadeScalarMultiply(const ECPPoint&, const Integer&, const ECPPoint&, const Integer&) const;
template void AbstractGroup<ECPPoint>::SimultaneousMultiply(ECPPoint*, const ECPPoint&, const Integer*, unsigned int) const;

// AbstractGroup<EC2NPoint> explicit instantiations
template class AbstractGroup<EC2NPoint>;
template const EC2NPoint& AbstractGroup<EC2NPoint>::Subtract(const EC2NPoint&, const EC2NPoint&) const;
template EC2NPoint& AbstractGroup<EC2NPoint>::Accumulate(EC2NPoint&, const EC2NPoint&) const;
template EC2NPoint& AbstractGroup<EC2NPoint>::Reduce(EC2NPoint&, const EC2NPoint&) const;
template EC2NPoint AbstractGroup<EC2NPoint>::ScalarMultiply(const EC2NPoint&, const Integer&) const;
template EC2NPoint AbstractGroup<EC2NPoint>::CascadeScalarMultiply(const EC2NPoint&, const Integer&, const EC2NPoint&, const Integer&) const;
template void AbstractGroup<EC2NPoint>::SimultaneousMultiply(EC2NPoint*, const EC2NPoint&, const Integer*, unsigned int) const;

// AbstractGroup<PolynomialMod2> explicit instantiations
template class AbstractGroup<PolynomialMod2>;
template PolynomialMod2 AbstractGroup<PolynomialMod2>::ScalarMultiply(const PolynomialMod2&, const Integer&) const;
template PolynomialMod2 AbstractGroup<PolynomialMod2>::CascadeScalarMultiply(const PolynomialMod2&, const Integer&, const PolynomialMod2&, const Integer&) const;
template void AbstractGroup<PolynomialMod2>::SimultaneousMultiply(PolynomialMod2*, const PolynomialMod2&, const Integer*, unsigned int) const;

// AbstractRing<PolynomialMod2> explicit instantiations
template class AbstractRing<PolynomialMod2>;
template const PolynomialMod2& AbstractRing<PolynomialMod2>::Divide(const PolynomialMod2&, const PolynomialMod2&) const;
template PolynomialMod2 AbstractRing<PolynomialMod2>::Exponentiate(const PolynomialMod2&, const Integer&) const;
template PolynomialMod2 AbstractRing<PolynomialMod2>::CascadeExponentiate(const PolynomialMod2&, const Integer&, const PolynomialMod2&, const Integer&) const;
template void AbstractRing<PolynomialMod2>::SimultaneousExponentiate(PolynomialMod2*, const PolynomialMod2&, const Integer*, unsigned int) const;

// AbstractEuclideanDomain<PolynomialMod2> explicit instantiations
template class AbstractEuclideanDomain<PolynomialMod2>;
template const PolynomialMod2& AbstractEuclideanDomain<PolynomialMod2>::Gcd(const PolynomialMod2&, const PolynomialMod2&) const;

// QuotientRing<EuclideanDomainOf<PolynomialMod2>> explicit instantiations
template class QuotientRing<EuclideanDomainOf<PolynomialMod2>>;
template const PolynomialMod2& QuotientRing<EuclideanDomainOf<PolynomialMod2>>::MultiplicativeInverse(const PolynomialMod2&) const;

// CFB template instantiations for randpool
template class CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>;
template void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::ProcessData(byte*, const byte*, size_t);
template void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::Resynchronize(const byte*, int);
template void CFB_CipherTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::UncheckedSetKey(const byte*, unsigned int, const NameValuePairs&);

template class CFB_EncryptionTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>;
template void CFB_EncryptionTemplate<AbstractPolicyHolder<CFB_CipherAbstractPolicy, CFB_ModePolicy>>::CombineMessageAndShiftRegister(byte*, byte*, const byte*, size_t);

NAMESPACE_END
