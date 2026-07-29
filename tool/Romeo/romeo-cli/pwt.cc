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

#include <map>
#include <vector>
#include <iostream>
#include <utility>

#include <pwt.hh>
#include <pairing_heap.hh>

#include <avalue.hh>
#include <timebounds.hh>
#include <result.hh>
#include <graph_node.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

unsigned LtBytes::vsize = 0;

PWNiterator::PWNiterator(PWNode* s): base(s), index(0) 
{
}

PWNiterator::~PWNiterator() {}

bool LtNodes::operator()(const PWNode* N1, const PWNode* N2) const
{
    return N1->key_less(N2);
}

bool LtNodesCost::operator()(const PWNode* N1, const PWNode* N2) const
{
    return (N1->cost_less_than(N2));
}

bool LtEq::operator()(const EqStorage* N1, const EqStorage* N2) const
{
    return N1->key_less(N2);
}

bool LtBytes::operator()(const byte* N1, const byte* N2) const
{
    return (romeo::compare(N1, N2, LtBytes::vsize) == LESS);
}

// Default contructor
PWNode::PWNode(const Job& j) : allocated_succs(0), sticky(true), trace_end(false), parent(NULL), trace_root(NULL), in(NULL), steps(0), storage(NULL), penalty(0), hash(0), job(j) {}
PWNode::~PWNode() 
{
    if (storage != NULL)
    {
        // Indicate to the storage that this node does not exist anymore
        storage->node = NULL;
    }
}

// Copy contructor
PWNode::PWNode(const PWNode& s) : allocated_succs(s.allocated_succs), sticky(s.sticky), trace_end(s.trace_end), parent(s.parent), trace_root(s.trace_root), in(s.in), steps(s.steps), storage(NULL), read_vars(s.read_vars), abs_vars(s.abs_vars), penalty(s.penalty), hash(s.hash), job(s.job) {}

void PWNode::deallocate() const
{
    if (!sticky && !trace_end && allocated_succs == 0)
    {
        if (parent)
        {
            parent->allocated_succs--;
            parent->deallocate();
        }

        delete this;
    }
}

// Ignore the sticky info: i.e. deallocate even if the successors have not been
// generated yet.
void PWNode::deallocate_() const
{
    if (!trace_end && allocated_succs == 0)
    {
        if (parent)
        {
            parent->allocated_succs--;
            parent->deallocate();
        }

        delete this;
    }
}


const PWNode* PWNode::parent_node() const
{
    return parent;
}

const Transition* PWNode::in_transition() const
{
    return in;
}

unsigned PWNode::nreads() const
{
    //return abs_vars.size();
    //return read_vars.size();
    //return read_vars.size() + steps;
    //return abs_vars.size() + steps;
    //return read_vars.size() + 10*abs_vars.size();
    //return read_vars.size() + abs_vars.size() + steps;
    //return 10*penalty + steps; //read_vars.size();
    return penalty; //read_vars.size();
    //return steps;
}

unsigned PWNode::nsteps() const
{
    return steps;
}

Avalue PWNode::backward_cost_heuristic() const
{
    // By default when going backward for control we try to get to the initial
    // state as fast as possible, so favor the shortest history
    return steps;
}

uint64_t PWNode::get_hash() const
{
    return hash;
}

void PWNode::set_hash(uint64_t h)
{
    hash = h;
}


void PWNode::init_propagation(GraphNode* n) const
{
    // Nothing by default
    // Used for control / backward propagation, for incremental updates (bvzone)
}

SuccInfo* PWNode::add_succ(GraphNode* src, const Transition* t, PState* s, GraphNode* dst) const
{
    bool found = false;
    for (auto its = src->succs.begin(); its != src->succs.end() && !found; its++)
    {
        found = (its->node == dst && its->trans == t);
    }

    SuccInfo* res = nullptr;
    if (!found)
    {
        src->succs.push_back(SuccInfo(dst, t));
        res = &src->succs.back(); 
    }

    return res;
}


bool PWNode::has_in_trace(const PWNode* n) const
{
    bool r = false;
    if (this != trace_root)
    {
        const PWNode* p = parent;
        while (p != trace_root && n != p)
        {
            p = p->parent;
        }

        if (n == p)
        {
            // We found that n is in the trace of this
            r = true;
        }
    }

    return r;
}

// -----------------------------------------------------------------------------

PassedList::PassedList(bool b): check_trace(b), R(NULL)
{
}

void PassedList::add_restriction(const PResult* r)
{
    Log.start("passed_add_restriction");
    if (R == NULL)
    {
        R = r->copy();
    } else {
        R->conjunction(*r);
    }
    Log.stop("passed_add_restriction");
}



void PassedList::info() const
{
}

PassedList::~PassedList()
{
}

// -----------------------------------------------------------------------------

EqStorage::~EqStorage()
{
}

PassedVEq::PassedVEq(bool b): PassedList(b)
{
}

PWTStatus PassedVEq::put(const PWNode* n)
{
    pair<set<const EqStorage*, LtEq>::iterator, bool> i = passed.insert(n->eq_storage());

    if (i.second)
    {
        // n should not be deallocated
        //n->sticky = true;
        return PWT_NEW;
    } else {

        // This state already exists in the passed list
        // We further test if it is in the trace
        if (check_trace && n != n->trace_root)
        {
            const PWNode* p = n->parent;
            while (p != n->trace_root && !p->equals(n))
            {
                p = p->parent;
            }

            if (p != n->trace_root)
                return PWT_IN_TRACE;
        }

        return PWT_IN_PASSED;
    }

}

PassedVEq::~PassedVEq()
{
    set<const EqStorage*,LtEq>::iterator i;

    for (i = passed.begin(); i != passed.end(); i++)
    {
        delete *i;
    }
}

// -----------------------------------------------------------------------------

PassedVOff::PassedVOff(): PassedList(false)
{
}

PWTStatus PassedVOff::put(const PWNode* n)
{
    return PWT_NEW;
}

// -----------------------------------------------------------------------------


MergeStorage::~MergeStorage()
{
}

PassedVMerge::PassedVMerge(unsigned vs, bool b): PassedList(b), nput(0), ninc(0)
{
    LtBytes::vsize = vs;
}

void PassedVMerge::info() const
{
    cout << "Number of nodes in passed list (markings): " << passed.size() << endl;
    cout << "Number of generated symbolic states: " << nput << endl;
    cout << "Number of inclusions: " << ninc << endl;
    cout << "Average length of collision lists: ";
    unsigned avg = 0;
    map<const byte*, MergeStorage*, LtBytes>::const_iterator it;
    for (it=passed.begin(); it != passed.end(); it++)
    {
        avg += it->second->size();   
    }
    cout << ((double) avg)/passed.size() << endl;
}


PWTStatus PassedVMerge::put(const PWNode* n)
{
    Log.start("PW");
    nput++;
    bool r = true;
    PWTStatus result = PWT_IN_PASSED;

    const byte* nkey = n->discrete();
    map<const byte*, MergeStorage*, LtBytes>::iterator i = passed.lower_bound(nkey);

    if (i != passed.end() && !passed.key_comp()(nkey, i->first))
    {
        // The key already exists
        r = i->second->addr(n, R);
        delete [] nkey;
    } else {
        passed.insert(i, pair<const byte*, MergeStorage*>(nkey, n->merge_storage()));
    }

    if (r)
    {
        Log.count("--pwnew");

        result = PWT_NEW;
    } else {
        ninc++;
        // This state already exists in the passed list
        // We further test if it is in the trace
        if (n != n->trace_root)
        {
            const PWNode* p = n->parent;
            if (check_trace)
            {
                PWTRel req = PWT_DIFF;
                while (p != n->trace_root && req != PWT_EQ)
                {
                    PWTRel req2 = n->compare(p);
                    if (req2 != PWT_DIFF)
                        req = req2;
                    p = p->parent;
                }

                if (req == PWT_EQ)
                    result = PWT_IN_TRACE;
                else if (req == PWT_INC)
                    result = PWT_NEW;
            }
        }

        Log.count("--pwin");
    }
    
    Log.stop("PW");

    return result;
}

PWTStatus PassedVMerge::putr(const PWNode* n, const PResult* res)
{
    Log.start("PW");
    nput++;
    bool r = true;
    PWTStatus result = PWT_IN_PASSED;

    const byte* nkey = n->discrete();
    map<const byte*, MergeStorage*, LtBytes>::iterator i = passed.lower_bound(nkey);

    if (i != passed.end() && !passed.key_comp()(nkey, i->first))
    {
        // The key already exists
        r = i->second->addr(n, res);
        delete [] nkey;
    } else {
        passed.insert(i, pair<const byte*, MergeStorage*>(nkey, n->merge_storage()));
    }

    if (r)
    {
        Log.count("--pwnew");

        result = PWT_NEW;
    } else {
        ninc++;
        // This state already exists in the passed list
        // We further test if it is in the trace
        if (n != n->trace_root)
        {
            const PWNode* p = n->parent;
            if (check_trace)
            {
                PWTRel req = PWT_DIFF;
                while (p != n->trace_root && req != PWT_EQ)
                {
                    PWTRel req2 = n->compare(p);
                    if (req2 != PWT_DIFF)
                        req = req2;
                    p = p->parent;
                }

                if (req == PWT_EQ)
                    result = PWT_IN_TRACE;
                else if (req == PWT_INC)
                    result = PWT_NEW;
            }
        }

        Log.count("--pwin");
    }
    
    Log.stop("PW");

    return result;
}

PassedVMerge::~PassedVMerge()
{
    map<const byte*, MergeStorage*, LtBytes>::iterator i;

    for (i = passed.begin(); i != passed.end(); i++)
    {
        delete [] i->first;
        delete i->second;
    }
}

// -----------------------------------------------------------------------------


PassedVHMerge::PassedVHMerge(unsigned vs, bool b): PassedList(b), passed(1 << 20), nput(0), ninc(0)
{
    LtBytes::vsize = vs;
}

void PassedVHMerge::info() const
{
    //cout << "Number of nodes in passed list (markings): " << passed.size() << endl;
    //cout << "Number of generated symbolic states: " << nput << endl;
    //cout << "Number of inclusions: " << ninc << endl;
    //cout << "Average length of collision lists: ";
    //unsigned avg = 0;
    //map<const byte*, MergeStorage*, LtBytes>::const_iterator it;
    //for (it=passed.begin(); it != passed.end(); it++)
    //{
    //    avg += it->second->size();   
    //}
    //cout << ((double) avg)/passed.size() << endl;
}

PWTStatus PassedVHMerge::put(const PWNode* n)
{
    Log.start("PW");
    nput++;
    bool r = true;
    PWTStatus result = PWT_IN_PASSED;

    const byte* nkey = n->discrete();
    //const unsigned bucket = n->get_hash() % passed.size();
    // Fibonacci hashing
    const unsigned bucket = (n->get_hash() * 11400714819323198485llu) >> 44; // 20 bits

    auto& pb = passed[bucket];

    auto i = pb.begin();
    while (i != pb.end() && compare(i->first, nkey, LtBytes::vsize) != EQUAL)
    {
        i++;
    }

    if (i != pb.end())
    {
        // The key already exists
        r = i->second->addr(n, R);
        delete [] nkey;
    } else {
        pb.push_back(pair<const byte*, MergeStorage*>(nkey, n->merge_storage()));
    }

    if (r)
    {
        Log.count("--pwnew");

        result = PWT_NEW;
    } else {
        ninc++;
        // This state already exists in the passed list
        // We further test if it is in the trace
        if (n != n->trace_root)
        {
            const PWNode* p = n->parent;
            if (check_trace)
            {
                PWTRel req = PWT_DIFF;
                while (p != n->trace_root && req != PWT_EQ)
                {
                    PWTRel req2 = n->compare(p);
                    if (req2 != PWT_DIFF)
                        req = req2;
                    p = p->parent;
                }

                if (req == PWT_EQ)
                    result = PWT_IN_TRACE;
                else if (req == PWT_INC)
                    result = PWT_NEW;
            }
        }

        Log.count("--pwin");
    }
    
    Log.stop("PW");

    return result;
}

PWTStatus PassedVHMerge::putr(const PWNode* n, const PResult* res)
{
    Log.start("PW");
    nput++;
    bool r = true;
    PWTStatus result = PWT_IN_PASSED;

    const byte* nkey = n->discrete();
    //const unsigned bucket = n->get_hash() % passed.size();
    const unsigned bucket = (n->get_hash() * 11400714819323198485llu) >> 44; // 20 bits

    auto& pb = passed[bucket];

    auto i = pb.begin();
    while (i != pb.end() && compare(i->first, nkey, LtBytes::vsize) != EQUAL)
    {
        i++;
    }

    if (i != pb.end())
    {
        // The key already exists
        r = i->second->addr(n, res);
        delete [] nkey;
    } else {
        pb.push_back(pair<const byte*, MergeStorage*>(nkey, n->merge_storage()));
    }

    if (r)
    {
        Log.count("--pwnew");

        result = PWT_NEW;
    } else {
        ninc++;
        // This state already exists in the passed list
        // We further test if it is in the trace
        if (n != n->trace_root)
        {
            const PWNode* p = n->parent;
            if (check_trace)
            {
                PWTRel req = PWT_DIFF;
                while (p != n->trace_root && req != PWT_EQ)
                {
                    PWTRel req2 = n->compare(p);
                    if (req2 != PWT_DIFF)
                        req = req2;
                    p = p->parent;
                }

                if (req == PWT_EQ)
                    result = PWT_IN_TRACE;
                else if (req == PWT_INC)
                    result = PWT_NEW;
            }
        }

        Log.count("--pwin");
    }
    
    Log.stop("PW");

    return result;
}

PassedVHMerge::~PassedVHMerge()
{
    for (auto& i : passed)
    {
        for (auto& j : i)
        {
            delete [] j.first;
            delete j.second;
        }
    }
}



// -----------------------------------------------------------------------------
RIncStorage::RIncStorage(const PWNode* s): node(s)
{
    s->storage = this;
}

RIncStorage::~RIncStorage()
{
    // Indicate to the node that its storage has been deleted (should not happen)
    if (node != NULL)
    {
        node->storage = NULL;
    }
}

const PWNode* RIncStorage::get_node() const
{
    return node;
}

PassedRInc::PassedRInc(const bool ct, WaitingList& q, unsigned vs): PassedList(ct), wqueue(q), nput(0)
{
    LtBytes::vsize = vs;
}

PWTStatus PassedRInc::put(const PWNode* n)
{
    nput++;

    PWTStatus r = PWT_NEW;
    bool add = true;

    const byte* nkey = n->discrete();
    map<const byte*, list<const RIncStorage*>, LtBytes>::iterator i = passed.lower_bound(nkey);

    list<const RIncStorage*>::iterator j;
    if (i != passed.end() && !passed.key_comp()(nkey, i->first))
    {
        // The key already exists
        delete [] nkey;

        j = i->second.begin(); 
        while (j != i->second.end() && (r == PWT_NEW || r == PWT_NEW_IN_TRACE))
        {
            if ((*j)->contains(n))
            {
                // n is contained in a previous state
                if (check_trace && n->has_in_trace((*j)->get_node()))
                {
                    r = PWT_IN_TRACE;
                } else {
                    r = PWT_IN_PASSED;
                }
                add = false;
                j++;
            } else if ((*j)->is_contained_in(n)) {
                if ((*j)->get_node() != NULL)
                {
                    wqueue.remove(const_cast<PWNode*>((*j)->get_node()));
                    if (check_trace && r != PWT_NEW_IN_TRACE && n->has_in_trace((*j)->get_node()))
                    {
                        r = PWT_NEW_IN_TRACE;
                    }
                }

                //(*j)->sticky = false;
                //(*j)->deallocate();
                delete *j;
                
                j = i->second.erase(j);
            } else {
                j++;
            }
        }
        
        if (add)
        {
            //n->sticky = true;
            i->second.push_back(n->rinc_storage()); // No previous sstate contains n
        }
    } else {
        //n->sticky = true;
        passed.insert(i, pair<const byte*, list<const RIncStorage*> >(nkey, list<const RIncStorage*>(1, n->rinc_storage())));
    }

    
    return r;
}


PassedRInc::~PassedRInc()
{
    map<const byte*, list<const RIncStorage*>, LtBytes>::iterator i;

    for (i = passed.begin(); i != passed.end(); i++)
    {
        delete [] i->first;
        list<const RIncStorage*>::iterator j;
        for (j = i->second.begin(); j != i->second.end(); j++)
        {
            delete *j;
        }
    }
}

void PassedRInc::info() const
{
    cout << "Number of nodes in passed list (markings): " << passed.size() << endl;
    cout << "Number of generated symbolic states: " << nput << endl;
}

// -----------------------------------------------------------------------------


WaitingList::WaitingList(const Job& j): restricter(NULL), job(j), es(j.es)
{
}

WaitingList::WaitingList(const Job& j, const expl_strategy ex): restricter(NULL), job(j), es(ex) 
{
}

WaitingList::~WaitingList()
{
}

// -----------------------------------------------------------------------------

SimpleWaitingList::SimpleWaitingList(const Job& j): WaitingList(j)
{
}

SimpleWaitingList::SimpleWaitingList(const Job& j, const expl_strategy ex): WaitingList(j, ex) 
{
}

PWNode* SimpleWaitingList::get()
{
    PWNode* s = NULL;
    
    if (!waiting.empty())
    { 
        if (es == ES_DF)
        {
            s = waiting.back();
            waiting.pop_back();
        } else {
            s = waiting.front();
            waiting.pop_front();
        }
    }
    
    return s;   
}

void SimpleWaitingList::remove(PWNode* n)
{
    waiting.remove(n);
}

void SimpleWaitingList::put(PWNode* n)
{
    waiting.push_back(n);
}

void SimpleWaitingList::add_restriction(const PResult& r)
{
    if (!r.universe())
    {
        if (job.restrict_update)
        {
            list<PWNode*>::iterator i;
            i = waiting.begin(); 
            while (i != waiting.end())
            {
                if ((*i)->restriction(r))
                {
                    (*i)->deallocate_();
                    i = waiting.erase(i);
                    Log.count("restricted");
                } else {
                    i++;
                }
            }
        } else {
            if (restricter == NULL)
                restricter = r.copy();
            else
                restricter->conjunction(r);
        }
    }
}

SimpleWaitingList::~SimpleWaitingList()
{
}

// -----------------------------------------------------------------------------

CostPriorityQueue::CostPriorityQueue(const Job& j): SimpleWaitingList(j)
{
}

PWNode* CostPriorityQueue::get()
{
    PWNode* s = NULL;
    
    if (!waiting.empty())
    { 
        s = waiting.front();
        waiting.pop_front();
    }
    
    return s;   
}

void CostPriorityQueue::put(PWNode* n)
{
    list<PWNode*>::const_iterator i = waiting.begin();

    while (i != waiting.end() && (*i)->cost_less_than(n))
    {
        i++;
    }
    
    waiting.insert(i, n);
}

// -----------------------------------------------------------------------------
