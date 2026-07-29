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

#include "transition.hh"
#include <climits>
#include <sstream>

#include <vzone.hh>
#include <vsclass.hh>
#include <timebounds.hh>
#include <dbm.hh>
#include <time_interval.hh>
#include <result.hh>
#include <property.hh>
#include <lexpression.hh>
#include <color_output.hh>

#include <rvalue.hh>

#include <graph_node.hh>
#include <size_digest.hh>

using namespace std;
using namespace romeo;


VZone* VZone::init(const Job& job)
{
    return new VZone(job);
}

PWNode* romeo::VZone::successor(unsigned i)
{
    return new VZone(*this, i);
}

bool VZone::set_firing_date(const unsigned i, const LExpression* e, const cvalue q=1)
{
    bool r = true;
    if (e != NULL)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        const time_bound u(v);
        const time_bound l(-v);

        D->constrain(i+1,0,u);
        D->constrain(0,i+1,l);
        r = !D->is_empty();
    }

    if (q != 1)
        cerr << warning_tag(color_output) << "set_firing_date: denominator different from 1 ignored (normal state classes)" << endl;

    return r;
}

bool romeo::VZone::firable(unsigned i) const
{
    const Transition& ti = *en[i];

    bool firable = ti.allow.eval(this).to_int();

    if (firable && job.feff)
    {
        firable = feff_firable(i);
    }

    if (firable)
    {
        DBM F(*D);

        // ti is firable
        F.constrain(0, i + 1, ti.timing->dbm_lower_bound(V, job.cts.statics));
        
        for (unsigned j=0; j<NE && !F.is_empty(); j++)
        {
            if (i!=j)
            {
                const Transition& tj = *en[j];
                if (tj.has_priority_over(ti, V, job.cts.statics))
                {
                    // If tj has priority it must not be firable
                    F.constrain(j + 1, 0, tj.timing->dbm_lower_bound(V, job.cts.statics).complement());
                }
            }
        }
        firable = !F.is_empty();
    }

    return firable;
}

// Constructors
// Create an initial symbolic state 
VZone::VZone(const Job& job): VSState(job)
{
    const unsigned size = NE+1;
    this->D = new DBM(size);
    DBM& C = *D;

    // All clocks equal and unbounded
    for (unsigned j = 0; j<size; j++)
    {
        C(0,j) = time_bound::zero;
    }

    for (unsigned i = 1; i<size; i++)
    {
        C(i,0) = time_bound::infinity;
        for (unsigned j = 1; j<i; j++)
        {
            C(i,j) = time_bound::zero;
            C(j,i) = time_bound::zero;
        }
    }

    // Apply the invariant
    for (unsigned i = 0; i < NE; i++)
    {
        C.constrain(i + 1, 0, en[i]->timing->dbm_upper_bound(V, job.cts.statics));
    }

    update_tsize();
}

// Create the successor of state class S by its kth enabled transition
VZone::VZone(const VZone& S, unsigned k): VSState(S,*S.en[k])
{
    const Transition& tf = *S.en[k];

    const unsigned size = NE+1;
    const unsigned old_size = S.NE+1;
    this->D = new DBM(*S.D);
    DBM& C = *D;

    // tf is firable
    C.constrain(0, k + 1, tf.timing->dbm_lower_bound(S.V, job.cts.statics));

    for (unsigned j=0; j < S.NE; j++)
    {
        if (k != j)
        {
            const Transition& tj = *S.en[j];
            if (tj.has_priority_over(tf, S.V, job.cts.statics))
            {
                // If tj has priority it must not be firable
                C.constrain(0, j + 1, tj.timing->dbm_lower_bound(S.V, job.cts.statics).complement());
            }
        }
    }

    unsigned indices[size];
    
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, &tf, indices, 1);
    
    // remap
    C.remap(indices, size);

    // Reset newly enabled transitions
    for (unsigned i = 0; i < size; i++)
    {
        if (indices[i] == old_size)
        {
            C.reset(i);
        }
    }

    // Future
    C.future();

    // Apply invariant
    for (unsigned i = 0; i < NE; i++)
    {
        C.constrain(i + 1, 0, en[i]->timing->dbm_upper_bound(V, job.cts.statics));
    }

    // normalization
    if (!job.no_abstract)
    {
        vector<time_bound> bounds(NE + 1);
        bounds[0] = time_bound::infinity;
        for (unsigned i = 0; i < NE; i++)
        {
            if (en[i]->timing->unbounded)
            {
                bounds[i + 1] = en[i]->timing->dbm_lower_bound(V, job.cts.statics);
            } else {
                bounds[i + 1] = time_bound::infinity;
            }
        }
        D->kxapprox(bounds);
    }

    update_tsize();
}

// Copy constructor
VZone::VZone(const VZone& S): VSState(S)
{   
    this->D = new DBM(*S.D);
}

VZone::VZone(const VZone& S, const Instruction& I): VSState(S,I)
{   
    const unsigned size = NE+1;

    this->D = new DBM(*S.D);

    DBM& C = *D;

    unsigned indices[size];
    // The reference clock does not move
    indices[0] = 0;
    // S.NE indicates we fire no transition
    map_indices(S,indices,1);

    // Remap
    this->D->remap(indices,size);

    // Reset newly added transitions
    for (unsigned i = 0; i < size; i++)
    {
        if (indices[i] == S.NE + 1)
        {
            C.reset(i);
        }
    }

    // Future
    C.future();

    // Apply invariant
    for (unsigned i = 0; i < NE; i++)
    {
        C.constrain(i + 1, 0, en[i]->timing->dbm_upper_bound(V, job.cts.statics));
    }

    update_tsize();
}

PWNode* VZone::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new VZone(*this);
    } else {
        return new VZone(*this,*I);
    }
}

std::string VZone::to_string() const
{
    stringstream domain;
    domain << VSState::to_string() << endl;

    vector<string> labels;
    labels.push_back("0");
    for (unsigned i=0; i<NE; i++)
        labels.push_back(en[i]->label);

    domain << D->to_string_labels(labels);

    return domain.str();
}

bool VZone::key_less(const PWNode* R) const
{
    const VZone* S = static_cast<const VZone*>(R); 
    relation_type r = romeo::compare(this->V, S->V, job.cts.variables.vstate_size());

    return (r == LESS || (job.pw == PASSED_EQ && r == EQUAL && D->compare(*S->D) == LESS));
}

bool VZone::equals(const PWNode* R) const
{
    const VZone* S = static_cast<const VZone*>(R); 
    return (VSState::equals(R) && D->compare(*S->D) == EQUAL);
}

bool VZone::contains(const PWNode* R) const
{
    const VZone* S = static_cast<const VZone*>(R); 
    if (VSState::equals(R))
    {
        relation_type r = D->relation(*S->D);
        return (r == EQUAL || r == GREATER);
    } else
        return false;
}


PWTRel VZone::compare(const PWNode* R) const
{
    const VZone* S = static_cast<const VZone*>(R); 
    PWTRel r = PWT_DIFF;

    if (VSState::equals(R))
    {
        relation_type rd = D->relation(*S->D);
        if (rd == EQUAL)
            r = PWT_EQ;
        else if (rd == LESS)
            r = PWT_INC;
    }

    return r;
}

// Clockval properties
void VZone::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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
        v = -(*D)(0,i+1).value();
        q = 1;
        s = (*D)(0,i+1).strict();
        u = false;
        d = false;
    }
}

void VZone::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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
        v = (*D)(i+1,0).value();
        q = 1;
        s = (*D)(i+1,0).strict();
        u = ((*D)(i+1,0) == time_bound::infinity);
        d = false;
    }
}

void VZone::update_tsize()
{
    tsize = D->eval_size();
}

bool romeo::VZone::empty() const
{
    return D->is_empty();
}

VZone::~VZone()
{
    delete D;
}

// ------------------ storage --------------------------------------------------

PassedList* VZone::init_passed(WaitingList& w, unsigned vs, bool b) const
{
    if (job.pw == PASSED_OFF) {
        return new PassedVOff();
    } else if (job.pw == PASSED_RINC || job.has_cost()) {
        return new PassedRInc(b, w, vs);
    } else if (job.pw == PASSED_EQ) {
        return new PassedVEq(b);
    } else {
        return new PassedVMerge(vs, b);
    }
}

// .............................................................................

bool VZoneMergeStorage::addr(const PWNode* s, const PResult* r)
{
    const VZone * n = static_cast<const VZone*>(s);
    return D.add_reduce(*n->D);
}

unsigned VZoneMergeStorage::size() const
{
    return D.size();
}

VZoneMergeStorage::VZoneMergeStorage(const VZone* s): VSStateMergeStorage(s), D(s->NE + 1)
{
    this->addr(s, NULL);
}

VZoneMergeStorage::~VZoneMergeStorage()
{
}

// .............................................................................

bool VZoneRIncStorage::contains(const PWNode* s) const
{
    const VZone * n = static_cast<const VZone*>(s);
    const relation_type r = D->relation(*n->D);
    return r == GREATER || r == EQUAL;
}

bool VZoneRIncStorage::is_contained_in(const PWNode* s) const
{
    const VZone * n = static_cast<const VZone*>(s);
    const relation_type r = D->relation(*n->D);
    return r == LESS || r == EQUAL;
}

VZoneRIncStorage::VZoneRIncStorage(const VZone* s): VSStateRIncStorage(s), D(new DBM(*s->D))
{
}

VZoneRIncStorage::~VZoneRIncStorage()
{
    delete D;
}

// .............................................................................

bool VZoneEqStorage::equals(const PWNode* s) const
{
    const VZone * n = static_cast<const VZone*>(s);
    
    return VSStateEqStorage::equals(s) && D->compare(*n->D) == EQUAL;
}

bool VZoneEqStorage::key_less(const EqStorage* s) const
{
    const VZoneEqStorage * n = static_cast<const VZoneEqStorage*>(s);
    const relation_type r = romeo::compare(this->V, n->V, this->size);

    return (r == LESS || (r == EQUAL && D->compare(*n->D) == LESS));
}


VZoneEqStorage::VZoneEqStorage(const VZone* s): VSStateEqStorage(s), D(new DBM(*s->D))
{
}

VZoneEqStorage::~VZoneEqStorage()
{
    delete D;
}



EqStorage* VZone::eq_storage() const
{
    return new VZoneEqStorage(this);
}

RIncStorage* VZone::rinc_storage() const
{
    return new VZoneRIncStorage(this);
}

MergeStorage* VZone::merge_storage() const
{
    return new VZoneMergeStorage(this);
}


// ------------------ control --------------------------------------------------

void VZone::set_winning(GraphNode* n, const bool w) const
{
    if (w)
    {
        n->winning.wd->add(*D);
    } 
}

void VZone::init_winning(GraphNode* n) const
{
    n->winning.wd = new DBMUnion(NE + 1);
}

void VZone::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wd->add_reduce(*x->winning.wd);
}

PResult* VZone::update_result(const GraphNode* g, PResult* r) const
{
    delete r;
    return init_result(g->winning.wd->contains_origin());
}

bool VZone::has_winning(const GraphNode* g) const
{
    return !g->winning.wd->empty();
}

bool VZone::update_reach(GraphNode* n) const
{
    list<SuccInfo>::iterator it;

    DBMUnion Good(NE + 1); 
    DBMUnion Bad(NE + 1);
    DBMUnion ForcedGood(NE + 1);
    DBMUnion ForcedBad(NE + 1);
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const unsigned int ctrl_flags = it->trans->control;
        const VZone* s = static_cast<const VZone*>(it->node->get_state());

        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            if (!it->up_to_date)
            {
                if (it->pred.wd != nullptr)
                {
                    delete it->pred.wd;
                }
                it->pred.wd = new DBMUnion(this->predecessor(s, *it->node->winning.wd, it->trans, false));

                if (it->pred2.wd != nullptr)
                {
                    delete it->pred2.wd;
                }
                if (!it->trans->timing->unbounded)
                {
                    DBMUnion LoseSucc(it->node->winning.wd->complement());
                    LoseSucc.intersection_assign(*s->D);
                    it->pred2.wd = new DBMUnion(this->predecessor(s, LoseSucc, it->trans, true));
                }
                
                
                it->up_to_date = true;
            }

            Good.add_reduce(*it->pred.wd);
            if (!it->trans->timing->unbounded)
            {
                ForcedBad.add_reduce(*it->pred2.wd);
            }
        } else {
            if (!it->up_to_date)
            {
                if (it->pred.wd != nullptr)
                {
                    delete it->pred.wd;
                }

                DBMUnion LoseSucc(it->node->winning.wd->complement());
                LoseSucc.intersection_assign(*s->D);
                it->pred.wd = new DBMUnion(this->predecessor(s, LoseSucc, it->trans, false));

                if (it->pred2.wd != nullptr)
                {
                    delete it->pred2.wd;
                }
                if (!it->trans->timing->unbounded)
                {
                    it->pred2.wd = new DBMUnion(this->predecessor(s, *it->node->winning.wd, it->trans, true));
                }
                
                it->up_to_date = true;
            }

            Bad.add_reduce(*it->pred.wd);
            if (!it->trans->timing->unbounded)
            {
                ForcedGood.add_reduce(*it->pred2.wd);
            }
        }
    }
    DBMUnion NotGood(Good.complement());
    ForcedBad.intersection_assign(NotGood);
    Bad.add_reduce(ForcedBad);
    Good.add_reduce(ForcedGood);
    
    //cout << "Good is " << endl << Good.to_string() << endl;
    //cout << "Bad is " << endl << Bad.to_string() << endl;

    DBMUnion NewWinning(Good.predt(Bad));
    NewWinning.intersection_assign(*D);

    //cout << "New Winning: " << endl << NewWinning.to_string() <<endl;
    //if (!n->winning.wd->exact_contains(NewWinning))
    bool result = false;
    if (!n->winning.wd->contains(NewWinning))
    {
        //cout << "   bigger" << endl;
        *n->winning.wd = NewWinning;

        if (!job.notrace)
        {
            // DBMUnion NotBad(Bad.complement());
            n->clear_strategy(WSET_DBM);
            for (it = n->succs.begin(); it != n->succs.end(); it++)
            {
                const unsigned int ctrl_flags = it->trans->control;
                LocalStrategy st;
                st.action = it->trans;
                for (unsigned i = 0; i < NE; i++)
                {
                    st.en.push_back(en[i]);
                }
                if (ctrl_flags & CTRL_CONTROLLABLE)
                {
                    if (!it->pred.wd->empty())
                    {
                        st.type = STRAT_ACTION;
                        st.domain.wd = new DBMUnion(*it->pred.wd);
                        // st.domain.wd->intersection_assign(NotBad);
                        //st.domain.wd->reduce();
                        add_local_strategy(WSET_DBM, n->strategy, st);
                    }
                } else {
                    if (!it->pred2.wd->empty())
                    {
                        st.type = STRAT_ENV_ACTION;
                        st.domain.wd = new DBMUnion(*it->pred2.wd);
                        //st.domain.wd->reduce();
                        add_local_strategy(WSET_DBM, n->strategy, st);
                    }
                }
            }

            // LocalStrategy wait;
            // wait.action = NULL;
            // for (unsigned i = 0; i < NE; i++)
            // {
            //     wait.en.push_back(en[i]);
            // }
            // wait.type = STRAT_ACTION;
            // wait.domain.wd = new DBMUnion(NewWinning);
            // add_local_strategy(WSET_DBM, n->strategy, wait);
        }

        //n->losing.wd = NewWinning.complement();
        result = true;
    }

    return result;
}

bool VZone::update_safe(GraphNode* n) const
{

    list<SuccInfo>::iterator it;

    DBMUnion Good(NE + 1); 
    DBMUnion Bad(NE + 1);
    DBMUnion ForcedGood(NE + 1);
    DBMUnion ForcedBad(NE + 1);
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const unsigned int ctrl_flags = it->trans->control;
        const VZone* s = static_cast<const VZone*>(it->node->get_state());

        if (!(ctrl_flags & CTRL_CONTROLLABLE))
        {
            if (!it->up_to_date)
            {
                if (it->pred.wd != nullptr)
                {
                    delete it->pred.wd;
                }
                it->pred.wd = new DBMUnion(this->predecessor(s, *it->node->winning.wd, it->trans, false));

                if (it->pred2.wd != nullptr)
                {
                    delete it->pred2.wd;
                }
                if (!it->trans->timing->unbounded)
                {
                    DBMUnion LoseSucc(it->node->winning.wd->complement());
                    LoseSucc.intersection_assign(*s->D);
                    it->pred2.wd = new DBMUnion(this->predecessor(s, LoseSucc, it->trans, true));
                }
                
                
                it->up_to_date = true;
            }

            Good.add_reduce(*it->pred.wd);
            if (!it->trans->timing->unbounded)
            {
                ForcedBad.add_reduce(*it->pred2.wd);
            }
        } else {
            if (!it->up_to_date)
            {
                if (it->pred.wd != nullptr)
                {
                    delete it->pred.wd;
                }

                DBMUnion LoseSucc(it->node->winning.wd->complement());
                LoseSucc.intersection_assign(*s->D);
                it->pred.wd = new DBMUnion(this->predecessor(s, LoseSucc, it->trans, false));

                if (it->pred2.wd != nullptr)
                {
                    delete it->pred2.wd;
                }
                if (!it->trans->timing->unbounded)
                {
                    it->pred2.wd = new DBMUnion(this->predecessor(s, *it->node->winning.wd, it->trans, true));
                }
                
                it->up_to_date = true;
            }

            Bad.add_reduce(*it->pred.wd);
            if (!it->trans->timing->unbounded)
            {
                ForcedGood.add_reduce(*it->pred2.wd);
            }
        }
    }
    // cout << "Good is " << endl << Good.to_string() << endl;
    // cout << "Bad is " << endl << Bad.to_string() << endl;
    // cout << "ForcedGood is " << endl << ForcedGood.to_string() << endl;
    // cout << "ForcedBad is " << endl << ForcedBad.to_string() << endl;
    DBMUnion NotBad(Bad.complement());
    ForcedGood.intersection_assign(NotBad);
    Bad.add_reduce(ForcedBad);
    Good.add_reduce(ForcedGood);

    DBMUnion NewWinning(Good.predut(Bad));
    NewWinning.intersection_assign(*D);

    //cout << "New Winning: " << endl << NewWinning.to_string() <<endl;
    //if (!n->winning.wd->exact_contains(NewWinning))
    bool result = false;
    if (!n->winning.wd->contains(NewWinning))
    {
        //cout << "   bigger" << endl;
        *n->winning.wd = NewWinning;

        // if (!job.notrace)
        // {
        //     n->clear_strategy(WSET_DBM);
        //     for (it = n->succs.begin(); it != n->succs.end(); it++)
        //     {
        //         LocalStrategy st;
        //         st.action = it->trans;
        //         for (unsigned i = 0; i < NE; i++)
        //         {
        //             st.en.push_back(en[i]);
        //         }
        //         const unsigned int ctrl_flags = it->trans->control;
        //         if (ctrl_flags & CTRL_CONTROLLABLE)
        //         {
        //             if (!it->pred.wd->empty())
        //             {
        //                 st.type = STRAT_ACTION;
        //                 st.domain.wd = new DBMUnion(*it->pred.wd);
        //                 // st.domain.wd->intersection_assign(NotBad);
        //                 //st.domain.wd->reduce();
        //                 add_local_strategy(WSET_DBM, n->strategy, st);
        //             }
        //         } else {
        //             if (!it->pred2.wd->empty())
        //             {
        //                 st.type = STRAT_ENV_ACTION;
        //                 st.domain.wd = new DBMUnion(*it->pred2.wd);
        //                 //st.domain.wd->reduce();
        //                 add_local_strategy(WSET_DBM, n->strategy, st);
        //             }
        //         }
        //     }

            // LocalStrategy wait;
            // wait.action = NULL;
            // for (unsigned i = 0; i < NE; i++)
            // {
            //     wait.en.push_back(en[i]);
            // }
            // wait.type = STRAT_ACTION;
            // wait.domain.wd = new DBMUnion(NewWinning);
            // add_local_strategy(WSET_DBM, n->strategy, wait);
        // }

        //n->losing.wd = NewWinning.complement();
        result = true;
    }

    return result;
}

DBMUnion VZone::predecessor(const VZone* succ, const DBMUnion& S, const Transition* tf, bool forced) const
{
    const unsigned dim = NE + 1;
    const unsigned sdim = S.dimension();

    unsigned indices[sdim];
    unsigned rindices[dim];

    unsigned f = 0;
    // We assume the index of the fired transition will be found
    while (tf != en[f])
    {
        f++;
    }

    // Map starting from the transition dimensions
    indices[0] = 0;
    succ->map_indices(*this, tf, indices, 1);

    rindices[0] = 0; // the ref clock does not move
    for (unsigned i = 0; i < NE; i++)
    {
        rindices[i + 1] = sdim;
    }

    DBMUnion R(S);
    // Find persistent transitions and reverse the mapping
    for (unsigned i = 0; i < sdim; i++)
    {
        if (indices[i] < dim)
        {
            rindices[indices[i]] = i;
        } else {
            // Constrain reset variables to be 0: go to the instant when the symbolic state was entered in.
            R.constrain(i, 0, time_bound::zero);
        }
    }

    // Eliminate non persistent transitions and remap to the size of S
    // Other dimensions are unconstrained
    R.remap(rindices, dim);
    R.intersection_assign(*D);

    // Apply the guard
    // tf is firable
    if (!forced)
    {
        R.constrain(0, f + 1, tf->timing->dbm_lower_bound(V, job.cts.statics));
    } else {
        time_bound up(-tf->timing->dbm_upper_bound(V, job.cts.statics));
        if (tf->timing->unbounded)
        {
            cout << error_tag(color_output) << ": cannot force a transition with no upper bound." << endl;
            exit(1);
        }
        if (up.strict())
        {
            cout << error_tag(color_output) << ": finite upper bounds for uncontrollable transitions should be non-strict." << endl;
            exit(1);
        }
        R.constrain(0, f + 1, up);
    }

    for (unsigned j=0; j < NE; j++)
    {
        if (f != j)
        {
            const Transition& tj = *en[j];
            if (tj.has_priority_over(*tf, V, job.cts.statics))
            {
                // If tj has priority it must not be firable
                R.constrain(j + 1, 0, tj.timing->dbm_lower_bound(V, job.cts.statics).complement());
            }
        }
    }

    return R;
}

PassedGN* VZone::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    if (job.pw == PASSED_EQ)
    {
        return new PassedGNEq(WSET_DBM, job.cts.variables.vstate_size(), F, B);
    } else {
        return new PassedGNInc(WSET_DBM, job.cts.variables.vstate_size(), F, B);
    }
}

bool romeo::VZone::safety_control_bad_state() const
{
    return false;
}

DBM* VZone::get_domain() const
{
    return D;
}

// -----------------------------------------------------------------------------

