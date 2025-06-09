// allocate.cpp - written and placed in the public domain by Jeffrey Walton

// The functions in allocate.h and allocate.cpp were originally in misc.h
// and misc.cpp. They were extracted in September 2019 to sidestep a circular
// dependency with misc.h and secblock.h.

#include "pch.h"
#include "config.h"

#ifndef CRYPTOPP_IMPORTS

#include "allocate.h"
#include "stdcpp.h"
#include "misc.h"
#include "trap.h"

// for memalign
#if defined(CRYPTOPP_MEMALIGN_AVAILABLE) || defined(CRYPTOPP_MM_MALLOC_AVAILABLE) || defined(QNX)
# include <malloc.h>
#endif
// for posix_memalign
#if defined(CRYPTOPP_POSIX_MEMALIGN_AVAILABLE)
# include <stdlib.h>
#endif

NAMESPACE_BEGIN(CryptoPP)

/**
 * @brief Invokes the current C++ new-handler or throws std::bad_alloc if none is set.
 *
 * This function retrieves the currently installed new-handler, restores it, and calls it to handle memory allocation failures. If no new-handler is set, it throws a std::bad_alloc exception.
 */
void CallNewHandler()
{
	std::new_handler newHandler = std::set_new_handler(NULLPTR);
	if (newHandler)
		std::set_new_handler(newHandler);

	if (newHandler)
		newHandler();
	else
		throw std::bad_alloc();
}

/**
 * @brief Allocates a block of memory aligned on a 16-byte boundary.
 *
 * Attempts to allocate a memory block of the specified size with 16-byte alignment, using platform-specific allocation methods when available. If allocation fails, repeatedly invokes the current new-handler until successful. The returned pointer is guaranteed to be 16-byte aligned.
 *
 * @param size Number of bytes to allocate.
 * @return Pointer to the allocated, 16-byte aligned memory block.
 */
void * AlignedAllocate(size_t size)
{
	byte *p;
#if defined(CRYPTOPP_MM_MALLOC_AVAILABLE)
	while ((p = (byte *)_mm_malloc(size, 16)) == NULLPTR)
#elif defined(CRYPTOPP_MEMALIGN_AVAILABLE)
	while ((p = (byte *)memalign(16, size)) == NULLPTR)
#elif defined(CRYPTOPP_MALLOC_ALIGNMENT_IS_16)
	while ((p = (byte *)malloc(size)) == NULLPTR)
#elif defined(CRYPTOPP_POSIX_MEMALIGN_AVAILABLE)
	while (posix_memalign(reinterpret_cast<void**>(&p), 16, size) != 0)
#else
	while ((p = (byte *)malloc(size + 16)) == NULLPTR)
#endif
		CallNewHandler();

#ifdef CRYPTOPP_NO_ALIGNED_ALLOC
	size_t adjustment = 16-((size_t)p%16);
	CRYPTOPP_ASSERT(adjustment > 0);
	p += adjustment;
	p[-1] = (byte)adjustment;
#endif

	// If this assert fires then there are problems that need
	// to be fixed. Please open a bug report.
	CRYPTOPP_ASSERT(IsAlignedOn(p, 16));
	return p;
}

/**
 * @brief Deallocates memory previously allocated with AlignedAllocate.
 *
 * Frees a memory block that was allocated with 16-byte alignment, using the appropriate platform-specific deallocation method. The pointer must not be null and must have been returned by AlignedAllocate.
 *
 * @param p Pointer to the aligned memory block to deallocate.
 */
void AlignedDeallocate(void *p)
{
	// Guard pointer due to crash on AIX when CRYPTOPP_NO_ALIGNED_ALLOC
	// is in effect. The guard was previously in place in SecBlock,
	// but it was removed at f4d68353ca7c as part of GH #875.
	CRYPTOPP_ASSERT(p);

	if (p != NULLPTR)
	{
#ifdef CRYPTOPP_MM_MALLOC_AVAILABLE
		_mm_free(p);
#elif defined(CRYPTOPP_NO_ALIGNED_ALLOC)
		p = (byte *)p - ((byte *)p)[-1];
		free(p);
#else
		free(p);
#endif
	}
}

/**
 * @brief Allocates a memory block of the specified size without alignment guarantees.
 *
 * Attempts to allocate a memory block of the given size using `malloc`. If allocation fails, repeatedly invokes the current new-handler until memory is successfully allocated.
 *
 * @param size Number of bytes to allocate.
 * @return Pointer to the allocated memory block, or never returns if allocation repeatedly fails and the new-handler throws.
 */
void * UnalignedAllocate(size_t size)
{
	void *p;
	while ((p = malloc(size)) == NULLPTR)
		CallNewHandler();
	return p;
}

/**
 * @brief Deallocates memory previously allocated without alignment requirements.
 *
 * Frees a memory block allocated by UnalignedAllocate.
 *
 * @param p Pointer to the memory block to deallocate.
 */
void UnalignedDeallocate(void *p)
{
	free(p);
}

NAMESPACE_END

#endif  // CRYPTOPP_IMPORTS
