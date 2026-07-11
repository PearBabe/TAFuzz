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

#include "simple_property.hh"
#include <vector>
#include <string>
#include <utility>
#include <iostream>
#include <sstream>

#include <valuation.hh>
#include <instruction.hh>
#include <linear_expression.hh>
#include <polyhedron.hh>
#include <cts.hh>
#include <pstate.hh>
#include <result.hh>

#include <color_output.hh>

#include <type.hh>
#include <access_expression.hh>
#include <lexpression.hh>
#include <rvalue.hh>
#include <stack_machine.hh>

using namespace std;
using namespace romeo;
using namespace romeo::lexpression;

// -----------------------------------------------------------------------------

LExpression::LExpression(int line): SimpleProperty(line)
{
}

LinearExpression LExpression::linear_expression(const byte V[], const byte C[]) const
{
    std::cerr << error_tag(color_output) << "Line " << decl_line << ": cannot use this operator with parameters: " << to_string() << std::endl;
    exit(1);
}

const LExpression* LExpression::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    std::cerr << error_tag(color_output) << "Line " << decl_line << ": cannot use this operator with parameters: " << to_string() << std::endl;
    exit(1);
}

bool LExpression::is_lexpression() const
{
    return true;
}

PResult* LExpression::eval(const PState* s) const
{
    RValue r(s->evaluate(this)); // FIXME: Not good: regenerates code each time
    PResult* res;

    if (r.is_unknown())
    {
        res = s->init_result(false);
        res->set_unknown(true);
    } else {
        res = s->init_result(r.to_int());
    }

    return res;

}

// -----------------------------------------------------------------------------

lexpression::Parameter::Parameter(const romeo::Parameter& v, int line): LExpression(line), param(v)
{
}

SProgram lexpression::Parameter::codegen() const
{
    cvalue v;
    if (!param.constant(v))
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": cannot evaluate parameter " << param.to_string() << ". Is it an undeclared variable?" << endl;
        exit(1);
    }

    SProgram L;
    L.add(StackMachine::PUSH);
    L.add(v);

    return L;
}

bool lexpression::Parameter::has_vars() const
{
    return false;
}

bool lexpression::Parameter::has_params() const
{
    cvalue v;
    return !param.constant(v);
}

bool lexpression::Parameter::is_const() const
{
    cvalue v;
    return param.constant(v);
}

bool lexpression::Parameter::is_numeric() const
{
    return true;
}


LinearExpression lexpression::Parameter::linear_expression(const byte V[], const byte C[]) const
{
    cvalue v;
    if (param.constant(v))
    {
        return LinearExpression(v);
    } else {
        return LinearExpression(Var(this->param.index()));
    }
}

string lexpression::Parameter::to_string() const
{
    stringstream s;

    s << param.to_string();

    return s.str();
}

const GenericExpression* lexpression::Parameter::copy(CTS& t) const
{
    const romeo::Parameter* v = t.lookup_parameter(param.label);
    if (v == NULL)
    {
        t.add_parameter(param);
        v = &(*(--t.end_parameters()));
    }

    return new Parameter(*v, decl_line);
}

const GenericExpression* lexpression::Parameter::abstract_copy(CTS& t, const VarSet& S) const
{
    return copy(t);
}

const GenericExpression* lexpression::Parameter::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* lexpression::Parameter::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return copy(t);
}

const LExpression* lexpression::Parameter::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    cvalue v;
    if (param.constant(v))
    {
        return new Litteral(v, decl_line);
    } else {
        const unsigned i = param.index();
        if (!negated)
        {
            if (ubs[i])
            {
                return new Litteral(ubounds[i], decl_line);
            } else {
                return new Litteral(INT_MAX, decl_line);
            }
        } else {
            if (lbs[i])
            {
                return new Litteral(lbounds[i], decl_line);
            } else {
                return new Litteral(INT_MIN, decl_line);
            }
        }
    }
}

// -----------------------------------------------------------------------------

lexpression::SyntaxParameter::SyntaxParameter(const unsigned i, int line): LExpression(line), id(i)
{
}

string lexpression::SyntaxParameter::to_string() const
{
    return string("$") + std::to_string(id);
}

const GenericExpression* lexpression::SyntaxParameter::copy(CTS& t) const
{
    return new SyntaxParameter(id, decl_line);
}

const GenericExpression* lexpression::SyntaxParameter::abstract_copy(CTS& t, const VarSet& S) const
{
    return copy(t);
}

const GenericExpression* lexpression::SyntaxParameter::instantiate(CTS& t, const unsigned i, const value v) const
{
    if (id == i)
    {
        return new Litteral(v, decl_line);
    } else {
        return copy(t);
    }
}

const GenericExpression* lexpression::SyntaxParameter::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new SyntaxParameter(id, decl_line);
}

bool SyntaxParameter::is_numeric() const
{
    return true;
}


// -----------------------------------------------------------------------------

lexpression::Abstracted::Abstracted(int line): LExpression(line)
{
}

SProgram lexpression::Abstracted::codegen() const
{
    SProgram L;
    L.add(StackMachine::PUSH);
    L.add(1);

    return L;
}

bool lexpression::Abstracted::is_const() const
{
    return true;
}

bool lexpression::Abstracted::is_abstracted() const
{
    return true;
}

string lexpression::Abstracted::to_string() const
{
    return "Abstracted";
}

const GenericExpression* lexpression::Abstracted::copy(CTS& t) const
{
    return new Abstracted(decl_line);
}

const GenericExpression* lexpression::Abstracted::abstract_copy(CTS& t, const VarSet& S) const
{
    return copy(t);
}

const GenericExpression* lexpression::Abstracted::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* lexpression::Abstracted::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return copy(t);
}



// -----------------------------------------------------------------------------
Litteral::Litteral(const RValue& v, int line): LExpression(line), val(v)
{
}

RValue Litteral::get_value() const
{
    return val;
}

LinearExpression Litteral::linear_expression(const byte V[], const byte C[]) const
{
    return LinearExpression(val.to_int());
}

SProgram Litteral::codegen() const
{
    SProgram L;

    if (!val.is_unknown())
    {
        L.add(val.get_type().rvalue_code(val));
    } else {
        L.add(StackMachine::PUSHU);
    }

    return L;
}

Variable Litteral::access(const byte V[], const byte C[], const byte** R) const
{
    *R = val.contents().p;
    return Variable(0, "#romeo_rvalue", val.get_type(), true, false, 0, 0, nullptr, true, false);
}

const Type& Litteral::access_type() const
{
    return val.get_type();
}

const Variable* Litteral::top_var() const
{
    return nullptr;
}

bool Litteral::has_constant_offsets() const
{
    return true;
}

string Litteral::to_string() const
{
    return val.to_string();
}

bool Litteral::is_static() const
{
    return true; // FIXME: depends if reference?
}

bool Litteral::is_numeric() const
{
    return val.is_numeric(); 
}

bool Litteral::is_const() const
{
    return true; // FIXME: depends if reference?
}

const LExpression* Litteral::copy(CTS& t) const
{
    return new Litteral(val, decl_line); 
}

bool Litteral::is_rvalue() const
{
    return true; 
}

const GenericExpression* Litteral::abstract_copy(CTS& t, const VarSet& S) const
{
    return copy(t);
}

const GenericExpression* Litteral::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* Litteral::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return copy(t);
}

const LExpression* Litteral::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    return copy(t);
}

bool Litteral::is_litteral(cvalue v) const
{
    return (val.to_int() == v);
}


// -----------------------------------------------------------------------------

RLValue::RLValue(const AccessExpression& x, int line): LExpression(line), e(x)
{
}

SProgram RLValue::codegen() const
{
    SProgram L;

    L.add(e.codegen());
    const Type& t = e.access_type();
    if (t.is_numeric())
    {
        L.add(t.load_code());
    }

    return L;
}

LinearExpression RLValue::linear_expression(const byte V[], const byte C[]) const
{
    return e.linear_expression(V, C);
}

const AccessExpression* RLValue::access_expr() const
{
    return &e;
}

bool RLValue::has_vars() const
{
    return e.has_vars();
}

bool RLValue::is_rlvalue() const
{
    return true;
}

bool RLValue::is_const() const
{
    return e.is_const(); // FIXME: should be true? Probably we don't care.
}

bool RLValue::is_static() const
{
    return e.is_static();
}

bool RLValue::is_numeric() const
{
    return e.is_numeric();
}

bool RLValue::has_params() const
{
    return e.has_params();
}

const Type& RLValue::get_type() const
{
    return e.access_type();
}

void RLValue::writes(VarSet& w) const
{
    e.writes(w);
}

void RLValue::reads(VarSet& r) const
{
    e.reads(r);
}

string RLValue::to_string() const
{
    return e.to_string();
}

const GenericExpression* RLValue::copy(CTS& t) const
{
    return new RLValue(*static_cast<const AccessExpression*>(e.copy(t)), decl_line);
}

const GenericExpression* RLValue::abstract_copy(CTS& t, const VarSet& S) const
{
    const AccessExpression* a = static_cast<const AccessExpression*>(e.abstract_copy(t, S));

    if (a->is_abstracted())
    {
        return a;
    } else {
        return new RLValue(*a, decl_line);
    }
}

const GenericExpression* lexpression::RLValue::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new RLValue(*static_cast<const AccessExpression*>(e.instantiate(t, i, v)), decl_line);
}

const GenericExpression* RLValue::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new RLValue(*static_cast<const AccessExpression*>(e.eliminate_refs(t, d)), decl_line);
}

const LExpression* RLValue::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    return static_cast<const LExpression*>(copy(t));
}

lexpression::RLValue::~RLValue()
{
    delete &e;
}

// -----------------------------------------------------------------------------

DyadicOperator::DyadicOperator(const LExpression& l, const LExpression& r, int line): LExpression(line), left(l), right(r)
{
}

bool DyadicOperator::has_vars() const
{
    return left.has_vars() || right.has_vars();
}

bool DyadicOperator::is_const() const
{
    return left.is_const() && right.is_const();
}

bool DyadicOperator::is_static() const
{
    return left.is_static() && right.is_static();
}

bool DyadicOperator::is_numeric() const
{
    return left.is_numeric() && right.is_numeric();
}

bool DyadicOperator::has_params() const
{
    return left.has_params() || right.has_params();
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

DyadicOperator::~DyadicOperator()
{
    delete &left;
    delete &right;
}

// -----------------------------------------------------------------------------

Addition::Addition(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Addition::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::ADD);

    return L;
}

LinearExpression Addition::linear_expression(const byte V[], const byte C[]) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return L+R;
}

string Addition::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " + " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Addition::copy(CTS& t) const
{
    return new Addition(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Addition::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Addition(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Addition::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Addition(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Addition::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Addition(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}


const LExpression* Addition::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    auto l = static_cast<const LExpression*>(left.abstract_parameters(t, negated, lbs, ubs, lbounds, ubounds)); 
    auto r = static_cast<const LExpression*>(right.abstract_parameters(t, negated, lbs, ubs, lbounds, ubounds));

    if (l->is_litteral(INT_MAX) || r->is_litteral(INT_MAX))
    {
        delete l;
        delete r;

        return new Litteral(INT_MAX, decl_line);
    } else {
        return new Addition(*l, *r, decl_line);
    }
}

// -----------------------------------------------------------------------------

Subtraction::Subtraction(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Subtraction::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::SUB);

    return L;
}

LinearExpression Subtraction::linear_expression(const byte V[], const byte C[]) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return L-R;
}

string Subtraction::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " - " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Subtraction::copy(CTS& t) const
{
    return new Subtraction(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Subtraction::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Subtraction(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Subtraction::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Subtraction(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Subtraction::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Subtraction(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const LExpression* Subtraction::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    auto l = static_cast<const LExpression*>(left.abstract_parameters(t, negated, lbs, ubs, lbounds, ubounds)); 
    auto r = static_cast<const LExpression*>(right.abstract_parameters(t, !negated, lbs, ubs, lbounds, ubounds));

    if (l->is_litteral(INT_MAX))
    {
        delete l;
        delete r;

        return new Litteral(INT_MAX, decl_line);
    } else {
        return new Subtraction(*l, *r, decl_line);
    }
}

// -----------------------------------------------------------------------------

Multiplication::Multiplication(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Multiplication::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::MUL);

    return L;
}

LinearExpression Multiplication::linear_expression(const byte V[], const byte C[]) const
{
    if (left.has_params())
    {
        const LinearExpression L = left.linear_expression(V, C);

        if (right.has_params())
        {
            std::cerr << error_tag(color_output) << "Line " << decl_line << ": only linear constraints are allowed with parameters: " << to_string() << std::endl;
            exit(1);
        } else {
            return L * SExpression(&right).evaluate(V, C).to_int();
        }
    } else {
        if (right.has_params())
        {
            const LinearExpression R = right.linear_expression(V, C);
            return R * SExpression(&left).evaluate(V, C).to_int();
        } else {
            return LinearExpression(SExpression(this).evaluate(V, C).to_int());
        }
    }
}

string Multiplication::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " * " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Multiplication::copy(CTS& t) const
{
    return new Multiplication(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Multiplication::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Multiplication(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Multiplication::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Multiplication(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Multiplication::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Multiplication(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const LExpression* Multiplication::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    cvalue cl = 0, cr = 0;
    bool l = !left.has_vars() && !left.has_params();
    if (l)
    {
        cl = SExpression(&left).evaluate(nullptr, nullptr).to_int();
    }

    bool r = !right.has_vars() && !right.has_params();
    if (r)
    {
        cr = SExpression(&right).evaluate(nullptr, nullptr).to_int();
    }

    if (!l && !r)
    {
        cerr << error_tag(color_output) << "Parameter abstraction requires constant coefficients for multiplication." << endl;
        exit(1);
    }
    
    auto lb = static_cast<const LExpression*>(left.abstract_parameters(t, negated != (cl < 0), lbs, ubs, lbounds, ubounds));
    auto rb = static_cast<const LExpression*>(right.abstract_parameters(t, negated != (cr < 0), lbs, ubs, lbounds, ubounds));

    if (l)
    {
        if (cl > 0)
        {
            if (rb->is_litteral(INT_MAX))
            {
                delete lb;
                delete rb;

                return new Litteral(INT_MAX, decl_line);
            } else if (rb->is_litteral(INT_MIN)) {
                delete lb;
                delete rb;

                return new Litteral(INT_MIN, decl_line);
            }
        } else if (cl < 0) {
            if (rb->is_litteral(INT_MAX))
            {
                delete lb;
                delete rb;

                return new Litteral(INT_MIN, decl_line);
            } else if (rb->is_litteral(INT_MIN)) {
                delete lb;
                delete rb;

                return new Litteral(INT_MAX, decl_line);
            }
        } else {
            delete lb;
            delete rb;

            return new Litteral(0, decl_line);
        }
    }

    if (r)
    {
        if (cr > 0)
        {
            if (lb->is_litteral(INT_MAX))
            {
                delete lb;
                delete rb;

                return new Litteral(INT_MAX, decl_line);
            } else if (lb->is_litteral(INT_MIN)) {
                delete lb;
                delete rb;

                return new Litteral(INT_MIN, decl_line);
            }
        } else if (cr < 0) {
            if (lb->is_litteral(INT_MAX))
            {
                delete lb;
                delete rb;

                return new Litteral(INT_MIN, decl_line);
            } else if (lb->is_litteral(INT_MIN)) {
                delete lb;
                delete rb;

                return new Litteral(INT_MAX, decl_line);
            }
        } else {
            delete lb;
            delete rb;

            return new Litteral(0, decl_line);
        }
    }

    return new Multiplication(*lb, *rb, decl_line);
}

// -----------------------------------------------------------------------------

Division::Division(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Division::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::DIV);

    return L;
}

string Division::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " / " << right.to_string() << " )";

    return s.str();
}

LinearExpression Division::linear_expression(const byte V[], const byte C[]) const
{
    if (right.has_params())
    {
        std::cerr << error_tag(color_output) << "Line " << decl_line << ": only linear constraints are allowed with parameters: "<< to_string() << std::endl;
        exit(1);
    } else {
        if (left.has_params())
        {
            const LinearExpression L = left.linear_expression(V, C);
            return L * SExpression(&right).evaluate(V, C).to_int();
        } else {
            return LinearExpression(SExpression(this).evaluate(V, C).to_int());
        }
    }
}

const GenericExpression* Division::copy(CTS& t) const
{
    return new Division(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Division::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Division(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Division::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Division(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Division::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Division(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const LExpression* Division::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    cvalue cr = 0;
    if (!right.has_vars() && !right.has_params())
    {
        cr = SExpression(&right).evaluate(nullptr, nullptr).to_int();
    } else {
        cerr << error_tag(color_output) << "Parameter abstraction requires constant coefficients for division." << endl;
        exit(1);
    }
    
    auto lb = static_cast<const LExpression*>(left.abstract_parameters(t, negated, lbs, ubs, lbounds, ubounds));
    auto rb = static_cast<const LExpression*>(right.abstract_parameters(t, negated != (cr < 0), lbs, ubs, lbounds, ubounds));

    if (cr > 0)
    {
        if (lb->is_litteral(INT_MAX))
        {
            delete lb;
            delete rb;

            return new Litteral(INT_MAX, decl_line);
        } else if (lb->is_litteral(INT_MIN)) {
            delete lb;
            delete rb;

            return new Litteral(INT_MIN, decl_line);
        }
    } else if (cr < 0) {
        if (lb->is_litteral(INT_MAX))
        {
            delete lb;
            delete rb;

            return new Litteral(INT_MIN, decl_line);
        } else if (lb->is_litteral(INT_MIN)) {
            delete lb;
            delete rb;

            return new Litteral(INT_MAX, decl_line);
        }
    } else {
        delete lb;
        delete rb;

        return new Litteral(0, decl_line);
    }

    return new Division(*lb, *rb, decl_line);
}

// -----------------------------------------------------------------------------

Modulo::Modulo(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Modulo::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::MOD);

    return L;
}

string Modulo::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " % " << right.to_string() << " )";

    return s.str();
}

LinearExpression Modulo::linear_expression(const byte V[], const byte C[]) const
{
    if (left.has_params() || right.has_params())
    {
        std::cerr << error_tag(color_output) << "Line " << decl_line << ": only linear constraints are allowed with parameters: "<< to_string() << std::endl;
        exit(1);
    } else {
        return LinearExpression(SExpression(this).evaluate(V, C).to_int());
    }
}

const GenericExpression* Modulo::copy(CTS& t) const
{
    return new Modulo(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Modulo::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Modulo(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Modulo::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Modulo(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Modulo::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Modulo(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}


// -----------------------------------------------------------------------------

Min::Min(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Min::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::MIN);

    return L;
}

string Min::to_string() const
{
    stringstream s;

    s << "min ( " << left.to_string() << ", " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Min::copy(CTS& t) const
{
    return new Min(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Min::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Min(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Min::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Min(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Min::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Min(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

// -----------------------------------------------------------------------------

Max::Max(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Max::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::MAX);

    return L;
}

string Max::to_string() const
{
    stringstream s;

    s << "max ( " << left.to_string() << ", " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Max::copy(CTS& t) const
{
    return new Max(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Max::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Max(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::Max::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Max(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::Max::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Max(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}


// -----------------------------------------------------------------------------

BitNot::BitNot(const LExpression& l, int line): LExpression(line), e(l) 
{
}

SProgram BitNot::codegen() const
{
    SProgram L;
    L.add(e.codegen());
    L.add(StackMachine::BIT_NOT);

    return L;
}

bool BitNot::is_numeric() const
{
    return e.is_numeric();
}

string BitNot::to_string() const
{
    stringstream s;

    s << "~ " << "( " << e.to_string() << " )";

    return s.str();
}

const GenericExpression* BitNot::copy(CTS& t) const
{
    return new BitNot(*static_cast<const LExpression*>(e.copy(t)), decl_line);
}

const GenericExpression* BitNot::abstract_copy(CTS& t, const VarSet& S) const
{
    return new BitNot(*static_cast<const LExpression*>(e.abstract_copy(t, S)), decl_line);
}

const GenericExpression* lexpression::BitNot::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new BitNot(*static_cast<const LExpression*>(e.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::BitNot::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new BitNot(*static_cast<const LExpression*>(e.eliminate_refs(t, d)), decl_line);
}


// -----------------------------------------------------------------------------

BitAnd::BitAnd(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram BitAnd::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::BIT_AND);

    return L;
}

string BitAnd::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " & " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* BitAnd::copy(CTS& t) const
{
    return new BitAnd(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* BitAnd::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new BitAnd(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::BitAnd::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new BitAnd(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::BitAnd::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new BitAnd(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

// -----------------------------------------------------------------------------

BitOr::BitOr(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram BitOr::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::BIT_OR);

    return L;
}

string BitOr::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " | " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* BitOr::copy(CTS& t) const
{
    return new BitOr(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* BitOr::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new BitOr(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::BitOr::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new BitOr(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::BitOr::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new BitOr(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

// -----------------------------------------------------------------------------

ShiftL::ShiftL(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram ShiftL::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::SHIFTL);

    return L;
}

string ShiftL::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " << " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* ShiftL::copy(CTS& t) const
{
    return new ShiftL(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* ShiftL::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new ShiftL(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::ShiftL::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new ShiftL(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::ShiftL::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new ShiftL(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

// -----------------------------------------------------------------------------

ShiftR::ShiftR(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram ShiftR::codegen() const
{
    SProgram L;
    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::SHIFTR);

    return L;
}

string ShiftR::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " >> " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* ShiftR::copy(CTS& t) const
{
    return new ShiftR(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* ShiftR::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new ShiftR(*l, *r, decl_line);
    }
}

const GenericExpression* lexpression::ShiftR::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new ShiftR(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* lexpression::ShiftR::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new ShiftR(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}



// -----------------------------------------------------------------------
lexpression::ClockVariable::ClockVariable(const Transition* t, int line): LExpression(line), transition(t) {}


string lexpression::ClockVariable::to_string() const
{
    stringstream s;

    s << "clock(" << transition->label << ")";

    return s.str();
}

bool lexpression::ClockVariable::is_clock_var() const
{
    return true;
}


const property::FiredTransition* lexpression::ClockVariable::to_property() const
{
    return new property::FiredTransition(transition, decl_line);
}

const GenericExpression* lexpression::ClockVariable::copy(CTS& t) const
{
    return new ClockVariable(transition, decl_line);
}

const GenericExpression* lexpression::ClockVariable::abstract_copy(CTS& t, const VarSet& S) const
{
    return new ClockVariable(transition, decl_line);
}

const GenericExpression* lexpression::ClockVariable::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new ClockVariable(transition, decl_line);
}

const GenericExpression* lexpression::ClockVariable::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new ClockVariable(transition, decl_line);
}
