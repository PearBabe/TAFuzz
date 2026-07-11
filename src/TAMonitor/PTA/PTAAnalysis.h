// 本文件声明 TAMonitor 到后向 Priced-DBM 求解器的独立适配与报告接口。

#ifndef TAMONITOR_PTA_ANALYSIS_H
#define TAMONITOR_PTA_ANALYSIS_H

#include "BackwardPricedSolver.h"
#include "MixedPricedSolver.h"
#include "TAMonitor.h"

#include <filesystem>
#include <string>

namespace tamonitor::pta {

/** 一次显式 PTA 分析的完整离线结果；不参与在线 verdict 计算。 */
struct PTAExecutionResult {
    std::string target_automaton;
    std::string cost_model_source;
    bool nonnegative_certified = false;
    WeightedAutomatonView automaton;
    CostModel costs;
    GoalSpec goals;
    AnalysisSnapshot snapshot;
    CostToGoResult initial_cost;
    bool geometric_oracle_checked = false;
    bool geometric_oracle_equal = false;
};

/** Roméo-style exact-forward / priced-backward 的独立离线结果。 */
struct PTAMixedExecutionResult {
    std::string target_automaton;
    std::string cost_model_source;
    bool nonnegative_certified = false;
    WeightedAutomatonView automaton;
    CostModel costs;
    GoalSpec goals;
    MixedAnalysisSnapshot snapshot;
    MixedCostToGoResult initial_cost;
    bool geometric_oracle_checked = false;
    bool geometric_oracle_equal = false;
    bool observer_oracle_checked = false;
    bool observer_strict_bound_unreachable = false;
    bool observer_bound_reachable = false;
};

/** 从 BuildPair 选择目标自动机、加载 cost model 并运行 Algorithm 1。 */
[[nodiscard]] PTAExecutionResult run_pta_analysis(
    const BuildPair& build,
    const Options& options);

/** 显式 mixed 模式：先 exact forward graph，完整后再 priced backward。 */
[[nodiscard]] PTAMixedExecutionResult run_mixed_pta_analysis(
    const BuildPair& build,
    const Options& options);

/** 仅在显式启用 PTA 分析时生成 pta_analysis.json/pta_pieces.jsonl。 */
void write_pta_outputs(
    const std::filesystem::path& output_dir,
    const PTAExecutionResult& result);

/** mixed 模式额外生成 reachable nodes/arcs 两个 JSONL。 */
void write_mixed_pta_outputs(
    const std::filesystem::path& output_dir,
    const PTAMixedExecutionResult& result);

/** complete、unreachable 和已证明的 initial -infinity 都是有效分析结果。 */
[[nodiscard]] bool is_successful(const PTAExecutionResult& result) noexcept;
[[nodiscard]] bool is_successful(const PTAMixedExecutionResult& result) noexcept;

} // namespace tamonitor::pta

#endif // TAMONITOR_PTA_ANALYSIS_H
