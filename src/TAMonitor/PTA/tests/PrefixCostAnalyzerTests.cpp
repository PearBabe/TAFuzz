// 本文件验证在线前缀 Federation cost-to-go、错误状态与最优 delay witness 回放。

#include "PrefixCostAnalyzer.h"

#include "PricedDBMOps.h"

#include <z3++.h>

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using tamonitor::pta::BigInt;
using tamonitor::pta::BigRational;
using tamonitor::pta::CostModel;
using tamonitor::pta::CostValueKind;
using tamonitor::pta::EdgeId;
using tamonitor::pta::GoalSpec;
using tamonitor::pta::MixedAnalysisSnapshot;
using tamonitor::pta::MixedCostToGoResult;
using tamonitor::pta::MixedPricedPiece;
using tamonitor::pta::PrefixCostAnalyzer;
using tamonitor::pta::PrefixQueryOptions;
using tamonitor::pta::RationalValuation;
using tamonitor::pta::ReachabilityMembership;
using tamonitor::pta::ReachabilityOptions;
using tamonitor::pta::RuntimeSymbolicState;
using tamonitor::pta::SolverOptions;
using tamonitor::pta::SymbolicCostCandidate;
using tamonitor::pta::SymbolicCostToGoResult;
using tamonitor::pta::SymbolicDomainStatus;
using tamonitor::pta::WeightedAutomatonView;
using tamonitor::pta::WeightedEdge;
using tamonitor::pta::WeightedLocation;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

pardibaal::DBM universe(pardibaal::dim_t dimension) {
    return pardibaal::DBM::unconstrained(dimension);
}

pardibaal::DBM interval(pardibaal::val_t lower,
                        pardibaal::val_t upper,
                        bool strict_lower = false,
                        bool strict_upper = false) {
    auto zone = universe(2);
    zone.restrict(
        0, 1,
        strict_lower ? pardibaal::bound_t::strict(-lower)
                     : pardibaal::bound_t::non_strict(-lower));
    zone.restrict(
        1, 0,
        strict_upper ? pardibaal::bound_t::strict(upper)
                     : pardibaal::bound_t::non_strict(upper));
    zone.close();
    return zone;
}

pardibaal::DBM point(pardibaal::val_t value) {
    return interval(value, value);
}

RationalValuation valuation(pardibaal::val_t value) {
    return {BigRational(0), BigRational(BigInt(value))};
}

RuntimeSymbolicState runtime_state(std::uint64_t id,
                                   tamonitor::pta::LocationId location,
                                   const pardibaal::DBM& zone) {
    return RuntimeSymbolicState{id, location, pardibaal::Federation(zone)};
}

/**
 * source 上 0<=x<=5，rate=1；唯一边要求 x>=5，edge cost=2。
 * 因而每个 source valuation 的手算剩余代价都是 V(x)=7-x。
 */
WeightedAutomatonView hand_calculated_automaton() {
    auto source_invariant = interval(0, 5);
    auto guard = universe(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-5));
    guard.close();

    return WeightedAutomatonView(
        2,
        0,
        {WeightedLocation(0, source_invariant, "source"),
         WeightedLocation(1, universe(2), "goal")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, guard, {}, "finish")});
}

CostModel hand_calculated_costs() {
    CostModel costs;
    costs.default_location_rate = 1;
    costs.default_edge_cost = 0;
    costs.edge_costs[EdgeId{0, 0}] = 2;
    return costs;
}

struct Fixture {
    WeightedAutomatonView automaton;
    CostModel costs;
    MixedAnalysisSnapshot mixed;
    PrefixCostAnalyzer analyzer;

    Fixture()
        : automaton(hand_calculated_automaton()),
          costs(hand_calculated_costs()),
          mixed(tamonitor::pta::solve_mixed(
              automaton,
              tamonitor::pta::compute_reachable_zone_graph(
                  automaton, GoalSpec{{1}}),
              costs,
              SolverOptions{})),
          analyzer(automaton, costs, mixed) {}
};

const SymbolicCostCandidate& selected_candidate(
    const SymbolicCostToGoResult& result) {
    require(result.piece_id.has_value(), "prefix result 缺少最优 piece id");
    for (const auto& candidate : result.candidates) {
        if (candidate.piece_id == result.piece_id &&
            candidate.runtime_state_id == result.runtime_state_id &&
            candidate.runtime_dbm_index == result.runtime_dbm_index) {
            return candidate;
        }
    }
    throw std::runtime_error("prefix result 无法定位最优 candidate");
}

const MixedPricedPiece& successor_piece(
    const MixedAnalysisSnapshot& snapshot,
    const SymbolicCostCandidate& candidate) {
    require(candidate.witness.successor_node.has_value() &&
                candidate.witness.successor_piece.has_value(),
            "非 Goal witness 缺少 successor node/piece");
    for (const auto& piece :
         snapshot.pieces(*candidate.witness.successor_node)) {
        if (piece.id == *candidate.witness.successor_piece) {
            return piece;
        }
    }
    throw std::runtime_error("witness 引用的 successor piece 不存在");
}

RationalValuation delayed(RationalValuation source,
                          const BigRational& delay) {
    for (std::size_t clock = 1; clock < source.size(); ++clock) {
        source[clock] += delay;
    }
    return source;
}

void replay_selected_witness(const Fixture& fixture,
                             const SymbolicCostToGoResult& result,
                             const BigRational& expected_delay) {
    require(result.optimizer_or_limit.has_value() &&
                result.delay_value_or_limit == expected_delay &&
                result.next_arc == 0 &&
                result.next_edge == EdgeId{0, 0} &&
                result.witness.has_value(),
            "prefix aggregate 丢失预期 next edge/arc/delay witness");

    const auto& candidate = selected_candidate(result);
    require(candidate.delay.replay_checked && candidate.delay.replay_valid &&
                candidate.delay.value_or_limit == expected_delay,
            "PrefixCostAnalyzer 内部 witness replay 未通过");

    const auto* graph = fixture.mixed.reachability();
    require(graph != nullptr, "mixed snapshot 缺少 reachable graph");
    const auto& arc = graph->arc(*result.next_arc);
    const auto endpoint = delayed(
        *result.optimizer_or_limit, *result.delay_value_or_limit);
    require(tamonitor::pta::contains(arc.fire_zone, endpoint),
            "delay 后 valuation 不属于 fire_zone");
    require(tamonitor::pta::contains(arc.entry_zone, endpoint),
            "无 reset 模型的 endpoint 不属于 entry_zone");

    const auto& successor = successor_piece(fixture.mixed, candidate);
    require(tamonitor::pta::contains(successor.weighted_zone.zone, endpoint),
            "endpoint 不属于 successor priced piece");

    const BigRational source_weight = tamonitor::pta::weight_at(
        candidate.affine_weight, *result.optimizer_or_limit);
    const BigRational target_weight =
        tamonitor::pta::weight_at(successor.weighted_zone, endpoint);
    const BigRational bellman_rhs =
        target_weight - BigRational(fixture.costs.edge_cost(EdgeId{0, 0})) -
        BigRational(fixture.costs.location_rate(0)) * expected_delay;
    require(source_weight == bellman_rhs,
            "next arc witness 不满足 priced Bellman 等式");
}

void require_point_parity(const Fixture& fixture,
                          pardibaal::val_t clock_value,
                          pardibaal::val_t expected_cost,
                          pardibaal::val_t expected_delay) {
    const MixedCostToGoResult point_result =
        fixture.mixed.query(0, valuation(clock_value));
    const auto prefix_result = fixture.analyzer.query(
        {runtime_state(17, 0, point(clock_value))},
        PrefixQueryOptions{tamonitor::pta::PrefixOptimizerBackend::Z3,
                           0,
                           100'000,
                           true});

    require(prefix_result.domain_status == SymbolicDomainStatus::Complete &&
                prefix_result.aggregate.kind == CostValueKind::Finite &&
                prefix_result.aggregate.value == BigRational(expected_cost) &&
                prefix_result.aggregate.attained &&
                prefix_result.aggregate.exact,
            "手算 point prefix cost 不一致");
    require(point_result.reachable_domain ==
                ReachabilityMembership::Reachable &&
                point_result.cost.kind == prefix_result.aggregate.kind &&
                point_result.cost.value == prefix_result.aggregate.value &&
                point_result.cost.attained == prefix_result.aggregate.attained &&
                point_result.next_edge == prefix_result.next_edge &&
                point_result.next_arc == prefix_result.next_arc,
            "PrefixCostAnalyzer point fast path 与 mixed.query 不一致");
    require(prefix_result.statistics.optimizer_calls == 0 &&
                prefix_result.optimizer_is_actual &&
                prefix_result.runtime_state_id == 17,
            "singleton runtime DBM 未走 point fast path");
    replay_selected_witness(
        fixture, prefix_result, BigRational(expected_delay));
}

void test_hand_calculated_points_and_witness() {
    const Fixture fixture;
    require_point_parity(fixture, 0, 7, 5);
    require_point_parity(fixture, 2, 5, 3);
    require_point_parity(fixture, 4, 3, 1);

    const auto goal = fixture.analyzer.query(
        {runtime_state(18, 1, point(5))},
        PrefixQueryOptions{tamonitor::pta::PrefixOptimizerBackend::Z3,
                           0,
                           100'000,
                           true});
    require(goal.domain_status == SymbolicDomainStatus::Complete &&
                goal.aggregate.kind == CostValueKind::Finite &&
                goal.aggregate.value == BigRational(0) &&
                goal.aggregate.attained && !goal.next_edge.has_value() &&
                !goal.next_arc.has_value() &&
                goal.delay_value_or_limit == BigRational(0),
            "Goal prefix 应返回 cost=0 且无 next edge/arc");
}

void test_federation_best_case_and_strict_infimum() {
    const Fixture fixture;

    pardibaal::Federation federation(interval(0, 1));
    federation.add(interval(3, 4));
    const auto best_case = fixture.analyzer.query(
        {RuntimeSymbolicState{21, 0, federation}},
        PrefixQueryOptions{tamonitor::pta::PrefixOptimizerBackend::Z3,
                           0,
                           100'000,
                           true});
    require(best_case.domain_status == SymbolicDomainStatus::Complete &&
                best_case.aggregate.kind == CostValueKind::Finite &&
                best_case.aggregate.value == BigRational(3) &&
                best_case.aggregate.attained &&
                best_case.optimizer_or_limit.has_value() &&
                (*best_case.optimizer_or_limit)[1] == BigRational(4) &&
                best_case.statistics.runtime_dbms == 2 &&
                best_case.statistics.optimizer_calls >= 2,
            "Federation existential best-case 应选择 x=4、V=3");
    replay_selected_witness(fixture, best_case, BigRational(1));

    for (const auto backend : {
             tamonitor::pta::PrefixOptimizerBackend::RomeoDBM,
             tamonitor::pta::PrefixOptimizerBackend::CrossCheck}) {
        const auto alternative = fixture.analyzer.query(
            {RuntimeSymbolicState{23, 0, federation}},
            PrefixQueryOptions{backend, 0, 100'000, true});
        require(alternative.domain_status == SymbolicDomainStatus::Complete &&
                    alternative.aggregate.kind == CostValueKind::Finite &&
                    alternative.aggregate.value == best_case.aggregate.value &&
                    alternative.aggregate.attained ==
                        best_case.aggregate.attained &&
                    alternative.delay_value_or_limit == BigRational(1) &&
                    alternative.statistics.optimizer_calls ==
                        (backend == tamonitor::pta::PrefixOptimizerBackend::CrossCheck
                             ? 4
                             : 2),
                "Roméo/crosscheck Federation query 与 Z3 reference 不一致");
        replay_selected_witness(fixture, alternative, BigRational(1));
    }

    const auto strict = fixture.analyzer.query(
        {runtime_state(22, 0, interval(2, 4, false, true))},
        PrefixQueryOptions{tamonitor::pta::PrefixOptimizerBackend::Z3,
                           0,
                           100'000,
                           true});
    require(strict.domain_status == SymbolicDomainStatus::Complete &&
                strict.aggregate.kind == CostValueKind::Finite &&
                strict.aggregate.value == BigRational(3) &&
                !strict.aggregate.attained &&
                strict.optimizer_or_limit.has_value() &&
                (*strict.optimizer_or_limit)[1] == BigRational(4) &&
                !strict.optimizer_is_actual &&
                strict.delay_value_or_limit == BigRational(1) &&
                !strict.delay_attained,
            "x<4 runtime domain 应返回 infimum=3、attained=false");
    const auto& strict_candidate = selected_candidate(strict);
    require(strict_candidate.delay.replay_checked &&
                strict_candidate.delay.replay_valid &&
                strict_candidate.delay.epsilon_optimal,
            "strict runtime domain 的 closure delay witness 无法回放");
}

void test_domain_statuses() {
    const Fixture fixture;

    const auto no_live = fixture.analyzer.query({});
    require(no_live.domain_status == SymbolicDomainStatus::NoLiveState &&
                no_live.aggregate.kind == CostValueKind::PositiveInfinity &&
                no_live.aggregate.exact,
            "空 live-state 集应是精确 +infinity");

    const auto outside = fixture.analyzer.query(
        {runtime_state(30, 0, point(6))});
    require(outside.domain_status ==
                SymbolicDomainStatus::OutsideReachableDomain &&
                outside.aggregate.kind == CostValueKind::Unknown,
            "完全位于 exact forward support 外应返回 Outside");

    const auto partial = fixture.analyzer.query(
        {runtime_state(31, 0, interval(4, 6))});
    require(partial.domain_status == SymbolicDomainStatus::DomainMismatch &&
                partial.aggregate.kind == CostValueKind::Unknown,
            "部分越出 exact forward support 应返回 DomainMismatch");

    const auto wrong_dimension = fixture.analyzer.query(
        {RuntimeSymbolicState{
            32, 0, pardibaal::Federation::unconstrained(3)}});
    require(wrong_dimension.domain_status ==
                SymbolicDomainStatus::DomainMismatch &&
                wrong_dimension.aggregate.kind == CostValueKind::Unknown,
            "runtime DBM dimension 错误应显式返回 DomainMismatch");
}

void test_incomplete_snapshot_and_region_limit() {
    const auto automaton = hand_calculated_automaton();
    const auto costs = hand_calculated_costs();
    ReachabilityOptions reach_options;
    reach_options.max_nodes = 1;
    const auto partial_graph =
        tamonitor::pta::compute_reachable_zone_graph(
            automaton, GoalSpec{{1}}, reach_options);
    const auto partial_mixed = tamonitor::pta::solve_mixed(
        automaton, partial_graph, costs, SolverOptions{});
    const PrefixCostAnalyzer partial_analyzer(
        automaton, costs, partial_mixed);
    const auto incomplete_snapshot = partial_analyzer.query(
        {runtime_state(40, 0, point(0))});
    require(incomplete_snapshot.domain_status ==
                SymbolicDomainStatus::IncompleteSnapshot &&
                incomplete_snapshot.aggregate.kind == CostValueKind::Unknown,
            "不完整 forward snapshot 不得输出伪 cost");

    const Fixture fixture;
    PrefixQueryOptions limited;
    limited.timeout_ms = 0;
    limited.max_regions = 0;
    const auto region_limited = fixture.analyzer.query(
        {runtime_state(41, 0, interval(0, 4))}, limited);
    require(region_limited.domain_status ==
                SymbolicDomainStatus::IncompleteQuery &&
                region_limited.aggregate.kind == CostValueKind::Unknown &&
                region_limited.diagnostic == "prefix_region_limit",
            "region limit 命中后不得输出部分 aggregate 或 witness");
    require(!region_limited.next_edge.has_value() &&
                !region_limited.next_arc.has_value(),
            "不完整 prefix query 不得泄漏伪 next guidance");
}

WeightedAutomatonView full_trace_automaton() {
    auto source_zero = point(0);
    auto waiting = interval(0, 5);
    auto finish_guard = universe(2);
    finish_guard.restrict(
        0, 1, pardibaal::bound_t::non_strict(-5));
    finish_guard.close();
    return WeightedAutomatonView(
        2, 0,
        {WeightedLocation(0, source_zero, "l0"),
         WeightedLocation(1, waiting, "l1"),
         WeightedLocation(2, universe(2), "goal")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, source_zero, {1}, "a"),
         WeightedEdge(EdgeId{1, 0}, 1, 1, universe(2), {}, "a"),
         WeightedEdge(EdgeId{1, 1}, 1, 2, finish_guard, {1}, "b")});
}

CostModel full_trace_costs() {
    CostModel costs;
    costs.default_location_rate = 1;
    costs.edge_costs[EdgeId{0, 0}] = 3;
    costs.edge_costs[EdgeId{1, 1}] = 2;
    return costs;
}

void prove_manual_suffix_cost(
    pardibaal::val_t clock_value,
    pardibaal::val_t expected,
    bool includes_initial_edge) {
    z3::context context;
    const z3::expr delay = context.real_const("delay");
    const z3::expr cost = context.real_const("cost");
    auto constraints = delay >= 0;
    constraints = constraints &&
        delay == context.int_val(5 - clock_value);
    constraints = constraints &&
        cost == delay + context.int_val(includes_initial_edge ? 5 : 2);

    z3::solver lower(context);
    lower.add(constraints && cost < context.int_val(expected));
    require(lower.check() == z3::unsat,
            "独立 path encoding 未证明 cost < expected 为 UNSAT");
    z3::solver equality(context);
    equality.add(constraints && cost == context.int_val(expected));
    require(equality.check() == z3::sat,
            "独立 path encoding 未证明 cost = expected 为 SAT");
}

void test_fixed_trace_hand_derivation() {
    const auto automaton = full_trace_automaton();
    const auto costs = full_trace_costs();
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{2}});
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, costs, SolverOptions{});
    const PrefixCostAnalyzer analyzer(automaton, costs, mixed);

    struct Expected {
        tamonitor::pta::LocationId location;
        pardibaal::val_t clock;
        pardibaal::val_t cost;
        pardibaal::val_t delay;
        std::optional<EdgeId> edge;
        std::optional<tamonitor::pta::ReachArcId> arc;
    };
    const std::vector<Expected> trace = {
        {0, 0, 10, 0, EdgeId{0, 0}, 0},
        {1, 0, 7, 5, EdgeId{1, 1}, 2},
        {1, 2, 5, 3, EdgeId{1, 1}, 2},
        {1, 4, 3, 1, EdgeId{1, 1}, 2},
        {2, 0, 0, 0, std::nullopt, std::nullopt},
    };

    for (std::size_t prefix = 0; prefix < trace.size(); ++prefix) {
        const auto& expected = trace[prefix];
        const auto result = analyzer.query(
            {runtime_state(prefix, expected.location, point(expected.clock))},
            PrefixQueryOptions{
                tamonitor::pta::PrefixOptimizerBackend::Z3,
                0,
                100'000,
                true});
        require(result.domain_status == SymbolicDomainStatus::Complete &&
                    result.aggregate.kind == CostValueKind::Finite &&
                    result.aggregate.value == BigRational(expected.cost) &&
                    result.aggregate.attained &&
                    result.delay_value_or_limit == BigRational(expected.delay) &&
                    result.next_edge == expected.edge &&
                    result.next_arc == expected.arc,
                "固定 trace 的逐前缀手算 cost/witness 不一致");
        if (prefix < 4) {
            prove_manual_suffix_cost(
                expected.clock, expected.cost, prefix == 0);
        }
    }
}

}  // namespace

int main() {
    try {
        test_hand_calculated_points_and_witness();
        test_federation_best_case_and_strict_infimum();
        test_domain_statuses();
        test_incomplete_snapshot_and_region_limit();
        test_fixed_trace_hand_derivation();
        std::cout << "PrefixCostAnalyzerTests: all tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "PrefixCostAnalyzerTests failed: " << error.what()
                  << '\n';
        return EXIT_FAILURE;
    }
}
