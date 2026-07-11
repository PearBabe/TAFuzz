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

#ifndef ROMEO_RVALUE_HH
#define ROMEO_RVALUE_HH

#include <list>

#include <valuation.hh>

namespace romeo
{
    class CTS;
    class Type;
    class Variable;
    class SProgram;

    union memrep
    {
        value i;
        fvalue f;
        const std::byte* p;
    };

    class RValue
    {
        private:
            const Type& type;
            memrep v;
            std::byte s; // LSB: known, next: const for refs
 
        public:
            value to_int() const;
            fvalue to_real() const;
            value to_int_() const;
            fvalue to_real_() const;
            bool is_int() const;
            bool is_unknown() const;

            bool is_numeric() const;
 
            RValue(const fvalue, const std::byte s = ((std::byte) 1));

            RValue(const int8_t, const std::byte s = ((std::byte) 1));
            RValue(const uint8_t, const std::byte s = ((std::byte) 1));
            RValue(const int16_t, const std::byte s = ((std::byte) 1));
            RValue(const uint16_t, const std::byte s = ((std::byte) 1));
            RValue(const int32_t, const std::byte s = ((std::byte) 1));
            RValue(const uint32_t, const std::byte s = ((std::byte) 1));
            RValue(const int64_t, const std::byte s = ((std::byte) 1));
            RValue(const uint64_t, const std::byte s = ((std::byte) 1));

            RValue(const Type&, const int64_t, const std::byte s = ((std::byte) 1));

            RValue(const Type&, const std::byte*);
            RValue(const Type&); // An unknown value with a type

            //RValue(const RValue&);
 
            const Type& get_type() const;
            memrep contents() const;
            std::byte status() const;

            void set_contents(memrep);
            void set_status(std::byte);

            RValue deref() const;

            std::string to_string() const;
                
            
            std::list<RValue> split() const;
    };
}


#endif

