// 本文件声明在线前缀查询使用的精确仿射目标优化接口。

#ifndef TAMONITOR_PTA_AFFINEOPTIMIZER_H
#define TAMONITOR_PTA_AFFINEOPTIMIZER_H

#include "PTATypes.h"

#include <cstdint>
#include <optional>
#include <string>

namespace tamonitor::pta {

/** 仿射函数在 DBM 定义域上的上确界类别。 */
enum class AffineOptimumKind {
    Empty,
    Finite,
    PositiveInfinity,
    Unknown,
};

/** 在线查询可选择的优化器后端。 */
enum class PrefixOptimizerBackend {
    Z3,
    RomeoDBM,
    CrossCheck,
};

/**
 * maximize W 的证明级结果。
 *
 * optimizer_or_limit 是原严格域中的实际最优 valuation，或者只在拓扑闭包中
 * 达到上确界的极限 valuation；两者由 optimizer_is_actual 区分。
 */
struct AffineSupremum {
    AffineOptimumKind kind = AffineOptimumKind::Unknown;
    BigRational value = BigRational(0);
    bool domain_attained = false;
    std::optional<RationalValuation> optimizer_or_limit;
    bool optimizer_is_actual = false;
    bool upper_bound_proved = false;
    bool timed_out = false;
    std::uint64_t elapsed_us = 0;
    std::string diagnostic;
};

/**
 * 精确计算 piece 的全局仿射 weight 在 domain 交集上的上确界。
 *
 * timeout_ms=0 表示不限时。有限结果只有在普通 QF_LRA solver 已证明闭包中
 * 不存在更大值后才返回；否则返回 Unknown。
 */
[[nodiscard]] AffineSupremum maximize_affine_z3(
    const WeightedZone& piece,
    const pardibaal::DBM& domain,
    std::uint64_t timeout_ms = 0);

/** 统一调度 Z3、Roméo-derived 或双后端交叉检查。 */
[[nodiscard]] AffineSupremum maximize_affine(
    const WeightedZone& piece,
    const pardibaal::DBM& domain,
    PrefixOptimizerBackend backend,
    std::uint64_t timeout_ms = 0);

} // namespace tamonitor::pta

#endif // TAMONITOR_PTA_AFFINEOPTIMIZER_H
