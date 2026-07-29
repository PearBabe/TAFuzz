#include "rift/core/frontier.h"
#include "rift/core/sha256.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <deque>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

namespace rift::core {
namespace {

constexpr std::uint8_t kStaticPath = 1U;
constexpr std::uint8_t kModelledPath = 2U;
constexpr std::uint8_t kUnknownPath = 4U;
using NodeOrdinal = std::uint32_t;
using EdgeOrdinal = std::uint32_t;
constexpr NodeOrdinal kInvalidNodeOrdinal =
    std::numeric_limits<NodeOrdinal>::max();

std::size_t path_class_index(std::uint8_t path_class);

struct TraversalEdge {
    const std::string *edge_id = nullptr;
    NodeOrdinal source = kInvalidNodeOrdinal;
    NodeOrdinal target = kInvalidNodeOrdinal;
    RelationKind kind = RelationKind::Unknown;
    Certainty certainty = Certainty::Unknown;
    ContextCompatibilityResult compatibility;
    // Canonical ledger reasons are edge-invariant.  Materialize them once;
    // forward/support summaries may visit the same edge hundreds of times.
    std::vector<std::string> ledger_reasons;
    const InfluenceEdge *graph_edge = nullptr;
    const ModelFact *model_fact = nullptr;
};

struct TraversalGraph {
    std::vector<const ContextualNode *> nodes;
    std::unordered_map<std::string, NodeOrdinal> node_ordinals;
    std::vector<TraversalEdge> edges;
    std::deque<std::string> model_edge_ids;
    std::vector<std::vector<EdgeOrdinal>> outgoing;
    std::vector<std::vector<EdgeOrdinal>> incoming;
    bool materialization_complete = true;
    std::vector<std::string> gap_reasons;
};

struct ForwardPredecessor {
    NodeOrdinal source = kInvalidNodeOrdinal;
    EdgeOrdinal edge = std::numeric_limits<EdgeOrdinal>::max();
    std::uint8_t source_path_class = 0U;
};

struct ForwardResult {
    NodeOrdinal boundary = kInvalidNodeOrdinal;
    std::vector<std::uint8_t> states;
    std::vector<std::array<std::optional<ForwardPredecessor>, 3>>
        predecessors;
    FrontierForwardSummary summary;
    std::vector<std::string> reachable_model_fact_ids;
    bool enumeration_complete = true;
    bool compatibility_complete = true;
    std::vector<std::string> gap_reasons;
};

struct ReverseSuccessor {
    NodeOrdinal target = kInvalidNodeOrdinal;
    EdgeOrdinal edge = std::numeric_limits<EdgeOrdinal>::max();
    std::uint8_t target_path_class = 0U;
};

struct ReverseConeResult {
    std::vector<std::uint8_t> states;
    std::vector<std::uint8_t> root_states;
    std::vector<std::array<std::optional<ReverseSuccessor>, 3>> successors;
    // Ordinal-sorted filters preserve ledger order while avoiding full graph
    // scans for nodes/arcs that cannot reach this cone's roots.
    std::vector<NodeOrdinal> active_nodes;
    std::vector<EdgeOrdinal> active_target_edges;
    bool enumeration_complete = true;
    bool compatibility_complete = true;
    std::vector<std::string> gap_reasons;
};

struct CachedStateLedger {
    std::uint64_t reached_node_count = 0;
    std::string digest;
};

struct CachedTransitionLedger {
    std::uint64_t transition_count = 0;
    std::string digest;
    std::vector<std::string> model_fact_ids;
};

struct CachedSupportLedger {
    std::uint64_t transition_count = 0;
    std::string transition_digest;
    std::vector<std::string> model_fact_ids;
    std::string model_fact_digest;
};

struct FrontierLedgerCaches {
    // Keys are exact compact ledgers, not digest-only approximations.  The
    // unordered-map hash only selects a bucket; string equality resolves any
    // collision before a cached certificate value is reused.
    std::unordered_map<std::string, CachedStateLedger> states;
    std::unordered_map<std::string, CachedTransitionLedger> transitions;
    std::unordered_map<std::string, CachedSupportLedger> supports;
};

bool valid_sha256(const std::string &value) {
    return value.size() == 64U &&
           std::all_of(value.begin(), value.end(), [](const char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

StageStatus combine_status(const StageStatus left, const StageStatus right) {
    if (left == StageStatus::Failed || right == StageStatus::Failed) {
        return StageStatus::Failed;
    }
    if (left == StageStatus::ConservativeIncomplete ||
        right == StageStatus::ConservativeIncomplete) {
        return StageStatus::ConservativeIncomplete;
    }
    return StageStatus::Complete;
}

template <typename T>
void sort_unique(std::vector<T> &values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
}

void append_unique(std::vector<std::string> &values, const std::string &value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

void append_u64_le(std::string &material, const std::uint64_t value) {
    for (std::uint32_t shift = 0; shift < 64U; shift += 8U) {
        material.push_back(
            static_cast<char>((value >> shift) & 0xffU));
    }
}

void append_u32_le(std::string &material, const std::uint32_t value) {
    for (std::uint32_t shift = 0; shift < 32U; shift += 8U) {
        material.push_back(
            static_cast<char>((value >> shift) & 0xffU));
    }
}

std::uint32_t read_u32_le(
    const std::string_view material, const std::size_t offset) {
    std::uint32_t value = 0;
    for (std::uint32_t index = 0; index < 4U; ++index) {
        value |= static_cast<std::uint32_t>(
                     static_cast<unsigned char>(material[offset + index]))
                 << (index * 8U);
    }
    return value;
}

void append_ledger_field(
    std::string &material, const std::string_view value) {
    append_u64_le(material, value.size());
    material.append(value.data(), value.size());
}

class LedgerHasher {
public:
    void append_u64(const std::uint64_t value) {
        std::array<std::uint8_t, 8> bytes{};
        for (std::uint32_t index = 0; index < bytes.size(); ++index) {
            bytes[index] = static_cast<std::uint8_t>(
                value >> (index * 8U));
        }
        hasher_.update(bytes.data(), bytes.size());
    }

    void append_field(const std::string_view value) {
        append_u64(value.size());
        hasher_.update(value.data(), value.size());
    }

    [[nodiscard]] std::string final_hex() {
        return sha256_digest_hex(hasher_.final());
    }

private:
    Sha256 hasher_;
};

std::string value_type_material(const ValueType &type) {
    std::ostringstream material;
    material << static_cast<int>(type.kind) << '\0' << type.canonical << '\0';
    if (type.bit_width) {
        material << *type.bit_width;
    }
    material << '\0';
    if (type.is_signed) {
        material << (*type.is_signed ? "signed" : "unsigned");
    }
    material << '\0';
    if (type.unit) {
        material << *type.unit;
    }
    return material.str();
}

std::string action_identity_material(const ExternalAction &action) {
    std::ostringstream material;
    material << action.action_schema_id << '\0' << action.action_class << '\0'
             << action.channel << '\0' << action.operation << '\0'
             << value_type_material(action.payload_type) << '\0'
             << action.payload_slot << '\0' << action.scope_schema << '\0'
             << action.generation_schema << '\0' << action.timing_capability
             << '\0' << action.required_capability;
    return material.str();
}

std::string traversal_contract_material(
    const FrontierTraversalContract &contract) {
    std::string material;
    append_ledger_field(material, "rift-frontier-traversal-contract/1.0.0");
    for (const std::string *field : {
             &contract.algorithm, &contract.algorithm_version,
             &contract.node_order, &contract.edge_order,
             &contract.path_class_encoding, &contract.meet_ledger,
             &contract.reach_ledger, &contract.transition_ledger,
             &contract.compatibility, &contract.model_arc_policy,
             &contract.exemplar_policy}) {
        append_ledger_field(material, *field);
    }
    append_u64_le(material, contract.maximum_path_exemplars);
    append_u64_le(material, contract.max_materialized_model_edges);
    append_u64_le(
        material, contract.max_forward_states_per_attachment);
    return material;
}

void normalize_provenance(std::vector<ModelProvenance> &items) {
    for (ModelProvenance &item : items) {
        sort_unique(item.selector_ids);
        sort_unique(item.capture_ids);
        sort_unique(item.matched_semantic_node_ids);
    }
    std::sort(
        items.begin(), items.end(),
        [](const ModelProvenance &left, const ModelProvenance &right) {
            return std::tie(
                       left.model_pack_sha256, left.model_pack_id,
                       left.model_pack_version, left.layer, left.rule_id,
                       left.emit_id, left.selector_ids, left.capture_ids,
                       left.matched_semantic_node_ids) <
                   std::tie(
                       right.model_pack_sha256, right.model_pack_id,
                       right.model_pack_version, right.layer, right.rule_id,
                       right.emit_id, right.selector_ids, right.capture_ids,
                       right.matched_semantic_node_ids);
        });
}

void normalize_action(ExternalAction &action) {
    normalize_provenance(action.provenance);
}

bool prefix_with_one_extra(
    const std::vector<std::string> &shorter,
    const std::vector<std::string> &longer) {
    return longer.size() == shorter.size() + 1U &&
           std::equal(shorter.begin(), shorter.end(), longer.begin());
}

bool is_terminal_phase(const LifecyclePhase phase) {
    return phase == LifecyclePhase::Cancelled ||
           phase == LifecyclePhase::Destroyed;
}

ContextCompatibilityResult contextual_compatibility_impl(
    const ContextualNode &source, const ContextualNode &target,
    const RelationKind relation_kind) {
    ContextCompatibilityResult result;
    const auto make_unknown = [&result](const std::string &reason) {
        if (result.verdict != WitnessCompatibility::Incompatible) {
            result.verdict = WitnessCompatibility::Unknown;
        }
        append_unique(result.reasons, reason);
    };
    const auto make_incompatible = [&result](const std::string &reason) {
        result.verdict = WitnessCompatibility::Incompatible;
        append_unique(result.reasons, reason);
    };

    if (source.call_context.truncated || target.call_context.truncated) {
        make_unknown("call context is truncated");
    } else if (source.call_context.callsite_ids !=
               target.call_context.callsite_ids) {
        bool balanced = false;
        if (relation_kind == RelationKind::Call) {
            balanced = prefix_with_one_extra(
                source.call_context.callsite_ids,
                target.call_context.callsite_ids);
        } else if (relation_kind == RelationKind::Return) {
            balanced = prefix_with_one_extra(
                target.call_context.callsite_ids,
                source.call_context.callsite_ids);
        }
        const bool global_transfer =
            source.abstract_object.abstraction == ObjectAbstraction::Global ||
            target.abstract_object.abstraction == ObjectAbstraction::Global;
        if (!balanced && !global_transfer) {
            make_unknown("call contexts are not proven concatenable");
        }
    }

    if (source.scope.status == IdentityStatus::Exact &&
        target.scope.status == IdentityStatus::Exact &&
        source.scope.scope_id != target.scope.scope_id) {
        make_unknown("exact scope identities differ across transfer");
    }
    if (source.generation.kind == IdentityStatus::Exact &&
        target.generation.kind == IdentityStatus::Exact &&
        source.generation.identity && target.generation.identity &&
        source.generation.identity != target.generation.identity) {
        make_unknown("exact generation identities differ across transfer");
    }
    if (source.task_context.certainty == Certainty::Must &&
        target.task_context.certainty == Certainty::Must &&
        source.task_context.context_id && target.task_context.context_id &&
        source.task_context.context_id != target.task_context.context_id &&
        relation_kind != RelationKind::Call &&
        relation_kind != RelationKind::Return) {
        make_unknown("task contexts differ without a proven event transfer");
    }
    if (is_terminal_phase(source.lifecycle_phase) &&
        (target.lifecycle_phase == LifecyclePhase::Active ||
         target.lifecycle_phase == LifecyclePhase::Committed) &&
        relation_kind != RelationKind::Call &&
        relation_kind != RelationKind::Return) {
        make_unknown("terminal-to-active lifecycle transfer is not proven");
    }

    const bool object_preserving =
        relation_kind == RelationKind::Object ||
        relation_kind == RelationKind::Field ||
        relation_kind == RelationKind::Alias;
    if (object_preserving &&
        source.abstract_object.certainty == Certainty::Must &&
        target.abstract_object.certainty == Certainty::Must &&
        source.abstract_object.object_id != target.abstract_object.object_id) {
        make_incompatible(
            "object-preserving relation joins distinct exact objects");
    }
    sort_unique(result.reasons);
    return result;
}

std::uint8_t certainty_mask(const Certainty certainty) {
    switch (certainty) {
    case Certainty::Must:
    case Certainty::May:
        return kStaticPath;
    case Certainty::Modelled:
        return kModelledPath;
    case Certainty::Unknown:
        return kUnknownPath;
    }
    return kUnknownPath;
}

std::uint8_t compose_one(
    const std::uint8_t path_class, const TraversalEdge &edge) {
    if (edge.compatibility.verdict == WitnessCompatibility::Incompatible) {
        return 0U;
    }
    if (path_class == kUnknownPath ||
        edge.compatibility.verdict == WitnessCompatibility::Unknown ||
        edge.certainty == Certainty::Unknown) {
        return kUnknownPath;
    }
    if (path_class == kModelledPath ||
        edge.certainty == Certainty::Modelled) {
        return kModelledPath;
    }
    return kStaticPath;
}

std::uint8_t compose_mask(
    const std::uint8_t mask, const TraversalEdge &edge) {
    std::uint8_t result = 0U;
    for (const std::uint8_t path_class :
         {kStaticPath, kModelledPath, kUnknownPath}) {
        if ((mask & path_class) != 0U) {
            result |= compose_one(path_class, edge);
        }
    }
    return result;
}

bool model_vm_complete(const ModelFactOverlay &overlay) {
    return overlay.status == StageStatus::Complete &&
           overlay.unknown_outcomes.empty() &&
           std::all_of(
               overlay.resource_ledger.begin(), overlay.resource_ledger.end(),
               [](const ModelResourceLedgerEntry &entry) {
                   return entry.complete;
               });
}

TraversalGraph build_traversal_graph(
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const FrontierOptions &options) {
    TraversalGraph result;
    result.nodes.reserve(graph.nodes.size());
    for (const ContextualNode &node : graph.nodes) {
        result.nodes.push_back(&node);
    }
    std::sort(
        result.nodes.begin(), result.nodes.end(),
        [](const ContextualNode *left, const ContextualNode *right) {
            return left->node_id < right->node_id;
        });
    result.node_ordinals.reserve(result.nodes.size());
    std::map<std::string, std::vector<NodeOrdinal>> by_semantic;
    for (std::size_t index = 0; index < result.nodes.size(); ++index) {
        const NodeOrdinal ordinal = static_cast<NodeOrdinal>(index);
        result.node_ordinals.emplace(result.nodes[index]->node_id, ordinal);
        by_semantic[result.nodes[index]->semantic_node_id].push_back(ordinal);
    }
    for (auto &[semantic, instances] : by_semantic) {
        (void)semantic;
        std::sort(
            instances.begin(), instances.end(),
            [&result](const NodeOrdinal left, const NodeOrdinal right) {
                return result.nodes[left]->node_id <
                       result.nodes[right]->node_id;
            });
    }

    std::vector<const InfluenceEdge *> graph_edges;
    graph_edges.reserve(graph.edges.size());
    for (const InfluenceEdge &edge : graph.edges) {
        graph_edges.push_back(&edge);
    }
    std::sort(
        graph_edges.begin(), graph_edges.end(),
        [](const InfluenceEdge *left, const InfluenceEdge *right) {
            return left->edge_id < right->edge_id;
        });
    result.edges.reserve(graph.edges.size());
    for (const InfluenceEdge *edge : graph_edges) {
        const auto source = result.node_ordinals.find(edge->source_node_id);
        const auto target = result.node_ordinals.find(edge->target_node_id);
        if (source == result.node_ordinals.end() ||
            target == result.node_ordinals.end()) {
            result.materialization_complete = false;
            append_unique(
                result.gap_reasons,
                "contextual graph edge has an unresolved endpoint");
            continue;
        }
        TraversalEdge materialized;
        materialized.edge_id = &edge->edge_id;
        materialized.source = source->second;
        materialized.target = target->second;
        materialized.kind = edge->kind;
        materialized.certainty = edge->certainty;
        materialized.compatibility = contextual_compatibility_impl(
            *result.nodes[source->second], *result.nodes[target->second],
            edge->kind);
        materialized.graph_edge = edge;
        result.edges.push_back(std::move(materialized));
    }

    std::vector<const ModelFact *> facts;
    for (const ModelFact &fact : overlay.semantic_facts) {
        if (fact.target_semantic_node_id) {
            facts.push_back(&fact);
        }
    }
    std::sort(
        facts.begin(), facts.end(),
        [](const ModelFact *left, const ModelFact *right) {
            return left->fact_id < right->fact_id;
        });
    std::uint64_t materialized_count = 0;
    bool materialization_limit_exhausted = false;
    for (const ModelFact *fact : facts) {
        const auto sources = by_semantic.find(fact->source_semantic_node_id);
        const auto targets = by_semantic.find(*fact->target_semantic_node_id);
        if (sources == by_semantic.end() || targets == by_semantic.end()) {
            result.materialization_complete = false;
            append_unique(
                result.gap_reasons,
                "model fact has no contextual instance for an endpoint");
            continue;
        }
        for (const NodeOrdinal source : sources->second) {
            for (const NodeOrdinal target : targets->second) {
                if (materialized_count >=
                    options.max_materialized_model_edges) {
                    result.materialization_complete = false;
                    materialization_limit_exhausted = true;
                    append_unique(
                        result.gap_reasons,
                        "model-edge materialization resource limit reached");
                    break;
                }
                TraversalEdge edge;
                edge.source = source;
                edge.target = target;
                edge.kind = RelationKind::Unknown;
                edge.certainty = fact->certainty;
                edge.model_fact = fact;
                result.model_edge_ids.push_back(stable_id(
                    "frontier-edge",
                    fact->fact_id + '\0' + result.nodes[source]->node_id +
                        '\0' + result.nodes[target]->node_id));
                edge.edge_id = &result.model_edge_ids.back();
                edge.compatibility = contextual_compatibility_impl(
                    *result.nodes[source], *result.nodes[target],
                    RelationKind::Unknown);
                result.edges.push_back(std::move(edge));
                ++materialized_count;
            }
            if (materialization_limit_exhausted) {
                break;
            }
        }
        if (materialization_limit_exhausted) {
            break;
        }
    }
    std::sort(
        result.edges.begin(), result.edges.end(),
        [](const TraversalEdge &left, const TraversalEdge &right) {
            return std::make_tuple(
                       left.model_fact == nullptr ? 0 : 1, *left.edge_id,
                       left.source, left.target) <
                   std::make_tuple(
                       right.model_fact == nullptr ? 0 : 1, *right.edge_id,
                       right.source, right.target);
        });
    for (TraversalEdge &edge : result.edges) {
        edge.ledger_reasons = edge.compatibility.reasons;
        if (edge.graph_edge != nullptr) {
            edge.ledger_reasons.insert(
                edge.ledger_reasons.end(),
                edge.graph_edge->uncertainty_reasons.begin(),
                edge.graph_edge->uncertainty_reasons.end());
        }
        sort_unique(edge.ledger_reasons);
    }
    result.outgoing.resize(result.nodes.size());
    result.incoming.resize(result.nodes.size());
    for (std::size_t index = 0; index < result.edges.size(); ++index) {
        const EdgeOrdinal edge_ordinal = static_cast<EdgeOrdinal>(index);
        const TraversalEdge &edge = result.edges[index];
        result.outgoing[edge.source].push_back(edge_ordinal);
        result.incoming[edge.target].push_back(edge_ordinal);
    }
    sort_unique(result.gap_reasons);
    return result;
}

ForwardResult forward_reach(
    const std::string &boundary_node_id, const Certainty attachment_certainty,
    const TraversalGraph &graph, const FrontierOptions &options,
    FrontierLedgerCaches &ledger_caches) {
    ForwardResult result;
    const auto boundary = graph.node_ordinals.find(boundary_node_id);
    result.states.assign(graph.nodes.size(), 0U);
    result.predecessors.resize(graph.nodes.size());
    if (boundary == graph.node_ordinals.end()) {
        result.enumeration_complete = false;
        result.gap_reasons.push_back(
            "boundary contextual node is absent from traversal graph");
        return result;
    }
    result.boundary = boundary->second;
    std::deque<NodeOrdinal> worklist;
    result.states[result.boundary] = certainty_mask(attachment_certainty);
    worklist.push_back(result.boundary);
    std::uint64_t changes = 1;
    while (!worklist.empty()) {
        const NodeOrdinal source = worklist.front();
        worklist.pop_front();
        const std::uint8_t source_state = result.states[source];
        for (const EdgeOrdinal edge_ordinal : graph.outgoing[source]) {
            const TraversalEdge &edge = graph.edges[edge_ordinal];
            if (edge.compatibility.verdict == WitnessCompatibility::Unknown) {
                // UNKNOWN is an explicitly represented path class, not an
                // enumeration gap.  The ledger remains complete while the
                // affected path is conservatively downgraded.
                for (const std::string &reason : edge.compatibility.reasons) {
                    append_unique(result.gap_reasons, reason);
                }
            }
            std::uint8_t candidate = 0U;
            std::array<std::optional<ForwardPredecessor>, 3> additions;
            for (const std::uint8_t source_class :
                 {kStaticPath, kModelledPath, kUnknownPath}) {
                if ((source_state & source_class) == 0U) {
                    continue;
                }
                const std::uint8_t target_class =
                    compose_one(source_class, edge);
                candidate |= target_class;
                if (target_class != 0U) {
                    const std::size_t index = target_class == kStaticPath
                        ? 0U
                        : target_class == kModelledPath ? 1U : 2U;
                    if (!additions[index]) {
                        additions[index] = ForwardPredecessor{
                            source, edge_ordinal, source_class};
                    }
                }
            }
            if (candidate == 0U) {
                continue;
            }
            std::uint8_t &prior = result.states[edge.target];
            const std::uint8_t merged = prior | candidate;
            if (merged == prior) {
                continue;
            }
            if (changes >= options.max_forward_states_per_attachment) {
                result.enumeration_complete = false;
                append_unique(
                    result.gap_reasons,
                    "forward-state resource limit reached");
                worklist.clear();
                break;
            }
            const std::uint8_t newly_added = merged & ~prior;
            prior = merged;
            for (const std::uint8_t target_class :
                 {kStaticPath, kModelledPath, kUnknownPath}) {
                if ((newly_added & target_class) == 0U) {
                    continue;
                }
                const std::size_t index = target_class == kStaticPath
                    ? 0U
                    : target_class == kModelledPath ? 1U : 2U;
                result.predecessors[edge.target][index] = additions[index];
            }
            ++changes;
            worklist.push_back(edge.target);
        }
    }
    std::string state_signature(result.states.begin(), result.states.end());
    auto cached_state = ledger_caches.states.find(state_signature);
    if (cached_state == ledger_caches.states.end()) {
        CachedStateLedger ledger;
        for (const std::uint8_t state : result.states) {
            if (state != 0U) {
                ++ledger.reached_node_count;
            }
        }
        LedgerHasher hasher;
        hasher.append_field("rift-reach-ledger/lp-u64le/1.0.0");
        hasher.append_u64(ledger.reached_node_count);
        for (std::size_t ordinal = 0; ordinal < result.states.size();
             ++ordinal) {
            const std::uint8_t state = result.states[ordinal];
            if (state == 0U) {
                continue;
            }
            hasher.append_field(graph.nodes[ordinal]->node_id);
            hasher.append_u64(state);
        }
        ledger.digest = hasher.final_hex();
        cached_state = ledger_caches.states
                           .emplace(
                               std::move(state_signature), std::move(ledger))
                           .first;
    }
    result.summary.reached_node_count =
        cached_state->second.reached_node_count;
    result.summary.reached_state_ledger_sha256 = cached_state->second.digest;

    // Five bytes per record are sufficient for an exact cache key because
    // edge ordinals are stable for this TraversalGraph and the path mask is a
    // byte.  Full IDs remain in the certificate ledger on a cache miss.
    constexpr std::size_t kCompactTransitionBytes = 5U;
    std::string transition_signature;
    transition_signature.reserve(
        graph.edges.size() * kCompactTransitionBytes);
    for (std::size_t ordinal = 0; ordinal < graph.edges.size(); ++ordinal) {
        const TraversalEdge &edge = graph.edges[ordinal];
        if (edge.source >= result.states.size() ||
            edge.target >= result.states.size() || edge.edge_id == nullptr) {
            continue;
        }
        const std::uint8_t contribution =
            compose_mask(result.states[edge.source], edge) &
            result.states[edge.target];
        if (contribution == 0U) {
            continue;
        }
        append_u32_le(
            transition_signature, static_cast<EdgeOrdinal>(ordinal));
        transition_signature.push_back(static_cast<char>(contribution));
    }
    auto cached_transition =
        ledger_caches.transitions.find(transition_signature);
    if (cached_transition == ledger_caches.transitions.end()) {
        CachedTransitionLedger ledger;
        ledger.transition_count =
            transition_signature.size() / kCompactTransitionBytes;
        LedgerHasher hasher;
        hasher.append_field("rift-transition-ledger/lp-u64le/1.0.0");
        hasher.append_u64(ledger.transition_count);
        for (std::size_t offset = 0; offset < transition_signature.size();
             offset += kCompactTransitionBytes) {
            const EdgeOrdinal ordinal =
                read_u32_le(transition_signature, offset);
            const std::uint8_t contribution = static_cast<std::uint8_t>(
                transition_signature[offset + 4U]);
            const TraversalEdge &edge = graph.edges[ordinal];
            hasher.append_field(
                edge.model_fact == nullptr ? "GRAPH_EDGE" : "MODEL_ARC");
            hasher.append_field(*edge.edge_id);
            hasher.append_field(graph.nodes[edge.source]->node_id);
            hasher.append_field(graph.nodes[edge.target]->node_id);
            hasher.append_u64(contribution);
            hasher.append_u64(static_cast<std::uint64_t>(edge.kind));
            hasher.append_u64(static_cast<std::uint64_t>(edge.certainty));
            hasher.append_u64(
                static_cast<std::uint64_t>(edge.compatibility.verdict));
            hasher.append_field(
                edge.model_fact == nullptr ? "" : edge.model_fact->fact_id);
            hasher.append_u64(edge.ledger_reasons.size());
            for (const std::string &reason : edge.ledger_reasons) {
                hasher.append_field(reason);
            }
            if (edge.model_fact != nullptr) {
                ledger.model_fact_ids.push_back(edge.model_fact->fact_id);
            }
        }
        sort_unique(ledger.model_fact_ids);
        ledger.digest = hasher.final_hex();
        cached_transition = ledger_caches.transitions
                                .emplace(
                                    std::move(transition_signature),
                                    std::move(ledger))
                                .first;
    }
    result.summary.reachable_transition_count =
        cached_transition->second.transition_count;
    result.summary.reachable_transition_ledger_sha256 =
        cached_transition->second.digest;
    result.reachable_model_fact_ids =
        cached_transition->second.model_fact_ids;
    result.summary.enumeration_complete =
        result.enumeration_complete && graph.materialization_complete;
    sort_unique(result.gap_reasons);
    return result;
}

std::uint8_t cone_membership_mask(const ConeMembership membership) {
    switch (membership) {
    case ConeMembership::MustInfluence:
    case ConeMembership::MayInfluence:
        return kStaticPath;
    case ConeMembership::ModelledInfluence:
        return kModelledPath;
    case ConeMembership::UnknownInfluence:
        return kUnknownPath;
    }
    return kUnknownPath;
}

ReverseConeResult reverse_cone_reach(
    const ApInfluenceCone &cone, const TraversalGraph &graph,
    const FrontierOptions &options) {
    ReverseConeResult result;
    result.states.assign(graph.nodes.size(), 0U);
    result.root_states.assign(graph.nodes.size(), 0U);
    result.successors.resize(graph.nodes.size());
    std::unordered_map<std::string, ConeMembership> memberships;
    memberships.reserve(cone.members.size());
    for (const ConeMember &member : cone.members) {
        memberships.emplace(member.node_id, member.membership);
    }
    std::set<std::string> root_ids;
    for (const CandidateAccount &account : cone.candidate_accounting) {
        if (account.disposition != CandidateDisposition::Included) {
            continue;
        }
        root_ids.insert(
            account.root_node_ids.begin(), account.root_node_ids.end());
    }
    // Valid M4 cones encode roots with an empty source-to-root witness.  Keep
    // this structural fallback for imported/legacy cones whose candidate
    // accounting predates explicit root IDs; it is still property-independent
    // and is fully bound by the cone digest.
    if (root_ids.empty()) {
        for (const ConeMember &member : cone.members) {
            if (member.witness_edge_ids.empty()) {
                root_ids.insert(member.node_id);
            }
        }
    }
    std::deque<NodeOrdinal> worklist;
    std::uint64_t changes = 0;
    for (const std::string &root_id : root_ids) {
        const auto ordinal = graph.node_ordinals.find(root_id);
        const auto membership = memberships.find(root_id);
        if (ordinal == graph.node_ordinals.end() ||
            membership == memberships.end()) {
            result.enumeration_complete = false;
            append_unique(
                result.gap_reasons,
                "cone root is absent from traversal graph or member ledger");
            continue;
        }
        const std::uint8_t root_mask =
            cone_membership_mask(membership->second);
        result.root_states[ordinal->second] |= root_mask;
        const std::uint8_t merged =
            result.states[ordinal->second] | root_mask;
        if (merged != result.states[ordinal->second]) {
            result.states[ordinal->second] = merged;
            worklist.push_back(ordinal->second);
            ++changes;
        }
    }
    if (root_ids.empty()) {
        result.enumeration_complete = false;
        result.gap_reasons.push_back("cone has no included contextual root");
    }
    while (!worklist.empty()) {
        const NodeOrdinal target = worklist.front();
        worklist.pop_front();
        const std::uint8_t target_state = result.states[target];
        for (const EdgeOrdinal edge_ordinal : graph.incoming[target]) {
            const TraversalEdge &edge = graph.edges[edge_ordinal];
            if (edge.edge_id == nullptr) {
                continue;
            }
            if (edge.compatibility.verdict ==
                WitnessCompatibility::Incompatible) {
                continue;
            }
            if (edge.compatibility.verdict == WitnessCompatibility::Unknown) {
                for (const std::string &reason : edge.compatibility.reasons) {
                    append_unique(result.gap_reasons, reason);
                }
            }
            std::uint8_t candidate = 0U;
            std::array<std::optional<ReverseSuccessor>, 3> additions;
            for (const std::uint8_t target_class :
                 {kStaticPath, kModelledPath, kUnknownPath}) {
                if ((target_state & target_class) == 0U) {
                    continue;
                }
                const std::uint8_t source_class =
                    compose_one(target_class, edge);
                candidate |= source_class;
                if (source_class != 0U) {
                    const std::size_t index =
                        path_class_index(source_class);
                    if (!additions[index]) {
                        additions[index] = ReverseSuccessor{
                            target, edge_ordinal, target_class};
                    }
                }
            }
            if (candidate == 0U) {
                continue;
            }
            std::uint8_t &prior = result.states[edge.source];
            const std::uint8_t merged = prior | candidate;
            if (merged == prior) {
                continue;
            }
            if (changes >= options.max_forward_states_per_attachment) {
                result.enumeration_complete = false;
                append_unique(
                    result.gap_reasons,
                    "reverse-cone state resource limit reached");
                worklist.clear();
                break;
            }
            const std::uint8_t newly_added = merged & ~prior;
            prior = merged;
            for (const std::uint8_t source_class :
                 {kStaticPath, kModelledPath, kUnknownPath}) {
                if ((newly_added & source_class) == 0U) {
                    continue;
                }
                const std::size_t index = path_class_index(source_class);
                result.successors[edge.source][index] = additions[index];
            }
            ++changes;
            worklist.push_back(edge.source);
        }
    }
    if (!graph.materialization_complete) {
        result.enumeration_complete = false;
        append_unique(
            result.gap_reasons,
            "traversal graph materialization is conservative-incomplete");
    }
    if (cone.status != StageStatus::Complete) {
        result.enumeration_complete = false;
        append_unique(
            result.gap_reasons,
            "influence cone is conservative-incomplete");
    }
    for (std::size_t ordinal = 0; ordinal < result.states.size(); ++ordinal) {
        if (result.states[ordinal] != 0U) {
            result.active_nodes.push_back(static_cast<NodeOrdinal>(ordinal));
        }
    }
    for (std::size_t ordinal = 0; ordinal < graph.edges.size(); ++ordinal) {
        const TraversalEdge &edge = graph.edges[ordinal];
        if (edge.target < result.states.size() &&
            result.states[edge.target] != 0U) {
            result.active_target_edges.push_back(
                static_cast<EdgeOrdinal>(ordinal));
        }
    }
    sort_unique(result.gap_reasons);
    return result;
}

std::uint8_t compose_path_classes(
    const std::uint8_t left, const std::uint8_t right) {
    if (left == kUnknownPath || right == kUnknownPath) {
        return kUnknownPath;
    }
    if (left == kModelledPath || right == kModelledPath) {
        return kModelledPath;
    }
    return kStaticPath;
}

std::uint8_t product_path_mask(
    const std::uint8_t forward_mask, const std::uint8_t reverse_mask) {
    std::uint8_t result = 0U;
    for (const std::uint8_t forward_class :
         {kStaticPath, kModelledPath, kUnknownPath}) {
        if ((forward_mask & forward_class) == 0U) {
            continue;
        }
        for (const std::uint8_t reverse_class :
             {kStaticPath, kModelledPath, kUnknownPath}) {
            if ((reverse_mask & reverse_class) != 0U) {
                result |= compose_path_classes(
                    forward_class, reverse_class);
            }
        }
    }
    return result;
}

std::size_t path_class_index(const std::uint8_t path_class) {
    return path_class == kStaticPath ? 0U
         : path_class == kModelledPath ? 1U
                                      : 2U;
}

struct ProductPathClasses {
    std::uint8_t forward = 0U;
    std::uint8_t root = 0U;
};

std::optional<ProductPathClasses> choose_product_path_classes(
    const std::uint8_t forward_mask, const std::uint8_t root_mask,
    const std::uint8_t effective_class) {
    for (const std::uint8_t forward_class :
         {kStaticPath, kModelledPath, kUnknownPath}) {
        if ((forward_mask & forward_class) == 0U) {
            continue;
        }
        for (const std::uint8_t root_class :
             {kStaticPath, kModelledPath, kUnknownPath}) {
            if ((root_mask & root_class) != 0U &&
                compose_path_classes(forward_class, root_class) ==
                    effective_class) {
                return ProductPathClasses{forward_class, root_class};
            }
        }
    }
    return std::nullopt;
}

bool reconstruct_forward_path(
    const NodeOrdinal target, const std::uint8_t target_path_class,
    const ForwardResult &forward, const TraversalGraph &graph,
    FrontierPathExemplar &exemplar) {
    NodeOrdinal cursor = target;
    std::uint8_t path_class = target_path_class;
    std::vector<FrontierPathStep> reverse_steps;
    std::uint64_t guard = 0;
    while (cursor != forward.boundary) {
        if (cursor >= forward.predecessors.size() || path_class == 0U) {
            return false;
        }
        const auto &predecessor =
            forward.predecessors[cursor][path_class_index(path_class)];
        if (!predecessor || predecessor->edge >= graph.edges.size()) {
            return false;
        }
        const TraversalEdge &edge = graph.edges[predecessor->edge];
        if (edge.target != cursor || edge.edge_id == nullptr) {
            return false;
        }
        FrontierPathStep step;
        step.kind = edge.model_fact == nullptr
            ? FrontierPathStepKind::GraphEdge
            : FrontierPathStepKind::ModelArc;
        step.source_node_id = graph.nodes[edge.source]->node_id;
        step.target_node_id = graph.nodes[edge.target]->node_id;
        if (edge.graph_edge != nullptr) {
            step.graph_edge_id = edge.graph_edge->edge_id;
        }
        if (edge.model_fact != nullptr) {
            step.model_fact_id = edge.model_fact->fact_id;
        }
        reverse_steps.push_back(std::move(step));
        if (edge.compatibility.verdict == WitnessCompatibility::Unknown ||
            edge.certainty == Certainty::Unknown) {
            for (const std::string &reason : edge.compatibility.reasons) {
                append_unique(exemplar.uncertainty_reasons, reason);
            }
            if (edge.graph_edge != nullptr) {
                for (const std::string &reason :
                     edge.graph_edge->uncertainty_reasons) {
                    append_unique(exemplar.uncertainty_reasons, reason);
                }
            }
        }
        cursor = predecessor->source;
        path_class = predecessor->source_path_class;
        ++guard;
        if (guard > graph.nodes.size()) {
            return false;
        }
    }
    exemplar.forward_steps.assign(
        reverse_steps.rbegin(), reverse_steps.rend());
    return true;
}

bool reconstruct_root_path(
    const NodeOrdinal source, const std::uint8_t source_path_class,
    const ReverseConeResult &reverse, const TraversalGraph &graph,
    FrontierPathExemplar &exemplar) {
    NodeOrdinal cursor = source;
    std::uint8_t path_class = source_path_class;
    std::uint64_t guard = 0;
    while ((reverse.root_states[cursor] & path_class) == 0U) {
        if (cursor >= reverse.successors.size() || path_class == 0U) {
            return false;
        }
        const auto &successor =
            reverse.successors[cursor][path_class_index(path_class)];
        if (!successor || successor->edge >= graph.edges.size()) {
            return false;
        }
        const TraversalEdge &edge = graph.edges[successor->edge];
        if (edge.source != cursor || edge.target != successor->target) {
            return false;
        }
        FrontierPathStep step;
        step.kind = edge.model_fact == nullptr
            ? FrontierPathStepKind::GraphEdge
            : FrontierPathStepKind::ModelArc;
        step.source_node_id = graph.nodes[edge.source]->node_id;
        step.target_node_id = graph.nodes[edge.target]->node_id;
        if (edge.graph_edge != nullptr) {
            step.graph_edge_id = edge.graph_edge->edge_id;
        }
        if (edge.model_fact != nullptr) {
            step.model_fact_id = edge.model_fact->fact_id;
        }
        exemplar.root_steps.push_back(std::move(step));
        if (edge.compatibility.verdict == WitnessCompatibility::Unknown ||
            edge.certainty == Certainty::Unknown) {
            for (const std::string &reason : edge.compatibility.reasons) {
                append_unique(exemplar.uncertainty_reasons, reason);
            }
            if (edge.graph_edge != nullptr) {
                for (const std::string &reason :
                     edge.graph_edge->uncertainty_reasons) {
                    append_unique(exemplar.uncertainty_reasons, reason);
                }
            }
        }
        cursor = successor->target;
        path_class = successor->target_path_class;
        ++guard;
        if (guard > graph.nodes.size()) {
            return false;
        }
    }
    exemplar.root_node_id = graph.nodes[cursor]->node_id;
    return true;
}

FrontierWitness build_witness(
    const BoundaryAttachment &attachment,
    const std::string &boundary_node_id,
    const std::string &cone_id,
    const ForwardResult &forward,
    const ReverseConeResult &reverse,
    const TraversalGraph &graph,
    const bool cone_complete, FrontierLedgerCaches &ledger_caches) {
    FrontierWitness result;
    result.attachment_id = attachment.attachment_id;
    result.boundary_node_id = boundary_node_id;
    result.forward_summary = forward.summary;
    std::array<bool, 3> exemplar_selected{false, false, false};
    bool exemplar_invariant_complete = true;
    constexpr std::size_t kCompactMeetBytes = 7U;
    std::string meet_signature;
    meet_signature.reserve(reverse.active_nodes.size() * kCompactMeetBytes);
    for (const NodeOrdinal ordinal : reverse.active_nodes) {
        if (ordinal >= forward.states.size() ||
            ordinal >= reverse.states.size()) {
            continue;
        }
        const std::uint8_t raw_forward_mask = forward.states[ordinal];
        const std::uint8_t raw_root_mask = reverse.states[ordinal];
        const std::uint8_t meet_mask =
            product_path_mask(raw_forward_mask, raw_root_mask);
        if (meet_mask == 0U) {
            continue;
        }
        ++result.meet_summary.meet_count;
        if ((meet_mask & kStaticPath) != 0U) {
            ++result.meet_summary.static_path_meet_count;
        }
        if ((meet_mask & kModelledPath) != 0U) {
            ++result.meet_summary.modelled_path_meet_count;
        }
        if ((meet_mask & kUnknownPath) != 0U) {
            ++result.meet_summary.unknown_path_meet_count;
        }
        ++result.meet_summary.effective_mask_histogram[meet_mask];
        append_u32_le(meet_signature, ordinal);
        meet_signature.push_back(static_cast<char>(raw_forward_mask));
        meet_signature.push_back(static_cast<char>(raw_root_mask));
        meet_signature.push_back(static_cast<char>(meet_mask));
        for (const std::uint8_t effective_class :
             {kStaticPath, kModelledPath, kUnknownPath}) {
            const std::size_t index = path_class_index(effective_class);
            if (exemplar_selected[index] ||
                (meet_mask & effective_class) == 0U) {
                continue;
            }
            const std::optional<ProductPathClasses> path_classes =
                choose_product_path_classes(
                    raw_forward_mask, raw_root_mask, effective_class);
            if (!path_classes) {
                exemplar_invariant_complete = false;
                continue;
            }
            FrontierPathExemplar exemplar;
            exemplar.meet_node_id = graph.nodes[ordinal]->node_id;
            const auto as_path_class = [](const std::uint8_t value) {
                return value == kStaticPath
                    ? FrontierPathClass::Static
                    : value == kModelledPath
                        ? FrontierPathClass::Modelled
                        : FrontierPathClass::Unknown;
            };
            exemplar.effective_path_class =
                as_path_class(effective_class);
            exemplar.raw_forward_path_class =
                as_path_class(path_classes->forward);
            exemplar.raw_root_path_class =
                as_path_class(path_classes->root);
            exemplar.compatibility =
                effective_class == kUnknownPath
                ? WitnessCompatibility::Unknown
                : WitnessCompatibility::Compatible;
            exemplar.reachability =
                effective_class == kStaticPath
                ? ReachabilityVerdict::StaticWitness
                : effective_class == kModelledPath
                    ? ReachabilityVerdict::ModelledWitness
                    : ReachabilityVerdict::Unknown;
            if (!reconstruct_forward_path(
                    static_cast<NodeOrdinal>(ordinal),
                    path_classes->forward, forward, graph, exemplar) ||
                !reconstruct_root_path(
                    static_cast<NodeOrdinal>(ordinal), path_classes->root,
                    reverse, graph, exemplar)) {
                exemplar_invariant_complete = false;
                append_unique(
                    result.uncertainty_reasons,
                    "canonical product-path predecessor is incomplete");
                continue;
            }
            if (effective_class == kUnknownPath) {
                append_unique(
                    exemplar.uncertainty_reasons,
                    "alternate or only witness retains UNKNOWN provenance");
            }
            sort_unique(exemplar.uncertainty_reasons);
            result.path_exemplars.push_back(std::move(exemplar));
            exemplar_selected[index] = true;
        }
    }
    LedgerHasher meet_hasher;
    meet_hasher.append_field("rift-meet-ledger/lp-u64le/1.0.0");
    meet_hasher.append_field(attachment.attachment_id);
    meet_hasher.append_field(boundary_node_id);
    meet_hasher.append_field(cone_id);
    meet_hasher.append_u64(result.meet_summary.meet_count);
    for (std::size_t offset = 0; offset < meet_signature.size();
         offset += kCompactMeetBytes) {
        const NodeOrdinal ordinal = read_u32_le(meet_signature, offset);
        meet_hasher.append_field(graph.nodes[ordinal]->node_id);
        meet_hasher.append_u64(static_cast<std::uint8_t>(
            meet_signature[offset + 4U]));
        meet_hasher.append_u64(static_cast<std::uint8_t>(
            meet_signature[offset + 5U]));
        meet_hasher.append_u64(static_cast<std::uint8_t>(
            meet_signature[offset + 6U]));
    }
    result.meet_summary.enumeration_complete =
        forward.enumeration_complete && reverse.enumeration_complete &&
        graph.materialization_complete && cone_complete &&
        exemplar_invariant_complete;
    result.meet_summary.ledger_sha256 = meet_hasher.final_hex();

    constexpr std::size_t kCompactSupportBytes = 5U;
    std::string support_signature;
    support_signature.reserve(
        reverse.active_target_edges.size() * kCompactSupportBytes);
    for (const EdgeOrdinal edge_ordinal : reverse.active_target_edges) {
        const TraversalEdge &edge = graph.edges[edge_ordinal];
        if (edge.source >= forward.states.size() ||
            edge.target >= reverse.states.size() || edge.edge_id == nullptr) {
            continue;
        }
        std::uint8_t supported_mask = 0U;
        for (const std::uint8_t forward_class :
             {kStaticPath, kModelledPath, kUnknownPath}) {
            if ((forward.states[edge.source] & forward_class) == 0U) {
                continue;
            }
            const std::uint8_t after_edge = compose_one(forward_class, edge);
            if (after_edge == 0U) {
                continue;
            }
            for (const std::uint8_t root_class :
                 {kStaticPath, kModelledPath, kUnknownPath}) {
                if ((reverse.states[edge.target] & root_class) != 0U) {
                    supported_mask |= compose_path_classes(
                        after_edge, root_class);
                }
            }
        }
        if (supported_mask == 0U) {
            continue;
        }
        append_u32_le(support_signature, edge_ordinal);
        support_signature.push_back(static_cast<char>(supported_mask));
    }
    auto cached_support = ledger_caches.supports.find(support_signature);
    if (cached_support == ledger_caches.supports.end()) {
        CachedSupportLedger ledger;
        ledger.transition_count =
            support_signature.size() / kCompactSupportBytes;
        LedgerHasher support_hasher;
        support_hasher.append_field(
            "rift-product-support/lp-u64le/1.0.0");
        support_hasher.append_u64(ledger.transition_count);
        for (std::size_t offset = 0; offset < support_signature.size();
             offset += kCompactSupportBytes) {
            const EdgeOrdinal edge_ordinal =
                read_u32_le(support_signature, offset);
            const std::uint8_t supported_mask = static_cast<std::uint8_t>(
                support_signature[offset + 4U]);
            const TraversalEdge &edge = graph.edges[edge_ordinal];
            support_hasher.append_field(
                edge.model_fact == nullptr ? "GRAPH_EDGE" : "MODEL_ARC");
            support_hasher.append_field(*edge.edge_id);
            support_hasher.append_field(graph.nodes[edge.source]->node_id);
            support_hasher.append_field(graph.nodes[edge.target]->node_id);
            support_hasher.append_u64(supported_mask);
            support_hasher.append_u64(
                static_cast<std::uint64_t>(edge.kind));
            support_hasher.append_u64(
                static_cast<std::uint64_t>(edge.certainty));
            support_hasher.append_u64(
                static_cast<std::uint64_t>(edge.compatibility.verdict));
            support_hasher.append_field(
                edge.model_fact == nullptr ? "" : edge.model_fact->fact_id);
            support_hasher.append_u64(edge.ledger_reasons.size());
            for (const std::string &reason : edge.ledger_reasons) {
                support_hasher.append_field(reason);
            }
            if (edge.model_fact != nullptr) {
                ledger.model_fact_ids.push_back(edge.model_fact->fact_id);
            }
        }
        sort_unique(ledger.model_fact_ids);
        ledger.transition_digest = support_hasher.final_hex();
        LedgerHasher fact_hasher;
        fact_hasher.append_field(
            "rift-product-model-facts/lp-u64le/1.0.0");
        fact_hasher.append_u64(ledger.model_fact_ids.size());
        for (const std::string &fact_id : ledger.model_fact_ids) {
            fact_hasher.append_field(fact_id);
        }
        ledger.model_fact_digest = fact_hasher.final_hex();
        cached_support = ledger_caches.supports
                             .emplace(
                                 std::move(support_signature),
                                 std::move(ledger))
                             .first;
    }
    result.support_summary.supporting_transition_count =
        cached_support->second.transition_count;
    result.support_summary.supporting_transition_ledger_sha256 =
        cached_support->second.transition_digest;
    result.model_fact_ids = cached_support->second.model_fact_ids;
    result.support_summary.supporting_model_fact_count =
        result.model_fact_ids.size();
    result.support_summary.supporting_model_fact_ledger_sha256 =
        cached_support->second.model_fact_digest;
    result.support_summary.enumeration_complete =
        result.meet_summary.enumeration_complete;
    result.compatibility =
        result.meet_summary.static_path_meet_count != 0U ||
                result.meet_summary.modelled_path_meet_count != 0U
            ? WitnessCompatibility::Compatible
            : WitnessCompatibility::Unknown;
    result.reachability = result.meet_summary.static_path_meet_count != 0U
        ? ReachabilityVerdict::StaticWitness
        : result.meet_summary.modelled_path_meet_count != 0U
            ? ReachabilityVerdict::ModelledWitness
            : ReachabilityVerdict::Unknown;
    for (const std::uint8_t path_class :
         {kStaticPath, kModelledPath, kUnknownPath}) {
        const std::uint64_t count = path_class == kStaticPath
            ? result.meet_summary.static_path_meet_count
            : path_class == kModelledPath
                ? result.meet_summary.modelled_path_meet_count
                : result.meet_summary.unknown_path_meet_count;
        if (count != 0U && !exemplar_selected[path_class_index(path_class)]) {
            exemplar_invariant_complete = false;
        }
    }
    if (!exemplar_invariant_complete) {
        result.compatibility = WitnessCompatibility::Unknown;
        result.reachability = ReachabilityVerdict::Unknown;
        result.meet_summary.enumeration_complete = false;
        result.support_summary.enumeration_complete = false;
    }
    if (result.meet_summary.unknown_path_meet_count != 0U) {
        append_unique(
            result.uncertainty_reasons,
            "alternate or only witness retains UNKNOWN provenance");
    }
    if (!result.meet_summary.enumeration_complete) {
        append_unique(
            result.uncertainty_reasons,
            "meet ledger is conservative-incomplete");
    }
    sort_unique(result.model_fact_ids);
    sort_unique(result.uncertainty_reasons);
    std::sort(
        result.path_exemplars.begin(), result.path_exemplars.end(),
        [](const FrontierPathExemplar &left,
           const FrontierPathExemplar &right) {
            return std::tie(left.reachability, left.meet_node_id) <
                   std::tie(right.reachability, right.meet_node_id);
        });
    std::ostringstream material;
    material << attachment.attachment_id << '\0' << boundary_node_id << '\0'
             << cone_id << '\0' << result.meet_summary.ledger_sha256 << '\0'
             << result.meet_summary.meet_count;
    result.witness_id = stable_id("frontier-witness", material.str());
    return result;
}

ControllabilityVerdict evaluate_controllability(
    const ExternalAction &action,
    const std::optional<ExecutorCapabilityManifest> &manifest) {
    if (!manifest || manifest->status == StageStatus::Failed) {
        return ControllabilityVerdict::Unknown;
    }
    std::set<ControllabilityVerdict> matches;
    for (const ExecutorCapabilityEntry &entry : manifest->capabilities) {
        if (entry.required_capability != action.required_capability) {
            continue;
        }
        if (entry.action_schema_id &&
            *entry.action_schema_id != action.action_schema_id) {
            continue;
        }
        matches.insert(entry.controllability);
    }
    if (matches.empty()) {
        return manifest->status == StageStatus::Complete
            ? ControllabilityVerdict::Unavailable
            : ControllabilityVerdict::Unknown;
    }
    if (matches.size() != 1U) {
        return ControllabilityVerdict::Unknown;
    }
    return *matches.begin();
}

bool controllable(const ControllabilityVerdict verdict) {
    return verdict == ControllabilityVerdict::Direct ||
           verdict == ControllabilityVerdict::Sequence ||
           verdict == ControllabilityVerdict::Timing ||
           verdict == ControllabilityVerdict::Environment;
}

bool closed(const FrontierCompletenessLedger &ledger) {
    return ledger.model_vm_complete &&
           ledger.attachment_enumeration_complete &&
           ledger.forward_enumeration_complete && ledger.cone_complete &&
           ledger.compatibility_complete;
}

std::string json_escape(const std::string_view value) {
    std::ostringstream output;
    output << '"';
    static constexpr char hex[] = "0123456789abcdef";
    for (const unsigned char character : value) {
        switch (character) {
        case '"':
            output << "\\\"";
            break;
        case '\\':
            output << "\\\\";
            break;
        case '\b':
            output << "\\b";
            break;
        case '\f':
            output << "\\f";
            break;
        case '\n':
            output << "\\n";
            break;
        case '\r':
            output << "\\r";
            break;
        case '\t':
            output << "\\t";
            break;
        default:
            if (character < 0x20U) {
                output << "\\u00" << hex[character >> 4U]
                       << hex[character & 0x0fU];
            } else {
                output << static_cast<char>(character);
            }
        }
    }
    output << '"';
    return output.str();
}

template <typename T, typename Emit>
void emit_array(
    std::ostringstream &output, const std::vector<T> &values, Emit emit) {
    output << '[';
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0U) {
            output << ',';
        }
        emit(output, values[index]);
    }
    output << ']';
}

void emit_strings(
    std::ostringstream &output, const std::vector<std::string> &values) {
    emit_array(
        output, values,
        [](std::ostringstream &stream, const std::string &value) {
            stream << json_escape(value);
        });
}

void emit_optional_string(
    std::ostringstream &output, const std::optional<std::string> &value) {
    if (value) {
        output << json_escape(*value);
    } else {
        output << "null";
    }
}

const char *value_kind_name(const ValueKind kind) {
    switch (kind) {
    case ValueKind::Boolean:
        return "bool";
    case ValueKind::Integer:
        return "integer";
    case ValueKind::Floating:
        return "floating";
    case ValueKind::Enumeration:
        return "enum";
    case ValueKind::BitVector:
        return "bitvector";
    case ValueKind::Timestamp:
        return "timestamp";
    case ValueKind::Duration:
        return "duration";
    case ValueKind::Pointer:
        return "pointer";
    case ValueKind::Record:
        return "record";
    case ValueKind::Array:
        return "array";
    case ValueKind::Unknown:
        return "unknown";
    }
    return "unknown";
}

void emit_value_type(std::ostringstream &output, const ValueType &type) {
    output << "{\"kind\":" << json_escape(value_kind_name(type.kind))
           << ",\"canonical\":" << json_escape(type.canonical);
    if (type.bit_width) {
        output << ",\"bit_width\":" << *type.bit_width;
    }
    if (type.is_signed) {
        output << ",\"signed\":"
               << (*type.is_signed ? "true" : "false");
    }
    if (type.unit) {
        output << ",\"unit\":" << json_escape(*type.unit);
    }
    output << '}';
}

const char *model_layer_name(const ModelLayer layer) {
    switch (layer) {
    case ModelLayer::Platform:
        return "platform";
    case ModelLayer::Framework:
        return "framework";
    case ModelLayer::ProjectAdapter:
        return "project_adapter";
    }
    return "framework";
}

void emit_provenance(
    std::ostringstream &output, const ModelProvenance &provenance) {
    output << "{\"model_pack_id\":"
           << json_escape(provenance.model_pack_id)
           << ",\"model_pack_version\":"
           << json_escape(provenance.model_pack_version)
           << ",\"model_pack_sha256\":"
           << json_escape(provenance.model_pack_sha256)
           << ",\"layer\":" << json_escape(model_layer_name(provenance.layer))
           << ",\"rule_id\":" << json_escape(provenance.rule_id)
           << ",\"emit_id\":" << json_escape(provenance.emit_id)
           << ",\"selector_ids\":";
    emit_strings(output, provenance.selector_ids);
    output << ",\"capture_ids\":";
    emit_strings(output, provenance.capture_ids);
    output << ",\"matched_semantic_node_ids\":";
    emit_strings(output, provenance.matched_semantic_node_ids);
    output << '}';
}

void emit_action(std::ostringstream &output, const ExternalAction &action) {
    output << "{\"external_action_id\":"
           << json_escape(action.external_action_id)
           << ",\"action_schema_id\":"
           << json_escape(action.action_schema_id)
           << ",\"action_class\":" << json_escape(action.action_class)
           << ",\"channel\":" << json_escape(action.channel)
           << ",\"operation\":" << json_escape(action.operation)
           << ",\"payload_type\":";
    emit_value_type(output, action.payload_type);
    output << ",\"payload_slot\":" << json_escape(action.payload_slot)
           << ",\"scope_schema\":" << json_escape(action.scope_schema)
           << ",\"generation_schema\":"
           << json_escape(action.generation_schema)
           << ",\"timing_capability\":"
           << json_escape(action.timing_capability)
           << ",\"required_capability\":"
           << json_escape(action.required_capability)
           << ",\"provenance\":";
    emit_array(
        output, action.provenance,
        [](std::ostringstream &stream, const ModelProvenance &item) {
            emit_provenance(stream, item);
        });
    output << '}';
}

void emit_ledger(
    std::ostringstream &output, const FrontierCompletenessLedger &ledger) {
    output << "{\"model_vm_complete\":"
           << (ledger.model_vm_complete ? "true" : "false")
           << ",\"attachment_enumeration_complete\":"
           << (ledger.attachment_enumeration_complete ? "true" : "false")
           << ",\"forward_enumeration_complete\":"
           << (ledger.forward_enumeration_complete ? "true" : "false")
           << ",\"cone_complete\":"
           << (ledger.cone_complete ? "true" : "false")
           << ",\"compatibility_complete\":"
           << (ledger.compatibility_complete ? "true" : "false")
           << ",\"gap_reasons\":";
    emit_strings(output, ledger.gap_reasons);
    output << '}';
}

void emit_axes(std::ostringstream &output, const FrontierEvidenceAxes &axes) {
    output << "{\"reachability\":"
           << json_escape(to_string(axes.reachability))
           << ",\"controllability\":"
           << json_escape(to_string(axes.controllability))
           << ",\"path_feasibility\":"
           << json_escape(to_string(axes.path_feasibility))
           << ",\"mutation_semantics\":"
           << json_escape(to_string(axes.mutation_semantics))
           << ",\"runtime_evidence\":"
           << json_escape(to_string(axes.runtime_evidence))
           << ",\"model_provenance\":{\"model_pack_sha256s\":";
    emit_strings(output, axes.model_provenance.model_pack_sha256s);
    output << ",\"attachment_ids\":";
    emit_strings(output, axes.model_provenance.attachment_ids);
    output << ",\"model_fact_ids\":";
    emit_strings(output, axes.model_provenance.model_fact_ids);
    output << "},\"completeness\":";
    emit_ledger(output, axes.completeness);
    output << '}';
}

void emit_witness(
    std::ostringstream &output, const FrontierWitness &witness) {
    output << "{\"witness_id\":" << json_escape(witness.witness_id)
           << ",\"attachment_id\":" << json_escape(witness.attachment_id)
           << ",\"boundary_node_id\":"
           << json_escape(witness.boundary_node_id)
           << ",\"forward_summary\":{\"reached_node_count\":"
           << witness.forward_summary.reached_node_count
           << ",\"reachable_transition_count\":"
           << witness.forward_summary.reachable_transition_count
           << ",\"enumeration_complete\":"
           << (witness.forward_summary.enumeration_complete
                   ? "true"
                   : "false")
           << ",\"reached_state_ledger_sha256\":"
           << json_escape(
                  witness.forward_summary.reached_state_ledger_sha256)
           << ",\"reachable_transition_ledger_sha256\":"
           << json_escape(
                  witness.forward_summary
                      .reachable_transition_ledger_sha256)
           << "},\"meet_summary\":{\"meet_count\":"
           << witness.meet_summary.meet_count
           << ",\"static_path_meet_count\":"
           << witness.meet_summary.static_path_meet_count
           << ",\"modelled_path_meet_count\":"
           << witness.meet_summary.modelled_path_meet_count
           << ",\"unknown_path_meet_count\":"
           << witness.meet_summary.unknown_path_meet_count
           << ",\"effective_mask_histogram\":[";
    for (std::size_t mask = 1U; mask <= 7U; ++mask) {
        if (mask != 1U) {
            output << ',';
        }
        output << witness.meet_summary.effective_mask_histogram[mask];
    }
    output
           << "],\"enumeration_complete\":"
           << (witness.meet_summary.enumeration_complete ? "true" : "false")
           << ",\"ledger_sha256\":"
           << json_escape(witness.meet_summary.ledger_sha256)
           << "},\"support_summary\":{\"supporting_transition_count\":"
           << witness.support_summary.supporting_transition_count
           << ",\"supporting_model_fact_count\":"
           << witness.support_summary.supporting_model_fact_count
           << ",\"enumeration_complete\":"
           << (witness.support_summary.enumeration_complete
                   ? "true"
                   : "false")
           << ",\"supporting_transition_ledger_sha256\":"
           << json_escape(
                  witness.support_summary
                      .supporting_transition_ledger_sha256)
           << ",\"supporting_model_fact_ledger_sha256\":"
           << json_escape(
                  witness.support_summary
                      .supporting_model_fact_ledger_sha256)
           << "},\"path_exemplars\":";
    emit_array(
        output, witness.path_exemplars,
        [](std::ostringstream &stream,
           const FrontierPathExemplar &exemplar) {
            const auto emit_steps = [](
                                        std::ostringstream &target,
                                        const std::vector<FrontierPathStep>
                                            &steps) {
                emit_array(
                    target, steps,
                    [](std::ostringstream &step_stream,
                       const FrontierPathStep &step) {
                        step_stream << "{\"kind\":"
                                    << json_escape(to_string(step.kind))
                                    << ",\"source_node_id\":"
                                    << json_escape(step.source_node_id)
                                    << ",\"target_node_id\":"
                                    << json_escape(step.target_node_id)
                                    << ",\"graph_edge_id\":";
                        emit_optional_string(
                            step_stream, step.graph_edge_id);
                        step_stream << ",\"model_fact_id\":";
                        emit_optional_string(
                            step_stream, step.model_fact_id);
                        step_stream << '}';
                    });
            };
            stream << "{\"effective_path_class\":"
                   << json_escape(to_string(exemplar.effective_path_class))
                   << ",\"raw_forward_path_class\":"
                   << json_escape(
                          to_string(exemplar.raw_forward_path_class))
                   << ",\"raw_root_path_class\":"
                   << json_escape(to_string(exemplar.raw_root_path_class))
                   << ",\"meet_node_id\":"
                   << json_escape(exemplar.meet_node_id)
                   << ",\"root_node_id\":"
                   << json_escape(exemplar.root_node_id)
                   << ",\"compatibility\":"
                   << json_escape(to_string(exemplar.compatibility))
                   << ",\"reachability\":"
                   << json_escape(to_string(exemplar.reachability))
                   << ",\"forward_steps\":";
            emit_steps(stream, exemplar.forward_steps);
            stream << ",\"root_steps\":";
            emit_steps(stream, exemplar.root_steps);
            stream << ",\"representative_only\":true"
                   << ",\"uncertainty_reasons\":";
            emit_strings(stream, exemplar.uncertainty_reasons);
            stream << '}';
        });
    output
           << ",\"compatibility\":"
           << json_escape(to_string(witness.compatibility))
           << ",\"reachability\":"
           << json_escape(to_string(witness.reachability))
           << ",\"model_fact_ids\":";
    emit_strings(output, witness.model_fact_ids);
    output << ",\"uncertainty_reasons\":";
    emit_strings(output, witness.uncertainty_reasons);
    output << '}';
}

void emit_attachment_account(
    std::ostringstream &output, const FrontierAttachmentAccount &account) {
    output << "{\"attachment_id\":" << json_escape(account.attachment_id)
           << ",\"semantic_node_id\":"
           << json_escape(account.semantic_node_id)
           << ",\"disposition\":"
           << json_escape(to_string(account.disposition))
           << ",\"contextual_node_ids\":";
    emit_strings(output, account.contextual_node_ids);
    output << ",\"witness_ids\":";
    emit_strings(output, account.witness_ids);
    output << ",\"uncertainty_reasons\":";
    emit_strings(output, account.uncertainty_reasons);
    output << '}';
}

void emit_candidate(
    std::ostringstream &output, const FrontierCandidate &candidate) {
    output << "{\"candidate_id\":" << json_escape(candidate.candidate_id)
           << ",\"action\":";
    emit_action(output, candidate.action);
    output << ",\"cone_id\":" << json_escape(candidate.cone_id)
           << ",\"ap_id\":" << json_escape(candidate.ap_id)
           << ",\"disposition\":"
           << json_escape(to_string(candidate.disposition))
           << ",\"evidence\":";
    emit_axes(output, candidate.evidence);
    output << ",\"attachment_accounting\":";
    emit_array(
        output, candidate.attachment_accounting,
        [](std::ostringstream &stream,
           const FrontierAttachmentAccount &account) {
            emit_attachment_account(stream, account);
        });
    output << ",\"witnesses\":";
    emit_array(
        output, candidate.witnesses,
        [](std::ostringstream &stream, const FrontierWitness &witness) {
            emit_witness(stream, witness);
        });
    output << ",\"rank_tier\":" << candidate.rank_tier
           << ",\"rank_reasons\":";
    emit_strings(output, candidate.rank_reasons);
    output << ",\"uncertainty_reasons\":";
    emit_strings(output, candidate.uncertainty_reasons);
    output << '}';
}

const char *gap_effect_name(const GapEffect effect) {
    switch (effect) {
    case GapEffect::PrecisionLoss:
        return "precision_loss";
    case GapEffect::SoundnessRisk:
        return "soundness_risk";
    case GapEffect::StageFailure:
        return "stage_failure";
    }
    return "soundness_risk";
}

void emit_location(
    std::ostringstream &output, const SourceLocation &location) {
    output << "{\"file\":" << json_escape(location.file)
           << ",\"line\":" << location.line
           << ",\"column\":" << location.column;
    if (location.end_line != 0U) {
        output << ",\"end_line\":" << location.end_line;
    }
    if (location.end_column != 0U) {
        output << ",\"end_column\":" << location.end_column;
    }
    output << ",\"location_kind\":"
           << json_escape(location.location_kind)
           << ",\"macro_stack\":";
    emit_strings(output, location.macro_stack);
    output << '}';
}

void emit_gap(std::ostringstream &output, const CoverageGap &gap) {
    output << "{\"construct_id\":" << json_escape(gap.gap_id)
           << ",\"kind\":" << json_escape(gap.kind)
           << ",\"effect\":" << json_escape(gap_effect_name(gap.effect))
           << ",\"detail\":" << json_escape(gap.detail)
           << ",\"locations\":";
    emit_array(
        output, gap.locations,
        [](std::ostringstream &stream, const SourceLocation &location) {
            emit_location(stream, location);
        });
    output << ",\"affected_ids\":";
    emit_strings(output, gap.affected_ids);
    output << '}';
}

std::vector<std::string> structural_input_errors(
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierInputDigests &digests,
    const std::optional<ExecutorCapabilityManifest> &executor_manifest,
    const FrontierOptions &options) {
    std::vector<std::string> errors;
    if (!valid_sha256(digests.model_fact_overlay_sha256) ||
        !valid_sha256(digests.graph_sha256) ||
        !valid_sha256(digests.cones_sha256) ||
        (digests.executor_manifest_sha256 &&
         !valid_sha256(*digests.executor_manifest_sha256))) {
        errors.push_back("frontier input digest is not SHA-256");
    }
    if (options.max_materialized_model_edges == 0U ||
        options.max_forward_states_per_attachment == 0U) {
        errors.push_back("frontier resource limit is zero");
    }
    if (executor_manifest.has_value() !=
        digests.executor_manifest_sha256.has_value()) {
        errors.push_back(
            "executor manifest and executor digest presence differ");
    }
    if (executor_manifest) {
        std::set<std::string> capability_ids;
        for (const ExecutorCapabilityEntry &entry :
             executor_manifest->capabilities) {
            if (!capability_ids.insert(entry.capability_id).second) {
                errors.push_back(
                    "duplicate executor capability ID: " +
                    entry.capability_id);
            }
        }
    }
    std::set<std::string> node_ids;
    for (const ContextualNode &node : graph.nodes) {
        if (!node_ids.insert(node.node_id).second) {
            errors.push_back("duplicate contextual node ID: " + node.node_id);
        }
    }
    std::set<std::string> edge_ids;
    for (const InfluenceEdge &edge : graph.edges) {
        if (!edge_ids.insert(edge.edge_id).second) {
            errors.push_back("duplicate contextual edge ID: " + edge.edge_id);
        }
        if (!node_ids.contains(edge.source_node_id) ||
            !node_ids.contains(edge.target_node_id)) {
            errors.push_back("contextual edge has a dangling endpoint");
        }
    }
    std::set<std::string> action_ids;
    for (const ExternalAction &action : overlay.external_actions) {
        if (!action_ids.insert(action.external_action_id).second) {
            errors.push_back(
                "duplicate external action ID: " + action.external_action_id);
        }
    }
    std::set<std::string> attachment_ids;
    for (const BoundaryAttachment &attachment : overlay.boundary_attachments) {
        if (!attachment_ids.insert(attachment.attachment_id).second) {
            errors.push_back(
                "duplicate boundary attachment ID: " +
                attachment.attachment_id);
        }
        if (!action_ids.contains(attachment.external_action_id)) {
            errors.push_back(
                "boundary attachment references unknown external action");
        }
        if (attachment.certainty != Certainty::Modelled &&
            attachment.certainty != Certainty::Unknown) {
            errors.push_back(
                "boundary attachment certainty exceeds model-pack contract");
        }
    }
    for (const ModelFact &fact : overlay.semantic_facts) {
        if (fact.certainty != Certainty::Modelled &&
            fact.certainty != Certainty::Unknown) {
            errors.push_back(
                "model fact certainty exceeds model-pack contract");
        }
    }
    std::set<std::string> cone_ids;
    for (const ApInfluenceCone &cone : cones.cones) {
        if (!cone_ids.insert(cone.cone_id).second) {
            errors.push_back("duplicate cone ID: " + cone.cone_id);
        }
    }
    sort_unique(errors);
    return errors;
}

}  // namespace

ContextCompatibilityResult evaluate_contextual_compatibility(
    const ContextualNode &source, const ContextualNode &target,
    const RelationKind relation_kind) {
    return contextual_compatibility_impl(source, target, relation_kind);
}

FrontierCandidates compute_frontier_candidates(
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierInputDigests &input_digests,
    const std::optional<ExecutorCapabilityManifest> &executor_manifest,
    const FrontierOptions &options) {
    FrontierCandidates result;
    result.input_digests = input_digests;
    result.traversal_contract.max_materialized_model_edges =
        options.max_materialized_model_edges;
    result.traversal_contract.max_forward_states_per_attachment =
        options.max_forward_states_per_attachment;
    result.traversal_contract_sha256 = sha256_hex(
        traversal_contract_material(result.traversal_contract));
    const std::string executor_digest =
        input_digests.executor_manifest_sha256.value_or("none");
    result.artifact_id = stable_id(
        "frontier-candidates",
        input_digests.model_fact_overlay_sha256 + '\0' +
            input_digests.graph_sha256 + '\0' + input_digests.cones_sha256 +
            '\0' + executor_digest + '\0' +
            result.traversal_contract_sha256);
    const std::vector<std::string> input_errors = structural_input_errors(
        overlay, graph, cones, input_digests, executor_manifest, options);
    if (!input_errors.empty()) {
        result.status = StageStatus::Failed;
        result.diagnostics = input_errors;
        return result;
    }

    result.status = combine_status(
        overlay.status, combine_status(graph.status, cones.status));
    if (executor_manifest) {
        result.status = combine_status(result.status, executor_manifest->status);
    }
    std::unordered_map<std::string, std::size_t> coverage_gap_indices;
    const auto append_coverage_gaps =
        [&](const std::vector<CoverageGap> &gaps) {
            for (const CoverageGap &gap : gaps) {
                const auto found = coverage_gap_indices.find(gap.gap_id);
                if (found == coverage_gap_indices.end()) {
                    coverage_gap_indices.emplace(
                        gap.gap_id, result.coverage_gaps.size());
                    result.coverage_gaps.push_back(gap);
                    continue;
                }
                if (!(result.coverage_gaps[found->second] == gap)) {
                    result.status = StageStatus::Failed;
                    append_unique(
                        result.diagnostics,
                        "conflicting coverage-gap payload for stable ID " +
                            gap.gap_id);
                }
            }
        };
    append_coverage_gaps(overlay.coverage_gaps);
    append_coverage_gaps(graph.coverage_gaps);
    append_coverage_gaps(cones.coverage_gaps);
    if (executor_manifest) {
        append_coverage_gaps(executor_manifest->coverage_gaps);
    }

    std::map<std::string, std::vector<const ContextualNode *>> by_semantic;
    for (const ContextualNode &node : graph.nodes) {
        by_semantic[node.semantic_node_id].push_back(&node);
    }
    for (auto &[semantic, nodes] : by_semantic) {
        (void)semantic;
        std::sort(
            nodes.begin(), nodes.end(),
            [](const ContextualNode *left, const ContextualNode *right) {
                return left->node_id < right->node_id;
            });
    }
    std::map<std::string, std::vector<const BoundaryAttachment *>> by_action;
    for (const BoundaryAttachment &attachment : overlay.boundary_attachments) {
        by_action[attachment.external_action_id].push_back(&attachment);
    }
    for (auto &[action, attachments] : by_action) {
        (void)action;
        std::sort(
            attachments.begin(), attachments.end(),
            [](const BoundaryAttachment *left,
               const BoundaryAttachment *right) {
                return left->attachment_id < right->attachment_id;
            });
    }

    const TraversalGraph traversal =
        build_traversal_graph(overlay, graph, options);
    std::vector<const ExternalAction *> actions;
    for (const ExternalAction &action : overlay.external_actions) {
        actions.push_back(&action);
    }
    std::sort(
        actions.begin(), actions.end(),
        [](const ExternalAction *left, const ExternalAction *right) {
            return std::tie(
                       left->external_action_id, left->channel,
                       left->operation, left->payload_slot,
                       left->scope_schema, left->generation_schema) <
                   std::tie(
                       right->external_action_id, right->channel,
                       right->operation, right->payload_slot,
                       right->scope_schema, right->generation_schema);
        });
    std::vector<const ApInfluenceCone *> ordered_cones;
    for (const ApInfluenceCone &cone : cones.cones) {
        ordered_cones.push_back(&cone);
    }
    std::sort(
        ordered_cones.begin(), ordered_cones.end(),
        [](const ApInfluenceCone *left, const ApInfluenceCone *right) {
            return left->cone_id < right->cone_id;
        });
    std::map<std::string, ReverseConeResult> reverse_cones;
    for (const ApInfluenceCone *cone : ordered_cones) {
        reverse_cones.emplace(
            cone->cone_id,
            reverse_cone_reach(*cone, traversal, options));
    }
    FrontierLedgerCaches ledger_caches;
    ledger_caches.states.reserve(64U);
    ledger_caches.transitions.reserve(64U);
    ledger_caches.supports.reserve(64U);

    const bool vm_complete = model_vm_complete(overlay);
    for (const ExternalAction *action : actions) {
        const auto attachment_group = by_action.find(action->external_action_id);
        const std::vector<const BoundaryAttachment *> empty_attachments;
        const auto &attachments = attachment_group == by_action.end()
            ? empty_attachments
            : attachment_group->second;
        // The forward fixed point depends on the exact boundary context and
        // attachment certainty, not on an AP cone.  Reuse it across every
        // property cone for this action instead of recomputing the same
        // whole-program closure for each action×cone pair.
        std::map<std::pair<std::string, Certainty>, ForwardResult>
            forward_cache;
        for (const ApInfluenceCone *cone : ordered_cones) {
            const ReverseConeResult &reverse =
                reverse_cones.at(cone->cone_id);
            FrontierCandidate candidate;
            candidate.action = *action;
            normalize_action(candidate.action);
            candidate.cone_id = cone->cone_id;
            candidate.ap_id = cone->ap_id;
            candidate.candidate_id = stable_id(
                "frontier-candidate",
                action->external_action_id + '\0' +
                    action_identity_material(*action) + '\0' + cone->cone_id);
            candidate.evidence.controllability =
                evaluate_controllability(*action, executor_manifest);
            candidate.evidence.model_provenance.model_pack_sha256s =
                overlay.model_pack_sha256s;
            sort_unique(
                candidate.evidence.model_provenance.model_pack_sha256s);
            candidate.evidence.completeness.model_vm_complete = vm_complete;
            candidate.evidence.completeness.attachment_enumeration_complete =
                vm_complete;
            candidate.evidence.completeness.forward_enumeration_complete =
                traversal.materialization_complete &&
                graph.status == StageStatus::Complete &&
                reverse.enumeration_complete;
            candidate.evidence.completeness.cone_complete =
                cone->status == StageStatus::Complete;
            candidate.evidence.completeness.compatibility_complete =
                reverse.compatibility_complete;
            for (const std::string &reason : traversal.gap_reasons) {
                append_unique(
                    candidate.evidence.completeness.gap_reasons, reason);
            }
            if (!vm_complete) {
                append_unique(
                    candidate.evidence.completeness.gap_reasons,
                    "model VM or resource ledger is incomplete");
            }
            if (graph.status != StageStatus::Complete) {
                append_unique(
                    candidate.evidence.completeness.gap_reasons,
                    "contextual graph is conservative-incomplete");
            }
            if (cone->status != StageStatus::Complete) {
                append_unique(
                    candidate.evidence.completeness.gap_reasons,
                    "influence cone is conservative-incomplete");
            }
            for (const std::string &reason : reverse.gap_reasons) {
                append_unique(
                    candidate.evidence.completeness.gap_reasons, reason);
            }
            bool has_compatible = false;
            bool has_unknown = false;
            for (const BoundaryAttachment *attachment : attachments) {
                FrontierAttachmentAccount account;
                bool account_has_compatible = false;
                bool account_has_unknown = false;
                account.attachment_id = attachment->attachment_id;
                account.semantic_node_id = attachment->semantic_node_id;
                candidate.evidence.model_provenance.attachment_ids.push_back(
                    attachment->attachment_id);
                const auto contextual =
                    by_semantic.find(attachment->semantic_node_id);
                if (contextual == by_semantic.end()) {
                    account.disposition = AttachmentDisposition::Unresolved;
                    account.uncertainty_reasons.push_back(
                        "attachment semantic node has no contextual instance");
                    candidate.evidence.completeness
                        .attachment_enumeration_complete = false;
                    has_unknown = true;
                    candidate.attachment_accounting.push_back(
                        std::move(account));
                    continue;
                }
                for (const ContextualNode *boundary : contextual->second) {
                    account.contextual_node_ids.push_back(boundary->node_id);
                    const auto boundary_ordinal =
                        traversal.node_ordinals.find(boundary->node_id);
                    if (boundary_ordinal == traversal.node_ordinals.end() ||
                        boundary_ordinal->second >= reverse.states.size() ||
                        (reverse.enumeration_complete &&
                         reverse.states[boundary_ordinal->second] == 0U)) {
                        // The AP-root reverse fixed point already includes all
                        // graph and model arcs.  A boundary outside that set
                        // cannot meet this cone, so avoid a whole-program
                        // forward traversal whose result is provably empty.
                        continue;
                    }
                    const auto cache_key = std::make_pair(
                        boundary->node_id, attachment->certainty);
                    auto cached = forward_cache.find(cache_key);
                    if (cached == forward_cache.end()) {
                        cached = forward_cache.emplace(
                            cache_key,
                            forward_reach(
                                boundary->node_id, attachment->certainty,
                                traversal, options, ledger_caches))
                                     .first;
                    }
                    const ForwardResult &forward = cached->second;
                    if (!forward.enumeration_complete) {
                        candidate.evidence.completeness
                            .forward_enumeration_complete = false;
                    }
                    if (!forward.compatibility_complete) {
                        candidate.evidence.completeness.compatibility_complete =
                            false;
                    }
                    for (const std::string &reason : forward.gap_reasons) {
                        append_unique(
                            candidate.evidence.completeness.gap_reasons,
                            reason);
                    }
                    if (product_path_mask(
                            forward.states[boundary_ordinal->second],
                            reverse.states[boundary_ordinal->second]) != 0U) {
                        FrontierWitness witness = build_witness(
                            *attachment, boundary->node_id, cone->cone_id,
                            forward, reverse, traversal,
                            cone->status == StageStatus::Complete,
                            ledger_caches);
                        account.witness_ids.push_back(witness.witness_id);
                        for (const std::string &fact :
                             witness.model_fact_ids) {
                            candidate.evidence.model_provenance.model_fact_ids
                                .push_back(fact);
                        }
                        if (witness.compatibility ==
                            WitnessCompatibility::Compatible) {
                            account_has_compatible = true;
                            has_compatible = true;
                        }
                        if (witness.meet_summary.unknown_path_meet_count !=
                            0U) {
                            account_has_unknown = true;
                            has_unknown = true;
                        }
                        candidate.witnesses.push_back(std::move(witness));
                    }
                }
                sort_unique(account.contextual_node_ids);
                sort_unique(account.witness_ids);
                if (account.witness_ids.empty()) {
                    if (candidate.evidence.completeness
                            .forward_enumeration_complete &&
                        candidate.evidence.completeness.cone_complete &&
                        candidate.evidence.completeness
                            .compatibility_complete) {
                        account.disposition = AttachmentDisposition::NoMeet;
                    } else {
                        account.disposition = AttachmentDisposition::Unknown;
                        account.uncertainty_reasons.push_back(
                            "empty meet under an incomplete ledger");
                        account_has_unknown = true;
                        has_unknown = true;
                    }
                } else if (account_has_compatible) {
                    account.disposition = AttachmentDisposition::Witnessed;
                } else {
                    account.disposition = AttachmentDisposition::Unknown;
                }
                if (account_has_unknown) {
                    append_unique(
                        account.uncertainty_reasons,
                        "attachment retains UNKNOWN-compatible witness provenance");
                }
                sort_unique(account.uncertainty_reasons);
                candidate.attachment_accounting.push_back(std::move(account));
            }
            if (attachments.empty() && !vm_complete) {
                has_unknown = true;
                append_unique(
                    candidate.uncertainty_reasons,
                    "action has no attachment under an incomplete model ledger");
            }
            std::sort(
                candidate.witnesses.begin(), candidate.witnesses.end(),
                [](const FrontierWitness &left,
                   const FrontierWitness &right) {
                    return left.witness_id < right.witness_id;
                });
            sort_unique(
                candidate.evidence.model_provenance.attachment_ids);
            sort_unique(candidate.evidence.model_provenance.model_fact_ids);
            sort_unique(candidate.evidence.completeness.gap_reasons);

            ReachabilityVerdict strongest = ReachabilityVerdict::Unknown;
            for (const FrontierWitness &witness : candidate.witnesses) {
                if (witness.reachability ==
                    ReachabilityVerdict::StaticWitness) {
                    strongest = ReachabilityVerdict::StaticWitness;
                    break;
                }
                if (witness.reachability ==
                    ReachabilityVerdict::ModelledWitness) {
                    strongest = ReachabilityVerdict::ModelledWitness;
                }
            }
            if (has_compatible) {
                candidate.evidence.reachability = strongest;
            } else if (has_unknown ||
                       !closed(candidate.evidence.completeness)) {
                candidate.evidence.reachability =
                    ReachabilityVerdict::Unknown;
            } else {
                candidate.evidence.reachability =
                    ReachabilityVerdict::NoStaticWitness;
            }

            if (candidate.evidence.reachability ==
                    ReachabilityVerdict::NoStaticWitness ||
                candidate.evidence.controllability ==
                    ControllabilityVerdict::Unavailable) {
                candidate.disposition = FrontierDisposition::Rejected;
                candidate.rank_tier = 4;
                candidate.rank_reasons.push_back(
                    candidate.evidence.reachability ==
                            ReachabilityVerdict::NoStaticWitness
                        ? "closed static analysis found no witness"
                        : "executor manifest marks the action unavailable");
            } else if (
                (candidate.evidence.reachability ==
                     ReachabilityVerdict::StaticWitness ||
                 candidate.evidence.reachability ==
                     ReachabilityVerdict::ModelledWitness) &&
                controllable(candidate.evidence.controllability)) {
                candidate.disposition = FrontierDisposition::Actionable;
                candidate.rank_tier =
                    candidate.evidence.reachability ==
                            ReachabilityVerdict::StaticWitness
                        ? 0U
                        : 1U;
                candidate.rank_reasons.push_back(
                    "static/modelled witness and executor capability intersect");
            } else {
                candidate.disposition = FrontierDisposition::Pending;
                candidate.rank_tier =
                    candidate.evidence.reachability ==
                            ReachabilityVerdict::Unknown
                        ? 3U
                        : 2U;
                candidate.rank_reasons.push_back(
                    candidate.evidence.reachability ==
                            ReachabilityVerdict::Unknown
                        ? "static witness remains unknown"
                        : "executor controllability remains unknown");
            }
            if (candidate.evidence.reachability ==
                ReachabilityVerdict::Unknown) {
                for (const std::string &reason :
                     candidate.evidence.completeness.gap_reasons) {
                    append_unique(candidate.uncertainty_reasons, reason);
                }
                if (candidate.uncertainty_reasons.empty()) {
                    candidate.uncertainty_reasons.push_back(
                        "only UNKNOWN-compatible witnesses were found");
                }
                result.status = combine_status(
                    result.status, StageStatus::ConservativeIncomplete);
            }
            sort_unique(candidate.rank_reasons);
            sort_unique(candidate.uncertainty_reasons);
            result.candidates.push_back(std::move(candidate));
        }
    }
    std::sort(
        result.candidates.begin(), result.candidates.end(),
        [](const FrontierCandidate &left, const FrontierCandidate &right) {
            return left.candidate_id < right.candidate_id;
        });
    std::sort(
        result.coverage_gaps.begin(), result.coverage_gaps.end(),
        [](const CoverageGap &left, const CoverageGap &right) {
            return std::tie(left.gap_id, left.kind, left.detail) <
                   std::tie(right.gap_id, right.kind, right.detail);
        });
    sort_unique(result.diagnostics);
    return result;
}

FuzzableFrontier project_fuzzable_frontier(
    const FrontierCandidates &candidates,
    const std::string &frontier_candidates_sha256) {
    FuzzableFrontier result;
    result.frontier_candidates_sha256 = frontier_candidates_sha256;
    result.artifact_id = stable_id(
        "fuzzable-frontier", frontier_candidates_sha256);
    if (!valid_sha256(frontier_candidates_sha256)) {
        result.status = StageStatus::Failed;
        result.diagnostics.push_back(
            "frontier candidates digest is not SHA-256");
        return result;
    }
    result.status = candidates.status;
    for (const FrontierCandidate &candidate : candidates.candidates) {
        if (candidate.disposition != FrontierDisposition::Actionable) {
            continue;
        }
        FuzzableAction action;
        action.candidate_id = candidate.candidate_id;
        action.action = candidate.action;
        action.cone_id = candidate.cone_id;
        action.ap_id = candidate.ap_id;
        action.evidence = candidate.evidence;
        action.rank_tier = candidate.rank_tier;
        action.rank_reasons = candidate.rank_reasons;
        for (const FrontierWitness &witness : candidate.witnesses) {
            if (witness.compatibility == WitnessCompatibility::Compatible) {
                action.witness_ids.push_back(witness.witness_id);
            }
        }
        sort_unique(action.witness_ids);
        result.actions.push_back(std::move(action));
    }
    std::sort(
        result.actions.begin(), result.actions.end(),
        [](const FuzzableAction &left, const FuzzableAction &right) {
            return std::tie(left.rank_tier, left.candidate_id) <
                   std::tie(right.rank_tier, right.candidate_id);
        });
    return result;
}

std::vector<std::string> validate_frontier_candidates(
    const FrontierCandidates &candidates,
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierInputDigests &expected_digests,
    const std::optional<ExecutorCapabilityManifest> &executor_manifest,
    const FrontierOptions &options, const FrontierValidationMode mode) {
    std::vector<std::string> errors;
    if (!candidates.candidate_accounting_complete ||
        !candidates.ranking_never_prunes) {
        errors.push_back("frontier contract flags must remain true");
    }
    if (candidates.input_digests.model_fact_overlay_sha256 !=
            expected_digests.model_fact_overlay_sha256 ||
        candidates.input_digests.graph_sha256 !=
            expected_digests.graph_sha256 ||
        candidates.input_digests.cones_sha256 !=
            expected_digests.cones_sha256 ||
        candidates.input_digests.executor_manifest_sha256 !=
            expected_digests.executor_manifest_sha256) {
        errors.push_back("frontier input digest mismatch");
    }
    std::set<std::string> candidate_ids;
    std::set<std::string> witness_ids;
    for (const FrontierCandidate &candidate : candidates.candidates) {
        if (!candidate_ids.insert(candidate.candidate_id).second) {
            errors.push_back(
                "duplicate frontier candidate ID: " +
                candidate.candidate_id);
        }
        for (const FrontierWitness &witness : candidate.witnesses) {
            if (!witness_ids.insert(witness.witness_id).second) {
                errors.push_back(
                    "duplicate frontier witness ID: " + witness.witness_id);
            }
        }
    }
    if (mode == FrontierValidationMode::Structural) {
        sort_unique(errors);
        return errors;
    }
    const FrontierCandidates recomputed = compute_frontier_candidates(
        overlay, graph, cones, expected_digests, executor_manifest, options);
    if (canonical_frontier_candidates_json(candidates) !=
        canonical_frontier_candidates_json(recomputed)) {
        errors.push_back(
            "frontier candidates differ from deterministic recomputation");
    }
    sort_unique(errors);
    return errors;
}

std::vector<std::string> validate_fuzzable_frontier(
    const FuzzableFrontier &frontier,
    const FrontierCandidates &candidates,
    const std::string &expected_frontier_candidates_sha256) {
    std::vector<std::string> errors;
    if (!frontier.actionable_projection_only ||
        !frontier.ranking_never_prunes) {
        errors.push_back("fuzzable frontier projection flags must remain true");
    }
    if (frontier.frontier_candidates_sha256 !=
        expected_frontier_candidates_sha256) {
        errors.push_back("fuzzable frontier candidate digest mismatch");
    }
    const FuzzableFrontier recomputed = project_fuzzable_frontier(
        candidates, expected_frontier_candidates_sha256);
    if (canonical_fuzzable_frontier_json(frontier) !=
        canonical_fuzzable_frontier_json(recomputed)) {
        errors.push_back(
            "fuzzable frontier differs from deterministic projection");
    }
    return errors;
}

std::string canonical_frontier_candidates_json(
    const FrontierCandidates &candidates) {
    std::ostringstream output;
    output << "{\"schema_version\":"
           << json_escape(candidates.schema_version)
           << ",\"artifact_id\":" << json_escape(candidates.artifact_id)
           << ",\"input_digests\":{\"model_fact_overlay_sha256\":"
           << json_escape(
                  candidates.input_digests.model_fact_overlay_sha256)
           << ",\"graph_sha256\":"
           << json_escape(candidates.input_digests.graph_sha256)
           << ",\"cones_sha256\":"
           << json_escape(candidates.input_digests.cones_sha256)
           << ",\"executor_manifest_sha256\":";
    emit_optional_string(
        output, candidates.input_digests.executor_manifest_sha256);
    output << "},\"traversal_contract\":{\"algorithm\":"
           << json_escape(candidates.traversal_contract.algorithm)
           << ",\"algorithm_version\":"
           << json_escape(candidates.traversal_contract.algorithm_version)
           << ",\"node_order\":"
           << json_escape(candidates.traversal_contract.node_order)
           << ",\"edge_order\":"
           << json_escape(candidates.traversal_contract.edge_order)
           << ",\"path_class_encoding\":"
           << json_escape(
                  candidates.traversal_contract.path_class_encoding)
           << ",\"meet_ledger\":"
           << json_escape(candidates.traversal_contract.meet_ledger)
           << ",\"reach_ledger\":"
           << json_escape(candidates.traversal_contract.reach_ledger)
           << ",\"transition_ledger\":"
           << json_escape(candidates.traversal_contract.transition_ledger)
           << ",\"compatibility\":"
           << json_escape(candidates.traversal_contract.compatibility)
           << ",\"model_arc_policy\":"
           << json_escape(candidates.traversal_contract.model_arc_policy)
           << ",\"exemplar_policy\":"
           << json_escape(candidates.traversal_contract.exemplar_policy)
           << ",\"maximum_path_exemplars\":"
           << candidates.traversal_contract.maximum_path_exemplars
           << ",\"max_materialized_model_edges\":"
           << candidates.traversal_contract.max_materialized_model_edges
           << ",\"max_forward_states_per_attachment\":"
           << candidates.traversal_contract
                  .max_forward_states_per_attachment
           << "},\"traversal_contract_sha256\":"
           << json_escape(candidates.traversal_contract_sha256)
           << ",\"candidate_accounting_complete\":"
           << (candidates.candidate_accounting_complete ? "true" : "false")
           << ",\"ranking_never_prunes\":"
           << (candidates.ranking_never_prunes ? "true" : "false")
           << ",\"status\":" << json_escape(to_string(candidates.status))
           << ",\"candidates\":";
    emit_array(
        output, candidates.candidates,
        [](std::ostringstream &stream, const FrontierCandidate &candidate) {
            emit_candidate(stream, candidate);
        });
    output << ",\"unsupported_constructs\":";
    emit_array(
        output, candidates.coverage_gaps,
        [](std::ostringstream &stream, const CoverageGap &gap) {
            emit_gap(stream, gap);
        });
    output << ",\"diagnostics\":";
    emit_strings(output, candidates.diagnostics);
    output << '}';
    return output.str();
}

std::string canonical_fuzzable_frontier_json(
    const FuzzableFrontier &frontier) {
    std::ostringstream output;
    output << "{\"schema_version\":" << json_escape(frontier.schema_version)
           << ",\"artifact_id\":" << json_escape(frontier.artifact_id)
           << ",\"frontier_candidates_sha256\":"
           << json_escape(frontier.frontier_candidates_sha256)
           << ",\"actionable_projection_only\":"
           << (frontier.actionable_projection_only ? "true" : "false")
           << ",\"ranking_never_prunes\":"
           << (frontier.ranking_never_prunes ? "true" : "false")
           << ",\"status\":" << json_escape(to_string(frontier.status))
           << ",\"actions\":";
    emit_array(
        output, frontier.actions,
        [](std::ostringstream &stream, const FuzzableAction &action) {
            stream << "{\"candidate_id\":"
                   << json_escape(action.candidate_id) << ",\"action\":";
            emit_action(stream, action.action);
            stream << ",\"cone_id\":" << json_escape(action.cone_id)
                   << ",\"ap_id\":" << json_escape(action.ap_id)
                   << ",\"evidence\":";
            emit_axes(stream, action.evidence);
            stream << ",\"witness_ids\":";
            emit_strings(stream, action.witness_ids);
            stream << ",\"rank_tier\":" << action.rank_tier
                   << ",\"rank_reasons\":";
            emit_strings(stream, action.rank_reasons);
            stream << '}';
        });
    output << ",\"diagnostics\":";
    emit_strings(output, frontier.diagnostics);
    output << '}';
    return output.str();
}

const char *to_string(const ReachabilityVerdict value) {
    switch (value) {
    case ReachabilityVerdict::StaticWitness:
        return "STATIC_WITNESS";
    case ReachabilityVerdict::ModelledWitness:
        return "MODELLED_WITNESS";
    case ReachabilityVerdict::Unknown:
        return "UNKNOWN";
    case ReachabilityVerdict::NoStaticWitness:
        return "NO_STATIC_WITNESS";
    }
    return "UNKNOWN";
}

const char *to_string(const ControllabilityVerdict value) {
    switch (value) {
    case ControllabilityVerdict::Direct:
        return "DIRECT";
    case ControllabilityVerdict::Sequence:
        return "SEQUENCE";
    case ControllabilityVerdict::Timing:
        return "TIMING";
    case ControllabilityVerdict::Environment:
        return "ENVIRONMENT";
    case ControllabilityVerdict::Unavailable:
        return "UNAVAILABLE";
    case ControllabilityVerdict::Unknown:
        return "UNKNOWN";
    }
    return "UNKNOWN";
}

const char *to_string(const PathFeasibilityVerdict value) {
    switch (value) {
    case PathFeasibilityVerdict::Sat:
        return "SAT";
    case PathFeasibilityVerdict::Unsat:
        return "UNSAT";
    case PathFeasibilityVerdict::Unknown:
        return "UNKNOWN";
    case PathFeasibilityVerdict::NotEvaluated:
        return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

const char *to_string(const MutationSemanticsVerdict value) {
    switch (value) {
    case MutationSemanticsVerdict::Supported:
        return "SUPPORTED";
    case MutationSemanticsVerdict::Heuristic:
        return "HEURISTIC";
    case MutationSemanticsVerdict::Unknown:
        return "UNKNOWN";
    case MutationSemanticsVerdict::NotEvaluated:
        return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

const char *to_string(const RuntimeEvidenceVerdict value) {
    switch (value) {
    case RuntimeEvidenceVerdict::Confirmed:
        return "CONFIRMED";
    case RuntimeEvidenceVerdict::Refuted:
        return "REFUTED";
    case RuntimeEvidenceVerdict::Unknown:
        return "UNKNOWN";
    case RuntimeEvidenceVerdict::NotEvaluated:
        return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

const char *to_string(const WitnessCompatibility value) {
    switch (value) {
    case WitnessCompatibility::Compatible:
        return "COMPATIBLE";
    case WitnessCompatibility::Unknown:
        return "UNKNOWN";
    case WitnessCompatibility::Incompatible:
        return "INCOMPATIBLE";
    }
    return "UNKNOWN";
}

const char *to_string(const FrontierDisposition value) {
    switch (value) {
    case FrontierDisposition::Actionable:
        return "ACTIONABLE";
    case FrontierDisposition::Pending:
        return "PENDING";
    case FrontierDisposition::Rejected:
        return "REJECTED";
    }
    return "PENDING";
}

const char *to_string(const AttachmentDisposition value) {
    switch (value) {
    case AttachmentDisposition::Witnessed:
        return "WITNESSED";
    case AttachmentDisposition::Unknown:
        return "UNKNOWN";
    case AttachmentDisposition::NoMeet:
        return "NO_MEET";
    case AttachmentDisposition::Unresolved:
        return "UNRESOLVED";
    }
    return "UNRESOLVED";
}

const char *to_string(const FrontierPathClass value) {
    switch (value) {
    case FrontierPathClass::Static:
        return "STATIC";
    case FrontierPathClass::Modelled:
        return "MODELLED";
    case FrontierPathClass::Unknown:
        return "UNKNOWN";
    }
    return "UNKNOWN";
}

const char *to_string(const FrontierPathStepKind value) {
    switch (value) {
    case FrontierPathStepKind::GraphEdge:
        return "GRAPH_EDGE";
    case FrontierPathStepKind::ModelArc:
        return "MODEL_ARC";
    }
    return "GRAPH_EDGE";
}

}  // namespace rift::core
