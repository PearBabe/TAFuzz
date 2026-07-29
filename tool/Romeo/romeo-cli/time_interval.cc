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

#include <time_interval.hh>
#include <sexpression.hh>
#include <timebounds.hh>
#include <cts.hh>
#include <rvalue.hh>

using namespace std;
using namespace romeo;

TimeInterval::TimeInterval(const SExpression& l, const SExpression& u, const bool ls, const bool us, const bool ub): 
    lbound(l), ubound(u), lstrict(ls), ustrict(us), unbounded(ub) {}

bool TimeInterval::unconstrained() const
{
    return !lstrict && lbound.is_constant(0) && unbounded;
}

string TimeInterval::to_string() const
{
    stringstream s;
    if (lstrict)
        s << "] ";
    else 
        s << "[ ";

    s << lbound.to_string() << ", ";

    if (unbounded)
    {
        s << "inf [";
    } else {
        s << ubound.to_string(); 
        if (lstrict)
            s << " [";
        else 
            s << " ]";
    }

    return s.str();
}

const TimeInterval* TimeInterval::copy(CTS& t) const
{
    return new TimeInterval(lbound.copy(t), ubound.copy(t), lstrict, ustrict, unbounded);
}

const TimeInterval* TimeInterval::abstract_copy(CTS& t, const VarSet& S) const
{
    return new TimeInterval(lbound.abstract_copy(t, S), ubound.abstract_copy(t, S), lstrict, ustrict, unbounded);
}

const TimeInterval* TimeInterval::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new TimeInterval(lbound.instantiate(t, i, v), ubound.instantiate(t, i, v), lstrict, ustrict, unbounded);
}

const TimeInterval* TimeInterval::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new TimeInterval(lbound.eliminate_refs(t, d), ubound.eliminate_refs(t, d), lstrict, ustrict, unbounded);
}

const TimeInterval* TimeInterval::abstract_parameters(CTS& t, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    auto l = lbound.abstract_parameters(t, true, lbs, ubs, lbounds, ubounds); 
    auto u = ubound.abstract_parameters(t, false, lbs, ubs, lbounds, ubounds); 
    bool ub = (!u.has_vars() && u.evaluate(nullptr, nullptr).to_int() == INT_MAX); // TODO not very nice

    return new TimeInterval(l, u, lstrict, ustrict || ub, unbounded || ub);
}

time_bound romeo::TimeInterval::dbm_lower_bound(const_valuation V, const_valuation C) const
{
    // Assumption: t->lbound has a 0 MSB
    // Warning: returns the time_bound corresponding to the opposite of the value!
    return time_bound(-lbound.evaluate(V, C).to_int(), lstrict? ROMEO_DBM_STRICT: ROMEO_DBM_NON_STRICT);
}

time_bound romeo::TimeInterval::dbm_upper_bound(const_valuation V, const_valuation C) const
{
    // Assumption: t->ubound has a 0 MSB
    if (unbounded)
        return time_bound::infinity;
    else {
        return time_bound(ubound.evaluate(V, C).to_int(), ustrict? ROMEO_DBM_STRICT: ROMEO_DBM_NON_STRICT);
    }
}

void romeo::TimeInterval::reads(VarSet& r) const
{
    lbound.reads(r);
    if (!unbounded)
    {
        ubound.reads(r);
    }
}

TimeInterval::~TimeInterval()
{
}

