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

#include <vsspoly.hh>
#include <polyhedron.hh>
#include <result.hh>
#include <linear_expression.hh>
#include <dbm.hh>
#include <graph_node.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

// Constructors
VSSPoly::VSSPoly(const Job& job): VSState(job), D(new Polyhedron(NE+job.cts.nparams(),true))
{
}

VSSPoly::VSSPoly(const VSSPoly& S, unsigned k): VSState(S,*S.en[k]), D(new Polyhedron(*S.D))
{
}

VSSPoly::VSSPoly(const VSSPoly& S): VSState(S), D(new Polyhedron(*S.D))
{
}

VSSPoly::VSSPoly(const VSSPoly& S, const Instruction& I): VSState(S,I)
{
}

void VSSPoly::remap(const VSSPoly& S, unsigned k, unsigned indices[], unsigned S_indices[], unsigned costvar)
{
    const unsigned NP = job.cts.nparams();

    // Do not move parameters around
    for (unsigned i=0; i<NP; i++)
    {
        indices[i] = i;
        S_indices[i] = i;
    }

    const VSSPoly* Sp = static_cast<const VSSPoly*>(S.parent);
    if (k == S.NE && Sp != NULL)
    {
        // S_indices maps transitions of S to those of its parent
        S.map_indices(*Sp, S.in, S_indices, NP);
        if (costvar > 0)
        {
            for (unsigned i = 0; i < S.NE + NP; i++)
            {
                if (S_indices[i] == Sp->NE + NP)
                {
                    S_indices[i] += costvar;
                }
            }
            S_indices[S.NE + NP] = Sp->NE + NP;
        }
    }

    // Map starting from the transition dimensions
    // indices maps transitions of this to those of its parent S
    if (k == S.NE)
    {
        map_indices(S, indices, NP);
    } else {
        map_indices(S, S.en[k], indices, NP);
    }

    if (costvar > 0)
    {
        for (unsigned i = 0; i < NE + NP; i++)
        {
            if (indices[i] == S.NE + NP)
            {
                indices[i] += costvar;
            }
        }
        indices[NE + NP] = S.NE + NP;
    }

    D->remap(indices, NP + NE + costvar);
}

std::string VSSPoly::to_string() const
{
    stringstream domain;
    domain << VSState::to_string() << endl;

    const unsigned NP = job.cts.nparams();

    vector<string> labels;
    for (list<Parameter>::const_iterator k=job.cts.begin_parameters(); k != job.cts.end_parameters(); k++)
    {
        cvalue v;
        if (!k->constant(v))
        {
            labels.push_back(k->label);
        }
    }
    
    for (unsigned k=0; k<NE; k++)
    {
        labels.push_back(en[k]->label);
    }

    domain << D->to_string_labels(labels,NP);

    return domain.str();
}

bool VSSPoly::key_less(const PWNode* S) const
{
    return VSState::key_less(S);
}

bool VSSPoly::equals(const PWNode* S) const
{
    return VSState::equals(S) && (convergence_domain() == (static_cast<const VSSPoly*>(S)->convergence_domain()));
}

bool VSSPoly::contains(const PWNode* S) const
{
    return VSState::equals(S) && (convergence_domain().contains((static_cast<const VSSPoly*>(S)->convergence_domain())));
}


PWTRel VSSPoly::compare(const PWNode* S) const
{
    PWTRel r = VSState::compare(S);
    if (r == PWT_EQ)
    {
        if (static_cast<const VSSPoly*>(S)->convergence_domain().contains(convergence_domain()))
        {
            if (!convergence_domain().contains(static_cast<const VSSPoly*>(S)->convergence_domain()))
                r = PWT_INC;
        } else
            r = PWT_DIFF;
    } 

    return r;
}

bool romeo::VSSPoly::empty() const
{
    return D->empty();
}

Polyhedron VSSPoly::convergence_domain() const
{
    return *D;
}

Polyhedron* VSSPoly::domain() const
{
    return D;
}

Key VSSPoly::get_abstracted_key(bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    const unsigned size = discrete_size() + (NE + 1) * (NE + 1) * sizeof(time_bound);
    byte* key = new byte[size];
    memcpy(key, V, job.cts.variables.vstate_size()*sizeof(byte));

    DBM dbm = D->abstract_parameters(D->dimension() - NE, lbs, ubs, lbounds, ubounds);
    dbm.copy_matrix(key + discrete_size());
    
    return Key(size, key);
}

VSSPoly::~VSSPoly()
{
    delete D;
}


// ------------------ control --------------------------------------------------
void VSSPoly::set_winning(GraphNode* n, const bool w) const
{
    if (w)
    {
        n->winning.wp->add_reduce(*D);
    }
}

void VSSPoly::init_winning(GraphNode* n) const
{
    n->winning.wp = new Polyhedron(D->dimension(), false);
}

void VSSPoly::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wp->add(*x->winning.wp);
}

bool VSSPoly::has_winning(const GraphNode* g) const
{
    return !g->winning.wp->empty();
}

PassedGN* VSSPoly::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    if (job.pw == PASSED_EQ)
    {
        return new PassedGNEqNC(WSET_POLY, job.cts.variables.vstate_size(), F, B);
    } else {
        return new PassedGNInc(WSET_POLY, job.cts.variables.vstate_size(), F, B);
    }
}

bool romeo::VSSPoly::safety_control_bad_state() const
{
     return false;
}
// ------------------------- storage -------------------------------------------

PassedList* VSSPoly::init_passed(WaitingList& w, unsigned vs, bool b) const
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
//
// .............................................................................

bool VSSPolyMergeStorage::addr(const PWNode* s, const PResult* R)
{
    const VSSPoly * n = static_cast<const VSSPoly*>(s);
    const Polyhedron& nD = *n->D;
    const Polyhedron& nCD = n->convergence_domain();

    bool res = !D->contains(nCD);

    if (res)
    {
        if (R != nullptr)
        {
            // If the (convergence) domain of s is not included in D, 
            // we further test if there are some parameter valuations 
            // not already in the result (restrict_new mode) for which the
            // future is not included here
            const PRPoly& c = static_cast<const PRPoly&>(*R);
            Polyhedron C(c.val);
            C.add_dimensions(D->dimension() - C.dimension());
            C.intersection_assign(nCD);

            res = !D->contains(C);
            Log.count("addr");
        } 

        if (s->job.pw_reduce)
        {
            D->add_reduce(nD);
        } else {
            D->add(nD);
        }
    }

    return res;
}

unsigned VSSPolyMergeStorage::size() const
{
    return D->size();
}

VSSPolyMergeStorage::VSSPolyMergeStorage(const VSSPoly* s): VSStateMergeStorage(s), D(new Polyhedron(*s->D))
{
}

VSSPolyMergeStorage::~VSSPolyMergeStorage()
{
    delete D;
}

// .............................................................................

bool VSSPolyRIncStorage::contains(const PWNode* s) const
{
    const VSSPoly * n = static_cast<const VSSPoly*>(s);
    return D->contains(n->convergence_domain());
}

bool VSSPolyRIncStorage::is_contained_in(const PWNode* s) const
{
    const VSSPoly * n = static_cast<const VSSPoly*>(s);
    return n->convergence_domain().contains(*D);
}

VSSPolyRIncStorage::VSSPolyRIncStorage(const VSSPoly* s): VSStateRIncStorage(s), D(new Polyhedron(s->convergence_domain()))
{
}

VSSPolyRIncStorage::~VSSPolyRIncStorage()
{
    delete D;
}

// .............................................................................

bool VSSPolyCostStorage::contains(const PWNode* s) const
{
    return VSSPolyRIncStorage::contains(s) && (cost <= s->min_cost());
}

bool VSSPolyCostStorage::is_contained_in(const PWNode* s) const
{
    return VSSPolyRIncStorage::is_contained_in(s) && (cost >= s->min_cost());
}

VSSPolyCostStorage::VSSPolyCostStorage(const VSSPoly* s): VSSPolyRIncStorage(s), cost(s->min_cost())
{
}

VSSPolyCostStorage::~VSSPolyCostStorage()
{
}


// .............................................................................

EqStorage* VSSPoly::eq_storage() const
{
    cerr << error_tag(color_output) << "Equality convergence not available with polyhedra" << endl;
    exit(1);
}

RIncStorage* VSSPoly::rinc_storage() const
{
    if (!job.hpeu)
    {
        return new VSStateCostStorage(this);
    } else {
        return new VSSPolyRIncStorage(this);
    }
}

MergeStorage* VSSPoly::merge_storage() const
{
    return new VSSPolyMergeStorage(this);
}



