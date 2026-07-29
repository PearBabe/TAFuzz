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
#include <string>
#include <sstream>

#include <simple_property.hh>
#include <pstate.hh>
#include <lexpression.hh>
#include <lconstraint.hh>
#include <instruction.hh>
#include <rvalue.hh>
#include <result.hh>
#include <cts.hh>
#include <stack_machine.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::property;

SimpleProperty::SimpleProperty(int line): Property(line)
{
}

bool SimpleProperty::is_simple() const
{
    return true;
}

// -----------------------------------------------------------------------
property::Deadlock::Deadlock(int line): SimpleProperty(line) {}

PResult* property::Deadlock::eval(const PState* s) const
{
    return s->init_result(s->deadlock());
}

SProgram property::Deadlock::codegen() const
{
    return SProgram(StackMachine::DEADLOCK);
}

string property::Deadlock::to_string() const
{
    stringstream s;

    s << "deadlock";

    return s.str();
}

const GenericExpression* property::Deadlock::copy(CTS& t) const
{
    return new Deadlock(decl_line);
}

const GenericExpression* property::Deadlock::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Deadlock(decl_line);
}

const GenericExpression* property::Deadlock::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Deadlock(decl_line);
}

const GenericExpression* property::Deadlock::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Deadlock(decl_line);
}

// -----------------------------------------------------------------------
property::SCBad::SCBad(int line): SimpleProperty(line) {}

PResult* property::SCBad::eval(const PState* s) const
{
    return s->init_result(s->safety_control_bad_state());
}

SProgram property::SCBad::codegen() const
{
    return SProgram(StackMachine::SCBAD);
}


string property::SCBad::to_string() const
{
    stringstream s;

    s << "safety_control_deadlock ";

    return s.str();
}

const GenericExpression* property::SCBad::copy(CTS& t) const
{
    return new SCBad(decl_line);
}

const GenericExpression* property::SCBad::abstract_copy(CTS& t, const VarSet& S) const
{
    return new SCBad(decl_line);
}

const GenericExpression* property::SCBad::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new SCBad(decl_line);
}

const GenericExpression* property::SCBad::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new SCBad(decl_line);
}


// -----------------------------------------------------------------------
property::Bounded::Bounded(const value v, int line): SimpleProperty(line), bound(v) {}

PResult* property::Bounded::eval(const PState* s) const
{
    return s->init_result(s->bounded(bound));
}

SProgram property::Bounded::codegen() const
{
    SProgram L;
    L.add(StackMachine::BOUNDED);
    L.add(bound);

    return L;
}

string property::Bounded::to_string() const
{
    stringstream s;

    s << "bounded (" << bound << ")";

    return s.str();
}

const GenericExpression* property::Bounded::copy(CTS& t) const
{
    return new Bounded(bound, decl_line);
}

const GenericExpression* property::Bounded::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Bounded(bound, decl_line);
}

const GenericExpression* property::Bounded::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Bounded(bound, decl_line);
}

const GenericExpression* property::Bounded::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Bounded(bound, decl_line);
}


// -----------------------------------------------------------------------
property::Steps::Steps(const unsigned v, const bool s, int line): SimpleProperty(line), val(v), strict(s) {}

PResult* property::Steps::eval(const PState* s) const
{
    return s->init_result(s->step_limit(val,strict));
}

SProgram property::Steps::codegen() const
{
    SProgram L;
    L.add(StackMachine::STEPS);
    L.add(val);
    L.add(strict);

    return L;
}

string property::Steps::to_string() const
{
    stringstream s;

    s << "#";
    if (strict)
        s << " < ";
    else 
        s << " <= ";
    s << val;

    return s.str();
}

const GenericExpression* property::Steps::copy(CTS& t) const
{
    return new Steps(val, strict, decl_line);
}

const GenericExpression* property::Steps::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Steps(val, strict, decl_line);
}

const GenericExpression* property::Steps::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Steps(val, strict, decl_line);
}

const GenericExpression* property::Steps::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Steps(val, strict, decl_line);
}

// -----------------------------------------------------------------------
property::CostLimit::CostLimit(const SExpression& u, const bool su, int line): SimpleProperty(line), ub(u), ustrict(su) 
{
}

PResult* property::CostLimit::eval(const PState* s) const
{
    return s->cost_limit(ub, ustrict);
}

string property::CostLimit::to_string() const
{
    stringstream s;
    
    if (!ub.is_null())
    {
        s << "cost";
        if (ustrict)
        {
            s << " < ";
        } else { 
            s << " <= ";
        }
        s << ub;
    }

    return s.str();
}

const GenericExpression* property::CostLimit::copy(CTS& t) const
{
    return new CostLimit(ub.copy(t), ustrict, decl_line);
}

const GenericExpression* property::CostLimit::abstract_copy(CTS& t, const VarSet& S) const
{
    return new CostLimit(ub.abstract_copy(t, S), ustrict, decl_line);
}

const GenericExpression* property::CostLimit::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new CostLimit(ub.instantiate(t, i, v), ustrict, decl_line);
}

const GenericExpression* property::CostLimit::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new CostLimit(ub.eliminate_refs(t, d), ustrict, decl_line);
}

bool CostLimit::has_cost() const
{
    return true;
}

// -----------------------------------------------------------------------
property::FiredTransition::FiredTransition(const Transition* t, int line): SimpleProperty(line), transition(t) {}

PResult* property::FiredTransition::eval(const PState* s) const
{
    //return real_prop->eval(s);
    return s->init_result(s->fired_transition(transition->id));
}

SProgram property::FiredTransition::codegen() const
{
    SProgram L;
    L.add(StackMachine::FIRED);
    L.add(transition->id);

    return L;
}

string property::FiredTransition::to_string() const
{
    stringstream s;

    s << transition->label;

    return s.str();
}

const GenericExpression* property::FiredTransition::copy(CTS& t) const
{
    return new FiredTransition(transition, decl_line);
}

const GenericExpression* property::FiredTransition::abstract_copy(CTS& t, const VarSet& S) const
{
    return new FiredTransition(transition, decl_line);
}

const GenericExpression* property::FiredTransition::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new FiredTransition(transition, decl_line);
}

const GenericExpression* property::FiredTransition::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new FiredTransition(transition, decl_line);
}

void property::FiredTransition::prepare(CTS& t) const
{
    /*
    const romeo::Variable& v = static_cast<const Variable&>(t.lookupOrAdd("#romeo_obs_"+transition, true));
    const lexpression::LValue* var = new lexpression::LValue(v);
    
    const RValue* one = new RValue(1);
    const RValue* zero = new RValue(0);
    const RValue* int_max = new RValue(INT_MAX);

    const instruction::Assignment* wait = new instruction::Assignment(v,*zero);
    const instruction::Assignment* fired = new instruction::Assignment(v,*one);
    
    const lconstraint::Eq* eq1 = new lconstraint::Eq(*var,*one);

    const instruction::Nop* nop = new instruction::Nop();
    const Property* prop_true = new lconstraint::True();

    t.initv = new instruction::Comma(*t.initv, *wait);
    
    Transition* tr = t.lookup_transition_non_const(transition);
    tr->assigns = new instruction::Comma(*t.initv, *fired);

    const unsigned sNT = t.ntrans();

    // [0,0]
    const TimeInterval* zeroTiming = new TimeInterval(*zero,*zero,false,false,false);

    const string label = "#romeo_tclean_"+transition;
    const Transition clean(sNT+1, label, 
            eq1,                  // When phi is true
            wait,                  // seek := 1
            zeroTiming,            // [0,0]
            nop,                   // no intermediate 
            one,                   // speed 1
            int_max,               // priority max
            true,                  // a utility transition
            prop_true);            // always allowed


    if (t.lookup_transition(label) == NULL)
        t.add_transition(clean);

    real_prop = eq1;
    */
}


