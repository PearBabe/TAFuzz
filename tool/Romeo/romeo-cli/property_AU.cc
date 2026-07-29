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

#include <properties.hh>
#include <pwt.hh>
#include <result.hh>
#include <cts.hh>
#include <pstate.hh>
#include <rvalue.hh>

using namespace romeo;
using namespace std;

// -----------------------------------------------------------------------
property::AU::AU(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line) {}

PResult* property::AU::eval(const PState* s) const
{
    const Job& job = s->job;

    SimpleWaitingList waiting(job);
    PassedList& passed = *s->init_passed(waiting, job.cts.variables.vstate_size(), true);

    PResult* r = s->reach_cond();
    r->set_approx(RES_UNKNOWN);
    // PResult* ru = s->init_result(false);


    PState* current = static_cast<PState*>(s->copy());
    
    waiting.put(current);
    while (!r->empty() && (current = static_cast<PState*>(waiting.get())) && !Job::stop)
    {
        // cout << "===================================" << endl;
        // cout << current << endl;
        // cout << *current << endl;
        // const PState* x = current;
        // while (x->in_transition() != NULL)
        // {
        //     cout << x->in_transition()->label << ", ";
        //     x = static_cast<const PState*>(x->parent_node());
        // }
        // cout << endl;

        bool block = false;
        const PWTStatus status = passed.put(current);

        if (!psi.eval(current).to_int())
        {
            // If we can delay forever then it is bad
            if (current->can_delay_forever())
            {
                block = true;
            } else {
                // We have not psi
                if (phi.eval(current).to_int()) 
                {
                    // But we have phi, continue...
                    if (status == PWT_IN_TRACE || status == PWT_NEW_IN_TRACE)
                    {
                        // ... unless this is a phi-loop
                        block = true;
                        // cout << "    phi-loop" << endl;
                    } else {
                        if (status == PWT_NEW)
                        {
                        // cout << "    new" << endl;
                            PWNiterator* i = current->iterator();
                            PState* succ;
                    
                            // For each successor
                            block = true;
                            while ((succ = static_cast<PState*>(i->next())))
                            {
                                waiting.put(succ);

                                // There is at least one successor
                                block = false;
                            }
                            delete i;
                        } else {
                            // if not new then convergence to some already explored state
                        // cout << "    old" << endl;
                            current->deallocate_();
                        }
                    }
                } else {
                    // Neither psi nor phi: stop here
                    block = true;
                        // cout << "    no phi, no psi" << endl;
                }
            }

        } else {
            // All good no need to go further
            // PResult* psir = current->init_result(true);
            // ru->disjunction(*psir);

            // delete psir;
            current->deallocate_();
        }

        // This path is no good, block it
        if (block)
        {
            // Unreachability condition
            const PResult& not_rcs = current->reach_cond()->negation();

            r->conjunction(not_rcs);
            if (job.restrict_test)
            {
                waiting.add_restriction(not_rcs);
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
    }

    // r->conjunction(*ru);
    // delete ru;
    //passed.info();

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
                r->set_approx(RES_UNDER_INT);
            } 
        }
    }    
    
    delete &passed;

    return r;
}

string property::AU::to_string() const
{
    stringstream s;

    s << "A (" << phi.to_string() << " U " << psi.to_string() << ")";

    return s.str();
}

const GenericExpression* property::AU::copy(CTS& t) const
{
    return new property::AU(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::AU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::AU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::AU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::AU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::AU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::AU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}

