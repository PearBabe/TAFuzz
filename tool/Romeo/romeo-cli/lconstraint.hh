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

#ifndef ROMEO_LCONSTRAINT_HH
#define ROMEO_LCONSTRAINT_HH

#include <lexpression.hh>
#include <expression.hh>

namespace romeo
{
    class PResult;
    class PState;
    class LExpression;
    class CTS;
    class RValue;
    class SProgram;

    class LConstraint: public LExpression
    {
        public:
            LConstraint(int);

            virtual bool is_lconstraint() const;
    };

    namespace lexpression
    {
        class LValue;
    }

    namespace lconstraint
    {
        class DyadicOperator: public LConstraint
        {
            protected:
                const LExpression& left;
                const LExpression& right;

            public:
                DyadicOperator(const LExpression&, const LExpression&, int);
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual bool has_vars() const;
                virtual bool has_params() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~DyadicOperator();
        };

        class True: public LConstraint
        {
            public:
                True(int);
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class False: public LConstraint
        {
            public:
                False(int);
                virtual bool is_const() const;
                virtual bool is_static() const;
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };

        // Comparisons
        class Eq: public DyadicOperator
        {
            public:
                Eq(const LExpression&, const LExpression&, int);

                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class Neq: public DyadicOperator
        {
            public:
                Neq(const LExpression&, const LExpression&, int);
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                virtual SProgram codegen() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class Leq: public DyadicOperator
        {
            public:
                Leq(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class Geq: public DyadicOperator
        {
            public:
                Geq(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class Less: public DyadicOperator
        {
            public:
                Less(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
 
        class Greater: public DyadicOperator
        {
            public:
                Greater(const LExpression&, const LExpression&, int);
                virtual SProgram codegen() const;
                
                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };

        
        class Forall: public LConstraint
        {
            private:
                const lexpression::LValue& idx;
                const LExpression& min_idx;
                const LExpression& max_idx;
                const Property& constr;
                 
            public:
                Forall(const lexpression::LValue&, const LExpression&, const LExpression&, const Property&, int);
                virtual SProgram codegen() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

        };
 
        class Exists: public LConstraint
        {
            private:
                const lexpression::LValue& idx;
                const LExpression& min_idx;
                const LExpression& max_idx;
                const Property& constr;
                 
            public:
                Exists(const lexpression::LValue&, const LExpression&, const LExpression&, const Property&, int);
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
