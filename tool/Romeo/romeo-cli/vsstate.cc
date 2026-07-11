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
#include <vector>
#include <cmath>

#include <whash.hh>

#include <color_output.hh>
#include <avalue.hh>
#include <vsstate.hh>
#include <result.hh>
#include <dresult.hh>
#include <property.hh>
#include <expression.hh>
#include <rvalue.hh>
#include <instruction.hh>
#include <graph_node.hh>
#include <time_interval.hh>

using namespace std;
using namespace romeo;

VSState* VSState::init(const Job& job)
{
    return new VSState(job);
}

VSState::VSState(const Job& job): PState(job), accum_cost(0), heuristic_cost(0), heuristic_approx(true), tsize()
{
    PResult::cts = &job.cts;
    this->V = new byte[job.cts.variables.vbyte_size()](); // value-initialisation -> 0
    job.cts.initv.execute(this->V, job.cts.statics);

    this->set_hash(romeo::whash(125, this->V, job.cts.variables.vstate_size()));
    update_enabled();

    if(job.feff)
    {
        nf = new unsigned[NE](); // intialized to 0
    }
}

VSState::VSState(const VSState& s, const Transition& f): PState(s), accum_cost(s.accum_cost), heuristic_cost(s.heuristic_cost), heuristic_approx(s.heuristic_approx), tsize(s.tsize)
{
    // Copy
    const unsigned NV = s.job.cts.variables.vbyte_size();
    this->V = new byte[NV];
    memcpy(this->V, s.V, s.job.cts.variables.vstate_size());

    // Apply assignments
    f.assigns.execute(this->V, job.cts.statics);

    // Compute the hash
    this->set_hash(whash(125, this->V, s.job.cts.variables.vstate_size()));

    // Compute enabled transitions
    update_enabled(s, f);
    //update_enabled();

    if (job.feff)
    {
        // Compute the number of transitions fired since each en[k] is enabled
        nf = new unsigned[NE](); // intialized to 0
        unsigned indices[NE];
    
        // The reference clock does not move
        indices[0] = 0;
        map_indices(s, &f, indices, 0);

        for (unsigned k = 0; k < NE; k++)
        {
            if (indices[k] != s.NE)
            {
                nf[k] = s.nf[indices[k]] + 1;
            }
        }
    }

    // Remember where this successor comes from
    s.allocated_succs++;
    this->allocated_succs = 0;
    this->parent = &s;
    this->in = &f;
    if (!f.utility)
    {
        this->steps = s.steps+1;
    }

    // update cost
    const value c = f.get_cost(s.V, job.cts.statics, job.non_negative_costs);
    accum_cost = accum_cost + c;

    // Update read variables that were abstracted away
    VarSet rs = read_vars;
    set_union(rs.begin(), rs.end(), f.read_vars.begin(), f.read_vars.end(), inserter(read_vars, read_vars.begin()));

    rs = abs_vars;
    set_union(rs.begin(), rs.end(), f.abs_vars.begin(), f.abs_vars.end(), inserter(abs_vars, abs_vars.begin()));

    if (!f.abs_vars.empty())
    {
        penalty++;
    }

    // Heuristic
    compute_heuristic();

}

VSState::VSState(const VSState& s, const Instruction& i): PState(s), accum_cost(s.accum_cost), heuristic_cost(s.heuristic_cost), heuristic_approx(s.heuristic_approx), tsize(s.tsize)
{
    const unsigned NV = s.job.cts.variables.vbyte_size();
    this->V = new byte[NV];
    memcpy(this->V, s.V, s.job.cts.variables.vstate_size() );

    SExpression(&i).execute(this->V, job.cts.statics);
    this->set_hash(whash(125, this->V, s.job.cts.variables.vstate_size()));

    update_enabled();

    if (job.feff)
    {
        // Compute the number of transitions fired since each en[k] is enabled
        nf = new unsigned[NE](); // intialized to 0
    }
}

VSState::VSState(const VSState& s): PState(s), NE(s.NE), accum_cost(s.accum_cost), heuristic_cost(s.heuristic_cost), heuristic_approx(s.heuristic_approx), tsize(s.tsize)
{
    // Copy
    const unsigned NV = s.job.cts.variables.vbyte_size();
    this->V = new byte[NV];
    memcpy(this->V, s.V, s.job.cts.variables.vstate_size() );

    this->en = new const Transition*[NE];
    memcpy(this->en, s.en, NE*sizeof(Transition*));
    
    if (job.feff)
    {
        nf = new unsigned[NE];
        memcpy(this->nf, s.nf, NE*sizeof(unsigned));
    }
}

PWNode* VSState::copy(const Instruction* I) const
{
    if (I == NULL)
    {
        return new VSState(*this);
    } else {
        return new VSState(*this,*I);
    }
}

void romeo::VSState::update_enabled()
{
    const CTS& cts = job.cts;
    unsigned NT = cts.ntrans();
    const Transition* enabled[NT];

    NE = 0;
    // For each transition
    for (list<Transition>::const_iterator i = cts.begin_transitions(); i != cts.end_transitions(); i++)
    {
        const Transition& f = *i;

        // If it is enabled
        const RValue& r = f.guard.eval(this);
        if ((r.is_unknown() && job.explore_unknown) || r.to_int())
        {
            enabled[NE] = &f;
            NE++;
        }
    }

    this->en = new const Transition*[NE];
    for (unsigned i = 0; i< NE; i++)
    {
        this->en[i] = enabled[i];
    }

}

void romeo::VSState::update_enabled(const VSState& s, const Transition& f)
{
    const CTS& cts = job.cts;
    unsigned NT = cts.ntrans();
    const Transition* enabled[NT];

    //if (x == cts.trans_to_check.end())
    //{
    //    cerr << error_tag(color_output) << ": Transition " << f.label << " was not enabled." << endl;
    //    exit(1);
    //}

    //NE = 0;
    //for (auto i: x->second)
    //{
    //   // A transition to check
    //   const Transition& t = *i;
    //   // If it is enabled
    //   PResult * r = t.guard->eval(this);
    //   bool satisfied = !r->empty();
    //   delete r;

    //   if (satisfied)
    //   {
    //       enabled[NE] = i;
    //       NE++;
    //   }
    //}
    //cout << "check after " << f.label << ": " << endl;
    //for (auto x: cts.trans_to_check[f.id])
    //{
    //    cout << "    " << x->label << endl;
    //}
    //cout << endl;
    //cout << "not enabled for sure after " << f.label << ": "<< endl;
    //for (auto x: cts.trans_disabled[f.id])
    //{
    //    cout << "    " << x->label << endl;
    //}
    //cout << endl;

    const auto cend = cts.trans_to_check[f.id].end();
    const auto eend = cts.trans_enabled[f.id].end();
    //const auto dend = cts.trans_disabled[f.id].end();

    auto i = cts.trans_to_check[f.id].begin();
    auto j = cts.trans_enabled[f.id].begin();
    //auto d = cts.trans_disabled[f.id].begin();
    NE = 0;
    unsigned k = 0;

    while (k < s.NE || i != cend || j != eend)
    {
        const unsigned xi = (i == cend ? cts.ntrans() : (*i)->id);
        const unsigned xj = (j == eend ? cts.ntrans() : (*j)->id);
        const unsigned xk = (k == s.NE ? cts.ntrans() : s.en[k]->id);

        // xi and xj can never be equal
        if (xj <= xk && xj < xi)
        {
            // xj is the min: enabled for sure
            enabled[NE] = *j;
            NE++;
            j++;
            if (xj == xk)
            {
                k++;
            }
        } else if (xi <= xk && xi < xj) {
            // xi is the min
            // previously enabled or not, it needs to be checked
            const RValue& g = (*i)->guard.eval(this);
            if ((g.is_unknown() && job.explore_unknown) || g.to_int())
            {
                enabled[NE] = *i;
                NE++;
            } 
            i++;
            if (xi == xk)
            {
                k++;
            }
        } else {
            // xk is the only min: a previously enabled transition that
            // does not need to be checked and is not enabled for sure.
            //while (d != dend && (*d)->id < s.en[k]->id)
            //{
            //    d++;
            //}

            //if (d == dend || (*d)->id > s.en[k]->id)
            if (!cts.trans_disabled[f.id].count(s.en[k]))
            {
                // Not disabled for sure and not in the to_check list 
                // (which does not include disabled for sure)
                // So it is still enabled
                enabled[NE] = s.en[k];
                NE++;
                //d++;
            }
            k++;
        }
    }

    this->en = new const Transition*[NE];
    for (unsigned i = 0; i < NE; i++)
    {
        this->en[i] = enabled[i];
    }
}

// map_indices gives when firing transition S.en[k] from S, the mapping indices
// that ranges over the size of this, and such that:
// indices[i] is the index (dimension number for the polyhedron) of this->en[i] in S.D
// If that value is the dimension of S.D (actually offset + NE, permitting to ignore additional cost dimensions), 
// then this->en[i] is newly enabled. 
// The offset value is used to ignore the offset first dimensions. 
// It is useful for parameters in which case its value is NP, or for DBMs with the ficticious zero clock
// in which case the value is 1.
void VSState::map_indices(const VSState& S, unsigned indices[], const unsigned offset) const
{
    map_indices(S, nullptr, indices, offset);
}

void VSState::map_indices(const VSState& S, const Transition* tf, unsigned indices[], const unsigned offset) const
{
    byte* intermediate = nullptr;
    bool has_intermediate = (tf != nullptr && !tf->intermediate.is_nop());

    // Check intermediate marking
    if (has_intermediate)
    {
        const unsigned NV = job.cts.variables.vbyte_size();
        intermediate = new byte[NV];
        memcpy(intermediate, S.V, job.cts.variables.vstate_size());

        tf->intermediate.execute(intermediate, job.cts.statics);

        //cout << static_cast<const VariableList&>(job.cts.variables).value_to_string(S.V) << endl;
        //cout << static_cast<const VariableList&>(job.cts.variables).value_to_string(intermediate) << endl;
        //cout << static_cast<const VariableList&>(job.cts.variables).value_to_string(V) << endl;
    }

    // Resets and previous indices
    unsigned j=0;
    for (unsigned i = 0; i < NE; i++)
    {
        // We assume the transitions are in id-ascending order in en
        while (j < S.NE && en[i]->id > S.en[j]->id) { j++; }

        bool interm = false;
        if (has_intermediate)
        {
            RValue r = en[i]->guard.evaluate(intermediate, job.cts.statics);
            interm = (r.is_unknown() || r.to_int() == 0);
        }

        if (j == S.NE 
                || en[i]->id < S.en[j]->id // was not enabled
                || interm // has been disabled by intermediate
                || en[i] == tf) // is the fired transition
        {
            indices[i + offset] = S.NE + offset;
        } else {
            indices[i + offset] = j + offset;
        }
    }

    if (has_intermediate)
    {
        delete [] intermediate;
    }
}

bool romeo::VSState::key_less(const PWNode* n) const
{
    const VSState* m = static_cast<const VSState*>(n);
    return (romeo::compare(this->V, m->V, job.cts.variables.vstate_size()) == LESS);
}

bool romeo::VSState::equals(const PWNode* n) const
{
    const VSState* m = static_cast<const VSState*>(n);
    return (romeo::compare(this->V, m->V, job.cts.variables.vstate_size()) == EQUAL);
}

bool romeo::VSState::contains(const PWNode* n) const
{
    return equals(n);
}

PWTRel romeo::VSState::compare(const PWNode* n) const
{
    const VSState* m = static_cast<const VSState*>(n);
    PWTRel r = PWT_DIFF;
    if (romeo::compare(this->V, m->V, job.cts.variables.vstate_size()) == EQUAL)
        r = PWT_EQ;

    return r;
}


bool romeo::VSState::empty() const
{
    return false;
}

PWNode* romeo::VSState::successor(unsigned i)
{
    return new VSState(*this, *en[i]);
}

PWNode* romeo::VSState::successor(const Transition* tf, const LExpression* e)
{
    PWNode* r = nullptr;

    unsigned i;
    for (i = 0; i < NE && tf != en[i]; i++);

    if (i < NE)
    {
        bool b = set_firing_date(i, e);
        if (b && firable(i))
        {
            r = successor(i);
            static_cast<VSState*>(r)->set_fired_date(e);
        }
    }

    return r;
}

PWNode* romeo::VSState::successor_by_label(const Transition* tf)
{
    PWNode* r = NULL;

    unsigned i;
    for (i = 0; i < NE && tf->label != en[i]->label; i++);

    if (i < NE)
    {
        if (firable(i))
        {
            r = successor(i);
        }
    }

    return r;
}

bool romeo::VSState::set_firing_date(const unsigned i, const LExpression* e, const cvalue q)
{
    return true;
}

void romeo::VSState::set_fired_date(const LExpression* e, const cvalue q)
{
}

bool romeo::VSState::update_firing_date(const Transition* tf, const LExpression* e, const cvalue q)
{
    unsigned i;
    for (i=0; i<NE && tf != en[i]; i++);

    return set_firing_date(i,e,q);
}

SizeDigest romeo::VSState::get_tsize() const
{
    return tsize;
}

void romeo::VSState::update_tsize()
{
    tsize = SizeDigest();
}

bool romeo::VSState::feff_firable(unsigned i) const
{
    bool firable = true;

    unsigned j = i;
    while (j > 0 && en[j - 1]->feff_id == en[i]->feff_id) 
    {
        j = j - 1;
        if (nf[j] >= nf[i])
        {
            firable = false;
        }
    }

    j = i + 1;
    while (j < NE && en[j]->feff_id == en[i]->feff_id) 
    {
        if (nf[j] > nf[i])
        {
            firable = false;
        }
        j = j + 1;
    }

    return firable;
}

bool romeo::VSState::firable(unsigned i) const
{
    bool firable = en[i]->allow.eval(this).to_int();

    for (unsigned j = 0; j < NE && firable; j++)
    {
        if (j != i && en[j]->has_priority_over(*en[i], V, job.cts.statics))
        {
            firable = false;
        }
    }

    if (firable && job.feff)
    {
        firable = feff_firable(i);
    }

    return firable;
}

string VSState::enabled_string(bool f) const
{
    stringstream oss;
    bool comma = false;
    bool deadlock = true;
    for (unsigned i=0; i<NE; i++)
    {
        if (!f || firable(i))
        {
            if (comma)
            {
                oss << ", ";
            } else {
                comma = true;
            }

            oss << en[i]->label;
            deadlock = false;
        }
    }

    if (deadlock)
    {
        oss << "None";
    }

    return oss.str();
}

string VSState::to_string() const
{
    string s = static_cast<const VariableList&>(job.cts.variables).value_to_string(V);
    if (job.feff)
    {
        stringstream ss;
        ss<< endl << "nf: ";
        for (unsigned k = 0; k < NE; k++)
        {
            ss << nf[k] << " ";
        }
        ss<< endl;
        s += ss.str();
    }
    
    if (job.has_cost() || job.hpeu)
    {
        stringstream ss;

        ss << endl << "cost: " << min_cost();
        if (heuristic_cost != 0)
        {
            ss << " (+ " << heuristic_cost << ")";
        }
        s += ss.str();
    }

    return s;
}

PWNiterator* VSState::iterator()
{
    return new VSSiterator(this);
}

VSSiterator::VSSiterator(PWNode* st): PWNiterator(st) 
{
    VSState * s = static_cast<VSState*>(base);
    // Precompute firable transitions
    for (unsigned i = 0; i < s->NE; i++)
    { 
        if (s->firable(i))
        {
            succs.push_back(i);
        }
    }
    
    if (base->job.randomize_succs)
    {
        // randomly shuffle succs
        const unsigned n = succs.size();
        for (unsigned i = 0; i < n; i++)
        {
           const unsigned j = rand() % n;
           const unsigned k = rand() % n;
           const unsigned temp = succs[j];
           succs[j] = succs[k];
           succs[k] = temp;
        }
    }
}

PWNode* VSSiterator::next()
{
    VSState * s = static_cast<VSState*>(base);
    PWNode * r;  
            
    if (index == succs.size()) {
        // None other firable
        r = NULL;
        base->sticky = false; // OK now we can deallocate it if needed
    } else {
        // Compute the successor
        r = s->successor(succs[index]);
        index++;
    }

    return r;
}

VSSiterator::~VSSiterator()
{
    base->sticky = false; // OK now we can deallocate it if needed
}

bool VSState::restriction(const PResult& r)
{
    // Nothing: useless for non-parametric stuff
    return false;
}

// (Marking) Properties 
bool romeo::VSState::bounded(const unsigned bound) const
{
    return job.cts.variables.bounded(bound, V);
}

cvalue romeo::VSState::max_bound() const
{
    return job.cts.variables.max_bound(V);
}

bool romeo::VSState::deadlock() const
{
    bool deadlock = true;
    for (unsigned i = 0; i < NE && deadlock; i++)
    {
        deadlock = en[i]->utility;
    }

    return deadlock;
}

bool romeo::VSState::safety_control_bad_state() const
{
    bool winc = true; // all controllable
    bool winiu = true; // all uncontrollable ineluctable

    for (unsigned i=0; i<NE; i++)
    {
        const unsigned int ctrl_flags = en[i]->control;
        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            // A winning controllable transition
            winc = false;
        } else if (ctrl_flags & CTRL_FORCED) {
            // A forced winning uncontrollable transition
            winiu = false;
        }
    }

    return (winc && winiu);
}

PResult* romeo::VSState::state_result(bool b) const
{
    if (b)
    {
        return reach_cond();
    } else {
        return init_result(false);
    }
}

RValue VSState::evaluate(const SExpression& e) const
{
    return e.evaluate(V, job.cts.statics);
}

PResult* romeo::VSState::cost_limit(const SExpression& ub, const bool us) const
{
    const value u = ub.evaluate(V, job.cts.statics).to_int();
    Avalue limu(u, (us? 1: 0));

    return init_result(this->min_cost() <= limu);
}

bool VSState::can_delay_forever() const
{
    bool result = (job.computation_mode != UNTIMED);

    for (unsigned i = 0; i < NE && result; i++)
    {
        if (!en[i]->timing->unbounded)
        {
            result = false;
        }
    }

    return result;
}

// Non parametric
PResult* VSState::init_result(bool b) const
{
    return new PBool(b);
}

CostResult* VSState::init_cost_result() const
{
    return new CostResult();
}

void romeo::VSState::compute_rc() const
{
    rc = new PBool(true);
}

// Clockval properties
void VSState::min_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
    unsigned i = 0;
    for (i=0; i<NE && en[i] != t; i++);

    v = 0;
    q = 1;
    s = false;
    u = false;
    d = false;

    // The transition is not enabled:
    if (i == NE)
        d = true;
}

void VSState::max_clockval(const Transition* t, cvalue& v, cvalue& q, bool& s, bool& u, bool& d) const
{
    unsigned i = 0;
    for (i=0; i<NE && en[i] != t; i++);

    v = 0;
    q = 1;
    s = true;
    u = true;
    d = false;
    
    // The transition is not enabled:
    if (i == NE)
        d = true;
}

// Destructor
VSState::~VSState()
{
    delete [] V;
    delete [] en;
}

unsigned VSState::nen() const
{
    return NE;
}

const Transition* VSState::get_enabled(unsigned i) const
{
    return en[i];
}

CostResult* VSState::current_cost() const
{
    return new CostResult(min_cost());
}

Avalue VSState::min_cost() const
{
    if (!job.minimize_read_vars)
    {
        return accum_cost;
    } else {
        return nreads();
    }
}

Avalue VSState::cost_heuristic() const
{
    return heuristic_cost;
}

bool VSState::is_heuristic_approximate() const
{
    return heuristic_approx;
}

void VSState::add_dcost(cvalue c)
{
    accum_cost += c;
}

void VSState::set_hcost(const Avalue& h)
{
    heuristic_cost = h;
}

void VSState::compute_heuristic()
{
    if (!job.cts.cost_heuristic.is_null())
    {
        heuristic_cost = job.cts.cost_heuristic.evaluate(V, job.cts.statics).to_int();
    } else {
        if (job.use_heuristic && job.heuristic_prop != NULL)
        {
            const Property* p = static_cast<const Property*>(job.heuristic_prop->copy(job.cts));
            CTS* cts = new CTS(job.cts);
            PropertyJob j(job, *cts, p);
            j.use_heuristic = false;
            j.minimize_read_vars = true;
            j.max_concretise_rounds = 30;

            PState* st = j.initial_state();
            CostResult* r = static_cast<CostResult*>(p->eval(st));

            heuristic_cost = r->cost();
            //heuristic_cost = 0;
            heuristic_approx = r->approx();
        }
    }
}

bool VSState::cost_less_than(const PWNode* n) const
{
    //const SizeDigest t1 = this->get_tsize();
    //const SizeDigest t2 = static_cast<const VSState*>(n)->get_tsize();

    const Avalue h1 = cost_heuristic();
    const Avalue h2 = n->cost_heuristic();
    const Avalue v1 = min_cost() + h1;
    const Avalue v2 = n->min_cost() + h2;

    bool r = ((v1 != v2) ? v1 < v2 : h1 < h2);
    if (!r && job.minimize_read_vars)
    {
        r = (nreads() == n->nreads() && in_transition()->prefval > n->in_transition()->prefval);
    }

    //return ((t1 < t2 || t2 < t1) ? t1 < t2 : r);
    return r;
}

// ------------------ storage --------------------------------------------------

PassedList* VSState::init_passed(WaitingList& w, unsigned vs, bool b) const
{
    if (job.pw == PASSED_OFF) {
        return new PassedVOff();
    } else {
        if (job.has_cost())
        {
            return new PassedRInc(b, w, vs);
        } else {
            return new PassedVEq(b);
        }
    }
}

WaitingList* VSState::init_waiting() const
{
    if (!job.has_cost())
    {
        return new SimpleWaitingList(job);
    } else {
        return new CostPriorityQueue(job);
    }
}

const byte* VSState::discrete() const
{
    byte* disc = new byte[discrete_size()];
    memcpy(disc, V, job.cts.variables.vstate_size()*sizeof(byte));
    
    return disc;
}

Key VSState::get_key() const
{
    return Key(discrete_size(), discrete());
}

Key VSState::get_abstracted_key(bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    return get_key();
}

unsigned VSState::key_size() const
{
    return discrete_size();
}

unsigned VSState::discrete_size() const
{
    return job.cts.variables.vstate_size();
}

// .............................................................................


bool VSStateMergeStorage::addr(const PWNode* s, const PResult* r)
{
    return false;
}

unsigned VSStateMergeStorage::size() const
{
    return 1;
}

VSStateMergeStorage::VSStateMergeStorage(const VSState* s)
{
}

VSStateMergeStorage::~VSStateMergeStorage()
{
}

// .............................................................................

bool VSStateRIncStorage::contains(const PWNode* s) const
{
    return false;
}

bool VSStateRIncStorage::is_contained_in(const PWNode*s) const
{
    return false;
}

VSStateRIncStorage::VSStateRIncStorage(const VSState* s): RIncStorage(s)
{
}

VSStateRIncStorage::~VSStateRIncStorage()
{
}
// .............................................................................

bool VSStateCostStorage::contains(const PWNode* s) const
{
    return s->min_cost() >= cost;
}

bool VSStateCostStorage::is_contained_in(const PWNode*s) const
{
    return s->min_cost() <= cost;
}

VSStateCostStorage::VSStateCostStorage(const VSState* s): RIncStorage(s), cost(s->min_cost())
{
}

VSStateCostStorage::~VSStateCostStorage()
{
}


// .............................................................................

VSStateEqStorage::VSStateEqStorage(const VSState* s): size(s->job.cts.variables.vstate_size())
{
    this->V = s->discrete();
}

bool VSStateEqStorage::equals(const PWNode* s) const
{
    const VSState* m = static_cast<const VSState*>(s);
    return (romeo::compare(this->V, m->V, this->size) == EQUAL);
}

bool VSStateEqStorage::key_less(const EqStorage* s) const
{
    const VSStateEqStorage* m = static_cast<const VSStateEqStorage*>(s);
    return (romeo::compare(this->V, m->V, this->size) == LESS);
}

const byte* VSStateEqStorage::key_copy() const
{
    byte* r = new byte[size];
    memcpy(r, V, size);

    return r;
}

VSStateEqStorage::~VSStateEqStorage()
{
    delete [] V;
}

// .............................................................................

EqStorage* VSState::eq_storage() const
{
    return new VSStateEqStorage(this);
}

RIncStorage* VSState::rinc_storage() const
{
    if (job.has_cost())
    {
        return new VSStateCostStorage(this);
    } else {
        cerr << error_tag(color_output) << "Inclusion convergence not available with untimed CTSs" << endl;
        exit(1);
    }
}

MergeStorage* VSState::merge_storage() const
{
    cerr << error_tag(color_output) << "Merge convergence not available with untimed CTSs" << endl;
    exit(1);
}

// ------------------ control --------------------------------------------------

void VSState::set_winning(GraphNode* n, const bool w) const
{
    n->winning.wb = w;
}

void VSState::init_winning(GraphNode* n) const
{
    n->winning.wb = false;
}

void VSState::add_winning(GraphNode* n, GraphNode* x) const
{
    n->winning.wb = (n->winning.wb || x->winning.wb);
}

PResult* VSState::update_result(const GraphNode* g, PResult* r) const
{
    delete r;
    return init_result(g->winning.wb);
}

bool VSState::has_winning(const GraphNode* g) const
{
    return g->winning.wb;
}

bool VSState::update_reach(GraphNode* n) const
{
    list<SuccInfo>::iterator it;

    bool winc = false;
    bool winiu = false;
    const Transition* strat = NULL;
    bool urgent = false;
    bool winu = true;
    bool winnau = true;
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const bool wins = it->node->winning.wb;
        const unsigned int ctrl_flags = it->trans->control;
        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            if (wins)
            {
                // A winning controllable transition
                winc = true;
                strat = it->trans;
            }
        } else {
            if (wins)
            {
                if (ctrl_flags & CTRL_FORCED)
                {
                    // A forced winning uncontrollable transition
                    winiu = true;
                }
            } else {
                // There is a losing uncontrollable transition
                winu = false;

                if (ctrl_flags & CTRL_DELAYED)
                {
                    // This losing uncontrollable transition
                    // can be be avoided if we are quick
                    urgent = true;
                } else {
                    // This losing uncontrollable transition
                    // cannot be avoided
                    winnau = false;
                }
            }
        }
    }

    const bool old_winning = n->winning.wb;
    n->winning.wb = (winc && winnau) || (winiu && winu);

    if (!old_winning && n->winning.wb)
    {
        if (!job.notrace)
        {
            LocalStrategy ls;
            ls.domain.wb = !urgent;
            ls.action = strat;
            n->strategy.push_back(ls); 
        }
        
        return true;
    }

    return false;
}

bool VSState::update_safe(GraphNode* n) const
{
    list<SuccInfo>::iterator it;

    bool winuu = false; // there exists a unavoidable uncontrollable
    bool winc = true; // all controllable
    bool winiu = true; // all uncontrollable ineluctable
    const Transition* strat = NULL;
    bool winu = false; // there exists an uncontrollable
    for (it = n->succs.begin(); it != n->succs.end(); it++)
    {
        const bool wins = it->node->winning.wb;
        const unsigned int ctrl_flags = it->trans->control;
        if (ctrl_flags & CTRL_CONTROLLABLE)
        {
            if (!wins)
            {
                // A winning controllable transition
                winc = false;
            }
        } else {
            if (!wins)
            {
                if (ctrl_flags & CTRL_FORCED)
                {
                    // A forced winning uncontrollable transition
                    winiu = false;
                }
            } else {
                // There is a losing uncontrollable transition
                winu = true;
                if (strat == NULL)
                {
                    strat = it->trans;
                }

                if (!(ctrl_flags & CTRL_DELAYED))
                {
                    // This losing uncontrollable transition
                    // cannot be avoided
                    winuu = true;
                    strat = it->trans;
                }
            }
        }
    }

    const bool old_winning = n->winning.wb;
    n->winning.wb = (winc && (winu || winiu)) || winuu;

    //cout << *this << endl;
    //cout << winc << " " << winiu << " " << winu << " " << winuu << endl; 
    //cout << n->winning.wb << endl;

    if (!old_winning && n->winning.wb)
    {
        if (!job.notrace)
        {
            LocalStrategy ls;
            ls.domain.wb = true;
            ls.action = strat;
            n->strategy.push_back(ls); 
        }

        return true;
    }

    return false;
}

PassedGN* VSState::init_passed_gn(WaitingGN& F, WaitingGN& B) const
{
    return new PassedGNEq(WSET_UNTIMED, job.cts.variables.vstate_size(), F, B);
}

// -----------------------------------------------------------------------------


