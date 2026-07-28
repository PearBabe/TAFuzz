// 本文件声明在线前缀 cost-to-go 运行记录及独立 JSONL 输出接口。

#ifndef TAMONITOR_PTA_PREFIX_COST_OUTPUT_H
#define TAMONITOR_PTA_PREFIX_COST_OUTPUT_H

#include "PrefixCostAnalyzer.h"

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor::pta {

/** 一个 trace 行相对在线 monitor 的求值状态。 */
enum class PrefixRecordStatus {
    Evaluated,
    NotEvaluatedMonitorTerminal,
    GoalAlreadyHit,
};

/** 保留 symbolic timed input 的闭区间；点时间满足 lower==upper。 */
struct PrefixTimestamp {
    BigRational lower = BigRational(0);
    BigRational upper = BigRational(0);
};

/**
 * 单个前缀的不可变运行记录。state/projection 时间由 monitor 适配层测量；
 * PrefixCostAnalyzer 的各阶段时间保存在 result.statistics 中。
 */
struct PrefixCostRecord {
    std::uint64_t prefix_index = 0;
    std::optional<std::uint64_t> input_index;
    std::optional<PrefixTimestamp> timestamp;
    PrefixRecordStatus status = PrefixRecordStatus::Evaluated;
    std::optional<std::uint64_t> terminal_source_prefix;
    std::vector<RuntimeSymbolicState> runtime_states;
    SymbolicCostToGoResult result;
    std::uint64_t state_extraction_us = 0;
    std::uint64_t observer_projection_us = 0;
    std::string diagnostic;
};

/** 整次固定 trace 的在线 prefix 查询结果。 */
struct PrefixCostRun {
    std::string target_automaton;
    PrefixOptimizerBackend optimizer = PrefixOptimizerBackend::Z3;
    std::uint64_t mixed_precompute_us = 0;
    std::vector<PrefixCostRecord> records;
};

/** 输出阶段统计；JSON 编码与文件写入分别计时。 */
struct PrefixCostOutputStatistics {
    std::vector<std::uint64_t> serialization_us;
    std::uint64_t file_write_us = 0;
};

/**
 * 生成 pta_prefix_costs.jsonl 与 pta_prefix_regions.jsonl。
 * serialization_us 只统计内存中的 JSON 编码，不含文件 I/O，因而不会被误当成
 * fuzzing 热路径延迟。
 */
[[nodiscard]] PrefixCostOutputStatistics write_prefix_cost_outputs(
    const std::filesystem::path& output_dir,
    const PrefixCostRun& run);

[[nodiscard]] std::string to_string(PrefixRecordStatus status);
[[nodiscard]] std::string to_string(PrefixOptimizerBackend backend);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_PREFIX_COST_OUTPUT_H
