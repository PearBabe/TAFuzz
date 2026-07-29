// 本文件声明基于 Roméo DBM::min/max 数学方法重写的精确仿射优化器。

#ifndef TAMONITOR_PTA_ROMEODBMOPTIMIZER_H
#define TAMONITOR_PTA_ROMEODBMOPTIMIZER_H

#include "AffineOptimizer.h"

namespace tamonitor::pta {

/**
 * 在 piece.zone 与 domain 的严格交集上精确计算 W 的上确界。
 *
 * 有限闭包最优值由 DBM 差分约束的 min-cost-transshipment
 * 对偶独立求得；Z3 普通 QF_LRA solver 仅认证该已知值是否在原
 * 严格域中取得，不使用 Z3 Optimize 计算目标值。
 * timeout_ms=0 表示不限时。
 */
[[nodiscard]] AffineSupremum maximize_affine_romeo_dbm(
    const WeightedZone& piece,
    const pardibaal::DBM& domain,
    std::uint64_t timeout_ms = 0);

} // namespace tamonitor::pta

#endif // TAMONITOR_PTA_ROMEODBMOPTIMIZER_H
