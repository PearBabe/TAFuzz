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




#ifndef ROMEO_CVSCLASS_HH
#define ROMEO_CVSCLASS_HH

#include <vector>
#include <string>
#include <set>

#include <linear_expression.hh>
#include <vsclass.hh>

namespace romeo
{

    //class LinearExpression;
    
    class CVSClass: public VSClass
    {
        private:
            std::vector<LinearExpression> costs;

            static void fm_constraints(const DBM&, const unsigned, const unsigned[], const unsigned, const bool[], std::vector<LinearExpression>&, std::vector<LinearExpression>&);
            static void fm_fired_constraints(const DBM&, const unsigned, const unsigned[], const bool[], std::vector<LinearExpression>&, std::vector<LinearExpression>&);
            static std::vector<LinearExpression> fm_eliminate(const DBM&, const unsigned, const std::vector<LinearExpression>&, const unsigned, const unsigned[], const bool[]);
            static std::set<LinearExpression,ltle> fm_combine(const std::vector<LinearExpression>&, const unsigned);

            Avalue cmin;

        public:
            // Constructors
            CVSClass(const Job&);
            CVSClass(const CVSClass&);
            CVSClass(const CVSClass&, unsigned);
            CVSClass(const CVSClass&, const Instruction&);
    
            // Create new symbolic states
            virtual PWNode* copy(const Instruction*) const;
            static CVSClass* init(const Job&);
            virtual PWNode* successor(unsigned);

            virtual Avalue min_cost() const;

            std::string to_string() const;

            // Destructor
            ~CVSClass();
    };

}


#endif

