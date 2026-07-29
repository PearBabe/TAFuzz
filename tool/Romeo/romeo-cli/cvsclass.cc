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


#include <sstream>
#include <vector>
#include <list>

#include <color_output.hh>
#include <job.hh>
#include <vsclass.hh>
#include <cvsclass.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <rvalue.hh>

using namespace std;
using namespace romeo;

#include <polyhedron.hh>
#include <ppl.hh>

#include <logger.hh>
extern romeo::Logger Log;


vector<LinearExpression> redundancy_removal_and_min(const DBM& D, const vector<LinearExpression>& cs, Avalue& m)
{
    //Log.start("-- redundancy & min");
    PPL_Convex_Polyhedron P(D.dimension(), PPL_UNIVERSE);

    //Log.start("---> dbm to PPL");
    // Put the DBM into the Polyhedron
    for (unsigned i=1; i<D.dimension(); i++)
    {
        if (D(i,0).bounded())
        {
            if (D(i,0).strict())
                P.add_constraint(PPL_Variable(i) < D(i,0).value());
            else 
                P.add_constraint(PPL_Variable(i) <= D(i,0).value());
        }

        if (D(0,i).strict())
            P.add_constraint(PPL_Variable(i) > -D(0,i).value());
        else 
            P.add_constraint(PPL_Variable(i) >= -D(0,i).value());

        for (unsigned j=1; j<i; j++)
        {
            if (D(i,j).bounded() && D(i,j) < D(i,0) + D(0,j))
            {
                if (D(i,j).strict())
                    P.add_constraint(PPL_Variable(i) - PPL_Variable(j) < D(i,j).value());
                else 
                    P.add_constraint(PPL_Variable(i) - PPL_Variable(j) <= D(i,j).value());
            }
            if (D(j,i).bounded() && D(j,i) < D(j,0) + D(0,i))
            {
                if (D(j,i).strict())
                    P.add_constraint(PPL_Variable(j) - PPL_Variable(i) < D(j,i).value());
                else 
                    P.add_constraint(PPL_Variable(j) - PPL_Variable(i) <= D(j,i).value());
            }
        }
    }
    //Log.stop("---> dbm to PPL");

    //Log.start("---> constraints to PPL");
    // Now the constraints
    vector<LinearExpression>::const_iterator ic;
    for (ic=cs.begin(); ic != cs.end(); ic++)
        P.add_constraint(ic->den() * PPL_Variable(0) >= ic->to_PPL());
    //Log.stop("---> constraints to PPL");

    //Log.start("--->  PPL min");
    // Compute the min
    POLY_COEFFICIENT_TYPE n, d;
    bool b, ns;
    b = P.minimize(PPL_Linear_Expression(PPL_Variable(0)), n,d,ns);
    if (b)
    {
#ifdef POLY_COEFFICIENT_MPZ
        const cvalue cn = mpz_get_si(n.get_mpz_t());
#else
        const cvalue cn = n;
#endif
        m = Avalue(cn, ns? 1: 0);
    } else {
        m = Avalue::minus_infinity;
    }
    //Log.stop("--->  PPL min");


    //Log.start("--->  PPL to DBM");
    // Finally retrieve the constraints
    PPL_Constraint_System C = P.minimized_constraints();
    PPL_Constraint_System::const_iterator k;

    vector<LinearExpression> newcs;
    for (k=C.begin(); k!=C.end(); k++)
    {
        if (k->coefficient(PPL_Variable(0)) != 0)
        {
#ifdef POLY_COEFFICIENT_MPZ
            const cvalue dk = mpz_get_si(k->inhomogeneous_term().get_mpz_t());
#else
            const cvalue dk = k->inhomogeneous_term();
#endif
            LinearExpression L(-dk);
            for (unsigned i=1; i<D.dimension(); i++)
            {
#ifdef POLY_COEFFICIENT_MPZ
                const cvalue di = mpz_get_si(k->coefficient(PPL_Variable(i)).get_mpz_t());
#else
                const cvalue di = k->coefficient(PPL_Variable(i));
#endif
                L = L + Var(i)*(-di);
            }

#ifdef POLY_COEFFICIENT_MPZ
            const cvalue d0 = mpz_get_si(k->coefficient(PPL_Variable(0)).get_mpz_t());
#else
            const cvalue d0 = k->coefficient(PPL_Variable(0));
#endif
            newcs.push_back(L / d0);
        } 

    }
    //Log.stop("--->  PPL to DBM");
    //Log.stop("-- redundancy & min");

    return newcs;
}


vector<LinearExpression> redundancy_removal_light(const DBM& D, const vector<LinearExpression>& cs)
{
    vector<LinearExpression> newcs;
    vector<LinearExpression>::const_iterator ic;
    vector<LinearExpression>::iterator ico;
    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        bool ok = true;
        vector<LinearExpression>::iterator ico;
        ico = newcs.begin(); 
        while (ico != newcs.end())
        {
            cvalue cden = abs(ic->den() * ico->den());
            const LinearExpression diff1 = cden* (*ico) - cden* (*ic);
            if (diff1.non_negative() || D.min(diff1).value() >= 0)
            {
                ok = false;
                ico++;
            } else {
                const LinearExpression diff2 = cden* (*ic) - cden * (*ico);
                if (diff2.non_negative() || D.min(diff2).value() >= 0)
                {
                    ico = newcs.erase(ico);
                } else {
                    ico++;
                }
            }
        }

        if (ok)
            newcs.push_back(*ic);
    }

    return newcs;

}

CVSClass* CVSClass::init(const Job& job)
{
    return new CVSClass(job);
}

PWNode* romeo::CVSClass::successor(unsigned i)
{
    return new CVSClass(*this, i);
}

CVSClass::CVSClass(const Job& j): VSClass(j)
{
    costs.push_back(LinearExpression());
    cmin = 0;
}

CVSClass::CVSClass(const CVSClass& S): VSClass(S), costs(S.costs), cmin(S.cmin)
{
}

void CVSClass::fm_fired_constraints(const DBM& SD, const unsigned m, const unsigned indices[], const bool eliminated[], vector<LinearExpression>& fmcs_pos, vector<LinearExpression>& fmcs_neg)
{
    fmcs_pos.push_back(LinearExpression(-Avalue(SD(0,m))));
    if (SD(m,0) != time_bound::infinity)
        fmcs_neg.push_back(LinearExpression(Avalue(SD(m,0))));

    for (unsigned i = 1; i < SD.dimension(); i++)
    {
        if (i != m && !eliminated[i]) 
        {
            // maybe need to additionally check for not newly enabled here
            //bool ok = true;
            //for (unsigned j = 0; j < i && ok; j++)
            //    if (j != m)
            //        ok = (SD(j,0) < SD(j,i) + SD(i,0));

            //if (ok)
            fmcs_pos.push_back(-Avalue(SD(0,i)) - Var(i));
            if (SD(i,0) != time_bound::infinity)
                fmcs_neg.push_back(Avalue(SD(i,0)) - Var(i));
        }
    }
}

void CVSClass::fm_constraints(const DBM& SD, const unsigned m, const unsigned indices[], const unsigned f, const bool eliminated[], vector<LinearExpression>& fmcs_pos, vector<LinearExpression>& fmcs_neg)
{
    // Should be already eliminated
    // if (!eliminated[f])
    // {
    //     fmcs_neg.push_back(SD(m,0) - Var(f));
    //     fmcs_pos.push_back(-SD(0,m) - Var(f));
    // }
    //fmcs_neg.push_back(SD(m,f));
    //fmcs_pos.push_back(max(-SD(f,m),time_bound::zero));

    fmcs_pos.push_back(LinearExpression(-Avalue(SD(0,m))));
    if (SD(m,0) != time_bound::infinity)
        fmcs_neg.push_back(LinearExpression(Avalue(SD(m,0))));
    for (unsigned i = 1; i < SD.dimension(); i++)
    {
        if (i != f && i != m && !eliminated[i]) 
        {
            // maybe need to additionally check for not newly enabled here
            // bool ok = true;
            //for (unsigned j = 0; j < i && ok; j++)
            //    if (j != m)
            //        ok = (SD(m,i) < SD(m,j) + SD(j,i));

            //if (ok)
            if (SD(i,m) != time_bound::infinity)
                fmcs_pos.push_back(-Avalue(SD(i,m)) + Var(i));
            if (SD(m,i) != time_bound::infinity)
                fmcs_neg.push_back(Avalue(SD(m,i)) + Var(i));
        }
    }
}

set<LinearExpression,ltle> CVSClass::fm_combine(const vector<LinearExpression>& cs, const unsigned m)
{
    set<LinearExpression,ltle> result;
    vector<LinearExpression>::const_iterator ic, jc;

    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        const cvalue cim = ic->coefficient(m);
        if (cim < 0)
        {
            for (jc = cs.begin(); jc != cs.end(); jc++)
            {
                const cvalue cjm = jc->coefficient(m);
                if (cjm > 0)
                {
                    const LinearExpression L = ((*ic)*cjm - (*jc)*cim) / (cjm - cim);
                    result.insert(L);
                }
            }
        }
    }
 
    // The result has the indices of the previous class
    return result;
}


vector<LinearExpression> CVSClass::fm_eliminate(const DBM& SD, const unsigned m, const vector<LinearExpression>& cs, const unsigned f, const unsigned indices[], const bool disabled[])
{
    //Log.start("-- fm_eliminate");
    vector<LinearExpression>::const_iterator ic, jc;
    // First compute combinations of expressions with positive and negative coefficients
    // of the variable to project out

    set<LinearExpression,ltle> setle = fm_combine(cs, m);

    // Now compute lower and upper bounds depending on sign
    vector<LinearExpression> fmcs_neg, fmcs_pos;
    if (m == f)
        fm_fired_constraints(SD, m, indices, disabled, fmcs_pos, fmcs_neg);
    else
        fm_constraints(SD, m, indices, f, disabled, fmcs_pos, fmcs_neg);

    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        const cvalue cm = ic->coefficient(m);

        if (cm != 0)
        {
            vector<LinearExpression>* fmcs;
            if (cm > 0)
                fmcs = &fmcs_pos;

            if (cm < 0)
                fmcs = &fmcs_neg;

            for (jc = fmcs->begin(); jc != fmcs->end(); jc++)
                setle.insert(*ic -cm*Var(m) + cm * (*jc));
        } else {
            setle.insert(*ic);
        }
    }

    vector<LinearExpression> newcs;
    set<LinearExpression,ltle>::iterator is;
    for (is = setle.begin(); is != setle.end(); is++)
    {
        newcs.push_back(*is);
    }

    //Log.stop("-- fm_eliminate");
    return newcs;
}



CVSClass::CVSClass(const CVSClass& S, unsigned k): VSClass(S,k)
{
    //Log.start("-- cvsclass");
    // Compute the new costs
    // First find the non-redundant new terms 
    // c*(ti - Dik) if c > 0
    // c*(ti + Dki) if c < 0
    // 0 if c = 0

    const unsigned size = NE +1;
    const unsigned old_size = S.NE +1;

    const Transition& tf = *S.en[k];

    const cvalue c = job.cts.cost_rate(S.V, job.non_negative_costs);

    unsigned indices[size];
    // The reference clock does not move
    indices[0] = 0;

    map_indices(S, &tf, indices, 1);

    // Find disabled transitions
    bool disabled[old_size];
    for (unsigned i = 0; i < old_size; i++)
        disabled[i] = true;

    for (unsigned j = 0; j < size; j++)
        if (indices[j] < old_size)
            disabled[indices[j]] = false;

    vector<LinearExpression> cs = S.costs;
    vector<LinearExpression>::iterator ic,jc;

    //cout << "================================================================================" << endl;
    //cout << "initially" << endl;
    // Discrete cost
    value dc = tf.get_cost(S.V, job.cts.statics, job.non_negative_costs);

    // Variable change: ti -> ti + tk
    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        // Compute the new coefficient of k
        // after variable change plus local cost increment
        cvalue C[old_size];
        ic->coefficients(old_size,C);
        cvalue ck = c - C[k+1];
        for (unsigned m=0; m<old_size; m++)
            ck += C[m];
        *ic = *ic + ck*Var(k+1) + dc;
        //cout << *ic << endl;
    }
    //cout << "------------------------------------------------------------------------------" << endl;
    bool eliminated[S.NE];
    eliminated[0] = true;
    for (unsigned m = 1; m < old_size; m++)
        eliminated[m] = false;

    // First eliminate the fired transition
    cs = S.fm_eliminate(*S.D, k+1, cs, k+1, indices, eliminated);
    eliminated[k+1] = true;

    //cout << "fired transition eliminated" << endl;
    //for (ic = cs.begin(); ic != cs.end(); ic++)
    //    cout << *ic << endl;
    //cout << "------------------------------------------------------------------------------" << endl;
    // Compute the new DBM for old variables
    DBM SD(S.NE+1);
    for (unsigned i = 1; i < S.NE+1; i++)
    {
        SD(i,0) = (*S.D)(i,k+1);
        //SD(0,i) = time_bound::infinity;
        //for (unsigned j = 1; j < S.NE+1; j++)
        //    SD(0,i) = min(SD(0,i), (*S.D)(j,i));
        SD(0,i) = time_bound::zero;
        for (unsigned j = 1; j < S.NE+1; j++)
        {
            const Transition& tj = *S.en[j-1];
            // with j == indices[i] we have min with <= 0
            time_bound vji = (*S.D)(j,i); 
            
            if (j != i && tj.has_priority_over(tf, S.V, job.cts.statics))
            {
                vji = vji.strictify();
            }

            SD(0,i) = std::min(SD(0,i), vji);
        }
    }
    
    for (unsigned i = 1; i < S.NE+1; i++)
    {
        for (unsigned j = 1; j < S.NE+1; j++)
            SD(i,j) = min((*S.D)(i,j), SD(i,0) + SD(0,j));
    }

    for (unsigned m = 1; m < old_size; m++)
    {
        // Fourier-Motzkin to eliminate each disabled transition
        // from the cost
        if (m != k + 1 && disabled[m])
        {
            cs = S.fm_eliminate(SD, m, cs, k+1, indices, eliminated);
            eliminated[m] = true;
        } 
    }
    
    //cout << "new DBM" << endl;
    //cout << SD << endl;
    //cout << "disabled transitions eliminated" << endl;
    //for (ic = cs.begin(); ic != cs.end(); ic++)
    //    cout << *ic << endl;
    //cout << "------------------------------------------------------------------------------" << endl;
    // Eliminate all other variables to get the actual cost
    //vector<LinearExpression> acs = cs;
    //for (unsigned m = 1; m < old_size; m++)
    //{
    //    // Fourier-Motzkin to eliminate each disabled transition
    //    // from the cost
    //    if (!eliminated[m])
    //    {
    //        acs = S.fm_eliminate(SD, m, acs, k+1, indices, eliminated);
    //        eliminated[m] = true;
    //    }
    //}

    ////cout << "all other transitions eliminated" << endl;
    ////for (ic = acs.begin(); ic != acs.end(); ic++)
    ////    cout << *ic << endl;
    ////cout << "------------------------------------------------------------------------------" << endl;
    //if (acs.begin() == acs.end())
    //{
    //    minc = LinearExpression(time_bound::minus_infinity);
    //} else {
    //    minc = *acs.begin();
    //    for (ic = ++acs.begin(); ic != acs.end(); ic++)
    //        minc = minc.max_with_cst(*ic); 
    //}

    // Compute the reverse map of indices
    unsigned rindices[old_size];
    for (unsigned i = 0; i < old_size; i++)
        rindices[i] = size;

    for (unsigned i = 0; i < size; i++)
        if (indices[i] < old_size)
            rindices[indices[i]] = i;

    for (ic = cs.begin(); ic != cs.end(); ic++)
        ic->remap(size, rindices);

    costs = redundancy_removal_and_min(*D, cs, cmin);
    
    //Log.stop("-- cvsclass");
    
}

CVSClass::CVSClass(const CVSClass& S, const Instruction& I): VSClass(S,I), cmin(S.cmin)
{
}

Avalue CVSClass::min_cost() const
{
    return cmin;
}

std::string CVSClass::to_string() const
{

    stringstream domain;
    domain << VSClass::to_string() << endl;
    
    
    vector<LinearExpression>::const_iterator i;
    for (auto i: costs)
    {
        domain << " c >= " << i << endl;
    }

    domain << endl;
    

    cvalue c = (job.cts.cost.is_null()? 0 : job.cts.cost.evaluate(V, job.cts.statics).to_int());

    domain << "local cost = " << c << endl;
    domain << "mincost = "; 

    const Avalue minc = min_cost();

    domain << minc;

    return domain.str();
}

PWNode* CVSClass::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new CVSClass(*this);
    } else {
        return new CVSClass(*this,*I);
    }
}



CVSClass::~CVSClass()
{
}

