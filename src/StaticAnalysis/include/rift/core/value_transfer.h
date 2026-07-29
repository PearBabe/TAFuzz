#ifndef RIFT_CORE_VALUE_TRANSFER_H
#define RIFT_CORE_VALUE_TRANSFER_H

#include "rift/core/types.h"

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

inline constexpr const char *kValueTransferIdentityScheme =
    "rift-value-transfer/lp-u64le/1.0.0";

enum class TransferExprKind {
    Input,
    Literal,
    Identity,
    Cast,
    Affine,
    Compare,
    Boolean,
    Select,
    Phi,
    Parse,
    Load,
    Store,
    CallArg,
    Return,
    Definedness,
    Unknown,
};

enum class TransferSoundness {
    Exact,
    Conservative,
    Unknown,
};

enum class DefinednessClass {
    Total,
    Conditional,
    Unknown,
};

enum class PathConditionClass {
    Unconditional,
    Conditional,
    Unknown,
};

enum class TransferSymbolDomain {
    SemanticNode,
    ContextualNode,
    ExternalActionPayload,
    Unknown,
};

enum class TransferEndpointDomain {
    SemanticNode,
    ContextualNode,
    CallArgumentSlot,
    Unknown,
};

enum class TransferLiteralKind {
    Boolean,
    Integer,
    Floating,
    Enumeration,
    BitVector,
    Unknown,
};

enum class CastOperation {
    NoOp,
    BoolToInt,
    IntToBool,
    SignExtend,
    ZeroExtend,
    TruncateModulo,
    Unknown,
};

enum class CompareOperation {
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
};

enum class BooleanOperation {
    Not,
    And,
    Or,
    Xor,
};

// Definedness is represented in the same typed DAG so a later SMT stage does
// not need to reverse engineer C/C++ undefined behaviour from prose.
enum class DefinednessOperation {
    SignedAddNoOverflow,
    SignedSubtractNoOverflow,
    SignedMultiplyNoOverflow,
    SignedNegateNoOverflow,
    ShortCircuitAnd,
    ShortCircuitOr,
    SelectChosenArm,
    Unknown,
};

struct TransferLiteral {
    TransferLiteralKind kind = TransferLiteralKind::Unknown;
    std::string canonical_value;

    friend bool operator==(const TransferLiteral &, const TransferLiteral &) =
        default;
};

struct TransferSymbolRef {
    TransferSymbolDomain domain = TransferSymbolDomain::Unknown;
    std::string symbol_id;
    ValueType value_type;

    friend bool operator==(
        const TransferSymbolRef &, const TransferSymbolRef &) = default;
};

// Expression IDs are bottom-up hashes. Operand, guard, coefficient, and
// predecessor order is semantic and must not be sorted by serializers.
struct TransferExpression {
    std::string expression_id;
    TransferExprKind kind = TransferExprKind::Unknown;
    ValueType value_type;
    std::optional<TransferSymbolRef> input;
    std::optional<TransferLiteral> literal;
    std::optional<CastOperation> cast_operation;
    std::optional<CompareOperation> compare_operation;
    std::optional<BooleanOperation> boolean_operation;
    std::optional<DefinednessOperation> definedness_operation;
    std::vector<std::string> operand_expression_ids;
    std::vector<std::string> guard_expression_ids;
    std::vector<std::string> predecessor_ids;
    // Decimal mathematical integers. The coefficient at position i applies
    // to operand_expression_ids[i].
    std::vector<std::string> affine_coefficients;
    std::optional<std::string> affine_offset;
    std::vector<std::string> uncertainty_reasons;

    friend bool operator==(
        const TransferExpression &, const TransferExpression &) = default;
};

struct TypedValueTransfer {
    std::string transfer_id;
    std::string program_point_id;
    TransferEndpointDomain output_domain = TransferEndpointDomain::Unknown;
    std::vector<std::string> input_node_ids;
    std::string output_node_id;
    std::vector<std::string> supporting_edge_ids;
    std::vector<std::string> semantic_relation_ids;
    std::string value_expression_id;
    DefinednessClass definedness = DefinednessClass::Unknown;
    std::optional<std::string> defined_when_expression_id;
    PathConditionClass path_condition = PathConditionClass::Unknown;
    std::optional<std::string> path_condition_expression_id;
    TransferSoundness soundness = TransferSoundness::Unknown;
    Certainty certainty = Certainty::Unknown;
    std::optional<std::string> callsite_id;
    std::optional<std::uint32_t> call_argument_index;
    std::vector<Evidence> evidence;
    std::vector<std::string> uncertainty_reasons;
};

struct ValueTransferOptions {
    std::uint64_t maximum_expression_nodes = 1'000'000;
    std::uint64_t maximum_transfers = 1'000'000;
    std::uint32_t maximum_expression_operands = 64;
};

struct SemanticValueTransferIndex {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string semantic_index_artifact_id;
    std::optional<std::string> semantic_index_sha256;
    bool physical_digest_binding_complete = false;
    bool property_independent = true;
    bool candidate_accounting_complete = true;
    bool resource_limit_hit = false;
    StageStatus status = StageStatus::Failed;
    ValueTransferOptions limits;
    std::uint64_t observed_expression_nodes = 0;
    std::uint64_t observed_transfers = 0;
    std::vector<TransferExpression> expressions;
    // Call-argument slot transfers are in this same ledger and are identified
    // by output_domain==CallArgumentSlot plus callsite/index.
    std::vector<TypedValueTransfer> transfers;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct ContextualValueTransferIndex {
    std::string schema_version = "1.0.0";
    std::string artifact_id;
    std::string semantic_value_transfer_artifact_id;
    std::string semantic_index_sha256;
    std::string graph_artifact_id;
    std::optional<std::string> semantic_value_transfers_sha256;
    std::optional<std::string> graph_sha256;
    bool physical_digest_binding_complete = false;
    bool property_independent = true;
    bool candidate_accounting_complete = true;
    bool resource_limit_hit = false;
    StageStatus status = StageStatus::Failed;
    ValueTransferOptions limits;
    std::uint64_t observed_expression_nodes = 0;
    std::uint64_t observed_transfers = 0;
    std::vector<TransferExpression> expressions;
    std::vector<TypedValueTransfer> transfers;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] const char *to_string(TransferExprKind value);
[[nodiscard]] const char *to_string(TransferSoundness value);
[[nodiscard]] const char *to_string(DefinednessClass value);
[[nodiscard]] const char *to_string(PathConditionClass value);
[[nodiscard]] const char *to_string(TransferSymbolDomain value);
[[nodiscard]] const char *to_string(TransferEndpointDomain value);
[[nodiscard]] const char *to_string(TransferLiteralKind value);
[[nodiscard]] const char *to_string(CastOperation value);
[[nodiscard]] const char *to_string(CompareOperation value);
[[nodiscard]] const char *to_string(BooleanOperation value);
[[nodiscard]] const char *to_string(DefinednessOperation value);

[[nodiscard]] std::string canonical_transfer_expression_id(
    const TransferExpression &expression);
[[nodiscard]] std::string canonical_typed_value_transfer_id(
    const TypedValueTransfer &transfer);
[[nodiscard]] std::string canonical_semantic_value_transfer_artifact_id(
    const SemanticValueTransferIndex &index);
[[nodiscard]] std::string canonical_contextual_value_transfer_artifact_id(
    const ContextualValueTransferIndex &index);

// Physical byte digests are unavailable until the sibling artifacts have
// been canonically serialized. These finalizers make the self-describing hash
// chain explicit without introducing property input or a second AST pass.
void bind_semantic_value_transfer_physical_digest(
    SemanticValueTransferIndex &index,
    const std::string &semantic_index_sha256);
void bind_contextual_value_transfer_physical_digests(
    ContextualValueTransferIndex &index,
    const std::string &semantic_value_transfers_sha256,
    const std::string &graph_sha256);

[[nodiscard]] bool typed_transfer_is_identity(
    const TypedValueTransfer &transfer,
    const std::vector<TransferExpression> &expressions);

[[nodiscard]] std::vector<std::string> validate_semantic_value_transfers(
    const SemanticValueTransferIndex &transfers,
    const SemanticIndex &semantic_index);
[[nodiscard]] std::vector<std::string> validate_contextual_value_transfers(
    const ContextualValueTransferIndex &transfers,
    const ContextualInfluenceGraph &graph,
    const SemanticIndex &semantic_index,
    const SemanticValueTransferIndex &semantic_transfers);

}  // namespace rift::core

#endif
