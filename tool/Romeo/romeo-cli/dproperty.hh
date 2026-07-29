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

#ifndef DPROPERTY_HH
#define DPROPERTY_HH

#include <vector>
#include <string>

#include <property.hh>
#include <sexpression.hh>

namespace romeo
{
    class PResult;
    class GenericExpression;
    class CTS;
    class DResult;
    class Transition;

    class SimpleDProp: public Property
    {
        protected:
            SExpression condition;
            const bool minimum;

        public:
            SimpleDProp(const SimpleDProp&);
            SimpleDProp(const SExpression&, const bool, int);

            virtual std::string to_string() const;
            bool cond_eval(const PState*) const; 

            bool is_min() const;
            virtual bool is_dprop() const;
    };

    class SDPValue: public SimpleDProp
    {
        private:
            SExpression expr;

        public:
            SDPValue(const SDPValue&);
            SDPValue(const SExpression&, const bool, const SExpression&, int);

            virtual PResult* eval(const PState*) const;

            virtual std::string to_string() const;
            virtual const GenericExpression* copy(CTS&) const;
            virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
            virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
            virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

    };

    class SDPClock: public SimpleDProp
    {
        private:
            const Transition* transition;

        public:
            SDPClock(const SDPClock&);
            SDPClock(const SExpression&, const bool, const Transition*, int);

            virtual PResult* eval(const PState*) const;

            virtual std::string to_string() const;
            virtual const GenericExpression* copy(CTS&) const;
            virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
            virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
            virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
            virtual bool is_clock() const;

    };

    /*
    class MultipleDProp: public Property
    {
        private:
            std::vector<const SimpleDProp*> props;

        public:
            virtual PResult* eval(const PState*) const;
            
            virtual std::string to_string() const;
            virtual const GenericExpression* copy(CTS&) const;
    };
    */

    class DProperty: public Property
    {
        private:
            const SimpleDProp& prop;
            const Property* invariant;

        public:
            DProperty(const SimpleDProp&, const Property*);

            virtual PResult* eval(const PState*) const;

            virtual std::string to_string() const;
            virtual const GenericExpression* copy(CTS&) const;
            virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
            virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
            virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;

            bool update(DResult&, const PState*) const;

            virtual bool is_clock() const;
            virtual bool is_dprop() const;
            virtual bool has_cost() const;
    };
}

#endif

