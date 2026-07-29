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

#ifndef ROMEO_TRANSITION_HH
#define ROMEO_TRANSITION_HH


#include <lobject.hh>
#include <valuation.hh>
#include <variable.hh>
#include <sexpression.hh>

namespace romeo
{
    class TimeInterval;
    class CTS;

    enum control_type { CTRL_CONTROLLABLE = 1, CTRL_FORCED = 2, CTRL_DELAYED = 4, CTRL_URGENT = 8 };

    class Transition: public LObject
    {
        public:
            unsigned feff_id;
            SExpression guard;
            SExpression assigns;
            const TimeInterval* timing;
            SExpression intermediate;
            SExpression speed;
            SExpression priority;
            SExpression cost;
            bool utility;
            unsigned int control;
            SExpression allow;

            bool max_bounded;
            cvalue max_bound;
            VarSet abs_vars;
            VarSet read_vars;
            VarSet en_vars;
            VarSet written_vars;
            int prefval;

        public:
            Transition(const unsigned, 
                       const std::string&, 
                       const SExpression&, 
                       const SExpression&, 
                       const TimeInterval*,
                       const SExpression&,
                       const SExpression&,
                       const SExpression&,
                       const SExpression&,
                       const bool,
                       const unsigned int,
                       const SExpression&
                       );
            
            bool has_priority_over(const Transition&, const std::byte[], const std::byte[]) const;

            virtual std::string to_string() const;
            const Transition* copy(CTS&) const;

            void copy(const Transition&, CTS&);
            void abstract_copy(const Transition&, CTS&, const VarSet&);
            const Transition* instantiate(CTS&, const unsigned, const value) const;

            void reads(VarSet&) const;
            void writes(VarSet&) const;

            cvalue get_cost(std::byte V[], const std::byte statics[], bool non_negative_costs) const;

            virtual ~Transition();
    };
}

#endif
