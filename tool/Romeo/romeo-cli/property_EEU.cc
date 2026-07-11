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

struct VSitem
{
    VarSet vars;
    list<string> trace;

    VSitem(const VarSet& vs): vars(vs), trace() {};
    VSitem(const VarSet& vs, const list<string>& t): vars(vs), trace(t) {};

};

struct cmpvs
{
    bool operator()(const VSitem& a, const VSitem& b) const
    {
        return (a.vars.size() < b.vars.size()) || (a.vars.size() == b.vars.size() && a.vars < b.vars);
    }
};

typedef set<VSitem, cmpvs> VSSet;

bool property::EEU::concretise(const Job& job, const VarSet& finit, VarSet& f, list<string>& trace) const
{
    if (job.verbose)
    {
        cout << "--------------------------------------------------------------------------------" << endl;
        cout << "start concretise with variables: ";
        for (VarSet::iterator iv = finit.begin(); iv != finit.end(); iv++)
        {
            cout << *iv << " ";
        }
        cout << endl;
    }
    
    set<VarSet> psets;
    PResult* r = NULL;;
    bool bigger;
    bool included = true;;

    VSSet W;

    list<string> last_trace;
    list<list<string> > last_traces;

    set<const Variable*> Sall;
    for (auto& vs: job.cts.variables)
    {
        Sall.insert(&vs);
    }

    //for (list<Transition>::const_iterator i=job.cts.begin_transitions(); i!= job.cts.end_transitions(); i++)
    //{
    //    VarSet St, Str, St_int, St_union;
    //    i->writes(St);

    //    set_intersection(St.begin(), St.end(), finit.begin(), finit.end(), inserter(St_int, St_int.begin())); // Intersection of S and St
    //    // Keep only transitions that write the set of variables of interest
    //    // Add all their dependencies
    //    if (!St_int.empty())
    //    {
    //        i->reads(Str);
    //        set_union(Str.begin(), Str.end(), f.begin(), f.end(), inserter(St_union, St_union.begin()));
    //        f = St_union;
    //    }
    //}

    W.insert(VSitem(f));

    unsigned nrounds = 0;
    do
    {
        VSSet::iterator ivs = W.begin();
        VSitem vsi = *ivs;
        W.erase(ivs);

        // f = vsi.vars;
        last_trace = vsi.trace;

        if (job.verbose)
        {
            cout << "concretise with variables: ";
            for (auto v : vsi.vars)
            {
                cout << v << " ";
            }
            cout << endl;
        }

        bigger = true;
        included = true;

        list<const Transition*> T;
        f.clear();
        job.cts.writing_trans_with_reads(vsi.vars, f, T);
        CTS* abs_cts = new CTS(job.cts, f, T);
        
        const CostEU_EEU* p = new CostEU_EEU(phi.abstract_copy(*abs_cts, f), psi.abstract_copy(*abs_cts, f), init, -1);

        PropertyJob j(job, *abs_cts, p);
        j.minimize_read_vars = true;
        j.ntraces = 1;

        PState* st = j.initial_state();
        if (job.verbose)
        {
            cout << "=> Verify " << *p << endl;
            //cout << " on: " << endl<<  *abs_cts << endl;
            cout << *st << endl;
        }


        PWNode* s = NULL;
        if (r != NULL && !r->empty())
        {
            PWNode* sprev;
            list<const Transition*> L = abs_cts->adapt_trace_ids(last_trace);

            // Test the previous trace in this augmented CTS
            s = st->copy();
            for (list<const Transition*>::iterator it = L.begin(); it != L.end() && s != NULL; it++)
            {
                sprev = s;
                s = s->successor(*it, NULL);
                delete sprev;
            }
            
            if (s == NULL)
            {
                // The previous trace does not work anymore
                // But I still use its transitions preferentially
                for (list<list<string> >::iterator itt = last_traces.begin(); itt != last_traces.end(); itt++)
                {
                    list<const Transition*> L = abs_cts->adapt_trace_ids(*itt);
                    for (list<const Transition*>::iterator it = L.begin(); it != L.end(); it++)
                    {
                        //if ((*it)->abs_vars.empty())
                        {
                            const_cast<Transition*>(*it)->prefval = 1;
                        }
                    }
                }
                
                list<const Transition*> L = abs_cts->adapt_trace_ids(last_trace);
                for (list<const Transition*>::iterator it = L.begin(); it != L.end(); it++)
                {
                    const_cast<Transition*>(*it)->prefval = 1;
                }
            }

            delete r;
        }

        if (s == NULL)
        {
            // The previous trace does not work anymore
            CTS::current_cts = abs_cts;
            r = p->eval(st);
            CTS::current_cts = &job.cts;

            if (job.verbose)
            {
                cout << "raw result: " << *r << endl;
                cout << r->get_trace() << endl;
            }

            if (!r->empty())
            {
                // Add to S the variables read on the trace
                //VarSet Snew = f;
                //bool added = r->best_trace_reads(Snew, job.cts);
                //r->first_trace_reads(Strace, job.cts);
                last_trace = r->first_trace_ids();
                last_traces.clear();
                for (list<list<const Transition*> >::iterator itt =  r->trace_contents.begin(); 
                                                              itt != r->trace_contents.end() && bigger; itt++)
                {
                    VarSet Strace;
                    PResult::trace_reads(*itt, Strace, job.cts);
                    last_traces.push_back(PResult::trace_ids(*itt));

                    // Sdiff = Strace - S
                    VarSet Sdiff;
                    set_difference(Strace.begin(), Strace.end(), f.begin(), f.end(), inserter(Sdiff, Sdiff.begin()));
                    
                    if (!Sdiff.empty())
                    {
                        //VarSet Sunion;
                        // Sunion = S U Sdiff
                        //set_union(f.begin(), f.end(), Sdiff.begin(), Sdiff.end(), inserter(Sunion, Sunion.begin()));
                        //set_union(f.begin(), f.end(), Snew.begin(), Snew.end(), inserter(Sunion, Sunion.begin()));

                        //VarSet Sunion2;
                        //set_union(finit.begin(), finit.end(), Strace.begin(), Strace.end(), inserter(Sunion2, Sunion2.begin()));
                        ////if (Sunion2 < Sunion)
                        //if (Sunion2.size() < Sunion.size() && !psets.count(Sunion2))
                        //{
                        //    if (job.verbose)
                        //    {
                        //        cout << "------------------ restart ----------------------" << endl;
                        //    }
                        //    psets.insert(Sunion2);
                        //    f = Sunion2;
                        //} else {
                          //f = Sunion;
                          //W.insert(VSitem(Sunion, PResult::trace_ids(*itt)));
                        //}

                        //for (VarSet::iterator iv = Sdiff.begin(); iv != Sdiff.end(); iv ++)
                        //{
                        //    VarSet f2 = f;
                        //    f2.insert(*iv);
                        //    W.insert(VSitem(f2, PResult::trace_ids(*itt)));
                        //}
                        VarSet Sunion;
                        // Sunion = S U Sdiff
                        set_union(f.begin(), f.end(), Sdiff.begin(), Sdiff.end(), inserter(Sunion, Sunion.begin()));
                        W.insert(VSitem(Sunion, PResult::trace_ids(*itt)));
                    } else {
                        // else no new reads -> terminate with true   
                        bigger = false;
                    }
                }
            } else {
                // else we may need to add more transitions
                // check if we have more variables (due to read variables for added transitions) than expected
                VarSet g;
                for (auto vs: abs_cts->variables)
                {
                    auto as = Sall.begin(); 
                    while (as != Sall.end() && (*as)->id != vs.id)
                    {
                        as++;
                    }

                    included = (included && vsi.vars.count((*as)->get_coffset()));
                    g.insert((*as)->get_coffset());
                }

                if (!included)
                {
                    if (job.verbose)
                    {
                        cout << "false but not included" << endl;
                    }
                    W.insert(VSitem(g));
                }

            }
        } else {
            // The previous trace still works
            // But now we are complete
            if (job.verbose)
            {
                cout << "reused the previous trace" << endl;
            }
            r = new CostResult(s->min_cost(), false); // !undef
            delete s;
        }

        //cout << "---------------------------------------------------------" << endl;
        //cout << *abs_cts << endl;
        //cout << j << endl;
        if (job.verbose)
        {
            cout << *r << endl;
            cout << r->get_trace() << endl;
        }

        delete st;
        nrounds++;
    } while ((nrounds <= job.max_concretise_rounds && bigger && !r->empty() && !W.empty()) || !included);
  
    bool res = !r->empty();
    delete r;

    if (res)
    {
        trace = last_trace;
    }

    return res;
}

// -----------------------------------------------------------------------
property::EEU::EEU(const SExpression& l, const SExpression& r, int line): TemporalProperty(l, r, line) {}

struct Partition
{
    VarSet init_vars;
    VarSet vars;
    bool update;
    list<string> trace;

    Partition(const VarSet& v, bool u): init_vars(v), vars(v), update(u), trace() {} 
    Partition(const VarSet& v, bool u, const list<string>& t): init_vars(v), vars(v), update(u), trace(t) {} 
};

PResult* property::EEU::eval(const PState* s) const
{
    Log.start("EEU");
    init = s;

    const Job& job = s->job;

    list<VarSet> Lvs = psi.var_reads();

    //VarSet prev_vs;
    //const PWNode* current = s;
    //while (current->in_transition() != NULL)
    //{
    //    current->in_transition()->reads(prev_vs);
    //    current = current->parent_node();
    //}

    list<Partition> facets;

    for (list<VarSet>::iterator is = Lvs.begin(); is != Lvs.end(); is++)
    {
    //    VarSet Sunion;
    //    set_union(is->begin(), is->end(), prev_vs.begin(), prev_vs.end(), inserter(Sunion, Sunion.begin()));
    //    facets.push_back(Partition(Sunion, true));
        facets.push_back(Partition(*is, true));
    }

    bool update = true;

    bool res = true;
    while (update && res)
    {
        list<Partition>::iterator i = facets.begin();
        while (i != facets.end() && res)
        {
            //cout << "====================================================================================" << endl;
            
            if (i->update)
            {
                res = concretise(job, i->init_vars, i->vars, i->trace);
                i->update = false;
            }

            //cout << " -> " << res << endl;
            i++;
        }

        update = false;
        i = facets.begin();
        while (i != facets.end())
        {
            list<Partition>::iterator j = i;
            j++; 
            while (j != facets.end())
            {
                VarSet Sint;
                set_intersection(i->vars.begin(), i->vars.end(), j->vars.begin(), j->vars.end(), inserter(Sint, Sint.begin()));
                if (!Sint.empty())
                {
                    VarSet Sunion;
                    set_union(i->vars.begin(), i->vars.end(), j->vars.begin(), j->vars.end(), inserter(Sunion, Sunion.begin()));
                    
                    i->vars = Sunion;
                    i->update =  true;
                    i->trace.clear();
                    update = true;

                    j = facets.erase(j);
                } else {
                    j++;
                }
            }
            i++;
        }
    }
    
    PBool * final_result = new PBool(res);
    final_result->trace = NULL;
    //final_result->trace = r->trace;
    //final_result->compute_trace(job.utility, orig_prop);
    
    if (res)
    {
        final_result->multipart = true;
        list<Partition>::iterator i;
        for (i = facets.begin(); i != facets.end(); i++)
        {
            final_result->trace_contents.push_back(job.cts.adapt_trace_ids(i->trace));
            final_result->ntraces++;
        }
    }



    Log.stop("EEU");
    return final_result;
}

string property::EEU::to_string() const
{
    stringstream s;

    s << "EF (" << psi.to_string() << ") (lazy)";

    return s.str();
}

const GenericExpression* property::EEU::copy(CTS& t) const
{
    return new property::EEU(phi.copy(t), psi.copy(t), decl_line);
}

const GenericExpression* property::EEU::abstract_copy(CTS& t, const VarSet& S) const
{
    return new property::EEU(phi.abstract_copy(t, S), psi.abstract_copy(t, S), decl_line);
}

const GenericExpression* property::EEU::instantiate(CTS& t, const unsigned i, const value v) const
{
    return new property::EEU(phi.instantiate(t, i, v), psi.instantiate(t, i, v), decl_line);
}

const GenericExpression* property::EEU::eliminate_refs(CTS& t, const ref_dict& d) const
{
    return new property::EEU(phi.eliminate_refs(t, d), psi.eliminate_refs(t, d), decl_line);
}

