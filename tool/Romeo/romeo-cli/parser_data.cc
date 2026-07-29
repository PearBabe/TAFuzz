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
#include <cstdlib>

#include <parser_data.hh>

#include <lexpression.hh>
#include <lconstraint.hh>
#include <access_expression.hh>
#include <instruction.hh>
#include <expression.hh>
#include <property.hh>
#include <cts.hh>
#include <type.hh>
#include <function.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::lexpression;

extern int yylineno;

ParserData::ParserData(): nblocks(0), ntrans(0), cts(new CTS(0,"coin")), ref_cts(cts), vp(cts), current_type(NULL), constness(false), check(false)
{
    CTS::current_cts = cts;
    active_blocks.push_back(NULL);
}

ParserData::~ParserData()
{
    // cts and ref_cts are already deleted as part of the jobs
}

const lexpression::LValue* ParserData::enforce_lvalue(const GenericExpression* e)
{
    if (e->is_lvalue())
    {
        return static_cast<const LValue*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected lvalue but got " << *e << endl;
        exit(1);
    }
}

const LExpression* ParserData::enforce_le(const GenericExpression* e)
{
    if (e->is_lexpression())
    {
        return static_cast<const LExpression*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected linear expression but got " << *e << endl;
        exit(1);
    }
}

const LExpression* ParserData::enforce_numeric(const GenericExpression* e)
{
    if (e->is_numeric())
    {
        return static_cast<const LExpression*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected numeric (linear) expression but got " << *e << endl;
        exit(1);
    }
}

const Property* ParserData::enforce_lc(const GenericExpression* e)
{
    if (e->is_lconstraint())
    {
        return static_cast<const Property*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected linear constraint but got " << *e << endl;
        exit(1);
    }
}

const AccessExpression* ParserData::enforce_access(const GenericExpression* e)
{
    if (e->is_access())
    {
        return static_cast<const AccessExpression*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected access expression but got " << *e << endl;
        exit(1);
    }
}

const Instruction* ParserData::enforce_instr(const GenericExpression* e)
{
    if (e->is_instruction())
    {
        return static_cast<const Instruction*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected instruction but got " << *e << endl;
        exit(1);
    }
}


const Property* ParserData::enforce_property(const GenericExpression* e)
{
    if (e->is_property())
    {
        if (e->is_clock_var())
        {
            auto f = static_cast<const ClockVariable*>(e);
            e = f->to_property();
            delete f;
        }
        return static_cast<const Property*>(e);
    } else {
        cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected property but got " << *e << endl;
        exit(1);
    }
}

const Property* ParserData::enforce_simple(const GenericExpression* e)
{
    if (e->is_property())
    {
        const Property* p = static_cast<const Property*>(e);
        if (p->is_simple())
            return p;
    }

    cerr << error_tag(color_output) << "Line " << e->decl_line << ": expected simple property but got " << *e << endl;
    exit(1);
}

instruction::Block* ParserData::new_block()
{
    instruction::Block* b = new instruction::Block(yylineno);
    push_block(b);

    return b;
}

void ParserData::push_block(instruction::Block* b)
{
    active_blocks.push_back(b);
    nblocks++;
}

instruction::Block* ParserData::current_block() const
{
    return active_blocks.back();
}

void ParserData::pop_block()
{
    active_blocks.pop_back();
    nblocks--;
}

bool ParserData::top_level() const
{
    return nblocks == 1;
}

const std::list<instruction::Block*>* ParserData::blocks() const
{
    return &active_blocks;
}

void ParserData::init_new_cts_copy()
{
    cts = new CTS(*cts);
    CTS::current_cts = cts;
    vp = cts;
}

int ParserData::lookup_sparam(const string& s) const
{
    int k = 0;
    for (auto f: tf_frames)
    {
        if (f.param == s)
        {
            return k;
        }
        k++;
    }

    return -1;
}

