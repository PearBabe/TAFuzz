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

#include <access_expression.hh>
#include <color_output.hh>

#include <variable.hh>
#include <type.hh>
#include <rvalue.hh>
#include <stack_machine.hh>
#include <cts.hh>
#include <valuation.hh>
#include <linear_expression.hh>

using namespace std;
using namespace romeo;
using namespace romeo::lexpression;

AccessExpression::AccessExpression(int line): LExpression(line)
{
}

bool AccessExpression::is_access() const
{
    return true;
}

bool AccessExpression::is_numeric() const
{
    return access_type().is_numeric();
}

bool AccessExpression::has_constant_offsets() const
{
    return true;
}

// -----------------------------------------------------------------------------

LValue::LValue(const Variable& v, int line): AccessExpression(line), var(v)
{
}

bool LValue::has_vars() const
{
    return true;
}

bool LValue::is_lvalue() const
{
    return true;
}

bool LValue::is_const() const
{
    return var.is_constant();
}

bool LValue::is_static() const
{
    return var.is_static();
}

bool LValue::has_params() const
{
    return false;
}

LinearExpression LValue::linear_expression(const byte V[], const byte C[]) const
{
    RLValue J(*this, decl_line);
    return LinearExpression(SExpression(&J).evaluate(V, C).to_int());
}

string LValue::to_string() const
{
    stringstream s;

    s << var.to_string();

    return s.str();
}

const GenericExpression* LValue::copy(CTS& t) const
{
    const Variable* v = t.lookup_variable_by_id(var.id);
    if (v == nullptr)
    {
        cerr << error_tag(color_output) << "Line "<< decl_line << ": Could not find variable when copying LValue." << endl;
        exit(1);
    }

    return new LValue(*v, decl_line);
}

const GenericExpression* LValue::abstract_copy(CTS& t, const VarSet& S) const
{
    if (S.count(var.get_coffset()))
    {
        return copy(t);
    } else {
        return new Abstracted(decl_line);
    }
}

const GenericExpression* LValue::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* LValue::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return copy(t);
}

const LExpression* LValue::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    return static_cast<const LExpression*>(copy(t));
}


SProgram LValue::codegen() const
{
    SProgram L;
    if (var.is_static())
    {
        L.add(StackMachine::ADDRC);
    } else {
        L.add(StackMachine::ADDR);
    }

    L.add(var.get_offset());

    return L;
}

Variable LValue::access(const byte V[], const byte C[], const byte** RV) const
{   
    if (RV != nullptr)
    {
        *RV = V;
    }

    return var;
}

const Type& LValue::access_type() const
{
    return var.get_reftype();
}

const Variable* LValue::top_var() const
{
    return &var;
}

void LValue::writes(VarSet& w) const
{
    // Add all involved memory byte cells
    var.insert_accesses(w);
}

void LValue::reads(VarSet& r) const
{
    // Add all involved memory byte cells
    var.insert_accesses(r);
}

// -----------------------------------------------------------------------------

ReferenceAccess::ReferenceAccess(const Variable& v, int line): LValue(v, line), bound_expr(nullptr)
{
}

ReferenceAccess::ReferenceAccess(const Variable& v, const GenericExpression* e, int line): LValue(v, line), bound_expr(e)
{
}

const GenericExpression* ReferenceAccess::copy(CTS& t) const
{
    const Variable* v = t.lookup_variable_by_id(var.id);
    if (v == nullptr)
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": Could not find variable when copying LValue." << endl;
        exit(1);
    }

    return new ReferenceAccess(*v, (bound_expr != nullptr ? bound_expr->copy(t): nullptr), decl_line);
}

const GenericExpression* ReferenceAccess::abstract_copy(CTS& t, const VarSet& S) const
{
    return copy(t);
}

const GenericExpression* ReferenceAccess::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* ReferenceAccess::eliminate_refs(CTS& t, const ref_dict& d) const
{
    if (bound_expr ==  nullptr)
    {
        auto x = d.find(var.get_offset());
        if (x == d.end())
        {
            cerr << error_tag(color_output) << "Line " << decl_line << ": cannot find a bound expression for reference " << var << endl;
            exit(1);
        }
    
        return new ReferenceAccess(var, x->second->copy(t), decl_line);
    } else {
        return new ReferenceAccess(var, bound_expr->eliminate_refs(t, d), decl_line);
    }
}

bool ReferenceAccess::is_refaccess() const
{
    return true;
}

SProgram ReferenceAccess::codegen() const
{
    SProgram L;
    if (var.is_static())
    {
        L.add(StackMachine::ADDRC);
    } else {
        L.add(StackMachine::ADDR);
    }

    L.add(var.get_offset());
    L.add(StackMachine::LOADP); // Got the pointed address

    return L;
}

Variable ReferenceAccess::access(const byte V[], const byte C[], const byte** RV) const
{   
    const byte* R;
    const byte* S = (var.is_constant() ? C: V);

    if (S != nullptr)
    {
        Variable x(var.ref_access(S, &R));
        
        if (x.is_static())
        {
            *RV = nullptr;
        } else {
            *RV = R;
        }

        return x;
    } else {
        // if S is null, we assume that we are actually doing some write/read or similar static
        // analyses so we use the real expression.
        if (bound_expr != nullptr)
        {
            return static_cast<const AccessExpression*>(bound_expr)->access(V, C, RV);
        } else {
            cerr << error_tag(color_output) << "Line " << decl_line << ": access: No bound expression for reference." << endl;
            exit(1);
        }
    }
}

void ReferenceAccess::reads(VarSet& w) const
{
    if (bound_expr != nullptr)
    {
        static_cast<const AccessExpression*>(bound_expr)->reads(w);
    } else {
        cerr << error_tag(color_output) << "Line " << decl_line << ": reads: No bound expression for reference." << endl;
        exit(1);
    }
}

void ReferenceAccess::writes(VarSet& w) const
{
    if (bound_expr != nullptr)
    {
        static_cast<const AccessExpression*>(bound_expr)->writes(w);
    } else {
        cerr << error_tag(color_output) << "Line " << decl_line << ": writes: No bound expression for reference." << endl;
        exit(1);
    }
}

// -----------------------------------------------------------------------------

AccessOperator::AccessOperator(const AccessExpression& x, int line): AccessExpression(line), e(x) {}

const Variable* AccessOperator::top_var() const
{
    return e.top_var();
}

// -----------------------------------------------------------------------------

SubscriptAccess::SubscriptAccess(const AccessExpression& e, const SExpression& s, int line): AccessOperator(e, line), subscript(s) {}

const GenericExpression* SubscriptAccess::copy(CTS& t) const
{
    return new SubscriptAccess(*static_cast<const AccessExpression*>(e.copy(t)), subscript.copy(t), decl_line);
}

const GenericExpression* SubscriptAccess::abstract_copy(CTS& t, const VarSet& S) const
{
    return new SubscriptAccess(*static_cast<const AccessExpression*>(e.abstract_copy(t, S)), subscript.abstract_copy(t, S), decl_line);
}

const GenericExpression* SubscriptAccess::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new SubscriptAccess(*static_cast<const AccessExpression*>(e.instantiate(t, i, v)), subscript.instantiate(t, i, v), decl_line);
}

const GenericExpression* SubscriptAccess::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new SubscriptAccess(*static_cast<const AccessExpression*>(e.eliminate_refs(t, d)), subscript.eliminate_refs(t, d), decl_line);
}

SProgram SubscriptAccess::codegen() const
{
    const Type& t = access_type();

    SProgram L;
    L.add(e.codegen());
    subscript.add_code(L);
    L.add(StackMachine::INDEX);
    L.add(e.access_type().size() / t.size());
    L.add(t.size());
    L.add(decl_line);

    return L;
}

Variable SubscriptAccess::access(const byte V[], const byte C[], const byte** RV) const
{   
    const Variable var = e.access(V, C, RV);
    
    RValue s(subscript.evaluate(V, C));

    if (!s.is_unknown())
    {
        return var.subscript_access(s.to_int(), decl_line);
    } else {
        return Variable(0, "#romeo_unknown_access", var.get_type(), false, true, var.get_offset(), var.get_coffset(), nullptr, var.is_utility(), var.is_state()); // Use static not constant (wich is normally not possible) to indicate an unknown variable
    }
}

const Type& SubscriptAccess::access_type() const
{
    const Type& t = e.access_type();

    return t.subscript_access(0, 0, false, false, decl_line).get_reftype(); // we can look at any element so we take the first one
}

string SubscriptAccess::to_string() const
{
    stringstream s;

    s << e.to_string() << "[" << subscript << "]";

    return s.str();
}

void SubscriptAccess::writes(VarSet& w) const
{
    if (has_constant_offsets())
    {
        const RValue ms = subscript.evaluate(nullptr, CTS::current_cts->statics);
        const Variable var = e.access(nullptr, CTS::current_cts->statics, nullptr);
        if (ms.is_unknown())
        {
            var.insert_accesses(w);
        } else {
            const value s = ms.to_int();

            var.subscript_access(s, decl_line).insert_accesses(w);
        }
    } else {
        e.writes(w);
    }
}

void SubscriptAccess::reads(VarSet& r) const
{
    if (has_constant_offsets())
    {
        const RValue ms = subscript.evaluate(nullptr, CTS::current_cts->statics);
        const Variable var = e.access(nullptr, CTS::current_cts->statics, nullptr);
        if (ms.is_unknown())
        {
            var.insert_accesses(r);
        } else {
            const value s = ms.to_int();

            var.subscript_access(s, decl_line).insert_accesses(r);
        }
    } else {
        e.reads(r);
        subscript.reads(r);
    }
}

bool SubscriptAccess::is_const() const
{
    return subscript.is_const() && e.is_const();
}

bool SubscriptAccess::is_static() const
{
    return subscript.is_static() && e.is_static(); 
}

bool SubscriptAccess::has_constant_offsets() const
{
    return subscript.is_static() && e.has_constant_offsets();
}

// -----------------------------------------------------------------------------

FieldAccess::FieldAccess(const AccessExpression& e, const unsigned s, int line): AccessOperator(e, line), field(s) {}

const GenericExpression* FieldAccess::copy(CTS& t) const
{
    return new FieldAccess(*static_cast<const AccessExpression*>(e.copy(t)), field, decl_line);
}

const GenericExpression* FieldAccess::abstract_copy(CTS& t, const VarSet& S) const
{
    return new FieldAccess(*static_cast<const AccessExpression*>(e.abstract_copy(t, S)), field, decl_line);
}

const GenericExpression* FieldAccess::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new FieldAccess(*static_cast<const AccessExpression*>(e.instantiate(t, i, v)), field, decl_line);
}

const GenericExpression* FieldAccess::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new FieldAccess(*static_cast<const AccessExpression*>(e.eliminate_refs(t, d)), field, decl_line);
}

SProgram FieldAccess::codegen() const
{
    SProgram L;
    const Type& t = e.access_type();

    L.add(e.codegen());
    L.add(StackMachine::PUSH);
    L.add(t.field_offset(field));
    L.add(StackMachine::ADDP);

    return L;
}

Variable FieldAccess::access(const byte V[], const byte C[], const byte** RV) const
{
    const Variable var = e.access(V, C, RV);
    
    return var.field_access(field, decl_line);
}

const Type& FieldAccess::access_type() const
{
    const Type& t = e.access_type();

    return t.field_access(field, 0, false, false, decl_line).get_reftype();
}

string FieldAccess::to_string() const
{
    stringstream s;

    s << e.to_string() << "." << field;

    return s.str();
}

bool FieldAccess::has_constant_offsets() const
{
    return e.has_constant_offsets();
}

bool FieldAccess::is_const() const
{
    return e.is_const();
}

bool FieldAccess::is_static() const
{
    return e.is_static(); 
}

void FieldAccess::writes(VarSet& w) const
{
    if (has_constant_offsets())
    {
        const Variable var = e.access(nullptr, CTS::current_cts->statics, nullptr);
        if (var.is_static() && !var.is_constant()) // unknown variable
        {
            var.insert_accesses(w);
        } else { 
            var.field_access(field, decl_line).insert_accesses(w);
        }
    } else {
        e.writes(w);
    }
}

void FieldAccess::reads(VarSet& r) const
{
    if (has_constant_offsets())
    {
        const Variable var = e.access(nullptr, CTS::current_cts->statics, nullptr);
        if (var.is_static() && !var.is_constant()) // unknown variable
        {
            var.insert_accesses(r);
        } else { 
            var.field_access(field, decl_line).insert_accesses(r);
        }
    } else {
        e.reads(r);
    }
}


