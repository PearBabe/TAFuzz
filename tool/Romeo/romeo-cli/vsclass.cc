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

#include <climits>
#include <sstream>

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

using namespace std;
using namespace romeo;


VSClass* VSClass::init(const Job& job)
{
    return new VSClass(job);
}

PWNode* romeo::VSClass::successor(unsigned i)
{
    return new VSClass(*this, i);
}

bool VSClass::set_firing_date(const unsigned i, const LExpression* e, const cvalue q=1)
{
    bool r = true;
    if (e != nullptr)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        const time_bound u(v);
        const time_bound l(-v);

        D->constrain(i + 1, 0, u);
        D->constrain(0, i + 1, l);
        r = !D->is_empty();
    }

    if (q != 1)
    {
        cerr << warning_tag(color_output) << "set_firing_date: denominator different from 1 ignored (normal state classes)" << endl;
    }

    return r;
}

bool romeo::VSClass::firable(unsigned i) const
{
    const Transition& ti = *en[i];

    bool firable = ti.allow.eval(this).to_int();

    if (firable && job.feff)
    {
        firable = feff_firable(i);
    }
    
    for (unsigned j = 0; j < NE && firable; j++)
    {
        if (i!=j)
        {
            const Transition& tj = *en[j];
            const time_bound a = (*D)(j + 1, i + 1); // +1 because of the ref clock
            if (a.negative() || (a.non_positive() && tj.has_priority_over(ti, V, job.cts.statics)))
            {
                firable = false;
            }
        }
    }

    return firable;
}

// Constructors
// Create an initial state class
VSClass::VSClass(const Job& job): VSState(job)
{
    const unsigned size = NE+1;
    this->D = new DBM(size);
    DBM& C = *D;

    C(0,0) = time_bound::zero;
    for (unsigned i = 1; i<size; i++)
    {
        const Transition* f = en[i-1];
        C(i,0) = f->timing->dbm_upper_bound(V, job.cts.statics);
        C(0,i) = f->timing->dbm_lower_bound(V, job.cts.statics);

        C(i,i) = time_bound::zero;
        for (unsigned j = 1; j<i; j++)
        {
            C(i,j) = C(i,0) + C(0,j);
            C(j,i) = C(j,0) + C(0,i);
        }
    }

    if (!job.no_abstract)
        D->abstract_time();
}

// Create the successor of state class S by its kth enabled transition
VSClass::VSClass(const VSClass& S, unsigned k): VSState(S,*S.en[k])
{
    const Transition& tf = *S.en[k];

    const unsigned size = NE+1;
    const unsigned old_size = S.NE+1;
    this->D = new DBM(size);
    DBM& C = *D;
    const DBM& SC = *S.D;

    unsigned indices[size];
    
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S,&tf,indices,1);

    C(0,0) = time_bound::zero;
    for (unsigned i = 1; i < size; i++)
    {
        const Transition& ti = *en[i-1];

        if (indices[i] == old_size)
        {
            C(i,0) = ti.timing->dbm_upper_bound(V, job.cts.statics);
            C(0,i) = ti.timing->dbm_lower_bound(V, job.cts.statics);
        } else {
            // The upper bound of en[i] is Dik 
            C(i,0) = SC(indices[i],k+1);

            // The lower bound of en[i] is the min of (-)Djis
            C(0,i) = time_bound::zero;
            for (unsigned j=1; j<old_size; j++)
            {
                // with j == indices[i] we have min with <= 0
                C(0,i) = std::min(C(0,i), SC(j,indices[i]));
            }

            if (ti.has_priority_over(tf, S.V, job.cts.statics))
            {
                C(0,i) = std::min(C(0,i), time_bound::zero.strictify());
            }

        }
    }

    for (unsigned i = 1; i < size; i++)
    {
        C(i,i) = time_bound::zero;
        for (unsigned j = 1; j < i; j++)
        {
            C(i,j) = C(i,0) + C(0,j);
            C(j,i) = C(j,0) + C(0,i);

            if (indices[i] != old_size && indices[j] != old_size) 
            {
                // en[j] and en[j] are persistent
                // we compare to the existing distance between en[i] and en[j]'s firings
                C(i,j) = std::min(C(i,j), SC(indices[i],indices[j]));
                C(j,i) = std::min(C(j,i), SC(indices[j],indices[i]));
            } 
        }
    }

    if (!job.no_abstract)
        D->abstract_time();
}

// Copy constructor
VSClass::VSClass(const VSClass& S): VSState(S)
{   
    this->D = new DBM(*S.D);
}


VSClass::VSClass(const VSClass& S, const Instruction& I): VSState(S,I)
{   
    const unsigned size = NE+1;

    this->D = new DBM(*S.D);

    DBM& C = *D;

    unsigned S_indices[S.NE+1];
    S_indices[0] = 0;
    
    const VSClass* Sp = static_cast<const VSClass*>(S.parent);
    if (Sp != NULL)
    {
        unsigned k;
        for (k=0; k<S.NE && Sp->en[k] != S.in ; k++);

        S.map_indices(*Sp,Sp->en[k],S_indices,1);
    }

    unsigned indices[size];
    // The reference clock does not move
    indices[0] = 0;
    // S.NE indicates we fire no transition
    map_indices(S,indices,1);

    // Remap
    this->D->remap(indices,size);
    
    // Constrain newly enabled transitions
    for (unsigned i = 1; i<size; i++)
    {
        if (indices[i] == S.NE+1 || Sp == NULL || S_indices[indices[i]] == Sp->NE+1)
        {
            const Transition& f = *en[i-1];
            C(i,0) = f.timing->dbm_upper_bound(V, job.cts.statics);
            C(0,i) = f.timing->dbm_lower_bound(V, job.cts.statics);

            C(i,i) = time_bound::zero;
            for (unsigned j = 1; j<i; j++)
            {
                C(i,j) = C(i,0) + C(0,j);
                C(j,i) = C(j,0) + C(0,i);
            }
        }
    }

    if (!job.no_abstract)
        D->abstract_time();
}

PWNode* VSClass::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new VSClass(*this);
    } else {
        return new VSClass(*this,*I);
    }
}

std::string VSClass::to_string() const
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

bool VSClass::key_less(const PWNode* R) const
{
    const VSClass* S = static_cast<const VSClass*>(R); 
    relation_type r = romeo::compare(this->V, S->V, job.cts.variables.vstate_size());

    return (r == LESS || (job.pw == PASSED_EQ && r == EQUAL && D->compare(*S->D) == LESS));
}

Key VSClass::get_key() const
{
    byte* key = new byte[key_size()];
    memcpy(key, V, job.cts.variables.vstate_size()*sizeof(byte));
    D->copy_matrix(key + discrete_size());
    
    return Key(key_size(), key);
}

unsigned VSClass::key_size() const
{
    return job.cts.variables.vstate_size() + (NE + 1) * (NE + 1) * sizeof(time_bound);
}

bool VSClass::equals(const PWNode* R) const
{
    const VSClass* S = static_cast<const VSClass*>(R); 
    return (VSState::equals(R) && D->compare(*S->D) == EQUAL);
}

bool VSClass::contains(const PWNode* R) const
{
    const VSClass* S = static_cast<const VSClass*>(R); 
    if (VSState::equals(R))
    {
        relation_type r = D->relation(*S->D);
        return (r == EQUAL || r == GREATER);
    } else
        return false;
}


PWTRel VSClass::compare(const PWNode* R) const
{
    const VSClass* S = static_cast<const VSClass*>(R); 
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
void VSClass::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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

void VSClass::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
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


bool romeo::VSClass::empty() const
{
    return false;
}

VSClass::~VSClass()
{
    delete D;
}

// ------------------ storage --------------------------------------------------

PassedList* VSClass::init_passed(WaitingList& w, unsigned vs, bool b) const
{
    if (job.pw == PASSED_OFF) {
        return new PassedVOff();
    } else if (job.pw == PASSED_RINC || job.has_cost()) {
        return new PassedRInc(b, w, vs);
    } else if (job.pw == PASSED_EQ) {
        return new PassedVEq(b);
    } else if (job.pw == PASSED_HASH) {
        return new PassedVHMerge(vs, b);
    } else {
        return new PassedVMerge(vs, b);
    }
}

// .............................................................................

bool VSClassMergeStorage::addr(const PWNode* s, const PResult* r)
{
    const VSClass * n = static_cast<const VSClass*>(s);
    return D.add_reduce(*n->D);
}

unsigned VSClassMergeStorage::size() const
{
    return D.size();
}

VSClassMergeStorage::VSClassMergeStorage(const VSClass* s): VSStateMergeStorage(s), D(s->nen() + 1)
{
    this->addr(s, NULL);
}

VSClassMergeStorage::~VSClassMergeStorage()
{
}

// .............................................................................

bool VSClassRIncStorage::contains(const PWNode* s) const
{
    const VSClass * n = static_cast<const VSClass*>(s);
    const relation_type r = D->relation(*n->D);
    return r == GREATER || r == EQUAL;
}

bool VSClassRIncStorage::is_contained_in(const PWNode* s) const
{
    const VSClass * n = static_cast<const VSClass*>(s);
    const relation_type r = D->relation(*n->D);
    return r == LESS || r == EQUAL;
}

VSClassRIncStorage::VSClassRIncStorage(const VSClass* s): VSStateRIncStorage(s), D(new DBM(*s->D))
{
}

VSClassRIncStorage::~VSClassRIncStorage()
{
    delete D;
}

// .............................................................................

bool VSClassEqStorage::equals(const PWNode* s) const
{
    const VSClass * n = static_cast<const VSClass*>(s);
    
    return VSStateEqStorage::equals(s) && D->compare(*n->D) == EQUAL;
}

bool VSClassEqStorage::key_less(const EqStorage* s) const
{
    const VSClassEqStorage * n = static_cast<const VSClassEqStorage*>(s);
    const relation_type r = romeo::compare(this->V, n->V, this->size);

    return (r == LESS || (r == EQUAL && D->compare(*n->D) == LESS));
}


VSClassEqStorage::VSClassEqStorage(const VSClass* s): VSStateEqStorage(s), D(new DBM(*s->D))
{
}

VSClassEqStorage::~VSClassEqStorage()
{
    delete D;
}

// .............................................................................

EqStorage* VSClass::eq_storage() const
{
    return new VSClassEqStorage(this);
}

RIncStorage* VSClass::rinc_storage() const
{
    return new VSClassRIncStorage(this);
}

MergeStorage* VSClass::merge_storage() const
{
    return new VSClassMergeStorage(this);
}


// ------------------ control --------------------------------------------------

void VSClass::set_winning(GraphNode* n, const bool w) const
{
    //n->winning.wd = new DBMUnion(NE + 1);
    if (w)
    {
        n->winning.wd->add(*D);
    } 
}

void VSClass::init_winning(GraphNode* n) const
{
    n->winning.wd = new DBMUnion(NE + 1);
}

void VSClass::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wd->add_reduce(*x->winning.wd);
}

PResult* VSClass::update_result(const GraphNode* n, PResult* r) const
{   
    vector<unsigned> dimsu;
    for (unsigned i = 0; i < NE; i++)
    {
        if (!(en[i]->control & CTRL_CONTROLLABLE))
        {
            dimsu.push_back(i + 1);
        }
    }

    DBMUnion W = n->winning.wd->uprojection(dimsu, *D);

    return init_result(!W.empty());
}

bool VSClass::has_winning(const GraphNode* g) const
{
    return !g->winning.wd->empty();
}

bool VSClass::update_reach(GraphNode* n) const
{
    //cout << "==============================================================================" << endl;
    //cout << to_string() << endl;
    DBMUnion NewWinning(NE + 1); // Empty
    // Complement of bad states
    DBMUnion Goodu(NE + 1); // Empty
    DBMUnion NotBadu(DBM(NE + 1)); // Universal
    DBMUnion NotBadc(DBM(NE + 1)); // Universal

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
            if (succ.pred.wd != nullptr)
            {
                delete succ.pred.wd;
            }
            succ.pred.wd = new DBMUnion(pred(static_cast<const VSClass*>(succ.node->get_state()), succ.tgt.td, succ.node->winning.wd, k, true));

            // Bad predecessors
            if (succ.pred2.wd != nullptr)
            {
                delete succ.pred2.wd;
            }
            DBMUnion bad = succ.node->winning.wd->complement();
            if (succ.tgt.td != nullptr)
            {
                bad.intersection_assign(*succ.tgt.td);
            } else {
                bad.intersection_assign(*static_cast<const VSClass*>(succ.node->get_state())->D);
            }
            succ.pred2.wd = new DBMUnion(pred(static_cast<const VSClass*>(succ.node->get_state()), succ.tgt.td, &bad, k, false).complement());
            succ.pred2.wd->intersection_assign(*D);
            
            succ.up_to_date = true;
        }

        // Winning states reachable by any transition

        if ((succ.trans->control & CTRL_CONTROLLABLE))
        {
            NewWinning.add_reduce(*succ.pred.wd);
            NotBadc.intersection_assign(*succ.pred2.wd);
        } else {
            Goodu.add_reduce(*succ.pred.wd);
            NotBadu.intersection_assign(*succ.pred2.wd);
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
    //cout << n->winning.wd->to_string() << endl;

    if (!n->winning.wd->contains(NewWinning))
    {
        //cout << "more winning!" << endl;
        n->winning.wd->clear();
        *n->winning.wd = NewWinning;


        if (!job.notrace)
        {
            //n->clear_strategy(WSET_DBM);
            
            if (!n->preds.empty())
            {
                for (auto p: n->preds)
                {    
                    LocalStrategy st;
                    st.action = p.trans;
                    st.type = STRAT_RESET;

                    const VSClass* s = static_cast<const VSClass*>(p.node->get_state());
                    const unsigned old_size = s->NE + 1;
                    const unsigned size = NE + 1;
                    unsigned indices[size];
                    
                    // The reference clock does not move
                    indices[0] = 0;
                    map_indices(*s, p.trans, indices, 1);

                    // Eliminate newly enabled transitions
                    vector<unsigned> dimsu;

                    for (unsigned i = 1; i < size; i++)
                    {
                        // We want the uncontrollable newly enabled to uproj them
                        if (indices[i] == old_size) 
                        {
                            if (!(en[i - 1]->control & CTRL_CONTROLLABLE)) 
                            {
                                dimsu.push_back(i);
                            } else {
                                st.ctr.push_back(en[i - 1]);
                                st.en.push_back(en[i - 1]);
                            }
                        } else {
                            st.en.push_back(en[i - 1]);
                        }
                    }

                    st.domain.wd = new DBMUnion(NewWinning.uprojection(dimsu, *D));

                    add_local_strategy(WSET_DBM, n->strategy, st);
                }
            } else {
                // Initial state
                LocalStrategy st;
                st.action = nullptr;
                st.type = STRAT_RESET;

                const unsigned size = NE + 1;
                vector<unsigned> dimsu;

                for (unsigned i = 1; i < size; i++)
                {
                    if (!(en[i - 1]->control & CTRL_CONTROLLABLE)) 
                    {
                        dimsu.push_back(i);
                    } else {
                        st.ctr.push_back(en[i - 1]);
                        st.en.push_back(en[i - 1]);
                    }
                }

                st.domain.wd = new DBMUnion(NewWinning.uprojection(dimsu, *D));

                add_local_strategy(WSET_DBM, n->strategy, st);
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
                    st.domain.wd = new DBMUnion(*succ.pred.wd);
                    st.domain.wd->intersection_assign(NotBadu);
                    //st.domain.wd->reduce();
                    add_local_strategy(WSET_DBM, n->strategy, st);
                }
            }


        }


        return true;
    }

    return false;
}

bool VSClass::update_safe(GraphNode* n) const
{
    cout << error_tag(color_output) << "Safety not implemented with state classes." << endl;
    exit(1);
}

SuccInfo* VSClass::add_succ(GraphNode* src, const Transition* t, PState* s, GraphNode* dst) const
{
    SuccInfo* res = PWNode::add_succ(src, t, s, dst);
    if (res != nullptr && s != nullptr)
    {
        res->tgt.td = new DBM(*static_cast<const VSClass*>(s)->D);
    }
    return res;
}

DBMUnion VSClass::pred(const VSClass* s, const DBM* rsD, const DBMUnion* w, const unsigned k, const bool controllable) const
{
    const unsigned size = s->NE + 1;
    const unsigned old_size = NE + 1;
    unsigned indices[size];

    DBMUnion sD(rsD != nullptr? *rsD: *s->D);
    DBMUnion rw(*w);
    if (rsD != nullptr)
    {
        rw.intersection_assign(sD);
    }
    
    // The reference clock does not move
    indices[0] = 0;
    s->map_indices(*this, en[k], indices, 1);

    // Eliminate newly enabled transitions
    vector<unsigned> dimsc;
    vector<unsigned> dimsu;
    unsigned offset = 0; // count the number of u transitions that will be 
                         // removed by the uprojection before a given c transition
                         // or the opposite depending on whether we do upred or cpred
    for (unsigned i = 1; i < size; i++)
    {
        if (indices[i] == old_size)
        {
            if (controllable)
            {
                if (s->en[i - 1]->control & CTRL_CONTROLLABLE) 
                {
                    dimsc.push_back(i - offset);
                } else {
                    dimsu.push_back(i);
                    offset++;
                } 
            } else {
                if (s->en[i - 1]->control & CTRL_CONTROLLABLE) 
                {
                    dimsc.push_back(i);
                    offset++;
                } else {
                    dimsu.push_back(i - offset);
                } 

            }
        }
    }

    DBMUnion r(old_size - dimsc.size() - dimsu.size());
    if (controllable)
    {
        // There exist values for c newly enabled transitions such that for all values 
        // of newly enabled u transitions we win
        DBMUnion rc = rw.uprojection(dimsu, sD);
        r = rc.eprojection(dimsc);
    } else {
        DBMUnion ru = rw.eprojection(dimsc);
        DBMUnion sDproj = sD.eprojection(dimsc);
        r = ru.uprojection(dimsu, sDproj);
    }

    // Remap to match the parent state class indices
    unsigned rindices[old_size];
    for (unsigned i = 0; i < old_size; i++)
    {
        rindices[i] = r.dimension();
    }

    offset = 0;
    for (unsigned i = 0; i < size; i++)
    {
        if (indices[i] != old_size)
        {
            rindices[indices[i]] = i - offset;
        } else {
            // A newly enabled transition (thus eliminated)
            offset++;
        }
    }

    // Remap to the source class size
    // Recall that here we have only persistent variables
    r.remap(rindices, old_size);

    // Operate reverse variable change
    r.rvchange_assign(k + 1);
    
    r.intersection_assign(*D);
    for (unsigned i = 1; i < old_size; i++)
    {
        r.constrain(k + 1, i, time_bound::zero); // Firabilility constraints
        // TODO: handle priorities
    }

    //cout << " ---------------------------------------------------------------" << endl;
    //if (controllable)
    //{
    //    cout << "predc of " << w->dimension() <<endl;
    //} else {
    //    cout << "predu of " << w->dimension() <<endl;
    //}

    //cout << w->to_string() << endl;
    //cout << " in " << endl;
    //cout << *this << endl;
    //cout << " from " << endl;
    //cout << *s << endl << endl;
    //cout << "is " << endl;
    //cout << r.to_string() << endl;


    return r;
}

// -----------------------------------------------------------------------------
PassedGN* VSClass::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    if (job.pw == PASSED_EQ)
    {
        return new PassedGNEq(WSET_DBM, job.cts.variables.vstate_size(), F, B);
    } else {
        return new PassedGNInc(WSET_DBM, job.cts.variables.vstate_size(), F, B);
    }
}

bool romeo::VSClass::safety_control_bad_state() const
{
    return false;
}

