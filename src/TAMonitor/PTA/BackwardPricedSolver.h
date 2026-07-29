// 本文件声明 Parrot--Lime Algorithm 1 的后向 priced-DBM 求解器及离线查询接口。

#ifndef TAMONITOR_PTA_BACKWARD_PRICED_SOLVER_H
#define TAMONITOR_PTA_BACKWARD_PRICED_SOLVER_H

#include "PTATypes.h"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor::pta {

using LocationId = std::uint32_t;
using PieceId = std::uint64_t;
using RegionId = std::uint64_t;

struct EdgeId {
    LocationId source = 0;
    std::uint32_t ordinal = 0;

    friend bool operator==(const EdgeId& lhs, const EdgeId& rhs) noexcept {
        return lhs.source == rhs.source && lhs.ordinal == rhs.ordinal;
    }

    friend bool operator<(const EdgeId& lhs, const EdgeId& rhs) noexcept {
        return lhs.source < rhs.source ||
               (lhs.source == rhs.source && lhs.ordinal < rhs.ordinal);
    }
};

struct WeightedLocation {
    LocationId id;
    pardibaal::DBM invariant;
    std::string name;

    WeightedLocation(
        LocationId location_id,
        pardibaal::DBM location_invariant,
        std::string location_name = {});
};

struct WeightedEdge {
    EdgeId id;
    LocationId source;
    LocationId target;
    pardibaal::DBM guard;
    std::vector<pardibaal::dim_t> resets;
    std::string label;

    WeightedEdge(
        EdgeId edge_id,
        LocationId source_location,
        LocationId target_location,
        pardibaal::DBM edge_guard,
        std::vector<pardibaal::dim_t> reset_clocks,
        std::string edge_label = {});
};

/**
 * MoniTAal TA 的独立只读快照。EdgeId 由 source location 与其局部序号组成，
 * 因而不依赖 vector 地址，能稳定写入离线 fuzzing 表。
 */
class WeightedAutomatonView {
public:
    WeightedAutomatonView(
        pardibaal::dim_t dimension,
        LocationId initial_location,
        std::vector<WeightedLocation> locations,
        std::vector<WeightedEdge> edges);

    [[nodiscard]] pardibaal::dim_t dimension() const noexcept;
    [[nodiscard]] LocationId initial_location() const noexcept;
    [[nodiscard]] const std::vector<WeightedLocation>& locations() const noexcept;
    [[nodiscard]] const std::vector<WeightedEdge>& edges() const noexcept;
    [[nodiscard]] const WeightedLocation& location(LocationId id) const;
    [[nodiscard]] const WeightedEdge& edge(std::size_t index) const;
    [[nodiscard]] const WeightedEdge& edge(const EdgeId& id) const;
    [[nodiscard]] const std::vector<std::size_t>& incoming_edge_indices(LocationId id) const;
    [[nodiscard]] const std::vector<std::size_t>& outgoing_edge_indices(LocationId id) const;

private:
    pardibaal::dim_t dimension_;
    LocationId initial_location_;
    std::vector<WeightedLocation> locations_;
    std::vector<WeightedEdge> edges_;
    std::map<LocationId, std::size_t> location_index_;
    std::map<EdgeId, std::size_t> edge_index_;
    std::map<LocationId, std::vector<std::size_t>> incoming_edges_;
    std::map<LocationId, std::vector<std::size_t>> outgoing_edges_;
};

struct CostModel {
    BigInt default_location_rate = 1;
    BigInt default_edge_cost = 0;
    std::map<LocationId, BigInt> location_rates;
    std::map<EdgeId, BigInt> edge_costs;

    [[nodiscard]] BigInt location_rate(LocationId location) const;
    [[nodiscard]] BigInt edge_cost(const EdgeId& edge) const;
    [[nodiscard]] bool is_nonnegative_for(const WeightedAutomatonView& automaton) const;
};

struct GoalSpec {
    std::vector<LocationId> locations;
};

struct DerivationWitness {
    bool is_goal_seed = false;
    DelayWitnessKind delay_kind = DelayWitnessKind::ZERO;
    std::optional<pardibaal::dim_t> facet_clock;
    std::optional<pardibaal::val_t> facet_bound;
    std::optional<EdgeId> next_edge;
    std::optional<PieceId> successor_piece;
    std::optional<RegionId> successor_unbounded_region;
    bool unbounded_delay = false;
};

struct PricedPiece {
    PieceId id = 0;
    LocationId location = 0;
    WeightedZone weighted_zone;
    DerivationWitness witness;
};

/** V=-infinity 的精确 DBM 定义域；与有限 weighted pieces 分开保存。 */
struct UnboundedRegion {
    LocationId location;
    pardibaal::DBM zone;
    DerivationWitness witness;
    RegionId id = 0;
};

enum class SolverStatus {
    Complete,
    Unreachable,
    UnboundedBelow,
    AssumptionRequired,
    ResourceLimit,
};

enum class CostValueKind {
    Finite,
    PositiveInfinity,
    NegativeInfinity,
    Unknown,
};

struct SolverOptions {
    std::size_t max_pieces = 1'000'000;
    std::uint64_t timeout_ms = 300'000;
    bool assume_lower_bounded = false;
    bool enable_subsumption = true;
};

struct SolverStatistics {
    std::size_t enqueued = 0;
    std::size_t accepted = 0;
    std::size_t subsumed = 0;
    std::size_t action_predecessors = 0;
    std::size_t time_predecessor_pieces = 0;
    std::size_t unbounded_regions = 0;
    std::size_t dominance_checks = 0;
    std::size_t dominance_unknown = 0;
    std::uint64_t elapsed_ms = 0;
};

struct CostToGoResult {
    CostValueKind kind = CostValueKind::Unknown;
    BigRational value = BigRational(0);
    bool attained = false;
    bool exact = false;
    bool lower_bound_assumed = false;
    SolverStatus solver_status = SolverStatus::ResourceLimit;
    std::optional<PieceId> piece_id;
    std::optional<RegionId> unbounded_region_id;
    std::optional<EdgeId> next_edge;
    std::optional<DerivationWitness> witness;
};

/**
 * 不可变分析快照。项目目前使用 C++17，因此 pieces() 返回 const vector&；
 * 其只读语义等价于计划中的 std::span。
 */
class AnalysisSnapshot {
public:
    AnalysisSnapshot();

    [[nodiscard]] SolverStatus status() const noexcept;
    [[nodiscard]] bool exact() const noexcept;
    [[nodiscard]] bool lower_bound_assumed() const noexcept;
    [[nodiscard]] const SolverStatistics& statistics() const noexcept;
    [[nodiscard]] const std::vector<PricedPiece>& pieces(LocationId location) const;
    [[nodiscard]] const std::map<LocationId, std::vector<PricedPiece>>& all_pieces() const noexcept;
    [[nodiscard]] const std::vector<UnboundedRegion>& unbounded_regions() const noexcept;
    [[nodiscard]] CostToGoResult query(
        LocationId location,
        const RationalValuation& valuation) const;

private:
    struct Impl;
    std::shared_ptr<const Impl> impl_;

    explicit AnalysisSnapshot(std::shared_ptr<const Impl> impl);
    friend AnalysisSnapshot solve(
        const WeightedAutomatonView&,
        const GoalSpec&,
        const CostModel&,
        const SolverOptions&);
};

[[nodiscard]] AnalysisSnapshot solve(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const CostModel& costs = CostModel{},
    const SolverOptions& options = SolverOptions{});

/** 使用默认 rate=1、edge cost=0 的论文算法便捷入口。 */
[[nodiscard]] AnalysisSnapshot solve(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const SolverOptions& options);

[[nodiscard]] std::string to_string(SolverStatus status);
[[nodiscard]] std::string to_string(CostValueKind kind);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_BACKWARD_PRICED_SOLVER_H
