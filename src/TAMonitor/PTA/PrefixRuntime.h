// 本文件声明 finite monitor 到在线 prefix cost-to-go 服务的只读适配层。

#ifndef TAMONITOR_PTA_PREFIX_RUNTIME_H
#define TAMONITOR_PTA_PREFIX_RUNTIME_H

#include "PTAAnalysis.h"
#include "PrefixCostOutput.h"

#include "state.h"

#include <cstdint>
#include <optional>
#include <set>
#include <vector>

namespace tamonitor::pta {

struct PrefixReplaySample {
    std::uint64_t prefix_index = 0;
    std::uint64_t iteration = 0;
    std::uint64_t wall_us = 0;
    std::uint64_t core_us = 0;
    std::uint64_t optimizer_us = 0;
    bool matches_online_result = false;
};

struct PrefixReplayBenchmark {
    PrefixOptimizerBackend backend = PrefixOptimizerBackend::Z3;
    std::uint64_t iterations_per_prefix = 0;
    std::vector<PrefixReplaySample> samples;
};

/**
 * 只读观察 finite monitor 的存活状态。它不参与 verdict；所有查询结果保存到
 * 独立 PrefixCostRun，待监控结束后统一序列化。
 */
class PrefixRuntimeObserver {
public:
    PrefixRuntimeObserver(
        const PTAMixedExecutionResult& mixed,
        PrefixQueryOptions query_options,
        std::uint64_t mixed_precompute_us);

    [[nodiscard]] bool uses_positive_automaton() const noexcept;

    void observe_symbolic(
        std::uint64_t prefix_index,
        std::optional<std::uint64_t> input_index,
        std::optional<PrefixTimestamp> timestamp,
        bool monitor_advanced,
        const std::vector<monitaal::symbolic_state_t>& positive,
        const std::vector<monitaal::symbolic_state_t>& negative);

    void observe_concrete(
        std::uint64_t prefix_index,
        std::optional<std::uint64_t> input_index,
        std::optional<PrefixTimestamp> timestamp,
        bool monitor_advanced,
        const std::vector<monitaal::concrete_state_t>& positive,
        const std::vector<monitaal::concrete_state_t>& negative);

    [[nodiscard]] const PrefixCostRun& run() const noexcept;
    void mark_monitor_terminal(std::uint64_t prefix_index) noexcept;
    [[nodiscard]] PrefixReplayBenchmark benchmark_evaluated_prefixes(
        std::uint64_t iterations_per_prefix) const;

private:
    PrefixCostAnalyzer analyzer_;
    PrefixQueryOptions query_options_;
    PrefixCostRun run_;
    std::set<LocationId> goals_;
    bool goal_hit_ = false;
    std::optional<std::uint64_t> goal_prefix_;
    std::optional<std::uint64_t> terminal_prefix_;

    void append_record(
        std::uint64_t prefix_index,
        std::optional<std::uint64_t> input_index,
        std::optional<PrefixTimestamp> timestamp,
        bool monitor_advanced,
        std::vector<RuntimeSymbolicState> states,
        std::uint64_t extraction_us,
        std::uint64_t projection_us);
};

[[nodiscard]] PrefixOptimizerBackend parse_prefix_optimizer_backend(
    const std::string& name);

void write_prefix_replay_benchmark(
    const std::filesystem::path& output_dir,
    const PrefixReplayBenchmark& benchmark);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_PREFIX_RUNTIME_H
