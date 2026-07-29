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

#ifndef ROMEO_SEXPRESSION_HH
#define ROMEO_SEXPRESSION_HH

#include <vector>
#include <string>

#include <printable.hh>
#include <variable.hh>
#include <sword.hh>
#include <generic_expression.hh>

namespace romeo
{

    class CTS;
    class PState;
    class Polyhedron;
    class StackMachine;
    class LinearExpression;

    class SExpression: public Printable
    {
        private:
            const GenericExpression* expr;
            mutable std::vector<word> code;
            mutable bool code_up_to_date;

            static StackMachine M;

        public:
            SExpression();
            SExpression(const GenericExpression*);
            SExpression(const SExpression&);
            SExpression& operator=(const SExpression&);

            const GenericExpression* get_expr() const;
            void add_code(SProgram&) const;

            RValue evaluate(const std::byte[], const std::byte[]) const;
            void execute(std::byte[], const std::byte[]) const;
            RValue eval(const PState*) const;

            Polyhedron constraint(const std::byte[], const std::byte[], unsigned) const;
            LinearExpression linear_expression(const std::byte[], const std::byte[]) const;

            bool is_null() const;
            virtual std::string to_string() const;

            bool is_constant(value) const;
            bool has_params() const;
            bool has_vars() const;
            bool has_cost() const;
            bool is_const() const;
            bool is_static() const;
            bool is_nop() const;
            int get_line() const;

            void prepare(CTS&) const;

            SExpression copy(CTS&) const;
            SExpression abstract_copy(CTS&, const VarSet&) const;
            SExpression instantiate(CTS&, const unsigned, const value) const;
            SExpression eliminate_refs(CTS&, const ref_dict&) const;
            SExpression abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;

            std::list<VarSet> var_reads() const;
            void reads(VarSet&) const;
            void writes(VarSet&) const;

            void clear();
            ~SExpression();

    };
}

#endif

