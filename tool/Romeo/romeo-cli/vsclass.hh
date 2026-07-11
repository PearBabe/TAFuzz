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

#ifndef ROMEO_VSCLASS_HH
#define ROMEO_VSCLASS_HH

#include <vector>
#include <list>
#include <string>

#include <pwt.hh>
#include <expression.hh>
#include <cts.hh>
#include <vsstate.hh>
#include <dbm.hh>
#include <timebounds.hh>


namespace romeo
{
    class VSCPoly;
    class VSClassEqStorage;
    class VSClassMergeStorage;
    class VSClassRIncStorage;

    class VSClass: public VSState
    {
        protected:
            DBM * D;

        protected:
            // From VSState
            virtual PWNode* successor(unsigned);
            virtual bool firable(unsigned) const;
            virtual bool set_firing_date(const unsigned, const LExpression*, const cvalue);

            // Constructors
            VSClass(const Job&);
            VSClass(const VSClass&);
            VSClass(const VSClass&, unsigned);
            VSClass(const VSClass&, const Instruction&);

            DBMUnion pred(const VSClass*, const DBM*, const DBMUnion*, const unsigned, const bool) const;
        public:
            // From PState
            virtual std::string to_string() const;

            // From PWNode
            virtual bool key_less(const PWNode*) const;
            virtual bool equals(const PWNode*) const;
            virtual bool contains(const PWNode*) const;
            virtual PWTRel compare(const PWNode*) const;
            virtual bool empty() const;
            virtual PassedList* init_passed(WaitingList&, unsigned, bool b=false) const;
            virtual EqStorage* eq_storage() const;
            virtual RIncStorage* rinc_storage() const;
            virtual MergeStorage* merge_storage() const;

            virtual Key get_key() const;
            virtual unsigned key_size() const;

            virtual PWNode* copy(const Instruction*) const;
            
            virtual void min_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;
            virtual void max_clockval(const Transition*, cvalue&, cvalue&, bool&, bool&, bool&) const;
            
            // Create new symbolic states
            static VSClass* init(const Job&);

            // Control
            virtual bool update_reach(GraphNode*) const;
            virtual bool update_safe(GraphNode*) const;
            virtual void set_winning(GraphNode*, const bool) const;
            virtual void init_winning(GraphNode*) const;
            virtual void add_winning(GraphNode*, GraphNode*) const;
            virtual PResult* update_result(const GraphNode*, PResult*) const;
            virtual bool has_winning(const GraphNode*) const;
            PassedGN* init_passed_gn(WaitingGN& F, WaitingGN& B) const;
            virtual SuccInfo* add_succ(GraphNode*, const Transition*, PState*, GraphNode*) const;
            virtual bool safety_control_bad_state() const;


            // Destructor
            virtual ~VSClass();

        friend class VSClassEqStorage;
        friend class VSClassRIncStorage;
        friend class VSClassMergeStorage;
    };

    class VSClassMergeStorage: public VSStateMergeStorage
    {
        private:
            DBMUnion D;

        public:
            virtual bool addr(const PWNode*, const PResult*);
            virtual unsigned size() const;

            VSClassMergeStorage(const VSClass*);
            virtual ~VSClassMergeStorage();
    };

    class VSClassRIncStorage: public VSStateRIncStorage
    {
        protected:
            DBM* D;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VSClassRIncStorage(const VSClass*);
            virtual ~VSClassRIncStorage();
    };

    class VSClassEqStorage: public VSStateEqStorage
    {
        private:
            DBM* D;

        public:
            virtual bool equals(const PWNode*) const;
            virtual bool key_less(const EqStorage*) const;

            VSClassEqStorage(const VSClass*);
            virtual ~VSClassEqStorage();
    };
   

}

#endif

