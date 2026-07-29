// 本文件实现 observer/global clock 投影、Goal latch 与逐前缀在线查询。

#include "PrefixRuntime.h"

#include <chrono>
#include <algorithm>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using Clock = std::chrono::steady_clock;

std::uint64_t elapsed_us(Clock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(Clock::now() - start)
            .count());
}

bool contains_goal(
    const std::vector<RuntimeSymbolicState>& states,
    const std::set<LocationId>& goals) {
    for (const auto& state : states) {
        if (goals.find(state.location) != goals.end() &&
            !state.semantic_domain.is_empty()) {
            return true;
        }
    }
    return false;
}

template <class State>
const std::vector<State>& select_states(
    bool positive,
    const std::vector<State>& positive_states,
    const std::vector<State>& negative_states) {
    return positive ? positive_states : negative_states;
}

}  // namespace

PrefixRuntimeObserver::PrefixRuntimeObserver(
    const PTAMixedExecutionResult& mixed,
    PrefixQueryOptions query_options,
    std::uint64_t mixed_precompute_us)
    : analyzer_(mixed.automaton, mixed.costs, mixed.snapshot),
      query_options_(query_options) {
    run_.target_automaton = mixed.target_automaton;
    run_.optimizer = query_options.optimizer;
    run_.mixed_precompute_us = mixed_precompute_us;
    goals_.insert(mixed.goals.locations.begin(), mixed.goals.locations.end());
}

bool PrefixRuntimeObserver::uses_positive_automaton() const noexcept {
    return run_.target_automaton == "positive";
}

void PrefixRuntimeObserver::append_record(
    std::uint64_t prefix_index,
    std::optional<std::uint64_t> input_index,
    std::optional<PrefixTimestamp> timestamp,
    bool monitor_advanced,
    std::vector<RuntimeSymbolicState> states,
    std::uint64_t extraction_us,
    std::uint64_t projection_us) {
    PrefixCostRecord record;
    record.prefix_index = prefix_index;
    record.input_index = input_index;
    record.timestamp = std::move(timestamp);
    record.runtime_states = std::move(states);
    record.state_extraction_us = extraction_us;
    record.observer_projection_us = projection_us;

    if (!monitor_advanced) {
        record.status = PrefixRecordStatus::NotEvaluatedMonitorTerminal;
        record.terminal_source_prefix = terminal_prefix_;
        record.diagnostic = "monitor verdict was already terminal";
        run_.records.push_back(std::move(record));
        return;
    }
    if (goal_hit_) {
        record.status = PrefixRecordStatus::GoalAlreadyHit;
        record.terminal_source_prefix = goal_prefix_;
        record.result.domain_status = SymbolicDomainStatus::GoalAlreadyHit;
        record.result.aggregate.kind = CostValueKind::Finite;
        record.result.aggregate.value = BigRational(0);
        record.result.aggregate.attained = true;
        record.result.aggregate.exact = true;
        record.result.aggregate.solver_status = SolverStatus::Complete;
        record.diagnostic = "first-hit Goal was reached by an earlier prefix";
        run_.records.push_back(std::move(record));
        return;
    }

    // 首次命中 Goal 仍查询全部状态，以保留同 prefix 的 Goal/非 Goal 候选。
    const bool hits_goal = contains_goal(record.runtime_states, goals_);
    record.result = analyzer_.query(record.runtime_states, query_options_);
    if (hits_goal) {
        // first-hit 语义在本 prefix 终止 suffix；候选仍完整保留供诊断。
        record.result.aggregate.kind = CostValueKind::Finite;
        record.result.aggregate.value = BigRational(0);
        record.result.aggregate.attained = true;
        record.result.aggregate.exact = true;
        record.result.aggregate.solver_status = SolverStatus::Complete;
        record.result.aggregate.piece_id.reset();
        record.result.aggregate.unbounded_region_id.reset();
        record.result.aggregate.next_edge.reset();
        record.result.aggregate.witness.reset();
        record.result.optimizer_or_limit.reset();
        record.result.optimizer_is_actual = true;
        record.result.delay_value_or_limit = BigRational(0);
        record.result.delay_attained = true;
        record.result.runtime_state_id.reset();
        record.result.runtime_dbm_index.reset();
        record.result.reachable_node.reset();
        record.result.piece_id.reset();
        record.result.next_arc.reset();
        record.result.next_edge.reset();
        record.result.witness.reset();
        goal_hit_ = true;
        goal_prefix_ = prefix_index;
    }
    if (record.runtime_states.empty()) {
        terminal_prefix_ = prefix_index;
    }
    run_.records.push_back(std::move(record));
}

void PrefixRuntimeObserver::observe_symbolic(
    std::uint64_t prefix_index,
    std::optional<std::uint64_t> input_index,
    std::optional<PrefixTimestamp> timestamp,
    bool monitor_advanced,
    const std::vector<monitaal::symbolic_state_t>& positive,
    const std::vector<monitaal::symbolic_state_t>& negative) {
    const auto extraction_start = Clock::now();
    const auto& selected = select_states(
        uses_positive_automaton(), positive, negative);
    const auto extraction_time = elapsed_us(extraction_start);

    const auto projection_start = Clock::now();
    std::vector<RuntimeSymbolicState> runtime_states;
    runtime_states.reserve(selected.size());
    const auto expected_dimension = analyzer_.automaton().dimension();
    for (std::size_t index = 0; index < selected.size(); ++index) {
        if (selected[index].is_empty()) continue;
        auto domain = selected[index].federation();
        if (domain.dimension() != expected_dimension + 1) {
            throw std::logic_error(
                "symbolic monitor state has an unexpected observer-clock dimension");
        }
        // MoniTAal 把 observer time 放在最后一维；只在副本上消去。
        domain.remove_clock(expected_dimension);
        runtime_states.push_back(RuntimeSymbolicState{
            static_cast<std::uint64_t>(index),
            selected[index].location(),
            std::move(domain)});
    }
    const auto projection_time = elapsed_us(projection_start);
    append_record(prefix_index, input_index, std::move(timestamp),
                  monitor_advanced, std::move(runtime_states), extraction_time,
                  projection_time);
}

void PrefixRuntimeObserver::observe_concrete(
    std::uint64_t prefix_index,
    std::optional<std::uint64_t> input_index,
    std::optional<PrefixTimestamp> timestamp,
    bool monitor_advanced,
    const std::vector<monitaal::concrete_state_t>& positive,
    const std::vector<monitaal::concrete_state_t>& negative) {
    const auto extraction_start = Clock::now();
    const auto& selected = select_states(
        uses_positive_automaton(), positive, negative);
    std::vector<std::pair<LocationId, monitaal::valuation_t>> extracted;
    extracted.reserve(selected.size());
    for (const auto& state : selected) {
        if (!state.is_empty()) {
            extracted.emplace_back(state.location(), state.valuation());
        }
    }
    const auto extraction_time = elapsed_us(extraction_start);

    const auto projection_start = Clock::now();
    std::vector<RuntimeSymbolicState> runtime_states;
    runtime_states.reserve(extracted.size());
    const auto expected_dimension = analyzer_.automaton().dimension();
    for (std::size_t index = 0; index < extracted.size(); ++index) {
        const auto& values = extracted[index].second;
        if (values.size() != expected_dimension + 1) {
            throw std::logic_error(
                "concrete monitor state has an unexpected global-clock dimension");
        }
        for (pardibaal::dim_t clock = 1; clock < expected_dimension; ++clock) {
            if (values[clock] > static_cast<monitaal::concrete_time_t>(
                    std::numeric_limits<pardibaal::val_t>::max())) {
                throw std::overflow_error(
                    "concrete clock value exceeds Pardibaal DBM range");
            }
        }
        auto point = pardibaal::DBM::zero(expected_dimension);
        for (pardibaal::dim_t clock = 1; clock < expected_dimension; ++clock) {
            point.assign(clock, static_cast<pardibaal::val_t>(values[clock]));
        }
        runtime_states.push_back(RuntimeSymbolicState{
            static_cast<std::uint64_t>(index), extracted[index].first,
            pardibaal::Federation(std::move(point))});
    }
    const auto projection_time = elapsed_us(projection_start);
    append_record(prefix_index, input_index, std::move(timestamp),
                  monitor_advanced, std::move(runtime_states), extraction_time,
                  projection_time);
}

const PrefixCostRun& PrefixRuntimeObserver::run() const noexcept {
    return run_;
}

void PrefixRuntimeObserver::mark_monitor_terminal(
    std::uint64_t prefix_index) noexcept {
    if (!terminal_prefix_.has_value()) terminal_prefix_ = prefix_index;
}

PrefixReplayBenchmark PrefixRuntimeObserver::benchmark_evaluated_prefixes(
    std::uint64_t iterations_per_prefix) const {
    PrefixReplayBenchmark benchmark;
    benchmark.backend = query_options_.optimizer;
    benchmark.iterations_per_prefix = iterations_per_prefix;
    for (const auto& record : run_.records) {
        if (record.status != PrefixRecordStatus::Evaluated) continue;
        for (std::uint64_t iteration = 0;
             iteration < iterations_per_prefix; ++iteration) {
            const auto started = Clock::now();
            const auto result = analyzer_.query(
                record.runtime_states, query_options_);
            const auto wall_us = elapsed_us(started);
            const bool same_kind =
                result.aggregate.kind == record.result.aggregate.kind;
            const bool same_value =
                result.aggregate.kind != CostValueKind::Finite ||
                result.aggregate.value == record.result.aggregate.value;
            const bool matches = same_kind && same_value &&
                result.aggregate.attained == record.result.aggregate.attained;
            if (!matches) {
                throw std::logic_error(
                    "prefix replay benchmark changed online cost semantics");
            }
            benchmark.samples.push_back(PrefixReplaySample{
                record.prefix_index,
                iteration,
                wall_us,
                result.statistics.core_query_us,
                result.statistics.optimizer_us,
                true});
        }
    }
    return benchmark;
}

PrefixOptimizerBackend parse_prefix_optimizer_backend(const std::string& name) {
    if (name == "z3") return PrefixOptimizerBackend::Z3;
    if (name == "romeo-dbm") return PrefixOptimizerBackend::RomeoDBM;
    if (name == "crosscheck") return PrefixOptimizerBackend::CrossCheck;
    throw std::invalid_argument("unknown prefix optimizer backend: " + name);
}

void write_prefix_replay_benchmark(
    const std::filesystem::path& output_dir,
    const PrefixReplayBenchmark& benchmark) {
    std::filesystem::create_directories(output_dir);
    std::ofstream raw(output_dir / "pta_prefix_replay_benchmark.csv");
    raw << "prefix_index,iteration,backend,wall_us,core_us,optimizer_us,match\n";
    std::vector<std::uint64_t> wall;
    wall.reserve(benchmark.samples.size());
    for (const auto& sample : benchmark.samples) {
        raw << sample.prefix_index << ',' << sample.iteration << ','
            << to_string(benchmark.backend) << ',' << sample.wall_us << ','
            << sample.core_us << ',' << sample.optimizer_us << ','
            << (sample.matches_online_result ? "true" : "false") << '\n';
        wall.push_back(sample.wall_us);
    }
    if (!raw) throw std::runtime_error("cannot write prefix replay samples");
    std::sort(wall.begin(), wall.end());
    auto quantile = [&](double value) {
        if (wall.empty()) return std::uint64_t(0);
        return wall[std::min<std::size_t>(
            wall.size() - 1,
            static_cast<std::size_t>(wall.size() * value))];
    };
    std::ofstream summary(output_dir / "pta_prefix_replay_summary.csv");
    summary << "backend,iterations_per_prefix,samples,p50_us,p95_us,p99_us,max_us,mismatches\n"
            << to_string(benchmark.backend) << ','
            << benchmark.iterations_per_prefix << ',' << wall.size() << ','
            << quantile(0.50) << ',' << quantile(0.95) << ','
            << quantile(0.99) << ',' << (wall.empty() ? 0 : wall.back())
            << ",0\n";
    if (!summary) throw std::runtime_error("cannot write prefix replay summary");
}

}  // namespace tamonitor::pta
