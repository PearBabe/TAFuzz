#ifndef RIFT_CORE_FRONTIER_H
#define RIFT_CORE_FRONTIER_H

#include "rift/core/influence.h"
#include "rift/core/model.h"

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

// These axes deliberately remain independent.  In particular, an executor
// capability or a SAT result must never upgrade static reachability.
enum class ReachabilityVerdict {
    StaticWitness,
    ModelledWitness,
    Unknown,
    NoStaticWitness,
};

enum class ControllabilityVerdict {
    Direct,
    Sequence,
    Timing,
    Environment,
    Unavailable,
    Unknown,
};

enum class PathFeasibilityVerdict {
    Sat,
    Unsat,
    Unknown,
    NotEvaluated,
};

enum class MutationSemanticsVerdict {
    Supported,
    Heuristic,
    Unknown,
    NotEvaluated,
};

enum class RuntimeEvidenceVerdict {
    Confirmed,
    Refuted,
    Unknown,
    NotEvaluated,
};

enum class WitnessCompatibility {
    Compatible,
    Unknown,
    Incompatible,
};

struct ContextCompatibilityResult {
    WitnessCompatibility verdict = WitnessCompatibility::Compatible;
    std::vector<std::string> reasons;
};

enum class FrontierDisposition {
    Actionable,
    Pending,
    Rejected,
};

enum class AttachmentDisposition {
    Witnessed,
    Unknown,
    NoMeet,
    Unresolved,
};

enum class FrontierPathClass {
    Static,
    Modelled,
    Unknown,
};

enum class FrontierPathStepKind {
    GraphEdge,
    ModelArc,
};

struct ExecutorCapabilityEntry {
    std::string capability_id;
    std::string required_capability;
    // Empty means that the capability applies to all action schemas.
    std::optional<std::string> action_schema_id;
    ControllabilityVerdict controllability =
        ControllabilityVerdict::Unknown;
    std::string evidence_note;
};

struct ExecutorCapabilityManifest {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string executor_id;
    std::string executor_version;
    StageStatus status = StageStatus::Failed;
    std::vector<ExecutorCapabilityEntry> capabilities;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct FrontierOptions {
    // Limits are core resource guards, not top-k pruning.  Reaching either
    // limit leaves the candidate in the ledger and marks it UNKNOWN.
    std::uint64_t max_materialized_model_edges = 1000000;
    std::uint64_t max_forward_states_per_attachment = 1000000;
};

enum class FrontierValidationMode {
    // Validate the materialized artifact's cheap structural invariants.  This
    // is the appropriate mode immediately after construction: recomputing the
    // same whole-program fixed point in the producer does not add independent
    // evidence and doubles the dominant cost on large programs.
    Structural,
    // Independently rerun the deterministic core and compare canonical bytes.
    // Unit tests and offline verification may request this explicitly; the
    // detached M5 verifier remains the certificate-grade trust boundary.
    DeterministicRecompute,
};

struct FrontierInputDigests {
    std::string model_fact_overlay_sha256;
    std::string graph_sha256;
    std::string cones_sha256;
    std::optional<std::string> executor_manifest_sha256;
};

struct FrontierCompletenessLedger {
    bool model_vm_complete = false;
    bool attachment_enumeration_complete = false;
    bool forward_enumeration_complete = false;
    bool cone_complete = false;
    bool compatibility_complete = false;
    std::vector<std::string> gap_reasons;
};

struct FrontierModelProvenance {
    std::vector<std::string> model_pack_sha256s;
    std::vector<std::string> attachment_ids;
    std::vector<std::string> model_fact_ids;
};

struct FrontierEvidenceAxes {
    ReachabilityVerdict reachability = ReachabilityVerdict::Unknown;
    ControllabilityVerdict controllability =
        ControllabilityVerdict::Unknown;
    PathFeasibilityVerdict path_feasibility =
        PathFeasibilityVerdict::NotEvaluated;
    MutationSemanticsVerdict mutation_semantics =
        MutationSemanticsVerdict::NotEvaluated;
    RuntimeEvidenceVerdict runtime_evidence =
        RuntimeEvidenceVerdict::NotEvaluated;
    FrontierModelProvenance model_provenance;
    FrontierCompletenessLedger completeness;
};

struct FrontierMeetSummary {
    // Counts are over the complete fixed-point intersection.  Path-class
    // counts are not mutually exclusive because one meet may retain both a
    // proved and an UNKNOWN alternate path.
    std::uint64_t meet_count = 0;
    std::uint64_t static_path_meet_count = 0;
    std::uint64_t modelled_path_meet_count = 0;
    std::uint64_t unknown_path_meet_count = 0;
    // Exact partition indexed by the effective path mask (1..7).  Index 0 is
    // always zero and is omitted from JSON.  This makes overlap accounting
    // independently checkable rather than inferring it from three marginals.
    std::array<std::uint64_t, 8> effective_mask_histogram{};
    bool enumeration_complete = false;
    // SHA-256 of the canonical, node-id-sorted meet ledger.  The ledger is
    // reconstructible from the certificate-bound graph, cone and attachment;
    // it is intentionally not expanded once per meet in this sidecar.
    std::string ledger_sha256;
};

struct FrontierForwardSummary {
    std::uint64_t reached_node_count = 0;
    std::uint64_t reachable_transition_count = 0;
    bool enumeration_complete = false;
    std::string reached_state_ledger_sha256;
    std::string reachable_transition_ledger_sha256;
};

struct FrontierSupportSummary {
    std::uint64_t supporting_transition_count = 0;
    std::uint64_t supporting_model_fact_count = 0;
    bool enumeration_complete = false;
    std::string supporting_transition_ledger_sha256;
    std::string supporting_model_fact_ledger_sha256;
};

struct FrontierPathStep {
    FrontierPathStepKind kind = FrontierPathStepKind::GraphEdge;
    std::string source_node_id;
    std::string target_node_id;
    std::optional<std::string> graph_edge_id;
    std::optional<std::string> model_fact_id;
};

struct FrontierPathExemplar {
    // At most one deterministic path is retained for each path class.  These
    // paths are evidence exemplars, never a claim that alternate paths were
    // pruned from the complete meet summary above.
    std::string meet_node_id;
    FrontierPathClass effective_path_class = FrontierPathClass::Unknown;
    FrontierPathClass raw_forward_path_class = FrontierPathClass::Unknown;
    FrontierPathClass raw_root_path_class = FrontierPathClass::Unknown;
    WitnessCompatibility compatibility = WitnessCompatibility::Unknown;
    ReachabilityVerdict reachability = ReachabilityVerdict::Unknown;
    std::vector<FrontierPathStep> forward_steps;
    std::vector<FrontierPathStep> root_steps;
    std::string root_node_id;
    std::vector<std::string> uncertainty_reasons;
};

struct FrontierWitness {
    std::string witness_id;
    std::string attachment_id;
    std::string boundary_node_id;
    FrontierForwardSummary forward_summary;
    FrontierSupportSummary support_summary;
    FrontierMeetSummary meet_summary;
    std::vector<FrontierPathExemplar> path_exemplars;
    WitnessCompatibility compatibility = WitnessCompatibility::Unknown;
    ReachabilityVerdict reachability = ReachabilityVerdict::Unknown;
    // Complete model provenance remains explicit.  Per-meet graph paths are
    // represented by the reconstructible digest and bounded exemplars.
    std::vector<std::string> model_fact_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct FrontierTraversalContract {
    std::string algorithm = "ordinal-path-class-fixed-point";
    std::string algorithm_version = "3.0.0";
    std::string node_order = "node-id-utf8-lexicographic";
    std::string edge_order =
        "arc-kind-id-source-target-utf8-lexicographic";
    std::string path_class_encoding =
        "STATIC=1,MODELLED=2,UNKNOWN=4";
    std::string meet_ledger = "rift-meet-ledger/lp-u64le/1.0.0";
    std::string reach_ledger = "rift-reach-ledger/lp-u64le/1.0.0";
    std::string transition_ledger =
        "rift-transition-ledger/lp-u64le/1.0.0";
    std::string compatibility = "rift-context-compatibility/1.0.0";
    std::string model_arc_policy = "semantic-context-expansion/1.0.0";
    std::string exemplar_policy =
        "one-per-effective-class/lexicographic-first";
    std::uint32_t maximum_path_exemplars = 3;
    std::uint64_t max_materialized_model_edges = 1000000;
    std::uint64_t max_forward_states_per_attachment = 1000000;
};

struct FrontierAttachmentAccount {
    std::string attachment_id;
    std::string semantic_node_id;
    AttachmentDisposition disposition = AttachmentDisposition::Unresolved;
    std::vector<std::string> contextual_node_ids;
    std::vector<std::string> witness_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct FrontierCandidate {
    std::string candidate_id;
    // Copy the complete action contract into the sidecar.  Consumers must not
    // conflate actions that happen to attach to the same contextual node.
    ExternalAction action;
    std::string cone_id;
    std::string ap_id;
    FrontierDisposition disposition = FrontierDisposition::Pending;
    FrontierEvidenceAxes evidence;
    std::vector<FrontierAttachmentAccount> attachment_accounting;
    std::vector<FrontierWitness> witnesses;
    std::uint32_t rank_tier = 0;
    std::vector<std::string> rank_reasons;
    std::vector<std::string> uncertainty_reasons;
};

struct FrontierCandidates {
    std::string schema_version = "3.0.0";
    std::string artifact_id;
    FrontierInputDigests input_digests;
    FrontierTraversalContract traversal_contract;
    std::string traversal_contract_sha256;
    bool candidate_accounting_complete = true;
    bool ranking_never_prunes = true;
    StageStatus status = StageStatus::Failed;
    std::vector<FrontierCandidate> candidates;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct FuzzableAction {
    std::string candidate_id;
    ExternalAction action;
    std::string cone_id;
    std::string ap_id;
    FrontierEvidenceAxes evidence;
    std::vector<std::string> witness_ids;
    std::uint32_t rank_tier = 0;
    std::vector<std::string> rank_reasons;
};

struct FuzzableFrontier {
    std::string schema_version = "2.0.0";
    std::string artifact_id;
    std::string frontier_candidates_sha256;
    bool actionable_projection_only = true;
    bool ranking_never_prunes = true;
    StageStatus status = StageStatus::Failed;
    std::vector<FuzzableAction> actions;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] FrontierCandidates compute_frontier_candidates(
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierInputDigests &input_digests,
    const std::optional<ExecutorCapabilityManifest> &executor_manifest =
        std::nullopt,
    const FrontierOptions &options = {});

[[nodiscard]] FuzzableFrontier project_fuzzable_frontier(
    const FrontierCandidates &candidates,
    const std::string &frontier_candidates_sha256);

[[nodiscard]] std::vector<std::string> validate_frontier_candidates(
    const FrontierCandidates &candidates,
    const ModelFactOverlay &overlay,
    const ContextualInfluenceGraph &graph,
    const ApInfluenceCones &cones,
    const FrontierInputDigests &expected_digests,
    const std::optional<ExecutorCapabilityManifest> &executor_manifest =
        std::nullopt,
    const FrontierOptions &options = {},
    FrontierValidationMode mode =
        FrontierValidationMode::DeterministicRecompute);

[[nodiscard]] std::vector<std::string> validate_fuzzable_frontier(
    const FuzzableFrontier &frontier,
    const FrontierCandidates &candidates,
    const std::string &expected_frontier_candidates_sha256);

[[nodiscard]] std::string canonical_frontier_candidates_json(
    const FrontierCandidates &candidates);
[[nodiscard]] std::string canonical_fuzzable_frontier_json(
    const FuzzableFrontier &frontier);

[[nodiscard]] ContextCompatibilityResult evaluate_contextual_compatibility(
    const ContextualNode &source, const ContextualNode &target,
    RelationKind relation_kind);

[[nodiscard]] const char *to_string(ReachabilityVerdict value);
[[nodiscard]] const char *to_string(ControllabilityVerdict value);
[[nodiscard]] const char *to_string(PathFeasibilityVerdict value);
[[nodiscard]] const char *to_string(MutationSemanticsVerdict value);
[[nodiscard]] const char *to_string(RuntimeEvidenceVerdict value);
[[nodiscard]] const char *to_string(WitnessCompatibility value);
[[nodiscard]] const char *to_string(FrontierDisposition value);
[[nodiscard]] const char *to_string(AttachmentDisposition value);
[[nodiscard]] const char *to_string(FrontierPathClass value);
[[nodiscard]] const char *to_string(FrontierPathStepKind value);

}  // namespace rift::core

#endif
