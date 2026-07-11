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

#include "polyhedron.hh"
#include <map>
#include <list>
#include <string>
#include <iostream>
#include <sstream>
#include <sys/time.h>

#include <job.hh>
#include <result.hh>
#include <cts.hh>
#include <property.hh>
#include <color_output.hh>
#include <pstate.hh>

#include <vsstate.hh>
#include <cvsclass_sp.hh>
#include <cvsclass_gp.hh>
#include <cvsclass.hh>
#include <vsclass.hh>
#include <vscpoly.hh>
#include <vscpoly_costs.hh>
#include <vscpar.hh>
#include <vscpar_costs.hh>
#include <vpsclass.hh>
#include <vlsclass.hh>
#include <vzone.hh>
#include <bvzone.hh>
#include <bcvzone.hh>
#include <vszpoly.hh>
#include <vszpoly_costs.hh>
#include <vszpar.hh>

#include <graph_node.hh>

#include <access_expression.hh>
#include <lexpression.hh>
#include <rvalue.hh>

using namespace std;
using namespace romeo;

#include <logger.hh>
romeo::Logger Log;

bool romeo::Job::stop = false;

romeo::Job::Job(const unsigned i, CTS& t, map<string,string>& options): id(i), cts(t), computation_mode(UNSPECIFIED)
{
    // set defaults
    es = ES_DF;
    pw = PASSED_MARKING;
    randomize_succs = false;
    pw_reduce = true;
    no_abstract = false;
    zones = false;
    simulation = false;
    verbose = false;
    quiet = false;
    simplified_result = false;
    utility = false;

    ip = false;
    ih_convergence = false;
    
    bound_normalize = false;
    bn_convergence = false;
    n_bound = 1;

    restrict_test = false;
    restrict_update = false;
    restrict_new = false;

    pdbm = false;
    pdbm_split = false;

    notrace = false;
    abs_time = false;
    timed_trace = false;
    ntraces = 1;

    non_negative_costs = true;
    cost_method = COST_SPLIT;

    is_control = false;
    minimize_read_vars = false;
    max_concretise_rounds = UINT_MAX;
    heuristic_prop = NULL;
    use_heuristic = false;

    hpeu = false;
    hpeu_sc = false;

    explore_unknown = false;

    graph_nodes_inside = true;

    feff = false;

    // add actual values
    this->add_options(options);
}

romeo::Job::Job(const Job& j, CTS& t): 
    id(j.id), 
    cts(t), 
    computation_mode(j.computation_mode), 
    es(j.es), 
    pw(j.pw), 
    randomize_succs(j.randomize_succs), 
    pw_reduce(j.pw_reduce), 
    no_abstract(j.no_abstract), 
    zones(j.zones), 
    simulation(j.simulation), 
    verbose(j.verbose), 
    quiet(j.quiet), 
    simplified_result(j.simplified_result), 
    utility(j.utility), 
    ip(j.ip), 
    ih_convergence(j.ih_convergence), 
    bound_normalize(j.bound_normalize), 
    bn_convergence(j.bn_convergence), 
    n_bound(j.n_bound), 
    restrict_test(j.restrict_test), 
    restrict_update(j.restrict_update), 
    restrict_new(j.restrict_new), 
    pdbm(j.pdbm),
    pdbm_split(j.pdbm_split),
    notrace(j.notrace),
    abs_time(j.abs_time), 
    timed_trace(j.timed_trace), 
    ntraces(j.ntraces), 
    non_negative_costs(j.non_negative_costs), 
    cost_method(j.cost_method), 
    is_control(j.is_control), 
    minimize_read_vars(j.minimize_read_vars), 
    max_concretise_rounds(j.max_concretise_rounds), 
    heuristic_prop(NULL), 
    use_heuristic(j.use_heuristic),
    hpeu(j.hpeu),
    hpeu_sc(j.hpeu_sc),
    explore_unknown(j.explore_unknown),
    graph_nodes_inside(j.graph_nodes_inside),
    feff(j.feff)
{
}




void romeo::Job::add_options(map<string,string>& options)
{
    if (options.find("rs") != options.end())
        randomize_succs = true;

    if (options.find("params") != options.end() && options["params"] == "integer")
        ip = true; 
    
    // shorthand
    if (options.find("ip") != options.end())
        ip = true;

    if (options.find("ihc") != options.end())
    {
        ih_convergence = true;
    }

    if (options.find("exploration") != options.end())
    {
        if (options["exploration"] == "bf")
        {
            es = ES_BF;
        }
    }

    if (options.find("passed") != options.end())
    {
        if (options["passed"] == "eq")
        {
            pw = PASSED_EQ;
        } else if (options["passed"] == "off") {
            pw = PASSED_OFF;
        } else if (options["passed"] == "hash") {
            pw = PASSED_HASH;
        } else if (options["passed"] == "rinc") {
            pw = PASSED_RINC;
        }
    }

    // shorthand
    if (options.find("eq") != options.end())
        pw = PASSED_EQ;

    if (options.find("poly_reduction") != options.end() && options["poly_reduction"] == "off")
        pw_reduce =false;

    // shorthand
    if (options.find("nored") != options.end())
        pw_reduce = false;

    if (options.find("restrict") != options.end())
    {
        restrict_test = true;
        restrict_update = true;

        if (options["restrict"] == "new")
        {
            restrict_update = false;
            restrict_new = true;
        }
    }

    if (options.find("pdbm") != options.end())
    {
        pdbm = true;
        if (options["pdbm"] == "split")
        {
            pdbm_split = true;
        }
    }

    if (options.find("no_abstract") != options.end())
    {
        no_abstract = true;
    }

    if (options.find("zones") != options.end())
    {
        zones = true;
    }

    if (options.find("quiet") != options.end())
    {
        quiet = true;
    }

    if (options.find("verbose") != options.end())
        verbose = true;

    if (options.find("simplify") != options.end())
    {
        simplified_result = true;
    }

    if (options.find("utility") != options.end())
    {
        utility = true;
    }


    if (options.find("bn") != options.end())
    {
        bound_normalize = true;
        // Convert the string to an unsigned;
        stringstream(options["bn"]) >> n_bound;
    }

    if (options.find("bnc") != options.end())
    {
        bn_convergence = true;
        // Convert the string to an unsigned;
        stringstream(options["bnc"]) >> n_bound;
    }

    if (options.find("no_trace") != options.end())
    {
        notrace = true;
    }

    if (options.find("timed_trace") != options.end())
    {
        timed_trace = true;
    }

    if (options.find("absolute") != options.end())
    {
        abs_time =true;
    }

    if (options.find("ntraces") != options.end())
    {
        // Convert the string to an unsigned;
        stringstream(options["ntraces"]) >> ntraces;
    }

    if (options.find("neg_costs") != options.end())
    {
        non_negative_costs = false;
    }

    if (options.find("cost_mode") != options.end())
    {
        if (options["cost_mode"] == "optim")
        {
            cost_method = COST_OPTIM;
        } else if (options["cost_mode"] == "poly") {
            cost_method = COST_POLY;
        } else if (options["cost_mode"] == "split") {
            cost_method = COST_SPLIT;
        } else if (options["cost_mode"] == "global") {
            cost_method = COST_GLOBAL;
        }
    }

    if (options.find("hpa") != options.end())
    {
        hpeu = true;
        if (options["hpa"] == "sc")
        {
            hpeu_sc = true;
        }
    }

    if (options.find("unknown") != options.end() && options["unknown"] == "explore")
    {
        explore_unknown = true;
    }

    if (options.find("nodes") != options.end() && options["nodes"] == "out")
    {
        graph_nodes_inside = false;
    }

    if (options.find("feff") != options.end())
    {
        feff = true;
    }

    if (options.find("cmode") != options.end())
    {
        if (options["cmode"] == "untimed")
        {
            computation_mode = UNTIMED;
        } else if (options["cmode"] == "timed") {
            computation_mode = TIMED;
        } else if (options["cmode"] == "hybrid") {
            computation_mode = HYBRID;
        }
    }
}

void romeo::Job::start() const
{
    stop = false;

    if (id > 0)
        cout << endl;
       
    if (!quiet)
        cout << info_tag(color_output) << highlight(color_output,this->to_string()) << endl;

    this->check_mode();
    this->execute();
}

bool romeo::Job::is_parametric() const
{
    return computation_mode == TIMED_PARAMETRIC || computation_mode == PARAMETRIC;
}

Job::~Job()
{
    delete &cts;
}


romeo::PropertyJob::PropertyJob(const unsigned i, const Property* p, CTS& t, map<string,string>& o): Job(i,t,o), prop(p)
{
    if (zones && !no_abstract)
    {
        bool bounds = true;
        list<Transition>::const_iterator i;
        for (i = t.begin_transitions(); i != t.end_transitions() && bounds; i++)
        {
            bounds = i->max_bounded;
        }
        if (!bounds && (prop->has_params() || t.nparams() > 0))
        {
            cout << warning_tag(color_output) << "Clock zone extrapolation requires bounded parameters: it is now deactivated." << endl;
            no_abstract = true;
        }
    }

    if (!zones)
    {
        // There is a problem with PDBMs so we deactivate this for now
        no_abstract = true;
    }

    if (timed_trace)
    {
        // We need to keep track of the observers
        // if any
        utility = true;
    }

    // Do not abstract if we try to get the values of the clocks
    if (prop->is_clock())
    {
        no_abstract = true;
    }

    // Or if it is control with state classes
    if (prop->is_control() && !zones)
    {
        no_abstract = true;
    }

    is_control = prop->is_control();

    if (cts.has_cost())
    {   
        if (prop->has_cost())
        {
            // Do not abstract if we try to get costs
            no_abstract = true;
            
            // We take as in ES_BF (in front) because the list in sorted by increasing cost
            // and stuff is added in the back
            es = ES_BF;
            
            if (cost_method != COST_SPLIT && cost_method != COST_POLY)
            {
                cout << warning_tag(color_output) << "Cannot use the current cost method for verification: falling back to split for timed, or poly for stopwatches" << endl;
                cost_method = COST_SPLIT;
            }
        } else {
            //if (!is_control)
            //{
            //    with_cost = false;
            //}
        }
    }

    prop->prepare(cts);
    cts.find_constants();
    this->find_cmode();

    // ihc does not work with restrict_update
    // Idem for PDBMs
    if ((ih_convergence || computation_mode == TIMED_PARAMETRIC) && restrict_test)
    {
        restrict_update = false;
        restrict_new = true;
    }

}

romeo::PropertyJob::PropertyJob(const Job& j, CTS& t, const Property* p): Job(j, t), prop(p)
{
}

void romeo::PropertyJob::execute() const
{
    stringstream prop_id;
    prop_id << "__check_prop_" << id;

    // cout << cts << endl;

    Log._start(prop_id.str());
    PState* s = initial_state();
    PResult* r = prop->evaluate(s);
    Log._stop(prop_id.str());

    list<const Transition*> tcontents;
    if (timed_trace)
    {
        r->print_trace = false;

        cout << *r << endl;

        if (!r->trace_contents.empty())
        {
            PState* sx;

            if (has_cost() && computation_mode == TIMED)
            {
                sx = CVSClassG::init(*this);
            } else {
                sx = VSCPar::init(*this);
            }

            // Time only the first trace
            tcontents = *r->trace_contents.begin();
            PWNode* sr = (*r->trace_props.begin())->validate_observers(sx);
            delete sx;

            for (auto t : tcontents)
            {
                sr = sr->successor(t);
                if (sr == NULL)
                {
                    cerr << error_tag(color_output) << "timed trace: impossible successor in replaying trace: " << t->label << endl;
                    exit(1);
                }
            }

            cout << endl << colorize(color_output, "Trace: ", AC_CYAN);
            print_retime(sr, tcontents);
            
            delete sr;
        } else {
            cout << endl << colorize(color_output, "No trace.", AC_CYAN) << endl;
        }
    } else {
        cout << *r << endl;
        if (!notrace)
        {
            cout << endl << r->get_trace() << endl;
        }
    }


    delete r;
    delete s;

    if (verbose)
    {
        cout << info_tag(color_output) << Log.times(prop_id.str()) << endl;
#ifndef NO_RUSAGE
        cout << info_tag(color_output) << Log.memory(prop_id.str()) << endl;
#endif
    }

    //Log.print();
    Log.clear();
}

string romeo::PropertyJob::to_string() const
{
    stringstream s;
    s << "Checking " << prop->to_string();

    return s.str();
}

bool romeo::PropertyJob::has_params() const
{
    return prop->has_params();
}

bool romeo::PropertyJob::has_time() const
{
    return prop->has_time();
}

bool romeo::PropertyJob::has_cost() const
{
    return prop->has_cost();
}

bool romeo::PropertyJob::uses_backward_mincost_zones() const
{
    return prop->uses_backward_mincost_zones();
}

PropertyJob::~PropertyJob()
{
    delete prop;
}

void romeo::Job::find_cmode()
{
    if (computation_mode == UNSPECIFIED)
    {
        if (cts.has_time())
        {
            computation_mode = TIMED;
        } else {
            computation_mode = UNTIMED;
        }

        if (cts.has_hybrid())
        {
            computation_mode = HYBRID;
        }
    }
    
    if (has_time() && computation_mode == UNTIMED)
    {
        computation_mode = TIMED;
    }
    
    if ((cts.has_params() || has_params()) && computation_mode != PARAMETRIC)
    {
        if (computation_mode == HYBRID)
        {
            computation_mode = PARAMETRIC;
        } else {
            computation_mode = TIMED_PARAMETRIC;
        }
    }
}

romeo::SimulationJob::SimulationJob(const unsigned i,
                                    const std::vector<std::pair<const Transition*, const LExpression*>*>& s, 
                                    CTS& t,
                                    map<string,string>& o): Job(i,t,o), sequence(s)
{
    // Disable state class abstraction
    no_abstract = true;

    // Simulation mode
    simulation = true;

    this->find_cmode();
}

string romeo::SimulationJob::to_string() const
{
    stringstream s;

    //cout << cts << endl;

    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;
    bool comma = false;

    if (!quiet)
    {
        if (sequence.empty())
        {
            s << "Printing initial state";
        } else {
            for (i=sequence.begin(); i!=sequence.end(); i++)
            {
                const Transition* t = (*i)->first;
                const Expression* e = (*i)->second;
            
                if (comma)
                    s << ", ";
                else {
                    s << "Firing "; 
                    comma = true;
                }

                s << t->label;
                if (e)
                    s << " @ " << e->to_string();
            }
        }
    }

    return s.str();
}


void romeo::SimulationJob::execute() const
{
    // cout << cts << endl;

    PWNode* s = initial_state();
    PWNode* r;
    
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;
    
    bool comma = false;
    string prefix = "";
    for (i=sequence.begin(); i!=sequence.end() && s != NULL; i++)
    {
        const Transition* t = (*i)->first;
        const LExpression* e = (*i)->second;
        
        r = s;
        s = s->successor(t,e);
        if (s == NULL)
        {
            cerr << error_tag(color_output) << t->label << " is not firable"; 
            if (prefix!="")
            {
                cerr << " after " << prefix;
            } 
            cerr << endl;
            
            r->deallocate_();
        } else {
            if (comma)
                prefix += ", ";
            else
                comma = true;

            prefix += t->label;
            if (e)
               prefix += " @ " + e->to_string();
        }
    }

    if (s != NULL)
    {
        PState* state = static_cast<PState*>(s);
        cout << colorize(color_output,state->to_string(), AC_CYAN) << endl;
        if (!quiet)
        {
            if (cts.nparams()>0)
            {
                cout << info_tag(color_output) << "Parametric reachability condition: "<< endl << state->reach_cond()->to_string() << endl;
            }

            cout << info_tag(color_output) << "Enabled: " << state->enabled_string(false) << endl;
            cout << info_tag(color_output) << "Firable: " << state->enabled_string(true) << endl;
        }

        s->deallocate_();
        //const PWNode * r = s;
        //while (r != NULL)
        //{
        //    const PWNode * rp = r->parent_node();
        //    r->deallocate();
        //    r = rp;
        //}
    }
}

bool romeo::SimulationJob::has_params() const
{
    bool r = false;
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        const LExpression* e = (*i)->second;
        if (e != NULL)
            r = r || e->has_params();
    }
    
    return r;
}

bool romeo::SimulationJob::has_time() const
{
    bool r = false;
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        const LExpression* e = (*i)->second;
        if (e != NULL)
            r = true;
    }
    
    return r;
}

bool romeo::SimulationJob::has_cost() const
{
    return cts.has_cost();   
}

SimulationJob::~SimulationJob()
{
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        delete *i;
    }
}

void Job::check_mode() const
{
    if (verbose)
    {
        cout << info_tag(color_output) << "Computation mode is ";

        switch (computation_mode)
        {
            case UNTIMED:
                cout << "discrete only";
                break;
            case TIMED:
                cout << "time";
                break;
            case HYBRID:
                cout << "hybrid";
                break; 
            case TIMED_PARAMETRIC:
                cout << "time with parameters";
                if (pdbm)
                {
                    if (pdbm_split) {
                        cout << " with split parametric DBMs";
                    } else {
                        cout << " with parametric DBMs";
                    } 
                }
                break; 
            case PARAMETRIC:
                cout << "hybrid with parameters";
                break;
            default:
                cout << endl << error_tag(color_output) << "Unknown!" << endl;
                exit(1);
        }
        cout << endl;

        if (computation_mode == TIMED_PARAMETRIC || computation_mode == PARAMETRIC)
        {
            cout << info_tag(color_output) << "Parameters are ";
            if (ip)
            {
                cout << "integer-valued";
            } else {
                cout << "real-valued";
            }
            cout << endl;
        }

        for (list<Parameter>::const_iterator k=cts.begin_parameters(); k != cts.end_parameters(); k++)
        {
            cvalue v;
            if (k->constant(v))
            {
                cout << info_tag(color_output) << "Parameter " << k->label << " must be equal to " << v << endl;
            }
        }

        cout << info_tag(color_output) << "Convergence method is ";
        if ((has_cost() && zones))
        {
            if (pw != PASSED_EQ)
            {
                cout << "inclusion plus reverse inclusion." << endl;
            } else {
                cout << "equality." << endl;
            }
        } else {
            switch (pw)
            {
                case PASSED_EQ: 
                    cout << "equality." << endl;
                    break;
                case PASSED_INC: 
                    cout << "inclusion." << endl;
                    break;
                case PASSED_MARKING: 
                    cout << "merge on common markings." << endl;
                    break;
                case PASSED_OFF:
                    cout << "off." << endl;
                    break;
                case PASSED_HASH:
                    cout << "merge with hash table." << endl;
                    break;
                case PASSED_RINC:
                    cout << "inclusion plus reverse inclusion." << endl;
                    break;
            }
        }
    }

    // Diagnostics
    if (!simulation && !quiet)
    {
        if (computation_mode == HYBRID|| computation_mode == PARAMETRIC)
        {
            cout << warning_tag(color_output) << "Transition speeds different from 1: no (theoretical) termination guarantee" << endl;
        }

        if (computation_mode == TIMED_PARAMETRIC || computation_mode == PARAMETRIC)
        {
            if (!ip && !ih_convergence)
            {
                cout << warning_tag(color_output) << "Real-valued parameters: no (theoretical) termination guarantee" << endl;
            } else {
                if (!cts.params_bounded())
                {
                    if (ip)
                    {
                        cout << warning_tag(color_output) << "Integer-valued parameters but not bounded: no (theoretical) termination guarantee" << endl;
                    } else {
                        cout << warning_tag(color_output) << "Convergence using integer hulls but parameters are not bounded: no (theoretical) termination guarantee" << endl;
                    }
                }
            }
        }
    }
}

PState* Job::initial_state() const
{
    PState * s = NULL;

    switch (computation_mode)
    {
        case UNSPECIFIED:
            cerr << error_tag(color_output) << "Unknown computation mode." << endl;
            exit(1);
        case UNTIMED:
            s = VSState::init(*this);
            break;
        case TIMED:
            if (zones)
            {
                if (uses_backward_mincost_zones())
                {
                    s = BVZone::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing zones (for backward mincost)." << endl;
                    }
                } else if (has_cost())
                {
                    s = BCVZone::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing zones (for optimal control)." << endl;
                    }
                } else {
                    s = VZone::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing zones." << endl;
                    }
                }
            } else {
                if (has_cost()) {
                    switch (cost_method)
                    {
                        case COST_SPLIT:
                            s = CVSClassSp::init(*this);
                            if (verbose)
                            {
                                cout << info_tag(color_output) << "Computing cost simple state classes (splitting)." << endl;
                            }
                            break;
                        case COST_OPTIM:
                            s = CVSClass::init(*this);
                            if (verbose)
                            {
                                cout << info_tag(color_output) << "Computing cost state classes." << endl;
                            }
                            break;
                        case COST_GLOBAL:
                            s = CVSClassG::init(*this);
                            if (verbose)
                            {
                                cout << info_tag(color_output) << "Computing global cost state classes." << endl;
                            }
                            break;
                        case COST_POLY:
                            s = CVSCPoly::init(*this);
                            if (verbose)
                            {
                                cout << info_tag(color_output) << "Computing polyhedral cost state classes." << endl;
                            }
                            break;
                    }
                } else {
                    s = VSClass::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing state classes." << endl;
                    }
                }
            }
            break;
        case HYBRID:
            if (zones)
            {
                if (has_cost())
                {
                    s = CVSZPoly::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing polyhedra with explicit clock semantics and costs." << endl;
                    }
                } else {
                    s = VSZPoly::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing polyhedra for explicit clock semantics." << endl;
                    }
                }
            } else {
                if (has_cost()) {
                    if (is_control)
                    {
                        cerr << error_tag(color_output) << "No optimal control with state classes for now." << endl;
                        exit(1);
                    } else {
                        s = CVSCPoly::init(*this);
                        if (verbose)
                        {
                            cout << info_tag(color_output) << "Computing polyhedral cost state classes." << endl;
                        }
                    }
                } else {
                    s = VSCPoly::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing polyhedral state classes." << endl;
                    }
                }
            }

            break;
        case TIMED_PARAMETRIC:
            if (zones || is_control)
            {
                s = VSZPar::init(*this);
                if (verbose)
                {
                    cout << info_tag(color_output) << "Computing polyhedra for explicit clock semantics and parameters." << endl;
                }
            } else {
                if (has_cost()) {
                    s = CVSCPar::init(*this);
                    if (verbose)
                    {
                        cout << info_tag(color_output) << "Computing polyhedral parametric state classes." << endl;
                    }
                } else {
                    // non-split PDBMs are deactivated with integer hulls for now
                    if (pdbm && (!(ip || ih_convergence) || pdbm_split))
                    // if (pdbm)
                    {
                        if (cts.nparams() > 1)
                        {
                            if (pdbm_split)
                            {
                                s = VLSClass<Polyhedron>::init(*this);
                                if (verbose)
                                {
                                    cout << info_tag(color_output) << "Computing parametric DBM state classes with splits." << endl;
                                }
                            } else {
                                s = VPSClass<Polyhedron>::init(*this);
                                if (verbose)
                                {
                                    cout << info_tag(color_output) << "Computing parametric DBM state classes." << endl;
                                }
                            }
                        } else {
                            if (pdbm_split)
                            {
                                s = VLSClass<PInterval>::init(*this);
                                if (verbose)
                                {
                                    cout << info_tag(color_output) << "Computing parametric DBM state classes with splits and one parameter." << endl;
                                }
                            } else {
                                s = VPSClass<PInterval>::init(*this);
                                if (verbose)
                                {
                                    cout << info_tag(color_output) << "Computing parametric DBM state classes with one parameter." << endl;
                                }
                            }
                        }
                    } else {
                        s = VSCPar::init(*this);
                        if (verbose)
                        {
                            cout << info_tag(color_output) << "Computing polyhedral parametric state classes." << endl;
                        }
                    }
                }
            }
            break;

        case PARAMETRIC:
            if (zones)
            {
                s = VSZPar::init(*this);
            } else {
                if (has_cost()) {
                    if (is_control)
                    {
                        s = VSZPar::init(*this);
                    } else {
                        s = CVSCPar::init(*this);
                    }
                } else {
                    s = VSCPar::init(*this);
                }
            }
            break;
    }
    return s;
}

bool Job::uses_backward_mincost_zones() const
{
    return false;
}

// ============================ Retiming =====================================

romeo::RetimeJob::RetimeJob(const unsigned i,
                            const std::vector<std::pair<const Transition*, const LExpression*>*>& s, 
                            CTS& t,
                            map<string,string>& o): Job(i,t,o), sequence(s)
{
    // Disable state class abstraction
    no_abstract = true;

    // Retime mode
    simulation = true;

    this->find_cmode();
}

string romeo::RetimeJob::to_string() const
{
    stringstream s;

    //cout << cts << endl;

    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;
    bool comma = false;

    if (!quiet)
    {
        if (sequence.empty())
        {
            s << "No sequence to retime";
        } else {
            for (i=sequence.begin(); i!=sequence.end(); i++)
            {
                const Transition* t = (*i)->first;
                const Expression* e = (*i)->second;
            
                if (comma)
                    s << ", ";
                else {
                    s << "Retiming "; 
                    comma = true;
                }

                s << t->label;
                if (e)
                    s << " @ " << e->to_string();
            }
        }
    }

    return s.str();
}


list<pair<const Transition*, pair<cvalue,cvalue> > > romeo::Job::retime_arbitrary(PWNode* s0) const
{
    PWNode* s = s0->copy();
    list<pair<const Transition*, pair<cvalue,cvalue> > > result;
    while (s->parent_node() != NULL)
    {
        const Transition* tf = s->in_transition();

        VSCPar * r = static_cast<VSCPar*>(static_cast<VSCPar*>(s)->predecessor());

        bool ls, rs, lb, rb;
        cvalue lv, rv, ld, rd;
        
        lv = r->minval(tf, ls, lb, ld);
        rv = r->maxval(tf, rs, rb, rd);

        // By default, we choose the earliest firing date within the class
        cvalue datep = lv;
        cvalue dateq = ld;

        if (ls)
        {
            // If that earliest date is strict, it cannot be chosen
            if (rb)
            {
                // There is a finite upper bound: try (lv + 1) / ld
                if (rd*lv + rd < rv*ld || (rd*lv + rd == ld*rv && !rs))
                {
                    datep = lv + 1;
                    dateq = ld;
                } else {
                    // So we have to choose in ]lv/ld,rv/rd[ which is of length <1: 
                    // choose the middle of the (rd*lv + ld*rv) / 2ld*rd
                    datep = rd*lv + ld*rv;
                    dateq = 2*ld*rd;
                }
            } else {
                // If there is no upper bound, just take (lv + 1)/ld
                datep = lv + 1;
                dateq = ld;
            }
        }

        cvalue g = gcd(datep, dateq);
        datep = datep / g;
        dateq = dateq / g;

        result.push_front(pair<const Transition*, pair<cvalue,cvalue> >(tf, pair<cvalue,cvalue>(datep, dateq)));
    
        r->update_firing_date(tf, new lexpression::Litteral(datep, -1), dateq);

        delete s;
        s = r;
    }

    cvalue absdatep = 0;
    cvalue absdateq = 1;

    auto it = result.begin();
    while (it != result.end())
    {
        const cvalue datep = it->second.first;
        const cvalue dateq = it->second.second;

        if (!it->first->utility)
        {
            // We use this if we want absolute time
            // for the trace or we have to accumulate
            // delays due to utility transitions not
            // being displayed
            if (abs_time || absdatep != 0)
            {
                // Add the current relative time
                absdatep = dateq*absdatep + absdateq*datep;
                absdateq = absdateq*dateq;

                // Simplify
                cvalue g = gcd(absdatep,absdateq);
                absdatep = absdatep / g; 
                absdateq = absdateq / g; 

                // The date printed will be absolute
                it->second.first  = absdatep;
                it->second.second = absdateq;

                if (!abs_time)
                {
                    // We have used the accumulated delay
                    // due to utility transitions so we 
                    // can reset it
                    absdatep = 0;
                    absdateq = 1;
                }
            }

            it++;
        } else {
            // Add the current relative time
            // Utility transition: accumulate its delay
            absdatep = dateq*absdatep + absdateq*datep;
            absdateq = absdateq*dateq;

            // remove this utility transition from the result
            it = result.erase(it); 
        }
    }

    return result;
}

void romeo::RetimeJob::execute() const
{
    PWNode* s;
    PWNode* r;
    
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    if (has_cost() && computation_mode == TIMED)
    {
        s = CVSClassG::init(*this);
    } else {
        s = VSCPar::init(*this);
    }

    list<const Transition*> seq;

    bool comma = false;
    string prefix = "";
    for (i=sequence.begin(); i!=sequence.end() && s != NULL; i++)
    {
        const Transition* t = (*i)->first;
        const LExpression* e = (*i)->second;
        
        seq.push_back(t);

        r = s;
        s = s->successor(t,e);
        if (s == NULL)
        {
            cerr << error_tag(color_output) << t->label << " is not firable"; 
            if (prefix!="")
            {
                cerr << " after " << prefix;
            } 
            cerr << endl;
            
            r->deallocate_();
        } else {
            if (comma)
            {
                prefix += ", ";
            } else {
                comma = true;
            }

            prefix += t->label;
            if (e)
            {
                prefix += " @ " + e->to_string();
            }
        }
    }
    print_retime(s, seq);
}

list<pair<const Transition*, pair<cvalue, cvalue> > > Job::retime_optimal(PWNode* s, const list<const Transition*>& seq) const
{
    vector<Avalue> V(seq.size() + 1, 0);
    
    static_cast<CVSClassG*>(s)->minvals(V);
    
    vector<Avalue>::iterator j = V.begin();
    // Ignore first value: 0 
    j++;

    list<pair<const Transition*, pair<cvalue, cvalue> > > result;
    
    Avalue rel_time = 0;
    for (auto i : seq)
    {
        result.push_back(pair<const Transition*, pair<cvalue, cvalue> >(i, pair<cvalue, cvalue>((*j - rel_time).value(), 1)));
        if (!abs_time)
        {
            rel_time = (*j);
        }
        j++;
    }

    return result;
}

void Job::print_retime(PWNode* s, const list<const Transition*>& seq) const
{
    if (s != NULL)
    {
        list<pair<const Transition*, pair<cvalue, cvalue> > > r;

        if (has_cost() && computation_mode == TIMED)
        {
            r = retime_optimal(s, seq);
        } else {
            if (has_cost())
            {
                cout << warning_tag(color_output) << "the given schedule might not be optimal for stopwatches or parameters." << endl;
            }
            r = retime_arbitrary(s);
        }

        stringstream st;
        if (r.empty())
        {
             st << "the result is obtained in the initial state.";
        } else {
            bool comma = false;
            for (auto x: r)
            {
                if (comma) {
                    st << ", ";
                } else {
                    comma = true;
                }
                
                st << x.first->label << "@" << x.second.first;
                if (x.second.second != 1)
                {
                    st << "/" << x.second.second;
                } 
            }
        }
        
        cout << colorize(color_output,st.str(), AC_CYAN) << endl;
    }
}

bool romeo::RetimeJob::has_params() const
{
    bool r = false;
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        const LExpression* e = (*i)->second;
        if (e != NULL)
            r = r || e->has_params();
    }
    
    return r;
}

bool romeo::RetimeJob::has_time() const
{
    bool r = false;
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        const LExpression* e = (*i)->second;
        if (e != NULL)
            r = true;
    }
    
    return r;
}

bool romeo::RetimeJob::has_cost() const
{
    return cts.has_cost();   
}

RetimeJob::~RetimeJob()
{
    std::vector<std::pair<const Transition*, const LExpression*>*>::const_iterator i;

    for (i=sequence.begin(); i!=sequence.end(); i++)
    {
        delete *i;
    }
}

// ============================ Graph computation =====================================

romeo::GraphJob::GraphJob(const unsigned i,
                            CTS& t,
                            map<string,string>& o): Job(i,t,o)
{
    // Disable state class abstraction
    no_abstract = !zones;

    cts.find_constants();
    this->find_cmode();
}

string romeo::GraphJob::to_string() const
{
    stringstream s;

    if (!quiet)
    {
        s << "Computing the (symbolic) graph.";
    }

    return s.str();
}

void romeo::GraphJob::execute() const
{
    PState* s = initial_state();
    GraphNode* initg = GraphNode::build_graph(s);

    GraphNode::export_graphviz(initg);
}


bool romeo::GraphJob::has_params() const
{
    return false;
}

bool romeo::GraphJob::has_time() const
{
    return false;
}

bool romeo::GraphJob::has_cost() const
{
    return false;
}

GraphJob::~GraphJob()
{
}
