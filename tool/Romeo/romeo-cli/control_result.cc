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

#include <list>
#include <utility>

#include "control_reach.hh"
#include "dbm.hh"
#include "graph_node.hh"
#include "vszpoly.hh"
#include <pwt.hh>
#include <control_result.hh>
#include <cts.hh>
#include <transition.hh>
#include <color_output.hh>

#include <vsstate.hh>
#include <vzone.hh>
#include <time_interval.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

ControlResult::ControlResult(PResult* ir, bool r, wset_type t): reach(r), internal_result(ir), wstype(t)
{
    if (!reach)
    {
        ir->negation();
    }
}

ControlResult::ControlResult(PResult* ir, bool r, const PassedGN& p): reach(r), internal_result(ir), wstype(p.wstype)
{
    if (!reach)
    {
        ir->negation();
    }

    strategy = p.get_strategy(r? property::CONTROL_REACH: property::CONTROL_SAFE);
}

ControlResult::~ControlResult()
{
    delete internal_result;
    internal_result = nullptr;

    // PassedGN::get_strategy allocates an independent copy of every discrete
    // key.  CDBM reachability/control currently produces no LocalStrategy
    // domains (that code is disabled), so the list elements contain no owned
    // priced-zone payloads to release here.
    for (const auto& entry: strategy)
    {
        delete [] entry.first;
    }
    strategy.clear();
}

PResult* ControlResult::copy() const
{
    return new ControlResult(internal_result->copy(), reach, wstype);
}

Polyhedron ControlResult::constraint() const
{
    return internal_result->constraint();
}

PResult& ControlResult::conjunction(const PResult& r)
{
    internal_result->conjunction(r);
    return *this;
}

PResult& ControlResult::disjunction(const PResult& r)
{
    internal_result->disjunction(r);
    return *this;
}

PResult& ControlResult::negation()
{
    internal_result->negation();
    return *this;
}

bool ControlResult::empty() const
{
    return internal_result->empty();
}

bool ControlResult::universe() const
{
    return internal_result->universe();
}

bool ControlResult::equals(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test ControlResults for equality" << endl;
    exit(1);
}

bool ControlResult::contains(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test ControlResults for inclusion" << endl;
    exit(1);
}

bool ControlResult::intersects(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test ControlResults for intersection" << endl;
    exit(1);
}


string ControlResult::to_string() const
{
    return internal_result->to_string();
}

string ControlResult::get_trace() const
{    
    stringstream s;
 
    //s << endl;
    if (strategy.empty())
    {
        s << endl << "No (partial) strategy for the ";
        if (reach)
        {
            s << "controller." << endl;
        } else {
            s << "environment." << endl;
        }
    } else {
        if (reach)
        {
            if (!internal_result->empty())
            {
                s << endl << "Strategy ";
            } else {
                s << endl << "Partial strategy ";
            }
            s << "for the controller:" << endl;
        } else {
            if (!internal_result->empty())
            {
                s << endl << "Strategy ";
            } else {
                s << endl << "Partial strategy ";
            }
            s << "for the controller (play any of proposed actions):" << endl;
        }
 
        for (auto si: strategy)
        {
            // Discrete part
            s << "when " << cts->variables.value_to_string(si.first) << endl;

            // Action part
            if (si.second.empty())
            {
                s << "  wait";
            } else {
                bool second = false;
                for (auto sj: si.second)
                {
                    if (second)
                    {
                        s << endl;
                    } else {
                        second = true;
                    }
                    const Transition* t = sj.action;
                    if (wstype == WSET_UNTIMED)
                    {
                        if (t != nullptr)
                        {
                            if (sj.type != STRAT_ENV_ACTION)
                            {
                                s << "  do " << t->label;
                                if (!sj.domain.wb)
                                {
                                    s << " immediately";
                                }
                            } else {
                                s << "  wait for " << t->label << " to happen";
                            }
                        } else {
                            s << "  wait";
                        }
                    } else {
                        string domain;
                        vector<string> labels;
                        if (wstype == WSET_POLY)
                        {
                            for (list<Parameter>::const_iterator k=cts->begin_parameters(); k != cts->end_parameters(); k++)
                            {
                                cvalue v;
                                if (!k->constant(v))
                                    labels.push_back(k->label);
                            }
    
                            const unsigned NP = cts->nparams();
     
                            for (auto tk: sj.en)
                            {
                                labels.push_back(tk->label);
                            }

                            if (cts->has_cost())
                            {
                                labels.push_back("#cost");
                            }
    
                            domain = sj.domain.wp->to_string_labels(labels, NP);
    
                        } else if (wstype == WSET_DBM) {
                            labels.push_back("0");
                            for (auto tk: sj.en)
                            {
                                labels.push_back(tk->label);
                            }
    
                            domain = sj.domain.wd->to_string_labels(labels);
                        }
    
                        if (sj.type == STRAT_ACTION)
                        {
                            s << "with: " << endl << domain << endl; 
                            if (t != nullptr)
                            {
                                s << "   do " << t->label;
                            } else {
                                s << "   wait";
                            }
                            s << endl << endl;
                        } else if (sj.type == STRAT_ENV_ACTION) {
                            s << "with: " << endl << domain << endl; 
                            if (t != nullptr)
                            {
                                s << "   wait for opponent to play " << t->label;
                            } else {
                                s << "   wait";
                            }
                            s << endl << endl;
                        } else if (sj.type == STRAT_ACTION_CLASS) {
                            s << "if initialisation results in: " << endl << domain << endl; 
                            if (t != nullptr)
                            {
                                s << "   (wait if necessary and) do " << t->label;
                            } else {
                                s << "   wait"; // should not be possible
                            }
                            s << endl << endl;

                        } else {
                            if (!sj.ctr.empty())
                            {
                                if (t == nullptr)
                                {
                                    s << "initialize ";
                                } else {
                                    s << "arriving with " << t->label << ", initialize ";
                                }
                                bool comma = false;
                                for (auto tk: sj.ctr)
                                {
                                    if (comma)
                                    {
                                        s << ", ";
                                    } else {
                                        comma = true;
                                    }
                                    s << tk->label;
                                }

                                s << " such that:" << endl << domain << endl;
                            } 
                            //else {
                            //    s << "  wait" << endl;
                            //}
                        }
                    }
                }
            }
            s << endl;
        }
    }
 
    return colorize(color_output, s.str(), AC_CYAN);
}

void ControlResult::compute_safety_strategy(wset_type wstype, GraphNode* initg)
{
    list<GraphNode*> waiting;
    set<GraphNode*> passed;

    waiting.push_back(initg);
    passed.insert(initg);
    
    while (!waiting.empty())
    {
        GraphNode* n = waiting.front();
        waiting.pop_front();
 
        if (wstype == WSET_UNTIMED)
        {
            bool winu = true;
            bool winnau = true;
            bool urgent = false;
            list<const Transition*> cs; // controllable winning transitions
            list<const Transition*> uas; // ineluctable uncontrollable winning transitions
            for (auto it: n->succs)
            {
                // We have the winning states for the environment
                const bool wins = !it.node->winning.wb;
                const unsigned int ctrl_flags = it.trans->control;
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    if (wins)
                    {
                        // A winning controllable transition
                        cs.push_back(it.trans);
                    }
                } else {
                    if (wins)
                    {
                        if (ctrl_flags & CTRL_FORCED)
                        {
                            // A forced winning uncontrollable transition
                            uas.push_back(it.trans);
                        }
                    } else {
                        // There is a losing uncontrollable transition
                        winu = false;

                        if (ctrl_flags & CTRL_DELAYED)
                        {
                            // This losing uncontrollable transition
                            // can be be avoided if we are quick
                            urgent = true;
                        } else {
                            // This losing uncontrollable transition
                            // cannot be avoided
                            winnau = false;
                        }
                    }
                }
            }

            // No uncontrollable unavoidable losing transition:
            // all transitions in cs are winning, possibly with urgency
            if (winnau)
            {
                for (auto t: cs)
                {
                    LocalStrategy st;
                    st.type = STRAT_ACTION;
                    st.action = t;
                    st.domain.wb = !urgent;
                    n->strategy.push_back(st);
                }
            }
            
            if (winu)
            {
                // No uncontrollable losing transitions at all; also all of uas is winning
                for (auto t: uas)
                {
                    LocalStrategy st;
                    st.action = t;
                    st.type = STRAT_ENV_ACTION;
                    st.domain.wb = true;
                    n->strategy.push_back(st);
                }
            }

        } else if (wstype == WSET_DBM) {
            const VZone* sn = static_cast<const VZone*>(n->get_state());
            DBMUnion Bad(sn->nen() + 1);

            list<pair<const Transition*, DBMUnion>> cs; 
            list<pair<const Transition*, DBMUnion>> aus; 

            for (auto it: n->succs)
            {
                const unsigned int ctrl_flags = it.trans->control;
                const VZone* s = static_cast<const VZone*>(it.node->get_state());
                // We actually have losing states
                DBMUnion W(it.node->winning.wd->complement());
                W.intersection_assign(*s->get_domain());
                
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    DBMUnion P(sn->predecessor(s, W, it.trans, false));
                    
                    if (!P.empty())
                    {
                        cs.push_back(pair<const Transition*, DBMUnion>(it.trans, P));
                    }
                } else {
                    Bad.add_reduce(sn->predecessor(s, *it.node->winning.wd, it.trans, false));
                    if (!it.trans->timing->unbounded)
                    {
                        DBMUnion P(sn->predecessor(s, W, it.trans, true));

                        if (!P.empty())
                        {
                            aus.push_back(pair<const Transition*, DBMUnion>(it.trans, P));
                        }
                    }
                }
            }

            DBMUnion NotBad(Bad.complement());
            
            // We can always try to do those, even if the state is not winning
            // But when this is winning, we would like have only the winning part
            for (auto p: cs)
            {
                p.second.intersection_assign(NotBad);

                if (!p.second.empty())
                {
                    LocalStrategy st;
                    for (unsigned i = 0; i < sn->nen(); i++)
                    {
                        st.en.push_back(sn->get_enabled(i));
                    }
                    st.action = p.first;
                    st.type = STRAT_ACTION;
                    st.domain.wd = new DBMUnion(p.second);
                    n->strategy.push_back(st);
                }
            }
            
            // We can count on those only if the opponent does not have a better opportunity
            for (auto p: aus)
            {
                p.second.intersection_assign(NotBad);

                if (!p.second.empty())
                {
                    LocalStrategy st;
                    for (unsigned i = 0; i < sn->nen(); i++)
                    {
                        st.en.push_back(sn->get_enabled(i));
                    }
                    st.action = p.first;
                    st.type = STRAT_ENV_ACTION;
                    st.domain.wd = new DBMUnion(p.second);
                    n->strategy.push_back(st);
                }
            }
        } else if (wstype == WSET_POLY) {
            const VSZPoly* sn = static_cast<const VSZPoly*>(n->get_state());
            Polyhedron Bad(sn->nen(), false);

            list<pair<const Transition*, Polyhedron>> cs; 
            list<pair<const Transition*, Polyhedron>> aus; 

            for (auto it: n->succs)
            {
                const unsigned int ctrl_flags = it.trans->control;
                const VSZPoly* s = static_cast<const VSZPoly*>(it.node->get_state());
                // We actually have losing states
                Polyhedron W(*it.node->winning.wp);
                W.negation_assign();
                W.intersection_assign(*s->get_domain());
                
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    Polyhedron P(sn->predecessor(s, W, it.trans, false));
                    
                    if (!P.empty())
                    {
                        cs.push_back(pair<const Transition*, Polyhedron>(it.trans, P));
                    }
                } else {
                    Bad.add_reduce(sn->predecessor(s, *it.node->winning.wp, it.trans, false));
                    if (!it.trans->timing->unbounded)
                    {
                        Polyhedron P(sn->predecessor(s, W, it.trans, true));

                        if (!P.empty())
                        {
                            aus.push_back(pair<const Transition*, Polyhedron>(it.trans, P));
                        }
                    }
                }
            }

            Polyhedron NotBad(Bad);
            NotBad.negation_assign();
            
            // We can always try to do those, even if the state is not winning
            // But when this is winning, we would like have only the winning part
            for (auto p: cs)
            {
                // cout << p.first->label << endl;
                p.second.intersection_assign(NotBad);

                if (!p.second.empty())
                {
                    LocalStrategy st;
                    for (unsigned i = 0; i < sn->nen(); i++)
                    {
                        st.en.push_back(sn->get_enabled(i));
                    }
                    st.type = STRAT_ACTION;
                    st.action = p.first;
                    st.domain.wp = new Polyhedron(p.second);
                    n->strategy.push_back(st);
                }
            }
            
            // We can count on those only if the opponent does not have a better opportunity
            for (auto p: aus)
            {
                p.second.intersection_assign(NotBad);

                if (!p.second.empty())
                {
                    LocalStrategy st;
                    for (unsigned i = 0; i < sn->nen(); i++)
                    {
                        st.en.push_back(sn->get_enabled(i));
                    }
                    st.action = p.first;
                    st.type = STRAT_ENV_ACTION;
                    st.domain.wp = new Polyhedron(p.second);
                    n->strategy.push_back(st);
                }
            }
        } else {
            cerr << error_tag(color_output) << "Unhandled state representation for safety strategy generation." << endl;
            exit(1);
            
        }

        for (auto it: n->succs)
        {
            if (!passed.count(it.node))
            {
                passed.insert(it.node);
                waiting.push_back(it.node);
            }
        }
    } 
}
