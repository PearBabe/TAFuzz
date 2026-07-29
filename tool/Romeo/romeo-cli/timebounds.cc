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

#include <iostream>
#include <sstream>
#include <cstdlib>
//#include <bitset>

using namespace std;

#include <timebounds.hh>
#include <color_output.hh>

using namespace romeo;

const time_bound time_bound::time_bound::minus_infinity(ROMEO_MIN_BVALUE >> 1, ROMEO_DBM_STRICT);
const time_bound time_bound::time_bound::infinity(ROMEO_MAX_BVALUE >> 1);
const time_bound time_bound::time_bound::zero(0);

romeo::time_bound::time_bound(): b(ROMEO_MAX_BVALUE >> 1)
{
}

romeo::time_bound::time_bound(const bvalue v, const unsigned s): b(0)
{
    const bextvalue encoded = static_cast<bextvalue>(v) * 2
                            + static_cast<bextvalue>(s);
    if (s > ROMEO_DBM_NON_STRICT
            || encoded < static_cast<bextvalue>(ROMEO_MIN_BVALUE)
            || encoded > static_cast<bextvalue>(ROMEO_MAX_BVALUE))
    {
        cerr << error_tag(color_output) << "overflow in converting int to DBM coefficient: " << v << endl;
        exit(1);
    }

    b = static_cast<bvalue>(encoded);
}

bool romeo::time_bound::strict() const
{
    return !(b & 1);
}

bool romeo::time_bound::bounded() const
{
    return *this != minus_infinity && *this != infinity;
}


time_bound romeo::time_bound::strictify() const
{
    return time_bound(b >> 1, ROMEO_DBM_STRICT);
}

time_bound romeo::time_bound::weakify() const
{
    return time_bound(b >> 1, ROMEO_DBM_NON_STRICT);
}

bvalue romeo::time_bound::value() const
{
    return (b >> 1);
}

time_bound romeo::time_bound::operator+(const time_bound& a) const
{
    // Assume b is never -inf
    if (a == time_bound::infinity || *this == time_bound::infinity)
    {
        return time_bound::infinity;
    } else if (*this == time_bound::minus_infinity || a == time_bound::minus_infinity) {
        return time_bound::minus_infinity;
    } else {
        const bextvalue e = (bextvalue) a.value() + (bextvalue) value();
        if ((e >= 0 && (e >> ROMEO_BVSIZE) != 0) || (e < 0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in adding DBM coefficients: " << *this << " and " << a << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e, (a.b & b) & 1);
    }
}

time_bound romeo::time_bound::operator-(const time_bound& a) const
{
    if (*this == time_bound::infinity || a == time_bound::minus_infinity)
    {
        return time_bound::infinity;
    } else if (*this == time_bound::minus_infinity || a == time_bound::infinity) {
        return time_bound::minus_infinity;
    } else {
        const bextvalue e = (bextvalue) value() - (bextvalue) a.value();
        if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in subtracting DBM coefficients: " << *this << " minus " << a << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e, (a.b & b) & 1);
    }
}

time_bound romeo::time_bound::operator+(const cvalue v) const
{
    // Assume b is never -inf
    if (*this == time_bound::infinity)
    {
        return time_bound::infinity;
    } else if (*this == time_bound::minus_infinity) {
        return time_bound::minus_infinity;
    } else {
        const bextvalue e = (bextvalue) v + (bextvalue) value();
        if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in adding DBM coefficients: " << *this << " and " << v << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e,  b & 1);
    }
}

time_bound romeo::time_bound::operator-(const cvalue v) const
{
    if (*this == time_bound::infinity)
    {
        return time_bound::infinity;
    } else if (*this == time_bound::minus_infinity) {
        return time_bound::minus_infinity;
    } else {
        const bextvalue e = (bextvalue) value() - (bextvalue) v;
        if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in subtracting DBM coefficients: " << *this << " minus " << v << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e, b & 1);
    }
}


time_bound romeo::time_bound::operator-() const
{
    // Assume *this is never inf
    const bextvalue e = (bextvalue) -value();
    if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
    {
        cerr << error_tag(color_output) << "overflow in taking opposite of: " << *this << endl;
        exit(1);
    } else if (*this == time_bound::infinity) {
        return time_bound::minus_infinity;
    } else if (*this == time_bound::minus_infinity) {
        return time_bound::infinity;
    } else {
        return  time_bound((bvalue) e, b & 1);
    }
}


time_bound romeo::time_bound::operator*(const cvalue v) const
{
    // Assume b is never -inf
    if (*this == time_bound::infinity)
    {
        if (v > 0)
            return time_bound::infinity;
        else if (v < 0)
            return time_bound::minus_infinity;
        else
            return time_bound::zero;
    } else if (*this == time_bound::minus_infinity) {
        if (v < 0)
            return time_bound::infinity;
        else if (v > 0)
            return time_bound::minus_infinity;
        else
            return time_bound::zero;
    } else {
        const bextvalue e = (bextvalue) value() * (bextvalue) v;
        if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in multiplying DBM coefficients: " << *this << " and " << v << endl;
            //cout << 1/0 << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e, b & 1);
    }
}

time_bound romeo::time_bound::operator/(const cvalue v) const
{
    // Assume b is never -inf
    if (*this == time_bound::infinity)
    {
        if (v > 0)
            return time_bound::infinity;
        else if (v < 0)
            return time_bound::minus_infinity;
        else {
            cerr << error_tag(color_output) << "division by 0 in DBM coefficients" << endl;
            exit(1);
        }
    } else if (*this == time_bound::minus_infinity) {
        if (v < 0)
            return time_bound::infinity;
        else if (v > 0)
            return time_bound::minus_infinity;
        else {
            cerr << error_tag(color_output) << "division by 0 in DBM coefficients" << endl;
            exit(1);
        }
    } else {
        const bextvalue e = (bextvalue) value() / (bextvalue) v;
        if ((e>=0 && (e >> ROMEO_BVSIZE) != 0) || (e<0 && (e ^ (bextvalue) -1) >> ROMEO_BVSIZE != 0))
        {
            cerr << error_tag(color_output) << "overflow in dividing DBM coefficients: " << *this << " and " << v << endl;
            exit(1);
        } else 
            return  time_bound((bvalue) e, b & 1);
    }
}


bool romeo::time_bound::operator==(const time_bound& a) const
{
    return a.b == b;
}

bool romeo::time_bound::operator!=(const time_bound& a) const
{
    return a.b != b;
}

bool romeo::operator<(const time_bound& a, const time_bound& b)
{
    return a.b < b.b;
}

bool romeo::operator<=(const time_bound& a, const time_bound& b)
{
    return a < b || a == b;
}

bool romeo::operator>(const time_bound& a, const time_bound& b)
{
    return !(a <= b);
}

bool romeo::operator>=(const time_bound& a, const time_bound& b)
{
    return !(a < b);
}

bool romeo::time_bound::negative() const
{
    return (value() < 0 || (b == 0));
}

bool romeo::time_bound::non_positive() const
{
    return (value() <= 0);
}

time_bound romeo::time_bound::complement() const
{
    const bvalue v = value();
    return time_bound(-v, (~(b & 1)) & 1);
}

ostream& romeo::operator<<(ostream& out, const time_bound& a)
{
    if (a == time_bound::infinity)
    {
        out << "<inf";
    } else if (a == time_bound::minus_infinity) {
        out << ">-inf";
    } else {
        out << "<";    
        if (!a.strict())
            out << "=";
        out << a.value();
    }
    return out;
}

relation_type romeo::relation(const time_bound* A, const time_bound* B, unsigned N)
{
    bool equal = true;
    bool mergeable = true;
    bool subseteq = true;
    bool superseteq = true;
    
    for (unsigned i = 0; i < N && (equal || subseteq || superseteq || mergeable); i++)
    {
        for (unsigned j = 0; j < i && (equal || subseteq || superseteq || mergeable); j++)
        {
            const unsigned k = i*N+j;
            const unsigned l = j*N+i;
            const time_bound ak = A[k];
            const time_bound al = A[l];
            const time_bound bk = B[k];
            const time_bound bl = B[l];
            if (ak != bk || al != bl)
            {
                if (!equal)
                    mergeable = false;

                equal = false;
                
                if (ak < bk || al < bl)
                    superseteq = false;

                if (ak > bk || al > bl)
                    subseteq = false;
            } 
        }
    }

    if (equal) {
        return EQUAL;
    } else if (subseteq) {
        return LESS;
    } else if (superseteq) {
        return GREATER;
    } else if (mergeable) {
        return MERGEABLE;
    } else {
        return NONE;
    }
}

string time_bound::to_string() const
{
    stringstream s;
    if (strict())
    {
        s << "<";
    }
    s << value();

    return s.str();
}
