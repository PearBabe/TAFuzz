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




#ifndef ROMEO_CVSCLASS_SP_HH
#define ROMEO_CVSCLASS_SP_HH

#include <vector>
#include <utility>
#include <string>
#include <set>

#include <linear_expression.hh>
#include <vsclass.hh>

namespace romeo
{
    class CVSClassRIncStorage;
    
    class CVSClassSp: public VSClass
    {
        private:
            std::vector<std::pair<LinearExpression, DBM*> > fm_eliminate(const unsigned, const std::vector<std::pair<LinearExpression, DBM*> >&, const unsigned, const std::vector<bool>&) const;
            static std::vector<std::pair<LinearExpression, DBM*> > fm_eliminate2(DBM&, DBM&, const unsigned, const LinearExpression&, const unsigned, const std::vector<bool>&);

            std::vector<std::pair<LinearExpression, DBM*> > costs;

            void copy_costs(const CVSClassSp&);
            Avalue cmin;

        public:
            // Constructors
            CVSClassSp(const Job&);
            CVSClassSp(const CVSClassSp&);
            CVSClassSp(const CVSClassSp&, unsigned);
            CVSClassSp(const CVSClassSp&, const Instruction&);
    
            // Create new symbolic states
            virtual PWNode* copy(const Instruction*) const;
            static CVSClassSp* init(const Job&);
            virtual PWNode* successor(unsigned);
            virtual bool contains(const PWNode*) const;

            virtual EqStorage* eq_storage() const;
            virtual RIncStorage* rinc_storage() const;
            virtual MergeStorage* merge_storage() const;

            virtual Avalue min_cost() const;

            std::string to_string() const;

            virtual bool set_firing_date(const unsigned, const LExpression*, const cvalue);

            virtual PWNiterator* iterator();

            // Destructor
            ~CVSClassSp();

            friend class CVSCiterator;
            friend class CVSClassRIncStorage;
    };

    struct ltpledbm
    {
        bool operator() (const std::pair<LinearExpression, DBM*>&, const std::pair<LinearExpression, DBM*>&) const;
    };

    class CVSCiterator: public VSSiterator
    {
        protected:
            const CVSClassSp* succ;
            unsigned subindex;

        public:
            CVSCiterator(PWNode*);
            virtual PWNode* next();
    };


    class CVSClassRIncStorage: public VSClassRIncStorage
    {
        private:
            LinearExpression cost;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            CVSClassRIncStorage(const CVSClassSp*);
            virtual ~CVSClassRIncStorage();
    };


}


#endif
