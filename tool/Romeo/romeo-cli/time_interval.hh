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

#ifndef ROMEO_TIME_INTERVAL_HH
#define ROMEO_TIME_INTERVAL_HH

#include <printable.hh>
#include <timebounds.hh>
#include <variable.hh>
#include <sexpression.hh>

namespace romeo
{
    class CTS;

    class TimeInterval: public Printable
    {
        public:
            SExpression lbound;
            SExpression ubound;
            const bool lstrict;
            const bool ustrict;
            const bool unbounded;

        public: 
            bool unconstrained() const;
            TimeInterval(const SExpression& l, 
                       const SExpression& u, 
                       const bool ls, 
                       const bool us, 
                       const bool ub);

            std::string to_string() const;
            const TimeInterval* copy(CTS&) const;
            const TimeInterval* abstract_copy(CTS&, const VarSet&) const;
            const TimeInterval* instantiate(CTS&, const unsigned, const value) const;
            const TimeInterval* eliminate_refs(CTS&, const ref_dict&) const;
            const TimeInterval* abstract_parameters(CTS& t, bool* lbs, bool* ubs, cvalue* lbounds, cvalue* ubounds) const;

            void reads(VarSet&) const;

            time_bound dbm_upper_bound(const_valuation, const_valuation) const;
            time_bound dbm_lower_bound(const_valuation, const_valuation) const;

            ~TimeInterval();
    };
}

#endif

