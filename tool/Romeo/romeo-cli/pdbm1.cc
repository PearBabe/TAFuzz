#include <string>


#include <pdbm1.hh>
#include <lexpression.hh>
#include <linear_expression.hh>
#include <time_interval.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

const SCoeff1 SCoeff1::infinity(time_bound::infinity, 0, 0, 0, false, false, true, true);
const SCoeff1 SCoeff1::zero(time_bound::zero, 0, 0, 0, false, false, true, true);

SCoeff1::SCoeff1(time_bound b, value a, value lval, value rval, bool lbound, bool rbound, bool lstrict, bool rstrict): x0(b), x1(a), lv(lval), rv(rval), lb(lbound), rb(rbound), ls(lstrict), rs(rstrict)
{
}

PDBM1Coeff::PDBM1Coeff()
{
    exprs.push_back(SCoeff1::infinity);
}

PDBM1Coeff::PDBM1Coeff(const PDBM1Coeff& c): exprs(c.exprs)
{
}

PDBM1Coeff::PDBM1Coeff(const SCoeff1& P)
{
    exprs.push_back(P);
}

PDBM1Coeff PDBM1Coeff::zero()
{
    return PDBM1Coeff(SCoeff1::zero);
}

PDBM1Coeff PDBM1Coeff::upper_constraint(const unsigned s, const TimeInterval& I, const valuation V, const valuation C) 
{
    PDBM1Coeff P;
    
    if (!I.unbounded)
    {
        const LinearExpression L = I.ubound.linear_expression(V, C);

        p.x0 = L.coefficient(0);
        p.x1 = L.coefficient(1);
        P.s =  I.ustrict;
    }

    return P;
}

PDBM1Coeff PDBM1Coeff::lower_constraint(const unsigned s, const TimeInterval& I, const valuation V, const valuation C) 
{
    const LinearExpression L = I.lbound.linear_expression(V, C);

    return PDBM1Coeff(L.coefficient(0), L.coefficient(1), I.lstrict);
}

PDBM1Coeff PDBM1Coeff::operator+ (const PDBM1Coeff& c) const
{
    Log.start("PDBM1Coeff::operator+");
    const PPL_Constraint_System C  = exprs.minimized_constraints();
    const PPL_Constraint_System Cc = c.exprs.minimized_constraints();

    PPL_Constraint_Iterator i, j;

    const unsigned s = exprs.space_dimension();

    PPL_Convex_Polyhedron P(s, PPL_UNIVERSE);
    const PPL_Variable x(s-1);

    for (i = C.begin(); i != C.end(); i++)
    {
        if (i->coefficient(x) != 0)
        {
            PPL_Linear_Expression ei = ppl_linear_expression(*i) + x;
            ei.set_space_dimension(s-1);
            for (j = Cc.begin(); j != Cc.end(); j++)
            {
                if (j->coefficient(x) != 0)
                {
                    PPL_Linear_Expression ej = ppl_linear_expression(*j) + x;
                    ej.set_space_dimension(s-1);
                    if (i->is_strict_inequality() || j->is_strict_inequality())
                        P.add_constraint(x < ei + ej);
                    else
                        P.add_constraint(x <= ei + ej);
                }
            }
        }
    }

    Log.stop("PDBM1Coeff::operator+");
    return PDBM1Coeff(P);
}

void PDBM1Coeff::min_with (const PDBM1Coeff& c)
{
    Log.start("PDBM1Coeff::min_with");
    exprs.intersection_assign(c.exprs);
    Log.stop("PDBM1Coeff::min_with");
}

PPL_Convex_Polyhedron PDBM1Coeff::greater_than_zero(const bool strict) const
{
    const PPL_Constraint_System C  = exprs.minimized_constraints();
    PPL_Constraint_Iterator i;

    const unsigned s = exprs.space_dimension();
    const PPL_Variable x(s-1);

    PPL_Convex_Polyhedron P(s-1, PPL_UNIVERSE);
    
    for (i = C.begin(); i != C.end(); i++)
    {
        if (i->coefficient(x) != 0)
        {
            PPL_Linear_Expression c = ppl_linear_expression(*i) + x;
            c.set_space_dimension(s-1);
            if (strict)
                P.add_constraint(c > 0);
            else
                P.add_constraint(c >= 0);
        }
    }

    return P;
}


void PDBM1Coeff::strictify()
{
    const PPL_Constraint_System C  = exprs.minimized_constraints();
    PPL_Constraint_Iterator i;
    const unsigned s = exprs.space_dimension();

    PPL_Convex_Polyhedron P(s, PPL_UNIVERSE);
    for (i = C.begin(); i != C.end(); i++)
    {
        const PPL_Linear_Expression c = ppl_linear_expression(*i);
        P.add_constraint(c > 0);
    }

    exprs = P;
}

bool romeo::operator== (const PDBM1Coeff& a, const PDBM1Coeff& b)
{
    return a.exprs == b.exprs;
}

bool romeo::operator<= (const PDBM1Coeff& a, const PDBM1Coeff& b)
{
    return b.exprs.contains(a.exprs);
}

bool romeo::operator< (const PDBM1Coeff& a, const PDBM1Coeff& b)
{
    return b.exprs.strictly_contains(a.exprs);
}

string PDBM1Coeff::to_string_labels(const vector<string>& labels, const unsigned NP) const
{
    stringstream st;
    
    const PPL_Constraint_System C  = exprs.minimized_constraints();
    PPL_Constraint_Iterator i;
    const unsigned s = exprs.space_dimension();
    const PPL_Variable x(s - 1);

    bool comma = false;
    bool strict = false;
    for (i = C.begin(); i != C.end(); i++)
    {
        if (i->coefficient(x) != 0)
        {
            if (i->is_strict_inequality())
                strict = true;

            if (comma)
                st << ", ";
            else
                comma = true;

            const PPL_Linear_Expression c = ppl_linear_expression(*i) + x;
            bool plus = false;
            for (unsigned k = 0; k < s - 1; k++)
            {
                PPL_Variable xk(k); 
                if (c.coefficient(xk) != 0)
                {
                    if (plus)
                        st << " + ";
                    else
                        plus = true;

                    if (c.coefficient(xk) != 1)
                        st << c.coefficient(xk) << "*";
                    st << labels[k];
                }
            }

            if (c.inhomogeneous_term() != 0 || !plus)
            {
                if (plus)
                    st << " + "; 

                st << c.inhomogeneous_term();
            }
        }
    }
    string result = "min( " + st.str() + " )";
    if (strict)
        result = " < " + result;
    else
        result = " <= " + result; 
    

    return result;
}

void PDBM1Coeff::integer_hull_assign()
{
    exprs = Polyhedron::integer_hull(exprs);
}

PDBM1::PDBM1(const unsigned s, const unsigned NP): size(s), matrix(new PDBM1Coeff[size * size]), RC(NP, PPL_UNIVERSE)
{
}

PDBM1::PDBM1(const PDBM1& d): size(d.size), matrix(new PDBM1Coeff[size*size]), RC(d.RC) 
{
    for (unsigned i = 0; i < size * size; i++)
        matrix[i] = d.matrix[i];
}

void PDBM1::add_pconstraint(const PPL_Convex_Polyhedron& F)
{
    PPL_Convex_Polyhedron Fe = F;
    Fe.add_space_dimensions_and_embed(1);

    RC.intersection_assign(F);

    for (unsigned i = 0; i < size; i++)
    {
        for (unsigned j = 0; j < size; j++)
        {
            (*this)(i,j).min_with(Fe);
        }
    }
}

PPL_Convex_Polyhedron PDBM1::pconstraint() const
{
    return RC;
}


bool PDBM1::contains(const PDBM1& d) const
{
    Log.start("PDBM1::contains");
    bool result = RC.contains(d.RC);

    if (result)
    {
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;
        //cout << to_Polyhedron() << endl;
        //cout << "_________________________________________" << endl;
        //cout << d.to_Polyhedron() << endl;
        //cout << "::::::::::::::::::::::::::::::::::::::::::::::::::::::" << endl;

        unsigned i;
        for (i = 0; i < size*size && d.matrix[i] <= this->matrix[i]; i++);

        if (i != size*size)
            result = false;
    }

    Log.stop("PDBM1::contains");
    return result;
}

bool PDBM1::equals(const PDBM1& d) const
{
    bool result = (RC == d.RC);

    if (result)
    {
        unsigned i;
        for (i = 0; i < size*size && this->matrix[i] == d.matrix[i]; i++);

        if (i != size*size)
            result = false;
    }

    return result;
}

PDBM1Coeff& PDBM1::operator() (const unsigned i, const unsigned j) const
{
    return matrix[i*size+j];
}

unsigned PDBM1::dimension() const
{
    return size;
}

void PDBM1::remap(unsigned indices[], unsigned new_size, unsigned NP)
{
    PDBM1Coeff* m = new PDBM1Coeff[new_size*new_size];
    for (unsigned i=0; i<new_size; i++)
    {
        if (indices[i] == size)
        {
            for (unsigned j=0; j<new_size; j++)
            {
                m[i*new_size+j] = (i==j ? PDBM1Coeff::zero(NP) : PDBM1Coeff(NP));
            }
        } else {
            for (unsigned j=0; j<new_size; j++)
            {
                if (indices[j] != size)
                {
                    m[i*new_size+j] = (*this)(indices[i],indices[j]);
                } else {
                    m[i*new_size+j] = (i==j ? PDBM1Coeff::zero(NP) : PDBM1Coeff(NP));
                }
            }
        }
    }

    delete [] matrix;
    matrix = m;
    size = new_size;
}

string PDBM1::to_string_labels(const vector<string>& labels, const unsigned NP) const
{
    stringstream domain;
    const PDBM1& D = *this;

    bool lineskip = false;
    for (unsigned i=1; i<size; i++)
    {
        if (lineskip)
            domain << endl;
        else
            lineskip = true;


        domain << "-" << labels[i + NP];
        domain << D(0, i).to_string_labels(labels, NP) << endl;
        domain << labels[i + NP];
        domain << D(i, 0).to_string_labels(labels, NP);
    }
    domain << endl;

    for (unsigned i=1; i<size; i++)
    {
        for (unsigned j=1; j<i; j++)
        {
            domain << labels[i + NP] << " - " << labels[j + NP] << D(i, j).to_string_labels(labels, NP) << endl;
            domain << labels[j + NP] << " - " << labels[i + NP] << D(j, i).to_string_labels(labels, NP) << endl;
	    }
    }

    domain << Polyhedron(PPL_Polyhedron(RC)).to_string_labels(labels, NP);

    return domain.str();
}

void PDBM1::integer_hull_assign()
{
    RC = Polyhedron::integer_hull(RC);
    for (unsigned i = 0; i < size; i++)
        for (unsigned j = 0; j < size; j++)
            if (i != j)
                (*this)(i,j).integer_hull_assign();
}

romeo::Polyhedron PDBM1::to_Polyhedron() const
{
    unsigned NP = RC.space_dimension();

    PPL_Convex_Polyhedron P(RC);
    P.add_space_dimensions_and_embed(size - 1);

    for (unsigned i = 1; i < size; i++)
    {
        // In the result polyhedron
        const PPL_Variable vi(NP + i - 1);

        // In the coefficient
        const PPL_Variable x(NP);

        PPL_Constraint_Iterator k;

        const PDBM1Coeff c0i = matrix[i];
        const PPL_Constraint_System C2  = c0i.exprs.minimized_constraints();
        for (k = C2.begin(); k != C2.end(); k++)
        {
            if (k->coefficient(x) != 0)
            {
                const PPL_Linear_Expression L = ppl_linear_expression(*k) + x;
                if (k->is_strict_inequality())
                {
                    P.add_constraint(-vi < L);
                } else {
                    P.add_constraint(-vi <= L);
                }
            }
        }

        const PDBM1Coeff ci0 = matrix[i*size];
        const PPL_Constraint_System C  = ci0.exprs.minimized_constraints();
        for (k = C.begin(); k != C.end(); k++)
        {
            if (k->coefficient(x) != 0)
            {
                const PPL_Linear_Expression L = ppl_linear_expression(*k) + x;
                if (k->is_strict_inequality())
                {
                    P.add_constraint(vi < L);
                } else {
                    P.add_constraint(vi <= L);
                }
            }
        }
    }

    for (unsigned i = 1; i < size; i++)
    {
        // In the result polyhedron
        const PPL_Variable vi(NP + i - 1);

        // In the coefficient
        const PPL_Variable x(NP);
        for (unsigned j = 1; j < size; j++)
        {
            if (i != j)
            {
                const PPL_Variable vj(NP + j - 1);

                const PDBM1Coeff cij = matrix[i*size + j];
                const PPL_Constraint_System C  = cij.exprs.minimized_constraints();
                PPL_Constraint_Iterator k;
                for (k = C.begin(); k != C.end(); k++)
                {
                    if (k->coefficient(x) != 0)
                    {
                        const PPL_Linear_Expression L = ppl_linear_expression(*k) + x;
                        if (k->is_strict_inequality())
                        {
                            P.add_constraint(vi - vj < L);
                        } else {
                            P.add_constraint(vi - vj <= L);
                        }
                    }
                }
            }
        }
    }

    return romeo::Polyhedron(PPL_Polyhedron(P));
}

