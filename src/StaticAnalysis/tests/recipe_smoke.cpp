#include "rift/core/recipe.h"

#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace {

using namespace rift::core;

void require(bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        std::exit(1);
    }
}

ValueType boolean_type() {
    ValueType type;
    type.kind = ValueKind::Boolean;
    type.canonical = "bool";
    return type;
}

ValueType integer_type(
    std::uint32_t width, bool is_signed,
    ValueKind kind = ValueKind::Integer,
    std::string canonical = {}) {
    ValueType type;
    type.kind = kind;
    type.canonical = canonical.empty()
                         ? (is_signed ? "signed-int" : "unsigned-int")
                         : std::move(canonical);
    type.bit_width = width;
    type.is_signed = is_signed;
    return type;
}

ExpressionStructure reference(std::string selector, const ValueType &type) {
    ExpressionStructure expression;
    expression.node_kind = "reference";
    expression.value_type = type;
    expression.referenced_selector_id = std::move(selector);
    return expression;
}

ExpressionStructure integer_literal(std::string value, const ValueType &type) {
    ExpressionStructure expression;
    expression.node_kind = "literal";
    expression.value_type = type;
    expression.literal = LiteralValue{LiteralKind::Integer, std::move(value)};
    return expression;
}

ExpressionStructure cast(
    ExpressionStructure operand, const ValueType &target) {
    ExpressionStructure expression;
    expression.node_kind = "cast";
    expression.operation = "integral_cast";
    expression.value_type = target;
    expression.operands.push_back(std::move(operand));
    return expression;
}

ExpressionStructure binary(
    std::string operation, ExpressionStructure left,
    ExpressionStructure right, const ValueType &type) {
    ExpressionStructure expression;
    expression.node_kind = "binary";
    expression.operation = std::move(operation);
    expression.value_type = type;
    expression.operands = {std::move(left), std::move(right)};
    return expression;
}

ExpressionStructure compare(
    std::string operation, ExpressionStructure left,
    ExpressionStructure right) {
    ExpressionStructure expression;
    expression.node_kind = "comparison";
    expression.operation = std::move(operation);
    expression.value_type = boolean_type();
    expression.operands = {std::move(left), std::move(right)};
    return expression;
}

ExpressionStructure boolean_expression(
    std::string operation, ExpressionStructure left,
    ExpressionStructure right) {
    ExpressionStructure expression;
    expression.node_kind = "boolean";
    expression.operation = std::move(operation);
    expression.value_type = boolean_type();
    expression.operands = {std::move(left), std::move(right)};
    return expression;
}

TypedPropertyIr property(
    std::string ap_id, std::string selector_id,
    ExpressionStructure predicate, ValueType ap_type = boolean_type()) {
    TypedPropertyIr result;
    result.schema_version = "2.0.0";
    result.artifact_id = "property.neutral";
    result.artifact_sha256 = std::string(64, '1');
    result.property_id = "property.neutral";
    result.logic = "MITL";
    result.time_domain = "dense";
    result.formula_text = "F_[0,10] p";
    result.formula.node_id = "formula.root";
    result.formula.operation = FormulaOperator::Eventually;
    result.formula.interval = TimeInterval{
        0.0, 10.0, false, true, false, "ms", {}};
    FormulaNode atom;
    atom.node_id = "formula.atom";
    atom.operation = FormulaOperator::Atom;
    atom.ap_id = ap_id;
    result.formula.operands.push_back(atom);
    AtomicProposition ap;
    ap.ap_id = std::move(ap_id);
    ap.roles = {ApRole::State};
    ap.value_type = std::move(ap_type);
    ap.predicate = std::move(predicate);
    result.atomic_propositions.push_back(std::move(ap));
    Selector selector;
    selector.selector_id = std::move(selector_id);
    selector.kind = SelectorKind::ExpressionStructure;
    selector.expression = result.atomic_propositions.front().predicate;
    result.selectors.push_back(std::move(selector));
    return result;
}

ExternalAction action(
    std::string action_id, std::string payload_slot,
    const ValueType &payload_type, std::string operation = "set") {
    ExternalAction result;
    result.external_action_id = std::move(action_id);
    result.action_schema_id = "action-schema.scalar";
    result.action_class = "scalar_input";
    result.channel = "fixture-channel";
    result.operation = std::move(operation);
    result.payload_type = payload_type;
    result.payload_slot = std::move(payload_slot);
    result.scope_schema = "scope-key";
    result.generation_schema = "generation-key";
    result.timing_capability = "interval";
    result.required_capability = "DIRECT";
    return result;
}

ModelValueTransferV2 identity_value_transfer() {
    ModelValueTransferV2 transfer;
    transfer.kind = ModelValueTransferKind::Identity;
    transfer.precondition = ModelValuePrecondition::None;
    transfer.executor_enforces_precondition = false;
    transfer.failure_branch_unknown = false;
    return transfer;
}

FrontierCandidate candidate(
    std::string candidate_id, std::string ap_id,
    ExternalAction external_action) {
    FrontierCandidate result;
    result.candidate_id = std::move(candidate_id);
    result.action = std::move(external_action);
    result.cone_id = "cone.neutral";
    result.ap_id = std::move(ap_id);
    result.disposition = FrontierDisposition::Actionable;
    result.evidence.reachability = ReachabilityVerdict::ModelledWitness;
    result.evidence.controllability = ControllabilityVerdict::Direct;
    result.evidence.path_feasibility =
        PathFeasibilityVerdict::NotEvaluated;
    result.evidence.mutation_semantics =
        MutationSemanticsVerdict::NotEvaluated;
    result.evidence.runtime_evidence =
        RuntimeEvidenceVerdict::NotEvaluated;
    result.evidence.completeness.model_vm_complete = true;
    result.evidence.completeness.attachment_enumeration_complete = true;
    result.evidence.completeness.forward_enumeration_complete = true;
    result.evidence.completeness.cone_complete = true;
    result.evidence.completeness.compatibility_complete = true;
    return result;
}

FrontierPathStep graph_step(
    const std::string &edge_id, const std::string &source,
    const std::string &target) {
    FrontierPathStep step;
    step.kind = FrontierPathStepKind::GraphEdge;
    step.source_node_id = source;
    step.target_node_id = target;
    step.graph_edge_id = edge_id;
    return step;
}

FrontierPathStep model_step(
    const std::string &fact_id, const std::string &source,
    const std::string &target) {
    FrontierPathStep step;
    step.kind = FrontierPathStepKind::ModelArc;
    step.source_node_id = source;
    step.target_node_id = target;
    step.model_fact_id = fact_id;
    return step;
}

FrontierPathExemplar path_exemplar(
    const std::string &meet, const std::string &root,
    std::vector<FrontierPathStep> forward_steps,
    std::vector<FrontierPathStep> root_steps = {},
    const ReachabilityVerdict reachability =
        ReachabilityVerdict::StaticWitness) {
    FrontierPathExemplar exemplar;
    exemplar.meet_node_id = meet;
    exemplar.root_node_id = root;
    exemplar.effective_path_class =
        reachability == ReachabilityVerdict::ModelledWitness
        ? FrontierPathClass::Modelled
        : FrontierPathClass::Static;
    exemplar.raw_forward_path_class = exemplar.effective_path_class;
    exemplar.raw_root_path_class = FrontierPathClass::Static;
    exemplar.compatibility = WitnessCompatibility::Compatible;
    exemplar.reachability = reachability;
    exemplar.forward_steps = std::move(forward_steps);
    exemplar.root_steps = std::move(root_steps);
    return exemplar;
}

struct Fixture {
    TypedPropertyIr typed_property;
    ApBindings bindings;
    ContextualInfluenceGraph graph;
    ApInfluenceCones cones;
    FrontierCandidates frontier;
    ModelFactOverlay overlay;
    PredicateOccurrenceBindings predicate_occurrences;
    RecipeInputDigests digests{
        std::string(64, 'a'), std::string(64, 'b'), std::string(64, 'c'),
        std::string(64, 'd'), std::string(64, 'e'), std::string(64, 'f'),
        std::string(64, '7')};
    RecipeOptions options;
};

Fixture fixture_for(
    const ValueType &payload_type, ExpressionStructure predicate,
    std::string selector_id = "selector.value",
    std::string ap_id = "ap.value",
    std::string action_id = "action.value") {
    Fixture fixture;
    fixture.typed_property = property(
        ap_id, selector_id, std::move(predicate));
    ExternalAction external_action = action(
        action_id, "payload.scalar", payload_type);
    fixture.bindings.schema_version = "2.0.0";
    fixture.bindings.artifact_id = "bindings.neutral";
    fixture.bindings.property_ir_sha256 = fixture.digests.property_ir_sha256;
    fixture.bindings.semantic_index_sha256 = std::string(64, '9');
    fixture.bindings.status = StageStatus::Complete;
    ApRoleBinding role_binding;
    role_binding.ap_id = ap_id;
    role_binding.role = ApRole::State;
    role_binding.resolution = BindingResolution::Confirmed;
    BindingCandidate binding;
    binding.binding_id = "binding.value";
    binding.status = CandidateStatus::Confirmed;
    binding.selector_ids = {selector_id};
    binding.semantic_node_ids = {"semantic.root"};
    role_binding.candidates.push_back(binding);
    fixture.bindings.bindings.push_back(role_binding);

    fixture.graph.artifact_id = "graph.neutral";
    fixture.graph.semantic_index_sha256 = std::string(64, '9');
    fixture.graph.status = StageStatus::Complete;
    ContextualNode boundary_node;
    boundary_node.node_id = "context.boundary";
    boundary_node.semantic_node_id = "semantic.boundary";
    boundary_node.kind = SemanticNodeKind::Value;
    boundary_node.value_type = payload_type;
    ContextualNode root_node;
    root_node.node_id = "context.root";
    root_node.semantic_node_id = "semantic.root";
    root_node.kind = SemanticNodeKind::Value;
    root_node.value_type = payload_type;
    fixture.graph.nodes = {boundary_node, root_node};
    InfluenceEdge value_edge;
    value_edge.edge_id = "edge.value";
    value_edge.source_node_id = boundary_node.node_id;
    value_edge.target_node_id = root_node.node_id;
    value_edge.kind = RelationKind::Defines;
    value_edge.certainty = Certainty::May;
    fixture.graph.edges.push_back(value_edge);

    fixture.cones.artifact_id = "cones.neutral";
    fixture.cones.ap_bindings_sha256 = fixture.digests.ap_bindings_sha256;
    fixture.cones.graph_sha256 = fixture.digests.graph_sha256;
    fixture.cones.candidate_accounting_complete = true;
    fixture.cones.ranking_never_prunes = true;
    fixture.cones.status = StageStatus::Complete;
    ApInfluenceCone cone;
    cone.cone_id = "cone.neutral";
    cone.ap_id = ap_id;
    cone.roles = {ApRole::State};
    cone.status = StageStatus::Complete;
    CandidateAccount account;
    account.binding_id = binding.binding_id;
    account.disposition = CandidateDisposition::Included;
    account.root_node_ids = {root_node.node_id};
    cone.candidate_accounting.push_back(account);
    fixture.cones.cones.push_back(cone);

    fixture.frontier.schema_version = "3.0.0";
    fixture.frontier.artifact_id = "frontier.neutral";
    fixture.frontier.input_digests.model_fact_overlay_sha256 =
        fixture.digests.model_fact_overlay_sha256;
    fixture.frontier.input_digests.graph_sha256 = fixture.digests.graph_sha256;
    fixture.frontier.input_digests.cones_sha256 = fixture.digests.cones_sha256;
    fixture.frontier.candidate_accounting_complete = true;
    fixture.frontier.ranking_never_prunes = true;
    fixture.frontier.status = StageStatus::Complete;
    FrontierCandidate frontier_candidate = candidate(
        "candidate.value", ap_id, external_action);
    FrontierWitness value_witness;
    value_witness.witness_id = "witness.value-path";
    value_witness.attachment_id = "attachment.value";
    value_witness.boundary_node_id = boundary_node.node_id;
    value_witness.path_exemplars.push_back(path_exemplar(
        root_node.node_id, root_node.node_id,
        {graph_step(
            value_edge.edge_id, boundary_node.node_id,
            root_node.node_id)}));
    value_witness.compatibility = WitnessCompatibility::Compatible;
    value_witness.reachability = ReachabilityVerdict::StaticWitness;
    frontier_candidate.witnesses.push_back(value_witness);
    fixture.frontier.candidates.push_back(std::move(frontier_candidate));
    fixture.overlay.artifact_id = "overlay.neutral";
    fixture.overlay.semantic_index_artifact_id = "index.neutral";
    fixture.overlay.semantic_index_identity = std::string(64, 'e');
    fixture.overlay.status = StageStatus::Complete;
    fixture.overlay.external_actions.push_back(std::move(external_action));
    BoundaryAttachment value_attachment;
    value_attachment.attachment_id = "attachment.value";
    value_attachment.external_action_id =
        fixture.overlay.external_actions.front().external_action_id;
    value_attachment.semantic_node_id = boundary_node.semantic_node_id;
    value_attachment.transfer_relation = "payload_to_value";
    value_attachment.certainty = Certainty::Modelled;
    value_attachment.value_transfer = identity_value_transfer();
    fixture.overlay.boundary_attachments.push_back(
        std::move(value_attachment));
    fixture.predicate_occurrences.artifact_id = "occurrences.neutral";
    fixture.predicate_occurrences.property_ir_sha256 =
        fixture.digests.property_ir_sha256;
    fixture.predicate_occurrences.semantic_index_sha256 =
        fixture.bindings.semantic_index_sha256;
    fixture.predicate_occurrences.canonical_compilation_database_sha256 =
        std::string(64, '8');
    fixture.predicate_occurrences.path_map_sha256 = std::string(64, '6');
    fixture.predicate_occurrences.status = StageStatus::Complete;
    fixture.options.analyzer_core_sha256 = std::string(64, '0');
    fixture.options.solver_timeout_ms = 1000;
    return fixture;
}

MutationRecipes run(Fixture &fixture) {
    MutationRecipes recipes = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    const std::vector<std::string> errors = validate_mutation_recipes(
        recipes, fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier,
        fixture.overlay, fixture.predicate_occurrences, fixture.digests,
        fixture.options);
    if (!errors.empty()) {
        for (const std::string &error : errors) {
            std::cerr << "VALIDATION " << error << '\n';
        }
    }
    require(errors.empty(), "recipe artifact validates");
    require(recipes.recipes.size() == 1, "one actionable candidate is retained");
    return recipes;
}

bool has_value(const ActionMutation &mutation, const std::string &value) {
    return std::any_of(
        mutation.suggested_values.begin(), mutation.suggested_values.end(),
        [&](const MutationValue &candidate_value) {
            return candidate_value.canonical == value;
        });
}

void add_second_exact_action(
    Fixture &fixture, const ValueType &type,
    const std::string &second_action_id = "action.second") {
    const std::string ap_id =
        fixture.typed_property.atomic_propositions.front().ap_id;
    Selector selector;
    selector.selector_id = "selector.second";
    selector.kind = SelectorKind::TypedFieldPath;
    selector.value_type = type;
    selector.field_path = {"second"};
    fixture.typed_property.selectors.push_back(selector);

    BindingCandidate binding;
    binding.binding_id = "binding.second";
    binding.status = CandidateStatus::Confirmed;
    binding.selector_ids = {selector.selector_id};
    binding.semantic_node_ids = {"semantic.second-root"};
    fixture.bindings.bindings.front().candidates.push_back(binding);

    ContextualNode boundary;
    boundary.node_id = "context.second-boundary";
    boundary.semantic_node_id = "semantic.second-boundary";
    boundary.kind = SemanticNodeKind::Value;
    boundary.value_type = type;
    ContextualNode root;
    root.node_id = "context.second-root";
    root.semantic_node_id = "semantic.second-root";
    root.kind = SemanticNodeKind::Value;
    root.value_type = type;
    fixture.graph.nodes.push_back(boundary);
    fixture.graph.nodes.push_back(root);
    InfluenceEdge edge;
    edge.edge_id = "edge.second";
    edge.source_node_id = boundary.node_id;
    edge.target_node_id = root.node_id;
    edge.kind = RelationKind::Defines;
    edge.certainty = Certainty::May;
    fixture.graph.edges.push_back(edge);

    CandidateAccount account;
    account.binding_id = binding.binding_id;
    account.disposition = CandidateDisposition::Included;
    account.root_node_ids = {root.node_id};
    fixture.cones.cones.front().candidate_accounting.push_back(account);

    ExternalAction second = action(
        second_action_id, "payload.second", type);
    if (std::none_of(
            fixture.overlay.external_actions.begin(),
            fixture.overlay.external_actions.end(),
            [&](const ExternalAction &item) {
                return item.external_action_id == second.external_action_id;
            })) {
        fixture.overlay.external_actions.push_back(second);
    } else {
        second = fixture.overlay.external_actions.front();
    }
    fixture.overlay.boundary_attachments.push_back({
        "attachment.second", second.external_action_id,
        boundary.semantic_node_id, "payload_to_value",
        Certainty::Modelled, {}, identity_value_transfer()});
    FrontierCandidate second_candidate = candidate(
        "candidate.second", ap_id, second);
    FrontierWitness witness;
    witness.witness_id = "witness.second";
    witness.attachment_id = "attachment.second";
    witness.boundary_node_id = boundary.node_id;
    witness.path_exemplars.push_back(path_exemplar(
        root.node_id, root.node_id,
        {graph_step(edge.edge_id, boundary.node_id, root.node_id)}));
    witness.compatibility = WitnessCompatibility::Compatible;
    witness.reachability = ReachabilityVerdict::StaticWitness;
    second_candidate.witnesses.push_back(witness);
    fixture.frontier.candidates.push_back(std::move(second_candidate));

    const auto occurrence = [&] (
        std::string occurrence_id, std::string selector_id,
        std::string semantic_node_id, std::string predicate_path) {
        PredicateOccurrence result;
        result.occurrence_id = std::move(occurrence_id);
        result.ap_id = ap_id;
        result.selector_id = std::move(selector_id);
        result.roles = {ApRole::State};
        result.predicate_paths = {std::move(predicate_path)};
        result.translation_unit_id = "tu.neutral";
        result.kind = PredicateOccurrenceKind::DeclRef;
        result.referenced_usr = "usr:" + result.selector_id;
        result.referenced_entity_id = "entity:" + result.selector_id;
        result.semantic_node_ids = {std::move(semantic_node_id)};
        result.value_type = type;
        result.certainty = Certainty::Must;
        result.resolution = PredicateOccurrenceResolution::Exact;
        return result;
    };
    fixture.predicate_occurrences.occurrences = {
        occurrence(
            "occurrence.first", "selector.value", "semantic.root",
            "predicate.operands[0].operands[0]"),
        occurrence(
            "occurrence.second", "selector.second",
            "semantic.second-root",
            "predicate.operands[1].operands[0]")};
    fixture.predicate_occurrences.observed_occurrences = 2;
    fixture.predicate_occurrences.selector_accounts.clear();
    for (const PredicateOccurrence &item :
         fixture.predicate_occurrences.occurrences) {
        PredicateSelectorAccount account_item;
        account_item.ap_id = item.ap_id;
        account_item.selector_id = item.selector_id;
        account_item.roles = item.roles;
        account_item.predicate_paths = item.predicate_paths;
        account_item.expected_value_type = type;
        account_item.occurrence_ids = {item.occurrence_id};
        account_item.resolution = PredicateOccurrenceResolution::Exact;
        fixture.predicate_occurrences.selector_accounts.push_back(
            std::move(account_item));
    }
}

void retarget_witness_to_confirmed_ap_site(
    Fixture &fixture, RelationKind relation = RelationKind::Data) {
    const std::string ap_id =
        fixture.typed_property.atomic_propositions.front().ap_id;

    Selector site_selector;
    site_selector.selector_id = "selector.ap-site";
    site_selector.kind = SelectorKind::SourceLocation;
    fixture.typed_property.selectors.push_back(site_selector);
    fixture.typed_property.atomic_propositions.front().roles.push_back(
        ApRole::Guard);
    RoleSelectorGroup site_group;
    site_group.group_id = "group.ap-site";
    site_group.role = ApRole::Guard;
    site_group.selector_ids = {site_selector.selector_id};
    fixture.typed_property.atomic_propositions.front()
        .role_selector_groups.push_back(site_group);

    ContextualNode site_root;
    site_root.node_id = "context.ap-site";
    site_root.semantic_node_id = "semantic.ap-site";
    site_root.kind = SemanticNodeKind::Value;
    site_root.value_type = boolean_type();
    fixture.graph.nodes.push_back(site_root);
    fixture.graph.edges.front().target_node_id = site_root.node_id;
    fixture.graph.edges.front().kind = relation;

    ApRoleBinding site_role;
    site_role.ap_id = ap_id;
    site_role.role = ApRole::Guard;
    site_role.resolution = BindingResolution::Confirmed;
    BindingCandidate site_binding;
    site_binding.binding_id = "binding.ap-site";
    site_binding.status = CandidateStatus::Confirmed;
    site_binding.selector_group_id = site_group.group_id;
    site_binding.selector_ids = {site_selector.selector_id};
    site_binding.semantic_node_ids = {site_root.semantic_node_id};
    site_role.candidates.push_back(site_binding);
    fixture.bindings.bindings.push_back(site_role);

    fixture.cones.cones.front().roles.push_back(ApRole::Guard);
    CandidateAccount site_account;
    site_account.binding_id = site_binding.binding_id;
    site_account.disposition = CandidateDisposition::Included;
    site_account.root_node_ids = {site_root.node_id};
    fixture.cones.cones.front().candidate_accounting.push_back(site_account);

    FrontierWitness &witness =
        fixture.frontier.candidates.front().witnesses.front();
    witness.path_exemplars = {path_exemplar(
        site_root.node_id, site_root.node_id,
        {graph_step(
            fixture.graph.edges.front().edge_id,
            witness.boundary_node_id, site_root.node_id)})};
}

void test_signed_boundary_and_direction() {
    const ValueType type = integer_type(8, true, ValueKind::Integer, "signed char");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("10", type)));
    MutationRecipes recipes = run(fixture);
    const MutationRecipe &recipe = recipes.recipes.front();
    require(recipe.status == RecipeStatus::Supported,
            "typed identity witness supports an external mutation recipe");
    require(recipe.solver_query.outcome == SolverOutcome::Sat, "signed comparison has SAT pair");
    require(recipe.direction_query &&
                recipe.direction_query->outcome == SolverOutcome::Unsat,
            "monotone-up claim has UNSAT opposite-direction proof");
    require(recipe.action_mutations.front().direction == MutationDirection::MonotoneUp,
            "signed comparison direction is proven up");
    require(fixture.frontier.candidates.front().action.payload_slot !=
                "selector.value",
            "portable action payload slot does not contain a Property selector ID");
    require(has_value(recipe.action_mutations.front(), "-128") &&
                has_value(recipe.action_mutations.front(), "9") &&
                has_value(recipe.action_mutations.front(), "10") &&
                has_value(recipe.action_mutations.front(), "11") &&
                has_value(recipe.action_mutations.front(), "127"),
            "signed boundary set preserves declared width");
    require(recipe.timing.status == TimingStatus::WidenedUnknown &&
                !recipe.timing.uncertainty_reasons.empty(),
            "missing clock details widen timing rather than invent precision");
}

void test_integral_promotions() {
    const ValueType signed_byte = integer_type(8, true, ValueKind::Integer, "signed char");
    const ValueType unsigned_byte = integer_type(8, false, ValueKind::Integer, "unsigned char");
    const ValueType promoted = integer_type(32, true, ValueKind::Integer, "int");
    Fixture signed_fixture = fixture_for(
        signed_byte,
        compare(">=", cast(reference("selector.value", signed_byte), promoted),
                integer_literal("0", promoted)));
    Fixture unsigned_fixture = fixture_for(
        unsigned_byte,
        compare(">", cast(reference("selector.value", unsigned_byte), promoted),
                integer_literal("200", promoted)));
    require(run(signed_fixture).recipes.front().solver_query.outcome == SolverOutcome::Sat,
            "signed integral promotion is encoded");
    require(run(unsigned_fixture).recipes.front().solver_query.outcome == SolverOutcome::Sat,
            "unsigned-byte to signed-int promotion is zero-extended");
}

void test_signed_ub_vs_unsigned_wrap() {
    const ValueType signed_type = integer_type(32, true, ValueKind::Integer, "int");
    const ValueType unsigned_type = integer_type(32, false, ValueKind::Integer, "unsigned int");
    ExpressionStructure signed_add = binary(
        "+", reference("selector.value", signed_type),
        integer_literal("1", signed_type), signed_type);
    ExpressionStructure unsigned_add = binary(
        "+", reference("selector.value", unsigned_type),
        integer_literal("1", unsigned_type), unsigned_type);
    Fixture signed_fixture = fixture_for(
        signed_type,
        compare(">", std::move(signed_add),
                reference("selector.value", signed_type)));
    Fixture unsigned_fixture = fixture_for(
        unsigned_type,
        compare(">", std::move(unsigned_add),
                reference("selector.value", unsigned_type)));
    MutationRecipes signed_recipes = run(signed_fixture);
    MutationRecipes unsigned_recipes = run(unsigned_fixture);
    require(signed_recipes.recipes.front().solver_query.outcome == SolverOutcome::Unsat,
            "signed overflow is excluded as UB, leaving no truth flip");
    require(unsigned_recipes.recipes.front().solver_query.outcome == SolverOutcome::Sat,
            "unsigned wrap is preserved and exposes boundary truth flip");
}

void test_bool_enum_and_bitmask() {
    Fixture boolean_fixture = fixture_for(
        boolean_type(), reference("selector.value", boolean_type()));
    MutationRecipes boolean_recipes = run(boolean_fixture);
    require(boolean_recipes.recipes.front().action_mutations.front().mutation_kind ==
                MutationKind::BooleanToggle &&
                has_value(boolean_recipes.recipes.front().action_mutations.front(), "false") &&
                has_value(boolean_recipes.recipes.front().action_mutations.front(), "true"),
            "Boolean predicate emits explicit toggle values");

    const ValueType enumeration = integer_type(
        8, false, ValueKind::Enumeration, "Mode");
    Fixture enum_fixture = fixture_for(
        enumeration,
        compare("==", reference("selector.value", enumeration),
                integer_literal("3", enumeration)));
    MutationRecipes enum_recipes = run(enum_fixture);
    require(enum_recipes.recipes.front().action_mutations.front().mutation_kind ==
                MutationKind::EnumAlternative,
            "enum equality retains enum mutation class");

    const ValueType bits = integer_type(
        8, false, ValueKind::BitVector, "flags8");
    ExpressionStructure masked = binary(
        "&", reference("selector.value", bits), integer_literal("12", bits), bits);
    Fixture bitmask_fixture = fixture_for(
        bits, compare("==", std::move(masked), integer_literal("4", bits)));
    MutationRecipes bitmask_recipes = run(bitmask_fixture);
    require(bitmask_recipes.recipes.front().action_mutations.front().mutation_kind ==
                MutationKind::BitmaskBoundary,
            "bitmask predicate emits bitmask boundary class");
    require(bitmask_recipes.recipes.front().action_mutations.front().direction ==
                MutationDirection::BoundarySet,
            "bitmask does not make an unproved monotone claim");
}

void test_nonlinear_and_solver_budget_are_total_unknown() {
    const ValueType type = integer_type(16, true, ValueKind::Integer, "short");
    ExpressionStructure nonlinear = binary(
        "*", reference("selector.value", type),
        reference("selector.value", type), type);
    Fixture nonlinear_fixture = fixture_for(
        type, compare(">", std::move(nonlinear), integer_literal("4", type)));
    MutationRecipes nonlinear_recipes = run(nonlinear_fixture);
    require(nonlinear_recipes.recipes.front().status == RecipeStatus::Unknown &&
                nonlinear_recipes.recipes.front().solver_query.outcome ==
                    SolverOutcome::Unsupported,
            "nonlinear expression abstains without deleting candidate");

    Fixture exhausted_truth_budget = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("4", type)));
    exhausted_truth_budget.options.max_solver_queries = 0;
    MutationRecipes no_truth_query = run(exhausted_truth_budget);
    require(no_truth_query.recipes.size() == 1 &&
                no_truth_query.recipes.front().status ==
                    RecipeStatus::Unknown &&
                no_truth_query.recipes.front().solver_query.outcome ==
                    SolverOutcome::NotRun,
            "exhausted budget records an unexecuted truth query as NOT_RUN");

    Fixture exhausted_direction_budget = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("4", type)));
    exhausted_direction_budget.options.max_solver_queries = 1;
    MutationRecipes no_direction_query = run(exhausted_direction_budget);
    const MutationRecipe &direction_unknown =
        no_direction_query.recipes.front();
    require(direction_unknown.solver_query.outcome == SolverOutcome::Sat &&
                direction_unknown.direction_query &&
                direction_unknown.direction_query->outcome ==
                    SolverOutcome::NotRun &&
                direction_unknown.status == RecipeStatus::Unknown &&
                direction_unknown.action_mutations.front().mutation_kind ==
                    MutationKind::Unknown &&
                direction_unknown.action_mutations.front().direction ==
                    MutationDirection::Unknown &&
                !direction_unknown.action_mutations.front()
                     .unknown_reasons.empty(),
            "unexecuted direction proof cannot leak a SUPPORTED status or direction claim");
    require(no_direction_query.solver_contract.max_queries == 1,
            "solver contract exposes the effective query budget");
    const std::string no_direction_digest = sha256_hex(
        canonical_mutation_recipes_json(no_direction_query));
    const RecipeReplayObligations no_direction_replay =
        build_recipe_replay_obligations(
            no_direction_query, no_direction_digest);
    require(
        no_direction_replay.obligations.size() == 1 &&
            no_direction_replay.obligations.front().status ==
                ReplayStatus::Unknown &&
            no_direction_replay.obligations.front().expected_relation ==
                ReplayExpectedRelation::Unknown,
        "an incomplete direction proof cannot create an actionable replay obligation");

    ValueType floating;
    floating.kind = ValueKind::Floating;
    floating.canonical = "double";
    floating.bit_width = 64;
    Fixture floating_fixture = fixture_for(
        floating, reference("selector.value", floating));
    MutationRecipes floating_recipes = run(floating_fixture);
    require(floating_recipes.recipes.front().status == RecipeStatus::Unknown &&
                floating_recipes.recipes.front().solver_query.outcome ==
                    SolverOutcome::Unsupported,
            "incomplete IEEE-754/NaN semantics abstain without deletion");
}

void test_single_reference_ap_site_fallback_is_value_only() {
    const ValueType type = integer_type(
        16, true, ValueKind::Integer, "short");
    ExpressionStructure c_comparison = compare(
        ">", cast(reference("selector.value", type), type),
        integer_literal("9", type));
    c_comparison.value_type = type;
    Fixture data_fixture = fixture_for(
        type, std::move(c_comparison), "selector.value", "ap.value",
        "action.value");
    data_fixture.typed_property.atomic_propositions.front().value_type = type;
    retarget_witness_to_confirmed_ap_site(data_fixture);
    MutationRecipes data_recipes = run(data_fixture);
    const MutationRecipe &data_recipe = data_recipes.recipes.front();
    require(data_recipe.status == RecipeStatus::Heuristic &&
                data_recipe.solver_query.outcome == SolverOutcome::Sat &&
                data_recipe.direction_query &&
                data_recipe.direction_query->outcome ==
                    SolverOutcome::Unsat &&
                data_recipe.action_mutations.front().direction ==
                    MutationDirection::Unknown &&
                data_recipe.action_mutations.front().suggested_values.empty(),
            "a non-identity value path binds the sole selector but withholds an external payload direction");

    const ValueType c_int = integer_type(
        32, true, ValueKind::Integer, "int");
    Fixture c_truth_fixture = fixture_for(
        type,
        cast(
            compare(
                ">", reference("selector.value", type),
                integer_literal("9", type)),
            c_int));
    retarget_witness_to_confirmed_ap_site(c_truth_fixture);
    MutationRecipes c_truth_recipes = run(c_truth_fixture);
    require(
        c_truth_recipes.recipes.front().solver_query.outcome ==
                SolverOutcome::Sat &&
            c_truth_recipes.recipes.front().direction_query &&
            c_truth_recipes.recipes.front().direction_query->outcome ==
                SolverOutcome::Unsat &&
            c_truth_recipes.recipes.front()
                    .action_mutations.front()
                    .direction == MutationDirection::Unknown,
        "C/C++ selector truth is solved locally without projecting through a generic data transform");

    Fixture control_fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("9", type)));
    retarget_witness_to_confirmed_ap_site(
        control_fixture, RelationKind::Control);
    MutationRecipes control_recipes = run(control_fixture);
    require(control_recipes.recipes.front().status ==
                RecipeStatus::Unknown &&
                control_recipes.recipes.front().solver_query.outcome ==
                    SolverOutcome::Unsupported,
            "a control-only path to the same AP site still cannot bind a value direction");

    ExpressionStructure ambiguous_predicate = compare(
        ">", reference("selector.value", type),
        reference("selector.bound", type));
    Fixture ambiguous_fixture = fixture_for(
        type, std::move(ambiguous_predicate));
    Selector bound_selector;
    bound_selector.selector_id = "selector.bound";
    bound_selector.kind = SelectorKind::TypedFieldPath;
    bound_selector.value_type = type;
    ambiguous_fixture.typed_property.selectors.push_back(bound_selector);
    retarget_witness_to_confirmed_ap_site(ambiguous_fixture);
    MutationRecipes ambiguous_recipes = run(ambiguous_fixture);
    require(ambiguous_recipes.recipes.front().status ==
                RecipeStatus::Unknown &&
                ambiguous_recipes.recipes.front().solver_query.outcome ==
                    SolverOutcome::Unsupported,
            "an AP-site path does not guess between multiple predicate references");
}

void test_two_roots_bind_two_dynamic_threshold_roles() {
    const ValueType type = integer_type(
        16, true, ValueKind::Integer, "short");
    ExpressionStructure predicate = compare(
        ">", reference("selector.observed", type),
        reference("selector.threshold", type));
    Fixture fixture = fixture_for(
        type, std::move(predicate), "selector.observed", "ap.dynamic",
        "action.observed");
    // The role binding intentionally identifies only graph roots; exact
    // predicate-operand identity comes from the additive occurrence sidecar.
    fixture.bindings.bindings.front().candidates.front().selector_ids.clear();

    Selector threshold_selector;
    threshold_selector.selector_id = "selector.threshold";
    threshold_selector.kind = SelectorKind::TypedFieldPath;
    threshold_selector.value_type = type;
    threshold_selector.field_path = {"threshold"};
    fixture.typed_property.selectors.push_back(threshold_selector);

    BindingCandidate threshold_binding;
    threshold_binding.binding_id = "binding.threshold";
    threshold_binding.status = CandidateStatus::Confirmed;
    threshold_binding.semantic_node_ids = {"semantic.threshold-root"};
    fixture.bindings.bindings.front().candidates.push_back(threshold_binding);

    ContextualNode threshold_boundary;
    threshold_boundary.node_id = "context.threshold-boundary";
    threshold_boundary.semantic_node_id = "semantic.threshold-boundary";
    threshold_boundary.kind = SemanticNodeKind::Value;
    threshold_boundary.value_type = type;
    ContextualNode threshold_root;
    threshold_root.node_id = "context.threshold-root";
    threshold_root.semantic_node_id = "semantic.threshold-root";
    threshold_root.kind = SemanticNodeKind::Value;
    threshold_root.value_type = type;
    fixture.graph.nodes.push_back(threshold_boundary);
    fixture.graph.nodes.push_back(threshold_root);
    InfluenceEdge threshold_edge;
    threshold_edge.edge_id = "edge.threshold-value";
    threshold_edge.source_node_id = threshold_boundary.node_id;
    threshold_edge.target_node_id = threshold_root.node_id;
    threshold_edge.kind = RelationKind::Defines;
    threshold_edge.certainty = Certainty::May;
    fixture.graph.edges.push_back(threshold_edge);

    CandidateAccount threshold_account;
    threshold_account.binding_id = threshold_binding.binding_id;
    threshold_account.disposition = CandidateDisposition::Included;
    threshold_account.root_node_ids = {threshold_root.node_id};
    fixture.cones.cones.front().candidate_accounting.push_back(
        threshold_account);

    ExternalAction threshold_action = action(
        "action.threshold", "payload.threshold", type);
    fixture.overlay.external_actions.push_back(threshold_action);
    BoundaryAttachment threshold_attachment;
    threshold_attachment.attachment_id = "attachment.threshold";
    threshold_attachment.external_action_id =
        threshold_action.external_action_id;
    threshold_attachment.semantic_node_id =
        threshold_boundary.semantic_node_id;
    threshold_attachment.transfer_relation = "payload_to_value";
    threshold_attachment.certainty = Certainty::Modelled;
    threshold_attachment.value_transfer = identity_value_transfer();
    fixture.overlay.boundary_attachments.push_back(
        std::move(threshold_attachment));
    FrontierCandidate threshold_candidate = candidate(
        "candidate.threshold", "ap.dynamic", threshold_action);
    FrontierWitness threshold_witness;
    threshold_witness.witness_id = "witness.threshold-value";
    threshold_witness.attachment_id = "attachment.threshold";
    threshold_witness.boundary_node_id = threshold_boundary.node_id;
    threshold_witness.path_exemplars.push_back(path_exemplar(
        threshold_root.node_id, threshold_root.node_id,
        {graph_step(
            threshold_edge.edge_id, threshold_boundary.node_id,
            threshold_root.node_id)}));
    threshold_witness.compatibility = WitnessCompatibility::Compatible;
    threshold_witness.reachability = ReachabilityVerdict::StaticWitness;
    threshold_candidate.witnesses.push_back(threshold_witness);
    fixture.frontier.candidates.push_back(std::move(threshold_candidate));

    const auto exact_occurrence = [&](
                                      std::string id,
                                      std::string selector,
                                      std::string semantic_node,
                                      std::string entity) {
        PredicateOccurrence occurrence;
        occurrence.occurrence_id = std::move(id);
        occurrence.ap_id = "ap.dynamic";
        occurrence.selector_id = std::move(selector);
        occurrence.roles = {ApRole::State};
        occurrence.predicate_paths = {"predicate.operands[0]"};
        occurrence.translation_unit_id = "tu.neutral";
        occurrence.kind = PredicateOccurrenceKind::DeclRef;
        occurrence.referenced_usr = "usr:" + entity;
        occurrence.referenced_entity_id = std::move(entity);
        occurrence.semantic_node_ids = {std::move(semantic_node)};
        occurrence.value_type = type;
        occurrence.certainty = Certainty::Must;
        occurrence.resolution = PredicateOccurrenceResolution::Exact;
        return occurrence;
    };
    fixture.predicate_occurrences.occurrences = {
        exact_occurrence(
            "occurrence.observed", "selector.observed", "semantic.root",
            "entity.observed"),
        exact_occurrence(
            "occurrence.threshold", "selector.threshold",
            "semantic.threshold-root", "entity.threshold")};
    fixture.predicate_occurrences.occurrences[1].predicate_paths = {
        "predicate.operands[1]"};
    fixture.predicate_occurrences.observed_occurrences = 2;
    for (const PredicateOccurrence &occurrence :
         fixture.predicate_occurrences.occurrences) {
        PredicateSelectorAccount account;
        account.ap_id = occurrence.ap_id;
        account.selector_id = occurrence.selector_id;
        account.roles = occurrence.roles;
        account.predicate_paths = occurrence.predicate_paths;
        account.occurrence_ids = {occurrence.occurrence_id};
        account.resolution = PredicateOccurrenceResolution::Exact;
        fixture.predicate_occurrences.selector_accounts.push_back(
            std::move(account));
    }

    MutationRecipes recipes = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    const std::vector<std::string> errors = validate_mutation_recipes(
        recipes, fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    require(errors.empty() && recipes.recipes.size() == 2,
            "two role roots produce two independently certified recipes");
    std::map<std::string, MutationDirection> directions;
    std::map<std::string, std::optional<std::string>> selectors;
    for (const MutationRecipe &recipe : recipes.recipes) {
        require(recipe.solver_query.outcome == SolverOutcome::Sat,
                "dynamic-threshold role has a SAT local truth-change pair");
        directions[recipe.frontier_candidate_id] =
            recipe.action_mutations.front().direction;
        selectors[recipe.frontier_candidate_id] =
            recipe.target_predicate_selector_id;
    }
    require(directions["candidate.value"] == MutationDirection::MonotoneUp,
            "observed-value root maps to increasing truth direction");
    require(directions["candidate.threshold"] == MutationDirection::MonotoneDown,
            "threshold root maps to decreasing truth direction");
    require(
        selectors["candidate.value"] ==
                std::optional<std::string>{"selector.observed"} &&
            selectors["candidate.threshold"] ==
                std::optional<std::string>{"selector.threshold"},
        "exact occurrence identities keep observed and dynamic-bound operands separate");

    fixture.predicate_occurrences.selector_accounts.front().resolution =
        PredicateOccurrenceResolution::Unknown;
    fixture.predicate_occurrences.selector_accounts.front()
        .uncertainty_reasons = {"translation_unit_resource_guard_reached"};
    MutationRecipes guarded = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    const auto guarded_observed = std::find_if(
        guarded.recipes.begin(), guarded.recipes.end(),
        [](const MutationRecipe &recipe) {
            return recipe.frontier_candidate_id == "candidate.value";
        });
    require(
        guarded_observed != guarded.recipes.end() &&
            guarded_observed->status == RecipeStatus::Unknown &&
            guarded_observed->solver_query.outcome ==
                SolverOutcome::Unsupported,
        "an UNKNOWN occurrence account can never leak an EXACT operand mapping");
}

void test_control_only_witness_does_not_map_value() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("3", type)));
    fixture.graph.edges.front().kind = RelationKind::Control;
    MutationRecipes recipes = run(fixture);
    const MutationRecipe &recipe = recipes.recipes.front();
    require(recipe.status == RecipeStatus::Unknown &&
                recipe.solver_query.outcome == SolverOutcome::Unsupported &&
                recipe.action_mutations.front().direction ==
                    MutationDirection::Unknown,
            "control-only influence never becomes a value mutation direction");
}

void test_modelled_identity_transfer_can_close_value_path() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare("==", reference("selector.value", type),
                      integer_literal("7", type)));
    fixture.graph.edges.clear();
    FrontierWitness &witness =
        fixture.frontier.candidates.front().witnesses.front();
    witness.reachability = ReachabilityVerdict::ModelledWitness;
    witness.path_exemplars = {path_exemplar(
        "context.root", "context.root",
        {model_step(
            "fact.identity", "context.boundary", "context.root")},
        {}, ReachabilityVerdict::ModelledWitness)};
    witness.model_fact_ids = {"fact.identity"};
    fixture.frontier.candidates.front()
        .evidence.model_provenance.model_fact_ids = {"fact.identity"};
    ModelFact fact;
    fact.fact_id = "fact.identity";
    fact.kind = ModelFactKind::SemanticTransfer;
    fact.source_semantic_node_id = "semantic.boundary";
    fact.target_semantic_node_id = "semantic.root";
    fact.transfer_relation = "identity";
    fact.certainty = Certainty::Modelled;
    fact.value_transfer = identity_value_transfer();
    fixture.overlay.semantic_facts.push_back(fact);
    MutationRecipes recipes = run(fixture);
    require(recipes.recipes.front().status == RecipeStatus::Supported &&
                recipes.recipes.front().solver_query.outcome ==
                    SolverOutcome::Sat,
            "certificate-bound MODELLED identity transfer closes a portable value path");
}

void test_joint_hyperedge_is_not_split() {
    const ValueType type = integer_type(8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare("==", reference("selector.value", type),
                      integer_literal("1", type)));
    const ExternalAction second_action = action(
        "action.second", "selector.value", type);
    fixture.overlay.external_actions.push_back(second_action);
    fixture.frontier.candidates.push_back(candidate(
        "candidate.second", "ap.value", second_action));
    ModelFact fact;
    fact.fact_id = "fact.joint";
    fact.kind = ModelFactKind::SemanticTransfer;
    fact.source_semantic_node_id = "node.left";
    fact.target_semantic_node_id = "node.right";
    fact.transfer_relation = "joint";
    fact.certainty = Certainty::Modelled;
    fixture.overlay.semantic_facts.push_back(fact);
    JointActionRequirement joint;
    joint.requirement_id = "joint.neutral";
    joint.frontier_candidate_ids = {
        "candidate.value", "candidate.second"};
    joint.action_ids = {"action.value", "action.second"};
    joint.model_fact_ids = {"fact.joint"};
    joint.complete = true;
    fixture.options.joint_action_requirements.push_back(joint);
    MutationRecipes recipes = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    const std::vector<std::string> errors = validate_mutation_recipes(
        recipes, fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier,
        fixture.overlay, fixture.predicate_occurrences, fixture.digests,
        fixture.options);
    require(errors.empty() && recipes.recipes.size() == 2,
            "joint fixture validates with one recipe per candidate");
    for (const MutationRecipe &recipe : recipes.recipes) {
        require(recipe.action_hyperedge.claim == JointActionClaim::JointRequired &&
                    recipe.action_hyperedge.action_ids.size() == 2 &&
                    recipe.action_mutations.size() == 2 &&
                    recipe.status == RecipeStatus::Unknown,
                "joint action remains indivisible and never becomes two flip claims");
    }
    std::reverse(
        fixture.frontier.candidates.begin(), fixture.frontier.candidates.end());
    std::reverse(
        fixture.overlay.external_actions.begin(),
        fixture.overlay.external_actions.end());
    std::reverse(
        fixture.options.joint_action_requirements.front()
            .frontier_candidate_ids.begin(),
        fixture.options.joint_action_requirements.front()
            .frontier_candidate_ids.end());
    std::reverse(
        fixture.options.joint_action_requirements.front().action_ids.begin(),
        fixture.options.joint_action_requirements.front().action_ids.end());
    MutationRecipes permuted = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    require(canonical_mutation_recipes_json(permuted) ==
                canonical_mutation_recipes_json(recipes),
            "candidate/action/joint input order does not change canonical recipes");
}

void test_source_joint_derivation_and_total_unknown() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    const auto make_fixture = [&](const std::string &operation) {
        Fixture fixture = fixture_for(
            type,
            boolean_expression(
                operation,
                compare(
                    ">", reference("selector.value", type),
                    integer_literal("3", type)),
                compare(
                    "<", reference("selector.second", type),
                    integer_literal("9", type))));
        add_second_exact_action(fixture, type);
        return fixture;
    };

    Fixture conjunction = make_fixture("&&");
    MutationRecipes recipes = build_mutation_recipes(
        conjunction.typed_property, conjunction.bindings,
        conjunction.graph, conjunction.cones, conjunction.frontier,
        conjunction.overlay, conjunction.predicate_occurrences,
        conjunction.digests, conjunction.options);
    require(recipes.recipes.size() == 2,
            "source conjunction retains one accounted recipe per candidate");
    for (const MutationRecipe &recipe : recipes.recipes) {
        require(
            recipe.action_hyperedge.claim ==
                    JointActionClaim::JointRequired &&
                recipe.action_hyperedge.action_ids.size() == 2 &&
                recipe.action_mutations.size() == 2 &&
                recipe.solver_query.outcome == SolverOutcome::Sat,
            "closed source AND, exact occurrences, compatible value witnesses, and multi-input SMT derive an indivisible joint recipe");
    }
    const std::vector<std::string> source_errors =
        validate_mutation_recipes(
            recipes, conjunction.typed_property, conjunction.bindings,
            conjunction.graph, conjunction.cones, conjunction.frontier,
            conjunction.overlay, conjunction.predicate_occurrences,
            conjunction.digests, conjunction.options);
    require(source_errors.empty(),
            "detached validation independently accepts an untampered automatic source joint");
    MutationRecipes split = recipes;
    for (MutationRecipe &recipe : split.recipes) {
        const auto candidate = std::find_if(
            conjunction.frontier.candidates.begin(),
            conjunction.frontier.candidates.end(),
            [&](const FrontierCandidate &item) {
                return item.candidate_id == recipe.frontier_candidate_id;
            });
        require(candidate != conjunction.frontier.candidates.end(),
                "source joint tamper fixture candidate exists");
        const std::string action_id =
            candidate->action.external_action_id;
        recipe.action_hyperedge.action_ids = {action_id};
        recipe.action_hyperedge.claim =
            JointActionClaim::SingleAction;
        recipe.action_mutations.erase(
            std::remove_if(
                recipe.action_mutations.begin(),
                recipe.action_mutations.end(),
                [&](const ActionMutation &mutation) {
                    return mutation.action_id != action_id;
                }),
            recipe.action_mutations.end());
    }
    const std::vector<std::string> split_errors =
        validate_mutation_recipes(
            split, conjunction.typed_property, conjunction.bindings,
            conjunction.graph, conjunction.cones, conjunction.frontier,
            conjunction.overlay, conjunction.predicate_occurrences,
            conjunction.digests, conjunction.options);
    require(std::any_of(
                split_errors.begin(), split_errors.end(),
                [](const std::string &error) {
                    return error.find(
                               "automatic joint action was split") !=
                           std::string::npos;
                }),
            "detached validation recomputes source-visible AND evidence and rejects a locally self-consistent split hyperedge");
    const std::string canonical = canonical_mutation_recipes_json(recipes);
    std::reverse(
        conjunction.frontier.candidates.begin(),
        conjunction.frontier.candidates.end());
    std::reverse(
        conjunction.overlay.external_actions.begin(),
        conjunction.overlay.external_actions.end());
    std::reverse(
        conjunction.predicate_occurrences.occurrences.begin(),
        conjunction.predicate_occurrences.occurrences.end());
    MutationRecipes permuted = build_mutation_recipes(
        conjunction.typed_property, conjunction.bindings,
        conjunction.graph, conjunction.cones, conjunction.frontier,
        conjunction.overlay, conjunction.predicate_occurrences,
        conjunction.digests, conjunction.options);
    require(canonical_mutation_recipes_json(permuted) == canonical,
            "automatic source joint derivation is input-order deterministic");

    Fixture disjunction = make_fixture("||");
    MutationRecipes alternatives = build_mutation_recipes(
        disjunction.typed_property, disjunction.bindings,
        disjunction.graph, disjunction.cones, disjunction.frontier,
        disjunction.overlay, disjunction.predicate_occurrences,
        disjunction.digests, disjunction.options);
    require(std::all_of(
                alternatives.recipes.begin(), alternatives.recipes.end(),
                [](const MutationRecipe &recipe) {
                    return recipe.action_hyperedge.claim ==
                               JointActionClaim::SingleAction &&
                           recipe.action_hyperedge.action_ids.size() == 1;
                }),
            "OR alternatives are never collapsed into an AND hyperedge");

    Fixture incomplete = make_fixture("&&");
    incomplete.predicate_occurrences.selector_accounts.back().resolution =
        PredicateOccurrenceResolution::Unknown;
    incomplete.predicate_occurrences.selector_accounts.back()
        .uncertainty_reasons = {"occurrence enumeration incomplete"};
    MutationRecipes unknown = build_mutation_recipes(
        incomplete.typed_property, incomplete.bindings, incomplete.graph,
        incomplete.cones, incomplete.frontier, incomplete.overlay,
        incomplete.predicate_occurrences, incomplete.digests,
        incomplete.options);
    require(std::all_of(
                unknown.recipes.begin(), unknown.recipes.end(),
                [](const MutationRecipe &recipe) {
                    return recipe.action_hyperedge.claim ==
                               JointActionClaim::JointUnknown &&
                           recipe.status == RecipeStatus::Unknown &&
                           !recipe.uncertainty_reasons.empty();
                }),
            "incomplete source occurrence evidence preserves the possible AND group as JointUnknown");

    Fixture shared_action = make_fixture("&&");
    const ExternalAction first_action =
        shared_action.frontier.candidates.front().action;
    FrontierCandidate &second_candidate =
        shared_action.frontier.candidates.back();
    second_candidate.action = first_action;
    shared_action.overlay.external_actions.erase(
        shared_action.overlay.external_actions.begin() + 1);
    shared_action.overlay.boundary_attachments.back().external_action_id =
        first_action.external_action_id;
    MutationRecipes deduplicated = build_mutation_recipes(
        shared_action.typed_property, shared_action.bindings,
        shared_action.graph, shared_action.cones, shared_action.frontier,
        shared_action.overlay, shared_action.predicate_occurrences,
        shared_action.digests, shared_action.options);
    require(std::all_of(
                deduplicated.recipes.begin(), deduplicated.recipes.end(),
                [](const MutationRecipe &recipe) {
                    return recipe.action_hyperedge.claim ==
                               JointActionClaim::SingleAction &&
                           recipe.action_hyperedge.action_ids.size() == 1;
                }),
            "two predicate operands controlled by one external action are deduplicated and never called a multi-action requirement");
}

void test_typed_clock_relation_closes_exact_timing() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("3", type)));
    ModelFact clock;
    clock.fact_id = "fact.clock";
    clock.kind = ModelFactKind::ClockRelation;
    clock.source_semantic_node_id = "semantic.boundary";
    clock.target_semantic_node_id = "semantic.root";
    clock.transfer_relation = "relative_clock";
    clock.certainty = Certainty::Modelled;
    clock.clock_relation = ModelClockRelationV2{
        "clock.monotonic", ModelClockUnit::Milliseconds, "epoch.session",
        1.0, 0.0, ModelClockWrap::None, std::nullopt,
        "event.accepted", "event.observed", ModelClockEndpoint::Mixed,
        "scope-key", "generation-key"};
    fixture.overlay.semantic_facts.push_back(clock);
    FrontierWitness &witness =
        fixture.frontier.candidates.front().witnesses.front();
    witness.model_fact_ids = {clock.fact_id};
    witness.path_exemplars.push_back(path_exemplar(
        "context.root", "context.root",
        {model_step(
            clock.fact_id, "context.boundary", "context.root")},
        {}, ReachabilityVerdict::ModelledWitness));
    fixture.frontier.candidates.front()
        .evidence.model_provenance.model_fact_ids = {clock.fact_id};
    MutationRecipes exact = run(fixture);
    const TimingContract &timing = exact.recipes.front().timing;
    require(timing.status == TimingStatus::Exact &&
                timing.clock_source ==
                    std::optional<std::string>{"clock.monotonic"} &&
                timing.unit == std::optional<std::string>{"ms"} &&
                timing.epoch ==
                    std::optional<std::string>{"epoch.session"} &&
                timing.start_event ==
                    std::optional<std::string>{"event.accepted"} &&
                timing.end_event ==
                    std::optional<std::string>{"event.observed"} &&
                timing.uncertainty_reasons.empty(),
            "one MODELLED complete clock fact on the compatible witness closes exact timing");

    ModelFact conflict = clock;
    conflict.fact_id = "fact.clock.conflict";
    conflict.clock_relation->clock_source = "clock.alternate";
    fixture.overlay.semantic_facts.push_back(conflict);
    witness.model_fact_ids.push_back(conflict.fact_id);
    witness.path_exemplars.push_back(path_exemplar(
        "context.root", "context.root",
        {model_step(
            conflict.fact_id, "context.boundary", "context.root")},
        {}, ReachabilityVerdict::ModelledWitness));
    fixture.frontier.candidates.front()
        .evidence.model_provenance.model_fact_ids.push_back(conflict.fact_id);
    MutationRecipes widened = run(fixture);
    require(widened.recipes.front().timing.status ==
                    TimingStatus::WidenedUnknown &&
                !widened.recipes.front()
                     .timing.uncertainty_reasons.empty(),
            "conflicting witness-bound clock relations widen timing instead of selecting one");

    fixture.overlay.semantic_facts.pop_back();
    witness.model_fact_ids.pop_back();
    witness.path_exemplars.pop_back();
    fixture.frontier.candidates.front()
        .evidence.model_provenance.model_fact_ids.pop_back();
    fixture.overlay.semantic_facts.front().certainty = Certainty::Unknown;
    MutationRecipes unknown = run(fixture);
    require(unknown.recipes.front().timing.status ==
                    TimingStatus::WidenedUnknown &&
                !unknown.recipes.front()
                     .timing.uncertainty_reasons.empty(),
            "UNKNOWN clock evidence cannot produce exact timing");
}

void test_typed_parse_transfer_is_branch_explicit() {
    const ValueType type = integer_type(
        32, true, ValueKind::Integer, "int");
    Fixture valid = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("3", type)));
    ModelValueTransferV2 parsed;
    parsed.kind =
        ModelValueTransferKind::ParseIdentityWithPrecondition;
    parsed.precondition =
        ModelValuePrecondition::CanonicalDecimalIntegerInRange;
    parsed.executor_enforces_precondition = true;
    parsed.failure_branch_unknown = true;
    valid.overlay.boundary_attachments.front().value_transfer = parsed;
    MutationRecipes valid_branch = run(valid);
    require(valid_branch.recipes.front().status ==
                    RecipeStatus::Supported &&
                valid_branch.recipes.front()
                        .action_mutations.front().direction ==
                    MutationDirection::MonotoneUp,
            "executor-enforced canonical in-range decimal parsing is identity in the typed int action coordinate");

    Fixture fallback = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("3", type)));
    ModelValueTransferV2 unknown;
    unknown.kind = ModelValueTransferKind::Unknown;
    unknown.precondition = ModelValuePrecondition::Unknown;
    unknown.executor_enforces_precondition = false;
    unknown.failure_branch_unknown = true;
    fallback.overlay.boundary_attachments.front().value_transfer = unknown;
    MutationRecipes failure_branch = run(fallback);
    require(failure_branch.recipes.front().status ==
                    RecipeStatus::Heuristic &&
                failure_branch.recipes.front()
                        .action_mutations.front().direction ==
                    MutationDirection::Unknown &&
                failure_branch.recipes.front()
                    .action_mutations.front().suggested_values.empty(),
            "fallback, range-error, truncation, and trailing-character branches never inherit the valid parse direction");
}

void test_modelled_all_required_relation_derives_joint() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type,
        compare(
            ">",
            binary(
                "+", reference("selector.value", type),
                reference("selector.second", type), type),
            integer_literal("10", type)));
    add_second_exact_action(fixture, type);
    ModelJointActionConstraint constraint;
    constraint.constraint_id = "constraint.atomic";
    constraint.group_instance_id = "group.instance";
    constraint.group_schema_id = "group.schema";
    constraint.combination = ModelJointActionOperator::AllRequired;
    constraint.participant_set_complete = true;
    constraint.participant_semantic_node_ids = {
        "semantic.boundary", "semantic.second-boundary"};
    constraint.scope_schema = "scope-key";
    constraint.generation_schema = "generation-key";
    constraint.certainty = Certainty::Modelled;
    fixture.overlay.joint_action_constraints.push_back(constraint);
    MutationRecipes recipes = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    require(std::all_of(
                recipes.recipes.begin(), recipes.recipes.end(),
                [](const MutationRecipe &recipe) {
                    return recipe.action_hyperedge.claim ==
                               JointActionClaim::JointRequired &&
                           recipe.solver_query.outcome == SolverOutcome::Sat;
                }),
            "MODELLED ALL_REQUIRED relation plus closed participants/value witnesses and multi-input SMT derives a joint hyperedge without a manual RecipeOption");

    fixture.overlay.joint_action_constraints.front().certainty =
        Certainty::Unknown;
    MutationRecipes unknown_relation = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    require(std::all_of(
                unknown_relation.recipes.begin(),
                unknown_relation.recipes.end(),
                [](const MutationRecipe &recipe) {
                    return recipe.action_hyperedge.claim ==
                               JointActionClaim::JointUnknown &&
                           recipe.status == RecipeStatus::Unknown;
                }),
            "UNKNOWN ALL_REQUIRED model evidence cannot be upgraded to JointRequired");
}

void test_control_guard_prerequisite_is_never_overclaimed() {
    const ValueType type = integer_type(
        8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("3", type)));
    ExternalAction guard = action(
        "action.guard", "payload.guard", boolean_type(), "enable");
    fixture.overlay.external_actions.push_back(guard);
    BoundaryAttachment guard_attachment;
    guard_attachment.attachment_id = "attachment.guard";
    guard_attachment.external_action_id = guard.external_action_id;
    guard_attachment.semantic_node_id = "semantic.guard-boundary";
    guard_attachment.transfer_relation = "guard_state";
    guard_attachment.certainty = Certainty::Modelled;
    guard_attachment.value_transfer = identity_value_transfer();
    fixture.overlay.boundary_attachments.push_back(guard_attachment);
    ContextualNode guard_boundary;
    guard_boundary.node_id = "context.guard-boundary";
    guard_boundary.semantic_node_id = "semantic.guard-boundary";
    guard_boundary.kind = SemanticNodeKind::Value;
    guard_boundary.value_type = boolean_type();
    fixture.graph.nodes.push_back(guard_boundary);
    InfluenceEdge control;
    control.edge_id = "edge.guard-control";
    control.source_node_id = guard_boundary.node_id;
    control.target_node_id = "context.root";
    control.kind = RelationKind::Control;
    control.certainty = Certainty::May;
    fixture.graph.edges.push_back(control);
    FrontierCandidate guard_candidate = candidate(
        "candidate.guard", "ap.value", guard);
    FrontierWitness guard_witness;
    guard_witness.witness_id = "witness.guard";
    guard_witness.attachment_id = guard_attachment.attachment_id;
    guard_witness.boundary_node_id = guard_boundary.node_id;
    guard_witness.path_exemplars.push_back(path_exemplar(
        "context.root", "context.root",
        {graph_step(
            control.edge_id, control.source_node_id,
            control.target_node_id)}));
    guard_witness.compatibility = WitnessCompatibility::Compatible;
    guard_witness.reachability = ReachabilityVerdict::StaticWitness;
    guard_candidate.witnesses.push_back(guard_witness);
    fixture.frontier.candidates.push_back(guard_candidate);

    MutationRecipes recipes = build_mutation_recipes(
        fixture.typed_property, fixture.bindings, fixture.graph,
        fixture.cones, fixture.frontier, fixture.overlay,
        fixture.predicate_occurrences, fixture.digests, fixture.options);
    const auto value_recipe = std::find_if(
        recipes.recipes.begin(), recipes.recipes.end(),
        [](const MutationRecipe &recipe) {
            return recipe.frontier_candidate_id == "candidate.value";
        });
    require(value_recipe != recipes.recipes.end() &&
                !value_recipe->prerequisite_choices.empty() &&
                value_recipe->prerequisite_choices.front()
                        .alternatives.front().status ==
                    PrerequisiteStatus::PartialOrderUnknown &&
                !value_recipe->prerequisite_choices.front()
                     .alternatives.front().uncertainty_reasons.empty(),
            "a guard control path produces an explicit before-DAG but remains PARTIAL when control is MAY and external temporal order is unclosed");
}

void test_prerequisite_alternatives_remain_choices() {
    const ValueType type = integer_type(8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("1", type)));
    ExternalAction first = action(
        "action.setup-first", "selector.setup", type, "prepare-first");
    ExternalAction second = action(
        "action.setup-second", "selector.setup", type, "prepare-second");
    fixture.overlay.external_actions.push_back(first);
    fixture.overlay.external_actions.push_back(second);
    fixture.overlay.boundary_attachments.push_back({
        "attachment.first", first.external_action_id, "node.setup",
        "identity", Certainty::Modelled, {}});
    fixture.overlay.boundary_attachments.push_back({
        "attachment.second", second.external_action_id, "node.setup",
        "identity", Certainty::Modelled, {}});
    ModelFact lifecycle;
    lifecycle.fact_id = "fact.lifecycle";
    lifecycle.kind = ModelFactKind::LifecycleTransition;
    lifecycle.source_semantic_node_id = "node.setup";
    lifecycle.target_semantic_node_id = "node.active";
    lifecycle.transfer_relation = "before";
    lifecycle.certainty = Certainty::Modelled;
    fixture.overlay.semantic_facts.push_back(lifecycle);
    FrontierWitness witness;
    witness.witness_id = "witness.value";
    witness.attachment_id = "attachment.value";
    witness.boundary_node_id = "node.boundary";
    witness.compatibility = WitnessCompatibility::Compatible;
    witness.reachability = ReachabilityVerdict::ModelledWitness;
    witness.model_fact_ids = {"fact.lifecycle"};
    fixture.frontier.candidates.front().witnesses.push_back(witness);
    MutationRecipes recipes = run(fixture);
    const auto &choices = recipes.recipes.front().prerequisite_choices;
    require(choices.size() == 1 && choices.front().alternatives.size() == 2,
            "alternative setup actions remain one OR choice with two DAGs");
    for (const PrerequisiteDag &alternative : choices.front().alternatives) {
        require(alternative.steps.size() == 2 &&
                    alternative.steps.back().predecessor_step_ids.size() == 1,
                "each prerequisite alternative preserves its own partial order");
    }
}

void test_replay_and_json_contract() {
    const ValueType type = integer_type(8, false, ValueKind::Integer, "uint8_t");
    Fixture fixture = fixture_for(
        type, compare(">", reference("selector.value", type),
                      integer_literal("1", type)));
    MutationRecipes recipes = run(fixture);
    const std::string recipes_json = canonical_mutation_recipes_json(recipes);
    require(recipes_json.find("\"direction_query\"") != std::string::npos &&
                recipes_json.find("\"solver_version\":\"4.8.12\"") !=
                    std::string::npos &&
                recipes_json.find("\"max_queries\":10000") !=
                    std::string::npos,
            "canonical recipe JSON records direction proof, solver version, and query budget");
    const std::string digest = sha256_hex(recipes_json);
    RecipeReplayObligations obligations =
        build_recipe_replay_obligations(recipes, digest);
    const std::vector<std::string> errors =
        validate_recipe_replay_obligations(obligations, recipes, digest);
    require(errors.empty() && obligations.obligations.size() == 1,
            "every recipe has a digest-bound replay obligation");
    require(obligations.obligations.front().status == ReplayStatus::Partial &&
                obligations.obligations.front().expected_relation ==
                    ReplayExpectedRelation::ApTruthChange,
            "widened timing creates partial replay, not a false ready claim");
    require(
        canonical_recipe_replay_obligations_json(obligations).find(
            "\"indivisible_hyperedge\":true") != std::string::npos,
        "replay serialization preserves hyperedge indivisibility");

    const auto rejected_field = [&](
                                    RecipeReplayObligations tampered,
                                    const std::string &field) {
        const std::vector<std::string> tamper_errors =
            validate_recipe_replay_obligations(
                tampered, recipes, digest);
        require(
            std::any_of(
                tamper_errors.begin(), tamper_errors.end(),
                [&](const std::string &error) {
                    return error.find(field) != std::string::npos;
                }),
            "replay validator accepted tampered " + field);
    };
    RecipeReplayObligations tampered = obligations;
    tampered.obligations.front().obligation_id += ".tampered";
    rejected_field(tampered, "obligation_id");
    tampered = obligations;
    tampered.obligations.front().frontier_candidate_id += ".tampered";
    rejected_field(tampered, "frontier_candidate_id");
    tampered = obligations;
    tampered.obligations.front().status = ReplayStatus::Ready;
    rejected_field(tampered, "status");
    tampered = obligations;
    tampered.obligations.front().atomic_action_ids.push_back("action.tampered");
    rejected_field(tampered, "atomic_action_ids");
    tampered = obligations;
    tampered.obligations.front().indivisible_hyperedge = false;
    rejected_field(tampered, "indivisible_hyperedge");
    tampered = obligations;
    tampered.obligations.front().ordered_step_ids.push_back("step.tampered");
    rejected_field(tampered, "ordered_step_ids");
    tampered = obligations;
    tampered.obligations.front().required_observations.push_back(
        "MONITOR_SUCCESSOR");
    rejected_field(tampered, "required_observations");
    tampered = obligations;
    tampered.obligations.front().expected_relation =
        ReplayExpectedRelation::Unknown;
    rejected_field(tampered, "expected_relation");
    tampered = obligations;
    tampered.obligations.front().solver_query_sha256 = std::string(64, 'f');
    rejected_field(tampered, "solver_query_sha256");
    tampered = obligations;
    tampered.obligations.front().scope_schema = "scope.tampered";
    rejected_field(tampered, "scope_schema");
    tampered = obligations;
    tampered.obligations.front().generation_schema = "generation.tampered";
    rejected_field(tampered, "generation_schema");
    tampered = obligations;
    tampered.obligations.front().timing_status = TimingStatus::Unknown;
    rejected_field(tampered, "timing_status");
    tampered = obligations;
    tampered.obligations.front().uncertainty_reasons.push_back(
        "tampered reason");
    rejected_field(tampered, "uncertainty_reasons");

    MutationRecipes ready_recipes = recipes;
    MutationRecipe &ready_recipe = ready_recipes.recipes.front();
    ready_recipe.status = RecipeStatus::Supported;
    ready_recipe.prerequisite_choices.clear();
    ready_recipe.timing.status = TimingStatus::Exact;
    ready_recipe.timing.clock_source = "clock.monotonic";
    ready_recipe.timing.unit = "ms";
    ready_recipe.timing.epoch = "process";
    ready_recipe.timing.quantum = 1.0;
    ready_recipe.timing.jitter = 0.0;
    ready_recipe.timing.wrap = "none";
    ready_recipe.timing.comparison_endpoint = TimingEndpoint::Closed;
    ready_recipe.timing.start_event = "action.accepted";
    ready_recipe.timing.end_event = "ap.observed";
    ready_recipe.timing.scope_schema = "scope.neutral";
    ready_recipe.timing.generation_schema = "generation.neutral";
    ready_recipe.timing.uncertainty_reasons.clear();
    const std::string ready_digest = sha256_hex(
        canonical_mutation_recipes_json(ready_recipes));
    RecipeReplayObligations ready = build_recipe_replay_obligations(
        ready_recipes, ready_digest);
    require(
        ready.obligations.front().status == ReplayStatus::Ready &&
            ready.obligations.front().uncertainty_reasons.empty(),
        "SUPPORTED SAT recipe with executable actions, no prerequisites, and exact timing is replay READY");

    MutationRecipes heuristic_recipes = ready_recipes;
    heuristic_recipes.recipes.front().status = RecipeStatus::Heuristic;
    RecipeReplayObligations heuristic = build_recipe_replay_obligations(
        heuristic_recipes,
        sha256_hex(canonical_mutation_recipes_json(heuristic_recipes)));
    require(
        heuristic.obligations.front().status == ReplayStatus::Partial,
        "HEURISTIC recipe cannot become replay READY");

    MutationRecipes no_values_recipes = ready_recipes;
    no_values_recipes.recipes.front()
        .action_mutations.front().suggested_values.clear();
    RecipeReplayObligations no_values = build_recipe_replay_obligations(
        no_values_recipes,
        sha256_hex(canonical_mutation_recipes_json(no_values_recipes)));
    require(
        no_values.obligations.front().status == ReplayStatus::Partial,
        "action without concrete mutation values cannot become replay READY");

    MutationRecipes ordered_recipes = ready_recipes;
    PrerequisiteStep setup;
    setup.step_id = "step.setup";
    setup.action_id = "action.setup";
    setup.operation = "prepare";
    PrerequisiteStep mutate;
    mutate.step_id = "step.mutate";
    mutate.action_id = ready_recipe.action_hyperedge.action_ids.front();
    mutate.operation = "mutate";
    mutate.predecessor_step_ids = {setup.step_id};
    PrerequisiteDag ordered_dag;
    ordered_dag.dag_id = "dag.ordered";
    ordered_dag.status = PrerequisiteStatus::Complete;
    ordered_dag.steps = {mutate, setup};
    PrerequisiteChoice ordered_choice;
    ordered_choice.choice_id = "choice.ordered";
    ordered_choice.alternatives = {ordered_dag};
    ordered_recipes.recipes.front().prerequisite_choices = {ordered_choice};
    RecipeReplayObligations ordered = build_recipe_replay_obligations(
        ordered_recipes,
        sha256_hex(canonical_mutation_recipes_json(ordered_recipes)));
    require(
        ordered.obligations.front().status == ReplayStatus::Ready &&
            ordered.obligations.front().ordered_step_ids ==
                std::vector<std::string>({"step.setup", "step.mutate"}),
        "singleton COMPLETE prerequisite DAG is deterministically ordered and READY");

    MutationRecipes ambiguous_recipes = ordered_recipes;
    PrerequisiteDag alternative = ordered_dag;
    alternative.dag_id = "dag.alternative";
    ambiguous_recipes.recipes.front()
        .prerequisite_choices.front().alternatives.push_back(alternative);
    RecipeReplayObligations ambiguous = build_recipe_replay_obligations(
        ambiguous_recipes,
        sha256_hex(canonical_mutation_recipes_json(ambiguous_recipes)));
    require(
        ambiguous.obligations.front().status == ReplayStatus::Partial &&
            ambiguous.obligations.front().ordered_step_ids.empty(),
        "unselected prerequisite OR alternatives cannot become replay READY");
}

}  // namespace

int main(int argc, char **argv) {
    if (argc == 2 && std::string(argv[1]) == "--dump-json") {
        const ValueType type = integer_type(
            8, false, ValueKind::Integer, "uint8_t");
        Fixture fixture = fixture_for(
            type, compare(">", reference("selector.value", type),
                          integer_literal("1", type)));
        MutationRecipes recipes = run(fixture);
        const std::string recipes_json =
            canonical_mutation_recipes_json(recipes);
        const std::string digest = sha256_hex(recipes_json);
        RecipeReplayObligations obligations =
            build_recipe_replay_obligations(recipes, digest);
        std::cout << recipes_json << '\n'
                  << canonical_recipe_replay_obligations_json(obligations)
                  << '\n';
        return 0;
    }
    test_signed_boundary_and_direction();
    test_integral_promotions();
    test_signed_ub_vs_unsigned_wrap();
    test_bool_enum_and_bitmask();
    test_nonlinear_and_solver_budget_are_total_unknown();
    test_single_reference_ap_site_fallback_is_value_only();
    test_two_roots_bind_two_dynamic_threshold_roles();
    test_control_only_witness_does_not_map_value();
    test_modelled_identity_transfer_can_close_value_path();
    test_joint_hyperedge_is_not_split();
    test_source_joint_derivation_and_total_unknown();
    test_typed_clock_relation_closes_exact_timing();
    test_typed_parse_transfer_is_branch_explicit();
    test_modelled_all_required_relation_derives_joint();
    test_control_guard_prerequisite_is_never_overclaimed();
    test_prerequisite_alternatives_remain_choices();
    test_replay_and_json_contract();
    std::cout << "recipe smoke: PASS\n";
    return 0;
}
