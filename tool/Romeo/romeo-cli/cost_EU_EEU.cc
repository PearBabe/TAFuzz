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
#include <dresult.hh>
#include <cts.hh>
#include <pstate.hh>
#include <vsstate.hh>
#include <rvalue.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

// -----------------------------------------------------------------------
property::CostEU_EEU::CostEU_EEU(const SExpression& l, const SExpression& r, const PState* s, int line): TemporalProperty(l, r, line), init(s) {}

PResult* property::CostEU_EEU::eval(const PState* s) const
{
    Log.start("CostEU_EEU");
    
    CostResult* r = static_cast<CostResult*>(s->init_cost_result());
    const Job& job = s->job;

    PState* current = static_cast<PState*>(s->copy());

    CostPriorityQueue waiting(job);
    PassedList& passed = *s->init_passed(waiting, job.cts.variables.vstate_size(), false);

    // Pre-put the state for better convergence
    passed.put(current);
    waiting.put(current);
    
    if (!psi.eval(current).to_int())
    {
        if (phi.eval(current).to_int()) 
        {
            while ((current = const_cast<PState*>(static_cast<const PState*>(waiting.get()))) && (!job.non_negative_costs || r->undef() || (job.non_negative_costs && r->cost() == current->min_cost() && r->ntraces < job.ntraces)))
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

                // First check whether this is the goal
                const bool psirb = psi.eval(current).to_int(); 

                if (psirb)
                {
                    CostResult* curc = current->current_cost();
                    if (r->update(*curc, job.ntraces > 1))
                    {
                        r->set_trace(current);
                        
                        // Compute the trace, removing utility transition that will be deallocated
                        // when the caller returns 
                        if (job.non_negative_costs)
                        {
                            r->compute_trace(job.utility, orig_prop);
                        } // if costs can be negative then we will have only one trace in the end
                    } 
                    delete curc;
                }
                
                if (!psirb)
                {
                    PWNiterator* i = current->iterator();
                    PState* succ;

                    // add all successors to the pw list
                    while ((succ = static_cast<PState*>(i->next())))
                    {
                        PWTStatus st = passed.put(succ);
                        //cout << "----------------------------------" << endl;
                        //cout << *succ << endl;

                        //if (!phi_succ->empty() && (st == PWT_NEW || r->ntraces < job.ntraces)) // this will cause additional states to be explored even with one trace
                        if (psi.eval(succ).to_int() || (phi.eval(succ).to_int() && st == PWT_NEW))
                        {
                            // We have phi and continue to look for psi
                            waiting.put(succ);
                        } else {
                            succ->deallocate_();
                        }
                    }

                    delete i;
                }
                current->deallocate_(); // All successors have been generated: deallocate() would equivalent
            }
        } 
        // if current satisfies neither phi or psi then we are done
        // and the result is undefined
    } else {
        // The initial state satisfies the property so the cost is 0
        // Even when the costs can be negative, we look for the min cost to 
        // first reach psi
        CostResult* curc = current->current_cost();
        r->update(*curc, false);
        delete curc;
        
        r->set_trace(current);
        r->compute_trace(job.utility, orig_prop);
    }
    
    //passed.info();

    // Now we are sure that the trace is optimal, if costs can be negative
    if (!job.non_negative_costs)
    {
        r->compute_trace(job.utility, orig_prop);
    }

    delete &passed;

    Log.stop("CostEU_EEU");
    return r;
}

string property::CostEU_EEU::to_string() const
{
    stringstream s;

    s << "mincost E (" << phi.to_string() << " U " << psi.to_string() << ") (EEU special)";

    return s.str();
}

const GenericExpression* property::CostEU_EEU::copy(CTS& t) const
{
    return new property::CostEU_EEU(phi.copy(t), psi.copy(t), init, decl_line);
}

const GenericExpression* property::CostEU_EEU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::CostEU_EEU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), init, decl_line);
}

const GenericExpression* property::CostEU_EEU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::CostEU_EEU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), init, decl_line);
}

const GenericExpression* property::CostEU_EEU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::CostEU_EEU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), init, decl_line);
}

bool property::CostEU_EEU::has_cost() const
{
    return true;
}

