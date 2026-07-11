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

#ifndef ROMEO_GENERIC_EXPRESSION_HH
#define ROMEO_GENERIC_EXPRESSION_HH

#include <set>
#include <map>

#include <valuation.hh>
#include <printable.hh>

#include <variable.hh>

namespace romeo
{
    class GenericExpression;
    typedef std::map<unsigned, const GenericExpression*> ref_dict;
    class CTS;
    class SProgram;
    class LExpression;

// -----------------------------------------------------------------------------

    class GenericExpression: public Printable
    {
        public:
            int decl_line;

        public:
            virtual bool is_const() const;
            virtual bool is_static() const;
            virtual bool has_vars() const;
            virtual bool has_params() const;

            virtual bool is_lvalue() const;
            virtual bool is_rvalue() const;
            virtual bool is_rlvalue() const;
            virtual bool is_lexpression() const;
            virtual bool is_numeric() const;
            virtual bool is_lconstraint() const;
            virtual bool is_control() const;
            virtual bool is_property() const;
            virtual bool is_access() const;
            virtual bool is_refaccess() const;
            virtual bool is_instruction() const;
            virtual bool is_abstracted() const;
            virtual bool is_litteral(cvalue) const;
            virtual bool is_clock_var() const;

            virtual void writes(VarSet&) const;
            virtual void reads(VarSet&) const;

            virtual SProgram codegen() const;

            GenericExpression(int);

            virtual const GenericExpression* copy(CTS&) const = 0;
            virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const = 0;
            virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const = 0;
            virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const = 0;
            virtual const LExpression* abstract_parameters(CTS& t, bool negated, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;

            virtual ~GenericExpression();

    };

    

// -----------------------------------------------------------------------------
}

#endif

