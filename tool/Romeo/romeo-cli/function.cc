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
#include <string>
#include <vector>

#include <function.hh>
#include <cts.hh>
#include <expression.hh>
#include <access_expression.hh>
#include <instruction.hh>
#include <variable.hh>
#include <rvalue.hh>
#include <stack_machine.hh>
#include <lobject.hh>
#include <type.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;
using namespace romeo::expression;
using namespace romeo::instruction;

// -----------------------------------------------------------------------------

FunctionCall::FunctionCall(const Function& f, const vector<const Expression*>& a, int line): LExpression(line), function(f), args(a)
{
    unsigned k = function.first_fparam_id;
    for (unsigned i = 0; i < args.size(); i++)
    {
        // We use the ids of variables to remember in which order they appear in the args list
        const Variable* var = function.cts.lookup_variable_by_id(k);
        if (var != nullptr)
        {
            if (var->get_type().is_reference())
            {
                if (args[i]->is_rlvalue())
                {
                    args[i] = static_cast<const lexpression::RLValue*>(args[i])->access_expr();
                }
                dicorefs[var->get_offset()] = args[i];
            }
            k++;
        } else {
            cerr << error_tag(color_output) << "Line " << decl_line << ": could not find parameter corresponding to argument " << *args[i] << " in function " << function.label  << endl;
            exit(1);
        }
    }

    code = function.code.eliminate_refs(function.cts, dicorefs);
}

FunctionCall::FunctionCall(const Function& f, const vector<const Expression*>& a, const SExpression& c, CTS& t, const ref_dict& d, int line): LExpression(line), function(f), args(a), code(c.eliminate_refs(t, d))
{
    
}

SProgram FunctionCall::codegen() const
{
    SProgram L;

    L.add(StackMachine::STARTF);
    // Copy the arguments into the parameters
    // We suppose the parameters are the first local variables
    unsigned k = function.first_fparam_id;
    for (unsigned i = 0; i < args.size(); i++)
    {
        // We use the ids of variables to remember in which order they appear in the args list
        const Variable* var = function.cts.lookup_variable_by_id(k);
        if (var != nullptr)
        {
            L.add(args[i]->codegen());
            L.add(lexpression::LValue(*var, decl_line).codegen());
            L.add(var->get_type().store_code());
            k++;
        } else {
            cerr << error_tag(color_output) << "Line " << decl_line << ": could not find parameter corresponding to argument " << *args[i] << " in function " << function.label  << endl;
            exit(1);
        }

    }

    code.add_code(L);
    L.add(StackMachine::ENDF);
    L.add(!function.rtype.is_void());

    return L;
}

bool FunctionCall::has_vars() const
{
    bool r = code.has_vars();
    
    for (unsigned i = 0; i < args.size() && !r; i++)
    {
        r = args[i]->has_vars();
    }

    return r;
}

bool FunctionCall::has_params() const
{
    bool r = code.has_params();
    
    for (unsigned i = 0; i < args.size() && !r; i++)
    {
        r = args[i]->has_params();
    }

    return r;
}

string FunctionCall::to_string() const
{
    stringstream s;

    s << function.label << "(";
    bool comma = false;
    for (unsigned i=0; i<args.size(); i++)
    {
        if (comma)
            s << ",";
        else
            comma = true;

        s << *args[i];
    }
    s << ")";
    
    return s.str();
}

const GenericExpression* FunctionCall::copy(CTS& t) const
{
    vector<const Expression*> copy_args;
    for (unsigned i = 0; i < args.size(); i++)
    {
        copy_args.push_back(static_cast<const Expression*>(args[i]->copy(t)));
    }

    const Function* f = t.lookup_function(function.label);
    if (f == nullptr)
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": in copy, could not find function " << function.label << endl;
        exit(1);
    }

    return new FunctionCall(*f, copy_args, decl_line);
}

const GenericExpression* FunctionCall::abstract_copy(CTS& t, const VarSet& S) const
{
    vector<const Expression*> copy_args;
    for (unsigned i = 0; i < args.size(); i++)
    {
        copy_args.push_back(static_cast<const Expression*>(args[i]->abstract_copy(t, S)));
    }

    const Function* f = t.lookup_function(function.label);
    if (f == nullptr)
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": in abstract copy, could not find function " << function.label << endl;
        exit(1);
    }

    return new FunctionCall(*f, copy_args, decl_line);
}

const GenericExpression* FunctionCall::instantiate(CTS& t, const unsigned i, const value v) const
{
    vector<const Expression*> copy_args;
    for (unsigned a = 0; a < args.size(); a++)
    {
        copy_args.push_back(static_cast<const Expression*>(args[a]->instantiate(t, i, v)));
    }

    const Function* f = t.lookup_function(function.label);
    if (f == nullptr)
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": in instantiate, could not find function " << function.label << endl;
        exit(1);
    }

    return new FunctionCall(*f, copy_args, decl_line);
}

const GenericExpression* FunctionCall::eliminate_refs(CTS& t, const ref_dict& d) const
{
    vector<const Expression*> copy_args;
    for (unsigned i = 0; i < args.size(); i++)
    {
        copy_args.push_back(static_cast<const Expression*>(args[i]->eliminate_refs(t, d)));
    }

    const Function* f = t.lookup_function(function.label);
    if (f == nullptr)
    {
        cerr << error_tag(color_output) << "Line " << decl_line << ": in reference elimination, could not find function " << function.label << endl;
        exit(1);
    }

    return new FunctionCall(*f, copy_args, code, t, d, decl_line);
}

bool FunctionCall::is_instruction() const
{
    return true;
}

bool FunctionCall::is_numeric() const
{
    return function.rtype.is_numeric();
}

void FunctionCall::writes(VarSet& w) const
{
    code.writes(w);
}

void FunctionCall::reads(VarSet& r) const
{
    for (unsigned i = 0; i < args.size(); i++)
    {
        args[i]->reads(r);
    }
    code.reads(r);
}

FunctionCall::~FunctionCall()
{
    for (unsigned i=0; i<args.size(); i++)
    {
        delete args[i];
    }
}

// -----------------------------------------------------------------------------
Function::Function(unsigned i, const string& s, CTS& c, const Type& r, const vector<const Type*>& a, const SExpression& b, const unsigned p): 
    LObject(i,s), cts(c), rtype(r), args(a), code(b), first_fparam_id(p)
{
}

string Function::to_string() const
{
    stringstream s;
    bool comma = false;

    s << rtype.to_string() << " "<< label << "(";

    vector<const Type*>::const_iterator k;
    for (k = args.begin(); k != args.end(); k++)
    {
        if (comma)
        {
            s << ", ";
        } else {
            comma = true;
        }

        s << (*k)->to_string();
    }
    s << ") " << code << endl;

    return s.str();
}

unsigned Function::nargs() const
{
    return args.size();
}

const Function* Function::copy(CTS& t) const
{
    return new Function(id, label, t, rtype, args, code.copy(t), first_fparam_id);
}

Function::~Function()
{
}

