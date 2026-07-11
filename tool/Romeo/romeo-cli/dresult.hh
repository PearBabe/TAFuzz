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

#ifndef DRESULT_HH
#define DRESULT_HH

#include <result.hh>
#include <avalue.hh>
#include <string>

namespace romeo
{
    class DResult: public PResult
    {
        protected:
            bool undefined;
            bool approximate;

        public:
            DResult(const bool, const bool);
            DResult(const DResult&);
            virtual PResult& conjunction(const PResult&);
            virtual PResult& disjunction(const PResult&);
            virtual PResult& negation();
            virtual bool empty() const;
            virtual bool universe() const;
            virtual bool equals(const PResult&);
            virtual bool contains(const PResult&);
            virtual bool intersects(const PResult&);

            bool undef() const;
            bool approx() const;

            virtual bool update(const DResult&, const bool) = 0;
    
    };

    class SimpleDProp;

    class SimpleDResult: public DResult
    {
        protected:
            const SimpleDProp& prop; // The property to optimize

        public:
            SimpleDResult(const SimpleDProp&, const bool, const bool);
            SimpleDResult(const SimpleDResult&);
    };
    
    class VarSDResult: public SimpleDResult
    {
        private:
            value val;       // The optimal value
    
        public:
            VarSDResult(const VarSDResult&);
            VarSDResult(const SimpleDProp&, const value);
            VarSDResult(const SimpleDProp&); // undefined result

            virtual std::string to_string() const;
            virtual bool update(const DResult&, const bool);
            virtual PResult* copy() const;

    };
     
    class ClockSDResult: public SimpleDResult
    {
        protected:
            cvalue val;      // The optimal value
            cvalue den;      // Denominator
            bool strict;     // Is the value a limit
            bool unbounded;  // Is it inf
    
        public:
            ClockSDResult(const ClockSDResult&);
            ClockSDResult(const SimpleDProp&, const cvalue, const cvalue, const bool, const bool);
            ClockSDResult(const SimpleDProp&);

            virtual std::string to_string() const;
            virtual bool update(const DResult&, const bool);
            virtual PResult* copy() const;

    };


    /*
    class MultipleDResult: DResult
    {
        private:
            std::vector<SimpleDResult*> results;
    };
*/
    class CostResult: public DResult
    {
        protected:
            Avalue val;

        public:
            CostResult();
            CostResult(const Avalue&);
            CostResult(const Avalue&, const bool);
            CostResult(const CostResult&);

            Avalue cost() const;

            virtual std::string to_string() const;
            virtual bool update(const DResult&, const bool);
            virtual PResult* copy() const;
    };

    class ParamCostResult: public CostResult
    {
        private:
            Polyhedron D;

        public:
            ParamCostResult(unsigned);
            ParamCostResult(const Avalue&, const Polyhedron&);
            ParamCostResult(const Avalue&, const Polyhedron&, const bool);
            ParamCostResult(const ParamCostResult&);

            Avalue cost() const;

            virtual std::string to_string() const;
            virtual bool update(const DResult&, const bool);
            virtual PResult* copy() const;

            virtual PResult& conjunction(const PResult&);
            virtual PResult& disjunction(const PResult&);
            virtual PResult& negation();
            virtual Polyhedron constraint() const;
    };

}

#endif

