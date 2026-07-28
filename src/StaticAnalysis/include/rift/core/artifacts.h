#ifndef RIFT_CORE_ARTIFACTS_H
#define RIFT_CORE_ARTIFACTS_H

#include "rift/core/types.h"

#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

enum class SelectorKind {
    Usr,
    QualifiedSignature,
    SourceLocation,
    TypedFieldPath,
    ExpressionStructure,
    Composite,
};

enum class ApRole {
    Trigger,
    Response,
    Cancel,
    State,
    Guard,
    Bound,
    Clock,
    Scope,
};

enum class FormulaOperator {
    Atom,
    Not,
    And,
    Or,
    Implies,
    Globally,
    Eventually,
    Until,
    Since,
    Next,
    Previous,
    True,
    False,
};

// JSON literals in the typed Property IR are retained as typed canonical
// scalars.  M4 accepted a `literal` member but discarded it, which made a
// later recipe engine unable to distinguish (for example) 0 from a missing
// constant.  Containers are intentionally unsupported: temporal predicates
// use scalar C/C++ values and unsupported payloads must fail closed.
enum class LiteralKind {
    Null,
    Boolean,
    Integer,
    Floating,
    String,
};

struct LiteralValue {
    LiteralKind kind = LiteralKind::Null;
    std::string canonical;

    friend bool operator==(const LiteralValue &, const LiteralValue &) = default;
};

struct ExpressionStructure {
    std::string node_kind;
    std::optional<std::string> operation;
    ValueType value_type;
    std::optional<std::string> referenced_selector_id;
    std::optional<LiteralValue> literal;
    std::vector<ExpressionStructure> operands;
};

struct Selector {
    std::string selector_id;
    SelectorKind kind = SelectorKind::SourceLocation;
    std::optional<std::string> usr;
    std::optional<std::string> qualified_signature;
    std::optional<SourceLocation> location;
    std::optional<ValueType> value_type;
    std::vector<std::string> field_path;
    std::optional<ExpressionStructure> expression;
    std::vector<std::string> component_ids;
};

struct TimeInterval {
    double lower = 0.0;
    std::optional<double> upper;
    bool upper_is_infinity = false;
    bool lower_closed = false;
    bool upper_closed = false;
    std::string unit;
    std::vector<std::string> bound_ap_ids;
};

struct FormulaNode {
    std::string node_id;
    FormulaOperator operation = FormulaOperator::False;
    std::optional<std::string> ap_id;
    std::optional<TimeInterval> interval;
    std::vector<FormulaNode> operands;
};

// A role-local selector clause.  Every selector inside one clause is a
// relational conjunction (all_of); multiple clauses for the same role are
// intentional alternatives (any_of).  The vocabulary is deliberately
// project-neutral: projects provide selector facts, while the core only
// interprets this small Boolean normal form.
struct RoleSelectorGroup {
    std::string group_id;
    ApRole role = ApRole::State;
    std::vector<std::string> selector_ids;
};

struct AtomicProposition {
    std::string ap_id;
    std::vector<ApRole> roles;
    ValueType value_type;
    ExpressionStructure predicate;
    // Legacy schema 1.0.0: one flat ledger is shared by all roles.
    std::vector<std::string> selector_ids;
    // Schema 2.0.0: role-specific DNF.  Exactly one representation is valid
    // for an artifact version; the loader/validator fail closed on mixtures.
    std::vector<RoleSelectorGroup> role_selector_groups;
    std::optional<std::string> description;
};

struct TypedPropertyIr {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string artifact_sha256;
    std::string property_id;
    std::string logic;
    std::string time_domain;
    std::string formula_text;
    FormulaNode formula;
    std::vector<AtomicProposition> atomic_propositions;
    std::vector<Selector> selectors;
};

template <typename T>
struct LoadResult {
    StageStatus status = StageStatus::Failed;
    std::optional<T> value;
    std::string observed_sha256;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct ArtifactDigests {
    std::optional<std::string> property_ir_sha256;
    std::optional<std::string> semantic_index_sha256;
    std::optional<std::string> ap_bindings_sha256;
    std::optional<std::string> graph_sha256;
};

[[nodiscard]] LoadResult<TypedPropertyIr> load_typed_property_ir(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256 = std::nullopt);

// In-memory validators are intentionally public: serializers and alternate
// frontends must pass the same uniqueness, referential-closure, interval, and
// digest gates as the built-in JSON loader.
[[nodiscard]] std::vector<std::string> validate_typed_property_ir(
    const TypedPropertyIr &property);
[[nodiscard]] std::vector<std::string> validate_semantic_index(
    const SemanticIndex &index);
[[nodiscard]] std::vector<std::string> validate_contextual_graph(
    const ContextualInfluenceGraph &graph,
    const std::optional<std::string> &expected_semantic_index_sha256);

}  // namespace rift::core

#endif
