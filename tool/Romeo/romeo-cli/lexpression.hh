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

#ifndef ROMEO_LEXPRESSION_HH
#define ROMEO_LEXPRESSION_HH

#include <simple_property.hh>
#include <rvalue.hh>

namespace romeo
{
    class RValue;
    class CTS;
    class Parameter;

    class LinearExpression;

    class LExpression: public SimpleProperty
    {
        public:
            LExpression(int);

            virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
            virtual bool is_lexpression() const;
            virtual PResult* eval(const PState*) const;

            virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
    };

    namespace lexpression
    {
        class DyadicOperator: public LExpression
        {
            protected:
                const LExpression& left;
                const LExpression& right;

            public:
                DyadicOperator(const LExpression&, const LExpression&, int);
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual bool is_numeric() const;
                virtual bool has_vars() const;
                virtual bool has_params() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~DyadicOperator();
        };
        
        class Litteral: public LExpression
        {
            private:
                RValue val;

            public:
                Litteral(const RValue&, int);

                RValue get_value() const;

                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const;
                virtual const Type& access_type() const;
                virtual const Variable* top_var() const;
                virtual bool has_constant_offsets() const;

                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                virtual SProgram codegen() const;
                virtual std::string to_string() const;

                virtual bool is_const() const;
                virtual bool is_rvalue() const;
                virtual bool is_static() const;
                virtual bool is_litteral(cvalue) const;
                virtual bool is_numeric() const;

                virtual const LExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };

        class RLValue: public LExpression
        {
            private:
                const AccessExpression& e;

            public:
                RLValue(const AccessExpression&, int);

                virtual SProgram codegen() const;
                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual bool is_rlvalue() const;
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual bool is_numeric() const;
                virtual bool has_vars() const;
                virtual bool has_params() const;

                const Type& get_type() const;
                
                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;

                const AccessExpression* access_expr() const;

                ~RLValue();
        };


        class Parameter: public LExpression
        {
            protected:
                const romeo::Parameter& param;
 
            public:
                Parameter(const romeo::Parameter&, int);
                virtual SProgram codegen() const;
 
                virtual bool has_vars() const;
                virtual bool has_params() const;
                virtual bool is_numeric() const;
                virtual bool is_const() const;

                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };
 
        class SyntaxParameter: public LExpression
        {
            protected:
                unsigned id;
 
            public:
                SyntaxParameter(const unsigned, int);
 
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual bool is_numeric() const;
        };
 
        class Abstracted: public LExpression
        {
            public:
                Abstracted(int);
                virtual SProgram codegen() const;
 
                virtual bool is_const() const;
                virtual bool is_abstracted() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };
 
        class ClockVariable: public LExpression
        {
            protected:
                const Transition* transition;
 
            public:
                ClockVariable(const Transition*, int);

                const property::FiredTransition* to_property() const;
 
                virtual bool is_clock_var() const;

                // virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

        };
 
       // Arithmetic
        class Addition: public DyadicOperator
        {
            public:
                Addition(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };
 
        class Subtraction: public DyadicOperator
        {
            public:
                Subtraction(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };
 
        class Multiplication: public DyadicOperator
        {
            public:
                Multiplication(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };
 
        class Division: public DyadicOperator
        {
            public:
                Division(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;
        };

        class Modulo: public DyadicOperator
        {
            public:
                Modulo(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

 
        class Min: public DyadicOperator
        {
            public:
                Min(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

        };
 
        class Max: public DyadicOperator
        {
            public:
                Max(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        // Bitwise operations
        class BitAnd: public DyadicOperator
        {
            public:
                BitAnd(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class BitOr: public DyadicOperator
        {
            public:
                BitOr(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class BitNot: public LExpression
        {
            private:
                const LExpression& e;

            public:
                BitNot(const LExpression&, int);
                virtual SProgram codegen() const;

                virtual bool is_numeric() const;
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class ShiftL: public DyadicOperator
        {
            public:
                ShiftL(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class ShiftR: public DyadicOperator
        {
            public:
                ShiftR(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

    }
}

#endif

