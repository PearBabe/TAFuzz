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

#include <string>
#include <sstream>
#include <iostream>
#include <cstdlib>

#include <checked_types.hh>
#include <color_output.hh>

using namespace romeo;
using namespace std;

uint8_t CheckedInteger::overflow = 0;

CheckedInteger::CheckedInteger(int32_t a, uint8_t f): data(a), defined(f)
{
}

CheckedInteger::CheckedInteger(const CheckedInteger& a): data(a.data), defined(a.defined)
{
}

CheckedInteger& CheckedInteger::operator=(const CheckedInteger& a)
{
    data = a.data;
    defined = a.defined;

    return *this;
}

CheckedInteger CheckedInteger::operator+(const CheckedInteger& a) const
{
    const int64_t s = ((int64_t) data) + ((int64_t) a.data);
    overflow |= s & 0xFFFFFFFF00000000;

    return CheckedInteger((int32_t) s, defined & a.defined);
}

CheckedInteger CheckedInteger::operator-(const CheckedInteger& a) const
{
    const int64_t s = ((int64_t) data) - ((int64_t) a.data);
    overflow |= s & 0xFFFFFFFF00000000;

    return CheckedInteger((int32_t) s, defined & a.defined);
}

CheckedInteger CheckedInteger::operator*(const CheckedInteger& a) const
{
    const int64_t s = ((int64_t) data) * ((int64_t) a.data);
    overflow |= s & 0xFFFFFFFF00000000;

    return CheckedInteger((int32_t) s, defined & a.defined);
}

CheckedInteger CheckedInteger::operator/(const CheckedInteger& a) const
{
    return CheckedInteger(data / a.data, defined & a.defined);
}

CheckedInteger CheckedInteger::operator-() const
{
    return CheckedInteger(-data, defined);
}

CheckedInteger::operator int() const
{
    if (defined)
        return data;
    else
    {
        cerr << error_tag(color_output) << "Cannot cast an undefined value to an integer" << endl;
        exit(1);
    }
}

bool romeo::operator < (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data < b.data; 
}

bool romeo::operator > (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data > b.data; 
}

bool romeo::operator <= (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data <= b.data; 
}

bool romeo::operator >= (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data >= b.data; 
}

bool romeo::operator == (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data == b.data; 
}

bool romeo::operator != (const CheckedInteger& a, const CheckedInteger& b)
{
    return !a.defined || !b.defined || a.data != b.data; 
}

string CheckedInteger::to_string() const
{
    stringstream s;
    if (defined)
        s << data;
    else
        s << "undefined";

    return s.str();
}


ostream& romeo::operator<<(ostream& s, const CheckedInteger& a)
{
    if (a.defined)
        s << a.data;
    else
        s << "undefined";

    return s;
}

