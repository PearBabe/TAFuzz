#include "rift/core/model.h"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace rift::core;

int failures = 0;
int adversarial_checks = 0;

void check(bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        ++failures;
    }
}

void expect_rejected(ModelPackV2 pack, const std::string &message) {
    ++adversarial_checks;
    check(!validate_model_pack_v2(pack).empty(), message);
}

ValueType integer_type() {
    ValueType type;
    type.kind = ValueKind::Integer;
    type.canonical = "int";
    type.bit_width = 32;
    type.is_signed = true;
    return type;
}

EntityRef entity(
    std::string id, std::optional<std::string> signature = std::nullopt,
    std::optional<std::string> usr = std::nullopt) {
    EntityRef result;
    result.entity_id = std::move(id);
    result.kind = EntityKind::Function;
    result.identity_status = IdentityStatus::Exact;
    result.qualified_signature = std::move(signature);
    result.usr = std::move(usr);
    result.canonical_type = "int";
    return result;
}

SemanticNode node(
    std::string id, std::string entity_id, std::string owner) {
    SemanticNode result;
    result.node_id = std::move(id);
    result.kind = SemanticNodeKind::Value;
    result.entity_id = std::move(entity_id);
    result.owner_function_id = std::move(owner);
    result.value_type = integer_type();
    result.ast_kind = "DeclRefExpr";
    return result;
}

SemanticIndex base_index() {
    SemanticIndex index;
    index.artifact_id = "index:demo";
    index.compilation_database_sha256 = std::string(64, 'b');
    index.status = StageStatus::Complete;
    index.entities = {
        entity("entity:ingest", "demo::ingest(int)", "usr.demo.ingest"),
        entity("entity:caller", "demo::caller()", "usr.demo.caller"),
        entity("entity:argument"), entity("entity:formal"),
        entity("entity:result"), entity("entity:receiver"),
        entity("entity:field", "demo::record::value", "usr.demo.field")};
    index.nodes = {
        node("node:ingest", "entity:ingest", "entity:ingest"),
        node("node:argument", "entity:argument", "entity:caller"),
        node("node:formal", "entity:formal", "entity:ingest"),
        node("node:result", "entity:result", "entity:caller"),
        node("node:receiver", "entity:receiver", "entity:caller"),
        node("node:field", "entity:field", "entity:ingest")};
    index.nodes.back().access_path =
        AccessPath{"entity:ingest", 0, {"entity:field"}, false};
    FunctionSummary summary;
    summary.function_entity_id = "entity:ingest";
    summary.parameter_node_ids = {"node:formal"};
    summary.receiver_node_id = "node:receiver";
    summary.return_node_id = "node:result";
    summary.owned_node_ids = {
        "node:ingest", "node:formal", "node:receiver", "node:field"};
    summary.callsite_ids = {"callsite:one"};
    index.function_summaries.push_back(std::move(summary));
    CallSiteSummary callsite;
    callsite.callsite_id = "callsite:one";
    callsite.caller_function_id = "entity:caller";
    callsite.candidate_callee_ids = {"entity:ingest"};
    callsite.argument_node_ids = {"node:argument"};
    callsite.argument_node_groups = {{"node:argument"}};
    callsite.argument_is_address = {false};
    callsite.receiver_node_id = "node:receiver";
    callsite.result_node_id = "node:result";
    callsite.direct = true;
    callsite.status = StageStatus::Complete;
    index.callsites.push_back(std::move(callsite));
    return index;
}

ExternalActionTemplateV2 action_template() {
    return ExternalActionTemplateV2{
        "action.stream.integer", "message_field", "stream", "set",
        integer_type(), "field", "session", "epoch", "relative", "direct"};
}

ModelPackV2 base_pack() {
    ModelPackV2 pack;
    pack.model_pack_id = "framework.demo";
    pack.model_pack_version = "1.0.0";
    pack.layer = ModelLayer::Framework;
    pack.target = ModelTargetContract{
        "1.0", "generic-abi", "evidence.public", "freeze_before_property"};
    pack.resource_limits = ModelResourceLimits{100, 100, 100, 100};
    pack.observed_sha256 = sha256_hex("framework.demo.bytes");
    pack.selectors.push_back(ModelSelectorV2{
        "selector.ingest", ModelSelectorKind::ExactQualifiedSignature,
        "demo::ingest(int)", std::nullopt, {}, std::nullopt, false});
    ModelRuleV2 rule;
    rule.rule_id = "rule.boundary";
    rule.matches.push_back(ModelMatchV2{"match.ingest", "selector.ingest"});
    rule.captures.push_back(ModelCaptureV2{
        "capture.argument", "match.ingest",
        ModelProjectionKind::CallArgument, 0});
    rule.emits.push_back(ModelEmitV2{
        "emit.boundary", ModelFactKind::ExternalBoundary,
        "capture.argument", std::nullopt, Certainty::Modelled,
        "executor_to_argument", action_template(), std::nullopt,
        std::nullopt});
    rule.evidence_note = "public interface contract";
    pack.rules.push_back(std::move(rule));
    return pack;
}

std::string valid_json() {
    return R"JSON({
  "schema_version": "2.0.0",
  "model_pack_id": "framework.demo",
  "model_pack_version": "1.0.0",
  "layer": "framework",
  "property_independent": true,
  "target": {
    "target_version": "1.0",
    "target_abi": "generic-abi",
    "evidence_id": "evidence.public",
    "digest_policy": "freeze_before_property"
  },
  "resource_limits": {
    "max_selector_matches": 100,
    "max_capture_values": 100,
    "max_join_assignments": 100,
    "max_emitted_facts": 100
  },
  "selectors": [{
    "selector_id": "selector.ingest",
    "kind": "exact_qualified_signature",
    "exact_value": "demo::ingest(int)"
  }],
  "rules": [{
    "rule_id": "rule.boundary",
    "matches": [{"match_id": "match.ingest", "selector_ref": "selector.ingest"}],
    "captures": [{
      "capture_id": "capture.argument",
      "match_ref": "match.ingest",
      "projection": "call_argument",
      "index": 0
    }],
    "joins": [],
    "emits": [{
      "emit_id": "emit.boundary",
      "fact_kind": "external_boundary",
      "source_capture_ref": "capture.argument",
      "certainty": "modelled",
      "transfer_relation": "executor_to_argument",
      "external_action": {
        "action_schema_id": "action.stream.integer",
        "action_class": "message_field",
        "channel": "stream",
        "operation": "set",
        "payload_type": {"kind": "integer", "canonical": "int", "bit_width": 32, "signed": true},
        "payload_slot": "field",
        "scope_schema": "session",
        "generation_schema": "epoch",
        "timing_capability": "relative",
        "required_capability": "direct"
      }
    }],
    "evidence_note": "public interface contract"
  }]
})JSON";
}

std::filesystem::path write_temp(const std::string &bytes) {
    const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    const std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("rift-model-vm-" + std::to_string(stamp) + ".json");
    std::ofstream output(path, std::ios::binary);
    output << bytes;
    return path;
}

void loader_tests() {
    const std::string json = valid_json();
    const std::filesystem::path path = write_temp(json);
    const auto loaded = load_model_pack_v2(path, sha256_hex(json));
    check(loaded.status == StageStatus::Complete && loaded.value.has_value(),
          "valid v2 JSON loads with bound digest");
    const auto wrong_digest = load_model_pack_v2(path, std::string(64, '0'));
    ++adversarial_checks;
    check(wrong_digest.status == StageStatus::Failed,
          "digest mismatch fails closed");
    std::filesystem::remove(path);

    std::string v1 = json;
    v1.replace(v1.find("2.0.0"), 5, "1.0.0");
    const auto v1_path = write_temp(v1);
    ++adversarial_checks;
    check(load_model_pack_v2(v1_path).status == StageStatus::Failed,
          "v1 boundary is non-executable");
    std::filesystem::remove(v1_path);

    std::string unknown = json;
    unknown.replace(
        unknown.find("\"property_independent\""), 22,
        "\"unknown_script\": \"x\", \"property_independent\"");
    const auto unknown_path = write_temp(unknown);
    ++adversarial_checks;
    check(load_model_pack_v2(unknown_path).status == StageStatus::Failed,
          "unknown executable member fails closed");
    std::filesystem::remove(unknown_path);

    std::string zero = json;
    const std::string needle = "\"max_selector_matches\": 100";
    zero.replace(zero.find(needle), needle.size(),
                 "\"max_selector_matches\": 0");
    const auto zero_path = write_temp(zero);
    ++adversarial_checks;
    check(load_model_pack_v2(zero_path).status == StageStatus::Failed,
          "zero resource limit fails closed");
    std::filesystem::remove(zero_path);
}

void validator_adversarial_tests() {
    ModelPackV2 pack = base_pack();
    check(validate_model_pack_v2(pack).empty(), "base pack validates");

    ModelPackV2 changed = pack;
    changed.schema_version = "1.0.0";
    expect_rejected(std::move(changed), "in-memory v1 rejected");

    changed = pack;
    changed.property_independent = false;
    expect_rejected(std::move(changed), "property-dependent pack rejected");

    changed = pack;
    changed.resource_limits.max_join_assignments = 0;
    expect_rejected(std::move(changed), "zero limit rejected semantically");

    changed = pack;
    changed.selectors.push_back(changed.selectors.front());
    expect_rejected(std::move(changed), "duplicate selector rejected");

    changed = pack;
    changed.rules.push_back(changed.rules.front());
    expect_rejected(std::move(changed), "duplicate rule rejected");

    changed = pack;
    ModelRuleV2 duplicate_nested = changed.rules.front();
    duplicate_nested.rule_id = "rule.other";
    changed.rules.push_back(std::move(duplicate_nested));
    expect_rejected(
        std::move(changed), "nested instruction IDs are globally unique");

    changed = pack;
    changed.rules.front().matches.front().selector_ref = "selector.missing";
    expect_rejected(std::move(changed), "dangling selector rejected");

    changed = pack;
    changed.rules.front().captures.front().match_ref = "match.missing";
    expect_rejected(std::move(changed), "dangling match rejected");

    changed = pack;
    changed.rules.front().emits.front().source_capture_ref = "capture.missing";
    expect_rejected(std::move(changed), "dangling emit capture rejected");

    changed = pack;
    changed.rules.clear();
    expect_rejected(std::move(changed), "empty rule set rejected");

    changed = pack;
    changed.rules.front().captures.clear();
    expect_rejected(std::move(changed), "empty capture set rejected");

    changed = pack;
    changed.rules.front().captures.front().index.reset();
    expect_rejected(std::move(changed), "missing call argument index rejected");

    changed = pack;
    changed.rules.front().captures.front().projection =
        ModelProjectionKind::MatchedNode;
    expect_rejected(std::move(changed), "unexpected projection index rejected");

    changed = pack;
    changed.rules.front().emits.front().certainty = Certainty::Must;
    expect_rejected(std::move(changed), "pack cannot emit MUST");

    changed = pack;
    changed.rules.front().emits.front().target_capture_ref = "capture.argument";
    expect_rejected(std::move(changed), "boundary cannot have target capture");

    changed = pack;
    changed.rules.front().emits.front().fact_kind =
        ModelFactKind::SemanticTransfer;
    changed.rules.front().emits.front().external_action.reset();
    expect_rejected(std::move(changed), "non-boundary requires target capture");

    changed = pack;
    ModelEmitV2 clock_emit;
    clock_emit.emit_id = "emit.clock";
    clock_emit.fact_kind = ModelFactKind::ClockRelation;
    clock_emit.source_capture_ref = "capture.argument";
    clock_emit.target_capture_ref = "capture.argument";
    clock_emit.certainty = Certainty::Modelled;
    clock_emit.transfer_relation = "relative_clock";
    clock_emit.clock_relation = ModelClockRelationV2{
        "clock.monotonic", ModelClockUnit::Milliseconds, "epoch.session",
        1.0, 0.0, ModelClockWrap::None, std::nullopt,
        "event.start", "event.end", ModelClockEndpoint::Closed,
        "session", "epoch"};
    changed.rules.front().emits.push_back(clock_emit);
    check(validate_model_pack_v2(changed).empty(),
          "complete typed clock relation validates");
    changed.rules.back().emits.back().clock_relation->quantum.reset();
    expect_rejected(
        std::move(changed), "clock relation with a missing fixed field fails closed");

    changed = pack;
    ModelEmitV2 joint_emit;
    joint_emit.emit_id = "emit.joint";
    joint_emit.fact_kind = ModelFactKind::JointActionRelation;
    joint_emit.source_capture_ref = "capture.argument";
    joint_emit.certainty = Certainty::Modelled;
    joint_emit.transfer_relation = "atomic_group";
    joint_emit.joint_action_relation = ModelJointActionRelationV2{
        "group.atomic", ModelJointActionOperator::AllRequired, true,
        {"capture.argument", "capture.result"}, "session", "epoch"};
    changed.rules.front().captures.push_back(ModelCaptureV2{
        "capture.result", "match.ingest", ModelProjectionKind::CallResult,
        std::nullopt});
    changed.rules.front().emits.push_back(joint_emit);
    check(validate_model_pack_v2(changed).empty(),
          "complete typed joint-action relation validates");
    changed.rules.front().emits.back()
        .joint_action_relation->participant_capture_refs = {
            "capture.argument", "capture.missing"};
    expect_rejected(
        std::move(changed), "joint-action relation rejects a dangling participant");

    changed = pack;
    changed.selectors.front().application_private = true;
    expect_rejected(std::move(changed), "framework private selector rejected");

    changed = pack;
    changed.layer = ModelLayer::ProjectAdapter;
    changed.selectors.front().application_private = true;
    check(validate_model_pack_v2(changed).empty(),
          "project adapter explicitly admits private selector");

    changed = pack;
    changed.selectors.push_back(ModelSelectorV2{
        "selector.field", ModelSelectorKind::TypedField, std::nullopt,
        "selector.missing", {"demo::record::value"}, "int", false});
    expect_rejected(std::move(changed), "typed field dangling owner rejected");

    changed = pack;
    changed.selectors.push_back(ModelSelectorV2{
        "selector.field.one", ModelSelectorKind::TypedField, std::nullopt,
        "selector.field.two", {"demo::record::value"}, "int", false});
    changed.selectors.push_back(ModelSelectorV2{
        "selector.field.two", ModelSelectorKind::TypedField, std::nullopt,
        "selector.field.one", {"demo::record::value"}, "int", false});
    expect_rejected(std::move(changed), "typed-field recursion rejected");

    const std::vector<std::string> forbidden{
        "target_property", "target_ap", "benchmark_case", "expected_answer",
        "selection_oracle", "gold_label", "experiment_result", "replay_input",
        "/absolute/location", "source.cpp"};
    for (const std::string &value : forbidden) {
        changed = pack;
        changed.rules.front().evidence_note = value;
        expect_rejected(
            std::move(changed), "forbidden hidden/source material rejected: " + value);
    }
}

ModelPackV2 projection_pack(ModelProjectionKind projection) {
    ModelPackV2 pack = base_pack();
    pack.model_pack_id =
        "framework.projection." + std::to_string(static_cast<int>(projection));
    pack.observed_sha256 = sha256_hex(pack.model_pack_id);
    ModelCaptureV2 &capture = pack.rules.front().captures.front();
    capture.projection = projection;
    if (projection == ModelProjectionKind::FormalParameter ||
        projection == ModelProjectionKind::CallArgument) {
        capture.index = 0;
    } else {
        capture.index.reset();
    }
    return pack;
}

void execution_tests() {
    SemanticIndex index = base_index();
    const std::string index_sha256 = sha256_hex("semantic-index.json bytes");
    const ModelPackV2 pack = base_pack();
    const auto result = execute_model_pack_v2(pack, index, index_sha256);
    check(result.value.has_value(), "base VM execution yields overlay");
    if (result.value) {
        check(result.status == StageStatus::Complete,
              "base execution is complete");
        check(result.value->external_actions.size() == 1 &&
                  result.value->boundary_attachments.size() == 1,
              "external action remains separate from one attachment");
        check(result.value->semantic_index_identity.size() == 64,
              "overlay binds semantic index content digest");
        check(validate_model_fact_overlay(
                  *result.value, index, index_sha256).empty(),
              "produced overlay independently validates");
    }

    ModelPackV2 semantic_contracts = pack;
    semantic_contracts.model_pack_id = "framework.semantic.contracts";
    semantic_contracts.observed_sha256 =
        sha256_hex("framework.semantic.contracts");
    semantic_contracts.rules.front().captures.push_back(ModelCaptureV2{
        "capture.result", "match.ingest", ModelProjectionKind::CallResult,
        std::nullopt});
    ModelEmitV2 clock_emit;
    clock_emit.emit_id = "emit.clock";
    clock_emit.fact_kind = ModelFactKind::ClockRelation;
    clock_emit.source_capture_ref = "capture.argument";
    clock_emit.target_capture_ref = "capture.result";
    clock_emit.certainty = Certainty::Modelled;
    clock_emit.transfer_relation = "relative_clock";
    clock_emit.clock_relation = ModelClockRelationV2{
        "clock.monotonic", ModelClockUnit::Milliseconds, "epoch.session",
        1.0, 0.0, ModelClockWrap::None, std::nullopt,
        "event.start", "event.end", ModelClockEndpoint::Closed,
        "session", "epoch"};
    semantic_contracts.rules.front().emits.push_back(clock_emit);
    ModelEmitV2 joint_emit;
    joint_emit.emit_id = "emit.joint";
    joint_emit.fact_kind = ModelFactKind::JointActionRelation;
    joint_emit.source_capture_ref = "capture.argument";
    joint_emit.certainty = Certainty::Modelled;
    joint_emit.transfer_relation = "atomic_group";
    joint_emit.joint_action_relation = ModelJointActionRelationV2{
        "group.atomic", ModelJointActionOperator::AllRequired, true,
        {"capture.argument", "capture.result"}, "session", "epoch"};
    semantic_contracts.rules.front().emits.push_back(joint_emit);
    const auto semantic_result = execute_model_pack_v2(
        semantic_contracts, index, index_sha256);
    check(semantic_result.value.has_value() &&
              semantic_result.value->semantic_facts.size() == 1 &&
              semantic_result.value->semantic_facts.front().clock_relation &&
              semantic_result.value->joint_action_constraints.size() == 1,
          "finite VM propagates typed clock and joint-action evidence");
    if (semantic_result.value) {
        const std::string before =
            canonical_model_fact_overlay_json(*semantic_result.value);
        ModelFactOverlay changed_overlay = *semantic_result.value;
        changed_overlay.semantic_facts.front().clock_relation->jitter = 0.5;
        const std::string after =
            canonical_model_fact_overlay_json(changed_overlay);
        check(before != after && sha256_hex(before) != sha256_hex(after),
              "clock metadata changes canonical overlay bytes and digest");
        ++adversarial_checks;
        check(!validate_model_fact_overlay(
                   changed_overlay, index, index_sha256).empty(),
              "clock metadata tamper breaks the content-bound fact identity");
        ModelFactOverlay changed_joint = *semantic_result.value;
        changed_joint.joint_action_constraints.front().combination =
            ModelJointActionOperator::AnySufficient;
        check(
            canonical_model_fact_overlay_json(changed_joint) != before,
            "joint-action semantics are certificate-bound by overlay bytes");
        ++adversarial_checks;
        check(!validate_model_fact_overlay(
                   changed_joint, index, index_sha256).empty(),
              "joint-action semantic tamper breaks its content-bound constraint identity");
    }

    for (const ModelProjectionKind projection : {
             ModelProjectionKind::MatchedNode,
             ModelProjectionKind::FormalParameter,
             ModelProjectionKind::CallArgument,
             ModelProjectionKind::CallResult,
             ModelProjectionKind::Receiver}) {
        const auto projected = execute_model_pack_v2(
            projection_pack(projection), index, index_sha256);
        check(projected.value.has_value() &&
                  !projected.value->boundary_attachments.empty(),
              "fixed projection executes: " +
                  std::to_string(static_cast<int>(projection)));
    }

    ModelPackV2 usr_pack = base_pack();
    usr_pack.model_pack_id = "framework.usr";
    usr_pack.observed_sha256 = sha256_hex("framework.usr");
    usr_pack.selectors.front().kind = ModelSelectorKind::ExactUsr;
    usr_pack.selectors.front().exact_value = "usr.demo.ingest";
    check(execute_model_pack_v2(usr_pack, index, index_sha256).value.has_value(),
          "exact USR selector executes");

    ModelPackV2 field_pack = base_pack();
    field_pack.model_pack_id = "framework.field";
    field_pack.observed_sha256 = sha256_hex("framework.field");
    field_pack.selectors.push_back(ModelSelectorV2{
        "selector.field", ModelSelectorKind::TypedField, std::nullopt,
        "selector.ingest", {"demo::record::value"}, "int", false});
    field_pack.rules.front().matches.front().selector_ref = "selector.field";
    field_pack.rules.front().captures.front().projection =
        ModelProjectionKind::MatchedNode;
    field_pack.rules.front().captures.front().index.reset();
    const auto field_result =
        execute_model_pack_v2(field_pack, index, index_sha256);
    check(field_result.value.has_value() &&
              field_result.value->boundary_attachments.front().semantic_node_id ==
                  "node:field",
          "typed field selector matches owner+field+type");

    SemanticIndex two_calls = index;
    two_calls.entities.push_back(entity("entity:argument.two"));
    two_calls.nodes.push_back(
        node("node:argument.two", "entity:argument.two", "entity:caller"));
    CallSiteSummary second = two_calls.callsites.front();
    second.callsite_id = "callsite:two";
    second.argument_node_ids = {"node:argument.two"};
    second.argument_node_groups = {{"node:argument.two"}};
    second.result_node_id.reset();
    second.receiver_node_id.reset();
    two_calls.callsites.push_back(std::move(second));
    const std::string two_calls_sha256 =
        sha256_hex("two-calls semantic-index.json bytes");
    const auto two = execute_model_pack_v2(
        pack, two_calls, two_calls_sha256);
    check(two.value.has_value() && two.value->external_actions.size() == 2,
          "same action schema at two callsites has distinct identities");

    ModelPackV2 multi_attachment = pack;
    multi_attachment.model_pack_id = "framework.multi.attachment";
    multi_attachment.observed_sha256 = sha256_hex("framework.multi.attachment");
    multi_attachment.rules.front().captures.push_back(ModelCaptureV2{
        "capture.result", "match.ingest", ModelProjectionKind::CallResult,
        std::nullopt});
    multi_attachment.rules.front().joins.push_back(ModelJoinV2{
        "join.callsite", ModelJoinKind::SameCallsite, "capture.argument",
        "capture.result"});
    ModelEmitV2 result_attachment =
        multi_attachment.rules.front().emits.front();
    result_attachment.emit_id = "emit.boundary.result";
    result_attachment.source_capture_ref = "capture.result";
    multi_attachment.rules.front().emits.push_back(
        std::move(result_attachment));
    const auto attached = execute_model_pack_v2(
        multi_attachment, index, index_sha256);
    check(attached.value.has_value() &&
              attached.value->external_actions.size() == 1 &&
              attached.value->boundary_attachments.size() == 2,
          "one callsite action retains multiple boundary attachments");

    ModelPackV2 unknown_scope = multi_attachment;
    unknown_scope.model_pack_id = "framework.scope.join";
    unknown_scope.observed_sha256 = sha256_hex("framework.scope.join");
    unknown_scope.rules.front().joins.front().kind =
        ModelJoinKind::SameScope;
    const auto scope_result = execute_model_pack_v2(
        unknown_scope, index, index_sha256);
    ++adversarial_checks;
    check(scope_result.value.has_value() &&
              scope_result.status == StageStatus::ConservativeIncomplete &&
              !scope_result.value->unknown_outcomes.empty() &&
              std::all_of(
                  scope_result.value->boundary_attachments.begin(),
                  scope_result.value->boundary_attachments.end(),
                  [](const BoundaryAttachment &attachment) {
                      return attachment.certainty == Certainty::Unknown;
                  }),
          "unclosed scope join is retained with explicit UNKNOWN evidence");

    ModelPackV2 multi_action = pack;
    multi_action.model_pack_id = "framework.multi.action";
    multi_action.observed_sha256 = sha256_hex("framework.multi.action");
    ModelEmitV2 alternate_action = multi_action.rules.front().emits.front();
    alternate_action.emit_id = "emit.alternate";
    alternate_action.external_action->action_schema_id =
        "action.stream.alternate";
    alternate_action.external_action->operation = "unset";
    multi_action.rules.front().emits.push_back(std::move(alternate_action));
    const auto actions_at_one_node = execute_model_pack_v2(
        multi_action, index, index_sha256);
    check(actions_at_one_node.value.has_value() &&
              actions_at_one_node.value->external_actions.size() == 2 &&
              actions_at_one_node.value->boundary_attachments.size() == 2,
          "multiple actions at one node are not merged");

    ModelPackV2 other = pack;
    other.model_pack_id = "framework.demo.alt";
    other.model_pack_version = "2.0.0";
    other.observed_sha256 = sha256_hex("framework.demo.alt.bytes");
    other.rules.front().emits.front().certainty = Certainty::Unknown;
    const auto forward = execute_model_packs_v2(
        {pack, other}, index, index_sha256);
    const auto reverse = execute_model_packs_v2(
        {other, pack}, index, index_sha256);
    check(forward.value.has_value() && reverse.value.has_value() &&
              canonical_model_fact_overlay_json(*forward.value) ==
                  canonical_model_fact_overlay_json(*reverse.value),
          "pack order permutation is byte-identical");
    if (forward.value) {
        check(forward.value->boundary_attachments.front().certainty ==
                  Certainty::Unknown &&
                  forward.value->external_actions.front().provenance.size() == 2,
              "multi-pack union preserves provenance and only downgrades certainty");
    }

    ModelPackV2 instruction_order = pack;
    instruction_order.model_pack_id = "framework.order";
    instruction_order.observed_sha256 = sha256_hex("framework.order.bytes");
    instruction_order.selectors.push_back(ModelSelectorV2{
        "selector.usr", ModelSelectorKind::ExactUsr, "usr.demo.ingest",
        std::nullopt, {}, std::nullopt, false});
    ModelRuleV2 second_rule = instruction_order.rules.front();
    second_rule.rule_id = "rule.boundary.second";
    second_rule.matches.front().match_id = "match.ingest.second";
    second_rule.matches.front().selector_ref = "selector.usr";
    second_rule.captures.front().capture_id = "capture.argument.second";
    second_rule.captures.front().match_ref = "match.ingest.second";
    second_rule.emits.front().emit_id = "emit.boundary.second";
    second_rule.emits.front().source_capture_ref = "capture.argument.second";
    instruction_order.rules.push_back(std::move(second_rule));
    ModelPackV2 reversed_instruction_order = instruction_order;
    std::reverse(
        reversed_instruction_order.selectors.begin(),
        reversed_instruction_order.selectors.end());
    std::reverse(
        reversed_instruction_order.rules.begin(),
        reversed_instruction_order.rules.end());
    reversed_instruction_order.observed_sha256 =
        sha256_hex("same semantics with reordered JSON bytes");
    const auto canonical_order =
        execute_model_pack_v2(instruction_order, index, index_sha256);
    const auto reversed_order =
        execute_model_pack_v2(
            reversed_instruction_order, index, index_sha256);
    check(canonical_order.value.has_value() &&
              reversed_order.value.has_value() &&
              canonical_model_fact_overlay_json(*canonical_order.value) ==
                  canonical_model_fact_overlay_json(*reversed_order.value),
          "selector/rule instruction order permutation is byte-identical");

    ModelPackV2 conflicting = pack;
    conflicting.observed_sha256 = sha256_hex("different bytes");
    conflicting.rules.front().emits.front().transfer_relation =
        "different_semantics";
    ++adversarial_checks;
    check(execute_model_packs_v2(
              {pack, conflicting}, index, index_sha256).status ==
              StageStatus::Failed,
          "same identity with conflicting bytes fails closed");

    ModelPackV2 exhausted = pack;
    exhausted.resource_limits.max_capture_values = 1;
    exhausted.resource_limits.max_emitted_facts = 1;
    const auto limited = execute_model_pack_v2(
        exhausted, two_calls, two_calls_sha256);
    ++adversarial_checks;
    check(limited.value.has_value() &&
              limited.status == StageStatus::ConservativeIncomplete &&
              !limited.value->unknown_outcomes.empty() &&
              std::any_of(
                  limited.value->resource_ledger.begin(),
                  limited.value->resource_ledger.end(),
                  [](const ModelResourceLedgerEntry &entry) {
                      return !entry.complete;
                  }),
          "resource exhaustion is explicit UNKNOWN with incomplete ledger");

    ModelPackV2 wrong_projection = pack;
    wrong_projection.rules.front().captures.front().index = 99;
    const auto projection_unknown =
        execute_model_pack_v2(wrong_projection, index, index_sha256);
    ++adversarial_checks;
    check(projection_unknown.value.has_value() &&
              projection_unknown.status ==
                  StageStatus::ConservativeIncomplete &&
              projection_unknown.value->boundary_attachments.empty() &&
              !projection_unknown.value->unknown_outcomes.empty(),
          "runtime out-of-range projection is explicit UNKNOWN");

    ++adversarial_checks;
    check(execute_model_pack_v2(pack, index, "not-a-sha").status ==
              StageStatus::Failed,
          "missing exact semantic index content digest fails closed");
}

}  // namespace

int main() {
    loader_tests();
    validator_adversarial_tests();
    execution_tests();
    check(adversarial_checks >= 20,
          "at least twenty adversarial cases executed");
    if (failures != 0) {
        std::cerr << failures << " failure(s), " << adversarial_checks
                  << " adversarial checks\n";
        return 1;
    }
    std::cout << "model VM smoke PASS: " << adversarial_checks
              << " adversarial checks\n";
    return 0;
}
