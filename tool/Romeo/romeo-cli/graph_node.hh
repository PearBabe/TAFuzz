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

#ifndef ROMEO_GRAPH_NODE
#define ROMEO_GRAPH_NODE

#include "avalue.hh"
#include "control_reach.hh"
#include "transition.hh"
#include <map>
#include <vector>

#include <pwt.hh>
#include <pstate.hh>
#include <result.hh>

#include <dbm.hh>
#include <cost_dbm.hh>
#include <polyhedron.hh>


namespace romeo
{
    class Transition;

    union tgt_type
    {
        DBM* td;
        Polyhedron* tp;
    };


    union WSet
    {
        bool wb;
        DBMUnion* wd;
        CostDBMUnion* wc;
        Polyhedron* wp;
    };

    enum wset_type
    {
        WSET_UNTIMED,
        WSET_DBM,
        WSET_CDBM,
        WSET_LDBM,
        WSET_PDBM,
        WSET_POLY
    };

    enum strat_type
    {
        STRAT_ACTION,
        STRAT_ENV_ACTION,
        STRAT_ACTION_CLASS,
        STRAT_RESET
    };

    // Strategy
    struct LocalStrategy
    {
        WSet domain;
        std::vector<const Transition*> en; // enabled transitions constrained in the domain
        std::vector<const Transition*> ctr; // newly enabled controllable transitions 
        const Transition* action; // What to do (wait if NULL)
        strat_type type;

        LocalStrategy(): domain(), en(), ctr(), action(nullptr), type(STRAT_ACTION) {}
        LocalStrategy(const LocalStrategy& s): domain(s.domain), en(s.en), ctr(s.ctr), action(s.action), type(s.type) {}
    };

    void add_local_strategy(const wset_type, std::list<LocalStrategy>&, const LocalStrategy&);
    void merge_strategies(const wset_type, std::list<LocalStrategy>&, const std::list<LocalStrategy>&);


    typedef std::map<const std::byte*, std::list<LocalStrategy>, LtBytes> Strategy;

    struct SuccInfo
    {
        GraphNode* node;
        const Transition* trans;
        WSet pred;
        WSet pred2;
        WSet delta;
        bool up_to_date;
        tgt_type tgt;

        SuccInfo(GraphNode*, const Transition*);
    };

    struct PredInfo
    {
        GraphNode* node;
        const Transition* trans;

        PredInfo(GraphNode*, const Transition*);
    };

    class GraphNode
    {
        protected:
            PState* state;
            //WSet losing;
            //const Transition* strategy;
            //bool urgent_strat;
            unsigned steps;

        public:
            Avalue back_cost;
            WSet winning;
            std::list<PredInfo> preds;
            std::list<SuccInfo> succs;
            std::list<LocalStrategy> strategy;

        public:
            static GraphNode* build_graph(const PState*);

        public:
            GraphNode(PState*);
            GraphNode(PState*, bool);
            ~GraphNode();
            bool has_preds() const;
            void erase_pred(GraphNode*);
            PredInfo first_pred_not_in(const std::set<GraphNode*>&, bool&) const;
            bool add_pred(GraphNode*, const Transition*);
            SuccInfo* add_succ(GraphNode*, const Transition*, PState*);
            void set_state(PState*);
            PState* get_state();
            const PState* get_state() const;
            bool restriction(const PResult&);
            const std::list<LocalStrategy> get_strategy() const;
            void clear_strategy(const wset_type);

            void set_outdated(SuccInfo&);
            void set_uptodate(SuccInfo&);

            unsigned n_not_to_update() const;
            unsigned nsteps() const;
            void update_steps(const unsigned);

            PResult* update_result(PResult*) const;
            bool has_winning() const;

            static void export_graphviz(GraphNode*);

            friend class PWNode;
    };

    struct LtBackGN
    {
        bool operator()(const GraphNode* N1, const GraphNode* N2) const
        {   
            const unsigned u1 = N1->n_not_to_update();
            const unsigned u2 = N2->n_not_to_update();
            const unsigned s1 = N1->nsteps();
            const unsigned s2 = N2->nsteps();
            //const unsigned p1 = N1->preds.size();
            //const unsigned p2 = N2->preds.size();

            if (s1 == s2)
            {
                return (u1 < u2);
            } else {
              return (s1 > s2);
            }
        }
    };

    struct LtBackGNHistory
    {
        bool operator()(const GraphNode* N1, const GraphNode* N2) const
        {   
            const Avalue c1 = N1->back_cost;
            const Avalue c2 = N2->back_cost;

            if (c1 == c2)
            {
                return N1->get_state()->backward_cost_heuristic() < N2->get_state()->backward_cost_heuristic();
            } else {
                return (c1 < c2);
            }
        }
    };

    class PassedGNEq;

    class WaitingGN
    {
        public:
            virtual GraphNode* get() = 0;
            virtual void put(GraphNode*) = 0;
            virtual void uput(GraphNode*) = 0;
            virtual bool empty() const = 0;
            virtual void add_restriction(const PResult&) = 0;
            virtual bool remove(GraphNode*) = 0;
    };

    class WaitingListGN: public WaitingGN
    {
        protected:
            std::list<GraphNode*> waiting;
            const Job& job;

            expl_strategy es;
        public:
            WaitingListGN(const Job&);
            WaitingListGN(const Job&, const expl_strategy);
            
            virtual GraphNode* get();
            virtual void put(GraphNode*);
            virtual void uput(GraphNode*);
            void oput(GraphNode*);
            virtual bool empty() const;
            virtual void add_restriction(const PResult&);
            virtual bool remove(GraphNode*);
    };

    template<typename T> class PriorityQueueGN : public WaitingGN
    {
        private:
            PairingHeap<GraphNode*, T> waiting;
            PResult* restricter;
            const Job& job;

        public:
            PriorityQueueGN(const Job& j): restricter(NULL), job(j)
            {
            }
            
            virtual GraphNode* get()
            {
                if (!waiting.is_empty())
                { 
                    return waiting.pop(); 
                } else {
                    return NULL;
                }
            }

            virtual void put(GraphNode* n)
            {
                waiting.insert(n);
            }

            virtual void uput(GraphNode* n)
            {
                waiting.insert(n);
            }

            virtual bool remove(GraphNode* n)
            {
                return waiting.delete_value(n);
            }

            virtual void add_restriction(const PResult& r)
            {
                if (!r.universe())
                {
                    if (job.restrict_update)
                    {
                        PHIterator<GraphNode*, T> i = waiting.iterator();
                        while (!i.done())
                        {
                            if ((*i)->restriction(r))
                            {
                                // The passed set owns graph nodes in the
                                // priced backward path.  Removing a restricted
                                // item here must only discard the heap wrapper;
                                // the node remains indexed in passed and is
                                // reclaimed with the graph.
                                waiting.erase(i);
                            } else {
                                i.next();
                            }
                        }
                    } else {
                        if (restricter == NULL)
                            restricter = r.copy();
                        else
                            restricter->conjunction(r);
                    }
                }
            }

            virtual bool empty() const
            {
                return waiting.is_empty();
            }

            ~PriorityQueueGN()
            {
                delete restricter;
                restricter = nullptr;
            }

    };
    class PassedGN
    {
        public:
            wset_type wstype;
            WaitingGN& fwd;
            WaitingGN& bwd;

        public:
            PassedGN(const wset_type, WaitingGN&, WaitingGN&);
            virtual GraphNode* put(PState*, GraphNode*&, bool) = 0;
            virtual Strategy get_strategy(property::control_mode) const = 0;
            virtual ~PassedGN();
    };

    class PassedGNEq: public PassedGN
    {
        protected:
            std::map<const EqStorage*, GraphNode*, LtEq> passed;

        public:
            PassedGNEq(const wset_type, const unsigned, WaitingGN&, WaitingGN&);
            virtual GraphNode* put(PState*, GraphNode*&, bool);
            virtual Strategy get_strategy(property::control_mode) const;
            virtual ~PassedGNEq();

        friend class CtrlBool;
    };
    
    class PassedGNEqNC: public PassedGN
    {
        protected:
            std::map<const std::byte*, std::list<GraphNode*>, LtBytes> passed;

        public:
            PassedGNEqNC(const wset_type, const unsigned, WaitingGN&, WaitingGN&);
            virtual GraphNode* put(PState*, GraphNode*&, bool);
            virtual Strategy get_strategy(property::control_mode) const;
            virtual ~PassedGNEqNC();

        friend class CtrlBool;
    };

    class PassedGNInc: public PassedGN
    {
        protected:
            std::map<const std::byte*, std::list<GraphNode*>, LtBytes> passed;

        public:
            PassedGNInc(const wset_type, const unsigned, WaitingGN&, WaitingGN&);
            virtual GraphNode* put(PState*, GraphNode*&, bool);
            virtual Strategy get_strategy(property::control_mode) const;
            virtual ~PassedGNInc();

        friend class CtrlBool;
    };

}

#endif
