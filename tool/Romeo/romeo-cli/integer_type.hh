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

#ifndef ROMEO_INTEGER_TYPE_HH
#define ROMEO_INTEGER_TYPE_HH

#include <string>
#include <sstream>

#include <type.hh>
#include <rvalue.hh>
#include <stack_machine.hh>

namespace romeo
{
    template <typename T> class Integer: public Numeric
    {
        public:
            Integer(unsigned i, std::string s): Numeric(i, s, sizeof(T))
            {
            }
            
            Type* copy() const
            {
                return new Integer<T>(this->id, this->label);
            }
            
            void set(std::byte V[], const RValue& x) const
            {
                *((T*) V) = (T) x.contents().i; 
                *((std::byte*) (V + bsize)) = x.status() & ((std::byte) 1); 
            }
            
            std::string value_to_string(const std::byte V[]) const
            {
                return std::to_string(ivalue(V));
            }
            
            std::string value_to_string(memrep v) const
            {
                return std::to_string(v.i);
            }

            bool is_int() const
            {
                return true;
            }
            
            T ivalue(const std::byte V[]) const
            {
                return *((T*) V);
            }
            
            value to_int(const std::byte V[]) const
            {
                return (value) ivalue(V);
            }
            
            fvalue to_real(const std::byte V[]) const
            {
                return (fvalue) to_int(V);
            }

            value to_int(const memrep v) const
            {
                return v.i;
            }
            
            fvalue to_real(const memrep v) const
            {
                return v.f;
            }

            SProgram load_code() const
            {
                switch (sizeof(T))
                {
                    case 1:
                        return SProgram(StackMachine::LOAD8);
                        break;
                    case 2:
                        return SProgram(StackMachine::LOAD16);
                        break;
                    case 4:
                        return SProgram(StackMachine::LOAD32);
                        break;
                    case 8:
                        return SProgram(StackMachine::LOAD64);
                        break;
                    default:
                        return SProgram(StackMachine::LOAD64);
                        break;
                }
            }

            SProgram store_code() const
            {
                switch (sizeof(T))
                {
                    case 1:
                        return SProgram(StackMachine::STORE8);
                        break;
                    case 2:
                        return SProgram(StackMachine::STORE16);
                        break;
                    case 4:
                        return SProgram(StackMachine::STORE32);
                        break;
                    case 8:
                        return SProgram(StackMachine::STORE64);
                        break;
                    default:
                        return SProgram(StackMachine::STORE64);
                        break;
                }
            }

            SProgram rvalue_code(const RValue& x) const
            {
                SProgram L;
                L.add(StackMachine::PUSH);
                L.add(x.contents().i);

                return L;
            }

            virtual RValue deref(const std::byte* V) const
            {
                return RValue(*((T*) V), *(V + sizeof(T))); 
            }

    };
}

#endif

