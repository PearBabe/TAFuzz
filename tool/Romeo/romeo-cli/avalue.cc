#include <string>
#include <sstream>
#include <numeric>

#include <avalue.hh>

using namespace romeo;
using namespace std;

Avalue Avalue::infinity(0, 0, 1);
Avalue Avalue::minus_infinity(0, 0, -1);

Avalue::Avalue(): val(0), ceps(0), inf(0), d(1)
{
}

Avalue::Avalue(cvalue v): val(v), ceps(0), inf(0), d(1)
{
}

Avalue::Avalue(cvalue v, char e): val(v), ceps(e), inf(0), d(1)
{
}

Avalue::Avalue(cvalue v, char e, char i): val(v), ceps(e), inf(i), d(1)
{
}

Avalue::Avalue(cvalue v, char e, char i, cvalue den): val(v), ceps(e), inf(i), d(den)
{
    if (d < 0)
    {
        d = -d;
        val = -val;
        ceps = -ceps;
        inf = -inf;
    }
    simplify();
}

Avalue::Avalue(const Avalue& v): val(v.val), ceps(v.ceps), inf(v.inf), d(v.d)
{
}

Avalue::Avalue(const time_bound& v): val(v.value()), ceps(v.strict()? -1: 0), inf(0), d(1)
{
    if (v == time_bound::infinity)
    {
        inf = 1;
    } else if (v == time_bound::minus_infinity) {
        inf = -1;
    }
}

time_bound Avalue::tbound() const
{
    if (inf == 1)
    {
        return time_bound::infinity;
    } else if (inf == -1) {
        return time_bound::minus_infinity;
    } else {
        return time_bound(val / d, ((ceps == 0)? ROMEO_DBM_NON_STRICT: ROMEO_DBM_STRICT));
    }
}

cvalue Avalue::value() const
{
    return val;
}

cvalue Avalue::denominator() const
{
    return d;
}

bool Avalue::is_inf() const
{
    return inf > 0;
}

bool Avalue::is_minus_inf() const
{
    return inf < 0;
}

bool Avalue::is_strict() const
{
    return ceps != 0;
}

void Avalue::strictify()
{
    ceps = -1;
}

void Avalue::simplify()
{
    const cvalue g = abs(gcd(val, d));
    if (g != 0)
    {
        val /= g;
        d /= g;
    }
}

Avalue& Avalue::operator=(const Avalue& a)
{
    val = a.val;
    ceps = a.ceps;
    inf = a.inf;
    d = a.d;

    return *this;
}

Avalue Avalue::operator+(const Avalue& a) const
{
    Avalue b(*this);

    if (a.d != d)
    {
        b.val *= a.d;
        b.val += a.val * d;
        b.d = d * a.d;
    } else {
        b.val += a.val;
    }

    b.simplify();
    
    b.ceps += a.ceps;
    b.inf += a.inf;

    if (b.ceps > 1)
    {
        b.ceps = 1;
    }
    
    if (b.ceps < -1)
    {
        b.ceps = -1;
    }

    if (b.inf > 1)
    {
        b.inf = 1;
    }
    
    if (b.inf < -1)
    {
        b.inf = -1;
    }

    return b;
}

Avalue Avalue::operator-(const Avalue& a) const
{
    Avalue b(*this);

    if (a.d != d)
    {
        b.val *= a.d;
        b.val -= a.val * d;
        b.d = d * a.d;

    } else {
        b.val -= a.val;
    }

    b.simplify();
    
    b.ceps -= a.ceps;
    b.inf -= a.inf;

    if (b.ceps > 1)
    {
        b.ceps = 1;
    }
    
    if (b.ceps < -1)
    {
        b.ceps = -1;
    }

    if (b.inf > 1)
    {
        b.inf = 1;
    }
    
    if (b.inf < -1)
    {
        b.inf = -1;
    }

    return b;
}

Avalue Avalue::operator-() const
{
    return (Avalue() - *this);
}

Avalue Avalue::operator*(const cvalue a) const
{
    Avalue b(*this);
    b.val *= a;

    b.simplify();

    if (a < 0)
    {
        b.ceps = -b.ceps;
        b.inf = -b.inf;
    } else if (a == 0) {
        b.inf = 0;
        b.ceps = 0;
    }

    return b;
}

Avalue Avalue::operator/(const cvalue a) const
{
    Avalue b(*this);
    b.d *= abs(a);

    b.simplify();

    if (a < 0)
    {
        b.val = -b.val;
        b.ceps = -b.ceps;
        b.inf = -b.inf;
    }

    return b;
}

bool Avalue::operator==(const Avalue& a) const
{
    return (inf != 0 && inf == a.inf) || (inf == 0 && a.inf == 0 && val == a.val && d == a.d && ceps == a.ceps) ;
}

bool Avalue::operator!=(const Avalue& a) const
{
    return !(*this == a);
}

string Avalue::to_string() const
{
    stringstream s;

    switch (inf)
    {
        case -1:
            s << "-inf";
            break;
        case 1:
            s << "+inf";
            break;
        case 0:
            s << val;
            switch (ceps)
            {
                case -1:
                    s << "-";
                    break;
                case 1:
                    s << "+";
                    break;
            }
            if (d != 1)
            {
                s << "/" << d;
            }

            break;
    }

    return s.str();
}


bool romeo::operator<(const Avalue& a, const Avalue& b)
{
    return (a.inf < b.inf) || (a.inf == 0 && b.inf == 0 && (a.val * b.d < b.val * a.d || (a.val * b.d == b.val * a.d && a.ceps < b.ceps)));
}

bool romeo::operator>(const Avalue& a, const Avalue& b)
{
    return (a.inf > b.inf) || (a.inf == 0 && b.inf == 0 && (a.val * b.d > b.val * a.d  || (a.val * b.d == b.val * a.d && a.ceps > b.ceps)));
}

bool romeo::operator<=(const Avalue& a, const Avalue& b)
{
    return !(a > b);
}

bool romeo::operator>=(const Avalue& a, const Avalue& b)
{
    return !(a < b);
}
