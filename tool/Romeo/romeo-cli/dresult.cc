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


#include <iostream>
#include <cstdlib>

#include <dresult.hh>
#include <avalue.hh>
#include <dproperty.hh>
#include <cts.hh>
#include <color_output.hh>

using namespace std;
using namespace romeo;

DResult::DResult(const bool u, const bool a): PResult(), undefined(u), approximate(a)
{
}

DResult::DResult(const DResult& r): PResult(r), undefined(r.undefined), approximate(r.approximate)
{
    trace = r.trace;
    trace_contents = r.trace_contents;
}

PResult& DResult::conjunction(const PResult& r)
{
    cerr << error_tag(color_output) << "Cannot conjunct DResults" << endl;
    exit(1);
}

PResult& DResult::disjunction(const PResult& r)
{
    cerr << error_tag(color_output) << "Cannot disjunct DResults" << endl;
    exit(1);
}

PResult& DResult::negation()
{
    cerr << error_tag(color_output) << "Cannot negate DResults" << endl;
    exit(1);
}

bool DResult::empty() const
{
    return undef();
}

bool DResult::universe() const
{
    cerr << error_tag(color_output) << "Cannot test DResults for universality" << endl;
    exit(1);
}

bool DResult::equals(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test DResults for equality" << endl;
    exit(1);
}

bool DResult::contains(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test DResults for inclusion" << endl;
    exit(1);
}

bool DResult::intersects(const PResult&)
{
    cerr << error_tag(color_output) << "Cannot test DResults for intersection" << endl;
    exit(1);
}

bool DResult::undef() const
{
    return undefined;
}

bool DResult::approx() const
{
    return approximate;
}

// -----------------------------------------------------------------------------

SimpleDResult::SimpleDResult(const SimpleDResult& r): DResult(r), prop(r.prop)
{
}

SimpleDResult::SimpleDResult(const SimpleDProp& p, const bool undef, const bool approx): DResult(undef, approx), prop(p)
{
}

// -----------------------------------------------------------------------------

VarSDResult::VarSDResult(const VarSDResult& r): SimpleDResult(r), val(r.val)
{
}

VarSDResult::VarSDResult(const SimpleDProp& p, const value v): SimpleDResult(p, false, false), val(v)
{
}

VarSDResult::VarSDResult(const SimpleDProp& p): SimpleDResult(p, true, false), val(0)
{
}


bool VarSDResult::update(const DResult& r, const bool reupdate)
{
    const VarSDResult& rv = static_cast<const VarSDResult&>(r);
    
    bool modified = false;
    if (!rv.undefined)
    {
        if (prop.is_min())
        {
            if (undefined || rv.val < val || (rv.val == val && reupdate))
            {
                val = rv.val;
                modified = true;
                undefined = false;
                approximate = rv.approximate;
            }
        } else {
            if (undefined || rv.val > val || (rv.val == val && reupdate))
            {
                val = rv.val;
                modified = true;
                undefined = false;
                approximate = rv.approximate;
            }
        }
    }

    return modified;
}


PResult* VarSDResult::copy() const
{
    // trace here
    return new VarSDResult(*this);
}

string VarSDResult::to_string() const
{
    stringstream s;
    if (apx == RES_UNDER)
    {
        s << colorize(color_output,"(Possible under-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER) {
        s << colorize(color_output,"(Possible over-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNKNOWN) {
        s << colorize(color_output,"(Possible approximation)", AC_MAGENTA) << endl;
    }

    if (undefined)
    {
        s << colorize(color_output, "undefined", AC_RED);
    } else {
        stringstream st;
        st << val;
        s << colorize(color_output, st.str(), AC_GREEN);
    }

    return s.str();
}

// -----------------------------------------------------------------------------

ClockSDResult::ClockSDResult(const ClockSDResult& r): SimpleDResult(r), val(r.val), den(r.den), strict(r.strict), unbounded(r.unbounded)
{
}

ClockSDResult::ClockSDResult(const SimpleDProp& p, const cvalue v, cvalue q, bool s, bool u): SimpleDResult(p, false, false), val(v), den(q), strict(s), unbounded(u)
{
}

ClockSDResult::ClockSDResult(const SimpleDProp& p): SimpleDResult(p, true, false), val(0), den(1), strict(false), unbounded(false)
{
}

bool ClockSDResult::update(const DResult& r, const bool reupdate)
{
    const ClockSDResult& rv = static_cast<const ClockSDResult&>(r);
    
    bool modified = false;
    if (!rv.undefined)
    {
        if (prop.is_min())
        {
            if (undefined || rv.val < val || (rv.val == val && ((!strict && rv.strict) || reupdate)))
            {
                val = rv.val;
                modified = true;
                undefined = false;
                approximate = rv.approximate;
            }
        } else {
            if (undefined || rv.val > val || (rv.val == val && ((!rv.strict && strict) || reupdate)) || (!rv.unbounded && unbounded)) 
            {
                val = rv.val;
                modified = true;
                undefined = false;
                approximate = rv.approximate;
            }
        }
    }

    return modified;
}


PResult* ClockSDResult::copy() const
{
    // trace here
    return new ClockSDResult(*this);
}

string ClockSDResult::to_string() const
{
    stringstream s;

    if (apx == RES_UNDER)
    {
        s << colorize(color_output,"(Possible under-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER) {
        s << colorize(color_output,"(Possible over-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNKNOWN) {
        s << colorize(color_output,"(Possible approximation)", AC_MAGENTA) << endl;
    }

    if (undefined)
    {
        s << colorize(color_output,"undefined",AC_RED);
    } else {
        stringstream st;
        if (unbounded)
        {
            st << "inf";
        } else {
            st << val;
            if (strict)
                st << " (limit)";

            s << colorize(color_output, st.str(), AC_GREEN);
        }
    }

    return s.str();
}

// -----------------------------------------------------------------------------

CostResult::CostResult(const Avalue& v): DResult(false, false), val(v)
{
}

CostResult::CostResult(const Avalue& v, const bool a): DResult(false, a), val(v)
{
}

CostResult::CostResult(): DResult(true, false), val(Avalue::infinity)
{
}

CostResult::CostResult(const CostResult& r): DResult(r), val(r.val)
{
}

bool CostResult::update(const DResult& r, const bool reupdate)
{
    const CostResult& rv = static_cast<const CostResult&>(r);
    
    bool modified = false;
    if (!rv.undefined && (undefined || rv.val < val || (rv.val == val && reupdate)))
    {
        val = rv.val;
        undefined = false;
        modified = true;
        approximate = rv.approximate;
    }

    return modified;
}

Avalue CostResult::cost() const
{
    return val;
}

PResult* CostResult::copy() const
{
    // trace here
    return new CostResult(*this);
}

string CostResult::to_string() const
{
    stringstream s;

    if (apx == RES_UNDER)
    {
        s << colorize(color_output,"(Possible under-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER) {
        s << colorize(color_output,"(Possible over-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNKNOWN) {
        s << colorize(color_output,"(Possible approximation)", AC_MAGENTA) << endl;
    }

    if (undefined)
    {
        s << colorize(color_output,"undefined",AC_RED);
    } else {
        s << colorize(color_output, val.to_string(), AC_GREEN);
    }

    return s.str();
}

// -----------------------------------------------------------------------------

ParamCostResult::ParamCostResult(const Avalue& v, const Polyhedron& P): CostResult(v), D(P)
{
}

ParamCostResult::ParamCostResult(const Avalue& v, const Polyhedron& P, const bool a): CostResult(v, a), D(P)
{
}

ParamCostResult::ParamCostResult(unsigned dim): CostResult(), D(dim, false)
{
}

ParamCostResult::ParamCostResult(const ParamCostResult& r): CostResult(r), D(r.D)
{
}

bool ParamCostResult::update(const DResult& r, const bool reupdate)
{
    const ParamCostResult& rv = static_cast<const ParamCostResult&>(r);
    
    bool modified = false;
    if (!rv.undefined && (undefined || rv.val < val))
    {
        val = rv.val;
        D = rv.D;
        undefined = false;
        modified = true;
        approximate = rv.approximate;
    } else {
        if (!rv.undefined && rv.val == val)
        {
            D.add_reduce(rv.D);
            modified = true;
        }
    }

    return modified;
}

Avalue ParamCostResult::cost() const
{
    return val;
}

PResult* ParamCostResult::copy() const
{
    // trace here
    return new ParamCostResult(*this);
}

string ParamCostResult::to_string() const
{
    stringstream s;

    if (apx == RES_UNDER)
    {
        s << colorize(color_output,"(Possible under-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER) {
        s << colorize(color_output,"(Possible over-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNKNOWN) {
        s << colorize(color_output,"(Possible approximation)", AC_MAGENTA) << endl;
    }

    if (undefined)
    {
        s << colorize(color_output, "undefined", AC_RED);
    } else {
        s << colorize(color_output, val.to_string()+"\n", AC_GREEN);

        vector<string> labels;
        for (list<Parameter>::const_iterator k = cts->begin_parameters(); k != cts->end_parameters(); k++)
        {
            cvalue v;
            if (!k->constant(v))
            {
                labels.push_back(k->label);
            }
        }

        s << colorize(color_output, D.to_string_labels(labels, 0), AC_CYAN);
    }

    return s.str();
}

PResult& ParamCostResult::conjunction(const PResult& r)
{
    D.intersection_assign(r.constraint());
    D.reduce();
    
    return *this;
}

PResult& ParamCostResult::disjunction(const PResult& r)
{
    D.add_reduce(r.constraint());

    return *this;
}

PResult& ParamCostResult::negation()
{
    D.negation_assign();
    D.reduce();

    return *this;
}

Polyhedron ParamCostResult::constraint() const
{
    return D;
}

