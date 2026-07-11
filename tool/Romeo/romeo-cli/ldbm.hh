#ifndef ROMEO_LDBM_HH
#define ROMEO_LDBM_HH

#include <vector>

#include <valuation.hh>
#include <linear_expression.hh>
#include <polyhedron.hh>

namespace romeo
{
    class LExpression;
    class TimeInterval;


    template<class T> class LDBM
    {
        private:
            unsigned size;

            LinearExpression* matrix;
            T RC;

        public:
            static void add_reduce(std::vector<LinearExpression>&, const LinearExpression&);
            static void add_strong_reduce(std::vector<LinearExpression>&, const LinearExpression&, const T&);

        public:
            LDBM(const unsigned, const unsigned);
            LDBM(const LDBM&);

            LinearExpression& operator() (const unsigned, const unsigned) const;
            //bool empty() const;
            //void constrain(const unsigned, const unsigned, cvalue);
            T pconstraint() const;
            void add_pconstraint(const T&);

            bool contains_restricted(const LDBM& d, const T& P) const;
            bool contains(const LDBM&) const;
            bool equals(const LDBM&) const;

            void integer_hull_assign();

            void remap(unsigned[], unsigned, unsigned);
            unsigned dimension() const;

            void abstract_time();

            std::string to_string_labels(const std::vector<std::string>&, const unsigned) const;
    };

}

#endif


