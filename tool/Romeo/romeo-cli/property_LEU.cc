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

#include <cstdlib>
#include <sstream>
#include <string>

#include <properties.hh>
#include <pwt.hh>
#include <result.hh>
#include <dresult.hh>
#include <cts.hh>
#include <pstate.hh>
#include <variable.hh>

using namespace romeo;
using namespace std;

#include <logger.hh> 
extern romeo::Logger Log;

// -----------------------------------------------------------------------
property::LEU::LEU(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line) {}

PResult* property::LEU::eval(const PState* s) const
{
    Log.start("LEU");

    const Job& job = s->job;
    CTS* cts= new CTS(job.cts);
    const Property* p = new CostEU(phi.copy(*cts), psi.copy(*cts), decl_line);

    PropertyJob j(job, *cts, p);
    j.heuristic_prop = new EEU(phi.copy(*cts), psi.copy(*cts), decl_line);
    j.minimize_read_vars = true;
    j.use_heuristic = true;

    PState* st = j.initial_state();

    PResult* r = p->eval(st);
    
    Log.stop("LEU");
    return r;
}

string property::LEU::to_string() const
{
    stringstream s;

    s << "EF (" << psi.to_string() << ") with global invariant (" << phi.to_string() << ") (lazy guided)";

    return s.str();
}

const GenericExpression* property::LEU::copy(CTS& t) const
{
    return new property::LEU(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::LEU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::LEU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::LEU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::LEU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::LEU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::LEU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}

