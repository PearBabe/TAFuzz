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

#ifndef ROMEO_VARIABLE_HH
#define ROMEO_VARIABLE_HH

#include <list>
#include <set>
#include <map>

#include <lobject.hh>
#include <valuation.hh>

namespace romeo
{
    class RValue;
    class Type;
    struct Field;

    namespace instruction
    {
        class Block;
    }

    typedef std::set<size_t> VarSet;

    class Variable: public LObject
    {
        protected:
            const Type& type;
            mutable size_t byte_offset;
            mutable size_t cell_offset;
            const instruction::Block* parent_block;
            const bool constant;
            const bool vstatic;
            const bool utility;
            const bool state;

        public:
            bool is_unknown(const std::byte[]) const;

            Variable subscript_access(const unsigned, int) const;
            Variable field_access(const unsigned, int) const;
            Variable ref_access(const std::byte[], const std::byte **) const;

            size_t byte_size() const;
            size_t cell_size() const;
            const Type& get_type() const;
            const Type& get_reftype() const; // return referenced type if ref, normal type otherwise

            void set_offset(const size_t) const;
            void set_coffset(const size_t) const;
            size_t get_offset() const;
            size_t get_coffset() const;
            virtual std::string to_string() const;

            std::string value_to_string(const std::byte[]) const;
            const Field* lookup_field(const std::string&) const;

            void insert_accesses(VarSet&) const;

            Variable(const unsigned, const std::string&, const Type&, bool c, bool st, size_t, size_t, const instruction::Block* p, bool u, bool s);
            Variable(const Variable&);

            const instruction::Block* block() const;
            bool is_constant() const; // cannot be written; goes with the other variables if not static
            bool is_static() const;   // value known at compile-time; goes into consts
            bool is_state() const;
            bool is_utility() const;
            bool is_bounded(const std::byte[], const value) const;
            cvalue max_bound(const std::byte[]) const;

            virtual ~Variable();
    };
    
    struct cmpvar
    {
        bool operator()(const Variable* x, const Variable* y) const
        {
            return x->label < y->label;
        }
    };

    namespace expression
    {
        class FunctionCall;
    }

    class VariableList
    {
        protected:
            std::list<Variable> variables;
            unsigned NV;
            const Variable* last_var;

            size_t current_offset;
            size_t state_size;

        public:

            VariableList();
            VariableList(const VariableList&);
            VariableList(const VariableList&, const VarSet&);

            const Variable* add_variable(const Variable&);
            
            unsigned nvars() const;
            size_t vbyte_size() const;
            size_t vstate_size() const;
            const Variable* last_added_variable() const;

            std::string to_string() const;
            std::string value_to_string(const std::byte[]) const;

            bool bounded(const unsigned, const std::byte[]) const;
            cvalue max_bound(const std::byte[]) const;

            std::list<Variable>::const_iterator begin() const;
            std::list<Variable>::const_iterator end() const;

            void clear();

            ~VariableList();

        friend class expression::FunctionCall;
    };

    class VContext
    {
        protected:
            VariableList* last;

            std::map<std::string, std::list<const Variable*> > variables_by_label;
            std::map<unsigned, const Variable*> variables_by_id;

            unsigned next_var_id;

        public:
            VariableList variables;
            VariableList static_consts;

            std::byte* statics;

        public:
            VContext(unsigned);
            VContext(const VContext&);
            VContext(const VContext&, const VarSet&);

            void build_variable_lookup();

            void add_variable(const std::string&, const Type&, bool c, bool st, size_t o, size_t co, const instruction::Block* p, bool u, bool s);
            void add_variable_copy(const Variable&);

            const Variable* last_added_variable() const;
            const Variable* lookup_variable_scoped(const std::string&, const std::list<instruction::Block*>* ab=NULL) const;
            const Variable* lookup_variable_by_label(const std::string&) const;
            const Variable* lookup_variable_by_id(unsigned) const;

            void clear();

            ~VContext();
    };
}

#endif

