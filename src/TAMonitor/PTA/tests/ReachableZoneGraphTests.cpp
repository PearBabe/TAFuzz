// 本文件验证 exact forward Post、strict DBM、Goal 截断与单向 inclusion 图语义。

#include "ReachableZoneGraph.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using tamonitor::pta::EdgeId;
using tamonitor::pta::GoalSpec;
using tamonitor::pta::ReachabilityOptions;
using tamonitor::pta::ReachabilityStatus;
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

void require_equal(
    const pardibaal::DBM& actual,
    const pardibaal::DBM& expected,
    const std::string& message) {
    require(actual.relation(expected).is_equal(), message);
}

WeightedAutomatonView make_diagonal_reset_automaton(bool strict_lower) {
    constexpr pardibaal::dim_t dimension = 3;  // 0, x, y

    auto source_invariant = universe(dimension);
    source_invariant.restrict(
        1, 0, pardibaal::bound_t::non_strict(2));  // x <= 2

    auto target_invariant = universe(dimension);
    target_invariant.restrict(
        1, 0, pardibaal::bound_t::non_strict(4));  // x <= 4

    auto guard = universe(dimension);
    guard.restrict(
        0, 1,
        strict_lower
            ? pardibaal::bound_t::strict(-1)      // x > 1
            : pardibaal::bound_t::non_strict(-1));  // x >= 1

    return WeightedAutomatonView(
        dimension,
        0,
        {WeightedLocation(0, source_invariant, "source"),
         WeightedLocation(1, target_invariant, "goal")},
        {WeightedEdge(
            EdgeId{0, 0}, 0, 1, guard,
            std::vector<pardibaal::dim_t>{2}, "reset-y")});
}

void test_reset_diagonal_post(bool strict_lower) {
    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        make_diagonal_reset_automaton(strict_lower), GoalSpec{{1}});

    require(graph.status() == ReachabilityStatus::Complete && graph.exact(),
            "两时钟 exact-forward 应完整终止");
    require(graph.initial_node() == 0 && graph.nodes().size() == 2 &&
                graph.arcs().size() == 1,
            "两时钟模型应得到两节点一 arc");

    auto expected_source = universe(3);
    expected_source.restrict(1, 0, pardibaal::bound_t::non_strict(2));
    expected_source.restrict(1, 2, pardibaal::bound_t::le_zero());
    expected_source.restrict(2, 1, pardibaal::bound_t::le_zero());
    expected_source.close();
    require_equal(
        graph.node(0).zone, expected_source,
        "初始 Future 未保持 x=y 或 source invariant");

    auto expected_fire = expected_source;
    expected_fire.restrict(
        0, 1,
        strict_lower
            ? pardibaal::bound_t::strict(-1)
            : pardibaal::bound_t::non_strict(-1));

    auto expected_entry = universe(3);
    expected_entry.restrict(2, 0, pardibaal::bound_t::le_zero());
    expected_entry.restrict(0, 2, pardibaal::bound_t::le_zero());
    expected_entry.restrict(1, 0, pardibaal::bound_t::non_strict(2));
    expected_entry.restrict(
        0, 1,
        strict_lower
            ? pardibaal::bound_t::strict(-1)
            : pardibaal::bound_t::non_strict(-1));

    auto expected_post = universe(3);
    expected_post.restrict(1, 0, pardibaal::bound_t::non_strict(4));
    expected_post.restrict(1, 2, pardibaal::bound_t::non_strict(2));
    expected_post.restrict(
        2, 1,
        strict_lower
            ? pardibaal::bound_t::strict(-1)
            : pardibaal::bound_t::non_strict(-1));

    const auto& arc = graph.arc(0);
    require_equal(arc.fire_zone, expected_fire,
                  "fire_zone 不等于 source.zone ∩ guard");
    require_equal(arc.entry_zone, expected_entry,
                  "entry_zone 未正确执行 y:=0 或 target invariant");
    require_equal(arc.post_zone, expected_post,
                  "post_zone 未保持 reset 生成的 x-y 对角约束");
    require_equal(graph.node(1).zone, expected_post,
                  "新 target node 不等于精确 Post");

    const auto strict_bound = arc.post_zone.at(2, 1);
    require(strict_bound.is_strict() == strict_lower &&
                strict_bound.get_bound() == -1,
            "strict guard 在 reset/future 后未精确传播到 x-y lower bound");
}

void test_goal_cutoff() {
    constexpr pardibaal::dim_t dimension = 2;
    const auto any = universe(dimension);
    WeightedAutomatonView automaton(
        dimension,
        0,
        {WeightedLocation(0, any), WeightedLocation(1, any),
         WeightedLocation(2, any)},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, any, {}, "enter-goal"),
         WeightedEdge(EdgeId{1, 0}, 1, 2, any, {}, "leave-goal")});

    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    require(graph.exact() && graph.nodes().size() == 2 &&
                graph.arcs().size() == 1,
            "Goal 节点不应继续展开 outgoing edge");
    require(graph.node(1).is_goal && graph.outgoing_arcs(1).empty() &&
                graph.statistics().goal_cutoffs == 1,
            "Goal cutoff 节点标记或统计错误");
}

void test_one_way_inclusion_retains_arc_domains() {
    constexpr pardibaal::dim_t dimension = 2;  // 0, x
    auto source_invariant = universe(dimension);
    source_invariant.restrict(1, 0, pardibaal::bound_t::non_strict(5));
    auto target_invariant = source_invariant;

    auto broad_guard = universe(dimension);
    broad_guard.restrict(0, 1, pardibaal::bound_t::non_strict(-1));
    auto narrow_guard = universe(dimension);
    narrow_guard.restrict(0, 1, pardibaal::bound_t::non_strict(-2));

    // 故意反转 vector 顺序；算法必须按稳定 EdgeId 先处理 broad。
    WeightedAutomatonView automaton(
        dimension,
        0,
        {WeightedLocation(0, source_invariant),
         WeightedLocation(1, target_invariant)},
        {WeightedEdge(EdgeId{0, 1}, 0, 1, narrow_guard, {}, "narrow"),
         WeightedEdge(EdgeId{0, 0}, 0, 1, broad_guard, {}, "broad")});

    const auto graph = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}});
    require(graph.exact() && graph.nodes().size() == 2 &&
                graph.arcs().size() == 2,
            "candidate ⊆ existing 时应复用 node 但保留两条 arc");
    require(graph.statistics().inclusion_reuses == 1 &&
                graph.incoming_arcs(1).size() == 2,
            "单向 inclusion convergence 未记录全部 incoming arc");
    require(graph.arc(0).edge.ordinal == 0 &&
                graph.arc(1).edge.ordinal == 1,
            "forward expansion 未按稳定 EdgeId 顺序");

    const auto broad_relation = graph.arc(0).post_zone.relation(
        graph.node(1).zone);
    const auto narrow_relation = graph.arc(1).post_zone.relation(
        graph.node(1).zone);
    require(broad_relation.is_equal() && narrow_relation.is_subset(),
            "arc.post_zone 必须保留各 edge 的实际像，不能替换为 target.zone");
    require(graph.support(1).is_equal(graph.node(1).zone),
            "location support 不等于可达 node Zone 并");
}

WeightedAutomatonView make_single_edge_automaton() {
    const auto any = universe(2);
    return WeightedAutomatonView(
        2, 0,
        {WeightedLocation(0, any), WeightedLocation(1, any)},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, any, {}, "edge")});
}

void test_resource_limits_never_report_exact() {
    const auto automaton = make_single_edge_automaton();

    ReachabilityOptions node_limited;
    node_limited.max_nodes = 1;
    const auto nodes = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}}, node_limited);
    require(nodes.status() == ReachabilityStatus::ResourceLimit &&
                !nodes.exact() && nodes.statistics().node_limit_hit &&
                nodes.nodes().size() == 1 && nodes.arcs().empty(),
            "node limit 不得被报告为完整 forward graph");

    ReachabilityOptions arc_limited;
    arc_limited.max_arcs = 0;
    const auto arcs = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{1}}, arc_limited);
    require(arcs.status() == ReachabilityStatus::ResourceLimit &&
                !arcs.exact() && arcs.statistics().arc_limit_hit &&
                arcs.nodes().size() == 1 && arcs.arcs().empty(),
            "arc limit 后不应留下孤立 target node 或伪 exact 状态");

    ReachabilityOptions zero_arc_but_goal;
    zero_arc_but_goal.max_arcs = 0;
    const auto initial_goal = tamonitor::pta::compute_reachable_zone_graph(
        automaton, GoalSpec{{0}}, zero_arc_but_goal);
    require(initial_goal.exact() && initial_goal.nodes().size() == 1 &&
                initial_goal.arcs().empty(),
            "初始 Goal 不需要 arc 容量，应完整终止");
}

}  // namespace

int main() {
    try {
        test_reset_diagonal_post(false);
        test_reset_diagonal_post(true);
        test_goal_cutoff();
        test_one_way_inclusion_retains_arc_domains();
        test_resource_limits_never_report_exact();
        std::cout << "TAMonitor reachable-zone graph tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "TAMonitor reachable-zone graph test failure: "
                  << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
