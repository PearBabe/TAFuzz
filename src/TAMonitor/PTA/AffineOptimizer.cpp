// 本文件实现严格 DBM 上的 Z3 精确仿射上确界：闭包优化、上界证明与取得性判定。

#include "AffineOptimizer.h"

#include "PricedDBMOps.h"
#include "RomeoDBMOptimizer.h"

#include <z3++.h>
#include <z3.h>

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

using ClockExpressions = std::vector<z3::expr>;
using SteadyClock = std::chrono::steady_clock;

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

z3::expr exact_real(z3::context& context, pardibaal::val_t value) {
    return context.real_val(std::to_string(value).c_str());
}

ClockExpressions make_clocks(z3::context& context,
                             pardibaal::dim_t dimension) {
    if (dimension == 0) {
        throw std::invalid_argument("DBM dimension 不能为 0");
    }
    ClockExpressions clocks;
    clocks.reserve(dimension);
    clocks.push_back(context.real_val(0));
    for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
        const std::string name = "pta_affine_clock_" + std::to_string(clock);
        clocks.push_back(context.real_const(name.c_str()));
    }
    return clocks;
}

template <typename Solver>
void assert_zone(Solver& solver,
                 z3::context& context,
                 const pardibaal::DBM& zone,
                 const ClockExpressions& clocks) {
    if (zone.dimension() != clocks.size()) {
        throw std::invalid_argument("DBM 与 Z3 clock dimension 不一致");
    }
    for (pardibaal::dim_t i = 0; i < zone.dimension(); ++i) {
        for (pardibaal::dim_t j = 0; j < zone.dimension(); ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) {
                continue;
            }
            const z3::expr difference = clocks[i] - clocks[j];
            const z3::expr constant = exact_real(context, bound.get_bound());
            solver.add(bound.is_strict() ? difference < constant
                                         : difference <= constant);
        }
    }
}

z3::expr weight_expression(z3::context& context,
                           const WeightedZone& piece,
                           const ClockExpressions& clocks) {
    if (piece.zone.dimension() != clocks.size() ||
        piece.rates.size() != clocks.size()) {
        throw std::invalid_argument("weighted zone 与 Z3 clock dimension 不一致");
    }
    const auto delta = offset(piece.zone);
    z3::expr weight = exact_real(context, piece.offset_weight);
    for (pardibaal::dim_t clock = 1; clock < piece.zone.dimension(); ++clock) {
        if (piece.rates[clock] == 0) {
            continue;
        }
        weight = weight + exact_real(context, piece.rates[clock]) *
                              (clocks[clock] - exact_real(context, delta[clock]));
    }
    return weight;
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

struct UpperVector {
    BigRational infinity;
    BigRational finite;
    BigRational epsilon;
};

UpperVector read_upper_vector(z3::context& context,
                              z3::optimize& optimizer,
                              const z3::optimize::handle& objective) {
    const Z3_ast_vector raw = Z3_optimize_get_upper_as_vector(
        context, optimizer, objective.h());
    z3::expr_vector vector(context, raw);
    if (vector.size() != 3) {
        throw std::runtime_error("Z3 Optimize upper vector 长度不是 3");
    }
    return {parse_rational(vector[0]), parse_rational(vector[1]),
            parse_rational(vector[2])};
}

class TimeoutBudget {
public:
    TimeoutBudget(SteadyClock::time_point start, std::uint64_t timeout_ms)
        : start_(start), timeout_ms_(timeout_ms) {}

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
        const std::uint64_t remaining = timeout_ms_ - elapsed;
        return static_cast<unsigned>(std::min<std::uint64_t>(
            std::max<std::uint64_t>(remaining, 1),
            std::numeric_limits<unsigned>::max()));
    }

private:
    [[nodiscard]] std::uint64_t elapsed_ms() const {
        return static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                SteadyClock::now() - start_)
                .count());
    }

    SteadyClock::time_point start_;
    std::uint64_t timeout_ms_;
};

template <typename Solver>
bool set_remaining_timeout(Solver& solver,
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

} // namespace

AffineSupremum maximize_affine_z3(const WeightedZone& piece,
                                  const pardibaal::DBM& domain,
                                  std::uint64_t timeout_ms) {
    if (piece.zone.dimension() != domain.dimension()) {
        throw std::invalid_argument("piece 与查询 domain 的 DBM dimension 不一致");
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

        const pardibaal::DBM closure = topological_closure(exact_piece->zone);
        const auto closure_piece = rebase(*exact_piece, closure);
        if (!closure_piece.has_value()) {
            result.kind = AffineOptimumKind::Empty;
            result.diagnostic = "empty_closure";
            return finish();
        }

        // thread_local context 避免每个在线前缀候选重复构造全局 Z3 context，
        // 同时不跨线程共享非线程安全对象。
        thread_local z3::context context;
        const auto clocks = make_clocks(context, closure.dimension());
        const z3::expr closure_weight =
            weight_expression(context, *closure_piece, clocks);

        z3::optimize optimizer(context);
        if (!set_remaining_timeout(optimizer, context, budget)) {
            result.timed_out = true;
            result.diagnostic = "timeout_before_optimize";
            return finish();
        }
        assert_zone(optimizer, context, closure, clocks);
        const auto objective = optimizer.maximize(closure_weight);
        const z3::check_result optimize_status = optimizer.check();
        if (optimize_status != z3::sat) {
            result.timed_out = budget.expired() ||
                reason_is_timeout(Z3_optimize_get_reason_unknown(context, optimizer));
            result.diagnostic = optimize_status == z3::unsat
                ? "unexpected_empty_closure"
                : "optimize_unknown:" +
                      std::string(Z3_optimize_get_reason_unknown(context, optimizer));
            return finish();
        }

        const UpperVector upper = read_upper_vector(context, optimizer, objective);
        if (upper.infinity > BigRational(0)) {
            result.kind = AffineOptimumKind::PositiveInfinity;
            result.diagnostic = "unbounded_above";
            return finish();
        }
        if (upper.infinity < BigRational(0) ||
            upper.epsilon != BigRational(0)) {
            // 输入已是闭 DBM，有限最大值不应再携带 epsilon；保守返回 Unknown。
            result.diagnostic = "unexpected_optimize_bound_vector";
            return finish();
        }

        const BigRational optimum = upper.finite;

        // Optimize 只提出候选值。普通 QF_LRA solver 独立证明闭包中没有 W>b，
        // 避免把 Optimize 的模型或旧版本 strict 行为当作证明。
        z3::solver upper_proof(context, "QF_LRA");
        if (!set_remaining_timeout(upper_proof, context, budget)) {
            result.timed_out = true;
            result.diagnostic = "timeout_before_upper_proof";
            return finish();
        }
        assert_zone(upper_proof, context, closure, clocks);
        upper_proof.add(closure_weight > exact_real(context, optimum));
        const z3::check_result proof_status = upper_proof.check();
        if (proof_status != z3::unsat) {
            result.timed_out = budget.expired() ||
                (proof_status == z3::unknown &&
                 reason_is_timeout(upper_proof.reason_unknown()));
            result.diagnostic = proof_status == z3::sat
                ? "optimize_upper_not_valid"
                : "upper_proof_unknown:" + upper_proof.reason_unknown();
            return finish();
        }
        result.upper_bound_proved = true;

        const z3::expr exact_weight =
            weight_expression(context, *exact_piece, clocks);
        z3::solver actual_solver(context, "QF_LRA");
        if (!set_remaining_timeout(actual_solver, context, budget)) {
            result.timed_out = true;
            result.diagnostic = "timeout_before_attainment_check";
            return finish();
        }
        assert_zone(actual_solver, context, exact_piece->zone, clocks);
        actual_solver.add(exact_weight == exact_real(context, optimum));
        const z3::check_result actual_status = actual_solver.check();
        if (actual_status == z3::sat) {
            result.kind = AffineOptimumKind::Finite;
            result.value = optimum;
            result.domain_attained = true;
            result.optimizer_is_actual = true;
            result.optimizer_or_limit =
                valuation_from_model(actual_solver.get_model(), clocks);
            result.diagnostic = "finite_attained";
            return finish();
        }
        if (actual_status == z3::unknown) {
            result.timed_out = budget.expired() ||
                reason_is_timeout(actual_solver.reason_unknown());
            result.diagnostic = "attainment_unknown:" +
                                actual_solver.reason_unknown();
            return finish();
        }

        // 严格域不取得上确界时，用闭包等值模型给出可复核的极限 valuation。
        z3::solver limit_solver(context, "QF_LRA");
        if (!set_remaining_timeout(limit_solver, context, budget)) {
            result.timed_out = true;
            result.diagnostic = "timeout_before_limit_check";
            return finish();
        }
        assert_zone(limit_solver, context, closure, clocks);
        limit_solver.add(closure_weight == exact_real(context, optimum));
        const z3::check_result limit_status = limit_solver.check();
        if (limit_status != z3::sat) {
            result.timed_out = budget.expired() ||
                (limit_status == z3::unknown &&
                 reason_is_timeout(limit_solver.reason_unknown()));
            result.diagnostic = limit_status == z3::unsat
                ? "optimum_missing_from_closure"
                : "limit_check_unknown:" + limit_solver.reason_unknown();
            return finish();
        }

        result.kind = AffineOptimumKind::Finite;
        result.value = optimum;
        result.domain_attained = false;
        result.optimizer_is_actual = false;
        result.optimizer_or_limit =
            valuation_from_model(limit_solver.get_model(), clocks);
        result.diagnostic = "finite_infimum_only";
        return finish();
    } catch (const z3::exception& exception) {
        result.kind = AffineOptimumKind::Unknown;
        result.timed_out = budget.expired();
        result.diagnostic = "z3_exception:" + std::string(exception.msg());
        return finish();
    } catch (const std::exception& exception) {
        result.kind = AffineOptimumKind::Unknown;
        result.timed_out = budget.expired();
        result.diagnostic = "optimizer_exception:" + std::string(exception.what());
        return finish();
    }
}

AffineSupremum maximize_affine(
    const WeightedZone& piece,
    const pardibaal::DBM& domain,
    PrefixOptimizerBackend backend,
    std::uint64_t timeout_ms) {
    if (backend == PrefixOptimizerBackend::Z3) {
        return maximize_affine_z3(piece, domain, timeout_ms);
    }
    if (backend == PrefixOptimizerBackend::RomeoDBM) {
        return maximize_affine_romeo_dbm(piece, domain, timeout_ms);
    }

    const auto started = SteadyClock::now();
    auto z3_result = maximize_affine_z3(piece, domain, timeout_ms);
    std::uint64_t remaining = timeout_ms;
    if (timeout_ms != 0) {
        const auto elapsed = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                SteadyClock::now() - started)
                .count());
        remaining = elapsed >= timeout_ms ? 1 : timeout_ms - elapsed;
    }
    auto romeo_result = maximize_affine_romeo_dbm(piece, domain, remaining);
    const auto total_us = static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(
            SteadyClock::now() - started)
            .count());

    bool equal = z3_result.kind == romeo_result.kind;
    if (equal && z3_result.kind == AffineOptimumKind::Finite) {
        equal = z3_result.value == romeo_result.value &&
                z3_result.domain_attained == romeo_result.domain_attained &&
                z3_result.optimizer_is_actual ==
                    romeo_result.optimizer_is_actual;
    }
    if (!equal) {
        AffineSupremum mismatch;
        mismatch.elapsed_us = total_us;
        mismatch.timed_out = z3_result.timed_out || romeo_result.timed_out;
        mismatch.diagnostic = "crosscheck_mismatch:z3=" +
            z3_result.diagnostic + ";romeo=" + romeo_result.diagnostic;
        return mismatch;
    }
    if (z3_result.kind == AffineOptimumKind::Unknown) {
        z3_result.diagnostic = "crosscheck_unknown:z3=" +
            z3_result.diagnostic + ";romeo=" + romeo_result.diagnostic;
    } else {
        z3_result.diagnostic = "crosscheck_equal:z3=" +
            z3_result.diagnostic + ";romeo=" + romeo_result.diagnostic;
    }
    z3_result.elapsed_us = total_us;
    z3_result.timed_out = z3_result.timed_out || romeo_result.timed_out;
    return z3_result;
}

} // namespace tamonitor::pta
