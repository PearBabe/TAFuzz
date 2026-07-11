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

#include <list>
#include <utility>
#include <iostream>
#include <sstream>

#include <cts.hh>
#include <job.hh>

#include <transition.hh>
#include <variable.hh>
#include <type.hh>
#include <type_list.hh>
#include <function.hh>
#include <parameter.hh>
#include <time_interval.hh>

#include <property.hh>
#include <properties.hh>
#include <lobject.hh>
#include <instruction.hh>
#include <rvalue.hh>
#include <lexpression.hh>
#include <lconstraint.hh>

#include <linear_expression.hh>
#include <polyhedron.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;

extern TypeList _romeo_types;

CTS* CTS:: current_cts = nullptr;

CTS::CTS(const unsigned i, const std::string& l): 
    LObject(i,l), VContext(0), NT(0), NP(0), NC(0), bounded_params(false), parameter_bound(0), 
    uses_time(false), uses_cost(false), uses_params(false), uses_hybrid(false),
    parameter_lbounded(nullptr), parameter_ubounded(nullptr), 
    parameter_lbounds(nullptr), parameter_ubounds(nullptr), 
    max_timing_constant(0), initv(), initp(), cost(), cost_heuristic()
{
}

CTS::CTS(const CTS& t): 
    LObject(t.id, t.label), 
    VContext(t),//.next_var_id, t.consts, t.constants.vbyte_size(), t.constants.vcell_size()),
    NT(0), NP(0), NC(0),
    bounded_params(t.bounded_params),
    parameter_bound(t.parameter_bound),
    uses_time(t.uses_time),
    uses_cost(t.uses_cost),
    uses_params(t.uses_params),
    uses_hybrid(t.uses_hybrid),
    parameter_lbounded(nullptr), parameter_ubounded(nullptr), 
    parameter_lbounds(nullptr), parameter_ubounds(nullptr), 
    max_timing_constant(t.max_timing_constant)
{
    for (auto& f: t.functions)
    {
        this->add_function(f->copy(*this));
    }

    for (auto& ti: t.transitions)
    {
        this->add_transition(ti);
    }

    this->initv = t.initv.copy(*this);
    this->initp = t.initp.copy(*this);

    this->cost = t.cost.copy(*this);
    this->cost_heuristic = t.cost_heuristic.copy(*this);

    find_constants();
}

void CTS::writing_trans_with_reads(const VarSet& S, VarSet& Sext, list<const Transition*>& T) const
{
    Sext = S;

    list<Transition>::const_iterator i;
    for (i = transitions.begin(); i != transitions.end(); i++)
    {
        VarSet St, St_int, Sr;
        i->writes(St);

        set_intersection(St.begin(), St.end(), S.begin(), S.end(), inserter(St_int, St_int.begin())); // Intersection of S and St
        // Keep only transitions that write the set of variables of interest with their read variables
        if (!St_int.empty())
        {
            i->reads(Sr);
            VarSet Su;
            // Compute full set of variables (including those added by reads of transitions writing to S)
            set_union(Sext.begin(), Sext.end(), Sr.begin(), Sr.end(), inserter(Su, Su.begin()));
            Sext = Su;
            T.push_back(&(*i));
        }
    }
}

CTS::CTS(const CTS& t, const VarSet& Sext, const list<const Transition*>& T): 
    LObject(t.id, t.label), 
    VContext(t, Sext),//.next_var_id, t.consts, t.constants.vbyte_size(), t.constants.vcell_size()),
    NT(0), NP(0), NC(0),
    bounded_params(t.bounded_params),
    parameter_bound(t.parameter_bound),
    uses_time(false), uses_cost(false), uses_params(false), uses_hybrid(false),
    max_timing_constant(t.max_timing_constant)
{
    for (auto f: t.functions)
    {
        this->add_function(f->copy(*this));
    }

    for (auto pt: T)
    {
        add_transition_abstract(*pt, Sext);
    }

    this->initv = t.initv.abstract_copy(*this, Sext);
    this->initp = t.initp.abstract_copy(*this, Sext);

    this->cost = t.cost.abstract_copy(*this, Sext);
    this->cost_heuristic = t.cost_heuristic.abstract_copy(*this, Sext);
       
    find_constants();
}

void CTS::add_transition(const Transition& t)
{
    this->transitions.push_back(t);
    // workaround: we want a copy so that t can be deleted
    // without deleting the expressions inside
    this->transitions.back().copy(t, *this);
    this->transitions.back().id = NT; // Fix the index that might be wrong in the parser due to transition replication.
    this->NT++;

    this->uses_time |= !t.timing->unconstrained();
    this->uses_hybrid |= !t.speed.is_constant(1);
    this->uses_params |= t.timing->lbound.has_params() || (!t.timing->unbounded && t.timing->ubound.has_params());
    this->uses_cost |= !t.cost.is_null() && !t.cost.is_constant(0);
    
    transitions_by_label[t.label] = &this->transitions.back();
}

void CTS::add_transition_abstract(const Transition& t, const VarSet& S)
{
    this->transitions.push_back(t);
    // workaround: we want a copy so that t can be deleted
    // without deleting the expressions inside
    Transition& t_abs = this->transitions.back();
    t_abs.abstract_copy(t, *this, S);
    t_abs.id = NT;

    // all variables read by this transition
    t.reads(t_abs.read_vars);

    this->NT++;

    this->uses_time |= !t.timing->unconstrained();
    this->uses_hybrid |= !t.speed.is_constant(1);
    this->uses_params |= t.timing->lbound.has_params() || (!t.timing->unbounded && t.timing->ubound.has_params());
    this->uses_cost |= !t.cost.is_null() && !t.cost.is_constant(0);

    transitions_by_label[t.label] = &this->transitions.back();
}

const Parameter* CTS::add_parameter(const Parameter& p)
{
    this->parameters.push_back(p);
    this->NP++;

    parameters_by_label[p.label] = &this->parameters.back();
    return &this->parameters.back();
}

void CTS::add_function(const Function* f)
{
    this->functions.push_back(f);

    functions_by_label[f->label] = this->functions.back();
}

unsigned CTS::ntrans() const { return NT; }
unsigned CTS::nparams() const { return NP; }
unsigned CTS::nconstants() const { return NC; }
bool CTS::params_bounded() const { return bounded_params; }
value CTS::params_bound() const { return parameter_bound; }
cvalue CTS::max_const() const { return max_timing_constant; }

list<Transition>::const_iterator CTS::begin_transitions() const { return transitions.begin(); }
list<Transition>::const_iterator CTS::end_transitions() const { return transitions.end(); }
list<Parameter>::const_iterator CTS::begin_parameters() const { return parameters.begin(); }
list<Parameter>::const_iterator CTS::end_parameters() const { return parameters.end(); }
list<const Function*>::const_iterator CTS::begin_functions() { return functions.begin(); }
list<const Function*>::const_iterator CTS::end_functions() { return functions.end(); }

Transition* CTS::lookup_transition_non_const(const std::string& s)
{
    list<Transition>::iterator k;
    for (k = transitions.begin(); k != transitions.end() && k->label != s; k++);

    if (k == transitions.end())
        return nullptr;
    else
        return &(*k);
}

const Transition* CTS::lookup_transition(const std::string& s) const
{
    map<string, const Transition*>::const_iterator i = transitions_by_label.find(s);

    if (i == transitions_by_label.end())
    {
        return nullptr;
    } else {
        return i->second;
    }
}

const Parameter* CTS::lookup_parameter(const std::string& s) const
{
    map<string, const Parameter*>::const_iterator i = parameters_by_label.find(s);

    if (i == parameters_by_label.end())
    {
        return nullptr;
    } else {
        return i->second;
    }

}

const Function* CTS::lookup_function(const std::string& s) const
{
    map<string, const Function*>::const_iterator i = functions_by_label.find(s);

    if (i == functions_by_label.end())
    {
        return nullptr;
    } else {
        return i->second;
    }
}


// Used only in timed_property to add observer variables
const Variable& CTS::find_or_add_util(const std::string& s)
{
    const Variable* v = this->lookup_variable_by_label(s);
    if (v == nullptr)
    {
        // Add as state variable (last arg = true)
        this->add_variable(s,*_romeo_types.integer(), false, false, 0, 0, nullptr, true, true);
        v = last_added_variable();
    }

    return *v;
}

void CTS::find_constants()
{
    // It is crucial that constants have the last indices and NP is the number
    // of non constant parameters

    if (parameter_lbounds != nullptr)
    {
        delete [] parameter_lbounds;
    }
    if (parameter_ubounds != nullptr)
    {
        delete [] parameter_ubounds;
    }
    if (parameter_lbounded != nullptr)
    {
        delete [] parameter_lbounded;
    }
    if (parameter_ubounded != nullptr)
    {
        delete [] parameter_ubounded;
    }

    parameter_lbounds = new cvalue[NP];
    parameter_ubounds = new cvalue[NP];
    parameter_lbounded = new bool[NP];
    parameter_ubounded = new bool[NP];
    for (unsigned i = 0; i < NP; i++)
    {
        parameter_lbounded[i] = false;
        parameter_ubounded[i] = false;
        parameter_lbounds[i] = (ROMEO_MIN_BVALUE >> 1);
        parameter_ubounds[i] = (ROMEO_MIN_BVALUE >> 1);
    }

    bounded_params = true;
    parameter_bound = 0;

    if (!initp.is_null())
    {
        unsigned N = 0;
        unsigned k = 0;
        bounded_params = true;
        
        for (auto& p: parameters)
        {
            cvalue lv = 0, rv = 0, ld, rd;
            bool lb, ls, rs, rb;

            if (!p.constant(lv))
            {
                Polyhedron P = initp.constraint(nullptr, statics, NP);
                P.project_on(p.index(), ls, lb, lv, rs, rb, rv, ld, rd);
            } else {
                rv = lv;
                ld = 1;
                rd = 1;
                rb = true;
                lb = true;
            }

            if (lb && rb && ld == 1 && rd == 1 && lv == rv)
            {
                N++;
                p.set_index(NP + NC - N);
                p.set_constant(lv);
            } else {
                p.set_index(k - N);
                parameter_lbounded[k - N] = lb;
                if (lb)
                {
                    parameter_lbounds[k - N] = lv;
                }
                parameter_ubounded[k - N] = rb;
                if (rb)
                {
                    parameter_ubounds[k - N] = rv;
                }
            }

            bounded_params = bounded_params && lb && rb;
            parameter_bound = max(parameter_bound, lv);
            parameter_bound = max(parameter_bound, rv);
            
            k++;
        }

        NP = NP+NC - N;
        NC = N;

    }
    // Compute max bounds for unbounded transitions
    for (auto& t: transitions)
    {
        if (t.timing->unbounded)
        {
            LinearExpression L = Var(NP) - t.timing->lbound.linear_expression(nullptr, statics);
            Polyhedron P(NP + 1, true);
            P.constrain(L, CSTR_EQ);
            for (unsigned k = 0; k < NP; k++)
            {
                if (parameter_lbounded[k])
                {
                    P.constrain(Var(k) - parameter_lbounds[k], CSTR_GWEAK);
                }
                if (parameter_ubounded[k])
                {
                    P.constrain(Var(k) - parameter_ubounds[k], CSTR_LWEAK);
                }
            }

            cvalue lv = 0, rv = 0, ld, rd;
            bool lb, ls, rs, rb;
            P.project_on(NP, ls, lb, lv, rs, rb, rv, ld, rd);
            t.max_bounded = rb;
            t.max_bound = rv;
        }
    }

    for (auto& t: transitions)
    {
        if (t.timing->lbound.has_vars() || (!t.timing->unbounded && t.timing->ubound.has_vars()))
        {
            if (!(t.timing->lbound.is_const() && (t.timing->unbounded || t.timing->ubound.is_const())))
            {
                cerr << error_tag(color_output) << "Error in transition " << t.label << ": cannot use variables in timing constraints." << endl;
                exit(1); 
            }
        } else {
            if (!t.timing->lbound.has_params())
            {
                // WARNING: check this conversion if interval bounds are allowed to be 64 bits
                max_timing_constant = std::max(max_timing_constant, (cvalue) t.timing->lbound.evaluate(nullptr, statics).to_int());
            }

            if (!t.timing->unbounded && !t.timing->ubound.has_params())
            {
                // WARNING: check this conversion if interval bounds are allowed to be 64 bits
                max_timing_constant = std::max(max_timing_constant, (cvalue) t.timing->ubound.evaluate(nullptr, statics).to_int());
            }
        }
    }

    //cout << "===============================================================" << endl;
    //cout << "variables" << endl;
    //for (auto x: variables)
    //{
    //    cout << x.label << "(" << x.get_offset() << ", " << x.get_coffset() << ", " << x.byte_size() + x.cell_size() << ") ";
    //}
    //cout << endl;
    // Pre-compute action of transitions on others
    for (auto j = transitions.begin(); j != transitions.end(); j++)
    {
        //cout << "--------------------------------------------------------" << endl;
        Transition& t = *j;
        t.written_vars.clear();
        t.read_vars.clear();
        t.writes(t.written_vars);
        t.reads(t.read_vars);
        t.guard.reads(t.en_vars);
        t.priority.reads(t.en_vars);
        //cout << t.label << endl; 
        //cout << "    ens : ";
        //for (auto x: t.en_vars)
        //{
        //    cout << x << " ";
        //}
        //cout << endl;
        //cout << "    writes : ";
        //for (auto x: t.written_vars)
        //{
        //    cout << x << " ";
        //}
        //cout << endl;
    }
    //cout << "--------------------------------------------------------" << endl;

    trans_to_check.clear();
    trans_disabled.clear();
    trans_enabled.clear();
    for (auto& ti: transitions)
    {
        trans_to_check.push_back(list<const Transition*>());
        //trans_disabled.push_back(list<const Transition*>());
        trans_disabled.push_back(set<const Transition*>());
        trans_enabled.push_back(list<const Transition*>());

        //cout << "--------------------------------------------------------" << endl;
        byte V[variables.vbyte_size()];
        memset(V, 0, variables.vbyte_size()); // value-initialisation -> 0
        //cout << variables.value_to_string(V) << endl;
        ti.assigns.execute(V, statics);

        //cout << variables.value_to_string(V) << endl;
        //cout << "After firing " << ti.label << ": " << endl;
        for (auto& tj: transitions)
        {
            //cout << tj.label << endl;
            VarSet S;
            set_intersection(tj.en_vars.begin(), tj.en_vars.end(), ti.written_vars.begin(), ti.written_vars.end(), inserter(S, S.begin()));

            RValue x = tj.guard.evaluate(V, statics);
            //cout << "    " << tj.label << " "<< x.to_int()  <<endl;;
            if (x.is_unknown())
            {
                //cout << "unknown " << S.empty() << endl;
                if (!S.empty())
                { 
                    // if tj reads a variable that was modified by ti 
                    // then it needs to be re-checked for enabledness
                    trans_to_check[ti.id].push_back(&tj);
                }
            } else {
                if (x.to_int() == 0)
                {
                    // This transition cannot be enabled anymore
                    //const Property* gi = static_cast<const Property*>(ti.guard.get_expr()->copy(*this));
                    //const Property* gj = static_cast<const Property*>(tj.guard.get_expr()->copy(*this));
                    //property::And A(*gi, *gj);
                    //byte Vd[variables.vbyte_size()];
                    //memset(Vd, 0, variables.vbyte_size()); // value-initialisation -> 0

                    //RValue xd = SExpression(&A).evaluate(Vd, statics);

                    //// Make sure ti and tj could be enabled at the same time
                    // Does not work as is because we do not know the values of variables
                    // so everything is unknown
                    //if (xd.is_unknown() || xd.to_int() != 0)
                    //{
                    //trans_disabled[ti.id].push_back(&tj);
                    trans_disabled[ti.id].insert(&tj);
                    //}
                } else {
                    // This transition is surely enabled now
                    trans_enabled[ti.id].push_back(&tj);
                }
            }
        }
        //cout << endl;
        //cout << "   disabled: ";
        //for (auto k: trans_disabled[ti.id])
        //{
        //    cout << k->label << " ";
        //}
        //cout << endl;
        //cout << "   enabled: ";
        //for (auto k: trans_enabled[ti.id])
        //{
        //    cout << k->label << " ";
        //}
        //cout << endl;
        //cout << "   test: ";
        //for (auto k: trans_to_check[ti.id])
        //{
        //    cout << k->label << " ";
        //}
        //cout << endl;
    }
}

string CTS::to_string() const
{
    stringstream s;

    s << "// NP " << NP << endl;
    s << "// NC " << NC << endl;
    s << "// NT " << NT << endl;
    s << "// NV " << variables.nvars() << endl;
    s << "// NVC " << static_consts.nvars() << endl;

    for (auto& p: parameters)
    {
        cvalue v;
        s << "// parameter ";
        s << p.label << " (id " << p.id << ", poly_index " << p.index();
        if (p.constant(v))
        {
            s << ", constant = " << v;
        }
        s << ") ";
        s << endl;
    }
    s << endl;

    s << "// Variables:" << endl;
    s << this->variables.to_string();
    s << "// Constants:" << endl;
    s << this->static_consts.to_string();
    s << endl;

    s << "parameters " << initp.to_string() << endl << endl;
    s << "initially " << initv.to_string() << endl << endl;
    s << "cost_rate " << cost.to_string() << endl << endl;
    s << "cost_heuristic " << cost_heuristic.to_string() << endl << endl;

    for (auto& t: transitions)
    {
        s << t.to_string();
    }

    return s.str();
}

bool CTS::has_time() const
{
    return uses_time;
}

bool CTS::has_hybrid() const
{
    return uses_hybrid;
}

bool CTS::has_params() const
{
    return uses_params;
}

bool CTS::has_cost() const
{
    return uses_cost || (!cost.is_null() && !cost.is_constant(0));
}

list<const Transition*> CTS::adapt_trace_ids(const list<std::string>& trace)
{
    list<const Transition*> L;

    for (auto& i: trace)
    {
        const Transition* t = this->lookup_transition(i);
        if (t == nullptr)
        {
            cerr << error_tag(color_output) << "Error in adapting the string trace for more concrete CTS: " << i << " not found." << endl;
            exit(1);
        }
        L.push_back(t);
    }

    return L;
}


// Remove parameters from transition intervals by hypercube overapproximation
CTS CTS::abstract_parameters() const
{
    CTS cts(*this);

    for (auto& t: cts.transitions)
    {
        const TimeInterval* ti = t.timing;
        t.timing = ti->abstract_parameters(cts, parameter_lbounded, parameter_ubounded, parameter_lbounds, parameter_ubounds);
        delete ti;
    }

    cts.initp.clear();
    cts.parameters.clear();
    cts.NP = 0;
    cts.NC = 0;

    cts.find_constants();

    return cts;
}

cvalue CTS::cost_rate(byte V[], bool non_negative_costs) const
{
    const value raw = (cost.is_null() ? 0 : cost.evaluate(V, statics).to_int());
    const value max_finite_cost = static_cast<value>(ROMEO_MAX_BVALUE) / 2 - 1;
    if (raw < -max_finite_cost || raw > max_finite_cost)
    {
        cerr << error_tag(color_output) << "Line " << cost.get_line()
             << ": local time cost is outside the finite DBM range (" << raw << ")" << endl;
        exit(1);
    }

    const cvalue c = static_cast<cvalue>(raw);
    if (non_negative_costs && c < 0)
    {
        cerr << error_tag(color_output) << "Line " <<  cost.get_line() << ": with the current options, the local time cost cannot be negative (" << c << ")" << endl;
        exit(1);
    }        

    return c;
}

CTS::~CTS()
{
    if (parameter_lbounds != nullptr)
    {
        delete [] parameter_lbounds;
    }
    if (parameter_ubounds != nullptr)
    {
        delete [] parameter_ubounds;
    }
    if (parameter_lbounded != nullptr)
    {
        delete [] parameter_lbounded;
    }
    if (parameter_ubounded != nullptr)
    {
        delete [] parameter_ubounded;
    }

    
    for (auto ifun : functions)
    {
        delete ifun;
    }

    if (statics)
    {
        delete [] statics;
    }
}
