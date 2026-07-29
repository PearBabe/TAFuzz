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
#include <cvsclass_sp.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <time_interval.hh>
#include <avalue.hh>
#include <rvalue.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern romeo::Logger Log;

bool ltpledbm::operator() (const pair<LinearExpression, DBM*>& a, const pair<LinearExpression, DBM*>& b) const
{
    return a.first < b.first || (a.first == b.first && a.second->compare(*b.second) == LESS);
}

// -----------------------------------------------------------------------------

CVSClassSp* CVSClassSp::init(const Job& job)
{
    return new CVSClassSp(job);
}

PWNode* romeo::CVSClassSp::successor(unsigned i)
{
    return new CVSClassSp(*this, i);
}

CVSClassSp::CVSClassSp(const Job& j): VSClass(j)
{
    costs.push_back(pair<LinearExpression, DBM*>(LinearExpression(), D));
    cmin = 0;
}

void CVSClassSp::copy_costs(const CVSClassSp& S)
{
    vector<pair<LinearExpression, DBM*> >::const_iterator ic;
    for (ic = S.costs.begin(); ic != S.costs.end(); ic++)
    {
        DBM* ND;
        if (ic->second == S.D)
        {
            ND = D;
        } else {
            ND = new DBM(*ic->second);
        }

        costs.push_back(pair<LinearExpression, DBM*>(ic->first, ND));
    }
}

CVSClassSp::CVSClassSp(const CVSClassSp& S): VSClass(S), cmin(S.cmin)
{
    copy_costs(S);
}

vector<pair<LinearExpression, DBM*> > CVSClassSp::fm_eliminate(const unsigned m, const vector<pair<LinearExpression, DBM*> >& cs, const unsigned f, const vector<bool>& disabled) const
{
    //cout << "===============================================================" << endl;
    //cout << "======================= eliminate =============================" << endl;
    //cout << "===============================================================" << endl;

    vector<pair<LinearExpression, DBM*> > newcs;
    vector<pair<LinearExpression, DBM*> >::const_iterator ic;

    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        vector<pair<LinearExpression, DBM*> > res;
        vector<pair<LinearExpression, DBM*> >::const_iterator jc;
        if (m == f)
        {
            DBM CSD = *ic->second;
            // Compute the new DBMs for old variables
            // cout << "*********** old cost dbm:" << endl << *ic->second << endl;
            DBM& SD = *ic->second;
            const Transition& tf = *en[f-1];
            for (unsigned i = 1; i < NE+1; i++)
            {
                if (i != f)
                {
                    SD(i,0) = SD(i, f);
                    SD(0,i) = time_bound::zero;
                    for (unsigned j = 1; j < NE+1; j++)
                    {
                        const Transition& tj = *en[j-1];
                        // with j == i we have min with <= 0
                        time_bound vji = SD(j, i); 
                        
                        if (j != i && tj.has_priority_over(tf, V, job.cts.statics))
                        {
                            vji = vji.strictify();
                        }

                        SD(0,i) = std::min(SD(0,i), vji);
                    }
                } else {
                    SD(i, 0) = time_bound::zero;
                    SD(0, i) = time_bound::zero;
                }

            }
            
            for (unsigned i = 1; i < NE+1; i++)
            {
                for (unsigned j = 1; j < NE+1; j++)
                    SD(i,j) = min(SD(i,j), SD(i,0) + SD(0,j));
            }

            // If the DBM is empty, just ignore it
            // it cannot fire this transition
            if (SD.is_empty())
            {
                continue;
            }

            //cout << "___________ new cost dbm:" << endl << SD << endl;

            res = fm_eliminate2(CSD, SD, m, ic->first, f, disabled);
        } else {
            res = fm_eliminate2(*ic->second, *ic->second, m, ic->first, f, disabled);
        }

        for (jc = res.begin(); jc != res.end(); jc++)
            newcs.push_back(*jc);
    }

    //cout << "_______________________________________________________________" << endl;
    
    return newcs;
}


vector<pair<LinearExpression, DBM*> > CVSClassSp::fm_eliminate2(DBM& SD, DBM& CSD, const unsigned m, const LinearExpression& L, const unsigned f, const vector<bool>& disabled)
{
    //Log.start(" ----> fm_eliminate (split)");
    // First compute combinations of expressions with positive and negative coefficients
    // of the variable to project out

    vector<pair<LinearExpression, DBM*> > newcs;

    const cvalue cm = L.coefficient(m);

    //cout << "===============================================================" << endl;
    //cout << "m is  " << m << endl;
    //cout << "f is  " << f << endl;
    //cout << "cm is " << cm << endl;
    //cout << "L is " << L << endl;
    //cout << "SD is " << endl << SD << endl;
    //cout << "CSD is " << endl << CSD << endl;
    //cout << "..............................................................." << endl;


    if (cm != 0)
    {
        if (cm > 0)
        {
            if (m == f)
            {

                DBM* ND = new DBM(CSD);

                for (unsigned i = 1; i < SD.dimension() && !ND->is_empty(); i++)
                {
                    if (i != m && !disabled[i]) 
                    {
                        ND->constrain(0, i, SD(0, i) - SD(0, m));
                    }
                }

                if (!ND->is_empty())
                    newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) + Avalue(SD(0, m))), ND));
                else
                    delete ND;

                for (unsigned i = 1; i < SD.dimension(); i++)
                {
                    if (i != m && !disabled[i])
                    {
                        DBM* ND = new DBM(CSD);

                        ND->constrain(i, 0, SD(0, m) - SD(0, i));

                        for (unsigned j = 1; j < SD.dimension() && !ND->is_empty(); j++)
                        {
                            if (j != m && !disabled[j]) 
                            {
                                ND->constrain(i, j, SD(0, j) - SD(0, i));
                            }
                        }

                        if (!ND->is_empty())
                            newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) + Avalue(SD(0, i)) + Var(i)), ND));
                        else
                            delete ND;
                    }
                }
            } else {
                DBM* ND = new DBM(CSD);

                for (unsigned i = 1; i < SD.dimension() && !ND->is_empty(); i++)
                {
                    if (i != m && !disabled[i] && SD(i, m) != time_bound::infinity) 
                    {
                        ND->constrain(i, 0, SD(i, m) - SD(0, m));
                    }
                }
                            
                if (!ND->is_empty())
                    newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) + Avalue(SD(0, m))), ND));
                else
                    delete ND;

                for (unsigned i = 1; i < SD.dimension(); i++)
                {
                    if (i != m && !disabled[i] && SD(i, m) != time_bound::infinity)
                    {
                        DBM* ND = new DBM(CSD);

                        ND->constrain(0, i, SD(0, m) - SD(i, m));

                        for (unsigned j = 1; j < SD.dimension() && !ND->is_empty(); j++)
                        {
                            if (j != m && !disabled[j]) 
                            {
                                ND->constrain(j, i, SD(j, m) - SD(i, m));
                            }
                        }

                        if (!ND->is_empty())
                            newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) + Avalue(SD(i, m)) - Var(i)), ND));
                        else
                            delete ND;
                                                           
                    }
                }
            }
        // ---------------------------------------------------------------------
        } else if (cm < 0) {
            if (m == f)
            {
                if (SD(m, 0) != time_bound::infinity)
                {
                    DBM* ND = new DBM(CSD);

                    for (unsigned i = 1; i < SD.dimension() && !ND->is_empty(); i++)
                    {
                        if (i != m && !disabled[i] && SD(i, 0) != time_bound::infinity) 
                        {
                            ND->constrain(i, 0, SD(i, 0) - SD(m, 0));
                        }
                    }
                    
                    if (!ND->is_empty())
                        newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) - Avalue(SD(m, 0))), ND));
                    else
                        delete ND;
                                
                }

                for (unsigned i = 1; i < SD.dimension(); i++)
                {
                    if (i != m && !disabled[i] && SD(i, 0) != time_bound::infinity)
                    {
                        DBM* ND = new DBM(CSD);

                        if (SD(m, 0) != time_bound::infinity)
                        {
                            ND->constrain(0, i, SD(m, 0) - SD(i, 0));
                        }

                        for (unsigned j = 1; j < SD.dimension() && !ND->is_empty(); j++)
                        {
                            if (j != m && !disabled[j] && SD(j, 0) != time_bound::infinity) 
                            {
                                ND->constrain(j, i, SD(j, 0) - SD(i, 0));
                            }
                        }

                        if (!ND->is_empty())
                            newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) - Avalue(SD(i, 0)) + Var(i)), ND));
                        else
                            delete ND;
                       
                    }
                }
            } else {
                if (SD(m, 0) != time_bound::infinity)
                {
                    DBM* ND = new DBM(CSD);

                    for (unsigned i = 1; i < SD.dimension() && !ND->is_empty(); i++)
                    {
                        if (i != m && !disabled[i] && SD(m, i) != time_bound::infinity) 
                        {
                            ND->constrain(0, i, SD(m, i) - SD(m, 0));
                        }
                    }
                    
                    if (!ND->is_empty())
                        newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) - Avalue(SD(m, 0))), ND));
                    else
                        delete ND;
                }

                for (unsigned i = 1; i < SD.dimension(); i++)
                {
                    if (i != m && !disabled[i] && SD(m, i) != time_bound::infinity)
                    {
                        DBM* ND = new DBM(CSD);

                        if (SD(m, 0) != time_bound::infinity)
                        {
                            ND->constrain(i, 0, SD(m, 0) - SD(m, i));
                        }

                        for (unsigned j = 1; j < SD.dimension() && !ND->is_empty(); j++)
                        {
                            if (j != m && !disabled[j] && SD(m, j) != time_bound::infinity) 
                            {
                                ND->constrain(i, j, (SD(m, j) - SD(m, i)).strictify());
                            }
                        }

                        if (!ND->is_empty())
                            newcs.push_back(pair<LinearExpression, DBM*>(L - cm * (Var(m) - Avalue(SD(m, i)) - Var(i)), ND));
                        else
                            delete ND;
                    }
                }
            }
        }
        delete &CSD;
    } else {
        newcs.push_back(pair<LinearExpression, DBM*>(L, &CSD));
    }

    //cout << "size of newcs is " << newcs.size() << endl;
    //Log.stop(" ----> fm_eliminate (split)");

    return newcs;
}


CVSClassSp::CVSClassSp(const CVSClassSp& S, unsigned k): VSClass(S,k)
{
    //Log.start(" ----> cvsclass_sp");
    // Compute the new costs
    // First find the non-redundant new terms 
    // c*(ti - Dik) if c > 0
    // c*(ti + Dki) if c < 0
    // 0 if c = 0

    const unsigned size = NE +1;
    const unsigned old_size = S.NE +1;

    const cvalue c = job.cts.cost_rate(S.V, job.non_negative_costs);

    vector<unsigned> indices(size, old_size);
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, S.en[k], indices.data(), 1);

    // Find disabled transitions
    vector<bool> disabled(old_size, true);

    for (unsigned j = 0; j < size; j++)
        if (indices[j] < old_size)
            disabled[indices[j]] = false;

    vector<pair<LinearExpression, DBM*> > cs;
    vector<pair<LinearExpression, DBM*> >::iterator ic,jc;
    vector<pair<LinearExpression, DBM*> >::const_iterator cc;

    //cout << "================================================================================" << endl;
    //cout << "initially" << endl;
    // Discrete cost
    const value dc = S.en[k]->get_cost(S.V, job.cts.statics, job.non_negative_costs);
    
    // Variable change: ti -> ti + tk
    for (cc = S.costs.begin(); cc != S.costs.end(); cc++)
    {
        // Compute the new coefficient of k
        // after variable change plus local cost increment
        vector<cvalue> C(old_size);
        cc->first.coefficients(old_size, C.data());
        cvalue ck = c - C[k+1];
        for (unsigned m = 0; m < old_size; m++)
        {
            ck += C[m];
        }

        LinearExpression L = cc->first + ck * Var(k + 1) + dc;
        //cout << *cc->second << endl;
        cs.push_back(pair<LinearExpression, DBM*>(L, new DBM(*cc->second)));
    }
    
    //cout << "------------------------------------------------------------------------------" << endl;
    vector<bool> eliminated(old_size, false);
    eliminated[0] = true;

    // First eliminate the fired transition
    cs = S.fm_eliminate(k+1, cs, k+1, eliminated);
    eliminated[k+1] = true;

    //cout << "fired transition eliminated" << endl;
    //for (ic = cs.begin(); ic != cs.end(); ic++)
    //    cout << *ic->second << endl;
    //cout << "------------------------------------------------------------------------------" << endl;
 
    for (unsigned m = 1; m < old_size; m++)
    {
        // Fourier-Motzkin to eliminate each disabled transition
        // from the cost
        if (m != k + 1 && disabled[m])
        {
            //cout << "disable m" << endl;
            cs = S.fm_eliminate(m, cs, k+1, eliminated);
            eliminated[m] = true;
        } 
    }

    //cout << "disabled transitions eliminated" << endl;
    
    // Compute the reverse map of indices
    vector<unsigned> rindices(old_size, size);

    for (unsigned i = 0; i < size; i++)
        if (indices[i] < old_size)
            rindices[indices[i]] = i;

    for (ic = cs.begin(); ic != cs.end(); ic++)
    {
        // Remap the linear expression
        ic->first.remap(size, rindices.data());

        //cout << "remap" << endl << *ic->second << endl;
        // Finish the computation of the next DBM
        DBM* ND = new DBM(size);
        (*ND)(0, 0) = time_bound::zero;
        for (unsigned i = 1; i < size; i++)
        {
            (*ND)(i, i) = time_bound::zero;
            const unsigned si = indices[i];
            if (si != old_size)
            {
                (*ND)(i, 0) = (*ic->second)(si, 0);
                (*ND)(0, i) = (*ic->second)(0, si);
            } else {
                const Transition& ti = *en[i-1];
                (*ND)(i, 0) = ti.timing->dbm_upper_bound(V, job.cts.statics);
                (*ND)(0, i) = ti.timing->dbm_lower_bound(V, job.cts.statics);
            }
        }


        for (unsigned i = 1; i < size; i++)
        {
            const unsigned si = indices[i];
            for (unsigned j = 1; j < i; j++)
            {
                const unsigned sj = indices[j];
                if (si != old_size && sj != old_size)
                {
                    (*ND)(i, j) = (*ic->second)(si, sj);
                    (*ND)(j, i) = (*ic->second)(sj, si);
                } else {
                    (*ND)(i, j) = (*ND)(i, 0) + (*ND)(0, j);
                    (*ND)(j, i) = (*ND)(j, 0) + (*ND)(0, i);
                }
            }
        }

        delete ic->second;
        ic->second = ND;
    }

    //cout << "done remap " << endl;

    set<pair<LinearExpression, DBM*>, ltpledbm > setcs;
    set<pair<LinearExpression, DBM*>, ltpledbm >::iterator kc;
    for (ic = cs.begin(); ic != cs.end(); ic++)
        setcs.insert(*ic);

    for (kc = setcs.begin(); kc != setcs.end(); kc++)
    {
        bool add = true;

        ic = costs.begin(); 
        while (ic != costs.end())
        {
            const relation_type r = ic->second->relation(*kc->second);
            // 0 <= min(L2 - L1) => forall x, L1(x) <= L2(x)
            if (r == LESS) 
            {
                if (ic->second->min(ic->first - kc->first) >= 0)
                    ic = costs.erase(ic);
                else
                    ic++;
            } else {
                if ((r == EQUAL || r == GREATER) && kc->second->min(kc->first - ic->first) >= 0)
                    add = false;

                ic++;
            } 
        }

        if (add)
        {
            costs.push_back(*kc);
        }
    }

    cmin = Avalue::infinity;
    for (ic = costs.begin(); ic != costs.end(); ic++)
    {
        cmin = min(cmin, ic->second->min(ic->first));
    }

    //cout << "done computing new cost" << endl;
    //Log.stop(" ----> cvsclass_sp");

}

bool CVSClassSp::set_firing_date(const unsigned i, const LExpression* e, const cvalue q = 1)
{
    bool r = VSClass::set_firing_date(i, e, q);

    if (e != nullptr)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        const time_bound u(v);
        const time_bound l(-v);

        vector<pair<LinearExpression, DBM*> >::iterator ic = costs.begin();
        while (ic != costs.end())
        {
            ic->second->constrain(i + 1, 0, u);
            ic->second->constrain(0, i + 1, l);
            if (ic->second->is_empty())
            {
                ic = costs.erase(ic);
            } else {
                ic++;
            }
        }
    }

    return r;
}

CVSClassSp::CVSClassSp(const CVSClassSp& S, const Instruction& I): VSClass(S,I), cmin(S.cmin)
{
    copy_costs(S);
}

Avalue CVSClassSp::min_cost() const
{
    return cmin;
}


bool CVSClassSp::contains(const PWNode* s) const
{
    const CVSClassSp* r = static_cast<const CVSClassSp*>(s);
    const LinearExpression L = r->costs[0].first - costs[0].first;
    const DBM* smalldbm = r->costs[0].second;
    return VSClass::contains(s) && smalldbm->min(L) >= 0;
}


std::string CVSClassSp::to_string() const
{

    stringstream domain;
    domain << VSClass::to_string() << endl;
    
    vector<string> labels;
    labels.push_back("0");
    for (unsigned k = 0; k < NE; k++)
    {
        labels.push_back(en[k]->label);
    }
    
    vector<pair<LinearExpression, DBM*> >::const_iterator i;
    for (i = costs.begin(); i != costs.end(); i++)
    {
        //domain << "----------------------" << endl;
        domain << " c >= " << (i->first).to_string_labels(labels) << endl;
        //domain << *i->second << endl;
    }

    domain << endl;
    

    cvalue c = (job.cts.cost.is_null()? 0: job.cts.cost.evaluate(V, job.cts.statics).to_int());

    domain << "local cost = " << c << endl;
    domain << "mincost = "; 

    const Avalue minc = min_cost();

    domain << minc;

    return domain.str();
}

PWNode* CVSClassSp::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new CVSClassSp(*this);
    } else {
        return new CVSClassSp(*this,*I);
    }
}

CVSClassSp::~CVSClassSp()
{
    vector<pair<LinearExpression, DBM*> >::const_iterator i;
    for (i = costs.begin(); i != costs.end(); i++)
    {
        if (i->second != D)
        {
            delete i->second;
        }
    }
}
// -----------------------------------------------------------------------------
//                                  Storage
// -----------------------------------------------------------------------------

bool CVSClassRIncStorage::contains(const PWNode* s) const
{
    const CVSClassSp* r = static_cast<const CVSClassSp*>(s);
    const LinearExpression L = r->costs[0].first - cost;
    const DBM* smalldbm = r->costs[0].second;
    return VSClassRIncStorage::contains(s) && smalldbm->min(L) >= 0;
}

bool CVSClassRIncStorage::is_contained_in(const PWNode* s) const
{
    const CVSClassSp* r = static_cast<const CVSClassSp*>(s);
    const LinearExpression L = cost - r->costs[0].first;
    const DBM* smalldbm = D;
    return VSClassRIncStorage::is_contained_in(s) && smalldbm->min(L) >= 0;
}

CVSClassRIncStorage::CVSClassRIncStorage(const CVSClassSp* s): VSClassRIncStorage(s), cost(s->costs[0].first)
{
}

CVSClassRIncStorage::~CVSClassRIncStorage()
{
}

// .............................................................................

EqStorage* CVSClassSp::eq_storage() const
{
    cerr << error_tag(color_output) << "Equality convergence not available with costs" << endl;
    exit(1);
}

RIncStorage* CVSClassSp::rinc_storage() const
{
    return new CVSClassRIncStorage(this);
}

MergeStorage* CVSClassSp::merge_storage() const
{
    cerr << error_tag(color_output) << "Merge convergence not available with costs" << endl;
    exit(1);
}



// -----------------------------------------------------------------------------
//                                  Iterator
// -----------------------------------------------------------------------------

PWNiterator* CVSClassSp::iterator()
{
    return new CVSCiterator(this);
}

CVSCiterator::CVSCiterator(PWNode* s): VSSiterator(s), succ(NULL), subindex(0)
{
}

PWNode* CVSCiterator::next()
{
    CVSClassSp * r;  

    if (succ == NULL)
    {
        // We are not currently enumerating the cost splitted DBMs of a succ
        // Get the next successor by the next transition
        succ = static_cast<CVSClassSp*>(VSSiterator::next());
        if (succ != NULL)
        {
            base->allocated_succs--;
        }
    }

    if (succ == NULL)
    {
        // None other firable
        r = NULL;
    } else {
        // Copy the successor
        r = new CVSClassSp(*succ);
        base->allocated_succs++;

        // And replace its DBM and cost with the good one
        vector<pair<LinearExpression, DBM*> >::const_iterator ic;
        for (ic = r->costs.begin(); ic != r->costs.end(); ic++)
        {
            if (ic->second != r->D)
            {
                delete ic->second;
            }
        }
        delete r->D;
        r->D = new DBM(*succ->costs[subindex].second);

        r->costs.clear();
        r->costs.push_back(pair<LinearExpression, DBM*>(succ->costs[subindex].first, r->D));
        
        // Prepare for the next one
        subindex++;
        if (subindex == succ->costs.size())
        {
            delete succ;
            succ = NULL;
            subindex = 0;
        }
    }

    return r;
}


