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

#include <expression.hh>
#include <stack_machine.hh>
#include <color_output.hh>

using namespace std;
using namespace romeo;

GenericExpression::GenericExpression(int l): decl_line(l)
{
}

bool GenericExpression::is_const() const
{
    return false;
}

bool GenericExpression::is_static() const
{
    return false;
}

bool GenericExpression::has_vars() const
{
    return false;
}

bool GenericExpression::has_params() const
{
    return false;
}

bool GenericExpression::is_lvalue() const
{
    return false;
}

bool GenericExpression::is_rlvalue() const
{
    return false;
}

bool GenericExpression::is_rvalue() const
{
    return false;
}

bool GenericExpression::is_lexpression() const
{
    return false;
}

bool GenericExpression::is_numeric() const
{
    return false;
}

bool GenericExpression::is_lconstraint() const
{
    return false;
}

bool GenericExpression::is_property() const
{
    return false;
}

bool GenericExpression::is_access() const
{
    return false;
}

bool GenericExpression::is_refaccess() const
{
    return false;
}

bool GenericExpression::is_instruction() const
{
    return false;
}

bool GenericExpression::is_control() const
{
    return false;
}

bool GenericExpression::is_abstracted() const
{
    return false;
}

bool GenericExpression::is_litteral(cvalue v) const
{
    return false;
}

bool GenericExpression::is_clock_var() const
{
    return false;
}

SProgram GenericExpression::codegen() const
{
    cerr << error_tag(color_output) << "Line: " << decl_line << ": Cannot generate code for expression: "  << *this << endl;
    exit(1);
}

void GenericExpression::writes(VarSet& w) const
{
}

void GenericExpression::reads(VarSet& r) const
{
}

const LExpression* GenericExpression::abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const
{
    cerr << error_tag(color_output) << "Cannot use parameter abstraction with anything else than linear expression" << endl;
    exit(1);
}

GenericExpression::~GenericExpression()
{
}


