/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2015)

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
#include <vector>
#include <sstream>
#include <cstdlib>

#include <ppl.hh>
#include <linear_expression.hh>
#include <avalue.hh>
#include <color_output.hh>

using namespace romeo;
using namespace std;

Var::Var(unsigned i)
{
    index = i;
}

string Var::to_string() const
{
    stringstream s;
    s << static_cast<char>('A' + index);

    return s.str();
}

string LinearExpression::to_string() const
{
    stringstream s;
    
    list< pair<unsigned, cvalue> >::const_iterator i;

    bool plus = false;
    if (c != Avalue(0) || coeffs.empty())
    {
        s << c;
        plus = true;
    }

    for (auto i: coeffs)
    {
        auto co = i.second;
        if (plus)
        {
            if (co > 0)
            {
                s << " + ";
            } else {
                // cannot be zero by construction
                s << " - ";
                co = -co;
            }
        } else {
            plus = true;
            if (co < 0)
            {
                s << "-";
                co = -co;
            }
        }
        if (co != 1)
        {
            s << co << "*";
        }

        s << Var(i.first);
    }

    if (denominator != 1) 
    {
        s << " ( /" << denominator << " )";
    }

    return s.str();
}

string Var::to_string_labels(const vector<string>& labels) const
{
    stringstream s;
    s << labels[index];

    return s.str();
}

string LinearExpression::to_string_labels(const vector<string>& labels) const
{
    stringstream s;
    
    list< pair<unsigned, cvalue> >::const_iterator i;
    
    bool plus = false;
    if (c != Avalue(0) || coeffs.empty())
    {
        s << c;
        plus = true;
    }

    for (auto i: coeffs)
    {
        auto co = i.second;
        if (plus)
        {
            if (co > 0)
            {
                s << " + ";
            } else {
                // cannot be zero by construction
                s << " - ";
                co = -co;
            }
        } else {
            plus = true;
            if (co < 0)
            {
                s << "-";
                co = -co;
            }
        }
        if (co != 1)
        {
            s << co << "*";
        }

        s << Var(i.first).to_string_labels(labels);
    }

    if (denominator != 1) 
    {
        s << " ( /" << denominator << " )";
    }

    return s.str();
}


LinearExpression LinearExpression::max_with_cst(const LinearExpression& e)
{
    if (c.value() * e.denominator < e.c.value() * denominator)
        return e;
    else if (c.value() * e.denominator < e.c.value() * denominator)
        return e;
    else
        return *this;

}
namespace romeo
{
    LinearExpression operator* (const Var& x, const cvalue v)
    {
        return LinearExpression(x)*v;
    }
    
    LinearExpression operator* (const cvalue v, const Var& x)
    {
        return v*LinearExpression(x);
    }
    
    LinearExpression operator+ (const Var& x, const cvalue v)
    {
        return LinearExpression(x)+v;
    }
    
    LinearExpression operator+ (const cvalue v, const Var& x)
    {
        return v+LinearExpression(x);
    }
    
    LinearExpression operator- (const Var& x, const cvalue v)
    {
        return LinearExpression(x)-v;
    }
    
    LinearExpression operator- (const cvalue v, const Var& x)
    {
        return v-LinearExpression(x);
    }
    
    LinearExpression operator+ (const Var& v, const Var& x)
    {
        return LinearExpression(v)+LinearExpression(x);
    }
    
    LinearExpression operator- (const Var& v, const Var& x)
    {
        return LinearExpression(v)-LinearExpression(x);
    }
}

// -----------------------------------------------------------------------------
LinearExpression::LinearExpression(): c(0), denominator(1)
{
    // Nothing special: the default constructor of list should have been called automatically
}

LinearExpression::LinearExpression(const Var& v): c(0), denominator(1)
{
    coeffs.push_back(pair<unsigned, cvalue>(v.index, 1));
}

LinearExpression::LinearExpression(const cvalue v): c(v), denominator(1)
{
    // Nothing special: the default constructor of list should have been called automatically
}

LinearExpression::LinearExpression(const LinearExpression& L): coeffs(L.coeffs), c(L.c), denominator(L.denominator)
{
}

LinearExpression::LinearExpression(const Avalue& b): c(b), denominator(1)
{
}

void LinearExpression::add_coeff(const pair<unsigned, cvalue>& x)
{
    if (x.second != 0)
    {
        coeffs.push_back(x);
    }
}

void LinearExpression::simplify()
{
    if (denominator != 1)
    {
        // FIXME : see if this can be factorised with gcd in polyhedron.cc
        // Compute the GCD of all coeffs and denominator

        cvalue min = 1;
        vector<cvalue> A;
        unsigned size = 0;

        A.push_back(abs(denominator));
        size++;

        if (c.value() != 0)
        {
            A.push_back(abs(c.value()));
            size++;
        }

        list< pair<unsigned, cvalue> >::const_iterator k;
        for (k = coeffs.begin(); k != coeffs.end(); k++)
        {
            A.push_back(abs(k->second));
            size++;
        }

        bool not_all_zero = (size > 0);
  
        while (not_all_zero)
        {
            unsigned index = 0;
            
            // OK because not all zero
            while (A[index] == 0)
                index++;
            
            min = A[index];
            for (unsigned i=index; i<size; i++)
            {
                if (A[i] < min && A[i] != 0)
                {
                    min = A[i];
                    index = i;
                }
            }

            not_all_zero = false;
            for (unsigned i=0; i<size; i++)
            {
                if (i!= index)
                {
                    A[i] %= min;
                    not_all_zero |= (A[i] != 0);
                }
            }
        } 
        
        if (min != 1)
        {
            denominator /= min;
            c = c / min;
            list< pair<unsigned, cvalue> >::iterator j;
            for (j = coeffs.begin(); j != coeffs.end(); j++)
                j->second /= min;
        }
    }
}

LinearExpression LinearExpression::operator+ (const LinearExpression& e) const
{
    list< pair<unsigned, cvalue> >::const_iterator i,j;

    LinearExpression L;
    L.c = this->c + e.c;
    if (!L.c.is_inf())
    {
        L.denominator = denominator * e.denominator;

        // Suppose the indices are in increasing order
        i = coeffs.begin();
        j = e.coeffs.begin();
        while (i != coeffs.end() && j != e.coeffs.end())
        {
            if (i->first == j->first)
            {
                const value x = e.denominator*i->second + denominator*j->second;
                L.add_coeff(pair<unsigned, cvalue>(i->first, x));
                i++;
                j++;
            } else {
                if (i->first < j->first)
                {
                    L.add_coeff(*i);
                    i++;
                } else {
                    L.add_coeff(*j);
                    j++;
                }
            }
        }

        // append the rest
        while (i != coeffs.end())
        {
            L.add_coeff(*i);
            i++;
        }

        while (j != e.coeffs.end())
        {
            L.add_coeff(*j);
            j++;
        }

        L.simplify();
    }

    return L;
}

LinearExpression LinearExpression::operator- (const LinearExpression& e) const
{
    list< pair<unsigned, cvalue> >::const_iterator i,j;

    LinearExpression L;
    L.c = this->c - e.c;
    if (!L.c.is_inf())
    {
        L.denominator = denominator * e.denominator;

        // Suppose the indices are in increasing order
        i = coeffs.begin();
        j = e.coeffs.begin();
        while (i != coeffs.end() && j != e.coeffs.end())
        {
            if (i->first == j->first)
            {
                const value x = e.denominator * i->second - denominator * j->second;
                L.add_coeff(pair<unsigned, cvalue>(i->first, x));
                i++;
                j++;
            } else {
                if (i->first < j->first)
                {
                    L.add_coeff(*i);
                    i++;
                } else {
                    L.add_coeff(pair<unsigned, cvalue>(j->first, -j->second));
                    j++;
                }
            }
        }

        // Append the rest
        while (i != coeffs.end())
        {
            L.add_coeff(*i);
            i++;
        }

        while (j != e.coeffs.end())
        {
            L.add_coeff(pair<unsigned, cvalue>(j->first, -j->second));
            j++;
        }

        L.simplify();
    }

    return L;
}

bool LinearExpression::operator== (const LinearExpression& a) const
{
    return c == a.c && denominator == a.denominator && coeffs == a.coeffs;
}

PPL_Linear_Expression LinearExpression::to_PPL() const
{
    PPL_Linear_Expression L(c.value());

    for (auto i: coeffs)
    {
        L += PPL_Variable(i.first)*i.second;
    }

    return L;
}

namespace romeo
{
    LinearExpression operator+ (const Var& v, const LinearExpression& e)
    {
        return LinearExpression(v) + e;
    }
    
    LinearExpression operator+ (const LinearExpression& e, const Var& v)
    {
        return e + LinearExpression(v);
    }
    
    LinearExpression operator- (const Var& v, const LinearExpression& e)
    {
        return LinearExpression(v) - e;
    }
    
    LinearExpression operator- (const LinearExpression& e, const Var& v)
    {
        return e - LinearExpression(v);
    }
    
    LinearExpression operator* (const cvalue v, const LinearExpression& e)
    {
        list< pair<unsigned, cvalue> >::iterator i;
        LinearExpression L; 
    
        if (v != 0)
        {
            L = e;
            L.c = L.c * v;
    
            for (i=L.coeffs.begin(); i != L.coeffs.end(); i++)
                i->second *= v;
        }
        L.simplify();
    
        return L;
    }
    
    LinearExpression operator/ (const LinearExpression& e, const cvalue v)
    {
        list< pair<unsigned, cvalue> >::iterator i;
        LinearExpression L; 
    
        if (v != 0)
        {
            L = e;
            L.denominator *= v;
        } else {
            cerr << error_tag(color_output) << " Division by 0 in linear expression" << endl;
            exit(1);
        }
    
        L.simplify();

        return L;
    }


    LinearExpression operator* (const LinearExpression& e, const cvalue v)
    {
        return v*e;
    }
    
    LinearExpression operator+ (const cvalue v, const LinearExpression& e)
    {
        LinearExpression L(e); 
        L.c = L.c + Avalue(v);
    
        return L;
    }
    
    LinearExpression operator+ (const LinearExpression& e, const cvalue v)
    {
        return v+e;
    }
    
    LinearExpression operator- (const cvalue v, const LinearExpression& e)
    {
        return v + ((-1) * e);
    }
    
    LinearExpression operator- (const LinearExpression& e, const cvalue v)
    {
        return e + (-v);
    }
}

cvalue romeo::LinearExpression::coefficient(const unsigned m) const
{
    list< pair<unsigned, cvalue> >::const_iterator i;
    for (i=coeffs.begin(); i != coeffs.end(); i++)
    {
        if (i->first > m)
            return 0;
        else if (i->first == m)
            return i->second;
    }

    return 0;
}

void romeo::LinearExpression::coefficients(const unsigned size, cvalue C[]) const
{

    for (unsigned k = 0; k < size; k++)
       C[k] = 0;

    list< pair<unsigned, cvalue> >::const_iterator i;
    for (i=coeffs.begin(); i != coeffs.end(); i++)
    {
        if (i->first < size)
            C[i->first] = i->second;
    }
}
            
Avalue romeo::LinearExpression::const_term() const
{
    return c;
}

cvalue romeo::LinearExpression::den() const
{
    return denominator;
}

bool romeo::LinearExpression::non_negative() const
{
    bool res = (c >= 0);

    list< pair<unsigned, cvalue> >::const_iterator i;
    for (i=coeffs.begin(); i != coeffs.end() && res; i++)
        res = (i->second >= 0);
    
    return res;
}

bool romeo::LinearExpression::non_positive() const
{
    bool res = (c <= 0);

    list< pair<unsigned, cvalue> >::const_iterator i;
    for (i=coeffs.begin(); i != coeffs.end() && res; i++)
        res = (i->second <= 0);
    
    return res;
}

bool romeo::LinearExpression::negative() const
{
    bool res = (c <= 0);
    bool strict = (c < 0);

    list< pair<unsigned, cvalue> >::const_iterator i;
    for (auto i=coeffs.begin(); i != coeffs.end() && res; i++)
    {
        res = (i->second <= 0);
        if (i->second < 0)
        {
            strict = true; 
        }
    }
    
    return res && strict;
}

bool romeo::LinearExpression::positive() const
{
    bool res = (c >= 0);
    bool strict = (c > 0);

    list< pair<unsigned, cvalue> >::const_iterator i;
    for (auto i=coeffs.begin(); i != coeffs.end() && res; i++)
    {
        res = (i->second >= 0);
        if (i->second > 0)
        {
            strict = true; 
        }
    }
    
    return res && strict;
}

void romeo::LinearExpression::strictify()
{
    c.strictify();
}

void romeo::LinearExpression::remap(const unsigned size, const unsigned rindices[])
{
    // Remap without disabled transitions
    list< pair<unsigned, cvalue> >::iterator i;
    i=coeffs.begin(); 
    while (i != coeffs.end()) 
    {
        if (rindices[i->first] < size)
        {
            i->first = rindices[i->first];
            i++;
        } else {
            i = coeffs.erase(i);
        }
    }
}

bool romeo::operator< (const LinearExpression& a, const LinearExpression& b)
{
    const unsigned sa = a.coeffs.size();
    const unsigned sb = b.coeffs.size();

    if (sa != sb)
       return sa < sb;
    else
    {
        if (sa == 0)
        {
            if (a.denominator * b.denominator >= 0)
                return b.denominator*a.c.value() < a.denominator*b.c.value(); 
            else
                return b.denominator*a.c.value() > a.denominator*b.c.value(); 
        } else {
            list< pair<unsigned, cvalue> >::const_iterator ia, ib;
            ia = a.coeffs.begin();
            ib = b.coeffs.begin();
            while (ia != a.coeffs.end() && ia->first == ib->first && b.denominator * ia->second == a.denominator * ib->second)
            {
                ia++;
                ib++;
            }
            
            if (ia == a.coeffs.end())
                if (a.denominator * b.denominator >= 0)
                    return a.denominator*b.c.value() > b.denominator*a.c.value();
                else
                    return a.denominator*b.c.value() < b.denominator*a.c.value();
            else
            {
                if (a.denominator * b.denominator >= 0)
                    return ia->first < ib->first || (ia->first == ib->first && b.denominator*ia->second < a.denominator*ib->second);
                else
                    return ia->first < ib->first || (ia->first == ib->first && b.denominator*ia->second > a.denominator*ib->second);
            }
        }
    } 
}

bool ltle::operator() (const LinearExpression& a, const LinearExpression& b) const
{
    return a < b;
}

LinearExpression LinearExpression::instantiate(const vector<Avalue>& vals) const
{
    if (vals.empty())
    {
        return *this;
    } else {
        LinearExpression L;
        L.c = c;
        L. denominator = denominator;
        for (auto p: coeffs)
        {
            if (vals[p.first].is_inf())
            {
                L.coeffs.push_back(p);
            } else {
                L.c = L.c + vals[p.first] * p.second;
            }
        }
        return L;
    }
}
