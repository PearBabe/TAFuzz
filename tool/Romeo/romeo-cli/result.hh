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

#ifndef ROMEO_RESULT_HH
#define ROMEO_RESULT_HH

#include <set>
#include <string>
#include <list>

#include <polyhedron.hh>
#include <printable.hh>
#include <variable.hh>

enum approx_t { RES_OVER, RES_UNDER, RES_EXACT, RES_UNKNOWN, RES_OVER_INT, RES_UNDER_INT, RES_INT } ;

namespace romeo
{    
    // Forward declarations
    class PWNode;
    class Transition;
    class Property;
    class CTS;

    class PResult: public Printable
    {
        public:
            PWNode* trace;
            static const CTS* cts;
            std::list<std::list<const Transition*> > trace_contents;
            std::list<const Property*> trace_props;

            bool multipart;
            bool print_trace;

            unsigned ntraces;

            bool unknown;
            approx_t apx;

        public:
            virtual PResult& conjunction(const PResult&) = 0;
            virtual PResult& disjunction(const PResult&) = 0;
            virtual PResult& negation() = 0;
            virtual PResult* copy() const = 0;
            virtual Polyhedron constraint() const;
            virtual bool empty() const = 0;
            virtual bool universe() const = 0;
            virtual bool equals(const PResult&) = 0;
            virtual bool contains(const PResult&) = 0;
            virtual bool intersects(const PResult&) = 0;
            virtual std::string get_trace() const;
            virtual std::string to_string() const = 0;


            void compute_trace(const bool, const Property*);
            void set_trace(PWNode*);
            std::string trace_to_string() const;
            void set_approx(const approx_t);

            static std::list<std::string> trace_ids(const std::list<const Transition*>&);
            std::list<std::string> first_trace_ids() const;

            static void trace_reads(const std::list<const Transition*>&, VarSet&, const CTS&);
            void first_trace_reads(VarSet&, const CTS&) const;
            bool best_trace_reads(VarSet&, const CTS&) const;

            virtual void simplify_with(const PResult&);
            virtual void integer_shape_close_assign();

            bool is_unknown() const;
            void set_unknown(const bool);

            PResult();
            PResult(const PResult&);
            virtual ~PResult();
    };

    class PBool: public PResult
    {
        protected:
            bool val;

        public:
            PBool(bool b=true);
            PBool(const PBool&);
            virtual PResult& conjunction(const PResult&);
            virtual PResult& disjunction(const PResult&);
            virtual PResult& negation();
            virtual PResult* copy() const;
            virtual bool empty() const;
            virtual bool universe() const;
            virtual std::string to_string() const;
            virtual bool equals(const PResult&);
            virtual bool contains(const PResult&);
            virtual bool intersects(const PResult&);
            virtual ~PBool();
    };

    class VSCPar;
    class VSZPar;

    class PRPoly: public PResult
    {
        protected:
            Polyhedron val;

        public:
            PRPoly(unsigned,bool b=true);
            PRPoly(const PRPoly&);
            PRPoly(const Polyhedron&);
            virtual PResult& conjunction(const PResult&);
            virtual PResult& disjunction(const PResult&);
            virtual PResult& negation();
            virtual PResult* copy() const;
            virtual bool empty() const;
            virtual bool universe() const;
            virtual std::string to_string() const;
            virtual bool equals(const PResult&);
            virtual bool contains(const PResult&);
            virtual bool intersects(const PResult&);
            virtual Polyhedron constraint() const;

            virtual ~PRPoly();

            virtual void simplify_with(const PResult&);
            virtual void integer_shape_close_assign();

            friend class VSCPar;
            friend class VSZPar;
            friend class VSSPolyMergeStorage;
    };


}

#endif


