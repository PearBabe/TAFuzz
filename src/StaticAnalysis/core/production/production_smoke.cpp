#include "rift/core/production.h"

#include <algorithm>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <string>

namespace {

using namespace rift::core;

void require(bool condition, const char *message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        std::exit(1);
    }
}

bool contains_error(
    const std::vector<std::string> &errors, const std::string &needle);
bool graph_reaches(
    const ContextualInfluenceGraph &graph, const std::string &source,
    const std::string &target);

ValueType integer_type(const std::string &canonical = "int") {
    ValueType type;
    type.kind = ValueKind::Integer;
    type.canonical = canonical;
    type.bit_width = 32;
    type.is_signed = true;
    return type;
}

SourceLocation at(
    std::uint32_t line, std::uint32_t column,
    std::uint32_t end_line = 0, std::uint32_t end_column = 0) {
    return {"src/neutral.cc", line, column, end_line, end_column,
            "spelling", {}};
}

EntityRef entity(
    std::string id, EntityKind kind, std::string signature,
    std::string type) {
    EntityRef result;
    result.entity_id = std::move(id);
    result.kind = kind;
    result.identity_status = IdentityStatus::Exact;
    result.usr = "usr:" + result.entity_id;
    result.qualified_signature = std::move(signature);
    result.canonical_type = std::move(type);
    result.declarations = {at(4, 1)};
    result.definitions = {at(4, 1)};
    result.translation_unit_ids = {"tu.neutral"};
    return result;
}

ExpressionStructure predicate() {
    ExpressionStructure result;
    result.node_kind = "reference";
    result.value_type.kind = ValueKind::Boolean;
    result.value_type.canonical = "bool";
    result.referenced_selector_id = "selector.composite";
    return result;
}

SemanticIndex relational_binding_fixture() {
    SemanticIndex index;
    index.artifact_id = "index.neutral";
    index.compilation_database_sha256 = std::string(64, '1');
    index.source_identity_root = "/fixture";
    index.status = StageStatus::Complete;
    index.translation_units.push_back({
        "tu.neutral", "src/neutral.cc", "c++", "/fixture",
        std::string(64, '2'), StageStatus::Complete, {}, {}});
    index.entities = {
        entity("entity.function", EntityKind::Function, "Neutral::commit:int ()", "int ()"),
        entity("entity.object", EntityKind::Local, "Neutral::context:NeutralState", "NeutralState"),
        entity("entity.field", EntityKind::Field, "NeutralState::ready:int", "int"),
        entity("entity.site", EntityKind::Expression, "Neutral::commit-site:int", "int"),
    };
    index.abstract_objects.push_back({
        "object.context", ObjectAbstraction::Stack, at(7, 3), Certainty::Must});

    SemanticNode function;
    function.node_id = "node.function";
    function.kind = SemanticNodeKind::Definition;
    function.entity_id = "entity.function";
    function.owner_function_id = "entity.function";
    function.value_type = integer_type("int ()");
    function.location = at(4, 1, 12, 1);
    function.ast_kind = "FunctionDecl";

    SemanticNode field;
    field.node_id = "node.field";
    field.kind = SemanticNodeKind::Memory;
    field.entity_id = "entity.object";
    field.owner_function_id = "entity.function";
    field.access_path = AccessPath{
        "entity.object", 0, {"entity.field"}, false};
    field.abstract_object_id = "object.context";
    field.value_type = integer_type();
    field.location = at(8, 5, 8, 17);
    field.ast_kind = "MemberExpr";

    SemanticNode site;
    site.node_id = "node.site";
    site.kind = SemanticNodeKind::Expression;
    site.entity_id = "entity.site";
    site.owner_function_id = "entity.function";
    site.value_type = integer_type();
    site.location = at(9, 1, 11, 20);
    site.ast_kind = "BinaryOperator";
    index.nodes = {function, field, site};

    SemanticRelation relation;
    relation.relation_id = "relation.field-site";
    relation.source_node_id = "node.field";
    relation.target_node_id = "node.site";
    relation.kind = RelationKind::Data;
    relation.certainty = Certainty::May;
    relation.evidence.push_back({
        "evidence.field-site", "ast_semantics", Certainty::May,
        "field reaches commit site", "fixture", at(9, 1)});
    index.relations.push_back(relation);
    FunctionSummary summary;
    summary.function_entity_id = "entity.function";
    summary.owned_node_ids = {"node.function", "node.field", "node.site"};
    summary.relation_ids = {"relation.field-site"};
    index.function_summaries.push_back(summary);
    return index;
}

TypedPropertyIr relational_property_fixture() {
    TypedPropertyIr property;
    property.artifact_id = "property.artifact";
    property.artifact_sha256 = std::string(64, '3');
    property.property_id = "property.neutral";
    property.logic = "MITL";
    property.time_domain = "dense";
    property.formula_text = "F_[0,1] committed";
    property.formula.node_id = "formula.root";
    property.formula.operation = FormulaOperator::Eventually;
    property.formula.interval = TimeInterval{0.0, 1.0, false, true, true, "s", {}};
    FormulaNode atom;
    atom.node_id = "formula.atom";
    atom.operation = FormulaOperator::Atom;
    atom.ap_id = "ap.committed";
    property.formula.operands.push_back(atom);

    Selector function;
    function.selector_id = "selector.function";
    function.kind = SelectorKind::QualifiedSignature;
    function.qualified_signature = "Neutral::commit:int ()";
    Selector post_site;
    post_site.selector_id = "selector.post-site";
    post_site.kind = SelectorKind::SourceLocation;
    post_site.location = at(10, 3);
    Selector field;
    field.selector_id = "selector.field";
    field.kind = SelectorKind::TypedFieldPath;
    field.value_type = integer_type("NeutralState");
    field.field_path = {"NeutralState", "ready"};
    Selector composite;
    composite.selector_id = "selector.composite";
    composite.kind = SelectorKind::Composite;
    composite.component_ids = {
        "selector.function", "selector.post-site", "selector.field"};
    property.selectors = {function, post_site, field, composite};

    AtomicProposition ap;
    ap.ap_id = "ap.committed";
    ap.roles = {ApRole::State, ApRole::Guard};
    ap.value_type.kind = ValueKind::Boolean;
    ap.value_type.canonical = "bool";
    ap.predicate = predicate();
    ap.selector_ids = {"selector.composite"};
    property.atomic_propositions.push_back(ap);
    return property;
}

void test_relational_composite_binding() {
    const SemanticIndex index = relational_binding_fixture();
    const TypedPropertyIr property = relational_property_fixture();
    const std::string index_digest(64, '4');
    const ApBindings bindings =
        bind_atomic_propositions(property, index, index_digest);
    require(bindings.status != StageStatus::Failed, "binding stage validates");
    require(bindings.bindings.size() == 2, "all AP roles share a ledger");
    require(
        bindings.bindings[0].resolution == BindingResolution::Confirmed,
        "function+range-site+record-field composite confirms");
    require(
        bindings.bindings[1].resolution == BindingResolution::Confirmed,
        "second role reuses compatible composite result");
    require(
        bindings.bindings[0].candidates.size() == 1 &&
            bindings.bindings[1].candidates.size() == 1,
        "composite is one relational candidate, not per-node ambiguity");
    const std::set<std::string> first(
        bindings.bindings[0].candidates[0].semantic_node_ids.begin(),
        bindings.bindings[0].candidates[0].semantic_node_ids.end());
    const std::set<std::string> second(
        bindings.bindings[1].candidates[0].semantic_node_ids.begin(),
        bindings.bindings[1].candidates[0].semantic_node_ids.end());
    require(first == second, "role compatibility ledgers are identical");
    require(first.contains("node.site"), "post-site range seed retained");
    require(first.contains("node.field"), "typed record field retained");
}

void test_binding_candidate_top1_order() {
    const SemanticIndex index = relational_binding_fixture();
    TypedPropertyIr property = relational_property_fixture();
    property.atomic_propositions[0].selector_ids = {
        "selector.function", "selector.field"};
    const std::string index_digest(64, 'b');
    const ApBindings bindings =
        bind_atomic_propositions(property, index, index_digest);
    require(bindings.status == StageStatus::ConservativeIncomplete,
            "two exact selector targets remain explicit ambiguity");
    require(
        bindings.bindings.size() == 2 &&
            bindings.bindings[0].candidates.size() == 2,
        "ambiguous role emits both candidates");
    for (const ApRoleBinding &binding : bindings.bindings) {
        require(
            binding.candidates[0].confidence >=
                binding.candidates[1].confidence,
            "binding candidates are confidence descending");
        if (binding.candidates[0].confidence ==
            binding.candidates[1].confidence) {
            require(
                binding.candidates[0].semantic_node_ids <
                    binding.candidates[1].semantic_node_ids,
                "equal-confidence candidates use stable semantic-node order");
        }
    }
    ApBindings reversed = bindings;
    std::reverse(
        reversed.bindings[0].candidates.begin(),
        reversed.bindings[0].candidates.end());
    ArtifactDigests expected;
    expected.property_ir_sha256 = property.artifact_sha256;
    expected.semantic_index_sha256 = index_digest;
    require(
        contains_error(
            validate_ap_bindings(reversed, property, index, expected),
            "stable Top-1 order"),
        "binding validator rejects a non-ranked candidate ledger");
}

void test_role_dnf_binding_isolates_roles_and_alternatives() {
    const SemanticIndex index = relational_binding_fixture();
    TypedPropertyIr property = relational_property_fixture();
    property.schema_version = "2.0.0";
    AtomicProposition &ap = property.atomic_propositions[0];
    ap.roles = {ApRole::Trigger, ApRole::Scope, ApRole::Guard};
    ap.selector_ids.clear();
    ap.predicate.referenced_selector_id = "selector.field";

    RoleSelectorGroup trigger;
    trigger.group_id = "group.trigger.commit";
    trigger.role = ApRole::Trigger;
    trigger.selector_ids = {
        "selector.function", "selector.post-site", "selector.field"};
    RoleSelectorGroup scope_field;
    scope_field.group_id = "group.scope.field";
    scope_field.role = ApRole::Scope;
    scope_field.selector_ids = {"selector.field"};
    RoleSelectorGroup scope_site;
    scope_site.group_id = "group.scope.site";
    scope_site.role = ApRole::Scope;
    scope_site.selector_ids = {"selector.post-site"};

    Selector absent;
    absent.selector_id = "selector.absent";
    absent.kind = SelectorKind::SourceLocation;
    absent.location = at(99, 1);
    property.selectors.push_back(absent);
    RoleSelectorGroup guard;
    guard.group_id = "group.guard.absent";
    guard.role = ApRole::Guard;
    guard.selector_ids = {"selector.absent"};
    ap.role_selector_groups = {
        trigger, scope_field, scope_site, guard};

    const std::string index_digest(64, 'd');
    const ApBindings bindings =
        bind_atomic_propositions(property, index, index_digest);
    require(bindings.schema_version == "2.0.0",
            "role-DNF input produces v2 bindings");
    require(bindings.status == StageStatus::ConservativeIncomplete,
            "an unresolved alternative keeps the binding stage conservative");
    require(bindings.bindings.size() == 3,
            "role-DNF emits exactly one ledger per declared role");

    const auto find_role = [&](ApRole role) -> const ApRoleBinding & {
        const auto found = std::find_if(
            bindings.bindings.begin(), bindings.bindings.end(),
            [&](const ApRoleBinding &binding) { return binding.role == role; });
        require(found != bindings.bindings.end(), "declared role is emitted");
        return *found;
    };
    const ApRoleBinding &trigger_binding = find_role(ApRole::Trigger);
    require(trigger_binding.resolution == BindingResolution::Confirmed,
            "one exact all-of group confirms the trigger role");
    require(trigger_binding.candidates.size() == 1,
            "trigger receives no scope or guard candidates");
    require(
        trigger_binding.candidates[0].selector_group_id ==
            std::optional<std::string>{"group.trigger.commit"},
        "candidate records its role-DNF group provenance");
    const std::set<std::string> trigger_nodes(
        trigger_binding.candidates[0].semantic_node_ids.begin(),
        trigger_binding.candidates[0].semantic_node_ids.end());
    require(trigger_nodes.contains("node.site") &&
                trigger_nodes.contains("node.field"),
            "all-of group retains compatible site and field witnesses");
    std::set<std::string> evidence_ids;
    for (const BindingEvidence &evidence :
         trigger_binding.candidates[0].evidence) {
        require(evidence_ids.insert(evidence.evidence_id).second,
                "binding evidence IDs are unique within a candidate");
    }
    require(evidence_ids.size() == 3,
            "every all-of selector contributes distinct evidence");

    const ApRoleBinding &scope_binding = find_role(ApRole::Scope);
    require(scope_binding.resolution == BindingResolution::Confirmed,
            "two designed alternatives are confirmed rather than ambiguous");
    require(scope_binding.candidates.size() == 2 &&
                std::all_of(
                    scope_binding.candidates.begin(),
                    scope_binding.candidates.end(),
                    [](const BindingCandidate &candidate) {
                        return candidate.status == CandidateStatus::Confirmed;
                    }),
            "each exact scope alternative remains an independent candidate");

    const ApRoleBinding &guard_binding = find_role(ApRole::Guard);
    require(guard_binding.resolution == BindingResolution::Unresolved,
            "an unmatched role group is explicit unresolved");
    require(guard_binding.candidates.size() == 1 &&
                guard_binding.candidates[0].status ==
                    CandidateStatus::Unresolved &&
                guard_binding.candidates[0].semantic_node_ids.empty(),
            "unmatched group emits a candidate-accounting placeholder");

    TypedPropertyIr reordered = property;
    std::reverse(
        reordered.atomic_propositions[0].role_selector_groups.begin(),
        reordered.atomic_propositions[0].role_selector_groups.end());
    for (RoleSelectorGroup &group :
         reordered.atomic_propositions[0].role_selector_groups) {
        std::reverse(group.selector_ids.begin(), group.selector_ids.end());
    }
    const ApBindings reordered_bindings =
        bind_atomic_propositions(reordered, index, index_digest);
    std::set<std::string> original_ids;
    std::set<std::string> reordered_ids;
    for (const ApRoleBinding &binding : bindings.bindings) {
        for (const BindingCandidate &candidate : binding.candidates) {
            original_ids.insert(candidate.binding_id);
        }
    }
    for (const ApRoleBinding &binding : reordered_bindings.bindings) {
        for (const BindingCandidate &candidate : binding.candidates) {
            reordered_ids.insert(candidate.binding_id);
        }
    }
    require(original_ids == reordered_ids,
            "role/group/selector order does not change stable candidate IDs");

    TypedPropertyIr missing_role = property;
    auto &groups =
        missing_role.atomic_propositions[0].role_selector_groups;
    groups.erase(
        std::remove_if(
            groups.begin(), groups.end(),
            [](const RoleSelectorGroup &group) {
                return group.role == ApRole::Guard;
            }),
        groups.end());
    require(
        contains_error(
            validate_typed_property_ir(missing_role),
            "declared role has no selector group"),
        "v2 semantic validation rejects a declared role without a group");

    TypedPropertyIr uncovered_predicate = property;
    uncovered_predicate.atomic_propositions[0].predicate.
        referenced_selector_id = "selector.composite";
    require(
        contains_error(
            validate_typed_property_ir(uncovered_predicate),
            "predicate selector is not covered"),
        "v2 semantic validation requires predicate-selector role coverage");
}

void test_typed_field_selector_matches_access_prefix() {
    SemanticIndex index = relational_binding_fixture();
    EntityRef subfield = entity(
        "entity.subfield", EntityKind::Field,
        "NeutralReady::bit:int", "int");
    index.entities.push_back(subfield);
    for (EntityRef &item : index.entities) {
        if (item.entity_id == "entity.field") {
            item.qualified_signature = "NeutralState::ready:NeutralReady";
            item.canonical_type = "NeutralReady";
        }
    }
    for (SemanticNode &node : index.nodes) {
        if (node.node_id == "node.field") {
            node.access_path->fields.push_back("entity.subfield");
        }
    }

    TypedPropertyIr property = relational_property_fixture();
    property.atomic_propositions[0].roles = {ApRole::State};
    property.atomic_propositions[0].selector_ids = {"selector.field"};
    property.atomic_propositions[0].predicate.referenced_selector_id =
        "selector.field";
    for (Selector &selector : property.selectors) {
        if (selector.selector_id == "selector.field") {
            selector.value_type = integer_type("NeutralReady");
            selector.value_type->kind = ValueKind::Record;
        }
    }
    const ApBindings bindings = bind_atomic_propositions(
        property, index, std::string(64, 'e'));
    require(bindings.status != StageStatus::Failed,
            "typed aggregate-field prefix validates");
    require(bindings.bindings.size() == 1 &&
                bindings.bindings[0].resolution ==
                    BindingResolution::Confirmed &&
                bindings.bindings[0].candidates[0].semantic_node_ids ==
                    std::vector<std::string>{"node.field"},
            "aggregate field selector binds a deeper subfield access");
}

void test_role_all_of_uses_direct_callsite_summary() {
    SemanticIndex index = relational_binding_fixture();
    index.entities.push_back(entity(
        "entity.callee", EntityKind::Function,
        "Neutral::derive:int (NeutralState *)", "int (NeutralState *)"));
    SemanticNode callee;
    callee.node_id = "node.callee";
    callee.kind = SemanticNodeKind::Definition;
    callee.entity_id = "entity.callee";
    callee.owner_function_id = "entity.callee";
    callee.value_type = integer_type("int (NeutralState *)");
    callee.location = at(20, 1, 24, 1);
    callee.ast_kind = "FunctionDecl";
    index.nodes.push_back(callee);
    for (SemanticNode &node : index.nodes) {
        if (node.node_id == "node.field") {
            node.owner_function_id = "entity.callee";
        }
        if (node.node_id == "node.site") {
            node.kind = SemanticNodeKind::CallSite;
            node.owner_function_id = "entity.function";
        }
    }
    CallSiteSummary callsite;
    callsite.callsite_id = "callsite.derive";
    callsite.caller_function_id = "entity.function";
    callsite.candidate_callee_ids = {"entity.callee"};
    callsite.result_node_id = "node.site";
    callsite.location = at(10, 3);
    callsite.direct = true;
    callsite.status = StageStatus::Complete;
    index.callsites.push_back(callsite);
    index.function_summaries[0].callsite_ids.push_back(callsite.callsite_id);
    FunctionSummary callee_summary;
    callee_summary.function_entity_id = "entity.callee";
    callee_summary.owned_node_ids = {"node.callee", "node.field"};
    index.function_summaries.push_back(callee_summary);

    TypedPropertyIr property = relational_property_fixture();
    for (Selector &selector : property.selectors) {
        if (selector.selector_id == "selector.function") {
            selector.qualified_signature =
                "Neutral::derive:int (NeutralState *)";
        }
    }
    const ApBindings bindings = bind_atomic_propositions(
        property, index, std::string(64, 'f'));
    require(bindings.status != StageStatus::Failed,
            "direct-call relational binding validates");
    require(
        !bindings.bindings.empty() &&
            bindings.bindings[0].resolution == BindingResolution::Confirmed,
        "role all-of relates a caller site to the direct callee definition");
}

void test_compile_database_cwd_invariance() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-plan-" + sha256_hex("cwd-invariance").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root / "bundle" / "meta", error);
    require(!error, "temporary planner fixture directory created");
    const std::filesystem::path database =
        root / "bundle" / "meta" / "compile_commands.json";
    {
        std::ofstream output(database);
        output << R"json([{
  "directory": "..",
  "file": "src/neutral.c",
  "arguments": ["clang-18", "-c", "src/neutral.c", "-o", "neutral.o"]
}])json";
    }
    const std::filesystem::path original = std::filesystem::current_path();
    std::filesystem::create_directories(root / "caller-a", error);
    std::filesystem::create_directories(root / "caller-b", error);
    std::filesystem::current_path(root / "caller-a");
    const CompilationPlan first = load_compilation_plan(database);
    std::filesystem::current_path(root / "caller-b");
    const CompilationPlan second = load_compilation_plan(database);
    std::filesystem::current_path(original);
    require(first.status == StageStatus::Complete, "relative directory accepted");
    require(second.status == StageStatus::Complete, "second caller cwd accepted");
    require(first.commands.size() == 1 && second.commands.size() == 1,
            "planner command count");
    require(
        first.commands[0].working_directory ==
            second.commands[0].working_directory,
        "compile directory does not depend on process cwd");
    require(
        first.commands[0].source_file == second.commands[0].source_file,
        "source resolution does not depend on process cwd");
    require(
        first.commands[0].working_directory ==
            (root / "bundle").lexically_normal().string(),
        "relative directory resolves against database parent");

    CompilationPlanOptions strict;
    strict.require_absolute_working_directories = true;
    const CompilationPlan rejected = load_compilation_plan(database, strict);
    require(rejected.status == StageStatus::Failed,
            "strict mode rejects relative compile directory");
    std::filesystem::remove_all(root, error);
}

void test_identity_v2_portability_and_fail_closed_paths() {
    const std::filesystem::path base =
        std::filesystem::temp_directory_path() /
        ("rift-production-identity-" +
         sha256_hex("identity-v2").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(base, error);
    std::filesystem::create_directories(base, error);
    require(!error, "temporary identity-v2 fixture directory created");

    auto relocated_plan = [&](const std::filesystem::path &root) {
        std::filesystem::create_directories(root, error);
        const std::filesystem::path source = root / "neutral.cc";
        const std::filesystem::path database = root / "compile_commands.json";
        {
            std::ofstream output(source);
            output << "int neutral(int value) { return value + 1; }\n";
        }
        {
            std::ofstream output(database);
            output << "[{\"directory\":\"" << root.string()
                   << "\",\"file\":\"" << source.string()
                   << "\",\"arguments\":[\"clang++-18\",\"-c\",\""
                   << source.string() << "\",\"-o\",\""
                   << (root / "neutral.o").string() << "\"]}]";
        }
        CompilationPlanOptions options;
        options.source_identity_root = root;
        return load_compilation_plan(database, options);
    };
    const CompilationPlan clone_a = relocated_plan(base / "clone-a");
    const CompilationPlan clone_b = relocated_plan(base / "clone-b");
    require(clone_a.status == StageStatus::Complete &&
                clone_b.status == StageStatus::Complete,
            "relocated identity-v2 plans load");
    require(
        clone_a.compilation_database_sha256 !=
            clone_b.compilation_database_sha256,
        "raw compile database digest records physical relocation");
    require(
        clone_a.canonical_compilation_database_sha256 ==
            clone_b.canonical_compilation_database_sha256 &&
            clone_a.commands[0].translation_unit_id ==
                clone_b.commands[0].translation_unit_id &&
            clone_a.commands[0].command_sha256 ==
                clone_b.commands[0].command_sha256,
        "canonical command, database, and TU identities survive relocation");
    require(
        clone_a.commands[0].logical_source_file ==
            "riftpath://v1/source/neutral.cc" &&
            clone_a.commands[0].logical_working_directory ==
                "riftpath://v1/source/",
        "portable plan exposes versioned logical source/cwd paths");
    const SemanticIndex clone_a_index = build_semantic_index(clone_a);
    const SemanticIndex clone_b_index = build_semantic_index(clone_b);
    require(
        clone_a_index.status == StageStatus::Complete &&
            clone_b_index.status == StageStatus::Complete &&
            clone_a_index.input_manifest_sha256 ==
                clone_b_index.input_manifest_sha256 &&
            clone_a_index.artifact_id == clone_b_index.artifact_id,
        "same logical files/bytes yield identical input manifest and index identity across checkouts");

    const std::filesystem::path micro = base / "micro";
    std::filesystem::create_directories(micro / "cases" / "case_1", error);
    std::filesystem::create_directories(micro / "sources", error);
    {
        std::ofstream output(micro / "sources" / "case.c");
        output << "#include <stddef.h>\n"
                  "#include <sys/socket.h>\n"
                  "int case_value(void) { char *end = NULL; "
                  "return end == NULL ? SOCK_DGRAM : 0; }\n";
    }
    const std::filesystem::path micro_db =
        micro / "cases" / "case_1" / "compile_commands.json";
    {
        std::ofstream output(micro_db);
        output << R"json([{"directory":"../..","file":"sources/case.c","arguments":["clang-18","-c","sources/case.c","-o","case.o"]}])json";
    }
    const CompilationPlan inferred = load_compilation_plan(micro_db);
    require(inferred.status == StageStatus::Complete,
            "default root inference covers source and working directory");
    require(
        inferred.identity_roots.size() == 1 &&
            inferred.identity_roots[0].root_id == "project" &&
            inferred.commands[0].logical_working_directory ==
                "riftpath://v1/project/" &&
            inferred.commands[0].logical_source_file ==
                "riftpath://v1/project/sources/case.c",
        "default micro layout maps to one portable project root");
    const SemanticIndex inferred_index = build_semantic_index(inferred);
    require(inferred_index.status != StageStatus::Failed,
            "relative main file and system-macro expansion resolve without identity failure");
    require(
        std::none_of(
            inferred_index.coverage_gaps.begin(),
            inferred_index.coverage_gaps.end(),
            [](const CoverageGap &gap) {
                return gap.kind == "unmapped_source_identity";
            }),
        "relative main-file spelling does not create an unmapped path gap");
    require(
        std::all_of(
            inferred_index.nodes.begin(), inferred_index.nodes.end(),
            [](const SemanticNode &node) {
                return node.location.file.starts_with("riftpath://v1/");
            }),
        "every semantic node uses a schema-valid logical source identity");

    // Clang may retain an include spelling that crosses a symlink before
    // applying `..` components.  Lexically normalizing that spelling changes
    // its meaning (for example, /lib -> /usr/lib on merged-/usr systems), so
    // physical provenance must resolve the existing file first.
    const std::filesystem::path symlink_fixture = base / "symlink-include";
    const std::filesystem::path symlink_project = symlink_fixture / "project";
    const std::filesystem::path symlink_usr = symlink_fixture / "usr";
    std::filesystem::create_directories(
        symlink_usr / "lib" / "gcc" / "neutral" / "11", error);
    std::filesystem::create_directories(symlink_usr / "include", error);
    std::filesystem::create_directories(symlink_project, error);
    require(!error, "symlink include fixture directories created");
    std::filesystem::create_directory_symlink(
        std::filesystem::path("usr/lib"), symlink_fixture / "lib", error);
    require(!error, "symlink include fixture alias created");
    {
        std::ofstream output(symlink_usr / "include" / "portable_fixture.h");
        output << "inline int portable_fixture_value() { return 7; }\n";
    }
    const std::filesystem::path symlink_source = symlink_project / "main.cc";
    {
        std::ofstream output(symlink_source);
        output << "#include <portable_fixture.h>\n"
                  "int main() { return portable_fixture_value(); }\n";
    }
    const std::filesystem::path symlink_include_spelling =
        symlink_fixture / "lib" / "gcc" / "neutral" / "11" / ".." /
        ".." / ".." / ".." / "include";
    const std::filesystem::path symlink_database =
        symlink_project / "compile_commands.json";
    {
        std::ofstream output(symlink_database);
        output << "[{\"directory\":\"" << symlink_project.string()
               << "\",\"file\":\"" << symlink_source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-isystem\",\""
               << symlink_include_spelling.string()
               << "\",\"-c\",\"" << symlink_source.string()
               << "\",\"-o\",\""
               << (symlink_project / "main.o").string() << "\"]}]";
    }
    CompilationPlanOptions symlink_options;
    symlink_options.source_identity_root = symlink_fixture;
    const CompilationPlan symlink_plan =
        load_compilation_plan(symlink_database, symlink_options);
    require(symlink_plan.status == StageStatus::Complete,
            "symlink include fixture plan loads");
    const SemanticIndex symlink_index = build_semantic_index(symlink_plan);
    require(symlink_index.status != StageStatus::Failed,
            "symlink include fixture indexes without stage failure");
    bool saw_symlink_header = false;
    for (const InputFileDigest &input : symlink_index.input_files) {
        if (input.logical_path.ends_with("/usr/include/portable_fixture.h")) {
            saw_symlink_header = true;
        }
        for (const std::string &observed : input.observed_paths) {
            require(std::filesystem::is_regular_file(observed),
                    "observed provenance path preserves symlink-aware filesystem semantics");
        }
    }
    require(saw_symlink_header,
            "symlinked include resolves to the canonical logical header");

    const std::filesystem::path project = base / "multi-root";
    const std::filesystem::path source_root = project / "source";
    const std::filesystem::path build_root = project / "build";
    std::filesystem::create_directories(source_root / "alpha", error);
    std::filesystem::create_directories(build_root / "beta", error);
    {
        std::ofstream output(source_root / "alpha" / "common.h");
        output << "inline int source_value() { return 1; }\n";
    }
    {
        std::ofstream output(build_root / "beta" / "common.h");
        output << "inline int build_value() { return 2; }\n";
    }
    const std::filesystem::path source = source_root / "main.cc";
    {
        std::ofstream output(source);
        output << "#include <stddef.h>\n"
                  "#include \"alpha/common.h\"\n"
                  "#include \"beta/common.h\"\n"
                  "int main() { return source_value() + build_value(); }\n";
    }
    const std::filesystem::path database = build_root / "compile_commands.json";
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << build_root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-I\",\""
               << source_root.string() << "\",\"-I\",\""
               << build_root.string() << "\",\"-c\",\"" << source.string()
               << "\",\"-o\",\"" << (build_root / "main.o").string()
               << "\"]}]";
    }
    CompilationPlanOptions multi_options;
    multi_options.identity_roots = {
        {"source", source_root}, {"build", build_root}};
    const CompilationPlan multi_plan =
        load_compilation_plan(database, multi_options);
    require(multi_plan.status == StageStatus::Complete,
            "explicit source/build path map loads");
    const SemanticIndex multi_index = build_semantic_index(multi_plan);
    require(multi_index.status == StageStatus::Complete,
            "source/build same-basename headers index completely");
    std::set<std::string> common_locations;
    for (const EntityRef &entity : multi_index.entities) {
        for (const SourceLocation &location : entity.definitions) {
            if (location.file.ends_with("/common.h")) {
                common_locations.insert(location.file);
            }
        }
    }
    require(
        common_locations ==
            std::set<std::string>{
                "riftpath://v1/build/beta/common.h",
                "riftpath://v1/source/alpha/common.h"},
        "same-basename headers retain distinct logical identities");
    require(
        multi_index.translation_units[0].source_file ==
            "riftpath://v1/source/main.cc" &&
            multi_index.translation_units[0].working_directory ==
                "riftpath://v1/build/",
        "semantic index persists logical, not physical, TU paths");
    std::set<InputFileRole> input_roles;
    for (const InputFileDigest &input : multi_index.input_files) {
        input_roles.insert(input.role);
        require(!input.logical_path.starts_with(project.string()),
                "input manifest never persists a physical project root");
        if (input.role != InputFileRole::Toolchain) {
            require(
                !input.observed_paths.empty() &&
                    std::all_of(
                        input.observed_paths.begin(),
                        input.observed_paths.end(),
                        [](const std::string &path) {
                            return std::filesystem::path(path).is_absolute();
                        }),
                "file-backed input retains absolute non-canonical provenance");
        }
    }
    require(
        input_roles.contains(InputFileRole::Main) &&
            input_roles.contains(InputFileRole::UserHeader) &&
            input_roles.contains(InputFileRole::Generated) &&
            input_roles.contains(InputFileRole::System) &&
            input_roles.contains(InputFileRole::Toolchain),
        "input manifest covers main/user/generated/system/toolchain inputs");
    {
        std::ofstream output(build_root / "beta" / "common.h");
        output << "inline int build_value() { return 4; }\n";
    }
    const SemanticIndex changed_header = build_semantic_index(multi_plan);
    require(
        changed_header.status == StageStatus::Complete &&
            changed_header.canonical_compilation_database_sha256 ==
                multi_index.canonical_compilation_database_sha256 &&
            changed_header.input_manifest_sha256 !=
                multi_index.input_manifest_sha256 &&
            changed_header.artifact_id != multi_index.artifact_id,
        "changing one loaded header changes manifest and index identity without changing compile DB identity");

    const std::filesystem::path repo = base / "repo";
    const std::filesystem::path repo2 = base / "repo2";
    std::filesystem::create_directories(repo, error);
    std::filesystem::create_directories(repo2, error);
    const std::string repo2_text = (repo2 / "common.h").string();
    require(
        canonicalize_identity_text({{"source", repo}}, repo2_text) ==
            repo2_text &&
            !logical_identity_path({{"source", repo}}, repo2 / "common.h"),
        "path replacement respects /repo versus /repo2 component boundary");
    require(
        logical_identity_path(
            {{"project", project}, {"build", build_root}},
            build_root / "beta" / "common.h") ==
            std::optional<std::string>(
                "riftpath://v1/build/beta/common.h"),
        "nested logical roots select the longest matching root");

    const std::filesystem::path response_root = base / "response";
    std::filesystem::create_directories(response_root, error);
    {
        std::ofstream output(response_root / "case.c");
        output << "int response_case(void) { return 0; }\n";
    }
    const std::filesystem::path response_db =
        response_root / "compile_commands.json";
    {
        std::ofstream output(response_db);
        output << "[{\"directory\":\"" << response_root.string()
               << "\",\"file\":\"" << (response_root / "case.c").string()
               << "\",\"arguments\":[\"clang-18\",\"@outside.rsp\"]}]";
    }
    CompilationPlanOptions response_options;
    response_options.source_identity_root = response_root;
    const CompilationPlan response =
        load_compilation_plan(response_db, response_options);
    require(response.status == StageStatus::Failed && response.commands.empty(),
            "unexpanded response-file command fails closed");
    require(
        std::any_of(
            response.coverage_gaps.begin(), response.coverage_gaps.end(),
            [](const CoverageGap &gap) {
                return gap.kind == "unmapped_compile_path" &&
                       gap.effect == GapEffect::StageFailure;
            }),
        "response-file failure is explicit in coverage gaps");

    const std::filesystem::path foreign = base / "foreign";
    std::filesystem::create_directories(foreign, error);
    {
        std::ofstream output(foreign / "external.h");
        output << "inline int external_value() { return 3; }\n";
    }
    const std::filesystem::path isolated = base / "isolated";
    std::filesystem::create_directories(isolated, error);
    {
        std::ofstream output(isolated / "main.cc");
        output << "#include \"" << (foreign / "external.h").string()
               << "\"\nint main() { return external_value(); }\n";
    }
    const std::filesystem::path isolated_db =
        isolated / "compile_commands.json";
    {
        std::ofstream output(isolated_db);
        output << "[{\"directory\":\"" << isolated.string()
               << "\",\"file\":\"" << (isolated / "main.cc").string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << (isolated / "main.cc").string() << "\",\"-o\",\""
               << (isolated / "main.o").string() << "\"]}]";
    }
    CompilationPlanOptions isolated_options;
    isolated_options.source_identity_root = isolated;
    const CompilationPlan isolated_plan =
        load_compilation_plan(isolated_db, isolated_options);
    require(isolated_plan.status == StageStatus::Complete,
            "unmapped-header fixture plan itself is portable");
    const SemanticIndex isolated_index = build_semantic_index(isolated_plan);
    require(isolated_index.status == StageStatus::Failed &&
                isolated_index.entities.empty() && isolated_index.nodes.empty() &&
                isolated_index.relations.empty(),
            "unmapped source header fails closed without partial TU facts");
    require(
        std::any_of(
            isolated_index.coverage_gaps.begin(),
            isolated_index.coverage_gaps.end(),
            [](const CoverageGap &gap) {
                return gap.kind == "unmapped_source_identity" &&
                       gap.effect == GapEffect::StageFailure;
            }),
        "unmapped source header records a stage-failure coverage gap");

    CompilationPlanOptions duplicate_root_options;
    duplicate_root_options.identity_roots = {
        {"source", isolated}, {"alias", isolated}};
    const CompilationPlan duplicate_root =
        load_compilation_plan(isolated_db, duplicate_root_options);
    require(
        duplicate_root.status == StageStatus::Failed &&
            duplicate_root.commands.empty(),
        "two logical IDs for one canonical physical root fail closed");
    std::filesystem::remove_all(base, error);
}

std::string semantic_fingerprint(const SemanticIndex &index) {
    std::string material = index.artifact_id;
    auto append = [&](const std::string &kind, const std::string &id) {
        material += '\0' + kind + '\0' + id;
    };
    for (const TranslationUnitRecord &item : index.translation_units) {
        append("tu", item.translation_unit_id);
    }
    for (const EntityRef &item : index.entities) {
        append("entity", item.entity_id);
        for (const std::string &tu : item.translation_unit_ids) {
            append("entity-tu", tu);
        }
    }
    for (const AbstractObject &item : index.abstract_objects) {
        append("object", item.object_id);
    }
    for (const SemanticNode &item : index.nodes) {
        append("node", item.node_id);
    }
    for (const SemanticRelation &item : index.relations) {
        append("relation", item.relation_id);
    }
    for (const FunctionSummary &item : index.function_summaries) {
        append("summary", item.function_entity_id);
    }
    for (const CallSiteSummary &item : index.callsites) {
        append("callsite", item.callsite_id);
    }
    for (const CoverageGap &item : index.coverage_gaps) {
        append("gap", item.gap_id);
    }
    return sha256_hex(material);
}

void test_multi_tu_duplicate_merge_is_linear_and_deterministic() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-multitu-" + sha256_hex("multitu").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary multi-TU fixture directory created");
    const std::filesystem::path header = root / "shared.h";
    const std::filesystem::path first_source = root / "first.cc";
    const std::filesystem::path second_source = root / "second.cc";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(header);
        output << "#pragma once\n"
                  "inline int shared(int value) { return value + 1; }\n";
    }
    {
        std::ofstream output(first_source);
        output << "#include \"shared.h\"\n"
                  "int first(int input) { return shared(input); }\n";
    }
    {
        std::ofstream output(second_source);
        output << "#include \"shared.h\"\n"
                  "int second(int input) { return shared(input); }\n";
    }
    {
        std::ofstream output(database);
        auto command = [&](const std::filesystem::path &source,
                           const std::filesystem::path &object) {
            output << "{\"directory\":\"" << root.string()
                   << "\",\"file\":\"" << source.string()
                   << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                      "\"-I\",\""
                   << root.string() << "\",\"-c\",\"" << source.string()
                   << "\",\"-o\",\"" << object.string() << "\"]}";
        };
        output << '[';
        command(first_source, root / "first.o");
        output << ',';
        command(second_source, root / "second.o");
        output << ']';
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete,
            "multi-TU compile plan loads");
    const SemanticIndex first = build_semantic_index(plan);
    const SemanticIndex second = build_semantic_index(plan);
    require(first.status == StageStatus::Complete &&
                second.status == StageStatus::Complete,
            "multi-TU fixture indexes completely");
    std::string shared_entity;
    for (const EntityRef &candidate : first.entities) {
        if (candidate.qualified_signature &&
            *candidate.qualified_signature == "shared:int (int)") {
            shared_entity = candidate.entity_id;
            require(candidate.translation_unit_ids.size() == 2,
                    "duplicate header entity merges both TU provenance sets");
            break;
        }
    }
    require(!shared_entity.empty(), "shared header function entity resolves");
    require(
        std::count_if(
            first.function_summaries.begin(),
            first.function_summaries.end(),
            [&](const FunctionSummary &summary) {
                return summary.function_entity_id == shared_entity;
            }) == 1,
        "duplicate inline function summary is merged once");
    auto unique_ids = [](const auto &items, const auto &id) {
        std::set<std::string> ids;
        for (const auto &item : items) {
            ids.insert(id(item));
        }
        return ids.size() == items.size();
    };
    require(unique_ids(first.nodes, [](const SemanticNode &item) {
                return item.node_id;
            }),
            "multi-TU semantic node IDs remain unique");
    require(unique_ids(first.relations, [](const SemanticRelation &item) {
                return item.relation_id;
            }),
            "multi-TU relation IDs remain unique");
    require(unique_ids(first.callsites, [](const CallSiteSummary &item) {
                return item.callsite_id;
            }),
            "multi-TU callsite IDs remain unique");
    require(
        semantic_fingerprint(first) == semantic_fingerprint(second),
        "multi-TU merge preserves deterministic artifact order and identity");
    std::filesystem::remove_all(root, error);
}

void test_argument_exprsite_totality() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-arguments-" +
         sha256_hex("argument-exprsite").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary argument ExprSite fixture created");
    const std::filesystem::path source = root / "neutral.cc";
    const std::filesystem::path object = root / "neutral.o";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(source);
        output << R"cpp(struct Item { int value; };
void sink(int code, void *absent, Item *item) {
  (void)code;
  (void)absent;
  (void)item;
}
int main() {
  sink(42, nullptr, new Item{7});
  return 0;
}
)cpp";
    }
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << source.string() << "\",\"-o\",\"" << object.string()
               << "\"]}]";
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete,
            "argument ExprSite compile plan loads");
    const SemanticIndex index = build_semantic_index(plan);
    require(index.status == StageStatus::ConservativeIncomplete,
            "unsupported argument is explicit conservative-incomplete");
    std::string sink_entity;
    for (const EntityRef &candidate : index.entities) {
        if (candidate.qualified_signature &&
            candidate.qualified_signature->find("sink:void") == 0) {
            sink_entity = candidate.entity_id;
            break;
        }
    }
    const CallSiteSummary *sink_call = nullptr;
    for (const CallSiteSummary &candidate : index.callsites) {
        if (candidate.direct && candidate.candidate_callee_ids.size() == 1 &&
            candidate.candidate_callee_ids.front() == sink_entity) {
            sink_call = &candidate;
            break;
        }
    }
    require(sink_call != nullptr, "three-argument sink callsite resolves");
    require(
        sink_call->argument_node_groups.size() == 3 &&
            sink_call->argument_is_address.size() == 3,
        "literal/null/unsupported actuals retain positional arity");
    require(
        std::all_of(
            sink_call->argument_node_groups.begin(),
            sink_call->argument_node_groups.end(),
            [](const std::vector<std::string> &group) {
                return !group.empty();
            }),
        "no actual argument position is represented by an empty group");
    auto node = [&](std::size_t position) -> const SemanticNode * {
        const std::string &node_id =
            sink_call->argument_node_groups[position].front();
        for (const SemanticNode &candidate : index.nodes) {
            if (candidate.node_id == node_id) {
                return &candidate;
            }
        }
        return nullptr;
    };
    auto object_for_node = [&](const SemanticNode &semantic)
        -> const AbstractObject * {
        if (!semantic.abstract_object_id) {
            return nullptr;
        }
        for (const AbstractObject &candidate : index.abstract_objects) {
            if (candidate.object_id == *semantic.abstract_object_id) {
                return &candidate;
            }
        }
        return nullptr;
    };
    auto entity_for = [&](const SemanticNode &semantic) -> const EntityRef * {
        for (const EntityRef &candidate : index.entities) {
            if (candidate.entity_id == semantic.entity_id) {
                return &candidate;
            }
        }
        return nullptr;
    };
    const SemanticNode *literal = node(0);
    const SemanticNode *null_pointer = node(1);
    const SemanticNode *unsupported = node(2);
    require(literal != nullptr && null_pointer != nullptr &&
                unsupported != nullptr,
            "all synthetic argument nodes resolve");
    require(
        literal->kind == SemanticNodeKind::Value &&
            literal->ast_kind == "IntegerLiteral" &&
            !literal->location.file.empty() && literal->value_type.bit_width,
        "integer literal retains exact ExprSite/location/type");
    require(
        null_pointer->kind == SemanticNodeKind::Value &&
            null_pointer->ast_kind == "CXXNullPtrLiteralExpr" &&
            !null_pointer->location.file.empty(),
        "nullptr retains exact ExprSite/location/type");
    require(
        object_for_node(*literal) != nullptr &&
            object_for_node(*literal)->certainty == Certainty::Must &&
            entity_for(*literal) != nullptr &&
            entity_for(*literal)->identity_status == IdentityStatus::Exact,
        "literal is represented as a must constant");
    require(
        object_for_node(*null_pointer) != nullptr &&
            object_for_node(*null_pointer)->certainty == Certainty::Must &&
            entity_for(*null_pointer) != nullptr &&
            entity_for(*null_pointer)->identity_status == IdentityStatus::Exact,
        "nullptr is represented as a must constant");
    require(
        unsupported->kind == SemanticNodeKind::Value &&
            unsupported->ast_kind == "CXXNewExpr" &&
            unsupported->access_path &&
            unsupported->access_path->unknown_suffix &&
            object_for_node(*unsupported) != nullptr &&
            object_for_node(*unsupported)->certainty == Certainty::Unknown &&
            entity_for(*unsupported) != nullptr &&
            entity_for(*unsupported)->identity_status ==
                IdentityStatus::Unknown,
        "unsupported expression is retained as an explicit unknown ExprSite");
    require(
        std::any_of(
            index.coverage_gaps.begin(), index.coverage_gaps.end(),
            [&](const CoverageGap &gap) {
                return gap.kind == "unsupported_argument_expression" &&
                       std::find(
                           gap.affected_ids.begin(), gap.affected_ids.end(),
                           unsupported->node_id) != gap.affected_ids.end() &&
                       !gap.locations.empty();
            }),
        "unsupported argument carries a source-located soundness gap");
    require(validate_semantic_index(index).empty(),
            "strict semantic validator accepts total positional groups");
    std::filesystem::remove_all(root, error);
}

void test_cfg_postdominator_control() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-cfg-" + sha256_hex("cfg-control").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary CFG fixture directory created");
    const std::filesystem::path source = root / "neutral.cc";
    const std::filesystem::path object = root / "neutral.o";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(source);
        output << R"cpp(int early(int guard, int value) {
  if (!guard) return 0;
  int ap_early = value;
  return ap_early;
}
int choose(int mode, int value) {
  int ap_switch = 0;
  switch (mode) {
    case 1: ap_switch = value; break;
    default: break;
  }
  return ap_switch;
}
int exceptional(int flag) {
  try {
    if (flag) throw flag;
  } catch (...) {
    return 1;
  }
  return 0;
}
)cpp";
    }
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << source.string() << "\",\"-o\",\"" << object.string()
               << "\"]}]";
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete, "CFG compile plan loads");
    const SemanticIndex index = build_semantic_index(plan);
    for (const std::string &diagnostic : index.diagnostics) {
        std::cerr << "CFG-DIAGNOSTIC " << diagnostic << '\n';
    }
    require(
        index.status == StageStatus::ConservativeIncomplete,
        "supported CFG facts survive explicit unsupported exception gap");
    require(
        std::any_of(
            index.coverage_gaps.begin(), index.coverage_gaps.end(),
            [](const CoverageGap &gap) {
                return gap.kind == "cfg_exceptional_control_flow" &&
                       gap.effect == GapEffect::SoundnessRisk;
            }),
        "exceptional control flow cannot be reported CFG-complete");
    auto entity_id = [&](const std::string &needle) {
        for (const EntityRef &candidate : index.entities) {
            if (candidate.qualified_signature &&
                candidate.qualified_signature->find(needle) !=
                    std::string::npos) {
                return candidate.entity_id;
            }
        }
        return std::string();
    };
    auto node_id = [&](const std::string &entity) {
        for (const SemanticNode &candidate : index.nodes) {
            if (candidate.entity_id == entity) {
                return candidate.node_id;
            }
        }
        return std::string();
    };
    const std::string guard = node_id(entity_id("guard:int"));
    const std::string early_ap = node_id(entity_id("ap_early:int"));
    const std::string mode = node_id(entity_id("mode:int"));
    const std::string switch_ap = node_id(entity_id("ap_switch:int"));
    require(
        !guard.empty() && !early_ap.empty() && !mode.empty() &&
            !switch_ap.empty(),
        "CFG fixture anchors resolve by semantic entity");
    auto has_control = [&](const std::string &from, const std::string &to) {
        return std::any_of(
            index.relations.begin(), index.relations.end(),
            [&](const SemanticRelation &relation) {
                return relation.source_node_id == from &&
                       relation.target_node_id == to &&
                       relation.kind == RelationKind::Control &&
                       !relation.evidence.empty() &&
                       relation.evidence.front().fact ==
                           "Clang CFG postdominator control dependence";
            });
    };
    require(has_control(guard, early_ap),
            "early-return reachability is CFG-control dependent");
    require(has_control(mode, switch_ap),
            "switch case write is CFG-control dependent");
    std::filesystem::remove_all(root, error);
}

void test_real_callsite_field_projection() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-fields-" +
         sha256_hex("callsite-fields").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary callsite-field fixture directory created");
    const std::filesystem::path source = root / "neutral.cc";
    const std::filesystem::path object = root / "neutral.o";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(source);
        output << R"cpp(struct Cell { int value; };
void assign(Cell *cell, int input) { cell->value = input; }
int extract(const Cell *cell) { return cell->value; }
void copyout(int input, int *output) { *output = input; }
int main() {
  Cell first{};
  Cell second{};
  Cell third{};
  int source_a = 1;
  int source_b = 2;
  int source_c = 3;
  assign(&first, source_a);
  assign(&second, source_b);
  assign(&third, source_c);
  int result_a = first.value;
  int result_b = second.value;
  int result_c = extract(&third);
  int output_state = 0;
  copyout(result_c, &output_state);
  int callback_result = output_state;
  return result_a + result_b + callback_result;
}
)cpp";
    }
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << source.string() << "\",\"-o\",\"" << object.string()
               << "\"]}]";
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete,
            "callsite-field compile plan loads");
    const SemanticIndex index = build_semantic_index(plan);
    require(index.status == StageStatus::Complete,
            "callsite-field fixture indexes completely");
    const ContextualInfluenceGraph graph = build_contextual_influence_graph(
        index, std::string(64, 'a'));
    require(graph.status == StageStatus::Complete,
            "callsite-field contextual graph is complete");
    auto semantic_node = [&](const std::string &signature) {
        std::string entity_id;
        for (const EntityRef &candidate : index.entities) {
            if (candidate.qualified_signature &&
                *candidate.qualified_signature == signature) {
                entity_id = candidate.entity_id;
                break;
            }
        }
        for (const SemanticNode &candidate : index.nodes) {
            if (candidate.entity_id == entity_id &&
                candidate.kind == SemanticNodeKind::Declaration) {
                return candidate.node_id;
            }
        }
        return std::string();
    };
    auto contextual_node = [&](const std::string &semantic_id) {
        for (const ContextualNode &candidate : graph.nodes) {
            if (candidate.semantic_node_id == semantic_id &&
                candidate.call_context.callsite_ids.empty()) {
                return candidate.node_id;
            }
        }
        return std::string();
    };
    const std::string source_a =
        contextual_node(semantic_node("source_a:int"));
    const std::string source_b =
        contextual_node(semantic_node("source_b:int"));
    const std::string result_a =
        contextual_node(semantic_node("result_a:int"));
    const std::string result_b =
        contextual_node(semantic_node("result_b:int"));
    const std::string source_c =
        contextual_node(semantic_node("source_c:int"));
    const std::string result_c =
        contextual_node(semantic_node("result_c:int"));
    const std::string callback_result =
        contextual_node(semantic_node("callback_result:int"));
    require(
        !source_a.empty() && !source_b.empty() && !result_a.empty() &&
            !result_b.empty() && !source_c.empty() && !result_c.empty() &&
            !callback_result.empty(),
        "real callsite-field anchors resolve");
    require(graph_reaches(graph, source_a, result_a),
            "first call input reaches its caller field read");
    require(graph_reaches(graph, source_b, result_b),
            "second call input reaches its caller field read");
    require(!graph_reaches(graph, source_a, result_b),
            "first call input does not contaminate second object result");
    require(!graph_reaches(graph, source_b, result_a),
            "second call input does not contaminate first object result");
    require(graph_reaches(graph, source_c, result_c),
            "callee write reaches a later callee read through caller storage");
    require(graph_reaches(graph, source_c, callback_result),
            "pointer output reaches a later caller read without a post-call write occurrence");
    std::filesystem::remove_all(root, error);
}

void test_unknown_call_effect_is_caller_context_bounded() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-unknown-call-" +
         sha256_hex("caller-context-summary").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary unknown-call fixture directory created");
    const std::filesystem::path source = root / "neutral.cc";
    const std::filesystem::path object = root / "neutral.o";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(source);
        output << R"cpp(struct Box { int value; };
Box shared;
void opaque(Box *);
int first() {
  opaque(&shared);
  return shared.value;
}
int second() {
  opaque(&shared);
  return shared.value;
}
)cpp";
    }
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << source.string() << "\",\"-o\",\"" << object.string()
               << "\"]}]";
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete,
            "unknown-call compile plan loads");
    const SemanticIndex index = build_semantic_index(plan);
    require(index.status != StageStatus::Failed,
            "unknown-call fixture indexes without stage failure");
    const ContextualInfluenceGraph graph = build_contextual_influence_graph(
        index, std::string(64, 'b'));
    require(graph.status == StageStatus::ConservativeIncomplete,
            "unknown external callee is reported incomplete");

    std::string first_owner;
    std::string second_owner;
    for (const EntityRef &candidate : index.entities) {
        if (!candidate.qualified_signature) {
            continue;
        }
        if (candidate.qualified_signature->find("first:") == 0) {
            first_owner = candidate.entity_id;
        } else if (candidate.qualified_signature->find("second:") == 0) {
            second_owner = candidate.entity_id;
        }
    }
    require(!first_owner.empty() && !second_owner.empty(),
            "unknown-call function owners resolve");
    std::map<std::string, std::string> semantic_owner;
    for (const SemanticNode &node : index.nodes) {
        semantic_owner[node.node_id] = node.owner_function_id;
    }
    std::map<std::string, const ContextualNode *> graph_nodes;
    for (const ContextualNode &node : graph.nodes) {
        graph_nodes[node.node_id] = &node;
    }
    std::string first_effect;
    for (const InfluenceEdge &edge : graph.edges) {
        const auto source_node = graph_nodes.find(edge.source_node_id);
        const auto target_node = graph_nodes.find(edge.target_node_id);
        if (edge.kind == RelationKind::Unknown &&
            source_node != graph_nodes.end() &&
            target_node != graph_nodes.end() &&
            source_node->second->location.line == 5 &&
            semantic_owner[target_node->second->semantic_node_id] ==
                first_owner) {
            first_effect = edge.source_node_id;
            break;
        }
    }
    require(!first_effect.empty(),
            "first opaque call has an explicit unknown-effect summary");
    bool leaks_to_second = false;
    for (const InfluenceEdge &edge : graph.edges) {
        if (edge.source_node_id != first_effect ||
            edge.kind != RelationKind::Unknown) {
            continue;
        }
        const auto target = std::find_if(
            graph.nodes.begin(), graph.nodes.end(),
            [&](const ContextualNode &node) {
                return node.node_id == edge.target_node_id;
            });
        if (target == graph.nodes.end()) {
            continue;
        }
        const std::string owner = semantic_owner[target->semantic_node_id];
        leaks_to_second = leaks_to_second || owner == second_owner;
    }
    require(!leaks_to_second,
            "unknown effect does not cross-product into another caller");
    std::filesystem::remove_all(root, error);
}

void test_non_field_member_access_has_entity_closed_path() {
    const std::filesystem::path root =
        std::filesystem::temp_directory_path() /
        ("rift-production-non-field-member-" +
         sha256_hex("enum-member-access").substr(0, 12));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    require(!error, "temporary non-field-member fixture directory created");
    const std::filesystem::path source = root / "neutral.cc";
    const std::filesystem::path object = root / "neutral.o";
    const std::filesystem::path database = root / "compile_commands.json";
    {
        std::ofstream output(source);
        output << R"cpp(struct Cursor {
  enum Direction { begin, end };
  int seek(int, Direction);
};
int probe(Cursor &cursor) {
  return cursor.seek(0, cursor.end);
}
)cpp";
    }
    {
        std::ofstream output(database);
        output << "[{\"directory\":\"" << root.string()
               << "\",\"file\":\"" << source.string()
               << "\",\"arguments\":[\"clang++-18\",\"-std=c++20\","
                  "\"-c\",\""
               << source.string() << "\",\"-o\",\"" << object.string()
               << "\"]}]";
    }
    CompilationPlanOptions plan_options;
    plan_options.source_identity_root = root;
    const CompilationPlan plan = load_compilation_plan(database, plan_options);
    require(plan.status == StageStatus::Complete,
            "non-field-member compile plan loads");
    const SemanticIndex index = build_semantic_index(plan);
    if (index.status == StageStatus::Failed) {
        for (const std::string &diagnostic : index.diagnostics) {
            std::cerr << "non-field-member diagnostic: " << diagnostic
                      << '\n';
        }
    }
    require(index.status != StageStatus::Failed,
            "enum constant member access indexes without stage failure");
    require(validate_semantic_index(index).empty(),
            "every non-field member access path closes over entity IDs");
    std::set<std::string> entity_ids;
    for (const EntityRef &candidate : index.entities) {
        entity_ids.insert(candidate.entity_id);
    }
    bool found_enum_member = false;
    for (const SemanticNode &candidate : index.nodes) {
        if (candidate.ast_kind != "MemberExpr" ||
            candidate.value_type.kind != ValueKind::Enumeration ||
            !candidate.access_path) {
            continue;
        }
        found_enum_member = true;
        require(candidate.access_path->fields.empty() &&
                    entity_ids.contains(candidate.access_path->root_entity_id),
                "enum constant is a root entity, not a synthetic object field");
    }
    require(found_enum_member,
            "non-field enum MemberExpr is represented explicitly");
    std::filesystem::remove_all(root, error);
}

SemanticNode path_node(
    std::string id, std::string entity_id, std::string owner,
    AccessPath path, SourceLocation location) {
    SemanticNode node;
    node.node_id = std::move(id);
    node.kind = SemanticNodeKind::Memory;
    node.entity_id = std::move(entity_id);
    node.owner_function_id = std::move(owner);
    node.access_path = std::move(path);
    node.abstract_object_id = "object.shared";
    node.value_type = integer_type();
    node.location = std::move(location);
    node.ast_kind = "DeclRefExpr";
    return node;
}

SemanticIndex context_fixture() {
    SemanticIndex index;
    index.artifact_id = "index.context";
    index.compilation_database_sha256 = std::string(64, '5');
    index.source_identity_root = "/fixture";
    index.status = StageStatus::Complete;
    index.translation_units.push_back({
        "tu.context", "src/neutral.cc", "c++", "/fixture",
        std::string(64, '6'), StageStatus::Complete, {}, {}});
    index.entities = {
        entity("entity.main", EntityKind::Function, "main:int ()", "int ()"),
        entity("entity.helper", EntityKind::Function, "helper:int (int)", "int (int)"),
        entity("entity.param", EntityKind::Parameter, "helper::value:int", "int"),
        entity("entity.source-a", EntityKind::Local, "main::source_a:int", "int"),
        entity("entity.source-b", EntityKind::Local, "main::source_b:int", "int"),
        entity("entity.result-a", EntityKind::Local, "main::result_a:int", "int"),
        entity("entity.result-b", EntityKind::Local, "main::result_b:int", "int"),
        entity("entity.call-a", EntityKind::Synthetic, "call-a:int", "int"),
        entity("entity.call-b", EntityKind::Synthetic, "call-b:int", "int"),
        entity("entity.shared", EntityKind::Local, "main::shared:NeutralState", "NeutralState"),
        entity("entity.shared-field", EntityKind::Field, "NeutralState::ready:int", "int"),
    };
    for (EntityRef &item : index.entities) {
        item.translation_unit_ids.clear();
        item.translation_unit_ids.insert("tu.context");
    }
    index.abstract_objects.push_back({
        "object.shared", ObjectAbstraction::Stack, at(20, 3), Certainty::Must});
    SemanticNode source_a = path_node(
        "node.source-a", "entity.source-a", "entity.main",
        {"entity.source-a", 0, {}, false}, at(20, 3));
    source_a.abstract_object_id.reset();
    SemanticNode source_b = path_node(
        "node.source-b", "entity.source-b", "entity.main",
        {"entity.source-b", 0, {}, false}, at(21, 3));
    source_b.abstract_object_id.reset();
    SemanticNode result_a = path_node(
        "node.result-a", "entity.result-a", "entity.main",
        {"entity.result-a", 0, {}, false}, at(24, 3));
    result_a.abstract_object_id.reset();
    SemanticNode result_b = path_node(
        "node.result-b", "entity.result-b", "entity.main",
        {"entity.result-b", 0, {}, false}, at(25, 3));
    result_b.abstract_object_id.reset();
    SemanticNode parameter = path_node(
        "node.param", "entity.param", "entity.helper",
        {"entity.param", 0, {}, false}, at(5, 12));
    parameter.abstract_object_id.reset();
    SemanticNode returned;
    returned.node_id = "node.return";
    returned.kind = SemanticNodeKind::ReturnSite;
    returned.entity_id = "entity.helper";
    returned.owner_function_id = "entity.helper";
    returned.value_type = integer_type();
    returned.location = at(5, 1);
    returned.ast_kind = "ReturnSlot";
    SemanticNode call_a;
    call_a.node_id = "node.call-a";
    call_a.kind = SemanticNodeKind::CallSite;
    call_a.entity_id = "entity.call-a";
    call_a.owner_function_id = "entity.main";
    call_a.value_type = integer_type();
    call_a.location = at(24, 18);
    call_a.ast_kind = "CallExpr";
    SemanticNode call_b = call_a;
    call_b.node_id = "node.call-b";
    call_b.entity_id = "entity.call-b";
    call_b.location = at(25, 18);
    const AccessPath shared{
        "entity.shared", 0, {"entity.shared-field"}, false};
    SemanticNode write_one = path_node(
        "node.write-one", "entity.shared", "entity.main", shared,
        at(27, 3, 27, 14));
    SemanticNode write_two = path_node(
        "node.write-two", "entity.shared", "entity.main", shared,
        at(30, 3, 30, 14));
    SemanticNode read = path_node(
        "node.read", "entity.shared", "entity.main", shared,
        at(32, 9, 32, 20));
    index.nodes = {
        source_a, source_b, result_a, result_b, parameter, returned,
        call_a, call_b, write_one, write_two, read};
    auto relation = [](std::string id, std::string from, std::string to) {
        SemanticRelation result;
        result.relation_id = std::move(id);
        result.source_node_id = std::move(from);
        result.target_node_id = std::move(to);
        result.kind = RelationKind::Data;
        result.certainty = Certainty::May;
        result.evidence.push_back({
            "evidence." + result.relation_id, "ast_semantics", Certainty::May,
            "fixture flow", "fixture", std::nullopt});
        return result;
    };
    index.relations = {
        relation("relation.param-return", "node.param", "node.return"),
        relation("relation.call-a-result", "node.call-a", "node.result-a"),
        relation("relation.call-b-result", "node.call-b", "node.result-b"),
        relation("relation.write-order", "node.write-one", "node.write-two"),
        relation("relation.read-order", "node.write-two", "node.read"),
    };
    FunctionSummary helper;
    helper.function_entity_id = "entity.helper";
    helper.parameter_node_ids = {"node.param"};
    helper.return_node_id = "node.return";
    helper.owned_node_ids = {"node.param", "node.return"};
    helper.relation_ids = {"relation.param-return"};
    FunctionSummary main;
    main.function_entity_id = "entity.main";
    main.owned_node_ids = {
        "node.source-a", "node.source-b", "node.result-a", "node.result-b",
        "node.call-a", "node.call-b", "node.write-one", "node.write-two",
        "node.read"};
    main.relation_ids = {
        "relation.call-a-result", "relation.call-b-result",
        "relation.write-order", "relation.read-order"};
    main.callsite_ids = {"callsite.a", "callsite.b"};
    index.function_summaries = {helper, main};
    CallSiteSummary first;
    first.callsite_id = "callsite.a";
    first.caller_function_id = "entity.main";
    first.candidate_callee_ids = {"entity.helper"};
    first.argument_node_ids = {"node.source-a"};
    first.argument_node_groups = {{"node.source-a"}};
    first.argument_is_address = {false};
    first.result_node_id = "node.call-a";
    first.location = at(24, 18);
    first.direct = true;
    first.status = StageStatus::Complete;
    CallSiteSummary second = first;
    second.callsite_id = "callsite.b";
    second.argument_node_ids = {"node.source-b"};
    second.argument_node_groups = {{"node.source-b"}};
    second.result_node_id = "node.call-b";
    second.location = at(25, 18);
    index.callsites = {first, second};
    return index;
}

bool graph_reaches(
    const ContextualInfluenceGraph &graph, const std::string &source,
    const std::string &target) {
    std::map<std::string, std::vector<std::string>> outgoing;
    for (const InfluenceEdge &edge : graph.edges) {
        outgoing[edge.source_node_id].push_back(edge.target_node_id);
    }
    std::deque<std::string> worklist{source};
    std::set<std::string> seen{source};
    while (!worklist.empty()) {
        const std::string current = worklist.front();
        worklist.pop_front();
        if (current == target) {
            return true;
        }
        for (const std::string &next : outgoing[current]) {
            if (seen.insert(next).second) {
                worklist.push_back(next);
            }
        }
    }
    return false;
}

void test_context_and_program_point_identity() {
    const ContextualInfluenceGraph graph = build_contextual_influence_graph(
        context_fixture(), std::string(64, '7'));
    require(graph.status != StageStatus::Failed, "context graph validates");
    for (const ContextualNode &node : graph.nodes) {
        if (node.semantic_node_id == "node.param" ||
            node.semantic_node_id == "node.return") {
            require(
                !node.call_context.callsite_ids.empty(),
                "callee formal/return has no uncontextualized root instance");
        }
    }
    std::string source_a;
    std::string result_b;
    std::set<std::string> field_program_points;
    std::set<const EntityRef *> field_entity_instances;
    for (const ContextualNode &node : graph.nodes) {
        if (node.semantic_node_id == "node.source-a" &&
            node.call_context.callsite_ids.empty()) {
            source_a = node.node_id;
        }
        if (node.semantic_node_id == "node.result-b" &&
            node.call_context.callsite_ids.empty()) {
            result_b = node.node_id;
        }
        if (node.semantic_node_id == "node.write-one" ||
            node.semantic_node_id == "node.write-two" ||
            node.semantic_node_id == "node.read") {
            field_program_points.insert(node.node_id);
            field_entity_instances.insert(node.entity.get());
        }
    }
    require(!source_a.empty() && !result_b.empty(), "entry nodes instantiated");
    require(
        !graph_reaches(graph, source_a, result_b),
        "call A source cannot flow through shared formal into call B result");
    require(
        field_program_points.size() == 3,
        "same object/field retains three distinct program-point nodes");
    require(
        field_entity_instances.size() == 1,
        "same source entity metadata is interned across contextual nodes");
}

void test_callsite_argument_group_validation() {
    const SemanticIndex valid = context_fixture();
    require(
        validate_semantic_index(valid).empty(),
        "callsite positional argument fixture validates");

    SemanticIndex arity_mismatch = valid;
    arity_mismatch.callsites[0].argument_is_address.clear();
    require(
        contains_error(
            validate_semantic_index(arity_mismatch), "arity mismatch"),
        "semantic index rejects positional address arity mismatch");

    SemanticIndex unknown_group_node = valid;
    unknown_group_node.callsites[0].argument_node_groups[0][0] =
        "node.absent";
    require(
        contains_error(
            validate_semantic_index(unknown_group_node),
            "positional argument group references unknown node"),
        "semantic index closes positional argument node references");

    SemanticIndex divergent_flat_group = valid;
    divergent_flat_group.callsites[0].argument_node_groups[0][0] =
        "node.source-b";
    require(
        contains_error(
            validate_semantic_index(divergent_flat_group),
            "flat and positional argument references disagree"),
        "semantic index rejects divergent flat/positional call arguments");
}

bool contains_error(
    const std::vector<std::string> &errors, const std::string &needle) {
    return std::any_of(
        errors.begin(), errors.end(), [&](const std::string &error) {
            return error.find(needle) != std::string::npos;
        });
}

const ConeMember &cone_member(
    const ApInfluenceCone &cone, const std::string &node_id) {
    const auto member = std::find_if(
        cone.members.begin(), cone.members.end(),
        [&](const ConeMember &item) { return item.node_id == node_id; });
    require(member != cone.members.end(), "expected cone member is present");
    return *member;
}

TypedPropertyIr single_ap_property(const std::string &ap_id) {
    TypedPropertyIr property;
    AtomicProposition ap;
    ap.ap_id = ap_id;
    ap.roles = {ApRole::State};
    property.atomic_propositions.push_back(std::move(ap));
    return property;
}

ContextualNode cone_node(
    const std::string &node_id, const std::string &semantic_node_id) {
    ContextualNode node;
    node.node_id = node_id;
    node.semantic_node_id = semantic_node_id;
    return node;
}

InfluenceEdge cone_edge(
    const std::string &edge_id, const std::string &source,
    const std::string &target, Certainty certainty,
    std::vector<std::string> uncertainty_reasons = {}) {
    InfluenceEdge edge;
    edge.edge_id = edge_id;
    edge.source_node_id = source;
    edge.target_node_id = target;
    edge.certainty = certainty;
    edge.uncertainty_reasons = std::move(uncertainty_reasons);
    return edge;
}

void test_influence_cone_certainty_is_conservative() {
    const std::string bindings_sha256(64, 'a');
    const std::string graph_sha256(64, 'b');

    {
        const TypedPropertyIr property = single_ap_property("ap.candidate-root");
        ContextualInfluenceGraph graph;
        graph.status = StageStatus::Complete;
        graph.nodes.push_back(cone_node("graph.candidate-root", "semantic.root"));

        ApBindings bindings;
        bindings.status = StageStatus::ConservativeIncomplete;
        ApRoleBinding role;
        role.ap_id = "ap.candidate-root";
        role.role = ApRole::State;
        role.resolution = BindingResolution::Ambiguous;
        BindingCandidate candidate;
        candidate.binding_id = "binding.candidate-root";
        candidate.status = CandidateStatus::Candidate;
        candidate.semantic_node_ids = {"semantic.root"};
        role.candidates.push_back(std::move(candidate));
        bindings.bindings.push_back(std::move(role));

        const ApInfluenceCones cones = compute_influence_cones(
            property, bindings, graph, bindings_sha256, graph_sha256);
        require(cones.status != StageStatus::Failed && cones.cones.size() == 1,
                "candidate-root cone computes");
        require(
            cone_member(cones.cones.front(), "graph.candidate-root").membership !=
                ConeMembership::MustInfluence,
            "non-confirmed binding root is never MUST");
    }

    {
        const TypedPropertyIr property = single_ap_property("ap.multi-root");
        ContextualInfluenceGraph graph;
        graph.status = StageStatus::Complete;
        graph.nodes = {
            cone_node("graph.root-a", "semantic.root-a"),
            cone_node("graph.root-b", "semantic.root-b"),
        };

        ApBindings bindings;
        bindings.status = StageStatus::Complete;
        ApRoleBinding role;
        role.ap_id = "ap.multi-root";
        role.role = ApRole::State;
        role.resolution = BindingResolution::Confirmed;
        BindingCandidate candidate;
        candidate.binding_id = "binding.multi-root";
        candidate.status = CandidateStatus::Confirmed;
        candidate.semantic_node_ids = {"semantic.root-a", "semantic.root-b"};
        role.candidates.push_back(std::move(candidate));
        bindings.bindings.push_back(std::move(role));

        const ApInfluenceCones cones = compute_influence_cones(
            property, bindings, graph, bindings_sha256, graph_sha256);
        require(cones.status != StageStatus::Failed && cones.cones.size() == 1,
                "multi-root cone computes");
        require(
            cone_member(cones.cones.front(), "graph.root-a").membership !=
                    ConeMembership::MustInfluence &&
                cone_member(cones.cones.front(), "graph.root-b").membership !=
                    ConeMembership::MustInfluence,
            "non-unique confirmed roots are never MUST");
    }

    {
        const TypedPropertyIr property = single_ap_property("ap.path-merge");
        ContextualInfluenceGraph graph;
        graph.status = StageStatus::Complete;
        graph.nodes = {
            cone_node("graph.may-source", "semantic.may-source"),
            cone_node("graph.unknown-source", "semantic.unknown-source"),
            cone_node("graph.only-unknown", "semantic.only-unknown"),
            cone_node("graph.cycle-source", "semantic.cycle-source"),
            cone_node("graph.cycle-middle", "semantic.cycle-middle"),
            cone_node("graph.unique-root", "semantic.unique-root"),
        };
        graph.edges = {
            cone_edge("edge.may-must", "graph.may-source", "graph.unique-root",
                      Certainty::Must),
            cone_edge("edge.may-weak", "graph.may-source", "graph.unique-root",
                      Certainty::May),
            cone_edge("edge.unknown-must", "graph.unknown-source",
                      "graph.unique-root", Certainty::Must),
            cone_edge("edge.unknown-weak", "graph.unknown-source",
                      "graph.unique-root", Certainty::Unknown,
                      {"alternate path certainty is unknown"}),
            cone_edge("edge.only-unknown", "graph.only-unknown",
                      "graph.unique-root", Certainty::Unknown,
                      {"only path certainty is unknown"}),
            cone_edge("edge.cycle-root", "graph.cycle-middle",
                      "graph.unique-root", Certainty::Must),
            cone_edge("edge.cycle-forward", "graph.cycle-source",
                      "graph.cycle-middle", Certainty::Must),
            cone_edge("edge.cycle-back", "graph.cycle-middle",
                      "graph.cycle-source", Certainty::May),
        };

        ApBindings bindings;
        bindings.status = StageStatus::Complete;
        ApRoleBinding role;
        role.ap_id = "ap.path-merge";
        role.role = ApRole::State;
        role.resolution = BindingResolution::Confirmed;
        BindingCandidate candidate;
        candidate.binding_id = "binding.path-merge";
        candidate.status = CandidateStatus::Confirmed;
        candidate.semantic_node_ids = {"semantic.unique-root"};
        role.candidates.push_back(std::move(candidate));
        bindings.bindings.push_back(std::move(role));

        const ApInfluenceCones cones = compute_influence_cones(
            property, bindings, graph, bindings_sha256, graph_sha256);
        require(cones.status != StageStatus::Failed && cones.cones.size() == 1,
                "path-merge cone computes");
        const ApInfluenceCone &cone = cones.cones.front();
        require(
            cone_member(cone, "graph.unique-root").membership ==
                ConeMembership::MustInfluence,
            "unique confirmed root remains MUST");
        require(
            cone_member(cone, "graph.may-source").membership ==
                ConeMembership::MayInfluence,
            "MAY alternate path prevents false MUST");
        require(
            cone_member(cone, "graph.unknown-source").membership ==
                ConeMembership::MayInfluence,
            "known influence remains actionable beside an unknown alternate path");
        require(
            cone_member(cone, "graph.only-unknown").membership ==
                ConeMembership::UnknownInfluence,
            "a source with only unknown paths remains UNKNOWN");
        require(
            cone_member(cone, "graph.cycle-source").membership ==
                    ConeMembership::MayInfluence &&
                cone_member(cone, "graph.cycle-middle").membership ==
                    ConeMembership::MayInfluence,
            "weaker cyclic alternate path prevents false MUST");

        ContextualInfluenceGraph reversed_graph = graph;
        std::reverse(
            reversed_graph.edges.begin(), reversed_graph.edges.end());
        const ApInfluenceCones reversed = compute_influence_cones(
            property, bindings, reversed_graph, bindings_sha256, graph_sha256);
        require(
            reversed.status != StageStatus::Failed &&
                reversed.cones.size() == 1,
            "reversed-edge cone computes");
        const ApInfluenceCone &reversed_cone = reversed.cones.front();
        require(
            cone.edge_ids == reversed_cone.edge_ids &&
                cone.members.size() == reversed_cone.members.size(),
            "cone evidence set is independent of graph edge order");
        for (std::size_t index = 0; index < cone.members.size(); ++index) {
            require(
                cone.members[index].node_id ==
                        reversed_cone.members[index].node_id &&
                    cone.members[index].membership ==
                        reversed_cone.members[index].membership &&
                    cone.members[index].witness_edge_ids ==
                        reversed_cone.members[index].witness_edge_ids &&
                    cone.members[index].uncertainty_reasons ==
                        reversed_cone.members[index].uncertainty_reasons,
                "cone member certificate is independent of graph edge order");
        }
    }
}

void test_influence_cone_certificate_closure() {
    ContextualInfluenceGraph graph;
    graph.nodes.resize(3);
    graph.nodes[0].node_id = "graph.source";
    graph.nodes[1].node_id = "graph.middle";
    graph.nodes[2].node_id = "graph.root";
    InfluenceEdge first;
    first.edge_id = "edge.source-middle";
    first.source_node_id = "graph.source";
    first.target_node_id = "graph.middle";
    first.certainty = Certainty::May;
    InfluenceEdge second;
    second.edge_id = "edge.middle-root";
    second.source_node_id = "graph.middle";
    second.target_node_id = "graph.root";
    second.certainty = Certainty::May;
    graph.edges = {first, second};

    ApBindings bindings;
    ApRoleBinding role;
    role.ap_id = "ap.certificate";
    role.role = ApRole::State;
    role.resolution = BindingResolution::Confirmed;
    BindingCandidate candidate;
    candidate.binding_id = "binding.certificate";
    candidate.status = CandidateStatus::Confirmed;
    role.candidates.push_back(candidate);
    bindings.bindings.push_back(role);

    ApInfluenceCones cones;
    cones.artifact_id = "cones.certificate";
    cones.ap_bindings_sha256 = std::string(64, '8');
    cones.graph_sha256 = std::string(64, '9');
    cones.status = StageStatus::Complete;
    ApInfluenceCone cone;
    cone.cone_id = "cone.certificate";
    cone.ap_id = "ap.certificate";
    cone.roles = {ApRole::State};
    cone.status = StageStatus::Complete;
    CandidateAccount account;
    account.binding_id = "binding.certificate";
    account.disposition = CandidateDisposition::Included;
    account.root_node_ids = {"graph.root"};
    cone.candidate_accounting.push_back(account);
    ConeMember source;
    source.node_id = "graph.source";
    source.membership = ConeMembership::MayInfluence;
    source.witness_edge_ids = {
        "edge.source-middle", "edge.middle-root"};
    ConeMember middle;
    middle.node_id = "graph.middle";
    middle.membership = ConeMembership::MayInfluence;
    middle.witness_edge_ids = {"edge.middle-root"};
    ConeMember root;
    root.node_id = "graph.root";
    root.membership = ConeMembership::MustInfluence;
    cone.members = {source, middle, root};
    cone.edge_ids = {"edge.source-middle", "edge.middle-root"};
    cones.cones.push_back(cone);
    ArtifactDigests expected;
    expected.ap_bindings_sha256 = cones.ap_bindings_sha256;
    expected.graph_sha256 = cones.graph_sha256;

    require(
        validate_influence_cones(cones, bindings, graph, expected).empty(),
        "continuous source-to-root cone certificate validates");

    ApBindings nonconfirmed_root = bindings;
    nonconfirmed_root.bindings[0].resolution = BindingResolution::Ambiguous;
    nonconfirmed_root.bindings[0].candidates[0].status =
        CandidateStatus::Candidate;
    require(
        contains_error(
            validate_influence_cones(
                cones, nonconfirmed_root, graph, expected),
            "MUST cone root is not uniquely confirmed"),
        "validator rejects false-MUST root certificate");

    ApInfluenceCones wrong_path_class = cones;
    wrong_path_class.cones[0].members[0].membership =
        ConeMembership::MustInfluence;
    require(
        contains_error(
            validate_influence_cones(
                wrong_path_class, bindings, graph, expected),
            "cone membership does not match path-class fixed point"),
        "validator independently recomputes path-class membership");

    ApInfluenceCones missing_role_root = cones;
    missing_role_root.cones[0].roles.push_back(ApRole::Guard);
    require(
        contains_error(
            validate_influence_cones(
                missing_role_root, bindings, graph, expected),
            "MUST cone root is not uniquely confirmed"),
        "validator rejects MUST root with an unbound AP role");

    ApInfluenceCones missing_root = cones;
    missing_root.cones[0].members.pop_back();
    require(
        contains_error(
            validate_influence_cones(
                missing_root, bindings, graph, expected),
            "included candidate root is absent"),
        "validator rejects included root outside cone members");

    ApInfluenceCones no_witness = cones;
    no_witness.cones[0].members[0].witness_edge_ids.clear();
    require(
        contains_error(
            validate_influence_cones(no_witness, bindings, graph, expected),
            "non-root cone member has no witness"),
        "validator rejects non-root member without root witness");

    ApInfluenceCones edge_outside_set = cones;
    edge_outside_set.cones[0].edge_ids.erase(
        edge_outside_set.cones[0].edge_ids.begin());
    require(
        contains_error(
            validate_influence_cones(
                edge_outside_set, bindings, graph, expected),
            "outside cone.edge_ids"),
        "validator rejects witness edge outside the cone edge set");

    ApInfluenceCones discontinuous = cones;
    std::reverse(
        discontinuous.cones[0].members[0].witness_edge_ids.begin(),
        discontinuous.cones[0].members[0].witness_edge_ids.end());
    require(
        contains_error(
            validate_influence_cones(
                discontinuous, bindings, graph, expected),
            "not a continuous source-to-root path"),
        "validator rejects a discontinuous witness ordering");
}

}  // namespace

int main() {
    test_relational_composite_binding();
    test_binding_candidate_top1_order();
    test_role_dnf_binding_isolates_roles_and_alternatives();
    test_typed_field_selector_matches_access_prefix();
    test_role_all_of_uses_direct_callsite_summary();
    test_compile_database_cwd_invariance();
    test_identity_v2_portability_and_fail_closed_paths();
    test_multi_tu_duplicate_merge_is_linear_and_deterministic();
    test_argument_exprsite_totality();
    test_cfg_postdominator_control();
    test_real_callsite_field_projection();
    test_unknown_call_effect_is_caller_context_bounded();
    test_non_field_member_access_has_entity_closed_path();
    test_context_and_program_point_identity();
    test_callsite_argument_group_validation();
    test_influence_cone_certainty_is_conservative();
    test_influence_cone_certificate_closure();
    std::cout << "PASS RIFT production relational binding smoke\n";
    return 0;
}
