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

#include <instruction.hh>
#include <access_expression.hh>
#include <valuation.hh>
#include <linear_expression.hh>
#include <polyhedron.hh>
#include <cts.hh>
#include <type.hh>

#include <stack_machine.hh>
#include <rvalue.hh>
#include <lexpression.hh>
#include <property.hh>
#include <lconstraint.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::instruction;

// -----------------------------------------------------------------------------

Instruction::Instruction(int l): GenericExpression(l)
{
}

bool Instruction::is_nop() const
{
    return false;
}

bool Instruction::is_instruction() const
{
    return true;
}

// -----------------------------------------------------------------------------

Assignment::Assignment(const lexpression::AccessExpression& x, const LExpression& r, int  l): Instruction(l), v(x), e(r)
{
}

SProgram Assignment::codegen() const
{
    SProgram L;
    
    const Type& t = v.access_type();
    L.add(e.codegen());
    L.add(v.codegen());
    L.add(t.store_code());

    return L;
}

bool Assignment::has_vars() const
{
    return true;
}

bool Assignment::has_params() const
{
    return e.has_params();
}

string Assignment::to_string() const
{
    stringstream s;

    s << v.to_string() << " = " << e.to_string();

    return s.str();
}

const GenericExpression* Assignment::copy(CTS& t) const
{
    return new Assignment(static_cast<const lexpression::AccessExpression&>(*v.copy(t)), *static_cast<const LExpression*>(e.copy(t)), decl_line);
}

const GenericExpression* Assignment::abstract_copy(CTS& t, const VarSet& S) const
{
    if (S.count(v.top_var()->get_coffset()))
    {
        return new Assignment(static_cast<const lexpression::AccessExpression&>(*v.abstract_copy(t, S)), *static_cast<const LExpression*>(e.abstract_copy(t, S)), decl_line);
    } else {
        return new Nop();
    }
}

const GenericExpression* Assignment::instantiate(CTS& t, const unsigned i, const value val) const
{
    return new Assignment(static_cast<const lexpression::AccessExpression&>(*v.instantiate(t, i, val)), *static_cast<const LExpression*>(e.instantiate(t, i, val)), decl_line);
}

const GenericExpression* Assignment::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Assignment(static_cast<const lexpression::AccessExpression&>(*v.eliminate_refs(t, d)), *static_cast<const LExpression*>(e.eliminate_refs(t, d)), decl_line);
}


void Assignment::writes(VarSet& w) const
{
    //w.insert(v.top_var());
    v.writes(w);
}

void Assignment::reads(VarSet& r) const
{
    v.reads(r);
    e.reads(r);
}

Assignment::~Assignment()
{
    delete &v;
    delete &e;
}

// -----------------------------------------------------------------------------

Initialisation::Initialisation(const Variable& x, const LExpression& r, int l): Instruction(l), v(x), e(r)
{
}

SProgram Initialisation::codegen() const
{
    SProgram L;
    
    const Type& t = v.get_type();
    L.add(e.codegen());
    if (v.is_static())
    {
        L.add(StackMachine::ADDRC);
    } else {
        L.add(StackMachine::ADDR);
    }

    L.add(v.get_offset());

    L.add(t.store_code());

    return L;
}

bool Initialisation::has_vars() const
{
    return true;
}

bool Initialisation::has_params() const
{
    return e.has_params();
}

string Initialisation::to_string() const
{
    stringstream s;

    s << v.to_string() << " := " << e.to_string();

    return s.str();
}

const GenericExpression* Initialisation::copy(CTS& t) const
{
    const Variable* var = t.lookup_variable_by_id(v.id);
    if (var == NULL)
    {
        // this should not happen
        t.add_variable_copy(v);
        var = t.last_added_variable();
    }
    return new Initialisation(*var, *static_cast<const LExpression*>(e.copy(t)), decl_line);
}

const GenericExpression* Initialisation::instantiate(CTS& t, const unsigned i, const value val) const
{
    const Variable* var = t.lookup_variable_by_id(v.id);
    if (var == NULL)
    {
        // this should not happen
        t.add_variable_copy(v);
        var = t.last_added_variable();
    }

    return new Initialisation(*var, *static_cast<const LExpression*>(e.instantiate(t, i, val)), decl_line);
}

const GenericExpression* Initialisation::eliminate_refs(CTS& t, const ref_dict& d) const
{
    const Variable* var = t.lookup_variable_by_id(v.id);
    if (var == NULL)
    {
        // this should not happen
        t.add_variable_copy(v);
        var = t.last_added_variable();
    }
    return new Initialisation(*var, *static_cast<const LExpression*>(e.eliminate_refs(t, d)), decl_line);
}

const GenericExpression* Initialisation::abstract_copy(CTS& t, const VarSet& S) const
{
    if (S.count(v.get_coffset()))
    {
        const Variable* var = t.lookup_variable_by_id(v.id);
        if (var == NULL)
        {
            // this should not happen
            t.add_variable_copy(v);
            var = t.last_added_variable();
        }

        return new Initialisation(*var, *static_cast<const LExpression*>(e.abstract_copy(t, S)), decl_line);
    } else {
        return new Nop();
    }
}

void Initialisation::writes(VarSet& w) const
{
    w.insert(v.get_coffset());
}

void Initialisation::reads(VarSet& r) const
{
    e.reads(r);
}

Initialisation::~Initialisation()
{
    delete &e;
}

// -----------------------------------------------------------------------------

Block::Block(int l): Instruction(l) 
{
}

Block::Block(const Block& B): Instruction(B.decl_line), instrs(B.instrs)
{
}

Block::Block(const vector<const Instruction*>& V, int l): Instruction(l), instrs(V)
{
}

SProgram Block::codegen() const
{
    SProgram L;
    
    for (auto i: instrs)
    {
        L.add(i->codegen());
    }

    return L;
}

bool Block::has_vars() const
{
    vector<const Instruction*>::const_iterator i;
    bool r = false;

    for (i=instrs.begin(); i!=instrs.end() && !r; i++)
        r = (*i)->has_vars();

    return r;
}

bool Block::has_params() const
{
    vector<const Instruction*>::const_iterator i;
    bool r = false;

    for (i=instrs.begin(); i!=instrs.end() && !r; i++)
        r = (*i)->has_params();

    return r;
}

string Block::to_string() const
{
    stringstream s;
    vector<const Instruction*>::const_iterator i;
    
    s << "{ ";
    for (i=instrs.begin(); i!=instrs.end(); i++)
        s << **i << "; ";

    s << "}";

    return s.str();
}

void Block::add_instruction(const Instruction* i)
{
    instrs.push_back(i);
}

const GenericExpression* Block::copy(CTS& t) const
{
    Block* c = new Block(decl_line);
    vector<const Instruction*>::const_iterator i;
    
    for (i=instrs.begin(); i!=instrs.end(); i++)
        c->add_instruction(static_cast<const Instruction*>((*i)->copy(t)));

    return c;
}

const GenericExpression* Block::abstract_copy(CTS& t, const VarSet& S) const
{
    // Not good: needs deep copy
    Block* c = new Block(decl_line);
    vector<const Instruction*>::const_iterator i;
    
    for (i = instrs.begin(); i != instrs.end(); i++)
    {
        c->add_instruction(static_cast<const Instruction*>((*i)->abstract_copy(t, S)));
    }

    return c;
}

const GenericExpression* Block::instantiate(CTS& t, const unsigned j, const value v) const
{
    // Not good: needs deep copy
    Block* c = new Block(decl_line);
    
    for (auto i = instrs.begin(); i != instrs.end(); i++)
    {
        c->add_instruction(static_cast<const Instruction*>((*i)->instantiate(t, j, v)));
    }

    return c;
}

const GenericExpression* Block::eliminate_refs(CTS& t, const ref_dict& d) const
{
    Block* c = new Block(decl_line);
    vector<const Instruction*>::const_iterator i;
    
    for (i = instrs.begin(); i != instrs.end(); i++)
    {
        c->add_instruction(static_cast<const Instruction*>((*i)->eliminate_refs(t, d)));
    }

    return c;
}

void Block::clear()
{
    instrs.clear();
}

void Block::writes(VarSet& w) const
{
    vector<const Instruction*>::const_iterator i;
    
    for (i = instrs.begin(); i != instrs.end(); i++)
    {
        (*i)->writes(w);
    }
}

void Block::reads(VarSet& r) const
{
    vector<const Instruction*>::const_iterator i;
    
    for (i = instrs.begin(); i != instrs.end(); i++)
    {
        (*i)->reads(r);
    }
}

Block::~Block()
{
    vector<const Instruction*>::const_iterator i;
    
    for (i = instrs.begin(); i != instrs.end(); i++)
    {
        delete *i;
    }
}

// -----------------------------------------------------------------------------

LoopBlock::LoopBlock(const Block& B): Block(B)
{
}

LoopBlock::LoopBlock(const LoopBlock& B): Block(B)
{
}

const GenericExpression* LoopBlock::copy(CTS& t) const
{
    return new LoopBlock(*static_cast<const Block*>(this->Block::copy(t)));
}

const GenericExpression* LoopBlock::abstract_copy(CTS& t, const VarSet& S) const
{
    return new LoopBlock(*static_cast<const Block*>(this->Block::abstract_copy(t, S)));
}

const GenericExpression* LoopBlock::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new LoopBlock(*static_cast<const Block*>(this->Block::instantiate(t, i, v)));
}

const GenericExpression* LoopBlock::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new LoopBlock(*static_cast<const Block*>(this->Block::eliminate_refs(t, d)));
}
//LoopBlock::~LoopBlock()
//{
//}


// -----------------------------------------------------------------------------

If::If(const Property& b, const Instruction& i, int l): Instruction(l), condition(b), instructions(i)
{
}

SProgram If::codegen() const
{
    SProgram L;
    
    SProgram I;
    I.add(instructions.codegen());
    const unsigned s = I.size();

    SProgram U;
    VarSet w;
    instructions.writes(w);

    // Since we do not know what will be executed we set all
    // variables that might be written to, to unknown
    U.add(StackMachine::POP);
    for (auto x: w)
    {
        U.add(StackMachine::PUSH);
        U.add(0);
        U.add(StackMachine::ADDR);
        U.add(x);
        U.add(StackMachine::STORE8_);
    } 
    U.add(StackMachine::JMP);
    U.add(s + 3);
    const unsigned su = U.size();

    L.add(condition.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JNU);
    L.add(su + 1);
    L.add(U);
    L.add(StackMachine::JZ);
    L.add(s + 1);
    L.add(I);

    return L;
}

bool If::has_vars() const
{
    return condition.has_vars() || instructions.has_vars();
}

bool If::has_params() const
{
    return condition.has_params() || instructions.has_params();
}

string If::to_string() const
{
    stringstream s;

    s << "if (" << condition.to_string() << ") " << instructions.to_string();

    return s.str();
}

const GenericExpression* If::copy(CTS& t) const
{
    return new If(*static_cast<const Property*>(condition.copy(t)), *static_cast<const Instruction*>(instructions.copy(t)), decl_line);
}

const GenericExpression* If::abstract_copy(CTS& t, const VarSet& S) const
{
    return new If(*static_cast<const Property*>(condition.abstract_copy(t, S)), *static_cast<const Instruction*>(instructions.abstract_copy(t, S)), decl_line);
}

const GenericExpression* If::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new If(*static_cast<const Property*>(condition.instantiate(t, i, v)), *static_cast<const Instruction*>(instructions.instantiate(t, i, v)), decl_line);
}

const GenericExpression* If::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new If(*static_cast<const Property*>(condition.eliminate_refs(t, d)), *static_cast<const Instruction*>(instructions.eliminate_refs(t, d)), decl_line);
}

void If::writes(VarSet& w) const
{
    instructions.writes(w);
}

void If::reads(VarSet& r) const
{
    condition.reads(r);
    instructions.reads(r);
}

If::~If()
{
    delete &condition;
    delete &instructions;
}

// -----------------------------------------------------------------------------

IfElse::IfElse(const Property& b, const Instruction& i, const Instruction& e, int l): Instruction(l), condition(b), instructions(i), else_instructions(e)
{
}

SProgram IfElse::codegen() const
{
    SProgram L;
    
    SProgram I;
    I.add(instructions.codegen());
    const unsigned s = I.size();

    SProgram IE;
    IE.add(else_instructions.codegen());
    const unsigned se = IE.size();

    SProgram U;
    VarSet w;
    instructions.writes(w);
    else_instructions.writes(w);

    // Since we do not know what will be executed we set all
    // variables that might be written to, to unknown
    U.add(StackMachine::POP);
    for (auto x: w)
    {
        U.add(StackMachine::PUSH);
        U.add(0);
        U.add(StackMachine::ADDR);
        U.add(x);
        U.add(StackMachine::STORE8_);
    } 
    U.add(StackMachine::JMP);
    U.add(s + se + 5); // s + se + 1 + 2 for each jump
    const unsigned su = U.size();

    L.add(condition.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JNU);
    L.add(su + 1);
    L.add(U);
    L.add(StackMachine::JZ);
    L.add(s + 3); // s + 1... + 2 for the jmp
    L.add(I);
    L.add(StackMachine::JMP);
    L.add(se + 1);
    L.add(IE);

    return L;
}

bool IfElse::has_vars() const
{
    return condition.has_vars() || instructions.has_vars() || else_instructions.has_vars();
}

bool IfElse::has_params() const
{
    return condition.has_params() || instructions.has_params() || else_instructions.has_params();
}

string IfElse::to_string() const
{
    stringstream s;

    s << "if (" << condition.to_string() << ") " << instructions.to_string() << " else " << else_instructions.to_string();

    return s.str();
}

const GenericExpression* IfElse::copy(CTS& t) const
{
    return new IfElse(*static_cast<const Property*>(condition.copy(t)), *static_cast<const Instruction*>(instructions.copy(t)),*static_cast<const Instruction*>(else_instructions.copy(t)), decl_line);
}

const GenericExpression* IfElse::abstract_copy(CTS& t, const VarSet& S) const
{
    return new IfElse(*static_cast<const Property*>(condition.abstract_copy(t, S)), *static_cast<const Instruction*>(instructions.abstract_copy(t, S)),*static_cast<const Instruction*>(else_instructions.abstract_copy(t, S)), decl_line);
}

const GenericExpression* IfElse::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new IfElse(*static_cast<const Property*>(condition.instantiate(t, i, v)), *static_cast<const Instruction*>(instructions.instantiate(t, i, v)),*static_cast<const Instruction*>(else_instructions.instantiate(t, i, v)), decl_line);
}

const GenericExpression* IfElse::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new IfElse(*static_cast<const Property*>(condition.eliminate_refs(t, d)), *static_cast<const Instruction*>(instructions.eliminate_refs(t, d)), *static_cast<const Instruction*>(else_instructions.eliminate_refs(t, d)), decl_line);
}

void IfElse::writes(VarSet& w) const
{
    instructions.writes(w);
    else_instructions.writes(w);
}

void IfElse::reads(VarSet& r) const
{
    condition.reads(r);
    instructions.reads(r);
    else_instructions.reads(r);
}

IfElse::~IfElse()
{
    delete &condition;
    delete &instructions;
    delete &else_instructions;
}

// -----------------------------------------------------------------------------

While::While(const Property& b, const LoopBlock& i, int l): Instruction(l), condition(b), instructions(i)
{
}

SProgram While::codegen() const
{
    SProgram L;
    
    SProgram I;
    I.add(instructions.codegen());
    const unsigned s = I.size();

    SProgram U;
    VarSet w;
    instructions.writes(w);

    // Since we do not know what will be executed we set all
    // variables that might be written to, to unknown
    U.add(StackMachine::POP);
    for (auto x: w)
    {
        U.add(StackMachine::PUSH);
        U.add(0);
        U.add(StackMachine::ADDR);
        U.add(x);
        U.add(StackMachine::STORE8_);
    } 
    U.add(StackMachine::JMP);
    U.add(s + 5); // +2 for the final jump
    const unsigned su = U.size();

    L.add(condition.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JNU);
    L.add(su + 1);
    L.add(U);
    L.add(StackMachine::JZ);
    L.add(s + 3); // +2 for the final jump
    L.add(I);
    L.add(StackMachine::JMP);
    L.add(-(word) L.size());

    return L;
}

bool While::has_vars() const
{
    return condition.has_vars() || instructions.has_vars();
}

bool While::has_params() const
{
    return condition.has_params() || instructions.has_params();
}

string While::to_string() const
{
    stringstream s;

    s << "while (" << condition.to_string() << ") " << instructions.to_string();

    return s.str();
}

const GenericExpression* While::copy(CTS& t) const
{
    return new While(*static_cast<const Property*>(condition.copy(t)), *static_cast<const LoopBlock*>(instructions.copy(t)), decl_line);
}

const GenericExpression* While::abstract_copy(CTS& t, const VarSet& S) const
{
    return new While(*static_cast<const Property*>(condition.abstract_copy(t, S)), *static_cast<const LoopBlock*>(instructions.abstract_copy(t, S)), decl_line);
}

const GenericExpression* While::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new While(*static_cast<const Property*>(condition.instantiate(t, i, v)), *static_cast<const LoopBlock*>(instructions.instantiate(t, i, v)), decl_line);
}

const GenericExpression* While::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new While(*static_cast<const Property*>(condition.eliminate_refs(t, d)), *static_cast<const LoopBlock*>(instructions.eliminate_refs(t, d)), decl_line);
}

void While::writes(VarSet& w) const
{
    instructions.writes(w);
}

void While::reads(VarSet& r) const
{
    condition.reads(r);
    instructions.reads(r);
}

While::~While()
{
    delete &condition;
}

// -----------------------------------------------------------------------------

DoWhile::DoWhile(const Property& b, const LoopBlock& i, int l): Instruction(l), condition(b), instructions(i)
{
}

SProgram DoWhile::codegen() const
{
    SProgram L;
    
    SProgram U;
    VarSet w;
    instructions.writes(w);

    // Since we do not know what will be executed we set all
    // variables that might be written to, to unknown
    U.add(StackMachine::POP);
    for (auto x: w)
    {
        U.add(StackMachine::PUSH);
        U.add(0);
        U.add(StackMachine::ADDR);
        U.add(x);
        U.add(StackMachine::STORE8_);
    } 
    U.add(StackMachine::JMP);
    U.add(3); // 2 for the JNZ + 1
    const unsigned su = U.size();

    L.add(instructions.codegen());
    L.add(condition.codegen());
    L.add(StackMachine::DUP);
    L.add(StackMachine::JNU);
    L.add(su + 1);
    L.add(U);
    L.add(StackMachine::JNZ);
    L.add(-(word) L.size()); // back to the beginning

    return L;
}

bool DoWhile::has_vars() const
{
    return condition.has_vars() || instructions.has_vars();
}

bool DoWhile::has_params() const
{
    return condition.has_params() || instructions.has_params();
}

string DoWhile::to_string() const
{
    stringstream s;

    s << "do" << instructions << " while (" << condition.to_string() << ");";

    return s.str();
}

const GenericExpression* DoWhile::copy(CTS& t) const
{
    return new DoWhile(*static_cast<const Property*>(condition.copy(t)), *static_cast<const LoopBlock*>(instructions.copy(t)), decl_line);
}

const GenericExpression* DoWhile::abstract_copy(CTS& t, const VarSet& S) const
{
    return new DoWhile(*static_cast<const Property*>(condition.abstract_copy(t, S)), *static_cast<const LoopBlock*>(instructions.abstract_copy(t, S)), decl_line);
}

const GenericExpression* DoWhile::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new DoWhile(*static_cast<const Property*>(condition.instantiate(t, i, v)), *static_cast<const LoopBlock*>(instructions.instantiate(t, i, v)), decl_line);
}

const GenericExpression* DoWhile::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new DoWhile(*static_cast<const Property*>(condition.eliminate_refs(t, d)), *static_cast<const LoopBlock*>(instructions.eliminate_refs(t, d)), decl_line);
}

void DoWhile::writes(VarSet& w) const
{
    instructions.writes(w);
}

void DoWhile::reads(VarSet& r) const
{
    condition.reads(r);
    instructions.reads(r);
}


DoWhile::~DoWhile()
{
    delete &condition;
}

// -----------------------------------------------------------------------------

For::For(const Instruction& it, const Instruction& s, const Property& b, const LoopBlock& i, int l): Instruction(l), init(it), step(s), condition(b), instructions(i)
{
}

SProgram For::codegen() const
{
    SProgram L;
    
    SProgram I;
    I.add(instructions.codegen());
    I.add(step.codegen());
    const unsigned s = I.size();

    SProgram U;
    VarSet w;
    instructions.writes(w);

    // Since we do not know what will be executed we set all
    // variables that might be written to, to unknown
    U.add(StackMachine::POP);
    for (auto x: w)
    {
        U.add(StackMachine::PUSH);
        U.add(0);
        U.add(StackMachine::ADDR);
        U.add(x);
        U.add(StackMachine::STORE8_);
    } 
    U.add(StackMachine::JMP);
    U.add(s + 5); // +2 for the final jump
    const unsigned su = U.size();

    SProgram W;
    W.add(condition.codegen());
    W.add(StackMachine::DUP);
    W.add(StackMachine::JNU);
    W.add(su + 1);
    W.add(U);
    W.add(StackMachine::JZ);
    W.add(s + 3); // +2 for the final jump
    W.add(I);
    W.add(StackMachine::JMP);
    W.add(-(word) W.size());

    L.add(init.codegen());
    L.add(W);

    return L;
}

bool For::has_vars() const
{
    return init.has_vars() || step.has_params() || condition.has_vars() || instructions.has_vars();
}

bool For::has_params() const
{
    return init.has_params() || step.has_params() || condition.has_params() || instructions.has_params();
}

string For::to_string() const
{
    stringstream s;

    s << "for (" << init << "; " << condition << "; " << step << ") " << instructions.to_string();

    return s.str();
}

const GenericExpression* For::copy(CTS& t) const
{
    return new For(
            *static_cast<const Instruction*>(init.copy(t)), 
            *static_cast<const Instruction*>(step.copy(t)), 
            *static_cast<const Property*>(condition.copy(t)), 
            *static_cast<const LoopBlock*>(instructions.copy(t)),
            decl_line);
}

const GenericExpression* For::abstract_copy(CTS& t, const VarSet& S) const
{
    return new For(
            *static_cast<const Instruction*>(init.abstract_copy(t, S)), 
            *static_cast<const Instruction*>(step.abstract_copy(t, S)), 
            *static_cast<const Property*>(condition.abstract_copy(t, S)), 
            *static_cast<const LoopBlock*>(instructions.abstract_copy(t, S)),
            decl_line);
}

const GenericExpression* For::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new For(
            *static_cast<const Instruction*>(init.instantiate(t, i, v)), 
            *static_cast<const Instruction*>(step.instantiate(t, i, v)), 
            *static_cast<const Property*>(condition.instantiate(t, i, v)), 
            *static_cast<const LoopBlock*>(instructions.instantiate(t, i, v)),
            decl_line);
}

const GenericExpression* For::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new For(
            *static_cast<const Instruction*>(init.eliminate_refs(t, d)), 
            *static_cast<const Instruction*>(step.eliminate_refs(t, d)), 
            *static_cast<const Property*>(condition.eliminate_refs(t, d)), 
            *static_cast<const LoopBlock*>(instructions.eliminate_refs(t, d)),
            decl_line);
}

void For::writes(VarSet& w) const
{
    instructions.writes(w);
    init.writes(w);
    step.writes(w);
}

void For::reads(VarSet& r) const
{
    condition.reads(r);
    instructions.reads(r);
    init.reads(r);
    step.reads(r);
}


For::~For()
{
    delete &init;
    delete &condition;
    delete &step;
}


// -----------------------------------------------------------------------------

Return::Return(const LExpression& r, int l): Instruction(l), ret(r)
{
}

SProgram Return::codegen() const
{
    SProgram L;
    
    L.add(ret.codegen());
    L.add(StackMachine::RET);

    return L;
}

bool Return::has_vars() const
{
    return ret.has_vars();
}

bool Return::has_params() const
{
    return ret.has_params();
}

string Return::to_string() const
{
    stringstream s;

    s << "return " << ret.to_string();

    return s.str();
}

const GenericExpression* Return::copy(CTS& t) const
{
    return new Return(*static_cast<const LExpression*>(ret.copy(t)), decl_line);
}

const GenericExpression* Return::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Return(*static_cast<const LExpression*>(ret.abstract_copy(t, S)), decl_line);
}

const GenericExpression* Return::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Return(*static_cast<const LExpression*>(ret.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Return::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Return(*static_cast<const LExpression*>(ret.eliminate_refs(t, d)), decl_line);
}

void Return::writes(VarSet& w) const
{
    ret.writes(w);
}

void Return::reads(VarSet& r) const
{
    ret.reads(r);
}

Return::~Return()
{
    delete &ret;
}


// -----------------------------------------------------------------------------

Nop::Nop(): Instruction(-1) 
{
}

SProgram Nop::codegen() const
{
    return SProgram();
}

string Nop::to_string() const
{
    return "nop";
}

const GenericExpression* Nop::copy(CTS& t) const
{
    return new Nop();
}

const GenericExpression* Nop::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Nop();
}

const GenericExpression* Nop::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Nop();
}

const GenericExpression* Nop::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Nop();
}

bool Nop::is_nop() const
{
    return true;
}


// -----------------------------------------------------------------------------

BinaryCombinator::BinaryCombinator(const Instruction& l, const Instruction& r, int line): Instruction(line), first(l), second(r)
{
}

bool BinaryCombinator::has_vars() const
{
    return first.has_vars() || second.has_vars();
}

bool BinaryCombinator::has_params() const
{
    return first.has_params() || second.has_params();
}

void BinaryCombinator::writes(VarSet& w) const
{
    first.writes(w);
    second.writes(w);
}

void BinaryCombinator::reads(VarSet& r) const
{
    first.reads(r);
    second.reads(r);
}


BinaryCombinator::~BinaryCombinator()
{
    delete &first;
    delete &second;
}


// -----------------------------------------------------------------------------

Comma::Comma(const Instruction& l, const Instruction& r, int line): BinaryCombinator(l, r, line)
{
}

SProgram Comma::codegen() const
{
    SProgram L;
    
    L.add(first.codegen());
    L.add(second.codegen());

    return L;
}

string Comma::to_string() const
{
    stringstream s;

    s << first << ", " << second;

    return s.str();
}

const GenericExpression* Comma::copy(CTS& t) const
{
    return new Comma(
            *static_cast<const Instruction*>(first.copy(t)), 
            *static_cast<const Instruction*>(second.copy(t)),
            decl_line);
}

const GenericExpression* Comma::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Comma(
            *static_cast<const Instruction*>(first.abstract_copy(t, S)), 
            *static_cast<const Instruction*>(second.abstract_copy(t, S)),
            decl_line);
}

const GenericExpression* Comma::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Comma(
            *static_cast<const Instruction*>(first.instantiate(t, i, v)), 
            *static_cast<const Instruction*>(second.instantiate(t, i, v)),
            decl_line);
}

const GenericExpression* Comma::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Comma(
            *static_cast<const Instruction*>(first.eliminate_refs(t, d)), 
            *static_cast<const Instruction*>(second.eliminate_refs(t, d)),
            decl_line);
}

// -----------------------------------------------------------------------------

Log::Log(const LExpression& r, int l): Instruction(l), e(r)
{
}

SProgram Log::codegen() const
{
    SProgram L;
    
    L.add(e.codegen());
    L.add(StackMachine::PRINT);

    return L;
}

bool Log::has_vars() const
{
    return e.has_vars();
}

bool Log::has_params() const
{
    return e.has_params();
}

string Log::to_string() const
{
    stringstream s;

    s << "log(" << e.to_string() << ")";

    return s.str();
}

const GenericExpression* Log::copy(CTS& t) const
{
    return new Log(*static_cast<const LExpression*>(e.copy(t)), decl_line);
}

const GenericExpression* Log::abstract_copy(CTS& t, const VarSet& S) const
{
    return new Log(*static_cast<const LExpression*>(e.abstract_copy(t, S)), decl_line);
}

const GenericExpression* Log::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new Log(*static_cast<const LExpression*>(e.instantiate(t, i, v)), decl_line);
}

const GenericExpression* Log::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new Log(*static_cast<const LExpression*>(e.eliminate_refs(t, d)), decl_line);
}

void Log::writes(VarSet& w) const
{
    e.writes(w);
}

void Log::reads(VarSet& r) const
{
    e.reads(r);
}

Log::~Log()
{
    delete &e;
}



