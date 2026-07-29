// 本文件实现后向 Priced-DBM 共享类型的构造期不变量检查。

#include "PTATypes.h"

#include <stdexcept>
#include <utility>

namespace tamonitor::pta {

WeightedZone::WeightedZone(pardibaal::DBM zone_value,
                           BigInt offset_weight_value,
                           std::vector<BigInt> rates_value,
                           bool attained_value)
    : zone(std::move(zone_value)),
      offset_weight(std::move(offset_weight_value)),
      rates(std::move(rates_value)),
      attained(attained_value) {
    // 后续 offset/facet 运算依赖 canonical DBM；构造时统一闭包，避免调用方
    // 通过 set() 构造非 canonical zone 后读到非最紧 bound。
    zone.close();
    if (rates.size() != zone.dimension()) {
        throw std::invalid_argument(
            "WeightedZone rates must have exactly one entry per DBM dimension");
    }
    if (rates.empty() || rates.front() != 0) {
        throw std::invalid_argument(
            "WeightedZone rate of the DBM reference clock must be zero");
    }
}

} // namespace tamonitor::pta
