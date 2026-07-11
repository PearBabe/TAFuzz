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



#ifndef ROMEO_MCOST_DBM_HH
#define ROMEO_MCOST_DBM_HH

#include <memory>

#include <dbm.hh>
#include <linear_expression.hh>

namespace romeo
{
    class MCostDBMUnion;

    struct CostEqn
    {
        cvalue* rates;
        time_bound coffset;
    };
    
    class MCostDBM: public DBM
    {
        private:
            std::vector<CostEqn> cost_eqns;
            mutable bool outdated_cexpr;
            mutable LinearExpression c_expr;

            mutable bool outdated_minc;
            mutable Avalue minc;

            mutable bool outdated_maxc;
            mutable Avalue maxc;

        public:
            MCostDBM(const unsigned);
            MCostDBM(const DBM&);
            MCostDBM(const MCostDBM&);

            MCostDBM& operator=(const MCostDBM&);

            void restriction_assign(const DBM&);
            void constrain(const unsigned, const unsigned, const time_bound&);

            MCostDBM facet_past(const MCostDBM&, const unsigned, const cvalue, const cvalue);
            MCostDBMUnion past_min(const cvalue);
            MCostDBMUnion past_max(const cvalue);

            void remap(unsigned[], unsigned);
            void unreset(const unsigned);

            void add_cost(const time_bound&);
            
            LinearExpression cost_expr() const;

            bool subsumes_eq(const MCostDBM&) const;
            bool subsumes_min(const MCostDBM&) const;
            bool subsumes_max(const MCostDBM&) const;

            time_bound cost_offset() const;
            time_bound origin_cost() const;

            MCostDBMUnion max(const MCostDBM&);
            MCostDBMUnion min(const MCostDBM&);
            MCostDBMUnion min2(const MCostDBM&);
            MCostDBMUnion min(const MCostDBMUnion&);

            std::string to_string() const;

            Avalue mincost() const;
            Avalue maxcost() const;

            ~MCostDBM();

        friend class MCostDBMUnion;
    };

    class MCostDBMUnion
    {
        protected:
            std::list<std::shared_ptr<MCostDBM> > disjuncts;
            unsigned dim;

            mutable bool outdated_minc;
            mutable Avalue minc;

            mutable bool outdated_maxc;
            mutable Avalue maxc;

        public:
            MCostDBMUnion(const unsigned s = 0);
            MCostDBMUnion(const MCostDBMUnion&);
            MCostDBMUnion(const MCostDBM&);
            MCostDBMUnion(const std::shared_ptr<MCostDBM>);

            MCostDBMUnion& operator=(const MCostDBMUnion&);

            unsigned dimension() const;

            void detach(std::shared_ptr<MCostDBM>&);

            void restriction_assign(const DBM&);
            void restriction_assign(const DBMUnion&);
            void restriction_assign_eq(const DBMUnion&);
            void restriction_assign_min(const DBMUnion&);
            void restriction_assign_max(const DBMUnion&);

            void constrain(const unsigned, const unsigned, const time_bound&);

            MCostDBMUnion past_min(const cvalue) const;
            MCostDBMUnion past_max(const cvalue) const;

            void remap(unsigned[], unsigned);
            void unreset(const unsigned);

            void add_cost(const time_bound&);

            void add(const MCostDBM&);
            void add(const std::shared_ptr<MCostDBM>);
            void add(const MCostDBMUnion&);
            void add_reduce_eq(const MCostDBM&);
            void add_reduce_eq(const std::shared_ptr<MCostDBM>);
            void add_reduce_eq(const MCostDBMUnion&);
            void add_reduce_min(const MCostDBM&);
            void add_reduce_min(const std::shared_ptr<MCostDBM>);
            void add_reduce_min(const MCostDBMUnion&);
            void add_reduce_max(const MCostDBM&);
            void add_reduce_max(const std::shared_ptr<MCostDBM>);
            void add_reduce_max(const MCostDBMUnion&);
            bool add_reduce_max_delta(const std::shared_ptr<MCostDBM>);
            bool add_reduce_max_delta(const MCostDBM&);
            bool test_reduce_max_delta(const std::shared_ptr<MCostDBM>);
            void add_reduce_max_delta(MCostDBMUnion& A, const MCostDBMUnion&);
            MCostDBMUnion add_reduce_max_delta(const MCostDBMUnion&);

            MCostDBMUnion reduce_max() const;

            bool subsumes_eq(const MCostDBM&) const;
            bool subsumes_eq(const MCostDBMUnion&) const;
            bool subsumes_min(const MCostDBM&) const;
            bool subsumes_min(const MCostDBMUnion&) const;
            bool subsumes_max(const MCostDBM&) const;
            bool subsumes_max(const MCostDBMUnion&) const;

            MCostDBMUnion max(const MCostDBM&) const;
            MCostDBMUnion max(const MCostDBMUnion&) const;
            MCostDBMUnion min(const MCostDBM&) const;
            MCostDBMUnion min(const MCostDBMUnion&) const;
            MCostDBMUnion maxmapmin(const MCostDBM&) const;
            MCostDBMUnion maxmapmin(const MCostDBMUnion&) const;

            bool empty() const;
            time_bound origin_cost() const;
            void clear();
            
            unsigned size() const;

            MCostDBMUnion predt_min(const DBMUnion&, const cvalue) const;
            MCostDBMUnion predt_max(const DBMUnion&, const cvalue) const;

            DBMUnion uncost() const;

            Avalue mincost() const;

            std::string to_string() const;

            ~MCostDBMUnion();

            friend class MCostDBM;
    };
}

#endif

