#include "rift/core/influence.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace rift::core {
namespace {

struct ContextState {
    std::vector<std::string> callsites;
    bool truncated = false;
};

struct ActualBinding {
    std::string contextual_node_id;
    std::optional<AccessPath> path;
    ContextState caller_context;
    bool address_of = false;
};

using ParameterBindings =
    std::map<std::string, std::vector<ActualBinding>>;
using InstanceMap = std::map<std::string, std::vector<std::string>>;

struct InstantiatedTransferExpression {
    std::string root_expression_id;
    std::vector<std::string> input_node_ids;
    bool unknown = false;
    std::vector<std::string> uncertainty_reasons;
};

bool valid_sha256(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](const char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

std::string path_material(const AccessPath &path) {
    std::ostringstream stream;
    stream << path.root_entity_id << "|d=" << path.dereference_depth;
    for (const std::string &field : path.fields) {
        stream << "|f=" << field;
    }
    stream << "|u=" << path.unknown_suffix;
    return stream.str();
}

std::string context_material(const ContextState &context) {
    std::ostringstream stream;
    stream << "truncated=" << context.truncated;
    for (const std::string &callsite : context.callsites) {
        stream << "|c=" << callsite;
    }
    return stream.str();
}

std::string path_context_material(
    const AccessPath &path, const ContextState &context) {
    return path_material(path) + '\0' + context_material(context);
}

StageStatus combine_status(StageStatus left, StageStatus right) {
    if (left == StageStatus::Failed || right == StageStatus::Failed) {
        return StageStatus::Failed;
    }
    if (left == StageStatus::ConservativeIncomplete ||
        right == StageStatus::ConservativeIncomplete) {
        return StageStatus::ConservativeIncomplete;
    }
    return StageStatus::Complete;
}

void append_unique(std::vector<std::string> &values, const std::string &value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

void append_unique_index(
    std::vector<std::size_t> &values, const std::size_t value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

std::string field_name(const EntityRef *entity, const std::string &fallback) {
    if (entity == nullptr || !entity->qualified_signature) {
        return fallback;
    }
    std::string value = *entity->qualified_signature;
    const std::size_t type = value.rfind(':');
    if (type != std::string::npos) {
        value.resize(type);
    }
    const std::size_t separator = value.rfind("::");
    return separator == std::string::npos ? value : value.substr(separator + 2);
}

class GraphBuilder {
  public:
    GraphBuilder(
        const SemanticIndex &index, std::string semantic_index_sha256,
        InfluenceOptions options,
        const SemanticValueTransferIndex *semantic_transfers = nullptr,
        ValueTransferOptions transfer_options = {})
        : index_(index), semantic_index_sha256_(std::move(semantic_index_sha256)),
          options_(options), semantic_transfers_(semantic_transfers),
          transfer_options_(transfer_options) {
        for (const EntityRef &entity : index.entities) {
            entities_[entity.entity_id] = &entity;
        }
        for (const AbstractObject &object : index.abstract_objects) {
            objects_[object.object_id] = &object;
        }
        for (const SemanticNode &node : index.nodes) {
            nodes_[node.node_id] = &node;
        }
        for (const SemanticRelation &relation : index.relations) {
            relations_[relation.relation_id] = &relation;
        }
        for (const FunctionSummary &summary : index.function_summaries) {
            summaries_[summary.function_entity_id] = &summary;
        }
        for (const CallSiteSummary &callsite : index.callsites) {
            callsites_[callsite.callsite_id] = &callsite;
        }
        if (semantic_transfers_ != nullptr) {
            for (const TransferExpression &expression :
                 semantic_transfers_->expressions) {
                semantic_transfer_expressions_[expression.expression_id] =
                    &expression;
            }
            for (const TypedValueTransfer &transfer :
                 semantic_transfers_->transfers) {
                if (transfer.callsite_id && transfer.call_argument_index) {
                    semantic_call_argument_transfers_[
                        *transfer.callsite_id + '\0' +
                        std::to_string(*transfer.call_argument_index)] =
                        &transfer;
                }
            }
        }
    }

    ContextualizationArtifacts build_artifacts() {
        ContextualizationArtifacts artifacts;
        if (semantic_transfers_ == nullptr) {
            artifacts.graph = build();
            artifacts.value_transfers.status = StageStatus::Failed;
            artifacts.value_transfers.diagnostics.push_back(
                "semantic value-transfer sidecar was not supplied");
            return artifacts;
        }
        contextual_transfers_ = &artifacts.value_transfers;
        contextual_transfers_->semantic_value_transfer_artifact_id =
            semantic_transfers_->artifact_id;
        contextual_transfers_->semantic_index_sha256 =
            semantic_index_sha256_;
        contextual_transfers_->limits = transfer_options_;
        contextual_transfers_->status = semantic_transfers_->status;
        contextual_transfers_->property_independent =
            semantic_transfers_->property_independent;
        contextual_transfers_->candidate_accounting_complete =
            semantic_transfers_->candidate_accounting_complete;
        contextual_transfers_->resource_limit_hit =
            semantic_transfers_->resource_limit_hit;
        contextual_transfers_->coverage_gaps =
            semantic_transfers_->coverage_gaps;
        artifacts.graph = build();
        contextual_transfers_->graph_artifact_id = artifacts.graph.artifact_id;
        contextual_transfers_->status = combine_status(
            contextual_transfers_->status, artifacts.graph.status);
        std::sort(
            contextual_transfers_->expressions.begin(),
            contextual_transfers_->expressions.end(),
            [](const TransferExpression &left,
               const TransferExpression &right) {
                return left.expression_id < right.expression_id;
            });
        std::sort(
            contextual_transfers_->transfers.begin(),
            contextual_transfers_->transfers.end(),
            [](const TypedValueTransfer &left,
               const TypedValueTransfer &right) {
                return left.transfer_id < right.transfer_id;
            });
        contextual_transfers_->artifact_id =
            canonical_contextual_value_transfer_artifact_id(
                *contextual_transfers_);
        const std::vector<std::string> validation_errors =
            validate_contextual_value_transfers(
                *contextual_transfers_, artifacts.graph, index_,
                *semantic_transfers_);
        if (!validation_errors.empty()) {
            contextual_transfers_->status = StageStatus::Failed;
            contextual_transfers_->diagnostics.insert(
                contextual_transfers_->diagnostics.end(),
                validation_errors.begin(), validation_errors.end());
        }
        contextual_transfers_ = nullptr;
        return artifacts;
    }

    ContextualInfluenceGraph build() {
        ContextualInfluenceGraph graph;
        graph_ = &graph;
        graph.artifact_id = stable_id(
            "graph", semantic_index_sha256_ + '\0' +
                         std::to_string(options_.call_string_limit) + '\0' +
                         std::to_string(options_.recursion_expansion_limit));
        graph.semantic_index_sha256 = semantic_index_sha256_;
        graph.call_string_limit = options_.call_string_limit;
        graph.object_sensitivity = options_.object_sensitive ? "hybrid" : "none";
        graph.field_sensitivity = options_.field_sensitive ? "full" : "none";
        graph.status = index_.status;
        graph.coverage_gaps = index_.coverage_gaps;
        graph.diagnostics = index_.diagnostics;

        const std::vector<std::string> index_errors =
            validate_semantic_index(index_);
        if (!index_errors.empty() || index_.status == StageStatus::Failed ||
            !valid_sha256(semantic_index_sha256_)) {
            graph.status = StageStatus::Failed;
            graph.diagnostics.insert(
                graph.diagnostics.end(), index_errors.begin(), index_errors.end());
            if (!valid_sha256(semantic_index_sha256_)) {
                graph.diagnostics.push_back("semantic index digest is not SHA-256");
            }
            graph_ = nullptr;
            return graph;
        }

        std::set<std::string> internally_called;
        for (const CallSiteSummary &callsite : index_.callsites) {
            for (const std::string &callee : callsite.candidate_callee_ids) {
                if (callee != callsite.caller_function_id) {
                    internally_called.insert(callee);
                }
            }
        }
        std::set<std::string> entry_functions;
        for (const FunctionSummary &summary : index_.function_summaries) {
            if (!internally_called.contains(summary.function_entity_id)) {
                entry_functions.insert(summary.function_entity_id);
            }
        }
        if (entry_functions.empty() && !index_.function_summaries.empty()) {
            for (const FunctionSummary &summary : index_.function_summaries) {
                entry_functions.insert(summary.function_entity_id);
            }
            add_gap(
                "entry_scc_widening", GapEffect::SoundnessRisk,
                "No acyclic call-graph entry was found; root SCCs were conservatively widened",
                {}, {});
        }

        const ContextState root;
        InstanceMap root_instances;
        for (const SemanticNode &node : index_.nodes) {
            bool root_owned = node.owner_function_id.empty() ||
                              entry_functions.contains(node.owner_function_id);
            if (node.access_path && is_global_path(*node.access_path)) {
                root_owned = true;
            }
            if (root_owned) {
                root_instances[node.node_id] =
                    instance_node(node, root, std::nullopt);
            }
        }
        for (const SemanticRelation &relation : index_.relations) {
            if (root_instances.contains(relation.source_node_id) &&
                root_instances.contains(relation.target_node_id)) {
                add_instantiated_relation(relation, root_instances, false);
            }
        }
        instantiate_semantic_transfers(root_instances, false);
        for (const CallSiteSummary &callsite : index_.callsites) {
            if (callsite.caller_function_id.empty() ||
                entry_functions.contains(callsite.caller_function_id)) {
                std::map<std::string, std::uint32_t> recursion;
                instantiate_call(callsite, root, root_instances, recursion);
            }
        }

        if (std::any_of(
                graph.edges.begin(), graph.edges.end(),
                [](const InfluenceEdge &edge) {
                    return edge.certainty == Certainty::Unknown;
                })) {
            graph.status = combine_status(
                graph.status, StageStatus::ConservativeIncomplete);
        }
        const std::vector<std::string> errors =
            validate_contextual_graph(graph, semantic_index_sha256_);
        if (!errors.empty()) {
            graph.status = StageStatus::Failed;
            graph.diagnostics.insert(
                graph.diagnostics.end(), errors.begin(), errors.end());
        }
        graph_ = nullptr;
        return graph;
    }

  private:
    const EntityRef *entity(const std::string &id) const {
        const auto found = entities_.find(id);
        return found == entities_.end() ? nullptr : found->second;
    }

    std::shared_ptr<const EntityRef> intern_entity(const EntityRef &value) {
        const auto found = contextual_entities_.find(value.entity_id);
        if (found != contextual_entities_.end()) {
            return found->second;
        }
        auto shared = std::make_shared<const EntityRef>(value);
        contextual_entities_.emplace(value.entity_id, shared);
        return shared;
    }

    std::shared_ptr<const std::vector<Evidence>> intern_evidence(
        const std::vector<Evidence> &evidence) {
        std::string material;
        for (const Evidence &item : evidence) {
            material.append(item.evidence_id);
            material.push_back('\0');
        }
        const std::string key = stable_id("evidence-set", material);
        const auto found = contextual_evidence_.find(key);
        if (found != contextual_evidence_.end()) {
            return found->second;
        }
        auto shared =
            std::make_shared<const std::vector<Evidence>>(evidence);
        contextual_evidence_.emplace(key, shared);
        return shared;
    }

    std::shared_ptr<const AccessPath> intern_path(const AccessPath &path) {
        const std::string key = path_material(path);
        const auto found = contextual_paths_.find(key);
        if (found != contextual_paths_.end()) {
            return found->second;
        }
        auto shared = std::make_shared<const AccessPath>(path);
        contextual_paths_.emplace(key, shared);
        return shared;
    }

    const SemanticNode *semantic_node(const std::string &id) const {
        const auto found = nodes_.find(id);
        return found == nodes_.end() ? nullptr : found->second;
    }

    bool is_global_path(const AccessPath &path) const {
        const EntityRef *root = entity(path.root_entity_id);
        return root != nullptr && root->kind == EntityKind::Global;
    }

    ContextState effective_context(
        const SemanticNode &node, const ContextState &requested,
        const std::optional<AccessPath> &mapped_path) const {
        const std::optional<AccessPath> path =
            mapped_path ? mapped_path : node.access_path;
        if (path && is_global_path(*path)) {
            return {};
        }
        return requested;
    }

    AbstractObject object_for(
        const SemanticNode &node, const std::optional<AccessPath> &path) const {
        if (path) {
            const std::string id = stable_id("object", path->root_entity_id);
            AbstractObject result;
            result.object_id = id;
            const EntityRef *root = entity(path->root_entity_id);
            if (root != nullptr) {
                if (root->kind == EntityKind::Global) {
                    result.abstraction = ObjectAbstraction::Global;
                } else if (root->kind == EntityKind::Parameter) {
                    result.abstraction = ObjectAbstraction::Summary;
                } else {
                    result.abstraction = ObjectAbstraction::Stack;
                }
                if (!root->definitions.empty()) {
                    result.allocation_site = root->definitions.front();
                } else if (!root->declarations.empty()) {
                    result.allocation_site = root->declarations.front();
                }
            }
            result.certainty = path->unknown_suffix ? Certainty::Unknown
                                                   : Certainty::May;
            return result;
        }
        if (node.abstract_object_id) {
            const auto found = objects_.find(*node.abstract_object_id);
            if (found != objects_.end()) {
                return *found->second;
            }
        }
        return {
            stable_id("object", "unknown\0" + node.node_id),
            ObjectAbstraction::Unknown,
            std::nullopt,
            Certainty::Unknown,
        };
    }

    std::vector<std::string> instance_node(
        const SemanticNode &node, const ContextState &requested_context,
        const std::optional<AccessPath> &mapped_path) {
        const std::optional<AccessPath> path =
            mapped_path ? mapped_path : node.access_path;
        const ContextState context =
            effective_context(node, requested_context, path);
        const std::string semantic_material =
            "semantic\0" + node.node_id +
            (path ? "\0path\0" + path_material(*path) : std::string());
        const std::string id = stable_id(
            "cig", semantic_material + '\0' + context_material(context));
        const auto existing = contextual_node_indices_.find(id);
        std::size_t contextual_index = 0;
        if (existing == contextual_node_indices_.end()) {
            ContextualNode result;
            result.node_id = id;
            result.semantic_node_id = node.node_id;
            result.kind = node.kind;
            const std::string entity_id = path ? path->root_entity_id
                                               : node.entity_id;
            if (const EntityRef *resolved = entity(entity_id)) {
                result.entity = intern_entity(*resolved);
            } else if (const EntityRef *resolved = entity(node.entity_id)) {
                result.entity = intern_entity(*resolved);
            } else {
                EntityRef unknown_entity;
                unknown_entity.entity_id = stable_id(
                    "entity", "unknown\0" + entity_id);
                unknown_entity.kind = EntityKind::Unknown;
                unknown_entity.identity_status = IdentityStatus::Unknown;
                result.entity = intern_entity(unknown_entity);
            }
            result.abstract_object = object_for(node, path);
            if (path) {
                for (const std::string &field : path->fields) {
                    result.field_path.push_back(field_name(entity(field), field));
                }
            }
            result.call_context.callsite_ids = context.callsites;
            result.call_context.truncated = context.truncated;
            result.lifecycle_phase = LifecyclePhase::Unknown;
            result.task_context.kind = TaskKind::Unknown;
            result.task_context.certainty = Certainty::Unknown;
            result.scope.scope_id = stable_id(
                "scope", path ? path->root_entity_id : node.entity_id);
            result.scope.status = IdentityStatus::Unknown;
            result.generation.kind = IdentityStatus::Unknown;
            result.generation.reuse_possible = true;
            result.location = node.location;
            result.value_type = node.value_type;
            Evidence evidence;
            evidence.evidence_id = stable_id(
                "evidence", id + "\0contextual-instantiation");
            evidence.kind = "ast_semantics";
            evidence.certainty = path && !path->unknown_suffix
                                     ? Certainty::May
                                     : Certainty::Unknown;
            evidence.fact =
                "semantic node instantiated under callsite-tagged context";
            evidence.producer = "rift-context-instantiator";
            if (!node.location.file.empty()) {
                evidence.location = node.location;
            }
            result.evidence.push_back(std::move(evidence));
            contextual_index = graph_->nodes.size();
            graph_->nodes.push_back(std::move(result));
            contextual_node_indices_.emplace(
                graph_->nodes.back().node_id, contextual_index);
            effective_paths_by_node_.push_back(
                path ? intern_path(*path) : nullptr);
        } else {
            contextual_index = existing->second;
        }
        if (path) {
            append_unique_index(
                path_context_node_indices_[path_context_material(*path, context)],
                contextual_index);
        }
        return {id};
    }

    std::vector<std::optional<AccessPath>> mapped_paths(
        const SemanticNode &node, const ParameterBindings &bindings) const {
        if (!node.access_path) {
            return {std::nullopt};
        }
        const AccessPath &formal = *node.access_path;
        const auto found = bindings.find(formal.root_entity_id);
        if (found == bindings.end()) {
            return {formal};
        }
        std::vector<std::optional<AccessPath>> result;
        std::set<std::string> seen;
        for (const ActualBinding &actual : found->second) {
            if (!actual.path) {
                result.push_back(std::nullopt);
                continue;
            }
            AccessPath mapped = *actual.path;
            if (actual.address_of && formal.dereference_depth > 0) {
                mapped.dereference_depth += formal.dereference_depth - 1;
            } else {
                mapped.dereference_depth += formal.dereference_depth;
            }
            mapped.fields.insert(
                mapped.fields.end(), formal.fields.begin(), formal.fields.end());
            mapped.unknown_suffix =
                mapped.unknown_suffix || formal.unknown_suffix;
            const std::string material = path_material(mapped);
            if (seen.insert(material).second) {
                result.push_back(std::move(mapped));
            }
        }
        if (result.empty()) {
            result.push_back(formal);
        }
        return result;
    }

    InstanceMap instantiate_nodes(
        const FunctionSummary &summary, const ContextState &context,
        const ParameterBindings &bindings) {
        InstanceMap instances;
        std::vector<std::string> semantic_ids = summary.owned_node_ids;
        for (const std::string &node : summary.parameter_node_ids) {
            append_unique(semantic_ids, node);
        }
        if (summary.receiver_node_id) {
            append_unique(semantic_ids, *summary.receiver_node_id);
        }
        if (summary.return_node_id) {
            append_unique(semantic_ids, *summary.return_node_id);
        }
        for (const std::string &semantic_id : semantic_ids) {
            const SemanticNode *node = semantic_node(semantic_id);
            if (node == nullptr) {
                continue;
            }
            for (const std::optional<AccessPath> &path :
                 mapped_paths(*node, bindings)) {
                for (const std::string &instance :
                     instance_node(*node, context, path)) {
                    append_unique(instances[semantic_id], instance);
                }
            }
        }
        return instances;
    }

    Certainty contextual_certainty(
        Certainty original, bool widened) const {
        if (original == Certainty::Unknown) {
            return Certainty::Unknown;
        }
        if (widened || original == Certainty::Must) {
            return Certainty::May;
        }
        return original;
    }

    void add_edge(
        const std::string &source, const std::string &target,
        RelationKind kind, Certainty certainty,
        const std::vector<Evidence> &evidence,
        std::vector<std::string> conditions = {},
        std::vector<std::string> uncertainty = {}) {
        if (source.empty() || target.empty()) {
            return;
        }
        std::sort(conditions.begin(), conditions.end());
        conditions.erase(
            std::unique(conditions.begin(), conditions.end()), conditions.end());
        std::ostringstream material;
        material << source << '\0' << target << '\0'
                 << static_cast<int>(kind) << '\0'
                 << static_cast<int>(certainty);
        for (const std::string &condition : conditions) {
            material << '\0' << condition;
        }
        const std::string id = stable_id("edge", material.str());
        if (edge_ids_.contains(id)) {
            return;
        }
        InfluenceEdge edge;
        edge.edge_id = id;
        edge.source_node_id = source;
        edge.target_node_id = target;
        edge.kind = kind;
        edge.certainty = certainty;
        if (evidence.empty()) {
            Evidence generated;
            generated.evidence_id = stable_id("evidence", id);
            generated.kind = kind == RelationKind::Control
                                 ? "control_dependence"
                                 : "ast_semantics";
            generated.certainty = certainty;
            generated.fact = "context-instantiated influence edge";
            generated.producer = "rift-context-instantiator";
            std::vector<Evidence> generated_evidence;
            generated_evidence.push_back(std::move(generated));
            edge.evidence =
                std::make_shared<const std::vector<Evidence>>(
                    std::move(generated_evidence));
        } else {
            edge.evidence = intern_evidence(evidence);
        }
        edge.condition_node_ids = std::move(conditions);
        edge.uncertainty_reasons = std::move(uncertainty);
        if (certainty == Certainty::Unknown && edge.uncertainty_reasons.empty()) {
            edge.uncertainty_reasons.push_back(
                "analysis coverage is incomplete for this influence edge");
        }
        graph_->edges.push_back(std::move(edge));
        edge_ids_.insert(graph_->edges.back().edge_id);
        append_unique(
            edge_ids_by_pair_[source + '\0' + target],
            graph_->edges.back().edge_id);
    }

    std::vector<std::string> mapped_conditions(
        const SemanticRelation &relation, const InstanceMap &instances) const {
        std::vector<std::string> result;
        for (const std::string &semantic : relation.condition_node_ids) {
            const auto found = instances.find(semantic);
            if (found != instances.end()) {
                for (const std::string &instance : found->second) {
                    append_unique(result, instance);
                }
            }
        }
        return result;
    }

    void add_instantiated_relation(
        const SemanticRelation &relation, const InstanceMap &instances,
        bool widened) {
        const auto sources = instances.find(relation.source_node_id);
        const auto targets = instances.find(relation.target_node_id);
        if (sources == instances.end() || targets == instances.end()) {
            return;
        }
        const bool multi = sources->second.size() > 1 || targets->second.size() > 1;
        const Certainty certainty = contextual_certainty(
            relation.certainty, widened || multi);
        const std::vector<std::string> conditions =
            mapped_conditions(relation, instances);
        for (const std::string &source : sources->second) {
            for (const std::string &target : targets->second) {
                add_edge(
                    source, target, relation.kind, certainty,
                    relation.evidence, conditions,
                    relation.uncertainty_reasons);
            }
        }
    }

    void mark_contextual_transfer_limit(const std::string &reason) {
        if (contextual_transfers_ == nullptr) {
            return;
        }
        contextual_transfers_->resource_limit_hit = true;
        contextual_transfers_->candidate_accounting_complete = false;
        contextual_transfers_->status = combine_status(
            contextual_transfers_->status,
            StageStatus::ConservativeIncomplete);
        const std::string gap_id = stable_id(
            "value-transfer-gap",
            std::string(kValueTransferIdentityScheme) + '\0' + reason);
        if (!contextual_transfer_gap_ids_.insert(gap_id).second) {
            return;
        }
        CoverageGap gap;
        gap.gap_id = gap_id;
        gap.kind = "contextual_value_transfer_resource_limit";
        gap.effect = GapEffect::PrecisionLoss;
        gap.detail = reason;
        contextual_transfers_->coverage_gaps.push_back(std::move(gap));
    }

    std::string intern_contextual_transfer_expression(
        TransferExpression expression) {
        if (contextual_transfers_ == nullptr) {
            return {};
        }
        ++contextual_transfers_->observed_expression_nodes;
        if (expression.operand_expression_ids.size() >
            transfer_options_.maximum_expression_operands) {
            expression.kind = TransferExprKind::Unknown;
            expression.input.reset();
            expression.literal.reset();
            expression.cast_operation.reset();
            expression.compare_operation.reset();
            expression.boolean_operation.reset();
            expression.definedness_operation.reset();
            expression.operand_expression_ids.resize(
                transfer_options_.maximum_expression_operands);
            expression.guard_expression_ids.clear();
            expression.predecessor_ids.clear();
            expression.affine_coefficients.clear();
            expression.affine_offset.reset();
            expression.uncertainty_reasons = {
                "contextual expression operand count exceeded configured limit"};
            mark_contextual_transfer_limit(
                "Contextual expression operand count exceeded configured limit");
        }
        expression.expression_id =
            canonical_transfer_expression_id(expression);
        const auto known = contextual_transfer_expression_indices_.find(
            expression.expression_id);
        if (known != contextual_transfer_expression_indices_.end()) {
            return known->first;
        }
        if (contextual_transfers_->expressions.size() >=
                transfer_options_.maximum_expression_nodes &&
            expression.kind != TransferExprKind::Unknown) {
            mark_contextual_transfer_limit(
                "Contextual expression node budget exhausted");
            TransferExpression unknown;
            unknown.kind = TransferExprKind::Unknown;
            unknown.value_type = expression.value_type;
            unknown.uncertainty_reasons = {
                "contextual expression node budget exhausted"};
            unknown.expression_id =
                canonical_transfer_expression_id(unknown);
            const std::string unknown_id = unknown.expression_id;
            if (!contextual_transfer_expression_indices_.contains(
                    unknown_id)) {
                contextual_transfer_expression_indices_[unknown_id] =
                    contextual_transfers_->expressions.size();
                contextual_transfers_->expressions.push_back(
                    std::move(unknown));
            }
            return unknown_id;
        }
        contextual_transfer_expression_indices_[expression.expression_id] =
            contextual_transfers_->expressions.size();
        contextual_transfers_->expressions.push_back(std::move(expression));
        return contextual_transfers_->expressions.back().expression_id;
    }

    InstantiatedTransferExpression instantiate_transfer_expression(
        const std::string &semantic_expression_id,
        const InstanceMap &instances,
        std::map<std::string, InstantiatedTransferExpression> &memo) {
        const auto memoized = memo.find(semantic_expression_id);
        if (memoized != memo.end()) {
            return memoized->second;
        }
        InstantiatedTransferExpression result;
        const auto found = semantic_transfer_expressions_.find(
            semantic_expression_id);
        if (found == semantic_transfer_expressions_.end()) {
            TransferExpression unknown;
            unknown.kind = TransferExprKind::Unknown;
            unknown.value_type.kind = ValueKind::Unknown;
            unknown.value_type.canonical = "unknown";
            unknown.uncertainty_reasons = {
                "semantic transfer expression is absent"};
            result.root_expression_id =
                intern_contextual_transfer_expression(std::move(unknown));
            result.unknown = true;
            result.uncertainty_reasons = {
                "semantic transfer expression is absent"};
            memo[semantic_expression_id] = result;
            return result;
        }
        TransferExpression contextual = *found->second;
        contextual.expression_id.clear();
        if (contextual.kind == TransferExprKind::Input) {
            if (!contextual.input ||
                contextual.input->domain !=
                    TransferSymbolDomain::SemanticNode) {
                contextual.kind = TransferExprKind::Unknown;
                contextual.input.reset();
                contextual.uncertainty_reasons = {
                    "semantic sidecar input has an unexpected symbol domain"};
                result.unknown = true;
            } else {
                const auto mapped = instances.find(
                    contextual.input->symbol_id);
                if (mapped == instances.end() || mapped->second.size() != 1) {
                    contextual.kind = TransferExprKind::Unknown;
                    contextual.input.reset();
                    contextual.uncertainty_reasons = {
                        mapped == instances.end()
                            ? "semantic input has no contextual instance"
                            : "semantic input has multiple contextual instances"};
                    result.unknown = true;
                } else {
                    contextual.input->domain =
                        TransferSymbolDomain::ContextualNode;
                    contextual.input->symbol_id = mapped->second.front();
                    result.input_node_ids.push_back(mapped->second.front());
                }
            }
            result.uncertainty_reasons = contextual.uncertainty_reasons;
            result.root_expression_id =
                intern_contextual_transfer_expression(std::move(contextual));
            memo[semantic_expression_id] = result;
            return result;
        }
        contextual.operand_expression_ids.clear();
        contextual.guard_expression_ids.clear();
        for (const std::string &operand :
             found->second->operand_expression_ids) {
            InstantiatedTransferExpression child =
                instantiate_transfer_expression(operand, instances, memo);
            contextual.operand_expression_ids.push_back(
                child.root_expression_id);
            for (const std::string &input : child.input_node_ids) {
                append_unique(result.input_node_ids, input);
            }
            result.unknown = result.unknown || child.unknown;
            for (const std::string &reason : child.uncertainty_reasons) {
                append_unique(result.uncertainty_reasons, reason);
            }
        }
        for (const std::string &guard :
             found->second->guard_expression_ids) {
            InstantiatedTransferExpression child =
                instantiate_transfer_expression(guard, instances, memo);
            contextual.guard_expression_ids.push_back(
                child.root_expression_id);
            for (const std::string &input : child.input_node_ids) {
                append_unique(result.input_node_ids, input);
            }
            result.unknown = result.unknown || child.unknown;
            for (const std::string &reason : child.uncertainty_reasons) {
                append_unique(result.uncertainty_reasons, reason);
            }
        }
        if (found->second->kind == TransferExprKind::Unknown) {
            result.unknown = true;
            for (const std::string &reason :
                 found->second->uncertainty_reasons) {
                append_unique(result.uncertainty_reasons, reason);
            }
        }
        result.root_expression_id =
            intern_contextual_transfer_expression(std::move(contextual));
        memo[semantic_expression_id] = result;
        return result;
    }

    std::vector<std::string> supporting_edges(
        const std::vector<std::string> &inputs,
        const std::string &output) const {
        std::vector<std::string> result;
        for (const std::string &input : inputs) {
            const auto found = edge_ids_by_pair_.find(
                input + '\0' + output);
            if (found == edge_ids_by_pair_.end()) {
                continue;
            }
            for (const std::string &edge : found->second) {
                append_unique(result, edge);
            }
        }
        std::sort(result.begin(), result.end());
        return result;
    }

    void append_contextual_transfer(TypedValueTransfer transfer) {
        if (contextual_transfers_ == nullptr) {
            return;
        }
        ++contextual_transfers_->observed_transfers;
        std::sort(transfer.input_node_ids.begin(), transfer.input_node_ids.end());
        transfer.input_node_ids.erase(
            std::unique(
                transfer.input_node_ids.begin(),
                transfer.input_node_ids.end()),
            transfer.input_node_ids.end());
        std::sort(
            transfer.supporting_edge_ids.begin(),
            transfer.supporting_edge_ids.end());
        transfer.supporting_edge_ids.erase(
            std::unique(
                transfer.supporting_edge_ids.begin(),
                transfer.supporting_edge_ids.end()),
            transfer.supporting_edge_ids.end());
        transfer.transfer_id =
            canonical_typed_value_transfer_id(transfer);
        if (!contextual_transfer_ids_.insert(transfer.transfer_id).second) {
            return;
        }
        if (contextual_transfers_->transfers.size() >=
            transfer_options_.maximum_transfers) {
            contextual_transfer_ids_.erase(transfer.transfer_id);
            mark_contextual_transfer_limit(
                "Contextual transfer budget exhausted");
            return;
        }
        contextual_transfers_->transfers.push_back(std::move(transfer));
    }

    void instantiate_semantic_transfers(
        const InstanceMap &instances, bool widened) {
        if (semantic_transfers_ == nullptr ||
            contextual_transfers_ == nullptr) {
            return;
        }
        for (const TypedValueTransfer &semantic :
             semantic_transfers_->transfers) {
            if (semantic.output_domain !=
                TransferEndpointDomain::SemanticNode) {
                continue;
            }
            const auto outputs = instances.find(semantic.output_node_id);
            if (outputs == instances.end()) {
                continue;
            }
            for (const std::string &output : outputs->second) {
                std::map<std::string, InstantiatedTransferExpression> memo;
                InstantiatedTransferExpression expression =
                    instantiate_transfer_expression(
                        semantic.value_expression_id, instances, memo);
                TypedValueTransfer transfer = semantic;
                transfer.program_point_id = stable_id(
                    "contextual-program-point",
                    semantic.program_point_id + '\0' + output);
                transfer.output_domain =
                    TransferEndpointDomain::ContextualNode;
                transfer.input_node_ids =
                    std::move(expression.input_node_ids);
                transfer.output_node_id = output;
                transfer.value_expression_id =
                    expression.root_expression_id;
                if (semantic.defined_when_expression_id) {
                    const InstantiatedTransferExpression defined =
                        instantiate_transfer_expression(
                            *semantic.defined_when_expression_id,
                            instances, memo);
                    transfer.defined_when_expression_id =
                        defined.root_expression_id;
                    expression.unknown = expression.unknown || defined.unknown;
                    for (const std::string &reason :
                         defined.uncertainty_reasons) {
                        append_unique(
                            expression.uncertainty_reasons, reason);
                    }
                }
                if (semantic.path_condition_expression_id) {
                    const InstantiatedTransferExpression path =
                        instantiate_transfer_expression(
                            *semantic.path_condition_expression_id,
                            instances, memo);
                    transfer.path_condition_expression_id =
                        path.root_expression_id;
                    expression.unknown = expression.unknown || path.unknown;
                    for (const std::string &reason :
                         path.uncertainty_reasons) {
                        append_unique(
                            expression.uncertainty_reasons, reason);
                    }
                }
                transfer.supporting_edge_ids = supporting_edges(
                    transfer.input_node_ids, output);
                if (widened || expression.unknown) {
                    transfer.soundness = TransferSoundness::Unknown;
                    transfer.certainty = Certainty::Unknown;
                    for (const std::string &reason :
                         expression.uncertainty_reasons) {
                        append_unique(
                            transfer.uncertainty_reasons, reason);
                    }
                    if (widened) {
                        append_unique(
                            transfer.uncertainty_reasons,
                            "context expansion was widened");
                    }
                }
                transfer.transfer_id.clear();
                append_contextual_transfer(std::move(transfer));
            }
        }
    }

    ContextState push_context(
        const ContextState &parent, const std::string &callsite) {
        ContextState result = parent;
        result.callsites.push_back(callsite);
        if (options_.call_string_limit == 0) {
            result.callsites.clear();
            result.truncated = true;
        } else if (result.callsites.size() > options_.call_string_limit) {
            const std::size_t erase_count =
                result.callsites.size() - options_.call_string_limit;
            result.callsites.erase(
                result.callsites.begin(),
                result.callsites.begin() + static_cast<std::ptrdiff_t>(erase_count));
            result.truncated = true;
        }
        return result;
    }

    std::vector<ActualBinding> actuals_for_group(
        const std::vector<std::string> &group, bool address_of,
        const ContextState &caller_context, const InstanceMap &caller_instances) {
        std::vector<ActualBinding> result;
        std::set<std::string> seen;
        for (const std::string &semantic_id : group) {
            const auto found = caller_instances.find(semantic_id);
            if (found == caller_instances.end()) {
                continue;
            }
            for (const std::string &instance : found->second) {
                if (!seen.insert(instance).second) {
                    continue;
                }
                ActualBinding actual;
                actual.contextual_node_id = instance;
                const auto contextual = contextual_node_indices_.find(instance);
                if (contextual != contextual_node_indices_.end() &&
                    contextual->second < effective_paths_by_node_.size() &&
                    effective_paths_by_node_[contextual->second]) {
                    actual.path =
                        *effective_paths_by_node_[contextual->second];
                }
                actual.caller_context = caller_context;
                actual.address_of = address_of;
                result.push_back(std::move(actual));
            }
        }
        return result;
    }

    ParameterBindings bind_parameters(
        const FunctionSummary &callee, const CallSiteSummary &callsite,
        const ContextState &caller_context, const InstanceMap &caller_instances) {
        ParameterBindings bindings;
        const std::size_t count = std::min(
            callee.parameter_node_ids.size(),
            callsite.argument_node_groups.size());
        for (std::size_t index = 0; index < count; ++index) {
            const SemanticNode *formal =
                semantic_node(callee.parameter_node_ids[index]);
            if (formal == nullptr || !formal->access_path) {
                continue;
            }
            const bool address =
                index < callsite.argument_is_address.size() &&
                callsite.argument_is_address[index];
            bindings[formal->access_path->root_entity_id] = actuals_for_group(
                callsite.argument_node_groups[index], address,
                caller_context, caller_instances);
        }
        return bindings;
    }

    std::optional<AccessPath> mapped_path_for_actual(
        const SemanticNode &formal_node, const ActualBinding &actual) const {
        if (!formal_node.access_path || !actual.path) {
            return std::nullopt;
        }
        AccessPath mapped = *actual.path;
        const AccessPath &formal = *formal_node.access_path;
        if (actual.address_of && formal.dereference_depth > 0) {
            mapped.dereference_depth += formal.dereference_depth - 1;
        } else {
            mapped.dereference_depth += formal.dereference_depth;
        }
        mapped.fields.insert(
            mapped.fields.end(), formal.fields.begin(), formal.fields.end());
        mapped.unknown_suffix = mapped.unknown_suffix || formal.unknown_suffix;
        return mapped;
    }

    std::pair<bool, bool> access_mode(
        const FunctionSummary &callee, const std::string &semantic_id) const {
        bool read = false;
        bool write = false;
        for (const std::string &relation_id : callee.relation_ids) {
            const auto found = relations_.find(relation_id);
            if (found == relations_.end()) {
                continue;
            }
            read = read || found->second->source_node_id == semantic_id;
            write = write || found->second->target_node_id == semantic_id;
        }
        return {read, write};
    }

    enum class ProgramOrder {
        BeforeOrAtCall,
        AfterCall,
        Unknown,
    };

    ProgramOrder relative_to_call(
        const SourceLocation &node, const SourceLocation &call) const {
        if (node.file.empty() || call.file.empty() || node.line == 0 ||
            call.line == 0 || node.file != call.file) {
            return ProgramOrder::Unknown;
        }
        const std::pair<std::uint32_t, std::uint32_t> node_begin{
            node.line, node.column};
        const std::pair<std::uint32_t, std::uint32_t> call_end{
            call.end_line == 0 ? call.line : call.end_line,
            call.end_column == 0 ? call.column : call.end_column};
        return node_begin <= call_end ? ProgramOrder::BeforeOrAtCall
                                      : ProgramOrder::AfterCall;
    }

    std::vector<std::pair<std::string, ProgramOrder>> caller_path_peers(
        const AccessPath &path, const ActualBinding &actual,
        const CallSiteSummary &callsite) const {
        ContextState context = actual.caller_context;
        if (is_global_path(path)) {
            context = {};
        }
        const auto found = path_context_node_indices_.find(
            path_context_material(path, context));
        if (found == path_context_node_indices_.end()) {
            return {};
        }
        std::vector<std::pair<std::string, ProgramOrder>> result;
        for (const std::size_t contextual_index : found->second) {
            if (contextual_index >= graph_->nodes.size()) {
                continue;
            }
            const ContextualNode &node = graph_->nodes[contextual_index];
            const SemanticNode *semantic = semantic_node(node.semantic_node_id);
            if (semantic == nullptr) {
                continue;
            }
            if (!semantic->owner_function_id.empty() &&
                semantic->owner_function_id != callsite.caller_function_id) {
                continue;
            }
            result.emplace_back(
                node.node_id,
                relative_to_call(node.location, callsite.location));
        }
        return result;
    }

    void add_parameter_boundaries(
        const FunctionSummary &callee, const CallSiteSummary &callsite,
        const ParameterBindings &bindings,
        const InstanceMap &callee_instances) {
        for (const std::string &semantic_id : callee.owned_node_ids) {
            const SemanticNode *formal_node = semantic_node(semantic_id);
            if (formal_node == nullptr || !formal_node->access_path) {
                continue;
            }
            if (formal_node->access_path->dereference_depth == 0 &&
                formal_node->access_path->fields.empty()) {
                // Scalar/base parameter flow is represented by the explicit
                // actual-to-formal call edge below.  Creating a caller-context
                // projection with the formal semantic ID would reintroduce a
                // query-visible uncontextualized formal node.
                continue;
            }
            const auto binding =
                bindings.find(formal_node->access_path->root_entity_id);
            if (binding == bindings.end()) {
                continue;
            }
            const auto instances = callee_instances.find(semantic_id);
            if (instances == callee_instances.end()) {
                continue;
            }
            const auto [read, write] = access_mode(callee, semantic_id);
            if (!read && !write) {
                add_gap(
                    "unclassified_parameter_subobject_effect",
                    GapEffect::SoundnessRisk,
                    "A mapped parameter subobject has no classified read/write role in the function summary",
                    formal_node->location, {callsite.callsite_id, semantic_id});
            }
            for (const ActualBinding &actual : binding->second) {
                const std::optional<AccessPath> path =
                    mapped_path_for_actual(*formal_node, actual);
                if (!path) {
                    add_gap(
                        "unmapped_parameter_subobject",
                        GapEffect::SoundnessRisk,
                        "A parameter subobject could not be mapped to a caller access path",
                        callsite.location, {callsite.callsite_id, semantic_id});
                    continue;
                }
                const std::vector<std::pair<std::string, ProgramOrder>> peers =
                    caller_path_peers(*path, actual, callsite);
                for (const std::string &callee_instance : instances->second) {
                    const auto contextual =
                        contextual_node_indices_.find(callee_instance);
                    if (contextual == contextual_node_indices_.end() ||
                        contextual->second >= effective_paths_by_node_.size() ||
                        !effective_paths_by_node_[contextual->second] ||
                        path_material(
                            *effective_paths_by_node_[contextual->second]) !=
                            path_material(*path)) {
                        continue;
                    }
                    bool write_reaches_post_call_peer = false;
                    for (const auto &[peer, order] : peers) {
                        const bool uncertain_order =
                            order == ProgramOrder::Unknown;
                        const Certainty certainty =
                            uncertain_order ? Certainty::Unknown
                                            : Certainty::May;
                        std::vector<std::string> uncertainty;
                        if (uncertain_order) {
                            uncertainty.push_back(
                                "caller occurrence and callsite cannot be source-ordered");
                            add_gap(
                                "cross_file_call_boundary_order",
                                GapEffect::SoundnessRisk,
                                "Caller occurrence and callsite could not be ordered in one spelling file",
                                callsite.location,
                                {callsite.callsite_id, semantic_id});
                        }
                        if ((read || (!read && !write)) &&
                            (order == ProgramOrder::BeforeOrAtCall ||
                             uncertain_order)) {
                            add_edge(
                                peer, callee_instance, RelationKind::Call,
                                certainty, {}, {}, uncertainty);
                        }
                        if ((write || (!read && !write)) &&
                            (order == ProgramOrder::AfterCall ||
                             uncertain_order)) {
                            add_edge(
                                callee_instance, peer, RelationKind::Return,
                                certainty, {}, {}, uncertainty);
                            write_reaches_post_call_peer = true;
                        }
                    }
                    if (write && !write_reaches_post_call_peer) {
                        // A caller may pass an object to one mutating callee
                        // and then to a later reading callee without spelling
                        // an intervening field occurrence.  In that case the
                        // only caller node for the exact access path is its
                        // declaration/storage representative, whose source
                        // location necessarily precedes the write.  Preserve
                        // the memory state transition through that
                        // representative; the exact root+field path and
                        // caller context keep distinct objects separated.
                        for (const auto &[peer, order] : peers) {
                            if (order != ProgramOrder::BeforeOrAtCall) {
                                continue;
                            }
                            add_edge(
                                callee_instance, peer, RelationKind::Return,
                                Certainty::May, {}, {},
                                {"caller access-path storage summary represents post-call state"});
                        }
                    }
                    if (peers.empty() && (read || write)) {
                        // No edge is needed when the caller has no occurrence of
                        // this subobject on the relevant side of the call.  The
                        // mapped callee node still preserves the side effect in
                        // the complete graph.
                        continue;
                    }
                }
            }
        }

        for (const std::string &parameter_id : callee.parameter_node_ids) {
            const SemanticNode *formal = semantic_node(parameter_id);
            if (formal == nullptr || !formal->access_path) {
                continue;
            }
            const auto actuals = bindings.find(formal->access_path->root_entity_id);
            const auto formals = callee_instances.find(parameter_id);
            if (actuals == bindings.end() || formals == callee_instances.end()) {
                continue;
            }
            for (const ActualBinding &actual : actuals->second) {
                for (const std::string &formal_instance : formals->second) {
                    add_edge(
                        actual.contextual_node_id, formal_instance,
                        RelationKind::Call,
                        Certainty::May,
                        {}, {}, {"callsite-tagged actual-to-formal binding"});
                    const auto [read, write] =
                        access_mode(callee, parameter_id);
                    const bool reference_parameter =
                        formal->value_type.canonical.find('&') !=
                        std::string::npos;
                    if (write && reference_parameter) {
                        add_edge(
                            formal_instance, actual.contextual_node_id,
                            RelationKind::Return, Certainty::May, {}, {},
                            {"reference-parameter side effect returned to caller"});
                    }
                }
            }
        }
    }

    ValueType contextual_value_type(const std::string &id) const {
        const auto found = contextual_node_indices_.find(id);
        if (found == contextual_node_indices_.end() ||
            found->second >= graph_->nodes.size()) {
            ValueType unknown;
            unknown.kind = ValueKind::Unknown;
            unknown.canonical = "unknown";
            return unknown;
        }
        return graph_->nodes[found->second].value_type;
    }

    std::string contextual_input_expression(const std::string &node_id) {
        TransferExpression input;
        input.kind = TransferExprKind::Input;
        input.value_type = contextual_value_type(node_id);
        input.input = TransferSymbolRef{
            TransferSymbolDomain::ContextualNode,
            node_id,
            input.value_type};
        return intern_contextual_transfer_expression(std::move(input));
    }

    void instantiate_call_argument_transfers(
        const FunctionSummary &callee, const CallSiteSummary &callsite,
        const InstanceMap &caller_instances,
        const InstanceMap &callee_instances, bool exact_boundary) {
        if (contextual_transfers_ == nullptr ||
            semantic_transfers_ == nullptr) {
            return;
        }
        const std::size_t count = std::min(
            callee.parameter_node_ids.size(),
            callsite.argument_node_groups.size());
        for (std::size_t index = 0; index < count; ++index) {
            const auto formals = callee_instances.find(
                callee.parameter_node_ids[index]);
            if (formals == callee_instances.end()) {
                continue;
            }
            const auto summary = semantic_call_argument_transfers_.find(
                callsite.callsite_id + '\0' + std::to_string(index));
            for (const std::string &formal : formals->second) {
                TypedValueTransfer transfer;
                InstantiatedTransferExpression expression;
                std::map<std::string, InstantiatedTransferExpression> memo;
                if (summary != semantic_call_argument_transfers_.end()) {
                    expression = instantiate_transfer_expression(
                        summary->second->value_expression_id,
                        caller_instances, memo);
                    transfer = *summary->second;
                    transfer.semantic_relation_ids =
                        summary->second->semantic_relation_ids;
                    if (summary->second->defined_when_expression_id) {
                        transfer.defined_when_expression_id =
                            instantiate_transfer_expression(
                                *summary->second
                                     ->defined_when_expression_id,
                                caller_instances, memo)
                                .root_expression_id;
                    }
                } else {
                    TransferExpression unknown;
                    unknown.kind = TransferExprKind::Unknown;
                    unknown.value_type = contextual_value_type(formal);
                    unknown.uncertainty_reasons = {
                        "call argument has no semantic typed-transfer summary"};
                    const auto actual_group =
                        index < callsite.argument_node_groups.size()
                            ? &callsite.argument_node_groups[index]
                            : nullptr;
                    if (actual_group != nullptr) {
                        for (const std::string &semantic : *actual_group) {
                            const auto actuals = caller_instances.find(semantic);
                            if (actuals == caller_instances.end()) {
                                continue;
                            }
                            for (const std::string &actual : actuals->second) {
                                unknown.operand_expression_ids.push_back(
                                    contextual_input_expression(actual));
                                append_unique(
                                    expression.input_node_ids, actual);
                            }
                        }
                    }
                    expression.root_expression_id =
                        intern_contextual_transfer_expression(
                            std::move(unknown));
                    expression.unknown = true;
                    expression.uncertainty_reasons = {
                        "call argument has no semantic typed-transfer summary"};
                    transfer.definedness = DefinednessClass::Unknown;
                    transfer.path_condition =
                        PathConditionClass::Unconditional;
                }
                transfer.program_point_id = stable_id(
                    "contextual-call-argument",
                    callsite.callsite_id + '\0' +
                        std::to_string(index) + '\0' + formal);
                transfer.output_domain =
                    TransferEndpointDomain::ContextualNode;
                transfer.input_node_ids =
                    std::move(expression.input_node_ids);
                transfer.output_node_id = formal;
                transfer.value_expression_id =
                    expression.root_expression_id;
                transfer.supporting_edge_ids = supporting_edges(
                    transfer.input_node_ids, formal);
                transfer.callsite_id = callsite.callsite_id;
                transfer.call_argument_index =
                    static_cast<std::uint32_t>(index);
                if (!exact_boundary || expression.unknown ||
                    transfer.soundness != TransferSoundness::Exact) {
                    transfer.soundness = TransferSoundness::Unknown;
                    transfer.certainty = Certainty::Unknown;
                    if (!exact_boundary) {
                        append_unique(
                            transfer.uncertainty_reasons,
                            "call boundary is widened or target closure is incomplete");
                    }
                    for (const std::string &reason :
                         expression.uncertainty_reasons) {
                        append_unique(
                            transfer.uncertainty_reasons, reason);
                    }
                } else {
                    transfer.certainty = Certainty::Must;
                }
                transfer.transfer_id.clear();
                append_contextual_transfer(std::move(transfer));
            }
        }
    }

    void append_return_boundary_transfer(
        const CallSiteSummary &callsite, const std::string &source,
        const std::string &target, bool exact_boundary) {
        const std::string input = contextual_input_expression(source);
        TransferExpression identity;
        identity.kind = TransferExprKind::Identity;
        identity.value_type = contextual_value_type(source);
        identity.operand_expression_ids = {input};
        const std::string identity_id =
            intern_contextual_transfer_expression(std::move(identity));
        TransferExpression returned;
        returned.kind = TransferExprKind::Return;
        returned.value_type = contextual_value_type(target);
        returned.operand_expression_ids = {identity_id};

        TypedValueTransfer transfer;
        transfer.program_point_id = stable_id(
            "contextual-call-return",
            callsite.callsite_id + '\0' + source + '\0' + target);
        transfer.output_domain = TransferEndpointDomain::ContextualNode;
        transfer.input_node_ids = {source};
        transfer.output_node_id = target;
        transfer.supporting_edge_ids = supporting_edges({source}, target);
        transfer.value_expression_id =
            intern_contextual_transfer_expression(std::move(returned));
        transfer.definedness = DefinednessClass::Total;
        transfer.path_condition = PathConditionClass::Unconditional;
        transfer.soundness = exact_boundary
            ? TransferSoundness::Exact
            : TransferSoundness::Unknown;
        transfer.certainty = exact_boundary
            ? Certainty::Must
            : Certainty::Unknown;
        transfer.callsite_id = callsite.callsite_id;
        if (!exact_boundary) {
            transfer.uncertainty_reasons = {
                "return boundary is widened or target closure is incomplete"};
        }
        Evidence evidence;
        evidence.evidence_id = stable_id(
            "evidence", transfer.program_point_id + "\0direct-return");
        evidence.kind = "call_graph";
        evidence.certainty = transfer.certainty;
        evidence.fact =
            "Direct callee return slot is bound to the caller result";
        evidence.producer = "rift-context-value-transfer";
        evidence.location = callsite.location;
        transfer.evidence.push_back(std::move(evidence));
        append_contextual_transfer(std::move(transfer));
    }

    void append_unknown_call_transfer(
        const CallSiteSummary &callsite, const std::string &source,
        const std::string &target, const std::string &reason) {
        if (contextual_transfers_ == nullptr) {
            return;
        }
        TransferExpression unknown;
        unknown.kind = TransferExprKind::Unknown;
        unknown.value_type = contextual_value_type(target);
        unknown.operand_expression_ids = {
            contextual_input_expression(source)};
        unknown.uncertainty_reasons = {reason};

        TypedValueTransfer transfer;
        transfer.program_point_id = stable_id(
            "contextual-unknown-call",
            callsite.callsite_id + '\0' + source + '\0' + target);
        transfer.output_domain = TransferEndpointDomain::ContextualNode;
        transfer.input_node_ids = {source};
        transfer.output_node_id = target;
        transfer.supporting_edge_ids = supporting_edges({source}, target);
        transfer.value_expression_id =
            intern_contextual_transfer_expression(std::move(unknown));
        transfer.definedness = DefinednessClass::Unknown;
        transfer.path_condition = PathConditionClass::Unknown;
        transfer.soundness = TransferSoundness::Unknown;
        transfer.certainty = Certainty::Unknown;
        transfer.callsite_id = callsite.callsite_id;
        transfer.uncertainty_reasons = {reason};
        append_contextual_transfer(std::move(transfer));
    }

    void add_unknown_call(
        const CallSiteSummary &callsite, const ContextState &context,
        const InstanceMap &instances, const std::string &reason) {
        std::vector<std::string> arguments;
        for (const std::string &semantic : callsite.argument_node_ids) {
            const auto found = instances.find(semantic);
            if (found != instances.end()) {
                for (const std::string &node : found->second) {
                    append_unique(arguments, node);
                }
            }
        }
        std::vector<std::string> results;
        if (callsite.result_node_id) {
            const auto found = instances.find(*callsite.result_node_id);
            if (found != instances.end()) {
                results = found->second;
            }
        }
        if (results.empty()) {
            const std::string id = stable_id(
                "cig", "unknown-call\0" + callsite.callsite_id + '\0' +
                           context_material(context));
            if (!contextual_node_indices_.contains(id)) {
                ContextualNode unknown;
                unknown.node_id = id;
                unknown.semantic_node_id = stable_id(
                    "node", "unknown-call\0" + callsite.callsite_id);
                unknown.kind = SemanticNodeKind::Unknown;
                EntityRef unknown_entity;
                unknown_entity.entity_id = stable_id(
                    "entity", "unknown-call\0" + callsite.callsite_id);
                unknown_entity.kind = EntityKind::Unknown;
                unknown_entity.identity_status = IdentityStatus::Unknown;
                unknown.entity = intern_entity(unknown_entity);
                unknown.abstract_object.object_id = stable_id("object", id);
                unknown.abstract_object.abstraction = ObjectAbstraction::Unknown;
                unknown.abstract_object.certainty = Certainty::Unknown;
                unknown.call_context.callsite_ids = context.callsites;
                unknown.call_context.truncated = context.truncated;
                unknown.task_context.kind = TaskKind::Unknown;
                unknown.task_context.certainty = Certainty::Unknown;
                unknown.scope.scope_id = stable_id("scope", id);
                unknown.scope.status = IdentityStatus::Unknown;
                unknown.generation.kind = IdentityStatus::Unknown;
                unknown.generation.reuse_possible = true;
                unknown.location = callsite.location;
                unknown.value_type.kind = ValueKind::Unknown;
                unknown.value_type.canonical = "unknown";
                const std::size_t unknown_index = graph_->nodes.size();
                graph_->nodes.push_back(std::move(unknown));
                contextual_node_indices_.emplace(
                    graph_->nodes.back().node_id, unknown_index);
                effective_paths_by_node_.push_back(nullptr);
            }
            results.push_back(id);
        }
        for (const std::string &argument : arguments) {
            for (const std::string &result : results) {
                add_edge(
                    argument, result, RelationKind::Unknown,
                    Certainty::Unknown, {}, {}, {reason});
                // Unknown callees may mutate pointer/reference arguments.
                add_edge(
                    result, argument, RelationKind::Unknown,
                    Certainty::Unknown, {}, {}, {reason});
                append_unknown_call_transfer(
                    callsite, argument, result, reason);
            }
        }
        add_gap(
            "unknown_call_summary", GapEffect::SoundnessRisk,
            reason, callsite.location, {callsite.callsite_id});
    }

    void instantiate_call(
        const CallSiteSummary &callsite, const ContextState &caller_context,
        const InstanceMap &caller_instances,
        std::map<std::string, std::uint32_t> &recursion) {
        const std::string expansion_key =
            callsite.callsite_id + '\0' + context_material(caller_context);
        if (!expanded_calls_.insert(expansion_key).second) {
            return;
        }
        if (!callsite.direct || callsite.candidate_callee_ids.empty()) {
            add_unknown_call(
                callsite, caller_context, caller_instances,
                "indirect call target set is unresolved");
            return;
        }
        const bool multiple_targets = callsite.candidate_callee_ids.size() > 1;
        for (const std::string &callee_id : callsite.candidate_callee_ids) {
            const auto found = summaries_.find(callee_id);
            if (found == summaries_.end()) {
                add_unknown_call(
                    callsite, caller_context, caller_instances,
                    "direct callee definition is absent from the semantic index");
                continue;
            }
            std::uint32_t &depth = recursion[callee_id];
            if (depth >= options_.recursion_expansion_limit) {
                add_unknown_call(
                    callsite, caller_context, caller_instances,
                    "recursive SCC expansion reached its configured widening limit");
                add_gap(
                    "recursive_scc_widening", GapEffect::SoundnessRisk,
                    "Recursive call summary was widened after bounded expansion",
                    callsite.location, {callsite.callsite_id, callee_id});
                continue;
            }
            ++depth;
            const FunctionSummary &callee = *found->second;
            const ContextState callee_context =
                push_context(caller_context, callsite.callsite_id);
            const ParameterBindings bindings = bind_parameters(
                callee, callsite, caller_context, caller_instances);
            InstanceMap callee_instances =
                instantiate_nodes(callee, callee_context, bindings);
            const bool widened = multiple_targets || callee_context.truncated ||
                                 callsite.status != StageStatus::Complete;
            for (const std::string &relation_id : callee.relation_ids) {
                const auto relation = relations_.find(relation_id);
                if (relation != relations_.end()) {
                    add_instantiated_relation(
                        *relation->second, callee_instances, widened);
                }
            }
            instantiate_semantic_transfers(callee_instances, widened);
            add_parameter_boundaries(
                callee, callsite, bindings, callee_instances);
            instantiate_call_argument_transfers(
                callee, callsite, caller_instances, callee_instances,
                !widened && callsite.direct &&
                    callsite.candidate_callee_ids.size() == 1);

            if (callee.return_node_id && callsite.result_node_id) {
                const auto returned =
                    callee_instances.find(*callee.return_node_id);
                const auto result =
                    caller_instances.find(*callsite.result_node_id);
                if (returned != callee_instances.end() &&
                    result != caller_instances.end()) {
                    for (const std::string &source : returned->second) {
                        for (const std::string &target : result->second) {
                            add_edge(
                                source, target, RelationKind::Return,
                                Certainty::May,
                                {}, {},
                                {"callsite-tagged return-to-call binding"});
                            append_return_boundary_transfer(
                                callsite, source, target,
                                !widened &&
                                    contextual_value_type(source) ==
                                        contextual_value_type(target));
                        }
                    }
                }
            }
            for (const std::string &nested_id : callee.callsite_ids) {
                const auto nested = callsites_.find(nested_id);
                if (nested != callsites_.end()) {
                    instantiate_call(
                        *nested->second, callee_context, callee_instances,
                        recursion);
                }
            }
            --depth;
        }
    }

    void add_gap(
        const std::string &kind, GapEffect effect, const std::string &detail,
        const SourceLocation &location, std::vector<std::string> affected) {
        std::ostringstream material;
        material << kind << '\0' << detail << '\0' << location.file << ':'
                 << location.line << ':' << location.column;
        const std::string id = stable_id("gap", material.str());
        if (gap_ids_.insert(id).second) {
            CoverageGap gap;
            gap.gap_id = id;
            gap.kind = kind;
            gap.effect = effect;
            gap.detail = detail;
            if (!location.file.empty()) {
                gap.locations.push_back(location);
            }
            gap.affected_ids = std::move(affected);
            graph_->coverage_gaps.push_back(std::move(gap));
        }
        if (effect != GapEffect::PrecisionLoss) {
            graph_->status = combine_status(
                graph_->status, StageStatus::ConservativeIncomplete);
        }
    }

    const SemanticIndex &index_;
    std::string semantic_index_sha256_;
    InfluenceOptions options_;
    const SemanticValueTransferIndex *semantic_transfers_ = nullptr;
    ValueTransferOptions transfer_options_;
    ContextualInfluenceGraph *graph_ = nullptr;
    ContextualValueTransferIndex *contextual_transfers_ = nullptr;
    std::unordered_map<std::string_view, const EntityRef *> entities_;
    std::unordered_map<std::string_view, const AbstractObject *> objects_;
    std::unordered_map<std::string_view, const SemanticNode *> nodes_;
    std::unordered_map<std::string_view, const SemanticRelation *> relations_;
    std::unordered_map<std::string_view, const FunctionSummary *> summaries_;
    std::unordered_map<std::string_view, const CallSiteSummary *> callsites_;
    std::unordered_map<std::string_view, const TransferExpression *>
        semantic_transfer_expressions_;
    std::unordered_map<std::string, const TypedValueTransfer *>
        semantic_call_argument_transfers_;
    std::unordered_map<std::string, std::shared_ptr<const EntityRef>>
        contextual_entities_;
    std::unordered_map<
        std::string, std::shared_ptr<const std::vector<Evidence>>>
        contextual_evidence_;
    std::unordered_map<std::string, std::shared_ptr<const AccessPath>>
        contextual_paths_;
    std::unordered_map<std::string_view, std::size_t>
        contextual_node_indices_;
    std::vector<std::shared_ptr<const AccessPath>> effective_paths_by_node_;
    std::unordered_map<std::string, std::vector<std::size_t>>
        path_context_node_indices_;
    std::unordered_set<std::string_view> edge_ids_;
    std::unordered_map<std::string, std::vector<std::string>>
        edge_ids_by_pair_;
    std::unordered_map<std::string, std::size_t>
        contextual_transfer_expression_indices_;
    std::set<std::string> contextual_transfer_ids_;
    std::set<std::string> contextual_transfer_gap_ids_;
    std::set<std::string> expanded_calls_;
    std::set<std::string> gap_ids_;
};

ConeMembership edge_membership(Certainty certainty) {
    switch (certainty) {
    case Certainty::Must:
        return ConeMembership::MustInfluence;
    case Certainty::May:
        return ConeMembership::MayInfluence;
    case Certainty::Modelled:
        return ConeMembership::ModelledInfluence;
    case Certainty::Unknown:
        return ConeMembership::UnknownInfluence;
    }
    return ConeMembership::UnknownInfluence;
}

ConeMembership compose_membership(
    ConeMembership downstream, Certainty edge) {
    const ConeMembership current = edge_membership(edge);
    if (downstream == ConeMembership::UnknownInfluence ||
        current == ConeMembership::UnknownInfluence) {
        return ConeMembership::UnknownInfluence;
    }
    if (downstream == ConeMembership::ModelledInfluence ||
        current == ConeMembership::ModelledInfluence) {
        return ConeMembership::ModelledInfluence;
    }
    if (downstream == ConeMembership::MayInfluence ||
        current == ConeMembership::MayInfluence) {
        return ConeMembership::MayInfluence;
    }
    return ConeMembership::MustInfluence;
}

constexpr std::uint8_t membership_bit(const ConeMembership membership) {
    switch (membership) {
    case ConeMembership::MustInfluence:
        return 1U << 0U;
    case ConeMembership::MayInfluence:
        return 1U << 1U;
    case ConeMembership::ModelledInfluence:
        return 1U << 2U;
    case ConeMembership::UnknownInfluence:
        return 1U << 3U;
    }
    return 1U << 3U;
}

std::uint8_t compose_membership_mask(
    const std::uint8_t downstream_mask, const Certainty edge) {
    std::uint8_t result = 0;
    for (const ConeMembership membership : {
             ConeMembership::MustInfluence,
             ConeMembership::MayInfluence,
             ConeMembership::ModelledInfluence,
             ConeMembership::UnknownInfluence}) {
        if ((downstream_mask & membership_bit(membership)) != 0U) {
            result |= membership_bit(compose_membership(membership, edge));
        }
    }
    return result;
}

ConeMembership summarize_membership_mask(const std::uint8_t mask) {
    const bool has_must =
        (mask & membership_bit(ConeMembership::MustInfluence)) != 0U;
    const bool has_may =
        (mask & membership_bit(ConeMembership::MayInfluence)) != 0U;
    const bool has_modelled =
        (mask & membership_bit(ConeMembership::ModelledInfluence)) != 0U;
    const bool has_unknown =
        (mask & membership_bit(ConeMembership::UnknownInfluence)) != 0U;

    // UNKNOWN-only evidence remains unknown, but it cannot erase a separate
    // witnessed influence path.  MUST is downgraded whenever an alternate
    // path depends on modelling or unresolved facts.  The bit-set union makes
    // aggregation commutative, associative, idempotent, and cycle terminating.
    if (has_may || (has_must && (has_modelled || has_unknown))) {
        return ConeMembership::MayInfluence;
    }
    if (has_must) {
        return ConeMembership::MustInfluence;
    }
    if (has_modelled) {
        return ConeMembership::ModelledInfluence;
    }
    return ConeMembership::UnknownInfluence;
}

using IncomingInfluenceEdges =
    std::unordered_map<std::string, std::vector<const InfluenceEdge *>>;

std::unordered_map<std::string, std::uint8_t> compute_path_membership_masks(
    std::vector<std::string> roots, const ConeMembership root_membership,
    const IncomingInfluenceEdges &incoming) {
    std::sort(roots.begin(), roots.end());
    roots.erase(std::unique(roots.begin(), roots.end()), roots.end());
    const std::unordered_set<std::string> root_set(
        roots.begin(), roots.end());
    std::unordered_map<std::string, std::uint8_t> masks;
    masks.reserve(incoming.size() + roots.size());
    std::deque<std::string> worklist;
    for (const std::string &root : roots) {
        masks[root] = membership_bit(root_membership);
        worklist.push_back(root);
    }
    while (!worklist.empty()) {
        const std::string target = worklist.front();
        worklist.pop_front();
        const auto predecessors = incoming.find(target);
        if (predecessors == incoming.end()) {
            continue;
        }
        for (const InfluenceEdge *edge : predecessors->second) {
            if (root_set.contains(edge->source_node_id)) {
                continue;
            }
            const std::uint8_t candidate = compose_membership_mask(
                masks.at(target), edge->certainty);
            std::uint8_t &current = masks[edge->source_node_id];
            const std::uint8_t merged = current | candidate;
            if (merged != current) {
                current = merged;
                worklist.push_back(edge->source_node_id);
            }
        }
    }
    return masks;
}

const char *role_name(ApRole role) {
    switch (role) {
    case ApRole::Trigger:
        return "trigger";
    case ApRole::Response:
        return "response";
    case ApRole::Cancel:
        return "cancel";
    case ApRole::State:
        return "state";
    case ApRole::Guard:
        return "guard";
    case ApRole::Bound:
        return "bound";
    case ApRole::Clock:
        return "clock";
    case ApRole::Scope:
        return "scope";
    }
    return "state";
}

}  // namespace

ContextualInfluenceGraph build_contextual_influence_graph(
    const SemanticIndex &index, const std::string &semantic_index_sha256,
    const InfluenceOptions &options) {
    return GraphBuilder(index, semantic_index_sha256, options).build();
}

ContextualizationArtifacts
build_contextual_influence_graph_with_value_transfers(
    const SemanticIndex &index,
    const SemanticValueTransferIndex &semantic_transfers,
    const std::string &semantic_index_sha256,
    const InfluenceOptions &options,
    const ValueTransferOptions &transfer_options) {
    return GraphBuilder(
               index, semantic_index_sha256, options,
               &semantic_transfers, transfer_options)
        .build_artifacts();
}

ApInfluenceCones compute_influence_cones(
    const TypedPropertyIr &property, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const std::string &bindings_sha256, const std::string &graph_sha256) {
    ApInfluenceCones result;
    result.artifact_id = stable_id(
        "cones", bindings_sha256 + '\0' + graph_sha256);
    result.ap_bindings_sha256 = bindings_sha256;
    result.graph_sha256 = graph_sha256;
    if (!valid_sha256(bindings_sha256) || !valid_sha256(graph_sha256)) {
        result.status = StageStatus::Failed;
        result.diagnostics.push_back("cone input digest is not SHA-256");
        return result;
    }
    result.status = combine_status(bindings.status, graph.status);
    result.coverage_gaps = bindings.coverage_gaps;
    result.coverage_gaps.insert(
        result.coverage_gaps.end(), graph.coverage_gaps.begin(),
        graph.coverage_gaps.end());

    std::map<std::string, std::vector<const ContextualNode *>> semantic_nodes;
    for (const ContextualNode &node : graph.nodes) {
        semantic_nodes[node.semantic_node_id].push_back(&node);
    }
    IncomingInfluenceEdges incoming;
    incoming.reserve(graph.nodes.size());
    for (const InfluenceEdge &edge : graph.edges) {
        incoming[edge.target_node_id].push_back(&edge);
    }
    for (auto &[target, edges] : incoming) {
        (void)target;
        std::sort(
            edges.begin(), edges.end(),
            [](const InfluenceEdge *left, const InfluenceEdge *right) {
                return left->edge_id < right->edge_id;
            });
    }
    std::map<std::string, std::vector<const ApRoleBinding *>> by_ap;
    for (const ApRoleBinding &binding : bindings.bindings) {
        by_ap[binding.ap_id].push_back(&binding);
    }

    for (const AtomicProposition &ap : property.atomic_propositions) {
        ApInfluenceCone cone;
        cone.cone_id = stable_id("cone", ap.ap_id + '\0' + graph_sha256);
        cone.ap_id = ap.ap_id;
        cone.roles = ap.roles;
        cone.status = combine_status(bindings.status, graph.status);
        std::vector<std::string> roots;
        bool roots_are_fully_confirmed = true;
        std::set<ApRole> observed_roles;
        const auto binding_group = by_ap.find(ap.ap_id);
        if (binding_group == by_ap.end()) {
            roots_are_fully_confirmed = false;
            cone.status = StageStatus::ConservativeIncomplete;
            cone.uncertainty_reasons.push_back("AP has no role bindings");
        } else {
            for (const ApRoleBinding *binding : binding_group->second) {
                observed_roles.insert(binding->role);
                if (binding->resolution != BindingResolution::Confirmed) {
                    roots_are_fully_confirmed = false;
                }
                for (const BindingCandidate &candidate : binding->candidates) {
                    CandidateAccount account;
                    account.binding_id = candidate.binding_id;
                    if (candidate.status == CandidateStatus::Rejected) {
                        account.disposition = CandidateDisposition::Rejected;
                    } else if (candidate.status == CandidateStatus::Unresolved) {
                        roots_are_fully_confirmed = false;
                        account.disposition = CandidateDisposition::Unresolved;
                        account.uncertainty_reasons =
                            candidate.uncertainty_reasons;
                        if (account.uncertainty_reasons.empty()) {
                            account.uncertainty_reasons.push_back(
                                "binding candidate is unresolved");
                        }
                    } else {
                        if (candidate.status != CandidateStatus::Confirmed) {
                            roots_are_fully_confirmed = false;
                        }
                        for (const std::string &semantic :
                             candidate.semantic_node_ids) {
                            const auto instances = semantic_nodes.find(semantic);
                            if (instances == semantic_nodes.end()) {
                                continue;
                            }
                            for (const ContextualNode *node : instances->second) {
                                append_unique(account.root_node_ids, node->node_id);
                                append_unique(roots, node->node_id);
                            }
                        }
                        if (account.root_node_ids.empty()) {
                            roots_are_fully_confirmed = false;
                            account.disposition = CandidateDisposition::Unresolved;
                            account.uncertainty_reasons.push_back(
                                "binding semantic node has no contextual graph instance");
                            cone.status = StageStatus::ConservativeIncomplete;
                        } else {
                            account.disposition = CandidateDisposition::Included;
                        }
                    }
                    cone.candidate_accounting.push_back(std::move(account));
                }
                if (binding->candidates.empty()) {
                    roots_are_fully_confirmed = false;
                    CandidateAccount account;
                    account.binding_id = stable_id(
                        "binding", ap.ap_id + '\0' + role_name(binding->role) +
                                       "\0empty");
                    account.disposition = CandidateDisposition::Unresolved;
                    account.uncertainty_reasons.push_back(
                        "role binding contains no candidates");
                    cone.candidate_accounting.push_back(std::move(account));
                    cone.status = StageStatus::ConservativeIncomplete;
                }
            }
            const std::set<ApRole> expected_roles(
                ap.roles.begin(), ap.roles.end());
            if (observed_roles != expected_roles) {
                roots_are_fully_confirmed = false;
            }
        }

        std::sort(roots.begin(), roots.end());
        roots.erase(std::unique(roots.begin(), roots.end()), roots.end());
        const std::unordered_set<std::string> root_set(
            roots.begin(), roots.end());
        const bool unique_confirmed_root =
            roots_are_fully_confirmed && roots.size() == 1;
        if (!roots.empty() && !unique_confirmed_root) {
            cone.status = StageStatus::ConservativeIncomplete;
            append_unique(
                cone.uncertainty_reasons,
                "AP binding does not identify one uniquely confirmed contextual root");
        }

        struct Reach {
            ConeMembership membership = ConeMembership::UnknownInfluence;
            std::uint8_t path_membership_mask =
                membership_bit(ConeMembership::UnknownInfluence);
            std::vector<std::string> witness;
            std::vector<std::string> uncertainty;
            std::vector<std::string> path_nodes;
        };
        std::unordered_map<std::string, Reach> reached;
        reached.reserve(graph.nodes.size());
        std::deque<std::string> worklist;
        const ConeMembership root_membership = unique_confirmed_root
            ? ConeMembership::MustInfluence
            : ConeMembership::MayInfluence;
        for (const std::string &root : roots) {
            std::vector<std::string> uncertainty;
            if (!unique_confirmed_root) {
                uncertainty.push_back(
                    "root membership is possible but not uniquely confirmed");
            }
            reached[root] = {
                root_membership, membership_bit(root_membership), {},
                std::move(uncertainty), {root}};
            worklist.push_back(root);
        }
        while (!worklist.empty()) {
            const std::string current = worklist.front();
            worklist.pop_front();
            const Reach downstream = reached[current];
            const auto predecessors = incoming.find(current);
            if (predecessors == incoming.end()) {
                continue;
            }
            for (const InfluenceEdge *edge : predecessors->second) {
                Reach candidate;
                candidate.path_membership_mask = compose_membership_mask(
                    downstream.path_membership_mask, edge->certainty);
                candidate.membership = summarize_membership_mask(
                    candidate.path_membership_mask);
                candidate.witness.push_back(edge->edge_id);
                candidate.witness.insert(
                    candidate.witness.end(), downstream.witness.begin(),
                    downstream.witness.end());
                candidate.uncertainty = downstream.uncertainty;
                candidate.uncertainty.insert(
                    candidate.uncertainty.end(),
                    edge->uncertainty_reasons.begin(),
                    edge->uncertainty_reasons.end());
                candidate.path_nodes = downstream.path_nodes;
                const bool closes_cycle = std::find(
                    downstream.path_nodes.begin(), downstream.path_nodes.end(),
                    edge->source_node_id) != downstream.path_nodes.end();
                if (!closes_cycle) {
                    candidate.path_nodes.insert(
                        candidate.path_nodes.begin(), edge->source_node_id);
                }
                if (candidate.membership == ConeMembership::UnknownInfluence &&
                    candidate.uncertainty.empty()) {
                    candidate.uncertainty.push_back(
                        "witness path contains an unknown influence edge");
                }
                if (root_set.contains(edge->source_node_id)) {
                    // A cone root is a fixed observation point.  Alternate
                    // cyclic paths may weaken predecessors, but must not
                    // replace the root's empty certificate witness.
                    continue;
                }
                const auto existing = reached.find(edge->source_node_id);
                if (existing == reached.end()) {
                    reached[edge->source_node_id] = std::move(candidate);
                    worklist.push_back(edge->source_node_id);
                } else {
                    Reach &prior = existing->second;
                    const std::uint8_t merged_mask =
                        prior.path_membership_mask |
                        candidate.path_membership_mask;
                    if (merged_mask == prior.path_membership_mask) {
                        continue;
                    }
                    const ConeMembership prior_membership = prior.membership;
                    const ConeMembership merged_membership =
                        summarize_membership_mask(merged_mask);
                    if (closes_cycle) {
                        prior.path_membership_mask = merged_mask;
                        prior.membership = merged_membership;
                        for (const std::string &reason : candidate.uncertainty) {
                            append_unique(prior.uncertainty, reason);
                        }
                        append_unique(
                            prior.uncertainty,
                            "alternate influence path contains a cycle");
                    } else if (
                        merged_membership == candidate.membership &&
                        merged_membership != prior_membership) {
                        candidate.path_membership_mask = merged_mask;
                        prior = std::move(candidate);
                    } else {
                        prior.path_membership_mask = merged_mask;
                        prior.membership = merged_membership;
                        if (merged_membership != prior_membership) {
                            for (const std::string &reason :
                                 candidate.uncertainty) {
                                append_unique(prior.uncertainty, reason);
                            }
                            append_unique(
                                prior.uncertainty,
                                "alternate path classes conservatively prevent MUST classification");
                        }
                    }
                    // Even if the public summary is unchanged, a newly seen
                    // path class must propagate through predecessors.
                    worklist.push_back(edge->source_node_id);
                }
            }
        }
        for (auto &[node_id, reach] : reached) {
            (void)node_id;
            if ((reach.path_membership_mask &
                 membership_bit(ConeMembership::UnknownInfluence)) != 0U) {
                append_unique(
                    reach.uncertainty,
                    "aggregate path classes retain UNKNOWN provenance");
            }
            std::sort(reach.uncertainty.begin(), reach.uncertainty.end());
            reach.uncertainty.erase(
                std::unique(
                    reach.uncertainty.begin(), reach.uncertainty.end()),
                reach.uncertainty.end());
        }
        std::vector<std::pair<const std::string *, const Reach *> >
            ordered_reached;
        ordered_reached.reserve(reached.size());
        for (const auto &[node_id, reach] : reached) {
            ordered_reached.emplace_back(&node_id, &reach);
        }
        std::sort(
            ordered_reached.begin(), ordered_reached.end(),
            [](const auto &left, const auto &right) {
                return *left.first < *right.first;
            });
        std::set<std::string> used_edges;
        for (const auto &[node_id_pointer, reach_pointer] : ordered_reached) {
            const std::string &node_id = *node_id_pointer;
            const Reach &reach = *reach_pointer;
            ConeMember member;
            member.node_id = node_id;
            member.membership = reach.membership;
            member.witness_edge_ids = reach.witness;
            member.uncertainty_reasons = reach.uncertainty;
            for (const std::string &edge : reach.witness) {
                used_edges.insert(edge);
            }
            if ((reach.path_membership_mask &
                 membership_bit(ConeMembership::UnknownInfluence)) != 0U) {
                cone.status = StageStatus::ConservativeIncomplete;
            }
            cone.members.push_back(std::move(member));
        }
        cone.edge_ids.assign(used_edges.begin(), used_edges.end());
        if (roots.empty()) {
            cone.status = StageStatus::ConservativeIncomplete;
            cone.uncertainty_reasons.push_back(
                "no confirmed or candidate AP binding maps to a graph root");
        }
        if (cone.status != StageStatus::Complete &&
            cone.uncertainty_reasons.empty()) {
            cone.uncertainty_reasons.push_back(
                "binding or graph coverage is conservative-incomplete");
        }
        result.status = combine_status(result.status, cone.status);
        result.cones.push_back(std::move(cone));
    }

    ArtifactDigests expected;
    expected.ap_bindings_sha256 = bindings_sha256;
    expected.graph_sha256 = graph_sha256;
    const std::vector<std::string> errors = validate_influence_cones(
        result, bindings, graph, expected);
    if (!errors.empty()) {
        result.status = StageStatus::Failed;
        result.diagnostics.insert(
            result.diagnostics.end(), errors.begin(), errors.end());
    }
    return result;
}

std::vector<std::string> validate_influence_cones(
    const ApInfluenceCones &cones, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ArtifactDigests &expected_digests) {
    std::vector<std::string> errors;
    if (!valid_sha256(cones.ap_bindings_sha256) ||
        !valid_sha256(cones.graph_sha256)) {
        errors.push_back("influence cones contain an invalid input digest");
    }
    if (expected_digests.ap_bindings_sha256 &&
        cones.ap_bindings_sha256 != *expected_digests.ap_bindings_sha256) {
        errors.push_back("influence cones AP bindings digest mismatch");
    }
    if (expected_digests.graph_sha256 &&
        cones.graph_sha256 != *expected_digests.graph_sha256) {
        errors.push_back("influence cones graph digest mismatch");
    }
    if (!cones.candidate_accounting_complete || !cones.ranking_never_prunes) {
        errors.push_back("cone contract flags must remain true");
    }
    std::set<std::string> graph_nodes;
    std::map<std::string, const InfluenceEdge *> graph_edges;
    IncomingInfluenceEdges incoming_edges;
    incoming_edges.reserve(graph.nodes.size());
    for (const ContextualNode &node : graph.nodes) {
        graph_nodes.insert(node.node_id);
    }
    for (const InfluenceEdge &edge : graph.edges) {
        graph_edges[edge.edge_id] = &edge;
        incoming_edges[edge.target_node_id].push_back(&edge);
    }
    std::map<std::string, std::set<std::string>> expected_candidates;
    for (const ApRoleBinding &binding : bindings.bindings) {
        for (const BindingCandidate &candidate : binding.candidates) {
            expected_candidates[binding.ap_id].insert(candidate.binding_id);
        }
        if (binding.candidates.empty()) {
            expected_candidates[binding.ap_id].insert(stable_id(
                "binding", binding.ap_id + '\0' + role_name(binding.role) +
                               "\0empty"));
        }
    }
    std::set<std::string> cone_ids;
    for (const ApInfluenceCone &cone : cones.cones) {
        if (!cone_ids.insert(cone.cone_id).second) {
            errors.push_back("duplicate cone ID: " + cone.cone_id);
        }
        std::set<std::string> accounts;
        std::map<std::string, const CandidateAccount *> accounts_by_id;
        std::set<std::string> roots;
        for (const CandidateAccount &account : cone.candidate_accounting) {
            if (!accounts.insert(account.binding_id).second) {
                errors.push_back(
                    "candidate accounted more than once: " + account.binding_id);
            }
            accounts_by_id[account.binding_id] = &account;
            for (const std::string &root : account.root_node_ids) {
                if (!graph_nodes.contains(root)) {
                    errors.push_back("candidate account references unknown root: " + root);
                }
                if (account.disposition == CandidateDisposition::Included) {
                    roots.insert(root);
                }
            }
            if (account.disposition == CandidateDisposition::Included &&
                account.root_node_ids.empty()) {
                errors.push_back(
                    "included candidate account has no cone root: " +
                    account.binding_id);
            }
            if ((account.disposition == CandidateDisposition::Unresolved ||
                 account.disposition == CandidateDisposition::Unreachable) &&
                account.uncertainty_reasons.empty()) {
                errors.push_back(
                    "unresolved/unreachable candidate lacks uncertainty reason");
            }
        }
        if (accounts != expected_candidates[cone.ap_id]) {
            errors.push_back(
                "candidate accounting is not complete for AP: " + cone.ap_id);
        }
        bool must_root_is_uniquely_confirmed = roots.size() == 1;
        bool saw_binding = false;
        std::set<ApRole> observed_binding_roles;
        for (const ApRoleBinding &binding : bindings.bindings) {
            if (binding.ap_id != cone.ap_id) {
                continue;
            }
            saw_binding = true;
            observed_binding_roles.insert(binding.role);
            if (binding.resolution != BindingResolution::Confirmed ||
                binding.candidates.empty()) {
                must_root_is_uniquely_confirmed = false;
            }
            for (const BindingCandidate &candidate : binding.candidates) {
                if (candidate.status == CandidateStatus::Rejected) {
                    continue;
                }
                const auto account = accounts_by_id.find(candidate.binding_id);
                if (candidate.status != CandidateStatus::Confirmed ||
                    account == accounts_by_id.end() ||
                    account->second->disposition !=
                        CandidateDisposition::Included) {
                    must_root_is_uniquely_confirmed = false;
                }
            }
        }
        if (!saw_binding) {
            must_root_is_uniquely_confirmed = false;
        }
        const std::set<ApRole> expected_binding_roles(
            cone.roles.begin(), cone.roles.end());
        if (observed_binding_roles != expected_binding_roles) {
            must_root_is_uniquely_confirmed = false;
        }
        std::set<std::string> members;
        std::map<std::string, const ConeMember *> members_by_id;
        for (const ConeMember &member : cone.members) {
            if (!members.insert(member.node_id).second) {
                errors.push_back("duplicate cone member: " + member.node_id);
            }
            if (!graph_nodes.contains(member.node_id)) {
                errors.push_back("cone references unknown graph node: " + member.node_id);
            }
            members_by_id[member.node_id] = &member;
            for (const std::string &edge : member.witness_edge_ids) {
                if (!graph_edges.contains(edge)) {
                    errors.push_back("cone witness references unknown edge: " + edge);
                }
            }
            if (member.membership == ConeMembership::UnknownInfluence &&
                member.uncertainty_reasons.empty()) {
                errors.push_back("unknown cone member lacks uncertainty reason");
            }
            if (roots.contains(member.node_id) &&
                member.membership == ConeMembership::MustInfluence &&
                !must_root_is_uniquely_confirmed) {
                errors.push_back(
                    "MUST cone root is not uniquely confirmed: " +
                    member.node_id);
            }
        }
        const ConeMembership validated_root_membership =
            must_root_is_uniquely_confirmed
                ? ConeMembership::MustInfluence
                : ConeMembership::MayInfluence;
        const std::unordered_map<std::string, std::uint8_t> validated_masks =
            compute_path_membership_masks(
                std::vector<std::string>(roots.begin(), roots.end()),
                validated_root_membership, incoming_edges);
        for (const auto &[node_id, mask] : validated_masks) {
            const auto member = members_by_id.find(node_id);
            if (member == members_by_id.end()) {
                errors.push_back(
                    "path-class fixed point reaches a node absent from cone members: " +
                    node_id);
                continue;
            }
            if (member->second->membership !=
                summarize_membership_mask(mask)) {
                errors.push_back(
                    "cone membership does not match path-class fixed point: " +
                    node_id);
            }
            if ((mask & membership_bit(
                    ConeMembership::UnknownInfluence)) != 0U &&
                member->second->uncertainty_reasons.empty()) {
                errors.push_back(
                    "member with UNKNOWN path provenance lacks uncertainty reason: " +
                    node_id);
            }
        }
        for (const std::string &node_id : members) {
            if (!validated_masks.contains(node_id)) {
                errors.push_back(
                    "cone member is not justified by path-class fixed point: " +
                    node_id);
            }
        }
        for (const std::string &root : roots) {
            if (!members.contains(root)) {
                errors.push_back(
                    "included candidate root is absent from cone members: " +
                    root);
            }
        }
        const std::set<std::string> cone_edges(
            cone.edge_ids.begin(), cone.edge_ids.end());
        if (cone_edges.size() != cone.edge_ids.size()) {
            errors.push_back("cone edge set contains duplicate edge IDs: " +
                             cone.cone_id);
        }
        for (const std::string &edge : cone.edge_ids) {
            const auto graph_edge = graph_edges.find(edge);
            if (graph_edge == graph_edges.end()) {
                errors.push_back("cone edge set references unknown edge: " + edge);
                continue;
            }
            if (!members.contains(graph_edge->second->source_node_id) ||
                !members.contains(graph_edge->second->target_node_id)) {
                errors.push_back(
                    "cone edge endpoint is absent from cone members: " + edge);
            }
        }
        for (const ConeMember &member : cone.members) {
            if (roots.contains(member.node_id)) {
                if (!member.witness_edge_ids.empty()) {
                    errors.push_back(
                        "cone root must have an empty witness: " +
                        member.node_id);
                }
                continue;
            }
            if (member.witness_edge_ids.empty()) {
                errors.push_back(
                    "non-root cone member has no witness to a root: " +
                    member.node_id);
                continue;
            }
            std::string cursor = member.node_id;
            std::set<std::string> witness_edges;
            bool continuous = true;
            for (const std::string &edge_id : member.witness_edge_ids) {
                if (!cone_edges.contains(edge_id)) {
                    errors.push_back(
                        "member witness references an edge outside cone.edge_ids: " +
                        edge_id);
                    continuous = false;
                }
                if (!witness_edges.insert(edge_id).second) {
                    errors.push_back(
                        "member witness repeats an edge: " + edge_id);
                    continuous = false;
                }
                const auto edge = graph_edges.find(edge_id);
                if (edge == graph_edges.end()) {
                    continuous = false;
                    continue;
                }
                if (edge->second->source_node_id != cursor) {
                    errors.push_back(
                        "member witness is not a continuous source-to-root path: " +
                        member.node_id);
                    continuous = false;
                }
                cursor = edge->second->target_node_id;
            }
            if (continuous && !roots.contains(cursor)) {
                errors.push_back(
                    "member witness does not terminate at an included root: " +
                    member.node_id);
            }
        }
        if (cone.status != StageStatus::Complete &&
            cone.uncertainty_reasons.empty()) {
            errors.push_back("incomplete cone lacks uncertainty reason: " + cone.cone_id);
        }
    }
    return errors;
}

}  // namespace rift::core
