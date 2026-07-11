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

#include <string>
#include <sstream>

#include <dproperty.hh>
#include <dresult.hh>
#include <pstate.hh>
#include <lexpression.hh>
#include <rvalue.hh>
#include <pwt.hh>
#include <priority_queue.hh>

using namespace std;
using namespace romeo;

// -----------------------------------------------------------------------------

SimpleDProp::SimpleDProp(const SimpleDProp& p): Property(p.decl_line), condition(p.condition), minimum(p.minimum)
{
}

SimpleDProp::SimpleDProp(const SExpression& c, const bool m, int line): Property(line), condition(c), minimum(m)
{
}

string SimpleDProp::to_string() const
{
    stringstream s;

    s << "when " << condition << " ";
    if (minimum)
        s << "minimize ";
    else
        s << "maximize ";

    return s.str();
}

bool SimpleDProp::is_min() const
{
    return minimum;
}

bool SimpleDProp::is_dprop() const
{
    return true;
}

bool SimpleDProp::cond_eval(const PState* s) const
{
    return condition.eval(s).to_int();
}
// -----------------------------------------------------------------------------

SDPValue::SDPValue(const SDPValue& p): SimpleDProp(p), expr(p.expr)
{
}

SDPValue::SDPValue(const SExpression& c, const bool m, const SExpression& e, int line): SimpleDProp(c, m, line), expr(e)
{
}

PResult* SDPValue::eval(const PState* s) const
{
    if (cond_eval(s))
    {
        return new VarSDResult(*this, s->evaluate(expr).to_int());
    } else {
        return new VarSDResult(*this);
    }
}

string SDPValue::to_string() const
{
    stringstream s;

    s << SimpleDProp::to_string();
    s << expr;

    return s.str();
}

const GenericExpression* SDPValue::copy(CTS& cts) const
{
    return new SDPValue(condition.copy(cts), minimum, expr.copy(cts), decl_line);
}

const GenericExpression* SDPValue::abstract_copy(CTS& cts, const VarSet& S) const
{
    return new SDPValue(condition.abstract_copy(cts, S), minimum, expr.abstract_copy(cts, S), decl_line);
}

const GenericExpression* SDPValue::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new SDPValue(condition.instantiate(t, i, v), minimum, expr.instantiate(t, i, v), decl_line);
}

const GenericExpression* SDPValue::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new SDPValue(condition.eliminate_refs(t, d), minimum, expr.eliminate_refs(t, d), decl_line);
}

// -----------------------------------------------------------------------------
SDPClock::SDPClock(const SDPClock& p): SimpleDProp(p), transition(p.transition)
{
}

SDPClock::SDPClock(const SExpression& c, const bool m, const Transition* t, int line): SimpleDProp(c, m, line), transition(t)
{
}

PResult* SDPClock::eval(const PState* s) const
{
    cvalue val, q;
    bool strict, unbounded, disabled;

    if (cond_eval(s))
    {
        if (minimum)
        {
            s->min_clockval(transition, val, q, strict, unbounded, disabled);
        } else {
            s->max_clockval(transition, val, q, strict, unbounded, disabled);
        }
        

        if (disabled)
        {
            return new ClockSDResult(*this);
        } else {
            return new ClockSDResult(*this, val, q, strict, unbounded);
        }
    } else {
        return new ClockSDResult(*this);
    }
}

string SDPClock::to_string() const
{
    stringstream s;

    s << SimpleDProp::to_string();
    s << transition->label;

    return s.str();
}

bool SDPClock::is_clock() const
{
    return true;
}

const GenericExpression* SDPClock::copy(CTS& cts) const
{
    return new SDPClock(condition.copy(cts), minimum, transition, decl_line);
}

const GenericExpression* SDPClock::abstract_copy(CTS& cts, const VarSet& S) const
{
    return new SDPClock(condition.abstract_copy(cts, S), minimum, transition, decl_line);
}

const GenericExpression* SDPClock::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new SDPClock(condition.instantiate(t, i, v), minimum, transition, decl_line);
}

const GenericExpression* SDPClock::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new SDPClock(condition.eliminate_refs(t, d), minimum, transition, decl_line);
}

// -----------------------------------------------------------------------------

DProperty::DProperty(const SimpleDProp& p, const Property* c): Property(p.decl_line), prop(p), invariant(c)
{
}

std::string DProperty::to_string() const
{
    return prop.to_string();
}

bool DProperty::update(DResult& r, const PState* s) const
{
    return r.update(*static_cast<DResult*>(prop.eval(s)), false);
}

bool DProperty::is_clock() const
{
    return prop.is_clock();
}

bool DProperty::is_dprop() const
{
    return prop.is_dprop();
}

bool DProperty::has_cost() const
{
    return prop.has_cost() || invariant->has_cost();
}

const GenericExpression* DProperty::copy(CTS& cts) const
{
    return new DProperty(*static_cast<const SimpleDProp*>(prop.copy(cts)), invariant);
}

const GenericExpression* DProperty::abstract_copy(CTS& cts, const VarSet& S) const
{
    return new DProperty(*static_cast<const SimpleDProp*>(prop.abstract_copy(cts, S)), invariant);
}

const GenericExpression* DProperty::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new DProperty(*static_cast<const SimpleDProp*>(prop.instantiate(t, i, v)), invariant);
}

const GenericExpression* DProperty::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new DProperty(*static_cast<const SimpleDProp*>(prop.eliminate_refs(t, d)), invariant);
}

PResult* DProperty::eval(const PState* s) const
{
    const Job& job = s->job;

    WaitingList* wl = nullptr;
    if (this->has_cost())
    {
        wl = new PriorityQueue<LtNodesCost>(job);
    } else {
        wl = new SimpleWaitingList(job);
    }
    WaitingList& waiting = *wl;

    //SimpleWaitingList waiting(job);
    PassedList& passed = *s->init_passed(waiting, job.cts.variables.vstate_size());

    PState* current = static_cast<PState*>(s->copy());
    
    // Pre-put the state for better convergence
    passed.put(current);
    waiting.put(current);

    // Here initialize the different quantities to measure
    DResult& r = *static_cast<DResult*>(prop.eval(current));
    if (prop.is_min())
    {
        r.set_approx(RES_OVER);
    } else {
        r.set_approx(RES_UNDER);
    }

    if (!r.undef())
    {
        r.set_trace(current);
    }

    bool heuristic_stop = false;
    while ((current = static_cast<PState*>(waiting.get())) && !Job::stop && !heuristic_stop)
    {
        //cout << "===================================================================" << endl;
        //cout << *current << endl;

        // If we have defined a cost heuristic, we want to stop as soon as the when clause holds
        if (!job.cts.cost_heuristic.is_null() && prop.cond_eval(current))
        {
            heuristic_stop = true;
        }

        PWNiterator* i = current->iterator();
        PState* succ;

        // add all successors to the pw list
        while ((succ = static_cast<PState*>(i->next())))
        {
            //cout << "--------------------------------------------------------------------" << endl;
            //cout << *succ << endl;
            bool ok = true;
            if (invariant != nullptr)
            {
                const PResult* r = invariant->eval(succ);
                ok = r->universe();
                delete r;
            }
            if (ok)
            {
                // Here compute the mins and maxs with this succ
                bool updated = update(r, static_cast<PState*>(succ));
                if (updated)
                {
                    r.set_trace(succ); 
                }

                PWTStatus st = passed.put(succ);
                if (st == PWT_NEW)
                {
                    waiting.put(succ);
                } else {
                    succ->deallocate_();
                }
            }
        }

        delete i;

        current->deallocate_();
    }
 
    r.compute_trace(job.utility, orig_prop);
    if (!Job::stop)
    {
        r.set_approx(RES_EXACT);
    }

    delete &passed;
    delete wl;

    return &r;



}


