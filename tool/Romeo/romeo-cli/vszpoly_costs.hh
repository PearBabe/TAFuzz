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

#ifndef ROMEO_CVSZPOLY_HH
#define ROMEO_CVSZPOLY_HH

#include <vector>
#include <string>

#include <vszpoly.hh>

#include <polyhedron.hh>

namespace romeo
{
    class LExpression;
    class Instruction;

    class CVSZPoly: public VSZPoly
    {
        protected:
            Avalue cmin;

        protected:
            virtual PWNode* successor(unsigned);

            // Constructors
            CVSZPoly(const Job&);
            CVSZPoly(const CVSZPoly&);
            CVSZPoly(const CVSZPoly&, unsigned);
            CVSZPoly(const CVSZPoly&, const Instruction&);

        public:
            // From PWNode
            virtual PWNode* copy(const Instruction*) const;
            
            // Create new symbolic states
            static CVSZPoly* init(const Job&);
      
            virtual std::string to_string() const;
            // Costs
            virtual Avalue min_cost() const;
        
            // Control
            void set_winning(GraphNode* n, const bool w) const;
            virtual PResult* update_result(const GraphNode*, PResult*) const;
            virtual Polyhedron predecessor(const VSZPoly*, const Polyhedron&, const Transition*, bool) const;
            Avalue backward_cost_heuristic() const;
            
    };

}

#endif

