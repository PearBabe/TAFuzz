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

#include <bcvzone.hh>
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


BCVZone* BCVZone::init(const Job& job)
{
    return new BCVZone(job);
}

PWNode* romeo::BCVZone::successor(unsigned i)
{
    return new BCVZone(*this, i);
}

// Constructors
// Create an initial symbolic state 
BCVZone::BCVZone(const Job& job): VZone(job)
{
}

// Create the successor of state class S by its kth enabled transition
BCVZone::BCVZone(const BCVZone& S, unsigned k): VZone(S,k)
{
}

// Copy constructor
BCVZone::BCVZone(const BCVZone& S): VZone(S)
{   
}

BCVZone::BCVZone(const BCVZone& S, const Instruction& I): VZone(S,I)
{
}

PWNode* BCVZone::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new BCVZone(*this);
    } else {
        return new BCVZone(*this,*I);
    }
}

std::string BCVZone::to_string() const
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

BCVZone::~BCVZone()
{
}


// ------------------ control --------------------------------------------------

void BCVZone::set_winning(GraphNode* n, const bool w) const
{
    if (w)
    {
        n->winning.wc->add_reduce_max(*D);
    } 
}

void BCVZone::init_winning(GraphNode* n) const
{
    n->winning.wc = new CostDBMUnion(NE + 1);
}

void BCVZone::destroy_graph_payload(GraphNode& n) const
{
    delete n.winning.wc;
    n.winning.wc = nullptr;

    // Controllable and uncontrollable edges use mutually exclusive members
    // of pred.  Only uncontrollable edges also populate pred2.
    for (auto& edge: n.succs)
    {
        if ((edge.trans->control & CTRL_CONTROLLABLE) != 0)
        {
            delete edge.pred.wc;
            edge.pred.wc = nullptr;
        } else {
            delete edge.pred.wd;
            edge.pred.wd = nullptr;
            delete edge.pred2.wc;
            edge.pred2.wc = nullptr;
        }
    }
}

void BCVZone::init_propagation(GraphNode* n) const
{
    for (auto pred = n->preds.begin(); pred != n->preds.end(); ++pred)
    {
        for (auto edge = pred->node->succs.begin(); edge != pred->node->succs.end(); ++edge)
        {
            if (edge->node == n)
            {
                pred->node->set_outdated(*edge);
            }
        }
    }
}

PResult* BCVZone::update_result(const GraphNode* g, PResult* r) const
{
    static_cast<CostResult*>(r)->update(CostResult(-g->winning.wc->origin_cost()), false);
    return r;
}

bool BCVZone::has_winning(const GraphNode* g) const
{
    return !g->winning.wc->empty();
}

bool BCVZone::update_reach(GraphNode* n) const
{
    const cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

    list<SuccInfo>::iterator it;

    CostDBMUnion Good(NE + 1); 
    CostDBMUnion UGood(NE + 1); 
    DBMUnion Bad(NE + 1);

    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const unsigned int ctrl_flags = it->trans->control;
        const BCVZone* s = dynamic_cast<const BCVZone*>(it->node->get_state());
        if (s == nullptr)
        {
            throw logic_error("BCVZone graph edge targets a non-BCVZone state");
        }

        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            if (!it->up_to_date)
            {
                if (it->pred.wc != NULL)
                {
                    delete it->pred.wc;
                }

                it->pred.wc = new CostDBMUnion(this->predecessor(s, *it->node->winning.wc, it->trans));
                n->set_uptodate(*it);
            }

            //cout << "Pred by " << it->trans->label << endl;
            //cout << it->pred.wc->to_string() << endl;

            Good.add_reduce_max(*it->pred.wc);
        } else {
            if (!it->up_to_date)
            {
                if (it->pred2.wc != NULL)
                {
                    delete it->pred2.wc;
                }

                if (it->pred.wd != NULL)
                {
                    delete it->pred.wd;
                }

                it->pred2.wc = new CostDBMUnion(this->predecessor(s, *it->node->winning.wc, it->trans));

                DBMUnion LoseSucc(it->node->winning.wc->uncost().complement());
                LoseSucc.intersection_assign(*s->D);
                it->pred.wd = new DBMUnion(this->VZone::predecessor(s, LoseSucc, it->trans, false));
                
                n->set_uptodate(*it);
            }

            Bad.add_reduce(*it->pred.wd);
            UGood = UGood.min(*it->pred2.wc);
        }
    }

    //cout << "Good:" << endl << Good.to_string() << endl << endl;
    //cout << "UGood:" << endl << UGood.to_string() << endl << endl;
    //cout << "Bad:" << endl << Bad.to_string() << endl << endl;
    //cout << "RGood:" << endl << Good.to_string() << endl << endl;


    //cout << "-------------------------------------------------------------------" << endl;
    CostDBMUnion Winning1(Good.predt_max(Bad, c));
    Winning1.restriction_assign_max(*D);
    //cout << "Winning1" << endl << Winning1.to_string() << endl;

    CostDBMUnion Winning2(UGood.predt_min(Good.uncost(), c));
    Winning2.add_reduce_min(UGood);
    Winning2.restriction_assign_max(Winning1.uncost());
    //cout << "Winning2" << endl << Winning2.to_string() << endl;
    
    CostDBMUnion NewWinning = Winning1.maxmapmin(Winning2);
    //CostDBMUnion NewWinning = Winning1;
    //cout << "NewWinning:" << endl << NewWinning.to_string() << endl << endl;
    //cout << "OldWinning:" << endl << n->winning.wc->to_string() << endl << endl;

    //if (!n->winning.wc->exact_contains(NewWinning))
    bool result = false;
    if (!n->winning.wc->subsumes_max(NewWinning))
    {
        //cout << "   bigger" << endl;
        n->winning.wc->add_reduce_max(NewWinning);

        //if (!job.notrace)
        //{
        //    CostDBMUnion NotBad(Bad.complement());
        //    n->clear_strategy(WSET_CDBM);
        //    for (it = n->succs.begin(); it != n->succs.end(); it++)
        //    {
        //        const unsigned int ctrl_flags = it->trans->control;
        //        if (ctrl_flags & CTRL_CONTROLLABLE)
        //        {
        //            LocalStrategy st;
        //            st.action = it->trans;
        //            st.en = new const Transition*[NE];
        //            memcpy(st.en, en, NE*sizeof(Transition*));
        //            st.domain.wc = new CostDBMUnion(*it->pred.wc);
        //            st.domain.wc->intersection_assign(NotBad);
        //            //st.domain.wc->reduce();
        //            add_local_strategy(WSET_CDBM, n->strategy, st);
        //        }
        //    }

        //    LocalStrategy wait;
        //    wait.action = NULL;
        //    wait.en = new const Transition*[NE];
        //    memcpy(wait.en, en, NE*sizeof(Transition*));
        //    wait.domain.wc = new CostDBMUnion(NewWinning);
        //    add_local_strategy(WSET_CDBM, n->strategy, wait);
        //}

        //n->losing.wc = NewWinning.complement();
        result = true;
    }

    return result;
}

bool BCVZone::update_safe(GraphNode* n) const
{
    return false;
}

CostDBMUnion BCVZone::predecessor(const BCVZone* succ, const CostDBMUnion& S, const Transition* tf) const
{
    const unsigned dim = NE + 1;
    const unsigned sdim = succ->NE + 1;

    if (S.dimension() != sdim)
    {
        throw logic_error("BCVZone predecessor received a weighted zone with the wrong dimension");
    }

    vector<unsigned> indices(sdim);
    vector<unsigned> rindices(dim, sdim);

    const Transition* const* fired = find(en, en + NE, tf);
    if (fired == en + NE)
    {
        throw logic_error("BCVZone predecessor cannot find the fired transition");
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
    R.restriction_assign_eq(*D);

    // Apply the guard
    // tf is firable
    R.constrain(0, f + 1, tf->timing->dbm_lower_bound(V, job.cts.statics));

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

    const cvalue edge_cost = tf->get_cost(V, job.cts.statics, job.non_negative_costs);
    if (edge_cost != 0)
    {
        R.add_cost(-edge_cost);
    }

    return R;
}

void BCVZone::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wc->add_reduce_max(*x->winning.wc);
}

PassedGN* BCVZone::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    return new PassedGNInc(WSET_CDBM, job.cts.variables.vstate_size(), F, B);
}

// -----------------------------------------------------------------------------
