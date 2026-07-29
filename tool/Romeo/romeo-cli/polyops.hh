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

#ifndef ROMEO_POLYOPS_HH
#define ROMEO_POLYOPS_HH

#include <string>
#include <vector>

#include <ppl.hh>

#include <expression.hh>

#define PPL_Polyhedron Parma_Polyhedra_Library::Pointset_Powerset<Parma_Polyhedra_Library::NNC_Polyhedron>
#define PPL_Convex_Polyhedron Parma_Polyhedra_Library::NNC_Polyhedron
#define PPL_Variable Parma_Polyhedra_Library::Variable

#define POLY_COEFFICIENT_MPZ 
#ifdef POLY_COEFFICIENT_MPZ
    #define POLY_COEFFICIENT_TYPE mpz_class
#else
    #define POLY_COEFFICIENT_TYPE int
#endif

namespace romeo
{
    void disjunction_assign(PPL_Polyhedron*,PPL_Polyhedron*); 
    void disjunction_assign_reduce(PPL_Polyhedron*,PPL_Polyhedron*); 
    PPL_Polyhedron* negation(const PPL_Polyhedron*); 

    std::string polyhedron_to_string(PPL_Polyhedron*, std::vector<std::string>, unsigned, unsigned);

    PPL_Polyhedron* integer_hull(const PPL_Polyhedron&);
    PPL_Polyhedron* strictify(const PPL_Polyhedron&);
    PPL_Polyhedron* normalize(const PPL_Polyhedron&);
    PPL_Polyhedron* simplify(const PPL_Polyhedron&);
    PPL_Polyhedron* closure(const PPL_Polyhedron&);

    void integer_hull(PPL_Convex_Polyhedron&, const std::vector<PPL_Variable>&);

    bool point_projection(Expression*, unsigned, unsigned, value&);
}

#endif
