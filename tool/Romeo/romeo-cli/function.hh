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

#ifndef ROMEO_FUNCTION
#define ROMEO_FUNCTION

#include <string>

#include <lexpression.hh>
#include <variable.hh>
#include <lobject.hh>
#include <sexpression.hh>

namespace romeo
{
    class Function;

    namespace expression
    {
        // Leafs
        class FunctionCall : public LExpression
        {
            private:
                const Function& function;
                std::vector<const Expression*> args;
                ref_dict dicorefs;
                SExpression code;
 
            public:
                FunctionCall(const Function&, const std::vector<const Expression*>&, int);
                FunctionCall(const Function&, const std::vector<const Expression*>&, const SExpression&, CTS&, const ref_dict&, int);
                virtual SProgram codegen() const;
 
                virtual bool has_vars() const;
                virtual bool has_params() const;
                
                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
                virtual bool is_instruction() const;
                virtual bool is_numeric() const;

                virtual void writes(VarSet&) const;
                virtual void reads(VarSet&) const;


                virtual ~FunctionCall();
        };
    }

    namespace instruction
    {
        class Block;    
    }

    class Function: public LObject
    {
        private:
            CTS& cts;
            const Type& rtype;
            const std::vector<const Type*>& args;
            SExpression code;
            const unsigned first_fparam_id;
            

        public:
            Function(unsigned, const std::string&, CTS&, const Type&, const std::vector<const Type*>&, const SExpression&, const unsigned);

            unsigned nargs() const;
            virtual std::string to_string() const;

            const Function* copy(CTS& t) const;

            virtual ~Function();

        friend class expression::FunctionCall;
    };


}

#endif

