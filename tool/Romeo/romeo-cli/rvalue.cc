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
software by the user in light of its specific s of free software,
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

#include <stack_machine.hh>
#include <rvalue.hh>
#include <valuation.hh>
#include <expression.hh>
#include <linear_expression.hh>
#include <polyhedron.hh>
#include <cts.hh>
#include <type.hh>
#include <type_list.hh>

#include <color_output.hh>

using namespace std;
using namespace romeo;

extern TypeList _romeo_types;

#include <logger.hh>
extern Logger Log;

// -----------------------------------------------------------------------------

RValue::RValue(const fvalue i, const byte st): type(*_romeo_types.real()), s(st)
{
    v.f = i;
}

RValue::RValue(const uint8_t i, const byte st): type(*_romeo_types.uinteger8()), s(st)
{
    v.i = i;
}

RValue::RValue(const int8_t i, const byte st): type(*_romeo_types.integer8()), s(st)
{
    v.i = i;
}

RValue::RValue(const uint16_t i, const byte st): type(*_romeo_types.uinteger16()), s(st)
{
    v.i = i;
}

RValue::RValue(const int16_t i, const byte st): type(*_romeo_types.integer16()), s(st)
{
    v.i = i;
}

RValue::RValue(const uint32_t i, const byte st): type(*_romeo_types.uinteger32()), s(st)
{
    v.i = i;
}

RValue::RValue(const int32_t i, const byte st): type(*_romeo_types.integer32()), s(st)
{
    v.i = i;
}

RValue::RValue(const uint64_t i, const byte st): type(*_romeo_types.uinteger64()), s(st)
{
    v.i = i;
}

RValue::RValue(const int64_t i, const byte st): type(*_romeo_types.integer64()), s(st)
{
    v.i = i;
}

RValue::RValue(const Type& t, const int64_t i, const byte st): type(t), s(st)
{
    v.i = i;
}

RValue::RValue(const Type& t, const byte* a): type(t)
{
    v.p = a;
    s = ((byte) 1);
}

RValue::RValue(const Type& t): type(t)
{
    v.p = nullptr;
    v.i = 0;
    v.f = 0;
    s = ((byte) 0);
}

const Type& RValue::get_type() const
{
    return type;
}

memrep RValue::contents() const
{
    return v;
}

byte RValue::status() const
{
    return s;
}

void RValue::set_contents(memrep x)
{
    v = x;
}

void RValue::set_status(byte x)
{
    s = x;
}

RValue RValue::deref() const
{
    if (!is_unknown())
    {
        return type.deref(v.p);
    } else {
        return RValue(type);
    }
}

bool RValue::is_int() const
{
    return type.is_int();
}

bool RValue::is_unknown() const
{
    return ((s & ((byte) 1)) == ((byte) 0));
}

bool RValue::is_numeric() const
{
    return type.is_numeric();
}
value RValue::to_int() const
{
    if (!is_unknown())
    {
        return type.to_int(v);
    } else {
        cerr << error_tag(color_output) << "Cannot convert unknown value to integer." << endl;
        exit(1);
    }
}

fvalue RValue::to_real() const
{
    if (!is_unknown())
    {
        return type.to_real(v);
    } else {
        cerr << error_tag(color_output) << "Cannot convert unknown value to real number." << endl;
        exit(1);
    }
}

value RValue::to_int_() const
{
    return type.to_int(v);
}

fvalue RValue::to_real_() const
{
    return type.to_real(v);
}

string RValue::to_string() const
{
    return (is_unknown()? "Unknown" : type.value_to_string(v));
}

list <RValue> RValue::split() const
{
    return type.split_rvalue(*this);
}
