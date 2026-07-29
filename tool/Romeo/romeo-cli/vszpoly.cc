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

#include "vszpoly.hh"
#include "valuation.hh"
#include "vszpoly_costs.hh"
#include <sstream>
#include <cmath>
#include <climits>

#include <color_output.hh>
#include <vsclass.hh>
#include <vscpoly.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <vszpar.hh>
#include <result.hh>
#include <property.hh>
#include <lexpression.hh>
#include <rvalue.hh>
#include <time_interval.hh>

#include <graph_node.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

// Constructors
VSZPoly::VSZPoly(const Job& job): VSSPoly(job) 
{
}

VSZPoly* VSZPoly::init(const Job& job)
{
    VSZPoly* R = new VSZPoly(job);
    R->init_constraints();

    return R;
}

void VSZPoly::init_constraints()
{
    const unsigned NP = job.cts.nparams();

    for (unsigned i = 0; i< NE; i++)
    {
        D->constrain(Var(NP+i),CSTR_EQ); // v_i = 0
    }

    const unsigned cv = job.cts.has_cost() ? 1 : 0;
    
    // Time elapsing
    cvalue future_rates[NE + NP + cv]; 
    
    //  - Not for parameters
    for (unsigned i=0; i < NP; i++)
    {
        future_rates[i] = 0;
    }

    //  - Transitions according to speeds
    for (unsigned i=0; i < NE; i++)
    {
        future_rates[i+NP] = this->en[i]->speed.evaluate(this->V, job.cts.statics).to_int();
    }

    // The local cost
    if (cv > 0)
    {
        cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

        if (job.is_control)
        {
            // For control we use the technique of BCFL04 and negate the costs;
            c = -c;
        }

        future_rates[NP + NE] = c;
    }

    D->future_assign(future_rates);

    for (unsigned i = 0; i< NE; i++)
    {
        apply_invariant(*en[i], NP + i);
    }

    // kapprox
    if (!job.no_abstract)
    {
        cvalue bounds[NP + NE + cv];
        for (unsigned i = 0; i < NP; i++)
        {
            bounds[i] = -1;
        }
        for (unsigned i = 0; i < NE; i++)
        {
            bounds[NP + i] = en[i]->max_bound;
        }
        if (cv > 0)
        {
            bounds[NP + NE] = -1;
        }
        D->kapprox_assign(bounds);
    }

}

bool VSZPoly::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    bool r = true;
    if (e != nullptr)
    {
        const unsigned NP = job.cts.nparams();
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();

        D->constrain(q*Var(NP+i) - v,CSTR_EQ);
        r = !D->empty();
    }

    return r;
}

void VSZPoly::apply_invariant(const Transition& f, const unsigned i)
{
    const Var vi(i);

    if (!f.timing->unbounded)
    {
        // vi < u or vi <= u
        const value u = f.timing->ubound.evaluate(V, job.cts.statics).to_int();
        const cstr_rel r = f.timing->ustrict ? CSTR_LSTRICT : CSTR_LWEAK;
        D->constrain(vi - u,r);
    }
}

LinearExpression VSZPoly::guard(const_valuation V, const Transition& f, const unsigned i) const
{
    const value gf = f.timing->lbound.evaluate(V, job.cts.statics).to_int();
    const Var vf(i);
   
    return vf - gf;
}

VSZPoly::VSZPoly(const VSZPoly& S, unsigned k): VSSPoly(S,k)
{
}

VSZPoly::VSZPoly(const VSZPoly& S): VSSPoly(S)
{
}

PWNode* VSZPoly::copy(const Instruction* I) const
{
    if (I == nullptr)
        return new VSZPoly(*this);
    else
    {
        VSZPoly* s = new VSZPoly(*this, *I);
        s->remap_and_constrain_new(*this, NE);
        return s;
    }
}

PWNode* VSZPoly::successor(unsigned i)
{
    const unsigned NP = job.cts.nparams();

    VSZPoly* R = new VSZPoly(*this, i);
    R->succ_constraints(*this, i);

    R->remap_and_constrain_new(*this, i);
    
    // kapprox
    if (!job.no_abstract)
    {
        cvalue bounds[NP+NE];
        for (unsigned i = 0; i < NP; i++)
        {
            bounds[i] = -1;
        }
        for (unsigned i = 0; i < NE; i++)
        {
            bounds[NP + i] = en[i]->max_bound;
        }
        D->kapprox_assign(bounds);
       
    }

    return R;
}

void VSZPoly::succ_constraints(const VSZPoly& S, unsigned k)
{
    const unsigned NP = job.cts.nparams();

    const Transition& tf = *S.en[k];

    // Firability constraints
    //   - Basic constraint
    const LinearExpression e = guard(S.V,tf,NP+k);
    if (tf.timing->lstrict)
    {
        D->constrain(e, CSTR_GSTRICT);
    } else {
        D->constrain(e, CSTR_GWEAK);
    }

    //   - priorities
    for (unsigned i = 0; i< S.NE; i++)
    {
        const value si = S.en[i]->speed.evaluate(S.V, job.cts.statics).to_int();
        if (i != k && si != value(0))
        {
            const Transition& ti = *S.en[i];
            if (ti.has_priority_over(tf, S.V, job.cts.statics))
            {
                // ti not yet in its firing interval
                const LinearExpression e = guard(S.V,ti,NP+i);
                if (ti.timing->lstrict)
                {
                    D->constrain(e, CSTR_LWEAK);
                } else {
                    D->constrain(e, CSTR_LSTRICT);
                }

            }
        }
    }
}

void VSZPoly::remap_and_constrain_new(const VSZPoly& S, unsigned k)
{
    const unsigned NP = job.cts.nparams();
    
    unsigned indices[NE + NP];
    unsigned S_indices[S.NE + NP];

    remap(S, k, indices, S_indices, 0);
    constrain_new(S, k, indices, S_indices, 0);
}

void VSZPoly::constrain_new(const VSZPoly& S, unsigned k, unsigned indices[], unsigned S_indices[], unsigned cv)
{
    const unsigned NP = job.cts.nparams();
    const VSZPoly* Sp = static_cast<const VSZPoly*>(S.parent);

    // reset
    for (unsigned i = 0; i < NE; i++)
    {
        if (indices[i + NP] == S.NE + NP + cv
        || (k == S.NE && (Sp == nullptr || S_indices[indices[i + NP]] == Sp->NE + NP + cv)))
        {
            D->unconstrain(NP+i);
            D->constrain(Var(NP+i), CSTR_EQ); // vi = 0
        }
    }

    // Time elapsing
    cvalue future_rates[NE + NP + cv]; 
    
    //  - Not for parameters
    for (unsigned i = 0; i < NP; i++)
    {
        future_rates[i] = 0;
    }

    //  - Transitions according to speeds
    for (unsigned i = 0; i < NE; i++)
    {
        future_rates[i + NP] = this->en[i]->speed.evaluate(this->V, job.cts.statics).to_int();
    }

    if (k < S.NE && cv > 0)
    {
        // The local cost
        cvalue c = job.cts.cost_rate(S.V, job.non_negative_costs);

        // Transition cost
        const Transition* tk = S.en[k];
        cvalue dc = tk->get_cost(S.V, job.cts.statics, job.non_negative_costs);

        if (job.is_control)
        {
            // For control we use the technique of BCFL04 and negate the costs;
            c = -c;
            dc = -dc;
        }

        future_rates[NP + NE] = c;
        
        // add_dcost(dc);
        D->affine_image(Var(NP + NE), Var(NP + NE) + dc, 1);
    }

    D->future_assign(future_rates);

    // Invariant
    for (unsigned i=0; i<NE; i++)
    {
        apply_invariant(*en[i],NP + i);
    }
}

VSZPoly::VSZPoly(const VSZPoly& S, const Instruction& I): VSSPoly(S,I)
{   
    this->D = new Polyhedron(*S.D);
}

bool VSZPoly::firable(unsigned i) const
{
    const unsigned NP = job.cts.nparams();
    const Transition& ti = *en[i];

    const value si = ti.speed.evaluate(V, job.cts.statics).to_int();
    
    // Is it firable?
    bool firable_i = ti.allow.eval(this).to_int();
    if (firable_i && job.feff)
    {
        firable_i = feff_firable(i);
    }

    if (si != value(0) && firable_i)
    {
        Polyhedron F(*D);
        
        //   - Basic constraint
        const LinearExpression e = guard(V, ti, NP + i);
        if (ti.timing->lstrict)
        {
            F.constrain(e, CSTR_GSTRICT);
        } else {
            F.constrain(e, CSTR_GWEAK);
        }

        //   - priorities
        for (unsigned j = 0; j< NE; j++)
        {
            const Transition& tj = *en[j];
            const value sj = tj.speed.evaluate(V, job.cts.statics).to_int();

            if (j != i && sj != value(0))
            {
                if (tj.has_priority_over(ti, V, job.cts.statics))
                {
                    // tj not yet in its firing interval
                    const LinearExpression e = guard(V, tj, NP + j);
                    if (tj.timing->lstrict)
                    {
                        F.constrain(e, CSTR_LWEAK);
                    } else {
                        F.constrain(e, CSTR_LSTRICT);
                    }

                }
            }
        }

        return !F.empty();
    } else {
        return false;
    }
}

// ------------------ control --------------------------------------------------

PResult* VSZPoly::update_result(const GraphNode* g, PResult* r) const
{
    delete r;
    return init_result(g->winning.wp->contains_origin());
}

Polyhedron VSZPoly::predecessor(const VSZPoly* succ, const Polyhedron& S, const Transition* tf, bool forced) const
{
    return pred(succ, S, tf, 0, forced);
}

Polyhedron VSZPoly::pred(const VSZPoly* succ, const Polyhedron& S, const Transition* tf, unsigned cv, bool forced) const
{
    Log.start("pred");
    const unsigned NP = job.cts.nparams();
    const unsigned dim = NE + NP + cv;
    const unsigned sdim = S.dimension();

    unsigned indices[sdim];
    unsigned rindices[dim];

    unsigned f = 0;
    // We assume the index of the fired transition will be found
    while (tf != en[f])
    {
        f++;
    }

    // Do not move parameters around
    for (unsigned i = 0; i < NP; i++)
    {
        indices[i]=i;
        rindices[i]=i;
    }

    // Map starting from the transition dimensions
    succ->map_indices(*this, tf, indices, NP);

    for (unsigned i = 0; i < NE; i++)
    {
        rindices[i + NP] = sdim;
    }

    Polyhedron R(S);
    // Find persistent transitions and reverse the mapping
    for (unsigned i = NP; i < NP + succ->NE; i++)
    {
        if (indices[i] < NP + NE)
        {
            rindices[indices[i]] = i;
        } else {
            // Constrain reset variables to be 0: go to the instant when the symbolic state was entered in.
            R.constrain(Var(i), CSTR_EQ);
        }
    }
    
    // Cost
    if (cv > 0)
    {
        indices[NP + succ->NE] = NP + NE;
        rindices[NP + NE] = NP + succ->NE;

        cvalue dc = tf->get_cost(V, job.cts.statics, job.non_negative_costs);
        if (job.is_control)
        {
            dc = -dc;
        }
        R.affine_image(Var(NP + succ->NE), Var(NP + succ->NE) - dc, 1);
    }

    // Eliminate non persistent transitions and remap to the size of this
    // Other dimensions are unconstrained
    R.remap(rindices, dim);
    R.intersection_assign(*D);

    // Apply the guard
    if (!forced)
    {
        const LinearExpression e = guard(V, *tf, NP+f);
        if (tf->timing->lstrict)
        {
            R.constrain(e, CSTR_GSTRICT);
        } else {
            R.constrain(e, CSTR_GWEAK);
        }
    } else {
        if (tf->timing->unbounded)
        {
            cout << error_tag(color_output) << ": cannot force a transition with no upper bound." << endl;
            exit(1);
        }
        const value u = tf->timing->ubound.evaluate(V, job.cts.statics).to_int();
        if (tf->timing->ustrict)
        {
            cout << error_tag(color_output) << ": finite upper bounds for uncontrollable transitions should be non-strict." << endl;
            exit(1);
        }
        // vi >= u
        R.constrain(Var(NP+f) - u, CSTR_GWEAK);
    }
    
    //   - priorities
    for (unsigned j = 0; j< NE; j++)
    {
        const Transition& tj = *en[j];
        const value sj = tj.speed.evaluate(V, job.cts.statics).to_int();

        if (j != f && sj != value(0))
        {
            if (tj.has_priority_over(*tf, V, job.cts.statics))
            {
                // tj not yet in its firing interval
                const LinearExpression e = guard(V, tj, NP + j);
                if (tj.timing->lstrict)
                {
                    R.constrain(e, CSTR_LWEAK);
                } else {
                    R.constrain(e, CSTR_LSTRICT);
                }
            }
        }
    }
    
    Log.stop("pred");
    return R;
}

bool VSZPoly::update_reach(GraphNode* n) const
{
    Log.start("update_reach");
    const unsigned NP = job.cts.nparams();
    list<SuccInfo>::iterator it;

    const unsigned cv = job.has_cost()? 1 : 0;

    // Time elapsing
    cvalue rates[NE + NP + 1]; 
    
    //  - Not for parameters
    for (unsigned i=0; i < NP; i++)
    {
        rates[i] = 0;
    }

    //  - Transitions according to speeds
    for (unsigned i = 0; i < NE; i++)
    {
        rates[i + NP] = this->en[i]->speed.evaluate(this->V, job.cts.statics).to_int();
    }

    if (cv > 0)
    {
        const cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

        // For control we use the technique of BCFL04 and negate the cost
        rates[NP + NE] = job.is_control? -c: c;
    }

    Polyhedron Good(NP + NE + cv, false); 
    Polyhedron Bad(NP + NE + cv, false);
    Polyhedron ForcedGood(NP + NE + cv, false); 
    Polyhedron ForcedBad(NP + NE + cv, false);
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const unsigned int ctrl_flags = it->trans->control;
        const VSZPoly* s = static_cast<const VSZPoly*>(it->node->get_state());

        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            if (!it->up_to_date)
            {
                if (it->pred.wp != nullptr)
                {
                    delete it->pred.wp;
                }
                it->pred.wp = new Polyhedron(this->predecessor(s, *it->node->winning.wp, it->trans, false));


                if (it->pred2.wp != nullptr)
                {
                    delete it->pred2.wp;
                }
                if (!it->trans->timing->unbounded)
                {
                    Polyhedron LoseSucc = *it->node->winning.wp;
                    LoseSucc.negation_assign();
                    LoseSucc.intersection_assign(*s->D);
                    it->pred2.wp = new Polyhedron(this->predecessor(s, LoseSucc, it->trans, true));
                }
                
                it->up_to_date = true;
            }

            Good.add_reduce(*it->pred.wp);
            if (!it->trans->timing->unbounded)
            {
                ForcedBad.add_reduce(*it->pred2.wp);
            }
        } else {
            if (!it->up_to_date)
            {
                if (it->pred.wp != nullptr)
                {
                    delete it->pred.wp;
                }

                Polyhedron LoseSucc = *it->node->winning.wp;
                LoseSucc.negation_assign();
                LoseSucc.intersection_assign(*s->D);
                it->pred.wp = new Polyhedron(this->predecessor(s, LoseSucc, it->trans, false));

                
                if (it->pred2.wp != nullptr)
                {
                    delete it->pred2.wp;
                }
                if (!it->trans->timing->unbounded)
                {
                    it->pred2.wp = new Polyhedron(this->predecessor(s, *it->node->winning.wp, it->trans, true));
                }
                it->up_to_date = true;
            }

            Bad.add_reduce(*it->pred.wp);
            if (!it->trans->timing->unbounded)
            {
                ForcedGood.add_reduce(*it->pred2.wp);
            }
        }
    }
    // cout << "-----------------------------------------------------"  << endl;
    // cout << "Good is " << endl << Good << endl;
    // cout << "Bad is " << endl << Bad << endl;

    Polyhedron NotGood(Good);
    NotGood.negation_assign();
    ForcedBad.intersection_assign(NotGood);
    Bad.add_reduce(ForcedBad);
    Good.add_reduce(ForcedGood);

    Polyhedron NewWinning = Good.predt_sem(rates, Bad);
    NewWinning.intersection_assign(*D);

    // cout << "New Winning: " << endl; 
    // cout << NewWinning <<endl;

    //if (!n->winning.wp->exact_contains(NewWinning))
    bool result = false;
    if (!n->winning.wp->contains(NewWinning))
    {
        // cout << "   bigger: " << endl << NewWinning << endl;
        *n->winning.wp = NewWinning;

        if (!job.notrace)
        {
            Bad.negation_assign();
            Polyhedron& NotBad = Bad;
            NotBad.intersection_assign(*D);
            n->clear_strategy(WSET_POLY);
            for (it = n->succs.begin(); it != n->succs.end(); it++)
            {
                const unsigned int ctrl_flags = it->trans->control;
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    LocalStrategy st;
                    st.action = it->trans;
                    st.type = STRAT_ACTION;
                    for (unsigned i = 0; i < NE; i++)
                    {
                        st.en.push_back(en[i]);
                    }
                    st.domain.wp = new Polyhedron(*it->pred.wp);
                    st.domain.wp->intersection_assign(NotBad);
                    st.domain.wp->reduce();
                    add_local_strategy(WSET_POLY, n->strategy, st);
                }
            }

            // LocalStrategy wait;
            // wait.action = nullptr;
            // wait.type = STRAT_ACTION;
            // for (unsigned i = 0; i < NE; i++)
            // {
            //     wait.en.push_back(en[i]);
            // }
            // wait.domain.wp = new Polyhedron(NewWinning);
            // add_local_strategy(WSET_POLY, n->strategy, wait);
        }

        //n->losing.wp = NewWinning.complement();
        result = true;
    }

    Log.stop("update_reach");
    return result;
}

bool VSZPoly::update_safe(GraphNode* n) const
{
    const unsigned NP = job.cts.nparams();
    list<SuccInfo>::iterator it;

    const unsigned cv = job.has_cost()? 1 : 0;

    // Time elapsing
    cvalue rates[NE + NP + 1]; 
    
    //  - Not for parameters
    for (unsigned i=0; i < NP; i++)
    {
        rates[i] = 0;
    }

    //  - Transitions according to speeds
    for (unsigned i = 0; i < NE; i++)
    {
        rates[i + NP] = this->en[i]->speed.evaluate(this->V, job.cts.statics).to_int();
    }

    if (cv > 0)
    {
        const cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

        // For control we use the technique of BCFL04 and negate the cost
        rates[NP + NE] = job.is_control? -c: c;
    }

    Polyhedron Good(NP + NE + cv, false); 
    Polyhedron Bad(NP + NE + cv, false);
    Polyhedron ForcedGood(NP + NE + cv, false); 
    Polyhedron ForcedBad(NP + NE + cv, false);
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const unsigned int ctrl_flags = it->trans->control;
        const VSZPoly* s = static_cast<const VSZPoly*>(it->node->get_state());

        if (!(ctrl_flags & CTRL_CONTROLLABLE))
        {
            if (!it->up_to_date)
            {
                if (it->pred.wp != nullptr)
                {
                    delete it->pred.wp;
                }
                it->pred.wp = new Polyhedron(this->predecessor(s, *it->node->winning.wp, it->trans, false));


                if (it->pred2.wp != nullptr)
                {
                    delete it->pred2.wp;
                }
                if (!it->trans->timing->unbounded)
                {
                    Polyhedron LoseSucc = *it->node->winning.wp;
                    LoseSucc.negation_assign();
                    LoseSucc.intersection_assign(*s->D);
                    it->pred2.wp = new Polyhedron(this->predecessor(s, LoseSucc, it->trans, true));
                }
                
                it->up_to_date = true;
            }

            Good.add_reduce(*it->pred.wp);
            if (!it->trans->timing->unbounded)
            {
                ForcedBad.add_reduce(*it->pred2.wp);
            }
        } else {
            if (!it->up_to_date)
            {
                if (it->pred.wp != nullptr)
                {
                    delete it->pred.wp;
                }

                Polyhedron LoseSucc = *it->node->winning.wp;
                LoseSucc.negation_assign();
                LoseSucc.intersection_assign(*s->D);
                it->pred.wp = new Polyhedron(this->predecessor(s, LoseSucc, it->trans, false));

                
                if (it->pred2.wp != nullptr)
                {
                    delete it->pred2.wp;
                }
                if (!it->trans->timing->unbounded)
                {
                    it->pred2.wp = new Polyhedron(this->predecessor(s, *it->node->winning.wp, it->trans, true));
                }
                it->up_to_date = true;
            }

            Bad.add_reduce(*it->pred.wp);
            if (!it->trans->timing->unbounded)
            {
                ForcedGood.add_reduce(*it->pred2.wp);
            }
        }
    }
    // cout << "-----------------------------------------------------"  << endl;
    // cout << "Good is " << endl << Good << endl;
    // cout << "Bad is " << endl << Bad << endl;
    Polyhedron NotBad(Bad);
    NotBad.negation_assign();
    ForcedGood.intersection_assign(NotBad);
    Bad.add_reduce(ForcedBad);
    Good.add_reduce(ForcedGood);

    Polyhedron NewWinning = Good.predt_sem(rates, Bad);
    NewWinning.intersection_assign(*D);

    // cout << "New Winning: " << endl; 
    // cout << NewWinning <<endl;

    //if (!n->winning.wp->exact_contains(NewWinning))
    bool result = false;
    if (!n->winning.wp->contains(NewWinning))
    {
        // cout << "   bigger: " << endl << NewWinning << endl;
        *n->winning.wp = NewWinning;
        if (cv > 0)
        {
            n->back_cost = NewWinning.minimize(Var(NP+NE));
            cout << n->back_cost << endl;
        }

        // if (!job.notrace)
        // {
        //     n->clear_strategy(WSET_POLY);
        //     for (it = n->succs.begin(); it != n->succs.end(); it++)
        //     {
        //         const unsigned int ctrl_flags = it->trans->control;
        //         if (!(ctrl_flags & CTRL_CONTROLLABLE))
        //         {
        //             LocalStrategy st;
        //             st.action = it->trans;
        //             st.type = STRAT_ACTION;
        //             for (unsigned i = 0; i < NE; i++)
        //             {
        //                 st.en.push_back(en[i]);
        //             }
        //             st.domain.wp = new Polyhedron(*it->pred.wp);
        //             st.domain.wp->reduce();
        //             add_local_strategy(WSET_POLY, n->strategy, st);
        //         }
        //     }

        //     LocalStrategy wait;
        //     wait.action = nullptr;
        //     wait.type = STRAT_ACTION;
        //     for (unsigned i = 0; i < NE; i++)
        //     {
        //         wait.en.push_back(en[i]);
        //     }
        //     wait.domain.wp = new Polyhedron(NewWinning);
        //     add_local_strategy(WSET_POLY, n->strategy, wait);        }

        //n->losing.wp = NewWinning.complement();
        result = true;
    }

    return result;
}

Polyhedron* VSZPoly::get_domain() const
{
    return D;
}

