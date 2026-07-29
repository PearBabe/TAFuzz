#include <avalue.hh>
#include <string>
#include <sstream>

#include <ldbm.hh>
#include <pdbm.hh>
#include <polyhedron.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <time_interval.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

template<class T> LDBM<T>::LDBM(const unsigned s, const unsigned NP): size(s), matrix(new LinearExpression[size * size]), RC(NP, true)
{
}

template<class T> LDBM<T>::LDBM(const LDBM& d): size(d.size), matrix(new LinearExpression[size*size]), RC(d.RC) 
{
    for (unsigned i = 0; i < size * size; i++)
    {
        matrix[i] = d.matrix[i];
    }
}

template<class T> T LDBM<T>::pconstraint() const
{
    return RC;
}

template<class T> void LDBM<T>::add_reduce(vector<LinearExpression>& es, const LinearExpression& e)
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

template<class T> void LDBM<T>::add_strong_reduce(vector<LinearExpression>& es, const LinearExpression& e, const T& RC)
{
    bool ok = true;
    auto i = es.begin();
    while (i != es.end() && ok)
    {
        if ((*i - e).positive() || RC.minimize(*i - e) >= 0)
        {
            i = es.erase(i);
        } else {
            ok = !(*i - e).non_positive() && RC.minimize(e - *i) < 0;
            i++;
        }
    }

    if (ok)
    {
        es.push_back(e);
    }
}


template<class T> void LDBM<T>::add_pconstraint(const T& F)
{
    RC.intersection_assign(F);
}

template<class T> bool LDBM<T>::contains_restricted(const LDBM& d, const T& P) const
{
    Log.start("LDBM::contains");
    T dRC_r(d.RC);
    dRC_r.intersection_assign(P);
    bool result = RC.contains(dRC_r);

    if (result && !dRC_r.empty())
    {
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;
        //cout << to_T() << endl;
        //cout << "_________________________________________" << endl;
        //cout << d.to_T() << endl;
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;

        unsigned i;
        for (i = 0; i < size*size && 
                (matrix[i].const_term().is_inf() 
                 || (!d.matrix[i].const_term().is_inf() && ((matrix[i] - d.matrix[i]).non_negative() || dRC_r.minimize(matrix[i] - d.matrix[i]) >= 0))); i++);

        if (i != size*size)
        {
            result = false;
        }
    }

    Log.stop("LDBM::contains");
    return result;
}

template<class T> bool LDBM<T>::contains(const LDBM& d) const
{
    Log.start("LDBM<T>::contains");
    bool result = RC.contains(d.RC);

    if (result && !d.RC.empty())
    {
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;
        //cout << to_T() << endl;
        //cout << "_________________________________________" << endl;
        //cout << d.to_T() << endl;
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;

        unsigned i;
        for (i = 0; i < size*size && 
                (matrix[i].const_term().is_inf() 
                 || (!d.matrix[i].const_term().is_inf() && ((matrix[i] - d.matrix[i]).non_negative() || d.RC.minimize(matrix[i] - d.matrix[i]) >= 0))); i++);

        if (i != size*size)
        {
            result = false;
        }
    }

    Log.stop("LDBM<T>::contains");
    return result;
}

template<class T> bool LDBM<T>::equals(const LDBM& d) const
{
    bool result = (RC.contains(d.RC) && d.RC.contains(RC));

    if (result)
    {
        unsigned i;
        for (i = 0; i < size*size && this->matrix[i] == d.matrix[i]; i++);

        if (i != size*size)
            result = false;
    }

    return result;
}

template<class T> LinearExpression& LDBM<T>::operator() (const unsigned i, const unsigned j) const
{
    return matrix[i*size+j];
}

template<class T> unsigned LDBM<T>::dimension() const
{
    return size;
}

template<class T> void LDBM<T>::remap(unsigned indices[], unsigned new_size, unsigned NP)
{
    LinearExpression* m = new LinearExpression[new_size*new_size];
    for (unsigned i=0; i<new_size; i++)
    {
        if (indices[i] == size)
        {
            for (unsigned j=0; j<new_size; j++)
            {
                m[i*new_size+j] = (i==j ? 0 : Avalue::infinity);
            }
        } else {
            for (unsigned j=0; j<new_size; j++)
            {
                if (indices[j] != size)
                {
                    m[i*new_size+j] = (*this)(indices[i],indices[j]);
                } else {
                    m[i*new_size+j] = (i==j ? 0 : Avalue::infinity);
                }
            }
        }
    }

    delete [] matrix;
    matrix = m;
    size = new_size;
}

template<class T> string LDBM<T>::to_string_labels(const vector<string>& labels, const unsigned NP) const
{
    stringstream domain;
    const LDBM& D = *this;

    bool lineskip = false;
    for (unsigned i=1; i<size; i++)
    {
        if (lineskip)
            domain << endl;
        else
            lineskip = true;


        domain << "-" << labels[i + NP] << " <= ";
        domain << D(0, i).to_string_labels(labels) << endl;
        domain << labels[i + NP] << " <= " ;
        domain << D(i, 0).to_string_labels(labels);
    }
    domain << endl;

    for (unsigned i=1; i<size; i++)
    {
        for (unsigned j=1; j<i; j++)
        {
            domain << labels[i + NP] << " - " << labels[j + NP] << " <= " << D(i, j).to_string_labels(labels) << endl;
            domain << labels[j + NP] << " - " << labels[i + NP] << " <= " << D(j, i).to_string_labels(labels) << endl;
	    }
    }

    domain << RC.to_string_labels(labels, NP);

    return domain.str();
}

template<class T> void LDBM<T>::integer_hull_assign()
{
    RC.integer_shape_assign();
}

template <class T> void romeo::LDBM<T>::abstract_time()
{
    // supposing here that clock 0 is null
    for (unsigned i=1; i<size; i++)
    {
        this->matrix[i*size] = Avalue::infinity;
        this->matrix[i] = 0;
    }
}
// .............................................................................
namespace romeo
{
    template class LDBM<romeo::Polyhedron>;
    template class LDBM<romeo::PInterval>;
}

