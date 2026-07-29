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
#include <job.hh>
#include <pstate.hh>
#include <property.hh>
#include <control_reach.hh>
#include <result.hh>
#include <dresult.hh>
#include <rvalue.hh>
#include <graph_node.hh>
#include <control_result.hh>

#include <color_output.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;




property::ControlReach::ControlReach(const SExpression& l, const SExpression& r, control_mode s, int line): TemporalProperty(l, r, line), mode(s) {}

bool property::ControlReach::is_control() const
{
    return (mode != BACKWARD_MINCOST);
}

PResult* property::ControlReach::eval(const PState* s) const
{
    Log.start("ControlReach");
    
    const Job& job = s->job;

    WaitingListGN fwd(job);
    // WaitingListGN bwd(job);
    PriorityQueueGN<LtBackGNHistory> bwd(job);

    PassedGN& passed = *s->init_passed_gn(fwd, bwd);

    PResult* r; 

    const bool w = psi.eval(s).to_int();

    GraphNode* nothing = nullptr;
    GraphNode* initg = passed.put(static_cast<PState*>(s->copy()), nothing, w);
    if (!w)
    { 
        GraphNode* current;
        if (job.has_cost())
        {
            r = s->init_cost_result();
        } else {
            r = s->init_result(false);
        }
        fwd.put(initg);

        while ((!fwd.empty() || !bwd.empty()) && !Job::stop)
        {
            if ((current = bwd.get()))
            {
                // cout << "=================================================================================" <<endl;
                // cout << "bwd: " << endl << *current->get_state() << endl;
                // const PWNode* y =current->get_state();
                // while (y->in_transition() != NULL)
                // {
                //     cout << y->in_transition()->label << " ";
                //     y = y->parent_node();
                // }
                // cout << endl;

                // Backward propagation

                bool res = (mode == CONTROL_SAFE)? current->get_state()->update_safe(current): current->get_state()->update_reach(current);
                //cout << "update -> " << res << endl;
                if (res)
                {
                    list<PredInfo>::iterator i;
                    for (i = current->preds.begin(); i != current->preds.end(); i++)
                    {
                        //cout << " add pred " << endl;
                        //cout << *(*i)->get_state() << endl;
                        list<SuccInfo>::iterator j;
                        for (j = i->node->succs.begin(); j != i->node->succs.end(); j++)
                        {
                            if (j->node == current)
                            {
                                i->node->set_outdated(*j);
                                //j->up_to_date = false;
                            }
                        }
                        bwd.uput(i->node);
                    }

                    if (current == initg)
                    {
                        r = initg->update_result(r);

                        // Truncates results... why?
                        //if (job.restrict_update)
                        //{
                        //    PResult* notr = r->copy();
                        //    notr->negation();
                        //    fwd.add_restriction(*notr);
                        //    bwd.add_restriction(*notr);
                        //    delete notr;
                        //}
                    }
                }
            } else {
                if ((current = fwd.get()))
                {
                    // cout << "=================================================================================" <<endl;
                    // cout << "fwd: " << endl << *current->get_state() << endl;
                    // const PWNode* y =current->get_state();
                    // while (y->in_transition() != NULL)
                    // {
                    //     cout << y->in_transition()->label << " ";
                    //     y = y->parent_node();
                    // }
                    // cout << endl;

                    // Forward exploration
                    PState* x = current->get_state();
                    PWNiterator* i = x->iterator();
                    PState* succ;
                    
                    bool propagate = false;

                    // compute all successors 
                    // it is crucial that all firable successors are indeed computed before
                    // the state has a chance to call update (in the backward propagation).
                    while ((succ = static_cast<PState*>(i->next())))
                    {
                        const bool psi_succ = psi.eval(succ).to_int();

                        GraphNode * gsucc = passed.put(succ, current, psi_succ);

                        //cout << "succ is " << endl;
                        //cout << *succ << endl;
                        
                        // No convergence and not a goal state: explore further
                        if (!psi_succ)
                        {
                            if (gsucc->get_state() == succ)
                            {
                                if (phi.eval(succ).to_int())
                                { 
                                    // Continue only if the path invariant phi is
                                    // satisfied and psi is not satisfied.
                                    // Otherwise, the succ stays but by
                                    // construction its winning status is empty / false
                                    fwd.put(gsucc);
                                }
                            }
                        }

                        // The passed set owns the canonical graph state.  A
                        // converged temporary successor is not inserted and
                        // must be released for both goal and non-goal cases.
                        if (gsucc->get_state() != succ)
                        {
                            delete succ;
                        }

                        // The new (or the one to which we converge) is winning: propagate the info
                        if (gsucc->has_winning())
                        {
                            //cout << "successor has winning" << endl;
                            //cout << *gsucc->get_state() << endl;
                            propagate = true;
                        }
                    }

                    delete i;

                    if (propagate)
                    {
                        bwd.uput(current);
                    }
                } 
            }
        }

        if (Job::stop)
        {
            r->set_approx(RES_UNKNOWN);
        }
    } else {
        if (job.has_cost())
        {
            r = new CostResult(Avalue(0));
        } else {
            r = s->init_result(true);
        }
    }

//  CtrlBool* res = new CtrlBool(r, passed, reach);
    if (!job.notrace && mode == CONTROL_SAFE)
    {
        ControlResult::compute_safety_strategy(passed.wstype, initg);
    }

    ControlResult* res = new ControlResult(r, (mode != CONTROL_SAFE), passed);
    delete &passed;

    Log.stop("ControlReach");
    return res;
}

string property::ControlReach::to_string() const
{
    stringstream s;

    if (mode == CONTROL_SAFE)
    {
        s << "safety ";
    }
    s << "control (" << phi.to_string() << " U " << psi.to_string() << ")";

    return s.str();
}

const GenericExpression* property::ControlReach::copy(CTS& t) const
{
    return new property::ControlReach(phi.copy(t), psi.copy(t), mode, decl_line);
}

const GenericExpression* property::ControlReach::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::ControlReach(phi.abstract_copy(t, S), psi.abstract_copy(t, S), mode, decl_line);
}

const GenericExpression* property::ControlReach::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::ControlReach(phi.instantiate(t, i, v), psi.instantiate(t, i, v), mode, decl_line);
}

const GenericExpression* property::ControlReach::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::ControlReach(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), mode, decl_line);
}

bool property::ControlReach::has_cost() const
{
    return mode == CONTROL_OPTIMAL;
}
// -----------------------------------------------------------------------------
