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

#ifndef ROMEO_DBM_HH
#define ROMEO_DBM_HH

#include <list>
#include <vector>
#include <string>

#include <avalue.hh>
#include <valuation.hh>
#include <printable.hh>
#include <size_digest.hh>

namespace romeo
{
    class DBMUnion;
    class LinearExpression;

    class DBM: public Printable
    {
        protected:
            bool empty;
            unsigned size;
            time_bound* matrix;

        public:
            DBM(const unsigned);
            DBM(const DBM&);
    
            DBM& operator=(const DBM&);

            unsigned dimension() const;

            void merge(const DBM&);
            void intersection_assign(const DBM&);
            void constrain(const unsigned, const unsigned, const time_bound);
            
            void close();

            void future();
            void past();
            void reset(const unsigned);
            void free_clock(const unsigned);

            void abstract_time();
            
            DBM* remove_dimensions(const std::vector<unsigned>&);
            void remap(unsigned[], unsigned);

            DBM* slice(const unsigned, const cvalue);
            
            void normalize();
            void normalize1(const unsigned k);

            void inc_size();
            
            std::string to_string() const;
            std::string to_string_labels(const std::vector<std::string>& labels) const;
            
            relation_type compare(const DBM&) const;
            relation_type relation(const DBM&) const;

            time_bound& operator() (const unsigned, const unsigned) const;
            bool is_empty() const;
            void relax_assign(unsigned);

            void max_approx(cvalue);
            void kxapprox(const std::vector<time_bound>&);
            bool contains_origin() const;

            Avalue min(const cvalue[], std::vector<Avalue>&) const;
            Avalue min2(const cvalue[], std::vector<Avalue>&) const;
            Avalue min(const cvalue[]) const;
            Avalue min(const LinearExpression&) const;
            Avalue max(const LinearExpression&) const;
            Avalue min(const LinearExpression&, std::vector<Avalue>&) const;
            Avalue max(const LinearExpression&, std::vector<Avalue>&) const;

            DBM scale(std::vector<cvalue>, unsigned);

            DBMUnion complement() const;
            virtual ~DBM();

            SizeDigest eval_size() const;

            void copy_matrix(void*);

            bool operator<(const DBM&) const;

            friend class DBMUnion;

    };

    class DBMUnion
    {
        protected:
            std::list<DBM*> disjuncts;
            unsigned dim;

        public:
            DBMUnion(const unsigned);
            DBMUnion(const DBMUnion&);
            DBMUnion(const DBM&);

            unsigned dimension() const;

            void intersection_assign(const DBMUnion&);

            void add(const DBM&);
            bool add_reduce(const DBM&);
            void add_reduce(const DBMUnion&);

            void clear();
            
            void reduce_assign();
            void max_approx(cvalue);
            
            DBMUnion complement() const;
            //DBMUnion uprojection2(const unsigned, const time_bound, const time_bound) const;
            DBMUnion eprojection(const std::vector<unsigned>&) const;
            DBMUnion uprojection(const std::vector<unsigned>&, const DBMUnion&) const;
            
            unsigned size() const;
            
            void future();
            void past();
            void reset(const unsigned);
            void abstract_time();
            void constrain(const unsigned, const unsigned, const time_bound);
            bool empty() const;
            void remap(unsigned[], unsigned);
            void relax_assign(unsigned);

            std::string to_string() const;
            std::string to_string_labels(const std::vector<std::string>& labels) const;

            bool contains(const DBM&) const;
            bool contains(const DBMUnion&) const;

            DBMUnion& operator=(const DBMUnion&);
            bool operator==(const DBMUnion& A) const;

            void rvchange_assign(const unsigned);
            DBMUnion pred(const unsigned, unsigned[], const unsigned);

            DBMUnion predt(const DBMUnion&) const;
            DBMUnion predut(const DBMUnion&) const;
            bool contains_origin() const;

            DBM* begin() const;
            DBM* end() const;

            DBMUnion scale(std::vector<cvalue>, unsigned);

            ~DBMUnion();

            friend class CostDBMUnion;
    };

}

#endif
