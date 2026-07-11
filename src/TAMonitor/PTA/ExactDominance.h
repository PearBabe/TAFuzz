// 本文件实现 Parrot--Lime Definition 10 的精确 priced-zone 支配判定接口。

#ifndef TAMONITOR_PTA_EXACT_DOMINANCE_H
#define TAMONITOR_PTA_EXACT_DOMINANCE_H

#include <cstddef>
#include <cstdint>
#include <memory>

namespace tamonitor::pta {

struct WeightedZone;

enum class DominanceResult {
    Dominated,
    NotDominated,
    Unknown,
};

struct DominanceStatistics {
    std::size_t checks = 0;
    std::size_t zone_rejections = 0;
    std::size_t attainment_rejections = 0;
    std::size_t dominated = 0;
    std::size_t solver_unknown = 0;
};

/**
 * 精确判断一个已有 weighted zone 是否支配候选 weighted zone。
 *
 * 语义采用论文的 W=-V 约定：dominator 支配 candidate 当且仅当
 * candidate.zone ⊆ dominator.zone，且 candidate.zone 上处处满足
 * W_candidate ≤ W_dominator。UNKNOWN 永远不能作为可剪枝结论。
 */
class ExactDominance {
public:
    ExactDominance();
    ~ExactDominance();

    ExactDominance(const ExactDominance&) = delete;
    ExactDominance& operator=(const ExactDominance&) = delete;
    ExactDominance(ExactDominance&&) noexcept;
    ExactDominance& operator=(ExactDominance&&) noexcept;

    [[nodiscard]] DominanceResult check(
        const WeightedZone& dominator,
        const WeightedZone& candidate,
        std::uint64_t timeout_ms = 0);

    [[nodiscard]] const DominanceStatistics& statistics() const noexcept;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_EXACT_DOMINANCE_H
