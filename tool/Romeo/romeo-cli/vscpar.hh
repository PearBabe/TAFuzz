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

#ifndef ROMEO_VSCPAR_HH
#define ROMEO_VSCPAR_HH

#include "polyhedron.hh"
#include <vscpoly.hh>

namespace romeo
{
    class VSCPar: public VSCPoly
    {
        protected:
            mutable Polyhedron* IH;
            Polyhedron* consistency;

        protected:
            // Constructors
            VSCPar(const Job&);
            VSCPar(const VSCPar&);
            VSCPar(const VSCPar&, unsigned);
            VSCPar(const VSCPar&, const Instruction&);

            virtual PWNode* successor(unsigned);
            virtual bool set_firing_date(const unsigned, const LExpression*, const cvalue);

            // Polymorphic subset of constructors
            virtual void init_constraints();
            virtual void newen_constraints(const Transition&, const unsigned);

        protected:
            bool integer_params;

        public:
            // Parametric operations
            virtual void compute_rc() const;
            virtual PResult* init_result(bool) const;
    
            // Create new symbolic states
            static VSCPar* init(const Job&);

            // Restrict using parametric constraints
            virtual bool restriction(const PResult&);

            virtual Polyhedron convergence_domain() const;

            // From PWNode
            virtual PWNode* copy(const Instruction*) const;

            PWNode* predecessor() const; 

            cvalue minval(const Transition*, bool&, bool&, cvalue&) const;
            cvalue maxval(const Transition*, bool&, bool&, cvalue&) const;

            virtual void update_tsize();

            // Control
            virtual PResult* update_result(const GraphNode*, PResult*) const;
            virtual SuccInfo* add_succ(GraphNode*, const Transition*, PState*, GraphNode*) const;

            ~VSCPar();

            friend class VSCPoly;
    };
}

#endif

