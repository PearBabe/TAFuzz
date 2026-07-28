#ifndef RIFT_CORE_PREDICATE_OCCURRENCE_H
#define RIFT_CORE_PREDICATE_OCCURRENCE_H

#include "rift/core/artifacts.h"
#include "rift/core/index.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

// A source-location selector denotes an occurrence in the property predicate,
// not merely the declaration that Clang's M4 index associates with it.  This
// sidecar preserves that distinction without adding nodes to the frozen M4
// SemanticIndex or ContextualInfluenceGraph.
enum class PredicateOccurrenceKind {
    DeclRef,
    MemberExpr,
    Unknown,
};

enum class PredicateOccurrenceResolution {
    Exact,
    Ambiguous,
    Unknown,
};

struct PredicateOccurrenceOptions {
    // Guards are global per invocation.  Translation units and candidates are
    // admitted in canonical order, so reaching either guard is deterministic.
    std::uint32_t maximum_translation_units = 64;
    std::uint64_t maximum_occurrences = 100000;
    bool retain_macro_stack = true;
};

struct PredicateOccurrence {
    std::string occurrence_id;
    std::string ap_id;
    std::string selector_id;
    std::vector<ApRole> roles;
    // Root is "predicate"; operands append ".operands[N]".
    std::vector<std::string> predicate_paths;
    std::string translation_unit_id;
    PredicateOccurrenceKind kind = PredicateOccurrenceKind::Unknown;
    SourceLocation spelling_location;
    SourceLocation expansion_location;
    std::optional<std::string> referenced_usr;
    std::optional<std::string> referenced_entity_id;
    std::vector<std::string> semantic_node_ids;
    ValueType value_type;
    // Present only when an object-rooted MemberExpr access path is proven from
    // AST structure and agrees with exactly one M4 semantic identity.
    std::optional<AccessPath> access_path;
    std::optional<std::string> member_base_entity_id;
    std::optional<std::string> member_abstract_object_id;
    Certainty certainty = Certainty::Unknown;
    PredicateOccurrenceResolution resolution =
        PredicateOccurrenceResolution::Unknown;
    std::vector<std::string> uncertainty_reasons;
};

struct PredicateSelectorAccount {
    std::string ap_id;
    std::string selector_id;
    std::vector<ApRole> roles;
    std::vector<std::string> predicate_paths;
    // Type declared jointly by the source-location selector and every
    // matching predicate reference.  EXACT resolution requires this type to
    // agree with the type Clang observes at the selected AST occurrence.
    ValueType expected_value_type;
    SourceLocation requested_location;
    std::vector<std::string> eligible_translation_unit_ids;
    std::vector<std::string> parsed_translation_unit_ids;
    std::vector<std::string> occurrence_ids;
    PredicateOccurrenceResolution resolution =
        PredicateOccurrenceResolution::Unknown;
    std::vector<std::string> uncertainty_reasons;
};

struct PredicateOccurrenceBindings {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string property_ir_sha256;
    std::string semantic_index_sha256;
    std::string canonical_compilation_database_sha256;
    std::string path_map_sha256;
    // These machine-checkable flags document the additive M5 contract.
    bool m4_index_immutable = true;
    bool candidate_accounting_complete = true;
    PredicateOccurrenceOptions options;
    std::uint64_t eligible_translation_units = 0;
    std::uint64_t parsed_translation_units = 0;
    std::uint64_t skipped_translation_units = 0;
    std::uint64_t observed_occurrences = 0;
    StageStatus status = StageStatus::Failed;
    std::vector<PredicateSelectorAccount> selector_accounts;
    std::vector<PredicateOccurrence> occurrences;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

// Model/index construction remains property-independent: this function only
// consumes an already-built SemanticIndex and parses the translation units
// selected by referenced source-location selectors in the loaded Property IR.
[[nodiscard]] PredicateOccurrenceBindings bind_predicate_occurrences(
    const CompilationPlan &plan,
    const TypedPropertyIr &property,
    const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256,
    const PredicateOccurrenceOptions &options = {});

[[nodiscard]] std::vector<std::string>
validate_predicate_occurrence_bindings(
    const PredicateOccurrenceBindings &bindings,
    const CompilationPlan &plan,
    const TypedPropertyIr &property,
    const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256);

[[nodiscard]] std::string canonical_predicate_occurrence_bindings_json(
    const PredicateOccurrenceBindings &bindings);

[[nodiscard]] const char *to_string(PredicateOccurrenceKind value);
[[nodiscard]] const char *to_string(PredicateOccurrenceResolution value);

}  // namespace rift::core

#endif
