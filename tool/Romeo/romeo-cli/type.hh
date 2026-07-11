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

#ifndef ROMEO_TYPE_HH
#define ROMEO_TYPE_HH

#include <vector>

#include <valuation.hh>
#include <lobject.hh>
#include <variable.hh>

namespace romeo
{
    class RValue;
    class SProgram;
    class Variable;
    union memrep;
    class Real;
    struct Field;

    class Type: public LObject
    {
        protected:
            size_t bsize;
            size_t csize;
            size_t tsize;

        public:
            Type(unsigned, std::string, size_t, size_t);
     
            size_t byte_size() const;
            size_t cell_size() const;
            size_t size() const;
            
            // For vector/field based operations (mentioning offset and co): the std::byte[] is the whole vector

            virtual void set(std::byte[], const RValue&) const;
            virtual Variable field_access(unsigned, const size_t, const bool, const bool, int) const;
            virtual size_t field_offset(unsigned) const;
            virtual Variable subscript_access(unsigned, const size_t, const bool, const bool, int) const;
            virtual Variable ref_access(const std::byte V[], const bool c, const std::byte** R) const;
            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;
            virtual const Field* lookup_field(const std::string&) const;

            virtual SProgram load_code() const;
            virtual SProgram store_code() const;
            virtual SProgram rvalue_code(const RValue&) const;

            virtual const Type& get_reftype() const;
            virtual void insert_accesses(VarSet&, const size_t) const;

            virtual RValue deref(const std::byte*) const;
            
            // For RValue: in those the std::byte[] contains only the value
            virtual bool is_int() const;
            virtual bool is_numeric() const;
            virtual value to_int(const std::byte[]) const;
            virtual fvalue to_real(const std::byte[]) const;
            virtual value to_int(const memrep) const;
            virtual fvalue to_real(const memrep) const;
            virtual bool is_bounded(const std::byte[], const value) const;
            virtual cvalue max_bound(const std::byte[]) const;

            virtual bool is_reference() const;
            virtual bool is_raw() const;
            virtual bool is_control() const;
            virtual bool is_enum() const;
            virtual bool is_void() const;

            virtual Type* copy() const = 0;

            virtual std::list<RValue> split_rvalue(const RValue&) const;
            virtual std::list<const Type*> split() const;

            virtual ~Type();
    };

    class Void: public Type
    {
        public:
            Void(unsigned, std::string);

            virtual bool is_void() const;
            virtual Type* copy() const;
    };

    class Raw: public Type
    {
        public:
            Raw(unsigned, std::string, const size_t);
            virtual bool is_raw() const;

            virtual Type* copy() const;

            virtual std::list<RValue> split_rvalue(const RValue&) const;
            virtual SProgram rvalue_code(const RValue&) const;
    };

    class Numeric: public Type
    {
        public:
            Numeric(unsigned, std::string, size_t);
            virtual bool is_bounded(const std::byte[], const value) const;
            virtual cvalue max_bound(const std::byte[]) const;
            virtual bool is_numeric() const;
            virtual void insert_accesses(VarSet&, const size_t) const;

            virtual std::list<RValue> split_rvalue(const RValue&) const;
            virtual std::list<const Type*> split() const;
    };

    class Enum: public Numeric
    {
        private:
            std::vector<std::string> names;

        public:
            Enum(unsigned, std::string, const std::vector<std::string>&);

            virtual void set(std::byte[], const RValue&) const;
            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;
            virtual bool is_enum() const;
            virtual RValue equals(const memrep, const std::byte, const RValue&) const;

            virtual SProgram load_code() const;
            virtual SProgram store_code() const;
            virtual SProgram rvalue_code(const RValue&) const;

            virtual RValue deref(const std::byte*) const;

            virtual bool is_bounded(const std::byte[], const value) const;
            virtual cvalue max_bound(const std::byte[]) const;
            virtual Type* copy() const;
    };

    class Real: public Numeric
    {
        public:
            Real(unsigned, std::string);

            virtual void set(std::byte[], const RValue&) const;
            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;

            virtual value to_int(const std::byte[]) const;
            virtual fvalue to_real(const std::byte[]) const;

            virtual value to_int(const memrep) const;
            virtual fvalue to_real(const memrep) const;

            virtual SProgram load_code() const;
            virtual SProgram store_code() const;
            virtual SProgram rvalue_code(const RValue&) const;

            virtual RValue deref(const std::byte*) const;

            virtual Type* copy() const;
    };

    class Structured: public Type
    {
        protected:
            unsigned size;

        public:
            Structured(unsigned, std::string, size_t, size_t, unsigned);

            //virtual SProgram load_code() const;
            virtual SProgram store_code() const;
            virtual SProgram rvalue_code(const RValue&) const;

            virtual void set(std::byte[], const RValue&) const;

            virtual std::list<RValue> split_rvalue(const RValue&) const;
    };

    class Array: public Structured
    {
        private:
            const Type& contents;

        public:
            Array(unsigned, std::string, unsigned, const Type&);

            virtual Variable subscript_access(unsigned, const size_t, const bool, const bool, int) const;
            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;
            virtual bool is_bounded(const std::byte[], const value) const;
            virtual cvalue max_bound(const std::byte[]) const;
            virtual void insert_accesses(VarSet&, const size_t) const;

            virtual std::list<const Type*> split() const;

            virtual Type* copy() const;
    };

    struct Field
    {
        unsigned id;
        std::string name;
        const Type& type;
        size_t offset;
        size_t coffset;

        Field(unsigned, std::string, const Type&, const size_t, const size_t);
        Field& operator=(const Field&);
    };

    class Record: public Structured
    {
        private:
            std::vector<Field*> contents;
        
        public:
            Record(unsigned, std::string);

            void add_field(std::string, const Type&);

            virtual Variable field_access(unsigned, const size_t, const bool, const bool, int) const;
            virtual size_t field_offset(unsigned) const;
            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;
            virtual const Field* lookup_field(const std::string&) const;
            virtual bool is_bounded(const std::byte[], const value) const;
            virtual cvalue max_bound(const std::byte[]) const;
            virtual void insert_accesses(VarSet&, const size_t) const;

            virtual std::list<const Type*> split() const;

            virtual Type* copy() const;
    };

    class Reference: public Type
    {
        private:
            const Type& type;

        public:
            Reference(unsigned, std::string, const Type&);

            virtual Variable ref_access(const std::byte V[], const bool c, const std::byte** R) const;
            virtual void insert_accesses(VarSet&, const size_t) const;
            virtual bool is_reference() const;

            virtual Type* copy() const;

            virtual std::string value_to_string(const std::byte[]) const;
            virtual std::string value_to_string(memrep) const;

            const Type& get_reftype() const;
            virtual SProgram store_code() const;
    };

}

#endif

