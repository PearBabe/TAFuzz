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
#include <string>
#include <sstream>
#include <climits>
#include <typeinfo>

#include <properties.hh>
#include <pstate.hh>
#include <lexpression.hh>
#include <lconstraint.hh>
#include <instruction.hh>
#include <rvalue.hh>
#include <avalue.hh>
#include <result.hh>
#include <cts.hh>
#include <polyhedron.hh>
#include <time_interval.hh>
#include <stack_machine.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::property;

int Property::nprops = 0;

romeo::PState::PState(const Job& j): PWNode(j), rc(nullptr), have_computed_rc(false) {}

romeo::PState::PState(const PState& s): PWNode(s), rc(nullptr), have_computed_rc(false) {}

romeo::PState::~PState()
{
    if (rc != nullptr)
    {
        delete rc;
    }
}

void romeo::PState::destroy_graph_payload(GraphNode&) const
{
}

bool romeo::PState::step_limit(const unsigned val, const bool strict) const
{
    return (this->steps <= val + (strict?-1:0));
}

bool romeo::PState::fired_transition(unsigned i) const
{
    return (this->in->id == i);
}

PResult* romeo::PState::reach_cond() const
{
    if (!have_computed_rc)
    {
        compute_rc();
        have_computed_rc = true;
    }

    return rc->copy();
}

// -----------------------------------------------------------------------------

Property::Property(int l): Expression(l), id(Property::nprops), orig_prop(this)
{
    Property::nprops++;
}

Polyhedron Property::constraint(const std::byte V[], const std::byte C[], const unsigned N) const
{
    std::cerr << error_tag(color_output) << "Line " << decl_line << ": cannot use this operator with parameters: " << to_string() << std::endl;
    exit(1);
}

PResult* romeo::Property::evaluate(const PState* s) const
{
    PResult* r = this->eval(s);

    if (s->job.is_parametric() && !is_dprop())
    {
        const PResult* c = s->reach_cond();

        r->conjunction(*c);

        if (s->job.simplified_result)
        {
            r->simplify_with(*c);
        }

        if (s->job.ip)
        {
            r->integer_shape_close_assign();
        }
    }

    return r;
}

PState* Property::validate_observers(const PState* s) const
{
    return static_cast<PState*>(s->copy());
}

void Property::prepare(CTS& t) const
{
}

bool Property::is_property() const
{
    return true;
}

bool Property::is_simple() const
{
    return false;
}

bool Property::is_clock() const
{
    return false;
}

bool Property::is_dprop() const
{
    return false;
}

bool Property::has_cost() const
{
    return false;
}

bool Property::uses_backward_mincost_zones() const
{
    return false;
}

list<VarSet> Property::var_reads() const
{
    VarSet V;
    this->reads(V);

    if (!V.empty())
    {
        return list<VarSet>(1, V);
    } else {
        return list<VarSet>();
    }
}

const Property* Property::negation(CTS& t) const
{
    return new Not(*static_cast<const Property*>(this->copy(t)), decl_line);
}

// -----------------------------------------------------------------------

DyadicOperator::DyadicOperator(const Property& l, const Property& r, int line): Property(line), left(l), right(r)
{
}

void DyadicOperator::prepare(CTS& t) const
{
    left.prepare(t);
    right.prepare(t);
}

bool DyadicOperator::is_simple() const
{
    return left.is_simple() && right.is_simple();
}

bool DyadicOperator::is_lconstraint() const
{
    return left.is_lconstraint() && right.is_lconstraint();
}

void DyadicOperator::writes(VarSet& w) const
{
    left.writes(w);
    right.writes(w);
}

void DyadicOperator::reads(VarSet& r) const
{
    left.reads(r);
    right.reads(r);
}

bool DyadicOperator::has_cost() const
{
    return left.has_cost() || right.has_cost();
}

DyadicOperator::~DyadicOperator()
{
    delete &left;
    delete &right;
}

// -----------------------------------------------------------------------
bool romeo::Property::has_time() const
{
    return false;
}

bool romeo::Property::has_params() const
{
    return false;
}

// -----------------------------------------------------------------------

TemporalProperty::TemporalProperty(const SExpression& l, const SExpression& r, int line): Property(line), phi(l), psi(r)
{
}

bool TemporalProperty::is_simple() const
{
    return false;
}

bool TemporalProperty::has_cost() const
{
    if (phi.has_cost())
    {
        std::cerr << error_tag(color_output) << "Line " << decl_line << ": cannot use cost in the first part of temporal property: " << to_string() << std::endl;
        exit(1);
    }

    return psi.has_cost();
}

// -----------------------------------------------------------------------
property::Not::Not(const Property& l, int line): Property(line), statement(l) {}

PResult* property::Not::eval(const PState* s) const
{
    //PResult* r = s->reach_cond();
    //PResult* res = &statement.eval(s)->negation().conjunction(*r);
    PResult* res = &statement.eval(s)->negation();
    //delete r;

    if (s->job.ip)
    {
        res->integer_shape_close_assign();
    }

    return res;
}

SProgram Not::codegen() const
{
    SProgram L;
    L.add(statement.codegen());
    L.add(StackMachine::NOT);

    return L;
}

string property::Not::to_string() const
{
    stringstream s;

    s << "not (" << statement.to_string() << ")";

    return s.str();
}

Polyhedron property::Not::constraint(const std::byte V[], const std::byte C[], const unsigned N) const
{
    Polyhedron P = statement.constraint(V, C, N);
    P.negation_assign();

    return P;
}

const GenericExpression* property::Not::copy(CTS& t) const
{
    return new property::Not(*static_cast<const Property*>(statement.copy(t)), decl_line);
}

const GenericExpression* property::Not::abstract_copy(CTS& t, const VarSet& S) const
{
    const Property* s = static_cast<const Property*>(statement.abstract_copy(t, S));
    if (s->is_abstracted())
    {
        return s;
    } else {
        return new property::Not(*s, decl_line);
    }
}

const GenericExpression* property::Not::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::Not(*static_cast<const Property*>(statement.instantiate(t, i, v)), decl_line);
}

const GenericExpression* property::Not::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::Not(*static_cast<const Property*>(statement.eliminate_refs(t, d)), decl_line);
}

void Not::prepare(CTS& t) const
{
    statement.prepare(t);
}

bool Not::is_simple() const
{
    return statement.is_simple();
}

bool Not::is_lconstraint() const
{
    return statement.is_lconstraint();
}

void Not::writes(VarSet& w) const
{
    statement.writes(w);
}

void Not::reads(VarSet& r) const
{
    statement.reads(r);
}

bool Not::has_cost() const
{
    return statement.has_cost();
}

const Property* Not::negation(CTS& t) const
{
    return static_cast<const Property*>(statement.copy(t));
}

Not::~Not()
{
    delete &statement;
}

// -----------------------------------------------------------------------
property::And::And(const Property& l, const Property& r, int line): DyadicOperator(l, r, line) {}

PResult* property::And::eval(const PState* s) const
{
    PResult * l = left.eval(s);
    PResult * r = &right.eval(s)->conjunction(*l);
    delete l;

    return r;
}

SProgram And::codegen() const
{
    SProgram L;
    SProgram R(right.codegen());
    L.add(left.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JZU);
    L.add(R.size() + 2);
    L.add(R);
    L.add(StackMachine::AND);

    return L;
}

string property::And::to_string() const
{
    stringstream s;

    s << "(" << left.to_string() << " and " << right.to_string() << ")";

    return s.str();
}

Polyhedron property::And::constraint(const std::byte V[], const std::byte C[], const unsigned N) const
{
    Polyhedron L = left.constraint(V, C, N);
    const Polyhedron R = right.constraint(V, C, N);
    L.intersection_assign(R);

    return L;
}

const GenericExpression* property::And::copy(CTS& t) const
{
    return new property::And(*static_cast<const Property*>(left.copy(t)), *static_cast<const Property*>(right.copy(t)), decl_line);
}

const GenericExpression* property::And::abstract_copy(CTS& t, const VarSet& S) const
{
    const Property* l = static_cast<const Property*>(left.abstract_copy(t, S));
    const Property* r = static_cast<const Property*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return r;
    } else if (r->is_abstracted()) {
        return l;
    } else {
        return new property::And(*l, *r, decl_line);
    }
}

const GenericExpression* property::And::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::And(*static_cast<const Property*>(left.instantiate(t, i, v)), *static_cast<const Property*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* property::And::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::And(*static_cast<const Property*>(left.eliminate_refs(t, d)), *static_cast<const Property*>(right.eliminate_refs(t, d)), decl_line);
}

list<VarSet> And::var_reads() const
{
    list<VarSet> L = left.var_reads();
    list<VarSet> R = right.var_reads();
    L.splice(L.end(), R); // Concatenate

    return L;
}

const Property* And::negation(CTS& t) const
{
    return new Or(*left.negation(t), *right.negation(t), decl_line);
}

// -----------------------------------------------------------------------
property::Or::Or(const Property& l, const Property& r, int line): DyadicOperator(l, r, line) {}

PResult* property::Or::eval(const PState* s) const
{
    PResult * l = left.eval(s);
    PResult * r = &right.eval(s)->disjunction(*l);
    delete l;

    return r;
}

SProgram Or::codegen() const
{
    SProgram L;
    SProgram R(right.codegen());
    L.add(left.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JNZU);
    L.add(R.size() + 2);
    L.add(R);
    L.add(StackMachine::OR);

    return L;
}

string property::Or::to_string() const
{
    stringstream s;

    s << "(" << left.to_string() << " or " << right.to_string() << ")";

    return s.str();
}

Polyhedron property::Or::constraint(const std::byte V[], const std::byte C[], const unsigned N) const
{
    Polyhedron L = left.constraint(V, C, N);
    const Polyhedron R = right.constraint(V, C, N);
    L.add_reduce(R);

    return L;
}

const GenericExpression* property::Or::copy(CTS& t) const
{
    return new property::Or(*static_cast<const Property*>(left.copy(t)), *static_cast<const Property*>(right.copy(t)), decl_line);
}

const GenericExpression* property::Or::abstract_copy(CTS& t, const VarSet& S) const
{
    const Property* l = static_cast<const Property*>(left.abstract_copy(t, S));
    const Property* r = static_cast<const Property*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new property::Or(*l, *r, decl_line);
    }
}

const GenericExpression* property::Or::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::Or(*static_cast<const Property*>(left.instantiate(t, i, v)), *static_cast<const Property*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* property::Or::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::Or(*static_cast<const Property*>(left.eliminate_refs(t, d)), *static_cast<const Property*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Or::negation(CTS& t) const
{
    return new And(*left.negation(t), *right.negation(t), decl_line);
}

// ---------------------------------------------------------------------------
void TemporalProperty::prepare(CTS& t) const
{
    phi.prepare(t);
    psi.prepare(t);
}
