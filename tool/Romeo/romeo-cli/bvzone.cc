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
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <iostream>
#include <vector>

#include <bvzone.hh>
#include <vsclass.hh>
#include <timebounds.hh>
#include <cost_dbm.hh>
#include <time_interval.hh>
#include <dresult.hh>
#include <property.hh>
#include <color_output.hh>

#include <rvalue.hh>

#include <graph_node.hh>

using namespace std;
using namespace romeo;

#include <logger.hh> 
extern romeo::Logger Log;


BVZone* BVZone::init(const Job& job)
{
    return new BVZone(job);
}

PWNode* romeo::BVZone::successor(unsigned i)
{
    return new BVZone(*this, i);
}

// Constructors
// Create an initial symbolic state 
BVZone::BVZone(const Job& job): VZone(job), offset_cost(0), cost_rates(new value[NE])
{
    const value c = !job.non_negative_costs ? 0
                    : job.cts.cost_rate(V, job.non_negative_costs);

    for (unsigned i = 0; i < NE; i++)
    {
        cost_rates[i] = c;
    }
}

// Create the successor of state class S by its kth enabled transition
BVZone::BVZone(const BVZone& S, unsigned k): VZone(S,k), offset_cost(S.offset_cost), cost_rates(new value[NE])
{
    const Transition& tf = *S.en[k];

    const unsigned size = NE+1;
    const unsigned old_size = S.NE+1;

    // Apply the guard (duplicated from VZone)
    DBM C(*S.D);
    C.constrain(0, k + 1, tf.timing->dbm_lower_bound(S.V, job.cts.statics));

    //Avalue m = Avalue::infinity;
    Avalue m = 0;
    for (unsigned i = 1; i < old_size; i++)
    {
        const Avalue x = (*S.D)(0, i);
        const Avalue y = C(0, i);

        m = max(m, (x - y) * S.cost_rates[i - 1]);
    }

    offset_cost = offset_cost + m;

    const value c = !job.non_negative_costs ? 0
                    : job.cts.cost_rate(V, job.non_negative_costs);

    unsigned indices[size];
    
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, &tf, indices, 1);
 
    for (unsigned i = 1; i < size; i++)
    {
        if (indices[i] == old_size)
        {
            cost_rates[i - 1] = c;
        } else {
            if (C(indices[i], 0) == time_bound::zero)
            {
                cost_rates[i - 1] = c;
            } else {
                cost_rates[i - 1] = min(c, S.cost_rates[indices[i] - 1]);
            }
        }
    }
}

// Copy constructor
BVZone::BVZone(const BVZone& S): VZone(S), offset_cost(S.offset_cost), cost_rates(new value[S.NE])
{   
    for (unsigned i = 0; i < S.NE ; i++)
    {
        cost_rates[i] = S.cost_rates[i];
    }
}

BVZone::BVZone(const BVZone& S, const Instruction& I): VZone(S,I), offset_cost(S.offset_cost), cost_rates(new value[NE]())
{
    // These rates are used only by the disabled forward-cost pruning heuristic.
    // Zero is a sound lower bound for the supported non-negative mode and avoids
    // reading uninitialised memory after observer/utility instructions.
}

PWNode* BVZone::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new BVZone(*this);
    } else {
        return new BVZone(*this,*I);
    }
}

std::string BVZone::to_string() const
{
    stringstream domain;
    domain << VSState::to_string() << endl;
    const value c = job.cts.cost_rate(V, job.non_negative_costs);
    domain << "local cost: " << c << endl;
    domain << "cost underapproximation: " << offset_cost << endl;
    domain << "cost u. rates: " << endl;
    for (unsigned i = 0; i < NE; i++)
    {
        domain << cost_rates[i] << " ";
    }
    domain << endl;

    vector<string> labels;
    labels.push_back("0");
    for (unsigned i=0; i<NE; i++)
        labels.push_back(en[i]->label);

    domain << D->to_string_labels(labels);

    return domain.str();
}

BVZone::~BVZone()
{
    delete[] cost_rates;
}


// ------------------ control --------------------------------------------------

void BVZone::set_winning(GraphNode* n, const bool w) const
{
    if (w)
    {
        n->winning.wc->add_reduce_max(*D);
    }
}

void BVZone::init_propagation(GraphNode* n) const
{
    for (auto itp = n->preds.begin(); itp != n->preds.end(); itp++)
    {
        GraphNode* g = itp->node;
 
        for (auto it = g->succs.begin(); it != g->succs.end(); it++)
        {
            if (it->node == n)
            {
                if (it->delta.wc == nullptr)
                {
                    it->delta.wc = new CostDBMUnion(*n->winning.wc);
                } else {
                    it->delta.wc->add_reduce_max(*n->winning.wc);
                }
            }
        }
    }
}

void BVZone::init_winning(GraphNode* n) const
{
    n->winning.wc = new CostDBMUnion(NE + 1);
}

void BVZone::destroy_graph_payload(GraphNode& n) const
{
    delete n.winning.wc;
    n.winning.wc = nullptr;

    // The backward reachability variant exclusively uses the delta member on
    // each edge; pred/pred2 and tgt belong to other graph algorithms.
    for (auto& edge: n.succs)
    {
        delete edge.delta.wc;
        edge.delta.wc = nullptr;
    }
}

void BVZone::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wc->add(*x->winning.wc);
}


PResult* BVZone::update_result(const GraphNode* g, PResult* r) const
{
    static_cast<CostResult*>(r)->update(CostResult(-g->winning.wc->origin_cost()), false);
    return r;
}

bool BVZone::has_winning(const GraphNode* g) const
{
    return !g->winning.wc->empty();
}

//bool BVZone::update_reach(GraphNode* n) const
//{
//    const cvalue c = (job.cts.cost == NULL ? 0 : job.cts.cost->evaluate(V, job.cts.statics).to_int());
//
//    list<SuccInfo>::iterator it;
//
//    //CostDBMUnion Good(*n->winning.wc);
//    CostDBMUnion Good;
//
//    for (it = n->succs.begin(); it != n->succs.end(); it++)
//    {
//        const BVZone* s = static_cast<const BVZone*>(it->node->get_state());
//
//        if (!it->up_to_date)
//        {
//            if (it->pred.wc != NULL)
//            {
//                delete it->pred.wc;
//            }
//
//            it->pred.wc = new CostDBMUnion(this->predecessor(s, *it->node->winning.wc, it->trans));
//            n->set_uptodate(*it);
//            //cout << "pred" << endl << it->pred.wc->to_string() << endl;
//            //Good.add(it->pred.wc->past_max(c));
//        }
//        Good.add_reduce_max(it->pred.wc->past_max(c));
//        
//
//    }
//
//    //cout << "Good:" << endl << Good.to_string() << endl << endl;
//
//
//    bool result = false;
//    if (!n->winning.wc->subsumes_max(Good))
//    {
//        n->winning.wc->clear();
//        *n->winning.wc = Good;
//
//        result = true;
//    }
//
//    return result;
//}

bool BVZone::update_reach(GraphNode* n) const
{
    Log.start("update_reach");
    const cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

    list<SuccInfo>::iterator it;

    CostDBMUnion Good(NE + 1);
    CostDBMUnion G(NE + 1);

    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const BVZone* s = dynamic_cast<const BVZone*>(it->node->get_state());
        if (s == nullptr)
        {
            throw logic_error("BVZone graph edge targets a non-BVZone state");
        }

        if (it->delta.wc != nullptr)
        {
            Log.start("ur1_Pred");
            CostDBMUnion Pred(this->predecessor(s, *it->delta.wc, it->trans));
            Log.stop("ur1_Pred");
            Log.start("ur2_Past");
            CostDBMUnion PastPred(Pred.past_max(c));
            Log.stop("ur2_Past");
            Log.start("ur3_Add pred");
            G.add_reduce_max(PastPred);
            Log.stop("ur3_Add pred");

            delete it->delta.wc;
            it->delta.wc = nullptr;
        } else {
            Log.count("edge not updated");
        }
        

    }
    Log.start("ur4_Good");
    n->winning.wc->add_reduce_max_delta(Good, G);
    Log.stop("ur4_Good");

    //cout << "Good:" << endl << Good.to_string() << endl << endl;


    //cout << "NewWinning:" << endl << Good.to_string() << endl << endl;
    //cout << "OldWinning:" << endl << n->winning.wc->to_string() << endl << endl;

    //if (!n->winning.wc->exact_contains(NewWinning))
    bool result = false;
    if (!Good.empty())
    {
        for (auto itp = n->preds.begin(); itp != n->preds.end(); itp++)
        {
            GraphNode* g = itp->node;

            for (it = g->succs.begin(); it != g->succs.end(); it++)
            {
                if (it->node == n)
                {
                    if (it->delta.wc == nullptr)
                    {
                        it->delta.wc = new CostDBMUnion(Good);
                    } else {
                        it->delta.wc->add_reduce_max(Good);
                    }
                }
            }

        }

        result = true;
    }

    Log.stop("update_reach");
    return result;
}

bool BVZone::update_safe(GraphNode* n) const
{
    return false;
}

CostDBMUnion BVZone::predecessor(const BVZone* succ, const CostDBMUnion& S, const Transition* tf) const
{
    const unsigned dim = NE + 1;
    const unsigned sdim = succ->NE + 1;

    if (S.dimension() != sdim)
    {
        throw logic_error("BVZone predecessor received a weighted zone with the wrong dimension");
    }

    vector<unsigned> indices(sdim);
    vector<unsigned> rindices(dim, sdim);

    const Transition* const* fired = find(en, en + NE, tf);
    if (fired == en + NE)
    {
        throw logic_error("BVZone predecessor cannot find the fired transition");
    }
    const unsigned f = static_cast<unsigned>(fired - en);

    // Map starting from the transition dimensions
    indices[0] = 0;
    succ->map_indices(*this, tf, indices.data(), 1);

    rindices[0] = 0; // the ref clock does not move
    CostDBMUnion R(S);
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
    R.remap(rindices.data(), dim);

    R.restriction_assign(*D);

    // Apply the guard
    // tf is firable
    R.constrain(0, f + 1, tf->timing->dbm_lower_bound(V, job.cts.statics));

    for (unsigned j = 0; j < NE; j++)
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

    const cvalue edge_cost = tf->get_cost(V, job.cts.statics, job.non_negative_costs);
    if (edge_cost != 0)
    {
        R.add_cost(-edge_cost);
    }

    //R = R.reduce_max();

    return R;
}

PassedGN* BVZone::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    return new PassedGNInc(WSET_CDBM, job.cts.variables.vstate_size(), F, B);
    //return new PassedGNEq(WSET_CDBM, job.cts.variables.vstate_size(), F, B);
}

Avalue BVZone::get_offset_cost() const
{
    return offset_cost;
}

// -----------------------------------------------------------------------------
