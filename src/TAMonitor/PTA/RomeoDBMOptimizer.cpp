// 本文件用任意精度最小费用转运重写 Roméo DBM::min/max 的数学算法。

#include "RomeoDBMOptimizer.h"

#include "PricedDBMOps.h"

#include <z3++.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace tamonitor::pta {
namespace {

using SteadyClock = std::chrono::steady_clock;
using ClockExpressions = std::vector<z3::expr>;

class TimeoutBudget {
public:
    TimeoutBudget(SteadyClock::time_point started, std::uint64_t timeout_ms)
        : started_(started), timeout_ms_(timeout_ms) {}

    [[nodiscard]] bool expired() const {
        return timeout_ms_ != 0 && elapsed_ms() >= timeout_ms_;
    }

    [[nodiscard]] std::optional<unsigned> remaining_z3_ms() const {
        if (timeout_ms_ == 0) {
            return std::nullopt;
        }
        const auto elapsed = elapsed_ms();
        if (elapsed >= timeout_ms_) {
            return 0U;
        }
        return static_cast<unsigned>(std::min<std::uint64_t>(
            std::max<std::uint64_t>(timeout_ms_ - elapsed, 1),
            std::numeric_limits<unsigned>::max()));
    }

private:
    [[nodiscard]] std::uint64_t elapsed_ms() const {
        return static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                SteadyClock::now() - started_)
                .count());
    }

    SteadyClock::time_point started_;
    std::uint64_t timeout_ms_;
};

struct ResidualArc {
    std::size_t target = 0;
    std::size_t reverse = 0;
    BigInt capacity = 0;
    BigInt cost = 0;
};

using ResidualGraph = std::vector<std::vector<ResidualArc>>;

void add_residual_arc(ResidualGraph& graph,
                      std::size_t source,
                      std::size_t target,
                      const BigInt& capacity,
                      const BigInt& cost) {
    const std::size_t forward_index = graph[source].size();
    const std::size_t reverse_index = graph[target].size();
    graph[source].push_back(
        {target, reverse_index, capacity, cost});
    graph[target].push_back(
        {source, forward_index, BigInt(0), -cost});
}

struct TransshipmentResult {
    bool finite = false;
    bool timed_out = false;
    BigInt value = 0;
};

/**
 * 求解
 *   min sum b_ij y_ij
 *   s.t. outgoing(i)-incoming(i)=c_i, y_ij>=0.
 *
 * 这是 max c^T x, x_i-x_j<=b_ij 的线性规划对偶。DBM 无
 * 负环，因而初始残量网络无负环；每次 Bellman–Ford 最短增广
 * 保持最小费用流不变量。供需无法全部路由时，原目标无上界。
 */
TransshipmentResult solve_transshipment(
    const pardibaal::DBM& closure,
    const std::vector<BigInt>& objective,
    const TimeoutBudget& budget) {
    const std::size_t dimension = closure.dimension();
    if (objective.size() != dimension) {
        throw std::invalid_argument("DBM 与 objective dimension 不一致");
    }

    BigInt total_supply = 0;
    for (const auto& coefficient : objective) {
        if (coefficient > 0) {
            total_supply += coefficient;
        }
    }
    if (total_supply == 0) {
        return {true, false, BigInt(0)};
    }

    const std::size_t super_source = dimension;
    const std::size_t super_sink = dimension + 1;
    ResidualGraph graph(dimension + 2);

    for (std::size_t i = 0; i < dimension; ++i) {
        if (objective[i] > 0) {
            add_residual_arc(
                graph, super_source, i, objective[i], BigInt(0));
        } else if (objective[i] < 0) {
            add_residual_arc(
                graph, i, super_sink, -objective[i], BigInt(0));
        }
    }

    // 全部 DBM bound 都是可用的对偶弧。容量取总供给已等价于无限，
    // 但避免在残量网络中引入特殊无穷数类型。
    for (std::size_t i = 0; i < dimension; ++i) {
        for (std::size_t j = 0; j < dimension; ++j) {
            if (i == j) {
                continue;
            }
            const auto bound = closure.at(i, j);
            if (!bound.is_inf()) {
                add_residual_arc(graph, i, j, total_supply,
                                 BigInt(bound.get_bound()));
            }
        }
    }

    BigInt sent = 0;
    BigInt minimum_cost = 0;
    const std::size_t node_count = graph.size();
    // potential 把原费用转为 reduced cost；首轮从 0 开始，Bellman–Ford
    // 允许负 reduced arc，更新后对所有本轮可达残量弧满足非负性。
    std::vector<BigInt> potential(node_count, BigInt(0));
    while (sent < total_supply) {
        if (budget.expired()) {
            return {false, true, BigInt(0)};
        }

        std::vector<std::optional<BigInt>> distance(node_count);
        std::vector<std::optional<std::pair<std::size_t, std::size_t>>>
            predecessor(node_count);
        distance[super_source] = BigInt(0);

        // 残量反向弧可以是负费用，故使用 Bellman–Ford，不以
        // Dijkstra 的非负 reduced-cost 前提代替数学正确性。
        for (std::size_t pass = 1; pass < node_count; ++pass) {
            bool changed = false;
            for (std::size_t source = 0; source < node_count; ++source) {
                if (!distance[source].has_value()) {
                    continue;
                }
                for (std::size_t arc_index = 0;
                     arc_index < graph[source].size(); ++arc_index) {
                    const auto& arc = graph[source][arc_index];
                    if (arc.capacity == 0) {
                        continue;
                    }
                    const BigInt reduced_cost =
                        arc.cost + potential[source] - potential[arc.target];
                    const BigInt candidate =
                        *distance[source] + reduced_cost;
                    if (!distance[arc.target].has_value() ||
                        candidate < *distance[arc.target]) {
                        distance[arc.target] = candidate;
                        predecessor[arc.target] =
                            std::make_pair(source, arc_index);
                        changed = true;
                    }
                }
            }
            if (!changed) {
                break;
            }
            if (budget.expired()) {
                return {false, true, BigInt(0)};
            }
        }

        if (!distance[super_sink].has_value()) {
            return {false, false, BigInt(0)};
        }

        for (std::size_t node = 0; node < node_count; ++node) {
            if (distance[node].has_value()) {
                potential[node] += *distance[node];
            }
        }

        BigInt augment = total_supply - sent;
        BigInt path_cost = 0;
        std::size_t node = super_sink;
        while (node != super_source) {
            if (!predecessor[node].has_value()) {
                throw std::logic_error("最短增广路缺少 predecessor");
            }
            const auto [source, arc_index] = *predecessor[node];
            augment = std::min(augment, graph[source][arc_index].capacity);
            path_cost += graph[source][arc_index].cost;
            node = source;
        }
        if (augment <= 0) {
            throw std::logic_error("最短增广路容量非正");
        }

        node = super_sink;
        while (node != super_source) {
            const auto [source, arc_index] = *predecessor[node];
            auto& arc = graph[source][arc_index];
            auto& reverse = graph[arc.target][arc.reverse];
            arc.capacity -= augment;
            reverse.capacity += augment;
            node = source;
        }
        sent += augment;
        minimum_cost += augment * path_cost;
    }

    return {true, false, minimum_cost};
}

std::string rational_string(const BigRational& value) {
    const std::string numerator = value.numerator().convert_to<std::string>();
    if (value.denominator() == 1) {
        return numerator;
    }
    return numerator + "/" + value.denominator().convert_to<std::string>();
}

BigRational parse_rational(const z3::expr& expression) {
    std::string numeral;
    if (!expression.is_numeral(numeral)) {
        throw std::runtime_error("Z3 未返回精确有理数 numeral");
    }
    const auto slash = numeral.find('/');
    if (slash == std::string::npos) {
        return BigRational(BigInt(numeral));
    }
    return BigRational(BigInt(numeral.substr(0, slash)),
                       BigInt(numeral.substr(slash + 1)));
}

z3::expr exact_real(z3::context& context, const BigInt& value) {
    const std::string text = value.convert_to<std::string>();
    return context.real_val(text.c_str());
}

z3::expr exact_real(z3::context& context, const BigRational& value) {
    const std::string text = rational_string(value);
    return context.real_val(text.c_str());
}

ClockExpressions make_clocks(z3::context& context,
                             pardibaal::dim_t dimension) {
    ClockExpressions clocks;
    clocks.reserve(dimension);
    clocks.push_back(context.real_val(0));
    for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
        const std::string name =
            "pta_romeo_clock_" + std::to_string(clock);
        clocks.push_back(context.real_const(name.c_str()));
    }
    return clocks;
}

void assert_zone(z3::solver& solver,
                 z3::context& context,
                 const pardibaal::DBM& zone,
                 const ClockExpressions& clocks) {
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

z3::expr weight_expression(z3::context& context,
                           const WeightedZone& piece,
                           const ClockExpressions& clocks) {
    const auto delta = offset(piece.zone);
    z3::expr expression = exact_real(context, piece.offset_weight);
    for (pardibaal::dim_t clock = 1;
         clock < piece.zone.dimension(); ++clock) {
        if (piece.rates[clock] != 0) {
            expression = expression + exact_real(context, piece.rates[clock]) *
                (clocks[clock] - exact_real(context, delta[clock]));
        }
    }
    return expression;
}

RationalValuation valuation_from_model(const z3::model& model,
                                       const ClockExpressions& clocks) {
    RationalValuation valuation;
    valuation.reserve(clocks.size());
    for (const auto& clock : clocks) {
        valuation.push_back(parse_rational(model.eval(clock, true)));
    }
    return valuation;
}

bool set_timeout(z3::solver& solver,
                 z3::context& context,
                 const TimeoutBudget& budget) {
    const auto remaining = budget.remaining_z3_ms();
    if (!remaining.has_value()) {
        return true;
    }
    if (*remaining == 0) {
        return false;
    }
    z3::params parameters(context);
    parameters.set("timeout", *remaining);
    solver.set(parameters);
    return true;
}

bool reason_is_timeout(const std::string& reason) {
    return reason.find("timeout") != std::string::npos ||
           reason.find("canceled") != std::string::npos;
}

struct AttainmentResult {
    bool known = false;
    bool actual = false;
    bool timed_out = false;
    std::optional<RationalValuation> valuation;
    std::string diagnostic;
};

AttainmentResult certify_attainment(const WeightedZone& exact_piece,
                                    const WeightedZone& closure_piece,
                                    const BigRational& optimum,
                                    const TimeoutBudget& budget) {
    thread_local z3::context context;
    const auto clocks = make_clocks(context, exact_piece.zone.dimension());

    z3::solver actual(context, "QF_LRA");
    if (!set_timeout(actual, context, budget)) {
        return {false, false, true, std::nullopt,
                "timeout_before_attainment_check"};
    }
    assert_zone(actual, context, exact_piece.zone, clocks);
    actual.add(weight_expression(context, exact_piece, clocks) ==
               exact_real(context, optimum));
    const auto actual_status = actual.check();
    if (actual_status == z3::sat) {
        return {true, true, false,
                valuation_from_model(actual.get_model(), clocks),
                "finite_attained"};
    }
    if (actual_status == z3::unknown) {
        return {false, false,
                budget.expired() || reason_is_timeout(actual.reason_unknown()),
                std::nullopt,
                "attainment_unknown:" + actual.reason_unknown()};
    }

    z3::solver limit(context, "QF_LRA");
    if (!set_timeout(limit, context, budget)) {
        return {false, false, true, std::nullopt,
                "timeout_before_limit_check"};
    }
    assert_zone(limit, context, closure_piece.zone, clocks);
    limit.add(weight_expression(context, closure_piece, clocks) ==
              exact_real(context, optimum));
    const auto limit_status = limit.check();
    if (limit_status == z3::sat) {
        return {true, false, false,
                valuation_from_model(limit.get_model(), clocks),
                "finite_infimum_only"};
    }
    if (limit_status == z3::unknown) {
        return {false, false,
                budget.expired() || reason_is_timeout(limit.reason_unknown()),
                std::nullopt,
                "limit_unknown:" + limit.reason_unknown()};
    }
    return {false, false, false, std::nullopt,
            "dual_optimum_missing_from_closure"};
}

} // namespace

AffineSupremum maximize_affine_romeo_dbm(const WeightedZone& piece,
                                         const pardibaal::DBM& domain,
                                         std::uint64_t timeout_ms) {
    if (piece.zone.dimension() != domain.dimension()) {
        throw std::invalid_argument(
            "piece 与查询 domain 的 DBM dimension 不一致");
    }

    const auto started = SteadyClock::now();
    const TimeoutBudget budget(started, timeout_ms);
    AffineSupremum result;
    auto finish = [&]() {
        result.elapsed_us = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::microseconds>(
                SteadyClock::now() - started)
                .count());
        return result;
    };

    try {
        const auto exact_piece = intersection(piece, domain);
        if (!exact_piece.has_value()) {
            result.kind = AffineOptimumKind::Empty;
            result.diagnostic = "empty_domain";
            return finish();
        }

        const auto closure = topological_closure(exact_piece->zone);
        const auto closure_piece = rebase(*exact_piece, closure);
        if (!closure_piece.has_value()) {
            result.kind = AffineOptimumKind::Empty;
            result.diagnostic = "empty_closure";
            return finish();
        }

        // 将参考钟系数补成 -sum c_i，使目标在整体平移下不变；
        // 固定 x_0=0 后与原目标完全等价。
        std::vector<BigInt> objective = closure_piece->rates;
        BigInt coefficient_sum = 0;
        for (std::size_t clock = 1; clock < objective.size(); ++clock) {
            coefficient_sum += objective[clock];
        }
        objective[0] = -coefficient_sum;

        const auto flow =
            solve_transshipment(closure, objective, budget);
        if (flow.timed_out) {
            result.timed_out = true;
            result.diagnostic = "timeout_during_transshipment";
            return finish();
        }
        if (!flow.finite) {
            result.kind = AffineOptimumKind::PositiveInfinity;
            result.diagnostic = "unbounded_above";
            return finish();
        }

        BigRational affine_constant(closure_piece->offset_weight);
        const auto delta = offset(closure_piece->zone);
        for (std::size_t clock = 1;
             clock < closure_piece->rates.size(); ++clock) {
            affine_constant -= BigRational(
                closure_piece->rates[clock] * delta[clock]);
        }
        const BigRational optimum =
            affine_constant + BigRational(flow.value);

        // 转运双偶的完整可行流就是上界证书。Z3 下面只检查
        // 固定 optimum 的等值可满足性，不参与最优值计算。
        result.upper_bound_proved = true;
        const auto attainment = certify_attainment(
            *exact_piece, *closure_piece, optimum, budget);
        if (!attainment.known) {
            result.timed_out = attainment.timed_out;
            result.diagnostic = attainment.diagnostic;
            return finish();
        }

        result.kind = AffineOptimumKind::Finite;
        result.value = optimum;
        result.domain_attained = attainment.actual;
        result.optimizer_is_actual = attainment.actual;
        result.optimizer_or_limit = attainment.valuation;
        result.diagnostic = attainment.diagnostic;
        return finish();
    } catch (const z3::exception& exception) {
        result.timed_out = budget.expired();
        result.diagnostic =
            "z3_attainment_exception:" + std::string(exception.msg());
        return finish();
    } catch (const std::exception& exception) {
        result.timed_out = budget.expired();
        result.diagnostic =
            "romeo_optimizer_exception:" + std::string(exception.what());
        return finish();
    }
}

} // namespace tamonitor::pta
