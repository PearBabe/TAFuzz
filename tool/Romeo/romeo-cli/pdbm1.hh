#ifndef ROMEO_PDBM1_HH
#define ROMEO_PDBM1_HH

#include <vector>
#include <list>

#include <valuation.hh>

namespace romeo
{
    class LExpression;
    class TimeInterval;

    class SCoeff1
    {
        public:
            time_bound x0; // x1 * a + x0 where a is a parameter
            value x1;
            
            // support interval
            value lv; // left endpoint
            value rv; // righ endpoint
            bool lb; // left bounded?
            bool rb; // right bounded?
            bool ls; // strict?
            bool rs;

        public:
            SCoeff1(time_bound, value, value, value, bool, bool, bool, bool);

        public:
            static const SCoeff1 infinity;
            static const SCoeff1 zero;
    };

    class PDBM1Coeff
    {
        public:
            std::list<SCoeff1> exprs;

        public:
            static PDBM1Coeff lower_constraint(const unsigned, const TimeInterval&, const valuation, const valuation);
            static PDBM1Coeff upper_constraint(const unsigned, const TimeInterval&, const valuation, const valuation);
            static PDBM1Coeff zero(const unsigned);

        public:
            PDBM1Coeff();
            PDBM1Coeff(const PDBMCoeff&);
            PDBM1Coeff(const unsigned);
            PDBM1Coeff(const LConstraint1&);

            PDBM1Coeff operator+ (const PDBMCoeff&) const;
            void min_with (const PDBMCoeff&);

            PInterval greater_than_zero(const bool) const;

            void strictify();
            void integer_hull_assign();

            friend bool operator< (const PDBM1Coeff&, const PDBM1Coeff&);
            friend bool operator<=(const PDBM1Coeff&, const PDBM1Coeff&);
            friend bool operator==(const PDBM1Coeff&, const PDBM1Coeff&);

            std::string to_string_labels(const std::vector<std::string>&, const unsigned) const;
    };

    bool operator< (const PDBM1Coeff&, const PDBM1Coeff&);
    bool operator<=(const PDBM1Coeff&, const PDBM1Coeff&);
    bool operator==(const PDBM1Coeff&, const PDBM1Coeff&);

    class PDBM1
    {
        private:
            unsigned size;

            PDBM1Coeff* matrix;

        public:
            PDBM1(const unsigned, const unsigned);
            PDBM1(const PDBM1&);

            PDBM1Coeff& operator() (const unsigned, const unsigned) const;
            //bool empty() const;
            //void constrain(const unsigned, const unsigned, cvalue);
            void add_pconstraint(const PInterval&);
            PInterval pconstraint() const;

            bool contains(const PDBM1&) const;
            bool equals(const PDBM1&) const;

            void integer_hull_assign();

            void remap(unsigned[], unsigned, unsigned);
            unsigned dimension() const;

            std::string to_string_labels(const std::vector<std::string>&, const unsigned) const;
    };
}

#endif


