#include "rift/core/frontier.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace {

using namespace rift::core;

constexpr const char *kShaA =
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
constexpr const char *kShaB =
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
constexpr const char *kShaC =
    "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
constexpr const char *kShaD =
    "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";

std::shared_ptr<const EntityRef> entity(const std::string &id) {
    EntityRef value;
    value.entity_id = id;
    value.kind = EntityKind::Expression;
    value.identity_status = IdentityStatus::Exact;
    return std::make_shared<const EntityRef>(std::move(value));
}

ContextualNode node(
    const std::string &id, const std::string &semantic,
    const std::string &object, const std::string &scope,
    const std::string &generation,
    std::vector<std::string> call_context = {"call.root"}) {
    ContextualNode result;
    result.node_id = id;
    result.semantic_node_id = semantic;
    result.kind = SemanticNodeKind::Value;
    result.entity = entity("entity." + id);
    result.abstract_object.object_id = object;
    result.abstract_object.abstraction = ObjectAbstraction::Value;
    result.abstract_object.certainty = Certainty::Must;
    result.call_context.callsite_ids = std::move(call_context);
    result.scope.scope_id = scope;
    result.scope.status = IdentityStatus::Exact;
    result.generation.kind = IdentityStatus::Exact;
    result.generation.identity = generation;
    result.generation.reuse_possible = false;
    result.task_context.kind = TaskKind::Task;
    result.task_context.context_id = "task.main";
    result.task_context.certainty = Certainty::Must;
    result.lifecycle_phase = LifecyclePhase::Active;
    result.value_type.kind = ValueKind::Boolean;
    result.value_type.canonical = "bool";
    return result;
}

InfluenceEdge edge(
    const std::string &id, const std::string &source,
    const std::string &target, const RelationKind kind = RelationKind::Data) {
    InfluenceEdge result;
    result.edge_id = id;
    result.source_node_id = source;
    result.target_node_id = target;
    result.kind = kind;
    result.certainty = Certainty::May;
    Evidence evidence;
    evidence.evidence_id = "evidence." + id;
    evidence.kind = "ast_semantics";
    evidence.certainty = Certainty::May;
    evidence.fact = "neutral fixture relation";
    evidence.producer = "frontier-smoke";
    result.evidence =
        std::make_shared<const std::vector<Evidence>>(
            std::vector<Evidence>{evidence});
    return result;
}

ModelProvenance provenance() {
    ModelProvenance result;
    result.model_pack_id = "model.neutral";
    result.model_pack_version = "2.0.0";
    result.model_pack_sha256 = kShaA;
    result.layer = ModelLayer::Framework;
    result.rule_id = "rule.boundary";
    result.emit_id = "emit.boundary";
    result.selector_ids = {"selector.boundary"};
    result.capture_ids = {"capture.boundary"};
    result.matched_semantic_node_ids = {"semantic.boundary"};
    return result;
}

ExternalAction action(
    const std::string &id, const std::string &channel,
    const std::string &slot) {
    ExternalAction result;
    result.external_action_id = id;
    result.action_schema_id = "action.schema.neutral";
    result.action_class = "structured_input";
    result.channel = channel;
    result.operation = "set";
    result.payload_type.kind = ValueKind::Boolean;
    result.payload_type.canonical = "bool";
    result.payload_slot = slot;
    result.scope_schema = "object";
    result.generation_schema = "epoch";
    result.timing_capability = "none";
    result.required_capability = "capability.set";
    ModelProvenance primary = provenance();
    ModelProvenance secondary = primary;
    secondary.emit_id = "emit.boundary.secondary";
    secondary.capture_ids = {"capture.secondary", "capture.boundary"};
    result.provenance = {primary, secondary};
    return result;
}

BoundaryAttachment attachment(
    const std::string &id, const std::string &action_id,
    const std::string &semantic_node) {
    BoundaryAttachment result;
    result.attachment_id = id;
    result.external_action_id = action_id;
    result.semantic_node_id = semantic_node;
    result.transfer_relation = "payload_to_value";
    result.certainty = Certainty::Modelled;
    result.provenance = {provenance()};
    return result;
}

ModelFact fact(
    const std::string &id, const std::string &source,
    const std::string &target) {
    ModelFact result;
    result.fact_id = id;
    result.kind = ModelFactKind::SemanticTransfer;
    result.source_semantic_node_id = source;
    result.target_semantic_node_id = target;
    result.transfer_relation = "modelled_transfer";
    result.certainty = Certainty::Modelled;
    result.provenance = {provenance()};
    return result;
}

struct Fixture {
    ModelFactOverlay overlay;
    ContextualInfluenceGraph graph;
    ApInfluenceCones cones;
    ExecutorCapabilityManifest executor;
    FrontierInputDigests digests;
};

Fixture fixture() {
    Fixture value;
    value.graph.artifact_id = "graph.neutral";
    value.graph.semantic_index_sha256 = kShaA;
    value.graph.status = StageStatus::Complete;
    value.graph.nodes = {
        node("node.boundary", "semantic.boundary", "object.main", "scope.main", "generation.1"),
        node("node.mid", "semantic.mid", "object.main", "scope.main", "generation.1"),
        node("node.ap", "semantic.ap", "object.main", "scope.main", "generation.1"),
        node("node.unknown", "semantic.unknown", "object.other", "scope.other", "generation.2", {"call.other"}),
        node("node.object1", "semantic.object1", "object.1", "scope.main", "generation.1"),
        node("node.object2", "semantic.object2", "object.2", "scope.main", "generation.1"),
        node("node.scope1", "semantic.scope1", "object.scope", "scope.1", "generation.1"),
        node("node.scope2", "semantic.scope2", "object.scope", "scope.2", "generation.2"),
        node("node.call1", "semantic.call1", "object.call", "scope.main", "generation.1", {"call.left"}),
        node("node.call2", "semantic.call2", "object.call", "scope.main", "generation.1", {"call.right"}),
    };
    value.graph.edges = {
        edge("edge.mid_ap", "node.mid", "node.ap"),
        edge("edge.unknown_ap", "node.unknown", "node.ap"),
        edge("edge.object", "node.object1", "node.object2", RelationKind::Object),
        edge("edge.scope", "node.scope1", "node.scope2"),
        edge("edge.call", "node.call1", "node.call2"),
    };
    CoverageGap shared_gap;
    shared_gap.gap_id = "gap.shared";
    shared_gap.kind = "shared_fixture_gap";
    shared_gap.effect = GapEffect::PrecisionLoss;
    shared_gap.detail = "same upstream gap is propagated by graph and cone";
    value.graph.coverage_gaps = {shared_gap};

    ApInfluenceCone cone;
    cone.cone_id = "cone.neutral";
    cone.ap_id = "ap.neutral";
    cone.roles = {ApRole::State};
    cone.status = StageStatus::Complete;
    ConeMember mid;
    mid.node_id = "node.mid";
    mid.membership = ConeMembership::MayInfluence;
    mid.witness_edge_ids = {"edge.mid_ap"};
    ConeMember ap;
    ap.node_id = "node.ap";
    ap.membership = ConeMembership::MustInfluence;
    ConeMember object2;
    object2.node_id = "node.object2";
    object2.membership = ConeMembership::MayInfluence;
    ConeMember scope2;
    scope2.node_id = "node.scope2";
    scope2.membership = ConeMembership::MayInfluence;
    ConeMember call2;
    call2.node_id = "node.call2";
    call2.membership = ConeMembership::MayInfluence;
    cone.members = {mid, ap, object2, scope2, call2};
    cone.edge_ids = {
        "edge.call", "edge.mid_ap", "edge.object", "edge.scope",
        "edge.unknown_ap"};
    value.cones.artifact_id = "cones.neutral";
    value.cones.ap_bindings_sha256 = kShaA;
    value.cones.graph_sha256 = kShaB;
    value.cones.status = StageStatus::Complete;
    value.cones.cones = {cone};
    value.cones.coverage_gaps = {shared_gap};

    value.overlay.artifact_id = "overlay.neutral";
    value.overlay.semantic_index_artifact_id = "index.neutral";
    value.overlay.semantic_index_identity = kShaA;
    value.overlay.status = StageStatus::Complete;
    value.overlay.model_pack_sha256s = {kShaA};
    value.overlay.external_actions = {
        action("action.multi", "channel.a", "slot.a"),
        action("action.same-node", "channel.b", "slot.b"),
        action("action.no-attachment", "channel.c", "slot.c"),
        action("action.object-negative", "channel.d", "slot.d"),
        action("action.scope-negative", "channel.e", "slot.e"),
        action("action.call-negative", "channel.f", "slot.f"),
    };
    value.overlay.boundary_attachments = {
        attachment("attachment.multi.good", "action.multi", "semantic.boundary"),
        attachment("attachment.multi.unknown", "action.multi", "semantic.unknown"),
        attachment("attachment.same-node", "action.same-node", "semantic.boundary"),
        attachment("attachment.object", "action.object-negative", "semantic.object1"),
        attachment("attachment.scope", "action.scope-negative", "semantic.scope1"),
        attachment("attachment.call", "action.call-negative", "semantic.call1"),
    };
    value.overlay.semantic_facts = {
        fact("fact.boundary-mid", "semantic.boundary", "semantic.mid")};
    ModelResourceLedgerEntry ledger;
    ledger.ledger_id = "ledger.neutral";
    ledger.model_pack_id = "model.neutral";
    ledger.operation = "EMIT";
    ledger.limit = 100;
    ledger.observed = 7;
    ledger.complete = true;
    ledger.certainty = Certainty::Modelled;
    value.overlay.resource_ledger = {ledger};

    value.executor.schema_version = "1.0.0";
    value.executor.artifact_id = "executor.neutral";
    value.executor.executor_id = "executor.fixture";
    value.executor.executor_version = "1.0.0";
    value.executor.status = StageStatus::Complete;
    ExecutorCapabilityEntry capability;
    capability.capability_id = "capability.set.entry";
    capability.required_capability = "capability.set";
    capability.controllability = ControllabilityVerdict::Direct;
    capability.evidence_note = "fixture executor accepts structured set actions";
    value.executor.capabilities = {capability};

    value.digests.model_fact_overlay_sha256 = kShaA;
    value.digests.graph_sha256 = kShaB;
    value.digests.cones_sha256 = kShaC;
    value.digests.executor_manifest_sha256 = kShaD;
    return value;
}

Fixture scaling_fixture(const std::size_t meet_count) {
    Fixture value = fixture();
    value.graph.coverage_gaps.clear();
    value.cones.coverage_gaps.clear();
    value.graph.nodes = {
        node(
            "node.scaling.boundary", "semantic.scaling.boundary",
            "object.scaling", "scope.scaling", "generation.scaling")};
    value.graph.edges.clear();
    ApInfluenceCone &cone = value.cones.cones.front();
    cone.members.clear();
    cone.edge_ids.clear();
    for (std::size_t index = 0; index < meet_count; ++index) {
        const std::string suffix = std::to_string(index);
        const std::string node_id = "node.scaling.meet." + suffix;
        const std::string edge_id = "edge.scaling." + suffix;
        value.graph.nodes.push_back(node(
            node_id, "semantic.scaling.meet." + suffix,
            "object.scaling", "scope.scaling", "generation.scaling"));
        value.graph.edges.push_back(edge(
            edge_id, "node.scaling.boundary", node_id));
        ConeMember member;
        member.node_id = node_id;
        member.membership = ConeMembership::MayInfluence;
        cone.members.push_back(std::move(member));
        cone.edge_ids.push_back(edge_id);
    }
    value.overlay.external_actions = {
        action("action.scaling", "channel.scaling", "slot.scaling")};
    value.overlay.boundary_attachments = {attachment(
        "attachment.scaling", "action.scaling",
        "semantic.scaling.boundary")};
    value.overlay.semantic_facts.clear();
    value.overlay.resource_ledger.front().observed = 1;
    return value;
}

const FrontierCandidate *find_candidate(
    const FrontierCandidates &frontier, const std::string &action_id) {
    const auto found = std::find_if(
        frontier.candidates.begin(), frontier.candidates.end(),
        [&action_id](const FrontierCandidate &candidate) {
            return candidate.action.external_action_id == action_id;
        });
    return found == frontier.candidates.end() ? nullptr : &*found;
}

bool require(const bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
    }
    return condition;
}

}  // namespace

int main(const int argc, char **argv) {
    Fixture base = fixture();
    const FrontierCandidates first = compute_frontier_candidates(
        base.overlay, base.graph, base.cones, base.digests, base.executor);
    bool ok = true;
    ok &= require(first.candidates.size() == 6U, "all actions are accounted");
    ok &= require(
        first.coverage_gaps.size() == 1U,
        "one upstream coverage gap is referenced once in the frontier ledger");
    ok &= require(
        validate_frontier_candidates(
            first, base.overlay, base.graph, base.cones, base.digests,
            base.executor)
            .empty(),
        "deterministic validator accepts frontier");
    ok &= require(
        validate_frontier_candidates(
            first, base.overlay, base.graph, base.cones, base.digests,
            base.executor, {}, FrontierValidationMode::Structural)
            .empty(),
        "producer hot-path structural validator accepts frontier");

    const FrontierCandidate *multi = find_candidate(first, "action.multi");
    ok &= require(multi != nullptr, "multi-attachment candidate exists");
    if (multi != nullptr) {
        ok &= require(
            multi->disposition == FrontierDisposition::Actionable,
            "one compatible attachment makes candidate actionable");
        ok &= require(
            multi->attachment_accounting.size() == 2U,
            "both attachments remain in the ledger");
        const auto good = std::find_if(
            multi->attachment_accounting.begin(),
            multi->attachment_accounting.end(),
            [](const FrontierAttachmentAccount &account) {
                return account.attachment_id == "attachment.multi.good";
            });
        const auto unknown = std::find_if(
            multi->attachment_accounting.begin(),
            multi->attachment_accounting.end(),
            [](const FrontierAttachmentAccount &account) {
                return account.attachment_id == "attachment.multi.unknown";
            });
        ok &= require(
            good != multi->attachment_accounting.end() &&
                good->disposition == AttachmentDisposition::Witnessed,
            "compatible attachment is witnessed");
        ok &= require(
            good != multi->attachment_accounting.end() &&
                good->witness_ids.size() == 1U,
            "all meet points for one boundary/cone pair share one union witness");
        if (good != multi->attachment_accounting.end() &&
            good->witness_ids.size() == 1U) {
            const auto union_witness = std::find_if(
                multi->witnesses.begin(), multi->witnesses.end(),
                [&](const FrontierWitness &witness) {
                    return witness.witness_id == good->witness_ids.front();
                });
            ok &= require(
                union_witness != multi->witnesses.end() &&
                    union_witness->meet_summary.meet_count >= 2U,
                "union witness accounts for both reachable cone members");
        }
        ok &= require(
            unknown != multi->attachment_accounting.end() &&
                unknown->disposition == AttachmentDisposition::Unknown,
            "later UNKNOWN attachment is not contaminated by earlier witness");
    }

    const FrontierCandidate *same_node =
        find_candidate(first, "action.same-node");
    ok &= require(
        same_node != nullptr && same_node->disposition ==
                                    FrontierDisposition::Actionable,
        "second action on one node remains independently actionable");
    ok &= require(
        same_node != nullptr && multi != nullptr &&
            same_node->candidate_id != multi->candidate_id,
        "multi-action/one-node identities are not merged");
    if (same_node != nullptr && multi != nullptr &&
        !same_node->witnesses.empty()) {
        const auto multi_good_witness = std::find_if(
            multi->witnesses.begin(), multi->witnesses.end(),
            [](const FrontierWitness &witness) {
                return witness.attachment_id == "attachment.multi.good";
            });
        if (multi_good_witness != multi->witnesses.end()) {
            const FrontierWitness &shared_path_witness =
                same_node->witnesses.front();
            ok &= require(
                multi_good_witness->support_summary
                        .supporting_transition_ledger_sha256 ==
                    shared_path_witness.support_summary
                        .supporting_transition_ledger_sha256,
                "identical product support reuses one semantic ledger");
            ok &= require(
                multi_good_witness->meet_summary.ledger_sha256 !=
                        shared_path_witness.meet_summary.ledger_sha256 &&
                    multi_good_witness->witness_id !=
                        shared_path_witness.witness_id,
                "attachment-specific meet and witness identities are not cached away");
        }
    }
    const FrontierCandidate *no_attachment =
        find_candidate(first, "action.no-attachment");
    ok &= require(
        no_attachment != nullptr &&
            no_attachment->evidence.reachability ==
                ReachabilityVerdict::NoStaticWitness &&
            no_attachment->disposition == FrontierDisposition::Rejected,
        "closed empty meet is NO_STATIC_WITNESS");
    const FrontierCandidate *object_negative =
        find_candidate(first, "action.object-negative");
    ok &= require(
        object_negative != nullptr &&
            object_negative->evidence.reachability ==
                ReachabilityVerdict::NoStaticWitness,
        "distinct exact objects do not form an object-preserving witness");
    for (const std::string action_id :
         {"action.scope-negative", "action.call-negative"}) {
        const FrontierCandidate *negative = find_candidate(first, action_id);
        ok &= require(
            negative != nullptr &&
                negative->evidence.reachability ==
                    ReachabilityVerdict::Unknown &&
                negative->disposition == FrontierDisposition::Pending,
            "scope/generation/call mismatch degrades to UNKNOWN");
    }

    Fixture permuted = base;
    std::reverse(permuted.graph.nodes.begin(), permuted.graph.nodes.end());
    std::reverse(permuted.graph.edges.begin(), permuted.graph.edges.end());
    std::reverse(
        permuted.overlay.external_actions.begin(),
        permuted.overlay.external_actions.end());
    for (ExternalAction &item : permuted.overlay.external_actions) {
        std::reverse(item.provenance.begin(), item.provenance.end());
        for (ModelProvenance &source : item.provenance) {
            std::reverse(source.capture_ids.begin(), source.capture_ids.end());
        }
    }
    std::reverse(
        permuted.overlay.boundary_attachments.begin(),
        permuted.overlay.boundary_attachments.end());
    std::reverse(
        permuted.overlay.semantic_facts.begin(),
        permuted.overlay.semantic_facts.end());
    std::reverse(
        permuted.cones.cones.front().members.begin(),
        permuted.cones.cones.front().members.end());
    const FrontierCandidates second = compute_frontier_candidates(
        permuted.overlay, permuted.graph, permuted.cones, permuted.digests,
        permuted.executor);
    ok &= require(
        canonical_frontier_candidates_json(first) ==
            canonical_frontier_candidates_json(second),
        "input and edge-order permutation is byte deterministic");

    Fixture small_scaling = scaling_fixture(32U);
    Fixture large_scaling = scaling_fixture(256U);
    const FrontierCandidates small_frontier = compute_frontier_candidates(
        small_scaling.overlay, small_scaling.graph, small_scaling.cones,
        small_scaling.digests, small_scaling.executor);
    const FrontierCandidates large_frontier = compute_frontier_candidates(
        large_scaling.overlay, large_scaling.graph, large_scaling.cones,
        large_scaling.digests, large_scaling.executor);
    const std::size_t small_bytes =
        canonical_frontier_candidates_json(small_frontier).size();
    const std::size_t large_bytes =
        canonical_frontier_candidates_json(large_frontier).size();
    ok &= require(
        large_bytes <= small_bytes + 4096U,
        "frontier certificate size is bounded by summaries, not meet count");

    ModelFactOverlay incomplete = base.overlay;
    incomplete.status = StageStatus::ConservativeIncomplete;
    incomplete.unknown_outcomes.push_back(
        {"unknown.vm", "model.neutral", std::nullopt, "EMIT",
         "resource coverage gap", {"emit.boundary"}});
    const FrontierCandidates with_gap = compute_frontier_candidates(
        incomplete, base.graph, base.cones, base.digests, base.executor);
    const FrontierCandidate *gap_empty =
        find_candidate(with_gap, "action.no-attachment");
    ok &= require(
        gap_empty != nullptr &&
            gap_empty->evidence.reachability ==
                ReachabilityVerdict::Unknown &&
            gap_empty->disposition == FrontierDisposition::Pending,
        "empty meet plus incomplete ledger is UNKNOWN");

    FrontierCandidates schema_gap = first;
    CoverageGap public_gap;
    public_gap.gap_id = "gap.frontier.schema-contract";
    public_gap.kind = "schema_contract_fixture";
    public_gap.effect = GapEffect::PrecisionLoss;
    public_gap.detail = "exercise the public unsupported-construct shape";
    schema_gap.coverage_gaps.push_back(public_gap);
    const std::string schema_gap_json =
        canonical_frontier_candidates_json(schema_gap);
    ok &= require(
        schema_gap_json.find("\"construct_id\":") != std::string::npos &&
            schema_gap_json.find("\"gap_id\":") == std::string::npos,
        "coverage gaps use the public common-schema field name");

    const std::string first_json = canonical_frontier_candidates_json(first);
    const std::string first_sha = sha256_hex(first_json);
    const FuzzableFrontier projection =
        project_fuzzable_frontier(first, first_sha);
    ok &= require(
        projection.actions.size() == 2U,
        "actionable projection contains only two compatible actions");
    ok &= require(
        validate_fuzzable_frontier(projection, first, first_sha).empty(),
        "projection validator accepts deterministic result");

    if (argc == 3) {
        std::ofstream candidates_output(argv[1], std::ios::binary);
        std::ofstream projection_output(argv[2], std::ios::binary);
        candidates_output << first_json;
        projection_output << canonical_fuzzable_frontier_json(projection);
        ok &= require(
            candidates_output.good() && projection_output.good(),
            "optional JSON fixtures are written");
    }

    if (!ok) {
        return 1;
    }
    std::cout << "frontier smoke: PASS\n";
    return 0;
}
