// 本文件验证 exact reachable graph 上的 Node-scoped mixed priced fixed point。

#include "MixedPricedSolver.h"
#include "PricedDBMOps.h"

#include <Fixpoint.h>
#include <TA.h>
#include <z3++.h>

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using tamonitor::pta::BigInt;
using tamonitor::pta::BigRational;
using tamonitor::pta::CostModel;
using tamonitor::pta::CostValueKind;
using tamonitor::pta::EdgeId;
using tamonitor::pta::GoalSpec;
using tamonitor::pta::MixedSolverStatus;
using tamonitor::pta::RationalValuation;
using tamonitor::pta::ReachabilityMembership;
using tamonitor::pta::ReachabilityOptions;
using tamonitor::pta::SolverOptions;
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

RationalValuation one_clock(pardibaal::val_t value) {
    return {BigRational(0), BigRational(BigInt(value))};
}

WeightedAutomatonView shortest_time_automaton(bool include_unreachable) {
    auto guard = universe(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-3));
    std::vector<WeightedLocation> locations{
        WeightedLocation(0, universe(2), "source"),
        WeightedLocation(1, universe(2), "goal")};
    std::vector<WeightedEdge> edges{
        WeightedEdge(EdgeId{0, 0}, 0, 1, guard, {}, "after-three")};
    if (include_unreachable) {
        locations.emplace_back(2, universe(2), "dead-prefix");
        edges.emplace_back(
            EdgeId{2, 0}, 2, 1, universe(2),
            std::vector<pardibaal::dim_t>{}, "dead-to-goal");
    }
    return WeightedAutomatonView(
        2, 0, std::move(locations), std::move(edges));
}

void test_mixed_shortest_time_domain_and_witness() {
    const auto automaton = shortest_time_automaton(true);
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, CostModel{}, SolverOptions{});
    const auto pure = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, CostModel{}, SolverOptions{});

    const auto initial = mixed.query(0, one_clock(0));
    require(mixed.status() == MixedSolverStatus::Complete && mixed.exact(),
            "非负 mixed 最短时间模型应完整终止");
    require(initial.reachable_domain == ReachabilityMembership::Reachable &&
                initial.cost.kind == CostValueKind::Finite &&
                initial.cost.value == BigRational(3) &&
                initial.cost.attained && initial.cost.exact,
            "mixed 初始最短剩余时间应为 3");
    require(initial.next_arc == 0 && initial.next_edge == EdgeId{0, 0} &&
                initial.witness.has_value() &&
                initial.witness->successor_node.has_value(),
            "mixed query 丢失 graph arc/node guidance witness");

    for (const auto value : {0, 1, 3, 5}) {
        const auto mixed_value = mixed.query(0, one_clock(value));
        const auto pure_value = pure.query(0, one_clock(value));
        require(mixed_value.cost.kind == pure_value.kind &&
                    mixed_value.cost.value == pure_value.value &&
                    mixed_value.cost.attained == pure_value.attained,
                "mixed 与 pure backward 在 reachable valuation 上不一致");
    }

    const auto outside = mixed.query(2, one_clock(0));
    const auto pure_dead = pure.query(2, one_clock(0));
    require(outside.reachable_domain ==
                ReachabilityMembership::OutsideReachableDomain &&
                outside.cost.kind == CostValueKind::Unknown &&
                pure_dead.kind == CostValueKind::Finite,
            "mixed 必须区分不可达前缀域与可达但无 Goal suffix");
}

WeightedAutomatonView cost_fourteen_automaton(bool strict_first_edge) {
    constexpr pardibaal::dim_t dimension = 3;  // 0, x, y
    auto initial_invariant = universe(dimension);
    initial_invariant.restrict(
        1, 0, pardibaal::bound_t::non_strict(2));
    auto middle_invariant = universe(dimension);
    middle_invariant.restrict(
        1, 0, pardibaal::bound_t::non_strict(4));

    auto first_guard = universe(dimension);
    first_guard.restrict(
        0, 1,
        strict_first_edge
            ? pardibaal::bound_t::strict(-1)
            : pardibaal::bound_t::non_strict(-1));
    auto second_guard = universe(dimension);
    second_guard.restrict(
        0, 2, pardibaal::bound_t::non_strict(-1));

    return WeightedAutomatonView(
        dimension,
        0,
        {WeightedLocation(0, initial_invariant, "initial"),
         WeightedLocation(1, middle_invariant, "middle"),
         WeightedLocation(2, universe(dimension), "goal")},
        {WeightedEdge(
             EdgeId{0, 0}, 0, 1, first_guard,
             std::vector<pardibaal::dim_t>{2}, "reset-y"),
         WeightedEdge(
             EdgeId{1, 0}, 1, 2, second_guard,
             std::vector<pardibaal::dim_t>{}, "finish")});
}

CostModel cost_fourteen_model() {
    CostModel costs;
    costs.default_location_rate = 0;
    costs.default_edge_cost = 0;
    costs.location_rates[0] = 2;
    costs.location_rates[1] = 3;
    costs.edge_costs[EdgeId{0, 0}] = 4;
    costs.edge_costs[EdgeId{1, 0}] = 5;
    return costs;
}

void check_independent_cost_fourteen_oracle() {
    z3::context context;
    z3::solver solver(context, "QF_LRA");
    const z3::expr first_delay = context.real_const("mixed_oracle_d0");
    const z3::expr second_delay = context.real_const("mixed_oracle_d1");
    const z3::expr cost = context.real_const("mixed_oracle_cost");
    solver.add(first_delay >= 1 && first_delay <= 2);
    solver.add(second_delay >= 1);
    solver.add(first_delay + second_delay <= 4);
    solver.add(cost == 2 * first_delay + 4 + 3 * second_delay + 5);

    solver.push();
    solver.add(cost < 14);
    require(solver.check() == z3::unsat,
            "独立 Z3 path encoding 找到了低于 14 的运行");
    solver.pop();
    solver.add(cost == 14);
    require(solver.check() == z3::sat,
            "独立 Z3 path encoding 未找到 cost=14 运行");
}

void test_nonzero_cost_and_strict_infimum() {
    const CostModel costs = cost_fourteen_model();
    for (const bool strict : {false, true}) {
        const auto automaton = cost_fourteen_automaton(strict);
        const auto graph = tamonitor::pta::compute_reachable_zone_graph(
            automaton, GoalSpec{{2}});
        const auto mixed = tamonitor::pta::solve_mixed(
            automaton, graph, costs, SolverOptions{});
        const auto pure = tamonitor::pta::solve(
            automaton, GoalSpec{{2}}, costs, SolverOptions{});
        const auto result = mixed.query(
            0, RationalValuation(automaton.dimension(), BigRational(0)));
        const auto pure_result = pure.query(
            0, RationalValuation(automaton.dimension(), BigRational(0)));

        require(mixed.status() == MixedSolverStatus::Complete &&
                    result.cost.kind == CostValueKind::Finite &&
                    result.cost.value == BigRational(14),
                "mixed 手算非零成本应为 14");
        require(result.cost.attained == !strict &&
                    pure_result.value == result.cost.value &&
                    pure_result.attained == result.cost.attained,
                "strict x>1 应保留 infimum=14 并令 attained=false");
    }
    check_independent_cost_fourteen_oracle();
}

void test_forward_and_backward_resource_contracts() {
    const auto automaton = shortest_time_automaton(false);
    ReachabilityOptions reach_limited;
    reach_limited.max_nodes = 1;
    const auto partial_graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}}, reach_limited);
    const auto no_backward = tamonitor::pta::solve_mixed(
        automaton, partial_graph, CostModel{}, SolverOptions{});
    const auto unknown = no_backward.query(0, one_clock(0));
    require(no_backward.status() ==
                MixedSolverStatus::IncompleteForwardResourceLimit &&
                no_backward.all_pieces().at(0).empty() &&
                unknown.reachable_domain == ReachabilityMembership::Unknown &&
                unknown.cost.kind == CostValueKind::Unknown,
            "incomplete forward 后不得启动或伪装 exact backward");

    const auto complete_graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    SolverOptions piece_limited;
    piece_limited.max_pieces = 1;
    const auto partial_backward = tamonitor::pta::solve_mixed(
        automaton, complete_graph, CostModel{}, piece_limited);
    require(partial_backward.status() ==
                MixedSolverStatus::IncompleteBackwardResourceLimit &&
                !partial_backward.exact() &&
                partial_backward.query(0, one_clock(0)).cost.kind ==
                    CostValueKind::Unknown,
            "backward piece limit 不得输出伪最优值");
}

void test_reachable_positive_infinity() {
    const auto any = universe(2);
    const WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, any, "reachable-dead-end"),
         WeightedLocation(1, any, "unreachable-goal")},
        {});
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, CostModel{}, SolverOptions{});
    const auto pure = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, CostModel{}, SolverOptions{});
    const auto result = mixed.query(0, one_clock(0));
    const auto pure_result = pure.query(0, one_clock(0));
    require(mixed.status() == MixedSolverStatus::Unreachable && mixed.exact() &&
                result.reachable_domain == ReachabilityMembership::Reachable &&
                result.cost.kind == CostValueKind::PositiveInfinity &&
                result.cost.exact &&
                pure_result.kind == CostValueKind::PositiveInfinity,
            "mixed 必须把 reachable-but-no-Goal 报告为精确 +infinity");
}

void test_inclusion_reused_arc_preserves_cheaper_path() {
    auto invariant = universe(2);
    invariant.restrict(1, 0, pardibaal::bound_t::non_strict(2));
    auto narrow = universe(2);
    narrow.restrict(0, 1, pardibaal::bound_t::non_strict(-1));
    const WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, invariant, "source"),
         WeightedLocation(1, invariant, "goal")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, universe(2), {}, "broad"),
         WeightedEdge(EdgeId{0, 1}, 0, 1, narrow, {}, "narrow-cheap")});
    CostModel costs;
    costs.default_location_rate = 1;
    costs.default_edge_cost = 0;
    costs.edge_costs[EdgeId{0, 0}] = 5;

    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    require(graph.nodes().size() == 2 && graph.arcs().size() == 2 &&
                graph.statistics().inclusion_reuses == 1,
            "broad/narrow Post 应收敛到一个 Goal node 但保留两 arc");
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, costs, SolverOptions{});
    const auto result = mixed.query(0, one_clock(0));
    require(result.cost.kind == CostValueKind::Finite &&
                result.cost.value == BigRational(1) &&
                result.next_edge == EdgeId{0, 1},
            "inclusion reuse 丢失了等待 1 后走 narrow cheap arc 的最优路径");
}

void test_graph_is_bound_to_exact_automaton_structure() {
    auto guard_five = universe(2);
    guard_five.restrict(0, 1, pardibaal::bound_t::non_strict(-5));
    auto guard_one = universe(2);
    guard_one.restrict(0, 1, pardibaal::bound_t::non_strict(-1));
    const WeightedAutomatonView source(
        2, 0,
        {WeightedLocation(0, universe(2)),
         WeightedLocation(1, universe(2))},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, guard_five, {}, "edge")});
    const WeightedAutomatonView incompatible(
        2, 0,
        {WeightedLocation(0, universe(2)),
         WeightedLocation(1, universe(2))},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, guard_one, {}, "edge")});
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        source, GoalSpec{{1}});
    require(graph.compatible_with(source) &&
                !graph.compatible_with(incompatible),
            "reachable snapshot 未精确绑定 invariant/guard/reset 结构");
    bool rejected = false;
    try {
        (void)tamonitor::pta::solve_mixed(
            incompatible, graph, CostModel{}, SolverOptions{});
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected,
            "mixed solver 接受了由另一 guard 自动机生成的 graph");
}

WeightedAutomatonView competing_arc_order(bool narrow_first_by_edge_id) {
    auto invariant = universe(2);
    invariant.restrict(1, 0, pardibaal::bound_t::non_strict(2));
    auto narrow_guard = universe(2);
    narrow_guard.restrict(0, 1, pardibaal::bound_t::non_strict(-1));
    const EdgeId broad_id{0, narrow_first_by_edge_id ? 1U : 0U};
    const EdgeId narrow_id{0, narrow_first_by_edge_id ? 0U : 1U};
    WeightedEdge broad(broad_id, 0, 1, universe(2), {}, "broad");
    WeightedEdge narrow(
        narrow_id, 0, 1, narrow_guard, {}, "narrow-cheap");
    std::vector<WeightedEdge> edges;
    if (narrow_first_by_edge_id) {
        // 同时让 vector 存储与 EdgeId 顺序相反，确认实现只依赖稳定 ID。
        edges.push_back(std::move(broad));
        edges.push_back(std::move(narrow));
    } else {
        edges.push_back(std::move(broad));
        edges.push_back(std::move(narrow));
    }
    return WeightedAutomatonView(
        2, 0,
        {WeightedLocation(0, invariant), WeightedLocation(1, invariant)},
        std::move(edges));
}

void test_mixed_subsumption_and_queue_order_independence() {
    CostModel normal_costs;
    normal_costs.default_location_rate = 1;
    normal_costs.default_edge_cost = 0;
    normal_costs.edge_costs[EdgeId{0, 0}] = 5;
    CostModel reversed_costs = normal_costs;
    reversed_costs.edge_costs.clear();
    reversed_costs.edge_costs[EdgeId{0, 1}] = 5;
    const auto normal_automaton = competing_arc_order(false);
    const auto reversed_automaton = competing_arc_order(true);
    const auto normal_graph = tamonitor::pta::compute_reachable_zone_graph(
        normal_automaton, GoalSpec{{1}});
    const auto reversed_graph = tamonitor::pta::compute_reachable_zone_graph(
        reversed_automaton, GoalSpec{{1}});
    SolverOptions pruned;
    SolverOptions unpruned;
    unpruned.enable_subsumption = false;
    const auto normal = tamonitor::pta::solve_mixed(
        normal_automaton, normal_graph, normal_costs, pruned);
    const auto reversed = tamonitor::pta::solve_mixed(
        reversed_automaton, reversed_graph, reversed_costs, pruned);
    const auto no_subsumption = tamonitor::pta::solve_mixed(
        normal_automaton, normal_graph, normal_costs, unpruned);
    for (const auto value : {0, 1, 2}) {
        const auto expected = normal.query(0, one_clock(value));
        const auto reordered = reversed.query(0, one_clock(value));
        const auto unpruned_value = no_subsumption.query(0, one_clock(value));
        require(expected.cost.kind == reordered.cost.kind &&
                    expected.cost.kind == unpruned_value.cost.kind &&
                    expected.cost.value == reordered.cost.value &&
                    expected.cost.value == unpruned_value.cost.value &&
                    expected.cost.attained == reordered.cost.attained &&
                    expected.cost.attained == unpruned_value.cost.attained,
                "mixed 的 edge 存储顺序或 subsumption 改变了逐点最优值");
    }
}

void test_signed_contract_and_unbounded_region() {
    const auto any = universe(2);
    const WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, any, "negative-rate"),
         WeightedLocation(1, any, "goal")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, any, {}, "finish")});
    CostModel costs;
    costs.default_location_rate = 0;
    costs.location_rates[0] = -1;
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});

    const auto rejected = tamonitor::pta::solve_mixed(
        automaton, graph, costs, SolverOptions{});
    require(rejected.status() == MixedSolverStatus::AssumptionRequired &&
                rejected.query(0, one_clock(0)).cost.kind ==
                    CostValueKind::Unknown,
            "signed mixed 模型未声明 lower bound 必须拒绝");

    SolverOptions assumed;
    assumed.assume_lower_bounded = true;
    const auto unbounded = tamonitor::pta::solve_mixed(
        automaton, graph, costs, assumed);
    const auto pure_unbounded = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, costs, assumed);
    const auto result = unbounded.query(0, one_clock(0));
    require(unbounded.status() == MixedSolverStatus::UnboundedBelow &&
                result.cost.kind == CostValueKind::NegativeInfinity &&
                result.cost.exact && result.next_arc == 0 &&
                pure_unbounded.query(0, one_clock(0)).kind ==
                    CostValueKind::NegativeInfinity,
            "reachable 负 rate 无界 delay 应得到精确 -infinity region");
}

void test_unreachable_negative_region_does_not_pollute_initial() {
    const auto any = universe(2);
    const WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, any, "initial"),
         WeightedLocation(1, any, "goal"),
         WeightedLocation(2, any, "unreachable-negative")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, any, {}, "finite"),
         WeightedEdge(EdgeId{2, 0}, 2, 1, any, {}, "negative")});
    CostModel costs;
    costs.default_location_rate = 0;
    costs.location_rates[2] = -1;
    SolverOptions assumed;
    assumed.assume_lower_bounded = true;
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, costs, assumed);
    const auto pure = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, costs, assumed);
    require(mixed.query(0, one_clock(0)).cost.kind == CostValueKind::Finite &&
                mixed.query(0, one_clock(0)).cost.value == BigRational(0) &&
                pure.query(0, one_clock(0)).kind == CostValueKind::Finite &&
                mixed.query(2, one_clock(0)).reachable_domain ==
                    ReachabilityMembership::OutsideReachableDomain &&
                pure.query(2, one_clock(0)).kind ==
                    CostValueKind::NegativeInfinity,
            "unreachable negative-rate region 不得污染 mixed 初始 cost");
}

bool monitaal_reachable_within(
    const monitaal::TA& automaton,
    monitaal::symb_time_t bound) {
    monitaal::symbolic_state_map_t<monitaal::symbolic_state_t> targets;
    const auto observer_clock = automaton.number_of_clocks();
    for (const auto& [location_id, location] : automaton.locations()) {
        if (!location.is_accept()) {
            continue;
        }
        auto target = monitaal::symbolic_state_t::unconstrained(
            location_id, automaton.number_of_clocks());
        target.restrict(location.invariant());
        target.restrict(monitaal::constraints_t{
            pardibaal::difference_bound_t::upper_non_strict(
                observer_clock, bound)});
        targets.insert(std::move(target));
    }
    auto predecessors =
        monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(targets, automaton);
    for (const auto& [_, target] : targets) {
        predecessors.insert(target);
    }
    if (!predecessors.has_state(automaton.initial_location())) {
        return false;
    }
    const monitaal::symbolic_state_t initial(
        automaton.initial_location(), automaton.number_of_clocks());
    return initial.is_included_in(predecessors.at(automaton.initial_location()));
}

void test_independent_observer_clock_oracle() {
    monitaal::clock_map_t clocks{{0, "0"}, {1, "x"}};
    const monitaal::TA ordinary(
        "mixed-observer",
        clocks,
        {monitaal::location_t(false, 0, "source", {}),
         monitaal::location_t(true, 1, "goal", {})},
        {monitaal::edge_t(
            0, 1,
            monitaal::constraints_t{
                pardibaal::difference_bound_t::lower_non_strict(1, 3)},
            {}, "finish")},
        0);
    const auto automaton = shortest_time_automaton(false);
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    const auto mixed = tamonitor::pta::solve_mixed(
        automaton, graph, CostModel{}, SolverOptions{});
    const auto result = mixed.query(0, one_clock(0));
    require(result.cost.value == BigRational(3) &&
                !monitaal_reachable_within(ordinary, 2) &&
                monitaal_reachable_within(ordinary, 3),
            "mixed cost=3 与 MoniTAal observer-clock oracle 不一致");
}

}  // namespace

int main() {
    try {
        test_mixed_shortest_time_domain_and_witness();
        test_nonzero_cost_and_strict_infimum();
        test_forward_and_backward_resource_contracts();
        test_reachable_positive_infinity();
        test_inclusion_reused_arc_preserves_cheaper_path();
        test_graph_is_bound_to_exact_automaton_structure();
        test_mixed_subsumption_and_queue_order_independence();
        test_signed_contract_and_unbounded_region();
        test_unreachable_negative_region_does_not_pollute_initial();
        test_independent_observer_clock_oracle();
        std::cout << "TAMonitor mixed priced solver tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "TAMonitor mixed priced solver test failure: "
                  << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
