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

#ifndef ROMEO_PARSER_DATA_HH
#define ROMEO_PARSER_DATA_HH

#include <vector>
#include <list>
#include <map>
#include <string>

#include <valuation.hh>

namespace romeo
{
    class CTS;
    struct Job;
    class LExpression;
    class LConstraint;
    class Property;
    class GenericExpression;
    class VContext;
    class Instruction;
    class Type;
    class Parameter;
    class Transition;
    class Function;
    class Variable;

    namespace lexpression 
    {
        class AccessExpression;
        class LValue;
    }

    namespace instruction
    {
        class Block;
    }

    struct TFFrame
    {
        std::string param;
        value lbound;
        value rbound;
        std::list<const Transition*> trans;

        TFFrame(const std::string& s, const unsigned l, const unsigned r): param(s), lbound(l), rbound(r)
        {
        }
    };

    class ParserData
    {
        private:
            std::list<instruction::Block*> active_blocks;
            unsigned nblocks;

        public:
            unsigned ntrans;
            CTS* cts;
            CTS* ref_cts;
            VContext* vp;
            std::vector<Job*> jobs;
            const Type* current_type;
            bool constness;
            std::map<std::string, value> known_int_consts;

            std::list<TFFrame> tf_frames;

            unsigned last_var_id;
            bool check;

        public:
            instruction::Block* new_block();
            void push_block(instruction::Block*);
            instruction::Block* current_block() const;
            const std::list<instruction::Block*>* blocks() const;
            void pop_block();
            bool top_level() const;

            void init_new_cts_copy();

            int lookup_sparam(const std::string&) const;
            //const Transition* lookup_transition(const std::string&) const;
            //const Variable* lookup_variable(const std::string&) const;
            //const Parameter* lookup_parameter(const std::string&) const;
            //const Function* lookup_function(const std::string&) const;

            //const Transition* add_transition(const Transition&);
            //const Parameter* add_parameter(const Parameter&);
            //const Function* add_function(const Function*);
            //const Variable* add_variable(const std::string&, const Type&, bool c = false, size_t o = 0, size_t co = 0, size_t bco = 0, const instruction::Block* p = NULL, bool u = false);


            //void rebuild_lookup();

            ParserData();
            ~ParserData();

            static const lexpression::LValue* enforce_lvalue(const GenericExpression*);
            static const LExpression* enforce_le(const GenericExpression*);
            static const LExpression* enforce_numeric(const GenericExpression*);
            static const Property* enforce_lc(const GenericExpression*);
            static const Instruction* enforce_instr(const GenericExpression*);
            static const Property* enforce_property(const GenericExpression*);
            static const Property* enforce_simple(const GenericExpression*);
            static const lexpression::AccessExpression* enforce_access(const GenericExpression*);
    };
}

#endif

