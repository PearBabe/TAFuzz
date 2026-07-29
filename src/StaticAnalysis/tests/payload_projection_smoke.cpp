#include "rift/core/production.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

using namespace rift::core;

void require(bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        std::exit(1);
    }
}

std::string reasons(const ExternalPayloadProjection &projection) {
    std::string result;
    for (const std::string &reason : projection.uncertainty_reasons) {
        if (!result.empty()) result += "; ";
        result += reason;
    }
    return result;
}

ValueType signed_int() {
    ValueType type;
    type.kind = ValueKind::Integer;
    type.canonical = "int";
    type.bit_width = 32;
    type.is_signed = true;
    return type;
}

ContextualNode node(std::string id, std::string semantic) {
    ContextualNode result;
    result.node_id = std::move(id);
    result.semantic_node_id = std::move(semantic);
    result.kind = SemanticNodeKind::Value;
    result.value_type = signed_int();
    result.scope.status = IdentityStatus::Exact;
    result.scope.scope_id = "scope.instance";
    result.generation.kind = IdentityStatus::Exact;
    result.generation.identity = "generation.instance";
    result.generation.reuse_possible = false;
    return result;
}

TransferExpression input_expression(const std::string &node_id) {
    TransferExpression expression;
    expression.kind = TransferExprKind::Input;
    expression.value_type = signed_int();
    expression.input = TransferSymbolRef{
        TransferSymbolDomain::ContextualNode, node_id, signed_int()};
    expression.expression_id = canonical_transfer_expression_id(expression);
    return expression;
}

TransferExpression affine_expression(
    const std::string &input_id, std::string scale, std::string offset) {
    TransferExpression expression;
    expression.kind = TransferExprKind::Affine;
    expression.value_type = signed_int();
    expression.operand_expression_ids = {input_id};
    expression.affine_coefficients = {std::move(scale)};
    expression.affine_offset = std::move(offset);
    expression.expression_id = canonical_transfer_expression_id(expression);
    return expression;
}

ModelValueTransferV2 identity_model() {
    ModelValueTransferV2 transfer;
    transfer.kind = ModelValueTransferKind::Identity;
    transfer.precondition = ModelValuePrecondition::None;
    transfer.executor_enforces_precondition = false;
    transfer.failure_branch_unknown = false;
    return transfer;
}

struct Fixture {
    ContextualInfluenceGraph graph;
    ModelFactOverlay overlay;
    ContextualValueTransferIndex transfers;
    FrontierCandidate candidate;
    std::vector<PayloadProjectionTargetRequest> targets;
};

Fixture fixture() {
    Fixture value;
    value.graph.artifact_id = "graph.fixture";
    value.graph.status = StageStatus::Complete;
    value.graph.nodes = {
        node("context.input", "semantic.input"),
        node("context.shifted", "semantic.shifted")};
    InfluenceEdge edge;
    edge.edge_id = "edge.data";
    edge.source_node_id = "context.input";
    edge.target_node_id = "context.shifted";
    edge.kind = RelationKind::Data;
    edge.certainty = Certainty::Must;
    value.graph.edges.push_back(edge);

    ExternalAction action;
    action.external_action_id = "action.payload";
    action.action_schema_id = "schema.scalar";
    action.action_class = "scalar";
    action.channel = "fixture";
    action.operation = "set";
    action.payload_type = signed_int();
    action.payload_slot = "payload.value";
    action.scope_schema = "scope-key";
    action.generation_schema = "generation-key";
    action.timing_capability = "none";
    action.required_capability = "DIRECT";
    value.overlay.status = StageStatus::Complete;
    value.overlay.external_actions.push_back(action);
    value.overlay.boundary_attachments.push_back({
        "attachment.input", action.external_action_id, "semantic.input",
        "payload_to_value", Certainty::Modelled, {}, identity_model()});

    value.candidate.candidate_id = "candidate.payload";
    value.candidate.action = action;
    value.candidate.cone_id = "cone.fixture";
    value.candidate.ap_id = "ap.fixture";
    value.candidate.disposition = FrontierDisposition::Actionable;
    value.candidate.evidence.completeness.model_vm_complete = true;
    value.candidate.evidence.completeness.attachment_enumeration_complete = true;
    value.candidate.evidence.completeness.forward_enumeration_complete = true;
    value.candidate.evidence.completeness.cone_complete = true;
    value.candidate.evidence.completeness.compatibility_complete = true;
    FrontierWitness witness;
    witness.witness_id = "witness.input";
    witness.attachment_id = "attachment.input";
    witness.boundary_node_id = "context.input";
    witness.compatibility = WitnessCompatibility::Compatible;
    witness.reachability = ReachabilityVerdict::ModelledWitness;
    value.candidate.witnesses.push_back(witness);

    value.transfers.artifact_id = "contextual-transfers.fixture";
    value.transfers.semantic_value_transfer_artifact_id =
        "semantic-transfers.fixture";
    value.transfers.semantic_index_sha256 = std::string(64, '1');
    value.transfers.graph_artifact_id = value.graph.artifact_id;
    value.transfers.semantic_value_transfers_sha256 = std::string(64, '2');
    value.transfers.graph_sha256 = std::string(64, '3');
    value.transfers.physical_digest_binding_complete = true;
    value.transfers.property_independent = true;
    value.transfers.candidate_accounting_complete = true;
    value.transfers.resource_limit_hit = false;
    value.transfers.status = StageStatus::Complete;
    TransferExpression input = input_expression("context.input");
    TransferExpression affine = affine_expression(input.expression_id, "3", "2");
    value.transfers.expressions = {input, affine};
    TypedValueTransfer transfer;
    transfer.program_point_id = "program-point.shifted";
    transfer.output_domain = TransferEndpointDomain::ContextualNode;
    transfer.input_node_ids = {"context.input"};
    transfer.output_node_id = "context.shifted";
    transfer.supporting_edge_ids = {"edge.data"};
    transfer.value_expression_id = affine.expression_id;
    transfer.definedness = DefinednessClass::Total;
    transfer.path_condition = PathConditionClass::Unconditional;
    transfer.soundness = TransferSoundness::Exact;
    transfer.certainty = Certainty::Must;
    transfer.transfer_id = canonical_typed_value_transfer_id(transfer);
    value.transfers.transfers.push_back(transfer);
    value.targets.push_back({"selector.shifted", {"context.shifted"}});
    return value;
}

bool has_affine_root(const ExternalPayloadProjection &projection) {
    const std::string root = projection.targets.front().value_expression_id;
    const auto found = std::find_if(
        projection.expressions.begin(), projection.expressions.end(),
        [&](const TransferExpression &expression) {
            return expression.expression_id == root;
        });
    return found != projection.expressions.end() &&
           found->kind == TransferExprKind::Affine &&
           found->affine_coefficients == std::vector<std::string>{"3"} &&
           found->affine_offset == std::optional<std::string>{"2"};
}

void test_exact_affine_projection() {
    Fixture value = fixture();
    const ExternalPayloadProjection projection =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        projection.status == PayloadProjectionStatus::Exact &&
            projection.targets.size() == 1 &&
            projection.targets.front().status ==
                PayloadProjectionStatus::Exact,
        "typed affine path closes one external payload projection: " +
            reasons(projection));
    require(has_affine_root(projection),
            "3*x+2 remains in the external payload coordinate");
    require(
        validate_external_payload_projection(
            projection, value.candidate, value.graph, value.overlay,
            value.transfers, value.targets)
            .empty(),
        "payload projection is deterministically recomputable");
}

void test_generic_data_edge_is_not_identity() {
    Fixture value = fixture();
    value.transfers.transfers.clear();
    value.transfers.expressions.clear();
    const ExternalPayloadProjection projection =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        projection.status == PayloadProjectionStatus::Unknown,
        "generic Data reachability never licenses payload identity");
}

void test_unknown_alternative_dominates_exact_path() {
    Fixture value = fixture();
    TransferExpression unknown;
    unknown.kind = TransferExprKind::Unknown;
    unknown.value_type = signed_int();
    unknown.uncertainty_reasons = {"fixture unknown branch"};
    unknown.expression_id = canonical_transfer_expression_id(unknown);
    value.transfers.expressions.push_back(unknown);
    TypedValueTransfer alternative = value.transfers.transfers.front();
    alternative.program_point_id = "program-point.unknown-alternative";
    alternative.value_expression_id = unknown.expression_id;
    alternative.soundness = TransferSoundness::Unknown;
    alternative.certainty = Certainty::Unknown;
    alternative.uncertainty_reasons = {"fixture unknown branch"};
    alternative.transfer_id = canonical_typed_value_transfer_id(alternative);
    value.transfers.transfers.push_back(alternative);
    const ExternalPayloadProjection projection =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        projection.status == PayloadProjectionStatus::Unknown &&
            std::any_of(
                projection.uncertainty_reasons.begin(),
                projection.uncertainty_reasons.end(),
                [](const std::string &reason) {
                    return reason.find("alternative") != std::string::npos;
                }),
        "exact plus UNKNOWN alternative fails closed");
}

void test_scope_generation_and_digest_are_not_labels() {
    Fixture value = fixture();
    value.graph.nodes.back().generation.kind = IdentityStatus::Unknown;
    value.graph.nodes.back().generation.identity.reset();
    const ExternalPayloadProjection unknown_generation =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        unknown_generation.status == PayloadProjectionStatus::Unknown,
        "matching schema strings do not prove generation co-reference");

    value = fixture();
    value.transfers.physical_digest_binding_complete = false;
    const ExternalPayloadProjection unbound =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        unbound.status == PayloadProjectionStatus::Unknown,
        "unbound sidecar bytes cannot support a payload projection");
}

void test_one_action_controls_two_occurrences() {
    Fixture value = fixture();
    value.graph.nodes.push_back(node("context.second", "semantic.second"));
    InfluenceEdge edge;
    edge.edge_id = "edge.second";
    edge.source_node_id = "context.input";
    edge.target_node_id = "context.second";
    edge.kind = RelationKind::Defines;
    edge.certainty = Certainty::Must;
    value.graph.edges.push_back(edge);
    TransferExpression input = input_expression("context.input");
    TransferExpression identity;
    identity.kind = TransferExprKind::Identity;
    identity.value_type = signed_int();
    identity.operand_expression_ids = {input.expression_id};
    identity.expression_id = canonical_transfer_expression_id(identity);
    value.transfers.expressions.push_back(identity);
    TypedValueTransfer transfer;
    transfer.program_point_id = "program-point.second";
    transfer.output_domain = TransferEndpointDomain::ContextualNode;
    transfer.input_node_ids = {"context.input"};
    transfer.output_node_id = "context.second";
    transfer.supporting_edge_ids = {"edge.second"};
    transfer.value_expression_id = identity.expression_id;
    transfer.definedness = DefinednessClass::Total;
    transfer.path_condition = PathConditionClass::Unconditional;
    transfer.soundness = TransferSoundness::Exact;
    transfer.certainty = Certainty::Must;
    transfer.transfer_id = canonical_typed_value_transfer_id(transfer);
    value.transfers.transfers.push_back(transfer);
    value.targets.push_back({"selector.second", {"context.second"}});
    const ExternalPayloadProjection projection =
        compose_external_payload_projection(
            value.candidate, value.graph, value.overlay, value.transfers,
            value.targets);
    require(
        projection.status == PayloadProjectionStatus::Exact &&
            projection.targets.size() == 2 &&
            projection.coordinate.external_action_id == "action.payload",
        "two predicate occurrences share one external payload coordinate");
}

}  // namespace

int main() {
    test_exact_affine_projection();
    test_generic_data_edge_is_not_identity();
    test_unknown_alternative_dominates_exact_path();
    test_scope_generation_and_digest_are_not_labels();
    test_one_action_controls_two_occurrences();
    std::cout << "payload projection smoke: PASS\n";
    return 0;
}
