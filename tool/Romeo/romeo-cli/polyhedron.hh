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

#ifndef ROMEO_POLYHEDRON_HH
#define ROMEO_POLYHEDRON_HH

#include <utility>
#include <string>
#include <vector>
#include <gmpxx.h>
#include <gmp.h>

#include <valuation.hh>
#include <linear_expression.hh>
#include <printable.hh>
#include <avalue.hh>
#include <size_digest.hh>

#define PPL_Polyhedron Parma_Polyhedra_Library::Pointset_Powerset<Parma_Polyhedra_Library::NNC_Polyhedron>
#define PPL_Constraint_System Parma_Polyhedra_Library::Constraint_System
#define PPL_Generator_System Parma_Polyhedra_Library::Generator_System
#define PPL_Linear_Expression Parma_Polyhedra_Library::Linear_Expression
#define PPL_Convex_Polyhedron Parma_Polyhedra_Library::NNC_Polyhedron
#define PPL_Constraint Parma_Polyhedra_Library::Constraint
#define PPL_Constraint_Iterator Parma_Polyhedra_Library::Constraint_System::const_iterator
#define PPL_Generator Parma_Polyhedra_Library::Generator
#define PPL_Variable Parma_Polyhedra_Library::Variable
#define PPL_Variables_Set Parma_Polyhedra_Library::Variables_Set
#define PPL_dimension_type Parma_Polyhedra_Library::dimension_type
#define PPL_UNIVERSE Parma_Polyhedra_Library::UNIVERSE
#define PPL_EMPTY Parma_Polyhedra_Library::EMPTY
#define PPL_print(a,b) Parma_Polyhedra_Library::IO_Operators::operator<<(a, b);

// Comment / Uncomment this line to use ints / GMP integers (Actually define it in Makefile)
// #define POLY_COEFFICIENT_MPZ 


#ifdef POLY_COEFFICIENT_MPZ
    #define POLY_COEFFICIENT_TYPE mpz_class
#else
    #define POLY_COEFFICIENT_TYPE int
#endif

// Forward declaration to avoid inclusion of ppl.hh at this point
namespace Parma_Polyhedra_Library
{
    class NNC_Polyhedron;
    class Linear_Expression;
    class Constraint;
    class Generator;
    template <typename PSET> class Pointset_Powerset;
    typedef size_t dimension_type;
}


namespace romeo
{
    // Romeo forward declarations
    class LinearExpression;
    struct Var;
    class DBM;
    class PInterval;

    // Mapper class for dimension remapping
    class Mapper
    {
    	private:
            unsigned new_size;
            unsigned* I;
    
        public:
            unsigned nnew;
    
    	public:
    		Mapper(const unsigned[], const unsigned, const unsigned);
    		bool has_empty_codomain() const;
            PPL_dimension_type max_in_codomain() const;
            bool maps(PPL_dimension_type, PPL_dimension_type&) const;
            ~Mapper();
    };

    PPL_Linear_Expression ppl_linear_expression(const PPL_Constraint&);

    class Polyhedron: public Printable
    {
        private:
            PPL_Polyhedron* D;

        private:
            static std::string coeff_to_string(POLY_COEFFICIENT_TYPE, bool&);
            static std::string constraint_to_string(const PPL_Constraint&, const std::vector<std::string>&, const unsigned, const unsigned);
            static unsigned nb_vars(const PPL_Constraint&, const unsigned, const unsigned);
            static unsigned first_var(const PPL_Constraint&, const unsigned, const unsigned);
            
            static POLY_COEFFICIENT_TYPE gcd(const PPL_Constraint&);
            static PPL_Constraint divide_and_floor(const PPL_Constraint&, POLY_COEFFICIENT_TYPE, const bool close=true);
            static bool is_tight(const PPL_Constraint&, const PPL_Generator&);
            static bool is_satisfied(const PPL_Constraint&, const PPL_Generator&);

            static PPL_Constraint simplification(const PPL_Constraint&);
            static PPL_Constraint integer_closure(const PPL_Constraint&);
            static PPL_Constraint integer_strictification(const PPL_Constraint&);
            static PPL_Convex_Polyhedron alter_constraints(const PPL_Convex_Polyhedron&, PPL_Constraint (*) (const PPL_Constraint&));

            static PPL_Constraint bound_normalize(const PPL_Constraint&, unsigned);

            static PPL_Convex_Polyhedron simplification(const PPL_Convex_Polyhedron&);
            static PPL_Convex_Polyhedron integer_closure(const PPL_Convex_Polyhedron&);
            static PPL_Convex_Polyhedron integer_strictification(const PPL_Convex_Polyhedron&);

            static PPL_Convex_Polyhedron bound_normalize(const PPL_Convex_Polyhedron&, unsigned);

            static void closed_integer_hull(PPL_Convex_Polyhedron&);
            static PPL_Convex_Polyhedron integer_hull_close(const PPL_Convex_Polyhedron&);
            static bool has_strict_constraints(const PPL_Convex_Polyhedron&);

            static void gauss(POLY_COEFFICIENT_TYPE** cs, unsigned start, unsigned nvars, unsigned neqs, unsigned nelims);
            static void abstract_find_dbm_coeffs(const PPL_Linear_Expression&, unsigned, unsigned, bool[], bool[], cvalue[], cvalue[], unsigned&, unsigned&, cvalue&, bool&);

            static bool contains_point(const PPL_Convex_Polyhedron& P, const PPL_Generator& v);

            void alter_disjuncts(PPL_Convex_Polyhedron (*) (const PPL_Convex_Polyhedron&));
        public: 
            static PPL_Convex_Polyhedron integer_hull(const PPL_Convex_Polyhedron&);
 
        public:
            Polyhedron(const LinearExpression&, const cstr_rel, const unsigned);
            Polyhedron(const Polyhedron&);
            Polyhedron(const unsigned, const bool);
            // Transitional
            Polyhedron(const PPL_Polyhedron&);
            Polyhedron(const PInterval&);

            virtual ~Polyhedron();

            void clear();

            unsigned dimension() const;
            void negation_assign();
            void intersection_assign(const Polyhedron&);
            void add(const Polyhedron&);
            void add_reduce(const Polyhedron&);

            void project_on(const unsigned, bool&, bool&, cvalue&, bool&, bool&, cvalue&, cvalue&, cvalue&);

            bool empty() const;
            bool universe() const;

            std::string to_string() const;
            std::string to_string_labels(const std::vector<std::string>&, const unsigned NP) const;

            void unconstrain(const unsigned);
            void remove_higher_dimensions(const unsigned);
            void add_dimensions(const unsigned);
            void constrain(const LinearExpression&, const cstr_rel);

            void affine_image(const Var&, const LinearExpression&, const cvalue);
            void remap(const unsigned [], const unsigned);
            void future_assign(const cvalue[]);
            Polyhedron predt(const cvalue[], const Polyhedron&);
            Polyhedron predt2(const cvalue[], const Polyhedron&);
            Polyhedron predt_sem(const cvalue[], const Polyhedron&);
            Polyhedron predut_sem(const cvalue[], const Polyhedron&);

            bool intersects(const Polyhedron&) const;
            bool contains(const Polyhedron&) const;
            bool exact_contains(const Polyhedron&) const;
            unsigned size() const;
            
            void integer_shape_assign();
            void integer_shape_close_assign();
            void simplification_assign();
            void integer_strictification_assign();
            void bound_normalize(unsigned);

            void simplify_with(const Polyhedron&);

            void reduce(const bool s=true);

            DBM abstract_parameters(unsigned, bool[], bool[], cvalue[], cvalue[]) const;

            PPL_Polyhedron to_PPL() const;

            bool operator==(const Polyhedron&);
            Polyhedron& operator=(const Polyhedron&);

            Avalue minimize(const LinearExpression&) const;
            bool contains_origin() const;
            void kapprox_assign(cvalue[]);

            Polyhedron eprojection(const std::vector<unsigned>&) const;
            Polyhedron uprojection(const std::vector<unsigned>&, const Polyhedron&) const;

            SizeDigest eval_size(unsigned) const;
    };
}

#endif

