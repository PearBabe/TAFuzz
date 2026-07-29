// 本文件忠实实现 Parrot--Lime Algorithm 1：Goal 起始、FIFO、入边与 priced predecessor。

#include "BackwardPricedSolver.h"

#include "ExactDominance.h"
#include "PricedDBMOps.h"

#include <algorithm>
#include <deque>
#include <set>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using Clock = pardibaal::dim_t;

bool is_zero(const BigRational& value) {
    return value.numerator() == 0;
}

bool point_in_zone(
    const pardibaal::DBM& zone,
    const RationalValuation& valuation) {
    const auto dimension = zone.dimension();
    if (valuation.size() != dimension || !is_zero(valuation.front())) {
        throw std::invalid_argument(
            "valuation 必须与 DBM dimension 对齐，且 0 号参考钟必须为零");
    }

    for (Clock i = 0; i < dimension; ++i) {
        for (Clock j = 0; j < dimension; ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) {
                continue;
            }
            const BigRational difference = valuation[i] - valuation[j];
            const BigRational constant(BigInt(bound.get_bound()));
            if (bound.is_strict() ? difference >= constant : difference > constant) {
                return false;
            }
        }
    }
    return true;
}

pardibaal::DBM nonnegative_invariant(
    const pardibaal::DBM& invariant,
    pardibaal::dim_t dimension) {
    if (invariant.dimension() != dimension) {
        throw std::invalid_argument("location invariant 的 DBM dimension 不一致");
    }

    pardibaal::DBM result = invariant;
    for (Clock clock = 1; clock < dimension; ++clock) {
        // 0-x <= 0，即 x >= 0。不要假定外部 DBM 构造器已隐式加入它。
        result.restrict(0, clock, pardibaal::bound_t::non_strict(0));
    }
    result.close();
    return result;
}

WeightedZone zero_weighted_zone(pardibaal::DBM zone) {
    const auto dimension = zone.dimension();
    return WeightedZone{
        std::move(zone),
        BigInt(0),
        std::vector<BigInt>(dimension, BigInt(0)),
        true};
}

bool timeout_reached(
    const std::chrono::steady_clock::time_point start,
    std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return false;
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start);
    if (elapsed.count() < 0) {
        return false;
    }
    return static_cast<std::uint64_t>(elapsed.count()) >= timeout_ms;
}

std::uint64_t elapsed_milliseconds(
    const std::chrono::steady_clock::time_point start) {
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start);
    return static_cast<std::uint64_t>(std::max<std::int64_t>(0, elapsed.count()));
}

std::uint64_t remaining_timeout_milliseconds(
    const std::chrono::steady_clock::time_point start,
    std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return 0;
    }
    const auto elapsed = elapsed_milliseconds(start);
    return elapsed >= timeout_ms ? 1 : timeout_ms - elapsed;
}

bool piece_limit_reached(
    const SolverStatistics& statistics,
    std::size_t max_pieces) {
    return statistics.accepted >= max_pieces ||
           statistics.unbounded_regions >= max_pieces - statistics.accepted;
}

}  // namespace

WeightedLocation::WeightedLocation(
    LocationId location_id,
    pardibaal::DBM location_invariant,
    std::string location_name)
    : id(location_id),
      invariant(std::move(location_invariant)),
      name(std::move(location_name)) {}

WeightedEdge::WeightedEdge(
    EdgeId edge_id,
    LocationId source_location,
    LocationId target_location,
    pardibaal::DBM edge_guard,
    std::vector<pardibaal::dim_t> reset_clocks,
    std::string edge_label)
    : id(edge_id),
      source(source_location),
      target(target_location),
      guard(std::move(edge_guard)),
      resets(std::move(reset_clocks)),
      label(std::move(edge_label)) {}

WeightedAutomatonView::WeightedAutomatonView(
    pardibaal::dim_t dimension,
    LocationId initial_location,
    std::vector<WeightedLocation> locations,
    std::vector<WeightedEdge> edges)
    : dimension_(dimension),
      initial_location_(initial_location),
      locations_(std::move(locations)),
      edges_(std::move(edges)) {
    if (dimension_ == 0) {
        throw std::invalid_argument("weighted automaton 至少需要 0 号参考钟");
    }

    for (std::size_t index = 0; index < locations_.size(); ++index) {
        const auto& location_value = locations_[index];
        if (location_value.invariant.dimension() != dimension_) {
            throw std::invalid_argument("location invariant 的 DBM dimension 不一致");
        }
        if (!location_index_.emplace(location_value.id, index).second) {
            throw std::invalid_argument("weighted automaton 含重复 location id");
        }
        incoming_edges_.emplace(location_value.id, std::vector<std::size_t>{});
        outgoing_edges_.emplace(location_value.id, std::vector<std::size_t>{});
    }
    if (location_index_.find(initial_location_) == location_index_.end()) {
        throw std::invalid_argument("weighted automaton 的 initial location 不存在");
    }

    std::set<EdgeId> edge_ids;
    for (std::size_t index = 0; index < edges_.size(); ++index) {
        const auto& edge_value = edges_[index];
        if (edge_value.id.source != edge_value.source) {
            throw std::invalid_argument("EdgeId.source 与 edge source 不一致");
        }
        if (!edge_ids.insert(edge_value.id).second ||
            !edge_index_.emplace(edge_value.id, index).second) {
            throw std::invalid_argument("weighted automaton 含重复 EdgeId");
        }
        if (edge_value.guard.dimension() != dimension_) {
            throw std::invalid_argument("edge guard 的 DBM dimension 不一致");
        }
        if (location_index_.find(edge_value.source) == location_index_.end() ||
            location_index_.find(edge_value.target) == location_index_.end()) {
            throw std::invalid_argument("edge 引用了不存在的 location");
        }
        for (const Clock clock : edge_value.resets) {
            if (clock == 0 || clock >= dimension_) {
                throw std::invalid_argument("edge reset 引用了非法时钟");
            }
        }
        incoming_edges_.at(edge_value.target).push_back(index);
        outgoing_edges_.at(edge_value.source).push_back(index);
    }
}

pardibaal::dim_t WeightedAutomatonView::dimension() const noexcept {
    return dimension_;
}

LocationId WeightedAutomatonView::initial_location() const noexcept {
    return initial_location_;
}

const std::vector<WeightedLocation>& WeightedAutomatonView::locations() const noexcept {
    return locations_;
}

const std::vector<WeightedEdge>& WeightedAutomatonView::edges() const noexcept {
    return edges_;
}

const WeightedLocation& WeightedAutomatonView::location(LocationId id) const {
    return locations_.at(location_index_.at(id));
}

const WeightedEdge& WeightedAutomatonView::edge(std::size_t index) const {
    return edges_.at(index);
}

const WeightedEdge& WeightedAutomatonView::edge(const EdgeId& id) const {
    return edges_.at(edge_index_.at(id));
}

const std::vector<std::size_t>& WeightedAutomatonView::incoming_edge_indices(
    LocationId id) const {
    return incoming_edges_.at(id);
}

const std::vector<std::size_t>& WeightedAutomatonView::outgoing_edge_indices(
    LocationId id) const {
    return outgoing_edges_.at(id);
}

BigInt CostModel::location_rate(LocationId location) const {
    const auto found = location_rates.find(location);
    return found == location_rates.end() ? default_location_rate : found->second;
}

BigInt CostModel::edge_cost(const EdgeId& edge) const {
    const auto found = edge_costs.find(edge);
    return found == edge_costs.end() ? default_edge_cost : found->second;
}

bool CostModel::is_nonnegative_for(const WeightedAutomatonView& automaton) const {
    for (const auto& location_value : automaton.locations()) {
        if (location_rate(location_value.id) < 0) {
            return false;
        }
    }
    for (const auto& edge_value : automaton.edges()) {
        if (edge_cost(edge_value.id) < 0) {
            return false;
        }
    }
    return true;
}

struct AnalysisSnapshot::Impl {
    pardibaal::dim_t dimension = 1;
    SolverStatus status = SolverStatus::ResourceLimit;
    bool exact = false;
    bool lower_bound_assumed = false;
    SolverStatistics statistics;
    std::set<LocationId> locations;
    std::map<LocationId, std::vector<PricedPiece>> pieces;
    std::vector<UnboundedRegion> unbounded_regions;
};

AnalysisSnapshot::AnalysisSnapshot() : impl_(std::make_shared<Impl>()) {}

AnalysisSnapshot::AnalysisSnapshot(std::shared_ptr<const Impl> impl)
    : impl_(std::move(impl)) {}

SolverStatus AnalysisSnapshot::status() const noexcept {
    return impl_->status;
}

bool AnalysisSnapshot::exact() const noexcept {
    return impl_->exact;
}

bool AnalysisSnapshot::lower_bound_assumed() const noexcept {
    return impl_->lower_bound_assumed;
}

const SolverStatistics& AnalysisSnapshot::statistics() const noexcept {
    return impl_->statistics;
}

const std::vector<PricedPiece>& AnalysisSnapshot::pieces(LocationId location) const {
    static const std::vector<PricedPiece> empty;
    const auto found = impl_->pieces.find(location);
    return found == impl_->pieces.end() ? empty : found->second;
}

const std::map<LocationId, std::vector<PricedPiece>>&
AnalysisSnapshot::all_pieces() const noexcept {
    return impl_->pieces;
}

const std::vector<UnboundedRegion>&
AnalysisSnapshot::unbounded_regions() const noexcept {
    return impl_->unbounded_regions;
}

CostToGoResult AnalysisSnapshot::query(
    LocationId location,
    const RationalValuation& valuation) const {
    if (impl_->locations.find(location) == impl_->locations.end()) {
        throw std::out_of_range("query 引用了不存在的 location");
    }
    if (valuation.size() != impl_->dimension || valuation.empty() ||
        !is_zero(valuation.front())) {
        throw std::invalid_argument(
            "query valuation 必须与 DBM dimension 对齐，且 0 号参考钟必须为零");
    }

    CostToGoResult result;
    result.solver_status = impl_->status;
    result.lower_bound_assumed = impl_->lower_bound_assumed;

    // 该区域上的 delay 目标沿无界方向严格下降，因此 V=-W=-infinity。
    for (const auto& region : impl_->unbounded_regions) {
        if (region.location == location && point_in_zone(region.zone, valuation)) {
            result.kind = CostValueKind::NegativeInfinity;
            result.attained = false;
            result.exact = true;
            result.unbounded_region_id = region.id;
            result.witness = region.witness;
            result.next_edge = region.witness.next_edge;
            return result;
        }
    }

    const PricedPiece* best_piece = nullptr;
    BigRational best_weight(0);
    for (const auto& piece : pieces(location)) {
        if (!contains(piece.weighted_zone, valuation)) {
            continue;
        }
        const BigRational piece_weight = weight_at(piece.weighted_zone, valuation);
        if (best_piece == nullptr || piece_weight > best_weight ||
            (piece_weight == best_weight && piece.weighted_zone.attained &&
             !best_piece->weighted_zone.attained) ||
            (piece_weight == best_weight &&
             piece.weighted_zone.attained == best_piece->weighted_zone.attained &&
             piece.id < best_piece->id)) {
            best_piece = &piece;
            best_weight = piece_weight;
        }
    }

    if (best_piece != nullptr) {
        result.kind = CostValueKind::Finite;
        result.value = -best_weight;
        result.attained = best_piece->weighted_zone.attained;
        result.exact = impl_->exact;
        result.piece_id = best_piece->id;
        result.next_edge = best_piece->witness.next_edge;
        result.witness = best_piece->witness;
        return result;
    }

    if (impl_->exact) {
        result.kind = CostValueKind::PositiveInfinity;
        result.attained = false;
        result.exact = true;
    } else {
        result.kind = CostValueKind::Unknown;
        result.attained = false;
        result.exact = false;
    }
    return result;
}

AnalysisSnapshot solve(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const CostModel& costs,
    const SolverOptions& options) {
    const auto started_at = std::chrono::steady_clock::now();
    auto output = std::make_shared<AnalysisSnapshot::Impl>();
    output->dimension = automaton.dimension();
    output->lower_bound_assumed = options.assume_lower_bounded;
    for (const auto& location_value : automaton.locations()) {
        output->locations.insert(location_value.id);
        output->pieces.emplace(location_value.id, std::vector<PricedPiece>{});
    }

    const bool nonnegative = costs.is_nonnegative_for(automaton);
    if (!nonnegative && !options.assume_lower_bounded) {
        output->status = SolverStatus::AssumptionRequired;
        output->exact = false;
        output->statistics.elapsed_ms = elapsed_milliseconds(started_at);
        return AnalysisSnapshot(std::move(output));
    }

    std::deque<PricedPiece> waiting;
    std::set<LocationId> unique_goals;
    for (const LocationId goal : goals.locations) {
        // location() 同时负责拒绝拼写错误的目标 id。
        const auto& goal_location = automaton.location(goal);
        if (!unique_goals.insert(goal).second) {
            continue;
        }
        pardibaal::DBM goal_zone =
            nonnegative_invariant(goal_location.invariant, automaton.dimension());
        if (goal_zone.is_empty()) {
            continue;
        }
        DerivationWitness seed_witness;
        seed_witness.is_goal_seed = true;
        seed_witness.delay_kind = DelayWitnessKind::ZERO;
        PricedPiece seed{
            0,
            goal,
            zero_weighted_zone(std::move(goal_zone)),
            std::move(seed_witness)};
        waiting.push_back(std::move(seed));
        ++output->statistics.enqueued;
    }

    ExactDominance dominance;
    PieceId next_piece_id = 1;
    RegionId next_region_id = 1;
    std::deque<UnboundedRegion> unbounded_waiting;
    const RationalValuation initial_zero(
        automaton.dimension(), BigRational(BigInt(0)));
    bool resource_limited = false;
    bool initial_unbounded = false;

    // Algorithm 1 是 label-correcting FIFO 固定点；队列顺序不是 Dijkstra 优先级。
    // -infinity marker 使用同一套几何 predecessor 独立传播，因为任意有限
    // rate/edge cost 与 -infinity 相加仍为 -infinity。
    while ((!waiting.empty() || !unbounded_waiting.empty()) &&
           !resource_limited && !initial_unbounded) {
        if (timeout_reached(started_at, options.timeout_ms) ||
            piece_limit_reached(output->statistics, options.max_pieces)) {
            resource_limited = true;
            break;
        }

        if (!unbounded_waiting.empty()) {
            UnboundedRegion candidate = std::move(unbounded_waiting.front());
            unbounded_waiting.pop_front();

            bool covered = false;
            for (const auto& existing : output->unbounded_regions) {
                if (existing.location != candidate.location) {
                    continue;
                }
                // relation().is_subset() 是真子集，equal 必须单独接受。
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
            ++output->statistics.unbounded_regions;
            const auto& accepted_region = output->unbounded_regions.back();

            if (timeout_reached(started_at, options.timeout_ms)) {
                resource_limited = true;
                break;
            }

            if (accepted_region.location == automaton.initial_location() &&
                point_in_zone(accepted_region.zone, initial_zero)) {
                // 只有 marker 真正覆盖 initial valuation，才能对主问题报告 -infinity。
                initial_unbounded = true;
                break;
            }

            for (const std::size_t edge_index :
                 automaton.incoming_edge_indices(accepted_region.location)) {
                if (timeout_reached(started_at, options.timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                const auto& edge_value = automaton.edge(edge_index);
                const auto& source = automaton.location(edge_value.source);

                // 用零仿射函数复用 Theorem 1 的精确几何 inverse-reset；
                // marker 的 -infinity 值本身不参与任何有限算术。
                const auto geometric_action = action_predecessor(
                    zero_weighted_zone(accepted_region.zone),
                    edge_value.resets,
                    edge_value.guard,
                    source.invariant,
                    BigInt(0));
                if (timeout_reached(started_at, options.timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                if (!geometric_action.has_value()) {
                    continue;
                }

                const auto timed_domains = time_predecessor(
                    *geometric_action, source.invariant, BigInt(0));
                if (timed_domains.unbounded_below) {
                    throw std::logic_error(
                        "零 rate/零 gradient 的 marker predecessor 不应产生新无界 delay");
                }
                if (timeout_reached(started_at, options.timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                for (const auto& timed_piece : timed_domains.pieces) {
                    DerivationWitness witness;
                    witness.delay_kind = timed_piece.witness_kind;
                    witness.facet_clock = timed_piece.facet_clock;
                    witness.facet_bound = timed_piece.facet_bound;
                    witness.next_edge = edge_value.id;
                    witness.successor_unbounded_region = accepted_region.id;
                    witness.unbounded_delay = false;
                    unbounded_waiting.push_back(UnboundedRegion{
                        source.id, timed_piece.weighted_zone.zone,
                        std::move(witness), 0});
                }
            }
            continue;
        }

        PricedPiece candidate = std::move(waiting.front());
        waiting.pop_front();

        bool is_subsumed = false;
        if (options.enable_subsumption) {
            for (const auto& existing : output->pieces.at(candidate.location)) {
                const DominanceResult result =
                    dominance.check(
                        existing.weighted_zone,
                        candidate.weighted_zone,
                        remaining_timeout_milliseconds(
                            started_at, options.timeout_ms));
                if (timeout_reached(started_at, options.timeout_ms)) {
                    resource_limited = true;
                    break;
                }
                if (result == DominanceResult::Dominated) {
                    is_subsumed = true;
                    break;
                }
                // UNKNOWN 明确按“不剪枝”处理，保证 Z3 不确定性不破坏完备性。
            }
        }
        if (resource_limited) {
            break;
        }
        if (is_subsumed) {
            ++output->statistics.subsumed;
            continue;
        }

        candidate.id = next_piece_id++;
        const LocationId candidate_location = candidate.location;
        output->pieces.at(candidate_location).push_back(std::move(candidate));
        ++output->statistics.accepted;
        const PricedPiece& accepted = output->pieces.at(candidate_location).back();

        // 按 Theorem 1 遍历原自动机中指向当前位置的入边，而不是反转边对象。
        for (const std::size_t edge_index :
             automaton.incoming_edge_indices(accepted.location)) {
            if (timeout_reached(started_at, options.timeout_ms)) {
                resource_limited = true;
                break;
            }

            const auto& edge_value = automaton.edge(edge_index);
            const auto& source = automaton.location(edge_value.source);
            ++output->statistics.action_predecessors;
            const auto action = action_predecessor(
                accepted.weighted_zone,
                edge_value.resets,
                edge_value.guard,
                source.invariant,
                costs.edge_cost(edge_value.id));
            if (timeout_reached(started_at, options.timeout_ms)) {
                resource_limited = true;
                break;
            }
            if (!action.has_value()) {
                continue;
            }

            const TimePredecessorResult timed = time_predecessor(
                *action,
                source.invariant,
                costs.location_rate(source.id));
            if (timeout_reached(started_at, options.timeout_ms)) {
                resource_limited = true;
                break;
            }

            if (timed.unbounded_below) {
                if (!timed.unbounded_domain.has_value()) {
                    throw std::logic_error(
                        "time_predecessor 报告无下界但未返回精确定义域");
                }
                DerivationWitness witness;
                witness.delay_kind = DelayWitnessKind::UPPER_FACET;
                witness.next_edge = edge_value.id;
                witness.successor_piece = accepted.id;
                witness.unbounded_delay = true;
                unbounded_waiting.push_back(UnboundedRegion{
                    source.id, *timed.unbounded_domain, std::move(witness), 0});
            }

            for (const auto& timed_piece : timed.pieces) {
                DerivationWitness witness;
                witness.delay_kind = timed_piece.witness_kind;
                witness.facet_clock = timed_piece.facet_clock;
                witness.facet_bound = timed_piece.facet_bound;
                witness.next_edge = edge_value.id;
                witness.successor_piece = accepted.id;

                waiting.push_back(PricedPiece{
                    0,
                    source.id,
                    timed_piece.weighted_zone,
                    std::move(witness)});
                ++output->statistics.enqueued;
                ++output->statistics.time_predecessor_pieces;
            }
        }
    }

    const auto& dominance_statistics = dominance.statistics();
    output->statistics.dominance_checks = dominance_statistics.checks;
    output->statistics.dominance_unknown = dominance_statistics.solver_unknown;

    if (!initial_unbounded && timeout_reached(started_at, options.timeout_ms)) {
        resource_limited = true;
    }

    if (initial_unbounded) {
        output->status = SolverStatus::UnboundedBelow;
        // 主问题的 -infinity 已精确证明，但提前停止意味着全状态离线表未完成。
        output->exact = false;
    } else if (resource_limited) {
        output->status = SolverStatus::ResourceLimit;
        output->exact = false;
    } else {
        // 两类 worklist 都已穷尽；有限值与 -infinity 域均达到 fixed point。
        bool initial_reachable = false;
        for (const auto& piece : output->pieces.at(automaton.initial_location())) {
            if (contains(piece.weighted_zone, initial_zero)) {
                initial_reachable = true;
                break;
            }
        }
        output->status = initial_reachable ? SolverStatus::Complete
                                           : SolverStatus::Unreachable;
        output->exact = true;
    }

    output->statistics.elapsed_ms = elapsed_milliseconds(started_at);
    return AnalysisSnapshot(std::move(output));
}

AnalysisSnapshot solve(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const SolverOptions& options) {
    return solve(automaton, goals, CostModel{}, options);
}

std::string to_string(SolverStatus status) {
    switch (status) {
        case SolverStatus::Complete:
            return "complete";
        case SolverStatus::Unreachable:
            return "unreachable";
        case SolverStatus::UnboundedBelow:
            return "unbounded_below";
        case SolverStatus::AssumptionRequired:
            return "assumption_required";
        case SolverStatus::ResourceLimit:
            return "incomplete_resource_limit";
    }
    throw std::logic_error("未知 SolverStatus");
}

std::string to_string(CostValueKind kind) {
    switch (kind) {
        case CostValueKind::Finite:
            return "finite";
        case CostValueKind::PositiveInfinity:
            return "positive_infinity";
        case CostValueKind::NegativeInfinity:
            return "negative_infinity";
        case CostValueKind::Unknown:
            return "unknown";
    }
    throw std::logic_error("未知 CostValueKind");
}

}  // namespace tamonitor::pta
