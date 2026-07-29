// 本文件声明 Roméo 风格 exact-forward / priced-backward 混合求解器。

#ifndef TAMONITOR_PTA_MIXED_PRICED_SOLVER_H
#define TAMONITOR_PTA_MIXED_PRICED_SOLVER_H

#include "BackwardPricedSolver.h"
#include "ReachableZoneGraph.h"

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor::pta {

/** 混合算法的完整性状态；前向与后向资源截断必须可区分。 */
enum class MixedSolverStatus {
    Complete,
    Unreachable,
    UnboundedBelow,
    AssumptionRequired,
    IncompleteForwardResourceLimit,
    IncompleteBackwardResourceLimit,
};

/** query 点相对 exact forward reachable space 的归属。 */
enum class ReachabilityMembership {
    Reachable,
    OutsideReachableDomain,
    Unknown,
};

/**
 * 图限定后向推导见证。next_arc 与 successor_node 使离线结果可回放；
 * next_edge 保留与现有纯后向查询相同的稳定边标识。
 */
struct MixedDerivationWitness {
    bool is_goal_seed = false;
    DelayWitnessKind delay_kind = DelayWitnessKind::ZERO;
    std::optional<pardibaal::dim_t> facet_clock;
    std::optional<pardibaal::val_t> facet_bound;
    std::optional<ReachArcId> next_arc;
    std::optional<EdgeId> next_edge;
    std::optional<ReachNodeId> successor_node;
    std::optional<PieceId> successor_piece;
    std::optional<RegionId> successor_unbounded_region;
    bool unbounded_delay = false;
};

/** 价格分片属于一个 reachable graph node，而不是整个 location。 */
struct MixedPricedPiece {
    PieceId id = 0;
    ReachNodeId node = 0;
    LocationId location = 0;
    WeightedZone weighted_zone;
    MixedDerivationWitness witness;
};

/** V=-infinity 的 node-scoped exact DBM 定义域。 */
struct MixedUnboundedRegion {
    RegionId id = 0;
    ReachNodeId node = 0;
    LocationId location = 0;
    pardibaal::DBM zone;
    MixedDerivationWitness witness;
};

struct MixedSolverStatistics {
    std::size_t goal_seeds = 0;
    SolverStatistics backward;
    std::uint64_t forward_elapsed_ms = 0;
    std::uint64_t backward_elapsed_ms = 0;
    std::uint64_t total_elapsed_ms = 0;
};

struct MixedCostToGoResult {
    ReachabilityMembership reachable_domain = ReachabilityMembership::Unknown;
    CostToGoResult cost;
    std::optional<ReachNodeId> reachable_node;
    std::optional<ReachArcId> next_arc;
    std::optional<EdgeId> next_edge;
    std::optional<MixedDerivationWitness> witness;
};

/**
 * exact reachable graph 上的不可变 priced-backward 快照。同一 location 可有
 * 多个重叠 reachable nodes；query 在所有覆盖 valuation 的 node 上取 V
 * 的点态最小值（等价于 W 的最大值）。
 */
class MixedAnalysisSnapshot {
public:
    MixedAnalysisSnapshot();

    [[nodiscard]] MixedSolverStatus status() const noexcept;
    [[nodiscard]] bool exact() const noexcept;
    [[nodiscard]] bool lower_bound_assumed() const noexcept;
    [[nodiscard]] const MixedSolverStatistics& statistics() const noexcept;
    [[nodiscard]] const ReachabilitySnapshot* reachability() const noexcept;
    [[nodiscard]] const std::vector<MixedPricedPiece>& pieces(
        ReachNodeId node) const;
    [[nodiscard]] const std::map<ReachNodeId, std::vector<MixedPricedPiece>>&
    all_pieces() const noexcept;
    [[nodiscard]] const std::vector<MixedUnboundedRegion>&
    unbounded_regions() const noexcept;
    [[nodiscard]] MixedCostToGoResult query(
        LocationId location,
        const RationalValuation& valuation) const;

private:
    struct Impl;
    std::shared_ptr<const Impl> impl_;

    explicit MixedAnalysisSnapshot(std::shared_ptr<const Impl> impl);
    friend MixedAnalysisSnapshot solve_mixed(
        const WeightedAutomatonView&,
        const ReachabilitySnapshot&,
        const CostModel&,
        const SolverOptions&);
};

/**
 * 仅当 reachability.exact() 为真时运行后向固定点。options.timeout_ms
 * 表示 forward+backward 的共享总预算，已用的 forward elapsed 会被扣除。
 */
[[nodiscard]] MixedAnalysisSnapshot solve_mixed(
    const WeightedAutomatonView& automaton,
    const ReachabilitySnapshot& reachability,
    const CostModel& costs = CostModel{},
    const SolverOptions& options = SolverOptions{});

/** 默认 rate=1、edge cost=0 的便捷入口。 */
[[nodiscard]] MixedAnalysisSnapshot solve_mixed(
    const WeightedAutomatonView& automaton,
    const ReachabilitySnapshot& reachability,
    const SolverOptions& options);

[[nodiscard]] std::string to_string(MixedSolverStatus status);
[[nodiscard]] std::string to_string(ReachabilityMembership membership);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_MIXED_PRICED_SOLVER_H
