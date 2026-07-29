// 本文件声明在线前缀 symbolic Federation 的精确 cost-to-go 查询与 witness 接口。

#ifndef TAMONITOR_PTA_PREFIX_COST_ANALYZER_H
#define TAMONITOR_PTA_PREFIX_COST_ANALYZER_H

#include "AffineOptimizer.h"
#include "MixedPricedSolver.h"

#include <pardibaal/Federation.h>

#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor::pta {

enum class SymbolicDomainStatus {
    Complete,
    GoalAlreadyHit,
    NoLiveState,
    OutsideReachableDomain,
    DomainMismatch,
    IncompleteSnapshot,
    IncompleteQuery,
    Unknown,
};

enum class NegativeInfinityCause {
    None,
    PointwiseSuffix,
    RuntimeDomainAggregate,
};

struct RuntimeSymbolicState {
    std::uint64_t runtime_state_id = 0;
    LocationId location = 0;
    pardibaal::Federation semantic_domain;
};

struct PrefixQueryOptions {
    PrefixOptimizerBackend optimizer = PrefixOptimizerBackend::Z3;
    std::uint64_t timeout_ms = 10;
    std::size_t max_regions = 100'000;
    bool materialize_witness = true;
};

struct PrefixQueryStatistics {
    std::size_t runtime_states = 0;
    std::size_t runtime_dbms = 0;
    std::size_t reachable_nodes_considered = 0;
    std::size_t piece_intersections = 0;
    std::size_t candidates = 0;
    std::size_t unbounded_candidates = 0;
    std::size_t optimizer_calls = 0;
    std::size_t cache_hits = 0;
    std::uint64_t filtering_us = 0;
    std::uint64_t intersection_us = 0;
    std::uint64_t optimizer_us = 0;
    std::uint64_t witness_us = 0;
    std::uint64_t core_query_us = 0;
};

struct MaterializedDelayWitness {
    std::optional<BigRational> value_or_limit;
    bool attained = false;
    bool epsilon_optimal = false;
    bool replay_checked = false;
    bool replay_valid = false;
    std::string diagnostic;
};

struct SymbolicCostCandidate {
    std::uint64_t runtime_state_id = 0;
    std::size_t runtime_dbm_index = 0;
    ReachNodeId reachable_node = 0;
    PieceId piece_id = 0;
    pardibaal::DBM domain;
    WeightedZone affine_weight;
    MixedDerivationWitness witness;
    AffineSupremum supremum;
    bool cost_attained = false;
    MaterializedDelayWitness delay;

    SymbolicCostCandidate(
        std::uint64_t state_id,
        std::size_t dbm_index,
        ReachNodeId node,
        PieceId piece,
        pardibaal::DBM candidate_domain,
        WeightedZone candidate_weight,
        MixedDerivationWitness candidate_witness);
};

struct SymbolicUnboundedCandidate {
    std::uint64_t runtime_state_id = 0;
    std::size_t runtime_dbm_index = 0;
    ReachNodeId reachable_node = 0;
    RegionId region_id = 0;
    pardibaal::DBM domain;
    MixedDerivationWitness witness;
};

struct SymbolicCostToGoResult {
    SymbolicDomainStatus domain_status = SymbolicDomainStatus::Unknown;
    CostToGoResult aggregate;
    NegativeInfinityCause negative_infinity_cause =
        NegativeInfinityCause::None;
    std::vector<SymbolicCostCandidate> candidates;
    std::vector<SymbolicUnboundedCandidate> unbounded_candidates;
    std::optional<RationalValuation> optimizer_or_limit;
    bool optimizer_is_actual = false;
    std::optional<BigRational> delay_value_or_limit;
    bool delay_attained = false;
    std::optional<std::uint64_t> runtime_state_id;
    std::optional<std::size_t> runtime_dbm_index;
    std::optional<ReachNodeId> reachable_node;
    std::optional<PieceId> piece_id;
    std::optional<ReachArcId> next_arc;
    std::optional<EdgeId> next_edge;
    std::optional<MixedDerivationWitness> witness;
    PrefixQueryStatistics statistics;
    std::string diagnostic;
};

/**
 * 不可变 prefix query service。automaton/costs 用于 witness 回放；mixed
 * snapshot 继续负责离线 priced pieces 和 exact reachable graph。
 */
class PrefixCostAnalyzer {
public:
    PrefixCostAnalyzer(
        WeightedAutomatonView automaton,
        CostModel costs,
        MixedAnalysisSnapshot snapshot);

    [[nodiscard]] SymbolicCostToGoResult query(
        const std::vector<RuntimeSymbolicState>& states,
        const PrefixQueryOptions& options = PrefixQueryOptions{}) const;

    [[nodiscard]] const WeightedAutomatonView& automaton() const noexcept;
    [[nodiscard]] const CostModel& costs() const noexcept;
    [[nodiscard]] const MixedAnalysisSnapshot& snapshot() const noexcept;

private:
    WeightedAutomatonView automaton_;
    CostModel costs_;
    MixedAnalysisSnapshot snapshot_;
    std::map<LocationId, std::vector<ReachNodeId>> nodes_by_location_;
    std::map<LocationId, pardibaal::Federation> support_by_location_;
    std::map<PieceId, const MixedPricedPiece*> pieces_by_id_;
    std::map<LocationId, std::vector<const MixedUnboundedRegion*>>
        unbounded_by_location_;
};

[[nodiscard]] std::string to_string(SymbolicDomainStatus status);
[[nodiscard]] std::string to_string(NegativeInfinityCause cause);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_PREFIX_COST_ANALYZER_H
