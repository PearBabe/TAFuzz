// 本文件实现在线前缀 Federation 的候选下确界、精确聚合与 delay witness 回放。

#include "PrefixCostAnalyzer.h"

#include "PricedDBMOps.h"

#include <z3++.h>

#include <algorithm>
#include <chrono>
#include <limits>
#include <set>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using SteadyClock = std::chrono::steady_clock;

std::uint64_t elapsed_us(const SteadyClock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            SteadyClock::now() - start)
            .count());
}

std::uint64_t elapsed_ms(const SteadyClock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(
            SteadyClock::now() - start)
            .count());
}

bool deadline_reached(const SteadyClock::time_point start,
                      std::uint64_t timeout_ms) {
    return timeout_ms != 0 && elapsed_ms(start) >= timeout_ms;
}

std::uint64_t remaining_ms(const SteadyClock::time_point start,
                           std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return 0;
    }
    const auto used = elapsed_ms(start);
    return used >= timeout_ms ? 1 : timeout_ms - used;
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

std::optional<RationalValuation> singleton_valuation(
    const pardibaal::DBM& input) {
    auto zone = input;
    zone.close();
    if (zone.is_empty()) {
        return std::nullopt;
    }

    RationalValuation valuation(zone.dimension(), BigRational(0));
    for (pardibaal::dim_t clock = 1; clock < zone.dimension(); ++clock) {
        const auto lower = zone.at(0, clock);
        const auto upper = zone.at(clock, 0);
        if (lower.is_inf() || upper.is_inf() || lower.is_strict() ||
            upper.is_strict() || -lower.get_bound() != upper.get_bound()) {
            return std::nullopt;
        }
        valuation[clock] = BigRational(BigInt(upper.get_bound()));
    }
    return valuation;
}

BigRational affine_value_unchecked(const WeightedZone& zone,
                                   const RationalValuation& valuation) {
    if (valuation.size() != zone.zone.dimension()) {
        throw std::invalid_argument("affine valuation 与 DBM dimension 不一致");
    }
    const auto delta = offset(zone.zone);
    BigRational value(zone.offset_weight);
    for (pardibaal::dim_t clock = 1; clock < zone.zone.dimension(); ++clock) {
        value += BigRational(zone.rates[clock]) *
                 (valuation[clock] - BigRational(delta[clock]));
    }
    return value;
}

bool finite_candidate_better(const SymbolicCostCandidate& candidate,
                             const SymbolicCostCandidate& best) {
    if (candidate.supremum.value != best.supremum.value) {
        return candidate.supremum.value > best.supremum.value;
    }
    if (candidate.cost_attained != best.cost_attained) {
        return candidate.cost_attained;
    }
    if (candidate.supremum.optimizer_is_actual !=
        best.supremum.optimizer_is_actual) {
        return candidate.supremum.optimizer_is_actual;
    }
    if (candidate.runtime_state_id != best.runtime_state_id) {
        return candidate.runtime_state_id < best.runtime_state_id;
    }
    if (candidate.runtime_dbm_index != best.runtime_dbm_index) {
        return candidate.runtime_dbm_index < best.runtime_dbm_index;
    }
    if (candidate.reachable_node != best.reachable_node) {
        return candidate.reachable_node < best.reachable_node;
    }
    return candidate.piece_id < best.piece_id;
}

std::string rational_text(const BigRational& value) {
    const std::string numerator = value.numerator().convert_to<std::string>();
    if (value.denominator() == 1) {
        return numerator;
    }
    return numerator + "/" +
           value.denominator().convert_to<std::string>();
}

z3::expr exact_real(z3::context& context, const BigRational& value) {
    const std::string text = rational_text(value);
    return context.real_val(text.c_str());
}

z3::expr exact_real(z3::context& context, const BigInt& value) {
    const std::string text = value.convert_to<std::string>();
    return context.real_val(text.c_str());
}

BigRational model_rational(const z3::expr& expression) {
    std::string numeral;
    if (!expression.is_numeral(numeral)) {
        throw std::runtime_error("delay solver 未返回精确有理数");
    }
    const auto slash = numeral.find('/');
    if (slash == std::string::npos) {
        return BigRational(BigInt(numeral));
    }
    return BigRational(BigInt(numeral.substr(0, slash)),
                       BigInt(numeral.substr(slash + 1)));
}

void assert_zone(z3::solver& solver,
                 z3::context& context,
                 const pardibaal::DBM& zone,
                 const std::vector<z3::expr>& clocks) {
    for (pardibaal::dim_t i = 0; i < zone.dimension(); ++i) {
        for (pardibaal::dim_t j = 0; j < zone.dimension(); ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) {
                continue;
            }
            const z3::expr difference = clocks[i] - clocks[j];
            const z3::expr constant =
                context.real_val(std::to_string(bound.get_bound()).c_str());
            solver.add(bound.is_strict() ? difference < constant
                                         : difference <= constant);
        }
    }
}

z3::expr affine_expression(z3::context& context,
                           const WeightedZone& zone,
                           const std::vector<z3::expr>& clocks) {
    const auto delta = offset(zone.zone);
    z3::expr result = exact_real(context, zone.offset_weight);
    for (pardibaal::dim_t clock = 1; clock < zone.zone.dimension(); ++clock) {
        if (zone.rates[clock] == 0) {
            continue;
        }
        result = result + exact_real(context, zone.rates[clock]) *
                              (clocks[clock] -
                               exact_real(context, BigInt(delta[clock])));
    }
    return result;
}

std::vector<z3::expr> endpoint_expressions(
    z3::context& context,
    const RationalValuation& source,
    const z3::expr& delay) {
    std::vector<z3::expr> endpoint;
    endpoint.reserve(source.size());
    endpoint.push_back(context.real_val(0));
    for (std::size_t clock = 1; clock < source.size(); ++clock) {
        endpoint.push_back(exact_real(context, source[clock]) + delay);
    }
    return endpoint;
}

std::vector<z3::expr> reset_expressions(
    z3::context& context,
    const std::vector<z3::expr>& endpoint,
    const std::vector<pardibaal::dim_t>& resets) {
    std::set<pardibaal::dim_t> reset_set(resets.begin(), resets.end());
    std::vector<z3::expr> result;
    result.reserve(endpoint.size());
    for (pardibaal::dim_t clock = 0; clock < endpoint.size(); ++clock) {
        result.push_back(reset_set.count(clock) != 0
            ? context.real_val(0)
            : endpoint[clock]);
    }
    return result;
}

RationalValuation delayed_valuation(const RationalValuation& source,
                                    const BigRational& delay) {
    RationalValuation result = source;
    for (std::size_t clock = 1; clock < result.size(); ++clock) {
        result[clock] += delay;
    }
    return result;
}

RationalValuation reset_valuation(
    RationalValuation valuation,
    const std::vector<pardibaal::dim_t>& resets) {
    for (const auto clock : resets) {
        if (clock >= valuation.size()) {
            throw std::invalid_argument("edge reset clock 越界");
        }
        valuation[clock] = BigRational(0);
    }
    return valuation;
}

}  // namespace

SymbolicCostCandidate::SymbolicCostCandidate(
    std::uint64_t state_id,
    std::size_t dbm_index,
    ReachNodeId node,
    PieceId piece,
    pardibaal::DBM candidate_domain,
    WeightedZone candidate_weight,
    MixedDerivationWitness candidate_witness)
    : runtime_state_id(state_id),
      runtime_dbm_index(dbm_index),
      reachable_node(node),
      piece_id(piece),
      domain(std::move(candidate_domain)),
      affine_weight(std::move(candidate_weight)),
      witness(std::move(candidate_witness)) {}

PrefixCostAnalyzer::PrefixCostAnalyzer(
    WeightedAutomatonView automaton,
    CostModel costs,
    MixedAnalysisSnapshot snapshot)
    : automaton_(std::move(automaton)),
      costs_(std::move(costs)),
      snapshot_(std::move(snapshot)) {
    const auto* reachability = snapshot_.reachability();
    if (reachability == nullptr) {
        return;
    }
    if (!reachability->compatible_with(automaton_)) {
        throw std::invalid_argument(
            "PrefixCostAnalyzer 的 automaton 与 reachable graph 不一致");
    }
    for (const auto& node : reachability->nodes()) {
        nodes_by_location_[node.location].push_back(node.id);
    }
    for (const auto& location : automaton_.locations()) {
        support_by_location_.emplace(
            location.id, reachability->support(location.id));
    }
    for (const auto& [_, pieces] : snapshot_.all_pieces()) {
        for (const auto& piece : pieces) {
            pieces_by_id_.emplace(piece.id, &piece);
        }
    }
    for (const auto& region : snapshot_.unbounded_regions()) {
        unbounded_by_location_[region.location].push_back(&region);
    }
}

const WeightedAutomatonView& PrefixCostAnalyzer::automaton() const noexcept {
    return automaton_;
}

const CostModel& PrefixCostAnalyzer::costs() const noexcept {
    return costs_;
}

const MixedAnalysisSnapshot& PrefixCostAnalyzer::snapshot() const noexcept {
    return snapshot_;
}

SymbolicCostToGoResult PrefixCostAnalyzer::query(
    const std::vector<RuntimeSymbolicState>& states,
    const PrefixQueryOptions& options) const {
    const auto query_started = SteadyClock::now();
    SymbolicCostToGoResult result;
    result.aggregate.solver_status = base_status(snapshot_.status());
    result.aggregate.lower_bound_assumed = snapshot_.lower_bound_assumed();
    result.statistics.runtime_states = states.size();

    const auto finish = [&]() {
        result.statistics.core_query_us = elapsed_us(query_started);
        return result;
    };

    if (states.empty()) {
        result.domain_status = SymbolicDomainStatus::NoLiveState;
        result.aggregate.kind = CostValueKind::PositiveInfinity;
        result.aggregate.exact = true;
        result.diagnostic = "no_live_state";
        return finish();
    }

    const auto* reachability = snapshot_.reachability();
    if (reachability == nullptr || !reachability->exact()) {
        result.domain_status = SymbolicDomainStatus::IncompleteSnapshot;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = "incomplete_forward_snapshot";
        return finish();
    }

    // 查询前先证明整个 runtime domain 属于 exact forward support。对实际同源
    // monitor，这应当恒真；部分相交表示实现/Goal 生命周期不一致，不能忽略。
    bool any_nonempty = false;
    bool any_inside = false;
    bool any_outside = false;
    for (const auto& state : states) {
        if (state.semantic_domain.is_empty()) {
            continue;
        }
        any_nonempty = true;
        if (state.semantic_domain.dimension() != automaton_.dimension()) {
            result.domain_status = SymbolicDomainStatus::DomainMismatch;
            result.aggregate.kind = CostValueKind::Unknown;
            result.diagnostic = "runtime_dbm_dimension_mismatch";
            return finish();
        }
        const auto support_it = support_by_location_.find(state.location);
        if (support_it == support_by_location_.end() ||
            support_it->second.is_empty()) {
            any_outside = true;
            continue;
        }
        if (state.semantic_domain.is_exact_subset(support_it->second) ||
            state.semantic_domain.is_exact_equal(support_it->second)) {
            any_inside = true;
        } else if (state.semantic_domain.is_intersecting(support_it->second)) {
            any_inside = true;
            any_outside = true;
        } else {
            any_outside = true;
        }
    }
    if (!any_nonempty) {
        result.domain_status = SymbolicDomainStatus::NoLiveState;
        result.aggregate.kind = CostValueKind::PositiveInfinity;
        result.aggregate.exact = true;
        result.diagnostic = "all_runtime_domains_empty";
        return finish();
    }
    if (any_outside) {
        result.domain_status = any_inside
            ? SymbolicDomainStatus::DomainMismatch
            : SymbolicDomainStatus::OutsideReachableDomain;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = any_inside
            ? "runtime_domain_partially_outside_forward_support"
            : "runtime_domain_outside_forward_support";
        return finish();
    }

    bool query_incomplete = false;
    bool optimizer_unknown = false;
    bool aggregate_domain_unbounded = false;
    std::optional<std::size_t> domain_unbounded_candidate;
    std::optional<std::size_t> best_candidate;

    for (const auto& state : states) {
        std::size_t dbm_index = 0;
        for (const auto& runtime_dbm : state.semantic_domain) {
            ++result.statistics.runtime_dbms;
            if (deadline_reached(query_started, options.timeout_ms)) {
                query_incomplete = true;
                break;
            }

            const auto unbounded_it = unbounded_by_location_.find(state.location);
            if (unbounded_it != unbounded_by_location_.end()) {
                for (const auto* region : unbounded_it->second) {
                    auto domain = runtime_dbm;
                    domain.intersection(region->zone);
                    domain.close();
                    if (domain.is_empty()) {
                        continue;
                    }
                    if (result.candidates.size() +
                            result.unbounded_candidates.size() >=
                        options.max_regions) {
                        query_incomplete = true;
                        break;
                    }
                    result.unbounded_candidates.push_back(
                        SymbolicUnboundedCandidate{
                            state.runtime_state_id,
                            dbm_index,
                            region->node,
                            region->id,
                            std::move(domain),
                            region->witness});
                    ++result.statistics.unbounded_candidates;
                }
            }
            if (query_incomplete) {
                break;
            }

            if (!snapshot_.exact()) {
                ++dbm_index;
                continue;
            }

            const auto point = singleton_valuation(runtime_dbm);
            const auto nodes_it = nodes_by_location_.find(state.location);
            if (nodes_it == nodes_by_location_.end()) {
                ++dbm_index;
                continue;
            }

            for (const ReachNodeId node_id : nodes_it->second) {
                const auto filter_started = SteadyClock::now();
                ++result.statistics.reachable_nodes_considered;
                if (!runtime_dbm.is_intersecting(reachability->node(node_id).zone)) {
                    result.statistics.filtering_us += elapsed_us(filter_started);
                    continue;
                }
                result.statistics.filtering_us += elapsed_us(filter_started);

                for (const auto& piece : snapshot_.pieces(node_id)) {
                    if (deadline_reached(query_started, options.timeout_ms)) {
                        query_incomplete = true;
                        break;
                    }
                    if (result.candidates.size() +
                            result.unbounded_candidates.size() >=
                        options.max_regions) {
                        query_incomplete = true;
                        break;
                    }
                    const auto intersection_started = SteadyClock::now();
                    const auto candidate_weight =
                        intersection(piece.weighted_zone, runtime_dbm);
                    result.statistics.intersection_us +=
                        elapsed_us(intersection_started);
                    ++result.statistics.piece_intersections;
                    if (!candidate_weight.has_value()) {
                        continue;
                    }

                    result.candidates.emplace_back(
                        state.runtime_state_id,
                        dbm_index,
                        node_id,
                        piece.id,
                        candidate_weight->zone,
                        *candidate_weight,
                        piece.witness);
                    auto& candidate = result.candidates.back();
                    ++result.statistics.candidates;

                    if (point.has_value()) {
                        candidate.supremum.kind = AffineOptimumKind::Finite;
                        candidate.supremum.value =
                            affine_value_unchecked(candidate.affine_weight, *point);
                        candidate.supremum.domain_attained = true;
                        candidate.supremum.optimizer_is_actual = true;
                        candidate.supremum.optimizer_or_limit = point;
                        candidate.supremum.upper_bound_proved = true;
                        candidate.supremum.diagnostic = "point_fast_path";
                    } else {
                        result.statistics.optimizer_calls +=
                            options.optimizer == PrefixOptimizerBackend::CrossCheck
                                ? 2
                                : 1;
                        candidate.supremum = maximize_affine(
                            candidate.affine_weight,
                            candidate.domain,
                            options.optimizer,
                            remaining_ms(query_started, options.timeout_ms));
                        result.statistics.optimizer_us +=
                            candidate.supremum.elapsed_us;
                        if (deadline_reached(
                                query_started, options.timeout_ms)) {
                            query_incomplete = true;
                            break;
                        }
                    }

                    if (candidate.supremum.kind == AffineOptimumKind::Finite) {
                        candidate.cost_attained =
                            candidate.supremum.domain_attained &&
                            candidate.affine_weight.attained;
                        if (!best_candidate.has_value() ||
                            finite_candidate_better(
                                candidate, result.candidates[*best_candidate])) {
                            best_candidate = result.candidates.size() - 1;
                        }
                    } else if (candidate.supremum.kind ==
                               AffineOptimumKind::PositiveInfinity) {
                        aggregate_domain_unbounded = true;
                        if (!domain_unbounded_candidate.has_value()) {
                            domain_unbounded_candidate =
                                result.candidates.size() - 1;
                        }
                    } else if (candidate.supremum.kind ==
                               AffineOptimumKind::Unknown) {
                        optimizer_unknown = true;
                    }
                }
                if (query_incomplete) {
                    break;
                }
            }
            if (query_incomplete) {
                break;
            }
            ++dbm_index;
        }
        if (query_incomplete) {
            break;
        }
    }

    if (!result.unbounded_candidates.empty()) {
        const auto& chosen = result.unbounded_candidates.front();
        result.domain_status = query_incomplete
            ? SymbolicDomainStatus::IncompleteQuery
            : SymbolicDomainStatus::Complete;
        result.aggregate.kind = CostValueKind::NegativeInfinity;
        result.aggregate.attained = false;
        result.aggregate.exact = true;
        result.aggregate.unbounded_region_id = chosen.region_id;
        result.aggregate.next_edge = chosen.witness.next_edge;
        result.aggregate.witness = base_witness(chosen.witness);
        result.negative_infinity_cause =
            NegativeInfinityCause::PointwiseSuffix;
        result.runtime_state_id = chosen.runtime_state_id;
        result.runtime_dbm_index = chosen.runtime_dbm_index;
        result.reachable_node = chosen.reachable_node;
        result.next_arc = chosen.witness.next_arc;
        result.next_edge = chosen.witness.next_edge;
        result.witness = chosen.witness;
        result.diagnostic = query_incomplete
            ? "pointwise_negative_infinity_with_incomplete_candidate_listing"
            : "pointwise_negative_infinity";
        return finish();
    }

    if (!snapshot_.exact()) {
        result.domain_status = SymbolicDomainStatus::IncompleteSnapshot;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = "incomplete_backward_snapshot";
        return finish();
    }
    if (query_incomplete) {
        result.domain_status = SymbolicDomainStatus::IncompleteQuery;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = deadline_reached(query_started, options.timeout_ms)
            ? "prefix_query_timeout"
            : "prefix_region_limit";
        return finish();
    }
    if (aggregate_domain_unbounded) {
        const auto& candidate =
            result.candidates[*domain_unbounded_candidate];
        result.domain_status = SymbolicDomainStatus::Complete;
        result.aggregate.kind = CostValueKind::NegativeInfinity;
        result.aggregate.attained = false;
        result.aggregate.exact = true;
        result.aggregate.piece_id = candidate.piece_id;
        result.aggregate.next_edge = candidate.witness.next_edge;
        result.aggregate.witness = base_witness(candidate.witness);
        result.negative_infinity_cause =
            NegativeInfinityCause::RuntimeDomainAggregate;
        result.runtime_state_id = candidate.runtime_state_id;
        result.runtime_dbm_index = candidate.runtime_dbm_index;
        result.reachable_node = candidate.reachable_node;
        result.piece_id = candidate.piece_id;
        result.next_arc = candidate.witness.next_arc;
        result.next_edge = candidate.witness.next_edge;
        result.witness = candidate.witness;
        result.diagnostic = "affine_unbounded_across_runtime_domain";
        return finish();
    }
    if (optimizer_unknown) {
        result.domain_status = SymbolicDomainStatus::Unknown;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = "one_or_more_candidate_optimizers_unknown";
        return finish();
    }
    if (!best_candidate.has_value()) {
        result.domain_status = SymbolicDomainStatus::Complete;
        result.aggregate.kind = CostValueKind::PositiveInfinity;
        result.aggregate.attained = false;
        result.aggregate.exact = true;
        result.diagnostic = "reachable_domain_without_goal_suffix";
        return finish();
    }

    auto& best = result.candidates[*best_candidate];
    if (options.materialize_witness &&
        deadline_reached(query_started, options.timeout_ms)) {
        result.domain_status = SymbolicDomainStatus::IncompleteQuery;
        result.aggregate.kind = CostValueKind::Unknown;
        result.diagnostic = "timeout_before_witness_materialization";
        return finish();
    }
    if (options.materialize_witness && best.supremum.optimizer_or_limit.has_value()) {
        const auto witness_started = SteadyClock::now();
        auto& delay = best.delay;
        delay.replay_checked = true;
        const auto& valuation = *best.supremum.optimizer_or_limit;
        if (best.witness.is_goal_seed) {
            delay.value_or_limit = BigRational(0);
            delay.attained = best.supremum.optimizer_is_actual;
            delay.epsilon_optimal = !delay.attained;
            delay.replay_valid = true;
            delay.diagnostic = "goal_seed";
        } else if (best.witness.unbounded_delay) {
            delay.attained = false;
            delay.epsilon_optimal = false;
            delay.replay_valid = true;
            delay.diagnostic = "unbounded_delay";
        } else if (!best.witness.next_arc.has_value() ||
                   !best.witness.next_edge.has_value()) {
            delay.replay_valid = false;
            delay.diagnostic = "missing_next_arc_or_edge";
        } else {
            const auto& arc = reachability->arc(*best.witness.next_arc);
            const auto& edge = automaton_.edge(*best.witness.next_edge);
            std::optional<BigRational> proposed_delay;
            if (best.witness.delay_kind == DelayWitnessKind::ZERO) {
                proposed_delay = BigRational(0);
            } else if (best.witness.facet_clock.has_value() &&
                       best.witness.facet_bound.has_value() &&
                       *best.witness.facet_clock < valuation.size()) {
                proposed_delay =
                    BigRational(BigInt(*best.witness.facet_bound)) -
                    valuation[*best.witness.facet_clock];
            }

            const auto successor_it = best.witness.successor_piece.has_value()
                ? pieces_by_id_.find(*best.witness.successor_piece)
                : pieces_by_id_.end();
            const MixedPricedPiece* successor =
                successor_it == pieces_by_id_.end()
                    ? nullptr
                    : successor_it->second;

            const auto replay = [&](const BigRational& d, bool exact_domain) {
                if (d < BigRational(0) || successor == nullptr ||
                    arc.source != best.reachable_node || !(arc.edge == edge.id) ||
                    successor->node != arc.target) {
                    return false;
                }
                auto fire = exact_domain
                    ? arc.fire_zone
                    : topological_closure(arc.fire_zone);
                auto entry = exact_domain
                    ? arc.entry_zone
                    : topological_closure(arc.entry_zone);
                auto successor_zone = exact_domain
                    ? successor->weighted_zone.zone
                    : topological_closure(successor->weighted_zone.zone);
                const auto endpoint = delayed_valuation(valuation, d);
                if (!contains(fire, endpoint)) {
                    return false;
                }
                const auto after_reset = reset_valuation(endpoint, edge.resets);
                if (!contains(entry, after_reset) ||
                    !contains(successor_zone, after_reset)) {
                    return false;
                }
                const BigRational lhs =
                    affine_value_unchecked(best.affine_weight, valuation);
                const BigRational rhs =
                    affine_value_unchecked(successor->weighted_zone, after_reset) -
                    BigRational(costs_.edge_cost(edge.id)) -
                    BigRational(costs_.location_rate(edge.source)) * d;
                return lhs == rhs;
            };

            const bool exact_domain = best.supremum.optimizer_is_actual;
            if (proposed_delay.has_value() &&
                replay(*proposed_delay, exact_domain)) {
                delay.value_or_limit = proposed_delay;
                delay.attained = exact_domain;
                delay.epsilon_optimal = !exact_domain;
                delay.replay_valid = true;
                delay.diagnostic = "closed_form_replayed";
            } else if (successor != nullptr) {
                // flat-slope/strict 情形下 facet metadata 可能不是可执行 delay。
                // 以单变量 QF_LRA 重新物化，同时强制 Bellman 等式。
                z3::context context;
                z3::solver solver(context, "QF_LRA");
                if (options.timeout_ms != 0) {
                    z3::params parameters(context);
                    parameters.set(
                        "timeout",
                        static_cast<unsigned>(std::min<std::uint64_t>(
                            remaining_ms(query_started, options.timeout_ms),
                            std::numeric_limits<unsigned>::max())));
                    solver.set(parameters);
                }
                const z3::expr d = context.real_const("pta_prefix_delay");
                solver.add(d >= 0);
                const auto endpoint = endpoint_expressions(context, valuation, d);
                const auto after_reset =
                    reset_expressions(context, endpoint, edge.resets);
                const auto fire = exact_domain
                    ? arc.fire_zone
                    : topological_closure(arc.fire_zone);
                const auto entry = exact_domain
                    ? arc.entry_zone
                    : topological_closure(arc.entry_zone);
                const auto successor_zone = exact_domain
                    ? successor->weighted_zone.zone
                    : topological_closure(successor->weighted_zone.zone);
                assert_zone(solver, context, fire, endpoint);
                assert_zone(solver, context, entry, after_reset);
                assert_zone(solver, context, successor_zone, after_reset);
                const z3::expr target_weight = affine_expression(
                    context, successor->weighted_zone, after_reset);
                solver.add(
                    exact_real(
                        context,
                        affine_value_unchecked(best.affine_weight, valuation)) ==
                    target_weight -
                        exact_real(context, costs_.edge_cost(edge.id)) -
                        exact_real(context, costs_.location_rate(edge.source)) * d);
                const auto check = solver.check();
                if (check == z3::sat) {
                    const BigRational solved =
                        model_rational(solver.get_model().eval(d, true));
                    delay.value_or_limit = solved;
                    delay.attained = exact_domain;
                    delay.epsilon_optimal = !exact_domain;
                    delay.replay_valid = replay(solved, exact_domain);
                    delay.diagnostic = delay.replay_valid
                        ? "qf_lra_replayed"
                        : "qf_lra_model_failed_numeric_replay";
                } else {
                    delay.replay_valid = false;
                    delay.diagnostic = check == z3::unknown
                        ? "delay_solver_unknown:" + solver.reason_unknown()
                        : "no_bellman_delay";
                }
            } else {
                delay.replay_valid = false;
                delay.diagnostic = "missing_successor_piece";
            }
        }
        result.statistics.witness_us += elapsed_us(witness_started);
        if (!best.delay.replay_valid) {
            result.domain_status = SymbolicDomainStatus::Unknown;
            result.aggregate.kind = CostValueKind::Unknown;
            result.diagnostic = "best_witness_not_replayable:" +
                                best.delay.diagnostic;
            return finish();
        }
    }

    result.domain_status = SymbolicDomainStatus::Complete;
    result.aggregate.kind = CostValueKind::Finite;
    result.aggregate.value = -best.supremum.value;
    result.aggregate.attained = best.cost_attained;
    result.aggregate.exact = true;
    result.aggregate.piece_id = best.piece_id;
    result.aggregate.next_edge = best.witness.next_edge;
    result.aggregate.witness = base_witness(best.witness);
    result.optimizer_or_limit = best.supremum.optimizer_or_limit;
    result.optimizer_is_actual = best.supremum.optimizer_is_actual;
    result.delay_value_or_limit = best.delay.value_or_limit;
    result.delay_attained = best.delay.attained;
    result.runtime_state_id = best.runtime_state_id;
    result.runtime_dbm_index = best.runtime_dbm_index;
    result.reachable_node = best.reachable_node;
    result.piece_id = best.piece_id;
    result.next_arc = best.witness.next_arc;
    result.next_edge = best.witness.next_edge;
    result.witness = best.witness;
    result.diagnostic = best.cost_attained
        ? "finite_attained"
        : "finite_infimum_only";
    return finish();
}

std::string to_string(SymbolicDomainStatus status) {
    switch (status) {
        case SymbolicDomainStatus::Complete:
            return "complete";
        case SymbolicDomainStatus::GoalAlreadyHit:
            return "goal_already_hit";
        case SymbolicDomainStatus::NoLiveState:
            return "no_live_state";
        case SymbolicDomainStatus::OutsideReachableDomain:
            return "outside_reachable_domain";
        case SymbolicDomainStatus::DomainMismatch:
            return "domain_mismatch";
        case SymbolicDomainStatus::IncompleteSnapshot:
            return "incomplete_snapshot";
        case SymbolicDomainStatus::IncompleteQuery:
            return "incomplete_query";
        case SymbolicDomainStatus::Unknown:
            return "unknown";
    }
    throw std::logic_error("未知 SymbolicDomainStatus");
}

std::string to_string(NegativeInfinityCause cause) {
    switch (cause) {
        case NegativeInfinityCause::None:
            return "none";
        case NegativeInfinityCause::PointwiseSuffix:
            return "pointwise_suffix";
        case NegativeInfinityCause::RuntimeDomainAggregate:
            return "runtime_domain_aggregate";
    }
    throw std::logic_error("未知 NegativeInfinityCause");
}

}  // namespace tamonitor::pta
