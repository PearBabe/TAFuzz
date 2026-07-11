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

#ifndef ROMEO_PSTATE_HH
#define ROMEO_PSTATE_HH

#include <string>
#include <pwt.hh>

namespace romeo
{
    struct Job;
    class PResult;
    class CostResult;
    class CTS;
    class SExpression;
    class Transition;
    class Property;
    class RValue;
    class GraphNode;

    class PState: public PWNode, public Printable
    {
        protected:
            mutable PResult* rc;
            mutable bool have_computed_rc;

        public:
            virtual bool deadlock() const = 0;
            virtual bool safety_control_bad_state() const = 0;
            virtual bool bounded(const unsigned) const = 0;
            virtual bool step_limit(const unsigned, const bool) const;
            virtual PResult* cost_limit(const SExpression&, const bool) const = 0;
            virtual bool fired_transition(unsigned) const;
            virtual RValue evaluate(const SExpression&) const = 0;
            virtual std::string enabled_string(bool) const = 0;
            virtual bool can_delay_forever() const = 0;

            virtual PResult* init_result(bool) const = 0;
            virtual PResult* reach_cond() const;
            virtual PResult* state_result(bool) const = 0;
            virtual CostResult* current_cost() const = 0;
            virtual Avalue min_cost() const = 0;
            virtual CostResult* init_cost_result() const = 0;

            // GraphNode stores algorithm-specific payloads in untagged
            // unions.  Let the dynamic state type release only the payloads
            // that it actually created before the state itself is destroyed.
            virtual void destroy_graph_payload(GraphNode&) const;

            virtual void compute_rc() const = 0;

            virtual void min_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const = 0;
            virtual void max_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const = 0;

            virtual cvalue max_bound() const = 0;

            PState(const Job&);
            PState(const PState&);

            virtual ~PState();
    };
}

#endif
