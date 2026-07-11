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

#ifndef ROMEO_SLDBM_HH
#define ROMEO_SLDBM_HH

#include <dbm.hh>
#include <valuation.hh>

namespace romeo
{
    class SLDBM
    {
      private:
        DBMUnion root;
        std::vector<std::vector<cvalue>> periods;

      public:
        SLDBM(const DBMUnion&);
        SLDBM(const unsigned);
        SLDBM(const SLDBM&);

        SLDBM& operator=(const SLDBM&);

        unsigned dimension() const;

        void constrain(const unsigned, const unsigned, const time_bound);
    
        void future();
        void past();
        void reset(const unsigned);
        void free_clock(const unsigned);

        SLDBM remove_dimensions(const std::vector<unsigned>&);
        void remap(unsigned[], unsigned);

        std::string to_string() const;
        std::string to_string_labels(const std::vector<std::string>& labels) const;
    
        relation_type compare(const SLDBM&) const;
        relation_type relation(const SLDBM&) const;

        time_bound& operator() (const unsigned, const unsigned) const;
        bool is_empty() const;
    
        virtual ~SLDBM();
    };
}

#endif
