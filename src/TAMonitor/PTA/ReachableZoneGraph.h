// 本文件声明 Roméo 风格 mixed 分析使用的精确、Goal 截断可达 Zone Graph。

#ifndef TAMONITOR_PTA_REACHABLE_ZONE_GRAPH_H
#define TAMONITOR_PTA_REACHABLE_ZONE_GRAPH_H

#include "BackwardPricedSolver.h"

#include <pardibaal/Federation.h>

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor::pta {

using ReachNodeId = std::uint64_t;
using ReachArcId = std::uint64_t;

/** 离散 location 与其上一个精确可达 DBM。 */
struct ReachableNode {
    ReachNodeId id;
    LocationId location;
    pardibaal::DBM zone;
    bool is_goal;
};

/**
 * 一次具体 timed-edge Post 的三个精确符号域。
 *
 * fire_zone  = source.zone ∩ guard
 * entry_zone = Reset(fire_zone) ∩ Inv(target)
 * post_zone  = Future(entry_zone) ∩ Inv(target)
 *
 * target node 可能是 post_zone 的真包含超集；因此 arc 始终单独保存
 * post_zone，不能用 target.zone 代替这条边的实际像。
 */
struct ReachableArc {
    ReachArcId id;
    ReachNodeId source;
    ReachNodeId target;
    EdgeId edge;
    pardibaal::DBM fire_zone;
    pardibaal::DBM entry_zone;
    pardibaal::DBM post_zone;
};

enum class ReachabilityStatus {
    Complete,
    ResourceLimit,
};

struct ReachabilityOptions {
    std::size_t max_nodes = 100'000;
    std::size_t max_arcs = 1'000'000;
    /** 0 表示不限时。 */
    std::uint64_t timeout_ms = 300'000;
};

struct ReachabilityStatistics {
    std::size_t expanded = 0;
    std::size_t nodes_created = 0;
    std::size_t arcs_created = 0;
    std::size_t successor_candidates = 0;
    std::size_t inclusion_reuses = 0;
    std::size_t empty_successors = 0;
    std::size_t goal_cutoffs = 0;
    std::uint64_t elapsed_ms = 0;
    bool node_limit_hit = false;
    bool arc_limit_hit = false;
    bool timeout_hit = false;
};

/** 不可变的 exact-forward 结果；NodeId/ArcId 与各自 vector 下标一致。 */
class ReachabilitySnapshot {
public:
    ReachabilitySnapshot();

    [[nodiscard]] ReachabilityStatus status() const noexcept;
    [[nodiscard]] bool exact() const noexcept;
    [[nodiscard]] std::optional<ReachNodeId> initial_node() const noexcept;
    [[nodiscard]] const ReachabilityStatistics& statistics() const noexcept;
    [[nodiscard]] const std::vector<ReachableNode>& nodes() const noexcept;
    [[nodiscard]] const std::vector<ReachableArc>& arcs() const noexcept;
    [[nodiscard]] const ReachableNode& node(ReachNodeId id) const;
    [[nodiscard]] const ReachableArc& arc(ReachArcId id) const;
    [[nodiscard]] const std::vector<ReachArcId>& incoming_arcs(
        ReachNodeId id) const;
    [[nodiscard]] const std::vector<ReachArcId>& outgoing_arcs(
        ReachNodeId id) const;
    [[nodiscard]] pardibaal::Federation support(LocationId location) const;
    /** 精确校验 graph 是否由同一 TA 结构生成；cost model 不参与绑定。 */
    [[nodiscard]] bool compatible_with(
        const WeightedAutomatonView& automaton) const;

private:
    struct Impl;
    std::shared_ptr<const Impl> impl_;

    explicit ReachabilitySnapshot(std::shared_ptr<const Impl> impl);
    friend ReachabilitySnapshot compute_reachable_zone_graph(
        const WeightedAutomatonView&,
        const GoalSpec&,
        const ReachabilityOptions&);
};

/** 用精确 DBM Post 构建首次进入 Goal 即停止展开的可达 Zone Graph。 */
[[nodiscard]] ReachabilitySnapshot compute_reachable_zone_graph(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const ReachabilityOptions& options = ReachabilityOptions{});

[[nodiscard]] std::string to_string(ReachabilityStatus status);

}  // namespace tamonitor::pta

#endif  // TAMONITOR_PTA_REACHABLE_ZONE_GRAPH_H
