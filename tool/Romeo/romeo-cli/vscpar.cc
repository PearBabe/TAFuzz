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
#include <iostream>

#include <vscpar.hh>
#include <vsclass.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <result.hh>

#include <rvalue.hh>
#include <lexpression.hh>
#include <lconstraint.hh>

#include <time_interval.hh>

#include <graph_node.hh>
#include <control_reach.hh>

using namespace std;;
using namespace romeo;

#include <logger.hh> 
extern romeo::Logger Log;


VSCPar::VSCPar(const Job& job): VSCPoly(job), IH(NULL) {}
VSCPar::VSCPar(const VSCPar& S, unsigned k): VSCPoly(S,k), IH(NULL) {}

VSCPar* VSCPar::init(const Job& job)
{
    Log.start("init");
    VSCPar* R = new VSCPar(job);
    R->init_constraints();

    R->update_tsize();

    Log.stop("init");

    return R;
}
    
void VSCPar::init_constraints()
{
    this->VSCPoly::init_constraints();

    const CTS& cts = job.cts;

    // For the integer hull all parameters should be non-negative
    if (job.ip || job.ih_convergence)
    {
        for (unsigned i = 0; i < cts.nparams(); i++)
            D->constrain(Var(i), CSTR_GWEAK);
    }

    // Add consistency constraints that make the intervals non-empty
    // for the initial marking (but not the others if the intervals use
    // variables in their bounds)
    for (list<Transition>::const_iterator i=cts.begin_transitions(); i != cts.end_transitions(); i++)
    {
        const Transition& f = *i;
        const LinearExpression l = f.timing->lbound.linear_expression(V, cts.statics);
        D->constrain(l, CSTR_GWEAK);

        if (!f.timing->unbounded)
        {
            const LinearExpression u = f.timing->ubound.linear_expression(V, cts.statics);
            if (f.timing->ustrict || f.timing->lstrict)
                D->constrain(l - u, CSTR_LSTRICT);
            else
                D->constrain(l - u, CSTR_LWEAK);
        }
    }

    // Initial constraints
    if (!job.cts.initp.is_null())
    {
        Polyhedron C = cts.initp.constraint(V, job.cts.statics, cts.nparams());
        C.add_dimensions(D->dimension() - C.dimension());

        D->intersection_assign(C);
    }

    // Possibly integer hull
    if (job.ip)
    {
        D->integer_shape_assign();
    } else if (job.bound_normalize) {
        D->bound_normalize(job.n_bound);    
    }
}

PWNode* VSCPar::successor(unsigned i)
{
    Log.start("Succ");
    const unsigned NP = job.cts.nparams();

    VSCPar* R = new VSCPar(*this, i);
    R->firability_constraints(*this, i);
    R->time_elapsing(*this, i);

    unsigned S_indices[NE + NP];
    unsigned indices[R->NE + NP];

    R->remap(*this, i, indices, S_indices, 0);
    R->constrain_new(*this, i, indices, S_indices);

    if (job.computation_mode == TIMED_PARAMETRIC && !job.no_abstract)
    {
        R->time_saturation();
    }
   
    Log.stop("Succ");

    // Possibly integer hull
    if (job.ip) {
        R->D->integer_shape_assign();
    } else if (job.bound_normalize) {
        R->D->bound_normalize(job.n_bound);    
    } else {
        R->D->simplification_assign(); // Workaround to bad simplification in PPL
    }

    
    R->update_tsize();

    return R;
}

bool VSCPar::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
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

void VSCPar::newen_constraints(const Transition& f, const unsigned i)
{
    const Var vi(i);

    // vi > l or vi >= l
    const LinearExpression l = f.timing->lbound.linear_expression(V, job.cts.statics);
    const cstr_rel rl = f.timing->lstrict ? CSTR_GSTRICT : CSTR_GWEAK;
    D->constrain(vi - l, rl);

    // Unnecessary if we forbid variables in parametric intervals.
    // Interval well-formedness: l >= 0
    // D->constrain(l, CSTR_GWEAK);
    
    if (!f.timing->unbounded)
    {
        // vi < u or vi <= u
        const LinearExpression u = f.timing->ubound.linear_expression(V, job.cts.statics);
        const cstr_rel ru = f.timing->ustrict ? CSTR_LSTRICT : CSTR_LWEAK;
        D->constrain(vi - u, ru);

        // Unnecessary if we forbid variables in parametric intervals.
        // Interval well-formedness: l <= u
        // D->constrain(l - u, CSTR_LWEAK);
    }
}

VSCPar::VSCPar(const VSCPar& S, const Instruction& I): VSCPoly(S,I), IH(NULL)
{
}

void VSCPar::compute_rc() const
{
    Polyhedron P(*D);
    P.remove_higher_dimensions(job.cts.nparams());

    rc = new PRPoly(P);
}

PResult* VSCPar::init_result(bool b) const
{
    return new PRPoly(job.cts.nparams(),b);
}

bool VSCPar::restriction(const PResult& r)
{
    bool result = false;
    Log.start("Restrict");
    
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
        if (job.ip)
            D->integer_shape_assign();
        else if (job.bound_normalize)
            D->bound_normalize(job.n_bound);    

        result = D->empty();
    } else {    
        C.intersection_assign(*D);
        result = C.empty();
    }
    
    Log.stop("Restrict");
    return result;
}

PWNode* VSCPar::copy(const Instruction* I) const
{
    if (I == NULL)
        return new VSCPar(*this);
    else
    {
        const unsigned NP = job.cts.nparams();
        VSCPar* s = new VSCPar(*this, *I);

        unsigned S_indices[NE + NP];
        unsigned indices[s->NE + NP];

        s->remap(*this, NE, indices, S_indices, 0);
        s->constrain_new(*this, NE, indices, S_indices);

        return s;
    }
}

PWNode* VSCPar::predecessor() const
{
    const unsigned NP = job.cts.nparams();
    VSCPar* S = static_cast<VSCPar*>(parent->copy());
    
    // find the index of the fired transition
    unsigned f = 0;
    while (f < S->NE && S->en[f] != in)
    {
        f++;
    }

    unsigned indices[NE + NP];
    unsigned rindices[S->NE + NP];

    // Do not move parameters around
    for (unsigned i = 0; i < NP; i++)
    {
        indices[i]=i;
        rindices[i]=i;
    }

    // Map starting from the transition dimensions
    map_indices(*S, in, indices, NP);

    for (unsigned i = 0; i < S->NE; i++)
    {
        rindices[i + NP] = NE + NP;
    }

    // Find persistent transitions and reverse the mapping
    for (unsigned i = 0; i < NE; i++)
    {
        if (indices[i + NP] < S->NE + NP)
        {
            rindices[indices[i + NP]] = i + NP;
        }
    }

    // Eliminate non persistent transitions and remap to the size of S
    // Other dimensions are unconstrained
    Polyhedron R(*D);
    R.remap(rindices, S->NE + NP);

    // Apply reverse variable changes
    // t_i' + tf = t_i
    const cvalue sf = in->speed.evaluate(S->V, job.cts.statics).to_int();
    for (unsigned i = 0; i < NE; i++)
    {
        if (indices[i + NP] < S->NE + NP)
        {
            const cvalue si = S->en[indices[i + NP] - NP]->speed.evaluate(S->V, job.cts.statics).to_int();
            R.affine_image(Var(indices[i + NP]), sf*Var(indices[i + NP]) + si*Var(f + NP), sf);
        }
    }

    // Apply fireability constraints
    for (unsigned i = 0; i < S->NE; i++)
    {
        if (f != i)
        {
            const cvalue si = S->en[i]->speed.evaluate(S->V, job.cts.statics).to_int();
            R.constrain(si*Var(f + NP) - sf*Var(i + NP), CSTR_LWEAK);
        }
    }

    // propagate the constraints backwards
    S->D->intersection_assign(R);

    return S;
}

cvalue VSCPar::maxval(const Transition* t, bool& strict, bool& bounded, cvalue& divisor) const
{
    const unsigned NP = job.cts.nparams();

    // find the index of the transition
    unsigned p = 0;
    while (p < NE && en[p] != t)
        p++;

    p += NP;

    bool ls, lb;
    cvalue lv, rv, ld;

    Polyhedron P(*D);
    P.project_on(p, ls, lb, lv, strict, bounded, rv, ld, divisor);

    return rv;
}

cvalue VSCPar::minval(const Transition* t, bool& strict, bool& bounded, cvalue& divisor) const
{
    const unsigned NP = job.cts.nparams();

    // find the index of the transition
    unsigned p = 0;
    while (p < NE && en[p] != t)
        p++;

    p += NP;

    bool rs, rb;
    cvalue lv, rv, rd;

    Polyhedron P(*D);
    P.project_on(p, strict, bounded, lv, rs, rb, rv, divisor, rd);

    return lv;
}

Polyhedron VSCPar::convergence_domain() const
{
    if (job.ih_convergence)
    {
        if (IH == NULL)
        {
            IH = new Polyhedron(*D);
    Log.start("TD");
            if (parent)
            {
                Polyhedron P(static_cast<const VSCPar*>(parent)->convergence_domain());
                P.remove_higher_dimensions(job.cts.nparams());
                P.add_dimensions(IH->dimension()-P.dimension());
                IH->intersection_assign(P);
            }
    Log.stop("TD");
            IH->integer_shape_assign();
        }
        return *IH;
    } else if (job.bn_convergence) {
        if (IH == NULL)
        {
            IH = new Polyhedron(*D);
            IH->bound_normalize(job.n_bound);
        }
        return *IH;
    } else {
        return *D;
    }
}

void VSCPar::update_tsize()
{
    tsize = D->eval_size(job.cts.nparams());
}


VSCPar::VSCPar(const VSCPar& S): VSCPoly(S), IH(NULL) {}

VSCPar::~VSCPar()
{
    if (IH != NULL)
        delete IH;
}

// ------------------ control --------------------------------------------------

PResult* VSCPar::update_result(const GraphNode* g, PResult* r) const
{
    delete r;

    const unsigned NP = job.cts.nparams();
    
    vector<unsigned> dimsu;
    for (unsigned i = 0; i < NE; i++)
    {
        if (!(en[i]->control & CTRL_CONTROLLABLE))
        {
            dimsu.push_back(i + job.cts.nparams());
        }
    }

    Polyhedron W = g->winning.wp->uprojection(dimsu, *D);
    W.remove_higher_dimensions(NP);

    return new PRPoly(W);
}

SuccInfo* VSCPar::add_succ(GraphNode* src, const Transition* t, PState* s, GraphNode* dst) const
{
    SuccInfo* res = PWNode::add_succ(src, t, s, dst);
    if (res != nullptr && s != nullptr)
    {
        res->tgt.tp = new Polyhedron(*static_cast<const VSCPar*>(s)->D);
    }
    return res;
}


