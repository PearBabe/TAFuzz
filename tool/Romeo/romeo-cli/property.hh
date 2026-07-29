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

#ifndef ROMEO_PROPERTY_HH
#define ROMEO_PROPERTY_HH

#include <expression.hh>

namespace romeo
{
    // Forward declarations
    class PState;
    class PResult;
    class CTS;
    class Polyhedron;
    
    class Property: public Expression
    {
        private: 
            static int nprops;

        public:
            const int id;
            const Property* orig_prop;
        
        public:
            Property(int);

            virtual PResult* eval(const PState*) const = 0;
            virtual PResult* evaluate(const PState*) const;

            virtual bool has_time() const;
            virtual bool has_cost() const;
            virtual bool has_params() const;
            virtual bool uses_backward_mincost_zones() const;
                
            virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;

            virtual void prepare(CTS&) const; 

            virtual bool is_property() const;
            virtual bool is_simple() const;

            virtual PState* validate_observers(const PState*) const;
            virtual bool is_clock() const;
            virtual bool is_dprop() const;

            virtual std::list<VarSet> var_reads() const;

            virtual const Property* negation(CTS&) const;

    };
       
}

#endif
