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

#include "control_reach.hh"
#include <sstream>

#include <graph_node.hh>
#include <color_output.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;


SuccInfo::SuccInfo(GraphNode* n, const Transition* t): node(n), trans(t), up_to_date(false)
{
    pred.wp = nullptr;
    pred2.wp = nullptr;
    delta.wp = nullptr;
    tgt.tp = nullptr;
}

PredInfo::PredInfo(GraphNode* n, const Transition* t): node(n), trans(t)
{
}

// -----------------------------------------------------------------------
GraphNode::GraphNode(PState* s): state(s), steps(s->nsteps())
{
    s->init_winning(this);
}

GraphNode::GraphNode(PState* s, bool w): state(s), steps(s->nsteps())
{
    s->init_winning(this);
    s->set_winning(this, w);
}

GraphNode::~GraphNode()
{
    if (state != nullptr)
    {
        state->destroy_graph_payload(*this);
        delete state;
        state = nullptr;
    }
}

bool GraphNode::has_preds() const
{
    return !preds.empty();
}

PredInfo GraphNode::first_pred_not_in(const set<GraphNode*>& S, bool& b) const
{
    b = true;
    // preds should not be empty
    for (auto g: preds)
    {
        if (!S.count(g.node))
        {
            return g;
        }

    }

    b = false;
    return preds.front();
}

void GraphNode::erase_pred(GraphNode* g)
{
    auto it = preds.begin(); 
    while (it != preds.end() && it->node != g)
    {
        it++;
    }

    preds.erase(it);
}

bool GraphNode::add_pred(GraphNode* n, const Transition* t)
{
    bool found = false;
    for (auto its = preds.begin(); its != preds.end() && !found; its++)
    {
        found = (its->node == n && its->trans == t);
    }

    if (!found)
    {
        preds.push_back(PredInfo(n, t));
    }

    return !found;
}

SuccInfo* GraphNode::add_succ(GraphNode* n, const Transition* t, PState* s)
{
    return state->add_succ(this, t, s, n);
}


void GraphNode::set_state(PState* s)
{
    state = s;
}

PState* GraphNode::get_state()
{
    return state;
}

const PState* GraphNode::get_state() const
{
    return state;
}
            
bool GraphNode::restriction(const PResult& r)
{
    return state->restriction(r);
}

const list<LocalStrategy> GraphNode::get_strategy() const
{
    return strategy;
}

void GraphNode::clear_strategy(const wset_type wstype)
{
    list<LocalStrategy>::iterator i;
    for (i = strategy.begin(); i != strategy.end(); i++)
    {
        if (wstype == WSET_POLY)
        {
            delete i->domain.wp;
        } else if (wstype == WSET_DBM) {
            delete i->domain.wd;
        }
    }
    strategy.clear();
}

PResult* GraphNode::update_result(PResult* r) const
{
    return state->update_result(this, r);
}

bool GraphNode::has_winning() const
{
    return state->has_winning(this);
}

void GraphNode::export_graphviz(GraphNode* init)
{
    const Job& job = init->get_state()->job; 
    stringstream g;
    map<GraphNode*, unsigned> ids;
    vector<GraphNode*> nodes;
    unsigned nnodes = 0;

    cout << "digraph G {" << endl;
    cout << "node[shape=box];" << endl;
    list<GraphNode*> waiting;
    set<GraphNode*> passed;
    passed.insert(init);
    waiting.push_back(init);
    while (!waiting.empty())
    {
        GraphNode* n = waiting.front();
        waiting.pop_front();

        auto it = ids.find(n);
        unsigned nid = 0; 
        if (it != ids.end())
        {
            nid = it->second;
        } else {
            nid = nnodes;
            ids[n] = nid;
            nodes.push_back(n);
            if (job.graph_nodes_inside)
            {
                cout << "C" << nid << "[ label = \"" << n->get_state()->to_string() << "\"];" << endl;
            }
            nnodes++;
        }

        list<SuccInfo>::const_iterator i;
        for (i = n->succs.begin(); i != n->succs.end(); i++)
        {
            auto it = ids.find(i->node);
            unsigned iid = 0; 
            if (it != ids.end())
            {
                iid = it->second;
            } else {
                iid = nnodes;
                ids[i->node] = iid;
                nodes.push_back(i->node);
                if (job.graph_nodes_inside)
                {
                    cout << "C" << iid << "[ label = \"" << i->node->get_state()->to_string() << "\"];" << endl;
                }
                nnodes++;
            }

            g << "C" << nid << " -> " << "C" << iid << " [ label= \"" << i->trans->label << "\"];" << endl;
            if (passed.count(i->node) == 0)
            {
                waiting.push_back(i->node);
                passed.insert(i->node);
            }
        }
    }

    if (job.graph_nodes_inside)
    {
        cout << endl;
    }

    cout << g.str();
    cout << "}" << endl<< endl;

    if (!job.graph_nodes_inside)
    {
        for (auto n : nodes)
        {
            cout << "--------------------------------------------------------------------------------" << endl;
            cout << "                                     C" << ids[n] << endl;
            cout << "--------------------------------------------------------------------------------" << endl;
            cout << n->state->to_string() << endl;
        }
    }
}

void GraphNode::set_outdated(SuccInfo& s)
{
    s.up_to_date = false;
}

void GraphNode::set_uptodate(SuccInfo& s)
{
    s.up_to_date = true;
}

unsigned GraphNode::n_not_to_update() const
{
    unsigned result = 0;
    for (const auto& edge: succs)
    {
        if (!edge.up_to_date)
        {
            result++;
        }
    }

    return result;
}

unsigned GraphNode::nsteps() const
{
    return steps;
}

void GraphNode::update_steps(const unsigned n)
{
    steps = max(steps, n);
}

GraphNode* GraphNode::build_graph(const PState* s) 
{
    const Job& job = s->job;

    WaitingListGN fwd(job);

    PassedGN& passed = *s->init_passed_gn(fwd, fwd);

    GraphNode* current;
    GraphNode* nothing = nullptr;
    GraphNode* initg = passed.put(static_cast<PState*>(s->copy()), nothing, false);
    fwd.put(initg);

    while (!fwd.empty())
    {
        current = fwd.get();
        //cout << "=================================================================================" <<endl;
        //cout << "fwd: " << endl << *current->get_state() << endl;
        //const PWNode* y =current->get_state();
        //while (y->in_transition() != NULL)
        //{
        //    cout << y->in_transition()->label << " ";
        //    y = y->parent_node();
        //}
        //cout << endl;

        // Forward exploration
        const PState* x = current->get_state();
        PWNiterator* i = const_cast<PState*>(x)->iterator();
        PState* succ;
        
        // compute all successors 
        while ((succ = static_cast<PState*>(i->next())))
        {
            GraphNode * gsucc = passed.put(succ, current, false);

            //cout << "succ is " << endl;
            //cout << *succ << endl;
            
            // No convergence: explore further
            if (gsucc->get_state() == succ)
            {
                fwd.put(gsucc);
            } else {
                succ->deallocate();
            }
        }
        
        delete i;
    }

    delete &passed;

    return initg;
}

// -----------------------------------------------------------------------

PassedGN::PassedGN(const wset_type w, WaitingGN& F, WaitingGN& B): wstype(w), fwd(F), bwd(B)
{
}

PassedGN::~PassedGN()
{
}

// -----------------------------------------------------------------------
PassedGNEq::PassedGNEq(const wset_type w, const unsigned vs, WaitingGN& F, WaitingGN& B): PassedGN(w, F, B)
{
    LtBytes::vsize = vs;
}

GraphNode* PassedGNEq::put(PState* s, GraphNode*& p, bool w)
{
    const EqStorage * es = s->eq_storage();
    map<const EqStorage*, GraphNode*, LtEq>::iterator i = passed.lower_bound(es);

    GraphNode* n;
    if (i != passed.end() && !passed.key_comp()(es, i->first))
    {
        // Found
        n = i->second;
        delete es;
    } else {
        n = new GraphNode(s);
        passed.insert(i, pair<const EqStorage*, GraphNode*>(es, n));
    }

    if (p != NULL)
    {
        n->add_pred(p, s->in_transition());
        p->add_succ(n, s->in_transition(), nullptr);
    }

    if (w)
    {
        s->set_winning(n, true);
    }

    // Only for incremental updates, hence should be after linking.
    if (w)
    {
        s->init_propagation(n);
        for (const auto& pred: n->preds)
        {
            bwd.uput(pred.node);
        }
    }

    return n;
}

Strategy PassedGNEq::get_strategy(property::control_mode mode) const
{
    Strategy r;

    map<const EqStorage*, GraphNode*, LtEq>::const_iterator i;
    for (i = passed.begin(); i != passed.end(); i++)
    {
        const EqStorage* s = i->first;
        const byte* new_key = s->key_copy();
        r.insert(pair<const byte*, const list<LocalStrategy> >(new_key, i->second->get_strategy()));
        // Good for untimed but we need to handle multiple states with the same discrete part
    }


    return r;
}



PassedGNEq::~PassedGNEq()
{
    set<GraphNode*> nodes;
    for (const auto& entry: passed)
    {
        if (wstype == WSET_CDBM)
        {
            nodes.insert(entry.second);
        }
        delete entry.first;
    }

    for (GraphNode* node: nodes)
    {
        delete node;
    }
}

// -----------------------------------------------------------------------

// WARNING: s (the domain inside) is modified
void romeo::add_local_strategy(const wset_type wstype, list<LocalStrategy>& L, const LocalStrategy& s)
{
    if (s.type != STRAT_ENV_ACTION)
    {
        for (auto sL : L)
        {
            //if (sL.type == STRAT_ACTION || sL.type == STRAT_ACTION_CLASS)
            if (sL.type == s.type && (sL.type != STRAT_RESET || (s.action == sL.action)))
            {
                if (wstype == WSET_POLY)
                {
                    Polyhedron P(*sL.domain.wp);
                    P.negation_assign();
                    s.domain.wp->intersection_assign(P);
                    s.domain.wp->reduce();
                } else if (wstype == WSET_DBM) {
                    DBMUnion D(sL.domain.wd->complement());
                    s.domain.wd->intersection_assign(D);
                }
            }
        }
        
        if (wstype == WSET_POLY)
        {
            if (!s.domain.wp->empty())
            {
                L.push_back(s);
            }
        } else if (wstype == WSET_DBM) {
            if (!s.domain.wd->empty())
            {
                L.push_back(s);
            }
        }
    //} else {
    //    L.push_back(s);
    }
}

void romeo::merge_strategies(const wset_type wstype, list<LocalStrategy>& L, const list<LocalStrategy>& A)
{
    list<LocalStrategy>::const_iterator ia;
    for (auto sA:  A)
    {
        add_local_strategy(wstype, L, sA);
    }
}

// -----------------------------------------------------------------------

PassedGNInc::PassedGNInc(const wset_type w, const unsigned vs, WaitingGN& F, WaitingGN& B): PassedGN(w, F, B)
{
    LtBytes::vsize = vs;
}

GraphNode* PassedGNInc::put(PState* s, GraphNode*& p, bool w)
{
    Log.start("put");

    const byte* nkey = s->discrete();
    map<const byte*, list<GraphNode*>, LtBytes>::iterator i = passed.lower_bound(nkey);

    GraphNode * n = nullptr;
    list<GraphNode*>::iterator j;
    // Priced graph nodes carry pending deltas (BVZone) or game-predecessor
    // caches (BCVZone).  The old reverse-inclusion merge discarded those
    // payloads, so keep the safe one-way inclusion until typed merge support
    // exists for both modes.
    const bool rincl = (wstype != WSET_CDBM);
    if (i != passed.end() && !passed.key_comp()(nkey, i->first))
    {
        // The key already exists
        delete [] nkey;

        //bool already_in = false;
        bool included = false;
        list<GraphNode*> subsumed;

        j = i->second.begin(); 
        while (j != i->second.end() && !included)
        {
            if ((*j)->get_state()->contains(s))
            {
                included = true;
            } else if (rincl && s->contains((*j)->get_state()) && !(*j)->preds.empty()) {
                // the initial node (preds empty) cannot be subsumed 
                subsumed.push_back(*j);
                j = i->second.erase(j);
            } else {
                j++;
            }
        }

        if (included)
        {
            Log.start("inc");
            // s is contained in a previous state
            n = *j;

            if (rincl && p != nullptr)
            {
                // same as below, remove link with outdated tgt
                auto its = p->succs.begin(); 
                list<const Transition*> trans_n;
                while (its != p->succs.end())
                {
                    if (its->node == *j && its->trans == s->in_transition()) 
                    {
                        its = p->succs.erase(its);
                    } else {
                        its++;
                    }
                }
            }
        
            n->update_steps(s->nsteps());
            Log.stop("inc");
        } else {
            // Add a new node
            n = new GraphNode(s);
            i->second.push_back(n);

            if (!subsumed.empty()) 
            {
                // Remove the nodes subsumed by this new node
                // Note that several subsumptions of a g by n are possible.
                // Hence n accumulates links and winning states in this loop.
                Log.start("rinc");

                bool wl_added_f = false;
                bool wl_added_b = false;
                
                for (auto g: subsumed)
                {
                    n->update_steps(g->nsteps());

                    // Merge winning sets
                    s->add_winning(n, g);
                    
                    // Merge links
                    for (auto pred: g->preds)
                    {
                        // add local pred
                        if (pred.node == g)
                        {
                            // self loop
                            n->add_pred(n, pred.trans);
                        } else {
                            n->add_pred(pred.node, pred.trans);

                            // update succ of pred
                            auto its = pred.node->succs.begin(); 
                            list<const Transition*> trans_n;
                            while (its != pred.node->succs.end())
                            {
                                if (its->node == n || its->node == g) 
                                {
                                    // For a given transition, we might have one
                                    // succ to g and one to n but when merging
                                    // they become the same. Therefore, when we add
                                    // the first of them, we record the transition
                                    // in trans_n so we can remove the other succ.
                                    // We also remove the old links from p that does not have the good tgt
                                    // The good links will be added at the end
                                    if ((pred.node == p && pred.trans == s->in_transition()) || find(trans_n.begin(), trans_n.end(), its->trans) != trans_n.end())
                                    {
                                        its = pred.node->succs.erase(its);
                                    } else {
                                        its->node = n;
                                        trans_n.push_back(its->trans);
                                        its++;
                                    }
                                } else {
                                    its++;
                                }
                            }
                        }
                    }

                    // successors will be recomputed for n
                    // but this might be done after some backpropagation happens 
                    // from those successors
                    for (auto succ: g->succs)
                    {
                        if (succ.node == g)
                        {
                            auto si = n->add_succ(n, succ.trans, nullptr);
                            if (si != nullptr)
                            {
                                si->tgt = succ.tgt;
                            }
                        } else { 
                            auto si = n->add_succ(succ.node, succ.trans, nullptr);
                            if (si != nullptr)
                            {
                                si->tgt = succ.tgt;
                            }

                            // update pred of succ
                            auto its = succ.node->preds.begin(); 
                            list<const Transition*> trans_n;
                            while (its != succ.node->preds.end() )
                            {
                                if (its->node == n || its->node == g) 
                                {
                                    // See above for succs of preds
                                    if (find(trans_n.begin(), trans_n.end(), its->trans) != trans_n.end())
                                    {
                                        its = succ.node->preds.erase(its);
                                    } else {
                                        its->node = n;
                                        trans_n.push_back(its->trans);
                                        its++;
                                    }
                                } else {
                                    its++;
                                }
                            }
                        }
                    }

                    // Remove from waiting lists
                    bool replace_f = fwd.remove(g);

                    // Add replacement to waiting list
                    if (replace_f && !wl_added_f)
                    {
                        fwd.put(n);
                        wl_added_f = true;
                    }

                    bool replace_b = bwd.remove(g);

                    // Add replacement to waiting list
                    if (replace_b && !wl_added_b)
                    {
                        bwd.put(n);
                        wl_added_b = true;
                    }

                    if (p == g)
                    {
                        p = n;
                    }

                    // Dealloc node
                    delete g;
                }
                Log.stop("rinc");
            } else {
                Log.count("new");
            }
        }
    } else {
        n = new GraphNode(s);
        passed.insert(i, pair<const byte*, list<GraphNode*> >(nkey, list<GraphNode*>(1, n)));
    }

    if (p != nullptr)
    {
        n->add_pred(p, s->in_transition());
        p->add_succ(n, s->in_transition(), s);
    }

    // Only for incremental updates, hence should be after linking.
    if (w)
    {
        s->set_winning(n, true);
        s->init_propagation(n);
        for (const auto& pred: n->preds)
        {
            bwd.uput(pred.node);
        }
    }

    Log.stop("put");
    return n;
}

Strategy PassedGNInc::get_strategy(property::control_mode mode) const
{
    Strategy r;
    
    std::map<const byte*, std::list<GraphNode*>, LtBytes>::const_iterator i;
    for (i = passed.begin(); i != passed.end(); i++)
    {
        const byte* key = i->first;

        // Check if the key (discrete part) is already in the strategy
        Strategy::iterator k = r.lower_bound(key);
        if (k != r.end() && !r.key_comp()(key, k->first))
        {
            // The key already exists

            list<GraphNode*>::const_iterator ig;
            for (ig = i->second.begin(); ig != i->second.end(); ig++)
            {
                if (mode != property::CONTROL_SAFE)
                {
                    merge_strategies(wstype, k->second, (*ig)->get_strategy());
                } else {
                    for (auto st: (*ig)->get_strategy())
                    {
                        k->second.push_back(st);
                    }
                }
            }
        } else {
            // The key does not exist
            // Add a copy
            const unsigned dsize = (*i->second.begin())->get_state()->discrete_size();
            byte* nkey = new byte[dsize];
            memcpy(nkey, key, dsize);

            list<GraphNode*>::const_iterator ig;
            list<LocalStrategy> L;
            for (ig = i->second.begin(); ig != i->second.end(); ig++)
            {
                if (mode != property::CONTROL_SAFE)
                {
                    merge_strategies(wstype, L, (*ig)->get_strategy());
                } else {
                    for (auto st: (*ig)->get_strategy())
                    {
                        L.push_back(st);
                    }
                }
            }

            r.insert(k, pair<const byte*, list<LocalStrategy> >(nkey, L));
        }
    }

    return r;
}

PassedGNInc::~PassedGNInc()
{
    set<GraphNode*> nodes;
    for (const auto& entry: passed)
    {
        if (wstype == WSET_CDBM)
        {
            nodes.insert(entry.second.begin(), entry.second.end());
        }
        delete [] entry.first;
    }

    for (GraphNode* node: nodes)
    {
        delete node;
    }
}


// -----------------------------------------------------------------------

PassedGNEqNC::PassedGNEqNC(const wset_type w, const unsigned vs, WaitingGN& F, WaitingGN& B): PassedGN(w, F, B)
{
    LtBytes::vsize = vs;
}

GraphNode* PassedGNEqNC::put(PState* s, GraphNode*& p, bool w)
{
    Log.start("put");

    const byte* nkey = s->discrete();
    map<const byte*, list<GraphNode*>, LtBytes>::iterator i = passed.lower_bound(nkey);

    GraphNode * n = nullptr;
    list<GraphNode*>::iterator j;
    if (i != passed.end() && !passed.key_comp()(nkey, i->first))
    {
        // The key already exists
        delete [] nkey;

        //bool already_in = false;
        bool equal = false;
        list<GraphNode*> subsumed;

        j = i->second.begin(); 
        while (j != i->second.end() && !equal)
        {
            equal = (*j)->get_state()->contains(s) && s->contains((*j)->get_state());
            if (!equal)
            {
                j++;
            }
        }

        if (equal)
        {
            Log.start("inc");
            // s is contained in a previous state
            n = *j;

            if (p != nullptr)
            {
                // same as below, remove link with outdated tgt
                auto its = p->succs.begin(); 
                list<const Transition*> trans_n;
                while (its != p->succs.end())
                {
                    if (its->node == *j && its->trans == s->in_transition()) 
                    {
                        its = p->succs.erase(its);
                    } else {
                        its++;
                    }
                }
            }
        
            n->update_steps(s->nsteps());
            Log.stop("inc");
        } else {
            // Add a new node
            n = new GraphNode(s);
            i->second.push_back(n);

            Log.count("new");
        }
    } else {
        n = new GraphNode(s);
        passed.insert(i, pair<const byte*, list<GraphNode*> >(nkey, list<GraphNode*>(1, n)));
    }

    if (p != nullptr)
    {
        n->add_pred(p, s->in_transition());
        p->add_succ(n, s->in_transition(), s);
    }

    // Only for incremental updates, hence should be after linking.
    if (w)
    {
        s->set_winning(n, true);
        s->init_propagation(n);
        for (const auto& pred: n->preds)
        {
            bwd.uput(pred.node);
        }
    }

    Log.stop("put");
    return n;
}

Strategy PassedGNEqNC::get_strategy(property::control_mode mode) const
{
    Strategy r;
    
    std::map<const byte*, std::list<GraphNode*>, LtBytes>::const_iterator i;
    for (i = passed.begin(); i != passed.end(); i++)
    {
        const byte* key = i->first;

        // Check if the key (discrete part) is already in the strategy
        Strategy::iterator k = r.lower_bound(key);
        if (k != r.end() && !r.key_comp()(key, k->first))
        {
            // The key already exists

            list<GraphNode*>::const_iterator ig;
            for (ig = i->second.begin(); ig != i->second.end(); ig++)
            {
                merge_strategies(wstype, k->second, (*ig)->get_strategy());
            }
        } else {
            // The key does not exist
            // Add a copy
            const unsigned dsize = (*i->second.begin())->get_state()->discrete_size();
            byte* nkey = new byte[dsize];
            memcpy(nkey, key, dsize);

            list<GraphNode*>::const_iterator ig;
            list<LocalStrategy> L;
            for (ig = i->second.begin(); ig != i->second.end(); ig++)
            {
                merge_strategies(wstype, L, (*ig)->get_strategy());
            }
            r.insert(k, pair<const byte*, list<LocalStrategy> >(nkey, L));
        }
    }

    return r;
}

PassedGNEqNC::~PassedGNEqNC()
{
    set<GraphNode*> nodes;
    for (const auto& entry: passed)
    {
        if (wstype == WSET_CDBM)
        {
            nodes.insert(entry.second.begin(), entry.second.end());
        }
        delete [] entry.first;
    }

    for (GraphNode* node: nodes)
    {
        delete node;
    }
}



// -----------------------------------------------------------------------

WaitingListGN::WaitingListGN(const Job& j): job(j), es(j.es)
{
}

WaitingListGN::WaitingListGN(const Job& j, const expl_strategy ex): job(j), es(ex)
{
}



GraphNode* WaitingListGN::get()
{
    GraphNode* s = NULL;
    
    if (!waiting.empty())
    { 
        if (es == ES_DF)
        {
            s = waiting.back();
            waiting.pop_back();
        } else {
            s = waiting.front();
            waiting.pop_front();
        }
    }
    
    return s;   
}

void WaitingListGN::uput(GraphNode* n)
{
    if (find(waiting.begin(), waiting.end(), n) == waiting.end())
    {
        waiting.push_back(n);
    }
}

void WaitingListGN::put(GraphNode* n)
{
    waiting.push_back(n);
}

void WaitingListGN::oput(GraphNode* n)
{
    list<GraphNode*>::const_iterator i = waiting.begin();

    while (i != waiting.end() && (*i)->get_state()->cost_less_than(n->get_state()))
    {
        i++;
    }
    
    waiting.insert(i, n);
}


bool WaitingListGN::empty() const
{
    return waiting.empty();
}

void WaitingListGN::add_restriction(const PResult& r)
{
    if (!r.universe())
    {
        if (job.restrict_update)
        {
            list<GraphNode*>::iterator i;
            i = waiting.begin(); 
            while (i != waiting.end())
            {
                if ((*i)->restriction(r))
                {
                    //(*i)->deallocate_();
                    i = waiting.erase(i);
                    Log.count("restricted");
                } else {
                    i++;
                }
            }
        } 
    }
}

bool WaitingListGN::remove(GraphNode* n)
{
    auto it  = waiting.begin();
    bool r = false; 
    while (it !=  waiting.end())
    {
        if (*it == n)
        {
            it = waiting.erase(it);
            r  = true;
        } else {
            it++;
        }
    }

    return r;
}

// -----------------------------------------------------------------------------
