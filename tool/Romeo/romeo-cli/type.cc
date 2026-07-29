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
#include <list>

#include <lobject.hh>
#include <type.hh>
#include <variable.hh>
#include <rvalue.hh>
#include <stack_machine.hh>
#include <color_output.hh>
#include <type_list.hh>

using namespace std;
using namespace romeo;


extern TypeList _romeo_types;
//------------------------------------------------------------------------------

Type::Type(unsigned i, string s, size_t b, size_t c): LObject(i,s), bsize(b), csize(c), tsize(b + c)
{
}

//RValue Type::evaluate(const byte V[], const size_t o, const size_t co, const bool b) const
//{
//    return RValue(*this, V, o, co, b);
//}


RValue Type::deref(const byte* a) const
{
    // Do nothing by default: only numeric types will deref lvalues
    return RValue(*this, a);
}

void Type::insert_accesses(VarSet& s, const size_t o) const
{
}

void Type::set(byte V[], const RValue& x) const
{
    cerr << error_tag(color_output) << to_string() << " does not support set()" << endl; 
    exit(1);
}

Variable Type::field_access(unsigned i, const size_t o, const bool, const bool, int decl_line) const
{
    cerr << error_tag(color_output) << "Line " << decl_line << ": " << to_string() << " does not support field access" << endl; 
    //cout << 1/0 << endl;
    exit(1);
}

size_t Type::field_offset(unsigned i) const
{
    cerr << error_tag(color_output) << to_string() << " does not support field offset access" << endl; 
    exit(1);
}

Variable Type::subscript_access(unsigned i, const size_t o, const bool, const bool, int decl_line) const
{
    cerr << error_tag(color_output) << "Line: " << decl_line << " " << to_string() << " does not support subscripted access" << endl; 
    exit(1);
}

Variable Type::ref_access(const byte V[], const bool cref, const byte** R) const
{
    cerr << error_tag(color_output) << to_string() << " does not support reference access" << endl; 
    exit(1);
}

SProgram Type::load_code() const
{
    cerr << error_tag(color_output) << to_string() << " has no load instruction." << endl; 
    exit(1);
}

SProgram Type::store_code() const
{
    cerr << error_tag(color_output) << to_string() << " has no store instruction." << endl; 
    exit(1);
}

SProgram Type::rvalue_code(const RValue& x) const
{
    cerr << error_tag(color_output) << to_string() << " has no instruction for rvalues." << endl; 
    exit(1);
}

string Type::value_to_string(const byte V[]) const
{
    cerr << error_tag(color_output) << to_string() << " does not support value printing" << endl; 
    exit(1);
}

string Type::value_to_string(memrep v) const
{
    cerr << error_tag(color_output) << to_string() << " does not support value printing" << endl; 
    exit(1);
}

const Field* Type::lookup_field(const string& s) const
{
    cerr << error_tag(color_output) << to_string() << " does not support field lookup" << endl; 
    exit(1);
}

bool Type::is_int() const
{
    return false;
}

bool Type::is_numeric() const
{
    return false;
}

value Type::to_int(const byte V[]) const
{
    cerr << error_tag(color_output) << "cannot convert "<< to_string() << " to integer." << endl; 
    exit(1);
}

fvalue Type::to_real(const byte V[]) const
{
    cerr << error_tag(color_output) << "cannot convert "<< to_string() << " to integer." << endl; 
    exit(1);
}

value Type::to_int(const memrep v) const
{
    cerr << error_tag(color_output) << "cannot convert "<< to_string() << " to integer." << endl; 
    exit(1);
}

fvalue Type::to_real(const memrep v) const
{
    cerr << error_tag(color_output) << "cannot convert "<< to_string() << " to real." << endl; 
    exit(1);
}

bool Type::is_bounded(const byte V[], const value b) const
{
    cerr << error_tag(color_output) << "cannot assess whether some " << *this << " is bounded by " << b << endl; 
    exit(1);
}

cvalue Type::max_bound(const byte V[]) const
{
    cerr << error_tag(color_output) << "cannot compute the value of variable of type " << *this << endl; 
    exit(1);
}

bool Type::is_reference() const
{
    return false;
}

bool Type::is_control() const
{
    return false;
}

bool Type::is_enum() const
{
    return false;
}

bool Type::is_raw() const
{
    return false;
}

bool Type::is_void() const
{
    return false;
}

size_t Type::byte_size() const
{
    return bsize;
}

size_t Type::cell_size() const
{
    return csize;
}

size_t Type::size() const
{
    return tsize;
}

const Type& Type::get_reftype() const
{
    return *this;
}

list<RValue> Type::split_rvalue(const RValue& x) const
{
    cerr << error_tag(color_output) << "cannot split rvalue of type " << *this << endl; 
    exit(1);
}

list<const Type*> Type::split() const
{
    cerr << error_tag(color_output) << "cannot split type " << *this << endl; 
    exit(1);
}

Type::~Type()
{
}

// -----------------------------------------------------------------------------

Void::Void(unsigned i, string s): Type(i, s, 0, 0)
{
}

bool Void::is_void() const
{
    return true;
}

Type* Void::copy() const
{
    return new Void(this->id, this->label);
}

// -----------------------------------------------------------------------------

Raw::Raw(unsigned i, string s, const size_t size): Type(i, s, size, 0)
{
}

list<RValue> Raw::split_rvalue(const RValue& x) const
{
    list<RValue> L;
    if (x.get_type().is_raw())
    {
        const uint32_t size = *((uint32_t*) x.contents().p);
        const size_t header_size = (size +1) * sizeof(uint32_t);
        size_t bo = header_size;
        for (unsigned k = 0; k < size; k++)
        {
            const uint32_t type_id = *((uint32_t*) x.contents().p + k + 1);
            const Type& t = *_romeo_types.type_by_id(type_id);
            if (!t.is_numeric())
            {
                cerr << error_tag(color_output) << "Unexpected non-numeric type in raw: " << t << endl; 
                exit(1);
            }

            const uint32_t bsize = t.byte_size();
            const uint32_t csize = t.cell_size();
            
            L.push_back(RValue(t, x.contents().p + bo).deref());
            bo += bsize + csize;
        }
    } 

    return L;
}

bool Raw::is_raw() const
{
    return true;
}

Type* Raw::copy() const
{
    return new Raw(this->id, this->label, tsize);
}

SProgram Raw::rvalue_code(const RValue& x) const
{
    cerr << error_tag(color_output) << " raw value should not be treated as an rvalue (should have been typecast before)" << endl;
    exit(1);

    //SProgram L;
    //L.add(StackMachine::PUSHA);
    //
    //const uint32_t size = *((uint32_t*) x.contents().p);
    //const size_t header_size = (size +1) * sizeof(uint32_t);
    //L.add((word) (x.contents().p + header_size)); // FIXME: ugly cast

    //return L; 
}

// -----------------------------------------------------------------------------

Enum::Enum(unsigned i, string s, const vector<string>& n): Numeric(i, s, sizeof(uint8_t)), names(n)
{
}

void Enum::set(byte V[], const RValue& x) const
{
    const Type& t = x.get_type();
    // Not a perfect check but a good compromise
    // Any enum with the same number of possible values matches
    if (!t.is_enum() || t.byte_size() != this->byte_size())
    {
        cerr << error_tag(color_output) << x.get_type().to_string() << " cannot be assigned to " << to_string() << endl; 
        exit(1);
    }

    *((uint8_t*) V) = (uint8_t) x.contents().i;
    *((byte*) (V + bsize)) = x.status() & ((byte) 1);
}

RValue Enum::equals(const memrep v1, const byte s1, const RValue& x2) const
{
    if (id == x2.get_type().id)
    {
        return RValue(v1.i == x2.contents().i, s1 & x2.status());
    } else {
        cerr << error_tag(color_output) << "cannot test equality between " << *this << " and " << x2.get_type() << endl; 
        exit(1);
    }
}

string Enum::value_to_string(const byte V[]) const
{
    return names[*((uint8_t*) V)];
}

string Enum::value_to_string(memrep v) const
{
    return names[(uint8_t) v.i];
}

bool Enum::is_bounded(const byte V[], const value b) const
{
    return true;
}

cvalue Enum::max_bound(const byte V[]) const
{
    return 0; // Should it be ROMEO_MIN_BVALUE?
}


bool Enum::is_enum() const
{
    return true;
}

Type* Enum::copy() const
{
    return new Enum(this->id, this->label, names);
}

SProgram Enum::load_code() const
{
    return SProgram(StackMachine::LOAD8);
}

SProgram Enum::store_code() const
{
    return SProgram(StackMachine::STORE8);
}

SProgram Enum::rvalue_code(const RValue& x) const
{
    SProgram L;
    L.add(StackMachine::PUSH);
    L.add(x.contents().i);

    return L;
}

RValue Enum::deref(const byte* V) const
{
    return RValue(*this, *((uint8_t*) V), *(V + sizeof(byte))); 
}

// -----------------------------------------------------------------------------

Numeric::Numeric(unsigned i, string s, size_t b): Type(i, s, b, 1)
{
}

bool Numeric::is_bounded(const byte V[], const value b) const
{
    const value val = to_int(V);
    return ((val >= 0? val: -val) <= b);
}

cvalue Numeric::max_bound(const byte V[]) const
{
    const value val = to_int(V);
    return (val >= 0? val: -val);
}

bool Numeric::is_numeric() const
{
    return true;
}

void Numeric::insert_accesses(VarSet& s, const size_t o) const
{
    s.insert(o + bsize);
}

list<RValue> Numeric::split_rvalue(const RValue& x) const
{
    return list<RValue>(1, x);
}

list<const Type*> Numeric::split() const
{
    return list<const Type*>(1, this);
}



// -----------------------------------------------------------------------------

Real::Real(unsigned i, string s): Numeric(i, s, sizeof(fvalue))
{
}

Type* Real::copy() const
{
    return new Real(this->id, this->label);
}

void Real::set(byte V[], const RValue& x) const
{
    *((fvalue*) V) = x.contents().f; 
    *((byte*) (V + bsize)) = x.status() & ((byte) 1); 
}

string Real::value_to_string(const byte V[]) const
{
    return std::to_string(to_real(V));
}

string Real::value_to_string(const memrep v) const
{
    return std::to_string(v.f);
}

value Real::to_int(const byte V[]) const
{
    return (value) to_real(V);
}

fvalue Real::to_real(const byte V[]) const
{
    return *((fvalue*) V);
}

value Real::to_int(const memrep v) const
{
    return (value) v.f;
}

fvalue Real::to_real(const memrep v) const
{
    return v.f;
}

SProgram Real::load_code() const
{
    return SProgram(StackMachine::LOADF);
}

SProgram Real::store_code() const
{
    return SProgram(StackMachine::STOREF);
}

SProgram Real::rvalue_code(const RValue& x) const
{
    SProgram L;
    L.add(StackMachine::PUSHF);
    L.add(x.contents().f);

    return L; 
}

RValue Real::deref(const byte* V) const
{
    return RValue(*((fvalue*) V), *(V + sizeof(fvalue))); 
}

// -----------------------------------------------------------------------------

Structured::Structured(unsigned i, string s, size_t b, size_t c, unsigned x): Type(i, s, b, c), size(x)
{
}

void Structured::set(byte V[], const RValue& x) const
{
    if (x.get_type().id != this->id)
    {
        cerr << error_tag(color_output) << x.get_type().to_string() << " cannot be assigned to " << to_string() << endl; 
        exit(1);
    }

    if (!x.is_unknown())
    {
        memcpy(V, x.contents().p, tsize);
    } else {
        memset(V, 0, tsize);
    }
}

SProgram Structured::store_code() const
{
    SProgram L;
    L.add(StackMachine::MEMCPY);
    L.add(tsize);

    return L;
}

SProgram Structured::rvalue_code(const RValue& x) const
{
    SProgram L;
    L.add(StackMachine::PUSHA);
    L.add((word) x.contents().p); // FIXME: ugly cast

    return L; 
}

list<RValue> Structured::split_rvalue(const RValue& x) const
{
    list<RValue> L;
    
    unsigned o = 0;
    for (auto t: split())
    {
        L.push_back(RValue(*t, x.contents().p + o).deref());
        o += t->size();
    }

    return L;
}


// -----------------------------------------------------------------------------

Record::Record(unsigned i, string s): Structured(i, s, 0, 0, 0)
{
}

Type* Record::copy() const
{
    Record* r = new Record(this->id, this->label);
    vector<Field*>::const_iterator i;
    for (i = contents.begin(); i != contents.end(); i++)
    {
        r->add_field((*i)->name, (*i)->type);
    }

    return r;
}

Field::Field(unsigned i, string s, const Type& t, size_t o, size_t co): id(i), name(s), type(t), offset(o), coffset(co)
{
}

void Record::add_field(string name, const Type& t)
{
    contents.push_back(new Field(contents.size(), name, t, bsize, bsize + t.byte_size()));
    bsize += t.size();
    tsize += t.size();
    size++;
}

Variable Record::field_access(unsigned field, const size_t o, const bool c, const bool st, int decl_line) const
{
    if (field < size)
    {
        const Field& f = *contents[field];
        return Variable(0, "#romeo_struct_field", f.type, c, st, o + f.offset, o + f.coffset, NULL, true, false);
    } else {
        cerr << error_tag(color_output) << "Line " << decl_line << " cannot access to field " << field << " in record with " << size << " fields" << endl; 
        exit(1);
    }
}

size_t Record::field_offset(unsigned field) const
{
    return contents[field]->offset;
}

string Record::value_to_string(const byte V[]) const
{
    stringstream s;
    bool comma = false;
    s << "{ ";
    for (unsigned n = 0; n < size; n++)
    {
        if (comma)
            s << ", ";
        else
            comma = true;

        s << contents[n]->name << " = " << field_access(n, 0, false, false, 0).value_to_string(V);
    }
    s << " }";

    return s.str();
}

string Record::value_to_string(memrep v) const
{
    return value_to_string(v.p);
}

const Field* Record::lookup_field(const string& s) const
{
    vector<Field*>::const_iterator i;

    for (i=contents.begin(); i != contents.end() && (*i)->name != s; i++);
    
    if (i == contents.end())
        return NULL;
    else
        return *i;
}

bool Record::is_bounded(const byte V[], const value b) const
{
    bool r = true;
    for (unsigned n = 0; n < size && r; n++)
    {
        r = field_access(n, 0, false, false, 0).is_bounded(V, b);
    }
    
    return r;
}

cvalue Record::max_bound(const byte V[]) const
{
    cvalue r = 0;
    for (unsigned n = 0; n < size && r; n++)
    {
        r = std::max(r, field_access(n, 0, false, false, 0).max_bound(V));
    }
    
    return r;
}

void Record::insert_accesses(VarSet& s, const size_t o) const
{
    for (unsigned k = 0; k < size; k++)
    {
        const Field& f = *contents[k];
        f.type.insert_accesses(s, o + f.offset);
    }
}

list<const Type*> Record::split() const
{
     list<const Type*> L;

    for (unsigned k = 0; k < size; k++)
    {
        const Field& f = *contents[k];
        for (auto y: f.type.split())
        {
            L.push_back(y);    
        }
    }

    return L;

}


// -----------------------------------------------------------------------------

Array::Array(unsigned i, string s, unsigned n, const Type& c): Structured(i, s, n*c.size(), 0, n), contents(c)
{
}

Type* Array::copy() const
{
    return new Array(this->id, this->label, this->size, this->contents);
}

Variable Array::subscript_access(unsigned s, const size_t o, const bool c, const bool st, int decl_line) const
{
    if (s < size)
    {
        const size_t array_cell = o + s * contents.size();
        return Variable(0, "#romeo_array_contents", contents, c, st, array_cell, array_cell + contents.byte_size(), NULL, true, false);
    } else {
        cerr << error_tag(color_output) << "Line " << decl_line << ": cannot access index " << s << " in array of size " << size << endl; 
        exit(1);
    }
}

string Array::value_to_string(const byte V[]) const
{
    stringstream s;
    bool comma = false;
    s << "[ ";
    for (unsigned n = 0; n < size; n++)
    {
        if (comma)
            s << ", ";
        else
            comma = true;

        s << subscript_access(n, 0, false, false, 0).value_to_string(V);
    }
    s << " ]";

    return s.str();
}

string Array::value_to_string(memrep v) const
{
    return value_to_string(v.p);
}

bool Array::is_bounded(const byte V[], const value b) const
{
    bool r = true;
    for (unsigned n = 0; n < size && r; n++)
    {
        r = subscript_access(n, 0, false, false, 0).is_bounded(V, b);
    }
    
    return r;
}

cvalue Array::max_bound(const byte V[]) const
{
    cvalue r = 0;
    for (unsigned n = 0; n < size && r; n++)
    {
        r = std::max(r, subscript_access(n, 0, false, false, 0).max_bound(V));
    }
    
    return r;
}

void Array::insert_accesses(VarSet& s, const size_t o) const
{
    for (unsigned k = 0; k < size; k++)
    {
        contents.insert_accesses(s, o + k * contents.size());
    }
}

list<const Type*> Array::split() const
{
     list<const Type*> L;

    for (unsigned k = 0; k < size; k++)
    {
        for (auto y: contents.split())
        {
            L.push_back(y);    
        }
    }

    return L;

}


// -----------------------------------------------------------------------------
Reference::Reference(unsigned i, string n, const Type& t): Type(i, n, sizeof(const byte*), 0), type(t) 
{
}

Type* Reference::copy() const
{
    return new Reference(this->id, this->label, this->type);
}

Variable Reference::ref_access(const byte V[], const bool cref, const byte** R) const
{
    *R = *((const byte**) V);
    const bool cvar = (*((byte*) (V + sizeof(byte*))) == ((byte) 2));

    return Variable(0, "#romeo_deref", type, cref || cvar, false, 0, 0, NULL, true, false);
}

bool Reference::is_reference() const
{
    return true;
}

const Type& Reference::get_reftype() const
{
    return type.get_reftype();
}

void Reference::insert_accesses(VarSet& s, const size_t o) const
{
    s.insert(o + bsize);
}

SProgram Reference::store_code() const
{
    return SProgram(StackMachine::STOREP);
}

string Reference::value_to_string(const byte V[]) const
{
    if (type.cell_size() > 0 && (*(V + type.byte_size()) & ((byte) 1)) == ((byte) 0))
    {
        return "Unknown";
    } else {
        return type.value_to_string(*((const byte**) V));
    }
}

string Reference::value_to_string(memrep v) const
{
    if (type.cell_size() > 0 && (*(v.p + type.byte_size()) & ((byte) 1)) == ((byte) 0))
    {
        return "Unknown";
    } else {
        return type.value_to_string(*((const byte**) v.p));
    }
}

