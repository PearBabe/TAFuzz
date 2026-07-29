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

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <sstream>

#include <list>
#include <algorithm>

#include <variable.hh>

#include <type.hh>
#include <lobject.hh>
#include <rvalue.hh>
#include <valuation.hh>
#include <color_output.hh>
#include <instruction.hh>
#include <cts.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
extern Logger Log;

Variable::Variable(const unsigned i, const string& s, const Type& t, bool c, bool sta, size_t o, size_t co, const instruction::Block* p, bool u, bool st): LObject(i,s), type(t), byte_offset(o), cell_offset(co), parent_block(p), constant(c), vstatic(sta), utility(u), state(st)
{
}

Variable::Variable(const Variable& v): LObject(v), type(v.type), byte_offset(v.byte_offset), cell_offset(v.cell_offset), parent_block(v.parent_block), constant(v.constant), vstatic(v.vstatic), utility(v.utility), state(v.state)
{
}

Variable::~Variable()
{
}

Variable Variable::subscript_access(const unsigned s, int decl_line) const
{
    return type.subscript_access(s, byte_offset, constant, vstatic, decl_line);
}

Variable Variable::field_access(const unsigned s, int decl_line) const
{
    return type.field_access(s, byte_offset, constant, vstatic, decl_line);
}

Variable Variable::ref_access(const byte V[], const byte **R) const
{
    Variable x = type.ref_access(V + byte_offset, constant, R);

    return x;
}

void Variable::insert_accesses(VarSet& s) const
{
    if (!constant)
    {
        //cout << "ins " << label << " " << type.label << " " << type.cell_size() << " " << cell_offset << endl;
        //for (unsigned i = 0; i < type.cell_size(); i++)
        //{
        //    s.insert(cell_offset + i);
        //}
        type.insert_accesses(s, byte_offset);
    }
}

bool Variable::is_unknown(const byte V[]) const
{
    return type.is_numeric() && (*(V + cell_offset) == ((byte) 0)); 
}

const Type& Variable::get_type() const
{
    return type;
}

const Type& Variable::get_reftype() const
{
    return type.get_reftype();
}

void Variable::set_offset(const size_t s) const
{
    byte_offset = s;
}

void Variable::set_coffset(const size_t s) const
{
    cell_offset = s;
}

size_t Variable::get_offset() const
{
    return byte_offset;
}

size_t Variable::get_coffset() const
{
    return cell_offset;
}

size_t Variable::byte_size() const
{
    return type.byte_size();
}

size_t Variable::cell_size() const
{
    return type.cell_size();
}

string Variable::to_string() const
{
    stringstream s;
    s << label;// << " (id " << id << ", type " << type << ", address " << this<< ")";
    return s.str();
}

string Variable::value_to_string(const byte V[]) const
{
    if (is_unknown(V))
    {
        return "Unknown";
    } else {
        return type.value_to_string(V + byte_offset);
    }
}

const Field* Variable::lookup_field(const string& s) const
{
    return type.lookup_field(s);
}

const instruction::Block* Variable::block() const
{
    return parent_block;
}

bool Variable::is_constant() const
{
    return constant;
}

bool Variable::is_static() const
{
    return vstatic;
}

bool Variable::is_state() const
{
    return state;
}

bool Variable::is_utility() const
{
    return utility;
}

bool Variable::is_bounded(const byte V[], const value b) const
{
    if (is_unknown(V))
    {
        return false;
    } else {
        return type.is_bounded(V + byte_offset, b);
    }
}

cvalue Variable::max_bound(const byte V[]) const
{
    if (is_unknown(V))
    {
        return 0;
    } else {
        return type.max_bound(V + byte_offset);
    }
}

//------------------------------------------------------------------------------

VariableList::VariableList(): NV(0), last_var(nullptr), current_offset(0), state_size(0) {}

VariableList::VariableList(const VariableList& L): variables(L.variables), NV(L.NV), last_var(nullptr), current_offset(L.current_offset), state_size(L.state_size) 
{
}

VariableList::VariableList(const VariableList& L, const VarSet& S): variables(), NV(0), last_var(nullptr), current_offset(0), state_size(0) 
{
    for (auto v: L.variables)
    {
        if (S.count(v.get_coffset()))
        {
            add_variable(v);
        }
    }
}

const Variable* VariableList::add_variable(const Variable& v)
{
    this->NV++;

    const Variable* var;
    if (v.is_state())
    {
        // We keep state variables in front
        this->variables.push_front(v);
        var = &variables.front();

        // Total size of the new variable
        const size_t vsize = v.byte_size() + v.cell_size();

        if (state_size < current_offset)
        {
            // make room for the new variable
            for (auto& i : variables)
            {
                if (!i.is_state())
                {
                    i.set_offset(i.get_offset() + vsize);
                    i.set_coffset(i.get_coffset() + vsize);
                }
            }
        } 
        
        // Add at the end of the state description
        var->set_offset(state_size);
        state_size += v.byte_size();

        var->set_coffset(state_size);
        state_size += v.cell_size();

        current_offset += vsize;
    } else {
        this->variables.push_back(v);
        var = &variables.back();

        // Add at the end of the complete vector
        var->set_offset(current_offset);
        current_offset += v.byte_size();

        var->set_coffset(current_offset);
        current_offset += v.cell_size();
    }

    last_var = var;

    return var;
}

unsigned VariableList::nvars() const { return NV; }

size_t VariableList::vbyte_size() const { return current_offset; }

size_t VariableList::vstate_size() const { return state_size; }

const Variable* VariableList::last_added_variable() const
{
    return last_var;
}

string VariableList::to_string() const
{
    stringstream oss;

    for (auto i: variables)
    {
        oss << "// variable ";
        oss << i.label << " (id " << i.id << " offset "<< i.get_offset() << ") ";
        oss << endl;
    }

    return oss.str();
}

string VariableList::value_to_string(const byte V[]) const
{
    stringstream oss;

    for (auto i: variables)
    {
        if (i.is_state())
        {
            oss << i.label << "=" << i.value_to_string(V) << " ";
        }
    }

    return oss.str();
}

bool VariableList::bounded(const unsigned bound, const byte V[]) const
{
    // State variables are in front by construction
    auto i = variables.begin();
    while (i != variables.end() && i->is_state())
    {
        if (!i->is_utility() && !i->is_bounded(V, bound))
        {
            return false;
        }

        i++;
    }

    return true;
}

cvalue VariableList::max_bound(const byte V[]) const
{
    cvalue r = 0;

    // State variables are in front by construction
    auto i = variables.begin();
    while (i != variables.end() && i->is_state())
    {
        if (!i->is_utility())
        {
            r = std::max(r, i->max_bound(V));
        }

        i++;
    }

    return r;
}

list<Variable>::const_iterator VariableList::begin() const
{
    return variables.begin();
}

list<Variable>::const_iterator VariableList::end() const
{
    return variables.end();
}

void VariableList::clear()
{
    variables.clear();
}

VariableList::~VariableList()
{
    //for (list<const Variable*>::const_iterator i=variables.begin(); i != variables.end(); i++)
    //{
    //    delete *i;
    //}
}


// -----------------------------------------------------------------------------

VContext::VContext(unsigned i): next_var_id(i), statics(nullptr) {}

VContext::VContext(const VContext& C): last(C.last), next_var_id(C.next_var_id), variables(C.variables), static_consts(C.static_consts)
{
    build_variable_lookup();

    if (C.statics == nullptr)
    {
        this->statics = nullptr;
    } else {
        this->statics = new byte[C.static_consts.vbyte_size()];
        memcpy(this->statics, C.statics, C.static_consts.vbyte_size());
    }
}


VContext::VContext(const VContext& C, const VarSet& S): last(C.last), next_var_id(C.next_var_id), variables(C.variables, S), static_consts(C.static_consts)
{
    build_variable_lookup();

    if (C.statics == nullptr)
    {
        this->statics = nullptr;
    } else {
        this->statics = new byte[C.static_consts.vbyte_size()];
        memcpy(this->statics, C.statics, C.static_consts.vbyte_size());
    }
}

void VContext::build_variable_lookup()
{
    for (auto i = variables.begin(); i != variables.end(); i++)
    {
        variables_by_label[i->label].push_back(&(*i));
        variables_by_id[i->id] = &(*i);
    }

    for (auto i = static_consts.begin(); i != static_consts.end(); i++)
    {
        variables_by_label[i->label].push_back(&(*i));
        variables_by_id[i->id] = &(*i);
    }
}

// name, type, constant?, static?, offset, unknown status offset, block it belongs to, utility?, state variable?
void VContext::add_variable(const string& n, const Type& t, bool c, bool st, size_t o, size_t co, const instruction::Block* p, bool u, bool s)
{
    if (st)
    {
        last = &CTS::current_cts->static_consts;
    } else {
        last = &variables;
    }
    const unsigned i = next_var_id; //constants.nvars() + variables.nvars();
    next_var_id++;

    const Variable* v = last->add_variable(Variable(i, n, t, c, st, o, co, p, u, s));
    variables_by_label[n].push_back(v);
    variables_by_id[i] = v;
}

void VContext::add_variable_copy(const Variable& v)
{
    if (v.is_static())
    {
        last = &CTS::current_cts->static_consts;
    } else {
        last = &variables;
    }

    const Variable* v1 = last->add_variable(v);
    variables_by_label[v.label].push_back(v1);
    variables_by_id[v.id] = v1;

    next_var_id = max(v.id + 1, next_var_id);
}

const Variable* VContext::last_added_variable() const
{
    return last->last_added_variable();
}

const Variable* VContext::lookup_variable_scoped(const std::string& s, const list<instruction::Block*>* ab) const
{
    map<string, list<const Variable*> >::const_iterator i = variables_by_label.find(s);

    if (i == variables_by_label.end())
    {
        return nullptr;
    } else {
        
        list<const Variable*>::const_reverse_iterator k;
        k = i->second.rbegin();
        while (k != i->second.rend() &&
            // Not the good label
            ((*k)->label != s || 
            // In a block that is active if specified
            (ab != nullptr && (find(ab->begin(), ab->end(), (*k)->block()) == ab->end()))))
        {
            k++;
        }

        if (k == i->second.rend())
        {
            return nullptr;
        } else {
            return (*k);
        }
    }


}

const Variable* VContext::lookup_variable_by_label(const std::string& s) const
{
    map<string, list<const Variable*> >::const_iterator i = variables_by_label.find(s);

    if (i == variables_by_label.end())
    {
        return nullptr;
    } else {
        
        list<const Variable*>::const_reverse_iterator k;
        k = i->second.rbegin();
        while (k != i->second.rend() && (*k)->label != s)
            // Not the good label
        {
            k++;
        }

        if (k == i->second.rend())
        {
            return nullptr;
        } else {
            return (*k);
        }
    }

}

const Variable* VContext::lookup_variable_by_id(unsigned k) const
{
    map<unsigned, const Variable*>::const_iterator i = variables_by_id.find(k);

    if (i == variables_by_id.end())
    {
        return nullptr;
    } else {
        return i->second;
    }

}

void VContext::clear()
{
    variables.clear();
}

VContext::~VContext()
{
}

