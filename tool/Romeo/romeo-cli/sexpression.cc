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


#include <sexpression.hh>
#include <stack_machine.hh>
#include <generic_expression.hh>
#include <property.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <variable.hh>
#include <vsstate.hh>
#include <result.hh>


using namespace romeo;
using namespace std;

StackMachine SExpression::M(1024); // stack size of 1024 ought to be enough for everybody

SExpression::SExpression(): expr(nullptr), code_up_to_date(true)
{
}

SExpression::SExpression(const GenericExpression* e): expr(e), code_up_to_date(false)
{
}

SExpression::SExpression(const SExpression& e): expr(e.expr), code_up_to_date(false)
{
}

SExpression& SExpression::operator=(const SExpression& e)
{
    expr = e.expr;
    code_up_to_date = false;

    return *this;
}

const GenericExpression* SExpression::get_expr() const
{
    return expr;
}

void SExpression::add_code(SProgram& L) const
{
    if (expr != nullptr)
    {
        if (!code_up_to_date)
        {
            code = expr->codegen().program();
            code_up_to_date = true;
        }

        for (auto x: code)
        {
            L.add(x);
        }
    } 
}

RValue SExpression::evaluate(const byte V[], const byte C[]) const
{
    if (expr != nullptr)
    {
        if (!code_up_to_date)
        {
            code = expr->codegen().program();
            code_up_to_date = true;
        }

        M.execute(code, (byte*) V, C, nullptr);
        return M.top();
    } else {
        return RValue(0, (std::byte) 0);
    }
}

void SExpression::execute(byte V[], const byte C[]) const
{
    if (expr != nullptr)
    {
        if (!code_up_to_date)
        {
            code = expr->codegen().program();
            code_up_to_date = true;
        }

        M.execute(code, V, C, nullptr);
    }
}

RValue SExpression::eval(const PState* S) const
{
    if (expr != nullptr)
    {
        if (!code_up_to_date)
        {
            code = expr->codegen().program();
            code_up_to_date = true;
        }

        const VSState* st = static_cast<const VSState*>(S);
        M.execute(code, st->V, st->job.cts.statics, st);
        return M.top();
    } else {
        return RValue(0);
    }
}

bool SExpression::is_null() const
{
    return (expr == nullptr);
}

Polyhedron SExpression::constraint(const byte V[], const byte C[], unsigned NP) const
{
    if (expr != nullptr)
    {
        return static_cast<const Property*>(expr)->constraint(V, C, NP);
    } else {
        return Polyhedron(NP, true); // Universe: no constraint
    }
}

LinearExpression SExpression::linear_expression(const byte V[], const byte C[]) const
{
    if (expr != nullptr)
    {
        return static_cast<const LExpression*>(expr)->linear_expression(V, C);
    } else {
        return LinearExpression();
    }
}

string SExpression::to_string() const
{
    if (expr != nullptr)
    {
        return expr->to_string();
    } else {
        return "null";
    }
}

bool SExpression::is_constant(value v) const
{
    if (expr != nullptr && !expr->has_vars() && !expr->has_params())
    {
        RValue r = evaluate(nullptr, nullptr);

        return (!r.is_unknown() && r.to_int() == v);
    } else {
        return false;
    }
}

bool SExpression::is_const() const
{
    if (expr != nullptr)
    {
        return expr->is_const();
    } else {
        return false;
    }
}

bool SExpression::is_static() const
{
    if (expr != nullptr)
    {
        return expr->is_static();
    } else {
        return false;
    }
}

bool SExpression::has_params() const
{
    if (expr != nullptr)
    {
        return expr->has_params();
    } else {
        return false;
    }
}

bool SExpression::has_vars() const
{
    if (expr != nullptr)
    {
        return expr->has_vars();
    } else {
        return false;
    }
}

bool SExpression::is_nop() const
{
    if (expr != nullptr)
    {
        return static_cast<const Instruction*>(expr)->is_nop();
    } else {
        return false;
    }
}

bool SExpression::has_cost() const
{
    if (expr != nullptr)
    {
        return static_cast<const Property*>(expr)->has_cost();
    } else {
        return false;
    }
}

int SExpression::get_line() const
{
    if (expr != nullptr)
    {
        return static_cast<const Property*>(expr)->decl_line;
    } else {
        return -1;
    }
}

void SExpression::prepare(CTS& t) const
{
    if (expr != nullptr)
    {
        static_cast<const Property*>(expr)->prepare(t);
    } 
}

SExpression SExpression::copy(CTS& t) const
{
    if (expr != nullptr)
    {
        return SExpression(expr->copy(t));
    } else {
        return SExpression();
    }
}

SExpression SExpression::abstract_copy(CTS& t, const VarSet& S) const
{
    if (expr != nullptr)
    {
        return SExpression(expr->abstract_copy(t, S));
    } else {
        return SExpression();
    }
}

SExpression SExpression::instantiate(CTS& t, const unsigned i, const value v) const
{
    if (expr != nullptr)
    {
        return SExpression(expr->instantiate(t, i, v));
    } else {
        return SExpression();
    }
}

SExpression SExpression::eliminate_refs(CTS& t, const ref_dict& d) const
{
    if (expr != nullptr)
    {
        return SExpression(expr->eliminate_refs(t, d));
    } else {
        return SExpression();
    }
}

SExpression SExpression::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    if (expr != nullptr)
    {
        return SExpression(expr->abstract_parameters(t, negated, lbs, ubs, lbounds, ubounds));
    } else {
        return SExpression();
    }
}

list<VarSet> SExpression::var_reads() const
{
    if (expr != nullptr)
    {
        return static_cast<const Property*>(expr)->var_reads();
    } else {
        return list<VarSet>();
    }
}

void SExpression::reads(VarSet& r) const
{
    if (expr != nullptr)
    {
        expr->reads(r);
    }
}

void SExpression::writes(VarSet& r) const
{
    if (expr != nullptr)
    {
        expr->writes(r);
    }
}

void SExpression::clear()
{
    if (expr != nullptr)
    {
        delete expr;
        expr = nullptr;
        code.clear();
        code_up_to_date = true;
    }
}

SExpression::~SExpression()
{
}

