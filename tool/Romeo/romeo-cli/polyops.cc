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

#include <string>
#include <vector>

#include <ppl.hh>
#include <polyops.hh>
#include <expression.hh>

using namespace std;
using namespace Parma_Polyhedra_Library;
using namespace Parma_Polyhedra_Library::IO_Operators;

#define PPL_Variable Parma_Polyhedra_Library::Variable

#include <logger.hh> 
extern romeo::Logger Log;

void romeo::disjunction_assign(Pointset_Powerset<NNC_Polyhedron>* P,Pointset_Powerset<NNC_Polyhedron>* Q) 
{
    Pointset_Powerset<NNC_Polyhedron>::const_iterator i;
    for (i = Q->begin(); i != Q->end(); i++)
        P->add_disjunct(i->pointset());
}

void romeo::disjunction_assign_reduce(Pointset_Powerset<NNC_Polyhedron>* P,Pointset_Powerset<NNC_Polyhedron>* Q) 
{

    Pointset_Powerset<NNC_Polyhedron>* B = new Pointset_Powerset<NNC_Polyhedron>(*Q); 

    list<Pointset_Powerset<NNC_Polyhedron>*> waiting;

    waiting.push_back(B);
    while (!waiting.empty())
    {
        Pointset_Powerset<NNC_Polyhedron>* current_ps = waiting.front();
        waiting.pop_front();
        Pointset_Powerset<NNC_Polyhedron>::iterator cit; 
        for (cit = current_ps->begin(); cit != current_ps->end(); cit++)
        {
            Pointset_Powerset<NNC_Polyhedron>::iterator it = P->begin();
            bool added = false;
            bool stop = false;
            while (it!=P->end() && !stop)
            {
                Pointset_Powerset<NNC_Polyhedron>* C;
                C = new Pointset_Powerset<NNC_Polyhedron>(it->pointset().space_dimension(),EMPTY);
                C->add_disjunct(cit->pointset());
                C->add_disjunct(it->pointset());
                C->pairwise_reduce();
                if (C->size() == 1)
                {
                    added = true;
                    if (it->pointset().contains(cit->pointset())) {
                        stop = true;
                    } else {
                        waiting.push_back(C);
                        it = P->drop_disjunct(it);
                    }
                } else {
                    delete C;
                    it++;
                }
            }
            if (!added)
            {
                P->add_disjunct(cit->pointset());
            } 
        }
    }
}

Linear_Expression* C2LE(const Constraint& c)
{
    Linear_Expression* L = new Linear_Expression();
    for (dimension_type i = 0; i<c.space_dimension(); i++)
        *L += c.coefficient(Variable(i))*Variable(i);
    *L += c.inhomogeneous_term();
 
    return L;
}

Pointset_Powerset<NNC_Polyhedron>* romeo::negation(const Pointset_Powerset<NNC_Polyhedron>* P)
{
    Log.start("negation");
    unsigned N = P->space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* r = new Pointset_Powerset<NNC_Polyhedron>(N,UNIVERSE);

	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P->begin(); it != P->end(); it++) {
		// Transform each disjunct polyhedron into a disjunction of the negation of 
        // its constraint
		Constraint_System sys = it->pointset().minimized_constraints();
		Constraint_System::const_iterator ci;
        Pointset_Powerset<NNC_Polyhedron> neg(N,EMPTY);
		for (ci=sys.begin(); ci!=sys.end(); ci++)
		{
		    Linear_Expression *e = C2LE(*ci);
			if (ci->is_equality()) {
                neg.add_disjunct(NNC_Polyhedron(Constraint_System(*e<0)));
                neg.add_disjunct(NNC_Polyhedron(Constraint_System(*e>0)));
			} else if (ci->is_strict_inequality()) {
                // Use the fact that constraints for PPL are of the form e > 0 or e >= 0
                neg.add_disjunct(NNC_Polyhedron(Constraint_System(*e<=0)));
            } else {
                neg.add_disjunct(NNC_Polyhedron(Constraint_System(*e<0)));
            }
            delete e;
		}
		// add in conjunction this disj to the result
        r->intersection_assign(neg);
	}

    Log.stop("negation");
    return r;
}

namespace romeo
{
    string coeff_to_string(POLY_COEFFICIENT_TYPE x, bool& first_print)
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
}

string romeo::polyhedron_to_string(Pointset_Powerset<NNC_Polyhedron>* D, vector<string> labels, unsigned NP, unsigned NV)
{
    stringstream domain;

    bool print_or = false;
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
    if (D->is_empty())
        domain << "false";
    else { 
        if (D->is_universe())
           domain << "true"; 
        else {
            for (it=D->begin(); it!= D->end(); it++)
            {
                if (print_or)
                    domain << "or" << endl;
                else
                    print_or = true;

                Constraint_System C = it->pointset().minimized_constraints();
                Constraint_System::const_iterator i;

                for (i=C.begin(); i!=C.end(); i++)
                {
                    bool first_print = true;
                    unsigned k = 0;
                    unsigned pluses = 0;
                    unsigned minuses = 0;
                    POLY_COEFFICIENT_TYPE x, sign;

                    for (k = NP; k < NP+NV; k++)
                    {
                        if (i->coefficient(PPL_Variable(k)) < 0)
                            minuses++; 
                        else if (i->coefficient(PPL_Variable(k)) > 0)
                            pluses++; 
                    }   

                    sign = (minuses > pluses ? -1 : 1);
                    
                    for (k = NP; k < NP+NV; k++)
                    {       
                        if ((x = i->coefficient(PPL_Variable(k))) != 0)
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
                            if (i->coefficient(PPL_Variable(k)) < 0)
                                minuses++; 
                            else if (i->coefficient(PPL_Variable(k)) > 0)
                                pluses++; 
                        }   

                        sign = (minuses > pluses ? -1 : 1);
                        for (k = 0; k < NP; k++)
                        {       
                            if ((x = i->coefficient(PPL_Variable(k))) != 0)
                            {           
                                domain << coeff_to_string(x*sign,first_print);
                                domain << labels[k];
                            }
                        }
                    }

                    if (i->is_equality())
                        domain << " = ";
                    else
                    {
                        if (sign == 1)
                            domain << " >";
                        else
                            domain << " <";

                        if (i->is_nonstrict_inequality())
                            domain << "=";

                        domain << " ";
                    }
                    
                    first_print = true;
                    if (!no_var)
                    {
                        for (k = 0; k < NP; k++)
                        {       
                            if ((x = i->coefficient(PPL_Variable(k))) != 0)
                            {           
                                domain << coeff_to_string(-x*sign,first_print);
                                domain << labels[k];
                            }
                        }
                    }

                    if (i->inhomogeneous_term() != 0 || first_print)
                    {
                        x = sign * -i->inhomogeneous_term();
                        x = (x>=0 ? 1 : -1); 
                        domain << coeff_to_string(x,first_print);
                        domain << abs(i->inhomogeneous_term());
                    }
                            
                    domain << endl;
                }
            }

        }
    }

    return domain.str();
}

namespace romeo
{
    int pgcd(int a, int b)
    {
        if (a%b == 0)
            return b;
        else
            return pgcd(b, a%b);
    }
    
    POLY_COEFFICIENT_TYPE pgcd(const Constraint& c, const vector<Variable>& V, unsigned size)
    {
        POLY_COEFFICIENT_TYPE p = abs(c.inhomogeneous_term());
    
        // Now compute the PGCD with the rest of the coefficients 
        for (unsigned i=0; i< size; i++)
        {
            if (c.coefficient(V[i]) != 0)
            {
                POLY_COEFFICIENT_TYPE q = abs(c.coefficient(V[i]));
                if (p == 0)
                    p = q;
                else
#ifdef POLY_COEFFICIENT_MPZ
                    mpz_gcd(p.get_mpz_t(),p.get_mpz_t(),q.get_mpz_t());
#else
                    p = pgcd(p,q);
#endif
            }
        }
    
        return p;
    }
    
    Constraint* simplify_and_floor(const Constraint& c, const vector<Variable>& V, unsigned size, POLY_COEFFICIENT_TYPE p)
    {
        //cout << "Simplify " << c << endl;
        if (p==0)
            cout << "argh" << endl;
        Linear_Expression L;
        POLY_COEFFICIENT_TYPE q,r;
        for (unsigned i=0; i< size; i++)
        {
            r = -c.coefficient(V[i]);
#ifdef POLY_COEFFICIENT_MPZ
            mpz_fdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
            q = static_cast<POLY_COEFFICIENT_TYPE>(floor(static_cast<double>(r)/p));
#endif
            L -= q*V[i];
        }
               
            
        r = -c.inhomogeneous_term();
#ifdef POLY_COEFFICIENT_MPZ
        mpz_cdiv_q(q.get_mpz_t(),r.get_mpz_t(),p.get_mpz_t());
#else
        q = static_cast<POLY_COEFFICIENT_TYPE>(ceil(static_cast<double>(r)/p));
#endif
        L-= q;
    
        return new Constraint(L >= 0);
    
    }
    
    bool is_tight(const Constraint& c, const Generator& p, const vector<Variable>& V, unsigned size)
    {
        POLY_COEFFICIENT_TYPE s=c.inhomogeneous_term()*p.divisor();
    
        for (unsigned i=0; i< size; i++)
            s += c.coefficient(V[i]) * p.coefficient(V[i]);
    
        return (s == 0);
    }
    
    NNC_Polyhedron& strictify_poly(const NNC_Polyhedron& P, const vector<Variable>& V)
    {
        Constraint_System C = P.minimized_constraints();
        Constraint_System::const_iterator j;
    
        Constraint_System R;
    
        for (j=C.begin(); j!=C.end(); j++)
        {
            Linear_Expression* e = C2LE(*j);
            if (j->is_nonstrict_inequality())
            {
                
                R.insert(*e+1 >0);
            } else {
                if (j->is_equality())
                {
                    R.insert(*e+1 >0);
                    R.insert(*e-1 <0);
                } else {
                    R.insert(*j);
                }
            }
            delete e;
        }
    
        NNC_Polyhedron& Q = *(new NNC_Polyhedron(R)); 
        Q.add_space_dimensions_and_embed(V.size()- Q.space_dimension());
    
        return Q;
    }

    NNC_Polyhedron& normalize_poly(const NNC_Polyhedron& P, const vector<Variable>& V)
    {
        Constraint_System C = P.minimized_constraints();
        Constraint_System::const_iterator j;
    
        Constraint_System R;
    
        for (j=C.begin(); j!=C.end(); j++)
        {
            Constraint *c;
            if (j->is_strict_inequality())
            {
                Linear_Expression* e = C2LE(*j);
                c = new Constraint(*e-1 >=0);
                delete e;
            } else {
                c = new Constraint(*j);
            }
    
            POLY_COEFFICIENT_TYPE d = pgcd(*c, V, V.size());
            Constraint * x;
            if (d != 1)
                x = simplify_and_floor(*c, V, V.size(), d);
            else
                x = new Constraint(*c);
    
            R.insert(*x);
    
            delete x;
            delete c;
        }
    
        NNC_Polyhedron& Q = *(new NNC_Polyhedron(R)); 
        Q.add_space_dimensions_and_embed(V.size()- Q.space_dimension());
    
        return Q;
    }

    NNC_Polyhedron& closure_poly(const NNC_Polyhedron& P, const vector<Variable>& V)
    {
        Constraint_System C = P.minimized_constraints();
        Constraint_System::const_iterator j;
    
        Constraint_System R;
    
        for (j=C.begin(); j!=C.end(); j++)
        {
            Constraint *c;
            if (j->is_strict_inequality())
            {
                Linear_Expression* e = C2LE(*j);
                c = new Constraint(*e >=0);
                delete e;
            } else {
                c = new Constraint(*j);
            }
    
            POLY_COEFFICIENT_TYPE d = pgcd(*c, V, V.size());
            Constraint * x;
            if (d != 1)
                x = simplify_and_floor(*c, V, V.size(), d);
            else
                x = new Constraint(*c);
    
            R.insert(*x);
    
            delete x;
            delete c;
        }
    
        NNC_Polyhedron& Q = *(new NNC_Polyhedron(R)); 
        Q.add_space_dimensions_and_embed(V.size()- Q.space_dimension());
    
        return Q;
    }

    NNC_Polyhedron& simplify_poly(const NNC_Polyhedron& P, const vector<Variable>& V)
    {
        Constraint_System C = P.minimized_constraints();
        Constraint_System::const_iterator j;
    
        Constraint_System R;
    
        for (j=C.begin(); j!=C.end(); j++)
        {
            POLY_COEFFICIENT_TYPE d = pgcd(*j, V, V.size());
            Constraint * x;
            if (d != 1)
                x = simplify_and_floor(*j, V, V.size(), d);
            else
                x = new Constraint(*j);
    
            R.insert(*x);
    
            delete x;
        }
    
        NNC_Polyhedron& Q = *(new NNC_Polyhedron(R)); 
        Q.add_space_dimensions_and_embed(V.size()- Q.space_dimension());
    
        return Q;
    }

    void integer_hull(NNC_Polyhedron& S, const vector<Variable>& Vars)
    {
        Log.start("IH");
        // Number of parameters
        unsigned nv = S.space_dimension();
      
        // cout << "Parameters: " << P << endl;
    
        vector<Variable> V = Vars;
        //
        // Tranform strict inequalities into non strict
        // and simplify by pgcd if possible
        NNC_Polyhedron& P = closure_poly(S, V);
    
        bool ok = false;
    
        while (!ok)
        {
            //cout << P << endl;
            ok = true;
    
            //cout << "inthull of " << P << endl;
            Generator_System G = P.minimized_generators();
            Generator_System::const_iterator i;
    
            Constraint_System C = P.minimized_constraints();
            Constraint_System::const_iterator j;
            
            // Look at all the vertices
            for (i=G.begin(); i!=G.end(); i++)
            {
                // If it is not integral
                if (i->is_point() && i->divisor() != 1)
                {
                    //cout << "   not integer: " << *i << endl;
                    unsigned extra_vars = 0;
                    Constraint_System Q;
    
                    // Look at all the constraints in P
                    unsigned ntight = 0;
                    for (j=C.begin(); j!=C.end(); j++)
                    {
                        // Create a constraint system of equalities with slack
                        // variables for tight constraints, i.e., those that define
                        // the vertex and are inequalities
                        ntight++;
                        if (is_tight(*j, *i, V, nv)) 
                        {
                            if(j->is_inequality())
                            {
                                V.push_back(Variable(nv+extra_vars));
                                Linear_Expression* e = C2LE(*j);
                                Q.insert(*e - V[nv+extra_vars] == 0);
                                delete e;
                                extra_vars++;
                            }
                            else
                                Q.insert(*j);
                        }
                    }

                    // Make sure it is a vertex
                    if (ntight >= nv)
                    {    
                        ok = false;
    
                        // Find a variable such that its value at the vertex is not
                        // integral
                        unsigned var = 0;
                        for (var=0; var< nv && i->coefficient(V[var]) % i->divisor() == 0; var++); 
                        
                        // Unconstrain all variables except var and the slack variables
                        // we get equations of type a*var + b*slacks = v
                        NNC_Polyhedron R(Q);
                        Variables_Set toRemove;
                        for (unsigned k=0; k<nv; k++)
                        {
                            if (k != var)
                                toRemove.insert(V[k]);
                        }
                        R.unconstrain(toRemove);
    
                        // when slacks = 0, i.e., at the vertex, we get the vertex value of v/a
                        // which is not integral. So we simplify as:
                        // var + floor(b/a) slacks <= floor(v/a)
                        // and we insert this new constraint in the system of tight constraints
                        Constraint_System D = R.minimized_constraints();
                        Constraint_System Q2=Q;
                        for (j=D.begin(); j!= D.end(); j++)
                        {
                            if (abs(j->coefficient(V[var])) != 0)
                            {
                                Linear_Expression* e = C2LE(*j);
                                Constraint B = (*e <= 0);
                                delete e;
                                Constraint* c = simplify_and_floor(B,V,V.size(),abs(j->coefficient(V[var])));
                                Q2.insert(*c);
                                delete c;
                            }
                        }
    
                        // Remove all slack variables
                        NNC_Polyhedron T(Q2);
                        Variables_Set toRemove2;
                        vector<Variable>::iterator vi = --V.end();
                        for (unsigned k=0; k<extra_vars; k++)
                        {
                            toRemove2.insert(*vi);
                            vi--;
                        }
    
                        T.remove_space_dimensions(toRemove2);

                        // add the new constraints to P
                        P.intersection_assign(T);
                    }
    
                    for (unsigned k=0; k<extra_vars; k++)
                        V.pop_back();
                }
            }
        }
        S.intersection_assign(P);
        Log.stop("IH");
    }
}


Pointset_Powerset<NNC_Polyhedron>* romeo::integer_hull(const Pointset_Powerset<NNC_Polyhedron>& P)
{
    const unsigned N = P.space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* result = new Pointset_Powerset<NNC_Polyhedron>(N,EMPTY);
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P.begin(); it != P.end(); it++)
    {
        NNC_Polyhedron Q = it->pointset();
        vector<Variable> V;
        for (unsigned i=0; i<N; i++)
            V.push_back(Variable(i));
        integer_hull(Q,V);
        result->add_disjunct(Q);
    }
    return result;
}

Pointset_Powerset<NNC_Polyhedron>* romeo::strictify(const Pointset_Powerset<NNC_Polyhedron>& P)
{
    const unsigned N = P.space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* result = new Pointset_Powerset<NNC_Polyhedron>(N,EMPTY);
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P.begin(); it != P.end(); it++)
    {
        NNC_Polyhedron Q = it->pointset();
        vector<Variable> V;
        for (unsigned i=0; i<N; i++)
            V.push_back(Variable(i));
        NNC_Polyhedron& R = strictify_poly(Q,V);
        result->add_disjunct(R);
        delete &R;
    }
    return result;
}

Pointset_Powerset<NNC_Polyhedron>* romeo::normalize(const Pointset_Powerset<NNC_Polyhedron>& P)
{
    const unsigned N = P.space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* result = new Pointset_Powerset<NNC_Polyhedron>(N,EMPTY);
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P.begin(); it != P.end(); it++)
    {
        NNC_Polyhedron Q = it->pointset();
        vector<Variable> V;
        for (unsigned i=0; i<N; i++)
            V.push_back(Variable(i));
        NNC_Polyhedron& R = normalize_poly(Q,V);
        result->add_disjunct(R);
        delete &R;
    }
    return result;
}

Pointset_Powerset<NNC_Polyhedron>* romeo::closure(const Pointset_Powerset<NNC_Polyhedron>& P)
{
    const unsigned N = P.space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* result = new Pointset_Powerset<NNC_Polyhedron>(N,EMPTY);
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P.begin(); it != P.end(); it++)
    {
        NNC_Polyhedron Q = it->pointset();
        vector<Variable> V;
        for (unsigned i=0; i<N; i++)
            V.push_back(Variable(i));
        NNC_Polyhedron& R = closure_poly(Q,V);
        result->add_disjunct(R);
        delete &R;
    }
    return result;
}

Pointset_Powerset<NNC_Polyhedron>* romeo::simplify(const Pointset_Powerset<NNC_Polyhedron>& P)
{
    const unsigned N = P.space_dimension();
	Pointset_Powerset<NNC_Polyhedron>* result = new Pointset_Powerset<NNC_Polyhedron>(N,EMPTY);
	Pointset_Powerset<NNC_Polyhedron>::const_iterator it;
	for(it = P.begin(); it != P.end(); it++)
    {
        NNC_Polyhedron Q = it->pointset();
        vector<Variable> V;
        for (unsigned i=0; i<N; i++)
            V.push_back(Variable(i));
        NNC_Polyhedron& R = simplify_poly(Q,V);
        result->add_disjunct(R);
        delete &R;
    }
    return result;
}

bool romeo::point_projection(Expression* e, unsigned n, unsigned p, value& v)
{
    bool r = false;

    Pointset_Powerset<NNC_Polyhedron>* D = e->pconstraint(NULL,n);

    Variables_Set toRemove;
    for (unsigned k=0; k<n; k++)
        if (k != p)
            toRemove.insert(Variable(k));

    D->remove_space_dimensions(toRemove);
    
    if (!D->empty())
    {
        Constraint_System C = D->begin()->pointset().minimized_constraints();
        Constraint_System::const_iterator i;
    
        if (!C.empty() && ++C.begin() == C.end() && C.begin()->is_equality())
        {
#ifdef POLY_COEFFICIENT_MPZ
            v = -mpz_get_si(C.begin()->inhomogeneous_term().get_mpz_t());
#else
            v = -C.begin()->inhomogeneous_term();
#endif
            r = true;
        } 
    }

    return r;
}

