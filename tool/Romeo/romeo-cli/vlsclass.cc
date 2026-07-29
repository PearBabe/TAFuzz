/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to [describe
functionalities and technical features of your software].

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
#include <climits>
#include <sstream>

#include <pwt.hh>
#include <vlsclass.hh>
#include <ldbm.hh>
#include <pdbm.hh>
#include <time_interval.hh>
#include <result.hh>
#include <property.hh>
#include <color_output.hh>
#include <linear_expression.hh>
#include <graph_node.hh>
#include <lexpression.hh>

#include <polyhedron.hh>
#include <ppl.hh>

#include <rvalue.hh>

using namespace std;
using namespace romeo;


template<class T> VLSClass<T>* VLSClass<T>::init(const Job& job)
{
    return new VLSClass(job);
}

template<class T> PWNode* romeo::VLSClass<T>::successor(unsigned i)
{
    return new VLSClass(*this, i);
}

template<class T> bool VLSClass<T>::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    bool r = true;
    if (e != NULL)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        vector<LDBM<T>> res;

        for (auto d: D)
        {
            T RC(d.pconstraint());
            RC.constrain(d(i + 1, 0) - v, CSTR_GWEAK);
            RC.constrain(d(0, i + 1) + v, CSTR_GWEAK);
            if (!RC.empty())
            {
                d(i + 1, 0) = v;
                d(0, i + 1) = -v;
                res.push_back(d);
            }
        }

        D = res;
        r = !res.empty(); 
    }

    if (q != 1)
    {
        cerr << warning_tag(color_output) << "set_firing_date: denominator different from 1 ignored (normal state classes)" << endl;
    }

    return r;
}

template<class T> bool romeo::VLSClass<T>::firable(unsigned i) const
{
    const Transition& ti = *en[i];    
    //cout << ti.label << " is firable? " << firable << " " << !firability(i).is_empty() << endl;
    //cout << Polyhedron(PPL_Polyhedron(firability(i))) << endl;

    bool firable = ti.allow.eval(this).to_int();    

    if (firable && job.feff)
    {
        firable = feff_firable(i);
    }

    if (firable)
    {
        for (auto d : D) 
        {
            Polyhedron F(d.pconstraint());
            for (unsigned j = 1; j < NE + 1 && !F.empty(); j++)
            {
                LinearExpression xji = d(j, i + 1);
                const Transition& tj = *en[j - 1];    
                if (j != i + 1 && (xji.const_term().is_strict() || tj.has_priority_over(ti, V, job.cts.statics)))
                {
                    F.constrain(xji, CSTR_GSTRICT);
                } else {
                    F.constrain(xji, CSTR_GWEAK); 
                }
            }

            if (!F.empty())
            {
                return true;
            }
        }
    }

    return false;
}

// Constructors
// Create an initial state class
template<class T> VLSClass<T>::VLSClass(const Job& job): VSState(job)
{
    const CTS& cts = job.cts;
    const unsigned size = NE+1;
    const unsigned NP = job.cts.nparams();

    D.push_back(LDBM<T>(size, NP));
    LDBM<T>& C = D.back();

    Polyhedron CS(NP, true);
    C(0, 0) = 0;
    for (unsigned i = 1; i < size; i++)
    {
        const Transition& f = *en[i - 1];
        if (f.timing->unbounded)
        {
            C(i, 0) = Avalue::infinity;
        } else {
            C(i, 0) = f.timing->ubound.linear_expression(V, job.cts.statics);
            if (f.timing->ustrict)
            {
                C(i, 0).strictify();
            }
        }
        C(0, i) = 0 - f.timing->lbound.linear_expression(V, job.cts.statics);
        if (f.timing->lstrict)
        {
            C(0, i).strictify();
        }

        // Consistency: intervals are not empty
        CS.constrain(C(0, i), CSTR_LWEAK);
        if (!f.timing->unbounded)
        {
            if (f.timing->lstrict || f.timing->ustrict)
            {
                CS.constrain(C(i, 0) + C(0, i), CSTR_GSTRICT);
            } else {
                CS.constrain(C(i, 0) + C(0, i), CSTR_GWEAK);
            }
        }

        C(i, i) = 0;
        for (unsigned j = 1; j < i; j++)
        {
            C(i, j) = C(i, 0) + C(0, j);
            C(j, i) = C(j, 0) + C(0, i);
        }
    }
    
    if (!job.no_abstract)
    {
        C.abstract_time();
    }

    // For the integer hull all parameters should be non-negative
    if (job.ip || job.ih_convergence)
    {
        for (unsigned i = 0; i < NP; i++)
        {
            CS.constrain(Var(i), CSTR_GWEAK);
        }
    }

    // Add consistency constraints that make the intervals non-empty
    // for the initial marking (but not the others if the intervals use
    // variables in their bounds)
    for (list<Transition>::const_iterator i=cts.begin_transitions(); i != cts.end_transitions(); i++)
    {
        const Transition& f = *i;
        const LinearExpression l = f.timing->lbound.linear_expression(V, cts.statics);
        CS.constrain(l, CSTR_GWEAK);

        if (!f.timing->unbounded)
        {
            const LinearExpression u = f.timing->ubound.linear_expression(V, cts.statics);
            const cstr_rel r = (f.timing->ustrict || f.timing->lstrict) ? CSTR_LSTRICT : CSTR_LWEAK;
            CS.constrain(l - u, r);
        }
    }

    // Initial constraints
    if (!job.cts.initp.is_null())
    {
        Polyhedron C = cts.initp.constraint(V, cts.statics, NP);
        C.add_dimensions(NP - C.dimension());

        CS.intersection_assign(C);
    }


    C.add_pconstraint(CS);

    if (job.ip)
    {
        for (auto& d: D)
        {
            d.integer_hull_assign();
        }
    }
    //cout << "initially " << endl << *this << endl;
}

// Create the successor of state class S by its kth enabled transition
template<class T> VLSClass<T>::VLSClass(const VLSClass& S, unsigned k): VSState(S,*S.en[k])
{
    const Transition& tf = *S.en[k];
    const unsigned NP = job.cts.nparams();

    const unsigned size = NE + 1;
    const unsigned old_size = S.NE + 1;

    unsigned indices[size];
        
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, &tf, indices, 1);

    for (auto d: S.D)
    {
        const LDBM<T>& SC = d;

        Polyhedron F(d.pconstraint());
        for (unsigned j = 1; j < old_size && !F.empty(); j++)
        {
            LinearExpression xjf = d(j, k + 1);
            const Transition& tj = *S.en[j - 1];    
            if (j != k + 1 && (xjf.const_term().is_strict() ||tj.has_priority_over(tf, V, job.cts.statics)))
            {
                F.constrain(xjf, CSTR_GSTRICT);
            } else {
                F.constrain(xjf, CSTR_GWEAK); 
            }
        }

        // cout << "Firability for " << S.en[k]->label << endl << F << endl;
        if (!F.empty())
        {
            vector<pair<unsigned, vector<LinearExpression>>> alts;
            LDBM<T> C(size, NP);
            C.add_pconstraint(F);

            const Polyhedron& RC = C.pconstraint();

            // Test if some parameter is now reduced to a single value
            vector<Avalue> vals(NP, Avalue::infinity);
            bool do_instantiate = false;
            for (unsigned i = 0; i < NP; i++)
            {
                const Avalue m = RC.minimize(Var(i));
                const Avalue M = -RC.minimize(0 - Var(i));
                if (m == M)
                {
                    vals[i] = m;
                    do_instantiate = true;
                }
            }
            if (!do_instantiate)
            {
                vals.clear();
            }

            C(0,0) = 0;
            for (unsigned i = 1; i < size; i++)
            {
                const Transition& ti = *en[i-1];

                if (indices[i] == old_size)
                {
                    if (ti.timing->unbounded)
                    {
                        C(i, 0) = Avalue::infinity;
                    } else {
                        C(i, 0) = ti.timing->ubound.linear_expression(V, job.cts.statics).instantiate(vals);
                        if (ti.timing->ustrict)
                        {
                            C(i, 0).strictify();
                        }
                    }
                    C(0, i) = 0 - ti.timing->lbound.linear_expression(V, job.cts.statics).instantiate(vals);
                    if (ti.timing->lstrict)
                    {
                        C(0, i).strictify();
                    }
                } else {
                    // The upper bound of en[i] is Dik 
                    C(i, 0) = SC(indices[i], k + 1).instantiate(vals);

                    // The lower bound of en[i] is the min of (-)Djis
                    C(0, i) = 0;
                    vector<LinearExpression> es;
                    for (unsigned j = 1; j < old_size; j++)
                    {
                        const Transition& tj = *S.en[j - 1];
                        // with j == indices[i] we have min with <= 0
                        LinearExpression vji = SC(j, indices[i]).instantiate(vals);
                        
                        if (j != indices[i] && tj.has_priority_over(tf, S.V, job.cts.statics))
                        {
                            vji.strictify();
                        }
                        
                        LDBM<T>::add_reduce(es, vji);
                    }
                    if (es.size() == 1)
                    {
                        C(0, i) = es.back();
                    } else {
                        alts.push_back(pair<unsigned, vector<LinearExpression>>(i, es));
                    }
                }
            }
            
            for (unsigned i = 1; i < size; i++)
            {
                C(i, i) = 0;
                for (unsigned j = 1; j < i; j++)
                {
                    C(i, j) = C(i, 0) + C(0, j);
                    C(j, i) = C(j, 0) + C(0, i);
                }
            }

            vector<string> labels;
            for (list<Parameter>::const_iterator k=job.cts.begin_parameters(); k != job.cts.end_parameters(); k++)
            {
                cvalue v;
                if (!k->constant(v))
                    labels.push_back(k->label);
            }
            
            labels.push_back("0");
            for (unsigned k=0; k<NE; k++)
            {
                labels.push_back(en[k]->label);
            }

            list<LDBM<T>*> ds(1, new LDBM<T>(C));
            list<LDBM<T>*> new_ds;
            //cout << "init succ" << endl << C.to_string_labels(labels, NP) << endl;
            //cout << "alts: " << endl;
            //for (auto a: alts)
            //{
            //    cout << a.first << " ";
            //    for (auto x: a.second)
            //    {
            //        cout << x << ", ";
            //    }
            //    cout << endl;
            //}
            //cout << endl;

            for (auto alt: alts)
            {
                for (auto ld: ds)
                {
                    for (auto a = alt.second.begin(); a != alt.second.end(); a++)
                    {
                        Polyhedron K(d.pconstraint());
                        for (auto b = alt.second.begin(); b != alt.second.end() && !K.empty(); b++)
                        {
                            if (a < b)
                            {
                                K.constrain(*a - *b, CSTR_LWEAK);
                            } else if (a > b) {
                                K.constrain(*a - *b, CSTR_LSTRICT);
                            }

                        }
                        //cout << *a << " K :" <<endl << K << endl;
                        if (!K.empty())
                        {
                            LDBM<T>* Da = new LDBM<T>(*ld);
                            Da->add_pconstraint(K);
                            if (!Da->pconstraint().empty())
                            {
                                (*Da)(0, alt.first) = *a;
                                for (unsigned j = 1; j < size; j++)
                                {
                                    if (j != alt.first)
                                    {
                                        (*Da)(j, alt.first) = (*Da)(j, 0) + *a;
                                    }
                                }
                                //cout << "   add " <<endl << Da->to_string_labels(labels, NP) << endl;
                                new_ds.push_back(Da);
                            } else {
                                delete Da;
                            }
                        }
                    }
                    delete ld;
                }
                ds = new_ds;
                new_ds.clear();
            }

            for (unsigned i = 1; i < size; i++)
            {
                for (unsigned j = 1; j < size; j++)
                {
                    if (i != j && indices[i] != old_size && indices[j] != old_size) 
                    {
                        for (auto ld: ds)
                        {
                            // en[j] and en[j] are persistent
                            // Make a canonical form with inf
                            const LinearExpression scij = SC(indices[i], indices[j]).instantiate(vals);
                            const LinearExpression cij = (*ld)(i, j);
                            const LinearExpression diff = cij - scij;
                            //cout << i << " " << j << " consider " << cij << " and " << scij << " with" << endl << ld->to_string_labels(labels, NP) << endl; 
                            if (diff.non_positive())
                            {
                                // The existing constraint is the tightest
                                //cout << i << " " << j << " a - b is better: " << endl << ld->to_string_labels(labels, NP) <<endl;
                                new_ds.push_back(ld);
                            } else {
                                if (diff.non_negative())
                                {
                                    // The constraint from the predecessor class is the tightest
                                    (*ld)(i, j) = scij;
                                    //cout << i << " " << j << " pred is better: " << endl<< ld->to_string_labels(labels, NP) << endl;
                                    new_ds.push_back(ld);
                                } else {
                                    // None of them is syntactically better than the other
                                    T P1(ld->pconstraint());
                                    P1.constrain(diff, CSTR_LSTRICT);
                                    T P2(ld->pconstraint());
                                    P2.constrain(diff, CSTR_GWEAK);
                                    LDBM<T>* ld2 = nullptr;
                                    if (!P1.empty())
                                    {
                                        ld2 = new LDBM<T>(*ld);
                                        ld->add_pconstraint(P1);
                                        //cout << i << " " << j << " mixed: add" << ld->to_string_labels(labels, NP) << endl;
                                        new_ds.push_back(ld);
                                    } else {
                                        ld2 = ld;
                                    }

                                    if (!P2.empty())
                                    {
                                        (*ld2)(i, j) = scij;
                                        ld2->add_pconstraint(P2);
                                        //cout << i << " " << j << " mixed: also add" << endl << ld2->to_string_labels(labels, NP) << endl;
                                        new_ds.push_back(ld2);
                                    }
                                }
                            }
                        }
                        ds = new_ds;
                        new_ds.clear();
                    }
                }
            }

            //cout << "---------------------------------------------" << endl;
            //cout << "firing " << S.en[k]->label << " from:" << S << endl << "gives " << endl << *this << endl;
            //cout << "firability: " << endl; 
            //cout << Polyhedron(PPL_Polyhedron(S.firability(k))) << endl;
            //cout << "____" << endl;
            //cout << Polyhedron(PPL_Polyhedron(RC)) << endl;

            for (auto ld: ds)
            {
                D.push_back(*ld);

                if (!job.no_abstract)
                {
                    D.back().abstract_time();
                }
                delete ld;
            }
        }
    }

    if (job.ip)
    {
        auto ld = D.begin();
        while (ld != D.end())
        {
            ld->integer_hull_assign();
            if (ld->pconstraint().empty())
            {
                ld = D.erase(ld);
            } else {
                ld++;
            }
        }
    }

}

// Copy constructor
template<class T> VLSClass<T>::VLSClass(const VLSClass& S): VSState(S), D(S.D)
{   
}


template<class T> VLSClass<T>::VLSClass(const VLSClass& S, const Instruction& I): VSState(S,I)
{   
    const unsigned NP = job.cts.nparams();
    const unsigned size = NE+1;

    for (auto d: S.D)
    {
        LDBM<T> C = d;

        unsigned S_indices[S.NE+1];
        S_indices[0] = 0;
        
        const VLSClass* Sp = static_cast<const VLSClass*>(S.parent);
        if (Sp != NULL)
        {
            S.map_indices(*Sp, S.in, S_indices, 1);
        }

        unsigned indices[size];
        // The reference clock does not move
        indices[0] = 0;
        map_indices(S, indices, 1);

        // Remap
        C.remap(indices, size, NP);
        
        // Constrain newly enabled transitions
        for (unsigned i = 1; i<size; i++)
        {
            if (indices[i] == S.NE+1 || Sp == NULL || S_indices[indices[i]] == Sp->NE+1)
            {
                const Transition& f = *en[i-1];
                if (f.timing->unbounded)
                {
                    C(i, 0) = Avalue::infinity;
                } else {
                    C(i, 0) = f.timing->ubound.linear_expression(V, job.cts.statics);
                    if (f.timing->ustrict)
                    {
                        C(i, 0).strictify();
                    }
                }
                C(0, i) = 0 - f.timing->lbound.linear_expression(V, job.cts.statics);
                if (f.timing->lstrict)
                {
                    C(0, i).strictify();
                }

                C(i,i) = 0;
                for (unsigned j = 1; j<i; j++)
                {
                    C(i,j) = C(i,0) + C(0,j);
                    C(j,i) = C(j,0) + C(0,i);
                }
            }
        }

        if (!job.no_abstract)
        {
            C.abstract_time();
        }
        D.push_back(C);
    }

}

template<class T> PWNode* VLSClass<T>::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new VLSClass(*this);
    } else {
        return new VLSClass(*this,*I);
    }
}

template<class T> std::string VLSClass<T>::to_string() const
{
    stringstream domain;
    domain << VSState::to_string() << endl;

    vector<string> labels;
    for (list<Parameter>::const_iterator k=job.cts.begin_parameters(); k != job.cts.end_parameters(); k++)
    {
        cvalue v;
        if (!k->constant(v))
            labels.push_back(k->label);
    }
    
    labels.push_back("0");
    for (unsigned k=0; k<NE; k++)
        labels.push_back(en[k]->label);

    //Polyhedron P = D->to_Polyhedron();
    for (auto d: D)
    {
        domain << "........................................................................................................" << endl;
        domain << d.to_string_labels(labels, job.cts.nparams());
    }

    //domain << endl << "--------------------------------------------------------------" << endl;
    //labels.clear();
    //for (list<Parameter>::const_iterator k=job.cts.begin_parameters(); k != job.cts.end_parameters(); k++)
    //{
    //    cvalue v;
    //    if (!k->constant(v))
    //        labels.push_back(k->label);
    //}
    //
    //labels.push_back("0");
    //for (unsigned k=0; k<NE; k++)
    //    labels.push_back(en[k]->label);


    //domain << D->to_string_labels(labels, job.cts.nparams());

    return domain.str();
}

template<class T> bool VLSClass<T>::key_less(const PWNode* R) const
{
    const VLSClass* S = static_cast<const VLSClass*>(R); 
    relation_type r = romeo::compare(this->V, S->V, job.cts.variables.vbyte_size());

    return (r == LESS);
}

template<class T> bool VLSClass<T>::equals(const PWNode* R) const
{
    //const VLSClass* S = static_cast<const VLSClass*>(R); 
    bool result = VSState::equals(R);
    // TODO: using to_Polyhedron?
    return result;
}

template<class T> bool VLSClass<T>::contains(const PWNode* R) const
{
    const VLSClass* S = static_cast<const VLSClass*>(R); 
    bool result = VSState::equals(R);

    return result && VLSClass<T>::contains(D, S->D);
}

template<class T> bool VLSClass<T>::contains(const vector<LDBM<T>>& a, const vector<LDBM<T>>& b)
{
    bool result = false;
    for (auto sd: b)
    {
        for (auto d: a)
        {
            if (d.pconstraint().contains(sd.pconstraint()))
            {
                result = true;
                for (unsigned i = 1; i < d.dimension() && result; i++)
                {
                    for (unsigned j = 1; j < d.dimension() && result; j++)
                    {
                        if (d(i,j).const_term().is_strict())
                        {
                            result = (d(i, j) - sd(i, j)).positive() || sd.pconstraint().minimize(d(i, j) - sd(i, j)) > 0;
                        } else {
                            result = (d(i, j) - sd(i, j)).non_negative() || sd.pconstraint().minimize(d(i, j) - sd(i, j)) >= 0;
                        }
                    }
                }
            }
            if (result)
            {
                return true;
            }
        }
    }
    return result;
}

template<class T> PWTRel VLSClass<T>::compare(const PWNode* R) const
{
    //const VLSClass* S = static_cast<const VLSClass*>(R); 
    PWTRel r = PWT_DIFF;
    // TODO

    return r;
}

// Clockval properties
template<class T> void VLSClass<T>::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
    unsigned i = 0;
    for (i=0; i<NE && en[i] != t; i++);

    // The transition is not enabled:
    if (i == NE)
    {
        v = 0;
        q = 1;
        s = false;
        u = false;
        d = true;
    } else {
        //TODO
    }
}

template<class T> void VLSClass<T>::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
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
        //TODO
    }
}

template<class T> PResult* VLSClass<T>::init_result(bool b) const
{
    return new PRPoly(job.cts.nparams(),b);
}

template<class T> bool VLSClass<T>::restriction(const PResult& r)
{
    bool result = false;

    //have_computed_rc = false;
    //if (rc != nullptr)
    //{
    //    delete rc;
    //    rc = nullptr;
    //}
    //const PRPoly& c = static_cast<const PRPoly&>(r);
    //Polyhedron Cp(c.val);
    //// TODO: Fix this
    //// Use only the first disjunct
    //PPL_Convex_Polyhedron C = Cp.to_PPL().begin()->pointset();
    //
    //if (job.restrict_update)
    //{
    //    D->add_pconstraint(C);
    //    if (job.ip)
    //        D->integer_hull_assign();

    //    result = D->pconstraint().is_empty();
    //} else {    
    //    C.intersection_assign(D->pconstraint());
    //    result = C.is_empty();
    //}
    
    return result;
}



template<class T> bool romeo::VLSClass<T>::empty() const
{
    return false;
}

template<class T> void romeo::VLSClass<T>::compute_rc() const
{
    Polyhedron P(job.cts.nparams(), false);
    for (auto d: D)
    {
        P.add(d.pconstraint());
    }
    rc = new PRPoly(P);
}

template<class T> VLSClass<T>::~VLSClass()
{
}



// ------------------------- storage -------------------------------------------

template<class T> PassedList* VLSClass<T>::init_passed(WaitingList& w, unsigned vs, bool b) const
{
    if (job.pw == PASSED_OFF)
    {
        return new PassedVOff();
   // EQ is broken in this case... because we do not have a canonical form
   // so we would need a list of classes with the same marking
   // } else if (job.pw == PASSED_EQ) {
   //     return new PassedVEq(b);
    } else if (job.pw == PASSED_RINC) {
        return new PassedRInc(b, w, vs);
    } else {
        return new PassedVMerge(vs, b);
    }
}

// .............................................................................

template<class T> bool VLSClassMergeStorage<T>::addr(const PWNode* s, const PResult* R)
{
    bool res = true;
    VLSClass<T> * n = const_cast<VLSClass<T>*>(static_cast<const VLSClass<T>*>(s));
    //vector<string> labels;
    //unsigned NP = 0;
    //for (list<Parameter>::const_iterator k=s->job.cts.begin_parameters(); k != s->job.cts.end_parameters(); k++)
    //{
    //    NP = 1;
    //    cvalue v;
    //    if (!k->constant(v))
    //        labels.push_back(k->label);
    //}
    //
    //labels.push_back("0");
    //for (unsigned k=0; k<n->nen(); k++)
    //{
    //    labels.push_back(n->en[k]->label);
    //}

    if (R != NULL)
    {
        const PRPoly& c = static_cast<const PRPoly&>(*R);
        PPL_Polyhedron P(c.constraint().to_PPL());
        auto d = n->D.begin(); 
        while (d != n->D.end())
        {
            bool skip = false;
            vector<Polyhedron> VP;
            for (auto k : P)
            {
                VP.push_back(d->pconstraint());
                VP.back().intersection_assign(PPL_Polyhedron(k.pointset()));
            }
            auto i = D.begin();
            while (i != D.end() && !skip)
            {
                //cout << "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" << endl;
                //cout << "°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°°" << endl;
                if (i->contains(*d)) 
                {
                    d = n->D.erase(d);
                    skip = true;
                    i++;
                } else if (d->contains(*i)) {
                    i = D.erase(i);
                } else {
                    unsigned inc = 0;
                    for (auto Pr : VP)
                    {
                        if (i->contains_restricted(*d, Pr))
                        {
                            //cout << X.to_string_labels(labels, NP) << endl << " included in " << endl << i->to_string_labels(labels, NP) << endl;
                            inc++;
                        } else {
                            //cout << X.to_string_labels(labels, NP) << endl << " NOT included in " << endl << i->to_string_labels(labels, NP) << endl;
                        }
                    }
                    if (inc == P.size())
                    {
                        d = n->D.erase(d);
                        skip = true;
                    } 
                    i++;
                }
            }

            if (!skip)
            {
                d++;
            }
        }
    } else {
        auto i = D.begin();
        while (i != D.end() && !n->D.empty())
        {
            bool skip =false;
            auto d = n->D.begin(); 
            while (d != n->D.end() && !skip)
            {
                if (i->contains(*d))
                {
                    d = n->D.erase(d);
                } else {
                    if (d->contains(*i)) 
                    {
                        i = D.erase(i);
                        skip = true;
                    }
                    d++;
                }
            }

            if (!skip)
            {
                i++;
            }
        }

    }

    res = !n->D.empty();
    if (res)
    {
        for (auto d: n->D)
        {
            D.push_back(d);
        }
    } else {
        //cout << "included" << endl;
    }


    return res;
}

template<class T> unsigned VLSClassMergeStorage<T>::size() const
{
    return D.size();
}

template<class T> VLSClassMergeStorage<T>::VLSClassMergeStorage(const VLSClass<T>* s): VSStateMergeStorage(s), D(s->D)
{
}

template<class T> VLSClassMergeStorage<T>::~VLSClassMergeStorage()
{
}

// .............................................................................

template<class T> bool VLSClassRIncStorage<T>::contains(const PWNode* s) const
{
    const VLSClass<T> * n = static_cast<const VLSClass<T>*>(s);
    return VLSClass<T>::contains(D, n->D);
}

template<class T> bool VLSClassRIncStorage<T>::is_contained_in(const PWNode* s) const
{
    const VLSClass<T> * n = static_cast<const VLSClass<T>*>(s);
    return VLSClass<T>::contains(n->D, D);
}

template<class T> VLSClassRIncStorage<T>::VLSClassRIncStorage(const VLSClass<T>* s): VSStateRIncStorage(s), D(s->D)
{
}

template<class T> VLSClassRIncStorage<T>::~VLSClassRIncStorage()
{
}

// .............................................................................

template<class T> PassedGN* VLSClass<T>::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    if (job.pw == PASSED_EQ)
    {
        return new PassedGNEqNC(WSET_LDBM, job.cts.variables.vstate_size(), F, B);
    } else {
        return new PassedGNInc(WSET_LDBM, job.cts.variables.vstate_size(), F, B);
    }
}

// .............................................................................

template<class T> EqStorage* VLSClass<T>::eq_storage() const
{
    cerr << error_tag(color_output) << "Equality convergence not available with polyhedra" << endl;
    exit(1);
}

template<class T> RIncStorage* VLSClass<T>::rinc_storage() const
{
    return new VLSClassRIncStorage<T>(this);
}

template<class T> MergeStorage* VLSClass<T>::merge_storage() const
{
    return new VLSClassMergeStorage<T>(this);
}

// .............................................................................
namespace romeo
{
    template class VLSClass<romeo::Polyhedron>;
    template class VLSClassMergeStorage<romeo::Polyhedron>;
    template class VLSClassRIncStorage<romeo::Polyhedron>;
    template class VLSClass<romeo::PInterval>;
    template class VLSClassMergeStorage<romeo::PInterval>;
    template class VLSClassRIncStorage<romeo::PInterval>;
}

