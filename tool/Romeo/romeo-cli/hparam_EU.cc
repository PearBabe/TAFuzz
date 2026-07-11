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

#include <cstdlib>
#include <sstream>
#include <string>

#include <cts.hh>
#include <pwt.hh>
#include <job.hh>
#include <pstate.hh>
#include <properties.hh>
#include <result.hh>
#include <rvalue.hh>
#include <vsclass.hh>
#include <priority_queue.hh>

#include <color_output.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

unsigned property::LtHPBytes::vsize = 0;
    

namespace romeo::property
{
    struct HPNode
    {
        const PState* s;
        vector<HPNode*> preds;
        vector<pair<unsigned, HPNode*>> succs;
        unsigned d;
        bool done;
    
        HPNode(const PState* st) : s(st), preds(), succs(), d(0), done(false) {}
    
        bool key_less(const HPNode& x) const
        {
            return s->key_less(x.s);
        }
    
        //bool operator<(const HPNode& x) const
        //{
        //    return (d + h) < (x.d + x.h);
        //}
    };
    
    struct LtHPN
    {
        bool operator()(const HPNode* N1, const HPNode* N2) const
        {
            return (N1->key_less(*N2));
        }
    };
    
    //struct LtHPNCost
    //{
    //    bool operator()(const HPNode* N1, const HPNode* N2) const
    //    {
    //        return (*N1 < *N2);
    //    }
    //};
}


romeo::property::HPEU::HPEU(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line) {}

romeo::property::HPNode* romeo::property::HPEU::compute_distances(const PState* s) const
{
    // Here we assume that psi does hold initially but phi does

    const PropertyJob& job = *static_cast<const PropertyJob*>(&s->job);
    CTS abs_cts = job.cts.abstract_parameters();

    PropertyJob& j = *(new PropertyJob(job, abs_cts, job.prop));
    if (j.hpeu_sc)
    {
        j.computation_mode = TIMED;
        j.pw = PASSED_EQ;
    } else {
        j.computation_mode = UNTIMED;
    }

    PState* sinit = j.initial_state();
    property::LtHPBytes::vsize = sinit->key_size();

    HPNode* ninit = new HPNode(sinit); 

    list<HPNode*> goals;

    list<HPNode*> waiting;
    set<HPNode*, LtHPN> passed;

    waiting.push_back(ninit);
    passed.insert(ninit);

    HPNode* current = nullptr;

    //cout << "---------------- forward -------------------------" << endl;
    // First compute the SCG or marking graph
    while (!waiting.empty())
    {
        current = waiting.front();
        // cout << *current->s << endl;
        waiting.pop_front();

        const PState* x = current->s;

        PWNiterator* i = const_cast<PState*>(x)->iterator();
        PState* succ;
        
        while ((succ = static_cast<PState*>(i->next())))
        {
            HPNode * nsucc = new HPNode(succ);
            //cout << " -> " << succ << endl; 
            //cout << *succ << endl;

            pair<set<HPNode*, LtHPN>::iterator, bool> i = passed.insert(nsucc);
            // We record predecessors and successors
            (*i.first)->preds.push_back(current);
            current->succs.push_back(pair<unsigned, HPNode*>(succ->in_transition()->id, *i.first));

            if (i.second)
            {
                // New state
                if (psi.eval(succ).to_int())
                {
                    // Record also goal states
                    goals.push_back(nsucc);
                } else {
                    if (phi.eval(succ).to_int())
                    {
                        waiting.push_back(nsucc);
                    }
                }
            } else {
                delete nsucc;
            }
        }
    }

    // Now compute the distances to the goals
    // Breadth-first is crucial
    //cout << "---------------- backward -------------------------" << endl;
    if (!goals.empty())
    {
        for (auto g: goals)
        {
            //cout << *g->s << endl;
            g->done = true;
            waiting.push_back(g);
        }

        while (!waiting.empty())
        {
            //cout << *current->s << endl;
            current = waiting.front();
            waiting.pop_front();
            
            for (auto p: current->preds)
            {
                if (!p->done)
                {
                    // Not visited yet
                    p->done = true;
                    p->d = current->d + 1;
                    waiting.push_back(p);
                } 
            }
        }
    }

    //cout << "computed " << sc << " elements in state (class) graph" <<endl;
    //cout << "added " << sch << " elements to hmap" <<endl;
    // Cleanup

    return ninit;
}


PResult* property::HPEU::eval(const PState* s) const
{
    Log.start("HPEU");
    const Job& job = s->job;
    const CTS& cts = job.cts;

    const bool w = psi.eval(s).to_int();
    PResult* r = s->init_result(w); 

    if (!w)
    {
        if (phi.eval(s).to_int())
        {
            HPNode* ninit = compute_distances(s);
            
            // Restore value normally set by vsstate
            // but here it has changed since the creation of s because of abstraction in compute_distances
            PResult::cts = &cts;

            CostPriorityQueue waiting(job);
            PassedList& passed = *s->init_passed(waiting, job.cts.variables.vstate_size());

            PResult& init_constraint = *s->reach_cond();
            PState* current = static_cast<PState*>(s->copy());

            static_cast<VSState*>(current)->set_hcost(Avalue(ninit->d));
            
            // Pre-put the state for better convergence
            passed.put(current);
            waiting.put(current);

            while ((current = static_cast<PState*>(waiting.get())) && (!r->equals(init_constraint)))
            {
                //cout << "===================================" << endl;
                //cout << current << " " << endl;
                //cout << *current << endl;
                //const PState* x = current;
                //while (x->in_transition() != NULL)
                //{
                //    cout << x->in_transition()->label << ", ";
                //    x = static_cast<const PState*>(x->parent_node());
                //}
                //cout << endl;


                // If we already have as a result all the parameter values for which current is feasible
                // it, or its successors, cannot bring us anything new.
                const PResult* rc = NULL;
                if (job.restrict_new)
                {
                    rc = current->reach_cond();
                }

                Log.count("visited states");

                // When restrict_new is enabled, we check whether the current state can bring some new
                // parameter valuations. If not, we skip it.
                if (!job.restrict_new || !r->contains(*rc))
                {
                    Log.count("states_not_contained");
                    PWNiterator* i = current->iterator();
                    PState* succ;

                    list<const Transition*> trace;
                    const PState* x = current;
                    while (x->in_transition() != nullptr)
                    {
                        trace.push_front(x->in_transition());
                        x = static_cast<const PState*>(x->parent_node());
                    }

                    HPNode* ncurrent = ninit;
                    for (auto t: trace)
                    {
                        bool found = false;
                        for (auto x : ncurrent->succs)
                        {
                            if (x.first == t->id)
                            {
                                found = true;
                                ncurrent = x.second;
                                break;
                            }
                        }
                        if (!found)
                        {
                            cerr << "could not find succ by " << t->label << endl;
                            exit(1);
                        }
                    }

                    bool stop_succs = false;
                    // add all successors to the pw list
                    while ((succ = static_cast<PState*>(i->next())) && !stop_succs)
                    {
                        //cout << "   -> ";
                        //cout << succ << endl;
                        //cout << *succ << endl;

                        const PResult* rcs = succ->reach_cond();
                        if (!r->contains(*rcs))
                        {
                            PWTStatus st = passed.put(succ);

                            if (psi.eval(succ).to_int())
                            {
                                // All good, no need to go further
                                // Add it to the current result
                                r->disjunction(*rcs);

                                // Removing already computed parameter valuations from further explorations
                                if (job.restrict_test)
                                {
                                    PResult* neg_rcs = rcs->copy();
                                    neg_rcs->negation();
                                    if (job.restrict_update)
                                    {
                                        // Go through all waiting states to restrict their possible
                                        // parameter values to not explore what we have already found
                                        waiting.add_restriction(*neg_rcs);
                                        
                                        // We can also remove those valuations from the current state and
                                        // stop generating successors if nothing more can be gained
                                        if (current->restriction(*neg_rcs))
                                        {
                                            stop_succs = true;
                                        }
                                    } else if (job.restrict_new) {
                                        // In that mode, we restrict states when testing them for inclusion
                                        // but keep them whole if adding them to the passed list
                                        passed.add_restriction(neg_rcs);
                                        
                                        // We can also remove those valuations from the current state and
                                        // stop generating successors if nothing more can be gained
                                        if (r->contains(*rc))
                                        {
                                            stop_succs = true;
                                        }
                                    }
                                    delete neg_rcs;
                                }

                                // We cannot gain anything if r is universal so we will stop
                                // and we have a trace (in non-parametric)
                                if (r->equals(init_constraint))
                                {
                                    r->set_trace(succ);

                                    // Compute the trace, removing utility transition that will be deallocated
                                    // when the caller returns 
                                    r->compute_trace(job.utility, orig_prop);
                                } else {
                                    if (st != PWT_NEW)
                                    {
                                        succ->deallocate_();
                                    }
                                }
                            } else {
                                //if (!phi_succ->empty() && st == PWT_NEW && !r->contains(*rcs))
                                if (phi.eval(succ).to_int() && st == PWT_NEW)
                                {
                                    //cout << "NEW" << endl;
                                    // We have phi and continue to look for psi
                                    Log.count("succ_new");
                                    static_cast<VSState*>(succ)->add_dcost(1);

                                    HPNode* nsucc = nullptr;
                                    for (auto x : ncurrent->succs)
                                    {
                                        if (x.first == succ->in_transition()->id)
                                        {
                                            nsucc = x.second;
                                            break;
                                        }
                                    }
                                    if (nsucc == nullptr)
                                    {
                                        cerr << "nsucc: could not find successor by " << succ->in_transition()->label << endl;
                                        exit(1);
                                    }

                                    if (!nsucc->done)
                                    {
                                        // not coreachable
                                        succ->deallocate_();
                                        //cout << "not coreachable" << endl;
                                    } else {
                                        // coreachable
                                        //cout << "found  " << i-> second << endl;
                                        static_cast<VSState*>(succ)->set_hcost(Avalue(nsucc->d));
                                        waiting.put(succ);
                                    }
                                } else {
                                    //cout << "OLD" << endl;
                                    succ->deallocate_();
                                }
                            }
                        }
                        delete rcs;
                    }

                    delete i;
                    current->deallocate_();
                } 

                if (job.restrict_new)
                {
                    delete rc;
                }

            }

            delete &init_constraint;
            //passed.info();

            delete &passed;

        }
    }
    

    Log.stop("HPEU");
    return r;
}

string property::HPEU::to_string() const
{
    stringstream s;

    s << "E (" << phi.to_string() << " U " << psi.to_string() << ") (hyperrectangle parameter abstraction guided)";

    return s.str();
}

const GenericExpression* property::HPEU::copy(CTS& t) const
{
    return new property::HPEU(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::HPEU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::HPEU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::HPEU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::HPEU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::HPEU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::HPEU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}


