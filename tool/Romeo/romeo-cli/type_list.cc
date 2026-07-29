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
#include <cstring>

#include <lobject.hh>
#include <type_list.hh>
#include <variable.hh>
#include <rvalue.hh>
#include <color_output.hh>

using namespace std;
using namespace romeo;

// Global variable containing all types
TypeList _romeo_types;

// -----------------------------------------------------------------------------

TypeList::TypeList()
{
    // Basic types
    add_type(new Void(0, "void"));
    add_type(new Real(1, "real"));
    add_type(new Integer<int8_t>(2, "int8_t"));
    add_type(new Integer<uint8_t>(3, "uint8_t"));
    add_type(new Integer<int16_t>(4, "int16_t"));
    add_type(new Integer<uint16_t>(5, "uint16_t"));
    add_type(new Integer<int32_t>(6, "int32_t"));
    add_type(new Integer<uint32_t>(7, "uint32_t"));
    add_type(new Integer<int64_t>(8, "int64_t"));
    add_type(new Integer<uint64_t>(9, "uint64_t"));
    //add_type(new Bool(11, "bool"));

    add_alias("byte", "uint8_t");
    add_alias("u8", "uint8_t");
    add_alias("i8", "int8_t");
    add_alias("u16", "uint16_t");
    add_alias("i16", "int16_t");
    add_alias("u32", "uint32_t");
    add_alias("int", "int32_t");
    add_alias("i32", "int32_t");
    add_alias("u64", "uint64_t");
    add_alias("i64", "int64_t");
}

TypeList::~TypeList()
{
    vector<const Type*>::iterator i;
    for (i=types.begin(); i!=types.end(); i++)
        delete *i;
}

void TypeList::add_type(const Type* t)
{
    const Type* x = lookup_type(t->label);
    if (x == nullptr)
    {
        types.push_back(t);
        mapping.insert(pair<const std::string, const Type*>(t->label, t));
    } else {
        cerr << error_tag(color_output) << "Cannot add already existing type: " << t->label << endl; 
        exit(1);
    }
}

void TypeList::add_alias(const string& alias, const string& s)
{
    const Type* t = lookup_type(s);
    if (t == nullptr)
    {
        cerr << error_tag(color_output) << "Cannot add alias " << alias << " to unknown type: " << s << endl; 
        exit(1);
    } else {
        mapping.insert(pair<const std::string, const Type*>(alias, t));
    }
}

unsigned TypeList::ntypes() const
{
    return types.size();
}

const Type* TypeList::lookup_type(const std::string& s) const
{
    auto k = mapping.find(s);

    if (k == mapping.end())
        return nullptr;
    else
        return k->second;
}

const Type* TypeList::type_by_id(const unsigned i) const
{
    return types[i];
}

const Type* TypeList::integer() const
{
    return integer32();
}

const Type* TypeList::integer8() const
{
    return types[2];
}

const Type* TypeList::uinteger8() const
{
    return types[3];
}

const Type* TypeList::integer16() const
{
    return types[4];
}

const Type* TypeList::uinteger16() const
{
    return types[5];
}

const Type* TypeList::integer32() const
{
    return types[6];
}

const Type* TypeList::uinteger32() const
{
    return types[7];
}

const Type* TypeList::integer64() const
{
    return types[8];
}

const Type* TypeList::uinteger64() const
{
    return types[9];
}

const Type* TypeList::real() const
{
    return types[2];
}

const Type* TypeList::void_type() const
{
    return types[1];
}


