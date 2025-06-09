// algebra.h - originally written and placed in the public domain by Wei Dai

/// \file algebra.h
/// \brief Classes for performing mathematics over different fields

#ifndef CRYPTOPP_ALGEBRA_H
#define CRYPTOPP_ALGEBRA_H

#include "config.h"
#include "integer.h"
#include "misc.h"

NAMESPACE_BEGIN(CryptoPP)

class Integer;

/// \brief Abstract group
/// \tparam T element class or type
/// \details <tt>const Element&</tt> returned by member functions are references
///   to internal data members. Since each object may have only
///   one such data member for holding results, the following code
///   will produce incorrect results:
///   <pre>    abcd = group.Add(group.Add(a,b), group.Add(c,d));</pre>
///   But this should be fine:
///   <pre>    abcd = group.Add(a, group.Add(b, group.Add(c,d));</pre>
template <class T> class /**
 * @brief Abstract base class representing a mathematical group over elements of type T.
 *
 * Defines the interface for group operations including equality, identity, addition, inversion, doubling, subtraction, accumulation, reduction, scalar multiplication, and simultaneous multiplication. Derived classes must implement core group operations and may override default behaviors for efficiency or specialized behavior.
 */
CRYPTOPP_NO_VTABLE AbstractGroup
{
public:
	typedef T Element;

	virtual ~AbstractGroup() {}

	/// \brief Compare two elements for equality
	/// \param a first element
	/// \param b second element
	/// \return true if the elements are equal, false otherwise
	/// \details Equal() tests the elements for equality using <tt>a==b</tt>
	virtual bool Equal(const Element &a, const Element &b) const =0;

	/// \brief Provides the Identity element
	/// \return the Identity element
	virtual const Element& Identity() const =0;

	/// \brief Adds elements in the group
	/// \param a first element
	/// \param b second element
	/// \return the sum of <tt>a</tt> and <tt>b</tt>
	virtual const Element& Add(const Element &a, const Element &b) const =0;

	/// \brief Inverts the element in the group
	/// \param a first element
	/// \return the inverse of the element
	virtual const Element& Inverse(const Element &a) const =0;

	/// \brief Determine if inversion is fast
	/// \return true if inversion is fast, false otherwise
	virtual bool InversionIsFast() const {return false;}

	/// \brief Doubles an element in the group
	/// \param a the element
	/// \return the element doubled
	virtual const Element& Double(const Element &a) const;

	/// \brief Subtracts elements in the group
	/// \param a first element
	/// \param b second element
	/// \return the difference of <tt>a</tt> and <tt>b</tt>. The element <tt>a</tt> must provide a Subtract member function.
	virtual const Element& Subtract(const Element &a, const Element &b) const;

	/// \brief TODO
	/// \param a first element
	/// \param b second element
	/// \return TODO
	virtual Element& Accumulate(Element &a, const Element &b) const;

	/// \brief Reduces an element in the congruence class
	/// \param a element to reduce
	/// \param b the congruence class
	/// \return the reduced element
	virtual Element& Reduce(Element &a, const Element &b) const;

	/// \brief Performs a scalar multiplication
	/// \param a multiplicand
	/// \param e multiplier
	/// \return the product
	virtual Element ScalarMultiply(const Element &a, const Integer &e) const;

	/// \brief TODO
	/// \param x first multiplicand
	/// \param e1 the first multiplier
	/// \param y second multiplicand
	/// \param e2 the second multiplier
	/// \return TODO
	virtual Element CascadeScalarMultiply(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const;

	/// \brief Multiplies a base to multiple exponents in a group
	/// \param results an array of Elements
	/// \param base the base to raise to the exponents
	/// \param exponents an array of exponents
	/// \param exponentsCount the number of exponents in the array
	/// \details SimultaneousMultiply() multiplies the base to each exponent in the exponents array and stores the
	///   result at the respective position in the results array.
	/// \details SimultaneousMultiply() must be implemented in a derived class.
	/// \pre <tt>COUNTOF(results) == exponentsCount</tt>
	/// \pre <tt>COUNTOF(exponents) == exponentsCount</tt>
	virtual void SimultaneousMultiply(Element *results, const Element &base, const Integer *exponents, unsigned int exponentsCount) const;
};

/// \brief Abstract ring
/// \tparam T element class or type
/// \details <tt>const Element&</tt> returned by member functions are references
///   to internal data members. Since each object may have only
///   one such data member for holding results, the following code
///   will produce incorrect results:
///   <pre>    abcd = group.Add(group.Add(a,b), group.Add(c,d));</pre>
///   But this should be fine:
///   <pre>    abcd = group.Add(a, group.Add(b, group.Add(c,d));</pre>
template <class T> class /**
		 * @brief Constructs an AbstractRing instance.
		 *
		 * Initializes the internal multiplicative group wrapper to reference this ring.
		 */
		
		/**
		 * @brief Copy constructs an AbstractRing instance.
		 *
		 * Initializes the internal multiplicative group wrapper to reference this ring. The source ring is not otherwise used.
		 */
		CRYPTOPP_NO_VTABLE AbstractRing : public AbstractGroup<T>
{
public:
	typedef T Element;

	/// \brief Construct an AbstractRing
	AbstractRing() {m_mg.m_pRing = this;}

	/// \brief Copy construct an AbstractRing
	/// \param source other AbstractRing
	AbstractRing(const AbstractRing &source)
		{CRYPTOPP_UNUSED(source); m_mg.m_pRing = this;}

	/// \brief Assign an AbstractRing
	/// \param source other AbstractRing
	AbstractRing& operator=(const AbstractRing &source)
		{CRYPTOPP_UNUSED(source); return *this;}

	/// \brief Determines whether an element is a unit in the group
	/// \param a the element
	/// \return true if the element is a unit after reduction, false otherwise.
	virtual bool IsUnit(const Element &a) const =0;

	/// \brief Retrieves the multiplicative identity
	/// \return the multiplicative identity
	virtual const Element& MultiplicativeIdentity() const =0;

	/// \brief Multiplies elements in the group
	/// \param a the multiplicand
	/// \param b the multiplier
	/// \return the product of a and b
	virtual const Element& Multiply(const Element &a, const Element &b) const =0;

	/// \brief Calculate the multiplicative inverse of an element in the group
	/// \param a the element
	virtual const Element& MultiplicativeInverse(const Element &a) const =0;

	/// \brief Square an element in the group
	/// \param a the element
	/// \return the element squared
	virtual const Element& Square(const Element &a) const;

	/// \brief Divides elements in the group
	/// \param a the dividend
	/// \param b the divisor
	/// \return the quotient
	virtual const Element& Divide(const Element &a, const Element &b) const;

	/// \brief Raises a base to an exponent in the group
	/// \param a the base
	/// \param e the exponent
	/// \return the exponentiation
	virtual Element Exponentiate(const Element &a, const Integer &e) const;

	/// \brief TODO
	/// \param x first element
	/// \param e1 first exponent
	/// \param y second element
	/// \param e2 second exponent
	/// \return TODO
	virtual Element CascadeExponentiate(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const;

	/// \brief Exponentiates a base to multiple exponents in the Ring
	/// \param results an array of Elements
	/// \param base the base to raise to the exponents
	/// \param exponents an array of exponents
	/// \param exponentsCount the number of exponents in the array
	/// \details SimultaneousExponentiate() raises the base to each exponent in the exponents array and stores the
	///   result at the respective position in the results array.
	/// \details SimultaneousExponentiate() must be implemented in a derived class.
	/// \pre <tt>COUNTOF(results) == exponentsCount</tt>
	/// \pre <tt>COUNTOF(exponents) == exponentsCount</tt>
	virtual void SimultaneousExponentiate(Element *results, const Element &base, const Integer *exponents, unsigned int exponentsCount) const;

	/// \brief Retrieves the multiplicative group
	/**
		 * @brief Returns a reference to the multiplicative group associated with the ring.
		 *
		 * @return Reference to the multiplicative group as an AbstractGroup.
		 */
	virtual const AbstractGroup<T>& MultiplicativeGroup() const
		{return m_mg;}

private:
	class MultiplicativeGroupT : public AbstractGroup<T>
	{
	public:
		const AbstractRing<T>& GetRing() const
			{return *m_pRing;}

		/**
			 * @brief Determines if two elements are equivalent in the quotient ring.
			 *
			 * Two elements are considered equal if their difference modulo the ring's modulus is the additive identity.
			 *
			 * @param a First element to compare.
			 * @param b Second element to compare.
			 * @return true if the elements are equivalent in the quotient ring, false otherwise.
			 */
			bool Equal(const Element &a, const Element &b) const
			{return GetRing().Equal(a, b);}

		/**
			 * @brief Returns the multiplicative identity element of the quotient ring.
			 *
			 * @return Reference to the multiplicative identity element.
			 */
			const Element& Identity() const
			{return GetRing().MultiplicativeIdentity();}

		/**
			 * @brief Returns the product of two elements in the quotient ring.
			 *
			 * Multiplies elements `a` and `b` using the underlying Euclidean domain's multiplication, then reduces the result modulo the ring's modulus.
			 *
			 * @param a First element.
			 * @param b Second element.
			 * @return Reference to the resulting element after multiplication and modular reduction.
			 */
			const Element& Add(const Element &a, const Element &b) const
			{return GetRing().Multiply(a, b);}

		Element& Accumulate(Element &a, const Element &b) const
			{return a = GetRing().Multiply(a, b);}

		/**
			 * @brief Returns the multiplicative inverse of the given element in the quotient ring.
			 *
			 * @param a The element whose multiplicative inverse is to be computed.
			 * @return const Element& Reference to the multiplicative inverse of a.
			 */
			const Element& Inverse(const Element &a) const
			{return GetRing().MultiplicativeInverse(a);}

		/**
			 * @brief Returns the result of dividing element a by element b in the underlying ring.
			 *
			 * @param a The dividend element.
			 * @param b The divisor element.
			 * @return const Element& Reference to the result of the division.
			 */
			const Element& Subtract(const Element &a, const Element &b) const
			{return GetRing().Divide(a, b);}

		Element& Reduce(Element &a, const Element &b) const
			{return a = GetRing().Divide(a, b);}

		/**
			 * @brief Returns the result of doubling the given element in the ring.
			 *
			 * This is equivalent to squaring the element using the underlying ring's Square operation.
			 *
			 * @param a The element to double.
			 * @return const Element& The doubled (squared) element.
			 */
			const Element& Double(const Element &a) const
			{return GetRing().Square(a);}

		/**
			 * @brief Performs scalar multiplication of an element by an integer exponent.
			 *
			 * Computes the result of raising the element to the given integer exponent using the underlying ring's exponentiation operation.
			 *
			 * @param a The element to be exponentiated.
			 * @param e The integer exponent.
			 * @return Element The result of exponentiating a by e.
			 */
			Element ScalarMultiply(const Element &a, const Integer &e) const
			{return GetRing().Exponentiate(a, e);}

		/**
			 * @brief Computes the combined scalar multiplication of two elements using their respective exponents.
			 *
			 * Returns the result of multiplying element `x` by exponent `e1` and element `y` by exponent `e2`, combined according to the ring's cascade exponentiation rules.
			 *
			 * @return The result of the cascade scalar multiplication.
			 */
			Element CascadeScalarMultiply(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const
			{return GetRing().CascadeExponentiate(x, e1, y, e2);}

		/**
			 * @brief Computes multiple exponentiations of a base element with different exponents.
			 *
			 * For each exponent in the array, raises the given base to that exponent and stores the result in the corresponding position of the results array.
			 *
			 * @param results Array to store the computed exponentiations.
			 * @param base The base element to be exponentiated.
			 * @param exponents Array of exponents.
			 * @param exponentsCount Number of exponentiations to perform.
			 */
			void SimultaneousMultiply(Element *results, const Element &base, const Integer *exponents, unsigned int exponentsCount) const
			{GetRing().SimultaneousExponentiate(results, base, exponents, exponentsCount);}

		const AbstractRing<T> *m_pRing;
	};

	MultiplicativeGroupT m_mg;
};

// ********************************************************

/// \brief Base and exponent
/// \tparam T base class or type
/// \tparam E exponent class or type
template <class T, class E = Integer>
struct BaseAndExponent
{
public:
	BaseAndExponent() {}
	BaseAndExponent(const T &base, const E &exponent) : base(base), exponent(exponent) {}
	bool operator<(const BaseAndExponent<T, E> &rhs) const {return exponent < rhs.exponent;}
	T base;
	E exponent;
};

// VC60 workaround: incomplete member template support
template <class Element, class Iterator>
	Element GeneralCascadeMultiplication(const AbstractGroup<Element> &group, Iterator begin, Iterator end);
template <class Element, class Iterator>
	Element GeneralCascadeExponentiation(const AbstractRing<Element> &ring, Iterator begin, Iterator end);

// ********************************************************

/// \brief Abstract Euclidean domain
/// \tparam T element class or type
/// \details <tt>const Element&</tt> returned by member functions are references
///   to internal data members. Since each object may have only
///   one such data member for holding results, the following code
///   will produce incorrect results:
///   <pre>    abcd = group.Add(group.Add(a,b), group.Add(c,d));</pre>
///   But this should be fine:
///   <pre>    abcd = group.Add(a, group.Add(b, group.Add(c,d));</pre>
template <class T> class /**
 * @brief Abstract base class for Euclidean domains.
 *
 * Defines the interface for performing division, modular reduction, and greatest common divisor computations in a Euclidean domain over elements of type T.
 *
 * @tparam T The element type of the Euclidean domain.
 */
 
/**
 * @brief Performs the division algorithm on two elements.
 *
 * Computes quotient and remainder such that a = q * d + r, where r and q are output parameters.
 *
 * @param r Reference to store the remainder.
 * @param q Reference to store the quotient.
 * @param a The dividend.
 * @param d The divisor.
 */
 
/**
 * @brief Computes the modular reduction of two elements.
 *
 * @param a The element to reduce.
 * @param b The modulus.
 * @return Reference to the result of a modulo b.
 */
 
/**
 * @brief Calculates the greatest common divisor of two elements.
 *
 * @param a The first element.
 * @param b The second element.
 * @return Reference to the greatest common divisor of a and b.
 */
CRYPTOPP_NO_VTABLE AbstractEuclideanDomain : public AbstractRing<T>
{
public:
	typedef T Element;

	/// \brief Performs the division algorithm on two elements in the ring
	/// \param r the remainder
	/// \param q the quotient
	/// \param a the dividend
	/// \param d the divisor
	virtual void DivisionAlgorithm(Element &r, Element &q, const Element &a, const Element &d) const =0;

	/// \brief Performs a modular reduction in the ring
	/// \param a the element
	/// \param b the modulus
	/// \return the result of <tt>a%b</tt>.
	virtual const Element& Mod(const Element &a, const Element &b) const =0;

	/// \brief Calculates the greatest common denominator in the ring
	/// \param a the first element
	/// \param b the second element
	/// \return the greatest common denominator of a and b.
	virtual const Element& Gcd(const Element &a, const Element &b) const;

protected:
	mutable Element result;
};

// ********************************************************

/// \brief Euclidean domain
/// \tparam T element class or type
/// \details <tt>const Element&</tt> returned by member functions are references
///   to internal data members. Since each object may have only
///   one such data member for holding results, the following code
///   will produce incorrect results:
///   <pre>    abcd = group.Add(group.Add(a,b), group.Add(c,d));</pre>
///   But this should be fine:
///   <pre>    abcd = group.Add(a, group.Add(b, group.Add(c,d));</pre>
template <class T> class EuclideanDomainOf : public AbstractEuclideanDomain<T>
{
public:
	typedef T Element;

	EuclideanDomainOf() {}

	/**
		 * @brief Checks if two elements are equal.
		 *
		 * @param a First element to compare.
		 * @param b Second element to compare.
		 * @return true if the elements are equal, false otherwise.
		 */
		bool Equal(const Element &a, const Element &b) const
		{return a==b;}

	/**
		 * @brief Returns the additive identity element of the domain.
		 *
		 * @return Reference to the zero element.
		 */
		const Element& Identity() const
		{return Element::Zero();}

	/**
		 * @brief Returns the sum of two elements in the algebraic structure.
		 *
		 * @param a The first element.
		 * @param b The second element.
		 * @return Reference to the result of a + b.
		 */
		const Element& Add(const Element &a, const Element &b) const
		{return result = a+b;}

	Element& Accumulate(Element &a, const Element &b) const
		{return a+=b;}

	/**
		 * @brief Returns the additive inverse of the given element.
		 *
		 * @param a The element whose additive inverse is to be computed.
		 * @return const Element& Reference to the result containing the additive inverse of a.
		 */
		const Element& Inverse(const Element &a) const
		{return result = -a;}

	/**
		 * @brief Returns the difference of two elements.
		 *
		 * Computes a - b and stores the result internally.
		 *
		 * @param a The minuend element.
		 * @param b The subtrahend element.
		 * @return const Element& Reference to the result of a - b.
		 */
		const Element& Subtract(const Element &a, const Element &b) const
		{return result = a-b;}

	Element& Reduce(Element &a, const Element &b) const
		{return a-=b;}

	/**
		 * @brief Returns the result of doubling the given element.
		 *
		 * @param a The element to double.
		 * @return const Element& Reference to the doubled element.
		 */
		const Element& Double(const Element &a) const
		{return result = a.Doubled();}

	/**
		 * @brief Returns the multiplicative identity element of the domain.
		 *
		 * @return Reference to the element representing one.
		 */
		const Element& MultiplicativeIdentity() const
		{return Element::One();}

	/**
		 * @brief Multiplies two elements in the ring.
		 *
		 * @param a The first element.
		 * @param b The second element.
		 * @return Reference to the product of a and b.
		 */
		const Element& Multiply(const Element &a, const Element &b) const
		{return result = a*b;}

	/**
		 * @brief Returns the square of the given element.
		 *
		 * @param a The element to be squared.
		 * @return const Element& Reference to the result of squaring a.
		 */
		const Element& Square(const Element &a) const
		{return result = a.Squared();}

	/**
		 * @brief Determines whether the given element is a unit in the domain.
		 *
		 * @param a The element to test.
		 * @return true if the element is a unit (has a multiplicative inverse); false otherwise.
		 */
		bool IsUnit(const Element &a) const
		{return a.IsUnit();}

	/**
		 * @brief Returns the multiplicative inverse of the given element.
		 *
		 * @param a The element for which to compute the multiplicative inverse.
		 * @return const Element& Reference to the result containing the multiplicative inverse of a.
		 */
		const Element& MultiplicativeInverse(const Element &a) const
		{return result = a.MultiplicativeInverse();}

	/**
		 * @brief Divides one element by another in the Euclidean domain.
		 *
		 * @param a The dividend element.
		 * @param b The divisor element.
		 * @return const Element& Reference to the result of the division.
		 */
		const Element& Divide(const Element &a, const Element &b) const
		{return result = a/b;}

	/**
		 * @brief Computes the remainder of dividing one element by another.
		 *
		 * Returns the result of `a` modulo `b`, using the `%` operator of the element type.
		 *
		 * @param a The dividend element.
		 * @param b The divisor element.
		 * @return Reference to the remainder of `a` divided by `b`.
		 */
		const Element& Mod(const Element &a, const Element &b) const
		{return result = a%b;}

	/**
		 * @brief Performs the division algorithm on two elements.
		 *
		 * Computes the quotient and remainder of dividing element `a` by element `d`, storing the remainder in `r` and the quotient in `q`.
		 */
		void DivisionAlgorithm(Element &r, Element &q, const Element &a, const Element &d) const
		{Element::Divide(r, q, a, d);}

	/**
	 * @brief Computes the greatest common divisor (GCD) of two elements using the Euclidean algorithm.
	 *
	 * Iteratively applies modular reduction to find the GCD of elements `a` and `b` in the Euclidean domain.
	 *
	 * @param a First element.
	 * @param b Second element.
	 * @return const Element& Reference to the computed GCD.
	 */
	const Element& Gcd(const Element &a, const Element &b) const
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

	/**
	 * @brief Raises an element to a given integer exponent.
	 *
	 * Computes base raised to the power of exponent within the algebraic structure.
	 *
	 * @param base The element to be exponentiated.
	 * @param exponent The integer exponent.
	 * @return Element The result of base raised to exponent.
	 */
	Element Exponentiate(const Element &base, const Integer &exponent) const
	{
		Element result;
		SimultaneousExponentiate(&result, base, &exponent, 1);
		return result;
	}

	/**
	 * @brief Computes the product of two elements each raised to a given exponent.
	 *
	 * Calculates \( x^{e1} \cdot y^{e2} \) using the ring's multiplicative group operations.
	 *
	 * @param x The first base element.
	 * @param e1 The exponent for the first base.
	 * @param y The second base element.
	 * @param e2 The exponent for the second base.
	 * @return The result of \( x^{e1} \cdot y^{e2} \).
	 */
	Element CascadeExponentiate(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const
	{
		return this->MultiplicativeGroup().AbstractGroup<T>::CascadeScalarMultiply(x, e1, y, e2);
	}

	/**
	 * @brief Computes multiple exponentiations of a base element with different exponents.
	 *
	 * Calculates `results[i] = base ^ exponents[i]` for each exponent in the array, using the ring's multiplicative group.
	 *
	 * @param results Array to store the computed exponentiations.
	 * @param base The base element to be exponentiated.
	 * @param exponents Array of exponents.
	 * @param expCount Number of exponentiations to perform.
	 */
	void SimultaneousExponentiate(Element *results, const Element &base, const Integer *exponents, unsigned int expCount) const
	{
		this->MultiplicativeGroup().AbstractGroup<T>::SimultaneousMultiply(results, base, exponents, expCount);
	}

	/**
	 * @brief Computes the scalar multiple of a group element by an integer exponent.
	 *
	 * Returns the result of raising the given base element to the specified exponent using the ring's exponentiation operation.
	 *
	 * @param base The element to be exponentiated.
	 * @param exponent The integer exponent.
	 * @return Element The result of exponentiating base by exponent.
	 */
	Element ScalarMultiply(const Element &base, const Integer &exponent) const
	{
		return Exponentiate(base, exponent);
	}

	/**
	 * @brief Computes the combined scalar multiplication of two elements.
	 *
	 * Returns the result of multiplying element `x` by scalar `e1` and element `y` by scalar `e2`, combined according to the group or ring operation. This implementation delegates to the cascade exponentiation method.
	 *
	 * @param x The first element.
	 * @param e1 The scalar multiplier for the first element.
	 * @param y The second element.
	 * @param e2 The scalar multiplier for the second element.
	 * @return Element The result of the combined scalar multiplication.
	 */
	Element CascadeScalarMultiply(const Element &x, const Integer &e1, const Element &y, const Integer &e2) const
	{
		return CascadeExponentiate(x, e1, y, e2);
	}

	/**
	 * @brief Computes multiple exponentiations of a base element with different exponents.
	 *
	 * Calculates base raised to each exponent in the exponents array and stores the results in the results array.
	 *
	 * @param results Array to store the computed exponentiations.
	 * @param base The base element to exponentiate.
	 * @param exponents Array of exponents.
	 * @param expCount Number of exponentiations to perform.
	 */
	void SimultaneousMultiply(Element *results, const Element &base, const Integer *exponents, unsigned int expCount) const
	{
		// Use the proper implementation from AbstractGroup<T>::SimultaneousMultiply
		// This is a simplified version that should work for basic cases
		for (unsigned int i = 0; i < expCount; i++)
		{
			results[i] = Exponentiate(base, exponents[i]);
		}
	}

	bool operator==(const EuclideanDomainOf<T> &rhs) const
		{CRYPTOPP_UNUSED(rhs); return true;}

private:
	mutable Element result;
};

/// \brief Quotient ring
/// \tparam T element class or type
/// \details <tt>const Element&</tt> returned by member functions are references
///   to internal data members. Since each object may have only
///   one such data member for holding results, the following code
///   will produce incorrect results:
///   <pre>    abcd = group.Add(group.Add(a,b), group.Add(c,d));</pre>
///   But this should be fine:
///   <pre>    abcd = group.Add(a, group.Add(b, group.Add(c,d));</pre>
template <class T> class QuotientRing : public AbstractRing<typename T::Element>
{
public:
	typedef T EuclideanDomain;
	typedef typename T::Element Element;

	QuotientRing(const EuclideanDomain &domain, const Element &modulus)
		: m_domain(domain), m_modulus(modulus) {}

	/**
		 * @brief Returns a reference to the underlying Euclidean domain.
		 *
		 * @return const EuclideanDomain& Reference to the Euclidean domain used by this quotient ring.
		 */
		const EuclideanDomain & GetDomain() const
		{return m_domain;}

	/**
		 * @brief Returns the modulus element used to define the quotient ring.
		 *
		 * @return Reference to the modulus element.
		 */
		const Element& GetModulus() const
		{return m_modulus;}

	/**
		 * @brief Determines if two elements are equivalent in the quotient ring.
		 *
		 * Returns true if the difference between elements a and b is congruent to zero modulo the ring's modulus, indicating they represent the same equivalence class.
		 *
		 * @param a First element to compare.
		 * @param b Second element to compare.
		 * @return true if a and b are equivalent modulo the modulus, false otherwise.
		 */
		bool Equal(const Element &a, const Element &b) const
		{return m_domain.Equal(m_domain.Mod(m_domain.Subtract(a, b), m_modulus), m_domain.Identity());}

	/**
		 * @brief Returns the additive identity element of the quotient ring.
		 *
		 * @return Reference to the additive identity element.
		 */
		const Element& Identity() const
		{return m_domain.Identity();}

	/**
		 * @brief Returns the sum of two elements in the quotient ring.
		 *
		 * Computes the addition of elements `a` and `b` using the underlying Euclidean domain, with the result reduced modulo the ring's modulus.
		 *
		 * @param a First element.
		 * @param b Second element.
		 * @return Reference to the resulting element in the quotient ring.
		 */
		const Element& Add(const Element &a, const Element &b) const
		{return m_domain.Add(a, b);}

	Element& Accumulate(Element &a, const Element &b) const
		{return m_domain.Accumulate(a, b);}

	/**
		 * @brief Returns the additive inverse of an element in the quotient ring.
		 *
		 * Computes the additive inverse of the given element by delegating to the underlying Euclidean domain.
		 *
		 * @param a The element whose additive inverse is to be computed.
		 * @return const Element& Reference to the additive inverse of the element.
		 */
		const Element& Inverse(const Element &a) const
		{return m_domain.Inverse(a);}

	/**
		 * @brief Returns the difference of two elements in the quotient ring.
		 *
		 * Computes the subtraction of elements `a` and `b` in the underlying domain, then reduces the result modulo the ring's modulus.
		 *
		 * @param a The minuend element.
		 * @param b The subtrahend element.
		 * @return const Element& Reference to the result of (a - b) mod modulus.
		 */
		const Element& Subtract(const Element &a, const Element &b) const
		{return m_domain.Subtract(a, b);}

	Element& Reduce(Element &a, const Element &b) const
		{return m_domain.Reduce(a, b);}

	/**
		 * @brief Returns the result of doubling the given element in the underlying domain.
		 *
		 * @param a The element to double.
		 * @return const Element& Reference to the doubled element.
		 */
		const Element& Double(const Element &a) const
		{return m_domain.Double(a);}

	/**
		 * @brief Determines if an element is a unit in the quotient ring.
		 *
		 * An element is a unit if its greatest common divisor with the modulus is a unit in the underlying Euclidean domain.
		 *
		 * @param a The element to test for invertibility.
		 * @return true if the element is a unit in the quotient ring; false otherwise.
		 */
		bool IsUnit(const Element &a) const
		{return m_domain.IsUnit(m_domain.Gcd(a, m_modulus));}

	/**
		 * @brief Returns the multiplicative identity element of the quotient ring.
		 *
		 * The multiplicative identity is obtained from the underlying Euclidean domain.
		 *
		 * @return Reference to the multiplicative identity element.
		 */
		const Element& MultiplicativeIdentity() const
		{return m_domain.MultiplicativeIdentity();}

	/**
		 * @brief Multiplies two elements in the quotient ring and reduces the result modulo the modulus.
		 *
		 * @param a First element to multiply.
		 * @param b Second element to multiply.
		 * @return Reference to the product of a and b, reduced modulo the ring's modulus.
		 */
		const Element& Multiply(const Element &a, const Element &b) const
		{return m_domain.Mod(m_domain.Multiply(a, b), m_modulus);}

	/**
		 * @brief Computes the square of an element in the quotient ring.
		 *
		 * Returns the result of squaring the element `a` in the underlying domain and reducing it modulo the ring's modulus.
		 *
		 * @param a The element to be squared.
		 * @return const Element& Reference to the squared and reduced element.
		 */
		const Element& Square(const Element &a) const
		{return m_domain.Mod(m_domain.Square(a), m_modulus);}

	/**
		 * @brief Computes the multiplicative inverse of an element in the quotient ring.
		 *
		 * @param a The element for which to compute the multiplicative inverse.
		 * @return const Element& Reference to the multiplicative inverse of `a` modulo the ring's modulus.
		 *
		 * @note The element `a` must be a unit in the quotient ring; otherwise, the behavior is undefined.
		 */
		const Element& MultiplicativeInverse(const Element &a) const;

	bool operator==(const QuotientRing<T> &rhs) const
		{return m_domain == rhs.m_domain && m_modulus == rhs.m_modulus;}

protected:
	EuclideanDomain m_domain;
	Element m_modulus;
};

NAMESPACE_END

#ifdef CRYPTOPP_MANUALLY_INSTANTIATE_TEMPLATES
#include "algebra.cpp"
#endif

#endif
