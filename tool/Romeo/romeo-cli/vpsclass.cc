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
#include <type_traits>
#include <vpsclass.hh>
#include <pdbm.hh>
#include <time_interval.hh>
#include <result.hh>
#include <property.hh>
#include <color_output.hh>
#include <linear_expression.hh>
#include <lexpression.hh>

#include <graph_node.hh>

#include <ppl.hh>
#include <polyhedron.hh>

#include <rvalue.hh>

using namespace std;
using namespace romeo;


template<class T> VPSClass<T>* VPSClass<T>::init(const Job& job)
{
    return new VPSClass<T>(job);
}

template<class T> PWNode* romeo::VPSClass<T>::successor(unsigned i)
{
    return new VPSClass<T>(*this, i);
}

template<class T> bool VPSClass<T>::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    bool r = true;
    if (e != NULL)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        T RC(D->pconstraint());
        for (auto c: (*D)(i + 1, 0).exprs)
        {
            RC.constrain(v - c, CSTR_LWEAK);
        }
        for (auto c: (*D)(0, i + 1).exprs)
        {
            RC.constrain(v + c, CSTR_GWEAK);
        }

        D->add_to_exprs(i + 1, 0, PDBMCoeff<T>(Avalue(v)));
        D->add_to_exprs(0, i + 1, PDBMCoeff<T>(Avalue(-v)));
        D->add_pconstraint(RC);
        r = !RC.empty(); 
    }

    if (q != 1)
    {
        cerr << warning_tag(color_output) << "set_firing_date: denominator different from 1 ignored (normal state classes)" << endl;
    }

    return r;
}

template<class T> T romeo::VPSClass<T>::firability(unsigned i) const
{
    T P = D->pconstraint();
    const Transition& ti = *en[i];

    for (unsigned j =0 ; j < NE; j++)
    {
        if (i != j)
        {
            const Transition& tj = *en[j];
            const PDBMCoeff<T>& a = (*D)(j + 1, i + 1);
            for (auto e: a.exprs)
            {
                const cstr_rel r = (e.const_term().is_strict() || tj.has_priority_over(ti, V, job.cts.statics))? CSTR_GSTRICT: CSTR_GWEAK;
                P.constrain(e, r);
            }
        }
    }

    return P;
}


template<class T> bool romeo::VPSClass<T>::firable(unsigned i) const
{
    const Transition& ti = *en[i];    
    //cout << ti.label << " is firable? " << firable << " " << !firability(i).is_empty() << endl;
    //cout << Polyhedron(PPL_Polyhedron(firability(i))) << endl;

    bool firable = ti.allow.eval(this).to_int();    
    if (firable && job.feff)
    {
        firable = feff_firable(i);
    }

    return firable && !firability(i).empty();
}

// Constructors
// Create an initial state class
template<class T> VPSClass<T>::VPSClass(const Job& job): VSState(job)
{
    const unsigned size = NE + 1;
    const CTS& cts = job.cts;
    const unsigned NP = cts.nparams();

    this->D = new PDBM<T>(size, NP);
    PDBM<T>& C = *D;

    C(0, 0) = PDBMCoeff<T>(0);
    for (unsigned i = 1; i<size; i++)
    {
        const Transition& f = *en[i-1];
        auto u = f.timing->ubound.linear_expression(V, cts.statics);
        if (f.timing->ustrict)
        {
            u.strictify();
        }
        auto l = 0 - f.timing->lbound.linear_expression(V, cts.statics);
        if (f.timing->lstrict)
        {
            l.strictify();
        }
        if (!f.timing->unbounded)
        {
            C(i, 0) = PDBMCoeff<T>(u);
        } // otherwise it is an empty vector -> infinity
        C(0, i) = PDBMCoeff<T>(l);
       
        C(i, i) = PDBMCoeff<T>(0);
        for (unsigned j = 1; j<i; j++)
        {
            C(i,j) = C(i,0) + C(0,j);
            C(j,i) = C(j,0) + C(0,i);
        }
    }

    if (!job.no_abstract)
    {
        C.abstract_time();
    }

    // For the integer hull all parameters should be non-negative
    T CS(NP, true);
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

    D->add_pconstraint(CS);

    // Possibly integer hull 
    if (job.ip)
    {
        C.integer_hull_assign();
    }


    //cout << "initially " << endl << *this << endl;
}

// Create the successor of state class S by its kth enabled transition
template<class T> VPSClass<T>::VPSClass(const VPSClass<T>& S, unsigned k): VSState(S,*S.en[k])
{
    const Transition& tf = *S.en[k];
    const unsigned NP = job.cts.nparams();

    const unsigned size = NE+1;
    const unsigned old_size = S.NE+1;
    this->D = new PDBM<T>(size, NP);
    PDBM<T>& C = *D;


    const PDBM<T>& SC = *S.D;

    unsigned indices[size];
    
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, &tf, indices, 1);

    auto F = S.firability(k);

    // Projection on parameters
    C.add_pconstraint(F);
    if (job.ip)
    {
        C.integer_hull_assign();
    }
    //const T& RC = C.pconstraint();
    T RC = C.pconstraint();

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
    
    C(0,0) = PDBMCoeff<T>(0);
    for (unsigned i = 1; i < size; i++)
    {
        const Transition& ti = *en[i-1];

        if (indices[i] == old_size)
        {
            if (!ti.timing->unbounded)
            {
                auto u = ti.timing->ubound.linear_expression(V, job.cts.statics);
                if (ti.timing->ustrict)
                {
                    u.strictify();
                }
                C(i, 0) = PDBMCoeff<T>(u.instantiate(vals));
            }
            auto l = 0 - ti.timing->lbound.linear_expression(V, job.cts.statics);
            if (ti.timing->lstrict)
            {
                l.strictify();
            }
            C(0, i) = PDBMCoeff<T>(l.instantiate(vals));
        } else {
            // The upper bound of en[i] is Dik 
            C.add_to_exprs(i, 0, SC(indices[i], k + 1).instantiate(vals));

            // The lower bound of en[i] is the min of (-)Djis
            C(0, i) = PDBMCoeff<T>(0);
            for (unsigned j = 1; j < old_size; j++)
            {
                // with j == indices[i] we have min with <= 0
                PDBMCoeff<T> vji = SC(j, indices[i]).instantiate(vals);
                                
                C.add_to_exprs(0, i, vji);
            }
            if (ti.has_priority_over(tf, S.V, job.cts.statics))
            {
                PDBMCoeff<T> zero_strict(Avalue(0, -1));
                C.add_to_exprs(0, i, zero_strict);
            }

            if (job.ip)
            {
                C(0, i).integer_hull_assign(RC);
            }
        }
    }
    
    for (unsigned i = 1; i < size; i++)
    {
        C(i, i) = PDBMCoeff<T>(0);
        for (unsigned j = 1; j < i; j++)
        {
            if (indices[i] != old_size && indices[j] != old_size) 
            {
                // en[j] and en[j] are persistent
                // Make a canonical form with inf
                C(i, j) = SC(indices[i], indices[j]).instantiate(vals);
                C(j, i) = SC(indices[j], indices[i]).instantiate(vals);
            } 
            //C.constrain(i, j, C(i, 0) + C(0, j));
            //C.constrain(j, i, C(j, 0) + C(0, i));
            C.add_to_exprs(i, j, PDBMCoeff<T>::plus(C(i, 0), C(0, j), RC));
            C.add_to_exprs(j, i, PDBMCoeff<T>::plus(C(j, 0), C(0, i), RC));

            if (job.ip && indices[i] != old_size && indices[j] != old_size)
            {
                C(i, j).integer_hull_assign(RC);
                C(j, i).integer_hull_assign(RC);
            }
        }
    }

    if (!job.no_abstract)
    {
        C.abstract_time();
    }

    // Propagate possible updates by integer hulls
    if (job.ip)
    {
        C.add_pconstraint(RC);
    }

    //PPL_Convex_Polyhedron RC = S.D->pconstraint();
    //RC.intersection_assign(S.firability(k));

    //cout << "---------------------------------------------" << endl;
    //cout << "firing " << S.en[k]->label << " from:" << S << endl << "gives " << endl << *this << endl;

    //if (job.ip)
    //{
    //    this->D->integer_hull_assign();
    //    //cout << "after IH" << endl;
    //    //cout << to_string() << endl;
    //}


    //cout << "firability: " << endl; 
    //cout << Polyhedron(PPL_Polyhedron(S.firability(k))) << endl;
    //cout << "____" << endl;
    //cout << Polyhedron(PPL_Polyhedron(RC)) << endl;
}

// Copy constructor
template<class T> VPSClass<T>::VPSClass(const VPSClass<T>& S): VSState(S)
{   
    this->D = new PDBM<T>(*S.D);
}


template<class T> VPSClass<T>::VPSClass(const VPSClass<T>& S, const Instruction& I): VSState(S,I)
{   
    const unsigned NP = job.cts.nparams();
    const unsigned size = NE+1;

    this->D = new PDBM<T>(*S.D);

    PDBM<T>& C = *D;

    unsigned S_indices[S.NE+1];
    S_indices[0] = 0;
    
    const VPSClass<T>* Sp = static_cast<const VPSClass<T>*>(S.parent);
    if (Sp != NULL)
    {
        S.map_indices(*Sp, S.in, S_indices, 1);
    }

    unsigned indices[size];
    // The reference clock does not move
    indices[0] = 0;

    map_indices(S,indices,1);

    // Remap
    this->D->remap(indices, size, NP);
    
    // Constrain newly enabled transitions
    for (unsigned i = 1; i<size; i++)
    {
        if (indices[i] == S.NE+1 || Sp == NULL || S_indices[indices[i]] == Sp->NE+1)
        {
            const Transition& f = *en[i-1];

            auto u = f.timing->ubound.linear_expression(V, job.cts.statics);
            if (f.timing->ustrict)
            {
                u.strictify();
            }
            auto l = 0 - f.timing->lbound.linear_expression(V, job.cts.statics);
            if (f.timing->lstrict)
            {
                l.strictify();
            }
            if (!f.timing->unbounded)
            {
                C(i, 0) = PDBMCoeff<T>(u);
            }
            C(0, i) = PDBMCoeff<T>(l);

            C(i, i) = PDBMCoeff<T>(0);
            for (unsigned j = 1; j<i; j++)
            {
                C(i, j) = C(i,0) + C(0,j);
                C(j, i) = C(j,0) + C(0,i);
            }
        }
    }

    if (!job.no_abstract)
    {
        C.abstract_time();
    }
}

template<class T> PWNode* VPSClass<T>::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new VPSClass<T>(*this);
    } else {
        return new VPSClass<T>(*this,*I);
    }
}

template<class T> std::string VPSClass<T>::to_string() const
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
    
    auto labels_ext= labels;
    labels_ext.push_back("0");
    for (unsigned k=0; k<NE; k++)
    {
        labels.push_back(en[k]->label);
        labels_ext.push_back(en[k]->label);
    }

    domain << D->to_string_labels(labels_ext, job.cts.nparams());

    // Polyhedron P = D->to_Polyhedron();
    // domain << P.to_string_labels(labels, job.cts.nparams());

    return domain.str();
}

template<class T> bool VPSClass<T>::key_less(const PWNode* R) const
{
    const VPSClass<T>* S = static_cast<const VPSClass<T>*>(R); 
    relation_type r = romeo::compare(this->V, S->V, job.cts.variables.vbyte_size());

    return (r == LESS);
}

template<class T> bool VPSClass<T>::equals(const PWNode* R) const
{
    const VPSClass<T>* S = static_cast<const VPSClass<T>*>(R); 
    return (VSState::equals(R) && D->equals(*S->D));
}

template<class T> bool VPSClass<T>::contains(const PWNode* R) const
{
    const VPSClass<T>* S = static_cast<const VPSClass<T>*>(R); 
    return (VSState::equals(R)) && D->contains(*S->D);
}


template<class T> PWTRel VPSClass<T>::compare(const PWNode* R) const
{
    const VPSClass<T>* S = static_cast<const VPSClass<T>*>(R); 
    PWTRel r = PWT_DIFF;

    if (VSState::equals(R))
    {
        if (D->equals(*S->D))
            r = PWT_EQ;
        else if (S->D->contains(*D))
            r = PWT_INC;
    }

    return r;
}

// Clockval properties
template<class T> void VPSClass<T>::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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

template<class T> void VPSClass<T>::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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

template<class T> PResult* VPSClass<T>::init_result(bool b) const
{
    return new PRPoly(job.cts.nparams(),b);
}

template<class T> bool VPSClass<T>::restriction(const PResult& r)
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



template<class T> bool romeo::VPSClass<T>::empty() const
{
    return false;
}

template<class T> void romeo::VPSClass<T>::compute_rc() const
{
    rc = new PRPoly(D->pconstraint());
}

template<class T> VPSClass<T>::~VPSClass()
{
    delete D;
}



// ------------------------- storage -------------------------------------------

template<class T> PassedList* VPSClass<T>::init_passed(WaitingList& w, unsigned vs, bool b) const
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

template<class T> bool VPSClassMergeStorage<T>::addr(const PWNode* s, const PResult* R)
{
    bool res = true;
    const VPSClass<T> * n = static_cast<const VPSClass<T>*>(s);
    vector<string> labels;
    //unsigned NP = 0;
    //for (list<Parameter>::const_iterator k=s->job.cts.begin_parameters(); k != s->job.cts.end_parameters(); k++)
    //{
    //    cvalue v;
    //    if (!k->constant(v))
    //    {
    //        NP++;
    //        labels.push_back(k->label);
    //    }
    //}
    //
    //labels.push_back("0");
    //for (unsigned k=0; k<n->nen(); k++)
    //{
    //    labels.push_back(n->en[k]->label);
    //}

    if (R != NULL)
    {
        //cout << n->D->to_string_labels(labels, NP) <<endl;
        const PRPoly& c = static_cast<const PRPoly&>(*R);
        PPL_Polyhedron P(c.constraint().to_PPL());
        res = false;
        for (auto k : P)
        {
            //cout << "!" << Polyhedron(PPL_Polyhedron(k.pointset())) << endl;
            PDBM<T> E(*n->D);
            E.add_pconstraint(Polyhedron(PPL_Polyhedron(k.pointset())));
            if (!E.pconstraint().empty())
            {
                //cout << "check" << endl;
                //cout << E.to_string_labels(labels, NP) <<endl;
                typename list<PDBM<T> >::iterator i = D.begin();
                bool add = true;
                while (i != D.end())
                {
                    //cout << "   vs " << endl;
                    //cout << i->to_string_labels(labels, NP) <<endl;

                    if (i->contains(E))
                    {
                        add = false;
                        //cout << "   included " << endl;
                        i++;
                    } else {
                        //cout << "   NOT included " << endl;
                        if (E.contains(*i)) {
                            i = D.erase(i);
                            //cout << "       contains! " << endl;
                        } else {
                            i++;
                        }
                    }
                }

                if (add)
                {
                    res = true;
                    //cout << "add it" << endl;
                    D.push_back(E);
                }
            }
        }
    } else {
        typename list<PDBM<T>>::iterator i = D.begin();
        while (i != D.end())
        {
            if (i->contains(*n->D))
            {
                res = false;
                i++;
            } else if (n->D->contains(*i)) {
                i = D.erase(i);
            } else {
                i++;
            }


        }

        if (res)
        {
            D.push_back(*n->D);
        }
    }


    return res;
}

template<class T> unsigned VPSClassMergeStorage<T>::size() const
{
    return D.size();
}

template<class T> VPSClassMergeStorage<T>::VPSClassMergeStorage(const VPSClass<T>* s): VSStateMergeStorage(s), D(1, *s->D)
{
}

template<class T> VPSClassMergeStorage<T>::~VPSClassMergeStorage()
{
}

// .............................................................................

template<class T> bool VPSClassRIncStorage<T>::contains(const PWNode* s) const
{
    const VPSClass<T> * n = static_cast<const VPSClass<T>*>(s);
    return D.contains(*n->D);
}

template<class T> bool VPSClassRIncStorage<T>::is_contained_in(const PWNode* s) const
{
    const VPSClass<T> * n = static_cast<const VPSClass<T>*>(s);
    return n->D->contains(D);
}

template<class T> VPSClassRIncStorage<T>::VPSClassRIncStorage(const VPSClass<T>* s): VSStateRIncStorage(s), D(*s->D)
{
}

template<class T> VPSClassRIncStorage<T>::~VPSClassRIncStorage()
{
}

// .............................................................................

template<class T> PassedGN* VPSClass<T>::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    if (job.pw == PASSED_EQ)
    {
        return new PassedGNEqNC(WSET_PDBM, job.cts.variables.vstate_size(), F, B);
    } else {
        return new PassedGNInc(WSET_PDBM, job.cts.variables.vstate_size(), F, B);
    }
}

// .............................................................................

template<class T> EqStorage* VPSClass<T>::eq_storage() const
{
    cerr << error_tag(color_output) << "Equality convergence not available with polyhedra" << endl;
    exit(1);
}

template<class T> RIncStorage* VPSClass<T>::rinc_storage() const
{
    return new VPSClassRIncStorage<T>(this);
}

template<class T> MergeStorage* VPSClass<T>::merge_storage() const
{
    return new VPSClassMergeStorage<T>(this);
}


// .............................................................................
namespace romeo
{
    template class VPSClass<romeo::Polyhedron>;
    template class VPSClassMergeStorage<romeo::Polyhedron>;
    template class VPSClassRIncStorage<romeo::Polyhedron>;
    template class VPSClass<romeo::PInterval>;
    template class VPSClassMergeStorage<romeo::PInterval>;
    template class VPSClassRIncStorage<romeo::PInterval>;
}
