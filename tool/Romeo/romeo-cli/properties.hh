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

#ifndef ROMEO_PROPERTIES_HH
#define ROMEO_PROPERTIES_HH

#include <property.hh>
#include <valuation.hh>
#include <sexpression.hh>

namespace romeo
{
    // Forward declarations
    class TimeInterval;
    class CTS;
    class PResult;
    class Transition;
    class Polyhedron;
    class RValue;
    class Variable;
    struct Job;
    struct Key;

    namespace property
    {
        class CostLimit;
    }

    namespace lconstraint
    {
        class Eq;
        class Leq;
    }

    namespace instruction
    {
        class Assignment;
    }

    namespace property
    {
        class Not: public Property
        {
            private:
                const Property& statement;

            public:
                Not(const Property&, int);
                virtual PResult* eval(const PState*) const;
                virtual SProgram codegen() const;

                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual void prepare(CTS&) const;  
                virtual bool is_simple() const;
                virtual bool is_lconstraint() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual bool has_cost() const;

                virtual const Property* negation(CTS&) const;

                virtual ~Not();
        };
    
        class DyadicOperator: public Property
        {
            protected:
                const Property& left;
                const Property& right;

            public:
                DyadicOperator(const Property&, const Property&, int);
                virtual bool is_simple() const;
                virtual bool is_lconstraint() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual bool has_cost() const;
                
                virtual void prepare(CTS&) const;  
                virtual ~DyadicOperator();
        };

        class And: public DyadicOperator
        {
            public:
                And(const Property&, const Property&, int);
                virtual PResult* eval(const PState*) const;
                virtual SProgram codegen() const;

                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual std::list<VarSet> var_reads() const;

                virtual const Property* negation(CTS&) const;
        };
    
        class Or: public DyadicOperator
        {
            public:
                Or(const Property&, const Property&, int);
                virtual PResult* eval(const PState*) const;
                virtual SProgram codegen() const;

                virtual Polyhedron constraint(const std::byte[], const std::byte[], const unsigned) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual const Property* negation(CTS&) const;
        };
    
        class TemporalProperty: public Property
        {
            protected:
                SExpression phi;
                SExpression psi;

            public:
                TemporalProperty(const SExpression&, const SExpression&, int);
                virtual bool is_simple() const;
                virtual void prepare(CTS&) const; 

                virtual bool has_cost() const;
        };

        class EU: public TemporalProperty
        {
            protected:
                const CostLimit* cl;

            public:
                EU(const SExpression&,const SExpression&, int);
                EU(const SExpression&,const SExpression&, const CostLimit*, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual bool has_cost() const;
        };

        class AG: public TemporalProperty
        {
            public:
                AG(const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class EEU: public TemporalProperty
        {
            protected:
                mutable const PState* init;

                bool concretise(const Job&, const VarSet&, VarSet&, std::list<std::string>&) const;

            public:
                EEU(const SExpression&,const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        class CostEU_EEU: public TemporalProperty
        {
            private:
                const PState* init;

            public:
                CostEU_EEU(const SExpression&,const SExpression&, const PState*, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual bool has_cost() const;
        };

        class LEU: public TemporalProperty
        {
            public:
                LEU(const SExpression&, const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };

        struct LtHPBytes
        {
            static unsigned vsize;
        
            bool operator()(const std::byte* N1, const std::byte* N2) const
            {
                return (romeo::compare(N1, N2, LtHPBytes::vsize) == LESS);
            }
        };

        struct HPNode;
        class HPEU: public TemporalProperty
        {
            private:
                HPNode* compute_distances(const PState* s) const;

            public:
                HPEU(const SExpression&,const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };


        class AU: public TemporalProperty
        {
            protected:
                static void block_path(PResult*, PResult*, PState*);
            public:
                AU(const SExpression&,const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };
        
        class LT: public AU
        {
            public:
                LT(const SExpression&,const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };
        
        class TimedProperty: public TemporalProperty
        {
            protected:
                const TimeInterval& timing;
                mutable Property* real_prop;

            protected:
                const lconstraint::Eq* get_eq(const romeo::Variable&, const value) const; 
                const lconstraint::Leq* get_leq(const romeo::Variable&, const value) const; 
                const instruction::Assignment* get_assign(const romeo::Variable&, const value) const; 
            
            public:
                TimedProperty(const SExpression&,const SExpression&, const TimeInterval&, int); 
                virtual PResult* eval(const PState*) const;

                virtual bool has_time() const;
                virtual bool has_params() const;
                virtual PState* validate_observers(const PState*) const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;

                virtual ~TimedProperty();
        };
    
        class TEU: public TimedProperty
        {
            public:
                TEU(const SExpression&,const SExpression&, const TimeInterval&, int);

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual void prepare(CTS&) const; 
        };
        
        class TAU: public TimedProperty
        {
            public:
                TAU(const SExpression&,const SExpression&, const TimeInterval&, int);
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual std::string to_string() const;
                virtual void prepare(CTS&) const; 
        };
        
        class TLT: public TimedProperty
        {
            public:
                TLT(const SExpression&,const SExpression&, const TimeInterval&, int);

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual void prepare(CTS&) const; 
        };

        class CostEU: public TemporalProperty
        {
            public:
                CostEU(const SExpression&,const SExpression&, int);
                virtual PResult* eval(const PState*) const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

                virtual bool has_cost() const;
        };
    }
}

#endif

