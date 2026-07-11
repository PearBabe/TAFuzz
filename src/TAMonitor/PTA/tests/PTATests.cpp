// 本文件用独立小模型验证 Parrot--Lime 后向 priced-DBM 的局部公式与全局固定点。

#include "BackwardPricedSolver.h"
#include "ExactDominance.h"
#include "PricedDBMOps.h"

#include <Fixpoint.h>
#include <TA.h>
#include <pardibaal/Federation.h>
#include <pardibaal/difference_bound_t.h>
#include <z3++.h>

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

using tamonitor::pta::AnalysisSnapshot;
using tamonitor::pta::BigInt;
using tamonitor::pta::BigRational;
using tamonitor::pta::CostModel;
using tamonitor::pta::CostValueKind;
using tamonitor::pta::DelayWitnessKind;
using tamonitor::pta::DominanceResult;
using tamonitor::pta::EdgeId;
using tamonitor::pta::ExactDominance;
using tamonitor::pta::GoalSpec;
using tamonitor::pta::LocationId;
using tamonitor::pta::RationalValuation;
using tamonitor::pta::SolverOptions;
using tamonitor::pta::SolverStatus;
using tamonitor::pta::TimePredecessorResult;
using tamonitor::pta::WeightedAutomatonView;
using tamonitor::pta::WeightedEdge;
using tamonitor::pta::WeightedLocation;
using tamonitor::pta::WeightedZone;

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

pardibaal::DBM universe(pardibaal::dim_t dimension) {
    return pardibaal::DBM::unconstrained(dimension);
}

pardibaal::DBM interval_zone(
    pardibaal::val_t lower,
    pardibaal::val_t upper,
    bool strict_lower = false,
    bool strict_upper = false) {
    auto zone = universe(2);
    zone.restrict(0, 1, strict_lower
        ? pardibaal::bound_t::strict(-lower)
        : pardibaal::bound_t::non_strict(-lower));
    zone.restrict(1, 0, strict_upper
        ? pardibaal::bound_t::strict(upper)
        : pardibaal::bound_t::non_strict(upper));
    zone.close();
    return zone;
}

RationalValuation one_clock(pardibaal::val_t value) {
    return {BigRational(0), BigRational(BigInt(value))};
}

BigRational best_weight(
    const TimePredecessorResult& result,
    const RationalValuation& valuation,
    bool* attained = nullptr,
    DelayWitnessKind* witness = nullptr) {
    std::optional<BigRational> best;
    bool best_attained = false;
    DelayWitnessKind best_witness = DelayWitnessKind::ZERO;
    for (const auto& piece : result.pieces) {
        if (!tamonitor::pta::contains(piece.weighted_zone, valuation)) {
            continue;
        }
        const auto value = tamonitor::pta::weight_at(piece.weighted_zone, valuation);
        if (!best.has_value() || value > *best ||
            (value == *best && piece.weighted_zone.attained && !best_attained)) {
            best = value;
            best_attained = piece.weighted_zone.attained;
            best_witness = piece.witness_kind;
        }
    }
    require(best.has_value(), "valuation 不在任何 time-predecessor piece 中");
    if (attained != nullptr) {
        *attained = best_attained;
    }
    if (witness != nullptr) {
        *witness = best_witness;
    }
    return *best;
}

void test_weighted_zone_primitives() {
    WeightedZone weighted(interval_zone(1, 3), BigInt(5), {BigInt(0), BigInt(2)});
    require(tamonitor::pta::weight_at(weighted, one_clock(2)) == BigRational(7),
            "Definition 3 weight evaluation 错误");

    auto restriction = universe(2);
    restriction.restrict(0, 1, pardibaal::bound_t::non_strict(-2));
    auto rebased = tamonitor::pta::intersection(weighted, restriction);
    require(rebased.has_value() && rebased->offset_weight == 7,
            "Definition 5 rebase 未保持全局仿射函数");
    require(tamonitor::pta::weight_at(*rebased, one_clock(3)) == BigRational(9),
            "rebase 后 valuation weight 改变");

    WeightedZone reset_target(interval_zone(0, 2), BigInt(4), {BigInt(0), BigInt(3)});
    auto reset = tamonitor::pta::inverse_reset(reset_target, {1});
    require(reset.has_value() && reset->rates[1] == 0 &&
            tamonitor::pta::contains(*reset, one_clock(100)),
            "Definition 7 inverse reset 几何域或 gradient 错误");

    auto impossible = tamonitor::pta::inverse_reset(
        WeightedZone(interval_zone(1, 2), BigInt(0), {BigInt(0), BigInt(0)}), {1});
    require(!impossible.has_value(), "reset 到 0 不应命中 x>=1 的 target zone");

    auto two_clock_target = universe(3);
    two_clock_target.restrict(1, 0, pardibaal::bound_t::le_zero());
    two_clock_target.restrict(0, 1, pardibaal::bound_t::le_zero());
    two_clock_target.restrict(2, 0, pardibaal::bound_t::le_zero());
    two_clock_target.restrict(0, 2, pardibaal::bound_t::le_zero());
    two_clock_target.close();
    auto two_clock_reset = tamonitor::pta::inverse_reset(
        WeightedZone(two_clock_target, BigInt(11),
                     {BigInt(0), BigInt(3), BigInt(-4)}), {1, 2});
    require(two_clock_reset.has_value() && two_clock_reset->rates[1] == 0 &&
                two_clock_reset->rates[2] == 0 &&
                tamonitor::pta::contains(
                    *two_clock_reset,
                    {BigRational(0), BigRational(17), BigRational(23)}),
            "多时钟 inverse reset 必须同时 free 并消除所有 reset 斜率");

    auto correlated_target = universe(4);
    for (const auto clock : {1U, 2U}) {
        correlated_target.restrict(clock, 0, pardibaal::bound_t::le_zero());
        correlated_target.restrict(0, clock, pardibaal::bound_t::le_zero());
    }
    correlated_target.restrict(0, 3, pardibaal::bound_t::non_strict(-2));
    correlated_target.restrict(3, 0, pardibaal::bound_t::non_strict(5));
    correlated_target.restrict(1, 3, pardibaal::bound_t::non_strict(-2));
    correlated_target.restrict(3, 2, pardibaal::bound_t::non_strict(5));
    correlated_target.close();
    WeightedZone correlated(
        correlated_target, BigInt(7),
        {BigInt(0), BigInt(3), BigInt(-2), BigInt(4)});
    auto correlated_reset = tamonitor::pta::inverse_reset(correlated, {1, 2});
    const RationalValuation before_reset{
        BigRational(0), BigRational(10), BigRational(20), BigRational(3)};
    const RationalValuation after_reset{
        BigRational(0), BigRational(0), BigRational(0), BigRational(3)};
    require(correlated_reset.has_value() &&
                tamonitor::pta::weight_at(*correlated_reset, before_reset) ==
                    tamonitor::pta::weight_at(correlated, after_reset),
            "含 diagonal/非零 gradient 的多 reset 未保持 W(u[R])");

    const auto negative_edge = tamonitor::pta::subtract_edge_weight(weighted, BigInt(-7));
    require(negative_edge.offset_weight == weighted.offset_weight + 7,
            "负 edge cost 的 W 符号传播错误");
    const auto zero_edge = tamonitor::pta::subtract_edge_weight(weighted, BigInt(0));
    require(zero_edge.offset_weight == weighted.offset_weight,
            "零 edge cost 不应改变 W");
}

void test_action_and_time_predecessors() {
    WeightedZone target(interval_zone(0, 2), BigInt(-2), {BigInt(0), BigInt(0)});
    auto guard = universe(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-3));
    auto invariant = universe(2);
    invariant.restrict(1, 0, pardibaal::bound_t::non_strict(5));

    const auto action = tamonitor::pta::action_predecessor(
        target, {1}, guard, invariant, BigInt(4));
    require(action.has_value() && action->offset_weight == -6,
            "Theorem 1 未正确减去 edge cost");
    require(tamonitor::pta::contains(*action, one_clock(3)) &&
            !tamonitor::pta::contains(*action, one_clock(2)),
            "Theorem 1 guard/invariant 几何域错误");

    auto strict_guard = universe(2);
    strict_guard.restrict(0, 1, pardibaal::bound_t::strict(-2));
    auto strict_invariant = universe(2);
    strict_invariant.restrict(1, 0, pardibaal::bound_t::strict(4));
    const auto strict_action = tamonitor::pta::action_predecessor(
        WeightedZone(universe(2), BigInt(0), {BigInt(0), BigInt(0)}),
        {}, strict_guard, strict_invariant, BigInt(0));
    require(strict_action.has_value() &&
                tamonitor::pta::contains(
                    *strict_action,
                    {BigRational(0), BigRational(BigInt(5), BigInt(2))}) &&
                !tamonitor::pta::contains(*strict_action, one_clock(2)) &&
                !tamonitor::pta::contains(*strict_action, one_clock(4)),
            "strict guard/source invariant 的 action predecessor 几何域错误");

    const auto earliest = tamonitor::pta::time_predecessor(
        *action, invariant, BigInt(2));
    bool attained = false;
    DelayWitnessKind witness = DelayWitnessKind::ZERO;
    require(best_weight(earliest, one_clock(1), &attained, &witness) == BigRational(-10),
            "Theorem 2 earliest-delay cost 错误");
    require(attained && witness == DelayWitnessKind::LOWER_FACET,
            "earliest-delay witness 错误");

    const auto flat = tamonitor::pta::time_predecessor(*action, invariant, BigInt(0));
    require(best_weight(flat, one_clock(1), &attained, &witness) == BigRational(-6),
            "p=sum(r) 时 weight 应与 delay 无关");
    require(attained && witness == DelayWitnessKind::LOWER_FACET,
            "p=sum(r) 的 target 外 valuation 不能伪造 ZERO witness");

    WeightedZone latest(interval_zone(2, 4), BigInt(0), {BigInt(0), BigInt(3)});
    const auto upper = tamonitor::pta::time_predecessor(latest, universe(2), BigInt(1));
    require(best_weight(upper, one_clock(1), &attained, &witness) == BigRational(3),
            "Theorem 2 latest-delay cost 错误");
    require(attained && witness == DelayWitnessKind::UPPER_FACET,
            "latest-delay witness 错误");

    WeightedZone strict_latest(
        interval_zone(2, 4, false, true), BigInt(0), {BigInt(0), BigInt(3)});
    const auto strict_upper = tamonitor::pta::time_predecessor(
        strict_latest, universe(2), BigInt(1));
    require(best_weight(strict_upper, one_clock(1), &attained) == BigRational(3) &&
            !attained,
            "严格 upper facet 应返回相同 supremum 但 attained=false");

    WeightedZone strict_earliest(
        interval_zone(2, 4, true, false), BigInt(0), {BigInt(0), BigInt(0)});
    const auto strict_lower = tamonitor::pta::time_predecessor(
        strict_earliest, universe(2), BigInt(1));
    require(best_weight(strict_lower, one_clock(0), &attained) == BigRational(-2) &&
                !attained,
            "严格 lower facet 应返回 epsilon 最优值且 attained=false");

    auto no_upper_zone = universe(2);
    no_upper_zone.restrict(0, 1, pardibaal::bound_t::non_strict(-2));
    WeightedZone no_upper(no_upper_zone, BigInt(0), {BigInt(0), BigInt(2)});
    const auto unbounded = tamonitor::pta::time_predecessor(
        no_upper, universe(2), BigInt(1));
    require(unbounded.unbounded_below && unbounded.unbounded_domain.has_value() &&
            tamonitor::pta::contains(*unbounded.unbounded_domain, one_clock(0)),
            "无 upper facet 必须返回带精确定义域的 -infinity marker");

    // 非严格 active facet 可能同时撞上另一个严格约束；attained 必须按
    // valuation 域拆分，而不能只查看所选 facet 自身的 strictness。
    auto mixed_strict_zone = universe(3);
    mixed_strict_zone.restrict(1, 0, pardibaal::bound_t::non_strict(5));
    mixed_strict_zone.restrict(2, 0, pardibaal::bound_t::strict(5));
    WeightedZone mixed_strict(
        mixed_strict_zone, BigInt(0), {BigInt(0), BigInt(2), BigInt(0)});
    const auto mixed = tamonitor::pta::time_predecessor(
        mixed_strict, universe(3), BigInt(1));
    require(best_weight(mixed, {BigRational(0), BigRational(0), BigRational(0)},
                        &attained) == BigRational(5) && !attained,
            "同时撞严格 y<5 的 supremum 应为 5 且不可达到");
    require(best_weight(mixed, {BigRational(0), BigRational(1), BigRational(0)},
                        &attained) == BigRational(6) && attained,
            "只撞非严格 x<=5 的最优值应可达到");
}

void test_figure_two_split() {
    auto zone = universe(3);
    zone.restrict(0, 1, pardibaal::bound_t::non_strict(-3)); // x>=3
    zone.restrict(0, 2, pardibaal::bound_t::non_strict(-3)); // y>=3
    zone.restrict(2, 0, pardibaal::bound_t::non_strict(9));  // y<=9
    zone.restrict(1, 0, pardibaal::bound_t::non_strict(10)); // x<=10
    zone.restrict(2, 1, pardibaal::bound_t::non_strict(4));  // y-x<=4
    zone.restrict(1, 2, pardibaal::bound_t::non_strict(3));  // x-y<=3
    zone.close();
    WeightedZone weighted(zone, BigInt(-3), {BigInt(0), BigInt(2), BigInt(-1)});
    const auto result = tamonitor::pta::time_predecessor(weighted, universe(3), BigInt(3));
    require(result.pieces.size() == 3,
            "论文 Fig.2 应分裂为原 zone 与两个 lower-facet pieces");
    std::size_t zero_pieces = 0;
    std::size_t lower_pieces = 0;
    for (const auto& piece : result.pieces) {
        zero_pieces += piece.witness_kind == DelayWitnessKind::ZERO ? 1 : 0;
        lower_pieces += piece.witness_kind == DelayWitnessKind::LOWER_FACET ? 1 : 0;
    }
    require(zero_pieces == 1 && lower_pieces == 2,
            "论文 Fig.2 必须是原 zone 加两个 lower-facet past");
    require(best_weight(result, {BigRational(0), BigRational(1), BigRational(1)}) ==
                BigRational(-9),
            "论文 Fig.2 代表点的反向 weight 错误");

    auto expected_domain = zone;
    expected_domain.past();
    expected_domain.close();
    for (int x = 0; x <= 10; ++x) {
        for (int y = 0; y <= 9; ++y) {
            const RationalValuation valuation{
                BigRational(0), BigRational(x), BigRational(y)};
            if (!tamonitor::pta::contains(expected_domain, valuation)) {
                continue;
            }
            const int delay = std::max({0, 3 - x, 3 - y});
            const BigRational expected(BigInt(2 * x - y - 2 * delay - 6));
            require(best_weight(result, valuation) == expected,
                    "论文 Fig.2 分片未在离散覆盖点保持 Lemma 3 的逐点 weight");
        }
    }
}

void test_exact_dominance() {
    WeightedZone dominator(interval_zone(0, 5), BigInt(0), {BigInt(0), BigInt(0)});
    WeightedZone worse(interval_zone(0, 5), BigInt(-1), {BigInt(0), BigInt(0)});
    WeightedZone better(interval_zone(0, 5), BigInt(1), {BigInt(0), BigInt(0)});
    ExactDominance dominance;
    require(dominance.check(dominator, worse) == DominanceResult::Dominated,
            "相等 DBM 上较差 weight 必须被支配");
    require(dominance.check(dominator, better) == DominanceResult::NotDominated,
            "较优 candidate 不得被错误剪枝");

    WeightedZone unattained(interval_zone(0, 5), BigInt(0),
                            {BigInt(0), BigInt(0)}, false);
    WeightedZone attained(interval_zone(0, 5), BigInt(0),
                          {BigInt(0), BigInt(0)}, true);
    require(dominance.check(unattained, attained) == DominanceResult::NotDominated,
            "unattained label 不得剪掉等值 attained candidate");
    require(dominance.check(attained, unattained) == DominanceResult::Dominated,
            "等值 attained label 可以支配 unattained candidate");

    WeightedZone crossing_a(interval_zone(0, 2), BigInt(0),
                            {BigInt(0), BigInt(1)});
    WeightedZone crossing_b(interval_zone(0, 2), BigInt(2),
                            {BigInt(0), BigInt(-1)});
    require(dominance.check(crossing_a, crossing_b) ==
                DominanceResult::NotDominated &&
                dominance.check(crossing_b, crossing_a) ==
                DominanceResult::NotDominated,
            "定义域相同但 affine weight 交叉时双方都不得被剪枝");
}

void require_exact_time_geometry(
    const WeightedZone& target,
    const pardibaal::DBM& invariant,
    const BigInt& rate,
    const std::string& context) {
    const auto result = tamonitor::pta::time_predecessor(target, invariant, rate);
    require(!result.unbounded_below, context + ": bounded target 不应报告无界成本");

    pardibaal::Federation actual;
    for (const auto& piece : result.pieces) {
        actual.add(piece.weighted_zone.zone);
    }
    auto expected = target.zone;
    expected.intersection(invariant);
    expected.close();
    expected.past();
    expected.intersection(invariant);
    expected.close();
    require(actual.is_exact_equal(expected),
            context + ": priced-time pieces 的几何并集不等于普通 DBM past");
}

void test_time_predecessor_geometry() {
    WeightedZone strict_interval(
        interval_zone(2, 7, true, true), BigInt(3),
        {BigInt(0), BigInt(2)});
    auto interval_invariant = interval_zone(0, 9);
    require_exact_time_geometry(
        strict_interval, interval_invariant, BigInt(4), "strict lower branch");
    require_exact_time_geometry(
        strict_interval, interval_invariant, BigInt(1), "strict upper branch");

    auto diagonal = universe(3);
    diagonal.restrict(0, 1, pardibaal::bound_t::non_strict(-2));
    diagonal.restrict(0, 2, pardibaal::bound_t::strict(-1));
    diagonal.restrict(1, 0, pardibaal::bound_t::non_strict(6));
    diagonal.restrict(2, 0, pardibaal::bound_t::strict(5));
    diagonal.restrict(1, 2, pardibaal::bound_t::non_strict(2));
    diagonal.restrict(2, 1, pardibaal::bound_t::non_strict(3));
    diagonal.close();
    auto invariant = universe(3);
    invariant.restrict(1, 0, pardibaal::bound_t::non_strict(8));
    invariant.restrict(2, 0, pardibaal::bound_t::non_strict(8));
    invariant.close();
    WeightedZone two_clock(
        diagonal, BigInt(-4), {BigInt(0), BigInt(2), BigInt(-1)});
    require_exact_time_geometry(
        two_clock, invariant, BigInt(3), "two-clock diagonal lower branch");
    require_exact_time_geometry(
        two_clock, invariant, BigInt(0), "two-clock diagonal upper branch");
}

WeightedAutomatonView one_edge_automaton(
    pardibaal::DBM guard,
    BigInt source_rate,
    bool connect_initial = true) {
    constexpr LocationId initial = 0;
    constexpr LocationId source = 1;
    constexpr LocationId goal = 2;
    std::vector<WeightedLocation> locations;
    locations.emplace_back(initial, universe(2));
    locations.emplace_back(source, universe(2));
    locations.emplace_back(goal, universe(2));
    std::vector<WeightedEdge> edges;
    if (connect_initial) {
        edges.emplace_back(EdgeId{initial, 0}, initial, source, universe(2),
                           std::vector<pardibaal::dim_t>{});
    }
    edges.emplace_back(EdgeId{source, 0}, source, goal, std::move(guard),
                       std::vector<pardibaal::dim_t>{});
    (void)source_rate;
    return WeightedAutomatonView(2, initial, std::move(locations), std::move(edges));
}

void test_solver_shortest_time_and_limits() {
    auto guard = universe(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-3));
    auto automaton = one_edge_automaton(std::move(guard), BigInt(1));
    CostModel costs;
    costs.default_location_rate = 1;
    costs.default_edge_cost = 0;
    const auto snapshot = tamonitor::pta::solve(
        automaton, GoalSpec{{2}}, costs, SolverOptions{});
    const auto value = snapshot.query(0, one_clock(0));
    require(snapshot.status() == SolverStatus::Complete && snapshot.exact(),
            "非负一边模型应完成 fixed point");
    require(value.kind == CostValueKind::Finite && value.value == BigRational(3),
            "默认 rate=1/edge=0 应得到最短剩余时间 3");
    require(!value.lower_bound_assumed,
            "非负模型不应伪称依赖用户 lower-bound 假设");

    SolverOptions limited;
    limited.max_pieces = 1;
    const auto partial = tamonitor::pta::solve(
        automaton, GoalSpec{{2}}, costs, limited);
    require(partial.status() == SolverStatus::ResourceLimit && !partial.exact(),
            "max_pieces 截断不得伪装成 complete");

    // accepted 恰好达到上限但 worklist 已空时仍应 Complete，而不是误报截断。
    WeightedAutomatonView goal_only(
        2, 0, {WeightedLocation(0, universe(2))}, {});
    SolverOptions exact_boundary;
    exact_boundary.max_pieces = 1;
    const auto one_piece = tamonitor::pta::solve(
        goal_only, GoalSpec{{0}}, costs, exact_boundary);
    require(one_piece.status() == SolverStatus::Complete && one_piece.exact() &&
            one_piece.query(0, one_clock(0)).value == BigRational(0),
            "worklist 已空时 accepted==max_pieces 仍应是完整结果");
}

void test_solver_strict_infimum() {
    auto strict_guard = universe(2);
    strict_guard.restrict(0, 1, pardibaal::bound_t::strict(-2));
    WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, universe(2)), WeightedLocation(1, universe(2))},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, strict_guard, {})});
    const auto snapshot = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, CostModel{}, SolverOptions{});
    const auto result = snapshot.query(0, one_clock(0));
    require(snapshot.status() == SolverStatus::Complete &&
                result.kind == CostValueKind::Finite &&
                result.value == BigRational(2) && !result.attained && result.exact,
            "strict x>2 应返回最短时间 infimum=2 且 attained=false");
}

void test_timeout_never_reports_complete() {
    constexpr LocationId location_count = 20000;
    std::vector<WeightedLocation> locations;
    std::vector<LocationId> goals;
    locations.reserve(location_count);
    goals.reserve(location_count);
    for (LocationId location = 0; location < location_count; ++location) {
        locations.emplace_back(location, universe(2));
        goals.push_back(location);
    }
    WeightedAutomatonView automaton(2, 0, std::move(locations), {});
    SolverOptions options;
    options.timeout_ms = 1;
    const auto result = tamonitor::pta::solve(
        automaton, GoalSpec{std::move(goals)}, CostModel{}, options);
    require(result.status() == SolverStatus::ResourceLimit && !result.exact(),
            "wall-clock deadline 命中后不得因 worklist 状态误报 Complete");
}

void test_solver_domain_sensitive_unboundedness() {
    constexpr LocationId initial = 0;
    constexpr LocationId source = 1;
    constexpr LocationId goal = 2;
    std::vector<WeightedLocation> locations;
    locations.emplace_back(initial, universe(2));
    locations.emplace_back(source, universe(2));
    locations.emplace_back(goal, universe(2));

    CostModel costs;
    costs.default_location_rate = 0;
    costs.location_rates[source] = -1;
    SolverOptions options;
    options.assume_lower_bounded = true;

    // 初态能进入负费率 source：等待任意久再到 Goal，初始值必须为 -infinity。
    std::vector<WeightedEdge> connected_edges;
    connected_edges.emplace_back(EdgeId{initial, 0}, initial, source,
                                 universe(2), std::vector<pardibaal::dim_t>{});
    connected_edges.emplace_back(EdgeId{source, 0}, source, goal,
                                 universe(2), std::vector<pardibaal::dim_t>{});
    WeightedAutomatonView connected(2, initial, locations, connected_edges);
    const auto unbounded = tamonitor::pta::solve(
        connected, GoalSpec{{goal}}, costs, options);
    const auto initial_unbounded = unbounded.query(initial, one_clock(0));
    require(unbounded.status() == SolverStatus::UnboundedBelow &&
            initial_unbounded.kind == CostValueKind::NegativeInfinity,
            "覆盖初态的 -infinity marker 必须报告 UNBOUNDED_BELOW");
    require(initial_unbounded.lower_bound_assumed,
            "显式 signed-weight 契约必须传播到查询结果");
    require(initial_unbounded.witness.has_value() &&
                initial_unbounded.witness->successor_unbounded_region.has_value() &&
                !initial_unbounded.witness->unbounded_delay,
            "反传的 -infinity marker 必须指向 successor region，不能伪称当前 delay 无界");

    // source 仍可到 Goal，但从 initial 不可达；局部 -infinity 不得污染初始结果。
    std::vector<WeightedEdge> disconnected_edges;
    disconnected_edges.emplace_back(EdgeId{source, 0}, source, goal,
                                    universe(2), std::vector<pardibaal::dim_t>{});
    WeightedAutomatonView disconnected(2, initial, locations, disconnected_edges);
    const auto local_only = tamonitor::pta::solve(
        disconnected, GoalSpec{{goal}}, costs, options);
    require(local_only.status() == SolverStatus::Unreachable && local_only.exact(),
            "初态不可达的局部负无界区域不得全局误报");
    require(local_only.query(source, one_clock(0)).kind == CostValueKind::NegativeInfinity,
            "局部 -infinity 域仍须保留在离线查询表中");
}

void test_negative_weight_assumption_contract() {
    WeightedAutomatonView automaton(
        2, 0,
        {WeightedLocation(0, universe(2)), WeightedLocation(1, universe(2))},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, universe(2), {})});
    CostModel costs;
    costs.default_location_rate = 0;
    costs.default_edge_cost = -1;

    const auto rejected = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, costs, SolverOptions{});
    const auto query = rejected.query(0, one_clock(0));
    require(rejected.status() == SolverStatus::AssumptionRequired &&
                query.kind == CostValueKind::Unknown && !query.exact &&
                !query.lower_bound_assumed,
            "未声明 lower-bounded 的 signed WTA 必须返回 ASSUMPTION_REQUIRED");

    SolverOptions assumed;
    assumed.assume_lower_bounded = true;
    const auto accepted = tamonitor::pta::solve(
        automaton, GoalSpec{{1}}, costs, assumed);
    const auto value = accepted.query(0, one_clock(0));
    require(accepted.status() == SolverStatus::Complete &&
                value.kind == CostValueKind::Finite && value.value == BigRational(-1) &&
                value.lower_bound_assumed,
            "有限负 edge WTA 在显式契约下应得到精确负成本");
}

WeightedAutomatonView competing_paths(bool reverse_storage_order) {
    auto wait_two = universe(2);
    wait_two.restrict(0, 1, pardibaal::bound_t::non_strict(-2));
    auto wait_four = universe(2);
    wait_four.restrict(0, 1, pardibaal::bound_t::non_strict(-4));
    WeightedEdge expensive(EdgeId{0, 0}, 0, 1, wait_two, {});
    WeightedEdge patient(EdgeId{0, 1}, 0, 1, wait_four, {});
    std::vector<WeightedEdge> edges;
    if (reverse_storage_order) {
        edges.push_back(std::move(patient));
        edges.push_back(std::move(expensive));
    } else {
        edges.push_back(std::move(expensive));
        edges.push_back(std::move(patient));
    }
    return WeightedAutomatonView(
        2, 0,
        {WeightedLocation(0, universe(2)), WeightedLocation(1, universe(2))},
        std::move(edges));
}

void test_queue_and_subsumption_independence() {
    CostModel costs;
    costs.default_location_rate = 1;
    costs.default_edge_cost = 0;
    costs.edge_costs[EdgeId{0, 0}] = 5;
    costs.edge_costs[EdgeId{0, 1}] = 0;

    SolverOptions with_subsumption;
    SolverOptions without_subsumption;
    without_subsumption.enable_subsumption = false;
    const auto normal = tamonitor::pta::solve(
        competing_paths(false), GoalSpec{{1}}, costs, with_subsumption);
    const auto reversed = tamonitor::pta::solve(
        competing_paths(true), GoalSpec{{1}}, costs, with_subsumption);
    const auto unpruned = tamonitor::pta::solve(
        competing_paths(false), GoalSpec{{1}}, costs, without_subsumption);

    for (const auto clock_value : {0, 1, 3, 5}) {
        const auto expected = normal.query(0, one_clock(clock_value));
        const auto reordered = reversed.query(0, one_clock(clock_value));
        const auto no_pruning = unpruned.query(0, one_clock(clock_value));
        require(expected.kind == CostValueKind::Finite &&
                    reordered.kind == expected.kind &&
                    no_pruning.kind == expected.kind &&
                    reordered.value == expected.value &&
                    no_pruning.value == expected.value &&
                    reordered.attained == expected.attained &&
                    no_pruning.attained == expected.attained,
                "入边存储顺序或关闭 subsumption 改变了逐点最优值");
    }
    require(normal.query(0, one_clock(0)).value == BigRational(4) &&
                normal.query(0, one_clock(3)).value == BigRational(1),
            "竞争路径模型的手算最短成本错误");
}

void test_independent_z3_figure_one_oracle() {
    z3::context context;
    z3::solver solver(context, "QF_LRA");
    const z3::expr t = context.real_const("oracle_t_l0");
    const z3::expr d = context.real_const("oracle_t_branch");
    const z3::expr cost = context.real_const("oracle_cost");
    const z3::expr via_l2 = context.bool_const("oracle_via_l2");
    solver.add(t >= 0);
    solver.add(t <= 2);
    solver.add(d >= 0);
    solver.add(t + d >= 2);
    solver.add(z3::implies(via_l2, cost == 5 * t + 10 * d + 1));
    solver.add(z3::implies(!via_l2, cost == 5 * t + d + 7));

    solver.push();
    solver.add(cost < 9);
    require(solver.check() == z3::unsat,
            "独立 QF_LRA path encoding 找到了低于论文最优值 9 的运行");
    solver.pop();
    solver.add(cost == 9);
    require(solver.check() == z3::sat,
            "独立 QF_LRA path encoding 未找到成本 9 的可行运行");
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

    const auto predecessors =
        monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(targets, automaton);
    if (!predecessors.has_state(automaton.initial_location())) {
        return false;
    }
    const monitaal::symbolic_state_t initial(
        automaton.initial_location(), automaton.number_of_clocks());
    return initial.is_included_in(predecessors.at(automaton.initial_location()));
}

void test_monitaal_observer_clock_oracle() {
    monitaal::clock_map_t clocks{{0, "0"}, {1, "x"}};
    monitaal::locations_t locations{
        monitaal::location_t(false, 0, "source", {}),
        monitaal::location_t(true, 1, "goal", {})};
    monitaal::edges_t edges{
        monitaal::edge_t(
            0, 1,
            monitaal::constraints_t{
                pardibaal::difference_bound_t::lower_non_strict(1, 3)},
            {}, "tick")};
    const monitaal::TA ordinary(
        "observer-oracle", clocks, locations, edges, 0);

    auto guard = universe(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-3));
    WeightedAutomatonView weighted(
        2, 0,
        {WeightedLocation(0, universe(2)), WeightedLocation(1, universe(2))},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, guard, {}, "tick")});
    const auto snapshot = tamonitor::pta::solve(
        weighted, GoalSpec{{1}}, CostModel{}, SolverOptions{});
    const auto result = snapshot.query(0, one_clock(0));

    require(result.kind == CostValueKind::Finite && result.value == BigRational(3),
            "rate=1/edge=0 solver 未得到 observer 模型的最短时间 3");
    require(!monitaal_reachable_within(ordinary, 2) &&
                monitaal_reachable_within(ordinary, 3),
            "MoniTAal 全局 observer-clock oracle 与最短时间 3 不一致");
}

void test_paper_figure_one() {
    constexpr LocationId l0 = 0;
    constexpr LocationId l1 = 1;
    constexpr LocationId l2 = 2;
    constexpr LocationId l3 = 3;
    constexpr LocationId l4 = 4;
    constexpr pardibaal::dim_t dimension = 3; // 0, x, y

    auto l1_invariant = universe(dimension);
    l1_invariant.restrict(2, 0, pardibaal::bound_t::le_zero());
    l1_invariant.restrict(0, 2, pardibaal::bound_t::le_zero());
    std::vector<WeightedLocation> locations;
    locations.emplace_back(l0, universe(dimension));
    locations.emplace_back(l1, l1_invariant);
    locations.emplace_back(l2, universe(dimension));
    locations.emplace_back(l3, universe(dimension));
    locations.emplace_back(l4, universe(dimension));

    auto x_at_most_two = universe(dimension);
    x_at_most_two.restrict(1, 0, pardibaal::bound_t::non_strict(2));
    auto x_at_least_two = universe(dimension);
    x_at_least_two.restrict(0, 1, pardibaal::bound_t::non_strict(-2));

    std::vector<WeightedEdge> edges;
    edges.emplace_back(EdgeId{l0, 0}, l0, l1, x_at_most_two,
                       std::vector<pardibaal::dim_t>{2});
    edges.emplace_back(EdgeId{l1, 0}, l1, l2, universe(dimension),
                       std::vector<pardibaal::dim_t>{});
    edges.emplace_back(EdgeId{l1, 1}, l1, l3, universe(dimension),
                       std::vector<pardibaal::dim_t>{});
    edges.emplace_back(EdgeId{l2, 0}, l2, l4, x_at_least_two,
                       std::vector<pardibaal::dim_t>{});
    edges.emplace_back(EdgeId{l3, 0}, l3, l4, x_at_least_two,
                       std::vector<pardibaal::dim_t>{});

    WeightedAutomatonView automaton(dimension, l0, std::move(locations), edges);
    CostModel costs;
    costs.default_location_rate = 0;
    costs.location_rates[l0] = 5;
    costs.location_rates[l2] = 10;
    costs.location_rates[l3] = 1;
    costs.edge_costs[EdgeId{l2, 0}] = 1;
    costs.edge_costs[EdgeId{l3, 0}] = 7;

    const auto snapshot = tamonitor::pta::solve(
        automaton, GoalSpec{{l4}}, costs, SolverOptions{});
    const RationalValuation zero(dimension, BigRational(0));
    const auto value = snapshot.query(l0, zero);
    require(snapshot.status() == SolverStatus::Complete &&
            value.kind == CostValueKind::Finite && value.value == BigRational(9),
            "论文 Fig.1 的全局最优 cost 必须为 9");
}

} // namespace

int main() {
    try {
        test_weighted_zone_primitives();
        test_action_and_time_predecessors();
        test_figure_two_split();
        test_exact_dominance();
        test_time_predecessor_geometry();
        test_solver_shortest_time_and_limits();
        test_solver_strict_infimum();
        test_timeout_never_reports_complete();
        test_solver_domain_sensitive_unboundedness();
        test_negative_weight_assumption_contract();
        test_queue_and_subsumption_independence();
        test_independent_z3_figure_one_oracle();
        test_monitaal_observer_clock_oracle();
        test_paper_figure_one();
        std::cout << "TAMonitor PTA tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "TAMonitor PTA test failure: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
