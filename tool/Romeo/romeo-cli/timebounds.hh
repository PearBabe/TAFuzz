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

#ifndef ROMEO_TIMEBOUNDS_HH
#define ROMEO_TIMEBOUNDS_HH

#include <climits>
#include <ostream>
#include <string>

#include <valuation.hh>

#define ROMEO_DBM_STRICT 0
#define ROMEO_DBM_NON_STRICT 1

namespace romeo
{
    // format: INT_MAX is inf and -INT_MAX is -inf 
    // the last bit is 0 iff strict constraint
    // hence the signed value is the all the other bits    

    class time_bound
    {
        private:
            bvalue b;

        public:
            static const time_bound infinity;
            static const time_bound minus_infinity;
            static const time_bound zero;

        public:
            time_bound(); // default is <+inf
            time_bound(const bvalue, const unsigned s=ROMEO_DBM_NON_STRICT); // default strictness is <=
            bool strict() const;
            bool bounded() const;
            bvalue value() const;
            time_bound strictify() const;
            time_bound weakify() const;
            time_bound operator+(const time_bound&) const;
            time_bound operator-(const time_bound&) const;
            time_bound operator+(const cvalue) const;
            time_bound operator-(const cvalue) const;
            time_bound operator-() const;
            time_bound operator*(const cvalue) const;
            time_bound operator/(const cvalue) const;
            bool operator==(const time_bound&) const;
            bool operator!=(const time_bound&) const;
            bool negative() const;
            bool non_positive() const;
            time_bound complement() const;
            std::string to_string() const;

        friend bool operator<(const time_bound&, const time_bound&); 
    };

    bool operator<(const time_bound&, const time_bound&); 
    bool operator>(const time_bound&, const time_bound&); 
    bool operator<=(const time_bound&, const time_bound&); 
    bool operator>=(const time_bound&, const time_bound&); 
    std::ostream& operator<<(std::ostream&, const time_bound&);
    relation_type relation(const time_bound*, const time_bound*, unsigned);
}

#endif

