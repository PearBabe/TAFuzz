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

#include <cstdint>
#include <string>
#include <sstream>
#include <algorithm>

#include <transition.hh>

#include <lobject.hh>
#include <time_interval.hh>
#include <sexpression.hh>
#include <rvalue.hh>
#include <cts.hh>
#include <color_output.hh>

#include <valuation.hh>

using namespace std;
using namespace romeo;

Transition::Transition(
        const unsigned i, 
        const std::string& l, 
        const SExpression& g, 
        const SExpression& a, 
        const TimeInterval* t, 
        const SExpression& r, 
        const SExpression& s, 
        const SExpression& p, 
        const SExpression& c, 
        const bool u, 
        const unsigned int cont, 
        const SExpression& al): 
    LObject(i,l), feff_id(i), guard(g), assigns(a), timing(t), intermediate(r), speed(s), priority(p), cost(c), utility(u), control(cont), allow(al), max_bounded(false), max_bound(-1), prefval(0) {}

string Transition::to_string() const
{
    stringstream s;

    s << "transition " << label
      << " " << timing->to_string()
      << " when " << guard.to_string() 
      << " do " << assigns.to_string()
      << " intermediate " << intermediate.to_string()
      << " speed " << speed.to_string();
    
    if (!priority.is_null())
    {
        s << " priority " << priority.to_string();
    }

    if (cost.is_null())
    {
        s << " cost " << cost.to_string();
    }

    s << " allow " << allow.to_string();
    s << " // id " << id << " feff " << feff_id;

    if (utility)
    {
        s << " (utility)";  
    }
    s << endl;

    return s.str();
}

bool Transition::has_priority_over(const Transition& t, const byte V[], const byte C[]) const
{
    const value p = (this->priority.is_null()? INT64_MIN: this->priority.evaluate(V, C).to_int());
    const value pt = (t.priority.is_null()? INT64_MIN: t.priority.evaluate(V, C).to_int());
 
    return p > pt;
}

const Transition* Transition::copy(CTS& t) const
{
    return new Transition(id, label, 
            guard.copy(t), 
            assigns.copy(t),
            timing->copy(t),
            intermediate.copy(t),
            speed.copy(t),
            priority.copy(t),
            cost.copy(t),
            utility,
            control,
            allow.copy(t)
            );
}

void Transition::copy(const Transition& tr, CTS& t)
{
    id = tr.id;
    label = tr.label;
    feff_id = tr.feff_id;
    guard = tr.guard.copy(t);
    assigns = tr.assigns.copy(t);
    timing = tr.timing->copy(t);
    intermediate = tr.intermediate.copy(t);
    speed = tr.speed.copy(t);
    priority = tr.priority.copy(t);
    cost = tr.cost.copy(t);
    utility = tr.utility;
    control = tr.control;
    allow = tr.allow.copy(t);
    prefval = 0;
}

void Transition::abstract_copy(const Transition& tr, CTS& t, const VarSet& S)
{
    id = tr.id;
    label = tr.label;
    feff_id = tr.feff_id;
    guard = tr.guard.copy(t); 
    assigns = tr.assigns.abstract_copy(t, S); // Abstract only what is written
    timing = tr.timing->copy(t);
    intermediate = tr.intermediate.copy(t);
    speed = tr.speed.copy(t);
    priority = tr.priority.copy(t);
    cost = tr.cost.copy(t); 
    utility = tr.utility;
    control = tr.control;
    allow = tr.allow.copy(t);
    prefval = 0;
}

const Transition* Transition::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Transition(
            id,
            label + "__" + std::to_string(v),
            guard.instantiate(t, i, v),
            assigns.instantiate(t, i, v),
            timing->instantiate(t, i, v),
            intermediate.instantiate(t, i, v),
            speed.instantiate(t, i, v),
            priority.instantiate(t, i, v),
            cost.instantiate(t, i, v),
            utility,
            control,
            allow.instantiate(t, i, v));
}

void Transition::writes(VarSet& w) const
{
    assigns.writes(w);
    intermediate.writes(w);
}

void Transition::reads(VarSet& r) const
{
    guard.reads(r);
    assigns.reads(r);
    intermediate.reads(r);
    timing->reads(r);
    intermediate.reads(r);
    speed.reads(r);
    priority.reads(r);
    cost.reads(r);
    allow.reads(r);
}

cvalue Transition::get_cost(byte V[], const byte statics[], bool non_negative_costs) const
{
    cvalue dc = 0;
    if (!cost.is_null())
    {
        const value raw = cost.evaluate(V, statics).to_int();
        const value max_finite_cost = static_cast<value>(ROMEO_MAX_BVALUE) / 2 - 1;
        if (raw < -max_finite_cost || raw > max_finite_cost)
        {
            cerr << error_tag(color_output) << "Line " << cost.get_line()
                 << ": cost of " << label << " is outside the finite DBM range ("
                 << raw << ")" << endl;
            exit(1);
        }

        dc = static_cast<cvalue>(raw);
        if (non_negative_costs && dc < 0)
        {
            cerr << error_tag(color_output) << "Line " << cost.get_line() << ": with the current options, the cost of " 
                 << label << " cannot be negative (" << dc << ")" << endl;
            exit(1);
        }
    }

    return dc;
}

Transition::~Transition()
{
    guard.clear();
    assigns.clear();
    intermediate.clear();
    speed.clear();
    priority.clear();
    cost.clear();
    allow.clear();
}

