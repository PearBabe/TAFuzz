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

#include <iostream>
#include <sstream>
#include <cmath>
#include <climits>

#include <vsclass.hh>
#include <vscpoly_costs.hh>
#include <vscpoly.hh>
#include <polyhedron.hh>
#include <linear_expression.hh>
#include <vscpar.hh>
#include <result.hh>
#include <property.hh>

#include <time_interval.hh>

#include <rvalue.hh>
#include <lexpression.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

// Constructors
CVSCPoly::CVSCPoly(const Job& job): VSCPoly(job), cmin(0)
{
}

CVSCPoly* CVSCPoly::init(const Job& job)
{
    const unsigned NP = job.cts.nparams();

    CVSCPoly* R = new CVSCPoly(job);
    R->init_constraints();

    // Add a dimension for the cost
    R->D->add_dimensions(1);

    // Constrain that variable to >= 0
    R->D->constrain(Var(NP + R->NE), CSTR_GWEAK);

    return R;
}


CVSCPoly::CVSCPoly(const CVSCPoly& S, unsigned k): VSCPoly(S,k), cmin(S.cmin)
{
}

CVSCPoly::CVSCPoly(const CVSCPoly& S): VSCPoly(S), cmin(S.cmin)
{
}

PWNode* CVSCPoly::copy(const Instruction* I) const
{
    if (I == NULL)
        return new CVSCPoly(*this);
    else
    {
        const unsigned NP = job.cts.nparams();
        CVSCPoly* s = new CVSCPoly(*this, *I);

        unsigned S_indices[NE + NP + 1];
        unsigned indices[s->NE + NP + 1];
        
        // The cost is always the last variable
        indices[s->NE + NP] = NE + NP;

        const CVSCPoly* Sp = static_cast<const CVSCPoly*>(parent);
        if (Sp != NULL)
            S_indices[NE + NP] = Sp->NE + NP;

        s->remap(*this, NE, indices, S_indices, 1);
        s->constrain_new(*this, NE, indices, S_indices);

        return s;
    }
}

PWNode* CVSCPoly::successor(unsigned i)
{
    const unsigned NP = job.cts.nparams();

    CVSCPoly* R = new CVSCPoly(*this, i);

    R->firability_constraints(*this, i);
    R->time_elapsing(*this, i);

    // The local cost
    const cvalue c = job.cts.cost_rate(V, job.non_negative_costs);

    // The cost variable
    const Var vc(NP + NE);
    // The fired variable
    const Var vf(NP + i);

    // The new cost expression
    // update cost
    const value dc = en[i]->get_cost(V, job.cts.statics, job.non_negative_costs);

    const LinearExpression expr = vc + c*vf + dc ;

    // Variable change
    R->D->affine_image(vc, expr, 1);

    unsigned S_indices[NE + NP + 1]; // +1 for the cost
    unsigned indices[R->NE + NP + 1];
    
    // The cost is always the last variable
    indices[R->NE + NP] = NE + NP;

    R->remap(*this, i, indices, S_indices, 1);
    R->constrain_new(*this, i, indices, S_indices);

    // Abstract away the max value of cost: no need since c >= 0  (not == 0) from the beginning
    //cvalue future_rates[R->NE + NP + 1]; 
    //for (unsigned i=0; i < R->NE + NP; i++)
    //{
    //    future_rates[i] = 0;
    //}
    //future_rates[R->NE + NP] = 1;
    //R->D->future_assign(future_rates);

    if (job.computation_mode == TIMED_PARAMETRIC && !job.no_abstract)
        R->time_saturation();

    R->cmin = R->D->minimize(Var(R->NE + NP));

    return R;
}

CVSCPoly::CVSCPoly(const CVSCPoly& S, const Instruction& I): VSCPoly(S,I), cmin(S.cmin)
{   
    this->D = new Polyhedron(*S.D);
}

//Polyhedron CVSCPoly::convergence_domain() const
//{
//    const unsigned NP = job.cts.nparams();
//
//    Polyhedron R(*D);
//    R.remove_higher_dimensions(NP + NE);
//    return R;
//}

std::string CVSCPoly::to_string() const
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

Avalue CVSCPoly::min_cost() const
{
    return cmin;
}
