#ifndef ROMEO_PDBM_HH
#define ROMEO_PDBM_HH

#include "linear_expression.hh"
#include <vector>

#include <valuation.hh>
#include <polyhedron.hh>

namespace romeo
{
    class PInterval
    {
        public:
            Avalue left;
            Avalue right;

        public:
            PInterval(); 
            PInterval(unsigned, bool); // for homogeneity with Polyhedron
            PInterval(const Polyhedron&); // conversion from Polyhedron
            
            Avalue minimize(const LinearExpression&) const;
            void constrain(const LinearExpression&, cstr_rel);
            void intersection_assign(const PInterval&);
            unsigned dimension() const;
            bool empty() const;
            bool contains(const PInterval&) const;
            std::string to_string_labels(std::vector<std::string>, unsigned) const;
            std::string to_string() const;
            void integer_shape_assign();

    };

    template<class T> class PDBMCoeff
    {
        public:
            std::vector<LinearExpression> exprs;
        
        public:
            static void add_reduce(std::vector<LinearExpression>&, const LinearExpression&);
            static void add_strong_reduce(std::vector<LinearExpression>&, const LinearExpression&, const T&);

            static bool dominates(const LinearExpression&, const LinearExpression&, const T&);
            static bool dominates_stricter(const LinearExpression&, const LinearExpression&, const T&);


        public:
            PDBMCoeff();
            PDBMCoeff(const PDBMCoeff&);
            PDBMCoeff(const LinearExpression&);
            PDBMCoeff(const std::vector<LinearExpression>&);

            void strictify();
            void integer_hull_assign(T&);
            std::string to_string_labels(const std::vector<std::string>&) const;
            unsigned size() const;

            PDBMCoeff<T> instantiate(const std::vector<Avalue>&) const;
            static PDBMCoeff plus(const PDBMCoeff&, const PDBMCoeff&, const T&);
            PDBMCoeff& operator=(const PDBMCoeff&);
            PDBMCoeff operator+(const PDBMCoeff&);
    };

    template<class T> class PDBM
    {
        private:
            unsigned size;

            PDBMCoeff<T>* matrix;
            T RC;

        public:
            PDBM(const unsigned, const unsigned);
            PDBM(const PDBM&);

            PDBMCoeff<T>& operator() (const unsigned, const unsigned) const;
            //bool empty() const;
            //void constrain(const unsigned, const unsigned, cvalue);
            void add_pconstraint(const T&);
            T pconstraint() const;
            
            void add_to_exprs(const unsigned, const unsigned, const PDBMCoeff<T>&);

            bool le_geq(const PDBMCoeff<T>&, const PDBMCoeff<T>&, const T&) const;
            bool le_eq(const PDBMCoeff<T>&, const PDBMCoeff<T>&) const;
            bool contains(const PDBM&) const;
            bool equals(const PDBM&) const;

            void integer_hull_assign();

            void remap(unsigned[], unsigned, unsigned);
            unsigned dimension() const;

            void abstract_time();

            std::string to_string_labels(const std::vector<std::string>&, const unsigned) const;

            romeo::Polyhedron to_Polyhedron() const;
    };
}

#endif


