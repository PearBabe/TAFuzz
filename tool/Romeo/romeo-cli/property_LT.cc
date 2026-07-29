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

#include <sstream>

#include <properties.hh>
#include <pwt.hh>
#include <result.hh>
#include <cts.hh>
#include <pstate.hh>
#include <color_output.hh>
#include <rvalue.hh>

using namespace std;
using namespace romeo;

// -----------------------------------------------------------------------
property::LT::LT(const SExpression& l, const SExpression& r, int line): AU(l, r, line) {}

PResult* property::LT::eval(const PState* s) const
{
    const Job& job = s->job;

    SimpleWaitingList waiting_phi(job);
    PassedList& passed_phi = *s->init_passed(waiting_phi, job.cts.variables.vstate_size());

    SimpleWaitingList waiting_psi(job);
    PassedList& passed_psi = *s->init_passed(waiting_psi, job.cts.variables.vstate_size(), true);

    PResult* r = s->reach_cond();
    r->set_approx(RES_OVER);

    PState* current = static_cast<PState*>(s->copy());
    
    passed_phi.put(current);
    if (!phi.eval(current).to_int())
    {
        waiting_phi.put(current);
    } else {
        waiting_psi.put(current);
    }

    while (!r->empty() && current != NULL && !Job::stop)
    {
        if ((current = static_cast<PState*>(waiting_psi.get())))
        {
            // cout << "------------------------- wpsi ----------------------" << endl;
            // cout << *current << endl;
            // const PState* x = current;
            // while (x->in_transition() != NULL)
            // {
            //     cout << x->in_transition()->label << ", ";
            //     x = static_cast<const PState*>(x->parent_node());
            // }
            // cout << endl;

            PWTStatus status = passed_psi.put(current);
            
            // We are looking for psi
            if (!psi.eval(current).to_int()) // not found, continue with psi
            {
                bool block = true;

                if (!current->can_delay_forever()) // otherwise block
                {
                    if (status == PWT_NEW)
                    {
                        PWNiterator* i = current->iterator();
                        PState* succ;
                    
                        // For each successor
                        while ((succ = static_cast<PState*>(i->next())))
                        {
                            waiting_psi.put(succ);

                            // There is at least one successor
                            block = false;
                        }
                        delete i;
                    } else {
                        if (status != PWT_IN_TRACE && status != PWT_NEW_IN_TRACE)
                        {
                            // Not a phi-loop: convergence to some already explored state
                            current->deallocate_();
                            block = false;
                        } 
                    }
                }

                // This path is no good, block it
                if (block)
                {
                    // Unreachability condition
                    const PResult& not_rcs = current->reach_cond()->negation();

                    r->conjunction(not_rcs);

                    if (job.restrict_test)
                    {
                        waiting_psi.add_restriction(not_rcs);
                        waiting_phi.add_restriction(not_rcs);
                    }
                    delete &not_rcs;

                    if (r->empty())
                    {
                        // The result is false (with parameters this is the empty polyhedron)
                        // We have a trace in non-parametric mode.
                        r->set_trace(current);
                    } else {
                        // Blocked this path, no need to keep this state allocated
                        current->deallocate_();
                    }
                }  

            } else {
                // psi was found continue with phi for the successors
                if (status == PWT_NEW)
                {
                    passed_phi.put(current);
                    waiting_phi.put(current);
                } else {
                    current->deallocate_();
                }
            }
        } else {
            if ((current = static_cast<PState*>(waiting_phi.get())))
            {
                // cout << "------------------------- wphi ----------------------" << endl;
                // cout << *current << endl;
                // const PState* x = current;
                // while (x->in_transition() != NULL)
                // {
                //     cout << x->in_transition()->label << ", ";
                //     x = static_cast<const PState*>(x->parent_node());
                // }
                // cout << endl;

                PWNiterator* i = current->iterator();
                PState* succ;
                
                // For each successor
                while ((succ = static_cast<PState*>(i->next())))
                {
                    PWTStatus st = passed_phi.put(succ);

                    if (st == PWT_NEW)
                    {
                        if (!phi.eval(succ).to_int())
                        {
                            waiting_phi.put(succ);
                        } else {
                            succ->trace_root = current;
                            succ->steps = 0;
                            waiting_psi.put(succ);
                        }
                    } else {
                        succ->deallocate_();
                    }
                }

                delete i;
                current->deallocate_();
            }
        }
    }

    //pw_phi->info();
    //pw_psi->info();

    // Compute the trace, removing utility transition that will be deallocated
    // when the caller returns 
    r->compute_trace(job.utility, orig_prop);

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
    
    delete &passed_phi;
    delete &passed_psi;

    return r;
}

string property::LT::to_string() const
{
    stringstream s;

    s << phi.to_string() << " --> " << psi.to_string();

    return s.str();
}

const GenericExpression* property::LT::copy(CTS& t) const
{
    return new property::LT(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::LT::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::LT(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::LT::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::LT(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::LT::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::LT(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}

