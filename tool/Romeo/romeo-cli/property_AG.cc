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
property::AG::AG(const SExpression& r, int line): TemporalProperty(r, r, line)
{
}

PResult* property::AG::eval(const PState* s) const
{
    Log.start("AG");

    PResult* r;
    const Job& job = s->job;

    WaitingList* waiting = new SimpleWaitingList(job);
    PassedList& passed = *s->init_passed(*waiting, job.cts.variables.vstate_size());

    PResult& init_constraint = *s->reach_cond();

    PState* current = static_cast<PState*>(s->copy());
    
    // Pre-put the state for better convergence
    passed.put(current);
    waiting->put(current);

    r = s->init_result(psi.eval(current).to_int());
    r->conjunction(init_constraint);
    r->set_approx(RES_OVER);

    if (!r->empty())
    {
        while ((current = static_cast<PState*>(waiting->get())) && (!r->empty() || r->ntraces < job.ntraces) && !Job::stop)
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

            // When restrict_new is enabled, we check whether the current state still has some admissible
            // parameter valuations. If not, we skip it.
            if (!job.restrict_new || r->intersects(*rc))
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

                    // If the successor does not have any admissible parameter valuation
                    // do not explore it
                    const PResult* rcs = succ->reach_cond();
                    if (r->intersects(*rcs))
                    {
                        PWTStatus st = passed.put(succ);
                        //if (st == PWT_NEW)
                        //{
                        //    cout << "      new " << endl;
                        //} else {
                        //    cout << "      old " << endl;
                        //}

                        if (!psi.eval(succ).to_int())
                        {
                            // We do not have psi. We need to block this path
                            {
                                // All good, no need to go further
                                // Add it to the current result

                                PResult* neg_rcs = rcs->copy();
                                neg_rcs->negation();
                                r->conjunction(*neg_rcs);

                                // Removing already computed parameter valuations from further explorations
                                if (job.restrict_test)
                                {
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
                                }

                                delete neg_rcs;

                                // We cannot gain anything if r is empty so we will stop
                                // and we have a trace (mostly in non-parametric)
                                if (r->empty())
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
                            // psi holds, just continue
                            if (st == PWT_NEW)
                            {
                                //cout << "NEW" << endl;
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
                r->set_approx(RES_OVER_INT);
            } 
        }
    }

    delete waiting;
    delete &init_constraint;
    //passed.info();

    delete &passed;

    Log.stop("AG");
    return r;
}

string property::AG::to_string() const
{
    stringstream s;

    s << "AG (" << psi.to_string() << ")";

    return s.str();
}

const GenericExpression* property::AG::copy(CTS& t) const
{
    return new property::AG(psi.copy(t), decl_line);
}

const GenericExpression* property::AG::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::AG(psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::AG::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::AG(psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::AG::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::AG(psi.eliminate_refs(t, d), decl_line);
}

