#include "avalue.hh"
#include "sexpression.hh"
#include <string>
#include <sstream>
#include <vector>

#include <ppl.hh>
#include <pdbm.hh>
#include <polyhedron.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <time_interval.hh>
#include <color_output.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

// Full real-line
PInterval::PInterval(): left(Avalue::minus_infinity), right(Avalue::infinity)
{
}

// for homogeneity with Polyhedron
PInterval::PInterval(unsigned NP, bool u): left(Avalue::minus_infinity), right(Avalue::infinity)
{
    if (!u) // empty
    {
        left = 1;
        right = 0;
    } 
}

// conversion from Polyhedron
PInterval::PInterval(const Polyhedron& P): left(Avalue::minus_infinity), right(Avalue::infinity) 
{
    assert(P.size() <= 1);

    if (P.empty())
    {
        left = 1;
        right = 0;
    } else {
        const PPL_Convex_Polyhedron& Q = P.to_PPL().begin()->pointset();
        PPL_Constraint_System C = Q.minimized_constraints();
        for (auto c: C)
        {
            auto cp = c.coefficient(PPL_Variable(0)).get_si();
            auto term = c.inhomogeneous_term().get_si();
            if (c.is_equality())
            {
                left = -term;
                right = -term;
            } else {
                bool strict = c.is_strict_inequality();
                char s = strict? 1: 0;
                if (cp > 0)
                {
                    left = std::max(left, Avalue(-term, s, 0, cp));
                } else if (cp < 0) {
                    right = std::min(right, Avalue(term, -s, 0, -cp));
                } // if the coeff is 0 ignore this constraint
            }
        }
    }
}

bool PInterval::contains(const PInterval& I) const
{
    return (I.left >= left) && (I.right <= right);
}


Avalue PInterval::minimize(const LinearExpression& L) const
{
    const auto c = L.coefficient(0);
    const auto v = L.const_term();

    if (v.is_inf() || c == 0)
    {
        return v;
    } else {
        if (c < 0)
        {
            return right * c + v;
        } else {
            return left * c + v;
        } 
    }
}

void PInterval::constrain(const LinearExpression& L, cstr_rel r)
{
    const auto c = L.coefficient(0);
    const auto v = L.const_term();

    if (!v.is_inf())
    {
        bool e = false;
        switch (r) 
        {
            case CSTR_GWEAK:
                if (c > 0)
                {
                    // Warning: we ignore any strictness info from L
                    left = std::max(left, Avalue(-v.value(), 0, 0, c * v.denominator()));
                } else if (c < 0) {
                    right = std::min(right, Avalue(v.value(), 0, 0, -c * v.denominator()));
                } else {
                    e = (v < 0);
                }
                break;
            case CSTR_GSTRICT:
                if (c > 0)
                {
                    left = std::max(left, Avalue(-v.value(), 1, 0, c * v.denominator()));
                } else if (c < 0) {
                    right = std::min(right, Avalue(v.value(), -1, 0, -c * v.denominator()));
                } else {
                    e = (v <= 0);
                }
                break;
            case CSTR_LWEAK:
                if (c > 0)
                {
                    right = std::min(right, Avalue(-v.value(), 0, 0, c * v.denominator()));
                } else if (c < 0) {
                    left = std::max(left, Avalue(v.value(), 0, 0, -c * v.denominator()));
                } else {
                    e = (v > 0);
                }
                break;
            case CSTR_LSTRICT:
                if (c > 0)
                {
                    right = std::min(right, Avalue(-v.value(), -1, 0, c * v.denominator()));
                } else if (c < 0) {
                    left = std::max(left, Avalue(v.value(), 1, 0, -c * v.denominator()));
                } else {
                    e = (v >= 0);
                }
                break;
            case CSTR_EQ:
                if (c > 0)
                {
                    left = std::max(left, Avalue(-v.value(), 0, 0, v.denominator()));
                    right = std::min(right, Avalue(-v.value(), 0, 0, v.denominator()));
                } else if (c < 0) {
                    right = std::min(right, Avalue(v.value(), 0, 0, v.denominator()));
                    left = std::max(left, Avalue(v.value(), 0, 0, v.denominator()));
                } else {
                    e = (v != 0);
                }
                break;
        } 
        if (e)
        {
            left = 1;
            right = 0;
        }
    } else {
        if (((r == CSTR_GWEAK || r ==CSTR_GSTRICT) && c * v == Avalue::minus_infinity)
        || ((r == CSTR_LWEAK || r ==CSTR_LSTRICT) && c * v == Avalue::infinity))
        {
            left = 1;
            right = 0;
        }
    }
}

void PInterval::intersection_assign(const PInterval& I)
{
    left = std::max(left, I.left);
    right = std::min(right, I.right);
}

unsigned PInterval::dimension() const
{
    return 1;
}

bool PInterval::empty() const
{
    return (left > right);
}

void PInterval::integer_shape_assign()
{
    const auto dl = left.denominator();
    const auto vl = left.value();
    const auto sl = left.is_strict();
    if (dl != 1)
    {
        if (vl % dl == 0)
        {
            // no approximation: keep the strictness
            left = Avalue(vl / dl, sl? 1 : 0, 0, 1);
        } else {
            // we take the next integer, which is already bigger than the true value
            // so it does not matter if the value was strict or not
            left = Avalue(vl / dl + 1, 0, 0, 1);
        } 
    }
    
    const auto dr = right.denominator();
    const auto vr = right.value();
    const auto sr = right.is_strict();
    if (dr != 1)
    {
        if (vr % dr == 0)
        {
            // no approximation: keep the strictness
            right = Avalue(vr / dr, sr? -1 : 0, 0, 1);
        } else {
            // we take the previous integer, which is already smaller than the true value
            // so it does not matter if the value was strict or not
            right = Avalue(vr / dr, 0, 0, 1);
        } 
    }
}

string PInterval::to_string_labels(vector<string> labels, unsigned NP) const
{
    assert(!labels.empty());

    stringstream s;
    s << endl << left << " <= " << labels[0] << " <= " << right;

    return s.str();
}

string PInterval::to_string() const
{
    return to_string_labels(vector<string>(1, "A"), 1);
}

// -----------------------------------------------------------------------------

template<class T> PDBMCoeff<T>::PDBMCoeff(): exprs()
{
}

template<class T> PDBMCoeff<T>::PDBMCoeff(const LinearExpression& x): exprs(1, x)
{
}

template<class T> PDBMCoeff<T>::PDBMCoeff(const vector<LinearExpression>& x): exprs(x)
{
}

template<class T> void PDBMCoeff<T>::add_reduce(vector<LinearExpression>& es, const LinearExpression& e)
{
    bool ok = true;
    auto i = es.begin();
    while (i != es.end() && ok)
    {
        if ((*i - e).positive())
        {
            i = es.erase(i);
        } else {
            ok = !(*i - e).non_positive();
            i++;
        }
    }

    if (ok)
    {
        es.push_back(e);
    }
}


template<class T> bool PDBMCoeff<T>::dominates(const LinearExpression& x, const LinearExpression& y, const T& RC)
{
    const LinearExpression L = x - y;

    if (x.const_term().is_strict())
    {
        return (L.positive() || RC.minimize(L) > 0);
    } else {
        return (L.non_negative() || RC.minimize(L) >= 0);
    }
}

template<class T> bool PDBMCoeff<T>::dominates_stricter(const LinearExpression& x, const LinearExpression& y, const T& RC)
{
    const LinearExpression L = x - y;
    return (L.positive() || RC.minimize(L) > 0);
}

template<class T> void PDBMCoeff<T>::add_strong_reduce(vector<LinearExpression>& es, const LinearExpression& e, const T& RC)
{
    bool ok = true;
    auto i = es.begin();
    while (i != es.end() && ok)
    {
        if (dominates(*i, e, RC))
        {
            i = es.erase(i);
        } else {
            ok = !dominates(e, *i, RC);

            i++;
        }
    }

    if (ok)
    {
        if (es.size() > 1)
        {
            T P(RC);
            for (auto& ep: es)
            {
                P.constrain(e - ep, CSTR_LSTRICT);
            }
            
            // Is it possible to have a value x for which e(x) is stricly smaller than the others
            if (!P.empty())
            {
                es.push_back(e);
            }
        } else {
            es.push_back(e);
        }
    }
}

template<class T> void PDBMCoeff<T>::strictify()
{
    for (auto& e: exprs)
    {
        e.strictify();
    }
}

template<class T> PDBMCoeff<T>::PDBMCoeff(const PDBMCoeff<T>& c): exprs(c.exprs)
{
}

template<class T> unsigned PDBMCoeff<T>::size() const 
{
    return exprs.size();
}

template<class T> void PDBMCoeff<T>::integer_hull_assign(T& RC)
{
    //cout << "IH of: ";
    //for (auto e: exprs)
    //{
    //    cout << e << ", ";
    //}
    //cout << endl;

    // TODO: handle strict?
    if (exprs.size() > RC.dimension())
    {
        const unsigned NP = RC.dimension();
        //Polyhedron P(NP + 1, true);
        Polyhedron P(RC);
        P.add_dimensions(1);

        for (auto e: exprs)
        {
            if (!e.const_term().is_inf())
            {
                P.constrain(Var(NP) - e, CSTR_LWEAK);
            }
        }

        exprs.clear();
        P.integer_shape_assign();
        PPL_Convex_Polyhedron Q = P.to_PPL().begin()->pointset();
        PPL_Constraint_System C = Q.minimized_constraints();
        for (auto c: C)
        {
            const cvalue cx = -c.coefficient(PPL_Variable(NP)).get_si();
            LinearExpression L = c.inhomogeneous_term().get_si();
            for (unsigned i = 0; i < NP; i++)
            {
                L = L + c.coefficient(PPL_Variable(i)).get_si() * Var(i);
            }
            if (cx != 0)
            {
                L = L / cx;
                add_strong_reduce(exprs, L, RC);
            } else {
                RC.constrain(L, CSTR_GWEAK);
            }
        }
    }

    //cout << "is: ";
    //for (auto e: exprs)
    //{
    //    cout << e << ", ";
    //}
    //cout << endl;
}

// template<class T> void PDBMCoeff<T>::integer_hull_assign(T& RC)
// {
//     //cout << "IH of: ";
//     //for (auto e: exprs)
//     //{
//     //    cout << e << ", ";
//     //}
//     //cout << endl;

//     // TODO: handle strict?
//     if (exprs.size() > RC.dimension())
//     {
//         const unsigned NP = RC.dimension();
//         Polyhedron P(NP + 1, true);

//         for (auto e: exprs)
//         {
//             if (!e.const_term().is_inf())
//             {
//                 P.constrain(Var(NP) - e, CSTR_LWEAK);
//             }
//         }

//         exprs.clear();
//         P.integer_shape_assign();
//         PPL_Convex_Polyhedron Q = P.to_PPL().begin()->pointset();
//         PPL_Constraint_System C = Q.minimized_constraints();
//         for (auto c: C)
//         {
//             const cvalue cx = -c.coefficient(PPL_Variable(NP)).get_si();
//             LinearExpression L = c.inhomogeneous_term().get_si();
//             for (unsigned i = 0; i < NP; i++)
//             {
//                 L = L + c.coefficient(PPL_Variable(i)).get_si() * Var(i);
//             }
//             add_strong_reduce(exprs, L / cx, RC);
//         }
//     }

//     //cout << "is: ";
//     //for (auto e: exprs)
//     //{
//     //    cout << e << ", ";
//     //}
//     //cout << endl;
// }


template<class T> string PDBMCoeff<T>::to_string_labels(const vector<std::string>& labels) const
{
    stringstream s;
    if (exprs.size() > 1)
    {
        s << " <= min(";
        bool comma = false;
        
        for (auto e: exprs)
        {
            if (comma)
            {
                s << ", ";
            } else {
                comma = true;
            }

            s << e.to_string_labels(labels);
        }
        s << ")";
    } else {
        if (exprs.empty())
        {
            s << " < +inf";
        } else {
            s << " <= " << exprs.back().to_string_labels(labels);
        }
    }

    return s.str();
}

template<class T> PDBMCoeff<T>& PDBMCoeff<T>::operator=(const PDBMCoeff<T>& x)
{
    exprs = x.exprs;

    return *this;
}

template<class T> PDBMCoeff<T> PDBMCoeff<T>::operator+(const PDBMCoeff<T>& x)
{
    vector<LinearExpression> es;
    for (auto e: this->exprs)
    {
        for (auto ex: x.exprs)
        {
            add_reduce(es, e + ex);
        }
    }

    return PDBMCoeff<T>(es);
    
}

template<class T> PDBMCoeff<T> PDBMCoeff<T>::instantiate(const vector<Avalue>& vals) const
{
    PDBMCoeff<T> x;
    for (auto e: exprs)
    {
        x.exprs.push_back(e.instantiate(vals));
    }

    return x;
}

template<class T> PDBMCoeff<T> PDBMCoeff<T>::plus(const PDBMCoeff<T>& x, const PDBMCoeff<T>& y, const T& RC)
{
    vector<LinearExpression> es;
    if (!y.exprs.empty()) // and not x.exprs empty too but this is implicit
    {
        for (auto ex: x.exprs)
        {
            for (auto ey: y.exprs)
            {
                add_strong_reduce(es, ex + ey, RC);
            }
        }
    }

    return PDBMCoeff<T>(es);
}

// -----------------------------------------------------------------------------

template<class T> PDBM<T>::PDBM(const unsigned s, const unsigned NP): size(s), matrix(new PDBMCoeff<T>[size * size]), RC(NP, true)
{
}

template<class T> PDBM<T>::PDBM(const PDBM& d): size(d.size), matrix(new PDBMCoeff<T>[size*size]), RC(d.RC) 
{
    const unsigned tsize = size * size;
    for (unsigned i = 0; i < tsize; i++)
    {
        matrix[i] = d.matrix[i];
    }
}

template<class T> void PDBM<T>::add_pconstraint(const T& F)
{
    RC.intersection_assign(F);
}

template<class T> void PDBM<T>::add_to_exprs(const unsigned i, const unsigned j, const PDBMCoeff<T>& c)
{
    PDBMCoeff<T>& x = matrix[i * size + j];

    for (auto e: c.exprs)
    {
        PDBMCoeff<T>::add_strong_reduce(x.exprs, e, RC);
        //PDBMCoeff<T>::add_reduce(x.exprs, e);
        //x.exprs.push_back(e);
    }
}

template<class T> T PDBM<T>::pconstraint() const
{
    return RC;
}

template<class T> bool PDBM<T>::le_geq(const PDBMCoeff<T>& a, const PDBMCoeff<T>& b, const T& P) const
{
    if (b.exprs.size() == 1)
    {
        for (auto& ea: a.exprs)
        {
            if (!PDBMCoeff<T>::dominates(ea, b.exprs[0], P))
            {
                return false;
            }
        }
    } else {
        for (auto& eb: b.exprs)
        {
            bool dominated = true;
            for (auto& ea: a.exprs)
            {
                if (!PDBMCoeff<T>::dominates(ea, eb, P))
                {
                    dominated = false;
                }
            }
            if (dominated)
            {
                // If eb is dominated by the min of ea's so is the min containing eb, i.e, b
                return true;
            }
        }

        // If none of the terms in the min is dominated, we check by splitting the b min
        unsigned i = 0;
        for (auto& eb: b.exprs)
        {
            // Partition P according to the linear expressions in $b$
            T R(P);
            unsigned j = 0;
            for (auto& ebp: b.exprs)
            {
                if (i != j) // To avoid comparing linear expressions
                {
                    R.constrain(eb - ebp, CSTR_LWEAK);
                }
                j++;
            }

            if (!R.empty()) // otherwise eb can never be smaller than the min of the others
            {
                for (auto& ea: a.exprs)
                {
                    if (!PDBMCoeff<T>::dominates(ea, eb, R))
                    {
                        return false;
                    }
                }
            }
            i++;
        }
    }

    return true;
}

template<class T> bool PDBM<T>::le_eq(const PDBMCoeff<T>& a, const PDBMCoeff<T>& b) const
{
    // TODO
    return true;
}

template<class T> bool PDBM<T>::contains(const PDBM& d) const
{
    bool result = RC.contains(d.RC);

    if (result && !d.RC.empty())
    {
        const unsigned tsize = size * size;
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;
        //cout << to_Polyhedron() << endl;
        //cout << "_________________________________________" << endl;
        //cout << d.to_Polyhedron() << endl;
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;

        unsigned i;
        for (i = 0; i < tsize && le_geq(matrix[i], d.matrix[i], d.RC) ; i++);

        if (i != tsize)
        {
            result = false;
        }
    }

    return result;
}

template<class T> bool PDBM<T>::equals(const PDBM& d) const
{
    bool result = (RC.contains(d.RC) && d.RC.contains(RC));

    if (result)
    {
        unsigned i;
        for (i = 0; i < size*size && le_eq(this->matrix[i], d.matrix[i]); i++);

        if (i != size*size)
            result = false;
    }

    return result;
}

template<class T> PDBMCoeff<T>& PDBM<T>::operator() (const unsigned i, const unsigned j) const
{
    return matrix[i * size + j];
}

template<class T> unsigned PDBM<T>::dimension() const
{
    return size;
}

template<class T> void PDBM<T>::remap(unsigned indices[], unsigned new_size, unsigned NP)
{
    PDBMCoeff<T>* m = new PDBMCoeff<T>[new_size*new_size];
    for (unsigned i=0; i<new_size; i++)
    {
        if (indices[i] == size)
        {
            for (unsigned j=0; j<new_size; j++)
            {
                m[i*new_size+j] = (i==j ? PDBMCoeff<T>(0) : PDBMCoeff<T>());
            }
        } else {
            for (unsigned j=0; j<new_size; j++)
            {
                if (indices[j] != size)
                {
                    m[i*new_size+j] = (*this)(indices[i],indices[j]);
                } else {
                    m[i*new_size+j] = (i==j ? PDBMCoeff<T>(0) : PDBMCoeff<T>());
                }
            }
        }
    }

    delete [] matrix;
    matrix = m;
    size = new_size;
}

template<class T> string PDBM<T>::to_string_labels(const vector<string>& labels, const unsigned NP) const
{
    stringstream domain;
    const PDBM& D = *this;

    bool lineskip = false;
    for (unsigned i=1; i<size; i++)
    {
        if (lineskip)
            domain << endl;
        else
            lineskip = true;


        domain << "-" << labels[i + NP];
        domain << D(0, i).to_string_labels(labels) << endl;
        domain << labels[i + NP];
        domain << D(i, 0).to_string_labels(labels);
    }
    domain << endl;

    for (unsigned i=1; i<size; i++)
    {
        for (unsigned j=1; j<i; j++)
        {
            domain << labels[i + NP] << " - " << labels[j + NP] << D(i, j).to_string_labels(labels) << endl;
            domain << labels[j + NP] << " - " << labels[i + NP] << D(j, i).to_string_labels(labels) << endl;
	    }
    }

    domain << RC.to_string_labels(labels, NP);

    return domain.str();
}

template<> void PDBM<PInterval>::integer_hull_assign()
{
    RC.integer_shape_assign();
    // We can surely optimize the computation of coefficient integer hull 
    // in this case
    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            if (i != j)
            {
                (*this)(i, j).integer_hull_assign(RC);
            }
        }
    }
}

template<> void PDBM<romeo::Polyhedron>::integer_hull_assign()
{
    const unsigned NP = RC.dimension();

    // const Polyhedron PRef(to_Polyhedron());
    // First we compute the integer hull for the projection on parameters
    RC.integer_shape_assign();
    Polyhedron P(RC);

    // Now we create a new polyhedron with the parameters plus one variable
    // per coefficient of the PDBM with two or more linear expressions (an effective min).

    // Find the latter coefficients
    vector<pair<unsigned, unsigned>> pairs;
    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            // if (i != j)
            if (i != j && (*this)(i, j).size() > 1)
            {
                pairs.push_back(pair<unsigned, unsigned>(i, j));
            }
        }
    }

    const unsigned nv = pairs.size();

    // Add the variables
    P.add_dimensions(nv);

    // With their constraints
    for (unsigned i = 0; i < nv; i++)  
    {
        const auto& p = pairs[i];
        for (auto L: (*this)(p.first, p.second).exprs)
        {
            P.constrain(Var(i + NP) - L, CSTR_LWEAK); // TODO: strictness
        }
    }
    
    // Compute the integer hull of that
    P.integer_shape_assign();

    // Now we want to reintroduce the normal variables, so we do a variable change
    P.add_dimensions(size - 1);
    for (unsigned i = 0; i < nv; i++)  
    {
        if (pairs[i].first == 0)
        {
            P.affine_image(Var(i + NP), 0 - Var(NP + nv + pairs[i].second - 1), 1);
        } else if (pairs[i].second == 0) {
            P.affine_image(Var(i + NP), Var(NP + nv + pairs[i].first - 1), 1);
        } else {
            P.affine_image(Var(i + NP), Var(NP + nv + pairs[i].first - 1) - Var(NP + nv + pairs[i].second - 1), 1);
        }
    }
    
    // And a remap to remove the extra variables
    unsigned indices[NP + size - 1];
    for (unsigned i = 0; i < NP; i++)
    {
        indices[i] = i;
    }
    for (unsigned i = NP; i < NP + size - 1; i++)
    {
        indices[i] = i + nv;
    }
    
    P.remap(indices, NP + size - 1);
    
    // now we need to put back the contraints in the DBM... they should be DBM constraints.
    PPL_Convex_Polyhedron Q = P.to_PPL().begin()->pointset();
    PPL_Constraint_System C = Q.minimized_constraints();
    for (auto c: C)
    {
        // const cvalue cx = -c.coefficient(PPL_Variable(NP)).get_si();
        LinearExpression L = c.inhomogeneous_term().get_si();
        for (unsigned k = 0; k < NP; k++)
        {
            L = L + c.coefficient(PPL_Variable(k)).get_si() * Var(k);
        }

        unsigned i = 0;
        unsigned j = 0;
        for (unsigned k = 1; k < size; k++)
        {
            const auto ck = c.coefficient(PPL_Variable(k - 1 + NP)).get_si();
            if (ck == 1)
            {
                i = k;                
            } else if (ck == -1) {
                j = k;
            } else {
                if (ck != 0)
                {
                    cerr << error_tag(color_output) << "Unexpected non-DBM constraint." << ck << endl;
                }
            }
        }
        if (i == 0 && j == 0)
        {
            RC.constrain(L, CSTR_GWEAK);
        } else {
            PDBMCoeff<romeo::Polyhedron>::add_reduce((*this)(i, j).exprs, L);
        }
    }    

    // cout << "-------------------------------" << endl;
    // const Polyhedron IP(to_Polyhedron());
    // Polyhedron refIP(PRef);
    // refIP.integer_shape_assign();
    // if (!(refIP.contains(IP) && IP.contains(refIP)))
    // {
    //     cout << "IH not equal" << endl;
    //     cout << refIP.dimension() << " --- " << IP.dimension() << endl;
    //     cout << refIP.contains(IP) << " === " << IP.contains(refIP) << endl;
    //     cout << P << endl;
    //     cout << "..." << endl;
    //     cout << PRef << endl << "with" << endl;
    //     cout << refIP << endl << " and "<< endl << IP << endl;;
    //     exit(1);
    // } 
        
}

template <class T> void romeo::PDBM<T>::abstract_time()
{
    // supposing here that clock 0 is null
    for (unsigned i=1; i<size; i++)
    {
        this->matrix[i*size] = PDBMCoeff<T>();
        this->matrix[i] = PDBMCoeff<T>(0);
    }
}

template <class T> romeo::Polyhedron PDBM<T>::to_Polyhedron() const
{
    // TODO Strictness
    
    unsigned NP = RC.dimension();
    Polyhedron P(RC);

    P.add_dimensions(size - 1);

    for (unsigned i = 1; i < size; i++)
    {
        // Rectangular constraints
        // Upper bounds
        for (auto e: (*this)(i, 0).exprs)
        {
            if (!e.const_term().is_inf())
            {
                if (!e.const_term().is_strict())
                {
                    P.constrain(Var(i - 1 + NP) - e, CSTR_LWEAK);
                } else {
                    P.constrain(Var(i - 1 + NP) - e, CSTR_LSTRICT);
                }
            }
        }

        // Lower bounds
        for (auto e: (*this)(0, i).exprs)
        {
            if (!e.const_term().is_strict())
            {
                P.constrain(Var(i - 1 + NP) + e, CSTR_GWEAK);
            } else {
                P.constrain(Var(i - 1 + NP) + e, CSTR_GSTRICT);
            }
        }

        // Diagonal constraints
        for (unsigned j = 1; j < size; j++)
        {
            if (i != j)
            {
                for (auto e: (*this)(i, j).exprs)
                {
                    if (!e.const_term().is_inf())
                    {
                        if (!e.const_term().is_strict())
                        {
                            P.constrain(Var(i - 1 + NP) - Var(j - 1 + NP) - e, CSTR_LWEAK);
                        } else {
                            P.constrain(Var(i - 1 + NP) - Var(j - 1 + NP) - e, CSTR_LSTRICT);
                        }
                    }
                }
            }
        }
    }


    return P;
}


// .............................................................................
namespace romeo
{
    template class PDBMCoeff<romeo::Polyhedron>;
    template class PDBM<romeo::Polyhedron>;
    template class PDBMCoeff<romeo::PInterval>;
    template class PDBM<romeo::PInterval>;
}
