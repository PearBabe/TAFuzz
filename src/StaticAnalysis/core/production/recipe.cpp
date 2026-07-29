#include "rift/core/recipe.h"

#include <z3++.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <functional>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

namespace rift::core {
namespace {

using boost::multiprecision::cpp_int;

constexpr std::string_view kEncodingVersion =
    "rift-local-truth-change/1.0.0";

bool valid_sha256(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](const char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

template <typename T>
void sort_unique(std::vector<T> &values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
}

bool integer_like(const ValueType &type) {
    return type.kind == ValueKind::Integer ||
           type.kind == ValueKind::Enumeration ||
           type.kind == ValueKind::BitVector ||
           type.kind == ValueKind::Timestamp ||
           type.kind == ValueKind::Duration;
}

bool complete_integer_type(const ValueType &type) {
    return integer_like(type) && type.bit_width && type.is_signed &&
           *type.bit_width > 0 && *type.bit_width <= 4096;
}

bool same_value_type(const ValueType &left, const ValueType &right) {
    return left.kind == right.kind && left.canonical == right.canonical &&
           left.bit_width == right.bit_width &&
           left.is_signed == right.is_signed && left.unit == right.unit;
}

std::string z3_version() {
    unsigned major = 0;
    unsigned minor = 0;
    unsigned build = 0;
    unsigned revision = 0;
    Z3_get_version(&major, &minor, &build, &revision);
    std::ostringstream stream;
    stream << major << '.' << minor << '.' << build;
    if (revision != 0) {
        stream << '.' << revision;
    }
    return stream.str();
}

std::optional<cpp_int> parse_integer(const std::string &value) {
    if (value.empty()) {
        return std::nullopt;
    }
    std::size_t offset = value.front() == '-' || value.front() == '+' ? 1 : 0;
    if (offset == value.size() ||
        !std::all_of(
            value.begin() + static_cast<std::ptrdiff_t>(offset), value.end(),
            [](const char c) { return c >= '0' && c <= '9'; })) {
        return std::nullopt;
    }
    try {
        return cpp_int(value);
    } catch (const std::exception &) {
        return std::nullopt;
    }
}

std::pair<cpp_int, cpp_int> integer_bounds(const ValueType &type) {
    const std::uint32_t width = *type.bit_width;
    const cpp_int power = cpp_int(1) << width;
    if (*type.is_signed) {
        return {-(cpp_int(1) << (width - 1)),
                (cpp_int(1) << (width - 1)) - 1};
    }
    return {0, power - 1};
}

bool integer_fits(const cpp_int &value, const ValueType &type) {
    const auto [minimum, maximum] = integer_bounds(type);
    return value >= minimum && value <= maximum;
}

std::string integer_string(const cpp_int &value) {
    return value.convert_to<std::string>();
}

std::string type_material(const ValueType &type) {
    std::ostringstream stream;
    stream << static_cast<int>(type.kind) << '|' << type.canonical << '|';
    if (type.bit_width) {
        stream << *type.bit_width;
    }
    stream << '|';
    if (type.is_signed) {
        stream << (*type.is_signed ? "signed" : "unsigned");
    }
    stream << '|';
    if (type.unit) {
        stream << *type.unit;
    }
    return stream.str();
}

void append_expression_material(
    std::ostringstream &stream, const ExpressionStructure &expression) {
    stream << expression.node_kind.size() << ':' << expression.node_kind << '|';
    if (expression.operation) {
        stream << expression.operation->size() << ':' << *expression.operation;
    }
    stream << '|' << type_material(expression.value_type) << '|';
    if (expression.referenced_selector_id) {
        stream << expression.referenced_selector_id->size() << ':'
               << *expression.referenced_selector_id;
    }
    stream << '|';
    if (expression.literal) {
        stream << static_cast<int>(expression.literal->kind) << ':'
               << expression.literal->canonical.size() << ':'
               << expression.literal->canonical;
    }
    stream << "|n=" << expression.operands.size() << '{';
    for (const ExpressionStructure &operand : expression.operands) {
        append_expression_material(stream, operand);
    }
    stream << '}';
}

void collect_references(
    const ExpressionStructure &expression, std::set<std::string> &references) {
    if (expression.node_kind == "reference" &&
        expression.referenced_selector_id) {
        references.insert(*expression.referenced_selector_id);
    }
    for (const ExpressionStructure &operand : expression.operands) {
        collect_references(operand, references);
    }
}

bool collect_reference_types(
    const ExpressionStructure &expression,
    std::map<std::string, ValueType> &types,
    std::string &error) {
    if (expression.node_kind == "reference") {
        if (!expression.referenced_selector_id) {
            error = "reference has no selector identity";
            return false;
        }
        const auto [found, inserted] = types.emplace(
            *expression.referenced_selector_id, expression.value_type);
        if (!inserted && !same_value_type(found->second, expression.value_type)) {
            error = "one selector is referenced with inconsistent value types";
            return false;
        }
    }
    for (const ExpressionStructure &operand : expression.operands) {
        if (!collect_reference_types(operand, types, error)) {
            return false;
        }
    }
    return true;
}

bool depends_on(
    const ExpressionStructure &expression, const std::string &selector_id) {
    if (expression.node_kind == "reference" &&
        expression.referenced_selector_id == selector_id) {
        return true;
    }
    return std::any_of(
        expression.operands.begin(), expression.operands.end(),
        [&](const ExpressionStructure &operand) {
            return depends_on(operand, selector_id);
        });
}

const AtomicProposition *find_ap(
    const TypedPropertyIr &property, const std::string &ap_id) {
    const auto found = std::find_if(
        property.atomic_propositions.begin(),
        property.atomic_propositions.end(),
        [&](const AtomicProposition &ap) { return ap.ap_id == ap_id; });
    return found == property.atomic_propositions.end() ? nullptr : &*found;
}

const ExternalAction *find_overlay_action(
    const ModelFactOverlay &overlay, const std::string &action_id) {
    const auto found = std::find_if(
        overlay.external_actions.begin(), overlay.external_actions.end(),
        [&](const ExternalAction &action) {
            return action.external_action_id == action_id;
        });
    return found == overlay.external_actions.end() ? nullptr : &*found;
}

bool same_action_contract(
    const ExternalAction &left, const ExternalAction &right) {
    return left.external_action_id == right.external_action_id &&
           left.action_schema_id == right.action_schema_id &&
           left.action_class == right.action_class &&
           left.channel == right.channel &&
           left.operation == right.operation &&
           same_value_type(left.payload_type, right.payload_type) &&
           left.payload_slot == right.payload_slot &&
           left.scope_schema == right.scope_schema &&
           left.generation_schema == right.generation_schema &&
           left.timing_capability == right.timing_capability &&
           left.required_capability == right.required_capability;
}

const ModelFact *find_model_fact(
    const ModelFactOverlay &overlay, const std::string &fact_id) {
    const auto found = std::find_if(
        overlay.semantic_facts.begin(), overlay.semantic_facts.end(),
        [&](const ModelFact &fact) { return fact.fact_id == fact_id; });
    return found == overlay.semantic_facts.end() ? nullptr : &*found;
}

bool value_capable_relation(RelationKind kind) {
    switch (kind) {
        case RelationKind::Defines:
        case RelationKind::Uses:
        case RelationKind::Loads:
        case RelationKind::Stores:
        case RelationKind::Data:
        case RelationKind::Call:
        case RelationKind::Return:
        case RelationKind::Object:
        case RelationKind::Field:
        case RelationKind::Alias:
        case RelationKind::MapsTo:
            return true;
        case RelationKind::Control:
        case RelationKind::Contains:
        case RelationKind::Unknown:
            return false;
    }
    return false;
}

bool identity_capable_relation(RelationKind kind) {
    return value_capable_relation(kind) && kind != RelationKind::Data;
}

struct ValuePathArc {
    std::string source;
    std::string target;
    bool identity_preserving = false;
    bool modelled = false;
    std::string stable_key;
};

struct ActionValuePath {
    std::string attachment_id;
    std::string boundary_node_id;
    std::string target_node_id;
    bool identity_preserving = false;
    bool modelled = false;
};

bool exact_value_type_match(const ValueType &left, const ValueType &right) {
    return left.kind == right.kind && left.canonical == right.canonical &&
           left.bit_width == right.bit_width &&
           left.is_signed == right.is_signed && left.unit == right.unit;
}

bool typed_identity_transfer(
    const std::optional<ModelValueTransferV2> &transfer) {
    if (!transfer) return false;
    if (transfer->kind == ModelValueTransferKind::Identity) return true;
    if (transfer->kind == ModelValueTransferKind::Affine) {
        return transfer->affine_scale == std::optional<std::int64_t>{1} &&
               transfer->affine_offset == std::optional<std::int64_t>{0} &&
               transfer->precondition == ModelValuePrecondition::None &&
               !transfer->executor_enforces_precondition &&
               !transfer->failure_branch_unknown;
    }
    return transfer->kind ==
               ModelValueTransferKind::ParseIdentityWithPrecondition &&
           transfer->precondition ==
               ModelValuePrecondition::CanonicalDecimalIntegerInRange &&
           transfer->executor_enforces_precondition &&
           transfer->failure_branch_unknown;
}

std::vector<ActionValuePath> find_action_value_paths(
    const FrontierCandidate &candidate,
    const std::set<std::string> &targets,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay) {
    std::vector<ActionValuePath> results;
    std::unordered_map<std::string, const ContextualNode *> nodes;
    std::map<std::string, std::vector<const ContextualNode *>> by_semantic;
    for (const ContextualNode &node : graph.nodes) {
        nodes[node.node_id] = &node;
        by_semantic[node.semantic_node_id].push_back(&node);
    }
    for (auto &[semantic, instances] : by_semantic) {
        (void)semantic;
        std::sort(
            instances.begin(), instances.end(),
            [](const ContextualNode *left, const ContextualNode *right) {
                return left->node_id < right->node_id;
            });
    }
    std::unordered_map<std::string, std::vector<ValuePathArc>> outgoing;
    for (const InfluenceEdge &edge : graph.edges) {
        if (edge.certainty == Certainty::Unknown ||
            !value_capable_relation(edge.kind)) {
            continue;
        }
        const auto source = nodes.find(edge.source_node_id);
        const auto target = nodes.find(edge.target_node_id);
        if (source == nodes.end() || target == nodes.end() ||
            evaluate_contextual_compatibility(
                *source->second, *target->second, edge.kind)
                    .verdict != WitnessCompatibility::Compatible) {
            continue;
        }
        outgoing[edge.source_node_id].push_back({
            edge.source_node_id, edge.target_node_id,
            identity_capable_relation(edge.kind) &&
                exact_value_type_match(
                    source->second->value_type, target->second->value_type),
            edge.certainty == Certainty::Modelled,
            "G:" + edge.edge_id});
    }
    const std::set<std::string> supported_fact_ids(
        candidate.evidence.model_provenance.model_fact_ids.begin(),
        candidate.evidence.model_provenance.model_fact_ids.end());
    for (const ModelFact &fact : overlay.semantic_facts) {
        if ((!supported_fact_ids.empty() &&
             !supported_fact_ids.contains(fact.fact_id)) ||
            !fact.target_semantic_node_id ||
            fact.certainty == Certainty::Unknown ||
            (fact.kind != ModelFactKind::SemanticTransfer &&
             fact.kind != ModelFactKind::PersistenceTransition)) {
            continue;
        }
        const auto sources = by_semantic.find(fact.source_semantic_node_id);
        const auto target_instances =
            by_semantic.find(*fact.target_semantic_node_id);
        if (sources == by_semantic.end() ||
            target_instances == by_semantic.end()) {
            continue;
        }
        for (const ContextualNode *source : sources->second) {
            for (const ContextualNode *target : target_instances->second) {
                if (evaluate_contextual_compatibility(
                        *source, *target, RelationKind::MapsTo)
                        .verdict != WitnessCompatibility::Compatible) {
                    continue;
                }
                outgoing[source->node_id].push_back({
                    source->node_id, target->node_id,
                    typed_identity_transfer(fact.value_transfer) &&
                        exact_value_type_match(
                            source->value_type, target->value_type),
                    true, "M:" + fact.fact_id + ":" + source->node_id +
                              ":" + target->node_id});
            }
        }
    }
    for (auto &[source, arcs] : outgoing) {
        (void)source;
        std::sort(
            arcs.begin(), arcs.end(),
            [](const ValuePathArc &left, const ValuePathArc &right) {
                return std::tie(
                           left.stable_key, left.source, left.target,
                           left.identity_preserving, left.modelled) <
                       std::tie(
                           right.stable_key, right.source, right.target,
                           right.identity_preserving, right.modelled);
            });
    }
    std::vector<const BoundaryAttachment *> attachments;
    for (const BoundaryAttachment &attachment :
         overlay.boundary_attachments) {
        if (attachment.external_action_id ==
            candidate.action.external_action_id) {
            attachments.push_back(&attachment);
        }
    }
    std::sort(
        attachments.begin(), attachments.end(),
        [](const BoundaryAttachment *left,
           const BoundaryAttachment *right) {
            return left->attachment_id < right->attachment_id;
        });
    struct State {
        std::string node;
        bool identity = false;
        bool modelled = false;
    };
    for (const BoundaryAttachment *attachment : attachments) {
        if (attachment->certainty == Certainty::Unknown) {
            continue;
        }
        const auto boundaries = by_semantic.find(
            attachment->semantic_node_id);
        if (boundaries == by_semantic.end()) {
            continue;
        }
        for (const ContextualNode *boundary : boundaries->second) {
            const bool attachment_identity =
                typed_identity_transfer(attachment->value_transfer) &&
                exact_value_type_match(
                    candidate.action.payload_type, boundary->value_type);
            std::vector<State> worklist{{
                boundary->node_id, attachment_identity,
                attachment->certainty == Certainty::Modelled}};
            std::set<std::tuple<std::string, bool, bool>> seen;
            seen.emplace(
                boundary->node_id, attachment_identity,
                attachment->certainty == Certainty::Modelled);
            for (std::size_t cursor = 0; cursor < worklist.size(); ++cursor) {
                const State state = worklist[cursor];
                if (targets.contains(state.node)) {
                    results.push_back({
                        attachment->attachment_id, boundary->node_id,
                        state.node, state.identity, state.modelled});
                }
                const auto arcs = outgoing.find(state.node);
                if (arcs == outgoing.end()) {
                    continue;
                }
                for (const ValuePathArc &arc : arcs->second) {
                    const State next{
                        arc.target,
                        state.identity && arc.identity_preserving,
                        state.modelled || arc.modelled};
                    const auto key = std::make_tuple(
                        next.node, next.identity, next.modelled);
                    if (seen.insert(key).second) {
                        worklist.push_back(next);
                    }
                }
            }
        }
    }
    std::sort(
        results.begin(), results.end(),
        [](const ActionValuePath &left, const ActionValuePath &right) {
            return std::tie(
                       left.attachment_id, left.boundary_node_id,
                       left.target_node_id, left.identity_preserving,
                       left.modelled) <
                   std::tie(
                       right.attachment_id, right.boundary_node_id,
                       right.target_node_id, right.identity_preserving,
                       right.modelled);
        });
    results.erase(
        std::unique(
            results.begin(), results.end(),
            [](const ActionValuePath &left, const ActionValuePath &right) {
                return std::tie(
                           left.attachment_id, left.boundary_node_id,
                           left.target_node_id, left.identity_preserving,
                           left.modelled) ==
                       std::tie(
                           right.attachment_id, right.boundary_node_id,
                           right.target_node_id, right.identity_preserving,
                           right.modelled);
            }),
        results.end());
    return results;
}

const BindingCandidate *find_binding_candidate(
    const ApBindings &bindings, const std::string &binding_id) {
    for (const ApRoleBinding &role : bindings.bindings) {
        for (const BindingCandidate &candidate : role.candidates) {
            if (candidate.binding_id == binding_id) {
                return &candidate;
            }
        }
    }
    return nullptr;
}

const ApRoleBinding *find_binding_role(
    const ApBindings &bindings, const std::string &binding_id) {
    for (const ApRoleBinding &role : bindings.bindings) {
        const auto candidate = std::find_if(
            role.candidates.begin(), role.candidates.end(),
            [&](const BindingCandidate &value) {
                return value.binding_id == binding_id;
            });
        if (candidate != role.candidates.end()) {
            return &role;
        }
    }
    return nullptr;
}

struct ValueBindingResult {
    std::optional<std::string> selector_id;
    std::vector<PayloadProjectionTargetRequest> projection_targets;
    std::vector<std::string> witness_ids;
    std::vector<std::string> potential_selector_ids;
    std::vector<std::string> reasons;
};

ValueBindingResult bind_action_to_predicate_reference(
    const FrontierCandidate &candidate,
    const AtomicProposition &ap,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences) {
    ValueBindingResult result;
    const auto cone = std::find_if(
        cones.cones.begin(), cones.cones.end(),
        [&](const ApInfluenceCone &value) {
            return value.cone_id == candidate.cone_id &&
                   value.ap_id == candidate.ap_id;
        });
    if (cone == cones.cones.end()) {
        result.reasons.push_back(
            "frontier cone is absent from the certificate-bound cone artifact");
        return result;
    }
    std::set<std::string> predicate_references;
    collect_references(ap.predicate, predicate_references);
    if (predicate_references.empty()) {
        result.reasons.push_back("predicate contains no selector reference");
        return result;
    }
    std::set<std::pair<std::string, std::string>> occurrence_accounts;
    std::set<std::pair<std::string, std::string>> exact_accounts;
    for (const PredicateSelectorAccount &account :
         predicate_occurrences.selector_accounts) {
        if (account.ap_id != ap.ap_id ||
            !predicate_references.contains(account.selector_id)) {
            continue;
        }
        occurrence_accounts.emplace(account.ap_id, account.selector_id);
        if (account.resolution == PredicateOccurrenceResolution::Exact) {
            exact_accounts.emplace(account.ap_id, account.selector_id);
        }
    }
    const bool occurrence_governed = !occurrence_accounts.empty();
    std::map<std::string, std::vector<std::string>> root_selectors;
    std::map<std::string, std::vector<std::string>> root_potential_selectors;
    std::set<std::string> confirmed_ap_site_roots;
    for (const CandidateAccount &account : cone->candidate_accounting) {
        if (account.disposition != CandidateDisposition::Included) {
            continue;
        }
        const BindingCandidate *binding =
            find_binding_candidate(bindings, account.binding_id);
        if (binding == nullptr ||
            binding->status != CandidateStatus::Confirmed) {
            continue;
        }
        const ApRoleBinding *role =
            find_binding_role(bindings, account.binding_id);
        for (const std::string &root : account.root_node_ids) {
            std::vector<std::string> &selectors = root_selectors[root];
            std::vector<std::string> &potential =
                root_potential_selectors[root];
            for (const std::string &selector : binding->selector_ids) {
                if (predicate_references.contains(selector)) {
                    potential.push_back(selector);
                }
                // A source occurrence account is authoritative for predicate
                // operands.  Legacy M4 range binding may conservatively bind
                // an enclosing declaration; keeping it in the cone is sound,
                // but it must not override an EXACT/UNKNOWN occurrence result.
                if (predicate_references.contains(selector) &&
                    occurrence_accounts.contains({ap.ap_id, selector})) {
                    continue;
                }
                selectors.push_back(selector);
            }
            sort_unique(selectors);
            sort_unique(potential);
            // A Guard binding denotes the confirmed AP evaluation site.  It
            // need not carry the selector of an operand referenced inside the
            // predicate (a source-location selector is the common case).
            if (role != nullptr && role->role == ApRole::Guard) {
                confirmed_ap_site_roots.insert(root);
            }
        }
    }
    // Predicate occurrences are an additive M5 sidecar.  They map the exact
    // DeclRefExpr/MemberExpr token selected by the typed predicate back to an
    // existing M4 semantic identity without changing the immutable M4 graph.
    // Expand that identity into every contextual instance; the cone-bound
    // value-path check below selects only the compatible instance.
    for (const PredicateOccurrence &occurrence :
         predicate_occurrences.occurrences) {
        if (occurrence.ap_id != ap.ap_id ||
            !exact_accounts.contains(
                {occurrence.ap_id, occurrence.selector_id}) ||
            occurrence.resolution != PredicateOccurrenceResolution::Exact ||
            occurrence.certainty != Certainty::Must) {
            continue;
        }
        for (const std::string &semantic_node_id :
             occurrence.semantic_node_ids) {
            for (const ContextualNode &node : graph.nodes) {
                if (node.semantic_node_id != semantic_node_id) {
                    continue;
                }
                std::vector<std::string> &selectors =
                    root_selectors[node.node_id];
                selectors.push_back(occurrence.selector_id);
                sort_unique(selectors);
            }
        }
    }
    if (root_selectors.empty()) {
        result.reasons.push_back(
            "cone has no confirmed binding root with selector provenance");
        return result;
    }

    std::set<std::string> mapped_selectors;
    std::map<std::string, std::set<std::string>> selector_target_nodes;
    std::set<std::string> potential_mapped_selectors;
    std::vector<std::string> ap_site_witness_ids;
    std::set<std::string> target_roots;
    for (const auto &[root, selectors] : root_selectors) {
        (void)selectors;
        target_roots.insert(root);
    }
    const std::vector<ActionValuePath> value_paths =
        find_action_value_paths(candidate, target_roots, graph, overlay);
    for (const ActionValuePath &path : value_paths) {
        const auto selected_root = root_selectors.find(path.target_node_id);
        if (selected_root == root_selectors.end()) {
            continue;
        }
        const auto potential_root =
            root_potential_selectors.find(path.target_node_id);
        std::vector<std::string> matching_witness_ids;
        for (const FrontierWitness &witness : candidate.witnesses) {
            if (witness.attachment_id == path.attachment_id &&
                witness.boundary_node_id == path.boundary_node_id &&
                witness.compatibility == WitnessCompatibility::Compatible &&
                (witness.reachability ==
                     ReachabilityVerdict::StaticWitness ||
                 witness.reachability ==
                     ReachabilityVerdict::ModelledWitness)) {
                matching_witness_ids.push_back(witness.witness_id);
            }
        }
        if (matching_witness_ids.empty()) {
            continue;
        }
        if (confirmed_ap_site_roots.contains(path.target_node_id)) {
            ap_site_witness_ids.insert(
                ap_site_witness_ids.end(), matching_witness_ids.begin(),
                matching_witness_ids.end());
        }
        bool root_intersects = false;
        for (const std::string &selector : selected_root->second) {
            if (predicate_references.contains(selector)) {
                mapped_selectors.insert(selector);
                selector_target_nodes[selector].insert(path.target_node_id);
                root_intersects = true;
            }
        }
        if (root_intersects) {
            result.witness_ids.insert(
                result.witness_ids.end(), matching_witness_ids.begin(),
                matching_witness_ids.end());
        }
        if (potential_root != root_potential_selectors.end()) {
            potential_mapped_selectors.insert(
                potential_root->second.begin(),
                potential_root->second.end());
        }
    }
    sort_unique(result.witness_ids);
    result.potential_selector_ids.assign(
        potential_mapped_selectors.begin(),
        potential_mapped_selectors.end());
    if (mapped_selectors.size() == 1) {
        result.selector_id = *mapped_selectors.begin();
        const auto target_nodes = selector_target_nodes.find(
            *result.selector_id);
        if (target_nodes != selector_target_nodes.end()) {
            PayloadProjectionTargetRequest target;
            target.selector_id = *result.selector_id;
            target.contextual_node_ids.assign(
                target_nodes->second.begin(), target_nodes->second.end());
            result.projection_targets.push_back(std::move(target));
        }
    } else if (mapped_selectors.empty() &&
               predicate_references.size() == 1 &&
               !occurrence_governed &&
               !ap_site_witness_ids.empty()) {
        // A value-capable path to a confirmed AP evaluation site proves that
        // the action reaches the predicate result.  If the predicate has one
        // and only one referenced selector, that selector is the unique
        // operand the path can denote.  With two references this inference is
        // intentionally withheld because observed-state and dynamic-bound
        // roles would otherwise be conflated.
        result.selector_id = *predicate_references.begin();
        result.witness_ids = std::move(ap_site_witness_ids);
        sort_unique(result.witness_ids);
    } else if (mapped_selectors.empty()) {
        result.reasons.push_back(
            occurrence_governed
                ? "exact predicate-occurrence accounts do not have a compatible value path"
                : !ap_site_witness_ids.empty() && predicate_references.size() > 1
                ? "value-capable witness reaches a confirmed AP site but the predicate has multiple reference selectors"
                : "no compatible value-capable witness reaches a confirmed predicate selector root");
    } else {
        result.reasons.push_back(
            "value-capable witnesses map the action to multiple predicate selectors");
    }
    if (result.selector_id) {
        result.potential_selector_ids.push_back(*result.selector_id);
        sort_unique(result.potential_selector_ids);
    }
    if (!result.projection_targets.empty() &&
        result.projection_targets.front().contextual_node_ids.size() != 1) {
        result.reasons.push_back(
            "predicate selector maps to multiple contextual target instances");
    }
    return result;
}

std::string expression_query_digest(
    const FrontierCandidate &candidate,
    const ExpressionStructure &predicate,
    const std::string &selector_id,
    const std::string &purpose) {
    std::ostringstream material;
    material << kEncodingVersion << '|'
             << candidate.candidate_id << '|'
             << candidate.action.external_action_id << '|'
             << selector_id << '|' << purpose << '|';
    append_expression_material(material, predicate);
    return sha256_hex(material.str());
}

struct EncodeFailure : std::runtime_error {
    using std::runtime_error::runtime_error;
};

ExpressionStructure expression_reference(
    std::string selector_id, const ValueType &type) {
    ExpressionStructure result;
    result.node_kind = "reference";
    result.value_type = type;
    result.referenced_selector_id = std::move(selector_id);
    return result;
}

ExpressionStructure expression_literal(
    LiteralKind kind, std::string value, const ValueType &type) {
    ExpressionStructure result;
    result.node_kind = "literal";
    result.value_type = type;
    result.literal = LiteralValue{kind, std::move(value)};
    return result;
}

ExpressionStructure expression_cast(
    ExpressionStructure operand, const ValueType &type) {
    if (same_value_type(operand.value_type, type)) return operand;
    ExpressionStructure result;
    result.node_kind = "cast";
    result.operation = "integral_cast";
    result.value_type = type;
    result.operands.push_back(std::move(operand));
    return result;
}

ExpressionStructure expression_unary(
    std::string operation, ExpressionStructure operand,
    const ValueType &type) {
    ExpressionStructure result;
    result.node_kind = "unary";
    result.operation = std::move(operation);
    result.value_type = type;
    result.operands.push_back(std::move(operand));
    return result;
}

ExpressionStructure expression_binary(
    std::string node_kind, std::string operation,
    ExpressionStructure left, ExpressionStructure right,
    const ValueType &type) {
    ExpressionStructure result;
    result.node_kind = std::move(node_kind);
    result.operation = std::move(operation);
    result.value_type = type;
    result.operands = {std::move(left), std::move(right)};
    return result;
}

class TransferExpressionConverter {
  public:
    explicit TransferExpressionConverter(
        const ExternalPayloadProjection &projection)
        : projection_(projection) {
        for (const TransferExpression &expression : projection.expressions) {
            expressions_.emplace(expression.expression_id, &expression);
        }
    }

    ExpressionStructure convert(const std::string &expression_id) {
        const auto memoized = memo_.find(expression_id);
        if (memoized != memo_.end()) return memoized->second;
        if (!active_.insert(expression_id).second) {
            throw EncodeFailure("payload transfer expression graph contains a cycle");
        }
        const auto found = expressions_.find(expression_id);
        if (found == expressions_.end()) {
            active_.erase(expression_id);
            throw EncodeFailure("payload projection references a missing transfer expression");
        }
        ExpressionStructure result = convert_node(*found->second);
        active_.erase(expression_id);
        memo_.emplace(expression_id, result);
        return result;
    }

  private:
    std::vector<ExpressionStructure> operands(
        const TransferExpression &expression) {
        std::vector<ExpressionStructure> result;
        result.reserve(expression.operand_expression_ids.size());
        for (const std::string &operand : expression.operand_expression_ids) {
            result.push_back(convert(operand));
        }
        return result;
    }

    ExpressionStructure convert_input(const TransferExpression &expression) {
        if (!expression.input ||
            !same_value_type(
                expression.value_type, expression.input->value_type)) {
            throw EncodeFailure("payload projection input type is incomplete");
        }
        switch (expression.input->domain) {
        case TransferSymbolDomain::ExternalActionPayload:
            if (expression.input->symbol_id !=
                projection_.coordinate.coordinate_id) {
                throw EncodeFailure(
                    "payload projection contains a second external coordinate");
            }
            return expression_reference(
                projection_.coordinate.coordinate_id, expression.value_type);
        case TransferSymbolDomain::ContextualNode:
            return expression_reference(
                "shared-context:" + expression.input->symbol_id,
                expression.value_type);
        case TransferSymbolDomain::SemanticNode:
        case TransferSymbolDomain::Unknown:
            throw EncodeFailure(
                "payload projection input is not contextual or external");
        }
        throw EncodeFailure("payload projection input domain is unsupported");
    }

    ExpressionStructure convert_literal(
        const TransferExpression &expression) {
        if (!expression.literal) {
            throw EncodeFailure("payload projection literal is absent");
        }
        switch (expression.literal->kind) {
        case TransferLiteralKind::Boolean:
            return expression_literal(
                LiteralKind::Boolean, expression.literal->canonical_value,
                expression.value_type);
        case TransferLiteralKind::Integer:
        case TransferLiteralKind::Enumeration:
        case TransferLiteralKind::BitVector:
            return expression_literal(
                LiteralKind::Integer, expression.literal->canonical_value,
                expression.value_type);
        case TransferLiteralKind::Floating:
        case TransferLiteralKind::Unknown:
            throw EncodeFailure(
                "floating or UNKNOWN payload projection literal is unsupported");
        }
        throw EncodeFailure("payload projection literal kind is unsupported");
    }

    ExpressionStructure convert_passthrough(
        const TransferExpression &expression) {
        std::vector<ExpressionStructure> values = operands(expression);
        if (values.size() != 1) {
            throw EncodeFailure(
                "value-preserving payload transfer does not have one operand");
        }
        return expression_cast(std::move(values.front()), expression.value_type);
    }

    ExpressionStructure convert_affine(
        const TransferExpression &expression) {
        if (!complete_integer_type(expression.value_type) ||
            expression.operand_expression_ids.size() !=
                expression.affine_coefficients.size() ||
            !expression.affine_offset) {
            throw EncodeFailure("payload affine transfer is incomplete");
        }
        std::vector<ExpressionStructure> values = operands(expression);
        std::optional<ExpressionStructure> result;
        for (std::size_t index = 0; index < values.size(); ++index) {
            const std::optional<cpp_int> coefficient =
                parse_integer(expression.affine_coefficients[index]);
            if (!coefficient ||
                !integer_fits(*coefficient, expression.value_type)) {
                throw EncodeFailure(
                    "payload affine coefficient is outside its typed domain");
            }
            if (*coefficient == 0) continue;
            ExpressionStructure term = expression_cast(
                std::move(values[index]), expression.value_type);
            if (*coefficient != 1) {
                term = expression_binary(
                    "binary", "*", std::move(term),
                    expression_literal(
                        LiteralKind::Integer, integer_string(*coefficient),
                        expression.value_type),
                    expression.value_type);
            }
            result = result
                         ? std::optional<ExpressionStructure>{expression_binary(
                               "binary", "+", std::move(*result),
                               std::move(term), expression.value_type)}
                         : std::optional<ExpressionStructure>{std::move(term)};
        }
        const std::optional<cpp_int> offset =
            parse_integer(*expression.affine_offset);
        if (!offset || !integer_fits(*offset, expression.value_type)) {
            throw EncodeFailure(
                "payload affine offset is outside its typed domain");
        }
        if (!result || *offset != 0) {
            ExpressionStructure literal = expression_literal(
                LiteralKind::Integer, integer_string(*offset),
                expression.value_type);
            result = result
                         ? std::optional<ExpressionStructure>{expression_binary(
                               "binary", "+", std::move(*result),
                               std::move(literal), expression.value_type)}
                         : std::optional<ExpressionStructure>{std::move(literal)};
        }
        return std::move(*result);
    }

    ExpressionStructure convert_compare(
        const TransferExpression &expression) {
        if (!expression.compare_operation) {
            throw EncodeFailure("payload comparison operation is absent");
        }
        std::vector<ExpressionStructure> values = operands(expression);
        if (values.size() != 2) {
            throw EncodeFailure("payload comparison is not binary");
        }
        const char *operation = nullptr;
        switch (*expression.compare_operation) {
        case CompareOperation::Eq: operation = "=="; break;
        case CompareOperation::Ne: operation = "!="; break;
        case CompareOperation::Lt: operation = "<"; break;
        case CompareOperation::Le: operation = "<="; break;
        case CompareOperation::Gt: operation = ">"; break;
        case CompareOperation::Ge: operation = ">="; break;
        }
        return expression_binary(
            "comparison", operation, std::move(values[0]),
            std::move(values[1]), expression.value_type);
    }

    ExpressionStructure convert_boolean(
        const TransferExpression &expression) {
        if (!expression.boolean_operation) {
            throw EncodeFailure("payload Boolean operation is absent");
        }
        std::vector<ExpressionStructure> values = operands(expression);
        if (*expression.boolean_operation == BooleanOperation::Not) {
            if (values.size() != 1) {
                throw EncodeFailure("payload Boolean NOT is not unary");
            }
            return expression_unary(
                "!", std::move(values.front()), expression.value_type);
        }
        if (values.size() != 2) {
            throw EncodeFailure("payload Boolean operation is not binary");
        }
        const char *operation = nullptr;
        switch (*expression.boolean_operation) {
        case BooleanOperation::Not: break;
        case BooleanOperation::And: operation = "&&"; break;
        case BooleanOperation::Or: operation = "||"; break;
        case BooleanOperation::Xor: operation = "xor"; break;
        }
        return expression_binary(
            "boolean", operation, std::move(values[0]),
            std::move(values[1]), expression.value_type);
    }

    ExpressionStructure convert_node(const TransferExpression &expression) {
        switch (expression.kind) {
        case TransferExprKind::Input:
            return convert_input(expression);
        case TransferExprKind::Literal:
            return convert_literal(expression);
        case TransferExprKind::Identity:
        case TransferExprKind::Parse:
        case TransferExprKind::Load:
        case TransferExprKind::Store:
        case TransferExprKind::CallArg:
        case TransferExprKind::Return:
            return convert_passthrough(expression);
        case TransferExprKind::Cast: {
            if (!expression.cast_operation ||
                *expression.cast_operation == CastOperation::Unknown) {
                throw EncodeFailure("payload cast operation is UNKNOWN");
            }
            return convert_passthrough(expression);
        }
        case TransferExprKind::Affine:
            return convert_affine(expression);
        case TransferExprKind::Compare:
            return convert_compare(expression);
        case TransferExprKind::Boolean:
            return convert_boolean(expression);
        case TransferExprKind::Select:
        case TransferExprKind::Phi:
        case TransferExprKind::Definedness:
        case TransferExprKind::Unknown:
            throw EncodeFailure(
                "payload transfer kind is not in the executable SMT subset");
        }
        throw EncodeFailure("payload transfer kind is unsupported");
    }

    const ExternalPayloadProjection &projection_;
    std::unordered_map<std::string, const TransferExpression *> expressions_;
    std::unordered_map<std::string, ExpressionStructure> memo_;
    std::unordered_set<std::string> active_;
};

ExpressionStructure substitute_selector(
    const ExpressionStructure &expression, const std::string &selector_id,
    const ExpressionStructure &replacement, std::size_t &replacements) {
    if (expression.node_kind == "reference" &&
        expression.referenced_selector_id == selector_id) {
        if (!same_value_type(expression.value_type, replacement.value_type)) {
            throw EncodeFailure(
                "predicate operand and payload projection types differ");
        }
        ++replacements;
        return replacement;
    }
    ExpressionStructure result = expression;
    result.operands.clear();
    result.operands.reserve(expression.operands.size());
    for (const ExpressionStructure &operand : expression.operands) {
        result.operands.push_back(substitute_selector(
            operand, selector_id, replacement, replacements));
    }
    return result;
}

struct PayloadPredicateRewrite {
    std::optional<ExpressionStructure> predicate;
    std::string payload_selector_id;
    bool identity_projection = false;
    std::vector<std::string> reasons;
};

PayloadPredicateRewrite rewrite_predicate_in_payload_coordinate(
    const ExpressionStructure &predicate, const std::string &selector_id,
    const ExternalPayloadProjection &projection) {
    PayloadPredicateRewrite result;
    result.payload_selector_id = projection.coordinate.coordinate_id;
    if (projection.status != PayloadProjectionStatus::Exact) {
        result.reasons = projection.uncertainty_reasons;
        if (result.reasons.empty()) {
            result.reasons.push_back("external payload projection is not EXACT");
        }
        return result;
    }
    const auto target = std::find_if(
        projection.targets.begin(), projection.targets.end(),
        [&](const PayloadProjectedTarget &candidate) {
            return candidate.selector_id == selector_id;
        });
    if (target == projection.targets.end() ||
        target->status != PayloadProjectionStatus::Exact ||
        target->value_expression_id.empty()) {
        result.reasons.push_back(
            "payload projection has no exact target for the predicate selector");
        return result;
    }
    try {
        TransferExpressionConverter converter(projection);
        const ExpressionStructure projected_value =
            converter.convert(target->value_expression_id);
        std::size_t replacements = 0;
        result.predicate = substitute_selector(
            predicate, selector_id, projected_value, replacements);
        if (replacements == 0) {
            result.predicate.reset();
            result.reasons.push_back(
                "predicate selector does not occur in the AP expression");
            return result;
        }
        result.identity_projection =
            projected_value.node_kind == "reference" &&
            projected_value.referenced_selector_id == result.payload_selector_id &&
            same_value_type(
                projected_value.value_type, projection.coordinate.value_type);
    } catch (const EncodeFailure &failure) {
        result.reasons.push_back(failure.what());
    }
    return result;
}

struct EncodedValue {
    z3::expr value;
    ValueType type;
    bool is_boolean = false;
    std::vector<z3::expr> defined;

    EncodedValue(z3::expr value, ValueType type, bool is_boolean)
        : value(std::move(value)), type(std::move(type)),
          is_boolean(is_boolean) {}
};

class ExpressionEncoder {
  public:
    ExpressionEncoder(
        z3::context &context, std::string selector_id,
        ValueType storage_type, z3::expr input,
        const std::map<std::string, z3::expr> &shared_state)
        : context_(context), shared_state_(shared_state) {
        target_inputs_.emplace(selector_id, std::move(input));
        target_types_.emplace(
            std::move(selector_id), std::move(storage_type));
    }

    ExpressionEncoder(
        z3::context &context,
        const std::map<std::string, z3::expr> &target_inputs,
        const std::map<std::string, ValueType> &target_types,
        const std::map<std::string, z3::expr> &shared_state)
        : context_(context), target_inputs_(target_inputs),
          target_types_(target_types), shared_state_(shared_state) {}

    EncodedValue encode(const ExpressionStructure &expression) {
        if (expression.node_kind == "reference") {
            if (!expression.referenced_selector_id) {
                throw EncodeFailure("reference has no selector identity");
            }
            const auto target = target_inputs_.find(
                *expression.referenced_selector_id);
            if (target != target_inputs_.end()) {
                const auto type = target_types_.find(
                    *expression.referenced_selector_id);
                if (type == target_types_.end() ||
                    !same_value_type(expression.value_type, type->second)) {
                    throw EncodeFailure(
                        "target reference type differs from external payload type");
                }
                return EncodedValue(
                    target->second, expression.value_type,
                    expression.value_type.kind == ValueKind::Boolean);
            }
            const auto shared = shared_state_.find(
                *expression.referenced_selector_id);
            if (shared == shared_state_.end()) {
                throw EncodeFailure("non-target reference has no shared-state binding");
            }
            return EncodedValue(
                shared->second, expression.value_type,
                expression.value_type.kind == ValueKind::Boolean);
        }
        if (expression.node_kind == "literal") {
            return encode_literal(expression);
        }
        if (expression.node_kind == "cast") {
            if (expression.operands.size() != 1) {
                throw EncodeFailure("cast does not have exactly one operand");
            }
            EncodedValue operand = encode(expression.operands.front());
            return encode_cast(std::move(operand), expression.value_type);
        }
        if (expression.node_kind == "unary") {
            return encode_unary(expression);
        }
        if (expression.node_kind == "binary") {
            return encode_binary(expression);
        }
        if (expression.node_kind == "comparison") {
            return encode_comparison(expression);
        }
        if (expression.node_kind == "boolean") {
            return encode_boolean(expression);
        }
        throw EncodeFailure(
            "unsupported expression node kind: " + expression.node_kind);
    }

  private:
    EncodedValue encode_literal(const ExpressionStructure &expression) {
        if (!expression.literal) {
            throw EncodeFailure("literal node has no retained scalar literal");
        }
        if (expression.value_type.kind == ValueKind::Boolean) {
            if (expression.literal->kind != LiteralKind::Boolean ||
                (expression.literal->canonical != "true" &&
                 expression.literal->canonical != "false")) {
                throw EncodeFailure("Boolean literal/type mismatch");
            }
            return EncodedValue(
                context_.bool_val(expression.literal->canonical == "true"),
                expression.value_type, true);
        }
        if (!complete_integer_type(expression.value_type) ||
            expression.literal->kind != LiteralKind::Integer) {
            throw EncodeFailure(
                "only fully typed integer/enum/bit-vector literals are supported");
        }
        const std::optional<cpp_int> value =
            parse_integer(expression.literal->canonical);
        if (!value || !integer_fits(*value, expression.value_type)) {
            throw EncodeFailure("integer literal is outside its declared type");
        }
        return EncodedValue(
            context_.bv_val(
                expression.literal->canonical.c_str(),
                *expression.value_type.bit_width),
            expression.value_type, false);
    }

    EncodedValue encode_cast(EncodedValue operand, const ValueType &target) {
        if (operand.is_boolean) {
            if (target.kind == ValueKind::Boolean) {
                operand.type = target;
                return operand;
            }
            if (!complete_integer_type(target)) {
                throw EncodeFailure("unsupported Boolean cast target");
            }
            EncodedValue result(
                z3::ite(
                    operand.value,
                    context_.bv_val(1U, *target.bit_width),
                    context_.bv_val(0U, *target.bit_width)),
                target, false);
            result.defined = std::move(operand.defined);
            return result;
        }
        if (target.kind == ValueKind::Boolean) {
            if (!complete_integer_type(operand.type)) {
                throw EncodeFailure("unsupported cast to Boolean");
            }
            EncodedValue result(
                operand.value !=
                    context_.bv_val(0U, *operand.type.bit_width),
                target, true);
            result.defined = std::move(operand.defined);
            return result;
        }
        if (!complete_integer_type(operand.type) ||
            !complete_integer_type(target)) {
            throw EncodeFailure("unsupported cast outside integer subset");
        }
        const std::uint32_t source_width = *operand.type.bit_width;
        const std::uint32_t target_width = *target.bit_width;
        z3::expr value = operand.value;
        if (target_width > source_width) {
            value = *operand.type.is_signed
                        ? z3::sext(value, target_width - source_width)
                        : z3::zext(value, target_width - source_width);
        } else if (target_width < source_width) {
            if (*target.is_signed) {
                throw EncodeFailure(
                    "narrowing conversion to signed type is implementation-dependent");
            }
            value = value.extract(target_width - 1, 0);
        } else if (!*operand.type.is_signed && *target.is_signed) {
            throw EncodeFailure(
                "same-width unsigned-to-signed conversion is implementation-dependent");
        }
        EncodedValue result(value, target, false);
        result.defined = std::move(operand.defined);
        return result;
    }

    EncodedValue encode_unary(const ExpressionStructure &expression) {
        if (!expression.operation || expression.operands.size() != 1) {
            throw EncodeFailure("unary expression is incomplete");
        }
        EncodedValue operand = encode(expression.operands.front());
        if (*expression.operation == "!" || *expression.operation == "not") {
            if (!operand.is_boolean ||
                expression.value_type.kind != ValueKind::Boolean) {
                throw EncodeFailure("logical-not operand/type mismatch");
            }
            EncodedValue result(!operand.value, expression.value_type, true);
            result.defined = std::move(operand.defined);
            return result;
        }
        if (operand.is_boolean || !complete_integer_type(operand.type) ||
            !same_value_type(operand.type, expression.value_type)) {
            throw EncodeFailure("integer unary operand/type mismatch");
        }
        z3::expr value = operand.value;
        if (*expression.operation == "-" ||
            *expression.operation == "neg") {
            value = -value;
            if (*operand.type.is_signed) {
                operand.defined.push_back(z3::bvneg_no_overflow(operand.value));
            }
        } else if (*expression.operation == "~" ||
                   *expression.operation == "bitnot") {
            value = ~value;
        } else if (*expression.operation != "+" &&
                   *expression.operation != "plus") {
            throw EncodeFailure("unsupported unary operator");
        }
        EncodedValue result(value, expression.value_type, false);
        result.defined = std::move(operand.defined);
        return result;
    }

    EncodedValue encode_binary(const ExpressionStructure &expression) {
        if (!expression.operation || expression.operands.size() != 2) {
            throw EncodeFailure("binary expression is incomplete");
        }
        if ((*expression.operation == "*" ||
             *expression.operation == "mul") &&
            depends_on_any_target(expression.operands[0]) &&
            depends_on_any_target(expression.operands[1])) {
            throw EncodeFailure("nonlinear target multiplication is unsupported");
        }
        EncodedValue left = encode(expression.operands[0]);
        EncodedValue right = encode(expression.operands[1]);
        if (left.is_boolean || right.is_boolean ||
            !complete_integer_type(left.type) ||
            !same_value_type(left.type, right.type) ||
            !same_value_type(left.type, expression.value_type)) {
            throw EncodeFailure(
                "binary arithmetic requires explicit, identical promoted types");
        }
        z3::expr value = left.value;
        const std::string &operation = *expression.operation;
        if (operation == "+" || operation == "add") {
            value = left.value + right.value;
            if (*left.type.is_signed) {
                left.defined.push_back(
                    z3::bvadd_no_overflow(left.value, right.value, true));
                left.defined.push_back(
                    z3::bvadd_no_underflow(left.value, right.value));
            }
        } else if (operation == "-" || operation == "sub") {
            value = left.value - right.value;
            if (*left.type.is_signed) {
                left.defined.push_back(
                    z3::bvsub_no_overflow(left.value, right.value));
                left.defined.push_back(
                    z3::bvsub_no_underflow(left.value, right.value, true));
            }
        } else if (operation == "*" || operation == "mul") {
            value = left.value * right.value;
            if (*left.type.is_signed) {
                left.defined.push_back(
                    z3::bvmul_no_overflow(left.value, right.value, true));
                left.defined.push_back(
                    z3::bvmul_no_underflow(left.value, right.value));
            }
        } else if (operation == "&" || operation == "bitand") {
            value = left.value & right.value;
        } else if (operation == "|" || operation == "bitor") {
            value = left.value | right.value;
        } else if (operation == "^" || operation == "bitxor") {
            value = left.value ^ right.value;
        } else {
            throw EncodeFailure("unsupported binary arithmetic operator");
        }
        EncodedValue result(value, expression.value_type, false);
        result.defined = std::move(left.defined);
        result.defined.insert(
            result.defined.end(), right.defined.begin(), right.defined.end());
        return result;
    }

    bool depends_on_any_target(
        const ExpressionStructure &expression) const {
        return std::any_of(
            target_inputs_.begin(), target_inputs_.end(),
            [&](const auto &entry) {
                return depends_on(expression, entry.first);
            });
    }

    EncodedValue encode_comparison(const ExpressionStructure &expression) {
        if (!expression.operation || expression.operands.size() != 2 ||
            (expression.value_type.kind != ValueKind::Boolean &&
             !complete_integer_type(expression.value_type))) {
            throw EncodeFailure("comparison expression is incomplete");
        }
        EncodedValue left = encode(expression.operands[0]);
        EncodedValue right = encode(expression.operands[1]);
        if (left.is_boolean != right.is_boolean ||
            !same_value_type(left.type, right.type)) {
            throw EncodeFailure(
                "comparison requires explicit, identical promoted operand types");
        }
        const std::string &operation = *expression.operation;
        z3::expr value = left.value == right.value;
        if (operation == "==" || operation == "eq") {
            value = left.value == right.value;
        } else if (operation == "!=" || operation == "ne") {
            value = left.value != right.value;
        } else {
            if (left.is_boolean || !complete_integer_type(left.type)) {
                throw EncodeFailure("ordered comparison requires integer operands");
            }
            const bool is_signed = *left.type.is_signed;
            if (operation == "<" || operation == "lt") {
                value = is_signed ? left.value < right.value
                                  : z3::ult(left.value, right.value);
            } else if (operation == "<=" || operation == "le") {
                value = is_signed ? left.value <= right.value
                                  : z3::ule(left.value, right.value);
            } else if (operation == ">" || operation == "gt") {
                value = is_signed ? left.value > right.value
                                  : z3::ugt(left.value, right.value);
            } else if (operation == ">=" || operation == "ge") {
                value = is_signed ? left.value >= right.value
                                  : z3::uge(left.value, right.value);
            } else {
                throw EncodeFailure("unsupported comparison operator");
            }
        }
        EncodedValue result(value, expression.value_type, true);
        result.defined = std::move(left.defined);
        result.defined.insert(
            result.defined.end(), right.defined.begin(), right.defined.end());
        return result;
    }

    EncodedValue encode_boolean(const ExpressionStructure &expression) {
        if (!expression.operation || expression.operands.size() != 2 ||
            expression.value_type.kind != ValueKind::Boolean) {
            throw EncodeFailure("Boolean expression is incomplete");
        }
        EncodedValue left = encode(expression.operands[0]);
        EncodedValue right = encode(expression.operands[1]);
        if (!left.is_boolean || !right.is_boolean) {
            throw EncodeFailure("Boolean operator has non-Boolean operand");
        }
        z3::expr value = left.value && right.value;
        if (*expression.operation == "&&" ||
            *expression.operation == "and") {
            value = left.value && right.value;
        } else if (*expression.operation == "||" ||
                   *expression.operation == "or") {
            value = left.value || right.value;
        } else if (*expression.operation == "xor") {
            value = left.value != right.value;
        } else {
            throw EncodeFailure("unsupported Boolean operator");
        }
        EncodedValue result(value, expression.value_type, true);
        result.defined = std::move(left.defined);
        result.defined.insert(
            result.defined.end(), right.defined.begin(), right.defined.end());
        return result;
    }

    z3::context &context_;
    std::map<std::string, z3::expr> target_inputs_;
    std::map<std::string, ValueType> target_types_;
    const std::map<std::string, z3::expr> &shared_state_;
};

z3::expr ordered_less(
    const z3::expr &left, const z3::expr &right, const ValueType &type) {
    if (type.kind == ValueKind::Boolean) {
        return !left && right;
    }
    return *type.is_signed ? left < right : z3::ult(left, right);
}

std::string model_value(
    const z3::model &model, const z3::expr &value, const ValueType &type) {
    if (type.kind == ValueKind::Boolean) {
        return model.eval(value, true).to_string();
    }
    return model.eval(z3::bv2int(value, *type.is_signed), true).to_string();
}

void add_tracked(
    z3::solver &solver, const z3::expr &constraint,
    const std::string &label, std::vector<std::string> &labels) {
    solver.add(constraint, label.c_str());
    labels.push_back(label);
}

struct QueryResult {
    SolverQueryEvidence truth_change;
    std::optional<SolverQueryEvidence> direction;
    MutationDirection proven_direction = MutationDirection::BoundarySet;
    std::optional<std::string> left_value;
    std::optional<std::string> right_value;
};

const ExpressionStructure *value_preserving_reference(
    const ExpressionStructure &expression) {
    if (expression.node_kind == "reference") {
        return &expression;
    }
    if (expression.node_kind != "cast" ||
        expression.operands.size() != 1 ||
        !same_value_type(
            expression.value_type,
            expression.operands.front().value_type)) {
        return nullptr;
    }
    return value_preserving_reference(expression.operands.front());
}

const ExpressionStructure *truth_preserving_operand(
    const ExpressionStructure &expression) {
    if (expression.node_kind != "cast" ||
        expression.operands.size() != 1) {
        return &expression;
    }
    const ExpressionStructure &operand = expression.operands.front();
    const bool same_type =
        same_value_type(expression.value_type, operand.value_type);
    const bool bool_to_integer =
        operand.value_type.kind == ValueKind::Boolean &&
        complete_integer_type(expression.value_type);
    const bool integer_to_bool =
        expression.value_type.kind == ValueKind::Boolean &&
        complete_integer_type(operand.value_type);
    return same_type || bool_to_integer || integer_to_bool
               ? truth_preserving_operand(operand)
               : &expression;
}

enum class MonotoneSign {
    Negative = -1,
    Independent = 0,
    Positive = 1,
    Unknown = 2,
};

MonotoneSign negate_sign(MonotoneSign sign) {
    if (sign == MonotoneSign::Positive) return MonotoneSign::Negative;
    if (sign == MonotoneSign::Negative) return MonotoneSign::Positive;
    return sign;
}

MonotoneSign combine_additive(
    MonotoneSign left, MonotoneSign right) {
    if (left == MonotoneSign::Unknown || right == MonotoneSign::Unknown) {
        return MonotoneSign::Unknown;
    }
    if (left == MonotoneSign::Independent) return right;
    if (right == MonotoneSign::Independent) return left;
    return left == right ? left : MonotoneSign::Unknown;
}

std::optional<cpp_int> integer_literal_value(
    const ExpressionStructure &expression) {
    if (expression.node_kind != "literal" || !expression.literal ||
        expression.literal->kind != LiteralKind::Integer) {
        return std::nullopt;
    }
    return parse_integer(expression.literal->canonical);
}

MonotoneSign monotone_sign(
    const ExpressionStructure &expression,
    const std::string &selector_id) {
    if (expression.node_kind == "reference") {
        return expression.referenced_selector_id == selector_id
                   ? MonotoneSign::Positive
                   : MonotoneSign::Independent;
    }
    if (expression.node_kind == "literal") {
        return MonotoneSign::Independent;
    }
    if (expression.node_kind == "cast" &&
        expression.operands.size() == 1) {
        return monotone_sign(expression.operands.front(), selector_id);
    }
    if (expression.node_kind == "unary" && expression.operation &&
        expression.operands.size() == 1) {
        MonotoneSign sign =
            monotone_sign(expression.operands.front(), selector_id);
        if (*expression.operation == "-" ||
            *expression.operation == "neg" ||
            *expression.operation == "!" ||
            *expression.operation == "not") {
            return negate_sign(sign);
        }
        if (*expression.operation == "+" ||
            *expression.operation == "plus") {
            return sign;
        }
        return MonotoneSign::Unknown;
    }
    if (expression.node_kind == "binary" && expression.operation &&
        expression.operands.size() == 2) {
        const MonotoneSign left =
            monotone_sign(expression.operands[0], selector_id);
        const MonotoneSign right =
            monotone_sign(expression.operands[1], selector_id);
        if (*expression.operation == "+" ||
            *expression.operation == "add") {
            return combine_additive(left, right);
        }
        if (*expression.operation == "-" ||
            *expression.operation == "sub") {
            return combine_additive(left, negate_sign(right));
        }
        if (*expression.operation == "*" ||
            *expression.operation == "mul") {
            const std::optional<cpp_int> left_constant =
                integer_literal_value(expression.operands[0]);
            const std::optional<cpp_int> right_constant =
                integer_literal_value(expression.operands[1]);
            if (left_constant && right == MonotoneSign::Independent) {
                return MonotoneSign::Independent;
            }
            if (right_constant && left == MonotoneSign::Independent) {
                return MonotoneSign::Independent;
            }
            if (left_constant) {
                if (*left_constant == 0) return MonotoneSign::Independent;
                return *left_constant < 0 ? negate_sign(right) : right;
            }
            if (right_constant) {
                if (*right_constant == 0) return MonotoneSign::Independent;
                return *right_constant < 0 ? negate_sign(left) : left;
            }
        }
        return MonotoneSign::Unknown;
    }
    if (expression.node_kind == "boolean" && expression.operation &&
        expression.operands.size() == 2 &&
        (*expression.operation == "&&" ||
         *expression.operation == "and" ||
         *expression.operation == "||" ||
         *expression.operation == "or")) {
        return combine_additive(
            monotone_sign(expression.operands[0], selector_id),
            monotone_sign(expression.operands[1], selector_id));
    }
    return MonotoneSign::Unknown;
}

std::optional<MutationDirection> syntactic_direction(
    const ExpressionStructure &expression, const std::string &selector_id) {
    const ExpressionStructure *truth = truth_preserving_operand(expression);
    if (truth != &expression) {
        return syntactic_direction(*truth, selector_id);
    }
    const ExpressionStructure *direct =
        value_preserving_reference(expression);
    if (direct != nullptr &&
        direct->referenced_selector_id == selector_id &&
        direct->value_type.kind == ValueKind::Boolean) {
        return MutationDirection::MonotoneUp;
    }
    if (expression.node_kind == "unary" && expression.operation &&
        (*expression.operation == "!" || *expression.operation == "not") &&
        expression.operands.size() == 1) {
        const ExpressionStructure *operand =
            value_preserving_reference(expression.operands[0]);
        if (operand != nullptr &&
            operand->referenced_selector_id == selector_id) {
            return MutationDirection::MonotoneDown;
        }
    }
    if (expression.node_kind != "comparison" || !expression.operation ||
        expression.operands.size() != 2) {
        return std::nullopt;
    }
    MonotoneSign sign = combine_additive(
        monotone_sign(expression.operands[0], selector_id),
        negate_sign(monotone_sign(expression.operands[1], selector_id)));
    if (sign != MonotoneSign::Positive &&
        sign != MonotoneSign::Negative) {
        return std::nullopt;
    }
    std::string operation = *expression.operation;
    const bool greater = operation == ">" || operation == ">=" ||
                         operation == "gt" || operation == "ge";
    const bool less = operation == "<" || operation == "<=" ||
                      operation == "lt" || operation == "le";
    if (!greater && !less) return std::nullopt;
    const bool increasing_truth =
        (greater && sign == MonotoneSign::Positive) ||
        (less && sign == MonotoneSign::Negative);
    return increasing_truth ? MutationDirection::MonotoneUp
                            : MutationDirection::MonotoneDown;
}

SolverQueryEvidence unsupported_query(
    const std::string &digest, const RecipeOptions &options,
    const std::string &reason, SolverOutcome outcome) {
    SolverQueryEvidence evidence;
    evidence.query_sha256 = digest;
    evidence.query_id = stable_id("query", digest);
    evidence.solver_version = z3_version();
    evidence.timeout_ms = options.solver_timeout_ms;
    evidence.outcome = outcome;
    evidence.flip_class = FlipClass::Unknown;
    evidence.unknown_reason = reason;
    return evidence;
}

bool solver_outcome_is_incomplete(SolverOutcome outcome) {
    return outcome == SolverOutcome::Unknown ||
           outcome == SolverOutcome::Timeout ||
           outcome == SolverOutcome::Unsupported ||
           outcome == SolverOutcome::NotRun;
}

QueryResult solve_truth_change(
    const FrontierCandidate &candidate,
    const ExpressionStructure &predicate,
    const std::string &selector_id,
    const ValueType &storage_type,
    const RecipeOptions &options,
    std::uint64_t &queries_used,
    bool require_adjacent_pair = false,
    bool require_false_to_true = false) {
    QueryResult result;
    const std::string digest = expression_query_digest(
        candidate, predicate, selector_id,
        require_adjacent_pair ? "payload-truth-change-adjacent"
                              : "truth-change");
    if (queries_used >= options.max_solver_queries) {
        result.truth_change = unsupported_query(
            digest, options, "solver query budget exhausted before query",
            SolverOutcome::NotRun);
        return result;
    }
    ++queries_used;
    try {
        z3::context context;
        z3::expr left = storage_type.kind == ValueKind::Boolean
                            ? context.bool_const("target_action_left")
                            : context.bv_const(
                                  "target_action_left",
                                  *storage_type.bit_width);
        z3::expr right = storage_type.kind == ValueKind::Boolean
                             ? context.bool_const("target_action_right")
                             : context.bv_const(
                                   "target_action_right",
                                   *storage_type.bit_width);
        std::map<std::string, ValueType> reference_types;
        std::string reference_error;
        if (!collect_reference_types(
                predicate, reference_types, reference_error)) {
            throw EncodeFailure(reference_error);
        }
        std::map<std::string, z3::expr> shared_state;
        std::size_t shared_index = 0;
        for (const auto &[reference_id, reference_type] : reference_types) {
            if (reference_id == selector_id) {
                continue;
            }
            const std::string name =
                "shared_state_" + std::to_string(shared_index++);
            if (reference_type.kind == ValueKind::Boolean) {
                shared_state.emplace(
                    reference_id, context.bool_const(name.c_str()));
            } else if (complete_integer_type(reference_type)) {
                shared_state.emplace(
                    reference_id,
                    context.bv_const(
                        name.c_str(), *reference_type.bit_width));
            } else {
                throw EncodeFailure(
                    "non-target shared reference has unsupported type");
            }
        }
        ExpressionEncoder left_encoder(
            context, selector_id, storage_type, left, shared_state);
        ExpressionEncoder right_encoder(
            context, selector_id, storage_type, right, shared_state);
        EncodedValue left_predicate = left_encoder.encode(predicate);
        EncodedValue right_predicate = right_encoder.encode(predicate);
        const auto coerce_truth = [&](EncodedValue value) {
            if (value.is_boolean) {
                return value;
            }
            if (!complete_integer_type(value.type)) {
                throw EncodeFailure(
                    "AP predicate does not have C/C++ scalar truth semantics");
            }
            ValueType boolean;
            boolean.kind = ValueKind::Boolean;
            boolean.canonical = "bool";
            EncodedValue result(
                value.value !=
                    context.bv_val(0U, *value.type.bit_width),
                boolean, true);
            result.defined = std::move(value.defined);
            return result;
        };
        left_predicate = coerce_truth(std::move(left_predicate));
        right_predicate = coerce_truth(std::move(right_predicate));
        if (!left_predicate.is_boolean || !right_predicate.is_boolean) {
            throw EncodeFailure("AP predicate does not encode to Boolean");
        }

        z3::solver solver(context);
        solver.set(
            "timeout", static_cast<unsigned>(std::min<std::uint64_t>(
                           options.solver_timeout_ms,
                           std::numeric_limits<unsigned>::max())));
        solver.set("random_seed", 0U);
        std::vector<std::string> labels;
        add_tracked(
            solver, context.bool_val(true),
            "same_except_target_action", labels);
        add_tracked(
            solver, context.bool_val(true),
            "same_initial_scope_generation_state", labels);
        for (std::size_t index = 0;
             index < left_predicate.defined.size(); ++index) {
            add_tracked(
                solver, left_predicate.defined[index],
                "defined_left_" + std::to_string(index), labels);
        }
        for (std::size_t index = 0;
             index < right_predicate.defined.size(); ++index) {
            add_tracked(
                solver, right_predicate.defined[index],
                "defined_right_" + std::to_string(index), labels);
        }
        add_tracked(solver, left != right, "different_target_action", labels);
        if (require_false_to_true) {
            add_tracked(
                solver, !left_predicate.value,
                "ap_left_false", labels);
            add_tracked(
                solver, right_predicate.value,
                "ap_right_true", labels);
        } else {
            add_tracked(
                solver, left_predicate.value != right_predicate.value,
                "different_ap_value", labels);
        }
        if (require_adjacent_pair &&
            storage_type.kind != ValueKind::Boolean) {
            const z3::expr one = context.bv_val(
                1U, *storage_type.bit_width);
            add_tracked(
                solver,
                right == left + one || left == right + one,
                "adjacent_external_payload_values", labels);
        }

        SolverQueryEvidence evidence;
        evidence.query_sha256 = digest;
        evidence.query_id = stable_id("query", digest);
        evidence.solver_version = z3_version();
        evidence.timeout_ms = options.solver_timeout_ms;
        evidence.assumption_literals = labels;
        const z3::check_result check = solver.check();
        if (check == z3::sat) {
            evidence.outcome = SolverOutcome::Sat;
            evidence.flip_class = FlipClass::LocalSummarySatPair;
            const z3::model model = solver.get_model();
            result.left_value = model_value(model, left, storage_type);
            result.right_value = model_value(model, right, storage_type);
            evidence.model = {
                "target_action_left=" + *result.left_value,
                "target_action_right=" + *result.right_value,
                "ap_left=" + model.eval(left_predicate.value, true).to_string(),
                "ap_right=" + model.eval(right_predicate.value, true).to_string()};
            for (const auto &[reference_id, state] : shared_state) {
                const ValueType &reference_type = reference_types.at(reference_id);
                evidence.model.push_back(
                    "shared:" + reference_id + '=' +
                    model_value(model, state, reference_type));
            }
        } else if (check == z3::unsat) {
            evidence.outcome = SolverOutcome::Unsat;
            evidence.flip_class = FlipClass::Unknown;
            const z3::expr_vector core = solver.unsat_core();
            for (unsigned index = 0; index < core.size(); ++index) {
                evidence.unsat_core.push_back(core[index].to_string());
            }
        } else {
            const std::string reason = solver.reason_unknown();
            evidence.outcome = reason.find("timeout") != std::string::npos
                                   ? SolverOutcome::Timeout
                                   : SolverOutcome::Unknown;
            evidence.flip_class = FlipClass::Unknown;
            evidence.unknown_reason =
                reason.empty() ? "solver returned UNKNOWN" : reason;
        }
        result.truth_change = std::move(evidence);

        const std::optional<MutationDirection> expected =
            syntactic_direction(predicate, selector_id);
        if (result.truth_change.outcome != SolverOutcome::Sat || !expected) {
            return result;
        }
        const std::string direction_name =
            *expected == MutationDirection::MonotoneUp ? "up" : "down";
        const std::string direction_digest = expression_query_digest(
            candidate, predicate, selector_id,
            "direction-counterexample-" + direction_name);
        if (queries_used >= options.max_solver_queries) {
            result.direction = unsupported_query(
                direction_digest, options,
                "solver query budget exhausted before monotonicity proof",
                SolverOutcome::NotRun);
            return result;
        }
        ++queries_used;
        z3::solver direction_solver(context);
        direction_solver.set(
            "timeout", static_cast<unsigned>(std::min<std::uint64_t>(
                           options.solver_timeout_ms,
                           std::numeric_limits<unsigned>::max())));
        direction_solver.set("random_seed", 0U);
        std::vector<std::string> direction_labels;
        add_tracked(
            direction_solver, context.bool_val(true),
            "same_except_target_action", direction_labels);
        add_tracked(
            direction_solver, context.bool_val(true),
            "same_initial_scope_generation_state", direction_labels);
        for (std::size_t index = 0;
             index < left_predicate.defined.size(); ++index) {
            add_tracked(
                direction_solver, left_predicate.defined[index],
                "defined_left_" + std::to_string(index), direction_labels);
        }
        for (std::size_t index = 0;
             index < right_predicate.defined.size(); ++index) {
            add_tracked(
                direction_solver, right_predicate.defined[index],
                "defined_right_" + std::to_string(index), direction_labels);
        }
        add_tracked(
            direction_solver, ordered_less(left, right, storage_type),
            "strictly_increasing_action", direction_labels);
        const z3::expr counterexample =
            *expected == MutationDirection::MonotoneUp
                ? left_predicate.value && !right_predicate.value
                : !left_predicate.value && right_predicate.value;
        add_tracked(
            direction_solver, counterexample,
            "opposite_direction_counterexample", direction_labels);

        SolverQueryEvidence direction_evidence;
        direction_evidence.query_sha256 = direction_digest;
        direction_evidence.query_id = stable_id("query", direction_digest);
        direction_evidence.solver_version = z3_version();
        direction_evidence.timeout_ms = options.solver_timeout_ms;
        direction_evidence.assumption_literals = direction_labels;
        const z3::check_result direction_check = direction_solver.check();
        if (direction_check == z3::unsat) {
            direction_evidence.outcome = SolverOutcome::Unsat;
            const z3::expr_vector core = direction_solver.unsat_core();
            for (unsigned index = 0; index < core.size(); ++index) {
                direction_evidence.unsat_core.push_back(
                    core[index].to_string());
            }
            result.proven_direction = *expected;
        } else if (direction_check == z3::sat) {
            direction_evidence.outcome = SolverOutcome::Sat;
            direction_evidence.flip_class = FlipClass::LocalSummarySatPair;
            const z3::model model = direction_solver.get_model();
            direction_evidence.model = {
                "counterexample_left=" + model_value(model, left, storage_type),
                "counterexample_right=" + model_value(model, right, storage_type)};
        } else {
            const std::string reason = direction_solver.reason_unknown();
            direction_evidence.outcome =
                reason.find("timeout") != std::string::npos
                    ? SolverOutcome::Timeout
                    : SolverOutcome::Unknown;
            direction_evidence.unknown_reason =
                reason.empty() ? "solver returned UNKNOWN" : reason;
        }
        result.direction = std::move(direction_evidence);
        return result;
    } catch (const EncodeFailure &failure) {
        result.truth_change = unsupported_query(
            digest, options, failure.what(), SolverOutcome::Unsupported);
        return result;
    } catch (const z3::exception &failure) {
        result.truth_change = unsupported_query(
            digest, options,
            std::string("Z3 encoding failure: ") + failure.msg(),
            SolverOutcome::Unknown);
        return result;
    }
}

struct JointTargetInput {
    std::string action_id;
    std::string selector_id;
    ValueType type;
};

struct JointQueryResult {
    SolverQueryEvidence truth_change;
    std::map<std::string, std::pair<std::string, std::string>> action_values;
};

JointQueryResult solve_joint_truth_change(
    const JointActionRequirement &joint,
    const ExpressionStructure &predicate,
    std::vector<JointTargetInput> targets,
    const RecipeOptions &options, std::uint64_t &queries_used) {
    std::sort(
        targets.begin(), targets.end(),
        [](const JointTargetInput &left, const JointTargetInput &right) {
            return std::tie(left.action_id, left.selector_id) <
                   std::tie(right.action_id, right.selector_id);
        });
    std::ostringstream digest_material;
    digest_material << kEncodingVersion << "|joint|"
                    << joint.requirement_id;
    for (const JointTargetInput &target : targets) {
        digest_material << '|' << target.action_id << '|'
                        << target.selector_id << '|'
                        << type_material(target.type);
    }
    append_expression_material(digest_material, predicate);
    const std::string digest = sha256_hex(digest_material.str());
    JointQueryResult result;
    if (queries_used >= options.max_solver_queries) {
        result.truth_change = unsupported_query(
            digest, options, "solver query budget exhausted before joint query",
            SolverOutcome::NotRun);
        return result;
    }
    ++queries_used;
    try {
        if (targets.size() < 2) {
            throw EncodeFailure("joint query has fewer than two atomic actions");
        }
        std::set<std::string> action_ids;
        std::set<std::string> selector_ids;
        for (const JointTargetInput &target : targets) {
            if (!action_ids.insert(target.action_id).second ||
                !selector_ids.insert(target.selector_id).second) {
                throw EncodeFailure(
                    "joint action/selector mapping is not one-to-one");
            }
            if (target.type.kind != ValueKind::Boolean &&
                !complete_integer_type(target.type)) {
                throw EncodeFailure(
                    "joint action payload has unsupported scalar type");
            }
        }
        z3::context context;
        std::map<std::string, z3::expr> left_inputs;
        std::map<std::string, z3::expr> right_inputs;
        std::map<std::string, ValueType> target_types;
        for (std::size_t index = 0; index < targets.size(); ++index) {
            const JointTargetInput &target = targets[index];
            const std::string left_name =
                "joint_left_" + std::to_string(index);
            const std::string right_name =
                "joint_right_" + std::to_string(index);
            if (target.type.kind == ValueKind::Boolean) {
                left_inputs.emplace(
                    target.selector_id,
                    context.bool_const(left_name.c_str()));
                right_inputs.emplace(
                    target.selector_id,
                    context.bool_const(right_name.c_str()));
            } else {
                left_inputs.emplace(
                    target.selector_id,
                    context.bv_const(
                        left_name.c_str(), *target.type.bit_width));
                right_inputs.emplace(
                    target.selector_id,
                    context.bv_const(
                        right_name.c_str(), *target.type.bit_width));
            }
            target_types.emplace(target.selector_id, target.type);
        }
        std::map<std::string, ValueType> reference_types;
        std::string reference_error;
        if (!collect_reference_types(
                predicate, reference_types, reference_error)) {
            throw EncodeFailure(reference_error);
        }
        std::map<std::string, z3::expr> shared_state;
        std::size_t shared_index = 0;
        for (const auto &[reference_id, reference_type] : reference_types) {
            if (target_types.contains(reference_id)) continue;
            const std::string name =
                "joint_shared_" + std::to_string(shared_index++);
            if (reference_type.kind == ValueKind::Boolean) {
                shared_state.emplace(
                    reference_id, context.bool_const(name.c_str()));
            } else if (complete_integer_type(reference_type)) {
                shared_state.emplace(
                    reference_id,
                    context.bv_const(
                        name.c_str(), *reference_type.bit_width));
            } else {
                throw EncodeFailure(
                    "joint non-target reference has unsupported type");
            }
        }
        ExpressionEncoder left_encoder(
            context, left_inputs, target_types, shared_state);
        ExpressionEncoder right_encoder(
            context, right_inputs, target_types, shared_state);
        EncodedValue left_predicate = left_encoder.encode(predicate);
        EncodedValue right_predicate = right_encoder.encode(predicate);
        const auto coerce_truth = [&](EncodedValue value) {
            if (value.is_boolean) return value;
            if (!complete_integer_type(value.type)) {
                throw EncodeFailure(
                    "joint AP predicate lacks C/C++ scalar truth semantics");
            }
            ValueType boolean;
            boolean.kind = ValueKind::Boolean;
            boolean.canonical = "bool";
            EncodedValue converted(
                value.value !=
                    context.bv_val(0U, *value.type.bit_width),
                boolean, true);
            converted.defined = std::move(value.defined);
            return converted;
        };
        left_predicate = coerce_truth(std::move(left_predicate));
        right_predicate = coerce_truth(std::move(right_predicate));

        z3::solver solver(context);
        solver.set(
            "timeout", static_cast<unsigned>(std::min<std::uint64_t>(
                           options.solver_timeout_ms,
                           std::numeric_limits<unsigned>::max())));
        solver.set("random_seed", 0U);
        std::vector<std::string> labels;
        add_tracked(
            solver, context.bool_val(true),
            "same_initial_scope_generation_state", labels);
        for (std::size_t index = 0;
             index < left_predicate.defined.size(); ++index) {
            add_tracked(
                solver, left_predicate.defined[index],
                "joint_defined_left_" + std::to_string(index), labels);
        }
        for (std::size_t index = 0;
             index < right_predicate.defined.size(); ++index) {
            add_tracked(
                solver, right_predicate.defined[index],
                "joint_defined_right_" + std::to_string(index), labels);
        }
        for (std::size_t index = 0; index < targets.size(); ++index) {
            add_tracked(
                solver,
                left_inputs.at(targets[index].selector_id) !=
                    right_inputs.at(targets[index].selector_id),
                "joint_action_changes_" + std::to_string(index), labels);
        }
        add_tracked(
            solver, !left_predicate.value,
            "joint_source_ap_false", labels);
        add_tracked(
            solver, right_predicate.value,
            "joint_target_ap_true", labels);

        SolverQueryEvidence evidence;
        evidence.query_sha256 = digest;
        evidence.query_id = stable_id("query", digest);
        evidence.solver_version = z3_version();
        evidence.timeout_ms = options.solver_timeout_ms;
        evidence.assumption_literals = labels;
        const z3::check_result check = solver.check();
        if (check == z3::sat) {
            evidence.outcome = SolverOutcome::Sat;
            evidence.flip_class = FlipClass::LocalSummarySatPair;
            const z3::model model = solver.get_model();
            evidence.model = {
                "ap_left=" +
                    model.eval(left_predicate.value, true).to_string(),
                "ap_right=" +
                    model.eval(right_predicate.value, true).to_string()};
            for (const JointTargetInput &target : targets) {
                const std::string left_value = model_value(
                    model, left_inputs.at(target.selector_id), target.type);
                const std::string right_value = model_value(
                    model, right_inputs.at(target.selector_id), target.type);
                result.action_values.emplace(
                    target.action_id,
                    std::make_pair(left_value, right_value));
                evidence.model.push_back(
                    "action:" + target.action_id + ":left=" + left_value);
                evidence.model.push_back(
                    "action:" + target.action_id + ":right=" + right_value);
            }
        } else if (check == z3::unsat) {
            evidence.outcome = SolverOutcome::Unsat;
            const z3::expr_vector core = solver.unsat_core();
            for (unsigned index = 0; index < core.size(); ++index) {
                evidence.unsat_core.push_back(core[index].to_string());
            }
        } else {
            const std::string reason = solver.reason_unknown();
            evidence.outcome = reason.find("timeout") != std::string::npos
                ? SolverOutcome::Timeout
                : SolverOutcome::Unknown;
            evidence.unknown_reason =
                reason.empty() ? "solver returned UNKNOWN" : reason;
        }
        result.truth_change = std::move(evidence);
    } catch (const EncodeFailure &failure) {
        result.truth_change = unsupported_query(
            digest, options, failure.what(), SolverOutcome::Unsupported);
    } catch (const z3::exception &failure) {
        result.truth_change = unsupported_query(
            digest, options,
            std::string("Z3 encoding failure: ") + failure.msg(),
            SolverOutcome::Unknown);
    }
    return result;
}

struct DirectBoundary {
    std::string selector_id;
    ValueType type;
    cpp_int value;
    bool equality = false;
    bool bitmask = false;
    std::optional<cpp_int> mask;
};

std::optional<DirectBoundary> direct_boundary(
    const ExpressionStructure &predicate) {
    const ExpressionStructure &truth = *truth_preserving_operand(predicate);
    if (truth.node_kind != "comparison" || !truth.operation ||
        truth.operands.size() != 2) {
        return std::nullopt;
    }
    const ExpressionStructure *reference = nullptr;
    const ExpressionStructure *literal = nullptr;
    if (const ExpressionStructure *candidate =
            value_preserving_reference(truth.operands[0]);
        candidate != nullptr &&
        truth.operands[1].node_kind == "literal") {
        reference = candidate;
        literal = &truth.operands[1];
    } else if (const ExpressionStructure *candidate =
                   value_preserving_reference(truth.operands[1]);
               candidate != nullptr &&
               truth.operands[0].node_kind == "literal") {
        reference = candidate;
        literal = &truth.operands[0];
    }
    if (reference == nullptr || literal == nullptr ||
        !reference->referenced_selector_id || !literal->literal ||
        literal->literal->kind != LiteralKind::Integer ||
        !same_value_type(reference->value_type, literal->value_type) ||
        !complete_integer_type(reference->value_type)) {
        return std::nullopt;
    }
    const std::optional<cpp_int> value =
        parse_integer(literal->literal->canonical);
    if (!value || !integer_fits(*value, reference->value_type)) {
        return std::nullopt;
    }
    DirectBoundary result;
    result.selector_id = *reference->referenced_selector_id;
    result.type = reference->value_type;
    result.value = *value;
    result.equality = *truth.operation == "==" ||
                      *truth.operation == "eq" ||
                      *truth.operation == "!=" ||
                      *truth.operation == "ne";
    return result;
}

std::optional<DirectBoundary> bitmask_boundary(
    const ExpressionStructure &predicate) {
    const ExpressionStructure &truth = *truth_preserving_operand(predicate);
    if (truth.node_kind != "comparison" || !truth.operation ||
        (*truth.operation != "==" && *truth.operation != "eq" &&
         *truth.operation != "!=" && *truth.operation != "ne") ||
        truth.operands.size() != 2) {
        return std::nullopt;
    }
    const ExpressionStructure *masked = nullptr;
    const ExpressionStructure *expected = nullptr;
    if (truth.operands[0].node_kind == "binary" &&
        truth.operands[1].node_kind == "literal") {
        masked = &truth.operands[0];
        expected = &truth.operands[1];
    } else if (truth.operands[1].node_kind == "binary" &&
               truth.operands[0].node_kind == "literal") {
        masked = &truth.operands[1];
        expected = &truth.operands[0];
    }
    if (masked == nullptr || expected == nullptr || !masked->operation ||
        (*masked->operation != "&" && *masked->operation != "bitand") ||
        masked->operands.size() != 2 || !expected->literal ||
        expected->literal->kind != LiteralKind::Integer) {
        return std::nullopt;
    }
    const ExpressionStructure *reference = nullptr;
    const ExpressionStructure *mask_literal = nullptr;
    if (const ExpressionStructure *candidate =
            value_preserving_reference(masked->operands[0]);
        candidate != nullptr &&
        masked->operands[1].node_kind == "literal") {
        reference = candidate;
        mask_literal = &masked->operands[1];
    } else if (const ExpressionStructure *candidate =
                   value_preserving_reference(masked->operands[1]);
               candidate != nullptr &&
               masked->operands[0].node_kind == "literal") {
        reference = candidate;
        mask_literal = &masked->operands[0];
    }
    if (reference == nullptr || mask_literal == nullptr ||
        !reference->referenced_selector_id || !mask_literal->literal ||
        mask_literal->literal->kind != LiteralKind::Integer ||
        !same_value_type(reference->value_type, masked->value_type) ||
        !same_value_type(reference->value_type, mask_literal->value_type) ||
        !same_value_type(reference->value_type, expected->value_type) ||
        !complete_integer_type(reference->value_type)) {
        return std::nullopt;
    }
    const std::optional<cpp_int> mask =
        parse_integer(mask_literal->literal->canonical);
    const std::optional<cpp_int> value =
        parse_integer(expected->literal->canonical);
    if (!mask || !value || !integer_fits(*mask, reference->value_type) ||
        !integer_fits(*value, reference->value_type) || *mask == 0) {
        return std::nullopt;
    }
    DirectBoundary result;
    result.selector_id = *reference->referenced_selector_id;
    result.type = reference->value_type;
    result.value = *value;
    result.equality = true;
    result.bitmask = true;
    result.mask = *mask;
    return result;
}

void add_mutation_value(
    ActionMutation &mutation, const cpp_int &value,
    MutationValuePurpose purpose, const ValueType &type) {
    if (!integer_fits(value, type)) {
        return;
    }
    const std::string canonical = integer_string(value);
    const bool duplicate = std::any_of(
        mutation.suggested_values.begin(), mutation.suggested_values.end(),
        [&](const MutationValue &item) {
            return item.canonical == canonical;
        });
    if (!duplicate) {
        mutation.suggested_values.push_back({canonical, type, purpose});
    }
}

void add_boundary_values(
    ActionMutation &mutation, const DirectBoundary &boundary) {
    const auto [minimum, maximum] = integer_bounds(boundary.type);
    if (boundary.type.kind != ValueKind::Enumeration) {
        add_mutation_value(
            mutation, minimum, MutationValuePurpose::TypeMin, boundary.type);
    }
    add_mutation_value(
        mutation, boundary.value - 1,
        MutationValuePurpose::BelowBoundary, boundary.type);
    add_mutation_value(
        mutation, boundary.value,
        boundary.type.kind == ValueKind::Enumeration
            ? MutationValuePurpose::EnumAlternative
            : MutationValuePurpose::AtBoundary,
        boundary.type);
    add_mutation_value(
        mutation, boundary.value + 1,
        MutationValuePurpose::AboveBoundary, boundary.type);
    if (boundary.type.kind != ValueKind::Enumeration) {
        add_mutation_value(
            mutation, maximum, MutationValuePurpose::TypeMax, boundary.type);
    }
}

std::vector<const TimeInterval *> intervals_for_ap(
    const FormulaNode &node, const std::string &ap_id,
    std::vector<const TimeInterval *> active = {}) {
    if (node.interval) {
        active.push_back(&*node.interval);
    }
    if (node.operation == FormulaOperator::Atom && node.ap_id == ap_id) {
        return active;
    }
    std::vector<const TimeInterval *> result;
    for (const FormulaNode &operand : node.operands) {
        std::vector<const TimeInterval *> nested =
            intervals_for_ap(operand, ap_id, active);
        result.insert(result.end(), nested.begin(), nested.end());
    }
    return result;
}

TimingContract build_timing_contract(
    const TypedPropertyIr &property, const FrontierCandidate &candidate,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay) {
    TimingContract timing;
    if (!candidate.action.scope_schema.empty()) {
        timing.scope_schema = candidate.action.scope_schema;
    }
    if (!candidate.action.generation_schema.empty()) {
        timing.generation_schema = candidate.action.generation_schema;
    }
    std::vector<const TimeInterval *> intervals =
        intervals_for_ap(property.formula, candidate.ap_id);
    std::sort(
        intervals.begin(), intervals.end(),
        [](const TimeInterval *left, const TimeInterval *right) {
            return std::tie(
                       left->lower, left->upper, left->upper_is_infinity,
                       left->lower_closed, left->upper_closed, left->unit,
                       left->bound_ap_ids) <
                   std::tie(
                       right->lower, right->upper, right->upper_is_infinity,
                       right->lower_closed, right->upper_closed, right->unit,
                       right->bound_ap_ids);
        });
    intervals.erase(
        std::unique(
            intervals.begin(), intervals.end(),
            [](const TimeInterval *left, const TimeInterval *right) {
                return left->lower == right->lower &&
                       left->upper == right->upper &&
                       left->upper_is_infinity == right->upper_is_infinity &&
                       left->lower_closed == right->lower_closed &&
                       left->upper_closed == right->upper_closed &&
                       left->unit == right->unit &&
                       left->bound_ap_ids == right->bound_ap_ids;
            }),
        intervals.end());
    if (intervals.empty()) {
        timing.status = TimingStatus::Unknown;
        timing.uncertainty_reasons.push_back(
            "no metric interval is structurally associated with this AP occurrence");
    } else {
        const TimeInterval &interval = *intervals.front();
        timing.lower = interval.lower;
        if (!interval.upper_is_infinity && interval.upper) {
            timing.upper = *interval.upper;
        }
        timing.lower_closed = interval.lower_closed;
        timing.upper_closed = interval.upper_closed;
        if (!interval.unit.empty()) {
            timing.unit = interval.unit;
        }
        timing.comparison_endpoint =
            interval.lower_closed == interval.upper_closed
                ? (interval.lower_closed ? TimingEndpoint::Closed
                                         : TimingEndpoint::Open)
                : TimingEndpoint::Mixed;
        timing.status = TimingStatus::WidenedUnknown;
        if (intervals.size() != 1) {
            timing.uncertainty_reasons.push_back(
                "multiple distinct metric intervals are associated with this AP occurrence");
        }
        if (interval.upper_is_infinity) {
            timing.uncertainty_reasons.push_back(
                "unbounded interval has no finite upper mutation boundary");
        }

        std::unordered_map<std::string, const ContextualNode *> nodes;
        for (const ContextualNode &node : graph.nodes) {
            nodes.emplace(node.node_id, &node);
        }
        std::set<std::string> candidate_fact_ids(
            candidate.evidence.model_provenance.model_fact_ids.begin(),
            candidate.evidence.model_provenance.model_fact_ids.end());
        std::set<std::string> witnessed_clock_fact_ids;
        for (const FrontierWitness &witness : candidate.witnesses) {
            if (witness.compatibility != WitnessCompatibility::Compatible) {
                continue;
            }
            const std::set<std::string> witness_facts(
                witness.model_fact_ids.begin(), witness.model_fact_ids.end());
            for (const FrontierPathExemplar &path :
                 witness.path_exemplars) {
                if (path.compatibility != WitnessCompatibility::Compatible) {
                    continue;
                }
                for (const FrontierPathStep &step : path.forward_steps) {
                    if (step.kind != FrontierPathStepKind::ModelArc ||
                        !step.model_fact_id ||
                        !witness_facts.contains(*step.model_fact_id) ||
                        !candidate_fact_ids.contains(*step.model_fact_id)) {
                        continue;
                    }
                    const ModelFact *fact =
                        find_model_fact(overlay, *step.model_fact_id);
                    const auto source = nodes.find(step.source_node_id);
                    const auto target = nodes.find(step.target_node_id);
                    if (fact == nullptr ||
                        fact->kind != ModelFactKind::ClockRelation ||
                        !fact->target_semantic_node_id ||
                        source == nodes.end() || target == nodes.end() ||
                        source->second->semantic_node_id !=
                            fact->source_semantic_node_id ||
                        target->second->semantic_node_id !=
                            *fact->target_semantic_node_id) {
                        continue;
                    }
                    witnessed_clock_fact_ids.insert(fact->fact_id);
                }
            }
        }
        std::vector<const ModelFact *> clock_facts;
        for (const std::string &fact_id : witnessed_clock_fact_ids) {
            const ModelFact *fact = find_model_fact(overlay, fact_id);
            if (fact != nullptr) clock_facts.push_back(fact);
        }
        if (clock_facts.empty()) {
            timing.uncertainty_reasons.insert(
                timing.uncertainty_reasons.end(),
                {"clock source is not closed by a witness-bound typed clock relation",
                 "epoch/quantum/jitter/wrap are not closed by available model facts",
                 "start/end event identity is not closed by available model facts"});
        } else if (clock_facts.size() != 1) {
            timing.uncertainty_reasons.push_back(
                "multiple witness-bound clock relations conflict with the uniqueness requirement");
        } else {
            const ModelFact &fact = *clock_facts.front();
            const ModelClockRelationV2 *clock =
                fact.clock_relation ? &*fact.clock_relation : nullptr;
            const bool complete = clock != nullptr && clock->clock_source &&
                clock->unit && clock->epoch && clock->quantum &&
                clock->jitter && clock->wrap && clock->start_event &&
                clock->end_event && clock->endpoint &&
                clock->scope_schema && clock->generation_schema;
            const TimingEndpoint interval_endpoint =
                interval.lower_closed == interval.upper_closed
                    ? (interval.lower_closed ? TimingEndpoint::Closed
                                             : TimingEndpoint::Open)
                    : TimingEndpoint::Mixed;
            const auto model_endpoint = [&]() {
                if (!clock || !clock->endpoint) return TimingEndpoint::Unknown;
                switch (*clock->endpoint) {
                case ModelClockEndpoint::Open: return TimingEndpoint::Open;
                case ModelClockEndpoint::Closed: return TimingEndpoint::Closed;
                case ModelClockEndpoint::Mixed: return TimingEndpoint::Mixed;
                case ModelClockEndpoint::Unknown: return TimingEndpoint::Unknown;
                }
                return TimingEndpoint::Unknown;
            }();
            const bool wrap_complete = clock && clock->wrap &&
                *clock->wrap != ModelClockWrap::Unknown &&
                (((*clock->wrap == ModelClockWrap::Modulo ||
                   *clock->wrap == ModelClockWrap::Saturating) &&
                  clock->wrap_value) ||
                 (*clock->wrap == ModelClockWrap::None &&
                  !clock->wrap_value));
            const bool compatible = complete &&
                fact.certainty == Certainty::Modelled &&
                to_string(*clock->unit) == interval.unit &&
                *clock->scope_schema == candidate.action.scope_schema &&
                *clock->generation_schema ==
                    candidate.action.generation_schema &&
                model_endpoint == interval_endpoint && wrap_complete;
            if (compatible && intervals.size() == 1) {
                timing.status = TimingStatus::Exact;
                timing.clock_source = *clock->clock_source;
                timing.unit = to_string(*clock->unit);
                timing.epoch = *clock->epoch;
                timing.quantum = *clock->quantum;
                timing.jitter = *clock->jitter;
                timing.wrap = to_string(*clock->wrap);
                if (clock->wrap_value) {
                    timing.wrap = *timing.wrap + ":" +
                        std::to_string(*clock->wrap_value);
                }
                timing.start_event = *clock->start_event;
                timing.end_event = *clock->end_event;
                timing.comparison_endpoint = interval_endpoint;
                timing.scope_schema = *clock->scope_schema;
                timing.generation_schema = *clock->generation_schema;
                timing.uncertainty_reasons.clear();
            } else {
                if (!complete) {
                    timing.uncertainty_reasons.push_back(
                        "witness-bound clock relation has missing fixed fields");
                }
                if (fact.certainty != Certainty::Modelled) {
                    timing.uncertainty_reasons.push_back(
                        "witness-bound clock relation is UNKNOWN rather than MODELLED");
                }
                if (complete &&
                    to_string(*clock->unit) != interval.unit) {
                    timing.uncertainty_reasons.push_back(
                        "clock unit conflicts with the typed temporal interval");
                }
                if (complete &&
                    (*clock->scope_schema != candidate.action.scope_schema ||
                     *clock->generation_schema !=
                         candidate.action.generation_schema)) {
                    timing.uncertainty_reasons.push_back(
                        "clock relation scope/generation is incompatible with the action witness");
                }
                if (complete && model_endpoint != interval_endpoint) {
                    timing.uncertainty_reasons.push_back(
                        "clock comparison endpoint conflicts with the temporal interval");
                }
                if (!wrap_complete) {
                    timing.uncertainty_reasons.push_back(
                        "clock wrap semantics are missing or UNKNOWN");
                }
            }
        }
    }
    const std::string &capability = candidate.action.timing_capability;
    if (capability == "delay") timing.mutation_actions.push_back(TimingMutationAction::Delay);
    else if (capability == "pause") timing.mutation_actions.push_back(TimingMutationAction::Pause);
    else if (capability == "drop") timing.mutation_actions.push_back(TimingMutationAction::Drop);
    else if (capability == "repeat") timing.mutation_actions.push_back(TimingMutationAction::Repeat);
    else if (capability == "reorder") timing.mutation_actions.push_back(TimingMutationAction::Reorder);
    else if (capability == "interval") timing.mutation_actions.push_back(TimingMutationAction::ChangeInterval);
    else if (!capability.empty() && capability != "none") {
        timing.uncertainty_reasons.push_back(
            "unrecognized timing capability token: " + capability);
    }
    if (timing.mutation_actions.empty() && !intervals.empty()) {
        timing.mutation_actions.push_back(TimingMutationAction::ChangeInterval);
    }
    sort_unique(timing.mutation_actions);
    sort_unique(timing.uncertainty_reasons);
    return timing;
}

bool prerequisite_fact_kind(ModelFactKind kind) {
    return kind == ModelFactKind::EventLink ||
           kind == ModelFactKind::TimerTransition ||
           kind == ModelFactKind::QueueTransition ||
           kind == ModelFactKind::LifecycleTransition ||
           kind == ModelFactKind::PersistenceTransition;
}

std::vector<PrerequisiteChoice> derive_prerequisites(
    const FrontierCandidate &candidate, const ModelFactOverlay &overlay) {
    std::set<std::string> witness_fact_ids;
    for (const FrontierWitness &witness : candidate.witnesses) {
        witness_fact_ids.insert(
            witness.model_fact_ids.begin(), witness.model_fact_ids.end());
    }
    std::unordered_map<std::string, const ExternalAction *> actions;
    for (const ExternalAction &action : overlay.external_actions) {
        actions[action.external_action_id] = &action;
    }
    std::vector<PrerequisiteChoice> choices;
    for (const std::string &fact_id : witness_fact_ids) {
        const ModelFact *fact = find_model_fact(overlay, fact_id);
        if (fact == nullptr || !prerequisite_fact_kind(fact->kind)) {
            continue;
        }
        std::set<std::string> prerequisite_action_ids;
        for (const BoundaryAttachment &attachment : overlay.boundary_attachments) {
            if (attachment.semantic_node_id == fact->source_semantic_node_id &&
                actions.contains(attachment.external_action_id)) {
                prerequisite_action_ids.insert(attachment.external_action_id);
            }
        }
        if (prerequisite_action_ids.empty()) {
            continue;
        }
        PrerequisiteChoice choice;
        choice.choice_id = stable_id(
            "prerequisite-choice", candidate.candidate_id + '\0' + fact_id);
        for (const std::string &prerequisite_action_id :
             prerequisite_action_ids) {
            PrerequisiteDag dag;
            dag.dag_id = stable_id(
                "prerequisite-dag",
                choice.choice_id + '\0' + prerequisite_action_id);
            if (prerequisite_action_id ==
                candidate.action.external_action_id) {
                dag.status = PrerequisiteStatus::PartialOrderUnknown;
                dag.uncertainty_reasons.push_back(
                    "lifecycle prerequisite aliases the target action and forms a cycle");
            } else {
                const ExternalAction &prerequisite =
                    *actions.at(prerequisite_action_id);
                PrerequisiteStep before;
                before.step_id = stable_id(
                    "prerequisite-step",
                    dag.dag_id + '\0' + prerequisite_action_id);
                before.action_id = prerequisite_action_id;
                before.operation = prerequisite.operation;
                PrerequisiteStep target;
                target.step_id = stable_id(
                    "prerequisite-step",
                    dag.dag_id + '\0' +
                        candidate.action.external_action_id);
                target.action_id = candidate.action.external_action_id;
                target.operation = candidate.action.operation;
                target.predecessor_step_ids = {before.step_id};
                dag.steps = {std::move(before), std::move(target)};
                dag.status = fact->certainty == Certainty::Modelled
                                 ? PrerequisiteStatus::Complete
                                 : PrerequisiteStatus::PartialOrderUnknown;
                if (dag.status == PrerequisiteStatus::PartialOrderUnknown) {
                    dag.uncertainty_reasons.push_back(
                        "prerequisite model fact is UNKNOWN rather than MODELLED");
                }
            }
            choice.alternatives.push_back(std::move(dag));
        }
        std::sort(
            choice.alternatives.begin(), choice.alternatives.end(),
            [](const PrerequisiteDag &left, const PrerequisiteDag &right) {
                return left.dag_id < right.dag_id;
            });
        choices.push_back(std::move(choice));
    }
    std::sort(
        choices.begin(), choices.end(),
        [](const PrerequisiteChoice &left, const PrerequisiteChoice &right) {
            return left.choice_id < right.choice_id;
        });
    return choices;
}

std::vector<PrerequisiteChoice> derive_control_guard_prerequisites(
    const FrontierCandidate &target_candidate,
    const TypedPropertyIr &property, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph, const ApInfluenceCones &cones,
    const FrontierCandidates &frontier, const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences) {
    std::vector<PrerequisiteChoice> choices;
    const AtomicProposition *ap = find_ap(
        property, target_candidate.ap_id);
    if (ap == nullptr) return choices;
    const ValueBindingResult target_binding =
        bind_action_to_predicate_reference(
            target_candidate, *ap, bindings, graph, cones, overlay,
            predicate_occurrences);
    if (!target_binding.selector_id) return choices;

    std::set<std::string> target_path_nodes;
    for (const FrontierWitness &witness : target_candidate.witnesses) {
        if (witness.compatibility != WitnessCompatibility::Compatible) {
            continue;
        }
        target_path_nodes.insert(witness.boundary_node_id);
        for (const FrontierPathExemplar &path : witness.path_exemplars) {
            if (path.compatibility != WitnessCompatibility::Compatible) {
                continue;
            }
            target_path_nodes.insert(path.meet_node_id);
            target_path_nodes.insert(path.root_node_id);
            for (const FrontierPathStep &step : path.forward_steps) {
                target_path_nodes.insert(step.source_node_id);
                target_path_nodes.insert(step.target_node_id);
            }
            for (const FrontierPathStep &step : path.root_steps) {
                target_path_nodes.insert(step.source_node_id);
                target_path_nodes.insert(step.target_node_id);
            }
        }
    }
    std::unordered_map<std::string, const InfluenceEdge *> graph_edges;
    for (const InfluenceEdge &edge : graph.edges) {
        graph_edges.emplace(edge.edge_id, &edge);
    }

    std::vector<const FrontierCandidate *> guards;
    for (const FrontierCandidate &candidate : frontier.candidates) {
        if (candidate.candidate_id == target_candidate.candidate_id ||
            candidate.ap_id != target_candidate.ap_id ||
            candidate.disposition != FrontierDisposition::Actionable ||
            candidate.action.external_action_id ==
                target_candidate.action.external_action_id ||
            candidate.action.scope_schema !=
                target_candidate.action.scope_schema ||
            candidate.action.generation_schema !=
                target_candidate.action.generation_schema) {
            continue;
        }
        const ValueBindingResult candidate_binding =
            bind_action_to_predicate_reference(
                candidate, *ap, bindings, graph, cones, overlay,
                predicate_occurrences);
        if (candidate_binding.selector_id) continue;
        guards.push_back(&candidate);
    }
    std::sort(
        guards.begin(), guards.end(),
        [](const FrontierCandidate *left,
           const FrontierCandidate *right) {
            return left->candidate_id < right->candidate_id;
        });
    for (const FrontierCandidate *guard : guards) {
        bool control_reaches_target_path = false;
        bool all_control_must = true;
        std::vector<std::string> control_edge_ids;
        for (const FrontierWitness &witness : guard->witnesses) {
            if (witness.compatibility != WitnessCompatibility::Compatible) {
                continue;
            }
            for (const FrontierPathExemplar &path :
                 witness.path_exemplars) {
                if (path.compatibility !=
                    WitnessCompatibility::Compatible) {
                    continue;
                }
                for (const FrontierPathStep &step : path.forward_steps) {
                    if (step.kind != FrontierPathStepKind::GraphEdge ||
                        !step.graph_edge_id) {
                        continue;
                    }
                    const auto edge = graph_edges.find(*step.graph_edge_id);
                    if (edge == graph_edges.end() ||
                        edge->second->kind != RelationKind::Control ||
                        !target_path_nodes.contains(
                            edge->second->target_node_id)) {
                        continue;
                    }
                    control_reaches_target_path = true;
                    all_control_must = all_control_must &&
                        edge->second->certainty == Certainty::Must;
                    control_edge_ids.push_back(edge->second->edge_id);
                }
            }
        }
        if (!control_reaches_target_path) continue;
        sort_unique(control_edge_ids);
        std::ostringstream material;
        material << target_candidate.candidate_id << '\0'
                 << guard->candidate_id;
        for (const std::string &edge_id : control_edge_ids) {
            material << '\0' << edge_id;
        }
        PrerequisiteChoice choice;
        choice.choice_id = stable_id(
            "prerequisite-control-choice", material.str());
        PrerequisiteDag dag;
        dag.dag_id = stable_id(
            "prerequisite-control-dag", material.str());
        dag.status = PrerequisiteStatus::PartialOrderUnknown;
        if (!all_control_must) {
            dag.uncertainty_reasons.push_back(
                "control dependence reaching the value path is MAY rather than MUST");
        }
        dag.uncertainty_reasons.push_back(
            "static control dependence does not close external-action temporal order or persistence");
        PrerequisiteStep before;
        before.step_id = stable_id(
            "prerequisite-control-step",
            dag.dag_id + '\0' + guard->action.external_action_id);
        before.action_id = guard->action.external_action_id;
        before.operation = guard->action.operation;
        PrerequisiteStep target;
        target.step_id = stable_id(
            "prerequisite-control-step",
            dag.dag_id + '\0' +
                target_candidate.action.external_action_id);
        target.action_id = target_candidate.action.external_action_id;
        target.operation = target_candidate.action.operation;
        target.predecessor_step_ids = {before.step_id};
        dag.steps = {std::move(before), std::move(target)};
        sort_unique(dag.uncertainty_reasons);
        choice.alternatives.push_back(std::move(dag));
        choices.push_back(std::move(choice));
    }
    std::sort(
        choices.begin(), choices.end(),
        [](const PrerequisiteChoice &left,
           const PrerequisiteChoice &right) {
            return left.choice_id < right.choice_id;
        });
    return choices;
}

const JointActionRequirement *joint_requirement(
    const std::vector<JointActionRequirement> &requirements,
    const FrontierCandidate &candidate) {
    const auto found = std::find_if(
        requirements.begin(), requirements.end(),
        [&](const JointActionRequirement &requirement) {
            return std::find(
                       requirement.frontier_candidate_ids.begin(),
                       requirement.frontier_candidate_ids.end(),
                       candidate.candidate_id) !=
                   requirement.frontier_candidate_ids.end();
        });
    return found == requirements.end() ? nullptr : &*found;
}

struct PredicateActionBranch {
    std::set<std::string> selector_ids;
    bool explicit_conjunction = false;
};

std::vector<PredicateActionBranch> predicate_action_branches(
    const ExpressionStructure &expression) {
    const bool is_or = expression.node_kind == "boolean" &&
        expression.operation &&
        (*expression.operation == "||" || *expression.operation == "or");
    const bool is_and = expression.node_kind == "boolean" &&
        expression.operation &&
        (*expression.operation == "&&" || *expression.operation == "and");
    if (is_or) {
        std::vector<PredicateActionBranch> result;
        for (const ExpressionStructure &operand : expression.operands) {
            std::vector<PredicateActionBranch> alternatives =
                predicate_action_branches(operand);
            result.insert(
                result.end(), std::make_move_iterator(alternatives.begin()),
                std::make_move_iterator(alternatives.end()));
        }
        return result;
    }
    if (is_and) {
        std::vector<PredicateActionBranch> result(1);
        for (const ExpressionStructure &operand : expression.operands) {
            const std::vector<PredicateActionBranch> nested =
                predicate_action_branches(operand);
            std::vector<PredicateActionBranch> product;
            for (const PredicateActionBranch &left : result) {
                for (const PredicateActionBranch &right : nested) {
                    PredicateActionBranch branch;
                    branch.selector_ids = left.selector_ids;
                    branch.selector_ids.insert(
                        right.selector_ids.begin(),
                        right.selector_ids.end());
                    branch.explicit_conjunction = true;
                    product.push_back(std::move(branch));
                }
            }
            result = std::move(product);
        }
        return result;
    }
    PredicateActionBranch leaf;
    collect_references(expression, leaf.selector_ids);
    return {std::move(leaf)};
}

bool closed_candidate_context(const FrontierCandidate &candidate) {
    const FrontierCompletenessLedger &ledger =
        candidate.evidence.completeness;
    return ledger.model_vm_complete &&
           ledger.attachment_enumeration_complete &&
           ledger.forward_enumeration_complete && ledger.cone_complete &&
           ledger.compatibility_complete && ledger.gap_reasons.empty();
}

struct CandidateJointSummary {
    const FrontierCandidate *candidate = nullptr;
    ValueBindingResult binding;
    std::optional<ExternalPayloadProjection> projection;
    bool exact_identity_projection = false;
};

std::vector<JointActionRequirement> derive_automatic_joint_requirements(
    const TypedPropertyIr &property, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph, const ApInfluenceCones &cones,
    const FrontierCandidates &frontier, const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const ContextualValueTransferIndex &value_transfers) {
    std::vector<CandidateJointSummary> candidates;
    for (const FrontierCandidate &candidate : frontier.candidates) {
        if (candidate.disposition != FrontierDisposition::Actionable) {
            continue;
        }
        const AtomicProposition *ap = find_ap(property, candidate.ap_id);
        if (ap == nullptr) continue;
        CandidateJointSummary summary;
        summary.candidate = &candidate;
        summary.binding = bind_action_to_predicate_reference(
            candidate, *ap, bindings, graph, cones, overlay,
            predicate_occurrences);
        if (summary.binding.selector_id &&
            !summary.binding.projection_targets.empty()) {
            summary.projection = compose_external_payload_projection(
                candidate, graph, overlay, value_transfers,
                summary.binding.projection_targets);
            const PayloadPredicateRewrite rewrite =
                rewrite_predicate_in_payload_coordinate(
                    ap->predicate, *summary.binding.selector_id,
                    *summary.projection);
            summary.exact_identity_projection =
                rewrite.predicate.has_value() && rewrite.identity_projection;
        }
        candidates.push_back(std::move(summary));
    }
    std::sort(
        candidates.begin(), candidates.end(),
        [](const CandidateJointSummary &left,
           const CandidateJointSummary &right) {
            return left.candidate->candidate_id <
                   right.candidate->candidate_id;
        });

    std::vector<JointActionRequirement> result;
    for (const AtomicProposition &ap : property.atomic_propositions) {
        const std::vector<PredicateActionBranch> branches =
            predicate_action_branches(ap.predicate);
        for (const PredicateActionBranch &branch : branches) {
            if (!branch.explicit_conjunction ||
                branch.selector_ids.size() < 2) {
                continue;
            }
            std::vector<const CandidateJointSummary *> members;
            for (const CandidateJointSummary &summary : candidates) {
                if (summary.candidate->ap_id != ap.ap_id) continue;
                const bool possible = std::any_of(
                    summary.binding.potential_selector_ids.begin(),
                    summary.binding.potential_selector_ids.end(),
                    [&](const std::string &selector_id) {
                        return branch.selector_ids.contains(selector_id);
                    });
                if (possible ||
                    (summary.binding.selector_id &&
                     branch.selector_ids.contains(
                         *summary.binding.selector_id))) {
                    members.push_back(&summary);
                }
            }
            std::set<std::string> action_ids;
            std::set<std::string> candidate_ids;
            std::map<std::string, std::set<std::string>>
                selector_actions;
            std::set<std::string> exact_selectors;
            std::set<std::string> scopes;
            std::set<std::string> generations;
            bool complete = true;
            for (const CandidateJointSummary *member : members) {
                const FrontierCandidate &candidate = *member->candidate;
                candidate_ids.insert(candidate.candidate_id);
                action_ids.insert(candidate.action.external_action_id);
                scopes.insert(candidate.action.scope_schema);
                generations.insert(candidate.action.generation_schema);
                complete = complete && member->binding.selector_id &&
                    member->exact_identity_projection &&
                    closed_candidate_context(candidate);
                if (member->binding.selector_id &&
                    branch.selector_ids.contains(
                        *member->binding.selector_id)) {
                    exact_selectors.insert(*member->binding.selector_id);
                    selector_actions[*member->binding.selector_id].insert(
                        candidate.action.external_action_id);
                }
            }
            if (action_ids.size() < 2) continue;
            complete = complete && exact_selectors == branch.selector_ids &&
                scopes.size() == 1 && generations.size() == 1 &&
                std::all_of(
                    selector_actions.begin(), selector_actions.end(),
                    [](const auto &entry) {
                        return entry.second.size() == 1;
                    });
            std::ostringstream material;
            material << "typed-source-conjunction" << '\0' << ap.ap_id;
            for (const std::string &selector : branch.selector_ids) {
                material << '\0' << selector;
            }
            for (const std::string &action_id : action_ids) {
                material << '\0' << action_id;
            }
            JointActionRequirement requirement;
            requirement.requirement_id = stable_id(
                "joint-source", material.str());
            requirement.frontier_candidate_ids.assign(
                candidate_ids.begin(), candidate_ids.end());
            requirement.action_ids.assign(
                action_ids.begin(), action_ids.end());
            requirement.complete = complete;
            result.push_back(std::move(requirement));
        }
    }

    std::unordered_map<std::string, const BoundaryAttachment *> attachments;
    for (const BoundaryAttachment &attachment :
         overlay.boundary_attachments) {
        attachments.emplace(attachment.attachment_id, &attachment);
    }
    for (const ModelJointActionConstraint &constraint :
         overlay.joint_action_constraints) {
        if (constraint.combination ==
            ModelJointActionOperator::AnySufficient) {
            continue;
        }
        const std::set<std::string> participant_nodes(
            constraint.participant_semantic_node_ids.begin(),
            constraint.participant_semantic_node_ids.end());
        for (const AtomicProposition &ap : property.atomic_propositions) {
            std::vector<const CandidateJointSummary *> members;
            std::set<std::string> covered_participants;
            for (const CandidateJointSummary &summary : candidates) {
                if (summary.candidate->ap_id != ap.ap_id) continue;
                bool witnessed = false;
                for (const FrontierWitness &witness :
                     summary.candidate->witnesses) {
                    const auto attachment =
                        attachments.find(witness.attachment_id);
                    if (attachment != attachments.end() &&
                        witness.compatibility ==
                            WitnessCompatibility::Compatible &&
                        participant_nodes.contains(
                            attachment->second->semantic_node_id)) {
                        witnessed = true;
                        covered_participants.insert(
                            attachment->second->semantic_node_id);
                    }
                }
                if (witnessed) members.push_back(&summary);
            }
            std::set<std::string> action_ids;
            std::set<std::string> candidate_ids;
            std::set<std::string> selectors;
            bool complete = constraint.certainty == Certainty::Modelled &&
                constraint.combination ==
                    ModelJointActionOperator::AllRequired &&
                constraint.participant_set_complete &&
                covered_participants == participant_nodes;
            for (const CandidateJointSummary *member : members) {
                const FrontierCandidate &candidate = *member->candidate;
                action_ids.insert(candidate.action.external_action_id);
                candidate_ids.insert(candidate.candidate_id);
                complete = complete && member->binding.selector_id &&
                    member->exact_identity_projection &&
                    closed_candidate_context(candidate) &&
                    candidate.action.scope_schema ==
                        constraint.scope_schema &&
                    candidate.action.generation_schema ==
                        constraint.generation_schema;
                if (member->binding.selector_id) {
                    selectors.insert(*member->binding.selector_id);
                }
            }
            if (action_ids.size() < 2) continue;
            complete = complete && selectors.size() == action_ids.size();
            JointActionRequirement requirement;
            requirement.requirement_id = stable_id(
                "joint-model",
                constraint.constraint_id + '\0' + ap.ap_id);
            requirement.frontier_candidate_ids.assign(
                candidate_ids.begin(), candidate_ids.end());
            requirement.action_ids.assign(
                action_ids.begin(), action_ids.end());
            requirement.model_fact_ids = {constraint.constraint_id};
            requirement.complete = complete;
            result.push_back(std::move(requirement));
        }
    }

    std::sort(
        result.begin(), result.end(),
        [](const JointActionRequirement &left,
           const JointActionRequirement &right) {
            return left.requirement_id < right.requirement_id;
        });
    std::map<std::string, std::size_t> owner_counts;
    for (const JointActionRequirement &requirement : result) {
        for (const std::string &candidate_id :
             requirement.frontier_candidate_ids) {
            ++owner_counts[candidate_id];
        }
    }
    for (JointActionRequirement &requirement : result) {
        if (std::any_of(
                requirement.frontier_candidate_ids.begin(),
                requirement.frontier_candidate_ids.end(),
                [&](const std::string &candidate_id) {
                    return owner_counts[candidate_id] != 1;
                })) {
            requirement.complete = false;
        }
    }
    return result;
}

ActionHyperedge build_hyperedge(
    const FrontierCandidate &candidate, const JointActionRequirement *joint) {
    ActionHyperedge edge;
    if (joint == nullptr) {
        edge.action_ids = {candidate.action.external_action_id};
        edge.claim = JointActionClaim::SingleAction;
        edge.hyperedge_id = stable_id(
            "action-hyperedge", candidate.action.external_action_id);
        return edge;
    }
    edge.action_ids = joint->action_ids;
    sort_unique(edge.action_ids);
    edge.claim = joint->complete ? JointActionClaim::JointRequired
                                 : JointActionClaim::JointUnknown;
    std::string material = joint->requirement_id;
    for (const std::string &action_id : edge.action_ids) {
        material.push_back('\0');
        material.append(action_id);
    }
    edge.hyperedge_id = stable_id("action-hyperedge", material);
    return edge;
}

std::vector<std::string> joint_errors(
    const JointActionRequirement &joint,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay) {
    std::vector<std::string> errors;
    if (joint.requirement_id.empty()) {
        errors.push_back("joint requirement has empty ID");
    }
    if (joint.frontier_candidate_ids.size() < 2 ||
        joint.action_ids.size() < 2) {
        errors.push_back(
            "joint requirement must contain at least two candidates and actions");
    }
    std::set<std::string> candidate_ids;
    std::set<std::string> action_ids;
    if (std::set<std::string>(
            joint.frontier_candidate_ids.begin(),
            joint.frontier_candidate_ids.end()).size() !=
        joint.frontier_candidate_ids.size()) {
        errors.push_back("joint requirement has duplicate candidate IDs");
    }
    if (std::set<std::string>(
            joint.action_ids.begin(), joint.action_ids.end()).size() !=
        joint.action_ids.size()) {
        errors.push_back("joint requirement has duplicate action IDs");
    }
    if (std::set<std::string>(
            joint.model_fact_ids.begin(), joint.model_fact_ids.end()).size() !=
        joint.model_fact_ids.size()) {
        errors.push_back("joint requirement has duplicate model-fact IDs");
    }
    std::map<std::string, std::string> candidate_actions;
    for (const FrontierCandidate &candidate : frontier.candidates) {
        candidate_ids.insert(candidate.candidate_id);
        action_ids.insert(candidate.action.external_action_id);
        candidate_actions[candidate.candidate_id] =
            candidate.action.external_action_id;
    }
    for (const std::string &candidate_id : joint.frontier_candidate_ids) {
        if (!candidate_ids.contains(candidate_id)) {
            errors.push_back(
                "joint requirement has unknown candidate: " + candidate_id);
        }
    }
    for (const std::string &action_id : joint.action_ids) {
        if (!action_ids.contains(action_id) ||
            find_overlay_action(overlay, action_id) == nullptr) {
            errors.push_back(
                "joint requirement has unknown action: " + action_id);
        }
    }
    for (const std::string &fact_id : joint.model_fact_ids) {
        if (find_model_fact(overlay, fact_id) == nullptr) {
            errors.push_back(
                "joint requirement has unknown model fact: " + fact_id);
        }
    }
    std::set<std::string> actions_from_candidates;
    for (const std::string &candidate_id : joint.frontier_candidate_ids) {
        const auto found = candidate_actions.find(candidate_id);
        if (found != candidate_actions.end()) {
            actions_from_candidates.insert(found->second);
        }
    }
    const std::set<std::string> declared_actions(
        joint.action_ids.begin(), joint.action_ids.end());
    if (actions_from_candidates != declared_actions) {
        errors.push_back(
            "joint requirement candidate/action relation is not closed");
    }
    if (joint.complete && joint.model_fact_ids.empty()) {
        errors.push_back(
            "complete joint requirement has no certificate-bound model fact");
    }
    return errors;
}

std::string recipe_material(
    const FrontierCandidate &candidate, const ActionHyperedge &edge,
    const std::string &query_sha256) {
    std::string material = candidate.candidate_id + '\0' + candidate.cone_id +
                           '\0' + candidate.ap_id + '\0' + query_sha256;
    for (const std::string &action_id : edge.action_ids) {
        material.push_back('\0');
        material.append(action_id);
    }
    return material;
}

bool dag_has_cycle(const PrerequisiteDag &dag) {
    std::unordered_map<std::string, std::vector<std::string>> successors;
    std::unordered_map<std::string, std::size_t> indegree;
    for (const PrerequisiteStep &step : dag.steps) {
        indegree.emplace(step.step_id, 0);
    }
    for (const PrerequisiteStep &step : dag.steps) {
        for (const std::string &predecessor : step.predecessor_step_ids) {
            if (!indegree.contains(predecessor)) {
                return true;
            }
            successors[predecessor].push_back(step.step_id);
            ++indegree[step.step_id];
        }
    }
    std::vector<std::string> ready;
    for (const auto &[step_id, degree] : indegree) {
        if (degree == 0) ready.push_back(step_id);
    }
    std::size_t visited = 0;
    while (!ready.empty()) {
        const std::string current = ready.back();
        ready.pop_back();
        ++visited;
        for (const std::string &successor : successors[current]) {
            if (--indegree[successor] == 0) ready.push_back(successor);
        }
    }
    return visited != indegree.size();
}

bool topological_steps(
    const MutationRecipe &recipe, std::vector<std::string> &result) {
    result.clear();
    std::map<std::string, const PrerequisiteStep *> steps;
    std::map<std::string, std::vector<std::string>> successors;
    std::map<std::string, std::size_t> indegree;
    std::set<std::string> action_ids;
    for (const PrerequisiteChoice &choice : recipe.prerequisite_choices) {
        // An OR group has no deterministic replay until the executor records a
        // selected branch.  A singleton group is already resolved.
        if (choice.alternatives.size() != 1) return false;
        const PrerequisiteDag &dag = choice.alternatives.front();
        if (dag.status != PrerequisiteStatus::Complete ||
            !dag.uncertainty_reasons.empty() || dag.steps.empty()) {
            return false;
        }
        for (const PrerequisiteStep &step : dag.steps) {
            if (step.step_id.empty() || step.action_id.empty() ||
                step.operation.empty() || !steps.emplace(step.step_id, &step).second ||
                !action_ids.insert(step.action_id).second) {
                return false;
            }
            indegree.emplace(step.step_id, 0);
        }
    }
    for (const auto &[step_id, step] : steps) {
        for (const std::string &predecessor : step->predecessor_step_ids) {
            if (!steps.contains(predecessor)) return false;
            successors[predecessor].push_back(step_id);
            ++indegree[step_id];
        }
    }
    std::set<std::string> ready;
    for (const auto &[step_id, degree] : indegree) {
        if (degree == 0) ready.insert(step_id);
    }
    while (!ready.empty()) {
        const std::string current = *ready.begin();
        ready.erase(ready.begin());
        result.push_back(current);
        for (const std::string &successor : successors[current]) {
            if (--indegree[successor] == 0) ready.insert(successor);
        }
    }
    if (result.size() != steps.size()) {
        result.clear();
        return false;
    }
    return true;
}

bool replay_action_mutations_executable(const MutationRecipe &recipe) {
    if (recipe.action_mutations.size() !=
        recipe.action_hyperedge.action_ids.size()) {
        return false;
    }
    const std::set<std::string> expected_actions(
        recipe.action_hyperedge.action_ids.begin(),
        recipe.action_hyperedge.action_ids.end());
    std::set<std::string> observed_actions;
    for (const ActionMutation &mutation : recipe.action_mutations) {
        observed_actions.insert(mutation.action_id);
        if (mutation.mutation_kind == MutationKind::Unknown ||
            mutation.direction == MutationDirection::Unknown ||
            mutation.suggested_values.empty() ||
            !mutation.unknown_reasons.empty()) {
            return false;
        }
    }
    return observed_actions == expected_actions;
}

std::string json_escape(const std::string &value) {
    std::ostringstream stream;
    stream << '"';
    for (const unsigned char character : value) {
        switch (character) {
            case '"': stream << "\\\""; break;
            case '\\': stream << "\\\\"; break;
            case '\b': stream << "\\b"; break;
            case '\f': stream << "\\f"; break;
            case '\n': stream << "\\n"; break;
            case '\r': stream << "\\r"; break;
            case '\t': stream << "\\t"; break;
            default:
                if (character < 0x20) {
                    constexpr char digits[] = "0123456789abcdef";
                    stream << "\\u00" << digits[character >> 4]
                           << digits[character & 0x0f];
                } else {
                    stream << static_cast<char>(character);
                }
        }
    }
    stream << '"';
    return stream.str();
}

template <typename T, typename Render>
std::string json_array(const std::vector<T> &values, Render render) {
    std::ostringstream stream;
    stream << '[';
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0) stream << ',';
        stream << render(values[index]);
    }
    stream << ']';
    return stream.str();
}

std::string json_strings(const std::vector<std::string> &values) {
    return json_array(values, [](const std::string &value) {
        return json_escape(value);
    });
}

std::string nullable_string(const std::optional<std::string> &value) {
    return value ? json_escape(*value) : "null";
}

std::string nullable_number(const std::optional<double> &value) {
    if (!value) return "null";
    std::ostringstream stream;
    stream.precision(17);
    stream << *value;
    return stream.str();
}

std::string nullable_bool(const std::optional<bool> &value) {
    if (!value) return "null";
    return *value ? "true" : "false";
}

std::string value_type_json(const ValueType &type) {
    const char *kind = "unknown";
    switch (type.kind) {
        case ValueKind::Boolean: kind = "bool"; break;
        case ValueKind::Integer: kind = "integer"; break;
        case ValueKind::Floating: kind = "floating"; break;
        case ValueKind::Enumeration: kind = "enum"; break;
        case ValueKind::BitVector: kind = "bitvector"; break;
        case ValueKind::Timestamp: kind = "timestamp"; break;
        case ValueKind::Duration: kind = "duration"; break;
        case ValueKind::Pointer: kind = "pointer"; break;
        case ValueKind::Record: kind = "record"; break;
        case ValueKind::Array: kind = "array"; break;
        case ValueKind::Unknown: break;
    }
    std::ostringstream stream;
    stream << "{\"kind\":" << json_escape(kind)
           << ",\"canonical\":" << json_escape(type.canonical);
    if (type.bit_width) stream << ",\"bit_width\":" << *type.bit_width;
    if (type.is_signed) stream << ",\"signed\":" << (*type.is_signed ? "true" : "false");
    if (type.unit) stream << ",\"unit\":" << json_escape(*type.unit);
    stream << '}';
    return stream.str();
}

std::string solver_query_json(const SolverQueryEvidence &query) {
    std::ostringstream stream;
    stream << "{\"query_id\":" << json_escape(query.query_id)
           << ",\"query_sha256\":" << json_escape(query.query_sha256)
           << ",\"encoding_version\":" << json_escape(query.encoding_version)
           << ",\"solver\":" << json_escape(query.solver)
           << ",\"solver_version\":" << json_escape(query.solver_version)
           << ",\"timeout_ms\":" << query.timeout_ms
           << ",\"outcome\":" << json_escape(to_string(query.outcome))
           << ",\"flip_class\":" << json_escape(to_string(query.flip_class))
           << ",\"assumption_literals\":" << json_strings(query.assumption_literals)
           << ",\"model\":" << json_strings(query.model)
           << ",\"unsat_core\":" << json_strings(query.unsat_core)
           << ",\"unknown_reason\":" << nullable_string(query.unknown_reason)
           << '}';
    return stream.str();
}

std::string evidence_axis_json(
    const std::string &state, std::vector<std::string> evidence_ids,
    std::vector<std::string> reasons) {
    sort_unique(evidence_ids);
    sort_unique(reasons);
    if ((state == "UNKNOWN" || state == "UNAVAILABLE") && reasons.empty()) {
        reasons.push_back("axis has no confirming evidence");
    }
    return "{\"state\":" + json_escape(state) +
           ",\"evidence_ids\":" + json_strings(evidence_ids) +
           ",\"reasons\":" + json_strings(reasons) + '}';
}

const char *frontier_state(ReachabilityVerdict value) {
    switch (value) {
        case ReachabilityVerdict::StaticWitness: return "STATIC_WITNESS";
        case ReachabilityVerdict::ModelledWitness: return "MODELLED_WITNESS";
        case ReachabilityVerdict::Unknown: return "UNKNOWN";
        case ReachabilityVerdict::NoStaticWitness: return "NO_STATIC_WITNESS";
    }
    return "UNKNOWN";
}

const char *frontier_state(ControllabilityVerdict value) {
    switch (value) {
        case ControllabilityVerdict::Direct: return "DIRECT";
        case ControllabilityVerdict::Sequence: return "SEQUENCE";
        case ControllabilityVerdict::Timing: return "TIMING";
        case ControllabilityVerdict::Environment: return "ENVIRONMENT";
        case ControllabilityVerdict::Unavailable: return "UNAVAILABLE";
        case ControllabilityVerdict::Unknown: return "UNKNOWN";
    }
    return "UNKNOWN";
}

const char *frontier_state(PathFeasibilityVerdict value) {
    switch (value) {
        case PathFeasibilityVerdict::Sat: return "SAT";
        case PathFeasibilityVerdict::Unsat: return "UNSAT";
        case PathFeasibilityVerdict::Unknown: return "UNKNOWN";
        case PathFeasibilityVerdict::NotEvaluated: return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

const char *frontier_state(MutationSemanticsVerdict value) {
    switch (value) {
        case MutationSemanticsVerdict::Supported: return "SUPPORTED";
        case MutationSemanticsVerdict::Heuristic: return "HEURISTIC";
        case MutationSemanticsVerdict::Unknown: return "UNKNOWN";
        case MutationSemanticsVerdict::NotEvaluated: return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

const char *frontier_state(RuntimeEvidenceVerdict value) {
    switch (value) {
        case RuntimeEvidenceVerdict::Confirmed: return "CONFIRMED";
        case RuntimeEvidenceVerdict::Refuted: return "REFUTED";
        case RuntimeEvidenceVerdict::Unknown: return "UNKNOWN";
        case RuntimeEvidenceVerdict::NotEvaluated: return "NOT_EVALUATED";
    }
    return "UNKNOWN";
}

std::string evidence_json(const FrontierEvidenceAxes &evidence) {
    std::vector<std::string> model_ids = evidence.model_provenance.attachment_ids;
    model_ids.insert(
        model_ids.end(), evidence.model_provenance.model_fact_ids.begin(),
        evidence.model_provenance.model_fact_ids.end());
    const bool complete = evidence.completeness.model_vm_complete &&
                          evidence.completeness.attachment_enumeration_complete &&
                          evidence.completeness.forward_enumeration_complete &&
                          evidence.completeness.cone_complete &&
                          evidence.completeness.compatibility_complete;
    std::ostringstream stream;
    stream << "{\"reachability\":"
           << evidence_axis_json(frontier_state(evidence.reachability), {}, {})
           << ",\"controllability\":"
           << evidence_axis_json(frontier_state(evidence.controllability), {}, {})
           << ",\"path_feasibility\":"
           << evidence_axis_json(frontier_state(evidence.path_feasibility), {}, {})
           << ",\"mutation_semantics\":"
           << evidence_axis_json(frontier_state(evidence.mutation_semantics), {}, {})
           << ",\"runtime_evidence\":"
           << evidence_axis_json(frontier_state(evidence.runtime_evidence), {}, {})
           << ",\"model_provenance\":"
           << evidence_axis_json(
                  model_ids.empty() ? "UNKNOWN" : "MODELLED", model_ids,
                  model_ids.empty()
                      ? std::vector<std::string>{"no model provenance IDs"}
                      : std::vector<std::string>{})
           << ",\"completeness_ledger\":"
           << evidence_axis_json(
                  complete ? "MUST" : "UNKNOWN", {},
                  evidence.completeness.gap_reasons)
           << '}';
    return stream.str();
}

std::string timing_json(const TimingContract &timing) {
    std::string endpoint = "null";
    if (timing.comparison_endpoint) {
        endpoint = json_escape(to_string(*timing.comparison_endpoint));
    }
    std::ostringstream stream;
    stream << "{\"status\":" << json_escape(to_string(timing.status))
           << ",\"clock_source\":" << nullable_string(timing.clock_source)
           << ",\"unit\":" << nullable_string(timing.unit)
           << ",\"epoch\":" << nullable_string(timing.epoch)
           << ",\"quantum\":" << nullable_number(timing.quantum)
           << ",\"jitter\":" << nullable_number(timing.jitter)
           << ",\"wrap\":" << nullable_string(timing.wrap)
           << ",\"comparison_endpoint\":" << endpoint
           << ",\"start_event\":" << nullable_string(timing.start_event)
           << ",\"end_event\":" << nullable_string(timing.end_event)
           << ",\"scope_schema\":" << nullable_string(timing.scope_schema)
           << ",\"generation_schema\":" << nullable_string(timing.generation_schema)
           << ",\"lower\":" << nullable_number(timing.lower)
           << ",\"upper\":" << nullable_number(timing.upper)
           << ",\"lower_closed\":" << nullable_bool(timing.lower_closed)
           << ",\"upper_closed\":" << nullable_bool(timing.upper_closed)
           << ",\"mutation_actions\":"
           << json_array(timing.mutation_actions, [](TimingMutationAction value) {
                  return json_escape(to_string(value));
              })
           << ",\"uncertainty_reasons\":"
           << json_strings(timing.uncertainty_reasons) << '}';
    return stream.str();
}

std::string prerequisite_step_json(const PrerequisiteStep &step) {
    return "{\"step_id\":" + json_escape(step.step_id) +
           ",\"action_id\":" + json_escape(step.action_id) +
           ",\"operation\":" + json_escape(step.operation) +
           ",\"predecessor_step_ids\":" +
           json_strings(step.predecessor_step_ids) + '}';
}

std::string prerequisite_dag_json(const PrerequisiteDag &dag) {
    return "{\"dag_id\":" + json_escape(dag.dag_id) +
           ",\"status\":" + json_escape(to_string(dag.status)) +
           ",\"steps\":" +
           json_array(dag.steps, prerequisite_step_json) +
           ",\"uncertainty_reasons\":" +
           json_strings(dag.uncertainty_reasons) + '}';
}

std::string prerequisite_choice_json(const PrerequisiteChoice &choice) {
    return "{\"choice_id\":" + json_escape(choice.choice_id) +
           ",\"alternatives\":" +
           json_array(choice.alternatives, prerequisite_dag_json) + '}';
}

std::string mutation_value_json(const MutationValue &value) {
    return "{\"canonical\":" + json_escape(value.canonical) +
           ",\"value_type\":" + value_type_json(value.value_type) +
           ",\"purpose\":" + json_escape(to_string(value.purpose)) + '}';
}

std::string action_mutation_json(const ActionMutation &mutation) {
    return "{\"action_id\":" + json_escape(mutation.action_id) +
           ",\"mutation_kind\":" + json_escape(to_string(mutation.mutation_kind)) +
           ",\"direction\":" + json_escape(to_string(mutation.direction)) +
           ",\"suggested_values\":" +
           json_array(mutation.suggested_values, mutation_value_json) +
           ",\"unknown_reasons\":" +
           json_strings(mutation.unknown_reasons) + '}';
}

std::string hyperedge_json(const ActionHyperedge &edge) {
    return "{\"hyperedge_id\":" + json_escape(edge.hyperedge_id) +
           ",\"action_ids\":" + json_strings(edge.action_ids) +
           ",\"indivisible\":" + (edge.indivisible ? "true" : "false") +
           ",\"claim\":" + json_escape(to_string(edge.claim)) + '}';
}

std::string recipe_json(const MutationRecipe &recipe) {
    std::ostringstream stream;
    stream << "{\"recipe_id\":" << json_escape(recipe.recipe_id)
           << ",\"frontier_candidate_id\":" << json_escape(recipe.frontier_candidate_id)
           << ",\"cone_id\":" << json_escape(recipe.cone_id)
           << ",\"ap_id\":" << json_escape(recipe.ap_id)
           << ",\"target_predicate_selector_id\":"
           << nullable_string(recipe.target_predicate_selector_id)
           << ",\"status\":" << json_escape(to_string(recipe.status))
           << ",\"action_hyperedge\":" << hyperedge_json(recipe.action_hyperedge)
           << ",\"action_mutations\":"
           << json_array(recipe.action_mutations, action_mutation_json)
           << ",\"prerequisite_choices\":"
           << json_array(recipe.prerequisite_choices, prerequisite_choice_json)
           << ",\"timing\":" << timing_json(recipe.timing)
           << ",\"solver_query\":" << solver_query_json(recipe.solver_query)
           << ",\"direction_query\":"
           << (recipe.direction_query ? solver_query_json(*recipe.direction_query)
                                      : "null")
           << ",\"evidence\":" << evidence_json(recipe.evidence)
           << ",\"uncertainty_reasons\":"
           << json_strings(recipe.uncertainty_reasons) << '}';
    return stream.str();
}

std::string coverage_gap_json(const CoverageGap &gap) {
    std::ostringstream stream;
    stream << "{\"construct_id\":" << json_escape(gap.gap_id)
           << ",\"kind\":" << json_escape(gap.kind)
           << ",\"effect\":";
    switch (gap.effect) {
        case GapEffect::PrecisionLoss: stream << "\"precision_loss\""; break;
        case GapEffect::SoundnessRisk: stream << "\"soundness_risk\""; break;
        case GapEffect::StageFailure: stream << "\"stage_failure\""; break;
    }
    stream << ",\"detail\":" << json_escape(gap.detail)
           << ",\"locations\":[]"
           << ",\"affected_ids\":" << json_strings(gap.affected_ids) << '}';
    return stream.str();
}

}  // namespace

MutationRecipes build_mutation_recipes(
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const RecipeInputDigests &input_digests,
    const RecipeOptions &options) {
    ContextualValueTransferIndex unavailable;
    unavailable.graph_artifact_id = graph.artifact_id;
    unavailable.property_independent = true;
    unavailable.candidate_accounting_complete = false;
    unavailable.status = StageStatus::ConservativeIncomplete;
    return build_mutation_recipes(
        property, bindings, graph, cones, frontier, overlay,
        predicate_occurrences, unavailable, input_digests, options);
}

MutationRecipes build_mutation_recipes(
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const ContextualValueTransferIndex &value_transfers,
    const RecipeInputDigests &input_digests,
    const RecipeOptions &options) {
    MutationRecipes result;
    RecipeOptions effective_options = options;
    if (effective_options.solver_timeout_ms == 0) {
        effective_options.solver_timeout_ms = 1;
        effective_options.max_solver_queries = 0;
    }
    result.property_ir_sha256 = input_digests.property_ir_sha256;
    result.ap_bindings_sha256 = input_digests.ap_bindings_sha256;
    result.graph_sha256 = input_digests.graph_sha256;
    result.cones_sha256 = input_digests.cones_sha256;
    result.frontier_candidates_sha256 =
        input_digests.frontier_candidates_sha256;
    result.model_fact_overlay_sha256 =
        input_digests.model_fact_overlay_sha256;
    result.predicate_occurrence_bindings_sha256 =
        input_digests.predicate_occurrence_bindings_sha256;
    result.analyzer_core_sha256 = options.analyzer_core_sha256;
    result.solver_contract.solver_version = z3_version();
    result.solver_contract.timeout_ms = effective_options.solver_timeout_ms;
    result.solver_contract.max_queries =
        effective_options.max_solver_queries;
    result.candidate_accounting_complete =
        frontier.candidate_accounting_complete;
    result.coverage_gaps = frontier.coverage_gaps;
    result.coverage_gaps.insert(
        result.coverage_gaps.end(),
        predicate_occurrences.coverage_gaps.begin(),
        predicate_occurrences.coverage_gaps.end());

    std::vector<JointActionRequirement> effective_joints =
        options.joint_action_requirements;
    std::vector<JointActionRequirement> automatic_joints =
        derive_automatic_joint_requirements(
            property, bindings, graph, cones, frontier, overlay,
            predicate_occurrences, value_transfers);
    effective_joints.insert(
        effective_joints.end(),
        std::make_move_iterator(automatic_joints.begin()),
        std::make_move_iterator(automatic_joints.end()));
    std::sort(
        effective_joints.begin(), effective_joints.end(),
        [](const JointActionRequirement &left,
           const JointActionRequirement &right) {
            return left.requirement_id < right.requirement_id;
        });
    std::map<std::string, std::size_t> effective_joint_owners;
    for (const JointActionRequirement &joint : effective_joints) {
        for (const std::string &candidate_id :
             joint.frontier_candidate_ids) {
            ++effective_joint_owners[candidate_id];
        }
    }
    for (JointActionRequirement &joint : effective_joints) {
        if (std::any_of(
                joint.frontier_candidate_ids.begin(),
                joint.frontier_candidate_ids.end(),
                [&](const std::string &candidate_id) {
                    return effective_joint_owners[candidate_id] != 1;
                })) {
            joint.complete = false;
        }
    }

    std::string artifact_material =
        input_digests.property_ir_sha256 + '\0' +
        input_digests.ap_bindings_sha256 + '\0' +
        input_digests.graph_sha256 + '\0' +
        input_digests.cones_sha256 + '\0' +
        input_digests.frontier_candidates_sha256 + '\0' +
        input_digests.model_fact_overlay_sha256 + '\0' +
        input_digests.predicate_occurrence_bindings_sha256 + '\0' +
        options.analyzer_core_sha256 + '\0' + z3_version() + '\0' +
        std::to_string(effective_options.solver_timeout_ms) + '\0' +
        std::to_string(effective_options.max_solver_queries);
    std::vector<const JointActionRequirement *> ordered_joints;
    ordered_joints.reserve(effective_joints.size());
    for (const JointActionRequirement &joint : effective_joints) {
        ordered_joints.push_back(&joint);
    }
    std::sort(
        ordered_joints.begin(), ordered_joints.end(),
        [](const JointActionRequirement *left,
           const JointActionRequirement *right) {
            return std::tie(left->requirement_id, left->action_ids,
                            left->frontier_candidate_ids) <
                   std::tie(right->requirement_id, right->action_ids,
                            right->frontier_candidate_ids);
        });
    for (const JointActionRequirement *joint_pointer : ordered_joints) {
        const JointActionRequirement &joint = *joint_pointer;
        artifact_material.push_back('\0');
        artifact_material.append(joint.requirement_id);
        artifact_material.append(joint.complete ? "\0complete" : "\0unknown");
        std::vector<std::string> candidate_ids = joint.frontier_candidate_ids;
        std::vector<std::string> action_ids = joint.action_ids;
        std::vector<std::string> fact_ids = joint.model_fact_ids;
        sort_unique(candidate_ids);
        sort_unique(action_ids);
        sort_unique(fact_ids);
        for (const std::string &candidate_id : candidate_ids) {
            artifact_material.push_back('\0');
            artifact_material.append(candidate_id);
        }
        for (const std::string &action_id : action_ids) {
            artifact_material.push_back('\0');
            artifact_material.append(action_id);
        }
        for (const std::string &fact_id : fact_ids) {
            artifact_material.push_back('\0');
            artifact_material.append(fact_id);
        }
    }
    result.artifact_id = stable_id("mutation-recipes", artifact_material);

    bool failed = false;
    if (!valid_sha256(input_digests.property_ir_sha256) ||
        !valid_sha256(input_digests.ap_bindings_sha256) ||
        !valid_sha256(input_digests.graph_sha256) ||
        !valid_sha256(input_digests.cones_sha256) ||
        !valid_sha256(input_digests.frontier_candidates_sha256) ||
        !valid_sha256(input_digests.model_fact_overlay_sha256) ||
        !valid_sha256(
            input_digests.predicate_occurrence_bindings_sha256) ||
        !valid_sha256(options.analyzer_core_sha256) ||
        options.solver_timeout_ms == 0) {
        failed = true;
        result.diagnostics.push_back(
            "recipe inputs require valid SHA-256 digests and a non-zero solver timeout");
    }
    if (bindings.property_ir_sha256 != input_digests.property_ir_sha256 ||
        cones.ap_bindings_sha256 != input_digests.ap_bindings_sha256 ||
        cones.graph_sha256 != input_digests.graph_sha256 ||
        frontier.input_digests.graph_sha256 != input_digests.graph_sha256 ||
        frontier.input_digests.cones_sha256 != input_digests.cones_sha256 ||
        frontier.input_digests.model_fact_overlay_sha256 !=
            input_digests.model_fact_overlay_sha256 ||
        predicate_occurrences.property_ir_sha256 !=
            input_digests.property_ir_sha256 ||
        predicate_occurrences.semantic_index_sha256 !=
            bindings.semantic_index_sha256) {
        failed = true;
        result.diagnostics.push_back(
            "recipe input artifacts do not close over the declared digest chain");
    }
    std::map<std::string, std::string> joint_owner;
    std::set<std::string> joint_ids;
    std::set<std::string> manually_supplied_joint_ids;
    for (const JointActionRequirement &joint :
         options.joint_action_requirements) {
        manually_supplied_joint_ids.insert(joint.requirement_id);
    }
    for (const JointActionRequirement &joint : effective_joints) {
        if (!joint_ids.insert(joint.requirement_id).second) {
            failed = true;
            result.diagnostics.push_back(
                "duplicate joint requirement ID: " + joint.requirement_id);
        }
        std::vector<std::string> errors;
        if (manually_supplied_joint_ids.contains(joint.requirement_id)) {
            errors = joint_errors(joint, frontier, overlay);
        } else if (joint.frontier_candidate_ids.size() < 2 ||
                   joint.action_ids.size() < 2) {
            errors.push_back(
                "automatically derived joint requirement is not n-ary");
        }
        if (!errors.empty()) {
            failed = true;
            result.diagnostics.insert(
                result.diagnostics.end(), errors.begin(), errors.end());
        }
        for (const std::string &candidate_id : joint.frontier_candidate_ids) {
            const auto [owner, inserted] = joint_owner.emplace(
                candidate_id, joint.requirement_id);
            if (!inserted) {
                failed = true;
                result.diagnostics.push_back(
                    "frontier candidate occurs in multiple joint requirements: " +
                    candidate_id + " (" + owner->second + ", " +
                    joint.requirement_id + ')');
            }
        }
    }

    std::uint64_t queries_used = 0;
    std::map<std::string, std::vector<JointTargetInput>> joint_targets;
    std::map<std::string, std::string> joint_target_errors;
    for (const JointActionRequirement &joint : effective_joints) {
        if (!joint.complete) continue;
        std::map<std::string, JointTargetInput> by_action;
        for (const std::string &candidate_id :
             joint.frontier_candidate_ids) {
            const auto candidate = std::find_if(
                frontier.candidates.begin(), frontier.candidates.end(),
                [&](const FrontierCandidate &item) {
                    return item.candidate_id == candidate_id;
                });
            if (candidate == frontier.candidates.end()) {
                joint_target_errors[joint.requirement_id] =
                    "joint candidate is absent from the frontier ledger";
                break;
            }
            const AtomicProposition *ap = find_ap(
                property, candidate->ap_id);
            if (ap == nullptr) {
                joint_target_errors[joint.requirement_id] =
                    "joint candidate AP is absent from Property IR";
                break;
            }
            const ValueBindingResult binding =
                bind_action_to_predicate_reference(
                    *candidate, *ap, bindings, graph, cones, overlay,
                    predicate_occurrences);
            std::optional<ExternalPayloadProjection> projection;
            PayloadPredicateRewrite rewrite;
            if (binding.selector_id && !binding.projection_targets.empty()) {
                projection = compose_external_payload_projection(
                    *candidate, graph, overlay, value_transfers,
                    binding.projection_targets);
                rewrite = rewrite_predicate_in_payload_coordinate(
                    ap->predicate, *binding.selector_id, *projection);
            }
            if (!binding.selector_id || !projection ||
                !rewrite.predicate || !rewrite.identity_projection) {
                joint_target_errors[joint.requirement_id] =
                    "joint action lacks a unique typed identity projection from one external payload coordinate to its predicate occurrence";
                break;
            }
            JointTargetInput input{
                candidate->action.external_action_id,
                *binding.selector_id,
                candidate->action.payload_type};
            const auto [position, inserted] = by_action.emplace(
                input.action_id, input);
            if (!inserted &&
                (position->second.selector_id != input.selector_id ||
                 !same_value_type(position->second.type, input.type))) {
                joint_target_errors[joint.requirement_id] =
                    "one joint action maps to incompatible predicate operands";
                break;
            }
        }
        if (!joint_target_errors.contains(joint.requirement_id)) {
            if (by_action.size() != joint.action_ids.size()) {
                joint_target_errors[joint.requirement_id] =
                    "joint action ledger is not closed by typed value witnesses";
            } else {
                for (const auto &[unused, input] : by_action) {
                    (void)unused;
                    joint_targets[joint.requirement_id].push_back(input);
                }
            }
        }
    }
    std::map<std::string, JointQueryResult> joint_query_cache;
    std::vector<const FrontierCandidate *> actionable_candidates;
    for (const FrontierCandidate &candidate : frontier.candidates) {
        if (candidate.disposition == FrontierDisposition::Actionable) {
            actionable_candidates.push_back(&candidate);
        }
    }
    std::sort(
        actionable_candidates.begin(), actionable_candidates.end(),
        [](const FrontierCandidate *left, const FrontierCandidate *right) {
            return left->candidate_id < right->candidate_id;
        });
    for (const FrontierCandidate *candidate_pointer : actionable_candidates) {
        const FrontierCandidate &candidate = *candidate_pointer;
        MutationRecipe recipe;
        recipe.frontier_candidate_id = candidate.candidate_id;
        recipe.cone_id = candidate.cone_id;
        recipe.ap_id = candidate.ap_id;
        recipe.evidence = candidate.evidence;
        recipe.prerequisite_choices =
            derive_prerequisites(candidate, overlay);
        {
            std::vector<PrerequisiteChoice> guard_choices =
                derive_control_guard_prerequisites(
                    candidate, property, bindings, graph, cones, frontier,
                    overlay, predicate_occurrences);
            recipe.prerequisite_choices.insert(
                recipe.prerequisite_choices.end(),
                std::make_move_iterator(guard_choices.begin()),
                std::make_move_iterator(guard_choices.end()));
            std::sort(
                recipe.prerequisite_choices.begin(),
                recipe.prerequisite_choices.end(),
                [](const PrerequisiteChoice &left,
                   const PrerequisiteChoice &right) {
                    return left.choice_id < right.choice_id;
                });
        }
        recipe.timing =
            build_timing_contract(property, candidate, graph, overlay);

        const JointActionRequirement *joint =
            joint_requirement(effective_joints, candidate);
        recipe.action_hyperedge = build_hyperedge(candidate, joint);
        const AtomicProposition *ap = find_ap(property, candidate.ap_id);
        const ExternalAction *overlay_action = find_overlay_action(
            overlay, candidate.action.external_action_id);
        ActionMutation mutation;
        mutation.action_id = candidate.action.external_action_id;
        std::string placeholder_digest = sha256_hex(
            candidate.candidate_id + std::string("\0unknown-recipe", 15));

        if (ap == nullptr) {
            failed = true;
            recipe.status = RecipeStatus::Unknown;
            recipe.uncertainty_reasons.push_back(
                "BROKEN_REFERENCE: frontier AP does not exist in Property IR");
            mutation.unknown_reasons = recipe.uncertainty_reasons;
            recipe.solver_query = unsupported_query(
                placeholder_digest, effective_options,
                recipe.uncertainty_reasons.front(),
                SolverOutcome::NotRun);
        } else if (overlay_action == nullptr) {
            failed = true;
            recipe.status = RecipeStatus::Unknown;
            recipe.uncertainty_reasons.push_back(
                "BROKEN_REFERENCE: frontier action does not exist in model overlay");
            mutation.unknown_reasons = recipe.uncertainty_reasons;
            recipe.solver_query = unsupported_query(
                placeholder_digest, effective_options,
                recipe.uncertainty_reasons.front(),
                SolverOutcome::NotRun);
        } else if (!same_action_contract(candidate.action, *overlay_action)) {
            failed = true;
            recipe.status = RecipeStatus::Unknown;
            recipe.uncertainty_reasons.push_back(
                "BROKEN_REFERENCE: frontier and model-overlay action contracts differ");
            mutation.unknown_reasons = recipe.uncertainty_reasons;
            recipe.solver_query = unsupported_query(
                placeholder_digest, effective_options,
                recipe.uncertainty_reasons.front(),
                SolverOutcome::NotRun);
        } else if (joint != nullptr) {
            const auto set_unknown_joint = [&](const std::string &reason,
                                               SolverOutcome outcome) {
                recipe.status = RecipeStatus::Unknown;
                recipe.uncertainty_reasons.push_back(reason);
                for (const std::string &action_id :
                     recipe.action_hyperedge.action_ids) {
                    ActionMutation joint_mutation;
                    joint_mutation.action_id = action_id;
                    joint_mutation.unknown_reasons.push_back(reason);
                    recipe.action_mutations.push_back(
                        std::move(joint_mutation));
                }
                recipe.solver_query = unsupported_query(
                    placeholder_digest, effective_options, reason, outcome);
            };
            if (!joint->complete) {
                set_unknown_joint(
                    "joint-action completeness is UNKNOWN because the typed AND/model, occurrence, value-witness, scope, generation, or enumeration evidence is not closed",
                    SolverOutcome::Unsupported);
            } else if (const auto error =
                           joint_target_errors.find(joint->requirement_id);
                       error != joint_target_errors.end()) {
                set_unknown_joint(error->second, SolverOutcome::Unsupported);
            } else {
                const auto cached = joint_query_cache.find(
                    joint->requirement_id);
                if (cached == joint_query_cache.end()) {
                    const auto [position, inserted] =
                        joint_query_cache.emplace(
                            joint->requirement_id,
                            solve_joint_truth_change(
                                *joint, ap->predicate,
                                joint_targets.at(joint->requirement_id),
                                effective_options, queries_used));
                    (void)inserted;
                    recipe.solver_query =
                        position->second.truth_change;
                } else {
                    recipe.solver_query = cached->second.truth_change;
                }
                const JointQueryResult &query =
                    joint_query_cache.at(joint->requirement_id);
                const ValueBindingResult current_binding =
                    bind_action_to_predicate_reference(
                        candidate, *ap, bindings, graph, cones, overlay,
                        predicate_occurrences);
                recipe.target_predicate_selector_id =
                    current_binding.selector_id;
                if (query.truth_change.outcome == SolverOutcome::Sat) {
                    recipe.status = RecipeStatus::Supported;
                    recipe.evidence.path_feasibility =
                        PathFeasibilityVerdict::Sat;
                    recipe.evidence.mutation_semantics =
                        MutationSemanticsVerdict::Supported;
                    for (const JointTargetInput &target :
                         joint_targets.at(joint->requirement_id)) {
                        ActionMutation joint_mutation;
                        joint_mutation.action_id = target.action_id;
                        joint_mutation.mutation_kind =
                            target.type.kind == ValueKind::Boolean
                                ? MutationKind::BooleanToggle
                                : MutationKind::BoundarySet;
                        joint_mutation.direction =
                            target.type.kind == ValueKind::Boolean
                                ? MutationDirection::Toggle
                                : MutationDirection::BoundarySet;
                        const auto values =
                            query.action_values.find(target.action_id);
                        if (values != query.action_values.end()) {
                            if (target.type.kind == ValueKind::Boolean) {
                                joint_mutation.suggested_values = {
                                    {values->second.first, target.type,
                                     MutationValuePurpose::SatLeft},
                                    {values->second.second, target.type,
                                     MutationValuePurpose::SatRight}};
                            } else {
                                const auto left =
                                    parse_integer(values->second.first);
                                const auto right =
                                    parse_integer(values->second.second);
                                if (left) add_mutation_value(
                                    joint_mutation, *left,
                                    MutationValuePurpose::SatLeft,
                                    target.type);
                                if (right) add_mutation_value(
                                    joint_mutation, *right,
                                    MutationValuePurpose::SatRight,
                                    target.type);
                            }
                        }
                        recipe.action_mutations.push_back(
                            std::move(joint_mutation));
                    }
                } else {
                    const std::string reason =
                        query.truth_change.unknown_reason.value_or(
                            query.truth_change.outcome == SolverOutcome::Unsat
                                ? "multi-action summary cannot construct an AP false-to-true pair"
                                : "multi-action truth-change proof is incomplete");
                    recipe.status = RecipeStatus::Unknown;
                    recipe.uncertainty_reasons.push_back(reason);
                    recipe.evidence.path_feasibility =
                        query.truth_change.outcome == SolverOutcome::Unsat
                            ? PathFeasibilityVerdict::Unsat
                            : PathFeasibilityVerdict::Unknown;
                    for (const std::string &action_id :
                         recipe.action_hyperedge.action_ids) {
                        ActionMutation joint_mutation;
                        joint_mutation.action_id = action_id;
                        joint_mutation.unknown_reasons.push_back(reason);
                        recipe.action_mutations.push_back(
                            std::move(joint_mutation));
                    }
                }
            }
        } else {
            const ValueBindingResult value_binding =
                bind_action_to_predicate_reference(
                    candidate, *ap, bindings, graph, cones, overlay,
                    predicate_occurrences);
            if (!value_binding.selector_id) {
                recipe.status = RecipeStatus::Unknown;
                recipe.uncertainty_reasons = value_binding.reasons;
                if (recipe.uncertainty_reasons.empty()) {
                    recipe.uncertainty_reasons.push_back(
                        "value-capable action-to-predicate binding remains UNKNOWN");
                }
                mutation.unknown_reasons = recipe.uncertainty_reasons;
                recipe.solver_query = unsupported_query(
                    placeholder_digest, effective_options,
                    recipe.uncertainty_reasons.front(),
                    SolverOutcome::Unsupported);
            } else {
                const std::string &selector_id = *value_binding.selector_id;
                recipe.target_predicate_selector_id = selector_id;
                std::optional<PayloadPredicateRewrite> payload_rewrite;
                if (!value_binding.projection_targets.empty()) {
                    recipe.payload_projection =
                        compose_external_payload_projection(
                            candidate, graph, overlay, value_transfers,
                            value_binding.projection_targets);
                    payload_rewrite =
                        rewrite_predicate_in_payload_coordinate(
                            ap->predicate, selector_id,
                            *recipe.payload_projection);
                }
                if (candidate.action.payload_type.kind ==
                               ValueKind::Floating ||
                           candidate.action.payload_type.kind ==
                               ValueKind::Unknown ||
                           (candidate.action.payload_type.kind !=
                                ValueKind::Boolean &&
                            !complete_integer_type(
                                candidate.action.payload_type))) {
                    recipe.status = RecipeStatus::Unknown;
                    recipe.uncertainty_reasons.push_back(
                        candidate.action.payload_type.kind == ValueKind::Floating
                            ? "IEEE-754 NaN/Inf/signed-zero summary is incomplete"
                            : "external payload type lacks complete bit-width/signedness semantics");
                    mutation.unknown_reasons = recipe.uncertainty_reasons;
                    recipe.solver_query = unsupported_query(
                        expression_query_digest(
                            candidate, ap->predicate, selector_id,
                            "unsupported-type"),
                        effective_options, recipe.uncertainty_reasons.front(),
                        SolverOutcome::Unsupported);
                } else {
                    const bool exact_external_projection =
                        recipe.payload_projection && payload_rewrite &&
                        payload_rewrite->predicate.has_value() &&
                        recipe.payload_projection->status ==
                            PayloadProjectionStatus::Exact;
                    const bool failed_external_rewrite =
                        recipe.payload_projection &&
                        recipe.payload_projection->status ==
                            PayloadProjectionStatus::Exact &&
                        (!payload_rewrite || !payload_rewrite->predicate);
                    if (failed_external_rewrite) {
                        recipe.status = RecipeStatus::Unknown;
                        recipe.uncertainty_reasons =
                            payload_rewrite->reasons;
                        if (recipe.uncertainty_reasons.empty()) {
                            recipe.uncertainty_reasons.push_back(
                                "exact payload projection is outside the executable SMT subset");
                        }
                        mutation.unknown_reasons = recipe.uncertainty_reasons;
                        recipe.solver_query = unsupported_query(
                            expression_query_digest(
                                candidate, ap->predicate, selector_id,
                                "payload-rewrite-unsupported"),
                            effective_options,
                            recipe.uncertainty_reasons.front(),
                            SolverOutcome::Unsupported);
                    } else {
                    const ExpressionStructure &query_predicate =
                        exact_external_projection
                            ? *payload_rewrite->predicate
                            : ap->predicate;
                    const std::string &query_selector =
                        exact_external_projection
                            ? payload_rewrite->payload_selector_id
                            : selector_id;
                    QueryResult query = solve_truth_change(
                        candidate, query_predicate, query_selector,
                        candidate.action.payload_type, effective_options,
                        queries_used, exact_external_projection,
                        exact_external_projection);
                    recipe.solver_query = query.truth_change;
                    recipe.direction_query = query.direction;
                    const bool incomplete_direction =
                        query.direction && solver_outcome_is_incomplete(
                                               query.direction->outcome);
                    if (query.truth_change.outcome == SolverOutcome::Sat &&
                        incomplete_direction) {
                        // The SAT pair proves local truth change, but an
                        // unfinished counterexample query cannot justify a
                        // monotone mutation direction.  Keep the candidate and
                        // both query certificates, while making the recipe and
                        // action mutation explicitly total-UNKNOWN.
                        recipe.status = RecipeStatus::Unknown;
                        recipe.evidence.path_feasibility =
                            PathFeasibilityVerdict::Sat;
                        recipe.evidence.mutation_semantics =
                            MutationSemanticsVerdict::Unknown;
                        const std::string reason =
                            query.direction->unknown_reason.value_or(
                                "monotonicity proof query is incomplete");
                        recipe.uncertainty_reasons.push_back(reason);
                        mutation.unknown_reasons.push_back(reason);
                    } else if (query.truth_change.outcome ==
                               SolverOutcome::Sat) {
                        recipe.status = exact_external_projection
                                            ? RecipeStatus::Supported
                                            : RecipeStatus::Heuristic;
                        recipe.evidence.path_feasibility =
                            PathFeasibilityVerdict::Sat;
                        recipe.evidence.mutation_semantics =
                            exact_external_projection
                                ? MutationSemanticsVerdict::Supported
                                : MutationSemanticsVerdict::Heuristic;
                        if (!exact_external_projection) {
                            const std::string reason =
                                recipe.payload_projection
                                    ? "typed payload projection is not exact; the SMT result is selector-local and cannot determine external payload values or direction"
                                    : "predicate binding has no contextual target for a typed external-payload projection; the SMT result is selector-local";
                            recipe.uncertainty_reasons.push_back(reason);
                            mutation.mutation_kind = MutationKind::Unknown;
                            mutation.direction = MutationDirection::Unknown;
                            mutation.suggested_values.clear();
                            mutation.unknown_reasons.push_back(reason);
                        } else {
                            mutation.direction = query.proven_direction;
                            if (candidate.action.payload_type.kind ==
                                ValueKind::Boolean) {
                                mutation.mutation_kind =
                                    MutationKind::BooleanToggle;
                                mutation.direction = MutationDirection::Toggle;
                                mutation.suggested_values = {
                                    {"false", candidate.action.payload_type,
                                     MutationValuePurpose::FalseValue},
                                    {"true", candidate.action.payload_type,
                                     MutationValuePurpose::TrueValue}};
                            } else if (const std::optional<DirectBoundary> mask =
                                           bitmask_boundary(query_predicate)) {
                                mutation.mutation_kind =
                                    MutationKind::BitmaskBoundary;
                                mutation.direction =
                                    MutationDirection::BoundarySet;
                                add_mutation_value(
                                    mutation, mask->value,
                                    MutationValuePurpose::MaskSet,
                                    mask->type);
                                cpp_int opposite = mask->value;
                                cpp_int bit = 1;
                                while (((*mask->mask) & bit) == 0) bit <<= 1;
                                opposite ^= bit;
                                add_mutation_value(
                                    mutation, opposite,
                                    MutationValuePurpose::MaskCleared,
                                    mask->type);
                            } else if (
                                const std::optional<DirectBoundary> boundary =
                                    direct_boundary(query_predicate)) {
                                mutation.mutation_kind =
                                    boundary->type.kind == ValueKind::Enumeration
                                        ? MutationKind::EnumAlternative
                                        : (boundary->equality
                                               ? MutationKind::BoundarySet
                                               : MutationKind::ThresholdCrossing);
                                add_boundary_values(mutation, *boundary);
                            } else {
                                mutation.mutation_kind =
                                    query.direction
                                        ? MutationKind::ThresholdCrossing
                                        : MutationKind::BoundarySet;
                            }
                            if (query.left_value) {
                                const std::optional<cpp_int> value =
                                    parse_integer(*query.left_value);
                                if (value) add_mutation_value(
                                    mutation, *value,
                                    MutationValuePurpose::SatLeft,
                                    candidate.action.payload_type);
                            }
                            if (query.right_value) {
                                const std::optional<cpp_int> value =
                                    parse_integer(*query.right_value);
                                if (value) add_mutation_value(
                                    mutation, *value,
                                    MutationValuePurpose::SatRight,
                                    candidate.action.payload_type);
                            }
                        }
                    } else {
                        recipe.status = RecipeStatus::Unknown;
                        recipe.evidence.path_feasibility =
                            query.truth_change.outcome == SolverOutcome::Unsat
                                ? PathFeasibilityVerdict::Unsat
                                : PathFeasibilityVerdict::Unknown;
                        recipe.evidence.mutation_semantics =
                            MutationSemanticsVerdict::Unknown;
                        std::string reason = query.truth_change.unknown_reason
                                                 .value_or(
                                                     query.truth_change.outcome ==
                                                             SolverOutcome::Unsat
                                                         ? "local summary admits no AP truth-change pair"
                                                         : "mutation semantics are not proven");
                        recipe.uncertainty_reasons.push_back(reason);
                        mutation.unknown_reasons.push_back(reason);
                    }
                    }
                }
            }
        }
        if (recipe.action_mutations.empty()) {
            recipe.action_mutations.push_back(std::move(mutation));
        }
        if (recipe.status == RecipeStatus::Unknown) {
            recipe.evidence.mutation_semantics =
                MutationSemanticsVerdict::Unknown;
            if (recipe.uncertainty_reasons.empty()) {
                recipe.uncertainty_reasons.push_back(
                    "mutation recipe remains UNKNOWN");
            }
        }
        recipe.recipe_id = stable_id(
            "recipe",
            recipe_material(
                candidate, recipe.action_hyperedge,
                recipe.solver_query.query_sha256));
        sort_unique(recipe.uncertainty_reasons);
        result.recipes.push_back(std::move(recipe));
    }
    std::sort(
        result.recipes.begin(), result.recipes.end(),
        [](const MutationRecipe &left, const MutationRecipe &right) {
            return left.recipe_id < right.recipe_id;
        });

    if (failed || frontier.status == StageStatus::Failed ||
        overlay.status == StageStatus::Failed ||
        predicate_occurrences.status == StageStatus::Failed) {
        result.status = StageStatus::Failed;
    } else if (frontier.status != StageStatus::Complete ||
               overlay.status != StageStatus::Complete ||
               predicate_occurrences.status != StageStatus::Complete ||
               std::any_of(
                   result.recipes.begin(), result.recipes.end(),
                   [](const MutationRecipe &recipe) {
                       return recipe.status != RecipeStatus::Supported;
                   })) {
        result.status = StageStatus::ConservativeIncomplete;
    } else {
        result.status = StageStatus::Complete;
    }
    return result;
}

RecipeReplayObligations build_recipe_replay_obligations(
    const MutationRecipes &recipes,
    const std::string &mutation_recipes_sha256) {
    RecipeReplayObligations result;
    result.mutation_recipes_sha256 = mutation_recipes_sha256;
    result.candidate_accounting_complete =
        recipes.candidate_accounting_complete;
    result.artifact_id = stable_id(
        "recipe-replay-obligations", mutation_recipes_sha256);
    for (const MutationRecipe &recipe : recipes.recipes) {
        RecipeReplayObligation obligation;
        obligation.recipe_id = recipe.recipe_id;
        obligation.frontier_candidate_id = recipe.frontier_candidate_id;
        obligation.atomic_action_ids = recipe.action_hyperedge.action_ids;
        const bool prerequisites_closed =
            topological_steps(recipe, obligation.ordered_step_ids);
        obligation.required_observations = {
            "ACTION_ACCEPTED", "AP_BEFORE", "AP_AFTER",
            "GENERATION_IDENTITY", "SCOPE_IDENTITY"};
        if (recipe.timing.status != TimingStatus::Unknown) {
            obligation.required_observations.push_back("RELATIVE_TIME");
        }
        sort_unique(obligation.required_observations);
        obligation.solver_query_sha256 = recipe.solver_query.query_sha256;
        obligation.scope_schema = recipe.timing.scope_schema;
        obligation.generation_schema = recipe.timing.generation_schema;
        obligation.timing_status = recipe.timing.status;
        const bool truth_change_proven =
            recipe.solver_query.outcome == SolverOutcome::Sat;
        const bool recipe_supported =
            recipe.status == RecipeStatus::Supported;
        const bool action_executable =
            replay_action_mutations_executable(recipe);
        const bool timing_closed =
            recipe.timing.status == TimingStatus::Exact;
        if (truth_change_proven && recipe.status != RecipeStatus::Unknown) {
            obligation.expected_relation =
                ReplayExpectedRelation::ApTruthChange;
            obligation.status =
                recipe_supported && action_executable &&
                        prerequisites_closed && timing_closed
                    ? ReplayStatus::Ready
                    : ReplayStatus::Partial;
            if (!recipe_supported) {
                obligation.uncertainty_reasons.push_back(
                    "mutation recipe is HEURISTIC rather than SUPPORTED");
            }
            if (!action_executable) {
                obligation.uncertainty_reasons.push_back(
                    "one or more atomic actions lack a closed executable mutation");
            }
            if (!prerequisites_closed) {
                obligation.uncertainty_reasons.push_back(
                    "prerequisite DAG is ambiguous, incomplete, or not totally replayable");
            }
            if (!timing_closed) {
                obligation.uncertainty_reasons.push_back(
                    "timing contract is widened or unknown");
            }
        } else {
            obligation.expected_relation = ReplayExpectedRelation::Unknown;
            obligation.status = ReplayStatus::Unknown;
            obligation.uncertainty_reasons.push_back(
                recipe.solver_query.outcome != SolverOutcome::Sat
                    ? "local truth-change query is not SAT"
                    : "recipe remains UNKNOWN despite a local SAT pair");
        }
        obligation.obligation_id = stable_id(
            "replay-obligation",
            recipe.recipe_id + '\0' + mutation_recipes_sha256);
        sort_unique(obligation.uncertainty_reasons);
        result.obligations.push_back(std::move(obligation));
    }
    std::sort(
        result.obligations.begin(), result.obligations.end(),
        [](const RecipeReplayObligation &left,
           const RecipeReplayObligation &right) {
            return left.obligation_id < right.obligation_id;
        });
    return result;
}

std::vector<std::string> validate_mutation_recipes(
    const MutationRecipes &recipes,
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const RecipeInputDigests &expected_digests,
    const RecipeOptions &options) {
    ContextualValueTransferIndex unavailable;
    unavailable.graph_artifact_id = graph.artifact_id;
    unavailable.property_independent = true;
    unavailable.candidate_accounting_complete = false;
    unavailable.status = StageStatus::ConservativeIncomplete;
    return validate_mutation_recipes(
        recipes, property, bindings, graph, cones, frontier, overlay,
        predicate_occurrences, unavailable, expected_digests, options);
}

std::vector<std::string> validate_mutation_recipes(
    const MutationRecipes &recipes,
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const ContextualValueTransferIndex &value_transfers,
    const RecipeInputDigests &expected_digests,
    const RecipeOptions &options) {
    std::vector<std::string> errors;
    if (recipes.property_ir_sha256 != expected_digests.property_ir_sha256 ||
        recipes.ap_bindings_sha256 != expected_digests.ap_bindings_sha256 ||
        recipes.graph_sha256 != expected_digests.graph_sha256 ||
        recipes.cones_sha256 != expected_digests.cones_sha256 ||
        recipes.frontier_candidates_sha256 !=
            expected_digests.frontier_candidates_sha256 ||
        recipes.model_fact_overlay_sha256 !=
            expected_digests.model_fact_overlay_sha256 ||
        recipes.predicate_occurrence_bindings_sha256 !=
            expected_digests.predicate_occurrence_bindings_sha256) {
        errors.push_back("recipe input digest closure mismatch");
    }
    if (!valid_sha256(recipes.property_ir_sha256) ||
        !valid_sha256(recipes.ap_bindings_sha256) ||
        !valid_sha256(recipes.graph_sha256) ||
        !valid_sha256(recipes.cones_sha256) ||
        !valid_sha256(recipes.frontier_candidates_sha256) ||
        !valid_sha256(recipes.model_fact_overlay_sha256) ||
        !valid_sha256(recipes.predicate_occurrence_bindings_sha256) ||
        !valid_sha256(recipes.analyzer_core_sha256)) {
        errors.push_back("recipe digest is not lowercase SHA-256");
    }
    if (recipes.analyzer_core_sha256 != options.analyzer_core_sha256) {
        errors.push_back("recipe analyzer core digest mismatch");
    }
    if (options.solver_timeout_ms == 0) {
        errors.push_back("recipe solver timeout configuration is zero");
    }
    if (recipes.solver_contract.solver != "Z3" ||
        recipes.solver_contract.solver_version != z3_version() ||
        recipes.solver_contract.encoding_version != kEncodingVersion ||
        recipes.solver_contract.timeout_ms !=
            std::max<std::uint64_t>(1, options.solver_timeout_ms) ||
        recipes.solver_contract.max_queries !=
            (options.solver_timeout_ms == 0
                 ? 0
                 : options.max_solver_queries)) {
        errors.push_back("recipe solver contract mismatch");
    }
    if (bindings.property_ir_sha256 != expected_digests.property_ir_sha256 ||
        cones.ap_bindings_sha256 != expected_digests.ap_bindings_sha256 ||
        cones.graph_sha256 != expected_digests.graph_sha256 ||
        frontier.input_digests.graph_sha256 != expected_digests.graph_sha256 ||
        frontier.input_digests.cones_sha256 != expected_digests.cones_sha256 ||
        frontier.input_digests.model_fact_overlay_sha256 !=
            expected_digests.model_fact_overlay_sha256 ||
        predicate_occurrences.property_ir_sha256 !=
            expected_digests.property_ir_sha256 ||
        predicate_occurrences.semantic_index_sha256 !=
            bindings.semantic_index_sha256) {
        errors.push_back("recipe source artifact digest chain is not closed");
    }
    if (!recipes.candidate_accounting_complete || !recipes.total_semantics) {
        errors.push_back("recipe accounting/total-semantics invariant is false");
    }
    std::set<std::string> actionable;
    for (const FrontierCandidate &candidate : frontier.candidates) {
        if (candidate.disposition == FrontierDisposition::Actionable) {
            actionable.insert(candidate.candidate_id);
        }
    }
    std::set<std::string> seen_recipes;
    std::set<std::string> seen_candidates;
    for (const MutationRecipe &recipe : recipes.recipes) {
        if (!seen_recipes.insert(recipe.recipe_id).second) {
            errors.push_back("duplicate recipe ID: " + recipe.recipe_id);
        }
        if (!seen_candidates.insert(recipe.frontier_candidate_id).second) {
            errors.push_back(
                "multiple recipes for actionable candidate: " +
                recipe.frontier_candidate_id);
        }
        if (!actionable.contains(recipe.frontier_candidate_id)) {
            errors.push_back(
                "recipe refers to non-actionable candidate: " +
                recipe.frontier_candidate_id);
        }
        if (find_ap(property, recipe.ap_id) == nullptr) {
            errors.push_back("recipe refers to unknown AP: " + recipe.ap_id);
        }
        const auto frontier_candidate = std::find_if(
            frontier.candidates.begin(), frontier.candidates.end(),
            [&](const FrontierCandidate &candidate) {
                return candidate.candidate_id == recipe.frontier_candidate_id;
            });
        if (frontier_candidate != frontier.candidates.end()) {
            const AtomicProposition *ap = find_ap(property, recipe.ap_id);
            if (ap != nullptr && recipe.solver_query.outcome == SolverOutcome::Sat) {
                const ValueBindingResult value_binding =
                    bind_action_to_predicate_reference(
                        *frontier_candidate, *ap, bindings, graph, cones,
                        overlay, predicate_occurrences);
                if (!value_binding.selector_id) {
                    errors.push_back(
                        "SAT recipe lacks a replayable value-path binding: " +
                        recipe.recipe_id);
                } else if (recipe.target_predicate_selector_id !=
                           value_binding.selector_id) {
                    errors.push_back(
                        "SAT recipe target predicate selector differs from "
                        "the occurrence/value-path proof: " + recipe.recipe_id);
                }
                if (recipe.payload_projection) {
                    if (value_binding.projection_targets.empty()) {
                        errors.push_back(
                            "recipe carries a payload projection without a contextual predicate target: " +
                            recipe.recipe_id);
                    } else {
                        const std::vector<std::string> projection_errors =
                            validate_external_payload_projection(
                                *recipe.payload_projection,
                                *frontier_candidate, graph, overlay,
                                value_transfers,
                                value_binding.projection_targets);
                        for (const std::string &error : projection_errors) {
                            errors.push_back(
                                "invalid external payload projection for " +
                                recipe.recipe_id + ": " + error);
                        }
                    }
                }
            }
        }
        if (recipe.action_hyperedge.claim ==
                JointActionClaim::SingleAction &&
            recipe.status == RecipeStatus::Supported &&
            (!recipe.payload_projection ||
             recipe.payload_projection->status !=
                 PayloadProjectionStatus::Exact)) {
            errors.push_back(
                "SUPPORTED single-action recipe lacks an EXACT external payload projection: " +
                recipe.recipe_id);
        }
        if (recipe.status == RecipeStatus::Unknown &&
            recipe.uncertainty_reasons.empty()) {
            errors.push_back("UNKNOWN recipe has no reason: " + recipe.recipe_id);
        }
        if (!recipe.action_hyperedge.indivisible ||
            recipe.action_hyperedge.action_ids.empty()) {
            errors.push_back("recipe has invalid action hyperedge: " + recipe.recipe_id);
        }
        std::set<std::string> hyperedge_actions(
            recipe.action_hyperedge.action_ids.begin(),
            recipe.action_hyperedge.action_ids.end());
        if (hyperedge_actions.size() !=
            recipe.action_hyperedge.action_ids.size()) {
            errors.push_back("recipe hyperedge has duplicate actions: " + recipe.recipe_id);
        }
        if (recipe.action_hyperedge.claim ==
                JointActionClaim::JointRequired &&
            hyperedge_actions.size() < 2) {
            errors.push_back("joint recipe was split into one action: " + recipe.recipe_id);
        }
        std::set<std::string> mutation_actions;
        if (recipe.action_mutations.empty()) {
            errors.push_back("recipe has no action mutation ledger: " + recipe.recipe_id);
        }
        for (const ActionMutation &mutation : recipe.action_mutations) {
            mutation_actions.insert(mutation.action_id);
            if (!hyperedge_actions.contains(mutation.action_id)) {
                errors.push_back("mutation is outside its action hyperedge: " + recipe.recipe_id);
            }
            if (mutation.mutation_kind == MutationKind::Unknown &&
                (mutation.direction != MutationDirection::Unknown ||
                 !mutation.suggested_values.empty() ||
                 mutation.unknown_reasons.empty())) {
                errors.push_back("UNKNOWN action mutation is not total: " + recipe.recipe_id);
            }
        }
        if (mutation_actions != hyperedge_actions) {
            errors.push_back("action hyperedge/mutation ledger mismatch: " + recipe.recipe_id);
        }
        if (!valid_sha256(recipe.solver_query.query_sha256) ||
            recipe.solver_query.timeout_ms == 0 ||
            recipe.solver_query.solver_version.empty()) {
            errors.push_back("invalid solver certificate: " + recipe.recipe_id);
        }
        if (recipe.solver_query.solver != recipes.solver_contract.solver ||
            recipe.solver_query.solver_version !=
                recipes.solver_contract.solver_version ||
            recipe.solver_query.encoding_version !=
                recipes.solver_contract.encoding_version ||
            recipe.solver_query.timeout_ms !=
                recipes.solver_contract.timeout_ms) {
            errors.push_back(
                "query/top-level solver contract mismatch: " + recipe.recipe_id);
        }
        if (recipe.direction_query &&
            (recipe.direction_query->solver != recipes.solver_contract.solver ||
             recipe.direction_query->solver_version !=
                 recipes.solver_contract.solver_version ||
             recipe.direction_query->encoding_version !=
                 recipes.solver_contract.encoding_version ||
             recipe.direction_query->timeout_ms !=
                 recipes.solver_contract.timeout_ms)) {
            errors.push_back(
                "direction-query/top-level solver contract mismatch: " +
                recipe.recipe_id);
        }
        if (recipe.solver_query.outcome == SolverOutcome::Sat &&
            (recipe.solver_query.flip_class !=
                 FlipClass::LocalSummarySatPair ||
             recipe.solver_query.model.size() < 2)) {
            errors.push_back("SAT recipe lacks local pair model: " + recipe.recipe_id);
        }
        if ((recipe.solver_query.outcome == SolverOutcome::Unknown ||
             recipe.solver_query.outcome == SolverOutcome::Timeout ||
             recipe.solver_query.outcome == SolverOutcome::Unsupported ||
             recipe.solver_query.outcome == SolverOutcome::NotRun) &&
            !recipe.solver_query.unknown_reason) {
            errors.push_back("non-decision solver result has no reason: " + recipe.recipe_id);
        }
        if (solver_outcome_is_incomplete(recipe.solver_query.outcome) &&
            recipe.status != RecipeStatus::Unknown) {
            errors.push_back(
                "incomplete truth-change query is hidden by a non-UNKNOWN recipe status: " +
                recipe.recipe_id);
        }
        if (recipe.direction_query) {
            if (solver_outcome_is_incomplete(
                    recipe.direction_query->outcome) &&
                !recipe.direction_query->unknown_reason) {
                errors.push_back(
                    "incomplete direction query has no reason: " +
                    recipe.recipe_id);
            }
            if (solver_outcome_is_incomplete(
                    recipe.direction_query->outcome) &&
                recipe.status != RecipeStatus::Unknown) {
                errors.push_back(
                    "incomplete direction query is hidden by a non-UNKNOWN recipe status: " +
                    recipe.recipe_id);
            }
            if (!recipe.action_mutations.empty()) {
                const MutationDirection direction =
                    recipe.action_mutations.front().direction;
                const bool monotone =
                    direction == MutationDirection::MonotoneUp ||
                    direction == MutationDirection::MonotoneDown;
                if (monotone &&
                    recipe.direction_query->outcome !=
                        SolverOutcome::Unsat) {
                    errors.push_back(
                        "monotone direction lacks UNSAT counterexample proof: " +
                        recipe.recipe_id);
                }
                if (solver_outcome_is_incomplete(
                        recipe.direction_query->outcome) &&
                    direction != MutationDirection::Unknown) {
                    errors.push_back(
                        "incomplete direction query still claims a mutation direction: " +
                        recipe.recipe_id);
                }
            }
        }
        for (const PrerequisiteChoice &choice :
             recipe.prerequisite_choices) {
            if (choice.alternatives.empty()) {
                errors.push_back("empty prerequisite choice: " + recipe.recipe_id);
            }
            for (const PrerequisiteDag &dag : choice.alternatives) {
                if (dag_has_cycle(dag) &&
                    dag.status != PrerequisiteStatus::PartialOrderUnknown) {
                    errors.push_back("cyclic prerequisite claims COMPLETE: " + dag.dag_id);
                }
                if (dag.status == PrerequisiteStatus::PartialOrderUnknown &&
                    dag.uncertainty_reasons.empty()) {
                    errors.push_back("unknown prerequisite DAG has no reason: " + dag.dag_id);
                }
            }
        }
        const bool exact_timing_complete = recipe.timing.clock_source &&
            recipe.timing.unit && recipe.timing.epoch && recipe.timing.quantum &&
            recipe.timing.jitter && recipe.timing.wrap &&
            recipe.timing.comparison_endpoint && recipe.timing.start_event &&
            recipe.timing.end_event && recipe.timing.scope_schema &&
            recipe.timing.generation_schema;
        if (recipe.timing.status == TimingStatus::Exact &&
            !exact_timing_complete) {
            errors.push_back("EXACT timing contract has missing fields: " + recipe.recipe_id);
        }
        if (recipe.timing.status != TimingStatus::Exact &&
            recipe.timing.uncertainty_reasons.empty()) {
            errors.push_back("widened timing contract has no reason: " + recipe.recipe_id);
        }
    }
    if (seen_candidates != actionable) {
        errors.push_back("not every actionable candidate has exactly one recipe");
    }
    std::vector<JointActionRequirement> expected_joints =
        options.joint_action_requirements;
    std::vector<JointActionRequirement> expected_automatic_joints =
        derive_automatic_joint_requirements(
            property, bindings, graph, cones, frontier, overlay,
            predicate_occurrences, value_transfers);
    expected_joints.insert(
        expected_joints.end(), expected_automatic_joints.begin(),
        expected_automatic_joints.end());
    std::sort(
        expected_joints.begin(), expected_joints.end(),
        [](const JointActionRequirement &left,
           const JointActionRequirement &right) {
            return left.requirement_id < right.requirement_id;
        });
    std::set<std::string> automatic_joint_ids;
    for (const JointActionRequirement &joint :
         expected_automatic_joints) {
        automatic_joint_ids.insert(joint.requirement_id);
    }
    std::map<std::string, std::size_t> expected_joint_owners;
    for (const JointActionRequirement &joint : expected_joints) {
        for (const std::string &candidate_id :
             joint.frontier_candidate_ids) {
            ++expected_joint_owners[candidate_id];
        }
    }
    for (JointActionRequirement &joint : expected_joints) {
        if (std::any_of(
                joint.frontier_candidate_ids.begin(),
                joint.frontier_candidate_ids.end(),
                [&](const std::string &candidate_id) {
                    return expected_joint_owners[candidate_id] != 1;
                })) {
            joint.complete = false;
        }
    }
    for (const JointActionRequirement &joint :
         options.joint_action_requirements) {
        std::vector<std::string> current = joint_errors(joint, frontier, overlay);
        errors.insert(errors.end(), current.begin(), current.end());
    }
    for (const FrontierCandidate &candidate : frontier.candidates) {
        if (candidate.disposition != FrontierDisposition::Actionable) {
            continue;
        }
        std::vector<const JointActionRequirement *> owners;
        for (const JointActionRequirement &joint : expected_joints) {
            if (std::find(
                    joint.frontier_candidate_ids.begin(),
                    joint.frontier_candidate_ids.end(),
                    candidate.candidate_id) !=
                joint.frontier_candidate_ids.end()) {
                owners.push_back(&joint);
            }
        }
        if (owners.size() > 1) {
            errors.push_back(
                "frontier candidate has ambiguous recomputed joint ownership: " +
                candidate.candidate_id);
            continue;
        }
        const auto found = std::find_if(
            recipes.recipes.begin(), recipes.recipes.end(),
            [&](const MutationRecipe &recipe) {
                return recipe.frontier_candidate_id ==
                       candidate.candidate_id;
            });
        if (found == recipes.recipes.end()) continue;
        std::set<std::string> expected_actions;
        JointActionClaim expected_claim =
            JointActionClaim::SingleAction;
        bool automatic = false;
        if (owners.empty()) {
            expected_actions.insert(
                candidate.action.external_action_id);
        } else {
            expected_actions.insert(
                owners.front()->action_ids.begin(),
                owners.front()->action_ids.end());
            expected_claim = owners.front()->complete
                ? JointActionClaim::JointRequired
                : JointActionClaim::JointUnknown;
            automatic = automatic_joint_ids.contains(
                owners.front()->requirement_id);
        }
        const std::set<std::string> actual_actions(
            found->action_hyperedge.action_ids.begin(),
            found->action_hyperedge.action_ids.end());
        if (actual_actions != expected_actions ||
            found->action_hyperedge.claim != expected_claim) {
            errors.push_back(
                std::string(automatic ? "automatic " : "") +
                "joint action was split or changed for candidate: " +
                candidate.candidate_id);
        }
    }
    return errors;
}

std::vector<std::string> validate_recipe_replay_obligations(
    const RecipeReplayObligations &obligations,
    const MutationRecipes &recipes,
    const std::string &expected_mutation_recipes_sha256) {
    std::vector<std::string> errors;
    if (!valid_sha256(expected_mutation_recipes_sha256) ||
        obligations.mutation_recipes_sha256 !=
            expected_mutation_recipes_sha256) {
        errors.push_back("replay obligation recipe digest mismatch");
    }
    const RecipeReplayObligations expected =
        build_recipe_replay_obligations(
            recipes, expected_mutation_recipes_sha256);
    if (obligations.artifact_id != expected.artifact_id) {
        errors.push_back("replay obligation artifact ID mismatch");
    }
    if (obligations.candidate_accounting_complete !=
        expected.candidate_accounting_complete) {
        errors.push_back("replay obligation candidate accounting mismatch");
    }
    if (!obligations.candidate_accounting_complete) {
        errors.push_back("replay obligation candidate accounting is incomplete");
    }

    std::map<std::string, const RecipeReplayObligation *> expected_by_recipe;
    for (const RecipeReplayObligation &expected_obligation :
         expected.obligations) {
        expected_by_recipe.emplace(
            expected_obligation.recipe_id, &expected_obligation);
    }
    std::set<std::string> seen;
    for (const RecipeReplayObligation &obligation : obligations.obligations) {
        if (!seen.insert(obligation.recipe_id).second) {
            errors.push_back(
                "duplicate replay obligation for recipe: " +
                obligation.recipe_id);
            continue;
        }
        const auto found = expected_by_recipe.find(obligation.recipe_id);
        if (found == expected_by_recipe.end()) {
            errors.push_back(
                "replay obligation refers to unknown recipe: " +
                obligation.recipe_id);
            continue;
        }
        const RecipeReplayObligation &wanted = *found->second;
        const auto mismatch = [&](bool differs, const char *field) {
            if (differs) {
                errors.push_back(
                    "replay obligation " + std::string(field) +
                    " mismatch: " + obligation.recipe_id);
            }
        };
        mismatch(obligation.obligation_id != wanted.obligation_id,
                 "obligation_id");
        mismatch(
            obligation.frontier_candidate_id !=
                wanted.frontier_candidate_id,
            "frontier_candidate_id");
        mismatch(obligation.status != wanted.status, "status");
        mismatch(
            obligation.atomic_action_ids != wanted.atomic_action_ids,
            "atomic_action_ids");
        mismatch(
            obligation.indivisible_hyperedge !=
                wanted.indivisible_hyperedge,
            "indivisible_hyperedge");
        mismatch(
            obligation.ordered_step_ids != wanted.ordered_step_ids,
            "ordered_step_ids");
        mismatch(
            obligation.required_observations !=
                wanted.required_observations,
            "required_observations");
        mismatch(
            obligation.expected_relation != wanted.expected_relation,
            "expected_relation");
        mismatch(
            obligation.solver_query_sha256 !=
                wanted.solver_query_sha256,
            "solver_query_sha256");
        mismatch(
            obligation.scope_schema != wanted.scope_schema,
            "scope_schema");
        mismatch(
            obligation.generation_schema != wanted.generation_schema,
            "generation_schema");
        mismatch(
            obligation.timing_status != wanted.timing_status,
            "timing_status");
        mismatch(
            obligation.uncertainty_reasons !=
                wanted.uncertainty_reasons,
            "uncertainty_reasons");
    }
    if (seen.size() != expected_by_recipe.size()) {
        errors.push_back("not every recipe has exactly one replay obligation");
    }
    return errors;
}

std::string canonical_mutation_recipes_json(
    const MutationRecipes &recipes) {
    std::ostringstream stream;
    stream << "{\"schema_version\":" << json_escape(recipes.schema_version)
           << ",\"artifact_id\":" << json_escape(recipes.artifact_id)
           << ",\"property_ir_sha256\":" << json_escape(recipes.property_ir_sha256)
           << ",\"ap_bindings_sha256\":" << json_escape(recipes.ap_bindings_sha256)
           << ",\"graph_sha256\":" << json_escape(recipes.graph_sha256)
           << ",\"cones_sha256\":" << json_escape(recipes.cones_sha256)
           << ",\"frontier_candidates_sha256\":" << json_escape(recipes.frontier_candidates_sha256)
           << ",\"model_fact_overlay_sha256\":" << json_escape(recipes.model_fact_overlay_sha256)
           << ",\"predicate_occurrence_bindings_sha256\":"
           << json_escape(recipes.predicate_occurrence_bindings_sha256)
           << ",\"analyzer_core_sha256\":" << json_escape(recipes.analyzer_core_sha256)
           << ",\"solver_contract\":{\"solver\":"
           << json_escape(recipes.solver_contract.solver)
           << ",\"solver_version\":" << json_escape(recipes.solver_contract.solver_version)
           << ",\"encoding_version\":" << json_escape(recipes.solver_contract.encoding_version)
           << ",\"timeout_ms\":" << recipes.solver_contract.timeout_ms
           << ",\"max_queries\":" << recipes.solver_contract.max_queries
           << '}'
           << ",\"candidate_accounting_complete\":"
           << (recipes.candidate_accounting_complete ? "true" : "false")
           << ",\"total_semantics\":" << (recipes.total_semantics ? "true" : "false")
           << ",\"status\":" << json_escape(to_string(recipes.status))
           << ",\"recipes\":" << json_array(recipes.recipes, recipe_json)
           << ",\"unsupported_constructs\":"
           << json_array(recipes.coverage_gaps, coverage_gap_json) << '}';
    return stream.str();
}

std::string canonical_recipe_replay_obligations_json(
    const RecipeReplayObligations &obligations) {
    auto obligation_json = [](const RecipeReplayObligation &obligation) {
        std::ostringstream stream;
        stream << "{\"obligation_id\":" << json_escape(obligation.obligation_id)
               << ",\"recipe_id\":" << json_escape(obligation.recipe_id)
               << ",\"frontier_candidate_id\":" << json_escape(obligation.frontier_candidate_id)
               << ",\"status\":" << json_escape(to_string(obligation.status))
               << ",\"atomic_action_ids\":" << json_strings(obligation.atomic_action_ids)
               << ",\"indivisible_hyperedge\":"
               << (obligation.indivisible_hyperedge ? "true" : "false")
               << ",\"ordered_step_ids\":" << json_strings(obligation.ordered_step_ids)
               << ",\"required_observations\":" << json_strings(obligation.required_observations)
               << ",\"expected_relation\":" << json_escape(to_string(obligation.expected_relation))
               << ",\"solver_query_sha256\":" << json_escape(obligation.solver_query_sha256)
               << ",\"scope_schema\":" << nullable_string(obligation.scope_schema)
               << ",\"generation_schema\":" << nullable_string(obligation.generation_schema)
               << ",\"timing_status\":" << json_escape(to_string(obligation.timing_status))
               << ",\"uncertainty_reasons\":" << json_strings(obligation.uncertainty_reasons)
               << '}';
        return stream.str();
    };
    std::ostringstream stream;
    stream << "{\"schema_version\":" << json_escape(obligations.schema_version)
           << ",\"artifact_id\":" << json_escape(obligations.artifact_id)
           << ",\"mutation_recipes_sha256\":" << json_escape(obligations.mutation_recipes_sha256)
           << ",\"candidate_accounting_complete\":"
           << (obligations.candidate_accounting_complete ? "true" : "false")
           << ",\"obligations\":"
           << json_array(obligations.obligations, obligation_json) << '}';
    return stream.str();
}

#define RIFT_ENUM_STRING_CASE(value, text) case value: return text

const char *to_string(RecipeStatus value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(RecipeStatus::Supported, "SUPPORTED");
        RIFT_ENUM_STRING_CASE(RecipeStatus::Heuristic, "HEURISTIC");
        RIFT_ENUM_STRING_CASE(RecipeStatus::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(MutationKind value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(MutationKind::BoundarySet, "BOUNDARY_SET");
        RIFT_ENUM_STRING_CASE(MutationKind::BooleanToggle, "BOOLEAN_TOGGLE");
        RIFT_ENUM_STRING_CASE(MutationKind::EnumAlternative, "ENUM_ALTERNATIVE");
        RIFT_ENUM_STRING_CASE(MutationKind::BitmaskBoundary, "BITMASK_BOUNDARY");
        RIFT_ENUM_STRING_CASE(MutationKind::ThresholdCrossing, "THRESHOLD_CROSSING");
        RIFT_ENUM_STRING_CASE(MutationKind::Presence, "PRESENCE");
        RIFT_ENUM_STRING_CASE(MutationKind::Absence, "ABSENCE");
        RIFT_ENUM_STRING_CASE(MutationKind::Count, "COUNT");
        RIFT_ENUM_STRING_CASE(MutationKind::Drop, "DROP");
        RIFT_ENUM_STRING_CASE(MutationKind::Repeat, "REPEAT");
        RIFT_ENUM_STRING_CASE(MutationKind::Reorder, "REORDER");
        RIFT_ENUM_STRING_CASE(MutationKind::Timeout, "TIMEOUT");
        RIFT_ENUM_STRING_CASE(MutationKind::Deadline, "DEADLINE");
        RIFT_ENUM_STRING_CASE(MutationKind::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(MutationDirection value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(MutationDirection::MonotoneUp, "MONOTONE_UP");
        RIFT_ENUM_STRING_CASE(MutationDirection::MonotoneDown, "MONOTONE_DOWN");
        RIFT_ENUM_STRING_CASE(MutationDirection::BoundarySet, "BOUNDARY_SET");
        RIFT_ENUM_STRING_CASE(MutationDirection::Toggle, "TOGGLE");
        RIFT_ENUM_STRING_CASE(MutationDirection::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(MutationValuePurpose value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::TypeMin, "TYPE_MIN");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::BelowBoundary, "BELOW_BOUNDARY");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::AtBoundary, "AT_BOUNDARY");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::AboveBoundary, "ABOVE_BOUNDARY");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::TypeMax, "TYPE_MAX");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::FalseValue, "FALSE_VALUE");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::TrueValue, "TRUE_VALUE");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::MaskCleared, "MASK_CLEARED");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::MaskSet, "MASK_SET");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::SatLeft, "SAT_LEFT");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::SatRight, "SAT_RIGHT");
        RIFT_ENUM_STRING_CASE(MutationValuePurpose::EnumAlternative, "ENUM_ALTERNATIVE");
    }
    return "AT_BOUNDARY";
}

const char *to_string(SolverOutcome value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(SolverOutcome::Sat, "SAT");
        RIFT_ENUM_STRING_CASE(SolverOutcome::Unsat, "UNSAT");
        RIFT_ENUM_STRING_CASE(SolverOutcome::Unknown, "UNKNOWN");
        RIFT_ENUM_STRING_CASE(SolverOutcome::Timeout, "TIMEOUT");
        RIFT_ENUM_STRING_CASE(SolverOutcome::Unsupported, "UNSUPPORTED");
        RIFT_ENUM_STRING_CASE(SolverOutcome::NotRun, "NOT_RUN");
    }
    return "UNKNOWN";
}

const char *to_string(FlipClass value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(FlipClass::LocalSummarySatPair, "LOCAL_SUMMARY_SAT_PAIR");
        RIFT_ENUM_STRING_CASE(FlipClass::SamePathFlip, "SAME_PATH_FLIP");
        RIFT_ENUM_STRING_CASE(FlipClass::CrossPathFlip, "CROSS_PATH_FLIP");
        RIFT_ENUM_STRING_CASE(FlipClass::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(JointActionClaim value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(JointActionClaim::SingleAction, "SINGLE_ACTION");
        RIFT_ENUM_STRING_CASE(JointActionClaim::JointRequired, "JOINT_REQUIRED");
        RIFT_ENUM_STRING_CASE(JointActionClaim::JointUnknown, "JOINT_UNKNOWN");
    }
    return "JOINT_UNKNOWN";
}

const char *to_string(PrerequisiteStatus value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(PrerequisiteStatus::Complete, "COMPLETE");
        RIFT_ENUM_STRING_CASE(PrerequisiteStatus::PartialOrderUnknown, "PARTIAL_ORDER_UNKNOWN");
    }
    return "PARTIAL_ORDER_UNKNOWN";
}

const char *to_string(TimingStatus value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TimingStatus::Exact, "EXACT");
        RIFT_ENUM_STRING_CASE(TimingStatus::WidenedUnknown, "WIDENED_UNKNOWN");
        RIFT_ENUM_STRING_CASE(TimingStatus::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(TimingEndpoint value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TimingEndpoint::Open, "OPEN");
        RIFT_ENUM_STRING_CASE(TimingEndpoint::Closed, "CLOSED");
        RIFT_ENUM_STRING_CASE(TimingEndpoint::Mixed, "MIXED");
        RIFT_ENUM_STRING_CASE(TimingEndpoint::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(TimingMutationAction value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TimingMutationAction::Delay, "DELAY");
        RIFT_ENUM_STRING_CASE(TimingMutationAction::Pause, "PAUSE");
        RIFT_ENUM_STRING_CASE(TimingMutationAction::Drop, "DROP");
        RIFT_ENUM_STRING_CASE(TimingMutationAction::Repeat, "REPEAT");
        RIFT_ENUM_STRING_CASE(TimingMutationAction::Reorder, "REORDER");
        RIFT_ENUM_STRING_CASE(TimingMutationAction::ChangeInterval, "CHANGE_INTERVAL");
    }
    return "CHANGE_INTERVAL";
}

const char *to_string(ReplayStatus value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(ReplayStatus::Ready, "READY");
        RIFT_ENUM_STRING_CASE(ReplayStatus::Partial, "PARTIAL");
        RIFT_ENUM_STRING_CASE(ReplayStatus::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

const char *to_string(ReplayExpectedRelation value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(ReplayExpectedRelation::ApTruthChange, "AP_TRUTH_CHANGE");
        RIFT_ENUM_STRING_CASE(ReplayExpectedRelation::MonitorSuccessorChange, "MONITOR_SUCCESSOR_CHANGE");
        RIFT_ENUM_STRING_CASE(ReplayExpectedRelation::Unknown, "UNKNOWN");
    }
    return "UNKNOWN";
}

#undef RIFT_ENUM_STRING_CASE

}  // namespace rift::core
