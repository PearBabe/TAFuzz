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
#include <sstream>
#include <cmath>
#include <climits>

#include <color_output.hh>

#include <vsclass.hh>
#include <vscpoly.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <vscpar.hh>
#include <result.hh>
#include <property.hh>

#include <time_interval.hh>

#include <rvalue.hh>
#include <lexpression.hh>

#include <graph_node.hh>
#include <control_reach.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

// Constructors
VSCPoly::VSCPoly(const Job& job): VSSPoly(job) 
{
}

VSCPoly* VSCPoly::init(const Job& job)
{
    VSCPoly* R = new VSCPoly(job);
    R->init_constraints();

    return R;
}

void VSCPoly::init_constraints()
{
    const unsigned NP = job.cts.nparams();
    for (unsigned i = 0; i< NE; i++)
    {
        const Transition& f = *en[i];
        newen_constraints(f,NP+i);
    }

    if (job.computation_mode == TIMED_PARAMETRIC && !job.no_abstract)
        time_saturation();
}

void VSCPoly::newen_constraints(const Transition& f, const unsigned i)
{
    const Var vi(i);

    // vi > l or vi >= l
    const value l = f.timing->lbound.evaluate(V, job.cts.statics).to_int();
    cstr_rel r = f.timing->lstrict ? CSTR_GSTRICT : CSTR_GWEAK;
    D->constrain(vi - l,r);

    if (!f.timing->unbounded)
    {
        // vi < u or vi <= u
        const value u = f.timing->ubound.evaluate(V, job.cts.statics).to_int();
        r = f.timing->ustrict ? CSTR_LSTRICT : CSTR_LWEAK;
        D->constrain(vi - u,r);
    }
}

bool VSCPoly::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    bool r = true;
    if (e != NULL)
    {
        const unsigned NP = job.cts.nparams();
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();

        D->constrain(q*Var(NP+i) - v,CSTR_EQ);
        r = !D->empty();
    }

    return r;
}


// Clockval properties
void VSCPoly::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
    const unsigned NP = job.cts.nparams();
    unsigned i = 0;
    for (i=0; i<NE && en[i] != t; i++);

    // The transition is not enabled:
    if (i == NE)
    {
        v = 0;
        s = false;
        u = false;
        d = true;
    } else {
        cvalue rv = 0, rd;
        bool rs, rb, lb;

        Polyhedron P(*D);
        P.project_on(i+NP, s, lb, v, rs, rb, rv, q, rd);
        
        u = !lb;
        d = false;
    }
}

void VSCPoly::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
    const unsigned NP = job.cts.nparams();
    unsigned i = 0;
    for (i=0; i<NE && en[i] != t; i++);

    // The transition is not enabled:
    if (i == NE)
    {
        v = 0;
        q = 1;
        s = true;
        u = true;
        d = true;
    } else {
        cvalue lv = 0, ld;
        bool ls, lb, rb;

        Polyhedron P(*D);
        P.project_on(i+NP, ls, lb, lv, s, rb, v, ld, q);
        
        u = !rb;
        d = false;

    }
}



VSCPoly::VSCPoly(const VSCPoly& S, unsigned k): VSSPoly(S,k)
{
}

VSCPoly::VSCPoly(const VSCPoly& S): VSSPoly(S)
{
}

PWNode* VSCPoly::copy(const Instruction* I) const
{
    if (I == NULL)
        return new VSCPoly(*this);
    else
    {
        const unsigned NP = job.cts.nparams();
        VSCPoly* s = new VSCPoly(*this, *I);

        unsigned S_indices[NE + NP];
        unsigned indices[s->NE + NP];

        s->remap(*this, NE, indices, S_indices, 0);
        s->constrain_new(*this, NE, indices, S_indices);

        return s;
    }
}

PWNode* VSCPoly::successor(unsigned i)
{
    const unsigned NP = job.cts.nparams();

    VSCPoly* R = new VSCPoly(*this, i);
    R->firability_constraints(*this, i);
    R->time_elapsing(*this, i);

    unsigned S_indices[NE+NP];
    unsigned indices[R->NE+NP];

    R->remap(*this, i, indices, S_indices, 0);
    R->constrain_new(*this, i, indices, S_indices);

    if (job.computation_mode == TIMED_PARAMETRIC && !job.no_abstract)
        R->time_saturation();

    return R;
}

void VSCPoly::firability_constraints(const VSCPoly& S, unsigned k)
{
    const unsigned NP = job.cts.nparams();

    const Transition& tf = *S.en[k];
    const Var vf(NP + k);
    const value sf = tf.speed.evaluate(S.V, job.cts.statics).to_int();

    // Firability constraints
    for (unsigned i = 0; i< S.NE; i++)
    {
        const Transition& ti = *S.en[i];
        const value si = ti.speed.evaluate(S.V, job.cts.statics).to_int();
        if (i != k && si != value(0))
        {
            Var vi(NP + i);
            if (ti.has_priority_over(tf, S.V, job.cts.statics)) 
            {
                D->constrain(si*vf - sf*vi, CSTR_LSTRICT);
            } else { 
                D->constrain(si*vf - sf*vi, CSTR_LWEAK);
            }
        }
    }
}

void VSCPoly::time_elapsing(const VSCPoly& S, unsigned k)
{
    const unsigned NP = job.cts.nparams();

    const Transition& tf = *S.en[k];
    const Var vf(NP + k);
    const value sf = tf.speed.evaluate(S.V, job.cts.statics).to_int();

    // Time elapsing
    for (unsigned i = 0; i< S.NE; i++)
    {
        const Transition& ti = *S.en[i];
        const value si = ti.speed.evaluate(S.V, job.cts.statics).to_int();

    		if (si != value(0) && i != k)
    		{
            const Var vi(NP + i);
            const LinearExpression expr = sf * vi - si * vf;
            D->affine_image(vi, expr, sf);
    		}
    }
}

void VSCPoly::constrain_new(const VSCPoly& S, unsigned k, unsigned indices[], unsigned S_indices[])
{
    const unsigned NP = job.cts.nparams();
    const VSCPoly* Sp = static_cast<const VSCPoly*>(S.parent);

    // Reconstrain newly enabled transitions
    for (unsigned i = 0; i < NE; i++)
    {
        if (indices[i + NP] == S.D->dimension() // normal (successor) case
            || (k == S.NE && (Sp == NULL || S_indices[indices[i + NP]] == Sp->D->dimension())))
        {
            const Transition& g = *en[i];
            newen_constraints(g, NP + i);
        }
    }
}

VSCPoly::VSCPoly(const VSCPoly& S, const Instruction& I): VSSPoly(S,I)
{   
    this->D = new Polyhedron(*S.D);
}

void VSCPoly::time_saturation()
{       
    Log.start("TE");
    const unsigned NP = job.cts.nparams();
    cvalue future_rates[NE+NP]; 
    cvalue past_rates[NE+NP]; 
    
    // All regular clocks in the cases when this function is called
    for (unsigned i=0; i < NP; i++)
    {
        future_rates[i] = 0;
        past_rates[i] = 0;
    }

    for (unsigned i=0; i < NE; i++)
    {
        future_rates[i+NP] = 1;
        past_rates[i+NP] = -1;
    }

    D->future_assign(future_rates);
    D->future_assign(past_rates);

    // Positivity constraints
    for (unsigned i=0; i<NE; i++)
        this->D->constrain(LinearExpression(Var(NP+i)), CSTR_GWEAK);

    Log.stop("TE");
}

bool VSCPoly::firable(unsigned i) const
{
    Log.start("firable");
    bool result = false;

    const unsigned NP = job.cts.nparams();
    const Var vi(NP + i);
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
        Polyhedron F(D->dimension(), true);
        for (unsigned j = 0; j< NE; j++)
        {
            const Transition& tj = *en[j];
            value sj = tj.speed.evaluate(V, job.cts.statics).to_int();
            if (i!=j && sj != value(0))
            {
                const Var vj(NP + j);
                if(tj.has_priority_over(ti, V, job.cts.statics))
                {
                    F.constrain(sj*vi - si*vj, CSTR_LSTRICT);
                } else {
                    F.constrain(sj*vi - si*vj, CSTR_LWEAK);
                }
            }
        }
        result =  D->intersects(F);
    }
    Log.stop("firable");

    return result;
}

// -------------------------------- control ------------------------------------
PResult* VSCPoly::update_result(const GraphNode* n, PResult* r) const
{   
    vector<unsigned> dimsu;
    for (unsigned i = 0; i < NE; i++)
    {
        if (!(en[i]->control & CTRL_CONTROLLABLE))
        {
            dimsu.push_back(i + job.cts.nparams());
        }
    }

    //cout << "full winning" <<endl;
    //cout << w.to_string() << endl;

    Polyhedron W = n->winning.wp->uprojection(dimsu, *D);
    //cout << "winning on c" << endl;
    //cout << r.to_string() << endl;

    return init_result(!W.empty());
}


bool VSCPoly::update_reach(GraphNode* n) const
{
    //cout << "==============================================================================" << endl;
    //cout << to_string() << endl;
    const unsigned NP = job.cts.nparams(); 
    Polyhedron NewWinning(NE + NP, false); // Empty
    // Complement of bad states
    Polyhedron Goodu(NE + NP, false); // Empty
    Polyhedron NotBadu(NE + NP, true); // Universal
    Polyhedron NotBadc(NE + NP, true); // Universal

    for (auto& succ : n->succs)
    {
        unsigned k = 0;
        while (en[k] != succ.trans)
        {
            // Find the index of transition *ic in en
            k++;
        }

        if (!succ.up_to_date)
        {
            // Good predecessors
            if (succ.pred.wp != nullptr)
            {
                delete succ.pred.wp;
            }
            succ.pred.wp = new Polyhedron(pred(static_cast<const VSCPoly*>(succ.node->get_state()), succ.tgt.tp, succ.node->winning.wp, k, true));

            // Bad predecessors
            if (succ.pred2.wp != nullptr)
            {
                delete succ.pred2.wp;
            }
            Polyhedron bad(*succ.node->winning.wp);
            bad.negation_assign();
            if (succ.tgt.tp != nullptr)
            {
                bad.intersection_assign(*succ.tgt.tp);
            } else {
                bad.intersection_assign(*static_cast<const VSCPoly*>(succ.node->get_state())->D);
            }
            succ.pred2.wp = new Polyhedron(pred(static_cast<const VSCPoly*>(succ.node->get_state()), succ.tgt.tp, &bad, k, false));
            succ.pred2.wp->negation_assign();
            succ.pred2.wp->intersection_assign(*D);
            
            succ.up_to_date = true;
        }

        // Winning states reachable by any transition

        if ((succ.trans->control & CTRL_CONTROLLABLE))
        {
            NewWinning.add_reduce(*succ.pred.wp);
            NotBadc.intersection_assign(*succ.pred2.wp);
        } else {
            Goodu.add_reduce(*succ.pred.wp);
            NotBadu.intersection_assign(*succ.pred2.wp);
        }

    }

    //cout << "cGood" << endl << NewWinning.to_string() << endl;
    //cout << "uGood" << endl << Goodu.to_string() << endl;
    //cout << "cNotBad" << endl << NotBadc.to_string() << endl;
    //cout << "uNotBad" << endl << NotBadu.to_string() << endl;
    Goodu.intersection_assign(NotBadc);
    //Goodu.intersection_assign(NotBadu);

    NewWinning.add_reduce(Goodu);
    NewWinning.intersection_assign(NotBadu);

    //cout << "new winning" << endl;
    //cout << NewWinning.to_string() << endl;
    //cout << "old winning" << endl;
    //cout << n->winning.wp->to_string() << endl;

    if (!n->winning.wp->contains(NewWinning))
    {
        //cout << "more winning!" << endl;
        n->winning.wp->clear();
        *n->winning.wp = NewWinning;


        if (!job.notrace)
        {
            if (!n->preds.empty())
            {
                for (auto p: n->preds)
                {    
                    LocalStrategy st;
                    st.action = p.trans;
                    st.type = STRAT_RESET;

                    const VSCPoly* s = static_cast<const VSCPoly*>(p.node->get_state());
                    const unsigned old_size = s->NE;
                    const unsigned size = NE;
                    unsigned indices[size + NP];
                    
                    // Parameters do not move
                    for (unsigned i = 0; i < NP; i++)
                    {
                        indices[i] = i;
                    }

                    map_indices(*s, p.trans, indices, NP);

                    // Eliminate newly enabled transitions
                    vector<unsigned> dimsu;

                    for (unsigned i = 0; i < size; i++)
                    {
                        // We want the uncontrollable newly enabled to uproj them
                        if (indices[i + NP] == old_size + NP) 
                        {
                            if (!(en[i]->control & CTRL_CONTROLLABLE)) 
                            {
                                dimsu.push_back(i + NP);
                            } else {
                                st.ctr.push_back(en[i]);
                                st.en.push_back(en[i]);
                            }
                        } else {
                            st.en.push_back(en[i]);
                        }
                    }

                    st.domain.wp = new Polyhedron(NewWinning.uprojection(dimsu, *D));

                    add_local_strategy(WSET_POLY, n->strategy, st);
                }
            } else {
                // Initial state
                LocalStrategy st;
                st.action = nullptr;
                st.type = STRAT_RESET;

                const unsigned size = NE;
                vector<unsigned> dimsu;

                for (unsigned i = 0; i < size; i++)
                {
                    if (!(en[i]->control & CTRL_CONTROLLABLE)) 
                    {
                        dimsu.push_back(i + NP);
                    } else {
                        st.ctr.push_back(en[i]);
                        st.en.push_back(en[i]);
                    }
                }

                st.domain.wp = new Polyhedron(NewWinning.uprojection(dimsu, *D));

                add_local_strategy(WSET_POLY, n->strategy, st);
            }

            for (auto succ: n->succs)
            {
                const unsigned int ctrl_flags = succ.trans->control;
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    LocalStrategy st;
                    st.action = succ.trans;
                    for (unsigned i = 0; i < NE; i++)
                    {
                        st.en.push_back(en[i]);
                    }
                    st.type = STRAT_ACTION_CLASS;
                    st.domain.wp = new Polyhedron(*succ.pred.wp);
                    st.domain.wp->intersection_assign(NotBadu);
                    //st.domain.wp->reduce();
                    add_local_strategy(WSET_POLY, n->strategy, st);
                }
            }


        }


        return true;
    }

    return false;
}

bool VSCPoly::update_safe(GraphNode* n) const
{
    cout << error_tag(color_output) << "Safety not implemented with state classes." << endl;
    exit(1);
}

Polyhedron VSCPoly::pred(const VSCPoly* s, const Polyhedron* rsD, const Polyhedron* w, const unsigned k, const bool controllable) const
{
    const unsigned succ_size = s->NE;
    const unsigned size = NE;
    const unsigned NP = job.cts.nparams();

    Polyhedron sD(rsD != nullptr? *rsD: *s->D);
    Polyhedron rw(*w);
    if (rsD != nullptr)
    {
        rw.intersection_assign(sD);
    }
    
    unsigned indices[succ_size + NP];
    unsigned rindices[size + NP];

    // Do not move parameters around
    for (unsigned i = 0; i < NP; i++)
    {
        indices[i] = i;
        rindices[i] = i;
    }

    // Map starting from the transition dimensions
    s->map_indices(*this, en[k], indices, NP);

    vector<unsigned> dimsc;
    vector<unsigned> dimsu;
    unsigned offset = 0; // count the number of u transitions that will be 
                         // removed by the uprojection before a given c transition
                         // or the opposite depending on whether we do upred or cpred
    for (unsigned i = 0; i < succ_size; i++)
    {
        if (indices[i + NP] == size + NP)
        {
            if (controllable)
            {
                if (s->en[i]->control & CTRL_CONTROLLABLE) 
                {
                    dimsc.push_back(i + NP - offset);
                } else {
                    dimsu.push_back(i + NP);
                    offset++;
                }
            } else {
                if (s->en[i]->control & CTRL_CONTROLLABLE) 
                {
                    dimsc.push_back(i + NP);
                    offset++;
                } else {
                    dimsu.push_back(i + NP - offset);
                }
            }
        }
    }

    Polyhedron r(succ_size - dimsc.size() - dimsu.size(), false);
    if (controllable)
    {
        // There exist values for c newly enabled transitions such that for all values 
        // of newly enabled u transitions we win
        Polyhedron rc = rw.uprojection(dimsu, sD);
        r = rc.eprojection(dimsc);
    } else {
        Polyhedron ru = rw.eprojection(dimsc);
        Polyhedron sDproj = sD.eprojection(dimsc);
        r = ru.uprojection(dimsu, sDproj);
    }

    // Remap to match the parent state class indices
    for (unsigned i = 0; i < size; i++)
    {
        rindices[i + NP] = r.dimension();
    }

    offset = 0;
    for (unsigned i = 0; i < succ_size; i++)
    {
        if (indices[i + NP] != size + NP)
        {
            rindices[indices[i + NP]] = i + NP - offset;
        } else {
            // A newly enabled transition (thus eliminated)
            offset++;
        }
    }

    // Remap to the source class size
    // Recall that here we have only persistent variables
    r.remap(rindices, size + NP);

    // Apply reverse variable changes
    // t_i' + tf = t_i
    const cvalue sf = en[k]->speed.evaluate(V, job.cts.statics).to_int();
    for (unsigned i = 0; i < succ_size; i++)
    {
        if (indices[i + NP] < size + NP)
        {
            const cvalue si = en[indices[i + NP] - NP]->speed.evaluate(V, job.cts.statics).to_int();
            r.affine_image(Var(indices[i + NP]), sf * Var(indices[i + NP]) + si * Var(k + NP), sf);
        }
    }

    // Apply firability constraints
    for (unsigned i = 0; i < size; i++)
    {
        if (k != i)
        {
            const cvalue si = en[i]->speed.evaluate(V, job.cts.statics).to_int();
            r.constrain(si * Var(k + NP) - sf * Var(i + NP), CSTR_LWEAK);
        }
    }

    // propagate the constraints backwards
    r.intersection_assign(*D);

    return r;
}

SuccInfo* VSCPoly::add_succ(GraphNode* src, const Transition* t, PState* s, GraphNode* dst) const
{
    SuccInfo* res = PWNode::add_succ(src, t, s, dst);
    if (res != nullptr && s != nullptr)
    {
        res->tgt.tp = new Polyhedron(*static_cast<const VSCPoly*>(s)->D);
    }
    return res;
}




