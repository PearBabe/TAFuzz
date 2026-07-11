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

#ifndef ROMEO_INSTRUCTION_HH
#define ROMEO_INSTRUCTION_HH

#include <string>
#include <vector>

#include <generic_expression.hh>
#include <valuation.hh>

namespace romeo
{
    class CTS;
    class LExpression;
    class Property;
    class RValue;
    class SProgram;

    namespace lexpression
    {
        class AccessExpression;
    }

    class Instruction: public GenericExpression
    {
        public:
            Instruction(int);
            virtual bool is_nop() const;
            virtual bool is_instruction() const;
    };

    namespace instruction
    {
        class Assignment: public Instruction
        {
            private:
                const lexpression::AccessExpression& v;
                const LExpression& e;

            public:
                virtual SProgram codegen() const;

                Assignment(const lexpression::AccessExpression&, const LExpression&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
            
                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~Assignment();
        };

        class Initialisation: public Instruction
        {
            private:
                const Variable& v;
                const LExpression& e;

            public:
                virtual SProgram codegen() const;

                Initialisation(const Variable&, const LExpression&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~Initialisation();
        };

        class Block: public Instruction
        {
            protected:
                std::vector<const Instruction*> instrs;

            public:
                virtual SProgram codegen() const;

                Block(int);
                Block(const Block&);
                Block(const std::vector<const Instruction*>&, int);

                void add_instruction(const Instruction*);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                void clear();

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~Block();
        };

        class LoopBlock: public Block
        {
            public:
                LoopBlock(const Block&);
                LoopBlock(const LoopBlock&);

                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                //virtual ~LoopBlock();
        };

        class If: public Instruction
        {
            private:
                const Property& condition;
                const Instruction& instructions;
 
            public:
                virtual SProgram codegen() const;

                If(const Property&, const Instruction&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~If();
        };

        class IfElse: public Instruction
        {
            private:
                const Property& condition;
                const Instruction& instructions;
                const Instruction& else_instructions;
 
            public:
                virtual SProgram codegen() const;

                IfElse(const Property&, const Instruction&, const Instruction&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~IfElse();
        };

        class While: public Instruction
        {
            private:
                const Property& condition;
                const LoopBlock instructions;
 
            public:
                virtual SProgram codegen() const;

                While(const Property&, const LoopBlock&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~While();
        };

        class DoWhile: public Instruction
        {
            private:
                const Property& condition;
                const LoopBlock instructions;
 
            public:
                virtual SProgram codegen() const;

                DoWhile(const Property&, const LoopBlock&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~DoWhile();
        };

        class For: public Instruction
        {
            private:
                const Instruction& init;
                const Instruction& step;
                const Property& condition;
                const LoopBlock instructions;
 
            public:
                virtual SProgram codegen() const;

                For(const Instruction&, const Instruction&, const Property&, const LoopBlock&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~For();
        };

        class Nop: public Instruction
        {
            public:
                Nop();
                virtual SProgram codegen() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual bool is_nop() const;
        };

        class BinaryCombinator: public Instruction
        {
            protected:
                const Instruction& first;
                const Instruction& second;

            public:
                BinaryCombinator(const Instruction&, const Instruction&, int);

                virtual bool has_vars() const;
                virtual bool has_params() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~BinaryCombinator();
        };

        class Comma: public BinaryCombinator
        {
            public:
                Comma(const Instruction&, const Instruction&, int);

                virtual SProgram codegen() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class Return: public Instruction
        {
            private:
                const LExpression& ret;

            public:
                Return(const LExpression&, int);

                virtual SProgram codegen() const;

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void reads(VarSet&) const;
                virtual void writes(VarSet&) const;

                virtual ~Return();

        };
 
        class Log: public Instruction
        {
            private:
                const LExpression& e;

            public:
                Log(const LExpression&, int);

                virtual SProgram codegen() const;

                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual void reads(VarSet&) const;
                virtual void writes(VarSet&) const;

                virtual ~Log();

        };

    }

}

#endif

