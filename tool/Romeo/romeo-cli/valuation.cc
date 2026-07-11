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

#include <cstring>
#include <valuation.hh>

romeo::relation_type romeo::compare(const void* A, const void* B, const unsigned size)
{
    const int r = std::memcmp(A,B,size);

    if (r == 0) {
        return EQUAL;
    } else if (r < 0) {
        return LESS;
    } else {
        return GREATER;
    }
}

romeo::cvalue romeo::gcd(romeo::cvalue a, romeo::cvalue b)
{
    // pgcd(a,b) = pgcd(b,a%b)
    while (b != 0)
    {
        cvalue m = a;
        a = b;
        b = m % b;
    }

    return a;
}


// -----------------------------------------------------------------------------

