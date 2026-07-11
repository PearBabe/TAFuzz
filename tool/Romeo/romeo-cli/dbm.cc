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

#include "valuation.hh"
#include <set>
#include <vector>
#include <algorithm>
#include <string>
#include <cstring>
#include <sstream>
#include <iostream>
#include <queue>


#include <dbm.hh>
#include <avalue.hh>
#include <linear_expression.hh>

using namespace romeo;
using namespace std;

DBM::DBM(const unsigned s): empty(false)
{
    this->size = s;
    this->matrix = new time_bound[s*s];
    for (unsigned i=0; i<s; i++)
    {
        for (unsigned j=0; j<s; j++)
        {
            matrix[i*s+j] = time_bound::infinity;
        }
        matrix[i*s+i] = time_bound::zero;
    }
}

DBM::DBM(const DBM& A): empty(A.empty)
{
    this->size = A.size;
    this->matrix = new time_bound[size*size];
    memcpy(this->matrix,A.matrix,size*size*sizeof(time_bound));
}

DBM& DBM::operator=(const DBM& A)
{
    if (this != &A)
    {
        time_bound* new_matrix = new time_bound[A.size * A.size];
        memcpy(new_matrix, A.matrix, A.size * A.size * sizeof(time_bound));

        delete [] matrix;
        matrix = new_matrix;
        size = A.size;
        empty = A.empty;
    }

    return *this;
}

unsigned DBM::dimension() const
{
    return size;
}

relation_type romeo::DBM::relation(const DBM& B) const
{
    bool equal = true;
    bool subset = true;
    bool superset = true;

    // MERGE: disabled - set to true to enable
    bool merge_x = false;
    bool merge_y = false;

    bool mset = false;
    unsigned x = 0; 
    unsigned y = 0;
    
    for (unsigned i = 0; i < size && (equal || subset || superset || merge_x || merge_y); i++)
    {
        for (unsigned j = 0; j < size && (equal || subset || superset || merge_x || merge_y); j++)
        {
            const unsigned k = i*size+j;
            const time_bound dij = matrix[k];
            const time_bound bij = B.matrix[k];
            if (dij < bij)
            {
                equal = false;
                superset = false;

                if (mset)
                {
                    if (x != j) 
                        merge_x = false;

                    if (y != i) 
                        merge_y = false;
                } else {
                    x = j;
                    y = i;
                    mset = true;
                }
                
            } else if (dij > bij) {
                equal = false;
                subset = false;

                if (mset)
                {
                    if (x != i) 
                        merge_x = false;

                    if (y != j) 
                        merge_y = false;
                } else {
                    x = i;
                    y = j;
                    mset = true;
                }
            }
        }
    }

    if (equal) {
        return EQUAL;
    } else if (subset) {
        return LESS;
    } else if (superset) {
        return GREATER;
    } else if (merge_x || merge_y) {
        DBM test = *this;
        test.merge(B);
        DBMUnion AB(size);
        AB.add(*this);
        AB.add(B);
        
        if (AB.contains(test))
            return MERGEABLE;
        else
            return NONE;
    } else {
        return NONE;
    }
}

void DBM::intersection_assign(const DBM& A)
{
    if (!empty)
    {
        bool touchs[size];
        for (unsigned i=0; i<size; i++)
            touchs[i] = false;

        for (unsigned i=0; i<size; i++)
        {
            for (unsigned j=0; j<size; j++)
            {
                const time_bound dij = (*this)(i,j);
                const time_bound aij = A(i,j);

                (*this)(i,j) = std::min(dij, aij);
                
                const bool touched = ((*this)(i,j) != dij);
                touchs[i] = touchs[i] || touched;
                touchs[j] = touchs[j] || touched;
            }
        }

        // normalization
        for (unsigned i=0; i<size && !empty; i++)
        {
            if (touchs[i])
            {
                normalize1(i);
            }
        }

    }
}

DBMUnion DBM::complement() const
{
    DBMUnion N(size);
    if (empty)
    {
        N.add(DBM(size));
    } else {
        for (unsigned i = 0; i < size; i++)
        {
            for (unsigned j = 0; j < size; j++)
            {
                if ((i == 0 || j == 0 || (*this)(i,j) < (*this)(i,0) + (*this)(0,j)) && i != j &&  (*this)(i, j) != time_bound::infinity)
                {
                    DBM X(size);
                    X.constrain(j, i, (*this)(i, j).complement());
                    N.add(X);
                }
            }
        }
    }

    return N;
}

void DBM::constrain(const unsigned i, const unsigned j, const time_bound d)
{
    const time_bound dij = this->matrix[i*size+j];
    if (d < dij)
    {
        this->matrix[i*size+j] = d;
        normalize1(i);
        normalize1(j);
    }
} 

void DBM::close()
{
    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            matrix[i*size + j] = matrix[i*size + j].weakify();
        }
    }
}

void DBM::future()
{
    // supposing here that clock 0 is null
    for (unsigned i=1; i<size; i++)
    {
        this->matrix[i*size] = time_bound::infinity;
    }
}

void DBM::past()
{
    // supposing here that clock 0 is null
    for (unsigned i = 1; i < size; i++)
    {
        //this->matrix[i] = time_bound::infinity;
        // Restricting to non-negative values
        this->matrix[i] = time_bound::zero;
        for (unsigned j = 0; j < size; j++)
        {
            if (matrix[j * size + i] < matrix[i])
            {
                matrix[i] = matrix[j * size + i];
            }
        }
    }
}

void DBM::abstract_time()
{
    // supposing here that clock 0 is null
    for (unsigned i=1; i<size; i++)
    {
        this->matrix[i*size] = time_bound::infinity;
        this->matrix[i] = time_bound::zero;
        normalize1(i);
    }
}

void DBM::reset(const unsigned i)
{
    // supposing here that clock 0 is null
    this->matrix[i] = time_bound::zero;
    this->matrix[i*size] = time_bound::zero;
    for (unsigned k=0; k<size; k++)
    {
        this->matrix[i*size+k] = this->matrix[k];
        this->matrix[k*size+i] = this->matrix[k*size];
    }
}

void DBM::free_clock(const unsigned i)
{
    // supposing here that clock 0 is null
    this->matrix[i] = time_bound::zero;
    this->matrix[i*size] = time_bound::infinity;
    for (unsigned k=0; k<size; k++)
    {
        if (k != i)
        {
            this->matrix[i*size+k] = time_bound::infinity;
            this->matrix[k*size+i] = this->matrix[k*size];
        }
    }
}

DBM* DBM::remove_dimensions(const vector<unsigned>& dims)
{
    // existential projection
    // the DBM should be normalized

    const unsigned new_size = size - dims.size();
    if (new_size == size)
        return new DBM(*this);
    
    vector<unsigned>::const_iterator ck, rk = dims.begin();
    unsigned rr = 0; // rows removed
    unsigned cr = 0; // columns removed

    DBM* m = new DBM(new_size);

    for (unsigned i=0; i < size; i++)
    {
        if (rk != dims.end() && i == *rk)
        {
            // if this dim should be removed (row)
            rk++;
            rr++;
        } else {
            cr = 0;
            ck = dims.begin();
            for (unsigned j=0; j < size; j++)
            {
                if (ck != dims.end() && j == *ck)
                {
                    // if this dim should be removed (column)
                    ck++;
                    cr++;
                } else {
                    (*m)(i-rr,j-cr) = (*this)(i,j);
                }
            }
        }
    }

    return m;
}

void DBM::remap(unsigned indices[], unsigned new_size)
{
    time_bound* m = new time_bound[new_size*new_size];
    for (unsigned i=0; i<new_size; i++)
    {
        if (indices[i] == size)
        {
            for (unsigned j=0; j<new_size; j++)
            {
                m[i*new_size+j] = (i==j ? time_bound::zero : time_bound::infinity);
            }
        } else {
            for (unsigned j=0; j<new_size; j++)
            {
                if (indices[j] != size)
                {
                    m[i*new_size+j] = (*this)(indices[i],indices[j]);
                } else {
                    m[i*new_size+j] = (i==j ? time_bound::zero : time_bound::infinity);
                }
            }
        }
    }

    delete [] matrix;
    matrix = m;
    size = new_size;
}


DBM* DBM::slice(const unsigned u, const cvalue v)
{
    DBM r(*this);
    r(u,0) = time_bound(v);
    r(0,u) = time_bound(-v);

    r.normalize1(u);
    r.normalize1(0);

    return r.remove_dimensions(vector<unsigned>(1,1));
}

void DBM::normalize()
{
    unsigned k=0; 
    while (k<size && !empty)
    {
        normalize1(k);
        k++;
    }
}

void DBM::normalize1(const unsigned k)
{
    for (unsigned i=0; i<size && !empty; i++)
    {
        for (unsigned j=0; j<size && !empty; j++)
        {
            const time_bound dij = matrix[i*size+j];
            const time_bound dik = matrix[i*size+k];
            const time_bound dkj = matrix[k*size+j];

            matrix[i*size+j] = std::min(dij, dik + dkj);
            if (i == j && matrix[i*size+j] != time_bound::zero)
            {
                empty = true;
            }
        } 
    }
}

void DBM::inc_size()
{
    time_bound * m = matrix;
    matrix = new time_bound[(size+1)*(size+1)];
    
    for (unsigned i = 0; i < size; i++)
        for (unsigned j = 0; j < size; j++)
            matrix[i*(size+1)+j] = m[i*size+j];

    for (unsigned i = 0; i < size; i++)
    {
        matrix[size*(size+1)+i] = time_bound::infinity;
        matrix[i*(size+1)+size] = time_bound::infinity;
    }
    
    matrix[size*(size+1)+size] = time_bound::zero;
    matrix[size] = time_bound::zero;

    size++;
    delete m;
}

string DBM::to_string() const
{
    // We do not have labels, add some arbitrary ones
    // Warning! Quick hack limited to around 26 variables
    vector<string> labels;
    labels.push_back("0");
    for (unsigned k=0; k<size-1; k++)
    {
        string s = "A";
        s[0] += k;
        labels.push_back(s);
    }

    return to_string_labels(labels);
}

string DBM::to_string_labels(const vector<string>& labels) const
{
    stringstream domain;
    const DBM& D = *this;

    if (empty)
    {
        return "false";
    } else if (size == 1) {
        return "true";
    }


    bool lineskip = false;
    for (unsigned i=1; i<size; i++)
    {
        if (lineskip)
            domain << endl;
        else
            lineskip = true;

        bool equali = (!D(i,0).strict() && !D(0,i).strict() && D(i,0).value() == -D(0,i).value());

        domain << labels[i];
        if (equali)
        {
            domain << " = " << D(i,0).value();
        } else {
            domain << " in ";
            if (D(0,i) == time_bound::infinity)
                domain << "]-inf";
            else {
                if (D(0,i).strict())
                    domain << "]";
                else
                    domain << "[";
                
                domain << -D(0,i).value();
            }

            domain << ", ";
            
            if (D(i,0) == time_bound::infinity)
                domain << "inf[";
            else {
                domain << D(i,0).value();
                if (D(i,0).strict())
                    domain << "[";
                else
                    domain << "]";
            }
        }
    }
    domain << endl;

    for (unsigned i=1; i<size; i++)
    {
        for (unsigned j=1; j<i; j++)
        {
            bool equal = (!D(i,j).strict() && !D(j,i).strict() && D(i,j).value() == -D(j,i).value());
            bool useful_ij = (D(i,j) != time_bound::infinity && D(i,j) != D(i,0) + D(0,j));
            bool useful_ji = (D(j,i) != time_bound::infinity && D(j,i) != D(j,0) + D(0,i));
 
            if (!equal && useful_ji)
            {
	            domain << -D(j,i).value();
                if (D(j,i).strict())
		            domain << " < ";
	            else
		            domain << " <= ";
            }

            if (useful_ij || useful_ji)
            {
	            domain << labels[i] << " - " << labels[j];
                if (equal)
                {
                    domain << " = ";
	                domain << D(i,j).value() << endl;
                }
            }
	        

            if (!equal)
            { 
                if (useful_ij)
                {
                    if (D(i,j).strict())
		                domain << " < ";
	                else    
		                domain << " <= ";
	                domain << D(i,j).value() << endl;
                } else if (useful_ji) {
                    domain << endl;
                }
            } 
        }
    }

    return domain.str();
}

relation_type DBM::compare(const DBM& D) const
{
    return romeo::compare(matrix,D.matrix,size*size*sizeof(time_bound));
}

void DBM::merge(const DBM& D)
{
    for (unsigned i=0; i<size*size; i++)
        matrix[i] = std::max(matrix[i], D.matrix[i]);

}

time_bound& DBM::operator() (const unsigned i, const unsigned j) const
{
    return matrix[i*size+j];
}

bool DBM::is_empty() const
{
    return empty;
    //bool r = false;

    //for (unsigned i = 0; i < size && !r; i++)
    //    r = r || ((*this)(i,i) != time_bound::zero);

    //return r; 
}

bool DBM::contains_origin() const
{
    bool result = true;
    for (unsigned i = 1; i < size && result; i++)
    {
        result = (matrix[i] >= time_bound::zero);
    }
    
    return result;
}

void DBM::max_approx(cvalue M)
{
    const DBM& D = *this;
    const time_bound minusM(-M, ROMEO_DBM_STRICT);
    for (unsigned i=0; i<size; i++)
    {
        for (unsigned j=0; j<size; j++)
        {
            if (D(i,j).value() > M)
                D(i,j) = time_bound::infinity;

            if (D(i,j).value() < -M)
                D(i,j) = minusM;
        }
    }
}

void DBM::kxapprox(const vector<time_bound>& bounds)
{
    const DBM& D = *this;
    for (unsigned i=0; i<size; i++)
    {
        for (unsigned j=0; j<size; j++)
        {
            if (i != j)
            {
                if (bounds[i] != time_bound::infinity && D(i, j) >= -bounds[i])
                {
                    D(i, j) = time_bound::infinity;
                } 
                
                if (bounds[j] != time_bound::infinity && D(i, j) <= bounds[j]) 
                {
                    D(i, j) = bounds[j];
                }
            }
        }
    }
}

Avalue DBM::min(const LinearExpression& L) const
{
    vector<Avalue> vs(size);
    
    return min(L, vs);
}

Avalue DBM::max(const LinearExpression& L) const
{
    vector<Avalue> vs(size);
    
    return Avalue(0) - min(0 - L, vs);
}

Avalue DBM::min(const cvalue coeffs[]) const
{
    vector<Avalue> vals(size);

    return min(coeffs, vals);
}

Avalue DBM::min(const LinearExpression& L, vector<Avalue>& vs) const
{
    // Warning: ignores the denominator!
    //cout << "min of " << L << " on:" << endl;
    //cout << *this << endl;
    cvalue C[size];
    L.coefficients(size, C);
    Avalue b = L.const_term();

    const Avalue r = min(C, vs);
    //cout << "is " << b << " + " << r << endl;
    
    return r + b;
}

Avalue DBM::max(const LinearExpression& L, vector<Avalue>& vs) const
{
    return Avalue(0) - min(0 - L, vs);
}

Avalue DBM::min(const cvalue coeffs[], vector<Avalue>& vs) const
{
    // No coefficient: the result is 0
    bool constant = true;
    for (unsigned k = 0; k < size; k++)
    {
        if (coeffs[k] != 0)
        {
            constant = false;
        }
    }

    if (constant)
    {
        for (unsigned k = 0; k < size; k++)
        {
            vs[k] = -matrix[k];
        }

        return 0;
    }


    vector<Avalue> vals(size);
    //DBM D(*this);
    vector<Avalue> D(size*size);
    for (unsigned i = 0; i < size * size; i++)
    {
        D[i] = matrix[i];
    }

    vector<Avalue> cs(size);

    vector<Avalue> caps(size*size);
    bool valids[size][size];
    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            caps[i*size + j] = Avalue::infinity;
            valids[i][j] = true;
        }
    }
    
    cs[0] = 0;
    for (unsigned k = 1; k < size; k++)
    {
        //char e = 0;
        //if (coeffs[k] < 0 && (*this)(k, 0).strict()) 
        //{
        //    e = -1;
        //} else if (coeffs[k] > 0 && (*this)(0, k).strict()) {
        //    e = 1;
        //}

        //cs[k] = Avalue(-coeffs[k], e);
        cs[k] = -coeffs[k];
        cs[0] = cs[0] - cs[k];
    }

    // Taking advantage of the fact that D(0,j) <= D(i,j) for all i
    // (Otherwise add D(i,0) and obtain D(i,0)<0)
    for (unsigned i = 0; i < size; i++)
    {
        vals[i] = -D[i];
    }

    //cout << "vals: ";
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << vals[i] << " ";
    //}
    //cout << endl;
    //cout << "cs: ";
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << cs[i] << " ";
    //}
    //cout << endl;

    // Test for unboundedness 
    //for (unsigned i = 0; i < size; i++)
    //{
    //    // recall here that we actually compute a max
    //    if (cs[i] > 0 && D(i,0) == time_bound::infinity)
    //    {
    //        vals[i] = D(i,0);
    //        return time_bound::minus_infinity;
    //    }
    //}

    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            D[i * size + j] = D[i * size + j] - vals[i] + vals[j];
        }
    }

    unsigned k = 0;
    unsigned nnp = 0;
    while (nnp < size)
    {
        nnp++;
         
        if (cs[k] > 0)
        {
            nnp = 0;
            vector<Avalue> dist(size);
            int pred[size];

            for (unsigned i = 0; i < size; i++)
            {
                dist[i] = Avalue::infinity;
                pred[i] = -1;
            }

            //cout<< "k: " << k << endl;
            //cout << "DpreBF:" << endl;
            ////cout << D << endl;
            //for (unsigned i = 0; i < size; i++)
            //{
            //    for (unsigned j = 0; j < size; j++)
            //    {
            //        cout << D[i * size + j] << " ";
            //    }
            //    cout << endl;
            //}
            
            // Bellman-Ford
            dist[k] = 0;
            for (unsigned m = 0; m < size-1; m++)
            {
                for (unsigned i = 0; i < size; i++)
                {
                    for (unsigned j = 0; j < size; j++)
                    {
                        if (dist[i] + D[i * size + j] < dist[j])
                        {
                            dist[j] = dist[i] + D[i * size + j];
                            pred[j] = i;
                        }
                    }
                }
            }

            for (unsigned i = 0; i < size; i++)
            {
                // Update potentials
                vals[i] = vals[i] - dist[i];
            }
                
            for (unsigned i = 0; i < size; i++)
            {
                // Compute reduced costs
                for (unsigned j = 0; j < size; j++)
                {
                    // If at some point the cost of a real arc becomes zero
                    // there is no need for a parallel backward arc anymore
                    if (Avalue((*this)(i, j)) == vals[i] - vals[j] && caps[i * size + j] < Avalue::infinity)
                    {
                        D[i * size + j] = 0;
                        caps[i * size + j] = Avalue::infinity;
                    } else {
                        // Normal reduced cost
                        D[i * size + j] = D[i * size + j] - dist[j] + dist[i];
                    }
                }
            }

    //cout << "dist: ";
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << dist[i] << " ";
    //}
    //cout << endl;
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << pred[i] << " ";
    //}
    //cout << endl;
    //cout << "vals: ";
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << vals[i] << " ";
    //}
    //cout << endl;
    //cout << "cs: ";
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << cs[i] << " ";
    //}
    //cout << endl;
    //cout << "reduced D:" << endl;
    //for (unsigned i = 0; i < size; i++)
    //{
    //    for (unsigned j = 0; j < size; j++)
    //    {
    //        cout << D[i * size + j] << " ";
    //    }
    //    cout << endl;
    //}



            for (unsigned i = 0; i < size && cs[k] > 0; i++)
            {
                if (cs[i] < 0)
                {
                    // Find the max flow that can be sent from k to i
                    Avalue mcap = std::min(-cs[i], cs[k]);
                    unsigned j = i;
                    while (pred[j] != -1)
                    {
                        if (!valids[pred[j]][j])
                        {
                            mcap = 0; // This arc has been invalidated by a previous i iteration
                        }

                        mcap = std::min(mcap, caps[pred[j]*size + j]);
                        j = pred[j];
                    }
                    
                    // Should always be true because we remove backward arcs when their cap is 0
                    // Except when put explicitly to 0 in the previous loop
                    if (mcap > 0) 
                    {
                        // Send the flow
                        cs[k] = cs[k] - mcap;
                        cs[i] = cs[i] + mcap;

                        j = i;
                        while (pred[j] != -1)
                        {
                            if (caps[pred[j]*size + j] < Avalue::infinity)
                            {
                                // A backward arc: update it
                                caps[pred[j]*size + j] = caps[pred[j]*size + j] - mcap;

                                // We have cancelled all the flow on this arc
                                // Remove it
                                if (caps[pred[j]*size + j] == 0)
                                {
                                    caps[pred[j]*size + j] = Avalue::infinity;
                                    D[pred[j] * size + j] = Avalue((*this)(pred[j], j)) + vals[j] - vals[pred[j]];
                                    valids[pred[j]][j] = false;
                                }
                            } else {
                                // A forward arc: create or update the backward arc
                                if (caps[j*size + pred[j]] < Avalue::infinity)
                                {
                                    // The backward arc exists: augment its capacity
                                    caps[j*size + pred[j]] = caps[j*size + pred[j]] + mcap;
                                } else {
                                    // It does not exist: create it if the parallel arc is not
                                    // already at cost 0
                                    if (D[j * size + pred[j]] > 0)
                                    {
                                        D[j * size + pred[j]] = 0;
                                        caps[j*size + pred[j]] = mcap;
                                        valids[j][pred[j]] = true;
                                    }
                                }
                            }

                            j = pred[j];
                        }
                    }
                }
            }
        }
        k = (k+1) % size;
    }

    Avalue minval = 0;
    vs[0] = 0;
    for (unsigned k = 1; k < size; k++)
    {
        vs[k] = vals[k] - vals[0];
        cvalue sum = 0;
        if (vs[k] == Avalue::infinity)
        {
            sum += coeffs[k];
        } else {
            minval = minval + vs[k] * coeffs[k];
        }

        if (sum < 0)
        {
            minval = Avalue::minus_infinity;
        }
    }

    return minval;
}

struct pqnode
{
    vector<int> vars;
    cvalue sum;
    vector<int> missing;

    pqnode(const vector<int>& v, const cvalue s, const vector<int>& m): vars(v), sum(s), missing(m) {}

    bool operator<(const pqnode& x) const
    {
        return ((vars.size() > x.vars.size()) || (vars.size() == x.vars.size() && sum < x.sum));
    }
};

Avalue DBM::min2(const cvalue coeffs[], vector<Avalue>& vs) const
{
    // Check for unboundedness
    for (unsigned i = 0; i < size; i++)
    {
        if (matrix[i * size] == time_bound::infinity)
        {
            cvalue sum = 0;
            for (unsigned j = 0; j < size; j++)
            {
                if (matrix[i * size + j] < time_bound::infinity) // includes i
                {
                    sum += coeffs[j];
                }
            }

            if (sum < 0)
            {
                return Avalue::minus_infinity;
            }
        }
    }

    vector<Avalue> D(size*size);
    for (unsigned i = 0; i < size * size; i++)
    {
        D[i] = matrix[i];
    }

    vector<int> pc;

    // Initial value
    vs[0] = 0;
    for (unsigned i = 1; i < size; i++)
    {
        if (coeffs[i] <= 0)
        {
            const auto di0 = D[i * size];
            if (di0 < Avalue::infinity)
            {
                vs[i] = di0; // biggest possible value
            } else {
                vs[i] = -D[i];
                for (unsigned j = 1; j < size; j++)
                {
                    if (coeffs[j] > 0 && D[i * size + j] < Avalue::infinity)
                    {
                        vs[i] = std::max(vs[i], -D[j] + D[i * size + j]);
                    }
                }
            }
        } else {
            pc.push_back(i);

            vs[i] = -D[i]; // smallest possible value
            // but we must satisfy the constraints wrt. those set to max
            // by using max_j(vs[j] - D(j, i)) <= vs[i]
            for (unsigned j = 1; j < size; j++)
            {
                if (coeffs[j] <= 0 && D[j * size + i] < Avalue::infinity)
                {
                    vs[i] = std::max(vs[i], vs[j] - D[j * size + i]);
                }
            }
        }
    }
    Avalue minval = 0;
    for (unsigned k = 1; k < size; k++)
    {
        minval = minval + vs[k] * coeffs[k];
    }
    //cout << "initially: " << minval<< endl;
    //for (unsigned i = 0; i < size; i++)
    //{
    //    cout << vs[i] << " ";
    //}
    //cout << endl;

    bool finished  = false;
    while (!finished)
    {
        // Find an improvement by decreasing the value for a positive coefficient
        finished = true;
        vector<vector<int>> imps(size);
        auto cmp = [](const pqnode& left, const pqnode& right) { return (left < right); }; 
        priority_queue<pqnode, vector<pqnode>, decltype(cmp)> w(cmp);

        for (auto i: pc)
        {
            if (vs[i] > -D[i])
            {
                vector<int> s;
                Avalue gap = vs[i] + D[i]; // note that this corresponds to j = 0
                cvalue sum = 0;
                for (unsigned j = 1; j < size; j++)
                {
                    // vs[i] > -D(0, i) and vs[i] == vs[j] - D(j, i)
                    // implies
                    // vs[j] > -D(0, i) + D(j, i) but not vs[j] > -D(0, j) then?
                    if (vs[i] == vs[j] - D[j * size + i])
                    {
                        // note that this case includes j == i
                        // decreasing vs[i] implies decreasing vs[j]
                        // vs[i] == vs[j] - D(j, i)
                        //
                        // if also:
                        // vs[j] == vs[k] - D(k, j)
                        // vs[i] == vs[k] - (D(k, j) + D(j, i))
                        // vs[i] <= vs[k] - D(k, i)
                        // and since we always have
                        // vs[i] >= vs[k] - D(k, i)
                        // then:
                        // vs[i] == vs[k] - D(k, i)
                        //
                        // similarly, if (i and k blocked on j):
                        // vs[i] == vs[j] - D(j, i)
                        // vs[k] == vs[j] - D(j, k)
                        // vs[i] == vs[k] + D(j, k) - D(j, i)
                        // and then?
                        //
                        // something  else:
                        // i blocked on j and k
                        // l blocked on j 
                        // vs[i] == vs[j] - D(j, i)
                        // vs[i] == vs[k] - D(k, i)
                        // vs[l] == vs[j] - D(j, l)
                        // then:
                        // vs[l] == vs[i] + D(j, i) - D(j, l)
                        // vs[l] == vs[k] - (D(k, j) + D(j, l)) + D(j, i)
                        // vs[k] - D(k, l) <= vs[l] <= vs[k] - D(k, l) + D(j, i)
                        // so l may or may not be blocked on k
                        //
                        //cout << i << " ++ " << j << endl;
                        gap = std::min(gap, vs[j] + D[j]);
                        sum = sum + coeffs[j];
                        s.push_back(j);
                    } 
                }

                if (gap > 0)
                {
                    imps[i] = s;
                    vector<int> rd1, rd;
                    set_difference(pc.begin(), pc.end(), s.begin(), s.end(), inserter(rd1, rd1.begin()));
                    for (auto x: rd1)
                    {
                        if (x < i && !imps[x].empty())
                        {
                            rd.push_back(x);
                        }
                    }

                    cvalue sumd = 0;
                    for (auto x: rd)
                    {
                        sumd = sumd + coeffs[x];
                    }
                    
                    if (sum + sumd > 0)
                    {
                        w.push(pqnode(s, sum, rd));
                    }
                }
            }
        }
        //cout << "imps = [ ";
        //for (auto x: imps)
        //{
        //    if (!x.empty())
        //    {
        //        cout << "[ ";
        //        for (auto y: x)
        //        {
        //            cout << y << " ";
        //        }
        //        cout << "] ";
        //    }
        //}
        //cout << "]" << endl;

        cvalue sum = 0;
        vector<int> vars;

        bool found = false;
        while (!found && !w.empty())
        {
            auto x = w.top();
            w.pop();
            
            //cout << "   [ ";
            //for (auto z: x.vars)
            //{
            //    cout << z << " ";
            //}
            //cout << "] -- [ ";
            //for (auto z: x.missing)
            //{
            //    cout << z << " ";
            //}
            //cout << "] " << x.last << "  ++  "  << x.sum << endl ;

            if (x.sum > 0)
            {
                found = true;
                vars = x.vars;
                sum = x.sum;
            } else {
                for (auto i: x.missing)
                {
                    const auto& s = imps[i];
                    //vector<int> ri;
                    //set_intersection(x.vars.begin(), x.vars.end(), s.begin(), s.end(), inserter(ri, ri.begin()));
                    //if (!ri.empty())
                    //if (!s.empty())
                    {
                        vector<int> ru;
                        set_union(x.vars.begin(), x.vars.end(), s.begin(), s.end(), inserter(ru, ru.begin()));
                        cvalue sum2 = 0;
                        for (auto z: ru)
                        {
                            sum2 = sum2 + coeffs[z];
                        }

                        vector<int> rd;
                        set_difference(x.missing.begin(), x.missing.end(), s.begin(), s.end(), inserter(rd, rd.begin()));
                        while (!rd.empty() && rd.back() > i)
                        {
                            rd.pop_back();
                        }

                        cvalue sumd = 0;
                        for (auto x: rd)
                        {
                            sumd = sumd + coeffs[x];
                        }
                        //cout << "consider [ ";
                        //for (auto x: ru)
                        //{
                        //    cout << x << " ";
                        //}
                        //cout << "] sum: " << sum2 << " sumd " << sumd << endl;

                        if (sum2 + sumd > 0)
                        {
                            w.push(pqnode(ru, sum2, rd));
                        }
                    }
                }
            }
        }
                        
        //cout << "vars = [ ";
        //for (auto x: vars)
        //{
        //    cout << x << " ";
        //}
        //cout << "]" << endl;

        if (sum > 0)
        {
            // An actual improvement
            finished = false;

            Avalue g = Avalue::infinity;
            vector<int> not_vars, nv;

            for (unsigned i = 0; i < size; i++)
            {
                nv.push_back(i);
            }
            set_difference(nv.begin(), nv.end(), vars.begin(), vars.end(), inserter(not_vars, not_vars.begin()));

            
            for (auto x: vars)
            {
                for (auto y: not_vars)
                {
                    g = std::min(g, vs[x] - (vs[y] - D[y * size + x]));
                    if (g == Avalue(0))
                    {
                        cout << "Error: zero gap: " << x  << " " << y << endl;
                        cout << vs[x] << " " << vs[y] << endl;
                        exit(1);
                    }
                }
            }

            //cout << "g: " << g << endl;

            for (auto y: vars)
            {
                vs[y] = vs[y] - g;
            }

            minval = 0;
            for (unsigned k = 1; k < size; k++)
            {
                minval = minval + vs[k] * coeffs[k];
            }
            //cout << "new value: " << minval<< endl;
            //for (unsigned i = 0; i < size; i++)
            //{
            //    cout << vs[i] << " ";
            //}
            //cout << endl;
        }
    }

    minval = 0;
    for (unsigned k = 1; k < size; k++)
    {
        minval = minval + vs[k] * coeffs[k];
    }

        //cout << "sum: " << sum << " gap: " << gap << endl;
    
    
    //}



    return minval;
}

//bool DBM::nspivot(vector<cvalue> coeffs, DBM& RC, vector<cvalue>& F, vector<int>& pred, vector<unsigned>& depth, vector<time_bound>& vals)
//{
//    time_bound minc = time_bound::infinity;
//
//    for (unsigned i = 0; i < size; i++)
//    {
//        for (unsigned j = 0; j < size; j++)
//        {
//            minc = std::min(minc, D(i,j));
//        }
//    }
//
//    if (minc < time_bound::zero)
//    {
//        // i -> j needs to be part of the spanning tree 
//
//        unsigned x = i;
//        unsigned y = j;
//
//        // Find the cycle _reverse_ arc with minium flow (p -> q)
//        unsigned p;
//        unsigned q;
//        unsigned minf = UINT_MAX; 
//        while (x != y)
//        {
//            if (depth[x] > depth[y])
//            {
//                const unsigned fx = F[pred[x] * size + x];
//                if (fx > 0 && fx < minf)
//                {
//                    q = x;
//                    p = pred[x];
//                    minf = fx;
//                }
//                x = pred[x];
//            } else if (depth[x] < depth[y]) {
//                const unsigned fy = F[y * size + pred[y]];
//                if (fy > 0 && fy < minf)
//                {
//                    p = y;
//                    q = pred[y];
//                    minf = fy;
//                }
//                y = pred[y];
//            } else {
//                const unsigned fx = F[pred[x] * size + x];
//                if (fx > 0 && fx < minf)
//                {
//                    q = x;
//                    p = pred[x];
//                    minf = fx;
//                }
//                x = pred[x];
//
//                const unsigned fy = F[y * size + pred[y]];
//                if (fy > 0 && fy < minf)
//                {
//                    p = y;
//                    q = pred[y];
//                    minf = fy;
//                }
//                y = pred[y];
//            }
//        }
//
//
//
//        pred[j] = i;
//    } else {
//        return false;
//    }
//
//}
//
//Avalue DBM::min2(const cvalue coeffs[], vector<time_bound>& vs) const
//{
//    // No coefficient: the result is 0
//    bool constant = true;
//    for (unsigned k = 0; k < size; k++)
//    {
//        if (coeffs[k] != 0)
//        {
//            constant = false;
//        }
//    }
//
//    if (constant)
//    {
//        for (unsigned k = 0; k < size; k++)
//        {
//            vs[k] = matrix[k];
//        }
//
//        return time_bound::zero;
//    }
//
//
//    vector<Avalue> vals(size);
//    DBM D(*this); // reduced costs
//    cvalue F[size*size](); // Flows
//    int pred[size]; // tree predecessor
//    unsigned depth[size]; // tree depth
//
//    cvalue cs[size]; // Objective function coeffs;
//    cs[0] = 0;
//    for (unsigned k = 1; k < size; k++)
//    {
//        cs[k] = -coeffs[k];
//        cs[0] += coeffs[k];
//    }
//
//    for (unsigned k = 0; k < size; k++)
//    {
//        pred[k] = -1;
//    }
//
//    // Initial tree
//    for (unsigned i = 0; i < size; j++)
//    {
//        unsigned j = 0;
//        if (-coeffs[i] > 0)
//        {
//            while (j < size && cs[i] > 0)
//            {
//                if (cs[j] < 0)
//                {
//                    // send flow from i to j
//                    vals[i] = D(i, j);
//                    const unsigned f = std::min(cs[i], -cs[j]);
//                    cs[i] -= f;
//                    cs[j] += f;
//                    F[i*size + j] = f;
//                    pred[j] = i;
//                }
//                j++;
//            }
//        } else if (-coeffs[i] < 0) {
//            vals[i] = time_bound::zero;
//        } else { // == 0
//            // arbitrarily send to 0
//            vals[i] = D(i, 0);
//        }
//    }
//
//
//
//
//    
//    Avalue minval = 0;
//    vs[0] = time_bound::zero;
//    for (unsigned k = 1; k < size; k++)
//    {
//        vs[k] = (vals[k] - vals[0]).tbound();
//        minval = minval + vals[k] * coeffs[k];
//    }
//
//    return minval;
//}


void DBM::relax_assign(unsigned i)
{
    for (unsigned k = 0; k < size; k++)
    {
        if (k != i)
        {
            (*this)(k, i) = time_bound::infinity;
            (*this)(i, k) = time_bound::infinity;
        }
    }
}

SizeDigest DBM::eval_size() const
{
    SizeDigest dig;

    dig.val = 0;
    dig.ninf = 0;
    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            const time_bound dij = matrix[i * size +j];
            if ( dij == time_bound::infinity)
            {
                dig.ninf++;
            } else {
                dig.val = dig.val + dij;
            }
        }
    }

    return dig;
}

DBM DBM::scale(vector<cvalue> p, unsigned n)
{
    DBM R(*this);

    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            R(i, j) = R(i, j) + (p[i] - p[j]) * n;
        }
    }
    
    return R;
}

DBM::~DBM()
{
    delete [] matrix;
}

bool DBM::operator<(const DBM& D) const
{
    return (this->relation(D) == LESS);
}

void DBM::copy_matrix(void* dst)
{
    memcpy(dst, matrix, size * size * sizeof(time_bound));
}

// -----------------------------------------------------------------------------
// DBMUnion
// -----------------------------------------------------------------------------

DBMUnion::DBMUnion(const unsigned s): dim(s)
{
}

DBMUnion::DBMUnion(const DBM& B): dim(B.dimension())
{
    disjuncts.push_back(new DBM(B));
}

DBMUnion::DBMUnion(const DBMUnion& A): dim(A.dim)
{
    list<DBM*>::const_iterator k;
    
    for (k=A.disjuncts.begin(); k!= A.disjuncts.end(); k++)
        this->disjuncts.push_back(new DBM(**k));
}

//DBMUnion DBMUnion::uprojection2(const unsigned u, const time_bound m, const time_bound M) const
//{
//    DBMUnion result(dim); //empty
//    list<DBM*>::const_iterator i;
//    set<unsigned> instants;
//    set<unsigned>::iterator k;
//
//    const unsigned vm = -m.value();
//    const unsigned vM = M.value();
//
//    bool okm = false;
//    bool okM = false;
//    for (i=disjuncts.begin(); i!=disjuncts.end(); i++)
//    {
//        const unsigned um = -(**i)(0,u).value();
//        const unsigned uM = (**i)(u,0).value();
//
//        if (um <= vm)
//            okm = true;
//        else
//            instants.insert(um);
//
//        if (uM >= vM)
//            okM = true;
//        else
//            instants.insert(uM);
//    }
//
//    if (okm && okM)
//    {
//        instants.insert(vm);
//        instants.insert(vM);
//
//        vector<DBMUnion> waiting(instants.size(),DBMUnion(dim));
//
//        for (k=instants.begin(); k != instants.end(); k++)
//        {
//            for (i=disjuncts.begin(); i != disjuncts.end(); i++)
//                waiting[*k].add_reduce(*(*i)->slice(u,*k));
//        }
//        
//        vector<DBMUnion>::iterator j;
//        for (j=waiting.begin(); j != waiting.end(); j++)
//            result.intersection_assign(*j);
//
//    } 
//
//    return result;
//}

DBMUnion DBMUnion::eprojection(const vector<unsigned>& dims) const
{
    DBMUnion r(dim - dims.size());

    list<DBM*>::const_iterator i;
    for (i=disjuncts.begin(); i!= disjuncts.end(); i++)
        r.add_reduce(*(*i)->remove_dimensions(dims));

    return r;
}

DBMUnion DBMUnion::uprojection(const vector<unsigned>& dims, const DBMUnion& C) const
{
    DBMUnion D = this->complement();
    D.intersection_assign(C);
    DBMUnion R = D.eprojection(dims).complement();

    R.intersection_assign(C.eprojection(dims));

    return R;
}

//DBMUnion DBMUnion::uprojection(const vector<unsigned>& dims, const DBM& D) const
//{
//    if (dims.empty() || this->empty())
//    {
//        return *this;
//    }
//    
//
//    vector<unsigned>::const_iterator k;
//    
//    if (dims.size() + 1 == dim) 
//    {
//        bool is_inf = true;
//        for (k = dims.begin(); k != dims.end() && is_inf; k++)
//        {
//            if (D(*k, 0) < time_bound::infinity)
//            {
//                is_inf = false;
//            }
//        }
//
//        if (is_inf)
//        {
//            return DBMUnion(dim - dims.size());
//        }
//    }
//
//
//    DBM l(D);
//    // on suppose que dims est trié
//    k = dims.begin();
//    for (unsigned i = 1; i < dim; i++) 
//    {
//        if (k == dims.end() || *k != i)
//        {
//            l.relax_assign(i);
//        } else {
//            k++;
//        }
//    }
//
//    DBMUnion c = this->complement();
//    c.intersection_assign(DBMUnion(l));
//    DBMUnion cp = c.eprojection(dims);
//    DBMUnion r = cp.complement();
//
//    return r;
//}


DBMUnion DBMUnion::complement() const
{
    DBMUnion r(dim);

    r.add(DBM(dim));

    list<DBM*>::const_iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        DBMUnion c = (*i)->complement();
        r.intersection_assign(c);
    }

    return r;
}

void DBMUnion::add(const DBM& B)
{
    dim = B.dimension();

    disjuncts.push_back(new DBM(B));
}

bool DBMUnion::add_reduce(const DBM& B)
{
    dim = B.dimension();
    bool res = true;

    if (B.is_empty())
    {
        return false;
    }

    list<DBM*> waiting;

    waiting.push_back(new DBM(B));
    while (!waiting.empty())
    {
        DBM* current = waiting.front();
        waiting.pop_front();

        list<DBM*>::iterator it = disjuncts.begin();
        bool added = false;
        bool stop = false;
        while (it!=disjuncts.end() && !stop)
        {
            relation_type r = current->relation(**it);
            if (r == GREATER)
            {
                delete *it;
                it = disjuncts.erase(it);
            } else if (r == MERGEABLE) {
                (*it)->merge(*current);

                added = true;
                waiting.push_back(*it);
                it = disjuncts.erase(it);
            } else if (r == EQUAL || r == LESS) {
                res = false;
                added = true;
                stop = true;
            } else {
                it++;
            }
        }
        if (!added)
        {
            disjuncts.push_back(current);
        }
    }

    return res;
}

unsigned DBMUnion::size() const
{
    return disjuncts.size();
}

void DBMUnion::clear()
{
    list<DBM*>::const_iterator i;

    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        delete *i;
    }
    disjuncts.clear();
}

void DBMUnion::add_reduce(const DBMUnion& A)
{
    list<DBM*>::const_iterator i;

    for (i = A.disjuncts.begin(); i != A.disjuncts.end(); i++)
        add_reduce(**i);
}

void DBMUnion::reduce_assign()
{
    const unsigned size = disjuncts.size();

    for (unsigned i=0; i<size; i++)
    {
        DBM* D = disjuncts.front();
        disjuncts.pop_front();
        this->add_reduce(*D);
        delete D;
    }
}

void DBMUnion::intersection_assign(const DBMUnion& A)
{
    list<DBM*>::const_iterator i;
    list<DBM*>::iterator j;

    DBMUnion r(dim);

    for (j = disjuncts.begin(); j != disjuncts.end(); j++)
    {
        for (i = A.disjuncts.begin(); i != A.disjuncts.end(); i++)
        {
            DBM copy(**j);
            copy.intersection_assign(**i);
            r.add_reduce(copy);
        }
    }

    clear();
    disjuncts.swap(r.disjuncts);
}

void DBMUnion::future()
{
    list<DBM*>::iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        (*i)->future();
    }
}

void DBMUnion::past()
{
    list<DBM*>::iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        (*i)->past();
    }
}

void DBMUnion::reset(const unsigned k)
{
    list<DBM*>::iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        (*i)->reset(k);
    }
}

void DBMUnion::abstract_time()
{
    list<DBM*>::iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        (*i)->abstract_time();
    }
}

void DBMUnion::constrain(const unsigned i, const unsigned j, const time_bound c)
{
    auto k = disjuncts.begin();
    while (k != disjuncts.end())
    {
        (*k)->constrain(i,j,c);
        if ((*k)->is_empty())
        {
            k = disjuncts.erase(k);
        } else {
            k++;
        }
    }
}

bool DBMUnion::empty() const
{
    return disjuncts.empty();
}

void DBMUnion::remap(unsigned indices[], unsigned size)
{
    dim = size;
    list<DBM*>::iterator i;
    for (i = disjuncts.begin(); i != disjuncts.end(); i++)
    {
        (*i)->remap(indices,size);
    }
}


bool DBMUnion::contains(const DBM& A) const
{
    list<DBM*> waiting;

    DBMUnion R(A);

    for (auto k: disjuncts)
    {
        R.intersection_assign(k->complement());
        if (R.empty())
        {
            break;
        }
    }

    return R.empty();
}

bool DBMUnion::contains(const DBMUnion& A) const
{
    bool r = true;
    for (auto k=A.disjuncts.begin(); k!= A.disjuncts.end() && r; k++)
    {
        r = contains(**k);
    }

    return r;
}

bool DBMUnion::operator==(const DBMUnion& A) const
{
    return contains(A) && A.contains(*this);
}

DBMUnion& DBMUnion::operator=(const DBMUnion& A)
{
    if (this != &A)
    {
        DBMUnion copy(A);
        clear();
        dim = copy.dim;
        disjuncts.swap(copy.disjuncts);
    }

    return *this;
}


void DBMUnion::relax_assign(unsigned i)
{
    list<DBM*>::iterator k;
    for (k=disjuncts.begin(); k!= disjuncts.end(); k++)
    {
        (*k)->relax_assign(i);
    }
}

// Predecessor w/ variable change for state classes
// f is the fired variable in the pred DBM
// pred_size is the predecessor DBM size
// as usual, indices gives for each variable in this its index in the predecessor DBM 
// (and pred_size if newly enabled) 
DBMUnion DBMUnion::pred(const unsigned f, unsigned indices[], const unsigned pred_size)
{
    list<DBM*>::iterator k;
    DBMUnion R(dim);
    for (k=disjuncts.begin(); k!= disjuncts.end(); k++)
    {
        DBM ND(pred_size);
        const DBM& D = **k;

        for (unsigned i = 1; i < dimension(); i++)
        {
            const unsigned ix = indices[i];
            if (ix != pred_size)
            {
                ND.constrain(ix, f, D(0, i));
                ND.constrain(f, ix, D(i, 0));
                
                for (unsigned j = 1; j < dimension(); j++)
                {
                    const unsigned jx = indices[j];
                    if (jx != pred_size)
                    {
                        ND.constrain(ix, jx, D(i, j));
                    } else {
                        ND.constrain(ix, f, D(i, 0) + D(i, j));
                    }
                }
            } else {
                for (unsigned j = 1; j < dimension(); j++)
                {
                    const unsigned jx = indices[j];
                    if (jx != pred_size)
                    {
                        ND.constrain(f, jx, D(0, i) + D(i, j));
                    }
                }
            } 
        }

        R.add(ND);
    }
    //cout << "DBM pred of " << endl;
    //cout << this->to_string() << endl;
    //cout << "is " << endl;
    //cout << R.to_string() << endl;

    return R;
}


void DBMUnion::rvchange_assign(const unsigned f)
{
    list<DBM*>::iterator k;
    for (k=disjuncts.begin(); k!= disjuncts.end(); k++)
    {
        vector<time_bound> rights(dimension());
        vector<time_bound> lefts(dimension());
        for (unsigned i = 1; i < dimension(); i++)
        {
            lefts[i] = (**k)(0, i);
            rights[i] = (**k)(i, 0);
            (**k)(i, 0) = time_bound::infinity;
            (**k)(0, i) = time_bound::infinity;
        }

        for (unsigned i = 1; i < dimension(); i++)
        {
            if (i != f)
            {
                (*k)->constrain(i, f, rights[i]);
                (*k)->constrain(f, i, lefts[i]);
            }
        }
    }
}


unsigned DBMUnion::dimension() const
{
    return dim;
}

string DBMUnion::to_string() const
{
    // We do not have labels, add some arbitrary ones
    // Warning! Quick hack limited to around 26 variables
    if (empty())
    {
        return "false";
    }

    vector<string> labels;
    labels.push_back("0");
    for (unsigned k = 0; k < dimension() - 1; k++)
    {
        string s = "A";
        s[0] += k;
        labels.push_back(s);
    }

    return to_string_labels(labels);
}

string DBMUnion::to_string_labels(const vector<string>& labels) const
{
    if (dim == 0)
    {
        return "false";
    } else {
        if (dim == 1)
        {
            return "true";
        }
    }


    bool comma = false;
    stringstream ostr;

    list<DBM*>::const_iterator k;
    for (k=disjuncts.begin(); k!= disjuncts.end(); k++)
    {
        if (comma)
            ostr << endl << "or" << endl;
        else
            comma = true;

        ostr << (*k)->to_string_labels(labels);
    }

    return ostr.str();
}

void DBMUnion::max_approx(cvalue M)
{
    list<DBM*>::iterator k;
    for (k=disjuncts.begin(); k!= disjuncts.end(); k++)
    {
        (*k)->max_approx(M);
    }
}

DBMUnion DBMUnion::scale(vector<cvalue> p, unsigned n)
{
    DBMUnion R(dim);
    for (auto k: disjuncts)
    {
        DBM RD(k->scale(p, n));
        R.add_reduce(RD);
    }

    return R;

}

bool DBMUnion::contains_origin() const
{
    bool result = false;
    list<DBM*>::const_iterator k;
    for (k = disjuncts.begin(); k != disjuncts.end() && !result; k++)
    {
        result = (*k)->contains_origin();
    }

    return result;
}

DBMUnion DBMUnion::predt(const DBMUnion& Bad) const
{
    DBMUnion PastG(*this);
    PastG.past();

    if (Bad.empty())
    {
        return PastG;
    } else {
        DBMUnion R(dim);
        R.add(DBM(dim));
        
        for (DBM* B: Bad.disjuncts)
        {
            DBMUnion PastBad(*B);
            PastBad.past();

            DBMUnion NegBad(B->complement());

            DBMUnion NegPastBad(PastBad.complement());
    
            // past(G) \ past(B)
            DBMUnion Gp(PastG);
            Gp.intersection_assign(NegPastBad);

            // G inter past(B)
            PastBad.intersection_assign(*this);
    
            // (G inter past(B)) \ B
            PastBad.intersection_assign(NegBad);

            // past of all this
            PastBad.past();

            Gp.add_reduce(PastBad);
            R.intersection_assign(Gp);
        }
        
        return R;
        
    }
}

DBMUnion DBMUnion::predut(const DBMUnion& Bad) const
{
    DBMUnion PastG(*this);
    PastG.past();

    if (Bad.empty())
    {
        return PastG;
    } else {
        DBMUnion R(dim);
        R.add(DBM(dim));
        
        DBMUnion NegGood(this->complement());
        for (DBM* B: Bad.disjuncts)
        {
            DBMUnion PastBad(*B);
            PastBad.past();

            DBMUnion BadMinusGood(*B);
            BadMinusGood.intersection_assign(NegGood);
            BadMinusGood.past();
            
            DBMUnion NegPastBadMG(BadMinusGood.complement());
    
            // past(G) \ past(B\G)
            DBMUnion Gp(PastG);
            Gp.intersection_assign(NegPastBadMG);

            // G inter past(B)
            PastBad.intersection_assign(*this);
    
            // (G inter past(B)) \ B
            DBMUnion NegBad(B->complement());
            PastBad.intersection_assign(NegBad);

            // past of all this
            PastBad.past();

            Gp.add_reduce(PastBad);
            R.intersection_assign(Gp);
        }
        
        return R;
        
    }
}

DBMUnion::~DBMUnion()
{
    clear();
}
