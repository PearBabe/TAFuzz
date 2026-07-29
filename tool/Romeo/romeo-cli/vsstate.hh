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

#ifndef ROMEO_VSSTATE_HH
#define ROMEO_VSSTATE_HH

#include <vector>
#include <string>

#include <pstate.hh>
#include <valuation.hh>
#include <avalue.hh>

#include <size_digest.hh>

namespace romeo
{
    // Forward declarations
    class Instruction;
    class VSStateEqStorage;

    
    class VSSiterator: public PWNiterator
    {
        public:
            VSSiterator(PWNode*);
            virtual PWNode* next();
            virtual ~VSSiterator();
    };

    class VSState: public PState
    {
        protected:
            // Values of the variables
            valuation V;
            
            // Enabled transitions
            const Transition** en;

            // Number of firings since enabling
            // For FEFF
            unsigned* nf;

            // Number of enabled transitions
            unsigned NE;

            // Accumulated cost (by transitions)
            cvalue accum_cost;

            // Cost heuristic value
            Avalue heuristic_cost;

            // Approximate heuristic?
            bool heuristic_approx;

            // Estimation of the size of the time/parameter domain in
            // subclasses
            SizeDigest tsize;

        protected:
            void update_enabled();
            void update_enabled(const VSState&, const Transition&);
            void map_indices(const VSState&, unsigned [], const unsigned offset=0) const;
            void map_indices(const VSState&, const Transition*, unsigned [], const unsigned offset=0) const;
            virtual bool firable(unsigned) const;
            virtual bool feff_firable(unsigned) const;
            virtual PWNode* successor(unsigned);
            virtual bool set_firing_date(const unsigned, const LExpression*, const cvalue q=1);
            virtual void set_fired_date(const LExpression*, const cvalue q=1);

            // Constructors
            VSState();
            VSState(const Job&);
            VSState(const VSState&);
            VSState(const VSState&, const Transition&);
            VSState(const VSState&, const Instruction&);

        public:
            // From PState
            virtual bool deadlock() const;
            virtual bool bounded(const unsigned) const;
            virtual RValue evaluate(const SExpression&) const;
            virtual bool safety_control_bad_state() const;
            virtual cvalue max_bound() const;
            virtual PResult* cost_limit(const SExpression&, const bool) const;
            virtual bool can_delay_forever() const;

            virtual void compute_rc() const;
            virtual PResult* init_result(bool) const;
            virtual CostResult* init_cost_result() const;
            virtual PResult* state_result(bool) const;

            virtual std::string to_string() const;
            virtual std::string enabled_string(bool) const;

            // From PWNode
            virtual bool key_less(const PWNode*) const;
            virtual bool equals(const PWNode*) const;
            virtual bool contains(const PWNode*) const;
            virtual PWTRel compare(const PWNode*) const;
            virtual bool empty() const;
            virtual PWNode* copy(const Instruction*) const;
            virtual PWNiterator* iterator();
            virtual PassedList* init_passed(WaitingList&, unsigned, bool b=false) const;
            virtual WaitingList* init_waiting() const;
            virtual EqStorage* eq_storage() const;
            virtual RIncStorage* rinc_storage() const;
            virtual MergeStorage* merge_storage() const;
            virtual const std::byte* discrete() const;
            virtual Key get_key() const;
            virtual Key get_abstracted_key(bool*, bool*, cvalue*, cvalue*) const;
            virtual unsigned key_size() const;
            virtual unsigned discrete_size() const;
            virtual bool restriction(const PResult&);
            virtual PWNode* successor(const Transition*, const LExpression*);
            virtual PWNode* successor_by_label(const Transition*);
            
            virtual void min_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;
            virtual void max_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;

            virtual CostResult* current_cost() const;
            virtual Avalue min_cost() const;
            virtual Avalue cost_heuristic() const;
            virtual bool cost_less_than(const PWNode*) const;

            void add_dcost(cvalue);
            void set_hcost(const Avalue&);
            void compute_heuristic();
            bool is_heuristic_approximate() const;

            // Create new states
            static VSState* init(const Job&);

            // Destructor
            virtual ~VSState();

            // Accessor
            unsigned nen() const;
            const Transition* get_enabled(unsigned i) const;

            virtual bool update_firing_date(const Transition*, const LExpression*, const cvalue q=1);

            SizeDigest get_tsize() const;
            virtual void update_tsize();

            // Control
            virtual bool update_reach(GraphNode*) const;
            virtual bool update_safe(GraphNode*) const;
            virtual void set_winning(GraphNode*, const bool) const;
            virtual void init_winning(GraphNode*) const;
            virtual void add_winning(GraphNode*, GraphNode*) const;
            virtual PResult* update_result(const GraphNode*, PResult*) const;
            virtual bool has_winning(const GraphNode*) const;
            virtual PassedGN* init_passed_gn(WaitingGN&, WaitingGN&) const;

            friend class SExpression;
            friend class VSSiterator;
            friend class VSStateEqStorage;
    };

    class VSStateMergeStorage: public MergeStorage
    {
        public:
            virtual bool addr(const PWNode*, const PResult*);
            virtual unsigned size() const;

            VSStateMergeStorage(const VSState*);
            virtual ~VSStateMergeStorage();
    };

    class VSStateRIncStorage: public RIncStorage
    {
        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VSStateRIncStorage(const VSState*);
            virtual ~VSStateRIncStorage();
    };

    class VSStateCostStorage: public RIncStorage
    {
        protected:
            Avalue cost;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VSStateCostStorage(const VSState*);
            virtual ~VSStateCostStorage();
    };


    class VSStateEqStorage: public EqStorage
    {
        protected:
            unsigned size;
            const std::byte* V;

        public:
            VSStateEqStorage(const VSState*);
            virtual bool equals(const PWNode*) const;
            virtual bool key_less(const EqStorage*) const;
            virtual const std::byte* key_copy() const;
            ~VSStateEqStorage();
    };

}

#endif

