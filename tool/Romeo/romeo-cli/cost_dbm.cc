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

#include <memory>
#include <iostream>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>

#include <cost_dbm.hh>
#include <linear_expression.hh>
#include <color_output.hh>

using namespace romeo;
using namespace std;

namespace
{
    // A time_bound carries the strictness bit of a DBM constraint.  Cost
    // constants are ordinary numbers: inheriting that bit would turn a
    // geometric open boundary into a spurious cost epsilon.
    time_bound cost_scalar(const time_bound& b)
    {
        return b.bounded() ? b.weakify() : b;
    }

    time_bound cost_product(const time_bound& b, const cvalue r)
    {
        return cost_scalar(b) * r;
    }

    cvalue checked_cost_coefficient(const bextvalue v, const char* operation)
    {
        if (v < static_cast<bextvalue>(numeric_limits<cvalue>::min())
                || v > static_cast<bextvalue>(numeric_limits<cvalue>::max()))
        {
            cerr << error_tag(color_output) << "cost coefficient overflow while "
                 << operation << endl;
            exit(1);
        }

        return static_cast<cvalue>(v);
    }
}


CostDBM::CostDBM(const unsigned n): DBM(n), rates(new cvalue[n]()), coffset(time_bound::zero), outdated_cexpr(false), outdated_minc(false), minc(0), outdated_maxc(false), maxc(0)
{
}

CostDBM::CostDBM(const CostDBM& D): DBM(D), rates(new cvalue[D.size]()), coffset(D.coffset), outdated_cexpr(D.outdated_cexpr), c_expr(D.c_expr), outdated_minc(D.outdated_minc), minc(D.minc), outdated_maxc(D.outdated_maxc), maxc(D.maxc)
{
    for (unsigned i = 0; i < size; i++)
    {
        rates[i] = D.rates[i];
    }
}

CostDBM::CostDBM(const DBM& D): DBM(D), rates(new cvalue[D.dimension()]()), coffset(time_bound::zero), outdated_cexpr(false), outdated_minc(false), minc(0), outdated_maxc(false), maxc(0)
{
}

CostDBM& CostDBM::operator=(const CostDBM& D)
{
    if (this != &D)
    {
        unique_ptr<cvalue[]> new_rates(new cvalue[D.size]());
        for (unsigned i = 0; i < D.size; i++)
        {
            new_rates[i] = D.rates[i];
        }

        DBM::operator=(D);

        delete [] rates;
        rates = new_rates.release();

        coffset = D.coffset;

        outdated_cexpr = D.outdated_cexpr;
        c_expr = D.c_expr;

        outdated_minc = D.outdated_minc;
        minc = D.minc;

        outdated_maxc = D.outdated_maxc;
        maxc = D.maxc;
    }

    return *this;
}

time_bound CostDBM::cost_offset() const
{
    return coffset;
}

void CostDBM::restriction_assign(const DBM& g)
{
    if (!is_empty())
    {
        coffset = cost_scalar(coffset);
        for (unsigned i = 1; i < size; i++)
        {
            coffset = coffset + cost_product((*this)(0, i), rates[i]);
        }


        DBM::intersection_assign(g);

        if (!is_empty())
        {
            for (unsigned i = 1; i < size; i++)
            {
                coffset = coffset - cost_product((*this)(0, i), rates[i]);
            }
            coffset = cost_scalar(coffset);
        }

        outdated_cexpr = true;
        outdated_minc = true;
        outdated_maxc = true;
    }
}

void CostDBM::constrain(const unsigned i, const unsigned j, const time_bound& c)
{
    if (!is_empty())
    {
        coffset = cost_scalar(coffset);
        for (unsigned i = 1; i < size; i++)
        {
            coffset = coffset + cost_product((*this)(0, i), rates[i]);
        }

        DBM::constrain(i, j, c);

        if (!is_empty())
        {
            for (unsigned i = 1; i < size; i++)
            {
                coffset = coffset - cost_product((*this)(0, i), rates[i]);
            }
            coffset = cost_scalar(coffset);
        }

        outdated_cexpr = true;
        outdated_minc = true;
        outdated_maxc = true;
    }
}

CostDBM CostDBM::facet_past(const CostDBM& G, const unsigned i, const cvalue rsum, const cvalue cost_rate)
{
    CostDBM F(G);
    
    F.DBM::past();
    
    F.rates[i] = checked_cost_coefficient(
            static_cast<bextvalue>(cost_rate) - static_cast<bextvalue>(rsum)
            + static_cast<bextvalue>(G.rates[i]),
            "computing a weighted facet past");
    
    for (unsigned j = 1; j < size; j++)
    {   
        F.coffset = F.coffset
                  + (cost_scalar(G(0,j)) - cost_scalar(F(0,j))) * F.rates[j];
    }
    F.coffset = cost_scalar(F.coffset);

    F.outdated_cexpr = true;
    F.outdated_minc = true;
    F.outdated_maxc = true;

    return F;
}

CostDBMUnion CostDBM::past_min(const cvalue cost_rate)
{
    CostDBMUnion P(size);

    CostDBM Z(*this);
    Z.close();
    DBM exact_past(*this);
    exact_past.past();

    bextvalue wide_rsum = 0;
    for (unsigned i = 1; i < size; i++)
    {
        wide_rsum += static_cast<bextvalue>(rates[i]);
    }
    const cvalue rsum = checked_cost_coefficient(wide_rsum, "summing weighted-zone rates");

    if (cost_rate == rsum)
    {
        CostDBM Q(*this);
        Q.DBM::past();
        for (unsigned j = 1; j < size; j++)
        {
            Q.coffset = Q.coffset
                      - (cost_scalar(Q(0,j)) - cost_scalar((*this)(0,j))) * rates[j];
        }
        Q.coffset = cost_scalar(Q.coffset);
        Q.outdated_cexpr = true;
        Q.outdated_minc = true;
        Q.outdated_maxc = true;
        P.add(Q);
    } else {
        if (cost_rate < rsum)
        {
            P.add(*this);
            for (unsigned i = 1; i < size; i++)
            {
                time_bound f = -Z(0,i);
                CostDBM F(Z);
                F.constrain(i, 0, f);
                CostDBM G(facet_past(F, i, rsum, cost_rate));
                G.restriction_assign(exact_past);
                P.add_reduce_min(G);
            }
        } else {
            for (unsigned i = 1; i < size; i++)
            {
                if (Z(i,0) != time_bound::infinity)
                {
                    time_bound f = -Z(i,0);
                    CostDBM F(Z);
                    F.constrain(0, i, f);
                    CostDBM G(facet_past(F, i, rsum, cost_rate));
                    // Facets are built on the topological closure, but a time
                    // predecessor must still satisfy every strict rectangular
                    // and diagonal constraint of the exact past.
                    G.restriction_assign(exact_past);
                    P.add_reduce_min(G);
                }
            }
        }
    }

    //cout << "past of " << endl;
    //cout << this->to_string() << endl;
    //cout << "is " << endl;
    //cout << P.to_string() << endl;
    return P;
}

CostDBMUnion CostDBM::past_max(const cvalue cost_rate)
{
    //cout << "=========================================================================="<< endl;
    //cout << "past of " << endl;
    //cout << this->to_string() << endl<< endl;

    CostDBMUnion P(size);

    const CostDBM& D = *this;
    CostDBM Z(D);

    bextvalue wide_rsum = 0;
    for (unsigned i = 1; i < size; i++)
    {
        wide_rsum += static_cast<bextvalue>(rates[i]);
    }
    const cvalue rsum = checked_cost_coefficient(wide_rsum, "summing weighted-zone rates");

    //cout << "rsum = " << rsum << endl;
    //cout << "cr = " << cost_rate << endl << endl;

    if (cost_rate == rsum)
    {
        Z.DBM::past();
        for (unsigned j = 1; j < size; j++)
        {
            Z.coffset = Z.coffset
                      - (cost_scalar(Z(0,j)) - cost_scalar(D(0,j))) * rates[j];
        }
        Z.coffset = cost_scalar(Z.coffset);
        Z.outdated_cexpr = true;
        Z.outdated_minc = true;
        Z.outdated_maxc = true;
        P.add(Z);
    } else {
        DBM exact_past(D);
        exact_past.past();
        Z.close();

        // Compute redundant facets through the minimum constraint graph
        // Take care to make sure that redundant rectangular facets are
        // eliminated rather than diagonal. For that we keep coordinate 0 for
        // the end
        vector<pair<unsigned, list<unsigned> > > eqs;
        vector<bool> represented(size, false);
        unsigned new_size = 0;

        // First find classes of variables that are equal up to some constant
        // and designate a representative: the biggest one here
        for (unsigned ix = 0; ix < size; ix++)
        {
            const unsigned i = size - 1 - ix;
            if (!represented[i])
            {
                eqs.push_back(pair<unsigned, list<unsigned> >(i, list<unsigned>()));
                for (unsigned jx = ix+1; jx < size ; jx++)
                {
                    const unsigned j = size - 1 - jx;
                    if (D(i, j) + D(j, i) == time_bound::zero)
                    {
                        if (!represented[j])
                        {
                            eqs[new_size].second.push_back(j);
                            represented[j] = true;
                            //cout << j << " is represented by " << i << endl;
                        }
                    }
                }
                new_size++;
            }
        }

        vector<vector<bool> > R(size, vector<bool>(size, false));
        
        // Create the matrix of redundancy indicators
        for (unsigned i = 0; i < size; i++)
        {
            for (unsigned j = 0; j < size; j++)
            {
                if (i != j && (represented[i] || represented[j] || D(i, j) == time_bound::infinity))
                {
                    // Represented variables are redundant (but they will have
                    // to be linked to their representative below)
                    R[i][j] = true;
                }
            }
        }

        for (unsigned i = 0; i < new_size; i++)
        {
            const unsigned a = eqs[i].first;
            for (unsigned j = 0; j < new_size; j++)
            {
                const unsigned b = eqs[j].first;
                for (unsigned k = 0; k < new_size; k++)
                {
                    const unsigned c = eqs[k].first;
                    if (a != b && a != c && b != c && D(a, c) + D(c, b) <= D(a,b))
                    {
                        //cout << "D(" << a << ", " << b << ") = " << D(a,b) << " is redundant by " << c << endl;
                        R[a][b] = true; // mark as redundant
                    }
                }
            }
        }

        // Link represented variables to their representative through
        // non-redundant constraints
        for (unsigned k = 0; k < new_size; k++)
        {
            const unsigned i = eqs[k].first;
            
            for (auto j : eqs[k].second)
            {
                R[i][j] = false;
                R[j][i] = false;
            }
        }

        if (cost_rate > rsum)
        {
            // Zero delay is optimal for valuations already in Z.  Lower-facet
            // pasts only cover valuations before Z and cannot replace Z.
            P.add(D);
            for (unsigned i = 1; i < size; i++)
            {
                if (!R[0][i])
                {
                    time_bound f = -Z(0,i);
                    CostDBM F(Z);
                    F.constrain(i, 0, f);
                    CostDBM G(facet_past(F, i, rsum, cost_rate));
                    G.restriction_assign(exact_past);
                    //P.add_reduce_max(facet_past(F, i, rsum, cost_rate));
                    P.add(G);
                }
            }

        } else {
            for (unsigned i = 1; i < size; i++)
            {
                if (!R[i][0]) 
                {
                    time_bound f = -Z(i,0);
                    CostDBM F(Z);
                    F.constrain(0, i, f);
                    CostDBM G(facet_past(F, i, rsum, cost_rate));
                    G.restriction_assign(exact_past);
                    //P.add_reduce_max(G);
                    P.add(G);
                }
            }
        }
    }

    //cout << "--------------------------------------------------------------------------" << endl;
    //cout << "is " << endl;
    //cout << P.to_string() << endl;
    return P;
}



void CostDBM::remap(unsigned indices[], unsigned new_size)
{
    const unsigned old_size = size;

    DBM::remap(indices, new_size);
    cvalue* rs = new cvalue[new_size]();
    
    for (unsigned i = 0; i < new_size; i++)
    {
        if (indices[i] == old_size)
        {
            rs[i] = 0;
        } else {
            rs[i] = rates[indices[i]];
        }
    }

    delete [] rates;
    rates = rs;
    
    outdated_cexpr = true;
    outdated_minc = true;
    outdated_maxc = true;
}

void CostDBM::unreset(const unsigned i)
{
    constrain(i, 0, time_bound::zero);
    free_clock(i);
    rates[i] = 0;

    outdated_cexpr = true;
    outdated_minc = true;
    outdated_maxc = true;
}

void CostDBM::add_cost(const time_bound& c)
{
    coffset = cost_scalar(cost_scalar(coffset) + cost_scalar(c));
    
    outdated_cexpr = true;
    outdated_minc = true;
    outdated_maxc = true;
}

LinearExpression CostDBM::cost_expr() const
{
    if (outdated_cexpr)
    {
        c_expr = Avalue(cost_scalar(coffset));
        for (unsigned i = 1; i < size; i++)
        {
            c_expr = c_expr + Var(i) * rates[i]
                     + Avalue(cost_scalar((*this)(0,i))) * rates[i];
        }

        outdated_cexpr = false;
    }

    return c_expr;
}

bool CostDBM::subsumes_eq(const CostDBM& D) const
{
    bool result = false;
    const relation_type r = relation(D);

    //cout << "------------------------------------------------------" << endl;
    //cout << *this << endl;
    //cout << "subsumes_eq " <<endl;
    //cout << D << endl;

    if (r == GREATER || r == EQUAL)
    {
        LinearExpression Linf = D.cost_expr() - cost_expr();
        LinearExpression Lsup = cost_expr() - D.cost_expr();
        result = (D.DBM::min(Linf) >= time_bound::zero && D.DBM::min(Lsup) >= time_bound::zero);
    }

    //cout << "subsume_eq " << result << endl;
    //cout << "------------------------------------------------------" << endl;

    return result;
}

bool CostDBM::subsumes_min(const CostDBM& D) const
{
    bool result = false;
    const relation_type r = relation(D);

    //cout << "------------------------------------------------------" << endl;
    //cout << *this << endl;
    //cout << "subsumes_min " <<endl;
    //cout << D << endl;

    if (r == GREATER || r == EQUAL)
    {
        LinearExpression Linf = D.cost_expr() - cost_expr();
        //cout << "min of " << Linf << " is " <<  D.DBM::min(Linf) << endl;
        result = (D.DBM::min(Linf) >= time_bound::zero);
    }
    //cout << "subsume_min " << result << endl;
    //cout << "------------------------------------------------------" << endl;

    return result;
}

bool CostDBM::subsumes_max(const CostDBM& D) const
{
    bool result = false;
    const relation_type r = relation(D);

    //if ((r == GREATER || r == EQUAL) && (maxcost() >= D.maxcost()))
    if (r == GREATER || r == EQUAL)
    {
        LinearExpression Lsup = cost_expr() - D.cost_expr();
        result = (D.DBM::min(Lsup) >= time_bound::zero);
    }

    return result;
}

CostDBMUnion CostDBM::max(const CostDBM& D)
{
    CostDBMUnion P(size);
    DBMUnion C1(complement());
    DBMUnion C2(D.complement());
    
    CostDBMUnion R1(*this);
    R1.restriction_assign_max(C2);
    P.add_reduce_max(R1);

    CostDBMUnion R2(D);
    R2.restriction_assign_max(C1);
    P.add_reduce_max(R2);

    CostDBM I(*this);
    I.restriction_assign(D);
    if (!I.is_empty())
    {
        //I.coffset = ((coffset < D.coffset)? D.coffset: coffset);
        time_bound cD = D.coffset; 
        for (unsigned i = 1; i < size; i++)
        {
            cD = cD
               + (cost_scalar(D(0, i)) - cost_scalar(I(0, i))) * D.rates[i];
        }
        cD = cost_scalar(cD);

        if (cD > I.coffset)
        {
            I.coffset = cD;
        }


        for (unsigned i = 1; i < size; i++)
        {
            I.rates[i] = ((rates[i]<D.rates[i])? D.rates[i]: rates[i]);
        }

        I.outdated_cexpr = true;
        I.outdated_minc = true;
        I.outdated_maxc = true;

        P.add_reduce_max(I);
    }
    return P;
}

CostDBMUnion CostDBM::min(const CostDBM& D)
{
    CostDBMUnion P(size);
    DBMUnion C1(complement());
    DBMUnion C2(D.complement());
    
    CostDBMUnion R1(*this);
    R1.restriction_assign_min(C2);
    P.add_reduce_min(R1);

    CostDBMUnion R2(D);
    R2.restriction_assign_min(C1);
    P.add_reduce_min(R2);

    CostDBM I(*this);
    I.restriction_assign(D);
    if (!I.is_empty())
    {
        //I.coffset = ((coffset > D.coffset)? D.coffset: coffset);
        time_bound cD = D.coffset; 
        for (unsigned i = 1; i < size; i++)
        {
            cD = cD
               + (cost_scalar(D(0, i)) - cost_scalar(I(0, i))) * D.rates[i];
        }
        cD = cost_scalar(cD);

        if (cD < I.coffset)
        {
            I.coffset = cD;
        }

        for (unsigned i = 1; i < size; i++)
        {
            I.rates[i] = ((rates[i] > D.rates[i])? D.rates[i]: rates[i]);
        }

        I.outdated_cexpr = true;
        I.outdated_minc = true;
        I.outdated_maxc = true;

        P.add_reduce_min(I);
    }

    return P;
}

CostDBMUnion CostDBM::min2(const CostDBM& D)
{
    CostDBMUnion P(size);
    DBMUnion C1(complement());
    DBMUnion C2(D.complement());
    
    CostDBMUnion R1(*this);
    R1.restriction_assign_min(C2);
    P.add_reduce_min(R1);

    CostDBMUnion R2(D);
    R2.restriction_assign_min(C1);
    P.add_reduce_min(R2);

    CostDBM I(*this);
    I.restriction_assign(D);
    if (!I.is_empty())
    {
        time_bound cD = D.coffset; 
        const time_bound cI = I.coffset;
        for (unsigned i = 1; i < size; i++)
        {
            cD = cD
               + (cost_scalar(D(0, i)) - cost_scalar(I(0, i))) * D.rates[i];
        }
        cD = cost_scalar(cD);

        if (cD < I.coffset)
        {
            I.coffset = cD;
        }

        for (unsigned i = 1; i < size; i++)
        {
            if (I(i,0) == time_bound::infinity || I(i,0) == -I(0,i))
            {
                I.rates[i] = ((rates[i] > D.rates[i])? D.rates[i]: rates[i]);
            } else {
                const cvalue width = (I(i, 0) + I(0,i)).value();
                const cvalue r1 = cI.value() + width * rates[i];
                const cvalue r2 = cD.value() + width * D.rates[i];
                I.rates[i] = floor((0.0 + std::min(r1, r2) - I.coffset.value()) / width);
            }
        }

        I.outdated_cexpr = true;
        I.outdated_minc = true;
        I.outdated_maxc = true;

        P.add_reduce_min(I);
    }

    return P;
}

CostDBMUnion CostDBM::min(const CostDBMUnion& D)
{
    CostDBMUnion P(size);
    if (D.empty())
    {
        P.add(*this);
    } else {
        for (auto Z: D.disjuncts)
        {
            P.add_reduce_min(min2(*Z));
        }
    }

    return P;
}

time_bound CostDBM::origin_cost() const
{
    return coffset;
}

string CostDBM::to_string() const
{
    stringstream s;
    s << coffset;
    return DBM::to_string() + cost_expr().to_string() + " -- " + s.str(); 
}

Avalue CostDBM::mincost() const
{
    if (outdated_minc)
    {
        LinearExpression L = cost_expr();
        minc = this->DBM::min(L);
        outdated_minc = false;
    }

    return minc;
}

Avalue CostDBM::maxcost() const
{
    if (outdated_maxc)
    {
        LinearExpression L = cost_expr();
        maxc = this->DBM::max(L);
        outdated_maxc = false;
    }

    return maxc;
}

CostDBM::~CostDBM()
{
    delete [] rates;
}

// -----------------------------------------------------------------------------


CostDBMUnion::CostDBMUnion(const unsigned s): dim(s), outdated_minc(false), minc(Avalue::infinity), outdated_maxc(false), maxc(Avalue::minus_infinity)
{
}

CostDBMUnion::CostDBMUnion(const CostDBMUnion& A): dim(A.dim), outdated_minc(A.outdated_minc), minc(A.minc), outdated_maxc(A.outdated_maxc), maxc(A.maxc)
{
    for (auto D: A.disjuncts)
    {
        add(D);
    }
}

CostDBMUnion::CostDBMUnion(const CostDBM& B): dim(B.dimension()), outdated_minc(true), minc(Avalue::infinity), outdated_maxc(true), maxc(Avalue::minus_infinity)
{
    add(B);
}

CostDBMUnion::CostDBMUnion(const shared_ptr<CostDBM> B): dim(B->dimension()), outdated_minc(true), minc(Avalue::infinity), outdated_maxc(true), maxc(Avalue::minus_infinity)
{
    add(B);
}

CostDBMUnion& CostDBMUnion::operator=(const CostDBMUnion& A)
{
    if (this != &A)
    {
        clear();
        dim = A.dim;

        for (auto D: A.disjuncts)
        {
            disjuncts.push_back(make_shared<CostDBM>(*D));
        }

        outdated_minc = A.outdated_minc;
        outdated_maxc = A.outdated_maxc;
        minc = A.minc;
        maxc = A.maxc;
    }

    return *this;
}

void CostDBMUnion::invalidate_cost_cache()
{
    outdated_minc = true;
    outdated_maxc = true;
}

void CostDBMUnion::accept_dimension(const unsigned candidate)
{
    if (disjuncts.empty() && dim == 0)
    {
        dim = candidate;
    } else if (dim != candidate) {
        throw invalid_argument("cannot combine CostDBM objects with different dimensions");
    }
}

unsigned CostDBMUnion::dimension() const
{
    return dim;
}

void CostDBMUnion::detach(shared_ptr<CostDBM>& p)
{
    CostDBM* D = p.get();
    if (D != nullptr && p.use_count() > 1)
    {
        p = make_shared<CostDBM>(*D);
        //p = shared_ptr<CostDBM>(new CostDBM(*D));
    }
}

void CostDBMUnion::restriction_assign(const DBM& g)
{
    invalidate_cost_cache();
    auto k = disjuncts.begin();
    while (k != disjuncts.end())
    {
        detach(*k);
        (*k)->restriction_assign(g);
        if ((*k)->is_empty())
        {
            k->reset();
            k = disjuncts.erase(k);
        } else {
            k++;
        }
    }
}

void CostDBMUnion::restriction_assign(const DBMUnion& g)
{
    if (g.empty())
    {
        clear();
    } else {
        CostDBMUnion Q(*this);
        clear();
        for (DBM* D: g.disjuncts)
        {
            CostDBMUnion P(Q);
            P.restriction_assign(*D);
            add(P);
        }
    }
}

void CostDBMUnion::restriction_assign_eq(const DBMUnion& g)
{
    if (g.empty())
    {
        clear();
    } else {
        CostDBMUnion Q(*this);
        clear();
        for (DBM* D: g.disjuncts)
        {
            CostDBMUnion P(Q);
            P.restriction_assign(*D);
            add_reduce_eq(P);
        }
    }
}

void CostDBMUnion::restriction_assign_max(const DBMUnion& g)
{
    if (g.empty())
    {
        clear();
    } else {
        CostDBMUnion Q(*this);
        clear();
        for (DBM* D: g.disjuncts)
        {
            CostDBMUnion P(Q);
            P.restriction_assign(*D);
            add_reduce_max(P);
        }
    }
}

void CostDBMUnion::restriction_assign_min(const DBMUnion& g)
{
    if (g.empty())
    {
        clear();
    } else {
        CostDBMUnion Q(*this);
        clear();
        for (DBM* D: g.disjuncts)
        {
            CostDBMUnion P(Q);
            P.restriction_assign(*D);
            add_reduce_min(P);
        }
    }
}

void CostDBMUnion::clear()
{
    for (auto D: disjuncts)
    {
        D.reset();
    }
    disjuncts.clear();

    minc = Avalue::infinity;
    maxc = Avalue::minus_infinity;
    outdated_minc = false;
    outdated_maxc = false;
}

void CostDBMUnion::constrain(const unsigned i, const unsigned j, const time_bound& c)
{
    invalidate_cost_cache();
    auto k = disjuncts.begin();
    while (k != disjuncts.end())
    {
        detach(*k);
        (*k)->constrain(i,j,c);
        if ((*k)->is_empty())
        {
            k->reset();
            k = disjuncts.erase(k);
        } else {
            k++;
        }
    }
}

void CostDBMUnion::add(const CostDBM& D)
{
    add(make_shared<CostDBM>(D));
}

void CostDBMUnion::add(const shared_ptr<CostDBM> D)
{
    if (!D->is_empty())
    {
        accept_dimension(D->dimension());
        disjuncts.push_back(D);
        invalidate_cost_cache();
    }
}

void CostDBMUnion::add(const CostDBMUnion& D)
{
    for (auto Z: D.disjuncts)
    {
        add(Z);
    }
}

void CostDBMUnion::add_reduce_eq(const CostDBM& D)
{
    add_reduce_eq(make_shared<CostDBM>(D));
}

void CostDBMUnion::add_reduce_eq(const shared_ptr<CostDBM> D)
{
    if (!D->is_empty())
    {
        accept_dimension(D->dimension());
        auto k = disjuncts.begin();
        bool subsumed = false;
        while (k != disjuncts.end() && !subsumed)
        {
            if ((*k)->subsumes_eq(*D))
            {
                subsumed = true;
                k++;
            } else if (D->subsumes_eq(**k)) {
                invalidate_cost_cache();
                k->reset();
                k = disjuncts.erase(k);
            } else {
                k++;
            }
        }

        if (!subsumed)
        {
            add(D);
        }
    }
}

void CostDBMUnion::add_reduce_min(const CostDBM& D)
{
    add_reduce_min(make_shared<CostDBM>(D));
}

void CostDBMUnion::add_reduce_min(const shared_ptr<CostDBM> D)
{
    if (!D->is_empty())
    {
        accept_dimension(D->dimension());
        auto k = disjuncts.begin();
        bool subsumed = false;
        while (k != disjuncts.end() && !subsumed)
        {
            if ((*k)->subsumes_min(*D))
            {
                subsumed = true;
                k++;
            } else if (D->subsumes_min(**k)) {
                invalidate_cost_cache();
                k->reset();
                k = disjuncts.erase(k);
            } else {
                k++;
            }
        }

        if (!subsumed)
        {
            add(D);
        }
    }
}


void CostDBMUnion::add_reduce_max(const CostDBM& D)
{
    add_reduce_max(make_shared<CostDBM>(D));
}

void CostDBMUnion::add_reduce_max(const shared_ptr<CostDBM> D)
{
    if (!D->is_empty())
    {
        accept_dimension(D->dimension());
        auto k = disjuncts.begin();
        bool subsumed = false;
        while (k != disjuncts.end() && !subsumed)
        {
            if ((*k)->subsumes_max(*D))
            {
                subsumed = true;
                k++;
            } else if (D->subsumes_max(**k)) {
                invalidate_cost_cache();
                k->reset();
                k = disjuncts.erase(k);
            } else {
                k++;
            }
        }

        if (!subsumed)
        {
            add(D);
        }
    }
}

bool CostDBMUnion::add_reduce_max_delta(const CostDBM& D)
{
    return add_reduce_max_delta(make_shared<CostDBM>(D));
}

bool CostDBMUnion::add_reduce_max_delta(const shared_ptr<CostDBM> D)
{
    if (test_reduce_max_delta(D))
    {
        add(D);
        return true;
    }

    return false;
}

bool CostDBMUnion::test_reduce_max_delta(const shared_ptr<CostDBM> D)
{
    bool r = false;
    if (!D->is_empty())
    {
        accept_dimension(D->dimension());
        r = true;
        auto k = disjuncts.begin();
        while (k != disjuncts.end() && r)
        {
            if ((*k)->subsumes_max(*D))
            {
                r = false;
                k++;
            } else if (D->subsumes_max(**k)) {
                invalidate_cost_cache();
                k->reset();
                k = disjuncts.erase(k);
            } else {
                k++;
            }
        }
    }

    return r;
}

void CostDBMUnion::add_reduce_eq(const CostDBMUnion& D)
{
    for (auto Z: D.disjuncts)
    {
        add_reduce_eq(*Z);
    }
}

void CostDBMUnion::add_reduce_min(const CostDBMUnion& D)
{
    for (auto Z: D.disjuncts)
    {
        add_reduce_min(*Z);
    }
}

void CostDBMUnion::add_reduce_max(const CostDBMUnion& D)
{
    for (auto Z: D.disjuncts)
    {
        add_reduce_max(*Z);
    }
}

CostDBMUnion CostDBMUnion::add_reduce_max_delta(const CostDBMUnion& D)
{
    CostDBMUnion R;
    for (auto Z: D.disjuncts)
    {
        if (add_reduce_max_delta(Z))
        {
            R.add(Z);
        }
    }

    return R;
}

void CostDBMUnion::add_reduce_max_delta(CostDBMUnion& A, const CostDBMUnion& D)
{
    CostDBMUnion R;
    for (auto Z: D.disjuncts)
    {
        //if (A.test_reduce_max_delta(Z) && test_reduce_max_delta(Z))
        if (test_reduce_max_delta(Z))
        {
            A.add(Z);
        }
    }

    add(A);
}

CostDBMUnion CostDBMUnion::past_min(const cvalue cost_rate) const
{
    CostDBMUnion P(dim);

    for (auto D: disjuncts)
    {
        P.add_reduce_min(D->past_min(cost_rate));
    }

    return P;
}

CostDBMUnion CostDBMUnion::past_max(const cvalue cost_rate) const
{
    CostDBMUnion P(dim);

    for (auto D: disjuncts)
    {
        P.add(D->past_max(cost_rate));
        //P.add_reduce_max(D->past_max(cost_rate));
    }

    return P;
}

CostDBMUnion CostDBMUnion::reduce_max() const
{
    CostDBMUnion P(dim);

    for (auto D: disjuncts)
    {
        P.add_reduce_max(D);
    }

    return P;
}

void CostDBMUnion::remap(unsigned indices[], unsigned new_size)
{
    invalidate_cost_cache();
    dim = new_size;
    for (auto D = disjuncts.begin(); D != disjuncts.end(); D++)
    {
        detach(*D);
        (*D)->remap(indices, new_size);
    }
}

void CostDBMUnion::unreset(const unsigned i)
{
    invalidate_cost_cache();
    for (auto D = disjuncts.begin(); D != disjuncts.end(); D++)
    {
        detach(*D);
        (*D)->unreset(i);
    }
}

void CostDBMUnion::add_cost(const time_bound& c)
{
    invalidate_cost_cache();
    for (auto D = disjuncts.begin(); D != disjuncts.end(); D++)
    {
        detach(*D);
        (*D)->add_cost(c);
    }
}

bool CostDBMUnion::empty() const
{
    return disjuncts.empty();
}

bool CostDBMUnion::subsumes_eq(const CostDBM& D) const
{
    bool subsumed = false;
    auto k = disjuncts.begin();

    while (k != disjuncts.end() && !subsumed)
    {
        subsumed = (*k)->subsumes_eq(D);
        k++;
    }

    return subsumed;
}

bool CostDBMUnion::subsumes_eq(const CostDBMUnion& D) const
{
    bool subsumed = true;
    auto k = D.disjuncts.begin();

    while (k != D.disjuncts.end() && subsumed)
    {
        subsumed = subsumes_eq(**k);
        k++;
    }

    return subsumed;
}

bool CostDBMUnion::subsumes_min(const CostDBM& D) const
{
    bool subsumed = false;
    auto k = disjuncts.begin();

    while (k != disjuncts.end() && !subsumed)
    {
        subsumed = (*k)->subsumes_min(D);
        k++;
    }

    return subsumed;
}

bool CostDBMUnion::subsumes_min(const CostDBMUnion& D) const
{
    bool subsumed = true;
    auto k = D.disjuncts.begin();

    while (k != D.disjuncts.end() && subsumed)
    {
        subsumed = subsumes_min(**k);
        k++;
    }

    return subsumed;
}

bool CostDBMUnion::subsumes_max(const CostDBM& D) const
{
    bool subsumed = false;
    auto k = disjuncts.begin();

    while (k != disjuncts.end() && !subsumed)
    {
        subsumed = (*k)->subsumes_max(D);
        k++;
    }

    return subsumed;
}

bool CostDBMUnion::subsumes_max(const CostDBMUnion& D) const
{
    bool subsumed = true;
    auto k = D.disjuncts.begin();

    while (k != D.disjuncts.end() && subsumed)
    {
        subsumed = subsumes_max(**k);
        k++;
    }

    return subsumed;
}

CostDBMUnion CostDBMUnion::max(const CostDBM& D) const
{
    CostDBMUnion P;

    if (disjuncts.empty())
    {
        P.add(D);
    } else {
        for (auto Z: disjuncts)
        {
            P.add_reduce_max(Z->max(D));
        }
    }

    return P;
}

CostDBMUnion CostDBMUnion::max(const CostDBMUnion& D) const
{
    CostDBMUnion P;

    if (D.disjuncts.empty())
    {
        return *this;
    } else {
        for (auto Z: D.disjuncts)
        {
            P.add_reduce_max(max(*Z));
        }
    }

    return P;
}

CostDBMUnion CostDBMUnion::min(const CostDBM& D) const
{
    CostDBMUnion P;

    if (disjuncts.empty())
    {
        P.add(D);
    } else {
        for (auto Z: disjuncts)
        {
            P.add_reduce_min(Z->min2(D));
        }
    }

    return P;
}

CostDBMUnion CostDBMUnion::min(const CostDBMUnion& D) const
{
    CostDBMUnion P;

    if (disjuncts.empty())
    {
        P.add(D);
    } else {
        for (auto Z: disjuncts)
        {
            P.add_reduce_min(Z->min(D));
        }
    }

    return P;
}


CostDBMUnion CostDBMUnion::maxmapmin(const CostDBM& D) const
{
    CostDBMUnion P;

    if (disjuncts.empty())
    {
        P.add(D);
    } else {
        for (auto Z: disjuncts)
        {
            P.add_reduce_max(Z->min(D));
        }
    }

    return P;
}

CostDBMUnion CostDBMUnion::maxmapmin(const CostDBMUnion& D) const
{
    CostDBMUnion P;

    if (disjuncts.empty())
    {
        P.add(D);
    } else {
        for (auto Z: disjuncts)
        {
            P.add_reduce_max(Z->min(D));
        }
    }

    return P;
}



CostDBMUnion CostDBMUnion::predt_min(const DBMUnion& Bad, const cvalue cost_rate) const
{
    CostDBMUnion Gp(*this);
    CostDBMUnion G(*this);
    Gp = Gp.past_min(cost_rate);
    //cout << "Gp " << Gp.to_string() << endl;

    DBMUnion PastBad(Bad);
    PastBad.past();
    //cout << "PB " << PastBad.to_string() << endl;

    DBMUnion NegBad(Bad.complement());
    //cout << "NB " << NegBad.to_string() << endl;

    DBMUnion NegPastBad(PastBad.complement());
    //cout << "NPB " << NegPastBad.to_string() << endl;
    
    // past(G) \ past(B)
    Gp.restriction_assign_min(NegPastBad);

    // G inter past(B)
    G.restriction_assign_min(PastBad);
    
    // (G inter past(B)) \ B
    G.restriction_assign_min(NegBad);

    // past of all this
    G = G.past_min(cost_rate);
    //cout << "pGipBmB " << G.to_string() << endl;

    Gp.add_reduce_min(G);

    return Gp;

}

CostDBMUnion CostDBMUnion::predt_max(const DBMUnion& Bad, const cvalue cost_rate) const
{
    CostDBMUnion Gp(*this);
    CostDBMUnion G(*this);
    Gp = Gp.past_max(cost_rate);
    //cout << "Gp " << Gp.to_string() << endl;

    DBMUnion PastBad(Bad);
    PastBad.past();
    //cout << "PB " << PastBad.to_string() << endl;

    DBMUnion NegBad(Bad.complement());
    //cout << "NB " << NegBad.to_string() << endl;

    DBMUnion NegPastBad(PastBad.complement());
    //cout << "NPB " << NegPastBad.to_string() << endl;
    
    // past(G) \ past(B)
    Gp.restriction_assign_max(NegPastBad);

    // G inter past(B)
    G.restriction_assign_max(PastBad);
    
    // (G inter past(B)) \ B
    G.restriction_assign_max(NegBad);

    // past of all this
    G = G.past_max(cost_rate);
    //cout << "pGipBmB " << G.to_string() << endl;

    Gp.add_reduce_max(G);

    return Gp;

}


time_bound CostDBMUnion::origin_cost() const
{
    time_bound c(time_bound::minus_infinity);
    for (auto Z: disjuncts)
    {
        if (Z->contains_origin())
        {
            c = std::max(c, Z->cost_offset());
        }
    }

    return c;
}


DBMUnion CostDBMUnion::uncost() const
{
    DBMUnion P(dim);

    for (auto D: disjuncts)
    {
        P.add(*D);
    }

    return P;
}

Avalue CostDBMUnion::mincost() const
{
    if (outdated_minc)
    {
        minc = Avalue::infinity;
        for (auto D: disjuncts)
        {
            minc = std::min(minc, D->mincost());
        }
        outdated_minc = false;
    }

    return minc;
}

string CostDBMUnion::to_string() const
{
    string s;
    if (disjuncts.empty())
    {
        s = "false";
    } else {
        for (auto D: disjuncts)
        {
            s += D->to_string() + "\n\n";
        }
    }

    return s;
}

unsigned CostDBMUnion::size() const
{
    return disjuncts.size();
}

CostDBMUnion::~CostDBMUnion()
{
    for (auto D: disjuncts)
    {
        D.reset();
    }
}
