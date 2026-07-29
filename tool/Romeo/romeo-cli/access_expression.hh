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

#ifndef ACCESS_EXPRESSION_HH
#define ACCESS_EXPRESSION_HH

#include <lexpression.hh>
#include <sexpression.hh>
#include <rvalue.hh>

namespace romeo
{
    class SProgram;
    class Variable;
    class Type;

    namespace lexpression
    {
        class AccessExpression: public LExpression
        {
            public:
                AccessExpression(int);

                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const = 0;
                virtual const Type& access_type() const = 0;
                virtual const Variable* top_var() const = 0;
                virtual bool has_constant_offsets() const;
                virtual bool is_access() const;
                virtual bool is_numeric() const;
        };

        class LValue: public AccessExpression
        {
            protected:
                const Variable& var;
 
            public:
                LValue(const Variable&, int);
 
                virtual bool is_lvalue() const;
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual bool has_vars() const;
                virtual bool has_params() const;


                virtual LinearExpression linear_expression(const std::byte[], const std::byte[]) const;
                
                virtual SProgram codegen() const;
                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const;
                virtual const Type& access_type() const;

                virtual const Variable* top_var() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

        };

        class ReferenceAccess: public LValue
        {    
            protected:
                const GenericExpression* bound_expr;

            public:
                ReferenceAccess(const Variable&, int);
                ReferenceAccess(const Variable&, const GenericExpression*, int);
 
                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const;
                virtual SProgram codegen() const;

                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual bool is_refaccess() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;
        };

        class AccessOperator: public AccessExpression
        {
            protected:
                const AccessExpression& e;

            public:
                AccessOperator(const AccessExpression&, int);

                virtual const Variable* top_var() const;
        };

        class SubscriptAccess: public AccessOperator
        {
            private:
                SExpression subscript;

            public:
                SubscriptAccess(const AccessExpression&, const SExpression&, int);
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual SProgram codegen() const;
                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const;
                virtual const Type& access_type() const;
                virtual std::string to_string() const;

                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;
                virtual bool has_constant_offsets() const;
        };

        class FieldAccess: public AccessOperator
        {
            private:
                const unsigned field;

            public:
                FieldAccess(const AccessExpression&, const unsigned, int);
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual SProgram codegen() const;
                virtual Variable access(const std::byte[], const std::byte[], const std::byte**) const;
                virtual const Type& access_type() const;
                virtual std::string to_string() const;

                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual bool has_constant_offsets() const;

        };
    }
}

#endif

