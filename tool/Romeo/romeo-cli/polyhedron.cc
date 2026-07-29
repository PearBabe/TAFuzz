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

#include "avalue.hh"
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <queue>

#include <ppl.hh>
#include <gmpxx.h>
#include <gmp.h>

#include <polyhedron.hh>
#include <pdbm.hh>
#include <dbm.hh>
#include <linear_expression.hh>
#include <size_digest.hh>
#include <color_output.hh>

#include <logger.hh> 
extern romeo::Logger Log;

using namespace std;
using namespace romeo;
using namespace Parma_Polyhedra_Library::IO_Operators;

PPL_Linear_Expression romeo::ppl_linear_expression(const PPL_Constraint& c)
{
    PPL_Linear_Expression L;
    for (PPL_dimension_type i = 0; i<c.space_dimension(); i++)
        L += c.coefficient(PPL_Variable(i))*PPL_Variable(i);
    L += c.inhomogeneous_term();
 
    return L;
}

romeo::Polyhedron::Polyhedron(const LinearExpression& V, const cstr_rel r, const unsigned N)
{
    D = new PPL_Polyhedron(N,PPL_UNIVERSE);
    this->constrain(V, r);
}

romeo::Polyhedron::Polyhedron(const unsigned d, const bool universe)
{
    if (universe)
    {
        D = new PPL_Polyhedron(d, PPL_UNIVERSE);
    } else {
        D = new PPL_Polyhedron(d, PPL_EMPTY);
    }
}

romeo::Polyhedron::Polyhedron(const Polyhedron& Q)
{
    D = new PPL_Polyhedron(*Q.D);
}

// Transitional for refactoring
romeo::Polyhedron::Polyhedron(const PPL_Polyhedron& P)
{
    D = new PPL_Polyhedron(P); 
}

romeo::Polyhedron::Polyhedron(const PInterval& I): Polyhedron(1, true) // conversion to Polyhedron
{
    if (I.right != Avalue::infinity)
    {
        auto dr = I.right.denominator();
        auto vr = I.right.value();
        auto sr = I.right.is_strict()? CSTR_LSTRICT: CSTR_LWEAK;
        constrain(dr * Var(0) - vr, sr);
    } 

    if (I.left != Avalue::minus_infinity)
    {
        auto dl = I.left.denominator();
        auto vl = I.left.value();
        auto sl = I.left.is_strict()? CSTR_GSTRICT: CSTR_GWEAK;
        constrain(dl * Var(0) - vl, sl);
    } 
}



unsigned romeo::Polyhedron::dimension() const
{
    return D->space_dimension();
}

void romeo::Polyhedron::negation_assign()
{
    unsigned N = D->space_dimension();
	  PPL_Polyhedron* r = new PPL_Polyhedron(N,UNIVERSE);

	  for(const auto& it: *D) 
    {
		    // Transform each disjunct polyhedron into a disjunction of the negation of 
        // its constraint
		    PPL_Constraint_System sys = it.pointset().minimized_constraints();
        PPL_Polyhedron neg(N,EMPTY);
		    for (const auto& ci: sys)
		    {
		        PPL_Linear_Expression e = ppl_linear_expression(ci);
			      if (ci.is_equality()) {
                neg.add_disjunct(PPL_Convex_Polyhedron(PPL_Constraint_System(e < 0)));
                neg.add_disjunct(PPL_Convex_Polyhedron(PPL_Constraint_System(e > 0)));
			      } else if (ci.is_strict_inequality()) {
                // Use the fact that constraints for PPL are of the form e > 0 or e >= 0
                neg.add_disjunct(PPL_Convex_Polyhedron(PPL_Constraint_System(e <= 0)));
            } else {
                neg.add_disjunct(PPL_Convex_Polyhedron(PPL_Constraint_System(e < 0)));
            }
		    }
		    // add in conjunction this disj to the result
        r->intersection_assign(neg);
	  }

    delete D;
    D = r;
    D->omega_reduce();
}

void romeo::Polyhedron::intersection_assign(const romeo::Polyhedron& Q)
{
    D->intersection_assign(*Q.D);
    D->omega_reduce();
}

void romeo::Polyhedron::add(const romeo::Polyhedron& Q)
{
    for (const auto& i: *Q.D)
    {
        this->D->add_disjunct(i.pointset());
    }
}

void romeo::Polyhedron::add_reduce(const romeo::Polyhedron& Q)
{
    PPL_Polyhedron* B = new PPL_Polyhedron(*Q.D); 

    list<PPL_Polyhedron*> waiting;

    waiting.push_back(B);
    while (!waiting.empty())
    {
        PPL_Polyhedron* current_ps = waiting.front();
        waiting.pop_front();
        for (const auto& cit: *current_ps)
        {
            PPL_Polyhedron::iterator it = D->begin();
            bool added = false;
            bool stop = false;
            while (it != D->end() && !stop)
            {
                PPL_Polyhedron* C;
                C = new PPL_Polyhedron(it->pointset().space_dimension(),EMPTY);
                C->add_disjunct(cit.pointset());
                C->add_disjunct(it->pointset());
                C->pairwise_reduce();
                if (C->size() == 1)
                {
                    added = true;
                    if (it->pointset().contains(cit.pointset())) {
                        stop = true;
                    } else {
                        waiting.push_back(C);
                        it = D->drop_disjunct(it);
                    }
                } else {
                    delete C;
                    it++;
                }
            }
            if (!added)
            {
                D->add_disjunct(cit.pointset());
            } 
        }
    }
}

void romeo::Polyhedron::project_on(const unsigned p, bool& ls, bool& lb, cvalue& lv, bool& rs, bool& rb, cvalue& rv, cvalue& ld, cvalue& rd)
{
    lv = 1;
    rv = 0;
    lb = false;
    rb = false;
    ls = false;
    rs = false;

    PPL_Variables_Set toRemove;
    for (unsigned k=0; k<this->D->space_dimension(); k++)
        if (k != p)
            toRemove.insert(Variable(k));

    D->remove_space_dimensions(toRemove);
    
    if (!D->empty())
    {
        PPL_Constraint_System C = D->begin()->pointset().minimized_constraints();

        const PPL_Variable v(0);
        for (const auto& i: C)
        {
            const POLY_COEFFICIENT_TYPE cv = i.coefficient(v);
            const int sign = (cv >= 0 ? 1 : -1);
#ifdef POLY_COEFFICIENT_MPZ
            const cvalue d = mpz_get_si(cv.get_mpz_t());
#else
            const cvalue d = cv;
#endif
            const POLY_COEFFICIENT_TYPE di = i.inhomogeneous_term();
#ifdef POLY_COEFFICIENT_MPZ
            const cvalue h = -mpz_get_si(di.get_mpz_t());
#else
            const cvalue h = -di;
#endif

            if (i.is_equality())
            {
                lb = true;
                rb = true;
                lv = h;
                rv = h;
                ld = d;
                rd = d;
            } else {
                if (sign > 0)
                {
                    lb = true;
                    lv = h;
                    ld = d;
                    if (i.is_strict_inequality())
                        ls = true;
                } else {
                    rb = true;
                    rv = -h;
                    rd = -d;
                    if (i.is_strict_inequality())
                        rs = true;
                }
            }
        }
    }
}

bool romeo::Polyhedron::empty() const
{
    return D->is_empty();
}

bool romeo::Polyhedron::universe() const
{
    return D->is_universe();
}

string romeo::Polyhedron::coeff_to_string(POLY_COEFFICIENT_TYPE x, bool& first_print)
{
    stringstream domain;
    if (x != 0)
    {
        if (first_print)
        {
            first_print = false;
            if (x < 0)
                domain << "-";
        } else {
            if (x < 0) 
                domain << " - ";
            else 
                domain << " + ";
        }
        
        if (abs(x) != 1)
            domain << abs(x) << "*";
    }
    
    return domain.str();
}

string romeo::Polyhedron::constraint_to_string(const PPL_Constraint& c, const vector<string>& labels, const unsigned NV, const unsigned NP)
{
    stringstream domain;
    bool first_print = true;
    unsigned k = 0;
    unsigned pluses = 0;
    unsigned minuses = 0;
    POLY_COEFFICIENT_TYPE x, sign;

    for (k = NP; k < NP+NV; k++)
    {
        if (c.coefficient(PPL_Variable(k)) < 0)
            minuses++; 
        else if (c.coefficient(PPL_Variable(k)) > 0)
            pluses++; 
    }   

    sign = (minuses > pluses ? -1 : 1);
    
    for (k = NP; k < NP+NV; k++)
    {       
        if ((x = c.coefficient(PPL_Variable(k))) != 0)
        {           
            domain << coeff_to_string(x*sign,first_print);
            domain << labels[k];
        }
    }

    bool no_var = (minuses+pluses == 0);
    if (no_var)
    {
        for (k = 0; k < NP; k++)
        {
            if (c.coefficient(PPL_Variable(k)) < 0)
                minuses++; 
            else if (c.coefficient(PPL_Variable(k)) > 0)
                pluses++; 
        }   

        sign = (minuses > pluses ? -1 : 1);
        for (k = 0; k < NP; k++)
        {       
            if ((x = c.coefficient(PPL_Variable(k))) != 0)
            {           
                domain << coeff_to_string(x*sign,first_print);
                domain << labels[k];
            }
        }
    }

    if (c.is_equality())
        domain << " = ";
    else
    {
        if (sign == 1)
            domain << " >";
        else
            domain << " <";

        if (c.is_nonstrict_inequality())
            domain << "=";

        domain << " ";
    }
    
    first_print = true;
    if (!no_var)
    {
        for (k = 0; k < NP; k++)
        {       
            if ((x = c.coefficient(PPL_Variable(k))) != 0)
            {           
                domain << coeff_to_string(-x*sign,first_print);
                domain << labels[k];
            }
        }
    }

    if (c.inhomogeneous_term() != 0 || first_print)
    {
        x = sign * -c.inhomogeneous_term();
        x = (x>=0 ? 1 : -1); 
        domain << coeff_to_string(x,first_print);
        domain << abs(c.inhomogeneous_term());
    }
            
    return domain.str();
}

unsigned romeo::Polyhedron::nb_vars(const PPL_Constraint& c, const unsigned NV, const unsigned NP)
{
    unsigned r = 0;

    for (unsigned k=NP; k<NP+NV; k++)
        if (c.coefficient(PPL_Variable(k)) != 0)
            r++;

    return r;
}

unsigned romeo::Polyhedron::first_var(const PPL_Constraint& c, const unsigned NV, const unsigned NP)
{
    unsigned k;
    for (k=NP; k<NP+NV && c.coefficient(PPL_Variable(k)) == 0; k++);

    return k;
}

string romeo::Polyhedron::to_string() const
{
    // We do not have labels, add some arbitrary ones
    // Warning! Quick hack limited to around 26 variables
    vector<string> labels;
    for (unsigned k=0; k<D->space_dimension(); k++)
    {
        string s = "A";
        s[0] += k;
        labels.push_back(s);
    }

    return to_string_labels(labels,0);
}

string romeo::Polyhedron::to_string_labels(const vector<string>& labels, const unsigned NP) const
{
    const unsigned N = D->space_dimension();
    const unsigned NV = N - NP;

    stringstream domain;

    bool print_or = false;
    if (D->is_empty())
        domain << "false";
    else { 
        if (D->is_universe())
           domain << "true"; 
        else {
            for (const auto& it: *D)
            {
                if (print_or)
                    domain << endl << "or" << endl;
                else
                    print_or = true;

                // First print the rectangular constraints for variables (non parameters)
                bool lineskip = false;
                for (unsigned k=NP; k<N; k++)
                {
                    if (lineskip)
                    {
                        domain << endl;
                    } else {
                        lineskip = true;
                    } 

                    bool ls,lb,rs,rb;
                    cvalue lv, rv, ld, rd;

                    Polyhedron(PPL_Polyhedron(it.pointset())).project_on(k, ls, lb, lv, rs, rb, rv, ld,rd);
                    domain << labels[k] << " in ";
                    if (lb)
                    {
                        if (ls)
                            domain << "]";
                        else
                            domain << "[";

                        domain << lv;
                        if (ld != 1)
                            domain << "/" << ld;
                    } else {
                        domain << "]-inf";
                    }

                    domain << ", ";

                    if (rb)
                    {
                        domain << rv;
                        if (rd != 1)
                            domain << "/" << rd;

                        if (rs)
                            domain << "[";
                        else
                            domain << "]";
                    } else {
                        domain << "inf[";
                    }

                }

                PPL_Constraint_System C = it.pointset().minimized_constraints();

                list<PPL_Constraint> sorted_vars;
                list<PPL_Constraint> sorted_pars;
                list<PPL_Constraint>::iterator j;

                for (const auto& i: C)
                {
                    const unsigned n = nb_vars(i, NV, NP);
                    if (n > 0)
                    {
                        // Ignore the rectangular constraints already printed above
                        if (n>1 || nb_vars(i, NP, 0) > 0)
                        {
                            const unsigned idx = first_var(i, NV, NP);
                            for (j = sorted_vars.begin(); j != sorted_vars.end() 
                                && n >= nb_vars(*j, NV, NP) 
                                && idx > first_var(*j, NV, NP) 
                                ; j++);
                            sorted_vars.insert(j, i);
                        }
                    } else {
                        const unsigned idx = first_var(i, NP, 0);
                        for (j = sorted_pars.begin(); j != sorted_pars.end() 
                            && nb_vars(*j, NP, 0) >= nb_vars(*j, NP, 0) 
                            && idx > first_var(*j, NP, 0) 
                            ; j++);
                        sorted_pars.insert(j, i);
                    }
                    
                }

                for (const auto& j: sorted_vars)
                {
                    domain << endl << constraint_to_string(j, labels, NV, NP);
                }

                for (const auto& j: sorted_pars)
                {
                    domain << endl << constraint_to_string(j, labels, NV, NP);
                }
            }
        }
    }

    return domain.str();
}

void romeo::Polyhedron::remove_higher_dimensions(const unsigned n)
{
    D->remove_higher_space_dimensions(n);
}

void romeo::Polyhedron::unconstrain(const unsigned n)
{
    D->unconstrain(PPL_Variable(n));
}

void romeo::Polyhedron::add_dimensions(const unsigned n)
{
    D->add_space_dimensions_and_embed(n);
}

void romeo::Polyhedron::constrain(const LinearExpression& V, const cstr_rel r)
{
    if (V.const_term().is_inf() || V.const_term().is_minus_inf())
    {
        if ((V.const_term().is_inf() && r != CSTR_GWEAK && r != CSTR_GSTRICT) 
         || (V.const_term().is_minus_inf() && r != CSTR_LWEAK && r != CSTR_LSTRICT))
        {
            D->add_constraint(PPL_Linear_Expression(1) <= 0);
        }
    } else {
        PPL_Linear_Expression L = V.to_PPL();
        PPL_Constraint C;
        switch (r)
        {
            case CSTR_GWEAK: C = (L >= 0); break;
            case CSTR_GSTRICT: C = (L > 0); break;
            case CSTR_EQ: C = (L == 0); break;
            case CSTR_LWEAK: C = (L <= 0); break;
            case CSTR_LSTRICT: C = (L < 0); break;
        }
        D->add_constraint(C);
    }
}

void romeo::Polyhedron::affine_image(const Var& vi, const LinearExpression& expr, const cvalue sf)
{
    PPL_Linear_Expression L = expr.to_PPL();
    PPL_Variable v(vi.index);

    D->affine_image(v,L,sf);
}

void romeo::Polyhedron::remap(const unsigned indices[], const unsigned new_size)
{
    // Compute the mapping
    Mapper M(indices, D->space_dimension(), new_size);
	
    // Add new dimensions to fit the desired new size
    D->add_space_dimensions_and_embed(M.nnew);

    // Remap properly
    D->map_space_dimensions(M);
}

void romeo::Polyhedron::future_assign(const cvalue rates[])
{
    const unsigned N = D->space_dimension();
    PPL_Polyhedron Q(N, UNIVERSE);

    for (unsigned i=0; i<N; i++)
        Q.add_constraint(PPL_Variable(i)==rates[i]);
    
    this->D->time_elapse_assign(Q);
}

romeo::Polyhedron romeo::Polyhedron::predt(const cvalue rates[], const romeo::Polyhedron& Bad)
{
    const unsigned dim = this->dimension();
    // Compute negative rates
    cvalue neg_rates[dim];
    for (unsigned i = 0; i < dim; i++)
    {
        neg_rates[i] = -rates[i];
    }

    Polyhedron Gp = *this;
    Gp.future_assign(neg_rates);
//    
    Polyhedron BadInter(dim, false), BadNoInter(dim, false);
   	for(const auto& it: *Bad.D)
    {
        const Polyhedron& Bi = PPL_Polyhedron(it.pointset());
        
        if (this->intersects(Bi))
        {
            BadInter.add_reduce(Bi);
        } else {
            BadNoInter.add_reduce(Bi);
        }
    }

    //cout << "----------------------------------------------------------" << endl;
    //cout << "Bad with no intersection " << endl;
    //cout << BadNoInter << endl;
    //cout << "Bad with intersection " << endl;
    //cout << BadInter << endl;

    // for B with no intersection with G: past(G) \ past(past(G) inter B)
    BadNoInter.intersection_assign(Gp);
    BadNoInter.future_assign(neg_rates);
    BadNoInter.negation_assign();
    Gp.intersection_assign(BadNoInter);
    Gp.reduce();
    //cout << "Good after removing Bad with no intersection"  << endl;
    //cout << Gp << endl;

    // For B with an intersection with G: past(G \ future(B)) union (G \ B)
    Polyhedron Good2 = *this;
    Polyhedron FutureBadInter = BadInter;
    FutureBadInter.future_assign(rates);
    FutureBadInter.negation_assign();
    FutureBadInter.intersection_assign(Good2);
    FutureBadInter.reduce();
    FutureBadInter.future_assign(neg_rates);
    
    Polyhedron Bad2 = Bad;
    Bad2.negation_assign();
    Good2.intersection_assign(Bad2);
    Good2.reduce();
    Good2.add_reduce(FutureBadInter);
    //cout << "Good after removing Bad with intersection"  << endl;
    //cout << Good2 << endl;

    Gp.intersection_assign(Good2);
    //cout << "final result" << endl;
    //cout << Gp << endl;

    return Gp;
}

romeo::Polyhedron romeo::Polyhedron::predt2(const cvalue rates[], const romeo::Polyhedron& Bad)
{
    // We compute (Past(G) \ Past(B)) U Past((G and Past(B)) \ B)
    const unsigned dim = this->dimension();
    // Compute negative rates
    cvalue neg_rates[dim];
    for (unsigned i = 0; i < dim; i++)
    {
        neg_rates[i] = -rates[i];
    }
    Polyhedron PastG(*this);
    PastG.future_assign(neg_rates);

    if (Bad.empty())
    {
        return PastG;
    } else {
        Polyhedron R(dim, true);

       	for(const auto& it: *Bad.D)
        {

            Polyhedron PastBad(PPL_Polyhedron(it.pointset()));
            PastBad.future_assign(neg_rates);

            Polyhedron NegBad(PPL_Polyhedron(it.pointset()));
            NegBad.negation_assign();

            Polyhedron NegPastBad(PastBad);
            NegPastBad.negation_assign();
    
            // past(G) \ past(B)
            Polyhedron Gp(PastG);
            Gp.intersection_assign(NegPastBad);

            // G inter past(B)
            PastBad.intersection_assign(*this);
    
            // (G inter past(B)) \ B
            PastBad.intersection_assign(NegBad);

            // past of all this
            PastBad.future_assign(neg_rates);

            Gp.add_reduce(PastBad);
            R.intersection_assign(Gp);
        }

        return R;
    }
}

romeo::Polyhedron romeo::Polyhedron::predt_sem(const cvalue rates[], const romeo::Polyhedron& Bad)
{
    // The set of x's for which there exists t >= 0 such that x + t in Good
    // And there is no 0 <= t1 < t such that x + t' in Bad 

    const unsigned N = this->dimension();
    Polyhedron G(*this);
    G.add_dimensions(1);

    Polyhedron B(Bad);
    B.add_dimensions(2);

    // t >= 0
    G.constrain(Var(N), CSTR_GWEAK);
    B.constrain(Var(N), CSTR_GWEAK);
    
    // t1 >= 0
    B.constrain(Var(N + 1), CSTR_GWEAK);

    // t1 <= t
    B.constrain(Var(N + 1) - Var(N), CSTR_LWEAK);
    
    for (unsigned i = 0; i < N; i++)
    {   
        // Replace x_i in G by x_i + r_i * t in G
        G.affine_image(Var(i), Var(i) - rates[i] * Var(N), 1);

        // Replace x_i in B by x_i + r_i * t1 in B
        B.affine_image(Var(i), Var(i) - rates[i] * Var(N + 1), 1);
    }

    // Project t1 out
    B.remove_higher_dimensions(N + 1);

    // We want x + r_i * t1 NOT in B
    B.negation_assign();
    
    // Together with x + r_i * t in G
    G.intersection_assign(B);

    // Project t out
    G.remove_higher_dimensions(N);

    return G;
}

romeo::Polyhedron romeo::Polyhedron::predut_sem(const cvalue rates[], const romeo::Polyhedron& Bad)
{
    // The set of x's for which there exists t >= 0 such that x + t in Good
    // And there is no 0 <= t1 < t such that x + t' in Bad 

    const unsigned N = this->dimension();
    Polyhedron G(*this);
    G.add_dimensions(1);

    Polyhedron B(Bad);
    B.add_dimensions(2);

    // t >= 0
    G.constrain(Var(N), CSTR_GWEAK);
    B.constrain(Var(N), CSTR_GWEAK);
    
    // t1 >= 0
    B.constrain(Var(N + 1), CSTR_GWEAK);

    // t1 < t
    B.constrain(Var(N + 1) - Var(N), CSTR_LSTRICT);
    
    for (unsigned i = 0; i < N; i++)
    {   
        // Replace x_i in G by x_i + r_i * t in G
        G.affine_image(Var(i), Var(i) - rates[i] * Var(N), 1);

        // Replace x_i in B by x_i + r_i * t1 in B
        B.affine_image(Var(i), Var(i) - rates[i] * Var(N + 1), 1);
    }

    // Project t1 out
    B.remove_higher_dimensions(N + 1);

    // We want x + r_i * t1 NOT in B
    B.negation_assign();
    
    // Together with x + r_i * t in G
    G.intersection_assign(B);

    // Project t out
    G.remove_higher_dimensions(N);

    return G;
}

romeo::Polyhedron romeo::Polyhedron::eprojection(const vector<unsigned>& dims) const
{
	PPL_Polyhedron result(this->dimension() - dims.size(), PPL_EMPTY);
    PPL_Variables_Set vset;
    for (auto k: dims)
    {
        vset.insert(PPL_Variable(k));   
    }

    for (const auto& P: *D)
    {
        auto Q(P.pointset());
        Q.remove_space_dimensions(vset);
        result.add_disjunct(Q);
    }

    return romeo::Polyhedron(result);
}

romeo::Polyhedron romeo::Polyhedron::uprojection(const vector<unsigned>& dims, const romeo::Polyhedron& C) const
{

    romeo::Polyhedron D(*this);
    D.negation_assign();
    D.intersection_assign(C);
    romeo::Polyhedron R(D.eprojection(dims));
    R.negation_assign();

    R.intersection_assign(C.eprojection(dims));

    return R;
}

bool romeo::Polyhedron::intersects(const Polyhedron& Q) const
{
    return !D->is_disjoint_from(*Q.D);
}

bool romeo::Polyhedron::contains(const Polyhedron& Q) const
{
    return D->contains(*Q.D);
}

bool romeo::Polyhedron::exact_contains(const Polyhedron& Q) const
{
    return D->geometrically_covers(*Q.D);
}

bool romeo::Polyhedron::is_satisfied(const PPL_Constraint& c, const PPL_Generator& p)
{
    POLY_COEFFICIENT_TYPE s = c.inhomogeneous_term() * p.divisor();

    for (unsigned i = 0; i< c.space_dimension(); i++)
    {
        s += c.coefficient(PPL_Variable(i)) * p.coefficient(PPL_Variable(i));
    }

    return (c.is_strict_inequality() ? s > 0 : s >= 0);
}

bool romeo::Polyhedron::contains_point(const PPL_Convex_Polyhedron& P, const PPL_Generator& v)
{
    PPL_Constraint_System C = P.minimized_constraints();
    
    // Check every constraint
    for (const auto& i: C)
    {
        if (!is_satisfied(i, v))
        {
            return false;
        }
    }

    return true;
}

// Integer hull related stuff
POLY_COEFFICIENT_TYPE romeo::Polyhedron::gcd(const PPL_Constraint& c)
{
    POLY_COEFFICIENT_TYPE min;
    vector<POLY_COEFFICIENT_TYPE> A;

    unsigned size = 0;
    if (c.inhomogeneous_term() != 0)
    {
        A.push_back(abs(c.inhomogeneous_term()));
        size++;
    }

    for (unsigned i=0; i<c.space_dimension(); i++)
    {
        if (c.coefficient(PPL_Variable(i)) != 0)
        {
            A.push_back(abs(c.coefficient(PPL_Variable(i))));
            size++;
        }
    }

    bool not_all_zero = (size > 0);
  
    while (not_all_zero)
    {
        unsigned index = 0;
        
        // OK because not all zero
        while (A[index] == 0)
            index++;
        
        min = A[index];
        for (unsigned i=index; i<size; i++)
        {
            if (A[i] < min && A[i] != 0)
            {
                min = A[i];
                index = i;
            }
        }

        not_all_zero = false;
        for (unsigned i=0; i<size; i++)
        {
            if (i!= index)
            {
                A[i] %= min;
                not_all_zero |= (A[i] != 0);
            }
        }
    } 

    return min;
}
    
PPL_Constraint romeo::Polyhedron::bound_normalize(const PPL_Constraint& c, unsigned M)
{
    const POLY_COEFFICIENT_TYPE m = M;
    POLY_COEFFICIENT_TYPE p = 0;
    for (unsigned i=0; i< c.space_dimension(); i++)
    {
        POLY_COEFFICIENT_TYPE q = abs(c.coefficient(PPL_Variable(i)));

        if (q > p)
            p = q;
    }

    if (p > m)
    {
        PPL_Linear_Expression L;
        POLY_COEFFICIENT_TYPE q,r;
        for (unsigned i=0; i< c.space_dimension(); i++)
        {
            r = -c.coefficient(PPL_Variable(i))*m;
#ifdef POLY_COEFFICIENT_MPZ
            mpz_fdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
            q = static_cast<POLY_COEFFICIENT_TYPE>(floor(static_cast<double>(r)/p));
#endif
            L -= q*PPL_Variable(i);
        }
                
        r = -c.inhomogeneous_term()*m;
#ifdef POLY_COEFFICIENT_MPZ
        mpz_cdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
        q = static_cast<POLY_COEFFICIENT_TYPE>(ceil(static_cast<double>(r)/p));
#endif
        L-= q;
        
        return (L >= 0);
    } else {
        return simplification(c);
    }

}

PPL_Constraint romeo::Polyhedron::divide_and_floor(const PPL_Constraint& c, POLY_COEFFICIENT_TYPE p, bool close)
{
    //cout << "Divide " << c << endl;
    //if (p==0)
    //    cout << "argh" << endl;
    PPL_Linear_Expression L;
    POLY_COEFFICIENT_TYPE q,r;
    for (unsigned i=0; i< c.space_dimension(); i++)
    {
        r = -c.coefficient(PPL_Variable(i));
#ifdef POLY_COEFFICIENT_MPZ
        mpz_fdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
        q = static_cast<POLY_COEFFICIENT_TYPE>(floor(static_cast<double>(r)/p));
#endif
        L -= q*PPL_Variable(i);
    }
            
    r = -c.inhomogeneous_term();
#ifdef POLY_COEFFICIENT_MPZ
    mpz_cdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
    q = static_cast<POLY_COEFFICIENT_TYPE>(ceil(static_cast<double>(r)/p));
#endif
    L-= q;
    
    if (c.is_strict_inequality() && !close)
        return (L > 0);
    else
        return (L >= 0);
}

bool romeo::Polyhedron::is_tight(const PPL_Constraint& c, const PPL_Generator& p)
{
    POLY_COEFFICIENT_TYPE s=c.inhomogeneous_term()*p.divisor();

    for (unsigned i=0; i< c.space_dimension(); i++)
        s += c.coefficient(PPL_Variable(i)) * p.coefficient(PPL_Variable(i));

    return (s == 0);
}

PPL_Constraint romeo::Polyhedron::simplification(const PPL_Constraint& c)
{
    POLY_COEFFICIENT_TYPE d = gcd(c);
    if (d != 1)
    {
        // Do not close the constraint (closing is the default behavior)-> false
        return divide_and_floor(c, d, false);
    } else
        return c;
}

// I wrote at some point that this was wrong but I do not see why anymore...
PPL_Constraint romeo::Polyhedron::integer_closure(const PPL_Constraint& c)
{
    if (c.is_strict_inequality())
    {
        // Close the constraint preserving only integers
        Linear_Expression e = ppl_linear_expression(c);
        return (e-1 >=0);
    } else
        return c;
}

// WRONG do not use!
PPL_Constraint romeo::Polyhedron::integer_strictification(const PPL_Constraint& c)
{
    if (c.is_nonstrict_inequality())
    {
        // Strictify the constraint preserving only integers
        Linear_Expression e = ppl_linear_expression(c);
        return (e+1 > 0);
    } else
        return c;
}



// Apply an arbitrary function on each constraint and get an new convex polyhedron
PPL_Convex_Polyhedron romeo::Polyhedron::alter_constraints(const PPL_Convex_Polyhedron& P, PPL_Constraint (*f) (const PPL_Constraint&))
{
    PPL_Constraint_System C = P.minimized_constraints();
    PPL_Constraint_System R;

    for (const auto& j: C)
    {
        if (j.is_equality())
        {
            PPL_Linear_Expression L = ppl_linear_expression(j);
            R.insert((*f)(L >= 0));
            R.insert((*f)(L <= 0));
        } else {
            R.insert((*f)(j));
        }
    }

    PPL_Convex_Polyhedron Q(R);

    // If the highest id variable has been removed for some reason, we need to adjust the dimension
    Q.add_space_dimensions_and_embed(P.space_dimension() - Q.space_dimension());

    return Q; 
}

PPL_Convex_Polyhedron romeo::Polyhedron::simplification(const PPL_Convex_Polyhedron& P)
{
    return alter_constraints(P,romeo::Polyhedron::simplification);
}

PPL_Convex_Polyhedron romeo::Polyhedron::integer_closure(const PPL_Convex_Polyhedron& P)
{
    return alter_constraints(P,romeo::Polyhedron::integer_closure);
}

PPL_Convex_Polyhedron romeo::Polyhedron::integer_strictification(const PPL_Convex_Polyhedron& P)
{
    return alter_constraints(P,romeo::Polyhedron::integer_strictification);
}

PPL_Convex_Polyhedron romeo::Polyhedron::bound_normalize(const PPL_Convex_Polyhedron& P, unsigned M)
{
    PPL_Constraint_System C = P.minimized_constraints();
    PPL_Constraint_System R;

    for (const auto& j: C)
    {
        if (j.is_equality())
        {
            PPL_Linear_Expression L = ppl_linear_expression(j);
            R.insert(bound_normalize(L >= 0, M));
            R.insert(bound_normalize(L <= 0, M));
        } else {
            R.insert(bound_normalize(j, M));
        }
    }

    PPL_Convex_Polyhedron Q(R);

    // If the highest id variable has been removed for some reason, we need to adjust the dimension
    Q.add_space_dimensions_and_embed(P.space_dimension() - Q.space_dimension());

    return Q; 
}

bool romeo::Polyhedron::has_strict_constraints(const PPL_Convex_Polyhedron& Q)
{
    PPL_Constraint_System C = Q.constraints();
    for (const auto& c: C)
    {
        if (c.is_strict_inequality())
        {
            return true;
        }
    }
    return false;
} 

PPL_Convex_Polyhedron romeo::Polyhedron::integer_hull(const PPL_Convex_Polyhedron& Q)
{
    Log.start("IH");
  
    // cout << "Parameters: " << P << endl;

    //vector<PPL_Variable> V = Vars;
    
    // IH^{strict}(S) = IH^{closed}(closure(S)) \cap S
    
    Log.start("Simplify");
    PPL_Convex_Polyhedron S = simplification(Q); 
    Log.stop("Simplify");

    if (has_strict_constraints(S))
    {
        PPL_Convex_Polyhedron P(S);
        // Tranform strict inequalities into non strict
        P.topological_closure_assign();
        closed_integer_hull(P);
        S.intersection_assign(P);
    } else {
        closed_integer_hull(S);
    }

    Log.stop("IH");
    
    return S;
}

PPL_Convex_Polyhedron romeo::Polyhedron::integer_hull_close(const PPL_Convex_Polyhedron& Q)
{
    Log.start("IH-closed");
    PPL_Convex_Polyhedron S = integer_closure(Q);
    closed_integer_hull(S);
    Log.stop("IH-closed");

    return S;
}

void romeo::Polyhedron::gauss(POLY_COEFFICIENT_TYPE** cs, unsigned start, unsigned nvars, unsigned neqs, unsigned nelims)
{
    for (unsigned i = 0; i < nelims; i++)
    {
        unsigned j = i;
        while (j < neqs && cs[j][start + i] == 0)
        {
            j++;
        }

        if (j == neqs)
        {
            continue;
        } else {
            if (i != j)
            {
                auto temp = cs[j];
                cs[j] = cs[i];
                cs[i] = temp;
            }
        }

        for (unsigned j = 0; j < neqs; j++)
        {
            if (j != i)
            {
                const auto csji = cs[j][start + i];
                if (csji != 0)
                {
                    const auto csii = cs[i][start + i];
                    for (unsigned k = 0; k < nvars; k++)
                    {
                        cs[j][k] = cs[j][k] * csii - cs[i][k] * csji;
                    } 
                } 
            }
        }
    }
}

void romeo::Polyhedron::closed_integer_hull(PPL_Convex_Polyhedron& P)
{
    // Number of parameters
    unsigned nv = P.space_dimension();

    bool ok = false;

    while (!ok)
    {
        // cout << "inthull of " ;
        // Parma_Polyhedra_Library::IO_Operators::operator<<(cout, P);
        // cout << endl;
        ok = true;

        PPL_Generator_System G = P.minimized_generators();
        PPL_Constraint_System C = P.minimized_constraints();
        
        // Look at all the vertices, even those that we cut off already
        // because this is more efficient. Since C is not changed, this is OK.
        for (const auto& i: G)
        {
            // If it is not integral
            if (i.is_point() && i.divisor() != 1)
            {
                // cout << "-   not integer: ";
                // Parma_Polyhedra_Library::IO_Operators::operator<<(cout, i);
                // cout << endl;
                
                ok = false;
                unsigned extra_vars = 0;
                PPL_Constraint_System Q;

                // Look at all the constraints in P
                for (const auto& j : C)
                {
                    // Create a constraint system of equalities with slack
                    // variables for tight constraints, i.e., those that define
                    // the vertex and are inequalities
                    if (is_tight(j, i)) 
                    {
                        if(j.is_inequality())
                        {
                            //V.push_back(Variable(nv+extra_vars));
                            PPL_Linear_Expression e = ppl_linear_expression(j);
                            Q.insert(e - PPL_Variable(nv + extra_vars) == 0);
                            // We do not need to add the PPL_Variable(nv+extra_vars) >= 0 constraint since 
                            // it plays no other role than allowing the subsequent flooring of the coefficients
                            // and the perf (sensible) and the shape of result (why?) are worse when adding it
                            extra_vars++;
                        } else {
                            Q.insert(j);
                        }
                    }
                }


                // Find a variable such that its value at the vertex is not
                // integral
                unsigned var = 0;
                for (var = 0; var < nv && i.coefficient(PPL_Variable(var)) % i.divisor() == 0; var++); 

                PPL_Variable v = PPL_Variable(var);
                
                // Unconstrain all variables except var and the slack variables
                // we get equations of type a*var + b*slacks = v
                PPL_Convex_Polyhedron R(Q);
                PPL_Variables_Set toRemove;
                for (unsigned k=0; k<nv; k++)
                {
                    if (k != var)
                    {
                        toRemove.insert(Variable(k));
                    }
                }
                // Remove would be better but we lose the correspondence to the initial variables
                // -> would require a remap!
                R.unconstrain(toRemove);

                // when slacks = 0, i.e., at the vertex, we get the vertex value of v/a
                // which is not integral. So we simplify as:
                // var + floor(b/a) slacks <= floor(v/a)
                // and we insert this new constraint in the system of tight constraints
                PPL_Constraint_System D = R.minimized_constraints();
                for (const auto& j : D)
                {
                    if (abs(j.coefficient(v)) != 0)
                    {
                        PPL_Linear_Expression e = ppl_linear_expression(j);
                        Q.insert(divide_and_floor((e <= 0), abs(j.coefficient(v))));
                    }
                }

                // Remove all slack variables
                PPL_Convex_Polyhedron T(Q);
                T.remove_higher_space_dimensions(T.space_dimension() - extra_vars);

                // Add potentially missing variables (due to the selection of constraints
                // corresponding to a vertex)
                T.add_space_dimensions_and_embed(P.space_dimension() - T.space_dimension());

                // add the new constraints to P
                P.intersection_assign(T);
            }
        }
    }
}

void romeo::Polyhedron::alter_disjuncts(PPL_Convex_Polyhedron (*f) (const PPL_Convex_Polyhedron&))
{
    const unsigned N = D->space_dimension();
	  PPL_Polyhedron* result = new PPL_Polyhedron(N, PPL_EMPTY);
	  for(const auto& it: *D)
    {
        const PPL_Convex_Polyhedron P = f(it.pointset());
        if (!P.is_empty())
        {
            result->add_disjunct(P);
        }
    }

    delete D;
    D = result;
}

void romeo::Polyhedron::integer_shape_assign()
{
    this->alter_disjuncts(integer_hull);
}

void romeo::Polyhedron::bound_normalize(unsigned M)
{
    const unsigned N = D->space_dimension();
	  PPL_Polyhedron* result = new PPL_Polyhedron(N, PPL_EMPTY);
	  for(const auto& it: *D)
	  {
        result->add_disjunct(bound_normalize(it.pointset(),M));
	  }

    if (D->contains(*result))
    {
        delete D;
        D = result;
    } else {
        this->integer_shape_assign();
    }
}

void romeo::Polyhedron::integer_shape_close_assign()
{
    this->alter_disjuncts(integer_hull_close);
}

void romeo::Polyhedron::simplification_assign()
{
    this->alter_disjuncts(simplification);
}

void romeo::Polyhedron::integer_strictification_assign()
{
    this->alter_disjuncts(integer_strictification);
}

void romeo::Polyhedron::simplify_with(const romeo::Polyhedron& P)
{
    D->simplify_using_context_assign(*P.D);
}

void romeo::Polyhedron::reduce(const bool strong)
{
    if (strong)
        D->pairwise_reduce();
    else
        D->omega_reduce();
}

unsigned romeo::Polyhedron::size() const
{
    return D->size();
}

romeo::Polyhedron::~Polyhedron()
{
    delete D;
}

void romeo::Polyhedron::clear()
{
    delete D;
    D = new PPL_Polyhedron();
}

bool romeo::Polyhedron::operator==(const Polyhedron& Q)
{
    return (*this->D == *Q.D);
}

romeo::Polyhedron& romeo::Polyhedron::operator=(const romeo::Polyhedron& Q)
{
    *D = *Q.D;

    return *this;
}

Avalue romeo::Polyhedron::minimize(const LinearExpression& L) const
{
    Avalue m;

    POLY_COEFFICIENT_TYPE n, d;
    bool b, ns;
    if (L.const_term().is_inf() || L.const_term().is_minus_inf())
    {
        return L.const_term();
    }
    b = D->minimize(L.to_PPL(), n, d, ns);
    if (b)
    {
#ifdef POLY_COEFFICIENT_MPZ
        const cvalue cn = mpz_get_si(n.get_mpz_t());
        const cvalue cd = mpz_get_si(d.get_mpz_t());
#else
        const cvalue cn = n;
        const cvalue cd = d;
#endif
        m = Avalue(cn, (ns? 0: 1), 0, cd);
    } else {
        m = Avalue::minus_infinity;
    }

    return m;
}

bool romeo::Polyhedron::contains_origin() const
{
    bool result = false;
    // For all disjuncts
	  for (const auto& it: *D)
    {
        PPL_Constraint_System C = it.pointset().minimized_constraints();
        
        // Look at all the constraints
        result = true;
        for (auto i = C.begin(); i != C.end() && result; i++)
        {
            result = (i->inhomogeneous_term() >= 0);
        }
    }

    return result;
}

PPL_Polyhedron romeo::Polyhedron::to_PPL() const
{
    return *D;
}

void romeo::Polyhedron::kapprox_assign(cvalue bounds[])
{
    const unsigned dim = this->dimension();
    for (unsigned i = 0; i < dim; i++)
    {
        if (bounds[i] >= 0)
        {
            Polyhedron Q(*this);
            Q.constrain(Var(i) - bounds[i], CSTR_GSTRICT);
            if (!Q.empty())
            {
                this->constrain(Var(i) - bounds[i], CSTR_LWEAK);
                Q.unconstrain(i);
                Q.constrain(Var(i) - bounds[i], CSTR_GSTRICT);
                this->add(Q);
                D->omega_reduce();
            }
        }
    }
}

void romeo::Polyhedron::abstract_find_dbm_coeffs(const PPL_Linear_Expression& e, unsigned NP, unsigned dim, bool lbs[], bool ubs[], cvalue lbounds[], cvalue ubounds[], unsigned& plus, unsigned& minus, cvalue& d, bool& inf)
{
    //Parma_Polyhedra_Library::IO_Operators::operator<<(cout, e);
    
    POLY_COEFFICIENT_TYPE sum = e.inhomogeneous_term();
    inf = false;
    for (unsigned x = 0; x < NP && !inf; x++)
    {
        const auto cx = e.coefficient(PPL_Variable(x));
        if (cx > 0)
        {
            if (ubs[x])
            {
                sum += cx * ubounds[x];
            } else {
                inf = true;
            }
        } else if (cx < 0) {
            if (lbs[x])
            {
                sum += cx * lbounds[x];
            } else {
                inf = true;
            }
        }
    }

    plus = NP - 1; 
    minus = NP - 1;
    POLY_COEFFICIENT_TYPE cp = 0, cm = 0;
    for (unsigned x = NP; x < dim; x++)
    {
        const auto cx = e.coefficient(PPL_Variable(x));
        if (cx > 0)
        {
            if (minus != NP - 1)
            {
                cerr << error_tag(color_output) << "Polyhedron parameter abstracting found non DBM constraint" << endl;
                exit(1);
            }
            minus = x;
            cm = -cx;
        } else if (cx < 0) {
            if (plus != NP - 1)
            {
                cerr << error_tag(color_output) << "Polyhedron parameter abstracting found non DBM constraint" << endl;
                exit(1);
            }
            plus = x;
            cp = -cx;
        }
    }

    if (!inf && (cp != 0 || cm != 0))
    {
        if (cp + cm == 0 || (plus == NP - 1) || minus == (NP - 1))
        {
            const auto c = ((plus != NP - 1) ? cp : -cm);
            if (c != 1)
            {
                if (sum % c == 0)
                {
                    sum = sum / c;
                } else {
                    sum = sum / c + 1;
                }
            }

            minus -= (NP - 1);
            plus -= (NP - 1);

#ifdef POLY_COEFFICIENT_MPZ
            d = mpz_get_si(sum.get_mpz_t());
#else
            d = sum;
#endif
        } else {
            cerr << error_tag(color_output) << "Polyhedron parameter abstracting found non DBM constraint" << endl;
            exit(1);
        }
    }
    //cout << " -> " << plus << " - " << minus << " <= " << d << " (cp = " <<  cp << ", cm = " << cm << ", inf = " << inf << ")" << endl; 
}

DBM romeo::Polyhedron::abstract_parameters(unsigned NP, bool lbs[], bool ubs[], cvalue lbounds[], cvalue ubounds[]) const
{
    const unsigned dim = dimension();
    DBM R(dim - NP + 1);

    if (D->size() == 0)
    {
        // Empty DBM
        R.constrain(1, 0, time_bound(0));
        R.constrain(0, 1, time_bound(0, true));
    } else {
        // Use only the first one
        const PPL_Convex_Polyhedron& P = D->begin()->pointset();

        PPL_Constraint_System C = P.minimized_constraints();
        
        // Look at all the constraints
        for (const auto& i: C)
        {
            unsigned plus = 0; 
            unsigned minus = 0;
            cvalue d;
            bool inf;

		        PPL_Linear_Expression e = ppl_linear_expression(i);
            abstract_find_dbm_coeffs(e, NP, dim, lbs, ubs, lbounds, ubounds, plus, minus, d, inf);
            if (!inf)
            {
                R.constrain(plus, minus, time_bound(d, !i.is_strict_inequality()));
            }
            
            if (i.is_equality())
            {
                abstract_find_dbm_coeffs(-e, NP, dim, lbs, ubs, lbounds, ubounds, plus, minus, d, inf);
                if (!inf)
                {
                    R.constrain(plus, minus, time_bound(d));
                }
            }
            

        }
    }
    //cout << "abstract " << endl<< to_string() << endl;
    //cout << "by " << endl << R.to_string() << endl;

    return R;
}

SizeDigest romeo::Polyhedron::eval_size(unsigned n) const
{
    LinearExpression L;
    for (unsigned i = 0; i < n; i++)
    {
        L = L + Var(i);
    }

    const Avalue m = minimize(L);
    const Avalue M = -minimize(0 - L);

    return SizeDigest(M - m, 0);
}


// Mapper
Mapper::Mapper(const unsigned indices[], const unsigned size, const unsigned new_size)
{
    I = new unsigned[size+new_size];
    this->new_size = new_size;
    
    // By default remove this dimension
    for (unsigned i=0; i<size+new_size; i++)
        I[i] = new_size;

    // number of new dimension to add
    nnew = 0;
    
    for (unsigned i=0; i<new_size; i++)
    {
        if (indices[i] != size)
        {
            // A previously existing dimension -> put it at the right place
            I[indices[i]] = i;
        } else {
            // A new dimension to add
            I[size + nnew] = i;
            nnew++;
        }
    }
}

bool Mapper::has_empty_codomain() const 
{ 
    return (new_size == 0);	
}

dimension_type Mapper::max_in_codomain() const 
{ 
    return new_size-1; 
}

bool Mapper::maps(dimension_type i, dimension_type& j) const 
{
	if (I[i] == new_size) {
		return false;
	} else {
		j = I[i];
		return true;
	}
}

Mapper::~Mapper() 
{ 
    delete[] I; 
}

