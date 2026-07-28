#ifndef RIFT_CORE_INFLUENCE_H
#define RIFT_CORE_INFLUENCE_H

#include "rift/core/artifacts.h"
#include "rift/core/types.h"
#include "rift/core/value_transfer.h"

#include <optional>
#include <string>
#include <vector>

namespace rift::core {

enum class BindingResolution {
    Confirmed,
    Partial,
    Ambiguous,
    Unresolved,
    Failed,
};

enum class CandidateStatus {
    Candidate,
    Confirmed,
    Rejected,
    Unresolved,
};

struct BindingEvidence {
    std::string evidence_id;
    std::string kind;
    Certainty certainty = Certainty::Unknown;
    std::string fact;
    std::string producer = "rift-core";
    std::optional<SourceLocation> location;
    std::optional<double> score;
};

struct BindingCandidate {
    std::string binding_id;
    CandidateStatus status = CandidateStatus::Unresolved;
    std::optional<std::string> selector_group_id;
    std::vector<std::string> selector_ids;
    std::vector<std::string> semantic_node_ids;
    std::vector<BindingEvidence> evidence;
    double confidence = 0.0;
    std::vector<std::string> uncertainty_reasons;
};

struct ApRoleBinding {
    std::string ap_id;
    ApRole role = ApRole::State;
    BindingResolution resolution = BindingResolution::Unresolved;
    std::vector<BindingCandidate> candidates;
};

struct ApBindings {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string property_ir_sha256;
    std::string semantic_index_sha256;
    StageStatus status = StageStatus::Failed;
    std::vector<ApRoleBinding> bindings;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct BindingOptions {
    // M4 keeps every role-local candidate but does not yet prove cross-role
    // object/scope/generation consistency.  Asking for that stronger contract
    // therefore fails closed instead of silently claiming it was evaluated.
    bool evaluate_cross_role_consistency = false;
    bool similarity_can_confirm = false;
};

struct InfluenceOptions {
    std::uint32_t call_string_limit = 1;
    std::uint32_t recursion_expansion_limit = 2;
    bool field_sensitive = true;
    bool object_sensitive = true;
};

struct ContextualizationArtifacts {
    ContextualInfluenceGraph graph;
    ContextualValueTransferIndex value_transfers;
};

enum class ConeMembership {
    MustInfluence,
    MayInfluence,
    ModelledInfluence,
    UnknownInfluence,
};

enum class CandidateDisposition {
    Included,
    Unreachable,
    Unresolved,
    Rejected,
};

struct CandidateAccount {
    std::string binding_id;
    CandidateDisposition disposition = CandidateDisposition::Unresolved;
    std::vector<std::string> root_node_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct ConeMember {
    std::string node_id;
    ConeMembership membership = ConeMembership::UnknownInfluence;
    std::vector<std::string> witness_edge_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct ApInfluenceCone {
    std::string cone_id;
    std::string ap_id;
    std::vector<ApRole> roles;
    std::vector<CandidateAccount> candidate_accounting;
    std::vector<ConeMember> members;
    std::vector<std::string> edge_ids;
    StageStatus status = StageStatus::Failed;
    std::vector<std::string> uncertainty_reasons;
};

struct ApInfluenceCones {
    std::string artifact_id;
    std::string ap_bindings_sha256;
    std::string graph_sha256;
    bool candidate_accounting_complete = true;
    bool ranking_never_prunes = true;
    StageStatus status = StageStatus::Failed;
    std::vector<ApInfluenceCone> cones;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] ApBindings bind_atomic_propositions(
    const TypedPropertyIr &property, const SemanticIndex &index,
    const std::string &semantic_index_sha256,
    const BindingOptions &options = {});

[[nodiscard]] std::vector<std::string> validate_ap_bindings(
    const ApBindings &bindings, const TypedPropertyIr &property,
    const SemanticIndex &index, const ArtifactDigests &expected_digests);

[[nodiscard]] ContextualInfluenceGraph build_contextual_influence_graph(
    const SemanticIndex &index, const std::string &semantic_index_sha256,
    const InfluenceOptions &options = {});

[[nodiscard]] ContextualizationArtifacts
build_contextual_influence_graph_with_value_transfers(
    const SemanticIndex &index,
    const SemanticValueTransferIndex &semantic_transfers,
    const std::string &semantic_index_sha256,
    const InfluenceOptions &options = {},
    const ValueTransferOptions &transfer_options = {});

[[nodiscard]] ApInfluenceCones compute_influence_cones(
    const TypedPropertyIr &property, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const std::string &bindings_sha256, const std::string &graph_sha256);

[[nodiscard]] std::vector<std::string> validate_influence_cones(
    const ApInfluenceCones &cones, const ApBindings &bindings,
    const ContextualInfluenceGraph &graph,
    const ArtifactDigests &expected_digests);

}  // namespace rift::core

#endif
