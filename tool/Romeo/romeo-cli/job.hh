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

#ifndef ROMEO_JOB_HH
#define ROMEO_JOB_HH

#include <vector>
#include <list>
#include <utility>
#include <string>
#include <map>

#include <printable.hh>
#include <cts.hh>


namespace romeo
{
    class PState;
    class Property;
    class Transition;
    class LExpression;
    class CTS;
    class PWT;
    class PWNode;

    enum expl_strategy { ES_BF, ES_DF };
    enum passed_strategy { PASSED_EQ, PASSED_INC, PASSED_MARKING, PASSED_HASH, PASSED_OFF, PASSED_RINC };
    enum cost_strategy { COST_POLY, COST_OPTIM, COST_GLOBAL, COST_SPLIT };
    enum cmode: uint8_t { UNSPECIFIED, UNTIMED, TIMED, HYBRID, TIMED_PARAMETRIC, PARAMETRIC }; 
    
    struct Job: public Printable
    {
        protected:
            std::list<std::pair<const Transition*, std::pair<cvalue, cvalue> > > retime_arbitrary(PWNode*) const;
            std::list<std::pair<const Transition*, std::pair<cvalue, cvalue> > > retime_optimal(PWNode*, const std::list<const Transition*>&) const;
            void print_retime(PWNode*, const std::list<const Transition*>&) const;

        public:
            static bool stop;
            const unsigned id;

            CTS& cts;

            cmode computation_mode;

            expl_strategy es;
            passed_strategy pw;

            bool randomize_succs;   // randomly shuffle the successors
            bool pw_reduce;         // try to reduce stored unions of polyhedra or zones
            bool no_abstract;       // to do perform the time abstraction for state classes (keep only diagonals)
            bool zones;             // do the computation with the TA abstraction instead of state classes
            bool simulation;        // simulation mode (to do some specific stuff)
            bool verbose;           // print more info
            bool quiet;             // print only the results
            bool simplified_result; // compute the result by removing the initial param constraints: give only what is new
            bool utility;           // keep utility transitions
            
            bool ip;                // integer hull: preserves only integers
            bool ih_convergence;    // integer hull: only for convergence - dense over-approx

            // use an arbitrary bound (n_bound below) for the coeffs of polyhedra
            bool bound_normalize;   // modify the states
            bool bn_convergence;    // only convergence
            unsigned n_bound;       // the bound for bn stuff

            // remove already known parameter values from exploration
            bool restrict_test;
            bool restrict_update;   
            bool restrict_new;

            bool pdbm;              // Use parametric DBMs instead of generic polyhedra
            bool pdbm_split;        // Use parametric DBMs with splitting so that each cell has only one linear expression

            bool notrace;
            bool abs_time;          // give the retiming with absolute dates instead of relative delays
            bool timed_trace;       // Ask for a timed trace
            unsigned ntraces;       // Max number of traces

            bool non_negative_costs;
            cost_strategy cost_method;

            bool is_control;        // Are we verifying a control property?

            bool minimize_read_vars; // For lazy EU, do we try to minimize the number of variables that are read along the path?
            unsigned max_concretise_rounds; // For lazy EU, how many rounds shall we try to concretise
            const Property* heuristic_prop; // For heuristics, which property to evaluate to find the heuristic
            bool use_heuristic; // whether to compute heuristics for states

            bool hpeu;
            bool hpeu_sc;

            bool explore_unknown; // Explore transitions with guards evaluating to unknown

            bool graph_nodes_inside; // Put nodes inside the graph

            bool feff; // Use FEFF for transitions instantiated through a syntax for loop
                                  
            Job(const unsigned,CTS&, std::map<std::string,std::string>&);
            Job(const Job&, CTS&);

            void add_options(std::map<std::string,std::string>&);
            void check_mode() const;
            void start() const;
            void find_cmode();
            PState* initial_state() const;


            virtual void execute() const = 0;
            virtual bool has_params() const = 0;
            virtual bool has_time() const = 0;
            virtual bool has_cost() const = 0;
            virtual bool uses_backward_mincost_zones() const;

            bool is_parametric() const;

            virtual ~Job();
    };

    struct PropertyJob: public Job
    {
        const Property* prop;
        
        PropertyJob(const unsigned, const Property*, CTS&, std::map<std::string,std::string>&);
        PropertyJob(const Job&, CTS&, const Property*);

        virtual void execute() const;
        virtual bool has_params() const;
        virtual bool has_time() const;
        virtual bool has_cost() const;
        virtual bool uses_backward_mincost_zones() const;

        virtual std::string to_string() const;
        
        virtual ~PropertyJob();
    };

    struct SimulationJob: public Job
    {
        std::vector<std::pair<const Transition*, const LExpression*>*> sequence;
        SimulationJob(const unsigned,
                      const std::vector<std::pair<const Transition*, const LExpression*>*>&, 
                      CTS&,
                      std::map<std::string,std::string>&);

        virtual void execute() const;
        virtual bool has_params() const;
        virtual bool has_time() const;
        virtual bool has_cost() const;

        virtual std::string to_string() const;
        virtual ~SimulationJob();
    };

    struct RetimeJob: public Job
    {
        std::vector<std::pair<const Transition*, const LExpression*>*> sequence;
        RetimeJob(const unsigned,
                      const std::vector<std::pair<const Transition*, const LExpression*>*>&, 
                      CTS&,
                      std::map<std::string,std::string>&);

        virtual void execute() const;
        virtual bool has_params() const;
        virtual bool has_time() const;
        virtual bool has_cost() const;

        virtual std::string to_string() const;
        virtual ~RetimeJob();
    };

    struct GraphJob: public Job
    {
        std::vector<std::pair<const Transition*, const LExpression*>*> sequence;
        GraphJob(const unsigned,
                      CTS&,
                      std::map<std::string,std::string>&);

        virtual void execute() const;
        virtual bool has_params() const;
        virtual bool has_time() const;
        virtual bool has_cost() const;

        virtual std::string to_string() const;
        virtual ~GraphJob();
    };


}

#endif
