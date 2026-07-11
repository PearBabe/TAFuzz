/* This file is part of the Roméo model-checking software

Copyright École Centrale de Nantes, LS2N

Contributors: Didier Lime (2014-2025)

Didier.Lime@ec-nantes.fr

This software is a computer program whose purpose is to [describe
functionalities and technical features of your software].

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

#ifndef ROMEO_VLSCLASS_HH
#define ROMEO_VLSCLASS_HH

#include "polyhedron.hh"
#include <vector>
#include <list>
#include <string>

#include <pwt.hh>
#include <expression.hh>
#include <cts.hh>
#include <vsstate.hh>
#include <ldbm.hh>

namespace romeo
{
    template<class T> class VLSClass: public VSState
    {
        protected:
            std::vector<LDBM<T>> D;

        protected:
            // From VSState
            virtual PWNode* successor(unsigned);
            virtual bool firable(unsigned) const;
            virtual bool set_firing_date(const unsigned, const LExpression*, const cvalue);

            // Constructors
            VLSClass(const Job&);
            VLSClass(const VLSClass&);
            VLSClass(const VLSClass&, unsigned);
            VLSClass(const VLSClass&, const Instruction&);

            static bool contains(const std::vector<LDBM<T>>&, const std::vector<LDBM<T>>&);
        public:
            // From PState
            virtual std::string to_string() const;

            // From PWNode
            virtual bool key_less(const PWNode*) const;
            virtual bool equals(const PWNode*) const;
            virtual bool contains(const PWNode*) const;
            virtual PWTRel compare(const PWNode*) const;
            virtual bool empty() const;
            virtual PassedList* init_passed(WaitingList&, unsigned vs, bool b=false) const;
            virtual PWNode* copy(const Instruction*) const;
            
            virtual void min_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;
            virtual void max_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;
            
            // Create new symbolic states
            static VLSClass* init(const Job&);

            virtual void compute_rc() const;

            virtual PResult* init_result(bool) const;
            
            // Restrict using parametric constraints
            virtual bool restriction(const PResult&);

            virtual PassedGN* init_passed_gn(WaitingGN&, WaitingGN&) const;

            virtual EqStorage* eq_storage() const;
            virtual RIncStorage* rinc_storage() const;
            virtual MergeStorage* merge_storage() const;

            // Destructor
            ~VLSClass();

            template<class U> friend class VLSClassMergeStorage;
            template<class U> friend class VLSClassRIncStorage;
    };

    template<class T> class VLSClassMergeStorage: public VSStateMergeStorage
    {
        private:
            std::vector<LDBM<T>> D;

        public:
            virtual bool addr(const PWNode*, const PResult*);
            virtual unsigned size() const;

            VLSClassMergeStorage(const VLSClass<T>*);
            virtual ~VLSClassMergeStorage();
    };

    template<class T> class VLSClassRIncStorage: public VSStateRIncStorage
    {
        private:
            std::vector<LDBM<T>> D;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VLSClassRIncStorage(const VLSClass<T>*);
            virtual ~VLSClassRIncStorage();
    };
   
}


#endif

