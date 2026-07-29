#ifndef ROMEO_BACKWARD_MINCOST
#define ROMEO_BACKWARD_MINCOST

#include <list>
#include <map>
#include <set>
#include <utility>

#include <properties.hh>
#include <result.hh>
#include <pwt.hh>
#include <control_reach.hh>

#include <bvzone.hh>

namespace romeo
{
    class PState;
    class Transition;
    struct Job;

    namespace property
    {
        class BackwardMincost: public TemporalProperty
        {
            public:
                BackwardMincost(const SExpression&, const SExpression&, int line);
                virtual PResult* eval(const PState*) const;

                virtual bool has_cost() const;
                virtual bool uses_backward_mincost_zones() const;

                virtual std::string to_string() const;
                virtual const GenericExpression* copy(CTS&) const;
                virtual const GenericExpression* abstract_copy(CTS&, const VarSet&) const;
                virtual const GenericExpression* instantiate(CTS&, const unsigned, const value) const;
                virtual const GenericExpression* eliminate_refs(CTS&, const ref_dict&) const;
        };
    }

}

#endif
