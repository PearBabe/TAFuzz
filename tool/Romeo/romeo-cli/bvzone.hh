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

#ifndef ROMEO_BVZONE_HH
#define ROMEO_BVZONE_HH

#include <vector>
#include <list>
#include <string>

#include <avalue.hh>
#include <pwt.hh>
#include <expression.hh>
#include <cts.hh>
#include <vzone.hh>
#include <cost_dbm.hh>
#include <timebounds.hh>


namespace romeo
{
    class BVZone: public VZone
    {
        protected:
            Avalue offset_cost;
            value* cost_rates;

        protected:
            // From VSState
            virtual PWNode* successor(unsigned);

            // Constructors
            BVZone(const Job&);
            BVZone(const BVZone&);
            BVZone(const BVZone&, unsigned);
            BVZone(const BVZone&, const Instruction&);

            CostDBMUnion predecessor(const BVZone*, const CostDBMUnion&, const Transition*) const;
        public:
            // From PState
            virtual std::string to_string() const;

            virtual PWNode* copy(const Instruction*) const;
            
            // Create new symbolic states
            static BVZone* init(const Job&);

            // Control
            virtual bool update_reach(GraphNode*) const;
            virtual bool update_safe(GraphNode*) const;
            virtual void set_winning(GraphNode*, const bool) const;
            virtual void init_winning(GraphNode*) const;
            virtual void init_propagation(GraphNode*) const;
            virtual void destroy_graph_payload(GraphNode&) const;
            virtual void add_winning(GraphNode*, GraphNode*) const;
            virtual PResult* update_result(const GraphNode*, PResult*) const;
            virtual bool has_winning(const GraphNode*) const;
            PassedGN* init_passed_gn(WaitingGN&, WaitingGN&) const;

            Avalue get_offset_cost() const;

            // Destructor
            virtual ~BVZone();
    };

}

#endif
