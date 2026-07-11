// 本文件声明 Parrot-Lime 2020 后向 weighted-zone 的局部 DBM 运算。

#ifndef TAMONITOR_PTA_PRICEDDBMOPS_H
#define TAMONITOR_PTA_PRICEDDBMOPS_H

#include "PTATypes.h"

#include <pardibaal/difference_bound_t.h>

#include <optional>
#include <vector>

namespace tamonitor::pta {

/** 返回 zone 的唯一坐标下确界 Delta_Z，包含下标 0 的参考钟。 */
[[nodiscard]] std::vector<BigInt> offset(const pardibaal::DBM& zone);

/** 精确判断有理数 valuation 是否属于 DBM。 */
[[nodiscard]] bool contains(const pardibaal::DBM& zone,
                            const RationalValuation& valuation);

[[nodiscard]] bool contains(const WeightedZone& zone,
                            const RationalValuation& valuation);

/** 按 Definition 3 精确求 W(v)。调用方须传入 zone 内 valuation。 */
[[nodiscard]] BigRational weight_at(const WeightedZone& zone,
                                    const RationalValuation& valuation);

/**
 * 在新几何 zone 上重定基点但保持同一个全局仿射函数。新 zone 可位于原
 * zone 的拓扑闭包中；空 zone 返回 nullopt。
 */
[[nodiscard]] std::optional<WeightedZone> rebase(
    const WeightedZone& weighted_zone,
    const pardibaal::DBM& new_zone);

/** Definition 5：几何求交并在新 offset 上重新计算权重。 */
[[nodiscard]] std::optional<WeightedZone> intersection(
    const WeightedZone& weighted_zone,
    const pardibaal::DBM& restriction);

/** 将所有有限严格 DBM bound 放宽为非严格 bound。 */
[[nodiscard]] pardibaal::DBM topological_closure(
    const pardibaal::DBM& zone);

/** Definition 6：枚举所有非空的 lower/upper facets。 */
[[nodiscard]] std::vector<WeightedFacet> lower_facets(
    const WeightedZone& weighted_zone);

[[nodiscard]] std::vector<WeightedFacet> upper_facets(
    const WeightedZone& weighted_zone);

/** Definition 7：先约束所有 reset clocks 为 0，再同时 relax/free。 */
[[nodiscard]] std::optional<WeightedZone> inverse_reset(
    const WeightedZone& weighted_zone,
    const std::vector<pardibaal::dim_t>& reset_clocks);

/** Definition 9：后向穿过离散边时执行 W <- W - edge_weight。 */
[[nodiscard]] WeightedZone subtract_edge_weight(
    const WeightedZone& weighted_zone,
    const BigInt& edge_weight);

/** Theorem 1：inverse reset、边权、guard、source invariant 的完整组合。 */
[[nodiscard]] std::optional<WeightedZone> action_predecessor(
    const WeightedZone& target,
    const std::vector<pardibaal::dim_t>& reset_clocks,
    const pardibaal::DBM& guard,
    const pardibaal::DBM& source_invariant,
    const BigInt& edge_weight);

/**
 * Definition 8：计算 weighted facet 的 closure-past 仿射值。严格约束下最终
 * attained 分类需要原 zone，由 time_predecessor 完成；不要单独据此字段下结论。
 */
[[nodiscard]] WeightedZone facet_past(
    const WeightedFacet& facet,
    const BigInt& location_rate);

/**
 * Theorem 2：计算 invariant-aware time predecessor。
 *
 * 严格边界的值在 closure 上取 supremum；返回 zone 再与 Past(original)
 * 相交，从而不会引入只能到达 closure、不能到达原 zone 的 valuation。
 * 每个 facet 还会按 Past(original intersect facet-equality) 精确拆分
 * attained/unattained 子域，处理同时命中其他严格 bound 的情形。
 */
[[nodiscard]] TimePredecessorResult time_predecessor(
    const WeightedZone& target,
    const pardibaal::DBM& invariant,
    const BigInt& location_rate);

} // namespace tamonitor::pta

#endif // TAMONITOR_PTA_PRICEDDBMOPS_H
