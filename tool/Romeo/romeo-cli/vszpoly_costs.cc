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

#include <sstream>
#include <cmath>
#include <climits>

#include <color_output.hh>
#include <vszpoly_costs.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <result.hh>
#include <dresult.hh>
#include <property.hh>
#include <lexpression.hh>
#include <rvalue.hh>
#include <time_interval.hh>

#include <graph_node.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

// Constructors
CVSZPoly::CVSZPoly(const Job& job): VSZPoly(job), cmin(0) 
{
}

CVSZPoly* CVSZPoly::init(const Job& job)
{
    const unsigned NP = job.cts.nparams();

    CVSZPoly* R = new CVSZPoly(job);

    // Add a dimension for the cost
    R->D->add_dimensions(1);

    // Constrain that variable to >= 0
    R->D->constrain(Var(NP + R->NE), CSTR_GWEAK);
    R->init_constraints();
    
    return R;
}

CVSZPoly::CVSZPoly(const CVSZPoly& S, unsigned k): VSZPoly(S,k), cmin(S.cmin)
{
}

CVSZPoly::CVSZPoly(const CVSZPoly& S): VSZPoly(S), cmin(S.cmin)
{
}

PWNode* CVSZPoly::copy(const Instruction* I) const
{
    const unsigned NP = job.cts.nparams();
    
    if (I == NULL)
    {
        return new CVSZPoly(*this);
    } else {
        CVSZPoly* s = new CVSZPoly(*this, *I);

        unsigned S_indices[NE + NP + 1];
        unsigned indices[s->NE + NP + 1];
        
        // The cost is always the last variable
        indices[s->NE + NP] = NE + NP;

        const CVSZPoly* Sp = static_cast<const CVSZPoly*>(parent);
        if (Sp != NULL)
            S_indices[NE + NP] = Sp->NE + NP;

        s->remap(*this, NE, indices, S_indices, 1);
        s->constrain_new(*this, NE, indices, S_indices, 1);
        
        return s;
    }
}

PWNode* CVSZPoly::successor(unsigned i)
{
    const unsigned NP = job.cts.nparams();

    CVSZPoly* R = new CVSZPoly(*this, i);
    R->succ_constraints(*this, i);

    unsigned S_indices[NE + NP + 1]; // +1 for the cost
    unsigned indices[R->NE + NP + 1];
    
    R->remap(*this, i, indices, S_indices, 1);
    R->constrain_new(*this, i, indices, S_indices, 1);

    R->cmin = R->D->minimize(Var(R->NE + NP));

    return R;
}

CVSZPoly::CVSZPoly(const CVSZPoly& S, const Instruction& I): VSZPoly(S,I), cmin(S.cmin)
{   
    this->D = new Polyhedron(*S.D);
}

std::string CVSZPoly::to_string() const
{
    stringstream domain;
    domain << VSState::to_string() << endl;

    const unsigned NP = job.cts.nparams();

    vector<string> labels;
    for (list<Parameter>::const_iterator k=job.cts.begin_parameters(); k != job.cts.end_parameters(); k++)
    {
        cvalue v;
        if (!k->constant(v))
            labels.push_back(k->label);
    }
    
    for (unsigned k=0; k<NE; k++)
    {
        labels.push_back(en[k]->label);
    }

    labels.push_back("#cost");
    domain << D->to_string_labels(labels,NP);

    return domain.str();
}

Avalue CVSZPoly::min_cost() const
{
    return cmin;
}
// ------------------ control --------------------------------------------------
void CVSZPoly::set_winning(GraphNode* n, const bool w) const
{
    const unsigned NP = job.cts.nparams();
    if (w)
    {
        n->winning.wp->add_reduce(*D);
        n->winning.wp->constrain(Var(NP+NE), CSTR_GWEAK);
    }
}

PResult* CVSZPoly::update_result(const GraphNode* g, PResult* r) const
{
    const unsigned NP = job.cts.nparams();

    // Constrain all clocks to 0 to obtain the initial state
    Polyhedron C(*g->winning.wp);
    for (unsigned i = NP; i < NP + NE; i++)
    {
        C.constrain(Var(i), CSTR_LWEAK);
    }

    // Take the minimum winning cost in the result
    Avalue mc = C.minimize(Var(NP + NE));
    
    static_cast<CostResult*>(r)->update(CostResult(mc), false);
    return r;
}

Polyhedron CVSZPoly::predecessor(const VSZPoly* succ, const Polyhedron& S, const Transition* tf, bool forced) const
{
    return pred(succ, S, tf, 1, forced);
}

Avalue CVSZPoly::backward_cost_heuristic() const
{
    // By default when going backward for control we try to get to the initial
    // state as fast as possible, so favor the shortest history
    return steps;
}

