#include "rift/core/value_transfer.h"

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace rift::core {
namespace {

void append_u64_le(std::string &material, std::uint64_t value) {
    for (unsigned shift = 0; shift < 64; shift += 8) {
        material.push_back(static_cast<char>((value >> shift) & 0xffU));
    }
}

void append_lp(std::string &material, std::string_view value) {
    append_u64_le(material, value.size());
    material.append(value);
}

void append_bool(std::string &material, bool value) {
    material.push_back(value ? '\1' : '\0');
}

void append_optional(
    std::string &material, const std::optional<std::string> &value) {
    append_bool(material, value.has_value());
    if (value) {
        append_lp(material, *value);
    }
}

void append_value_type(std::string &material, const ValueType &type) {
    append_lp(material, std::to_string(static_cast<int>(type.kind)));
    append_lp(material, type.canonical);
    append_bool(material, type.bit_width.has_value());
    if (type.bit_width) {
        append_u64_le(material, *type.bit_width);
    }
    append_bool(material, type.is_signed.has_value());
    if (type.is_signed) {
        append_bool(material, *type.is_signed);
    }
    append_optional(material, type.unit);
}

void append_strings(
    std::string &material, const std::vector<std::string> &values) {
    append_u64_le(material, values.size());
    for (const std::string &value : values) {
        append_lp(material, value);
    }
}

template <typename T>
void append_optional_enum(
    std::string &material, const std::optional<T> &value) {
    append_bool(material, value.has_value());
    if (value) {
        append_lp(material, std::to_string(static_cast<int>(*value)));
    }
}

bool valid_sha256(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

template <typename Index>
std::unordered_map<std::string, const TransferExpression *> expression_map(
    const Index &index) {
    std::unordered_map<std::string, const TransferExpression *> result;
    result.reserve(index.expressions.size());
    for (const TransferExpression &expression : index.expressions) {
        result.emplace(expression.expression_id, &expression);
    }
    return result;
}

bool identity_chain(
    const std::string &id,
    const std::unordered_map<std::string, const TransferExpression *> &nodes,
    std::unordered_set<std::string> &visiting, bool &saw_identity) {
    const auto found = nodes.find(id);
    if (found == nodes.end() || !visiting.insert(id).second) {
        return false;
    }
    const TransferExpression &node = *found->second;
    bool result = false;
    switch (node.kind) {
    case TransferExprKind::Input:
        result = node.operand_expression_ids.empty();
        break;
    case TransferExprKind::Identity:
        saw_identity = true;
        [[fallthrough]];
    case TransferExprKind::Load:
    case TransferExprKind::Store:
    case TransferExprKind::CallArg:
    case TransferExprKind::Return:
        result = node.operand_expression_ids.size() == 1 &&
                 identity_chain(
                     node.operand_expression_ids.front(), nodes, visiting,
                     saw_identity);
        break;
    case TransferExprKind::Cast:
        result = node.cast_operation == CastOperation::NoOp &&
                 node.operand_expression_ids.size() == 1 &&
                 identity_chain(
                     node.operand_expression_ids.front(), nodes, visiting,
                     saw_identity);
        break;
    default:
        result = false;
        break;
    }
    visiting.erase(id);
    return result;
}

void validate_expression_shape(
    const TransferExpression &expression, std::vector<std::string> &errors) {
    const std::size_t count = expression.operand_expression_ids.size();
    const auto require_count = [&](std::size_t expected) {
        if (count != expected) {
            errors.push_back(
                expression.expression_id + ": invalid operand count");
        }
    };
    switch (expression.kind) {
    case TransferExprKind::Input:
        require_count(0);
        if (!expression.input || expression.input->symbol_id.empty()) {
            errors.push_back(expression.expression_id + ": missing input symbol");
        }
        break;
    case TransferExprKind::Literal:
        require_count(0);
        if (!expression.literal) {
            errors.push_back(expression.expression_id + ": missing literal");
        }
        break;
    case TransferExprKind::Identity:
    case TransferExprKind::Cast:
    case TransferExprKind::Load:
    case TransferExprKind::Store:
    case TransferExprKind::CallArg:
    case TransferExprKind::Return:
        require_count(1);
        break;
    case TransferExprKind::Compare:
        require_count(2);
        break;
    case TransferExprKind::Boolean:
        if (!expression.boolean_operation ||
            (*expression.boolean_operation == BooleanOperation::Not
                 ? count != 1
                 : count != 2)) {
            errors.push_back(
                expression.expression_id + ": invalid boolean operation");
        }
        break;
    case TransferExprKind::Select:
        require_count(3);
        break;
    case TransferExprKind::Affine:
        if (count == 0 || count != expression.affine_coefficients.size() ||
            !expression.affine_offset) {
            errors.push_back(
                expression.expression_id + ": malformed affine expression");
        }
        break;
    case TransferExprKind::Definedness:
        if (!expression.definedness_operation || count == 0 ||
            expression.value_type.kind != ValueKind::Boolean) {
            errors.push_back(
                expression.expression_id + ": malformed definedness expression");
        }
        break;
    case TransferExprKind::Phi:
    case TransferExprKind::Parse:
    case TransferExprKind::Unknown:
        break;
    }
}

template <typename Index>
void validate_expression_ledger(
    const Index &index, std::vector<std::string> &errors) {
    std::unordered_set<std::string> ids;
    ids.reserve(index.expressions.size());
    for (const TransferExpression &expression : index.expressions) {
        if (!ids.insert(expression.expression_id).second) {
            errors.push_back("duplicate expression ID: " + expression.expression_id);
        }
        if (canonical_transfer_expression_id(expression) !=
            expression.expression_id) {
            errors.push_back(
                "non-canonical expression ID: " + expression.expression_id);
        }
        validate_expression_shape(expression, errors);
    }
    for (const TransferExpression &expression : index.expressions) {
        for (const std::string &operand : expression.operand_expression_ids) {
            if (!ids.contains(operand)) {
                errors.push_back(
                    expression.expression_id + ": unknown operand " + operand);
            }
        }
        for (const std::string &guard : expression.guard_expression_ids) {
            if (!ids.contains(guard)) {
                errors.push_back(
                    expression.expression_id + ": unknown guard " + guard);
            }
        }
    }
}

template <typename Index>
bool has_unknown_descendant(
    const Index &index, const std::string &root) {
    const auto nodes = expression_map(index);
    std::vector<std::string> worklist{root};
    std::unordered_set<std::string> seen;
    while (!worklist.empty()) {
        const std::string current = worklist.back();
        worklist.pop_back();
        if (!seen.insert(current).second) {
            continue;
        }
        const auto found = nodes.find(current);
        if (found == nodes.end()) {
            return true;
        }
        if (found->second->kind == TransferExprKind::Unknown) {
            return true;
        }
        worklist.insert(
            worklist.end(), found->second->operand_expression_ids.begin(),
            found->second->operand_expression_ids.end());
    }
    return false;
}

template <typename Index>
void validate_transfer_ledger(
    const Index &index, std::vector<std::string> &errors) {
    std::unordered_set<std::string> expressions;
    for (const TransferExpression &expression : index.expressions) {
        expressions.insert(expression.expression_id);
    }
    std::unordered_set<std::string> transfers;
    for (const TypedValueTransfer &transfer : index.transfers) {
        if (!transfers.insert(transfer.transfer_id).second) {
            errors.push_back("duplicate transfer ID: " + transfer.transfer_id);
        }
        if (canonical_typed_value_transfer_id(transfer) != transfer.transfer_id) {
            errors.push_back("non-canonical transfer ID: " + transfer.transfer_id);
        }
        if (!expressions.contains(transfer.value_expression_id)) {
            errors.push_back(
                transfer.transfer_id + ": missing value expression root");
        }
        if (transfer.definedness == DefinednessClass::Conditional) {
            if (!transfer.defined_when_expression_id ||
                !expressions.contains(*transfer.defined_when_expression_id)) {
                errors.push_back(
                    transfer.transfer_id + ": missing definedness root");
            }
        } else if (transfer.defined_when_expression_id) {
            errors.push_back(
                transfer.transfer_id + ": unexpected definedness root");
        }
        if (transfer.path_condition == PathConditionClass::Conditional) {
            if (!transfer.path_condition_expression_id ||
                !expressions.contains(*transfer.path_condition_expression_id)) {
                errors.push_back(
                    transfer.transfer_id + ": missing path-condition root");
            }
        } else if (transfer.path_condition_expression_id) {
            errors.push_back(
                transfer.transfer_id + ": unexpected path-condition root");
        }
        if (transfer.soundness == TransferSoundness::Exact &&
            has_unknown_descendant(index, transfer.value_expression_id)) {
            errors.push_back(
                transfer.transfer_id + ": exact transfer contains Unknown");
        }
        if (transfer.call_argument_index && !transfer.callsite_id) {
            errors.push_back(
                transfer.transfer_id + ": argument index has no callsite");
        }
        if (transfer.output_domain ==
                TransferEndpointDomain::CallArgumentSlot &&
            (!transfer.callsite_id || !transfer.call_argument_index)) {
            errors.push_back(
                transfer.transfer_id + ": incomplete call-argument metadata");
        }
    }
}

}  // namespace

#define RIFT_ENUM_STRING_CASE(name, spelling) \
    case name:                               \
        return spelling

const char *to_string(TransferExprKind value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TransferExprKind::Input, "input");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Literal, "literal");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Identity, "identity");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Cast, "cast");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Affine, "affine");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Compare, "compare");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Boolean, "boolean");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Select, "select");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Phi, "phi");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Parse, "parse");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Load, "load");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Store, "store");
        RIFT_ENUM_STRING_CASE(TransferExprKind::CallArg, "call_arg");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Return, "return");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Definedness, "definedness");
        RIFT_ENUM_STRING_CASE(TransferExprKind::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(TransferSoundness value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TransferSoundness::Exact, "exact");
        RIFT_ENUM_STRING_CASE(TransferSoundness::Conservative, "conservative");
        RIFT_ENUM_STRING_CASE(TransferSoundness::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(DefinednessClass value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(DefinednessClass::Total, "total");
        RIFT_ENUM_STRING_CASE(DefinednessClass::Conditional, "conditional");
        RIFT_ENUM_STRING_CASE(DefinednessClass::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(PathConditionClass value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(PathConditionClass::Unconditional, "unconditional");
        RIFT_ENUM_STRING_CASE(PathConditionClass::Conditional, "conditional");
        RIFT_ENUM_STRING_CASE(PathConditionClass::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(TransferSymbolDomain value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TransferSymbolDomain::SemanticNode, "semantic_node");
        RIFT_ENUM_STRING_CASE(TransferSymbolDomain::ContextualNode, "contextual_node");
        RIFT_ENUM_STRING_CASE(TransferSymbolDomain::ExternalActionPayload, "external_action_payload");
        RIFT_ENUM_STRING_CASE(TransferSymbolDomain::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(TransferEndpointDomain value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TransferEndpointDomain::SemanticNode, "semantic_node");
        RIFT_ENUM_STRING_CASE(TransferEndpointDomain::ContextualNode, "contextual_node");
        RIFT_ENUM_STRING_CASE(TransferEndpointDomain::CallArgumentSlot, "call_argument_slot");
        RIFT_ENUM_STRING_CASE(TransferEndpointDomain::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(TransferLiteralKind value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::Boolean, "boolean");
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::Integer, "integer");
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::Floating, "floating");
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::Enumeration, "enumeration");
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::BitVector, "bit_vector");
        RIFT_ENUM_STRING_CASE(TransferLiteralKind::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(CastOperation value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(CastOperation::NoOp, "no_op");
        RIFT_ENUM_STRING_CASE(CastOperation::BoolToInt, "bool_to_int");
        RIFT_ENUM_STRING_CASE(CastOperation::IntToBool, "int_to_bool");
        RIFT_ENUM_STRING_CASE(CastOperation::SignExtend, "sign_extend");
        RIFT_ENUM_STRING_CASE(CastOperation::ZeroExtend, "zero_extend");
        RIFT_ENUM_STRING_CASE(CastOperation::TruncateModulo, "truncate_modulo");
        RIFT_ENUM_STRING_CASE(CastOperation::Unknown, "unknown");
    }
    return "unknown";
}

const char *to_string(CompareOperation value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(CompareOperation::Eq, "eq");
        RIFT_ENUM_STRING_CASE(CompareOperation::Ne, "ne");
        RIFT_ENUM_STRING_CASE(CompareOperation::Lt, "lt");
        RIFT_ENUM_STRING_CASE(CompareOperation::Le, "le");
        RIFT_ENUM_STRING_CASE(CompareOperation::Gt, "gt");
        RIFT_ENUM_STRING_CASE(CompareOperation::Ge, "ge");
    }
    return "eq";
}

const char *to_string(BooleanOperation value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(BooleanOperation::Not, "not");
        RIFT_ENUM_STRING_CASE(BooleanOperation::And, "and");
        RIFT_ENUM_STRING_CASE(BooleanOperation::Or, "or");
        RIFT_ENUM_STRING_CASE(BooleanOperation::Xor, "xor");
    }
    return "not";
}

const char *to_string(DefinednessOperation value) {
    switch (value) {
        RIFT_ENUM_STRING_CASE(DefinednessOperation::SignedAddNoOverflow, "signed_add_no_overflow");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::SignedSubtractNoOverflow, "signed_subtract_no_overflow");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::SignedMultiplyNoOverflow, "signed_multiply_no_overflow");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::SignedNegateNoOverflow, "signed_negate_no_overflow");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::ShortCircuitAnd, "short_circuit_and");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::ShortCircuitOr, "short_circuit_or");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::SelectChosenArm, "select_chosen_arm");
        RIFT_ENUM_STRING_CASE(DefinednessOperation::Unknown, "unknown");
    }
    return "unknown";
}

#undef RIFT_ENUM_STRING_CASE

std::string canonical_transfer_expression_id(
    const TransferExpression &expression) {
    std::string material;
    append_lp(material, kValueTransferIdentityScheme);
    append_lp(material, "expression");
    append_lp(material, std::to_string(static_cast<int>(expression.kind)));
    append_value_type(material, expression.value_type);
    append_bool(material, expression.input.has_value());
    if (expression.input) {
        append_lp(
            material,
            std::to_string(static_cast<int>(expression.input->domain)));
        append_lp(material, expression.input->symbol_id);
        append_value_type(material, expression.input->value_type);
    }
    append_bool(material, expression.literal.has_value());
    if (expression.literal) {
        append_lp(
            material,
            std::to_string(static_cast<int>(expression.literal->kind)));
        append_lp(material, expression.literal->canonical_value);
    }
    append_optional_enum(material, expression.cast_operation);
    append_optional_enum(material, expression.compare_operation);
    append_optional_enum(material, expression.boolean_operation);
    append_optional_enum(material, expression.definedness_operation);
    append_strings(material, expression.operand_expression_ids);
    append_strings(material, expression.guard_expression_ids);
    append_strings(material, expression.predecessor_ids);
    append_strings(material, expression.affine_coefficients);
    append_optional(material, expression.affine_offset);
    append_strings(material, expression.uncertainty_reasons);
    return stable_id("value-expr", material);
}

std::string canonical_typed_value_transfer_id(
    const TypedValueTransfer &transfer) {
    std::string material;
    append_lp(material, kValueTransferIdentityScheme);
    append_lp(material, "transfer");
    append_lp(material, transfer.program_point_id);
    append_lp(
        material, std::to_string(static_cast<int>(transfer.output_domain)));
    append_strings(material, transfer.input_node_ids);
    append_lp(material, transfer.output_node_id);
    append_strings(material, transfer.supporting_edge_ids);
    append_strings(material, transfer.semantic_relation_ids);
    append_lp(material, transfer.value_expression_id);
    append_lp(material, std::to_string(static_cast<int>(transfer.definedness)));
    append_optional(material, transfer.defined_when_expression_id);
    append_lp(material, std::to_string(static_cast<int>(transfer.path_condition)));
    append_optional(material, transfer.path_condition_expression_id);
    append_lp(material, std::to_string(static_cast<int>(transfer.soundness)));
    append_lp(material, std::to_string(static_cast<int>(transfer.certainty)));
    append_optional(material, transfer.callsite_id);
    append_bool(material, transfer.call_argument_index.has_value());
    if (transfer.call_argument_index) {
        append_u64_le(material, *transfer.call_argument_index);
    }
    append_strings(material, transfer.uncertainty_reasons);
    return stable_id("value-transfer", material);
}

std::string canonical_semantic_value_transfer_artifact_id(
    const SemanticValueTransferIndex &index) {
    std::string material;
    append_lp(material, kValueTransferIdentityScheme);
    append_lp(material, "semantic-sidecar");
    append_lp(material, index.semantic_index_artifact_id);
    append_optional(material, index.semantic_index_sha256);
    append_bool(material, index.physical_digest_binding_complete);
    append_bool(material, index.property_independent);
    append_u64_le(material, index.limits.maximum_expression_nodes);
    append_u64_le(material, index.limits.maximum_transfers);
    append_u64_le(material, index.limits.maximum_expression_operands);
    for (const TransferExpression &expression : index.expressions) {
        append_lp(material, expression.expression_id);
    }
    for (const TypedValueTransfer &transfer : index.transfers) {
        append_lp(material, transfer.transfer_id);
    }
    return stable_id("value-transfer-index", material);
}

std::string canonical_contextual_value_transfer_artifact_id(
    const ContextualValueTransferIndex &index) {
    std::string material;
    append_lp(material, kValueTransferIdentityScheme);
    append_lp(material, "contextual-sidecar");
    append_lp(material, index.semantic_value_transfer_artifact_id);
    append_lp(material, index.semantic_index_sha256);
    append_lp(material, index.graph_artifact_id);
    append_optional(material, index.semantic_value_transfers_sha256);
    append_optional(material, index.graph_sha256);
    append_bool(material, index.physical_digest_binding_complete);
    append_bool(material, index.property_independent);
    append_u64_le(material, index.limits.maximum_expression_nodes);
    append_u64_le(material, index.limits.maximum_transfers);
    append_u64_le(material, index.limits.maximum_expression_operands);
    for (const TransferExpression &expression : index.expressions) {
        append_lp(material, expression.expression_id);
    }
    for (const TypedValueTransfer &transfer : index.transfers) {
        append_lp(material, transfer.transfer_id);
    }
    return stable_id("contextual-value-transfer-index", material);
}

void bind_semantic_value_transfer_physical_digest(
    SemanticValueTransferIndex &index,
    const std::string &semantic_index_sha256) {
    index.semantic_index_sha256 = semantic_index_sha256;
    index.physical_digest_binding_complete =
        valid_sha256(semantic_index_sha256);
    if (!index.physical_digest_binding_complete) {
        index.status = StageStatus::Failed;
        index.diagnostics.push_back(
            "semantic-index physical digest is not SHA-256");
    }
    index.artifact_id =
        canonical_semantic_value_transfer_artifact_id(index);
}

void bind_contextual_value_transfer_physical_digests(
    ContextualValueTransferIndex &index,
    const std::string &semantic_value_transfers_sha256,
    const std::string &graph_sha256) {
    index.semantic_value_transfers_sha256 =
        semantic_value_transfers_sha256;
    index.graph_sha256 = graph_sha256;
    index.physical_digest_binding_complete =
        valid_sha256(semantic_value_transfers_sha256) &&
        valid_sha256(graph_sha256);
    if (!index.physical_digest_binding_complete) {
        index.status = StageStatus::Failed;
        index.diagnostics.push_back(
            "contextual sidecar physical input digest is not SHA-256");
    }
    index.artifact_id =
        canonical_contextual_value_transfer_artifact_id(index);
}

bool typed_transfer_is_identity(
    const TypedValueTransfer &transfer,
    const std::vector<TransferExpression> &expressions) {
    if (transfer.soundness != TransferSoundness::Exact) {
        return false;
    }
    std::unordered_map<std::string, const TransferExpression *> nodes;
    nodes.reserve(expressions.size());
    for (const TransferExpression &expression : expressions) {
        nodes.emplace(expression.expression_id, &expression);
    }
    std::unordered_set<std::string> visiting;
    bool saw_identity = false;
    return identity_chain(
               transfer.value_expression_id, nodes, visiting, saw_identity) &&
           saw_identity;
}

std::vector<std::string> validate_semantic_value_transfers(
    const SemanticValueTransferIndex &transfers,
    const SemanticIndex &semantic_index) {
    std::vector<std::string> errors;
    if (!transfers.property_independent) {
        errors.push_back("semantic value-transfer sidecar is property dependent");
    }
    if (transfers.semantic_index_artifact_id != semantic_index.artifact_id) {
        errors.push_back("semantic index artifact identity mismatch");
    }
    if (transfers.physical_digest_binding_complete) {
        if (!transfers.semantic_index_sha256 ||
            !valid_sha256(*transfers.semantic_index_sha256)) {
            errors.push_back(
                "semantic sidecar physical digest binding is incomplete");
        }
    } else if (transfers.semantic_index_sha256) {
        errors.push_back(
            "semantic sidecar has a digest without a complete binding flag");
    }
    validate_expression_ledger(transfers, errors);
    validate_transfer_ledger(transfers, errors);
    std::unordered_set<std::string> semantic_nodes;
    for (const SemanticNode &node : semantic_index.nodes) {
        semantic_nodes.insert(node.node_id);
    }
    std::unordered_set<std::string> relations;
    for (const SemanticRelation &relation : semantic_index.relations) {
        relations.insert(relation.relation_id);
    }
    std::unordered_set<std::string> callsites;
    for (const CallSiteSummary &callsite : semantic_index.callsites) {
        callsites.insert(callsite.callsite_id);
    }
    for (const TypedValueTransfer &transfer : transfers.transfers) {
        if (transfer.output_domain == TransferEndpointDomain::SemanticNode &&
            !semantic_nodes.contains(transfer.output_node_id)) {
            errors.push_back(transfer.transfer_id + ": unknown semantic output");
        }
        if (transfer.output_domain == TransferEndpointDomain::CallArgumentSlot) {
            if (!transfer.callsite_id || !transfer.call_argument_index ||
                !callsites.contains(*transfer.callsite_id)) {
                errors.push_back(
                    transfer.transfer_id + ": malformed call-argument slot");
            }
        }
        for (const std::string &input : transfer.input_node_ids) {
            if (!semantic_nodes.contains(input)) {
                errors.push_back(transfer.transfer_id + ": unknown semantic input");
            }
        }
        for (const std::string &relation : transfer.semantic_relation_ids) {
            if (!relations.contains(relation)) {
                errors.push_back(transfer.transfer_id + ": unknown relation");
            }
        }
    }
    if (transfers.artifact_id !=
        canonical_semantic_value_transfer_artifact_id(transfers)) {
        errors.push_back("semantic value-transfer artifact ID mismatch");
    }
    return errors;
}

std::vector<std::string> validate_contextual_value_transfers(
    const ContextualValueTransferIndex &transfers,
    const ContextualInfluenceGraph &graph,
    const SemanticIndex &semantic_index,
    const SemanticValueTransferIndex &semantic_transfers) {
    std::vector<std::string> errors;
    if (!transfers.property_independent) {
        errors.push_back("contextual value-transfer sidecar is property dependent");
    }
    if (!valid_sha256(transfers.semantic_index_sha256) ||
        transfers.semantic_index_sha256 != graph.semantic_index_sha256) {
        errors.push_back("contextual sidecar semantic-index digest mismatch");
    }
    if (transfers.graph_artifact_id != graph.artifact_id) {
        errors.push_back("contextual graph artifact identity mismatch");
    }
    if (transfers.semantic_value_transfer_artifact_id !=
        semantic_transfers.artifact_id) {
        errors.push_back("semantic value-transfer artifact identity mismatch");
    }
    if (transfers.physical_digest_binding_complete) {
        if (!transfers.semantic_value_transfers_sha256 ||
            !valid_sha256(*transfers.semantic_value_transfers_sha256) ||
            !transfers.graph_sha256 ||
            !valid_sha256(*transfers.graph_sha256)) {
            errors.push_back(
                "contextual sidecar physical digest binding is incomplete");
        }
    } else if (transfers.semantic_value_transfers_sha256 ||
               transfers.graph_sha256) {
        errors.push_back(
            "contextual sidecar has digests without a complete binding flag");
    }
    validate_expression_ledger(transfers, errors);
    validate_transfer_ledger(transfers, errors);
    std::unordered_set<std::string> graph_nodes;
    for (const ContextualNode &node : graph.nodes) {
        graph_nodes.insert(node.node_id);
    }
    std::unordered_set<std::string> graph_edges;
    for (const InfluenceEdge &edge : graph.edges) {
        graph_edges.insert(edge.edge_id);
    }
    std::unordered_set<std::string> relations;
    for (const SemanticRelation &relation : semantic_index.relations) {
        relations.insert(relation.relation_id);
    }
    for (const TypedValueTransfer &transfer : transfers.transfers) {
        if (transfer.output_domain != TransferEndpointDomain::ContextualNode ||
            !graph_nodes.contains(transfer.output_node_id)) {
            errors.push_back(transfer.transfer_id + ": unknown contextual output");
        }
        for (const std::string &input : transfer.input_node_ids) {
            if (!graph_nodes.contains(input)) {
                errors.push_back(transfer.transfer_id + ": unknown contextual input");
            }
        }
        for (const std::string &edge : transfer.supporting_edge_ids) {
            if (!graph_edges.contains(edge)) {
                errors.push_back(transfer.transfer_id + ": unknown supporting edge");
            }
        }
        for (const std::string &relation : transfer.semantic_relation_ids) {
            if (!relations.contains(relation)) {
                errors.push_back(transfer.transfer_id + ": unknown semantic relation");
            }
        }
    }
    if (transfers.artifact_id !=
        canonical_contextual_value_transfer_artifact_id(transfers)) {
        errors.push_back("contextual value-transfer artifact ID mismatch");
    }
    return errors;
}

}  // namespace rift::core
