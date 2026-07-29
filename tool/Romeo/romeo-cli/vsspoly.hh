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

#ifndef ROMEO_VSSPOLY_HH
#define ROMEO_VSSPOLY_HH

#include <vector>
#include <string>

#include <pwt.hh>
#include <vsstate.hh>

#include <polyhedron.hh>

namespace romeo
{
    class VSSPolyMergeStorage;
    class VSSPolyRIncStorage;
    
    // Forward declarations
    class CTS;
    struct Job;
    class Transition;
    class VSClass;

    class VSSPoly: public VSState
    {
        protected:
            Polyhedron* D;
            
        protected:
            // Constructors
            VSSPoly(const Job&);
            VSSPoly(const VSSPoly&);
            VSSPoly(const VSSPoly&, unsigned);
            VSSPoly(const VSSPoly&, const Instruction&);

        public:
            virtual void remap(const VSSPoly&, unsigned, unsigned[], unsigned[], unsigned cv);

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
            
            virtual Polyhedron convergence_domain() const;

            virtual Key get_abstracted_key(bool*, bool*, cvalue*, cvalue*) const;

            Polyhedron* domain() const;

            // control
            virtual void set_winning(GraphNode*, const bool) const;
            virtual void init_winning(GraphNode*) const;
            virtual void add_winning(GraphNode*, GraphNode*) const;
            virtual bool has_winning(const GraphNode*) const;
            virtual PassedGN* init_passed_gn(WaitingGN&, WaitingGN&) const;
            virtual bool safety_control_bad_state() const;

            // Destructor
            virtual ~VSSPoly();

        friend class VSSPolyMergeStorage;
        friend class VSSPolyRIncStorage;
    };


    class VSSPolyMergeStorage: public VSStateMergeStorage
    {
        private:
            Polyhedron* D;

        public:
            virtual bool addr(const PWNode*, const PResult*);
            virtual unsigned size() const;

            VSSPolyMergeStorage(const VSSPoly*);
            virtual ~VSSPolyMergeStorage();
    };

    class VSSPolyRIncStorage: public VSStateRIncStorage
    {
        private:
            Polyhedron* D;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VSSPolyRIncStorage(const VSSPoly*);
            virtual ~VSSPolyRIncStorage();
    };
   
    class VSSPolyCostStorage: public VSSPolyRIncStorage
    {
        private:
            Avalue cost;

        public:
            virtual bool contains(const PWNode*) const;
            virtual bool is_contained_in(const PWNode*) const;

            VSSPolyCostStorage(const VSSPoly*);
            virtual ~VSSPolyCostStorage();
    };
}

#endif

