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

#include <vector>
#include <string>
#include <utility>
#include <iostream>
#include <sstream>

#include <lconstraint.hh>
#include <lexpression.hh>
#include <rvalue.hh>
#include <access_expression.hh>
#include <stack_machine.hh>

#include <property.hh>

#include <valuation.hh>
#include <linear_expression.hh>
#include <polyhedron.hh>
#include <cts.hh>
#include <result.hh>
#include <pstate.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::lconstraint;

LConstraint::LConstraint(int line): LExpression(line)
{
}

bool LConstraint::is_lconstraint() const
{
    return true;
}

// -----------------------------------------------------------------------------

DyadicOperator::DyadicOperator(const LExpression& l, const LExpression& r, int line): LConstraint(line), left(l), right(r)
{
}

bool DyadicOperator::has_vars() const
{
    return left.has_vars() || right.has_vars();
}

bool DyadicOperator::has_params() const
{
    return left.has_params() || right.has_params();
}

bool DyadicOperator::is_const() const
{
    return left.is_const() && right.is_const();
}

bool DyadicOperator::is_static() const
{
    return left.is_static() && right.is_static();
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

Eq::Eq(const LExpression& l, const LExpression& r, int line): lconstraint::DyadicOperator(l, r, line)
{
}

SProgram Eq::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::EQ);

    return L;
}

Polyhedron Eq::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return Polyhedron(L-R, CSTR_EQ, N);
}

string Eq::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " == " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Eq::copy(CTS& t) const
{
    return new Eq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Eq::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Eq(*l, *r, decl_line);
    }
}

const GenericExpression* Eq::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Eq(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Eq::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Eq(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Eq::negation(CTS& t) const
{
    return new Neq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

// -----------------------------------------------------------------------------

Neq::Neq(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Neq::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::NEQ);

    return L;
}

Polyhedron Neq::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression e = L - right.linear_expression(V, C);

    Polyhedron P(e, CSTR_GSTRICT, N);
    const Polyhedron Q(e, CSTR_LSTRICT, N);
    P.add(Q);

    return P;
}

string Neq::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " != " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Neq::copy(CTS& t) const
{
    return new Neq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Neq::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Neq(*l, *r, decl_line);
    }
}

const GenericExpression* Neq::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Neq(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Neq::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Neq(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Neq::negation(CTS& t) const
{
    return new Eq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

// -----------------------------------------------------------------------------

Leq::Leq(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Leq::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::LEQ);

    return L;
}

Polyhedron Leq::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return Polyhedron(L-R, CSTR_LWEAK, N);
}

string Leq::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " <= " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Leq::copy(CTS& t) const
{
    return new Leq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Leq::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Leq(*l, *r, decl_line);
    }
}

const GenericExpression* Leq::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Leq(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Leq::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Leq(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Leq::negation(CTS& t) const
{
    return new Greater(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}


// -----------------------------------------------------------------------------

Geq::Geq(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Geq::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::GEQ);

    return L;
}

Polyhedron Geq::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return Polyhedron(L-R, CSTR_GWEAK, N);
}

string Geq::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " >= " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Geq::copy(CTS& t) const
{
    return new Geq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Geq::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Geq(*l, *r, decl_line);
    }
}

const GenericExpression* Geq::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Geq(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Geq::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Geq(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Geq::negation(CTS& t) const
{
    return new Less(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

// -----------------------------------------------------------------------------

Less::Less(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Less::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::LOWER);

    return L;
}

Polyhedron Less::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return Polyhedron(L-R, CSTR_LSTRICT, N);
}

string Less::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " < " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Less::copy(CTS& t) const
{
    return new Less(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Less::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Less(*l, *r, decl_line);
    }
}

const GenericExpression* Less::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Less(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Less::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Less(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Less::negation(CTS& t) const
{
    return new Geq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

// -----------------------------------------------------------------------------

Greater::Greater(const LExpression& l, const LExpression& r, int line): DyadicOperator(l, r, line)
{
}

SProgram Greater::codegen() const
{
    SProgram L;

    L.add(left.codegen());
    L.add(right.codegen());
    L.add(StackMachine::GREATER);

    return L;
}

Polyhedron Greater::constraint(const byte V[], const byte C[], const unsigned N) const
{
    const LinearExpression L = left.linear_expression(V, C);
    const LinearExpression R = right.linear_expression(V, C);

    return Polyhedron(L-R, CSTR_GSTRICT, N);
}

string Greater::to_string() const
{
    stringstream s;

    s << "( " << left.to_string() << " > " << right.to_string() << " )";

    return s.str();
}

const GenericExpression* Greater::copy(CTS& t) const
{
    return new Greater(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

const GenericExpression* Greater::abstract_copy(CTS& t, const VarSet& S) const
{
    const LExpression* l = static_cast<const LExpression*>(left.abstract_copy(t, S));
    const LExpression* r = static_cast<const LExpression*>(right.abstract_copy(t, S));

    if (l->is_abstracted())
    {
        return l;
    } else if (r->is_abstracted()) {
        return r;
    } else {
        return new Greater(*l, *r, decl_line);
    }
}

const GenericExpression* Greater::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Greater(*static_cast<const LExpression*>(left.instantiate(t, i, v)), *static_cast<const LExpression*>(right.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Greater::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Greater(*static_cast<const LExpression*>(left.eliminate_refs(t, d)), *static_cast<const LExpression*>(right.eliminate_refs(t, d)), decl_line);
}

const Property* Greater::negation(CTS& t) const
{
    return new Leq(*static_cast<const LExpression*>(left.copy(t)), *static_cast<const LExpression*>(right.copy(t)), decl_line);
}

// -----------------------------------------------------------------------------

True::True(int line): LConstraint(line)
{
}

bool True::is_const() const
{
    return true;
}

bool True::is_static() const
{
    return true;
}

SProgram True::codegen() const
{
    SProgram L;

    L.add(StackMachine::PUSH);
    L.add(1);

    return L;
}

Polyhedron True::constraint(const byte V[], const byte C[], const unsigned N) const
{
    return Polyhedron(N,true);
}

string True::to_string() const
{
    stringstream s;

    s << "true";

    return s.str();
}

const GenericExpression* True::copy(CTS& t) const
{
    return new True(decl_line);
}

const GenericExpression* True::abstract_copy(CTS& t, const VarSet& S) const
{
    return new True(decl_line);
}

const GenericExpression* True::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* True::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new True(decl_line);
}

const Property* True::negation(CTS& t) const
{
    return new False(decl_line);
}

// -----------------------------------------------------------------------------

False::False(int line): LConstraint(line)
{
}

bool False::is_const() const
{
    return true;
}

bool False::is_static() const
{
    return true;
}

SProgram False::codegen() const
{
    SProgram L;

    L.add(StackMachine::PUSH);
    L.add(0);

    return L;
}

Polyhedron False::constraint(const byte V[], const byte C[], const unsigned N) const
{
    return Polyhedron(N,false);
}

string False::to_string() const
{
    stringstream s;

    s << "false";

    return s.str();
}

const GenericExpression* False::copy(CTS& t) const
{
    return new False(decl_line);
}

const GenericExpression* False::abstract_copy(CTS& t, const VarSet& S) const
{
    return new False(decl_line);
}

const GenericExpression* False::instantiate(CTS& t, const unsigned i, const value v) const
{
    return copy(t);
}

const GenericExpression* False::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new False(decl_line);
}

const Property* False::negation(CTS& t) const
{
    return new True(decl_line);
}

// -----------------------------------------------------------------------------

Forall::Forall(const lexpression::LValue& i, const LExpression& l, const LExpression& u, const Property& c, int line): LConstraint(line), idx(i), min_idx(l), max_idx(u), constr(c)
{
}

SProgram Forall::codegen() const
{
    SProgram L;

    // idx = idx + 1
    SProgram I;
    I.add(idx.codegen());
    I.add(StackMachine::LOAD32);
    I.add(StackMachine::PUSH);
    I.add(1);
    I.add(StackMachine::ADD);
    I.add(idx.codegen());
    I.add(StackMachine::STORE32);
    
    // Set idx to min_idx
    L.add(min_idx.codegen());
    L.add(idx.codegen());
    L.add(StackMachine::STORE32);

    // Initialize result in loop
    L.add(StackMachine::PUSH);
    L.add(1);

    SProgram B;
    // Discard previous result
    B.add(StackMachine::POP);

    // Test while condition
    B.add(idx.codegen());
    B.add(StackMachine::LOAD32);
    B.add(max_idx.codegen());
    B.add(StackMachine::LEQ);

    // If the condition is false, we have reached the end
    // of the loop and the property holds
    B.add(StackMachine::JNZ);
    B.add(5); // 2 for push and 2 for jmp and 1 for this value
    
    // Push the final result
    B.add(StackMachine::PUSH);
    B.add(1);

    // And move to the end
    B.add(StackMachine::JMP);
    
    SProgram C;
    // Value of the condition
    C.add(constr.codegen());
    
    // Save result
    C.add(StackMachine::DUP);
    
    // Skip to the end if false, with 0 still on the stack
    C.add(StackMachine::JZ);
    C.add(I.size() + 3); // counting 1 for this value and 2 for JMP
    C.add(I);

    // Go back to condition testing, still with a 1 on the stack
    C.add(StackMachine::JMP);
    C.add(-(word) (B.size() + C.size() + 1));

    B.add(C.size() + 1);
    
    L.add(B);
    L.add(C);

    return L;
}

string Forall::to_string() const
{
    stringstream s;

    s << "forall " << idx << " in " << min_idx << ", " << max_idx << ": " << constr;

    return s.str();
}

const GenericExpression* Forall::copy(CTS& t) const
{
    return new Forall(*static_cast<const lexpression::LValue*>(idx.copy(t)),
                      *static_cast<const LExpression*>(min_idx.copy(t)),
                      *static_cast<const LExpression*>(max_idx.copy(t)),
                      *static_cast<const LConstraint*>(constr.copy(t)),
                      decl_line);
}

const GenericExpression* Forall::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Forall(*static_cast<const lexpression::LValue*>(idx.abstract_copy(t, S)),
                      *static_cast<const LExpression*>(min_idx.abstract_copy(t, S)),
                      *static_cast<const LExpression*>(max_idx.abstract_copy(t, S)),
                      *static_cast<const LConstraint*>(constr.abstract_copy(t, S)),
                      decl_line);
}

const GenericExpression* Forall::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Forall(*static_cast<const lexpression::LValue*>(idx.instantiate(t, i, v)),
                      *static_cast<const LExpression*>(min_idx.instantiate(t, i, v)),
                      *static_cast<const LExpression*>(max_idx.instantiate(t, i, v)),
                      *static_cast<const LConstraint*>(constr.instantiate(t, i, v)),
                      decl_line);
}

const GenericExpression* Forall::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Forall(*static_cast<const lexpression::LValue*>(idx.eliminate_refs(t, d)),
                      *static_cast<const LExpression*>(min_idx.eliminate_refs(t, d)),
                      *static_cast<const LExpression*>(max_idx.eliminate_refs(t, d)),
                      *static_cast<const LConstraint*>(constr.eliminate_refs(t, d)),
                      decl_line);
}


// -----------------------------------------------------------------------------

Exists::Exists(const lexpression::LValue& i, const LExpression& l, const LExpression& u, const Property& c, int line): LConstraint(line), idx(i), min_idx(l), max_idx(u), constr(c)
{
}

SProgram Exists::codegen() const
{
    SProgram L;

    // idx = idx + 1
    SProgram I;
    I.add(idx.codegen());
    I.add(StackMachine::LOAD32);
    I.add(StackMachine::PUSH);
    I.add(1);
    I.add(StackMachine::ADD);
    I.add(idx.codegen());
    I.add(StackMachine::STORE32);
    
    // Set idx to min_idx
    L.add(min_idx.codegen());
    L.add(idx.codegen());
    L.add(StackMachine::STORE32);

    // Initialize result in loop
    L.add(StackMachine::PUSH);
    L.add(1);

    SProgram B;
    // Discard previous result
    B.add(StackMachine::POP);

    // Test while condition
    B.add(idx.codegen());
    B.add(StackMachine::LOAD32);
    B.add(max_idx.codegen());
    B.add(StackMachine::LEQ);

    // If the condition is false, we have reached the end
    // of the loop and the property is false
    B.add(StackMachine::JNZ);
    B.add(5); // 2 for push and 2 for jmp and 1 for this value
    
    // Push the final result
    B.add(StackMachine::PUSH);
    B.add(0);

    // And move to the end
    B.add(StackMachine::JMP);
    
    SProgram C;
    // Value of the condition
    C.add(constr.codegen());
    
    // Save result
    C.add(StackMachine::DUP);
    
    // Skip to the end if true, with 1 still on the stack
    C.add(StackMachine::JNZ);
    C.add(I.size() + 3); // counting 1 for this value and 2 for JMP
    C.add(I);

    // Go back to condition testing, still with a 1 on the stack
    C.add(StackMachine::JMP);
    C.add(-(word) (B.size() + C.size() + 1));

    B.add(C.size() + 1);
    
    L.add(B);
    L.add(C);

    return L;
}

string Exists::to_string() const
{
    stringstream s;

    s << "exists " << idx << " in " << min_idx << ", " << max_idx << ": " << constr;

    return s.str();
}

const GenericExpression* Exists::copy(CTS& t) const
{
    return new Exists(*static_cast<const lexpression::LValue*>(idx.copy(t)),
                      *static_cast<const LExpression*>(min_idx.copy(t)),
                      *static_cast<const LExpression*>(max_idx.copy(t)),
                      *static_cast<const LConstraint*>(constr.copy(t)),
                      decl_line);
}

const GenericExpression* Exists::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Exists(*static_cast<const lexpression::LValue*>(idx.abstract_copy(t, S)),
                      *static_cast<const LExpression*>(min_idx.abstract_copy(t, S)),
                      *static_cast<const LExpression*>(max_idx.abstract_copy(t, S)),
                      *static_cast<const LConstraint*>(constr.abstract_copy(t, S)),
                      decl_line);
}

const GenericExpression* Exists::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Exists(*static_cast<const lexpression::LValue*>(idx.instantiate(t, i, v)),
                      *static_cast<const LExpression*>(min_idx.instantiate(t, i, v)),
                      *static_cast<const LExpression*>(max_idx.instantiate(t, i, v)),
                      *static_cast<const LConstraint*>(constr.instantiate(t, i, v)),
                      decl_line);
}

const GenericExpression* Exists::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Exists(*static_cast<const lexpression::LValue*>(idx.eliminate_refs(t, d)),
                      *static_cast<const LExpression*>(min_idx.eliminate_refs(t, d)),
                      *static_cast<const LExpression*>(max_idx.eliminate_refs(t, d)),
                      *static_cast<const LConstraint*>(constr.eliminate_refs(t, d)),
                      decl_line);
}


