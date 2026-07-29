// 本文件实现 Roméo 风格 mixed 分析的 exact forward reachable-zone graph。

#include "ReachableZoneGraph.h"

#include <algorithm>
#include <chrono>
#include <deque>
#include <map>
#include <set>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using Clock = pardibaal::dim_t;
using SteadyClock = std::chrono::steady_clock;

bool timeout_reached(
    const SteadyClock::time_point start,
    std::uint64_t timeout_ms) {
    if (timeout_ms == 0) {
        return false;
    }
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        SteadyClock::now() - start);
    return elapsed.count() >= 0 &&
           static_cast<std::uint64_t>(elapsed.count()) >= timeout_ms;
}

std::uint64_t elapsed_milliseconds(const SteadyClock::time_point start) {
    const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        SteadyClock::now() - start);
    return static_cast<std::uint64_t>(
        std::max<std::int64_t>(0, elapsed.count()));
}

bool is_included_in(
    const pardibaal::DBM& candidate,
    const pardibaal::DBM& existing) {
    const auto relation = candidate.relation(existing);
    return relation.is_equal() || relation.is_subset();
}

}  // namespace

struct ReachabilitySnapshot::Impl {
    ReachabilityStatus status = ReachabilityStatus::ResourceLimit;
    bool exact = false;
    std::optional<ReachNodeId> initial_node;
    ReachabilityStatistics statistics;
    std::vector<ReachableNode> nodes;
    std::vector<ReachableArc> arcs;
    std::vector<std::vector<ReachArcId>> incoming;
    std::vector<std::vector<ReachArcId>> outgoing;
    std::shared_ptr<const WeightedAutomatonView> automaton;
};

ReachabilitySnapshot::ReachabilitySnapshot()
    : impl_(std::make_shared<Impl>()) {}

ReachabilitySnapshot::ReachabilitySnapshot(std::shared_ptr<const Impl> impl)
    : impl_(std::move(impl)) {}

ReachabilityStatus ReachabilitySnapshot::status() const noexcept {
    return impl_->status;
}

bool ReachabilitySnapshot::exact() const noexcept {
    return impl_->exact;
}

std::optional<ReachNodeId> ReachabilitySnapshot::initial_node() const noexcept {
    return impl_->initial_node;
}

const ReachabilityStatistics& ReachabilitySnapshot::statistics() const noexcept {
    return impl_->statistics;
}

const std::vector<ReachableNode>& ReachabilitySnapshot::nodes() const noexcept {
    return impl_->nodes;
}

const std::vector<ReachableArc>& ReachabilitySnapshot::arcs() const noexcept {
    return impl_->arcs;
}

const ReachableNode& ReachabilitySnapshot::node(ReachNodeId id) const {
    const auto index = static_cast<std::size_t>(id);
    const auto& result = impl_->nodes.at(index);
    if (result.id != id) {
        throw std::logic_error("ReachNodeId 与 snapshot 下标不一致");
    }
    return result;
}

const ReachableArc& ReachabilitySnapshot::arc(ReachArcId id) const {
    const auto index = static_cast<std::size_t>(id);
    const auto& result = impl_->arcs.at(index);
    if (result.id != id) {
        throw std::logic_error("ReachArcId 与 snapshot 下标不一致");
    }
    return result;
}

const std::vector<ReachArcId>& ReachabilitySnapshot::incoming_arcs(
    ReachNodeId id) const {
    (void)node(id);
    return impl_->incoming.at(static_cast<std::size_t>(id));
}

const std::vector<ReachArcId>& ReachabilitySnapshot::outgoing_arcs(
    ReachNodeId id) const {
    (void)node(id);
    return impl_->outgoing.at(static_cast<std::size_t>(id));
}

pardibaal::Federation ReachabilitySnapshot::support(LocationId location) const {
    pardibaal::Federation result;
    for (const auto& reachable : impl_->nodes) {
        if (reachable.location == location) {
            result.add(reachable.zone);
        }
    }
    return result;
}

bool ReachabilitySnapshot::compatible_with(
    const WeightedAutomatonView& automaton) const {
    if (!impl_->automaton ||
        impl_->automaton->dimension() != automaton.dimension() ||
        impl_->automaton->initial_location() != automaton.initial_location() ||
        impl_->automaton->locations().size() != automaton.locations().size() ||
        impl_->automaton->edges().size() != automaton.edges().size()) {
        return false;
    }

    for (const auto& expected : impl_->automaton->locations()) {
        try {
            const auto& actual = automaton.location(expected.id);
            if (!expected.invariant.relation(actual.invariant).is_equal()) {
                return false;
            }
        } catch (const std::out_of_range&) {
            return false;
        }
    }
    for (const auto& expected : impl_->automaton->edges()) {
        try {
            const auto& actual = automaton.edge(expected.id);
            if (expected.source != actual.source ||
                expected.target != actual.target ||
                expected.resets != actual.resets ||
                expected.label != actual.label ||
                !expected.guard.relation(actual.guard).is_equal()) {
                return false;
            }
        } catch (const std::out_of_range&) {
            return false;
        }
    }
    return true;
}

ReachabilitySnapshot compute_reachable_zone_graph(
    const WeightedAutomatonView& automaton,
    const GoalSpec& goals,
    const ReachabilityOptions& options) {
    const auto start = SteadyClock::now();
    auto impl = std::make_shared<ReachabilitySnapshot::Impl>();
    impl->automaton = std::make_shared<WeightedAutomatonView>(automaton);

    const auto finish = [&](ReachabilityStatus status) {
        impl->status = status;
        impl->exact = status == ReachabilityStatus::Complete;
        impl->statistics.elapsed_ms = elapsed_milliseconds(start);
        return ReachabilitySnapshot{impl};
    };

    std::set<LocationId> known_locations;
    std::map<LocationId, std::vector<std::size_t>> outgoing_edges;
    for (const auto& location : automaton.locations()) {
        known_locations.insert(location.id);
        outgoing_edges.emplace(
            location.id, automaton.outgoing_edge_indices(location.id));
    }

    std::set<LocationId> goal_locations;
    for (const auto goal : goals.locations) {
        if (known_locations.count(goal) == 0) {
            throw std::invalid_argument("GoalSpec 引用了不存在的 location");
        }
        goal_locations.insert(goal);
    }

    for (auto& [location, edge_indices] : outgoing_edges) {
        (void)location;
        std::sort(
            edge_indices.begin(), edge_indices.end(),
            [&](std::size_t lhs, std::size_t rhs) {
                return automaton.edge(lhs).id < automaton.edge(rhs).id;
            });
    }

    // Z0 = Future({0} ∩ Inv(l0)) ∩ Inv(l0)。先交 invariant 很重要：
    // 若 invariant 在时刻 0 不成立，不能从一个虚假初始点开始 delay。
    pardibaal::DBM initial_zone = pardibaal::DBM::zero(automaton.dimension());
    initial_zone.intersection(
        automaton.location(automaton.initial_location()).invariant);
    if (timeout_reached(start, options.timeout_ms)) {
        impl->statistics.timeout_hit = true;
        return finish(ReachabilityStatus::ResourceLimit);
    }
    if (initial_zone.is_empty()) {
        return finish(ReachabilityStatus::Complete);
    }
    initial_zone.future();
    initial_zone.intersection(
        automaton.location(automaton.initial_location()).invariant);
    if (timeout_reached(start, options.timeout_ms)) {
        impl->statistics.timeout_hit = true;
        return finish(ReachabilityStatus::ResourceLimit);
    }
    if (initial_zone.is_empty()) {
        return finish(ReachabilityStatus::Complete);
    }

    if (timeout_reached(start, options.timeout_ms)) {
        impl->statistics.timeout_hit = true;
        return finish(ReachabilityStatus::ResourceLimit);
    }
    if (options.max_nodes == 0) {
        impl->statistics.node_limit_hit = true;
        return finish(ReachabilityStatus::ResourceLimit);
    }

    const bool initial_is_goal =
        goal_locations.count(automaton.initial_location()) != 0;
    impl->nodes.push_back(ReachableNode{
        ReachNodeId{0}, automaton.initial_location(),
        std::move(initial_zone), initial_is_goal});
    impl->incoming.emplace_back();
    impl->outgoing.emplace_back();
    impl->initial_node = ReachNodeId{0};
    impl->statistics.nodes_created = 1;

    std::deque<ReachNodeId> worklist;
    worklist.push_back(ReachNodeId{0});
    bool interrupted = false;

    while (!worklist.empty() && !interrupted) {
        if (timeout_reached(start, options.timeout_ms)) {
            impl->statistics.timeout_hit = true;
            interrupted = true;
            break;
        }

        const ReachNodeId source_id = worklist.front();
        worklist.pop_front();
        // 展开时可能 push 新 node 并使 nodes vector 重分配，因此不能
        // 把 element reference 跨越整个 outgoing-edge 循环保存。
        const auto source_location =
            impl->nodes.at(static_cast<std::size_t>(source_id)).location;
        const bool source_is_goal =
            impl->nodes.at(static_cast<std::size_t>(source_id)).is_goal;
        const pardibaal::DBM source_zone =
            impl->nodes.at(static_cast<std::size_t>(source_id)).zone;
        if (source_is_goal) {
            ++impl->statistics.goal_cutoffs;
            continue;
        }
        ++impl->statistics.expanded;

        for (const auto edge_index : outgoing_edges.at(source_location)) {
            if (timeout_reached(start, options.timeout_ms)) {
                impl->statistics.timeout_hit = true;
                interrupted = true;
                break;
            }

            const auto& edge = automaton.edge(edge_index);

            pardibaal::DBM fire_zone = source_zone;
            fire_zone.intersection(edge.guard);
            if (fire_zone.is_empty()) {
                ++impl->statistics.empty_successors;
                continue;
            }

            pardibaal::DBM entry_zone = fire_zone;
            for (const Clock reset : edge.resets) {
                entry_zone.assign(reset, 0);
            }
            entry_zone.intersection(automaton.location(edge.target).invariant);
            if (entry_zone.is_empty()) {
                ++impl->statistics.empty_successors;
                continue;
            }

            pardibaal::DBM post_zone = entry_zone;
            post_zone.future();
            post_zone.intersection(automaton.location(edge.target).invariant);
            if (timeout_reached(start, options.timeout_ms)) {
                impl->statistics.timeout_hit = true;
                interrupted = true;
                break;
            }
            if (post_zone.is_empty()) {
                ++impl->statistics.empty_successors;
                continue;
            }
            ++impl->statistics.successor_candidates;

            std::optional<ReachNodeId> target_id;
            // 只做 candidate ⊆ existing 的单向 convergence。不删除已有小节点，
            // 否则旧 arc 的 delta/witness 会被不安全地重连。
            for (const auto& existing : impl->nodes) {
                if (existing.location == edge.target &&
                    is_included_in(post_zone, existing.zone)) {
                    target_id = existing.id;
                    ++impl->statistics.inclusion_reuses;
                    break;
                }
            }

            // 一条实际 Post 已被发现，但 arc 容量不足时图已不完整。
            // 必须在创建新 target 前检查，避免留下无入边的孤立节点。
            if (impl->arcs.size() >= options.max_arcs) {
                impl->statistics.arc_limit_hit = true;
                interrupted = true;
                break;
            }

            if (!target_id.has_value()) {
                if (impl->nodes.size() >= options.max_nodes) {
                    impl->statistics.node_limit_hit = true;
                    interrupted = true;
                    break;
                }
                target_id = static_cast<ReachNodeId>(impl->nodes.size());
                const bool target_is_goal = goal_locations.count(edge.target) != 0;
                impl->nodes.push_back(ReachableNode{
                    *target_id, edge.target, post_zone, target_is_goal});
                impl->incoming.emplace_back();
                impl->outgoing.emplace_back();
                ++impl->statistics.nodes_created;
                worklist.push_back(*target_id);
            }

            const ReachArcId arc_id =
                static_cast<ReachArcId>(impl->arcs.size());
            impl->arcs.push_back(ReachableArc{
                arc_id, source_id, *target_id, edge.id,
                std::move(fire_zone), std::move(entry_zone),
                std::move(post_zone)});
            impl->outgoing.at(static_cast<std::size_t>(source_id)).push_back(arc_id);
            impl->incoming.at(static_cast<std::size_t>(*target_id)).push_back(arc_id);
            ++impl->statistics.arcs_created;
        }
    }

    if (!interrupted && timeout_reached(start, options.timeout_ms)) {
        impl->statistics.timeout_hit = true;
        interrupted = true;
    }

    return finish(interrupted
        ? ReachabilityStatus::ResourceLimit
        : ReachabilityStatus::Complete);
}

std::string to_string(ReachabilityStatus status) {
    switch (status) {
        case ReachabilityStatus::Complete:
            return "complete";
        case ReachabilityStatus::ResourceLimit:
            return "incomplete_forward_resource_limit";
    }
    throw std::logic_error("unknown ReachabilityStatus");
}

}  // namespace tamonitor::pta
