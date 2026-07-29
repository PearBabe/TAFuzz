#include "timebounds.hh"
#include <sldbm.hh>

using namespace std;
using namespace romeo;

SLDBM::SLDBM(const DBMUnion& D): root(D)
{
  
}
SLDBM::SLDBM(const unsigned n): root(n)
{
  
}

SLDBM::SLDBM(const SLDBM& D): root(D.root), periods(D.periods)
{
  
}

SLDBM& SLDBM::operator=(const SLDBM& D)
{
    root = D.root;
    periods = D.periods;
    return *this;
}

unsigned SLDBM::dimension() const
{
    return root.dimension();
}

void SLDBM::constrain(const unsigned i, const unsigned j, const time_bound c)
{
    for (auto& D: this->root)
    {
        time_bound b(c - D(i, j));
        time_bound m(time_bound::infinity);
        
        auto k = periods.begin();
        while (k != periods.end())
        {
            auto p = *k;
            bool cut_period = false;
            if (p[i] > p[j])
            {
                // i increases faster than j so at some point i - j will cross the <= constraint c
                // and the constraint thus restricts the period
                cut_period = true;
            } 

            // For each k xi - xj increases by p[i] - p[j]
            m = min(m, b / (p[i] - p[j]));

            if (m < time_bound::infinity)
            {
                const cvalue mv = m.value();
                for (unsigned n = 1; n < mv; n++)
                {
                   DBMUnion K(root.scale(p, i));
                   root.add_reduce(K);
                }
            }

            if (cut_period)
            {
                k = periods.erase(k);
            } else {
                k++;
            }
        }
    }

    root.constrain(i, j, c); 
}

void SLDBM::future()
{
    root.future();
}

void SLDBM::past()
{
    root.past();  
}

void SLDBM::reset(const unsigned i)
{
    root.reset(i);

    auto k = periods.begin();
    while (k != periods.end())
    {
        (*k)[i] = 0;

        bool zero = true;
        for (auto x: *k)
        {
            if (x != 0)
            {
                zero = false;
                break;
            }
        }

        if (!zero)
        {
            k = periods.erase(k);
        } else {
            k++;
        }
    }
}

void SLDBM::free_clock(const unsigned i)
{
    root.free_clock(i);

    auto k = periods.begin();
    while (k != periods.end())
    {
        (*k)[i] = 0;

        bool zero = true;
        for (auto x: *k)
        {
            if (x != 0)
            {
                zero = false;
                break;
            }
        }

        if (!zero)
        {
            k = periods.erase(k);
        } else {
            k++;
        }
    }
}

SLDBM SLDBM::remove_dimensions(const std::vector<unsigned>& dims)
{
    DBM* r = root.remove_dimensions(dims);
    SLDBM S(*r);
    delete r;

    for (auto p: periods)
    {
        auto q(p);
        for (auto d: dims)
        {
            q.erase(q.begin() + d);      
        }

        bool zero = true;
        for (auto x: q)
        {
            if (x != 0)
            {
                zero = false;
                break;
            }
        }

        if (!zero)
        {
            S.periods.push_back(q);
        }
    }
    
    return S;
}

void SLDBM::remap(unsigned[], unsigned)
{
  
}

std::string SLDBM::to_string() const
{
  
}
std::string SLDBM::to_string_labels(const std::vector<std::string>& labels) const
{
  
}

relation_type SLDBM::compare(const SLDBM&) const
{
  
}
relation_type SLDBM::relation(const SLDBM&) const
{
  
}

time_bound& SLDBM::operator() (const unsigned, const unsigned) const
{
  
}
bool SLDBM::is_empty() const
{
  
}

SLDBM::~SLDBM()
{
  
}
