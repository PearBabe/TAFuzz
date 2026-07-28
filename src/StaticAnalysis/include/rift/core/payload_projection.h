#ifndef RIFT_CORE_PAYLOAD_PROJECTION_H
#define RIFT_CORE_PAYLOAD_PROJECTION_H

#include "rift/core/frontier.h"
#include "rift/core/value_transfer.h"

#include <optional>
#include <string>
#include <vector>

namespace rift::core {

enum class PayloadProjectionStatus {
    Exact,
    Unknown,
};

enum class PayloadApplicationKind {
    BoundaryAttachment,
    TypedTransfer,
};

struct PayloadProjectionTargetRequest {
    std::string selector_id;
    std::vector<std::string> contextual_node_ids;

    friend bool operator==(
        const PayloadProjectionTargetRequest &,
        const PayloadProjectionTargetRequest &) = default;
};

struct ExternalPayloadCoordinate {
    std::string coordinate_id;
    std::string external_action_id;
    std::string payload_slot;
    ValueType value_type;
    std::string scope_schema;
    std::string generation_schema;

    friend bool operator==(
        const ExternalPayloadCoordinate &,
        const ExternalPayloadCoordinate &) = default;
};

struct PayloadTransferApplication {
    std::string application_id;
    PayloadApplicationKind kind = PayloadApplicationKind::TypedTransfer;
    std::optional<std::string> attachment_id;
    std::optional<std::string> transfer_id;
    std::vector<std::string> input_node_ids;
    std::string output_node_id;
    std::string value_expression_id;
    std::optional<std::string> defined_when_expression_id;
    std::optional<std::string> path_condition_expression_id;

    friend bool operator==(
        const PayloadTransferApplication &,
        const PayloadTransferApplication &) = default;
};

struct PayloadProjectedTarget {
    std::string selector_id;
    std::string contextual_node_id;
    std::string value_expression_id;
    std::vector<std::string> application_ids;
    PayloadProjectionStatus status = PayloadProjectionStatus::Unknown;
    std::vector<std::string> uncertainty_reasons;

    friend bool operator==(
        const PayloadProjectedTarget &,
        const PayloadProjectedTarget &) = default;
};

// This proof is deliberately candidate-local.  Every target in one proof is
// expressed over exactly one external payload coordinate.  Contextual inputs
// not controlled by that action remain shared-state symbols for the later
// two-copy SMT query.
struct ExternalPayloadProjection {
    std::string schema_version = "1.0.0";
    std::string projection_id;
    ExternalPayloadCoordinate coordinate;
    PayloadProjectionStatus status = PayloadProjectionStatus::Unknown;
    bool candidate_accounting_complete = false;
    std::vector<TransferExpression> expressions;
    std::vector<PayloadTransferApplication> applications;
    std::vector<PayloadProjectedTarget> targets;
    std::vector<std::string> uncertainty_reasons;

    friend bool operator==(
        const ExternalPayloadProjection &,
        const ExternalPayloadProjection &) = default;
};

struct PayloadProjectionOptions {
    std::uint64_t maximum_fixpoint_rounds = 1'000'000;
    bool require_exact_scope = true;
    bool require_exact_generation = true;
};

[[nodiscard]] ExternalPayloadProjection compose_external_payload_projection(
    const FrontierCandidate &candidate,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay,
    const ContextualValueTransferIndex &value_transfers,
    const std::vector<PayloadProjectionTargetRequest> &targets,
    const PayloadProjectionOptions &options = {});

[[nodiscard]] std::vector<std::string>
validate_external_payload_projection(
    const ExternalPayloadProjection &projection,
    const FrontierCandidate &candidate,
    const ContextualInfluenceGraph &graph,
    const ModelFactOverlay &overlay,
    const ContextualValueTransferIndex &value_transfers,
    const std::vector<PayloadProjectionTargetRequest> &targets,
    const PayloadProjectionOptions &options = {});

[[nodiscard]] const char *to_string(PayloadProjectionStatus value);
[[nodiscard]] const char *to_string(PayloadApplicationKind value);

}  // namespace rift::core

#endif
