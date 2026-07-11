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
#include <stdexcept>
#include <sstream>
#include <string>

#include <cts.hh>
#include <job.hh>
#include <pstate.hh>
#include <property.hh>
#include <backward_mincost.hh>
#include <priority_queue.hh>
#include <result.hh>
#include <dresult.hh>
#include <control_result.hh>
#include <rvalue.hh>

#include <color_output.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

namespace
{
    const BVZone& backward_zone(const GraphNode& node)
    {
        const BVZone* zone = dynamic_cast<const BVZone*>(node.get_state());

        if (zone == nullptr)
        {
            throw logic_error("BackwardMincost received a non-BVZone graph node");
        }

        return *zone;
    }

    PState* property_state(PWNode* node)
    {
        PState* state = dynamic_cast<PState*>(node);

        if (state == nullptr)
        {
            delete node;
            throw logic_error("BackwardMincost iterator returned a non-PState node");
        }

        return state;
    }
}

struct LtBVZones
{
    bool operator()(const GraphNode* N1, const GraphNode* N2) const
    {
        const SizeDigest d1 = backward_zone(*N1).get_tsize();
        const SizeDigest d2 = backward_zone(*N2).get_tsize();
        
        return (d2 < d1);
    }
};

property::BackwardMincost::BackwardMincost(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line) {}

bool property::BackwardMincost::has_cost() const
{
    // Preserve TemporalProperty's validation that the path condition does not
    // itself depend on the accumulated cost.  The return value here describes
    // the numeric result/state representation, not only predicate syntax.
    (void) TemporalProperty::has_cost();
    return true;
}

bool property::BackwardMincost::uses_backward_mincost_zones() const
{
    return true;
}

PResult* property::BackwardMincost::eval(const PState* s) const
{
    Log.start("BackwardMincost");
    
    const Job& job = s->job;

    if (!job.non_negative_costs)
    {
        cerr << warning_tag(color_output)
             << "Backward mincost with signed costs assumes that all goal-reaching costs are lower-bounded; negative cycles are not detected."
             << endl;
    }

    PriorityQueueGN<LtBVZones> fwd(job);
    PriorityQueueGN<LtBackGN> bwd(job);
    //WaitingListGN bwd(job, ES_BF);

    PassedGN& passed = *s->init_passed_gn(fwd, bwd);

    PResult* r; 

    const bool w = psi.eval(s).to_int();

    if (!w)
    { 
        GraphNode* current;
        GraphNode* nothing = nullptr;
        GraphNode* initg = passed.put(property_state(s->copy()), nothing, false);
        r = s->init_cost_result();
        fwd.put(initg);

        bool stop = false;
        while ((!fwd.empty() || !bwd.empty()) && !stop && !Job::stop)
        //while (!r && (!fwd.empty() || !bwd.empty())) // early termination
        {
            if ((current = fwd.get()))
            {
                Log.start("fwd");
                //cout << "=================================================================================" <<endl;
                //cout << "fwd: " << current << endl << *current->get_state() << endl;
                //const PWNode* y =current->get_state();
                //while (y->in_transition() != NULL)
                //{
                //    cout << y->in_transition()->label << " ";
                //    y = y->parent_node();
                //}
                //cout << endl;

                // Forward exploration
                PState* x = current->get_state();

                //if (x->get_offset_cost() > static_cast<CostResult*>(r)->cost())
                if (false)
                {
                    // Stop here!
                    stop = true;
                } else {

                    PWNiterator* i = x->iterator();
                    PWNode* next;
                    
                    bool propagate = false;

                    // compute all successors 
                    // it is crucial that all firable successors are indeed computed before
                    // the state has a chance to call update (in the backward propagation).
                    while ((next = i->next()))
                    {
                        PState* succ = property_state(next);
                        const bool psi_succ = psi.eval(succ).to_int();

                        GraphNode * gsucc = passed.put(succ, current, psi_succ);

                        //cout << "-----------------------------------------------" << endl;
                        //cout << "succ is " << gsucc << endl;
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
                            } else {
                                //succ->deallocate();
                                delete succ;
                            }
                        } else {
                            if (gsucc->get_state() != succ)
                            {
                                //succ->deallocate();
                                delete succ;
                            }
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
                Log.stop("fwd");
            } else {
                if ((current = bwd.get()))
                {
                    Log.start("bwd");
                    //cout << "=================================================================================" <<endl;
                    //cout << "bwd: "<< current << endl << *current->get_state() << endl;
                    //const PWNode* y =current->get_state();
                    //while (y->in_transition() != NULL)
                    //{
                    //    cout << y->in_transition()->label << " ";
                    //    y = y->parent_node();
                    //}
                    //cout << endl;

                    // Backward propagation

                    bool res = current->get_state()->update_reach(current);
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
                    Log.stop("bwd");
                } 
            }
        }

        if (Job::stop)
        {
            r->set_approx(RES_UNKNOWN);
        }
    } else {
        r = new CostResult(Avalue(0));
    }

//  CtrlBool* res = new CtrlBool(r, passed, reach);
    ControlResult* res = new ControlResult(r, true, passed);

    delete &passed;

    Log.stop("BackwardMincost");
    return res;
}

string property::BackwardMincost::to_string() const
{
    stringstream s;

    s << "backward mincost (" << phi.to_string() << " U " << psi.to_string() << ")";

    return s.str();
}

const GenericExpression* property::BackwardMincost::copy(CTS& t) const
{
    return new property::BackwardMincost(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::BackwardMincost::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::BackwardMincost(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::BackwardMincost::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::BackwardMincost(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::BackwardMincost::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::BackwardMincost(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}
