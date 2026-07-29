#include "rift/core/payload_projection.h"

#include <algorithm>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace rift::core {
namespace {

template <typename T>
void sort_unique(std::vector<T> &values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
}

void append_unique(std::vector<std::string> &values, std::string value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(std::move(value));
    }
}

bool same_value_type(const ValueType &left, const ValueType &right) {
    return left.kind == right.kind && left.canonical == right.canonical &&
           left.bit_width == right.bit_width &&
           left.is_signed == right.is_signed && left.unit == right.unit;
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

std::string value_type_material(const ValueType &type) {
    std::ostringstream material;
    material << static_cast<int>(type.kind) << '\0' << type.canonical << '\0';
    if (type.bit_width) material << *type.bit_width;
    material << '\0';
    if (type.is_signed) material << (*type.is_signed ? '1' : '0');
    material << '\0';
    if (type.unit) material << *type.unit;
    return material.str();
}

bool candidate_complete(const FrontierCandidate &candidate) {
    const FrontierCompletenessLedger &ledger = candidate.evidence.completeness;
    return ledger.model_vm_complete &&
           ledger.attachment_enumeration_complete &&
           ledger.forward_enumeration_complete && ledger.cone_complete &&
           ledger.compatibility_complete && ledger.gap_reasons.empty();
}

bool usable_witness(const FrontierWitness &witness) {
    return witness.compatibility == WitnessCompatibility::Compatible &&
           (witness.reachability == ReachabilityVerdict::StaticWitness ||
            witness.reachability == ReachabilityVerdict::ModelledWitness);
}

const ExternalAction *find_action(
    const ModelFactOverlay &overlay, const std::string &action_id) {
    const auto found = std::find_if(
        overlay.external_actions.begin(), overlay.external_actions.end(),
        [&](const ExternalAction &action) {
            return action.external_action_id == action_id;
        });
    return found == overlay.external_actions.end() ? nullptr : &*found;
}

const BoundaryAttachment *find_attachment(
    const ModelFactOverlay &overlay, const std::string &attachment_id) {
    const auto found = std::find_if(
        overlay.boundary_attachments.begin(),
        overlay.boundary_attachments.end(),
        [&](const BoundaryAttachment &attachment) {
            return attachment.attachment_id == attachment_id;
        });
    return found == overlay.boundary_attachments.end() ? nullptr : &*found;
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

struct ProjectionState {
    std::string expression_id;
    std::vector<std::string> application_ids;
    std::optional<std::string> defined_when_expression_id;
    std::optional<std::string> path_condition_expression_id;
};

class Composer {
  public:
    Composer(
        const FrontierCandidate &candidate,
        const ContextualInfluenceGraph &graph,
        const ModelFactOverlay &overlay,
        const ContextualValueTransferIndex &value_transfers,
        std::vector<PayloadProjectionTargetRequest> targets,
        const PayloadProjectionOptions &options)
        : candidate_(candidate), graph_(graph), overlay_(overlay),
          value_transfers_(value_transfers), targets_(std::move(targets)),
          options_(options) {
        for (const ContextualNode &node : graph_.nodes) {
            nodes_.emplace(node.node_id, &node);
        }
        for (const InfluenceEdge &edge : graph_.edges) {
            edges_.emplace(edge.edge_id, &edge);
        }
        for (const TransferExpression &expression :
             value_transfers_.expressions) {
            source_expressions_.emplace(
                expression.expression_id, &expression);
        }
        std::sort(
            targets_.begin(), targets_.end(),
            [](const PayloadProjectionTargetRequest &left,
               const PayloadProjectionTargetRequest &right) {
                return std::tie(
                           left.selector_id, left.contextual_node_ids) <
                       std::tie(
                           right.selector_id, right.contextual_node_ids);
            });
        for (PayloadProjectionTargetRequest &target : targets_) {
            sort_unique(target.contextual_node_ids);
        }
    }

    ExternalPayloadProjection run() {
        initialize_coordinate();
        validate_inputs();
        if (!projection_.uncertainty_reasons.empty()) {
            finalize();
            return projection_;
        }
        seed_boundary();
        if (states_.empty()) {
            add_reason("no exact candidate-local boundary payload seed exists");
            finalize();
            return projection_;
        }
        compute_relevant_nodes();
        propagate();
        materialize_targets();
        audit_unknown_alternatives();
        finalize();
        return projection_;
    }

  private:
    void add_reason(std::string reason) {
        append_unique(projection_.uncertainty_reasons, std::move(reason));
    }

    void initialize_coordinate() {
        projection_.coordinate.external_action_id =
            candidate_.action.external_action_id;
        projection_.coordinate.payload_slot = candidate_.action.payload_slot;
        projection_.coordinate.value_type = candidate_.action.payload_type;
        projection_.coordinate.scope_schema = candidate_.action.scope_schema;
        projection_.coordinate.generation_schema =
            candidate_.action.generation_schema;
        projection_.coordinate.coordinate_id = stable_id(
            "external-payload-coordinate",
            candidate_.action.external_action_id + '\0' +
                candidate_.action.payload_slot + '\0' +
                value_type_material(candidate_.action.payload_type) + '\0' +
                candidate_.action.scope_schema + '\0' +
                candidate_.action.generation_schema);
        TransferExpression input;
        input.kind = TransferExprKind::Input;
        input.value_type = candidate_.action.payload_type;
        input.input = TransferSymbolRef{
            TransferSymbolDomain::ExternalActionPayload,
            projection_.coordinate.coordinate_id,
            candidate_.action.payload_type};
        coordinate_expression_id_ = intern(std::move(input));
    }

    void validate_inputs() {
        if (candidate_.disposition != FrontierDisposition::Actionable) {
            add_reason("frontier candidate is not actionable");
        }
        if (!candidate_complete(candidate_)) {
            add_reason("frontier candidate completeness ledger is open");
        }
        const ExternalAction *overlay_action = find_action(
            overlay_, candidate_.action.external_action_id);
        if (overlay_action == nullptr) {
            add_reason("external action is absent from the model overlay");
        } else if (!same_action_contract(candidate_.action, *overlay_action)) {
            add_reason("frontier and model-overlay action contracts differ");
        }
        if (!value_transfers_.physical_digest_binding_complete) {
            add_reason("contextual value-transfer physical digest binding is incomplete");
        }
        if (!value_transfers_.property_independent) {
            add_reason("contextual value-transfer sidecar is not property independent");
        }
        if (!value_transfers_.candidate_accounting_complete ||
            value_transfers_.resource_limit_hit ||
            value_transfers_.status != StageStatus::Complete ||
            !value_transfers_.coverage_gaps.empty()) {
            add_reason("contextual value-transfer accounting is incomplete");
        }
        if (value_transfers_.graph_artifact_id != graph_.artifact_id) {
            add_reason("contextual value-transfer sidecar is cross-wired to another graph");
        }
        if (targets_.empty()) {
            add_reason("no predicate target was requested");
        }
        std::set<std::string> selectors;
        for (const PayloadProjectionTargetRequest &target : targets_) {
            if (target.selector_id.empty() ||
                !selectors.insert(target.selector_id).second) {
                add_reason("predicate target selector IDs are empty or duplicated");
            }
            if (target.contextual_node_ids.size() != 1) {
                add_reason(
                    "a predicate selector does not resolve to exactly one contextual instance");
            }
            for (const std::string &node_id : target.contextual_node_ids) {
                if (!nodes_.contains(node_id)) {
                    add_reason("predicate target references an unknown contextual node");
                }
            }
        }
    }

    bool exact_context(
        const ContextualNode &boundary, const ContextualNode &node,
        std::string &reason) const {
        if (options_.require_exact_scope &&
            (boundary.scope.status != IdentityStatus::Exact ||
             node.scope.status != IdentityStatus::Exact ||
             boundary.scope.scope_id.empty() ||
             boundary.scope.scope_id != node.scope.scope_id)) {
            reason = "scope co-reference is not exact";
            return false;
        }
        if (options_.require_exact_generation &&
            (boundary.generation.kind != IdentityStatus::Exact ||
             node.generation.kind != IdentityStatus::Exact ||
             !boundary.generation.identity || !node.generation.identity ||
             boundary.generation.identity != node.generation.identity ||
             boundary.generation.reuse_possible ||
             node.generation.reuse_possible)) {
            reason = "generation co-reference is not exact";
            return false;
        }
        return true;
    }

    std::optional<std::string> model_boundary_expression(
        const BoundaryAttachment &attachment,
        const ContextualNode &boundary) {
        if (attachment.certainty == Certainty::Unknown) {
            add_reason("boundary attachment certainty is UNKNOWN");
            return std::nullopt;
        }
        if (!attachment.value_transfer) {
            add_reason("boundary attachment has no typed value transfer");
            return std::nullopt;
        }
        if (!same_value_type(
                candidate_.action.payload_type, boundary.value_type)) {
            add_reason("boundary payload and contextual node types differ");
            return std::nullopt;
        }
        TransferExpression expression;
        expression.value_type = boundary.value_type;
        expression.operand_expression_ids = {coordinate_expression_id_};
        const ModelValueTransferV2 &model = *attachment.value_transfer;
        switch (model.kind) {
        case ModelValueTransferKind::Identity:
            expression.kind = TransferExprKind::Identity;
            break;
        case ModelValueTransferKind::Affine:
            if (!model.affine_scale || !model.affine_offset ||
                model.precondition != ModelValuePrecondition::None ||
                model.executor_enforces_precondition ||
                model.failure_branch_unknown) {
                add_reason("boundary affine transfer is incomplete");
                return std::nullopt;
            }
            expression.kind = TransferExprKind::Affine;
            expression.affine_coefficients = {
                std::to_string(*model.affine_scale)};
            expression.affine_offset =
                std::to_string(*model.affine_offset);
            break;
        case ModelValueTransferKind::ParseIdentityWithPrecondition:
            if (model.precondition !=
                    ModelValuePrecondition::CanonicalDecimalIntegerInRange ||
                !model.executor_enforces_precondition ||
                !model.failure_branch_unknown) {
                add_reason("boundary parse transfer precondition is not executor-closed");
                return std::nullopt;
            }
            expression.kind = TransferExprKind::Parse;
            break;
        case ModelValueTransferKind::Unknown:
            add_reason("boundary value transfer is UNKNOWN");
            return std::nullopt;
        }
        return intern(std::move(expression));
    }

    void seed_boundary() {
        std::vector<std::pair<const FrontierWitness *, const BoundaryAttachment *>>
            seeds;
        for (const FrontierWitness &witness : candidate_.witnesses) {
            if (!usable_witness(witness)) continue;
            const BoundaryAttachment *attachment = find_attachment(
                overlay_, witness.attachment_id);
            if (attachment == nullptr ||
                attachment->external_action_id !=
                    candidate_.action.external_action_id) {
                continue;
            }
            seeds.emplace_back(&witness, attachment);
        }
        std::sort(
            seeds.begin(), seeds.end(),
            [](const auto &left, const auto &right) {
                return std::tie(
                           left.first->boundary_node_id,
                           left.second->attachment_id) <
                       std::tie(
                           right.first->boundary_node_id,
                           right.second->attachment_id);
            });
        seeds.erase(
            std::unique(
                seeds.begin(), seeds.end(), [](const auto &left, const auto &right) {
                    return left.first->boundary_node_id ==
                               right.first->boundary_node_id &&
                           left.second->attachment_id ==
                               right.second->attachment_id;
                }),
            seeds.end());
        if (seeds.size() != 1) {
            add_reason(
                "external action does not resolve to exactly one candidate-local contextual boundary instance");
            return;
        }
        const FrontierWitness &witness = *seeds.front().first;
        const BoundaryAttachment &attachment = *seeds.front().second;
        const auto boundary = nodes_.find(witness.boundary_node_id);
        if (boundary == nodes_.end() ||
            boundary->second->semantic_node_id !=
                attachment.semantic_node_id) {
            add_reason("boundary witness and attachment semantic identities differ");
            return;
        }
        boundary_node_ = boundary->second;
        std::string context_reason;
        if (!exact_context(*boundary_node_, *boundary_node_, context_reason)) {
            add_reason(context_reason);
            return;
        }
        const std::optional<std::string> root =
            model_boundary_expression(attachment, *boundary_node_);
        if (!root) return;
        PayloadTransferApplication application;
        application.kind = PayloadApplicationKind::BoundaryAttachment;
        application.attachment_id = attachment.attachment_id;
        application.input_node_ids = {};
        application.output_node_id = boundary_node_->node_id;
        application.value_expression_id = *root;
        application.application_id = stable_id(
            "payload-transfer-application",
            std::string("boundary\0", 9) + attachment.attachment_id + '\0' +
                boundary_node_->node_id + '\0' + *root);
        projection_.applications.push_back(application);
        states_[boundary_node_->node_id] = ProjectionState{
            *root, {application.application_id}, std::nullopt, std::nullopt};
    }

    void compute_relevant_nodes() {
        for (const PayloadProjectionTargetRequest &target : targets_) {
            relevant_nodes_.insert(
                target.contextual_node_ids.begin(),
                target.contextual_node_ids.end());
        }
        bool changed = true;
        while (changed) {
            changed = false;
            for (const TypedValueTransfer &transfer : value_transfers_.transfers) {
                if (!relevant_nodes_.contains(transfer.output_node_id)) continue;
                for (const std::string &input : transfer.input_node_ids) {
                    changed = relevant_nodes_.insert(input).second || changed;
                }
            }
        }
    }

    std::string intern(TransferExpression expression) {
        expression.expression_id = canonical_transfer_expression_id(expression);
        const std::string expression_id = expression.expression_id;
        const auto known = projection_expression_indices_.find(
            expression_id);
        if (known == projection_expression_indices_.end()) {
            projection_expression_indices_[expression_id] =
                projection_.expressions.size();
            projection_.expressions.push_back(std::move(expression));
        }
        return expression_id;
    }

    std::optional<std::string> clone_expression(
        const std::string &source_id,
        std::map<std::string, std::string> &memo,
        std::vector<std::string> &reasons) {
        const auto memoized = memo.find(source_id);
        if (memoized != memo.end()) return memoized->second;
        const auto found = source_expressions_.find(source_id);
        if (found == source_expressions_.end()) {
            append_unique(reasons, "typed transfer references a missing expression");
            return std::nullopt;
        }
        const TransferExpression &source = *found->second;
        if (source.kind == TransferExprKind::Unknown) {
            append_unique(reasons, "typed transfer expression contains UNKNOWN");
            return std::nullopt;
        }
        if (source.kind == TransferExprKind::Input) {
            if (!source.input ||
                source.input->domain != TransferSymbolDomain::ContextualNode) {
                append_unique(reasons, "typed transfer input has an invalid domain");
                return std::nullopt;
            }
            const auto projected = states_.find(source.input->symbol_id);
            if (projected != states_.end()) {
                const auto node = nodes_.find(source.input->symbol_id);
                if (node == nodes_.end() ||
                    !same_value_type(
                        node->second->value_type,
                        source.input->value_type)) {
                    append_unique(reasons, "typed transfer input type is inconsistent");
                    return std::nullopt;
                }
                memo[source_id] = projected->second.expression_id;
                return projected->second.expression_id;
            }
            TransferExpression shared = source;
            shared.expression_id.clear();
            const std::string cloned = intern(std::move(shared));
            memo[source_id] = cloned;
            return cloned;
        }
        TransferExpression clone = source;
        clone.expression_id.clear();
        clone.operand_expression_ids.clear();
        clone.guard_expression_ids.clear();
        for (const std::string &operand : source.operand_expression_ids) {
            const std::optional<std::string> child =
                clone_expression(operand, memo, reasons);
            if (!child) return std::nullopt;
            clone.operand_expression_ids.push_back(*child);
        }
        for (const std::string &guard : source.guard_expression_ids) {
            const std::optional<std::string> child =
                clone_expression(guard, memo, reasons);
            if (!child) return std::nullopt;
            clone.guard_expression_ids.push_back(*child);
        }
        const std::string cloned = intern(std::move(clone));
        memo[source_id] = cloned;
        return cloned;
    }

    RelationKind relation_for(
        const TypedValueTransfer &transfer,
        const std::string &input_node_id) const {
        for (const std::string &edge_id : transfer.supporting_edge_ids) {
            const auto found = edges_.find(edge_id);
            if (found != edges_.end() &&
                found->second->source_node_id == input_node_id &&
                found->second->target_node_id == transfer.output_node_id) {
                return found->second->kind;
            }
        }
        const auto expression = source_expressions_.find(
            transfer.value_expression_id);
        if (expression != source_expressions_.end()) {
            if (expression->second->kind == TransferExprKind::CallArg) {
                return RelationKind::Call;
            }
            if (expression->second->kind == TransferExprKind::Return) {
                return RelationKind::Return;
            }
        }
        return RelationKind::MapsTo;
    }

    bool contexts_close(
        const TypedValueTransfer &transfer,
        std::vector<std::string> &reasons) const {
        const auto output = nodes_.find(transfer.output_node_id);
        if (output == nodes_.end() || boundary_node_ == nullptr) {
            append_unique(reasons, "typed transfer output node is missing");
            return false;
        }
        std::string context_reason;
        if (!exact_context(*boundary_node_, *output->second, context_reason)) {
            append_unique(reasons, context_reason);
            return false;
        }
        for (const std::string &input_id : transfer.input_node_ids) {
            if (!states_.contains(input_id)) continue;
            if (!value_capable_relation(relation_for(transfer, input_id))) {
                append_unique(
                    reasons,
                    "typed transfer is supported only by a non-value relation");
                return false;
            }
            const auto input = nodes_.find(input_id);
            if (input == nodes_.end()) {
                append_unique(reasons, "typed transfer input node is missing");
                return false;
            }
            if (!exact_context(*boundary_node_, *input->second, context_reason)) {
                append_unique(reasons, context_reason);
                return false;
            }
            const ContextCompatibilityResult compatibility =
                evaluate_contextual_compatibility(
                    *input->second, *output->second,
                    relation_for(transfer, input_id));
            if (compatibility.verdict != WitnessCompatibility::Compatible) {
                append_unique(
                    reasons,
                    "typed transfer contexts are not exactly concatenable");
                return false;
            }
        }
        return true;
    }

    bool apply_transfer(const TypedValueTransfer &transfer) {
        if (!relevant_nodes_.contains(transfer.output_node_id)) return false;
        bool depends_on_payload = false;
        for (const std::string &input : transfer.input_node_ids) {
            depends_on_payload = states_.contains(input) || depends_on_payload;
        }
        if (!depends_on_payload) return false;
        if (transfer.output_domain != TransferEndpointDomain::ContextualNode ||
            transfer.soundness != TransferSoundness::Exact ||
            transfer.certainty != Certainty::Must ||
            transfer.definedness == DefinednessClass::Unknown ||
            transfer.path_condition != PathConditionClass::Unconditional ||
            !transfer.uncertainty_reasons.empty()) {
            unknown_relevant_transfers_.insert(transfer.transfer_id);
            return false;
        }
        std::vector<std::string> reasons;
        if (!contexts_close(transfer, reasons)) {
            unknown_relevant_transfers_.insert(transfer.transfer_id);
            for (std::string &reason : reasons) add_reason(std::move(reason));
            return false;
        }
        std::map<std::string, std::string> memo;
        const std::optional<std::string> value = clone_expression(
            transfer.value_expression_id, memo, reasons);
        std::optional<std::string> defined;
        if (value && transfer.defined_when_expression_id) {
            defined = clone_expression(
                *transfer.defined_when_expression_id, memo, reasons);
        }
        std::optional<std::string> path_condition;
        if (value && transfer.path_condition_expression_id) {
            path_condition = clone_expression(
                *transfer.path_condition_expression_id, memo, reasons);
        }
        if (!value ||
            (transfer.defined_when_expression_id && !defined) ||
            (transfer.path_condition_expression_id && !path_condition)) {
            unknown_relevant_transfers_.insert(transfer.transfer_id);
            for (std::string &reason : reasons) add_reason(std::move(reason));
            return false;
        }
        std::vector<std::string> application_chain;
        for (const std::string &input : transfer.input_node_ids) {
            const auto state = states_.find(input);
            if (state == states_.end()) continue;
            application_chain.insert(
                application_chain.end(), state->second.application_ids.begin(),
                state->second.application_ids.end());
        }
        sort_unique(application_chain);
        std::ostringstream application_material;
        application_material << transfer.transfer_id << '\0'
                             << transfer.output_node_id << '\0' << *value;
        for (const std::string &application : application_chain) {
            application_material << '\0' << application;
        }
        PayloadTransferApplication application;
        application.kind = PayloadApplicationKind::TypedTransfer;
        application.transfer_id = transfer.transfer_id;
        application.input_node_ids = transfer.input_node_ids;
        sort_unique(application.input_node_ids);
        application.output_node_id = transfer.output_node_id;
        application.value_expression_id = *value;
        application.defined_when_expression_id = defined;
        application.path_condition_expression_id = path_condition;
        application.application_id = stable_id(
            "payload-transfer-application", application_material.str());
        application_chain.push_back(application.application_id);
        sort_unique(application_chain);

        const ProjectionState proposed{
            *value, application_chain, defined, path_condition};
        const auto current = states_.find(transfer.output_node_id);
        if (current == states_.end()) {
            states_[transfer.output_node_id] = proposed;
            projection_.applications.push_back(std::move(application));
            return true;
        }
        if (current->second.expression_id != proposed.expression_id ||
            current->second.defined_when_expression_id !=
                proposed.defined_when_expression_id ||
            current->second.path_condition_expression_id !=
                proposed.path_condition_expression_id) {
            ambiguous_outputs_.insert(transfer.output_node_id);
            return false;
        }
        for (const std::string &id : proposed.application_ids) {
            append_unique(current->second.application_ids, id);
        }
        if (std::none_of(
                projection_.applications.begin(),
                projection_.applications.end(),
                [&](const PayloadTransferApplication &existing) {
                    return existing.application_id == application.application_id;
                })) {
            projection_.applications.push_back(std::move(application));
        }
        return false;
    }

    void propagate() {
        std::vector<const TypedValueTransfer *> transfers;
        for (const TypedValueTransfer &transfer : value_transfers_.transfers) {
            transfers.push_back(&transfer);
        }
        std::sort(
            transfers.begin(), transfers.end(),
            [](const TypedValueTransfer *left,
               const TypedValueTransfer *right) {
                return left->transfer_id < right->transfer_id;
            });
        std::uint64_t rounds = 0;
        bool changed = true;
        while (changed && rounds < options_.maximum_fixpoint_rounds) {
            changed = false;
            ++rounds;
            for (const TypedValueTransfer *transfer : transfers) {
                changed = apply_transfer(*transfer) || changed;
            }
        }
        if (changed) {
            add_reason("payload projection fixpoint round limit was reached");
        }
    }

    void materialize_targets() {
        for (const PayloadProjectionTargetRequest &request : targets_) {
            PayloadProjectedTarget target;
            target.selector_id = request.selector_id;
            if (request.contextual_node_ids.size() == 1) {
                target.contextual_node_id = request.contextual_node_ids.front();
                const auto state = states_.find(target.contextual_node_id);
                if (state != states_.end() &&
                    !ambiguous_outputs_.contains(target.contextual_node_id)) {
                    target.value_expression_id = state->second.expression_id;
                    target.application_ids = state->second.application_ids;
                    target.status = PayloadProjectionStatus::Exact;
                } else {
                    target.uncertainty_reasons.push_back(
                        state == states_.end()
                            ? "no exact typed payload projection reaches the predicate target"
                            : "multiple non-equivalent typed projections reach the predicate target");
                }
            } else {
                target.uncertainty_reasons.push_back(
                    "predicate target contextual identity is not unique");
            }
            projection_.targets.push_back(std::move(target));
        }
    }

    void audit_unknown_alternatives() {
        if (!unknown_relevant_transfers_.empty()) {
            add_reason(
                "an UNKNOWN or non-exact typed transfer is an alternative on the payload-to-predicate region");
        }
        for (const std::string &output : ambiguous_outputs_) {
            if (relevant_nodes_.contains(output)) {
                add_reason(
                    "non-equivalent exact typed-transfer alternatives reach the payload-to-predicate region");
                break;
            }
        }
        for (PayloadProjectedTarget &target : projection_.targets) {
            if (target.status == PayloadProjectionStatus::Unknown) {
                for (const std::string &reason : target.uncertainty_reasons) {
                    add_reason(reason);
                }
            }
        }
    }

    void finalize() {
        sort_unique(projection_.uncertainty_reasons);
        std::sort(
            projection_.expressions.begin(), projection_.expressions.end(),
            [](const TransferExpression &left,
               const TransferExpression &right) {
                return left.expression_id < right.expression_id;
            });
        std::sort(
            projection_.applications.begin(), projection_.applications.end(),
            [](const PayloadTransferApplication &left,
               const PayloadTransferApplication &right) {
                return left.application_id < right.application_id;
            });
        std::sort(
            projection_.targets.begin(), projection_.targets.end(),
            [](const PayloadProjectedTarget &left,
               const PayloadProjectedTarget &right) {
                return std::tie(left.selector_id, left.contextual_node_id) <
                       std::tie(right.selector_id, right.contextual_node_id);
            });
        projection_.candidate_accounting_complete =
            candidate_complete(candidate_) &&
            value_transfers_.candidate_accounting_complete &&
            !value_transfers_.resource_limit_hit &&
            value_transfers_.status == StageStatus::Complete;
        projection_.status =
            projection_.uncertainty_reasons.empty() &&
                    !projection_.targets.empty() &&
                    std::all_of(
                        projection_.targets.begin(), projection_.targets.end(),
                        [](const PayloadProjectedTarget &target) {
                            return target.status ==
                                   PayloadProjectionStatus::Exact;
                        })
                ? PayloadProjectionStatus::Exact
                : PayloadProjectionStatus::Unknown;
        std::ostringstream material;
        material << projection_.coordinate.coordinate_id << '\0'
                 << static_cast<int>(projection_.status);
        for (const PayloadProjectedTarget &target : projection_.targets) {
            material << '\0' << target.selector_id << '\0'
                     << target.contextual_node_id << '\0'
                     << target.value_expression_id;
        }
        for (const PayloadTransferApplication &application :
             projection_.applications) {
            material << '\0' << application.application_id;
        }
        for (const std::string &reason : projection_.uncertainty_reasons) {
            material << '\0' << reason;
        }
        projection_.projection_id = stable_id(
            "external-payload-projection", material.str());
    }

    const FrontierCandidate &candidate_;
    const ContextualInfluenceGraph &graph_;
    const ModelFactOverlay &overlay_;
    const ContextualValueTransferIndex &value_transfers_;
    std::vector<PayloadProjectionTargetRequest> targets_;
    PayloadProjectionOptions options_;
    ExternalPayloadProjection projection_;
    std::string coordinate_expression_id_;
    const ContextualNode *boundary_node_ = nullptr;
    std::unordered_map<std::string, const ContextualNode *> nodes_;
    std::unordered_map<std::string, const InfluenceEdge *> edges_;
    std::unordered_map<std::string, const TransferExpression *>
        source_expressions_;
    std::unordered_map<std::string, std::size_t>
        projection_expression_indices_;
    std::map<std::string, ProjectionState> states_;
    std::set<std::string> relevant_nodes_;
    std::set<std::string> unknown_relevant_transfers_;
    std::set<std::string> ambiguous_outputs_;
};

}  // namespace

ExternalPayloadProjection compose_external_payload_projection(
    const FrontierCandidate &candidate,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay,
    const ContextualValueTransferIndex &value_transfers,
    const std::vector<PayloadProjectionTargetRequest> &targets,
    const PayloadProjectionOptions &options) {
    return Composer(
               candidate, graph, overlay, value_transfers, targets, options)
        .run();
}

std::vector<std::string> validate_external_payload_projection(
    const ExternalPayloadProjection &projection,
    const FrontierCandidate &candidate,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay,
    const ContextualValueTransferIndex &value_transfers,
    const std::vector<PayloadProjectionTargetRequest> &targets,
    const PayloadProjectionOptions &options) {
    const ExternalPayloadProjection expected =
        compose_external_payload_projection(
            candidate, graph, overlay, value_transfers, targets, options);
    if (projection == expected) return {};
    return {
        "external payload projection differs from deterministic recomputation"};
}

const char *to_string(PayloadProjectionStatus value) {
    switch (value) {
    case PayloadProjectionStatus::Exact:
        return "EXACT";
    case PayloadProjectionStatus::Unknown:
        return "UNKNOWN";
    }
    return "UNKNOWN";
}

const char *to_string(PayloadApplicationKind value) {
    switch (value) {
    case PayloadApplicationKind::BoundaryAttachment:
        return "BOUNDARY_ATTACHMENT";
    case PayloadApplicationKind::TypedTransfer:
        return "TYPED_TRANSFER";
    }
    return "TYPED_TRANSFER";
}

}  // namespace rift::core
