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

#include <properties.hh>
#include <pwt.hh>
#include <result.hh>
#include <cts.hh>
#include <pstate.hh>
#include <sexpression.hh>
#include <simple_property.hh>
#include <rvalue.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

// -----------------------------------------------------------------------
property::EU::EU(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line), cl(nullptr)
{
}

property::EU::EU(const SExpression& l, const SExpression& r, const CostLimit* c, int line): TemporalProperty(l, r, line), cl(c)
{
}

PResult* property::EU::eval(const PState* s) const
{
    Log.start("EU");

    PResult* r;
    const Job& job = s->job;

    WaitingList* waiting;
    if (!job.has_cost())
    {
        waiting = new SimpleWaitingList(job);
    } else {
        waiting = new CostPriorityQueue(job);
    }
    PassedList& passed = *s->init_passed(*waiting, job.cts.variables.vstate_size());

    PResult& init_constraint = *s->reach_cond();

    PState* current = static_cast<PState*>(s->copy());
    
    // Pre-put the state for better convergence
    passed.put(current);
    waiting->put(current);

    r = s->init_result(psi.eval(current).to_int());
    r->set_approx(RES_UNDER);

    // If we have a cost limit (cost <= lim or cost < lim)
    // We must satisfy it in only two cases: either psi holds or we have non negative costs
    if (cl != nullptr && (!r->empty() || job.non_negative_costs))
    {
        PResult* c = cl->eval(current);
        r->conjunction(*c);
        delete c;
    }

    if (!r->equals(init_constraint))
    {
        if (phi.eval(current).to_int()) 
        {
            while ((current = static_cast<PState*>(waiting->get())) && (!r->equals(init_constraint) || r->ntraces < job.ntraces) && !Job::stop)
            {
                //cout << "===================================" << endl;
                //cout << current << endl;
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

                    bool stop_succs = false;
                    // add all successors to the pw list
                    while ((succ = static_cast<PState*>(i->next())) && !stop_succs)
                    {
                        //cout << "   -- " << succ->in_transition()->label << " -> ";
                        //cout << succ << endl;
                        //cout << *succ;
                        //cout << endl;

                        PResult* rcs = succ->reach_cond();
                        if (cl != nullptr && (job.non_negative_costs || psi.eval(succ).to_int()))
                        {
                            PResult* c = cl->eval(succ);
                            rcs->conjunction(*c);
                            delete c;
                        }

                        if (!r->contains(*rcs))
                        {
                            PWTStatus st = passed.put(succ);
                            //if (st == PWT_NEW)
                            //{
                            //    cout << "      new " << endl;
                            //} else {
                            //    cout << "      old " << endl;
                            //}

                            if (psi.eval(succ).to_int() && (cl == nullptr || !rcs->empty()))
                            {
                                //if (!rcs->empty())
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
                                            waiting->add_restriction(*neg_rcs);
                                            
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
                                    } 
                                    else {
                                        if (st != PWT_NEW)
                                        {
                                            succ->deallocate_();
                                        }
                                    }
                                }

                            } else {
                                //if (!phi_succ->empty() && st == PWT_NEW && !r->contains(*rcs))
                                if (phi.eval(succ).to_int() && st == PWT_NEW)
                                {
                                    //cout << "NEW" << endl;
                                    // We have phi and continue to look for psi
                                    Log.count("succ_new");
                                    waiting->put(succ);
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
        } 
        // if current satisfies neither phi or psi then we are done
        // and the result is undefined
    } else {
        // The initial state satisfies the property
        r->set_trace(current);
        r->compute_trace(job.utility, orig_prop);
    }
    
    if (!Job::stop)
    {
        r->set_approx(RES_EXACT);        
        if (job.is_parametric())
        {
            if (job.ip)
            {
                r->set_approx(RES_INT);        
            } else if (job.ih_convergence) {
                r->set_approx(RES_UNDER_INT);
            } 
        }
    }

    delete waiting;
    delete &init_constraint;
    //passed.info();

    delete &passed;

    Log.stop("EU");
    return r;
}

string property::EU::to_string() const
{
    stringstream s;

    s << "E (" << phi.to_string() << " U " << psi.to_string();
    if (cl != nullptr)
    {
        s << " and " << cl->to_string();
    } 
    s << ")";

    return s.str();
}

const GenericExpression* property::EU::copy(CTS& t) const
{
    return new property::EU(phi.copy(t), psi.copy(t), (cl == nullptr? nullptr: static_cast<const CostLimit*>(cl->copy(t))), decl_line);
}

const GenericExpression* property::EU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::EU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), (cl == nullptr? nullptr: static_cast<const CostLimit*>(cl->abstract_copy(t, S))), decl_line);
}

const GenericExpression* property::EU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::EU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), (cl == nullptr? nullptr: static_cast<const CostLimit*>(cl->instantiate(t, i, v))), decl_line);
}

const GenericExpression* property::EU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::EU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), (cl == nullptr? nullptr: static_cast<const CostLimit*>(cl->eliminate_refs(t, d))), decl_line);
}

bool property::EU::has_cost() const
{
    return (cl != nullptr);
}
