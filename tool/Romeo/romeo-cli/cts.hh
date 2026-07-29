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

#ifndef ROMEO_CTS_HH
#define ROMEO_CTS_HH

#include <list>
#include <vector>
#include <map>
#include <set>

#include <valuation.hh>
#include <lobject.hh>
#include <variable.hh>

#include <transition.hh>
#include <parameter.hh>

namespace romeo
{

    // Forward declarations ----------------------------------------------------
    class Function;
    class SExpression;
    class Variable;

    enum cmode: uint8_t;

    namespace instruction
    {
        class Block;
    }

    // -------------------------------------------------------------------------

    class CTS: public LObject, public VContext
    {
        private:
            unsigned NT;
            unsigned NP;
            unsigned NC;

            std::list<Parameter> parameters;
            std::list<Transition> transitions;
            std::list<const Function*> functions;

            bool bounded_params;
            cvalue parameter_bound;

            bool uses_time;
            bool uses_cost;
            bool uses_params;
            bool uses_hybrid;

        public:
            bool* parameter_lbounded;
            bool* parameter_ubounded;
            cvalue* parameter_lbounds;
            cvalue* parameter_ubounds;

        private:
            cvalue max_timing_constant;
            std::map<std::string, const Transition*> transitions_by_label;
            std::map<std::string, const Parameter*> parameters_by_label;
            std::map<std::string, const Function*> functions_by_label;

        public:
            SExpression initv; // Instructions
            SExpression initp; // Linear constraint

            SExpression cost;
            SExpression cost_heuristic;

            std::vector<std::list<const Transition*> > trans_to_check;
            std::vector<std::set<const Transition*> > trans_disabled;
            std::vector<std::list<const Transition*> > trans_enabled;

            static CTS* current_cts;

        public:
            const Transition* lookup_transition(const std::string&) const;
            Transition* lookup_transition_non_const(const std::string&);
            const Parameter* lookup_parameter(const std::string&) const;
            const Function* lookup_function(const std::string&) const;
            
            std::list<Transition>::const_iterator begin_transitions() const;
            std::list<Transition>::const_iterator end_transitions() const;
            std::list<Parameter>::const_iterator begin_parameters() const;
            std::list<Parameter>::const_iterator end_parameters() const;
            std::list<const Function*>::const_iterator begin_functions();
            std::list<const Function*>::const_iterator end_functions();

            const Variable& find_or_add_util(const std::string&);

            void add_transition(const Transition&);
            void add_transition_abstract(const Transition&, const VarSet&);
            const Parameter* add_parameter(const Parameter&);

            void add_function(const Function*);

            void find_constants();

            unsigned ntrans() const;
            unsigned nparams() const;
            unsigned nconstants() const;
            bool params_bounded() const;
            value params_bound() const;

            cvalue max_const() const;

            bool has_time() const;
            bool has_cost() const;
            bool has_params() const;
            bool has_hybrid() const;

            std::list<const Transition*> adapt_trace_ids(const std::list<std::string>&);

            void writing_trans_with_reads(const VarSet& S, VarSet& Sext, std::list<const Transition*>& T) const;

            // Remove parameters from transition intervals by hypercube overapproximation
            CTS abstract_parameters() const;

            cvalue cost_rate(std::byte V[], bool non_negative_costs) const;
        
            CTS(const unsigned, const std::string&);
            CTS(const CTS&);
            CTS(const CTS&, const VarSet&, const std::list<const Transition*>&);

            virtual std::string to_string() const;

            ~CTS();
    };

}

#endif

