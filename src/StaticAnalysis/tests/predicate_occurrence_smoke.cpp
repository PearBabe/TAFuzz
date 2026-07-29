#include "rift/core/production.h"

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unistd.h>
#include <vector>

namespace {

using namespace rift::core;

void require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

ValueType boolean_type() {
    ValueType type;
    type.kind = ValueKind::Boolean;
    type.canonical = "bool";
    type.bit_width = 8;
    return type;
}

ValueType integer_type() {
    ValueType type;
    type.kind = ValueKind::Integer;
    type.canonical = "int";
    type.bit_width = 32;
    type.is_signed = true;
    return type;
}

ValueType unsigned_integer_type(std::uint32_t bit_width) {
    ValueType type;
    type.kind = ValueKind::Integer;
    type.canonical = bit_width == 16 ? "uint16_t" : "unsigned";
    type.bit_width = bit_width;
    type.is_signed = false;
    return type;
}

ValueType floating_type() {
    ValueType type;
    type.kind = ValueKind::Floating;
    type.canonical = "float";
    type.bit_width = 32;
    return type;
}

ExpressionStructure reference(const std::string &selector_id) {
    ExpressionStructure expression;
    expression.node_kind = "reference";
    expression.value_type = integer_type();
    expression.referenced_selector_id = selector_id;
    return expression;
}

ExpressionStructure literal_one() {
    ExpressionStructure expression;
    expression.node_kind = "literal";
    expression.value_type = integer_type();
    expression.literal = LiteralValue{LiteralKind::Integer, "1"};
    return expression;
}

ExpressionStructure comparison(
    ExpressionStructure left, ExpressionStructure right) {
    ExpressionStructure expression;
    expression.node_kind = "comparison";
    expression.operation = ">";
    expression.value_type = boolean_type();
    expression.operands = {std::move(left), std::move(right)};
    return expression;
}

Selector location_selector(
    const std::string &id, std::uint32_t line, std::uint32_t column,
    std::string file = "fixture.cpp") {
    Selector selector;
    selector.selector_id = id;
    selector.kind = SelectorKind::SourceLocation;
    selector.location = SourceLocation{
        std::move(file), line, column, line, column, "spelling", {}};
    selector.value_type = integer_type();
    return selector;
}

AtomicProposition proposition(
    const std::string &ap_id, ExpressionStructure predicate,
    const std::vector<std::string> &selector_ids) {
    AtomicProposition ap;
    ap.ap_id = ap_id;
    ap.roles = {ApRole::State};
    ap.value_type = boolean_type();
    ap.predicate = std::move(predicate);
    RoleSelectorGroup group;
    group.group_id = "group-" + ap_id;
    group.role = ApRole::State;
    group.selector_ids = selector_ids;
    ap.role_selector_groups.push_back(std::move(group));
    return ap;
}

TypedPropertyIr make_property() {
    TypedPropertyIr property;
    property.schema_version = "2.0.0";
    property.artifact_id = stable_id("property", "predicate-occurrence-smoke");
    property.artifact_sha256 = sha256_hex("predicate-occurrence-smoke-property");
    property.property_id = "property-occurrence-smoke";
    property.logic = "MITL";
    property.time_domain = "discrete";
    property.formula_text = "ap-single && ap-pair && ap-missing";
    property.formula.node_id = "formula-root";
    property.formula.operation = FormulaOperator::True;

    property.selectors = {
        location_selector("selector-single", 5, 23),
        location_selector("selector-left", 6, 21),
        location_selector("selector-member", 6, 36),
        location_selector("selector-missing", 99, 1),
        location_selector("selector-alias", 9, 41),
        location_selector("selector-macro", 11, 49),
        location_selector("selector-shared", 1, 46, "shared.h"),
    };
    property.atomic_propositions.push_back(proposition(
        "ap-single", comparison(reference("selector-single"), literal_one()),
        {"selector-single"}));
    property.atomic_propositions.push_back(proposition(
        "ap-pair",
        comparison(reference("selector-left"), reference("selector-member")),
        {"selector-left", "selector-member"}));
    property.atomic_propositions.push_back(proposition(
        "ap-missing", reference("selector-missing"),
        {"selector-missing"}));
    property.atomic_propositions.push_back(proposition(
        "ap-alias", comparison(reference("selector-alias"), literal_one()),
        {"selector-alias"}));
    property.atomic_propositions.push_back(proposition(
        "ap-macro", comparison(reference("selector-macro"), literal_one()),
        {"selector-macro"}));
    property.atomic_propositions.push_back(proposition(
        "ap-shared", comparison(reference("selector-shared"), literal_one()),
        {"selector-shared"}));
    return property;
}

CompilationCommand command_for(
    const std::filesystem::path &directory,
    const std::filesystem::path &source,
    const std::vector<LogicalPathRoot> &roots) {
    CompilationCommand command;
    command.working_directory = directory.string();
    command.source_file = source.string();
    command.arguments = {
        "clang++-18", "-std=c++20", "-fsyntax-only", source.string()};
    command.logical_working_directory =
        logical_identity_path(roots, directory).value();
    command.logical_source_file =
        logical_identity_path(roots, source).value();
    command.raw_command_sha256 = sha256_hex(
        command.working_directory + '\0' + command.source_file);
    command.command_sha256 = sha256_hex(
        command.logical_working_directory + '\0' + command.logical_source_file);
    command.translation_unit_id = stable_id(
        "tu", command.logical_source_file + '\0' + command.command_sha256);
    return command;
}

const PredicateSelectorAccount &account(
    const PredicateOccurrenceBindings &bindings, const std::string &selector_id) {
    const auto found = std::find_if(
        bindings.selector_accounts.begin(), bindings.selector_accounts.end(),
        [&](const PredicateSelectorAccount &candidate) {
            return candidate.selector_id == selector_id;
        });
    require(found != bindings.selector_accounts.end(),
            "missing selector account " + selector_id);
    return *found;
}

const PredicateOccurrence &occurrence(
    const PredicateOccurrenceBindings &bindings,
    const std::string &selector_id) {
    const auto found = std::find_if(
        bindings.occurrences.begin(), bindings.occurrences.end(),
        [&](const PredicateOccurrence &candidate) {
            return candidate.selector_id == selector_id;
        });
    require(found != bindings.occurrences.end(),
            "missing occurrence " + selector_id);
    return *found;
}

void write_file(const std::filesystem::path &path, const std::string &contents) {
    std::ofstream stream(path, std::ios::binary);
    require(stream.good(), "could not create fixture " + path.string());
    stream << contents;
    require(stream.good(), "could not write fixture " + path.string());
}

}  // namespace

int main(int argc, char **argv) {
    namespace fs = std::filesystem;
    const fs::path fixture = fs::temp_directory_path() /
                             ("rift-predicate-occurrence-" +
                              std::to_string(static_cast<long long>(::getpid())));
    std::error_code error;
    fs::remove_all(fixture, error);
    fs::create_directories(fixture);
    try {
        const fs::path source = fixture / "fixture.cpp";
        const fs::path unrelated = fixture / "unrelated.cpp";
        const fs::path other = fixture / "other.cpp";
        const fs::path shared = fixture / "shared.h";
        write_file(
            source,
            "struct Box {\n"
            "  int threshold;\n"
            "};\n"
            "int evaluate(int observed, Box box) {\n"
            "  const bool single = observed > 1;\n"
            "  const bool pair = observed > box.threshold;\n"
            "  return single || pair;\n"
            "}\n"
            "int via_pointer(Box *box) { return box->threshold; }\n"
            "#define READ_VALUE(x) (x)\n"
            "int via_macro(int observed) { return READ_VALUE(observed); }\n"
            "#include \"shared.h\"\n");
        write_file(
            unrelated,
            "int unrelated(int value) { return value + 1; }\n"
            "#include \"shared.h\"\n");
        write_file(other, "int other(int value) { return value - 1; }\n");
        write_file(
            shared,
            "inline int shared_value(int source) { return source; }\n");

        CompilationPlan plan;
        plan.compilation_database_path = (fixture / "compile_commands.json").string();
        plan.compilation_database_sha256 = sha256_hex("physical-compile-db");
        plan.canonical_compilation_database_sha256 =
            sha256_hex("canonical-compile-db");
        plan.identity_roots = {{"source", fixture}};
        plan.path_map_sha256 = identity_path_map_sha256(plan.identity_roots);
        plan.source_identity_root =
            std::string(kIdentityScheme) + ':' + plan.path_map_sha256;
        plan.status = StageStatus::Complete;
        plan.commands = {
            command_for(fixture, source, plan.identity_roots),
            command_for(fixture, unrelated, plan.identity_roots),
            command_for(fixture, other, plan.identity_roots),
        };
        std::sort(
            plan.commands.begin(), plan.commands.end(),
            [](const CompilationCommand &left,
               const CompilationCommand &right) {
                return left.translation_unit_id < right.translation_unit_id;
            });

        SemanticIndex index = build_semantic_index(plan);
        if (index.status == StageStatus::Failed) {
            std::string detail = "fixture semantic index failed";
            for (const std::string &diagnostic : index.diagnostics) {
                detail += " | " + diagnostic;
            }
            for (const CoverageGap &gap : index.coverage_gaps) {
                detail += " | " + gap.kind + ": " + gap.detail;
            }
            throw std::runtime_error(detail);
        }
        require(index.translation_units.size() == 3,
                "fixture must contain three indexed translation units");
        const auto index_snapshot = std::make_tuple(
            index.artifact_id, index.entities.size(), index.nodes.size(),
            index.relations.size(), index.translation_units.size());

        TypedPropertyIr property = make_property();
        const std::string semantic_sha =
            sha256_hex("predicate-occurrence-smoke-index");
        const PredicateOccurrenceBindings bindings =
            bind_predicate_occurrences(plan, property, index, semantic_sha);
        if (bindings.status != StageStatus::ConservativeIncomplete) {
            std::string detail =
                "one unmatched selector must make the sidecar conservative; status=" +
                std::string(to_string(bindings.status));
            for (const std::string &diagnostic : bindings.diagnostics) {
                detail += " | " + diagnostic;
            }
            throw std::runtime_error(detail);
        }
        require(bindings.m4_index_immutable,
                "sidecar must attest immutable M4 input");
        require(bindings.candidate_accounting_complete,
                "unmatched token is accounted for, not resource-truncated");
        require(bindings.eligible_translation_units == 2 &&
                    bindings.parsed_translation_units == 2 &&
                    bindings.skipped_translation_units == 0,
                "only property-referenced translation units may be parsed");
        require(bindings.selector_accounts.size() == 7,
                "all seven referenced selectors require an account");
        require(bindings.occurrences.size() == 7,
                "five unique and two header-context source tokens should be observed");
        require(index_snapshot == std::make_tuple(
                    index.artifact_id, index.entities.size(), index.nodes.size(),
                    index.relations.size(), index.translation_units.size()),
                "occurrence binding mutated the M4 semantic index");

        const PredicateSelectorAccount &single_account =
            account(bindings, "selector-single");
        require(
            single_account.resolution == PredicateOccurrenceResolution::Exact &&
                single_account.occurrence_ids.size() == 1 &&
                single_account.expected_value_type == integer_type(),
            "single DeclRef selector did not resolve exactly");
        const PredicateOccurrence &single =
            occurrence(bindings, "selector-single");
        require(single.kind == PredicateOccurrenceKind::DeclRef &&
                    single.spelling_location.line == 5 &&
                    single.spelling_location.column == 23 &&
                    single.semantic_node_ids.size() == 1,
                "single reference lost its precise token or M4 root node");

        const PredicateOccurrence &left =
            occurrence(bindings, "selector-left");
        const PredicateOccurrence &member =
            occurrence(bindings, "selector-member");
        require(left.kind == PredicateOccurrenceKind::DeclRef &&
                    left.predicate_paths ==
                        std::vector<std::string>{"predicate.operands[0]"},
                "left side of the dynamic comparison was not retained");
        require(member.kind == PredicateOccurrenceKind::MemberExpr &&
                    member.predicate_paths ==
                        std::vector<std::string>{"predicate.operands[1]"},
                "right side of the dynamic comparison was not retained");
        require(member.access_path &&
                    member.access_path->dereference_depth == 0 &&
                    member.access_path->fields.size() == 1 &&
                    !member.access_path->unknown_suffix &&
                    member.member_base_entity_id ==
                        std::optional<std::string>(
                            member.access_path->root_entity_id) &&
                    member.member_abstract_object_id.has_value() &&
                    member.semantic_node_ids.size() == 1,
                "direct MemberExpr did not preserve a proven M4 base/object/access path");
        require(
            account(bindings, "selector-left").resolution ==
                    PredicateOccurrenceResolution::Exact &&
                account(bindings, "selector-member").resolution ==
                    PredicateOccurrenceResolution::Exact,
            "both sides of a dynamic threshold must resolve independently");

        const PredicateSelectorAccount &missing =
            account(bindings, "selector-missing");
        require(missing.resolution == PredicateOccurrenceResolution::Unknown &&
                    missing.occurrence_ids.empty() &&
                    std::find(
                        missing.uncertainty_reasons.begin(),
                        missing.uncertainty_reasons.end(),
                        "predicate_occurrence_unmatched") !=
                        missing.uncertainty_reasons.end(),
                "unmatched selectors must remain explicitly UNKNOWN");

        const PredicateOccurrence &alias =
            occurrence(bindings, "selector-alias");
        require(
            alias.kind == PredicateOccurrenceKind::MemberExpr &&
                alias.resolution == PredicateOccurrenceResolution::Unknown &&
                std::find(
                    alias.uncertainty_reasons.begin(),
                    alias.uncertainty_reasons.end(),
                    "alias_resolution_required") !=
                    alias.uncertainty_reasons.end(),
            "pointer-member alias occurrence must fail closed as UNKNOWN");
        const PredicateOccurrence &macro =
            occurrence(bindings, "selector-macro");
        require(
            macro.resolution == PredicateOccurrenceResolution::Unknown &&
                !macro.spelling_location.macro_stack.empty() &&
                std::find(
                    macro.uncertainty_reasons.begin(),
                    macro.uncertainty_reasons.end(),
                    "macro_occurrence_requires_expansion_reasoning") !=
                    macro.uncertainty_reasons.end(),
            "macro occurrence must retain spelling/expansion provenance and remain UNKNOWN");

        const PredicateSelectorAccount &shared_account =
            account(bindings, "selector-shared");
        require(
            shared_account.resolution ==
                    PredicateOccurrenceResolution::Unknown &&
                shared_account.eligible_translation_unit_ids.size() == 2 &&
                shared_account.occurrence_ids.size() == 2 &&
                std::find(
                    shared_account.uncertainty_reasons.begin(),
                    shared_account.uncertainty_reasons.end(),
                    "multiple_predicate_occurrence_candidates") !=
                    shared_account.uncertainty_reasons.end(),
            "one header token in multiple TU contexts must remain total UNKNOWN");
        const bool all_shared_occurrences_unknown = std::all_of(
            bindings.occurrences.begin(), bindings.occurrences.end(),
            [](const PredicateOccurrence &candidate) {
                return candidate.selector_id != "selector-shared" ||
                       (candidate.resolution ==
                            PredicateOccurrenceResolution::Unknown &&
                        candidate.certainty == Certainty::Unknown);
            });
        require(
            all_shared_occurrences_unknown,
            "multi-candidate account leaked an exact occurrence claim");

        TypedPropertyIr reordered = property;
        std::reverse(
            reordered.atomic_propositions.begin(),
            reordered.atomic_propositions.end());
        std::reverse(reordered.selectors.begin(), reordered.selectors.end());
        const PredicateOccurrenceBindings second =
            bind_predicate_occurrences(plan, reordered, index, semantic_sha);
        require(
            canonical_predicate_occurrence_bindings_json(bindings) ==
                canonical_predicate_occurrence_bindings_json(second),
            "canonical occurrence bindings depend on Property IR array order");

        const std::vector<std::string> validation_errors =
            validate_predicate_occurrence_bindings(
                bindings, plan, property, index, semantic_sha);
        require(validation_errors.empty(),
                "in-memory occurrence contract validation failed");

        PredicateOccurrenceOptions bounded_options;
        bounded_options.maximum_occurrences = 1;
        const PredicateOccurrenceBindings bounded =
            bind_predicate_occurrences(
                plan, property, index, semantic_sha, bounded_options);
        const bool recorded_occurrence_guard = std::any_of(
            bounded.selector_accounts.begin(), bounded.selector_accounts.end(),
            [](const PredicateSelectorAccount &candidate) {
                return std::find(
                           candidate.uncertainty_reasons.begin(),
                           candidate.uncertainty_reasons.end(),
                           "occurrence_resource_guard_reached") !=
                       candidate.uncertainty_reasons.end();
            });
        require(
            bounded.observed_occurrences == 1 &&
                !bounded.candidate_accounting_complete &&
                bounded.status == StageStatus::ConservativeIncomplete &&
                recorded_occurrence_guard,
            "occurrence resource guard did not truncate deterministically and fail closed");
        require(
            validate_predicate_occurrence_bindings(
                bounded, plan, property, index, semantic_sha)
                .empty(),
            "resource-truncated occurrence artifact violated its schema contract");

        for (const ValueType &wrong_type :
             {unsigned_integer_type(16), floating_type()}) {
            TypedPropertyIr mismatched = property;
            const auto selector = std::find_if(
                mismatched.selectors.begin(), mismatched.selectors.end(),
                [](const Selector &candidate) {
                    return candidate.selector_id == "selector-single";
                });
            require(selector != mismatched.selectors.end(),
                    "type-mismatch fixture lost selector-single");
            selector->value_type = wrong_type;
            const auto ap = std::find_if(
                mismatched.atomic_propositions.begin(),
                mismatched.atomic_propositions.end(),
                [](const AtomicProposition &candidate) {
                    return candidate.ap_id == "ap-single";
                });
            require(ap != mismatched.atomic_propositions.end() &&
                        ap->predicate.operands.size() == 2,
                    "type-mismatch fixture lost ap-single predicate");
            ap->predicate.operands[0].value_type = wrong_type;
            ap->predicate.operands[1].value_type = wrong_type;

            const PredicateOccurrenceBindings wrong =
                bind_predicate_occurrences(
                    plan, mismatched, index, semantic_sha);
            const PredicateSelectorAccount &wrong_account =
                account(wrong, "selector-single");
            const PredicateOccurrence &wrong_occurrence =
                occurrence(wrong, "selector-single");
            require(
                wrong_account.expected_value_type == wrong_type &&
                    wrong_account.resolution ==
                        PredicateOccurrenceResolution::Unknown &&
                    wrong_occurrence.resolution ==
                        PredicateOccurrenceResolution::Unknown &&
                    std::find(
                        wrong_occurrence.uncertainty_reasons.begin(),
                        wrong_occurrence.uncertainty_reasons.end(),
                        "predicate_occurrence_type_mismatch") !=
                        wrong_occurrence.uncertainty_reasons.end(),
                "position-exact but type-incompatible predicate occurrence did not fail closed");
            require(
                validate_predicate_occurrence_bindings(
                    wrong, plan, mismatched, index, semantic_sha)
                    .empty(),
                "well-formed UNKNOWN type-mismatch artifact failed validation");
        }

        PredicateOccurrenceBindings type_tamper = bindings;
        const auto tampered_occurrence = std::find_if(
            type_tamper.occurrences.begin(), type_tamper.occurrences.end(),
            [](const PredicateOccurrence &candidate) {
                return candidate.selector_id == "selector-single";
            });
        require(tampered_occurrence != type_tamper.occurrences.end(),
                "type-tamper fixture lost selector-single occurrence");
        tampered_occurrence->value_type = floating_type();
        require(
            !validate_predicate_occurrence_bindings(
                 type_tamper, plan, property, index, semantic_sha)
                 .empty(),
            "validator accepted an EXACT occurrence whose type was tampered");

        PredicateOccurrenceBindings ledger_tamper = bindings;
        const auto downgraded = std::find_if(
            ledger_tamper.occurrences.begin(),
            ledger_tamper.occurrences.end(),
            [](const PredicateOccurrence &candidate) {
                return candidate.selector_id == "selector-single";
            });
        require(downgraded != ledger_tamper.occurrences.end(),
                "ledger-tamper fixture lost selector-single occurrence");
        downgraded->resolution = PredicateOccurrenceResolution::Unknown;
        downgraded->certainty = Certainty::Unknown;
        downgraded->uncertainty_reasons.push_back("tampered_resolution");
        require(
            !validate_predicate_occurrence_bindings(
                 ledger_tamper, plan, property, index, semantic_sha)
                 .empty(),
            "validator accepted an EXACT account backed by an UNKNOWN occurrence");

        if (argc == 3 && std::string(argv[1]) == "--emit") {
            write_file(
                argv[2], canonical_predicate_occurrence_bindings_json(bindings));
        } else {
            require(argc == 1,
                    "usage: rift_predicate_occurrence_smoke [--emit PATH]");
        }
        fs::remove_all(fixture, error);
        std::cout << "PASS predicate_occurrence_smoke\n";
        return EXIT_SUCCESS;
    } catch (const std::exception &failure) {
        fs::remove_all(fixture, error);
        std::cerr << "FAIL predicate_occurrence_smoke: " << failure.what()
                  << '\n';
        return EXIT_FAILURE;
    }
}
