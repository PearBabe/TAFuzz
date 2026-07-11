// 本文件定义后向 Priced-DBM 局部算法共享的精确数值与数据类型。

#ifndef TAMONITOR_PTA_PTATYPES_H
#define TAMONITOR_PTA_PTATYPES_H

#include <boost/multiprecision/cpp_int.hpp>
#include <boost/rational.hpp>

#include <pardibaal/DBM.h>

#include <optional>
#include <vector>

namespace tamonitor::pta {

using BigInt = boost::multiprecision::cpp_int;
using BigRational = boost::rational<BigInt>;
using RationalValuation = std::vector<BigRational>;

/**
 * 论文 Definition 3 的 weighted zone。
 *
 * rates 与 DBM 维数完全对齐；下标 0 是恒为 0 的参考钟，因而 rates[0]
 * 必须为 0。论文中的语义为：
 *
 *   W(v) = offset_weight + sum_x rates[x] * (v[x] - Delta_Z[x]).
 *
 * 后向算法保存 W=-V，所以 W 越大表示到目标的剩余成本 V 越小。
 */
struct WeightedZone {
    pardibaal::DBM zone;
    BigInt offset_weight;
    std::vector<BigInt> rates;
    bool attained;

    WeightedZone(pardibaal::DBM zone,
                 BigInt offset_weight,
                 std::vector<BigInt> rates,
                 bool attained = true);
};

enum class FacetKind {
    LOWER,
    UPPER,
};

/** Definition 6 的带权单时钟 facet。 */
struct WeightedFacet {
    WeightedZone weighted_zone;
    pardibaal::dim_t clock;
    pardibaal::val_t boundary;
    FacetKind kind;
    bool boundary_strict;
};

enum class DelayWitnessKind {
    ZERO,
    LOWER_FACET,
    UPPER_FACET,
};

/** 单个时间前驱分片及其最优 delay 的符号见证。 */
struct TimePredecessorPiece {
    WeightedZone weighted_zone;
    DelayWitnessKind witness_kind;
    std::optional<pardibaal::dim_t> facet_clock;
    std::optional<pardibaal::val_t> facet_bound;
};

/**
 * Theorem 2 的返回值。unbounded_below=true 表示 unbounded_domain 上 W 的
 * 上确界为 +infinity，等价于真实剩余成本 V=-W 无下界；这种情形不能
 * 伪装成空的不可达集合，也必须由全局 solver 继续反向传播该定义域。
 */
struct TimePredecessorResult {
    std::vector<TimePredecessorPiece> pieces;
    bool unbounded_below = false;
    /** valuation 属于该域时，W=+infinity（即 V=-infinity）。 */
    std::optional<pardibaal::DBM> unbounded_domain;
};

} // namespace tamonitor::pta

#endif // TAMONITOR_PTA_PTATYPES_H
