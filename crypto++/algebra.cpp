// algebra.cpp - originally written and placed in the public domain by Wei Dai

#include "pch.h"

#ifndef CRYPTOPP_ALGEBRA_CPP	// SunCC workaround: compiler could cause this file to be included twice
#define CRYPTOPP_ALGEBRA_CPP

#include "algebra.h"
#include "integer.h"

#include <vector>

NAMESPACE_BEGIN(CryptoPP)

template <class T> /**
 * @brief Returns the sum of an element with itself in the group.
 *
 * @param a The group element to be doubled.
 * @return The result of adding a to itself.
 */
const T& AbstractGroup<T>::Double(const Element &a) const
{
	return this->Add(a, a);
}

template <class T> /**
 * @brief Returns the difference of two group elements.
 *
 * Computes the group operation of element `a` with the inverse of element `b`, effectively calculating `a - b` in the group.
 *
 * @param a The minuend element.
 * @param b The subtrahend element.
 * @return The result of the group operation `a + (-b)`.
 */
const T& AbstractGroup<T>::Subtract(const Element &a, const Element &b) const
{
	// make copy of a in case Inverse() overwrites it
	Element a1(a);
	return this->Add(a1, Inverse(b));
}

template <class T> /**
 * @brief Adds an element to another and assigns the result to the first element.
 *
 * @param a The element to be updated with the sum.
 * @param b The element to add.
 * @return Reference to the updated element a.
 */
T& AbstractGroup<T>::Accumulate(Element &a, const Element &b) const
{
	return a = this->Add(a, b);
}

template <class T> /**
 * @brief Subtracts an element from another and assigns the result.
 *
 * Modifies element `a` by subtracting element `b` from it, assigning the result to `a`.
 *
 * @return Reference to the updated element `a`.
 */
T& AbstractGroup<T>::Reduce(Element &a, const Element &b) const
{
	return a = this->Subtract(a, b);
}

template <class T> /**
 * @brief Computes the square of an element in the ring.
 *
 * @param a The element to be squared.
 * @return The result of multiplying the element by itself.
 */
const T& AbstractRing<T>::Square(const Element &a) const
{
	return this->Multiply(a, a);
}

template <class T> /**
 * @brief Returns the result of dividing element a by element b in the ring.
 *
 * Computes the product of a and the multiplicative inverse of b. If b does not have an inverse, the result is the ring's identity element.
 *
 * @return The element representing a divided by b.
 */
const T& AbstractRing<T>::Divide(const Element &a, const Element &b) const
{
	// make copy of a in case MultiplicativeInverse() overwrites it
	Element a1(a);
	return this->Multiply(a1, this->MultiplicativeInverse(b));
}

template <class T> /**
 * @brief Computes the remainder of dividing one element by another in the Euclidean domain.
 *
 * Uses the division algorithm to return the modulus of element `a` by element `b`.
 *
 * @return The remainder of `a` divided by `b`.
 */
const T& AbstractEuclideanDomain<T>::Mod(const Element &a, const Element &b) const
{
	Element q;
	this->DivisionAlgorithm(result, q, a, b);
	return result;
}

template <class T> /**
 * @brief Computes the greatest common divisor (GCD) of two elements.
 *
 * Uses the Euclidean algorithm to find the GCD of elements `a` and `b` in the domain.
 *
 * @return Reference to the GCD of `a` and `b`.
 */
const T& AbstractEuclideanDomain<T>::Gcd(const Element &a, const Element &b) const
{
	Element g[3]={b, a};
	unsigned int i0=0, i1=1, i2=2;

	while (!this->Equal(g[i1], this->Identity()))
	{
		g[i2] = this->Mod(g[i0], g[i1]);
		unsigned int t = i0; i0 = i1; i1 = i2; i2 = t;
	}

	return result = g[i0];
}

template <class T> /**
 * @brief Computes the multiplicative inverse of an element in the quotient ring.
 *
 * Uses the extended Euclidean algorithm to find the multiplicative inverse of the given element modulo the ring's modulus. If the inverse exists, it is returned; otherwise, the identity element is returned.
 *
 * @param a The element for which to compute the multiplicative inverse.
 * @return The multiplicative inverse of `a` modulo the ring's modulus, or the identity element if no inverse exists.
 */
const typename QuotientRing<T>::Element& QuotientRing<T>::MultiplicativeInverse(const Element &a) const
{
	Element g[3]={m_modulus, a};
	Element v[3]={m_domain.Identity(), m_domain.MultiplicativeIdentity()};
	Element y;
	unsigned int i0=0, i1=1, i2=2;

	while (!this->Equal(g[i1], this->Identity()))
	{
		// y = g[i0] / g[i1];
		// g[i2] = g[i0] % g[i1];
		m_domain.DivisionAlgorithm(g[i2], y, g[i0], g[i1]);
		// v[i2] = v[i0] - (v[i1] * y);
		v[i2] = m_domain.Subtract(v[i0], m_domain.Multiply(v[i1], y));
		unsigned int t = i0; i0 = i1; i1 = i2; i2 = t;
	}

	return m_domain.IsUnit(g[i0]) ? m_domain.Divide(v[i0], g[i0]) : m_domain.Identity();
}

template <class T> /**
 * @brief Computes the scalar multiplication of a group element by an integer exponent.
 *
 * Returns the result of multiplying the given group element by the specified exponent using efficient simultaneous multiplication techniques.
 *
 * @param base The group element to be multiplied.
 * @param exponent The integer exponent.
 * @return The result of scalar multiplication.
 */
T AbstractGroup<T>::ScalarMultiply(const Element &base, const Integer &exponent) const
{
	Element result;
	this->SimultaneousMultiply(&result, base, &exponent, 1);
	return result;
}

template <class T> /**
 * @brief Computes the simultaneous scalar multiplication of two group elements by two exponents.
 *
 * Calculates \( x^{e1} + y^{e2} \) efficiently using a windowed method with precomputed power tables and bit scanning, minimizing the number of group operations.
 *
 * @param x First group element.
 * @param e1 Exponent for the first element.
 * @param y Second group element.
 * @param e2 Exponent for the second element.
 * @return The group element resulting from the cascade scalar multiplication.
 */
T AbstractGroup<T>::CascadeScalarMultiply(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const
{
	const unsigned expLen = STDMAX(e1.BitCount(), e2.BitCount());
	if (expLen==0)
		return this->Identity();

	const unsigned w = (expLen <= 46 ? 1 : (expLen <= 260 ? 2 : 3));
	const unsigned tableSize = 1<<w;
	std::vector<Element> powerTable(tableSize << w);

	powerTable[1] = x;
	powerTable[tableSize] = y;
	if (w==1)
		powerTable[3] = this->Add(x,y);
	else
	{
		powerTable[2] = this->Double(x);
		powerTable[2*tableSize] = this->Double(y);

		unsigned i, j;

		for (i=3; i<tableSize; i+=2)
			powerTable[i] = Add(powerTable[i-2], powerTable[2]);
		for (i=1; i<tableSize; i+=2)
			for (j=i+tableSize; j<(tableSize<<w); j+=tableSize)
				powerTable[j] = Add(powerTable[j-tableSize], y);

		for (i=3*tableSize; i<(tableSize<<w); i+=2*tableSize)
			powerTable[i] = Add(powerTable[i-2*tableSize], powerTable[2*tableSize]);
		for (i=tableSize; i<(tableSize<<w); i+=2*tableSize)
			for (j=i+2; j<i+tableSize; j+=2)
				powerTable[j] = Add(powerTable[j-1], x);
	}

	Element result;
	unsigned power1 = 0, power2 = 0, prevPosition = expLen-1;
	bool firstTime = true;

	for (int i = expLen-1; i>=0; i--)
	{
		power1 = 2*power1 + e1.GetBit(i);
		power2 = 2*power2 + e2.GetBit(i);

		if (i==0 || 2*power1 >= tableSize || 2*power2 >= tableSize)
		{
			unsigned squaresBefore = prevPosition-i;
			unsigned squaresAfter = 0;
			prevPosition = i;
			while ((power1 || power2) && power1%2 == 0 && power2%2==0)
			{
				power1 /= 2;
				power2 /= 2;
				squaresBefore--;
				squaresAfter++;
			}
			if (firstTime)
			{
				result = powerTable[(power2<<w) + power1];
				firstTime = false;
			}
			else
			{
				while (squaresBefore--)
					result = this->Double(result);
				if (power1 || power2)
					Accumulate(result, powerTable[(power2<<w) + power1]);
			}
			while (squaresAfter--)
				result = this->Double(result);
			power1 = power2 = 0;
		}
	}
	return result;
}

template <class Element, class Iterator> /**
 * @brief Performs cascade scalar multiplication for multiple base-exponent pairs in an abstract group.
 *
 * Computes the sum of each base multiplied by its corresponding exponent, i.e., \f$\sum_i \text{base}_i \cdot \text{exponent}_i\f$, using optimized strategies for one, two, or more pairs. For more than two pairs, it uses a heap-based approach to combine exponents and accumulate results efficiently.
 *
 * @tparam Element The group element type.
 * @tparam Iterator An iterator type over pairs of base and exponent.
 * @param group The abstract group in which the operation is performed.
 * @param begin Iterator to the beginning of the base-exponent pairs.
 * @param end Iterator to the end of the base-exponent pairs.
 * @return The resulting group element after cascade multiplication.
 */
Element GeneralCascadeMultiplication(const AbstractGroup<Element> &group, Iterator begin, Iterator end)
{
	if (end-begin == 1)
		return group.ScalarMultiply(begin->base, begin->exponent);
	else if (end-begin == 2)
		return group.CascadeScalarMultiply(begin->base, begin->exponent, (begin+1)->base, (begin+1)->exponent);
	else
	{
		Integer q, t;
		Iterator last = end;
		--last;

		std::make_heap(begin, end);
		std::pop_heap(begin, end);

		while (!!begin->exponent)
		{
			// last->exponent is largest exponent, begin->exponent is next largest
			t = last->exponent;
			Integer::Divide(last->exponent, q, t, begin->exponent);

			if (q == Integer::One())
				group.Accumulate(begin->base, last->base);	// avoid overhead of ScalarMultiply()
			else
				group.Accumulate(begin->base, group.ScalarMultiply(last->base, q));

			std::push_heap(begin, end);
			std::pop_heap(begin, end);
		}

		return group.ScalarMultiply(last->base, last->exponent);
	}
}

struct WindowSlider
{
	/**
	 * @brief Initializes a WindowSlider for managing sliding windows over an exponent.
	 *
	 * Constructs a WindowSlider to facilitate windowed exponentiation or multiplication by segmenting the given exponent into windows of configurable size. The window size is determined automatically based on the bit length of the exponent if not specified.
	 *
	 * @param expIn The exponent to be processed.
	 * @param fastNegate Enables optimized handling of negative windows if true.
	 * @param windowSizeIn Optional window size; if zero, an optimal size is chosen based on the exponent's bit length.
	 */
	WindowSlider(const Integer &expIn, bool fastNegate, unsigned int windowSizeIn=0)
		: exp(expIn), windowModulus(Integer::One()), windowSize(windowSizeIn), windowBegin(0), expWindow(0)
		, fastNegate(fastNegate), negateNext(false), firstTime(true), finished(false)
	{
		if (windowSize == 0)
		{
			unsigned int expLen = exp.BitCount();
			windowSize = expLen <= 17 ? 1 : (expLen <= 24 ? 2 : (expLen <= 70 ? 3 : (expLen <= 197 ? 4 : (expLen <= 539 ? 5 : (expLen <= 1434 ? 6 : 7)))));
		}
		windowModulus <<= windowSize;
	}

	/**
	 * @brief Advances the exponent to the next nonzero window for windowed exponentiation.
	 *
	 * Updates internal state to locate the next window of bits in the exponent, skipping leading zeros, and prepares the window value for use in windowed multiplication or exponentiation. Handles fast negation if enabled.
	 */
	void FindNextWindow()
	{
		unsigned int expLen = exp.WordCount() * WORD_BITS;
		unsigned int skipCount = firstTime ? 0 : windowSize;
		firstTime = false;
		while (!exp.GetBit(skipCount))
		{
			if (skipCount >= expLen)
			{
				finished = true;
				return;
			}
			skipCount++;
		}

		exp >>= skipCount;
		windowBegin += skipCount;
		expWindow = word32(exp % (word(1) << windowSize));

		if (fastNegate && exp.GetBit(windowSize))
		{
			negateNext = true;
			expWindow = (word32(1) << windowSize) - expWindow;
			exp += windowModulus;
		}
		else
			negateNext = false;
	}

	Integer exp, windowModulus;
	unsigned int windowSize, windowBegin;
	word32 expWindow;
	bool fastNegate, negateNext, firstTime, finished;
};

template <class T>
/**
 * @brief Computes multiple scalar multiplications of a base element by different exponents simultaneously.
 *
 * For each exponent in the input array, calculates the scalar multiplication of the base element by that exponent and stores the result in the corresponding position of the results array. Uses a windowed exponentiation technique with bucket accumulation for efficiency.
 *
 * @param results Pointer to an array where each computed scalar multiplication will be stored.
 * @param base The group element to be multiplied by each exponent.
 * @param expBegin Pointer to the beginning of an array of exponents.
 * @param expCount The number of exponents (and results) to compute.
 */
void AbstractGroup<T>::SimultaneousMultiply(T *results, const T &base, const Integer *expBegin, unsigned int expCount) const
{
	std::vector<std::vector<Element> > buckets(expCount);
	std::vector<WindowSlider> exponents;
	exponents.reserve(expCount);
	unsigned int i;

	for (i=0; expBegin && i<expCount; i++)
	{
		CRYPTOPP_ASSERT(expBegin->NotNegative());
		exponents.push_back(WindowSlider(*expBegin++, InversionIsFast(), 0));
		exponents[i].FindNextWindow();
		buckets[i].resize(((size_t) 1) << (exponents[i].windowSize-1), Identity());
	}

	unsigned int expBitPosition = 0;
	Element g = base;
	bool notDone = true;

	while (notDone)
	{
		notDone = false;
		for (i=0; i<expCount; i++)
		{
			if (!exponents[i].finished && expBitPosition == exponents[i].windowBegin)
			{
				Element &bucket = buckets[i][exponents[i].expWindow/2];
				if (exponents[i].negateNext)
					Accumulate(bucket, Inverse(g));
				else
					Accumulate(bucket, g);
				exponents[i].FindNextWindow();
			}
			notDone = notDone || !exponents[i].finished;
		}

		if (notDone)
		{
			g = Double(g);
			expBitPosition++;
		}
	}

	for (i=0; i<expCount; i++)
	{
		Element &r = *results++;
		r = buckets[i][buckets[i].size()-1];
		if (buckets[i].size() > 1)
		{
			for (int j = (int)buckets[i].size()-2; j >= 1; j--)
			{
				Accumulate(buckets[i][j], buckets[i][j+1]);
				Accumulate(r, buckets[i][j]);
			}
			Accumulate(buckets[i][0], buckets[i][1]);
			r = Add(Double(r), buckets[i][0]);
		}
	}
}

template <class T> /**
 * @brief Computes the exponentiation of a ring element by an integer exponent.
 *
 * Raises the given base element to the specified exponent using simultaneous exponentiation.
 *
 * @param base The element to be exponentiated.
 * @param exponent The exponent to raise the base to.
 * @return The result of base raised to the given exponent.
 */
T AbstractRing<T>::Exponentiate(const Element &base, const Integer &exponent) const
{
	Element result;
	SimultaneousExponentiate(&result, base, &exponent, 1);
	return result;
}

template <class T> /**
 * @brief Computes the simultaneous exponentiation of two elements with given exponents.
 *
 * Returns the product of x raised to e1 and y raised to e2, i.e., x^e1 * y^e2, using an efficient cascade method in the ring's multiplicative group.
 *
 * @param x First base element.
 * @param e1 Exponent for the first base.
 * @param y Second base element.
 * @param e2 Exponent for the second base.
 * @return T The result of x^e1 * y^e2.
 */
T AbstractRing<T>::CascadeExponentiate(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const
{
	return MultiplicativeGroup().AbstractGroup<T>::CascadeScalarMultiply(x, e1, y, e2);
}

template <class Element, class Iterator> /**
 * @brief Performs cascade exponentiation for multiple base-exponent pairs in a ring.
 *
 * Computes the product of multiple elements each raised to their respective exponents, using the ring's multiplicative group for efficient evaluation.
 *
 * @tparam Element The type of the ring element.
 * @tparam Iterator An iterator type over pairs of (Element, exponent).
 * @param ring The abstract ring in which exponentiation is performed.
 * @param begin Iterator to the beginning of the base-exponent pairs.
 * @param end Iterator to the end of the base-exponent pairs.
 * @return Element The result of the cascade exponentiation.
 */
Element GeneralCascadeExponentiation(const AbstractRing<Element> &ring, Iterator begin, Iterator end)
{
	return GeneralCascadeMultiplication<Element>(ring.MultiplicativeGroup(), begin, end);
}

template <class T>
/**
 * @brief Computes multiple exponentiations of a base element with different exponents simultaneously.
 *
 * Calculates `results[i] = base ^ exponents[i]` for each exponent in the array, using the ring's multiplicative group for efficient simultaneous exponentiation.
 */
void AbstractRing<T>::SimultaneousExponentiate(T *results, const T &base, const Integer *exponents, unsigned int expCount) const
{
	MultiplicativeGroup().AbstractGroup<T>::SimultaneousMultiply(results, base, exponents, expCount);
}

NAMESPACE_END

#endif
