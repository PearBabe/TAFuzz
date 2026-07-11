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

#include <vszpar.hh>
#include <vsclass.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <result.hh>

#include <lexpression.hh>
#include <lconstraint.hh>
#include <time_interval.hh>

#include <graph_node.hh>

using namespace std;
using namespace romeo;

#include <logger.hh> 
extern romeo::Logger Log;


VSZPar::VSZPar(const Job& job): VSZPoly(job) {}
VSZPar::VSZPar(const VSZPar& S, unsigned k): VSZPoly(S,k) {}

VSZPar* VSZPar::init(const Job& job)
{
    VSZPar* R = new VSZPar(job);
    R->init_constraints();

    return R;
}


void VSZPar::init_constraints()
{
    this->VSZPoly::init_constraints();

    const CTS& cts = job.cts;

    // For the integer hull all parameters should be non-negative
    if (job.ip || job.ih_convergence)
    {
        for (unsigned i = 0; i < cts.nparams(); i++)
            D->constrain(Var(i), CSTR_GWEAK);
    }

    // Add consistency constraints that make the intervals non-empty
    // for the initial marking (variables in parametric intervals are forbidden)
    for (list<Transition>::const_iterator i=cts.begin_transitions(); i != cts.end_transitions(); i++)
    {
        const Transition& f = *i;
        const LinearExpression l = f.timing->lbound.linear_expression(V, job.cts.statics);
        D->constrain(l, CSTR_GWEAK);

        if (!f.timing->unbounded)
        {
            const LinearExpression u = f.timing->ubound.linear_expression(V, job.cts.statics);
            D->constrain(l - u, CSTR_LWEAK);
        }
    }

    // Initial constraints
    if (!cts.initp.is_null())
    {
        Polyhedron C = cts.initp.constraint(V, job.cts.statics, cts.nparams());
        C.add_dimensions(D->dimension() - C.dimension());

        D->intersection_assign(C);
    }

    // Possibly integer hull (shape because union of convex polyhedra)
    if (job.ip)
    {
        D->integer_shape_assign();
    }
}

PWNode* VSZPar::successor(unsigned i)
{
    Log.start("Succ");

    VSZPar* R = new VSZPar(*this, i);
    R->succ_constraints(*this,i);
    R->remap_and_constrain_new(*this, i);

    if (R->job.ip)
    {
        R->D->integer_shape_assign();
    } else {
        // Workaround to bad simplification in PPL
        R->D->simplification_assign();
    }

    Log.stop("Succ");
    
    return R;
}

bool VSZPar::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    bool r = true;
    if (e != NULL)
    {
        const unsigned NP = job.cts.nparams();
        const LinearExpression v = e->linear_expression(V, job.cts.statics);

        D->constrain(q*Var(i+NP) - v,CSTR_EQ);
        r = !D->empty();
    }

    return r;
}

void VSZPar::apply_invariant(const Transition& f, const unsigned i)
{
    const Var vi(i);

    // vi > l or vi >= l
    const LinearExpression l = f.timing->lbound.linear_expression(V, job.cts.statics);

    // Unnecessary if we forbid variables in parametric intervals.
    // Interval well-formedness: l >= 0
    // D->constrain(l, CSTR_GWEAK);
    
    if (!f.timing->unbounded)
    {
        // vi < u or vi <= u
        const LinearExpression u = f.timing->ubound.linear_expression(V, job.cts.statics);
        const cstr_rel r = f.timing->ustrict ? CSTR_LSTRICT : CSTR_LWEAK;
        D->constrain(vi - u,r);

        // Unnecessary if we forbid variables in parametric intervals.
        // Interval well-formedness: l <= u
        // D->constrain(l - u, CSTR_LWEAK);
    }
}

PResult* VSZPar::init_result(bool b) const
{
    return new PRPoly(job.cts.nparams(),b);
}

LinearExpression VSZPar::guard(const_valuation V, const Transition& f, const unsigned i) const
{
    const LinearExpression gf = f.timing->lbound.linear_expression(V, job.cts.statics);
    const Var vf(i);
   
    return vf - gf;
}

VSZPar::VSZPar(const VSZPar& S, const Instruction& I): VSZPoly(S,I)
{
}

void VSZPar::compute_rc() const
{
    Polyhedron P(*D);
    P.remove_higher_dimensions(job.cts.nparams());

    rc = new PRPoly(P);
}

bool VSZPar::restriction(const PResult& r)
{
    Log.start("Restrict");
    bool result = false;

    have_computed_rc = false;
    if (rc != nullptr)
    {
        delete rc;
        rc = nullptr;
    }

    const PRPoly& c = static_cast<const PRPoly&>(r);
    Polyhedron C(c.val);
    C.add_dimensions(D->dimension() - C.dimension());

    if (job.restrict_update)
    {
        D->intersection_assign(C);
        result = D->empty();
    } else {    
        C.intersection_assign(*D);
        result = C.empty();
    }
    
    Log.stop("Restrict");
    return result;
}

PWNode* VSZPar::copy(const Instruction* I) const
{
    if (I == NULL)
        return new VSZPar(*this);
    else
    {
        VSZPar* s = new VSZPar(*this, *I);
        s->remap_and_constrain_new(*this,NE);
        return s;
    }
}

VSZPar::VSZPar(const VSZPar& S): VSZPoly(S) {}

// -----------------------------------------------------------------------------
// Control
//
PResult* VSZPar::update_result(const GraphNode* g, PResult* r) const
{
    delete r;

    const unsigned NP = job.cts.nparams();
    Polyhedron R(*g->winning.wp);

    for (unsigned i = 0; i < NE; i++)
    {
        R.constrain(Var(NP+i), CSTR_EQ);
    }
    R.remove_higher_dimensions(NP);

    return new PRPoly(R);
}

