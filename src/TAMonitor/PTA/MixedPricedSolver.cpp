// 本文件实现 exact reachable-zone graph 上的 FIFO priced-backward 固定点。

#include "MixedPricedSolver.h"

#include "ExactDominance.h"
#include "PricedDBMOps.h"

#include <algorithm>
#include <chrono>
#include <deque>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using Clock = pardibaal::dim_t;

bool is_zero(const BigRational& value) {
    return value.numerator() == 0;
}

WeightedZone zero_weighted_zone(const pardibaal::DBM& zone) {
    return WeightedZone(
        zone,
        BigInt(0),
        std::vector<BigInt>(zone.dimension(), BigInt(0)),
        true);
}

bool timeout_reached(
    const std::chrono::steady_clock::time_point started_at,
    std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return false;
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - started_at);
    return elapsed.count() >= 0 &&
           static_cast<std::uint64_t>(elapsed.count()) >= timeout_ms;
}

std::uint64_t elapsed_milliseconds(
    const std::chrono::steady_clock::time_point started_at) {
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - started_at);
    return static_cast<std::uint64_t>(
        std::max<std::int64_t>(0, elapsed.count()));
}

std::uint64_t remaining_timeout_milliseconds(
    const std::chrono::steady_clock::time_point started_at,
    std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return 0;
    }
    const auto elapsed = elapsed_milliseconds(started_at);
    // ExactDominance 中 0 表示不限时，所以已超时时传 1ms，
    // 外层会在下一个检查点立即停止。
    return elapsed >= timeout_ms ? 1 : timeout_ms - elapsed;
}

std::uint64_t saturating_add(std::uint64_t lhs, std::uint64_t rhs) {
    if (rhs > std::numeric_limits<std::uint64_t>::max() - lhs) {
        return std::numeric_limits<std::uint64_t>::max();
    }
    return lhs + rhs;
}

bool piece_limit_reached(
    const SolverStatistics& statistics,
    std::size_t max_pieces) {
    if (statistics.accepted >= max_pieces) {
        return true;
    }
    return statistics.unbounded_regions >= max_pieces - statistics.accepted;
}

SolverStatus base_status(MixedSolverStatus status) {
    switch (status) {
        case MixedSolverStatus::Complete:
            return SolverStatus::Complete;
        case MixedSolverStatus::Unreachable:
            return SolverStatus::Unreachable;
        case MixedSolverStatus::UnboundedBelow:
            return SolverStatus::UnboundedBelow;
        case MixedSolverStatus::AssumptionRequired:
            return SolverStatus::AssumptionRequired;
        case MixedSolverStatus::IncompleteForwardResourceLimit:
        case MixedSolverStatus::IncompleteBackwardResourceLimit:
            return SolverStatus::ResourceLimit;
    }
    throw std::logic_error("未知 MixedSolverStatus");
}

DerivationWitness base_witness(const MixedDerivationWitness& witness) {
    DerivationWitness result;
    result.is_goal_seed = witness.is_goal_seed;
    result.delay_kind = witness.delay_kind;
    result.facet_clock = witness.facet_clock;
    result.facet_bound = witness.facet_bound;
    result.next_edge = witness.next_edge;
    result.successor_piece = witness.successor_piece;
    result.successor_unbounded_region = witness.successor_unbounded_region;
    result.unbounded_delay = witness.unbounded_delay;
    return result;
}

const WeightedEdge& edge_for_id(
    const WeightedAutomatonView& automaton,
    const std::map<EdgeId, std::size_t>& edge_indices,
    const EdgeId& id) {
    const auto found = edge_indices.find(id);
    if (found == edge_indices.end()) {
        throw std::invalid_argument(
            "reachable graph 的 arc 引用了 automaton 中不存在的 EdgeId");
    }
    return automaton.edge(found->second);
}

void validate_reachability_snapshot(
    const WeightedAutomatonView& automaton,
    const ReachabilitySnapshot& reachability,
    const std::map<EdgeId, std::size_t>& edge_indices) {
    if (!reachability.compatible_with(automaton)) {
        throw std::invalid_argument(
            "reachable graph 与 mixed solver 的 automaton 结构不一致");
    }
    for (const auto& node : reachability.nodes()) {
        if (node.zone.dimension() != automaton.dimension()) {
            throw std::invalid_argument(
                "reachable node 的 DBM dimension 与 automaton 不一致");
        }
        // location() 负责拒绝不存在的 id。
        (void)automaton.location(node.location);
    }

    for (const auto& arc : reachability.arcs()) {
        const auto& source = reachability.node(arc.source);
        const auto& target = reachability.node(arc.target);
        const auto& edge = edge_for_id(automaton, edge_indices, arc.edge);
        if (edge.source != source.location || edge.target != target.location) {
            throw std::invalid_argument(
                "reachable arc 的 graph endpoints 与 automaton edge 不一致");
        }
        if (arc.fire_zone.dimension() != automaton.dimension() ||
            arc.entry_zone.dimension() != automaton.dimension() ||
            arc.post_zone.dimension() != automaton.dimension()) {
            throw std::invalid_argument(
                "reachable arc 的 DBM dimension 与 automaton 不一致");
        }
    }
}

}  // namespace

struct MixedAnalysisSnapshot::Impl {
    pardibaal::dim_t dimension = 1;
    MixedSolverStatus status =
        MixedSolverStatus::IncompleteForwardResourceLimit;
    bool exact = false;
    bool lower_bound_assumed = false;
    MixedSolverStatistics statistics;
    std::set<LocationId> locations;
    std::shared_ptr<const ReachabilitySnapshot> reachability;
    std::map<ReachNodeId, std::vector<MixedPricedPiece>> pieces;
    std::vector<MixedUnboundedRegion> unbounded_regions;
};

MixedAnalysisSnapshot::MixedAnalysisSnapshot()
    : impl_(std::make_shared<Impl>()) {}

MixedAnalysisSnapshot::MixedAnalysisSnapshot(std::shared_ptr<const Impl> impl)
    : impl_(std::move(impl)) {}

MixedSolverStatus MixedAnalysisSnapshot::status() const noexcept {
    return impl_->status;
}

bool MixedAnalysisSnapshot::exact() const noexcept {
    return impl_->exact;
}

bool MixedAnalysisSnapshot::lower_bound_assumed() const noexcept {
    return impl_->lower_bound_assumed;
}

const MixedSolverStatistics& MixedAnalysisSnapshot::statistics() const noexcept {
    return impl_->statistics;
}

const ReachabilitySnapshot* MixedAnalysisSnapshot::reachability() const noexcept {
    return impl_->reachability.get();
}

const std::vector<MixedPricedPiece>& MixedAnalysisSnapshot::pieces(
    ReachNodeId node) const {
    static const std::vector<MixedPricedPiece> empty;
    const auto found = impl_->pieces.find(node);
    return found == impl_->pieces.end() ? empty : found->second;
}

const std::map<ReachNodeId, std::vector<MixedPricedPiece>>&
MixedAnalysisSnapshot::all_pieces() const noexcept {
    return impl_->pieces;
}

const std::vector<MixedUnboundedRegion>&
MixedAnalysisSnapshot::unbounded_regions() const noexcept {
    return impl_->unbounded_regions;
}

MixedCostToGoResult MixedAnalysisSnapshot::query(
    LocationId location,
    const RationalValuation& valuation) const {
    if (impl_->locations.find(location) == impl_->locations.end()) {
        throw std::out_of_range("mixed query 引用了不存在的 location");
    }
    if (valuation.size() != impl_->dimension || valuation.empty() ||
        !is_zero(valuation.front())) {
        throw std::invalid_argument(
            "mixed query valuation 必须与 DBM dimension 对齐，"
            "且 0 号参考钟必须为零");
    }

    MixedCostToGoResult result;
    result.cost.solver_status = base_status(impl_->status);
    result.cost.lower_bound_assumed = impl_->lower_bound_assumed;

    if (!impl_->reachability || !impl_->reachability->exact()) {
        result.reachable_domain = ReachabilityMembership::Unknown;
        result.cost.kind = CostValueKind::Unknown;
        return result;
    }

    std::vector<ReachNodeId> covering_nodes;
    for (const auto& node : impl_->reachability->nodes()) {
        if (node.location == location && contains(node.zone, valuation)) {
            covering_nodes.push_back(node.id);
        }
    }
    if (covering_nodes.empty()) {
        // exact forward 已穷尽，因而可精确断言该点不属于
        // 真实可达域；这不等价于“可达但 Goal 成本为 +infinity”。
        result.reachable_domain = ReachabilityMembership::OutsideReachableDomain;
        result.cost.kind = CostValueKind::Unknown;
        return result;
    }
    result.reachable_domain = ReachabilityMembership::Reachable;

    // -infinity 定义域是一个完整 certificate，即使其他后向
    // worklist 被资源限制截断，该点的 -infinity 结论仍然精确。
    for (const auto& region : impl_->unbounded_regions) {
        if (region.location != location ||
            !std::binary_search(
                covering_nodes.begin(), covering_nodes.end(), region.node) ||
            !contains(region.zone, valuation)) {
            continue;
        }
        result.cost.kind = CostValueKind::NegativeInfinity;
        result.cost.attained = false;
        result.cost.exact = true;
        result.cost.unbounded_region_id = region.id;
        result.cost.next_edge = region.witness.next_edge;
        result.cost.witness = base_witness(region.witness);
        result.reachable_node = region.node;
        result.next_arc = region.witness.next_arc;
        result.next_edge = region.witness.next_edge;
        result.witness = region.witness;
        return result;
    }

    // 未穷尽的 label-correcting worklist 只给出当前上界，不对外
    // 冒充最优值。分片仍可通过 pieces(node) 作调试。
    if (!impl_->exact) {
        result.cost.kind = CostValueKind::Unknown;
        return result;
    }

    const MixedPricedPiece* best_piece = nullptr;
    BigRational best_weight(0);
    for (const ReachNodeId node : covering_nodes) {
        for (const auto& piece : pieces(node)) {
            if (!contains(piece.weighted_zone, valuation)) {
                continue;
            }
            const BigRational piece_weight =
                weight_at(piece.weighted_zone, valuation);
            if (best_piece == nullptr || piece_weight > best_weight ||
                (piece_weight == best_weight &&
                 piece.weighted_zone.attained &&
                 !best_piece->weighted_zone.attained) ||
                (piece_weight == best_weight &&
                 piece.weighted_zone.attained ==
                     best_piece->weighted_zone.attained &&
                 piece.id < best_piece->id)) {
                best_piece = &piece;
                best_weight = piece_weight;
            }
        }
    }

    if (best_piece != nullptr) {
        result.cost.kind = CostValueKind::Finite;
        result.cost.value = -best_weight;
        result.cost.attained = best_piece->weighted_zone.attained;
        result.cost.exact = true;
        result.cost.piece_id = best_piece->id;
        result.cost.next_edge = best_piece->witness.next_edge;
        result.cost.witness = base_witness(best_piece->witness);
        result.reachable_node = best_piece->node;
        result.next_arc = best_piece->witness.next_arc;
        result.next_edge = best_piece->witness.next_edge;
        result.witness = best_piece->witness;
        return result;
    }

    result.cost.kind = CostValueKind::PositiveInfinity;
    result.cost.attained = false;
    result.cost.exact = true;
    return result;
}

MixedAnalysisSnapshot solve_mixed(
    const WeightedAutomatonView& automaton,
    const ReachabilitySnapshot& reachability,
    const CostModel& costs,
    const SolverOptions& options) {
    const auto backward_started_at = std::chrono::steady_clock::now();
    auto output = std::make_shared<MixedAnalysisSnapshot::Impl>();
    output->dimension = automaton.dimension();
    output->lower_bound_assumed = options.assume_lower_bounded;
    output->reachability =
        std::make_shared<ReachabilitySnapshot>(reachability);
    output->statistics.forward_elapsed_ms =
        reachability.statistics().elapsed_ms;

    for (const auto& location : automaton.locations()) {
        output->locations.insert(location.id);
    }
    for (const auto& node : reachability.nodes()) {
        output->pieces.emplace(
            node.id, std::vector<MixedPricedPiece>{});
    }

    std::map<EdgeId, std::size_t> edge_indices;
    for (std::size_t index = 0; index < automaton.edges().size(); ++index) {
        edge_indices.emplace(automaton.edge(index).id, index);
    }
    validate_reachability_snapshot(automaton, reachability, edge_indices);

    const auto finish = [&output, backward_started_at]() {
        output->statistics.backward_elapsed_ms =
            elapsed_milliseconds(backward_started_at);
        output->statistics.backward.elapsed_ms =
            output->statistics.backward_elapsed_ms;
        output->statistics.total_elapsed_ms = saturating_add(
            output->statistics.forward_elapsed_ms,
            output->statistics.backward_elapsed_ms);
        return MixedAnalysisSnapshot(std::move(output));
    };

    // 前向图不完整时，部分图上的后向值不是原 TA 的值。
    // 因此明确不启动 backward worklist。
    if (!reachability.exact()) {
        output->status =
            MixedSolverStatus::IncompleteForwardResourceLimit;
        output->exact = false;
        return finish();
    }

    const bool nonnegative = costs.is_nonnegative_for(automaton);
    if (!nonnegative && !options.assume_lower_bounded) {
        output->status = MixedSolverStatus::AssumptionRequired;
        output->exact = false;
        return finish();
    }

    // timeout_ms 是 mixed forward+backward 的共享总预算。graph 快照保存
    // 的 elapsed 从本次 backward 额度中扣除。0 仍表示不限时。
    std::uint64_t backward_timeout_ms = 0;
    if (options.timeout_ms != 0) {
        if (output->statistics.forward_elapsed_ms >= options.timeout_ms) {
            output->status =
                MixedSolverStatus::IncompleteBackwardResourceLimit;
            output->exact = false;
            return finish();
        }
        backward_timeout_ms =
            options.timeout_ms - output->statistics.forward_elapsed_ms;
    }

    std::deque<MixedPricedPiece> waiting;
    std::deque<MixedUnboundedRegion> unbounded_waiting;
    for (const auto& node : reachability.nodes()) {
        if (!node.is_goal || node.zone.is_empty()) {
            continue;
        }
        MixedDerivationWitness witness;
        witness.is_goal_seed = true;
        witness.delay_kind = DelayWitnessKind::ZERO;
        waiting.push_back(MixedPricedPiece{
            0,
            node.id,
            node.location,
            zero_weighted_zone(node.zone),
            std::move(witness)});
        ++output->statistics.goal_seeds;
        ++output->statistics.backward.enqueued;
    }

    ExactDominance dominance;
    PieceId next_piece_id = 1;
    RegionId next_region_id = 1;
    bool resource_limited = false;

    // Roméo mixed 阶段的 label-correcting FIFO：每个新接受 label 就是
    // delta，只沿该 reachable node 已记录的 incoming arcs 反传一次。
    while ((!waiting.empty() || !unbounded_waiting.empty()) &&
           !resource_limited) {
        if (timeout_reached(backward_started_at, backward_timeout_ms) ||
            piece_limit_reached(
                output->statistics.backward, options.max_pieces)) {
            resource_limited = true;
            break;
        }

        if (!unbounded_waiting.empty()) {
            MixedUnboundedRegion candidate =
                std::move(unbounded_waiting.front());
            unbounded_waiting.pop_front();

            bool covered = false;
            for (const auto& existing : output->unbounded_regions) {
                if (existing.node != candidate.node) {
                    continue;
                }
                const auto relation = candidate.zone.relation(existing.zone);
                if (relation.is_equal() || relation.is_subset()) {
                    covered = true;
                    break;
                }
            }
            if (covered) {
                continue;
            }

            candidate.id = next_region_id++;
            output->unbounded_regions.push_back(std::move(candidate));
            ++output->statistics.backward.unbounded_regions;
            const auto& accepted = output->unbounded_regions.back();

            for (const ReachArcId arc_id :
                 reachability.incoming_arcs(accepted.node)) {
                if (timeout_reached(
                        backward_started_at, backward_timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                const auto& arc = reachability.arc(arc_id);
                const auto& source_node = reachability.node(arc.source);
                const auto& edge =
                    edge_for_id(automaton, edge_indices, arc.edge);

                // -infinity 与任意有限权重相加仍为 -infinity。用零
                // affine 函数仅复用精确几何 predecessor。
                auto target = intersection(
                    zero_weighted_zone(accepted.zone), arc.entry_zone);
                if (!target) {
                    continue;
                }
                auto action = action_predecessor(
                    *target,
                    edge.resets,
                    edge.guard,
                    source_node.zone,
                    BigInt(0));
                if (!action) {
                    continue;
                }
                const auto timed = time_predecessor(
                    *action, source_node.zone, BigInt(0));
                if (timed.unbounded_below) {
                    throw std::logic_error(
                        "零 rate/零 gradient 的 -infinity marker predecessor "
                        "不应产生新的 unbounded delay");
                }
                for (const auto& timed_piece : timed.pieces) {
                    MixedDerivationWitness witness;
                    witness.delay_kind = timed_piece.witness_kind;
                    witness.facet_clock = timed_piece.facet_clock;
                    witness.facet_bound = timed_piece.facet_bound;
                    witness.next_arc = arc.id;
                    witness.next_edge = edge.id;
                    witness.successor_node = accepted.node;
                    witness.successor_unbounded_region = accepted.id;
                    unbounded_waiting.push_back(MixedUnboundedRegion{
                        0,
                        source_node.id,
                        source_node.location,
                        timed_piece.weighted_zone.zone,
                        std::move(witness)});
                }
            }
            continue;
        }

        MixedPricedPiece candidate = std::move(waiting.front());
        waiting.pop_front();

        bool is_subsumed = false;
        if (options.enable_subsumption) {
            for (const auto& existing : output->pieces.at(candidate.node)) {
                const DominanceResult result = dominance.check(
                    existing.weighted_zone,
                    candidate.weighted_zone,
                    remaining_timeout_milliseconds(
                        backward_started_at, backward_timeout_ms));
                if (timeout_reached(
                        backward_started_at, backward_timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                if (result == DominanceResult::Dominated) {
                    is_subsumed = true;
                    break;
                }
                // UNKNOWN 必须按不剪枝处理，否则会破坏完备性。
            }
        }
        if (resource_limited) {
            break;
        }
        if (is_subsumed) {
            ++output->statistics.backward.subsumed;
            continue;
        }

        candidate.id = next_piece_id++;
        const ReachNodeId candidate_node = candidate.node;
        output->pieces.at(candidate_node).push_back(std::move(candidate));
        ++output->statistics.backward.accepted;
        const auto& accepted = output->pieces.at(candidate_node).back();

        for (const ReachArcId arc_id :
             reachability.incoming_arcs(accepted.node)) {
            if (timeout_reached(
                    backward_started_at, backward_timeout_ms)) {
                resource_limited = true;
                break;
            }
            const auto& arc = reachability.arc(arc_id);
            const auto& source_node = reachability.node(arc.source);
            const auto& edge =
                edge_for_id(automaton, edge_indices, arc.edge);
            ++output->statistics.backward.action_predecessors;

            // target piece 先限制到该 arc 的真实 reset 后入口域。
            // target node 可能是 post_zone 的真包含超集，不做此步
            // 会把其他前缀才能到达的 valuation 错传回本 arc。
            auto target = intersection(
                accepted.weighted_zone, arc.entry_zone);
            if (!target) {
                continue;
            }
            auto action = action_predecessor(
                *target,
                edge.resets,
                edge.guard,
                source_node.zone,
                costs.edge_cost(edge.id));
            if (!action) {
                continue;
            }

            const auto timed = time_predecessor(
                *action,
                source_node.zone,
                costs.location_rate(source_node.location));

            if (timed.unbounded_below) {
                if (!timed.unbounded_domain) {
                    throw std::logic_error(
                        "time_predecessor 报告无下界但未返回定义域");
                }
                MixedDerivationWitness witness;
                witness.delay_kind = DelayWitnessKind::UPPER_FACET;
                witness.next_arc = arc.id;
                witness.next_edge = edge.id;
                witness.successor_node = accepted.node;
                witness.successor_piece = accepted.id;
                witness.unbounded_delay = true;
                unbounded_waiting.push_back(MixedUnboundedRegion{
                    0,
                    source_node.id,
                    source_node.location,
                    *timed.unbounded_domain,
                    std::move(witness)});
            }

            for (const auto& timed_piece : timed.pieces) {
                MixedDerivationWitness witness;
                witness.delay_kind = timed_piece.witness_kind;
                witness.facet_clock = timed_piece.facet_clock;
                witness.facet_bound = timed_piece.facet_bound;
                witness.next_arc = arc.id;
                witness.next_edge = edge.id;
                witness.successor_node = accepted.node;
                witness.successor_piece = accepted.id;
                waiting.push_back(MixedPricedPiece{
                    0,
                    source_node.id,
                    source_node.location,
                    timed_piece.weighted_zone,
                    std::move(witness)});
                ++output->statistics.backward.enqueued;
                ++output->statistics.backward.time_predecessor_pieces;
            }
        }
    }

    const auto& dominance_statistics = dominance.statistics();
    output->statistics.backward.dominance_checks =
        dominance_statistics.checks;
    output->statistics.backward.dominance_unknown =
        dominance_statistics.solver_unknown;

    if (timeout_reached(backward_started_at, backward_timeout_ms)) {
        resource_limited = true;
    }
    if (resource_limited) {
        output->status =
            MixedSolverStatus::IncompleteBackwardResourceLimit;
        output->exact = false;
        return finish();
    }

    // 两类 worklist 均穷尽，才可对所有 reachable valuations
    // 声明 exact。主问题状态由初始零 valuation 判定。
    output->exact = true;
    bool initial_unbounded = false;
    bool initial_finite = false;
    if (reachability.initial_node()) {
        const RationalValuation initial_zero(
            automaton.dimension(), BigRational(BigInt(0)));
        const LocationId initial_location = automaton.initial_location();
        for (const auto& region : output->unbounded_regions) {
            if (region.location == initial_location &&
                contains(region.zone, initial_zero)) {
                initial_unbounded = true;
                break;
            }
        }
        if (!initial_unbounded) {
            for (const auto& entry : output->pieces) {
                const auto& node = reachability.node(entry.first);
                if (node.location != initial_location ||
                    !contains(node.zone, initial_zero)) {
                    continue;
                }
                for (const auto& piece : entry.second) {
                    if (contains(piece.weighted_zone, initial_zero)) {
                        initial_finite = true;
                        break;
                    }
                }
                if (initial_finite) {
                    break;
                }
            }
        }
    }

    if (initial_unbounded) {
        output->status = MixedSolverStatus::UnboundedBelow;
    } else if (initial_finite) {
        output->status = MixedSolverStatus::Complete;
    } else {
        output->status = MixedSolverStatus::Unreachable;
    }
    return finish();
}

MixedAnalysisSnapshot solve_mixed(
    const WeightedAutomatonView& automaton,
    const ReachabilitySnapshot& reachability,
    const SolverOptions& options) {
    return solve_mixed(automaton, reachability, CostModel{}, options);
}

std::string to_string(MixedSolverStatus status) {
    switch (status) {
        case MixedSolverStatus::Complete:
            return "complete";
        case MixedSolverStatus::Unreachable:
            return "unreachable";
        case MixedSolverStatus::UnboundedBelow:
            return "unbounded_below";
        case MixedSolverStatus::AssumptionRequired:
            return "assumption_required";
        case MixedSolverStatus::IncompleteForwardResourceLimit:
            return "incomplete_forward_resource_limit";
        case MixedSolverStatus::IncompleteBackwardResourceLimit:
            return "incomplete_backward_resource_limit";
    }
    throw std::logic_error("未知 MixedSolverStatus");
}

std::string to_string(ReachabilityMembership membership) {
    switch (membership) {
        case ReachabilityMembership::Reachable:
            return "reachable";
        case ReachabilityMembership::OutsideReachableDomain:
            return "outside_reachable_domain";
        case ReachabilityMembership::Unknown:
            return "unknown";
    }
    throw std::logic_error("未知 ReachabilityMembership");
}

}  // namespace tamonitor::pta
