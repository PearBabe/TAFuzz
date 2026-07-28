#ifndef RIFT_CORE_MODEL_H
#define RIFT_CORE_MODEL_H

#include "rift/core/artifacts.h"

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

// model-pack/1.0.0 remains a non-executable M4 input contract.  These types
// and APIs intentionally describe only the incompatible, finite 2.0.0 VM.
enum class ModelLayer {
    Platform,
    Framework,
    ProjectAdapter,
};

enum class ModelSelectorKind {
    ExactQualifiedSignature,
    ExactUsr,
    TypedField,
};

enum class ModelProjectionKind {
    MatchedNode,
    FormalParameter,
    CallArgument,
    CallResult,
    Receiver,
};

enum class ModelJoinKind {
    SameObject,
    SameScope,
    SameGeneration,
    SameHandle,
    SameCallsite,
    SameTask,
};

enum class ModelFactKind {
    ExternalBoundary,
    SemanticTransfer,
    EventLink,
    TimerTransition,
    QueueTransition,
    LifecycleTransition,
    ScopeKey,
    ClockRelation,
    PersistenceTransition,
    // A typed n-ary executor/action composition constraint.  It is emitted
    // into ModelFactOverlay::joint_action_constraints rather than the CIG
    // value/event arc ledger, so an AND requirement can never create a
    // spurious data-flow edge.
    JointActionRelation,
};

enum class ModelClockUnit {
    Nanoseconds,
    Microseconds,
    Milliseconds,
    Seconds,
    Ticks,
};

enum class ModelClockWrap {
    None,
    Modulo,
    Saturating,
    Unknown,
};

enum class ModelClockEndpoint {
    Open,
    Closed,
    Mixed,
    Unknown,
};

enum class ModelJointActionOperator {
    AllRequired,
    AnySufficient,
    Unknown,
};

enum class ModelValueTransferKind {
    Identity,
    Affine,
    ParseIdentityWithPrecondition,
    Unknown,
};

enum class ModelValuePrecondition {
    None,
    CanonicalDecimalIntegerInRange,
    Unknown,
};

struct ModelResourceLimits {
    std::uint64_t max_selector_matches = 100000;
    std::uint64_t max_capture_values = 100000;
    std::uint64_t max_join_assignments = 100000;
    std::uint64_t max_emitted_facts = 100000;
};

struct ModelTargetContract {
    std::string target_version;
    std::string target_abi;
    std::string evidence_id;
    std::string digest_policy;
};

struct ModelSelectorV2 {
    std::string selector_id;
    ModelSelectorKind kind = ModelSelectorKind::ExactQualifiedSignature;
    // exact qualified signature / USR.  Typed-field selectors instead use
    // owner_selector_ref + field_path and may constrain canonical_type.
    std::optional<std::string> exact_value;
    std::optional<std::string> owner_selector_ref;
    std::vector<std::string> field_path;
    std::optional<std::string> canonical_type;
    // Only project_adapter packs may mark and consume application-private APIs.
    bool application_private = false;
};

struct ModelMatchV2 {
    std::string match_id;
    std::string selector_ref;
};

struct ModelCaptureV2 {
    std::string capture_id;
    std::string match_ref;
    ModelProjectionKind projection = ModelProjectionKind::MatchedNode;
    std::optional<std::uint32_t> index;
};

struct ModelJoinV2 {
    std::string join_id;
    ModelJoinKind kind = ModelJoinKind::SameObject;
    std::string left_capture_ref;
    std::string right_capture_ref;
};

// This is a schema for an external executor action, not a CIG/SemanticIndex
// node.  Runtime controllability is deliberately absent: it is established by
// a separate executor-capability manifest.
struct ExternalActionTemplateV2 {
    std::string action_schema_id;
    std::string action_class;
    std::string channel;
    std::string operation;
    ValueType payload_type;
    std::string payload_slot;
    std::string scope_schema;
    std::string generation_schema;
    std::string timing_capability;
    std::string required_capability;
};

// Optional members permit in-memory total-UNKNOWN artifacts and make missing
// evidence machine-checkable.  The closed model-pack JSON schema requires
// every member for a clock_relation emit.
struct ModelClockRelationV2 {
    std::optional<std::string> clock_source;
    std::optional<ModelClockUnit> unit;
    std::optional<std::string> epoch;
    std::optional<double> quantum;
    std::optional<double> jitter;
    std::optional<ModelClockWrap> wrap;
    std::optional<std::uint64_t> wrap_value;
    std::optional<std::string> start_event;
    std::optional<std::string> end_event;
    std::optional<ModelClockEndpoint> endpoint;
    std::optional<std::string> scope_schema;
    std::optional<std::string> generation_schema;
};

struct ModelJointActionRelationV2 {
    std::string group_schema_id;
    ModelJointActionOperator combination =
        ModelJointActionOperator::Unknown;
    bool participant_set_complete = false;
    std::vector<std::string> participant_capture_refs;
    std::string scope_schema;
    std::string generation_schema;
};

// A finite semantic summary, never an interpreted transfer_relation string.
// PARSE_IDENTITY_WITH_PRECONDITION is identity only in the typed external
// action coordinate when the executor itself constructs the canonical decimal
// representation and the failure branch remains explicitly UNKNOWN.
struct ModelValueTransferV2 {
    ModelValueTransferKind kind = ModelValueTransferKind::Unknown;
    std::optional<std::int64_t> affine_scale;
    std::optional<std::int64_t> affine_offset;
    ModelValuePrecondition precondition = ModelValuePrecondition::Unknown;
    bool executor_enforces_precondition = false;
    bool failure_branch_unknown = true;
};

struct ModelEmitV2 {
    std::string emit_id;
    ModelFactKind fact_kind = ModelFactKind::SemanticTransfer;
    std::string source_capture_ref;
    std::optional<std::string> target_capture_ref;
    Certainty certainty = Certainty::Unknown;
    std::string transfer_relation;
    std::optional<ExternalActionTemplateV2> external_action;
    std::optional<ModelClockRelationV2> clock_relation = std::nullopt;
    std::optional<ModelJointActionRelationV2> joint_action_relation =
        std::nullopt;
    std::optional<ModelValueTransferV2> value_transfer = std::nullopt;
};

struct ModelRuleV2 {
    std::string rule_id;
    std::vector<ModelMatchV2> matches;
    std::vector<ModelCaptureV2> captures;
    std::vector<ModelJoinV2> joins;
    std::vector<ModelEmitV2> emits;
    std::string evidence_note;
};

struct ModelPackV2 {
    std::string schema_version = "2.0.0";
    std::string model_pack_id;
    std::string model_pack_version;
    ModelLayer layer = ModelLayer::Framework;
    bool property_independent = true;
    ModelTargetContract target;
    ModelResourceLimits resource_limits;
    std::vector<ModelSelectorV2> selectors;
    std::vector<ModelRuleV2> rules;
    // Digest of the exact loaded bytes, supplied by the loader rather than by
    // the pack itself (self-hashes are not stable contracts).
    std::string observed_sha256;
};

struct ModelProvenance {
    std::string model_pack_id;
    std::string model_pack_version;
    // Canonical semantic pack digest (array order independent). The loader's
    // observed_sha256 separately binds exact input bytes for the certificate.
    std::string model_pack_sha256;
    ModelLayer layer = ModelLayer::Framework;
    std::string rule_id;
    std::string emit_id;
    std::vector<std::string> selector_ids;
    std::vector<std::string> capture_ids;
    std::vector<std::string> matched_semantic_node_ids;
};

struct ExternalAction {
    std::string external_action_id;
    std::string action_schema_id;
    std::string action_class;
    std::string channel;
    std::string operation;
    ValueType payload_type;
    std::string payload_slot;
    std::string scope_schema;
    std::string generation_schema;
    std::string timing_capability;
    std::string required_capability;
    std::vector<ModelProvenance> provenance;
};

struct BoundaryAttachment {
    std::string attachment_id;
    std::string external_action_id;
    std::string semantic_node_id;
    std::string transfer_relation;
    Certainty certainty = Certainty::Unknown;
    std::vector<ModelProvenance> provenance;
    std::optional<ModelValueTransferV2> value_transfer = std::nullopt;
};

struct ModelFact {
    std::string fact_id;
    ModelFactKind kind = ModelFactKind::SemanticTransfer;
    std::string source_semantic_node_id;
    std::optional<std::string> target_semantic_node_id;
    std::string transfer_relation;
    Certainty certainty = Certainty::Unknown;
    std::vector<ModelProvenance> provenance;
    std::optional<ModelClockRelationV2> clock_relation = std::nullopt;
    std::optional<ModelValueTransferV2> value_transfer = std::nullopt;
};

struct ModelJointActionConstraint {
    std::string constraint_id;
    // Stable per matched assignment, not just per schema.  This prevents two
    // sessions/objects described by the same pack rule from being merged.
    std::string group_instance_id;
    std::string group_schema_id;
    ModelJointActionOperator combination =
        ModelJointActionOperator::Unknown;
    bool participant_set_complete = false;
    std::vector<std::string> participant_semantic_node_ids;
    std::string scope_schema;
    std::string generation_schema;
    Certainty certainty = Certainty::Unknown;
    std::vector<ModelProvenance> provenance;
};

struct ModelVmUnknown {
    std::string unknown_id;
    std::string model_pack_id;
    std::optional<std::string> rule_id;
    std::string operation;
    std::string reason;
    std::vector<std::string> affected_emit_ids;
};

struct ModelResourceLedgerEntry {
    std::string ledger_id;
    std::string model_pack_id;
    std::optional<std::string> rule_id;
    std::string operation;
    std::uint64_t limit = 0;
    std::uint64_t observed = 0;
    bool complete = false;
    Certainty certainty = Certainty::Unknown;
};

struct ModelFactOverlay {
    std::string artifact_id;
    std::string semantic_index_artifact_id;
    std::string semantic_index_identity;
    StageStatus status = StageStatus::Failed;
    // Canonical semantic pack digests. Exact loaded-byte digests stay in each
    // ModelPackV2::observed_sha256 and must be bound by the analysis certificate.
    std::vector<std::string> model_pack_sha256s;
    std::vector<ExternalAction> external_actions;
    std::vector<BoundaryAttachment> boundary_attachments;
    std::vector<ModelFact> semantic_facts;
    std::vector<ModelJointActionConstraint> joint_action_constraints;
    std::vector<ModelVmUnknown> unknown_outcomes;
    std::vector<ModelResourceLedgerEntry> resource_ledger;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] LoadResult<ModelPackV2> load_model_pack_v2(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256 = std::nullopt);

[[nodiscard]] std::vector<std::string> validate_model_pack_v2(
    const ModelPackV2 &pack);

[[nodiscard]] std::string canonical_model_pack_semantic_sha256(
    const ModelPackV2 &pack);

// The finite VM accepts SemanticIndex only.  A Property IR cannot be passed to
// this API by construction, enforcing pack-before-property execution.
[[nodiscard]] LoadResult<ModelFactOverlay> execute_model_pack_v2(
    const ModelPackV2 &pack, const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256);

// Repeated --model-pack execution uses this deterministic union.  Inputs are
// canonicalized by digest/ID; duplicate facts are unioned and conflicting
// certainty can only be downgraded to UNKNOWN, never upgraded.
[[nodiscard]] LoadResult<ModelFactOverlay> execute_model_packs_v2(
    const std::vector<ModelPackV2> &packs,
    const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256);

[[nodiscard]] std::vector<std::string> validate_model_fact_overlay(
    const ModelFactOverlay &overlay, const SemanticIndex &semantic_index,
    const std::optional<std::string> &expected_semantic_index_sha256 =
        std::nullopt);

[[nodiscard]] std::string canonical_model_fact_overlay_json(
    const ModelFactOverlay &overlay);

[[nodiscard]] const char *to_string(ModelLayer value);
[[nodiscard]] const char *to_string(ModelFactKind value);
[[nodiscard]] const char *to_string(ModelClockUnit value);
[[nodiscard]] const char *to_string(ModelClockWrap value);
[[nodiscard]] const char *to_string(ModelClockEndpoint value);
[[nodiscard]] const char *to_string(ModelJointActionOperator value);
[[nodiscard]] const char *to_string(ModelValueTransferKind value);
[[nodiscard]] const char *to_string(ModelValuePrecondition value);

}  // namespace rift::core

#endif
