/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to perform
parametric model checking on timed and hybrid systems.

This software is governed by the CeCILL license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

The fact that you are presently reading this means that you have had
knowledge of the CeCILL license and that you accept its terms. */

#ifndef ROMEO_VALUATION_HH
#define ROMEO_VALUATION_HH

#include <checked_types.hh>

#ifdef NO_STD_BYTE
namespace std
{
    typedef uint8_t byte;
}
#endif

namespace romeo
{
    enum relation_type { EQUAL, GREATER, LESS, MERGEABLE, NONE };

#define ROMEO_BSIZE 32
    const unsigned ROMEO_BVSIZE = ROMEO_BSIZE - 1;

#if ROMEO_BSIZE == 32
    #define ROMEO_MAX_BVALUE ((int32_t) 0x7FFFFFFF)
    #define ROMEO_MIN_BVALUE ((int32_t) 0x80000000)
    typedef int32_t bvalue;
    typedef int64_t bextvalue;
    typedef int32_t cvalue; // Polyhedra coeff reduction
#else
    #define ROMEO_MAX_BVALUE ((int64_t) 0x7FFFFFFFFFFFFFFF)
    #define ROMEO_MIN_BVALUE ((int64_t) 0x8000000000000000)
    typedef int64_t bvalue;
    typedef __int128_t bextvalue;
    typedef int64_t cvalue; // Polyhedra coeff reduction
#endif


    //typedef CheckedInteger value;
    typedef int64_t value;
    typedef float fvalue; 

    typedef std::byte* valuation;
    typedef const std::byte* const const_valuation;

    relation_type compare(const void*, const void*, const unsigned);

    enum rv_type { RV_INT, RV_REAL };


    cvalue gcd(cvalue, cvalue);
}

#endif

