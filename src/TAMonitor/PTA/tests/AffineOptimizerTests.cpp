// 本文件用独立 DBM 小模型验证 Z3 affine optimizer 的精确值、严格取得性与无界分类。

#include "AffineOptimizer.h"
#include "PricedDBMOps.h"

#include <pardibaal/DBM.h>
#include <pardibaal/difference_bound_t.h>

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using tamonitor::pta::AffineOptimumKind;
using tamonitor::pta::BigInt;
using tamonitor::pta::BigRational;
using tamonitor::pta::WeightedZone;

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
    zone.restrict(0, 1, strict_lower
        ? pardibaal::bound_t::strict(-lower)
        : pardibaal::bound_t::non_strict(-lower));
    zone.restrict(1, 0, strict_upper
        ? pardibaal::bound_t::strict(upper)
        : pardibaal::bound_t::non_strict(upper));
    zone.close();
    return zone;
}

void test_closed_maximum() {
    const auto zone = interval(0, 5);
    const WeightedZone piece(zone, BigInt(0), {BigInt(0), BigInt(2)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, zone);

    require(result.kind == AffineOptimumKind::Finite &&
                result.value == BigRational(10),
            "closed interval 的 affine maximum 应为 10");
    require(result.upper_bound_proved && result.domain_attained &&
                result.optimizer_is_actual && result.optimizer_or_limit.has_value(),
            "closed maximum 应有 QF_LRA proof 和实际 optimizer");
    require(tamonitor::pta::contains(zone, *result.optimizer_or_limit) &&
                tamonitor::pta::weight_at(piece, *result.optimizer_or_limit) ==
                    result.value,
            "closed optimizer valuation 无法回放");
}

void test_strict_upper_limit() {
    const auto strict_zone = interval(0, 5, false, true);
    const WeightedZone piece(strict_zone, BigInt(0),
                             {BigInt(0), BigInt(2)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, strict_zone);

    require(result.kind == AffineOptimumKind::Finite &&
                result.value == BigRational(10) && result.upper_bound_proved,
            "x<5 的 supremum 应为 10");
    require(!result.domain_attained && !result.optimizer_is_actual &&
                result.optimizer_or_limit.has_value(),
            "strict upper maximum 应只返回 closure limit");
    require(!tamonitor::pta::contains(strict_zone, *result.optimizer_or_limit) &&
                tamonitor::pta::contains(
                    tamonitor::pta::topological_closure(strict_zone),
                    *result.optimizer_or_limit),
            "strict limit 应在 closure 内、原域外");
    require((*result.optimizer_or_limit)[1] == BigRational(5),
            "strict upper limit valuation 应为 x=5");
}

void test_strict_lower_negative_rate() {
    const auto strict_zone = interval(0, 5, true, false);
    const WeightedZone piece(strict_zone, BigInt(0),
                             {BigInt(0), BigInt(-3)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, strict_zone);

    require(result.kind == AffineOptimumKind::Finite &&
                result.value == BigRational(0) && !result.domain_attained,
            "x>0 上 -3x 的 supremum 应为 0 且不可取得");
    require(result.optimizer_or_limit.has_value() &&
                (*result.optimizer_or_limit)[1] == BigRational(0),
            "strict lower limit valuation 应为 x=0");
}

void test_unbounded_above() {
    auto zone = universe(2);
    zone.restrict(0, 1, pardibaal::bound_t::le_zero()); // x>=0
    zone.close();
    const WeightedZone piece(zone, BigInt(7), {BigInt(0), BigInt(1)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, zone);

    require(result.kind == AffineOptimumKind::PositiveInfinity &&
                !result.optimizer_or_limit.has_value(),
            "无上界 x 上正梯度必须返回 +infinity");
}

void test_empty_intersection() {
    const auto piece_zone = interval(0, 1);
    const auto query_zone = interval(2, 3);
    const WeightedZone piece(piece_zone, BigInt(0),
                             {BigInt(0), BigInt(1)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, query_zone);

    require(result.kind == AffineOptimumKind::Empty &&
                !result.optimizer_or_limit.has_value(),
            "空 piece/domain 交集必须与 Unknown 区分");
}

void test_diagonal_objective() {
    auto zone = universe(3);
    // 0<=y<=2，x-y<=1，y-x<=0，因此 y<=x<=y+1。
    zone.restrict(0, 2, pardibaal::bound_t::le_zero());
    zone.restrict(2, 0, pardibaal::bound_t::non_strict(2));
    zone.restrict(1, 2, pardibaal::bound_t::non_strict(1));
    zone.restrict(2, 1, pardibaal::bound_t::le_zero());
    zone.close();

    // W=2x-y，最优点 (x,y)=(3,2)，精确值 4。
    const WeightedZone piece(zone, BigInt(0),
                             {BigInt(0), BigInt(2), BigInt(-1)});
    const auto result = tamonitor::pta::maximize_affine_z3(piece, zone);
    require(result.kind == AffineOptimumKind::Finite &&
                result.value == BigRational(4) && result.domain_attained &&
                result.optimizer_or_limit.has_value(),
            "diagonal DBM 的 affine maximum 错误");
    require(tamonitor::pta::contains(zone, *result.optimizer_or_limit) &&
                tamonitor::pta::weight_at(piece, *result.optimizer_or_limit) ==
                    BigRational(4),
            "diagonal optimizer 无法精确回放");
}

void test_zero_objective_on_strict_domain() {
    // 0<x<1 不含整数，实际 optimizer valuation 必须经过有理数解析路径。
    const auto zone = interval(0, 1, true, true);
    const BigInt large("123456789012345678901234567890");
    const WeightedZone piece(zone, large, {BigInt(0), BigInt(0)}, false);
    const auto result = tamonitor::pta::maximize_affine_z3(piece, zone);

    require(result.kind == AffineOptimumKind::Finite &&
                result.value == BigRational(large),
            "零梯度的大整数 weight 必须保持精确");
    require(result.domain_attained && result.optimizer_is_actual &&
                result.optimizer_or_limit.has_value() &&
                tamonitor::pta::contains(zone, *result.optimizer_or_limit),
            "非空严格域上的常数目标仍应有实际 optimizer");
    require((*result.optimizer_or_limit)[1].denominator() != 1,
            "0<x<1 的 optimizer 应保留 Z3 精确有理 valuation");
    require(!piece.attained,
            "测试应保持 suffix attained 与几何 domain_attained 相互独立");
}

} // namespace

int main() {
    try {
        test_closed_maximum();
        test_strict_upper_limit();
        test_strict_lower_negative_rate();
        test_unbounded_above();
        test_empty_intersection();
        test_diagonal_objective();
        test_zero_objective_on_strict_domain();
        std::cout << "AffineOptimizerTests: all tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& exception) {
        std::cerr << "AffineOptimizerTests failed: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
