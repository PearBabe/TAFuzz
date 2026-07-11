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

#include <cts.hh>
#include <result.hh>
#include <polyhedron.hh>
#include <pwt.hh>

#include <color_output.hh>

#include <logger.hh> 
extern romeo::Logger Log;

using namespace std;
using namespace romeo;

const CTS* PResult::cts;
PResult::PResult(): trace(NULL), trace_contents(), multipart(false), print_trace(true), ntraces(0), unknown(false), apx(RES_EXACT) {}
PResult::~PResult() {}

PResult::PResult(const PResult& r): trace(r.trace), trace_contents(r.trace_contents), multipart(r.multipart), print_trace(r.print_trace), ntraces(r.ntraces), unknown(r.unknown), apx(r.apx) {}


void PResult::compute_trace(const bool utility, const Property* p)
{
    if (trace) 
    {
        list<const Transition*> tc;

        const PWNode* N = trace;

        while (N->parent_node() != NULL)
        {
            if (utility || !N->in_transition()->utility)
            {
                tc.push_front(N->in_transition());
            }

            N=N->parent_node();
        }

        trace_contents.push_back(tc);
        trace_props.push_back(p);
        ntraces++;

        trace->trace_end = false;
        trace->deallocate();
        trace = NULL;
    }
}

string PResult::trace_to_string() const
{
    stringstream s;
    
    if (print_trace)
    {
        if (ntraces == 0)
        {
            s << "No trace.";
        } else {
            s << "Trace";
            if (ntraces > 1)
            {
                if (!multipart)
                {
                    s << "s";
                }
                s << ": " << endl;
            } else {
                s << ": ";
            }
        }

        bool already_empty = false;
        bool newline = false;
        for (list<list<const Transition*> >::const_iterator j = trace_contents.begin(); j != trace_contents.end(); j++)
        {
            if (newline)
            {
                s << endl;
            } else {
                newline = true;
            }

            if (j->empty())
            {
                if (!already_empty)
                {
                    if (!multipart)
                    {
                        s << "the result is obtained in the initial state.";
                    } else {
                        s << std::endl << "part of the result is obtained in the initial state.";
                    }
                }
                already_empty = true;
            } else {
                if (ntraces > 1)
                {
                    s << "-> ";
                }

                bool comma = false;
                list<const Transition*>::const_iterator i;
                for (i = j->begin(); i != j->end(); i++)
                {
                    if (comma)
                        s << ", ";
                    else
                        comma = true;

                    s << (*i)->label;
                }
            }
        }
    }

    return s.str();
}

void PResult::set_trace(PWNode* n)
{
    if (trace != NULL)
    {
        // Perhaps we do not need this anymore
        // Try to deallocate it
        trace->trace_end = false;
        trace->deallocate();
    }

    trace = n;
    trace->trace_end = true; // do not deallocate this while it is the trace end
}

void PResult::set_approx(const approx_t a)
{
    apx = a;
}

void PResult::simplify_with(const PResult& r)
{    
}

void PResult::integer_shape_close_assign()
{
}

void PResult::trace_reads(const list<const Transition*>& L, VarSet& r, const CTS& ref_cts)
{
    list<const Transition*>::const_iterator i;
    for (i = L.begin(); i != L.end(); i++)
    {
        const Transition* t = ref_cts.lookup_transition((*i)->label);
        if (t == NULL)
        {
            cerr << error_tag(color_output) << "Error in adapting the trace for more concrete CTS: " << (*i)->label << " not found." << endl;
            exit(1);
        }
        t->reads(r);
    }
}

void PResult::first_trace_reads(VarSet& r, const CTS& ref_cts) const
{
    if (!trace_contents.empty())
    {
        trace_reads(*trace_contents.begin(), r, ref_cts);
    }
}

bool PResult::best_trace_reads(VarSet& r, const CTS& ref_cts) const
{
    bool br = false;

    if (!trace_contents.empty())
    {
        vector<VarSet> tab(ntraces);

        map<unsigned, unsigned> m;

        for (list<list<const Transition*> >::const_iterator k = trace_contents.begin(); k != trace_contents.end(); k++)
        {
            VarSet S;
            for (list<const Transition*>::const_iterator i = k->begin(); i != k->end(); i++)
            {
                const Transition* t = ref_cts.lookup_transition((*i)->label);
                if (t == NULL)
                {
                    cerr << error_tag(color_output) << "Error in adapting the trace for more concrete CTS: " << (*i)->label << " not found." << endl;
                    exit(1);
                }
                t->reads(S);
            }

            for (VarSet::iterator j = S.begin(); j != S.end(); j++)
            {
                if (m.count(*j) == 0)
                {
                    m[*j] = 0;
                } else {
                    m[*j]++;
                }
            }
        }

        for (auto j : m)
        {
            tab[j.second].insert(j.first);
        }

        VarSet Sunion;

        if (!tab[ntraces - 1].empty())
        {
            set_union(tab[ntraces -1].begin(), tab[ntraces -1].end(), r.begin(), r.end(), inserter(Sunion, Sunion.begin()));
        } 

        if (Sunion.size() > r.size())
        {
            br = true;
            r = Sunion;
        } else {
            unsigned b = 1;
            while (b < ntraces && !br)
            {
                for (VarSet::iterator is = tab[ntraces - 1 -b].begin(); is != tab[ntraces - 1 - b].end() && !br; is++)
                {
                    br = r.insert(*is).second;
                }

                b++;
            }
        }
    }

    return br;

}

Polyhedron PResult::constraint() const
{
    cerr << error_tag(color_output) << "Cannot get constraint from this kind of result" << endl;
    exit(1);
}

list<string> PResult::trace_ids(const list<const Transition*>& Lt)
{
    list<string> L;

    list<const Transition*>::const_iterator i;
    for (i = Lt.begin(); i != Lt.end(); i++)
    {
        L.push_back((*i)->label);
    }

    return L;
}

list<string> PResult::first_trace_ids() const
{
    list<string> L;

    if (!trace_contents.empty())
    {
        L = trace_ids(*trace_contents.begin());
    }

    return L;
}

std::string PResult::get_trace() const
{
    return colorize(color_output,this->trace_to_string(), AC_CYAN);
}

bool PResult::is_unknown() const
{
    return unknown;
}

void PResult::set_unknown(const bool u) 
{
    unknown = u;
}

// -----------------------------------------------------------------------------

PBool::PBool(bool b): PResult(), val(b) {}
PBool::PBool(const PBool& r) : PResult(r), val(r.val) {}

bool PBool::equals(const PResult& r)
{
    if (unknown)
    {
        return true;
    } else {
        return val == static_cast<const PBool&>(r).val;
    }
}

bool PBool::contains(const PResult& r)
{
    return equals(r);
}

bool PBool::intersects(const PResult& r)
{
    const bool rval = static_cast<const PBool&>(r).val; 
    return val && rval;
}

PResult& PBool::conjunction(const PResult& r)
{
    const bool rval = static_cast<const PBool&>(r).val; 
    if ((!unknown && !val) || (!r.unknown && !rval))
    {
        unknown = false;
        val = false;
    } else {
        val &= rval;
        unknown = (unknown || r.unknown);
    }
    
    return *this;
}

PResult& PBool::disjunction(const PResult& r)
{
    const bool rval = static_cast<const PBool&>(r).val; 
    if ((!unknown && val) || (!r.unknown && rval))
    {
        unknown = false;
        val = true;
    } else {
        val |= rval;
        unknown = (unknown || r.unknown);
    }

    return *this;
}

PResult& PBool::negation()
{
    val = !val;
 
    return *this;
}

PResult* PBool::copy() const
{
    return new PBool(*this);
}

bool PBool::empty() const
{
    if (unknown)
    {
        return false;
    } else {
        return !val;
    }
}

bool PBool::universe() const
{
    if (unknown)
    {
        return false;
    } else {
        return val;
    }
}

std::string PBool::to_string() const
{
    std::stringstream s;
    if (apx != RES_EXACT)
    {
        s << colorize(color_output,"maybe ", AC_MAGENTA);
    }

    if (unknown)
    {
        s << colorize(color_output,"unknown", AC_MAGENTA);
    } else {
        if (val)
            s << colorize(color_output,"true", AC_GREEN);
        else
            s << colorize(color_output,"false", AC_RED);
    }

    return s.str();
}

PBool::~PBool() {}

// ----------------------------------------------------------------

PRPoly::PRPoly(unsigned dim, bool b): PResult(), val(dim,b)
{
}

PRPoly::PRPoly(const PRPoly& r): PResult(r), val(r.val)
{
}

PRPoly::PRPoly(const Polyhedron& P): PResult(), val(P)
{
}

bool PRPoly::equals(const PResult& r)
{
    return val == static_cast<const PRPoly&>(r).val;
}

bool PRPoly::contains(const PResult& r)
{
    //if (val.exact_contains(static_cast<const PRPoly&>(r).val) != val.contains(static_cast<const PRPoly&>(r).val))
    //{
    //    Log.count("inexact_result_contains");
    //}

    Log.start("result_contains");
    const bool b = val.contains(static_cast<const PRPoly&>(r).val);
    Log.stop("result_contains");

    return b;
}

bool PRPoly::intersects(const PResult& r)
{
    return val.intersects(r.constraint());
}

void PRPoly::simplify_with(const PResult& r)
{    
    const PRPoly& p = static_cast<const PRPoly&>(r);
    val.simplify_with(p.val);
}


PResult& PRPoly::conjunction(const PResult& r)
{
    val.intersection_assign(r.constraint());
    val.reduce();
    
    return *this;
}

PResult& PRPoly::disjunction(const PResult& r)
{
    val.add_reduce(r.constraint());

    return *this;
}

PResult& PRPoly::negation()
{
    if (apx == RES_OVER)
    {
        apx = RES_UNDER;
    } else if (apx == RES_UNDER) {
        apx = RES_OVER;
    } else if (apx == RES_UNDER_INT) {
        apx = RES_OVER_INT;
    } else if (apx == RES_OVER_INT) {
        apx = RES_UNDER_INT;
    }
    val.negation_assign();
    val.reduce();

    return *this;
}

PResult* PRPoly::copy() const
{
    return new PRPoly(*this);
}

bool PRPoly::empty() const
{
    return val.empty();
}

bool PRPoly::universe() const
{
    return val.universe();
}

std::string PRPoly::to_string() const
{
    std::stringstream s;
    
    vector<string> labels;
    for (list<Parameter>::const_iterator k=cts->begin_parameters(); k != cts->end_parameters(); k++)
    {
        cvalue v;
        if (!k->constant(v))
        {
            labels.push_back(k->label);
        }
    }

    if (apx == RES_UNDER)
    {
        s << colorize(color_output,"(Possible under-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER) {
        s << colorize(color_output,"(Possible over-approximation)", AC_MAGENTA) << endl;
    } else if (apx == RES_OVER_INT) {
        s << colorize(color_output,"(Possible over-approximation, but contains no spurious integer values)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNDER_INT) {
        s << colorize(color_output,"(Possible under-approximation, but contains all integer values)", AC_MAGENTA) << endl;
    } else if (apx == RES_INT) {
        s << colorize(color_output,"(The result is the set of integer solutions of these constraints)", AC_MAGENTA) << endl;
    } else if (apx == RES_UNKNOWN) {
        s << colorize(color_output,"(Possible approximation)", AC_MAGENTA) << endl;
    }

    if (val.universe())
    {
        s << colorize(color_output,"true", AC_GREEN);
    } else if (val.empty()) {
        s << colorize(color_output,"false", AC_RED);
    } else {
        s << colorize(color_output,val.to_string_labels(labels,0), AC_GREEN);
    }
   
    return s.str();
}

Polyhedron PRPoly::constraint() const
{
    return val;
}

void PRPoly::integer_shape_close_assign()
{
    val.integer_shape_close_assign();
}

PRPoly::~PRPoly()
{
}


