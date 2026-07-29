// 本文件用 Z3 QF_LRA 精确实现 priced-zone 支配；UNKNOWN 时保守地禁止剪枝。

#include "ExactDominance.h"

#include "PTATypes.h"
#include "PricedDBMOps.h"

#include <z3++.h>

#include <algorithm>
#include <stdexcept>
#include <cstdint>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace tamonitor::pta {
namespace {

z3::expr exact_real(z3::context& context, const BigInt& value) {
    const std::string decimal = value.convert_to<std::string>();
    return context.real_val(decimal.c_str());
}

z3::expr exact_real(z3::context& context, pardibaal::val_t value) {
    return context.real_val(std::to_string(value).c_str());
}

std::vector<z3::expr> make_clock_expressions(
    z3::context& context,
    pardibaal::dim_t dimension) {
    std::vector<z3::expr> clocks;
    clocks.reserve(dimension);

    // DBM 的 0 号维是恒为零的参考钟，不创建可自由赋值的 Z3 变量。
    clocks.push_back(context.real_val(0));
    for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
        const std::string name = "pta_clock_" + std::to_string(clock);
        clocks.push_back(context.real_const(name.c_str()));
    }
    return clocks;
}

void assert_zone(
    z3::solver& solver,
    z3::context& context,
    const pardibaal::DBM& zone,
    const std::vector<z3::expr>& clocks) {
    const auto dimension = zone.dimension();
    if (clocks.size() != dimension) {
        throw std::invalid_argument("DBM 与 Z3 时钟维数不一致");
    }

    // at(i,j) 表示 x_i-x_j <= c（或 <c）。编码全部有限 DBM 项，
    // 因此即使输入尚未做最短路闭包，公式仍与输入约束精确等价。
    for (pardibaal::dim_t i = 0; i < dimension; ++i) {
        for (pardibaal::dim_t j = 0; j < dimension; ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) {
                continue;
            }
            const z3::expr difference = clocks[i] - clocks[j];
            const z3::expr constant = exact_real(context, bound.get_bound());
            solver.add(bound.is_strict() ? difference < constant : difference <= constant);
        }
    }
}

z3::expr weight_expression(
    z3::context& context,
    const WeightedZone& weighted_zone,
    const std::vector<z3::expr>& clocks) {
    const auto dimension = weighted_zone.zone.dimension();
    if (weighted_zone.rates.size() != dimension || clocks.size() != dimension) {
        throw std::invalid_argument("weighted zone 的 gradient 维数不一致");
    }

    const std::vector<BigInt> zone_offset = offset(weighted_zone.zone);
    if (zone_offset.size() != dimension) {
        throw std::invalid_argument("weighted zone 的 offset 维数不一致");
    }

    z3::expr result = exact_real(context, weighted_zone.offset_weight);
    for (pardibaal::dim_t clock = 0; clock < dimension; ++clock) {
        if (weighted_zone.rates[clock] == 0) {
            continue;
        }
        result = result + exact_real(context, weighted_zone.rates[clock]) *
                              (clocks[clock] - exact_real(context, zone_offset[clock]));
    }
    return result;
}

}  // namespace

class ExactDominance::Impl {
public:
    DominanceResult check(
        const WeightedZone& dominator,
        const WeightedZone& candidate,
        std::uint64_t timeout_ms) {
        ++statistics.checks;

        if (candidate.zone.dimension() != dominator.zone.dimension()) {
            ++statistics.zone_rejections;
            return DominanceResult::NotDominated;
        }

        // 论文只比较最优 infimum；本实现还公开“该值是否真正达到”。一个
        // attained 候选若被同值但 unattained 的旧 piece 剪掉，会丢失见证。
        // 此处保守地少剪枝，不改变 Definition 10 的 cost/value 语义。
        if (candidate.attained && !dominator.attained) {
            ++statistics.attainment_rejections;
            return DominanceResult::NotDominated;
        }

        // PARDIBAAL 的 is_subset() 是“真子集”谓词；相等 DBM 必须显式接受。
        const auto zone_relation = candidate.zone.relation(dominator.zone);
        if (!zone_relation.is_equal() && !zone_relation.is_subset()) {
            ++statistics.zone_rejections;
            return DominanceResult::NotDominated;
        }

        try {
            z3::solver solver(context, "QF_LRA");
            if (timeout_ms != 0) {
                z3::params parameters(context);
                const auto z3_timeout = static_cast<unsigned>(
                    std::min<std::uint64_t>(
                        timeout_ms, std::numeric_limits<unsigned>::max()));
                parameters.set("timeout", z3_timeout);
                solver.set(parameters);
            }
            const auto clocks = make_clock_expressions(context, candidate.zone.dimension());
            assert_zone(solver, context, candidate.zone, clocks);

            const z3::expr candidate_weight =
                weight_expression(context, candidate, clocks);
            const z3::expr dominator_weight =
                weight_expression(context, dominator, clocks);

            // Definition 10：若 Z_candidate ∧ (W_candidate > W_dominator)
            // 不可满足，则旧 label 在候选定义域上处处不差，可以安全剪枝。
            solver.add(candidate_weight > dominator_weight);
            const z3::check_result result = solver.check();
            if (result == z3::unsat) {
                ++statistics.dominated;
                return DominanceResult::Dominated;
            }
            if (result == z3::sat) {
                return DominanceResult::NotDominated;
            }

            ++statistics.solver_unknown;
            return DominanceResult::Unknown;
        } catch (const z3::exception&) {
            ++statistics.solver_unknown;
            return DominanceResult::Unknown;
        } catch (const std::exception&) {
            ++statistics.solver_unknown;
            return DominanceResult::Unknown;
        }
    }

    z3::context context;
    DominanceStatistics statistics;
};

ExactDominance::ExactDominance() : impl_(std::make_unique<Impl>()) {}

ExactDominance::~ExactDominance() = default;

ExactDominance::ExactDominance(ExactDominance&&) noexcept = default;

ExactDominance& ExactDominance::operator=(ExactDominance&&) noexcept = default;

DominanceResult ExactDominance::check(
    const WeightedZone& dominator,
    const WeightedZone& candidate,
    std::uint64_t timeout_ms) {
    return impl_->check(dominator, candidate, timeout_ms);
}

const DominanceStatistics& ExactDominance::statistics() const noexcept {
    return impl_->statistics;
}

}  // namespace tamonitor::pta
