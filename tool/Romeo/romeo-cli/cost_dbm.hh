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



#ifndef ROMEO_COST_DBM_HH
#define ROMEO_COST_DBM_HH

#include <memory>

#include <dbm.hh>
#include <linear_expression.hh>

namespace romeo
{
    class CostDBMUnion;
    
    class CostDBM: public DBM
    {
        private:
            cvalue* rates;
            time_bound coffset;
            mutable bool outdated_cexpr;
            mutable LinearExpression c_expr;

            mutable bool outdated_minc;
            mutable Avalue minc;

            mutable bool outdated_maxc;
            mutable Avalue maxc;

        public:
            CostDBM(const unsigned);
            CostDBM(const DBM&);
            CostDBM(const CostDBM&);

            CostDBM& operator=(const CostDBM&);

            void restriction_assign(const DBM&);
            void constrain(const unsigned, const unsigned, const time_bound&);

            CostDBM facet_past(const CostDBM&, const unsigned, const cvalue, const cvalue);
            CostDBMUnion past_min(const cvalue);
            CostDBMUnion past_max(const cvalue);

            void remap(unsigned[], unsigned);
            void unreset(const unsigned);

            void add_cost(const time_bound&);
            
            LinearExpression cost_expr() const;

            bool subsumes_eq(const CostDBM&) const;
            bool subsumes_min(const CostDBM&) const;
            bool subsumes_max(const CostDBM&) const;

            time_bound cost_offset() const;
            time_bound origin_cost() const;

            CostDBMUnion max(const CostDBM&);
            CostDBMUnion min(const CostDBM&);
            CostDBMUnion min2(const CostDBM&);
            CostDBMUnion min(const CostDBMUnion&);

            std::string to_string() const;

            Avalue mincost() const;
            Avalue maxcost() const;

            ~CostDBM();

        friend class CostDBMUnion;
    };

    class CostDBMUnion
    {
        protected:
            std::list<std::shared_ptr<CostDBM> > disjuncts;
            unsigned dim;

            mutable bool outdated_minc;
            mutable Avalue minc;

            mutable bool outdated_maxc;
            mutable Avalue maxc;

            void invalidate_cost_cache();
            void accept_dimension(unsigned);

        public:
            CostDBMUnion(const unsigned s = 0);
            CostDBMUnion(const CostDBMUnion&);
            CostDBMUnion(const CostDBM&);
            CostDBMUnion(const std::shared_ptr<CostDBM>);

            CostDBMUnion& operator=(const CostDBMUnion&);

            unsigned dimension() const;

            void detach(std::shared_ptr<CostDBM>&);

            void restriction_assign(const DBM&);
            void restriction_assign(const DBMUnion&);
            void restriction_assign_eq(const DBMUnion&);
            void restriction_assign_min(const DBMUnion&);
            void restriction_assign_max(const DBMUnion&);

            void constrain(const unsigned, const unsigned, const time_bound&);

            CostDBMUnion past_min(const cvalue) const;
            CostDBMUnion past_max(const cvalue) const;

            void remap(unsigned[], unsigned);
            void unreset(const unsigned);

            void add_cost(const time_bound&);

            void add(const CostDBM&);
            void add(const std::shared_ptr<CostDBM>);
            void add(const CostDBMUnion&);
            void add_reduce_eq(const CostDBM&);
            void add_reduce_eq(const std::shared_ptr<CostDBM>);
            void add_reduce_eq(const CostDBMUnion&);
            void add_reduce_min(const CostDBM&);
            void add_reduce_min(const std::shared_ptr<CostDBM>);
            void add_reduce_min(const CostDBMUnion&);
            void add_reduce_max(const CostDBM&);
            void add_reduce_max(const std::shared_ptr<CostDBM>);
            void add_reduce_max(const CostDBMUnion&);
            bool add_reduce_max_delta(const std::shared_ptr<CostDBM>);
            bool add_reduce_max_delta(const CostDBM&);
            bool test_reduce_max_delta(const std::shared_ptr<CostDBM>);
            void add_reduce_max_delta(CostDBMUnion& A, const CostDBMUnion&);
            CostDBMUnion add_reduce_max_delta(const CostDBMUnion&);

            CostDBMUnion reduce_max() const;

            bool subsumes_eq(const CostDBM&) const;
            bool subsumes_eq(const CostDBMUnion&) const;
            bool subsumes_min(const CostDBM&) const;
            bool subsumes_min(const CostDBMUnion&) const;
            bool subsumes_max(const CostDBM&) const;
            bool subsumes_max(const CostDBMUnion&) const;

            CostDBMUnion max(const CostDBM&) const;
            CostDBMUnion max(const CostDBMUnion&) const;
            CostDBMUnion min(const CostDBM&) const;
            CostDBMUnion min(const CostDBMUnion&) const;
            CostDBMUnion maxmapmin(const CostDBM&) const;
            CostDBMUnion maxmapmin(const CostDBMUnion&) const;

            bool empty() const;
            time_bound origin_cost() const;
            void clear();
            
            unsigned size() const;

            CostDBMUnion predt_min(const DBMUnion&, const cvalue) const;
            CostDBMUnion predt_max(const DBMUnion&, const cvalue) const;

            DBMUnion uncost() const;

            Avalue mincost() const;

            std::string to_string() const;

            ~CostDBMUnion();

            friend class CostDBM;
    };
}

#endif
