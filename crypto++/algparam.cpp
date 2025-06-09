// algparam.cpp - originally written and placed in the public domain by Wei Dai

#include "pch.h"

#ifndef CRYPTOPP_IMPORTS

#include "algparam.h"
#include "integer.h"

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Retrieves a value by name and type from two combined name-value pair collections.
 *
 * For the special name "ValueNames", returns true only if both collections provide the value. For all other names, returns true if either collection provides the value.
 *
 * @param name The name of the value to retrieve.
 * @param valueType The type information of the value to retrieve.
 * @param pValue Pointer to the location where the value should be stored if found.
 * @return true if the value is found according to the described logic; false otherwise.
 */
bool CombinedNameValuePairs::GetVoidValue(const char *name, const std::type_info &valueType, void *pValue) const
{
	if (strcmp(name, "ValueNames") == 0)
		return m_pairs1.GetVoidValue(name, valueType, pValue) && m_pairs2.GetVoidValue(name, valueType, pValue);
	else
		return m_pairs1.GetVoidValue(name, valueType, pValue) || m_pairs2.GetVoidValue(name, valueType, pValue);
}

/**
 * @brief Disabled assignment operator for AlgorithmParametersBase.
 *
 * This operator is intentionally disabled and will trigger an assertion failure if called.
 */
void AlgorithmParametersBase::operator=(const AlgorithmParametersBase &rhs)
{
	CRYPTOPP_UNUSED(rhs);
	CRYPTOPP_ASSERT(false);
}

/**
 * @brief Retrieves a parameter value by name and type from the parameter chain.
 *
 * If the requested name is "ValueNames", appends this parameter's name to the provided string and, if a next parameter exists, recursively collects names from the chain. If the name matches this parameter's name, assigns its value to the provided pointer and marks it as used. Otherwise, delegates the retrieval to the next parameter in the chain if present.
 *
 * @param name The name of the parameter to retrieve.
 * @param valueType The expected type of the value.
 * @param pValue Pointer to the location where the value should be stored.
 * @return true if the value was found and assigned; false otherwise.
 */
bool AlgorithmParametersBase::GetVoidValue(const char *name, const std::type_info &valueType, void *pValue) const
{
	if (strcmp(name, "ValueNames") == 0)
	{
		NameValuePairs::ThrowIfTypeMismatch(name, typeid(std::string), valueType);
		if (m_next.get())
		    m_next->GetVoidValue(name, valueType, pValue);
		(*reinterpret_cast<std::string *>(pValue) += m_name) += ";";
		return true;
	}
	else if (strcmp(name, m_name) == 0)
	{
		AssignValue(name, valueType, pValue);
		m_used = true;
		return true;
	}
	else if (m_next.get())
		return m_next->GetVoidValue(name, valueType, pValue);
	else
	    return false;
}

/**
 * @brief Constructs an AlgorithmParameters object with default settings.
 *
 * Initializes the object to throw if parameters are not used.
 */
AlgorithmParameters::AlgorithmParameters()
	: m_defaultThrowIfNotUsed(true)
{
}

/**
 * @brief Constructs an AlgorithmParameters object by copying the default throw flag and transferring ownership of the next parameter.
 *
 * Transfers the `m_defaultThrowIfNotUsed` flag from the source object and moves the ownership of the `m_next` parameter, leaving the source without a next parameter.
 *
 * @param x The AlgorithmParameters object to copy from.
 */
AlgorithmParameters::AlgorithmParameters(const AlgorithmParameters &x)
	: m_defaultThrowIfNotUsed(x.m_defaultThrowIfNotUsed)
{
	m_next.reset(const_cast<AlgorithmParameters &>(x).m_next.release());
}

/**
 * @brief Transfers ownership of the next parameter object from another AlgorithmParameters instance.
 *
 * After assignment, this instance takes ownership of the `m_next` pointer from the source, leaving the source with a null `m_next`.
 * @return Reference to this AlgorithmParameters instance.
 */
AlgorithmParameters & AlgorithmParameters::operator=(const AlgorithmParameters &x)
{
	m_next.reset(const_cast<AlgorithmParameters &>(x).m_next.release());
	return *this;
}

/**
 * @brief Attempts to retrieve a parameter value by name and type from the next parameter in the chain.
 *
 * Delegates the value retrieval to the next parameter object if it exists. Returns false if there is no next parameter.
 *
 * @param name The name of the parameter to retrieve.
 * @param valueType The type information of the value to retrieve.
 * @param pValue Pointer to the location where the value should be stored if found.
 * @return true if the value was successfully retrieved from the next parameter; false otherwise.
 */
bool AlgorithmParameters::GetVoidValue(const char *name, const std::type_info &valueType, void *pValue) const
{
	if (m_next.get())
		return m_next->GetVoidValue(name, valueType, pValue);
	else
		return false;
}

NAMESPACE_END

#endif
