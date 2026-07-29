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

#ifndef ROMEO_PWT_HH
#define ROMEO_PWT_HH

#include <cstdlib>
#include <map>
#include <list>
#include <vector>
#include <set>
#include <utility>

#include <job.hh>
#include <pairing_heap.hh>

namespace romeo
{
    enum PWTStatus { PWT_NEW, PWT_IN_PASSED, PWT_IN_TRACE, PWT_NONE, PWT_NEW_IN_TRACE }; 
    enum PWTRel { PWT_EQ, PWT_INC, PWT_DIFF }; 
    class PassedList;
    class WaitingList;
    class PassedVMerge;
    class PassedVEq;
    class PWNode;
    class PResult;
    class Transition;
    class GraphNode;
    struct SuccInfo;
    union tgt_type;
    class PWNode;

    class PWNiterator
    {
        protected:
            PWNode* base;
            std::vector<unsigned> succs;
            unsigned index;

        public:
            PWNiterator(PWNode*);
            virtual PWNode* next() = 0;
            virtual ~PWNiterator();
    };

    class MergeStorage
    {
        public:
            virtual bool addr(const PWNode*, const PResult*) = 0;
            virtual unsigned size() const = 0;

            virtual ~MergeStorage();
    };

    class RIncStorage
    {
        protected:
            const PWNode* node;

        public:
            const PWNode* get_node() const;
            virtual bool contains(const PWNode*) const = 0;
            virtual bool is_contained_in(const PWNode*) const = 0;

            RIncStorage(const PWNode*);
            virtual ~RIncStorage();

        friend class PWNode;
    };

    class EqStorage
    {
        public:
            virtual bool key_less(const EqStorage*) const = 0;
            virtual bool equals(const PWNode*) const = 0;
            virtual const std::byte* key_copy() const = 0;

            virtual ~EqStorage();
    };

    struct Key
    {
        unsigned size;
        const std::byte* k;

        Key(unsigned s, const std::byte* key): size(s), k(key) {}

        bool operator<(const Key& a) const
        {
            return ((size < a.size) || (size == a.size && romeo::compare(k, a.k, size) == LESS));
        }
    };

    namespace property { class LT; }

    class Transition;
    class CTS;
    class LExpression;
    class Instruction;
    class Avalue;
    class PassedGN;
    class WaitingGN;

    class PWNode
    {
        protected:
            mutable unsigned allocated_succs; // Number of allocated successors (for deallocate())
            mutable bool sticky;              // false iff it is ever allowed to deallocated
            mutable bool trace_end;           // current trace end should not be deallocated
            const PWNode* parent;           // Parent node
            const PWNode* trace_root;       // Limit for the trace inclusion checking
            const Transition* in;     // Transition fired from parent node
            unsigned steps;           // Number of discrete steps from the initial state (length of the trace)

            mutable RIncStorage* storage; // A link to the RIncStorage corresponding to this state (NULL otherwise)

            VarSet read_vars;
            VarSet abs_vars;
            unsigned penalty;

            uint64_t hash;

        public:
            PWNode(const Job& j);
            PWNode(const PWNode&);
            virtual ~PWNode();

            const Job& job;

            void deallocate() const;
            void deallocate_() const;

            // Accessors
            const PWNode* parent_node() const;
            const Transition* in_transition() const;

            // need also constructors
            virtual bool key_less(const PWNode*) const = 0;
            virtual bool equals(const PWNode*) const = 0;
            virtual PWTRel compare(const PWNode*) const = 0;
            virtual bool contains(const PWNode*) const = 0;
            virtual bool empty() const = 0;
            virtual PWNiterator* iterator() = 0;
            virtual PassedList* init_passed(WaitingList&, unsigned, bool b=false) const = 0;
            virtual WaitingList* init_waiting() const = 0;
            virtual RIncStorage* rinc_storage() const = 0;
            virtual MergeStorage* merge_storage() const = 0;
            virtual EqStorage* eq_storage() const = 0;
            virtual const std::byte* discrete() const = 0;
            virtual Key get_key() const = 0;
            virtual Key get_abstracted_key(bool*, bool*, cvalue*, cvalue*) const = 0;
            virtual unsigned key_size() const = 0;
            virtual unsigned discrete_size() const = 0;
            virtual PWNode* copy(const Instruction* I = NULL) const = 0;
            virtual bool restriction(const PResult&) = 0;
            virtual PWNode* successor(const Transition*, const LExpression* e = NULL) = 0;
            virtual PWNode* successor_by_label(const Transition*) = 0;

            virtual Avalue min_cost() const = 0;
            virtual Avalue cost_heuristic() const = 0;
            virtual Avalue backward_cost_heuristic() const;

            virtual bool cost_less_than(const PWNode*) const = 0;

            virtual bool update_reach(GraphNode*) const = 0;
            virtual bool update_safe(GraphNode*) const = 0;
            virtual void set_winning(GraphNode*, const bool) const = 0;
            virtual void init_winning(GraphNode*) const = 0;
            virtual void add_winning(GraphNode*, GraphNode*) const = 0;
            virtual void init_propagation(GraphNode*) const;
            virtual SuccInfo* add_succ(GraphNode*, const Transition*, PState*, GraphNode*) const;

            virtual PResult* update_result(const GraphNode*, PResult*) const = 0;
            virtual bool has_winning(const GraphNode*) const = 0;
            virtual PassedGN* init_passed_gn(WaitingGN&, WaitingGN&) const = 0;

            unsigned nreads() const;
            unsigned nsteps() const;

            uint64_t get_hash() const;
            void set_hash(uint64_t);

            bool has_in_trace(const PWNode*) const;

            friend class PassedVMerge;
            friend class PassedVHMerge;
            friend class PassedVEq;
            friend class PassedVInc;
            friend class PassedRInc;
            friend class SimplePassedCosts;
            friend class property::LT;
            friend class PWNiterator;
            friend class VSSiterator;
            friend class CVSCiterator;
            friend class RIncStorage;
            friend class PResult;
            friend class DProperty;
    };

    struct LtBytes
    {
        static unsigned vsize;

        bool operator()(const std::byte*, const std::byte*) const;
    };
    
    struct LtEq
    {
        bool operator()(const EqStorage*, const EqStorage*) const;
    };

    struct LtNodes
    {
        bool operator()(const PWNode*, const PWNode*) const;
    };

    struct LtNodesCost
    {
        bool operator()(const PWNode*, const PWNode*) const;
    };

    class WaitingList
    {
        protected:
            std::list<PWNode*> waiting;

            PResult* restricter;
            const Job& job;

            expl_strategy es;

        public:
            WaitingList(const Job&);
            WaitingList(const Job&, const expl_strategy);
            
            virtual PWNode* get() = 0;;
            virtual void put(PWNode*) = 0;

            virtual void remove(PWNode*) = 0;
            virtual void add_restriction(const PResult&) = 0;

            virtual ~WaitingList();

    };

    class SimpleWaitingList: public WaitingList
    {
        protected:
            std::list<PWNode*> waiting;

        public:
            SimpleWaitingList(const Job&);
            SimpleWaitingList(const Job&, const expl_strategy);
            
            virtual PWNode* get();
            virtual void put(PWNode*);

            virtual void remove(PWNode*);
            virtual void add_restriction(const PResult&);

            virtual ~SimpleWaitingList();

    };

    class CostPriorityQueue: public SimpleWaitingList
    {
        public:
            CostPriorityQueue(const Job&);

            virtual PWNode* get();
            virtual void put(PWNode*);
            
    };

    class PassedList
    {
        protected:
            bool check_trace;
            PResult* R; // Restricter

        public:
            PassedList(bool b=false);
            virtual PWTStatus put(const PWNode*) = 0;
            virtual void add_restriction(const PResult*);
            virtual void info() const;

            virtual ~PassedList();
    };

    class PassedVMerge: public PassedList
    {
        protected:
            std::map<const std::byte*, MergeStorage*, LtBytes> passed;
            unsigned nput;
            unsigned ninc;

        public:
            PassedVMerge(unsigned, bool b=false);
            virtual PWTStatus put(const PWNode*);
            virtual PWTStatus putr(const PWNode*, const PResult*);
            virtual void info() const;

            virtual ~PassedVMerge();
    };

    class PassedVHMerge: public PassedList
    {
        protected:
            std::vector<std::list<std::pair<const std::byte*, MergeStorage*> > > passed;
            unsigned nput;
            unsigned ninc;

        public:
            PassedVHMerge(unsigned, bool b=false);
            virtual PWTStatus put(const PWNode*);
            virtual PWTStatus putr(const PWNode*, const PResult*);
            virtual void info() const;

            virtual ~PassedVHMerge();
    };

    class PassedVEq: public PassedList
    {
        protected:
            std::set<const EqStorage*, LtEq> passed;

        public:
            PassedVEq(bool b=false);
            virtual PWTStatus put(const PWNode*);

            virtual ~PassedVEq();
    };

    class PassedVOff: public PassedList
    {
        public:
            PassedVOff();
            virtual PWTStatus put(const PWNode*);
    };

    class PassedRInc: public PassedList
    {
        protected:
            std::map<const std::byte*, std::list<const RIncStorage*>, LtBytes> passed;
            WaitingList& wqueue;
            unsigned nput;

        public:
            PassedRInc(const bool b, WaitingList&, unsigned);
            virtual PWTStatus put(const PWNode*);

            virtual void info() const;
            virtual ~PassedRInc();
    };
}

#endif

