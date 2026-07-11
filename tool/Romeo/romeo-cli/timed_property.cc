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

#include <climits>
#include <sstream>

#include <properties.hh>

#include <expression.hh>
#include <lexpression.hh>
#include <access_expression.hh>
#include <lconstraint.hh>
#include <instruction.hh>
#include <rvalue.hh>

#include <cts.hh>
#include <time_interval.hh>

#include <result.hh>
#include <pstate.hh>

using namespace std;
using namespace romeo;
using namespace romeo::lexpression;

// -----------------------------------------------------------------------
property::TimedProperty::TimedProperty(const SExpression& l, const SExpression& r, const TimeInterval& I, int line): TemporalProperty(l, r, line), timing(I) {}

bool property::TimedProperty::has_params() const
{
    return timing.lbound.has_params() || (!timing.unbounded && timing.ubound.has_params());
}

bool property::TimedProperty::has_time() const
{
    return !timing.lbound.is_constant(0) || !timing.unbounded;
}

PState* property::TimedProperty::validate_observers(const PState* s) const
{
    const romeo::Variable& vprop = static_cast<const Variable&>(s->job.cts.find_or_add_util("#romeo_prop_var"));
    const instruction::Assignment e(*new LValue(vprop, decl_line), *new lexpression::Litteral(real_prop->id, decl_line), decl_line);
    PState* x = static_cast<PState*>(s->copy(&e));
    return x;
}

PResult* property::TimedProperty::eval(const PState* s) const
{
    //cout << *real_prop << endl;
    const PState* x = validate_observers(s);

    real_prop->orig_prop = this;
    PResult* r = real_prop->eval(x);
    delete x;

    return r;
}


const lconstraint::Eq* property::TimedProperty::get_eq(const romeo::Variable& var, const value v) const
{
    return new lconstraint::Eq(*new lexpression::RLValue(*new lexpression::LValue(var, decl_line), decl_line), *new lexpression::Litteral(v, decl_line), decl_line);
}

const lconstraint::Leq* property::TimedProperty::get_leq(const romeo::Variable& var, const value v) const
{
    return new lconstraint::Leq(*new lexpression::RLValue(*new lexpression::LValue(var, decl_line), decl_line), *new lexpression::Litteral(v, decl_line), decl_line);
}

const instruction::Assignment* property::TimedProperty::get_assign(const romeo::Variable& var, const value v) const
{
    return new instruction::Assignment(*new lexpression::LValue(var, decl_line), *new lexpression::Litteral(v, decl_line), decl_line);
}

void property::TimedProperty::writes(VarSet& w) const
{
    real_prop->writes(w);
}

void property::TimedProperty::reads(VarSet& r) const
{
    real_prop->reads(r);
}

property::TimedProperty::~TimedProperty()
{
    delete &timing;
    delete real_prop;
}

// -----------------------------------------------------------------------
property::TEU::TEU(const SExpression& l, const SExpression& r, const TimeInterval& I, int line): TimedProperty(l, r, I, line) {}

string property::TEU::to_string() const
{
    stringstream s;

    s << "E ( "<< phi.to_string() << " U" << timing.to_string() << " " << psi.to_string() << " )";

    return s.str();
}

const GenericExpression* property::TEU::copy(CTS& t) const
{
    return new property::TEU(phi.copy(t), psi.copy(t), *timing.copy(t), decl_line);
}

const GenericExpression* property::TEU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::TEU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), *timing.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::TEU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::TEU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), *timing.copy(t), decl_line);
}

const GenericExpression* property::TEU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::TEU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), *timing.eliminate_refs(t, d), decl_line);
}

void romeo::property::TEU::prepare(CTS& t) const
{
    const romeo::Variable& vseek = static_cast<const Variable&>(t.find_or_add_util("#romeo_clock_constraint_var"));
    const romeo::Variable& vprop = static_cast<const Variable&>(t.find_or_add_util("#romeo_prop_var"));
    
    
    const Property* phic = static_cast<const Property*>(phi.get_expr()->copy(t));
    const Property* psic = static_cast<const Property*>(psi.get_expr()->copy(t));

    const lconstraint::Eq* eq0 = get_eq(vseek, 0);
    const lconstraint::Eq* eq1 = get_eq(vseek, 1);
    const lconstraint::Less* less2 = new lconstraint::Less(*new lexpression::RLValue(*new lexpression::LValue(vseek, decl_line), decl_line), *new lexpression::Litteral(2, decl_line), decl_line);
    
    const property::And* gphi = new property::And(*phic, *less2, decl_line);
    const property::And* gpsi = new property::And(*psic, *eq1, decl_line);
    
    real_prop = new property::EU(gphi, gpsi, decl_line);
    
    const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);

    const property::And* pinned_eq0 = new property::And(*pin, *eq0, decl_line);

    const instruction::Assignment* good_time = get_assign(vseek, 1);
    const instruction::Assignment* assign2 = get_assign(vseek, 2);
    
    const TimeInterval* the_time = new TimeInterval(timing.lbound.copy(t), timing.ubound.copy(t), timing.lstrict, timing.ustrict, timing.unbounded);
    const TimeInterval* zeroTiming = new TimeInterval(new lexpression::Litteral(0, decl_line), new lexpression::Litteral(0, decl_line), false, false, false);

    const unsigned sNT = t.ntrans();

    const Transition obs(sNT, "#romeo_clock_constraint_", 
            pinned_eq0,             // when seek = 0
            good_time,              // do seek := 2
            the_time,                // [l,u] original timing
            new instruction::Nop(), // no intermediate
            new lexpression::Litteral(1, decl_line),          // speed 1
            NULL,                   // no priority 
            NULL,                   // no cost 
            true,                   // utility
            CTRL_CONTROLLABLE,      // Fully controllable
            new lconstraint::True(decl_line)); // always allowed
        
    t.add_transition(obs);

    const Transition obs2(sNT+1, "#romeo_clock_urgent_", 
            eq1->copy(t),             // when vurgent= 0 and psi holds
            assign2,              // do vurgent := 1
            zeroTiming,                // [0,0]
            new instruction::Nop(), // no intermediate
            new lexpression::Litteral(1, decl_line),          // speed 1
            NULL,                   // no priority 
            NULL,                   // no cost 
            true,                   // utility
            CTRL_CONTROLLABLE,      // Fully controllable
            new lconstraint::True(decl_line)); // always allowed
        
    t.add_transition(obs2);
    
    const instruction::Assignment* seek_off = get_assign(vseek, 0);
    const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(seek_off);
    
    const instruction::Assignment* validate_obs = get_assign(vprop, 0);
    const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(validate_obs);

    TemporalProperty::prepare(t);
}


// -----------------------------------------------------------------------
property::TAU::TAU(const SExpression& l, const SExpression& r, const TimeInterval& I, int line): TimedProperty(l, r, I, line) {}

string property::TAU::to_string() const
{
    stringstream s;

    s << "A ( "<< phi.to_string() << " U" << timing.to_string() << " " << psi.to_string() << " )";

    return s.str();
}

const GenericExpression* property::TAU::copy(CTS& t) const
{
    return new property::TAU(phi.copy(t), psi.copy(t), *timing.copy(t), decl_line);
}

const GenericExpression* property::TAU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::TAU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), *timing.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::TAU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::TAU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), *timing.copy(t), decl_line);
}

const GenericExpression* property::TAU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::TAU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), *timing.eliminate_refs(t, d), decl_line);
}

void romeo::property::TAU::prepare(CTS& t) const
{
    const romeo::Variable& vseek = static_cast<const Variable&>(t.find_or_add_util("#romeo_clock_constraint_var"));
    const romeo::Variable& vprop = static_cast<const Variable&>(t.find_or_add_util("#romeo_prop_var"));
   
    if (!timing.lbound.is_constant(0) || timing.lstrict)
    {
        const lconstraint::Eq* eq2 = get_eq(vseek, 2);
        const Property* phic = static_cast<const Property*>(phi.get_expr()->copy(t));
        const Property* psic = static_cast<const Property*>(psi.get_expr()->copy(t));
        const property::And* gpsi = new property::And(*psic, *eq2, decl_line);
        real_prop = new property::AU(phic, gpsi, decl_line);
    } else {
        const lconstraint::Eq* eq0 = get_eq(vseek, 0);
        const Property* phic = static_cast<const Property*>(phi.get_expr()->copy(t));
        const Property* psic = static_cast<const Property*>(psi.get_expr()->copy(t));
        const property::And* gpsib = new property::And(*psic, *eq0, decl_line);
        real_prop = new property::AU(phic, gpsib, decl_line);
    }


    const unsigned sNT = t.ntrans();        
                               
    if (!timing.lbound.is_constant(0) || timing.lstrict)
    {
        if (timing.lstrict)
        {
            const lconstraint::Eq* eq0 = get_eq(vseek, 0);
            const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
            const property::And* pinned_eq0 = new property::And(*pin, *eq0, decl_line);

            const instruction::Assignment* good_time = get_assign(vseek, 2);
           
            // lowermost part of the complement of timing (for strict lower bounds)
            // [0,l] (the property has ]l,u])
            const TimeInterval* min_time = new TimeInterval(new lexpression::Litteral(0, decl_line), timing.lbound.copy(t), false, false, false);

            const Transition obs_strict(sNT, "#romeo_clock_constraint_", 
                    pinned_eq0,               // when seek = 0  
                    good_time,                // do seek := 2
                    min_time,                 // [0,l] see just above
                    new instruction::Nop(),   // no intermediate
                    new lexpression::Litteral(1, decl_line),            // speed 1
                    new lexpression::Litteral(INT_MIN, decl_line),      // priority max
                    NULL,                     // no cost
                    true,                     // utility
                    CTRL_CONTROLLABLE,        // Fully controllable
                    new lconstraint::True(decl_line)); // always allowed

            t.add_transition(obs_strict);
        } else {
            const lconstraint::Eq* eq0 = get_eq(vseek, 0);
            const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
            const property::And* pinned_eq0 = new property::And(*pin, *eq0, decl_line);

            const instruction::Assignment* good_time = get_assign(vseek, 2);
            
            // timing barrier (for non-strict lower bounds)
            // [l,l]
            const TimeInterval* min_barrier = new TimeInterval(timing.lbound.copy(t), timing.lbound.copy(t), false, false, false);

            const Transition obs_nonstrict(sNT, "#romeo_clock_constraint_", 
                    pinned_eq0,               // when seek = 0 
                    good_time,                // do seek := 2
                    min_barrier,              // [l,l] see above
                    new instruction::Nop(),   // no intermediate
                    new lexpression::Litteral(1, decl_line),            // speed 1
                    new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                    NULL,                     // no cost
                    true,                     // utility
                    CTRL_CONTROLLABLE,        // Fully controllable
                    new lconstraint::True(decl_line)); // always allowed
     

            t.add_transition(obs_nonstrict);
        }
    }

    if (!timing.unbounded)
    {
        { // Scoping to make variables local

            const lconstraint::Leq* leq2 = get_leq(vseek, 2);
            const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);

            const property::And* pinned_leq2 = new property::And(*pin, *leq2, decl_line);

            // uppermost part of the complement of timing
            // ]u,inf] or [u,inf[
            const TimeInterval* max_time = new TimeInterval(timing.ubound.copy(t), new lexpression::Litteral(INT_MAX, decl_line), !timing.ustrict, true, true);

            const instruction::Assignment* bad_time = get_assign(vseek, 3);

            const Transition too_late(sNT+1, "#romeo_clock_constraint_too_late_", 
                    pinned_leq2,              // when seek <= 2
                    bad_time,                 // do seek := 3
                    max_time,                 // ]u,inf] see above
                    new instruction::Nop(),   // no intermediate
                    new lexpression::Litteral(1, decl_line),            // speed 1
                    new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                    NULL,                     // no cost
                    true,                     // utility
                    CTRL_CONTROLLABLE,        // Fully controllable
                    new lconstraint::True(decl_line)); // always allowed
                
            t.add_transition(too_late);
        }

        { // Scoping to make variables local
            const lconstraint::Eq* eq3 = get_eq(vseek, 3);
            const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);

            const property::And* pinned_eq3 = new property::And(*pin, *eq3, decl_line);

            // [0,0]
            const TimeInterval* zeroTiming = new TimeInterval(new lexpression::Litteral(0, decl_line), new lexpression::Litteral(0, decl_line), false, false, false);

            const Transition stop(sNT+2, "#romeo_stop_if_too_late_", 
                    pinned_eq3,               // when seek = 3
                    new instruction::Nop(),   // do nothing
                    zeroTiming,               // [0,0]
                    new instruction::Nop(),   // no intermediate
                    new lexpression::Litteral(1, decl_line),            // speed 1
                    new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                    NULL,                     // no cost
                    true,                     // utility
                    CTRL_CONTROLLABLE,        // Fully controllable
                    new lconstraint::False(decl_line)); // never allowed (blocks time)

            t.add_transition(stop);
        }
    }

    {
        const instruction::Assignment* seek_off = get_assign(vseek, 0);
        const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(seek_off);

        const instruction::Assignment* validate_obs = get_assign(vprop, 0);
        const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(validate_obs);
    }

    TemporalProperty::prepare(t);
}

// -----------------------------------------------------------------------
property::TLT::TLT(const SExpression& l, const SExpression& r, const TimeInterval& I, int line): TimedProperty(l, r, I, line) {}

void romeo::property::TLT::prepare(CTS& t) const
{
    const romeo::Variable& vseek = static_cast<const Variable&>(t.find_or_add_util("#romeo_clock_constraint_var"));
    const romeo::Variable& vprop = static_cast<const Variable&>(t.find_or_add_util("#romeo_prop_var"));
    
    {
        const lconstraint::Eq* eq1 = get_eq(vseek, 1);

        const Property* phic = static_cast<const Property*>(phi.get_expr()->copy(t));
        const Property* psic = static_cast<const Property*>(psi.get_expr()->copy(t));
        const property::And* ppsi = new property::And(*psic, *eq1, decl_line);
        real_prop = new property::LT(phic, ppsi, decl_line);
    }

    const unsigned sNT = t.ntrans();

    {
        const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
        const lconstraint::Eq* eq0 = get_eq(vseek, 0);
        const Property* phic = static_cast<const Property*>(phi.get_expr()->copy(t));
        const property::And* pphi = new property::And(*phic, *eq0, decl_line);
        const property::And* pinned_pphi = new property::And(*pin, *pphi, decl_line);

        const instruction::Assignment* seek_on = get_assign(vseek, 1);

        // [0,0]
        const TimeInterval* zeroTiming = new TimeInterval(new lexpression::Litteral(0, decl_line), new lexpression::Litteral(0, decl_line), false, false, false);

        const Transition obs_phi(sNT+1, "#romeo_lt_obs_phi_", 
                pinned_pphi,               // When phi is true
                seek_on,                   // seek := 1
                zeroTiming,                // [0,0]
                new instruction::Nop(),    // no intermediate 
                new lexpression::Litteral(1, decl_line),             // speed 1
                new lexpression::Litteral(INT_MAX, decl_line),       // priority max
                NULL,                      // no cost
                true,                      // a utility transition
                CTRL_CONTROLLABLE,         // Fully controllable
                new lconstraint::True(decl_line));  // always allowed

        t.add_transition(obs_phi);
    }

    {
        const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
        const lconstraint::Eq* eq1 = get_eq(vseek, 1);
        const Property* psic = static_cast<const Property*>(psi.get_expr()->copy(t));
        const property::And* ppsi = new property::And(*psic, *eq1, decl_line);
        const property::And* pinned_ppsi = new property::And(*pin, *ppsi, decl_line);

        const instruction::Assignment* seek_off = get_assign(vseek, 0);;

        // [0,0]
        const TimeInterval* zeroTiming = new TimeInterval(new lexpression::Litteral(0, decl_line), new lexpression::Litteral(0, decl_line), false, false, false);

        const Transition obs_psi(sNT+2, "#romeo_lt_obs_psi_", 
                pinned_ppsi,              // When psi is true
                seek_off,                 // seek := 0
                zeroTiming,               // [0,0]
                new instruction::Nop(),   // no intermediate
                new lexpression::Litteral(1, decl_line),            // speed 1
                new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                NULL,                     // no cost
                true,                     // a utility transition
                CTRL_CONTROLLABLE,        // Fully controllable
                new lconstraint::True(decl_line)); // always allowed

        t.add_transition(obs_psi);
    }
    
    { // Scoping to make variables local
        const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
        const lconstraint::Eq* eq1 = get_eq(vseek, 1);
        const property::And* pinned_eq1 = new property::And(*pin, *eq1, decl_line);

        const instruction::Assignment* bad_time = get_assign(vseek, 3);

        // uppermost part of the complement of timing
        // ]u,inf] or [u,inf[
        const TimeInterval* max_time = new TimeInterval(timing.ubound.copy(t), new lexpression::Litteral(INT_MAX, decl_line), !timing.ustrict, true, true);

        const Transition too_late(sNT, "#romeo_clock_constraint_too_late_", 
                pinned_eq1,              // when seek == 1
                bad_time,                 // do seek := 3
                max_time,                 // ]u,inf] see above
                new instruction::Nop(),   // no intermediate
                new lexpression::Litteral(1, decl_line),            // speed 1
                new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                NULL,                     // no cost
                true,                     // utility
                CTRL_CONTROLLABLE,        // Fully controllable
                new lconstraint::True(decl_line)); // always allowed
            
        t.add_transition(too_late);
    }

    { // Scoping to make variables local
        const lconstraint::Eq* pin = get_eq(vprop, real_prop->id);
        const lconstraint::Eq* eq3 = get_eq(vseek, 3);
        const property::And* pinned_eq3 = new property::And(*pin, *eq3, decl_line);

        // [0,0]
        const TimeInterval* zeroTiming = new TimeInterval(new lexpression::Litteral(0, decl_line), new lexpression::Litteral(0, decl_line), false, false, false);

        const Transition stop(sNT+3, "#romeo_stop_if_too_late_", 
                pinned_eq3,               // when seek = 3
                new instruction::Nop(),   // do nothing
                zeroTiming,               // [0,0]
                new instruction::Nop(),   // no intermediate
                new lexpression::Litteral(1, decl_line),            // speed 1
                new lexpression::Litteral(INT_MAX, decl_line),      // priority max
                NULL,                     // no cost
                true,                     // utility
                CTRL_CONTROLLABLE,        // Fully controllable
                new lconstraint::False(decl_line)); // never allowed (blocks time)

        t.add_transition(stop);
    }

    {
        const instruction::Assignment* seek_off = get_assign(vseek, 0);
        const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(seek_off);

        const instruction::Assignment* validate_obs = get_assign(vprop, 0);
        const_cast<instruction::Block*>(static_cast<const instruction::Block*>(t.initv.get_expr()))->add_instruction(validate_obs);
    }

    TemporalProperty::prepare(t);
}

string property::TLT::to_string() const
{
    stringstream s;

    s << "( "<< phi.to_string() << " -->" << timing.to_string() << " " << psi.to_string() << " )";

    return s.str();
}

const GenericExpression* property::TLT::copy(CTS& t) const
{
    return new property::TLT(phi.copy(t), psi.copy(t), *timing.copy(t), decl_line);
}

const GenericExpression* property::TLT::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::TLT(phi.abstract_copy(t, S), psi.abstract_copy(t, S), *timing.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::TLT::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::TLT(phi.instantiate(t, i, v), psi.instantiate(t, i, v), *timing.copy(t), decl_line);
}

const GenericExpression* property::TLT::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::TLT(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), *timing.eliminate_refs(t, d), decl_line);
}


