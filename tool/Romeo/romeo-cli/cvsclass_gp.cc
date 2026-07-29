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
#include <vector>
#include <list>

#include <color_output.hh>
#include <job.hh>
#include <vsclass.hh>
#include <cvsclass_gp.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <rvalue.hh>
#include <time_interval.hh>

using namespace std;
using namespace romeo;

CVSClassG* CVSClassG::init(const Job& job)
{
    return new CVSClassG(job);
}

PWNode* romeo::CVSClassG::successor(unsigned i)
{
    return new CVSClassG(*this, i);
}

CVSClassG::CVSClassG(const Job& j): VSClass(j), gsched(1)
{
    gen = new unsigned[NE];
    for (unsigned i = 0; i < NE; i++)
    {
        gen[i] = 0;
    }
}

CVSClassG::CVSClassG(const CVSClassG& S): VSClass(S), gsched(S.gsched), obj(S.obj), cmin(S.cmin)
{
    gen = new unsigned[NE];
    for (unsigned i = 0; i < NE; i++)
    {
        gen[i] = S.gen[i];
    }
}

CVSClassG::CVSClassG(const CVSClassG& S, unsigned k): VSClass(S,k), gsched(S.gsched)
{
    const unsigned size = NE +1;
    const unsigned old_size = S.NE +1;
    const unsigned curidx = steps;
    const Transition* f = S.en[k];

    const cvalue c = job.cts.cost_rate(S.V, job.non_negative_costs);

    // Update the objective
    obj = S.obj + c * (Var(curidx) - Var(curidx > 0? curidx - 1: 0));

    unsigned indices[size];
    // The reference clock does not move
    indices[0] = 0;
    map_indices(S, f, indices,1);


    // Find who last enabled the current enabled transitions
    gen = new unsigned[NE];
    for (unsigned i = 0; i < NE; i++)
    {
        if (indices[i+1] < old_size)
        {
            gen[i] = S.gen[indices[i+1]-1];
        } else {
            gen[i] = this->steps;
        }
    }

    // Add the new constraints
    gsched.inc_size();
    // t_{i-1} <= t_i
    gsched.constrain(curidx - 1, curidx, time_bound::zero);

    // find the transition t_e that enabled t_i
    const unsigned eidx = S.gen[k];

    // t_i is >= t_e + Is(t_i)
    gsched.constrain(eidx, curidx, f->timing->dbm_lower_bound(S.V, job.cts.statics));

    // t_i fires before other enabled transitions t_j and before its own
    // upper bound
    // t_i <= gen(t_j) + Is(t_j)

    for (unsigned j = 0; j < S.NE; j++)
    {
        const unsigned jidx = S.gen[j];
        const Transition* tj = S.en[j];
        gsched.constrain(curidx, jidx, tj->timing->dbm_upper_bound(S.V, job.cts.statics));
    }

    // compute the cost by global optimization
    cmin = gsched.min(obj);
}

CVSClassG::CVSClassG(const CVSClassG& S, const Instruction& I): VSClass(S,I), gsched(S.gsched), obj(S.obj), cmin(S.cmin)
{
}

Avalue CVSClassG::min_cost() const
{
    return cmin + Avalue(accum_cost);
    //if (minc.cst_bounded())
    //    return accum_cost + time_bound(minc.const_term(), minc.cst_strict()? ROMEO_DBM_STRICT: ROMEO_DBM_NON_STRICT);
    //else
    //    return accum_cost + time_bound::minus_infinity;
}

std::string CVSClassG::to_string() const
{

    stringstream domain;
    domain << VSClass::to_string() << endl;
    
    domain << endl;

    cvalue c = (job.cts.cost.is_null() ? 0 : job.cts.cost.evaluate(V, job.cts.statics).to_int());

    domain << "local cost = " << c << endl;
    domain << "mincost = "; 

    const Avalue minc = min_cost();
    
    domain << minc;

    return domain.str();
}

void CVSClassG::set_fired_date(const LExpression* e, const cvalue q)
{
    if (e != NULL)
    {
        const value v = SExpression(e).evaluate(V, job.cts.statics).to_int();
        const time_bound u(v);
        const time_bound l(-v);

        gsched.constrain(steps, steps - 1, u);
        gsched.constrain(steps - 1, steps, l);
    }
}

PWNode* CVSClassG::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new CVSClassG(*this);
    } else {
        return new CVSClassG(*this,*I);
    }
}

void CVSClassG::minvals(std::vector<Avalue>& V) const
{
    // Warning: ignores the denominator!
    cvalue C[gsched.dimension()];
    obj.coefficients(gsched.dimension(), C);
    gsched.min(C, V);
}

CVSClassG::~CVSClassG()
{
}

