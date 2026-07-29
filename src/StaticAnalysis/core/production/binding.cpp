#include "rift/core/influence.h"

#include <algorithm>
#include <deque>
#include <filesystem>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace rift::core {
namespace {

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

bool valid_sha256(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](const char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

void append_unique(std::vector<std::string> &values, const std::string &value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

std::string normalize_path(std::string value) {
    std::replace(value.begin(), value.end(), '\\', '/');
    while (value.starts_with("./")) {
        value.erase(0, 2);
    }
    return value;
}

bool same_file(const std::string &expected, const std::string &actual) {
    const std::string left = normalize_path(expected);
    const std::string right = normalize_path(actual);
    return left == right || right.ends_with('/' + left) ||
           left.ends_with('/' + right);
}

bool same_location(
    const SourceLocation &selector, const SourceLocation &node) {
    if (!same_file(selector.file, node.file)) {
        return false;
    }
    const auto position = [](std::uint32_t line, std::uint32_t column) {
        return std::pair<std::uint32_t, std::uint32_t>{line, column};
    };
    const auto selected = position(selector.line, selector.column);
    const auto begin = position(node.line, node.column);
    if (node.end_line == 0 || node.end_column == 0) {
        return selected == begin;
    }
    const auto end = position(node.end_line, node.end_column);
    return selected >= begin && selected <= end;
}

std::string field_display_name(const EntityRef &entity) {
    if (entity.qualified_signature) {
        std::string value = *entity.qualified_signature;
        const std::size_t type = value.rfind(':');
        if (type != std::string::npos) {
            value.resize(type);
        }
        const std::size_t separator = value.rfind("::");
        return separator == std::string::npos ? value
                                              : value.substr(separator + 2);
    }
    return entity.entity_id;
}

struct SelectorMatch {
    std::set<std::string> node_ids;
    std::vector<std::set<std::string>> candidate_groups;
    std::set<std::string> function_constraints;
    std::string evidence_kind;
    bool semantic_confirmation = false;
    std::vector<std::string> uncertainty;
};

class Matcher {
  public:
    explicit Matcher(const SemanticIndex &index) : index_(index) {
        for (const EntityRef &entity : index.entities) {
            entities_[entity.entity_id] = &entity;
        }
        for (const SemanticNode &node : index.nodes) {
            nodes_[node.node_id] = &node;
        }
        for (const SemanticRelation &relation : index.relations) {
            adjacency_[relation.source_node_id].insert(relation.target_node_id);
            adjacency_[relation.target_node_id].insert(relation.source_node_id);
        }
        // CallSiteSummary is the authoritative interprocedural fact.  The
        // semantic relation table intentionally stores intra-procedural value
        // facts, so expose direct call-to-definition adjacency explicitly to
        // relational selector clauses without guessing from names.
        std::map<std::string, std::vector<std::string>> definitions_by_entity;
        for (const SemanticNode &node : index_.nodes) {
            if (node.kind == SemanticNodeKind::Definition) {
                definitions_by_entity[node.entity_id].push_back(node.node_id);
            }
        }
        for (const CallSiteSummary &callsite : index_.callsites) {
            if (!callsite.direct || !callsite.result_node_id) {
                continue;
            }
            for (const std::string &callee : callsite.candidate_callee_ids) {
                const auto definitions = definitions_by_entity.find(callee);
                if (definitions == definitions_by_entity.end()) {
                    continue;
                }
                for (const std::string &definition : definitions->second) {
                    adjacency_[*callsite.result_node_id].insert(definition);
                    adjacency_[definition].insert(*callsite.result_node_id);
                }
            }
        }
    }

    SelectorMatch match(
        const Selector &selector,
        const std::map<std::string, const Selector *> &selectors,
        std::set<std::string> &stack) const {
        SelectorMatch result;
        switch (selector.kind) {
        case SelectorKind::Usr:
            result.evidence_kind = "usr_match";
            result.semantic_confirmation = true;
            if (selector.usr) {
                for (const SemanticNode &node : index_.nodes) {
                    const EntityRef *entity = entity_for(node);
                    if (entity != nullptr && entity->usr &&
                        *entity->usr == *selector.usr) {
                        result.node_ids.insert(node.node_id);
                        if (entity->kind == EntityKind::Function ||
                            entity->kind == EntityKind::Method ||
                            entity->kind == EntityKind::Constructor ||
                            entity->kind == EntityKind::Destructor) {
                            result.function_constraints.insert(entity->entity_id);
                        }
                    }
                }
            }
            break;
        case SelectorKind::QualifiedSignature:
            result.evidence_kind = "qualified_signature_match";
            result.semantic_confirmation = true;
            if (selector.qualified_signature) {
                for (const SemanticNode &node : index_.nodes) {
                    const EntityRef *entity = entity_for(node);
                    if (entity != nullptr && entity->qualified_signature &&
                        *entity->qualified_signature ==
                            *selector.qualified_signature) {
                        result.node_ids.insert(node.node_id);
                        if (entity->kind == EntityKind::Function ||
                            entity->kind == EntityKind::Method ||
                            entity->kind == EntityKind::Constructor ||
                            entity->kind == EntityKind::Destructor) {
                            result.function_constraints.insert(entity->entity_id);
                        }
                    }
                }
            }
            break;
        case SelectorKind::SourceLocation:
            result.evidence_kind = "source_location_match";
            result.semantic_confirmation = true;
            if (selector.location) {
                std::vector<const SemanticNode *> candidates;
                for (const SemanticNode &node : index_.nodes) {
                    if (same_location(*selector.location, node.location)) {
                        candidates.push_back(&node);
                    }
                }
                if (!candidates.empty()) {
                    const auto span = [](const SemanticNode *node) {
                        if (node->location.end_line == 0 ||
                            node->location.end_column == 0) {
                            return std::uint64_t{0};
                        }
                        return (static_cast<std::uint64_t>(
                                    node->location.end_line -
                                    node->location.line)
                                << 32U) +
                               node->location.end_column;
                    };
                    const std::uint64_t best = span(*std::min_element(
                        candidates.begin(), candidates.end(),
                        [&](const SemanticNode *left,
                            const SemanticNode *right) {
                            return span(left) < span(right);
                        }));
                    for (const SemanticNode *node : candidates) {
                        if (span(node) == best) {
                            result.node_ids.insert(node->node_id);
                        }
                    }
                }
            }
            break;
        case SelectorKind::TypedFieldPath:
            result.evidence_kind = "type_field_match";
            result.semantic_confirmation = true;
            for (const SemanticNode &node : index_.nodes) {
                if (!node.access_path || selector.field_path.empty()) {
                    continue;
                }
                const EntityRef *root = entity_by_id(
                    node.access_path->root_entity_id);
                std::size_t selector_offset = 0;
                if (root != nullptr && root->canonical_type &&
                    type_component_matches(
                        selector.field_path.front(), *root->canonical_type)) {
                    selector_offset = 1;
                }
                const std::size_t selected_field_count =
                    selector.field_path.size() - selector_offset;
                const bool aggregate_prefix =
                    selector.value_type &&
                    selector.value_type->kind == ValueKind::Record &&
                    node.access_path->fields.size() >= selected_field_count;
                if (node.access_path->fields.size() != selected_field_count &&
                    !aggregate_prefix) {
                    continue;
                }
                const EntityRef *selected_field =
                    selected_field_count == 0
                        ? nullptr
                        : entity_by_id(node.access_path->fields[
                              selected_field_count - 1]);
                const bool type_matches =
                    !selector.value_type ||
                    type_component_matches(
                        selector.value_type->canonical,
                        node.value_type.canonical) ||
                    (selected_field != nullptr &&
                     selected_field->canonical_type &&
                     type_component_matches(
                         selector.value_type->canonical,
                         *selected_field->canonical_type)) ||
                    (root != nullptr && root->canonical_type &&
                     type_component_matches(
                         selector.value_type->canonical,
                         *root->canonical_type));
                if (!type_matches) {
                    continue;
                }
                bool equal = true;
                for (std::size_t index = 0;
                     index < selected_field_count; ++index) {
                    const auto found = entities_.find(
                        node.access_path->fields[index]);
                    if (found == entities_.end() ||
                        field_display_name(*found->second) !=
                            selector.field_path[index + selector_offset]) {
                        equal = false;
                        break;
                    }
                }
                if (equal) {
                    result.node_ids.insert(node.node_id);
                }
            }
            break;
        case SelectorKind::ExpressionStructure:
            result.evidence_kind = "expression_structure_match";
            result.semantic_confirmation = false;
            result.uncertainty.push_back(
                "AST expression shape is retained only as a retrieval candidate in M4");
            if (selector.expression) {
                for (const SemanticNode &node : index_.nodes) {
                    if (node.kind == SemanticNodeKind::Expression ||
                        node.kind == SemanticNodeKind::Control ||
                        node.kind == SemanticNodeKind::CallSite) {
                        if (selector.expression->value_type.canonical ==
                            node.value_type.canonical) {
                            result.node_ids.insert(node.node_id);
                        }
                    }
                }
            }
            break;
        case SelectorKind::Composite: {
            result.evidence_kind = "ast_semantics";
            result.semantic_confirmation = true;
            if (!stack.insert(selector.selector_id).second) {
                result.semantic_confirmation = false;
                result.uncertainty.push_back("cyclic composite selector");
                break;
            }
            struct Part {
                const Selector *selector = nullptr;
                SelectorMatch match;
            };
            std::vector<Part> parts;
            for (const std::string &component_id : selector.component_ids) {
                const auto component = selectors.find(component_id);
                if (component == selectors.end()) {
                    result.semantic_confirmation = false;
                    result.uncertainty.push_back(
                        "missing composite selector component: " + component_id);
                    continue;
                }
                SelectorMatch part = match(*component->second, selectors, stack);
                result.semantic_confirmation =
                    result.semantic_confirmation && part.semantic_confirmation;
                result.uncertainty.insert(
                    result.uncertainty.end(), part.uncertainty.begin(),
                    part.uncertainty.end());
                result.function_constraints.insert(
                    part.function_constraints.begin(),
                    part.function_constraints.end());
                parts.push_back({component->second, std::move(part)});
            }
            stack.erase(selector.selector_id);
            // A composite is a relational conjunction.  Build one compatible
            // witness set per site seed, requiring every component to
            // contribute.  Multiple occurrences that support one site are
            // accumulated in that candidate rather than misreported as
            // alternative AP sites.  This is the semantic primitive reused by
            // role-DNF all_of clauses.
            if (parts.size() == 1) {
                result.candidate_groups = parts.front().match.candidate_groups;
            } else {
                const auto part_priority = [](const Part &part) {
                    if (part.selector->kind == SelectorKind::SourceLocation ||
                        part.selector->kind ==
                            SelectorKind::ExpressionStructure) {
                        return 0;
                    }
                    if (!part.match.function_constraints.empty()) {
                        return 1;
                    }
                    return 2;
                };
                std::sort(
                    parts.begin(), parts.end(),
                    [&](const Part &left, const Part &right) {
                        const int left_priority = part_priority(left);
                        const int right_priority = part_priority(right);
                        if (left_priority != right_priority) {
                            return left_priority < right_priority;
                        }
                        return left.selector->selector_id <
                               right.selector->selector_id;
                    });
                const auto seed = std::find_if(
                    parts.begin(), parts.end(), [&](const Part &part) {
                        return part_priority(part) == 0;
                    });
                const Part &seed_part =
                    seed == parts.end() ? parts.front() : *seed;
                for (const std::set<std::string> &seed_group :
                     seed_part.match.candidate_groups) {
                    std::set<std::string> combined = seed_group;
                    bool satisfied = true;
                    for (const Part &part : parts) {
                        if (&part == &seed_part) {
                            continue;
                        }
                        bool component_satisfied = false;
                        std::set<std::string> contribution;
                        for (const std::set<std::string> &candidate :
                             part.match.candidate_groups) {
                            if (groups_compatible(combined, candidate)) {
                                component_satisfied = true;
                                contribution.insert(
                                    candidate.begin(), candidate.end());
                            }
                        }
                        if (!component_satisfied) {
                            satisfied = false;
                            break;
                        }
                        combined.insert(
                            contribution.begin(), contribution.end());
                    }
                    if (satisfied) {
                        result.candidate_groups.push_back(std::move(combined));
                    }
                }
                std::sort(
                    result.candidate_groups.begin(),
                    result.candidate_groups.end());
                result.candidate_groups.erase(
                    std::unique(
                        result.candidate_groups.begin(),
                        result.candidate_groups.end()),
                    result.candidate_groups.end());
            }
            for (const std::set<std::string> &group : result.candidate_groups) {
                result.node_ids.insert(group.begin(), group.end());
            }
            if (result.candidate_groups.empty()) {
                result.semantic_confirmation = false;
                result.uncertainty.push_back(
                    "composite components have no owner/dependency-compatible binding seed set");
            }
            break;
        }
        }
        if (result.candidate_groups.empty() &&
            selector.kind != SelectorKind::Composite) {
            for (const std::string &node : result.node_ids) {
                result.candidate_groups.push_back({node});
            }
        }
        return result;
    }

    const SemanticNode *node_for(const std::string &id) const {
        const auto found = nodes_.find(id);
        return found == nodes_.end() ? nullptr : found->second;
    }

  private:
    const EntityRef *entity_by_id(const std::string &id) const {
        const auto found = entities_.find(id);
        return found == entities_.end() ? nullptr : found->second;
    }

    static bool type_component_matches(
        const std::string &expected, const std::string &actual) {
        const auto strip = [](std::string value) {
            for (const std::string &prefix : {
                     std::string("const "), std::string("volatile "),
                     std::string("struct "), std::string("class ")}) {
                std::size_t position = 0;
                while ((position = value.find(prefix, position)) !=
                       std::string::npos) {
                    value.erase(position, prefix.size());
                }
            }
            value.erase(
                std::remove_if(
                    value.begin(), value.end(),
                    [](const char character) {
                        return character == '*' || character == '&' ||
                               character == ' ';
                    }),
                value.end());
            return value;
        };
        const std::string left = strip(expected);
        const std::string right = strip(actual);
        return left == right || right.ends_with("::" + left) ||
               left.ends_with("::" + right);
    }

    bool connected(const std::string &left, const std::string &right) const {
        if (left == right) {
            return true;
        }
        std::deque<std::pair<std::string, unsigned>> worklist{{left, 0}};
        std::set<std::string> visited{left};
        while (!worklist.empty()) {
            const auto [current, depth] = worklist.front();
            worklist.pop_front();
            if (depth >= 3) {
                continue;
            }
            const auto edges = adjacency_.find(current);
            if (edges == adjacency_.end()) {
                continue;
            }
            for (const std::string &next : edges->second) {
                if (next == right) {
                    return true;
                }
                if (visited.insert(next).second) {
                    worklist.push_back({next, depth + 1});
                }
            }
        }
        return false;
    }

    bool groups_compatible(
        const std::set<std::string> &left,
        const std::set<std::string> &right) const {
        bool left_has_access = false;
        bool right_has_access = false;
        for (const std::string &left_id : left) {
            const SemanticNode *node = node_for(left_id);
            left_has_access = left_has_access ||
                              (node != nullptr && node->access_path.has_value());
        }
        for (const std::string &right_id : right) {
            const SemanticNode *node = node_for(right_id);
            right_has_access = right_has_access ||
                               (node != nullptr && node->access_path.has_value());
        }
        for (const std::string &left_id : left) {
            const SemanticNode *left_node = node_for(left_id);
            if (left_node == nullptr) {
                continue;
            }
            for (const std::string &right_id : right) {
                const SemanticNode *right_node = node_for(right_id);
                if (right_node == nullptr) {
                    continue;
                }
                if (left_id == right_id ||
                    (left_node->access_path && right_node->access_path &&
                     !left_node->access_path->unknown_suffix &&
                     !right_node->access_path->unknown_suffix &&
                     (left_node->access_path->root_entity_id ==
                          right_node->access_path->root_entity_id ||
                      (left_node->abstract_object_id.has_value() &&
                       left_node->abstract_object_id ==
                           right_node->abstract_object_id))) ||
                    connected(left_id, right_id)) {
                    return true;
                }
                if ((!left_has_access || !right_has_access) &&
                    !left_node->owner_function_id.empty() &&
                    left_node->owner_function_id ==
                        right_node->owner_function_id) {
                    return true;
                }
            }
        }
        return false;
    }

    const EntityRef *entity_for(const SemanticNode &node) const {
        const auto found = entities_.find(node.entity_id);
        return found == entities_.end() ? nullptr : found->second;
    }

    const SemanticIndex &index_;
    std::map<std::string, const EntityRef *> entities_;
    std::map<std::string, const SemanticNode *> nodes_;
    std::map<std::string, std::set<std::string>> adjacency_;
};

CoverageGap binding_gap(
    const std::string &kind, const std::string &detail,
    const std::vector<std::string> &affected) {
    CoverageGap gap;
    std::ostringstream material;
    material << kind << '\0' << detail;
    for (const std::string &id : affected) {
        material << '\0' << id;
    }
    gap.gap_id = stable_id("gap", material.str());
    gap.kind = kind;
    gap.effect = GapEffect::SoundnessRisk;
    gap.detail = detail;
    gap.affected_ids = affected;
    return gap;
}

int candidate_status_rank(CandidateStatus status) {
    switch (status) {
    case CandidateStatus::Confirmed:
        return 0;
    case CandidateStatus::Candidate:
        return 1;
    case CandidateStatus::Unresolved:
        return 2;
    case CandidateStatus::Rejected:
        return 3;
    }
    return 4;
}

bool candidate_precedes(
    const BindingCandidate &left, const BindingCandidate &right) {
    if (left.confidence != right.confidence) {
        return left.confidence > right.confidence;
    }
    const int left_status = candidate_status_rank(left.status);
    const int right_status = candidate_status_rank(right.status);
    if (left_status != right_status) {
        return left_status < right_status;
    }
    if (left.semantic_node_ids != right.semantic_node_ids) {
        return left.semantic_node_ids < right.semantic_node_ids;
    }
    return left.binding_id < right.binding_id;
}

}  // namespace

ApBindings bind_atomic_propositions(
    const TypedPropertyIr &property, const SemanticIndex &index,
    const std::string &semantic_index_sha256,
    const BindingOptions &options) {
    ApBindings result;
    result.schema_version = property.schema_version;
    result.artifact_id = stable_id(
        "bindings", property.artifact_sha256 + '\0' + semantic_index_sha256);
    result.property_ir_sha256 = property.artifact_sha256;
    result.semantic_index_sha256 = semantic_index_sha256;
    if (options.similarity_can_confirm) {
        result.status = StageStatus::Failed;
        result.diagnostics.push_back(
            "similarity_can_confirm violates the RIFT binding contract");
        return result;
    }
    if (options.evaluate_cross_role_consistency) {
        result.status = StageStatus::Failed;
        result.diagnostics.push_back(
            "cross-role object/scope/generation consistency is not evaluated in M4");
        return result;
    }
    const std::vector<std::string> property_errors =
        validate_typed_property_ir(property);
    const std::vector<std::string> index_errors = validate_semantic_index(index);
    if (!property_errors.empty() || !index_errors.empty() ||
        !valid_sha256(semantic_index_sha256)) {
        result.status = StageStatus::Failed;
        result.diagnostics.insert(
            result.diagnostics.end(), property_errors.begin(), property_errors.end());
        result.diagnostics.insert(
            result.diagnostics.end(), index_errors.begin(), index_errors.end());
        if (!valid_sha256(semantic_index_sha256)) {
            result.diagnostics.push_back("semantic index digest is not SHA-256");
        }
        return result;
    }

    result.status = index.status == StageStatus::Failed
                        ? StageStatus::Failed
                        : index.status;
    Matcher matcher(index);
    std::map<std::string, const Selector *> selectors;
    for (const Selector &selector : property.selectors) {
        selectors[selector.selector_id] = &selector;
    }

    for (const AtomicProposition &ap : property.atomic_propositions) {
        if (property.schema_version == "1.0.0") {
        std::map<std::string, SelectorMatch> matches;
        for (const std::string &selector_id : ap.selector_ids) {
            const auto selector = selectors.find(selector_id);
            if (selector == selectors.end()) {
                continue;
            }
            std::set<std::string> stack;
            matches.emplace(
                selector_id, matcher.match(*selector->second, selectors, stack));
        }

        struct LedgerSeed {
            std::set<std::string> nodes;
            std::vector<std::string> selector_ids;
            std::vector<const SelectorMatch *> evidence;
            bool confirms = true;
            std::vector<std::string> uncertainty;
        };
        std::map<std::string, LedgerSeed> ledger;
        for (const auto &[selector_id, match] : matches) {
            for (const std::set<std::string> &group : match.candidate_groups) {
                std::ostringstream key;
                for (const std::string &node : group) {
                    key << node << '\0';
                }
                LedgerSeed &seed = ledger[key.str()];
                seed.nodes = group;
                append_unique(seed.selector_ids, selector_id);
                seed.evidence.push_back(&match);
                seed.confirms = seed.confirms && match.semantic_confirmation;
                seed.uncertainty.insert(
                    seed.uncertainty.end(), match.uncertainty.begin(),
                    match.uncertainty.end());
            }
        }

        for (const ApRole role : ap.roles) {
            ApRoleBinding binding;
            binding.ap_id = ap.ap_id;
            binding.role = role;

            for (const auto &[ledger_key, seed] : ledger) {
                BindingCandidate candidate;
                std::ostringstream material;
                material << ap.ap_id << '\0' << role_name(role) << '\0'
                         << ledger_key;
                candidate.binding_id = stable_id("binding", material.str());
                candidate.semantic_node_ids.assign(
                    seed.nodes.begin(), seed.nodes.end());
                candidate.selector_ids = seed.selector_ids;
                candidate.uncertainty_reasons = seed.uncertainty;
                for (std::size_t evidence_index = 0;
                     evidence_index < seed.evidence.size(); ++evidence_index) {
                    const SelectorMatch &match = *seed.evidence[evidence_index];
                    const std::string &selector_id =
                        seed.selector_ids[std::min(
                            evidence_index, seed.selector_ids.size() - 1)];
                    BindingEvidence evidence;
                    evidence.evidence_id = stable_id(
                        "evidence", candidate.binding_id + '\0' + selector_id);
                    evidence.kind = match.evidence_kind;
                    evidence.certainty = match.semantic_confirmation
                                             ? Certainty::Must
                                             : Certainty::Unknown;
                    evidence.fact =
                        "typed selector " + selector_id +
                        " produced an owner/dependency-compatible semantic binding set";
                    if (!seed.nodes.empty()) {
                        const SemanticNode *node =
                            matcher.node_for(*seed.nodes.begin());
                        if (node != nullptr) {
                        evidence.location = node->location;
                        }
                    }
                    candidate.evidence.push_back(std::move(evidence));
                }
                candidate.status = seed.confirms ? CandidateStatus::Candidate
                                                 : CandidateStatus::Unresolved;
                candidate.confidence = seed.confirms ? 1.0 : 0.5;
                binding.candidates.push_back(std::move(candidate));
            }

            std::vector<std::size_t> confirmable;
            for (std::size_t position = 0;
                 position < binding.candidates.size(); ++position) {
                if (binding.candidates[position].status ==
                    CandidateStatus::Candidate) {
                    confirmable.push_back(position);
                }
            }
            if (confirmable.size() == 1) {
                binding.resolution = BindingResolution::Confirmed;
                binding.candidates[confirmable.front()].status =
                    CandidateStatus::Confirmed;
            } else if (confirmable.size() > 1) {
                binding.resolution = BindingResolution::Ambiguous;
                result.status = StageStatus::ConservativeIncomplete;
                for (const std::size_t position : confirmable) {
                    binding.candidates[position].uncertainty_reasons.push_back(
                        "more than one semantic node satisfies the typed selector");
                }
                result.coverage_gaps.push_back(binding_gap(
                    "ambiguous_ap_binding",
                    "Multiple semantic nodes satisfy an AP role binding",
                    {ap.ap_id, role_name(role)}));
            } else {
                binding.resolution = BindingResolution::Unresolved;
                result.status = StageStatus::ConservativeIncomplete;
                result.coverage_gaps.push_back(binding_gap(
                    "unresolved_ap_binding",
                    "No semantically confirmable node satisfies an AP role binding",
                    {ap.ap_id, role_name(role)}));
            }
            std::sort(
                binding.candidates.begin(), binding.candidates.end(),
                candidate_precedes);
            result.bindings.push_back(std::move(binding));
        }
            continue;
        }

        // Schema 2.0.0 binds each temporal role from its own DNF clauses.
        // A clause is an all-of relational composite; clauses of one role are
        // designed alternatives, not accidental ambiguity.
        for (const ApRole role : ap.roles) {
            ApRoleBinding binding;
            binding.ap_id = ap.ap_id;
            binding.role = role;
            std::size_t group_count = 0;
            std::size_t confirmed_group_count = 0;
            bool any_ambiguous_group = false;

            for (const RoleSelectorGroup &group : ap.role_selector_groups) {
                if (group.role != role) {
                    continue;
                }
                ++group_count;
                std::vector<std::string> ordered_selectors = group.selector_ids;
                std::sort(ordered_selectors.begin(), ordered_selectors.end());

                std::map<std::string, SelectorMatch> component_matches;
                Selector clause;
                clause.selector_id = group.group_id;
                clause.kind = SelectorKind::Composite;
                clause.component_ids = ordered_selectors;
                bool all_components_present = true;
                for (const std::string &selector_id : ordered_selectors) {
                    const auto found = selectors.find(selector_id);
                    if (found == selectors.end()) {
                        all_components_present = false;
                        continue;
                    }
                    std::set<std::string> stack;
                    component_matches.emplace(
                        selector_id,
                        matcher.match(*found->second, selectors, stack));
                }
                std::set<std::string> stack;
                SelectorMatch clause_match = all_components_present
                                                 ? matcher.match(
                                                       clause, selectors, stack)
                                                 : SelectorMatch{};
                std::vector<std::size_t> group_candidate_positions;
                for (const std::set<std::string> &nodes :
                     clause_match.candidate_groups) {
                    BindingCandidate candidate;
                    candidate.selector_group_id = group.group_id;
                    candidate.selector_ids = ordered_selectors;
                    candidate.semantic_node_ids.assign(
                        nodes.begin(), nodes.end());
                    std::ostringstream material;
                    material << ap.ap_id << '\0' << role_name(role) << '\0'
                             << group.group_id << '\0';
                    for (const std::string &node : nodes) {
                        material << node << '\0';
                    }
                    candidate.binding_id =
                        stable_id("binding", material.str());
                    bool confirms = clause_match.semantic_confirmation;
                    for (const std::string &selector_id : ordered_selectors) {
                        const auto found = component_matches.find(selector_id);
                        if (found == component_matches.end()) {
                            confirms = false;
                            candidate.uncertainty_reasons.push_back(
                                "missing selector in role-DNF group: " +
                                selector_id);
                            continue;
                        }
                        const SelectorMatch &component = found->second;
                        confirms = confirms &&
                                   component.semantic_confirmation &&
                                   !component.candidate_groups.empty();
                        candidate.uncertainty_reasons.insert(
                            candidate.uncertainty_reasons.end(),
                            component.uncertainty.begin(),
                            component.uncertainty.end());
                        BindingEvidence evidence;
                        evidence.evidence_id = stable_id(
                            "evidence",
                            candidate.binding_id + '\0' + group.group_id +
                                '\0' + selector_id);
                        evidence.kind = component.evidence_kind;
                        evidence.certainty =
                            component.semantic_confirmation &&
                                    !component.candidate_groups.empty()
                                ? Certainty::Must
                                : Certainty::Unknown;
                        evidence.fact =
                            "role-DNF all-of selector " + selector_id +
                            " contributed an owner/dependency-compatible binding witness";
                        if (!nodes.empty()) {
                            const SemanticNode *node =
                                matcher.node_for(*nodes.begin());
                            if (node != nullptr) {
                                evidence.location = node->location;
                            }
                        }
                        candidate.evidence.push_back(std::move(evidence));
                    }
                    candidate.uncertainty_reasons.insert(
                        candidate.uncertainty_reasons.end(),
                        clause_match.uncertainty.begin(),
                        clause_match.uncertainty.end());
                    std::sort(
                        candidate.uncertainty_reasons.begin(),
                        candidate.uncertainty_reasons.end());
                    candidate.uncertainty_reasons.erase(
                        std::unique(
                            candidate.uncertainty_reasons.begin(),
                            candidate.uncertainty_reasons.end()),
                        candidate.uncertainty_reasons.end());
                    candidate.status = confirms ? CandidateStatus::Candidate
                                                : CandidateStatus::Unresolved;
                    candidate.confidence = confirms ? 1.0 : 0.5;
                    group_candidate_positions.push_back(
                        binding.candidates.size());
                    binding.candidates.push_back(std::move(candidate));
                }

                std::vector<std::size_t> confirmable;
                for (const std::size_t position : group_candidate_positions) {
                    if (binding.candidates[position].status ==
                        CandidateStatus::Candidate) {
                        confirmable.push_back(position);
                    }
                }
                if (confirmable.size() == 1) {
                    binding.candidates[confirmable.front()].status =
                        CandidateStatus::Confirmed;
                    ++confirmed_group_count;
                } else if (confirmable.size() > 1) {
                    any_ambiguous_group = true;
                    for (const std::size_t position : confirmable) {
                        binding.candidates[position].uncertainty_reasons.push_back(
                            "more than one semantic candidate satisfies one role-DNF group");
                    }
                    result.coverage_gaps.push_back(binding_gap(
                        "ambiguous_role_selector_group",
                        "Multiple semantic candidates satisfy one role-DNF all-of group",
                        {ap.ap_id, role_name(role), group.group_id}));
                } else {
                    BindingCandidate placeholder;
                    placeholder.selector_group_id = group.group_id;
                    placeholder.selector_ids = ordered_selectors;
                    std::ostringstream material;
                    material << ap.ap_id << '\0' << role_name(role) << '\0'
                             << group.group_id << "\0unresolved";
                    placeholder.binding_id =
                        stable_id("binding", material.str());
                    placeholder.status = CandidateStatus::Unresolved;
                    placeholder.confidence = 0.0;
                    placeholder.uncertainty_reasons.push_back(
                        "role-DNF group has no complete owner/dependency-compatible candidate");
                    binding.candidates.push_back(std::move(placeholder));
                    result.coverage_gaps.push_back(binding_gap(
                        "unresolved_role_selector_group",
                        "No semantic candidate satisfies one role-DNF all-of group",
                        {ap.ap_id, role_name(role), group.group_id}));
                }
            }

            if (group_count > 0 && confirmed_group_count == group_count) {
                binding.resolution = BindingResolution::Confirmed;
            } else if (confirmed_group_count > 0) {
                binding.resolution = BindingResolution::Partial;
                result.status = StageStatus::ConservativeIncomplete;
                result.coverage_gaps.push_back(binding_gap(
                    "partial_ap_role_binding",
                    "Only a subset of the designed role-DNF alternatives is confirmed",
                    {ap.ap_id, role_name(role)}));
            } else if (any_ambiguous_group) {
                binding.resolution = BindingResolution::Ambiguous;
                result.status = StageStatus::ConservativeIncomplete;
            } else {
                binding.resolution = BindingResolution::Unresolved;
                result.status = StageStatus::ConservativeIncomplete;
            }
            std::sort(
                binding.candidates.begin(), binding.candidates.end(),
                candidate_precedes);
            result.bindings.push_back(std::move(binding));
        }
    }

    ArtifactDigests expected;
    expected.property_ir_sha256 = property.artifact_sha256;
    expected.semantic_index_sha256 = semantic_index_sha256;
    const std::vector<std::string> validation_errors =
        validate_ap_bindings(result, property, index, expected);
    if (!validation_errors.empty()) {
        result.status = StageStatus::Failed;
        result.diagnostics.insert(
            result.diagnostics.end(), validation_errors.begin(),
            validation_errors.end());
    }
    return result;
}

std::vector<std::string> validate_ap_bindings(
    const ApBindings &bindings, const TypedPropertyIr &property,
    const SemanticIndex &index, const ArtifactDigests &expected_digests) {
    std::vector<std::string> errors;
    if (bindings.schema_version != property.schema_version) {
        errors.push_back("AP bindings schema version does not match Property IR");
    }
    if (!valid_sha256(bindings.property_ir_sha256) ||
        !valid_sha256(bindings.semantic_index_sha256)) {
        errors.push_back("AP bindings contain an invalid input digest");
    }
    if (bindings.property_ir_sha256 != property.artifact_sha256) {
        errors.push_back("AP bindings Property IR digest does not bind the loaded artifact");
    }
    if (expected_digests.property_ir_sha256 &&
        bindings.property_ir_sha256 != *expected_digests.property_ir_sha256) {
        errors.push_back("AP bindings Property IR digest mismatch");
    }
    if (expected_digests.semantic_index_sha256 &&
        bindings.semantic_index_sha256 !=
            *expected_digests.semantic_index_sha256) {
        errors.push_back("AP bindings semantic index digest mismatch");
    }

    std::map<std::string, std::set<ApRole>> ap_roles;
    std::map<
        std::pair<std::string, ApRole>,
        std::map<std::string, std::set<std::string>>>
        role_groups;
    std::set<std::string> selector_ids;
    std::set<std::string> node_ids;
    for (const AtomicProposition &ap : property.atomic_propositions) {
        ap_roles[ap.ap_id].insert(ap.roles.begin(), ap.roles.end());
        for (const RoleSelectorGroup &group : ap.role_selector_groups) {
            role_groups[{ap.ap_id, group.role}][group.group_id] =
                std::set<std::string>(
                    group.selector_ids.begin(), group.selector_ids.end());
        }
    }
    for (const Selector &selector : property.selectors) {
        selector_ids.insert(selector.selector_id);
    }
    for (const SemanticNode &node : index.nodes) {
        node_ids.insert(node.node_id);
    }
    std::set<std::pair<std::string, ApRole>> seen_roles;
    std::set<std::string> candidate_ids;
    std::set<std::string> evidence_ids;
    for (const ApRoleBinding &binding : bindings.bindings) {
        const auto ap = ap_roles.find(binding.ap_id);
        if (ap == ap_roles.end()) {
            errors.push_back("binding references unknown AP: " + binding.ap_id);
        } else if (!ap->second.contains(binding.role)) {
            errors.push_back("binding role is not declared by AP: " + binding.ap_id);
        }
        if (!seen_roles.insert({binding.ap_id, binding.role}).second) {
            errors.push_back("duplicate AP role binding: " + binding.ap_id);
        }
        std::size_t confirmed = 0;
        std::map<std::string, std::size_t> confirmed_by_group;
        std::map<std::string, std::size_t> candidate_by_group;
        std::set<std::string> accounted_groups;
        if (!std::is_sorted(
                binding.candidates.begin(), binding.candidates.end(),
                candidate_precedes)) {
            errors.push_back(
                "binding candidates are not in stable Top-1 order: " +
                binding.ap_id);
        }
        for (const BindingCandidate &candidate : binding.candidates) {
            if (!candidate_ids.insert(candidate.binding_id).second) {
                errors.push_back("duplicate binding candidate ID: " + candidate.binding_id);
            }
            for (const std::string &selector : candidate.selector_ids) {
                if (!selector_ids.contains(selector)) {
                    errors.push_back("candidate references unknown selector: " + selector);
                }
            }
            if (property.schema_version == "1.0.0") {
                if (candidate.selector_group_id) {
                    errors.push_back(
                        "legacy binding candidate contains a selector group ID: " +
                        candidate.binding_id);
                }
            } else {
                if (!candidate.selector_group_id) {
                    errors.push_back(
                        "role-DNF binding candidate lacks selector group ID: " +
                        candidate.binding_id);
                } else {
                    const auto groups = role_groups.find(
                        {binding.ap_id, binding.role});
                    const auto group =
                        groups == role_groups.end()
                            ? std::map<std::string, std::set<std::string>>::const_iterator{}
                            : groups->second.find(*candidate.selector_group_id);
                    if (groups == role_groups.end() ||
                        group == groups->second.end()) {
                        errors.push_back(
                            "candidate references unknown role selector group: " +
                            *candidate.selector_group_id);
                    } else {
                        accounted_groups.insert(*candidate.selector_group_id);
                        const std::set<std::string> observed(
                            candidate.selector_ids.begin(),
                            candidate.selector_ids.end());
                        if (observed != group->second) {
                            errors.push_back(
                                "candidate selector set differs from role selector group: " +
                                candidate.binding_id);
                        }
                        if (candidate.status == CandidateStatus::Confirmed) {
                            ++confirmed_by_group[*candidate.selector_group_id];
                        } else if (candidate.status == CandidateStatus::Candidate) {
                            ++candidate_by_group[*candidate.selector_group_id];
                        }
                    }
                }
            }
            for (const std::string &node : candidate.semantic_node_ids) {
                if (!node_ids.contains(node)) {
                    errors.push_back("candidate references unknown semantic node: " + node);
                }
            }
            if (candidate.status == CandidateStatus::Confirmed) {
                ++confirmed;
                bool semantic_evidence = false;
                for (const BindingEvidence &evidence : candidate.evidence) {
                    if (evidence.kind != "name_similarity" &&
                        evidence.kind != "llm_similarity" &&
                        evidence.certainty != Certainty::Unknown) {
                        semantic_evidence = true;
                    }
                }
                if (!semantic_evidence) {
                    errors.push_back(
                        "confirmed candidate lacks non-similarity semantic evidence: " +
                        candidate.binding_id);
                }
            }
            for (const BindingEvidence &evidence : candidate.evidence) {
                if (!evidence_ids.insert(evidence.evidence_id).second) {
                    errors.push_back(
                        "duplicate binding evidence ID: " +
                        evidence.evidence_id);
                }
            }
        }
        if (property.schema_version == "1.0.0") {
            if (binding.resolution == BindingResolution::Partial) {
                errors.push_back("legacy role binding cannot use PARTIAL resolution");
            }
            if (binding.resolution == BindingResolution::Confirmed &&
                confirmed != 1) {
                errors.push_back(
                    "CONFIRMED role binding must contain exactly one confirmed candidate");
            }
            if (binding.resolution == BindingResolution::Ambiguous &&
                binding.candidates.size() < 2) {
                errors.push_back(
                    "AMBIGUOUS role binding requires at least two candidates");
            }
        } else {
            const auto expected = role_groups.find(
                {binding.ap_id, binding.role});
            const std::size_t expected_groups =
                expected == role_groups.end() ? 0 : expected->second.size();
            if (expected != role_groups.end()) {
                for (const auto &[group_id, selectors_for_group] :
                     expected->second) {
                    (void)selectors_for_group;
                    if (!accounted_groups.contains(group_id)) {
                        errors.push_back(
                            "role-DNF selector group lacks candidate accounting: " +
                            group_id);
                    }
                }
            }
            std::size_t exact_groups = 0;
            bool ambiguous_group = false;
            bool malformed_group = false;
            if (expected != role_groups.end()) {
                for (const auto &[group_id, selectors_for_group] :
                     expected->second) {
                    (void)selectors_for_group;
                    const std::size_t group_confirmed =
                        confirmed_by_group[group_id];
                    const std::size_t group_candidates =
                        candidate_by_group[group_id];
                    if (group_confirmed == 1 && group_candidates == 0) {
                        ++exact_groups;
                    } else if (group_confirmed > 1 ||
                               (group_confirmed > 0 && group_candidates > 0) ||
                               group_candidates == 1) {
                        malformed_group = true;
                    } else if (group_candidates > 1) {
                        ambiguous_group = true;
                    }
                }
            }
            if (malformed_group) {
                errors.push_back(
                    "role-DNF group has an invalid confirmed/candidate status combination");
            }
            const BindingResolution expected_resolution =
                expected_groups > 0 && exact_groups == expected_groups
                    ? BindingResolution::Confirmed
                    : exact_groups > 0
                          ? BindingResolution::Partial
                          : ambiguous_group
                                ? BindingResolution::Ambiguous
                                : BindingResolution::Unresolved;
            if (binding.resolution != expected_resolution) {
                errors.push_back(
                    "role-DNF role resolution disagrees with group accounting: " +
                    binding.ap_id + '/' + role_name(binding.role));
            }
        }
    }
    for (const auto &[ap_id, roles] : ap_roles) {
        for (const ApRole role : roles) {
            if (!seen_roles.contains({ap_id, role})) {
                errors.push_back(
                    "missing AP role binding: " + ap_id + '/' + role_name(role));
            }
        }
    }
    return errors;
}

}  // namespace rift::core
