#include "TAMonitor.h"

#include "Fixpoint.h"
#include "Monitor.h"
#include "state.h"

#include <chrono>
#include <stdexcept>
#include <vector>

namespace tamonitor {

namespace {

std::string finite_status_to_verdict(monitaal::single_monitor_answer_e pos, monitaal::single_monitor_answer_e neg) {
    if (pos == monitaal::OUT && neg == monitaal::OUT) {
        return "INCONCLUSIVE";
    }
    if (pos == monitaal::OUT) {
        return "NEGATIVE";
    }
    if (neg == monitaal::OUT) {
        return "POSITIVE";
    }
    return "INCONCLUSIVE";
}

template<class state_t>
class FiniteSingleMonitor {
public:
    explicit FiniteSingleMonitor(const monitaal::TA& automaton)
        : automaton_(automaton),
          accepting_space_(monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(
              monitaal::Fixpoint<monitaal::symbolic_state_t>::accept_states(automaton), automaton)) {
        state_t init(automaton_.initial_location(), automaton_.number_of_clocks());
        init.intersection(accepting_space_);
        if (init.is_empty()) {
            status_ = monitaal::OUT;
        } else {
            status_ = monitaal::ACTIVE;
            states_.push_back(init);
        }
    }

    monitaal::single_monitor_answer_e input(const monitaal::timed_input_t& input) {
        std::vector<state_t> next_states;
        const bool observable = input.label != "" && automaton_.labels().find(input.label) != automaton_.labels().end();

        for (auto state : states_) {
            state.delay(input.time);
            if (!state.satisfies(automaton_.locations().at(state.location()).invariant())) {
                continue;
            }
            state.restrict(automaton_.locations().at(state.location()).invariant());

            if (!observable) {
                add_if_alive(state, next_states);
                continue;
            }

            for (const auto& edge : automaton_.edges_from(state.location())) {
                if (edge.label() != input.label) {
                    continue;
                }
                auto candidate = state;
                if (candidate.do_transition(edge) &&
                    candidate.satisfies(automaton_.locations().at(edge.to()).invariant())) {
                    candidate.restrict(automaton_.locations().at(edge.to()).invariant());
                    add_if_alive(candidate, next_states);
                }
            }
        }

        states_ = std::move(next_states);
        status_ = states_.empty() ? monitaal::OUT : monitaal::ACTIVE;
        return status_;
    }

    bool accepts_now() const {
        for (const auto& state : states_) {
            if (automaton_.locations().at(state.location()).is_accept()) {
                return true;
            }
        }
        return false;
    }

    size_t state_count() const {
        return states_.size();
    }

    monitaal::single_monitor_answer_e status() const {
        return status_;
    }

private:
    void add_if_alive(state_t& state, std::vector<state_t>& next_states) {
        state.intersection(accepting_space_);
        if (!state.is_empty()) {
            next_states.push_back(state);
        }
    }

    const monitaal::TA automaton_;
    const monitaal::symbolic_state_map_t<monitaal::symbolic_state_t> accepting_space_;
    std::vector<state_t> states_;
    monitaal::single_monitor_answer_e status_ = monitaal::OUT;
};

template<class state_t>
RunResult run_infinite_typed(const BuildPair& build, const std::vector<TimedEvent>& trace) {
    monitaal::Monitor<state_t> monitor(build.positive.automaton, build.negative.automaton);
    RunResult result;
    monitaal::monitor_answer_e answer = monitor.status();
    size_t positive_states = monitor.positive_state_estimate().size();
    size_t negative_states = monitor.negative_state_estimate().size();

    for (const auto& event : trace) {
        const bool advance_monitor = answer == monitaal::INCONCLUSIVE;
        if (advance_monitor) {
            const monitaal::timed_input_t input(event.time, event.canonical_label);
            answer = monitor.input(input);
            positive_states = monitor.positive_state_estimate().size();
            negative_states = monitor.negative_state_estimate().size();
        }

        StepResult step;
        step.index = result.steps.size() + 1;
        step.time = event.time;
        step.canonical_label = event.canonical_label;
        step.human_label = event.human_label;
        step.verdict = verdict_to_string(answer);
        step.positive_states = positive_states;
        step.negative_states = negative_states;
        step.monitor_advanced = advance_monitor;
        result.steps.push_back(step);
    }
    result.final_verdict = verdict_to_string(monitor.status());
    return result;
}

template<class state_t>
RunResult run_finite_typed(const BuildPair& build, const std::vector<TimedEvent>& trace) {
    FiniteSingleMonitor<state_t> pos(build.positive.automaton);
    FiniteSingleMonitor<state_t> neg(build.negative.automaton);
    RunResult result;
    std::string verdict = finite_status_to_verdict(pos.status(), neg.status());
    size_t positive_states = pos.state_count();
    size_t negative_states = neg.state_count();

    for (const auto& event : trace) {
        const bool advance_monitor = verdict != "POSITIVE" && verdict != "NEGATIVE";
        if (advance_monitor) {
            const monitaal::timed_input_t input(event.time, event.canonical_label);
            const auto pos_status = pos.input(input);
            const auto neg_status = neg.input(input);
            verdict = finite_status_to_verdict(pos_status, neg_status);
            positive_states = pos.state_count();
            negative_states = neg.state_count();
        }

        StepResult step;
        step.index = result.steps.size() + 1;
        step.time = event.time;
        step.canonical_label = event.canonical_label;
        step.human_label = event.human_label;
        step.verdict = verdict;
        step.positive_states = positive_states;
        step.negative_states = negative_states;
        step.monitor_advanced = advance_monitor;
        result.steps.push_back(step);
    }

    if (verdict == "POSITIVE" || verdict == "NEGATIVE") {
        result.final_verdict = verdict;
        return result;
    }

    const bool pos_accepts = pos.accepts_now();
    const bool neg_accepts = neg.accepts_now();
    if (pos_accepts && !neg_accepts) {
        result.final_verdict = "POSITIVE";
    } else if (neg_accepts && !pos_accepts) {
        result.final_verdict = "NEGATIVE";
    } else if (!pos_accepts && !neg_accepts) {
        result.final_verdict = "INCONCLUSIVE";
    } else {
        result.final_verdict = "INCONCLUSIVE";
    }
    return result;
}

}

RunResult run_monitor(const BuildPair& build, const std::vector<TimedEvent>& trace, const Options& options) {
    const auto start = std::chrono::steady_clock::now();
    RunResult result;

    if (options.word_mode == WordMode::Infinite) {
        result = options.state_mode == StateMode::Symbolic
            ? run_infinite_typed<monitaal::symbolic_state_t>(build, trace)
            : run_infinite_typed<monitaal::concrete_state_t>(build, trace);
    } else {
        result = options.state_mode == StateMode::Symbolic
            ? run_finite_typed<monitaal::symbolic_state_t>(build, trace)
            : run_finite_typed<monitaal::concrete_state_t>(build, trace);
    }

    const auto end = std::chrono::steady_clock::now();
    result.monitor_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    return result;
}

}
