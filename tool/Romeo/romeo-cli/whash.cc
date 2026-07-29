/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2019)

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

#include <cstdint>
#include <whash.hh>

using namespace std;

// Implementation of the wee hash function from the Cormen et al 
// Introduction to algorithms (4th ed.) book


// a should be odd and not too big
static const uint32_t a = 123;
static const uint32_t c = a + 128;
static const uint32_t r = 4;

namespace
{
    // VSState stores its discrete state in a packed byte buffer: it is neither
    // guaranteed to be uint64_t-aligned nor padded to a whole word.  Loading a
    // word through a cast therefore violates alignment/aliasing rules and, for
    // a partial final word, reads outside the buffer.  Spell out the byte order
    // to retain the historical x86-64 interpretation on every architecture.
    uint64_t load_little_endian(const std::byte msg[], const size_t n)
    {
        uint64_t result = 0;
        for (size_t i = 0; i < n; ++i)
        {
            result |= uint64_t(std::to_integer<uint8_t>(msg[i])) << (8 * i);
        }
        return result;
    }
}

#define WH(k, q, c, w, T) { const T x = k + q; \
                      for (uint32_t i = 0; i < r; i++) \
                      { \
                          const T f = (2*x + c) * x; \
                          q = (f >> w) + (f << w); \
                      } }

uint64_t romeo::whash(const uint64_t b, const std::byte msg[], const uint32_t n)
{
    uint64_t q = b;

    size_t i = 0;
    while (i + sizeof(uint64_t) < n)
    {
        const uint64_t k = load_little_endian(msg + i, sizeof(uint64_t));
        //const uint64_t x = k + q;
        //for (auto i = 0; i < r; i++)
        //{
        //    const uint64_t f = (2*x + c) * x;
        //    q = (f >> 32) + (f << 32);
        //}
        WH(k, q, c, 32, uint64_t)

        i = i + sizeof(uint64_t);
    }

    if (i < n)
    {
        const uint32_t t = n - i;
        // The final block contains between one and eight bytes.  Keep the
        // original length-dependent final-round constant, but zero-extend the
        // actual remaining bytes instead of reading an overlapping word.
        const uint64_t k = load_little_endian(msg + i, t);
        //const uint64_t x = k + q;
        //for (auto i = 0; i < r; i++)
        //{
        //    const uint64_t f = (2*x + a + 2*t) * x;
        //    q = (f >> 32) + (f << 32);
        //}
        WH(k, q, a + 2 * t, 32, uint64_t)
    }

    return q;
}

uint64_t romeo::whash64(const uint64_t b, const uint64_t k)
{
    uint64_t q = b;
    // const uint64_t x = k + q
    //for (auto i = 0; i < r; i++)
    //{
    //    const uint64_t f = (2*x + c) * x;
    //    q = (f >> 32) + (f << 32);
    //}
    WH(k, q, c, 32, uint64_t)

    return q;
}

uint32_t romeo::whash32(const uint32_t b, const uint32_t k)
{
    uint32_t q = b;
    //const uint32_t x = k + q;
    //for (auto i = 0; i < r; i++)
    //{
    //    const uint32_t f = (2*x + a + 64) * x;
    //    q = (f >> 16) + (f << 16);
    //}
    WH(k, q, a + 64, 16, uint32_t)

    return q;
}


