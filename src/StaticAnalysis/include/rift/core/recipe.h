#ifndef RIFT_CORE_RECIPE_H
#define RIFT_CORE_RECIPE_H

#include "rift/core/artifacts.h"
#include "rift/core/frontier.h"
#include "rift/core/model.h"
#include "rift/core/payload_projection.h"
#include "rift/core/predicate_occurrence.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

enum class RecipeStatus {
    Supported,
    Heuristic,
    Unknown,
};

enum class MutationKind {
    BoundarySet,
    BooleanToggle,
    EnumAlternative,
    BitmaskBoundary,
    ThresholdCrossing,
    Presence,
    Absence,
    Count,
    Drop,
    Repeat,
    Reorder,
    Timeout,
    Deadline,
    Unknown,
};

enum class MutationDirection {
    MonotoneUp,
    MonotoneDown,
    BoundarySet,
    Toggle,
    Unknown,
};

enum class MutationValuePurpose {
    TypeMin,
    BelowBoundary,
    AtBoundary,
    AboveBoundary,
    TypeMax,
    FalseValue,
    TrueValue,
    MaskCleared,
    MaskSet,
    SatLeft,
    SatRight,
    EnumAlternative,
};

enum class SolverOutcome {
    Sat,
    Unsat,
    Unknown,
    Timeout,
    Unsupported,
    NotRun,
};

enum class FlipClass {
    LocalSummarySatPair,
    SamePathFlip,
    CrossPathFlip,
    Unknown,
};

enum class JointActionClaim {
    SingleAction,
    JointRequired,
    JointUnknown,
};

enum class PrerequisiteStatus {
    Complete,
    PartialOrderUnknown,
};

enum class TimingStatus {
    Exact,
    WidenedUnknown,
    Unknown,
};

enum class TimingEndpoint {
    Open,
    Closed,
    Mixed,
    Unknown,
};

enum class TimingMutationAction {
    Delay,
    Pause,
    Drop,
    Repeat,
    Reorder,
    ChangeInterval,
};

enum class ReplayStatus {
    Ready,
    Partial,
    Unknown,
};

enum class ReplayExpectedRelation {
    ApTruthChange,
    MonitorSuccessorChange,
    Unknown,
};

struct MutationValue {
    std::string canonical;
    ValueType value_type;
    MutationValuePurpose purpose = MutationValuePurpose::AtBoundary;
};

struct ActionMutation {
    std::string action_id;
    MutationKind mutation_kind = MutationKind::Unknown;
    MutationDirection direction = MutationDirection::Unknown;
    std::vector<MutationValue> suggested_values;
    std::vector<std::string> unknown_reasons;
};

// A hyperedge is always indivisible.  Consumers must never turn a
// JointRequired/JointUnknown edge into independent truth-flip claims.
struct ActionHyperedge {
    std::string hyperedge_id;
    std::vector<std::string> action_ids;
    bool indivisible = true;
    JointActionClaim claim = JointActionClaim::SingleAction;
};

struct SolverQueryEvidence {
    std::string query_id;
    std::string query_sha256;
    std::string encoding_version = "rift-local-truth-change/1.0.0";
    std::string solver = "Z3";
    std::string solver_version;
    std::uint64_t timeout_ms = 0;
    SolverOutcome outcome = SolverOutcome::NotRun;
    FlipClass flip_class = FlipClass::Unknown;
    std::vector<std::string> assumption_literals;
    std::vector<std::string> model;
    std::vector<std::string> unsat_core;
    std::optional<std::string> unknown_reason;
};

struct PrerequisiteStep {
    std::string step_id;
    std::string action_id;
    std::string operation;
    std::vector<std::string> predecessor_step_ids;
};

struct PrerequisiteDag {
    std::string dag_id;
    PrerequisiteStatus status = PrerequisiteStatus::PartialOrderUnknown;
    std::vector<PrerequisiteStep> steps;
    std::vector<std::string> uncertainty_reasons;
};

// alternatives are OR; steps inside each DAG are a partial-order conjunction.
struct PrerequisiteChoice {
    std::string choice_id;
    std::vector<PrerequisiteDag> alternatives;
};

struct TimingContract {
    TimingStatus status = TimingStatus::Unknown;
    std::optional<std::string> clock_source;
    std::optional<std::string> unit;
    std::optional<std::string> epoch;
    std::optional<double> quantum;
    std::optional<double> jitter;
    std::optional<std::string> wrap;
    std::optional<TimingEndpoint> comparison_endpoint;
    std::optional<std::string> start_event;
    std::optional<std::string> end_event;
    std::optional<std::string> scope_schema;
    std::optional<std::string> generation_schema;
    std::optional<double> lower;
    std::optional<double> upper;
    std::optional<bool> lower_closed;
    std::optional<bool> upper_closed;
    std::vector<TimingMutationAction> mutation_actions;
    std::vector<std::string> uncertainty_reasons;
};

struct MutationRecipe {
    std::string recipe_id;
    std::string frontier_candidate_id;
    std::string cone_id;
    std::string ap_id;
    std::optional<std::string> target_predicate_selector_id;
    std::optional<ExternalPayloadProjection> payload_projection;
    RecipeStatus status = RecipeStatus::Unknown;
    ActionHyperedge action_hyperedge;
    std::vector<ActionMutation> action_mutations;
    std::vector<PrerequisiteChoice> prerequisite_choices;
    TimingContract timing;
    SolverQueryEvidence solver_query;
    std::optional<SolverQueryEvidence> direction_query;
    FrontierEvidenceAxes evidence;
    std::vector<std::string> uncertainty_reasons;
};

struct SolverContract {
    std::string solver = "Z3";
    std::string solver_version;
    std::string encoding_version = "rift-local-truth-change/1.0.0";
    std::uint64_t timeout_ms = 0;
    std::uint64_t max_queries = 0;
};

struct MutationRecipes {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string property_ir_sha256;
    std::string ap_bindings_sha256;
    std::string graph_sha256;
    std::string cones_sha256;
    std::string frontier_candidates_sha256;
    std::string model_fact_overlay_sha256;
    std::string predicate_occurrence_bindings_sha256;
    std::string analyzer_core_sha256;
    SolverContract solver_contract;
    bool candidate_accounting_complete = true;
    bool total_semantics = true;
    StageStatus status = StageStatus::Failed;
    std::vector<MutationRecipe> recipes;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

// Explicit joint summaries are a closed typed input to the recipe stage.
// The production implementation can additionally derive a requirement from
// a source-visible Boolean conjunction when occurrence, value-path, scope,
// generation, and SMT evidence close the complete n-ary group.  It never
// derives conjunction from names.  Every supplied fact ID must resolve in the
// certificate-bound model overlay.
struct JointActionRequirement {
    std::string requirement_id;
    std::vector<std::string> frontier_candidate_ids;
    std::vector<std::string> action_ids;
    std::vector<std::string> model_fact_ids;
    bool complete = false;
};

struct RecipeOptions {
    std::uint64_t solver_timeout_ms = 100;
    std::uint64_t max_solver_queries = 10000;
    std::string analyzer_core_sha256;
    std::vector<JointActionRequirement> joint_action_requirements;
};

struct RecipeInputDigests {
    std::string property_ir_sha256;
    std::string ap_bindings_sha256;
    std::string graph_sha256;
    std::string cones_sha256;
    std::string frontier_candidates_sha256;
    std::string model_fact_overlay_sha256;
    std::string predicate_occurrence_bindings_sha256;
};

struct RecipeReplayObligation {
    std::string obligation_id;
    std::string recipe_id;
    std::string frontier_candidate_id;
    ReplayStatus status = ReplayStatus::Unknown;
    std::vector<std::string> atomic_action_ids;
    bool indivisible_hyperedge = true;
    std::vector<std::string> ordered_step_ids;
    std::vector<std::string> required_observations;
    ReplayExpectedRelation expected_relation = ReplayExpectedRelation::Unknown;
    std::string solver_query_sha256;
    std::optional<std::string> scope_schema;
    std::optional<std::string> generation_schema;
    TimingStatus timing_status = TimingStatus::Unknown;
    std::vector<std::string> uncertainty_reasons;
};

struct RecipeReplayObligations {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string mutation_recipes_sha256;
    bool candidate_accounting_complete = true;
    std::vector<RecipeReplayObligation> obligations;
};

[[nodiscard]] MutationRecipes build_mutation_recipes(
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const RecipeInputDigests &input_digests,
    const RecipeOptions &options = {});

// Typed-transfer-aware production overload.  The legacy overload above is
// retained only as a fail-closed compatibility path and cannot issue a
// SUPPORTED external-payload direction without this sidecar.
[[nodiscard]] MutationRecipes build_mutation_recipes(
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const ContextualValueTransferIndex &value_transfers,
    const RecipeInputDigests &input_digests,
    const RecipeOptions &options = {});

[[nodiscard]] RecipeReplayObligations build_recipe_replay_obligations(
    const MutationRecipes &recipes,
    const std::string &mutation_recipes_sha256);

[[nodiscard]] std::vector<std::string> validate_mutation_recipes(
    const MutationRecipes &recipes,
    const TypedPropertyIr &property,
    const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierCandidates &frontier,
    const ModelFactOverlay &overlay,
    const PredicateOccurrenceBindings &predicate_occurrences,
    const RecipeInputDigests &expected_digests,
    const RecipeOptions &options = {});

[[nodiscard]] std::vector<std::string> validate_mutation_recipes(
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
    const RecipeOptions &options = {});

[[nodiscard]] std::vector<std::string> validate_recipe_replay_obligations(
    const RecipeReplayObligations &obligations,
    const MutationRecipes &recipes,
    const std::string &expected_mutation_recipes_sha256);

[[nodiscard]] std::string canonical_mutation_recipes_json(
    const MutationRecipes &recipes);
[[nodiscard]] std::string canonical_recipe_replay_obligations_json(
    const RecipeReplayObligations &obligations);

[[nodiscard]] const char *to_string(RecipeStatus value);
[[nodiscard]] const char *to_string(MutationKind value);
[[nodiscard]] const char *to_string(MutationDirection value);
[[nodiscard]] const char *to_string(MutationValuePurpose value);
[[nodiscard]] const char *to_string(SolverOutcome value);
[[nodiscard]] const char *to_string(FlipClass value);
[[nodiscard]] const char *to_string(JointActionClaim value);
[[nodiscard]] const char *to_string(PrerequisiteStatus value);
[[nodiscard]] const char *to_string(TimingStatus value);
[[nodiscard]] const char *to_string(TimingEndpoint value);
[[nodiscard]] const char *to_string(TimingMutationAction value);
[[nodiscard]] const char *to_string(ReplayStatus value);
[[nodiscard]] const char *to_string(ReplayExpectedRelation value);

}  // namespace rift::core

#endif
