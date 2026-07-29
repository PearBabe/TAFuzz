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

#ifndef ROMEO_LINEAR_EXPRESSION
#define ROMEO_LINEAR_EXPRESSION

#include <list>
#include <utility>
#include <string>
#include <vector>

#include <valuation.hh>
#include <printable.hh>
#include <avalue.hh>

#define PPL_Linear_Expression Parma_Polyhedra_Library::Linear_Expression
#define PPL_Variable Parma_Polyhedra_Library::Variable

namespace Parma_Polyhedra_Library
{
    class Linear_Expression;
    class Variable;
}

namespace romeo
{
    class LinearExpression;
    class Avalue;

    enum cstr_rel { CSTR_GWEAK, CSTR_GSTRICT, CSTR_EQ, CSTR_LWEAK, CSTR_LSTRICT };

    typedef std::vector<std::pair<LinearExpression, cstr_rel>> cstr_list;

    struct Var: public Printable
    {
        unsigned index;

        Var(unsigned);
        std::string to_string() const;
        std::string to_string_labels(const std::vector<std::string>&) const;
    };

    LinearExpression operator* (const Var&, const cvalue);
    LinearExpression operator* (const cvalue, const Var&);

    LinearExpression operator+ (const Var&, const cvalue);
    LinearExpression operator+ (const cvalue, const Var&);

    LinearExpression operator- (const Var&, const cvalue);
    LinearExpression operator- (const cvalue, const Var&);

    LinearExpression operator+ (const Var&, const Var&);
    LinearExpression operator- (const Var&, const Var&);

    class LinearExpression: public Printable
    {
        private:
            std::list< std::pair<unsigned, cvalue> > coeffs;
            Avalue c;
            cvalue denominator;

        public:
            LinearExpression();
            LinearExpression(const cvalue);
            LinearExpression(const Var&);
            LinearExpression(const LinearExpression&);

            LinearExpression(const Avalue&);
            
            LinearExpression max_with_cst(const LinearExpression&);
            void add_coeff(const std::pair<unsigned, cvalue>&);
            void simplify();

            LinearExpression operator+ (const LinearExpression&) const;
            LinearExpression operator- (const LinearExpression&) const;
            
            bool operator== (const LinearExpression&) const;
            PPL_Linear_Expression to_PPL() const;
            
            void coefficients(const unsigned, cvalue[]) const;
            cvalue coefficient(const unsigned) const;
            Avalue const_term() const;
            cvalue den() const;

            bool non_negative() const;
            bool non_positive() const;
            bool negative() const;
            bool positive() const;

            void strictify();
            void remap(const unsigned, const unsigned[]);

            LinearExpression instantiate(const std::vector<Avalue>&) const;

            std::string to_string() const;
            std::string to_string_labels(const std::vector<std::string>&) const;
        
        friend LinearExpression operator+ (const Var&, const LinearExpression&);
        friend LinearExpression operator+ (const LinearExpression&, const Var&);
        
        friend LinearExpression operator- (const Var&, const LinearExpression&);
        friend LinearExpression operator- (const LinearExpression&, const Var&);

        friend LinearExpression operator* (const LinearExpression&, const cvalue);
        friend LinearExpression operator* (const cvalue, const LinearExpression&);

        friend LinearExpression operator/ (const LinearExpression&, const cvalue);

        friend LinearExpression operator+ (const LinearExpression&, const cvalue);
        friend LinearExpression operator+ (const cvalue, const LinearExpression&);

        friend LinearExpression operator- (const LinearExpression&, const cvalue);
        friend LinearExpression operator- (const cvalue, const LinearExpression&);

        friend bool operator< (const LinearExpression&, const LinearExpression&);
    };

    LinearExpression operator+ (const Var&, const LinearExpression&);
    LinearExpression operator+ (const LinearExpression&, const Var&);
    
    LinearExpression operator- (const Var&, const LinearExpression&);
    LinearExpression operator- (const LinearExpression&, const Var&);

    LinearExpression operator* (const LinearExpression&, const cvalue);
    LinearExpression operator* (const cvalue, const LinearExpression&);

    LinearExpression operator/ (const LinearExpression&, const cvalue);

    LinearExpression operator+ (const LinearExpression&, const cvalue);
    LinearExpression operator+ (const cvalue, const LinearExpression&);

    LinearExpression operator- (const LinearExpression&, const cvalue);
    LinearExpression operator- (const cvalue, const LinearExpression&);

    bool operator< (const LinearExpression&, const LinearExpression&);

    struct ltle
    {
        bool operator() (const LinearExpression&, const LinearExpression&) const;
    };
}

#endif

