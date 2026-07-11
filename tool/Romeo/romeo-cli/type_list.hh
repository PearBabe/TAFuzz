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

#ifndef ROMEO_TYPE_LIST_HH
#define ROMEO_TYPE_LIST_HH

#include <type.hh>
#include <integer_type.hh>

namespace romeo
{
    class TypeList
    {
        private:
            std::vector<const Type*> types;
            std::map<const std::string, const Type*> mapping;

        public:
            TypeList();
            ~TypeList();

            void add_type(const Type*);
            void add_alias(const std::string&, const std::string&);
            const Type* lookup_type(const std::string&) const;
            const Type* type_by_id(const unsigned) const;
            unsigned ntypes() const;

            const Type* integer() const;
            const Type* integer8() const;
            const Type* integer16() const;
            const Type* integer32() const;
            const Type* integer64() const;
            const Type* uinteger8() const;
            const Type* uinteger16() const;
            const Type* uinteger32() const;
            const Type* uinteger64() const;
            const Type* real() const;
            const Type* void_type() const;
    };
}

#endif

