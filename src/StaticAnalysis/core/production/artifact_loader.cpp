#include "rift/core/artifacts.h"
#include "rift/core/index.h"

#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <iomanip>
#include <set>
#include <sstream>
#include <string_view>

namespace rift::core {
namespace {

using llvm::json::Array;
using llvm::json::Object;
using llvm::json::Value;

struct ParseContext {
    std::vector<std::string> errors;

    void error(const std::string &path, const std::string &message) {
        errors.push_back(path + ": " + message);
    }
};

std::optional<std::string> string_member(
    const Object &object, llvm::StringRef key, const std::string &path,
    ParseContext &context) {
    const std::optional<llvm::StringRef> value = object.getString(key);
    if (!value.has_value() || value->empty()) {
        context.error(path + '.' + key.str(), "expected non-empty string");
        return std::nullopt;
    }
    return value->str();
}

bool reject_unknown_members(
    const Object &object, const std::set<std::string> &allowed,
    const std::string &path, ParseContext &context) {
    bool valid = true;
    for (const auto &member : object) {
        const std::string name = llvm::StringRef(member.first).str();
        if (!allowed.contains(name)) {
            context.error(path + '.' + name, "unknown member");
            valid = false;
        }
    }
    return valid;
}

std::optional<ValueKind> parse_value_kind(std::string_view text) {
    static const std::map<std::string_view, ValueKind> values{
        {"bool", ValueKind::Boolean},
        {"integer", ValueKind::Integer},
        {"floating", ValueKind::Floating},
        {"enum", ValueKind::Enumeration},
        {"bitvector", ValueKind::BitVector},
        {"timestamp", ValueKind::Timestamp},
        {"duration", ValueKind::Duration},
        {"pointer", ValueKind::Pointer},
        {"record", ValueKind::Record},
        {"array", ValueKind::Array},
        {"unknown", ValueKind::Unknown},
    };
    const auto found = values.find(text);
    return found == values.end() ? std::nullopt
                                 : std::optional<ValueKind>(found->second);
}

std::optional<ValueType> parse_value_type(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected value type object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object, {"kind", "canonical", "bit_width", "signed", "unit"},
        path, context);
    const auto kind_text = string_member(*object, "kind", path, context);
    const auto canonical = string_member(*object, "canonical", path, context);
    if (!kind_text || !canonical) {
        return std::nullopt;
    }
    const auto kind = parse_value_kind(*kind_text);
    if (!kind) {
        context.error(path + ".kind", "unsupported value kind");
        return std::nullopt;
    }
    ValueType result;
    result.kind = *kind;
    result.canonical = *canonical;
    if (const auto width = object->getInteger("bit_width")) {
        if (*width <= 0 ||
            *width > static_cast<std::int64_t>(
                         std::numeric_limits<std::uint32_t>::max())) {
            context.error(path + ".bit_width", "must be a positive uint32");
        } else {
            result.bit_width = static_cast<std::uint32_t>(*width);
        }
    } else if (object->get("bit_width") != nullptr) {
        context.error(path + ".bit_width", "expected integer");
    }
    if (const auto signed_value = object->getBoolean("signed")) {
        result.is_signed = *signed_value;
    } else if (object->get("signed") != nullptr) {
        context.error(path + ".signed", "expected boolean");
    }
    if (const auto unit = object->getString("unit")) {
        if (unit->empty()) {
            context.error(path + ".unit", "must not be empty");
        } else {
            result.unit = unit->str();
        }
    } else if (object->get("unit") != nullptr) {
        context.error(path + ".unit", "expected string");
    }
    return result;
}

std::optional<SourceLocation> parse_location(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected source location object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"file", "line", "column", "end_line", "end_column",
         "location_kind", "macro_stack"},
        path, context);
    const auto file = string_member(*object, "file", path, context);
    const auto kind = string_member(*object, "location_kind", path, context);
    const auto line = object->getInteger("line");
    const auto column = object->getInteger("column");
    if (!line || *line <= 0) {
        context.error(path + ".line", "expected positive integer");
    }
    if (!column || *column <= 0) {
        context.error(path + ".column", "expected positive integer");
    }
    if (!file || !kind || !line || !column || *line <= 0 || *column <= 0) {
        return std::nullopt;
    }
    SourceLocation result;
    result.file = *file;
    result.line = static_cast<std::uint32_t>(*line);
    result.column = static_cast<std::uint32_t>(*column);
    result.location_kind = *kind;
    if (const auto end = object->getInteger("end_line")) {
        if (*end <= 0) {
            context.error(path + ".end_line", "expected positive integer");
        } else {
            result.end_line = static_cast<std::uint32_t>(*end);
        }
    }
    if (const auto end = object->getInteger("end_column")) {
        if (*end <= 0) {
            context.error(path + ".end_column", "expected positive integer");
        } else {
            result.end_column = static_cast<std::uint32_t>(*end);
        }
    }
    if (const Array *stack = object->getArray("macro_stack")) {
        for (std::size_t index = 0; index < stack->size(); ++index) {
            const auto value = (*stack)[index].getAsString();
            if (!value || value->empty()) {
                context.error(
                    path + ".macro_stack[" + std::to_string(index) + "]",
                    "expected non-empty string");
            } else {
                result.macro_stack.push_back(value->str());
            }
        }
    }
    return result;
}

std::optional<ExpressionStructure> parse_expression(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected expression object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"node_kind", "operator", "value_type", "referenced_selector_id",
         "literal", "operands"},
        path, context);
    const auto node_kind = string_member(*object, "node_kind", path, context);
    const auto type = parse_value_type(
        object->getObject("value_type"), path + ".value_type", context);
    const Array *operands = object->getArray("operands");
    if (operands == nullptr) {
        context.error(path + ".operands", "expected array");
    }
    if (!node_kind || !type || operands == nullptr) {
        return std::nullopt;
    }
    ExpressionStructure result;
    result.node_kind = *node_kind;
    result.value_type = *type;
    if (const auto operation = object->getString("operator")) {
        if (operation->empty()) {
            context.error(path + ".operator", "must be null or non-empty");
        } else {
            result.operation = operation->str();
        }
    } else if (const Value *value = object->get("operator");
               value != nullptr && !value->getAsNull()) {
        context.error(path + ".operator", "expected string or null");
    }
    if (const auto selector = object->getString("referenced_selector_id")) {
        if (selector->empty()) {
            context.error(
                path + ".referenced_selector_id", "must be non-empty");
        } else {
            result.referenced_selector_id = selector->str();
        }
    } else if (const Value *value = object->get("referenced_selector_id");
               value != nullptr && !value->getAsNull()) {
        context.error(
            path + ".referenced_selector_id", "expected string or null");
    }
    if (const Value *literal = object->get("literal")) {
        LiteralValue parsed;
        if (const auto value = literal->getAsString()) {
            parsed.kind = LiteralKind::String;
            parsed.canonical = value->str();
        } else if (const auto value = literal->getAsBoolean()) {
            parsed.kind = LiteralKind::Boolean;
            parsed.canonical = *value ? "true" : "false";
        } else if (const auto value = literal->getAsInteger()) {
            parsed.kind = LiteralKind::Integer;
            parsed.canonical = std::to_string(*value);
        } else if (const auto value = literal->getAsNumber()) {
            parsed.kind = LiteralKind::Floating;
            std::ostringstream stream;
            stream << std::setprecision(std::numeric_limits<double>::max_digits10)
                   << *value;
            parsed.canonical = stream.str();
        } else if (literal->getAsNull()) {
            parsed.kind = LiteralKind::Null;
            parsed.canonical = "null";
        } else {
            context.error(
                path + ".literal",
                "expected scalar string, boolean, integer, number, or null");
        }
        if (!parsed.canonical.empty() || parsed.kind == LiteralKind::String) {
            result.literal = std::move(parsed);
        }
    }
    for (std::size_t index = 0; index < operands->size(); ++index) {
        auto operand = parse_expression(
            (*operands)[index].getAsObject(),
            path + ".operands[" + std::to_string(index) + "]", context);
        if (operand) {
            result.operands.push_back(std::move(*operand));
        }
    }
    return result;
}

std::optional<SelectorKind> parse_selector_kind(std::string_view text) {
    static const std::map<std::string_view, SelectorKind> values{
        {"usr", SelectorKind::Usr},
        {"qualified_signature", SelectorKind::QualifiedSignature},
        {"source_location", SelectorKind::SourceLocation},
        {"typed_field_path", SelectorKind::TypedFieldPath},
        {"expression_structure", SelectorKind::ExpressionStructure},
        {"composite", SelectorKind::Composite},
    };
    const auto found = values.find(text);
    return found == values.end() ? std::nullopt
                                 : std::optional<SelectorKind>(found->second);
}

std::optional<Selector> parse_selector(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected selector object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"selector_id", "kind", "usr", "qualified_signature", "location",
         "value_type", "field_path", "expression_structure", "components"},
        path, context);
    const auto id = string_member(*object, "selector_id", path, context);
    const auto kind_text = string_member(*object, "kind", path, context);
    if (!id || !kind_text) {
        return std::nullopt;
    }
    const auto kind = parse_selector_kind(*kind_text);
    if (!kind) {
        context.error(path + ".kind", "unsupported selector kind");
        return std::nullopt;
    }
    Selector result;
    result.selector_id = *id;
    result.kind = *kind;
    if (const auto usr = object->getString("usr")) {
        result.usr = usr->str();
    }
    if (const auto signature = object->getString("qualified_signature")) {
        result.qualified_signature = signature->str();
    }
    if (object->get("location") != nullptr) {
        result.location = parse_location(
            object->getObject("location"), path + ".location", context);
    }
    if (object->get("value_type") != nullptr) {
        result.value_type = parse_value_type(
            object->getObject("value_type"), path + ".value_type", context);
    }
    if (const Array *fields = object->getArray("field_path")) {
        for (std::size_t index = 0; index < fields->size(); ++index) {
            const auto value = (*fields)[index].getAsString();
            if (!value || value->empty()) {
                context.error(
                    path + ".field_path[" + std::to_string(index) + "]",
                    "expected non-empty string");
            } else {
                result.field_path.push_back(value->str());
            }
        }
    }
    if (object->get("expression_structure") != nullptr) {
        result.expression = parse_expression(
            object->getObject("expression_structure"),
            path + ".expression_structure", context);
    }
    if (const Array *components = object->getArray("components")) {
        for (std::size_t index = 0; index < components->size(); ++index) {
            const auto value = (*components)[index].getAsString();
            if (!value || value->empty()) {
                context.error(
                    path + ".components[" + std::to_string(index) + "]",
                    "expected non-empty string");
            } else {
                result.component_ids.push_back(value->str());
            }
        }
    }
    switch (*kind) {
    case SelectorKind::Usr:
        if (!result.usr) {
            context.error(path + ".usr", "required for USR selector");
        }
        break;
    case SelectorKind::QualifiedSignature:
        if (!result.qualified_signature) {
            context.error(
                path + ".qualified_signature", "required for signature selector");
        }
        break;
    case SelectorKind::SourceLocation:
        if (!result.location) {
            context.error(path + ".location", "required for location selector");
        }
        break;
    case SelectorKind::TypedFieldPath:
        if (!result.value_type || result.field_path.empty()) {
            context.error(
                path, "typed field selector requires value_type and field_path");
        }
        break;
    case SelectorKind::ExpressionStructure:
        if (!result.expression) {
            context.error(
                path + ".expression_structure",
                "required for expression selector");
        }
        break;
    case SelectorKind::Composite:
        if (result.component_ids.size() < 2) {
            context.error(path + ".components", "requires at least two components");
        }
        break;
    }
    return result;
}

std::optional<ApRole> parse_role(std::string_view text) {
    static const std::map<std::string_view, ApRole> values{
        {"trigger", ApRole::Trigger}, {"response", ApRole::Response},
        {"cancel", ApRole::Cancel},   {"state", ApRole::State},
        {"guard", ApRole::Guard},    {"bound", ApRole::Bound},
        {"clock", ApRole::Clock},    {"scope", ApRole::Scope},
    };
    const auto found = values.find(text);
    return found == values.end() ? std::nullopt
                                 : std::optional<ApRole>(found->second);
}

std::optional<FormulaOperator> parse_formula_operator(std::string_view text) {
    static const std::map<std::string_view, FormulaOperator> values{
        {"atom", FormulaOperator::Atom},
        {"not", FormulaOperator::Not},
        {"and", FormulaOperator::And},
        {"or", FormulaOperator::Or},
        {"implies", FormulaOperator::Implies},
        {"globally", FormulaOperator::Globally},
        {"eventually", FormulaOperator::Eventually},
        {"until", FormulaOperator::Until},
        {"since", FormulaOperator::Since},
        {"next", FormulaOperator::Next},
        {"previous", FormulaOperator::Previous},
        {"true", FormulaOperator::True},
        {"false", FormulaOperator::False},
    };
    const auto found = values.find(text);
    return found == values.end()
               ? std::nullopt
               : std::optional<FormulaOperator>(found->second);
}

std::optional<TimeInterval> parse_interval(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected interval object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"lower", "upper", "lower_closed", "upper_closed", "unit",
         "bound_ap_refs"},
        path, context);
    const auto lower = object->getNumber("lower");
    const auto lower_closed = object->getBoolean("lower_closed");
    const auto upper_closed = object->getBoolean("upper_closed");
    const auto unit = string_member(*object, "unit", path, context);
    if (!lower || !std::isfinite(*lower) || *lower < 0.0) {
        context.error(path + ".lower", "expected finite non-negative number");
    }
    if (!lower_closed) {
        context.error(path + ".lower_closed", "expected boolean");
    }
    if (!upper_closed) {
        context.error(path + ".upper_closed", "expected boolean");
    }
    TimeInterval result;
    if (lower) {
        result.lower = *lower;
    }
    if (const auto numeric = object->getNumber("upper")) {
        if (!std::isfinite(*numeric) || *numeric < 0.0) {
            context.error(path + ".upper", "expected non-negative number");
        } else {
            result.upper = *numeric;
        }
    } else if (const auto text = object->getString("upper");
               text && *text == "infinity") {
        result.upper_is_infinity = true;
    } else {
        context.error(path + ".upper", "expected number or infinity");
    }
    if (lower_closed) {
        result.lower_closed = *lower_closed;
    }
    if (upper_closed) {
        result.upper_closed = *upper_closed;
    }
    if (unit) {
        result.unit = *unit;
    }
    if (const Array *refs = object->getArray("bound_ap_refs")) {
        for (std::size_t index = 0; index < refs->size(); ++index) {
            const auto value = (*refs)[index].getAsString();
            if (!value || value->empty()) {
                context.error(
                    path + ".bound_ap_refs[" + std::to_string(index) + "]",
                    "expected non-empty string");
            } else {
                result.bound_ap_ids.push_back(value->str());
            }
        }
    }
    return result;
}

std::optional<FormulaNode> parse_formula(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected formula node object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object, {"node_id", "operator", "ap_ref", "interval", "operands"},
        path, context);
    const auto id = string_member(*object, "node_id", path, context);
    const auto operation_text = string_member(*object, "operator", path, context);
    const Array *operands = object->getArray("operands");
    if (operands == nullptr) {
        context.error(path + ".operands", "expected array");
    }
    if (!id || !operation_text || operands == nullptr) {
        return std::nullopt;
    }
    const auto operation = parse_formula_operator(*operation_text);
    if (!operation) {
        context.error(path + ".operator", "unsupported formula operator");
        return std::nullopt;
    }
    FormulaNode result;
    result.node_id = *id;
    result.operation = *operation;
    if (const auto ap = object->getString("ap_ref")) {
        result.ap_id = ap->str();
    }
    if (object->get("interval") != nullptr) {
        result.interval = parse_interval(
            object->getObject("interval"), path + ".interval", context);
    }
    for (std::size_t index = 0; index < operands->size(); ++index) {
        auto child = parse_formula(
            (*operands)[index].getAsObject(),
            path + ".operands[" + std::to_string(index) + "]", context);
        if (child) {
            result.operands.push_back(std::move(*child));
        }
    }
    const std::size_t count = result.operands.size();
    switch (result.operation) {
    case FormulaOperator::Atom:
        if (!result.ap_id || count != 0) {
            context.error(path, "atom requires ap_ref and zero operands");
        }
        break;
    case FormulaOperator::True:
    case FormulaOperator::False:
        if (count != 0) {
            context.error(path, "constant formula requires zero operands");
        }
        break;
    case FormulaOperator::Not:
    case FormulaOperator::Globally:
    case FormulaOperator::Eventually:
    case FormulaOperator::Next:
    case FormulaOperator::Previous:
        if (count != 1) {
            context.error(path, "unary formula requires one operand");
        }
        break;
    case FormulaOperator::Implies:
    case FormulaOperator::Until:
    case FormulaOperator::Since:
        if (count != 2) {
            context.error(path, "binary formula requires two operands");
        }
        break;
    case FormulaOperator::And:
    case FormulaOperator::Or:
        if (count < 2) {
            context.error(path, "n-ary formula requires at least two operands");
        }
        break;
    }
    const bool needs_interval =
        result.operation == FormulaOperator::Globally ||
        result.operation == FormulaOperator::Eventually ||
        result.operation == FormulaOperator::Until ||
        result.operation == FormulaOperator::Since;
    if (needs_interval && !result.interval) {
        context.error(path + ".interval", "required for temporal operator");
    }
    return result;
}

std::optional<RoleSelectorGroup> parse_role_selector_group(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected role selector group object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object, {"group_id", "role", "all_of"}, path, context);
    const auto group_id = string_member(*object, "group_id", path, context);
    const auto role_text = string_member(*object, "role", path, context);
    const Array *all_of = object->getArray("all_of");
    if (all_of == nullptr) {
        context.error(path + ".all_of", "expected array");
    }
    const auto role = role_text ? parse_role(*role_text) : std::nullopt;
    if (role_text && !role) {
        context.error(path + ".role", "unsupported AP role");
    }
    if (!group_id || !role || all_of == nullptr) {
        return std::nullopt;
    }
    RoleSelectorGroup result;
    result.group_id = *group_id;
    result.role = *role;
    std::set<std::string> seen;
    for (std::size_t index = 0; index < all_of->size(); ++index) {
        const auto selector = (*all_of)[index].getAsString();
        if (!selector || selector->empty()) {
            context.error(
                path + ".all_of[" + std::to_string(index) + "]",
                "expected non-empty string");
        } else if (!seen.insert(selector->str()).second) {
            context.error(path + ".all_of", "duplicate selector ref");
        } else {
            result.selector_ids.push_back(selector->str());
        }
    }
    if (result.selector_ids.empty()) {
        context.error(path + ".all_of", "at least one selector is required");
    }
    return result;
}

std::optional<AtomicProposition> parse_ap(
    const Object *object, const std::string &path,
    const std::string &schema_version, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected atomic proposition object");
        return std::nullopt;
    }
    if (schema_version == "1.0.0") {
        reject_unknown_members(
            *object,
            {"ap_id", "roles", "value_type", "predicate", "selector_refs",
             "description"},
            path, context);
    } else {
        reject_unknown_members(
            *object,
            {"ap_id", "roles", "value_type", "predicate",
             "role_selector_groups", "description"},
            path, context);
    }
    const auto id = string_member(*object, "ap_id", path, context);
    const auto type = parse_value_type(
        object->getObject("value_type"), path + ".value_type", context);
    const auto predicate = parse_expression(
        object->getObject("predicate"), path + ".predicate", context);
    const Array *roles = object->getArray("roles");
    const Array *selectors = schema_version == "1.0.0"
                                 ? object->getArray("selector_refs")
                                 : nullptr;
    const Array *role_groups = schema_version == "2.0.0"
                                   ? object->getArray("role_selector_groups")
                                   : nullptr;
    if (roles == nullptr) {
        context.error(path + ".roles", "expected array");
    }
    if (schema_version == "1.0.0" && selectors == nullptr) {
        context.error(path + ".selector_refs", "expected array");
    }
    if (schema_version == "2.0.0" && role_groups == nullptr) {
        context.error(path + ".role_selector_groups", "expected array");
    }
    if (!id || !type || !predicate || roles == nullptr ||
        (schema_version == "1.0.0" && selectors == nullptr) ||
        (schema_version == "2.0.0" && role_groups == nullptr)) {
        return std::nullopt;
    }
    AtomicProposition result;
    result.ap_id = *id;
    result.value_type = *type;
    result.predicate = *predicate;
    std::set<ApRole> seen_roles;
    for (std::size_t index = 0; index < roles->size(); ++index) {
        const auto text = (*roles)[index].getAsString();
        const auto role = text ? parse_role(*text) : std::nullopt;
        if (!role) {
            context.error(
                path + ".roles[" + std::to_string(index) + "]",
                "unsupported AP role");
        } else if (!seen_roles.insert(*role).second) {
            context.error(path + ".roles", "duplicate AP role");
        } else {
            result.roles.push_back(*role);
        }
    }
    if (result.roles.empty()) {
        context.error(path + ".roles", "at least one role is required");
    }
    if (selectors != nullptr) {
        std::set<std::string> seen_selectors;
        for (std::size_t index = 0; index < selectors->size(); ++index) {
            const auto text = (*selectors)[index].getAsString();
            if (!text || text->empty()) {
                context.error(
                    path + ".selector_refs[" + std::to_string(index) + "]",
                    "expected non-empty string");
            } else if (!seen_selectors.insert(text->str()).second) {
                context.error(path + ".selector_refs", "duplicate selector ref");
            } else {
                result.selector_ids.push_back(text->str());
            }
        }
    }
    if (role_groups != nullptr) {
        for (std::size_t index = 0; index < role_groups->size(); ++index) {
            auto group = parse_role_selector_group(
                (*role_groups)[index].getAsObject(),
                path + ".role_selector_groups[" +
                    std::to_string(index) + "]",
                context);
            if (group) {
                result.role_selector_groups.push_back(std::move(*group));
            }
        }
    }
    if (const auto description = object->getString("description")) {
        if (description->empty()) {
            context.error(path + ".description", "must be non-empty");
        } else {
            result.description = description->str();
        }
    }
    return result;
}

void collect_expression_refs(
    const ExpressionStructure &expression, std::set<std::string> &refs) {
    if (expression.referenced_selector_id) {
        refs.insert(*expression.referenced_selector_id);
    }
    for (const ExpressionStructure &operand : expression.operands) {
        collect_expression_refs(operand, refs);
    }
}

void validate_formula_refs(
    const FormulaNode &formula, const std::set<std::string> &ap_ids,
    std::set<std::string> &formula_ids, std::vector<std::string> &errors) {
    if (!formula_ids.insert(formula.node_id).second) {
        errors.push_back("duplicate formula node ID: " + formula.node_id);
    }
    if (formula.ap_id && !ap_ids.contains(*formula.ap_id)) {
        errors.push_back("formula references unknown AP: " + *formula.ap_id);
    }
    if (formula.interval) {
        const TimeInterval &interval = *formula.interval;
        if (interval.upper && interval.lower > *interval.upper) {
            errors.push_back(
                "interval lower exceeds upper at formula node: " +
                formula.node_id);
        }
        for (const std::string &ap : interval.bound_ap_ids) {
            if (!ap_ids.contains(ap)) {
                errors.push_back("interval references unknown bound AP: " + ap);
            }
        }
    }
    for (const FormulaNode &operand : formula.operands) {
        validate_formula_refs(operand, ap_ids, formula_ids, errors);
    }
}

template <typename Range, typename Getter>
void require_unique_ids(
    const Range &range, Getter getter, const std::string &kind,
    std::set<std::string> &global, std::vector<std::string> &errors) {
    for (const auto &item : range) {
        const std::string &id = getter(item);
        if (id.empty()) {
            errors.push_back(kind + " has empty ID");
        } else if (!global.insert(id).second) {
            errors.push_back("duplicate cross-artifact ID " + id + " (" + kind + ')');
        }
    }
}

bool valid_sha256(const std::string &value) {
    if (value.size() != 64) {
        return false;
    }
    return std::all_of(value.begin(), value.end(), [](const char character) {
        return (character >= '0' && character <= '9') ||
               (character >= 'a' && character <= 'f');
    });
}

}  // namespace

LoadResult<TypedPropertyIr> load_typed_property_ir(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256) {
    LoadResult<TypedPropertyIr> result;
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        result.diagnostics.push_back("cannot open typed Property IR: " + path.string());
        return result;
    }
    const std::string bytes{
        std::istreambuf_iterator<char>(stream),
        std::istreambuf_iterator<char>()};
    result.observed_sha256 = sha256_hex(bytes);
    if (expected_sha256) {
        if (!valid_sha256(*expected_sha256)) {
            result.diagnostics.push_back("expected Property IR digest is not SHA-256");
            return result;
        }
        if (*expected_sha256 != result.observed_sha256) {
            result.diagnostics.push_back(
                "typed Property IR digest mismatch: expected " +
                *expected_sha256 + ", observed " + result.observed_sha256);
            return result;
        }
    }

    llvm::Expected<Value> parsed = llvm::json::parse(bytes);
    if (!parsed) {
        result.diagnostics.push_back(
            "invalid typed Property IR JSON: " +
            llvm::toString(parsed.takeError()));
        return result;
    }
    const Object *root = parsed->getAsObject();
    if (root == nullptr) {
        result.diagnostics.push_back("typed Property IR root must be an object");
        return result;
    }
    ParseContext context;
    reject_unknown_members(
        *root,
        {"schema_version", "artifact_id", "property_id", "logic",
         "time_domain", "formula_text", "formula", "atomic_propositions",
         "selectors", "source_document"},
        "$", context);
    const auto schema = string_member(*root, "schema_version", "$", context);
    if (schema && *schema != "1.0.0" && *schema != "2.0.0") {
        context.error("$.schema_version", "unsupported schema version");
    }
    const auto artifact = string_member(*root, "artifact_id", "$", context);
    const auto property_id = string_member(*root, "property_id", "$", context);
    const auto logic = string_member(*root, "logic", "$", context);
    const auto time_domain = string_member(*root, "time_domain", "$", context);
    const auto formula_text = string_member(*root, "formula_text", "$", context);
    auto formula = parse_formula(root->getObject("formula"), "$.formula", context);
    const Array *aps = root->getArray("atomic_propositions");
    const Array *selectors = root->getArray("selectors");
    if (aps == nullptr || aps->empty()) {
        context.error("$.atomic_propositions", "expected non-empty array");
    }
    if (selectors == nullptr) {
        context.error("$.selectors", "expected array");
    }
    if (!schema || !artifact || !property_id || !logic || !time_domain || !formula_text ||
        !formula || aps == nullptr || selectors == nullptr) {
        result.diagnostics = std::move(context.errors);
        return result;
    }
    TypedPropertyIr property;
    property.schema_version = *schema;
    property.artifact_id = *artifact;
    property.artifact_sha256 = result.observed_sha256;
    property.property_id = *property_id;
    property.logic = *logic;
    property.time_domain = *time_domain;
    property.formula_text = *formula_text;
    property.formula = std::move(*formula);
    for (std::size_t index = 0; index < aps->size(); ++index) {
        auto ap = parse_ap(
            (*aps)[index].getAsObject(),
            "$.atomic_propositions[" + std::to_string(index) + "]",
            property.schema_version, context);
        if (ap) {
            property.atomic_propositions.push_back(std::move(*ap));
        }
    }
    for (std::size_t index = 0; index < selectors->size(); ++index) {
        auto selector = parse_selector(
            (*selectors)[index].getAsObject(),
            "$.selectors[" + std::to_string(index) + "]", context);
        if (selector) {
            property.selectors.push_back(std::move(*selector));
        }
    }
    std::vector<std::string> semantic_errors = validate_typed_property_ir(property);
    context.errors.insert(
        context.errors.end(), semantic_errors.begin(), semantic_errors.end());
    if (!context.errors.empty()) {
        result.diagnostics = std::move(context.errors);
        return result;
    }
    result.status = StageStatus::Complete;
    result.value = std::move(property);
    return result;
}

std::vector<std::string> validate_typed_property_ir(
    const TypedPropertyIr &property) {
    std::vector<std::string> errors;
    if (property.schema_version != "1.0.0" &&
        property.schema_version != "2.0.0") {
        errors.push_back("typed Property IR has unsupported schema version");
    }
    if (!valid_sha256(property.artifact_sha256)) {
        errors.push_back("typed Property IR has invalid artifact SHA-256");
    }
    std::set<std::string> global_ids;
    if (!global_ids.insert(property.artifact_id).second ||
        !global_ids.insert(property.property_id).second) {
        errors.push_back("property artifact/property IDs collide");
    }
    require_unique_ids(
        property.selectors,
        [](const Selector &selector) -> const std::string & {
            return selector.selector_id;
        },
        "selector", global_ids, errors);
    require_unique_ids(
        property.atomic_propositions,
        [](const AtomicProposition &ap) -> const std::string & {
            return ap.ap_id;
        },
        "atomic proposition", global_ids, errors);
    for (const AtomicProposition &ap : property.atomic_propositions) {
        for (const RoleSelectorGroup &group : ap.role_selector_groups) {
            if (group.group_id.empty()) {
                errors.push_back("role selector group has empty ID");
            } else if (!global_ids.insert(group.group_id).second) {
                errors.push_back(
                    "duplicate cross-artifact ID " + group.group_id +
                    " (role selector group)");
            }
        }
    }

    std::set<std::string> selector_ids;
    for (const Selector &selector : property.selectors) {
        selector_ids.insert(selector.selector_id);
    }
    for (const Selector &selector : property.selectors) {
        for (const std::string &component : selector.component_ids) {
            if (!selector_ids.contains(component)) {
                errors.push_back(
                    "composite selector references unknown component: " + component);
            }
            if (component == selector.selector_id) {
                errors.push_back("composite selector directly references itself: " + component);
            }
        }
        if (selector.expression) {
            std::set<std::string> refs;
            collect_expression_refs(*selector.expression, refs);
            for (const std::string &ref : refs) {
                if (!selector_ids.contains(ref)) {
                    errors.push_back("selector expression references unknown selector: " + ref);
                }
            }
        }
    }
    std::set<std::string> ap_ids;
    for (const AtomicProposition &ap : property.atomic_propositions) {
        ap_ids.insert(ap.ap_id);
        const std::set<ApRole> declared_roles(
            ap.roles.begin(), ap.roles.end());
        std::set<ApRole> grouped_roles;
        std::set<std::string> grouped_selectors;
        if (property.schema_version == "1.0.0" &&
            !ap.role_selector_groups.empty()) {
            errors.push_back(
                "legacy AP must not contain role selector groups: " + ap.ap_id);
        }
        if (property.schema_version == "2.0.0" &&
            !ap.selector_ids.empty()) {
            errors.push_back(
                "role-DNF AP must not contain flat selector refs: " + ap.ap_id);
        }
        for (const std::string &selector : ap.selector_ids) {
            if (!selector_ids.contains(selector)) {
                errors.push_back("AP references unknown selector: " + selector);
            }
        }
        for (const RoleSelectorGroup &group : ap.role_selector_groups) {
            if (!declared_roles.contains(group.role)) {
                errors.push_back(
                    "selector group uses an undeclared AP role: " +
                    group.group_id);
            } else {
                grouped_roles.insert(group.role);
            }
            if (group.selector_ids.empty()) {
                errors.push_back(
                    "role selector group has empty all-of clause: " +
                    group.group_id);
            }
            std::set<std::string> within_group;
            for (const std::string &selector : group.selector_ids) {
                if (!within_group.insert(selector).second) {
                    errors.push_back(
                        "role selector group repeats selector: " +
                        group.group_id + '/' + selector);
                }
                if (!selector_ids.contains(selector)) {
                    errors.push_back(
                        "role selector group references unknown selector: " +
                        selector);
                }
                grouped_selectors.insert(selector);
            }
        }
        if (property.schema_version == "2.0.0") {
            for (const ApRole role : declared_roles) {
                if (!grouped_roles.contains(role)) {
                    errors.push_back(
                        "declared role has no selector group: " + ap.ap_id);
                }
            }
        }
        std::set<std::string> refs;
        collect_expression_refs(ap.predicate, refs);
        for (const std::string &ref : refs) {
            if (!selector_ids.contains(ref)) {
                errors.push_back("AP predicate references unknown selector: " + ref);
            }
            if (property.schema_version == "2.0.0" &&
                !grouped_selectors.contains(ref)) {
                errors.push_back(
                    "AP predicate selector is not covered by a role selector group: " +
                    ref);
            }
        }
    }
    std::set<std::string> formula_ids;
    validate_formula_refs(property.formula, ap_ids, formula_ids, errors);
    for (const std::string &id : formula_ids) {
        if (!global_ids.insert(id).second) {
            errors.push_back("formula node ID collides across property artifact: " + id);
        }
    }
    return errors;
}

std::vector<std::string> validate_semantic_index(const SemanticIndex &index) {
    std::vector<std::string> errors;
    if (!valid_sha256(index.compilation_database_sha256)) {
        errors.push_back("semantic index has invalid compilation database digest");
    }
    const bool portable_identity = !index.identity_scheme.empty();
    std::set<std::string> logical_roots;
    if (portable_identity) {
        if (index.identity_scheme != kIdentityScheme) {
            errors.push_back("semantic index uses an unsupported identity scheme");
        }
        if (!valid_sha256(index.canonical_compilation_database_sha256)) {
            errors.push_back(
                "semantic index has invalid canonical compilation database digest");
        }
        if (!valid_sha256(index.path_map_sha256)) {
            errors.push_back("semantic index has invalid path-map digest");
        }
        if (index.source_identity_root !=
            index.identity_scheme + ':' + index.path_map_sha256) {
            errors.push_back(
                "semantic index identity descriptor is not bound to its path map");
        }
        for (const std::string &root : index.logical_root_ids) {
            if (root.empty() || !logical_roots.insert(root).second) {
                errors.push_back(
                    "semantic index has an empty or duplicate logical root ID");
            }
        }
        if (logical_roots.empty()) {
            errors.push_back("portable semantic index has no logical roots");
        }
        std::vector<LogicalPathRoot> root_descriptors;
        for (const std::string &root : logical_roots) {
            root_descriptors.push_back({root, {}});
        }
        if (valid_sha256(index.path_map_sha256) &&
            index.path_map_sha256 !=
                identity_path_map_sha256(root_descriptors)) {
            errors.push_back(
                "semantic index path-map digest is not bound to logical root IDs");
        }
    }
    auto valid_logical_path = [&](const std::string &path) {
        if (!portable_identity || path.empty()) {
            return true;
        }
        constexpr std::string_view prefix = "riftpath://v1/";
        if (!path.starts_with(prefix)) {
            return false;
        }
        const std::size_t separator = path.find('/', prefix.size());
        if (separator == std::string::npos) {
            return false;
        }
        const std::string root =
            path.substr(prefix.size(), separator - prefix.size());
        // `toolchain` is a reserved content-addressed identity domain for
        // system headers, compiler predefines, and declarations for which
        // Clang exposes no physical spelling.  It is intentionally not tied
        // to a checkout-specific physical root.
        return root == "toolchain" || logical_roots.contains(root);
    };
    std::set<std::string> ids;
    ids.insert(index.artifact_id);
    require_unique_ids(
        index.translation_units,
        [](const TranslationUnitRecord &item) -> const std::string & {
            return item.translation_unit_id;
        },
        "translation unit", ids, errors);
    require_unique_ids(
        index.input_files,
        [](const InputFileDigest &item) -> const std::string & {
            return item.input_file_id;
        },
        "input file", ids, errors);
    require_unique_ids(
        index.entities,
        [](const EntityRef &item) -> const std::string & { return item.entity_id; },
        "entity", ids, errors);
    require_unique_ids(
        index.abstract_objects,
        [](const AbstractObject &item) -> const std::string & { return item.object_id; },
        "abstract object", ids, errors);
    require_unique_ids(
        index.nodes,
        [](const SemanticNode &item) -> const std::string & { return item.node_id; },
        "semantic node", ids, errors);
    require_unique_ids(
        index.relations,
        [](const SemanticRelation &item) -> const std::string & {
            return item.relation_id;
        },
        "semantic relation", ids, errors);
    require_unique_ids(
        index.callsites,
        [](const CallSiteSummary &item) -> const std::string & {
            return item.callsite_id;
        },
        "callsite", ids, errors);

    std::set<std::string> tus;
    std::set<std::string> input_file_ids;
    std::map<std::string, const InputFileDigest *> inputs_by_id;
    std::map<std::string, std::string> input_digest_by_path;
    std::set<std::string> entities;
    std::set<std::string> objects;
    std::set<std::string> nodes;
    std::set<std::string> relations;
    std::set<std::string> callsites;
    auto valid_input_path = [&](const std::string &path) {
        constexpr std::string_view toolchain = "riftpath://v1/toolchain/";
        return path.starts_with(toolchain) || valid_logical_path(path);
    };
    std::ostringstream input_manifest;
    input_manifest << kIdentityScheme << '\0' << "input-manifest/1.0.0";
    for (const InputFileDigest &input : index.input_files) {
        input_file_ids.insert(input.input_file_id);
        inputs_by_id[input.input_file_id] = &input;
        if (!valid_sha256(input.sha256)) {
            errors.push_back(
                "input file has invalid content digest: " +
                input.input_file_id);
        }
        if (!valid_input_path(input.logical_path)) {
            errors.push_back(
                "input file has invalid logical path: " +
                input.input_file_id);
        }
        if (input.role != InputFileRole::Toolchain &&
            input.observed_paths.empty()) {
            errors.push_back(
                "file-backed input has no physical provenance path: " +
                input.input_file_id);
        }
        std::set<std::string> observed_paths;
        for (const std::string &path : input.observed_paths) {
            if (!std::filesystem::path(path).is_absolute()) {
                errors.push_back(
                    "input provenance path is not absolute: " +
                    input.input_file_id);
            }
            if (!observed_paths.insert(path).second) {
                errors.push_back(
                    "input provenance path is duplicated: " +
                    input.input_file_id);
            }
        }
        const std::string expected_id = stable_id(
            "input-file", std::string(kIdentityScheme) + '\0' +
                              to_string(input.role) + '\0' +
                              input.logical_path + '\0' + input.sha256);
        if (input.input_file_id != expected_id) {
            errors.push_back(
                "input file ID is not bound to path/role/content: " +
                input.input_file_id);
        }
        const auto [known, inserted] = input_digest_by_path.emplace(
            input.logical_path, input.sha256);
        if (!inserted && known->second != input.sha256) {
            errors.push_back(
                "one logical input path has multiple content digests: " +
                input.logical_path);
        }
        input_manifest << '\0' << to_string(input.role) << '\0'
                       << input.logical_path.size() << ':'
                       << input.logical_path << '\0' << input.sha256 << '\0'
                       << input.byte_size;
    }
    if (portable_identity &&
        (!valid_sha256(index.input_manifest_sha256) ||
         index.input_manifest_sha256 != sha256_hex(input_manifest.str()))) {
        errors.push_back(
            "semantic index input manifest digest is invalid or stale");
    }
    if (portable_identity && valid_sha256(index.input_manifest_sha256)) {
        const std::string expected_artifact = stable_id(
            "index", index.identity_scheme + '\0' +
                         index.canonical_compilation_database_sha256 + '\0' +
                         index.path_map_sha256 + '\0' +
                         index.input_manifest_sha256);
        if (index.artifact_id != expected_artifact) {
            errors.push_back(
                "semantic index artifact ID is not bound to canonical inputs");
        }
    }
    for (const auto &item : index.translation_units) {
        tus.insert(item.translation_unit_id);
        if (!valid_logical_path(item.source_file) ||
            !valid_logical_path(item.working_directory)) {
            errors.push_back(
                "translation unit contains a non-logical persisted path: " +
                item.translation_unit_id);
        }
        if (portable_identity && !valid_sha256(item.command_sha256)) {
            errors.push_back(
                "translation unit has invalid canonical command digest: " +
                item.translation_unit_id);
        }
        bool has_main_input = false;
        for (const std::string &input_id : item.input_file_ids) {
            const auto input = inputs_by_id.find(input_id);
            if (input == inputs_by_id.end()) {
                errors.push_back(
                    "translation unit references unknown input file: " +
                    input_id);
                continue;
            }
            has_main_input = has_main_input ||
                             input->second->role == InputFileRole::Main;
        }
        if (portable_identity && item.status != StageStatus::Failed &&
            !has_main_input) {
            errors.push_back(
                "non-failed translation unit has no main input digest: " +
                item.translation_unit_id);
        }
    }
    for (const auto &item : index.entities) {
        entities.insert(item.entity_id);
        for (const std::string &tu : item.translation_unit_ids) {
            if (!tus.contains(tu)) {
                errors.push_back("entity references unknown translation unit: " + tu);
            }
        }
        for (const SourceLocation &location : item.declarations) {
            if (!valid_logical_path(location.file)) {
                errors.push_back(
                    "entity declaration contains a non-logical path: " +
                    item.entity_id);
            }
        }
        for (const SourceLocation &location : item.definitions) {
            if (!valid_logical_path(location.file)) {
                errors.push_back(
                    "entity definition contains a non-logical path: " +
                    item.entity_id);
            }
        }
    }
    for (const auto &item : index.abstract_objects) {
        objects.insert(item.object_id);
    }
    for (const auto &item : index.nodes) {
        nodes.insert(item.node_id);
        if (!entities.contains(item.entity_id)) {
            errors.push_back("semantic node references unknown entity: " + item.entity_id);
        }
        if (item.abstract_object_id && !objects.contains(*item.abstract_object_id)) {
            errors.push_back("semantic node references unknown object: " + *item.abstract_object_id);
        }
        if (item.access_path &&
            !entities.contains(item.access_path->root_entity_id)) {
            errors.push_back(
                "semantic node access path references unknown root entity: " +
                item.access_path->root_entity_id);
        }
        if (item.access_path) {
            for (const std::string &field : item.access_path->fields) {
                if (!entities.contains(field)) {
                    errors.push_back(
                        "semantic node access path references unknown field entity: " +
                        field);
                }
            }
        }
        if (!valid_logical_path(item.location.file)) {
            errors.push_back(
                "semantic node contains a non-logical source path: " +
                item.node_id);
        }
    }
    for (const auto &item : index.callsites) {
        callsites.insert(item.callsite_id);
    }
    for (const auto &item : index.relations) {
        relations.insert(item.relation_id);
        if (!nodes.contains(item.source_node_id)) {
            errors.push_back("relation references unknown source node: " + item.source_node_id);
        }
        if (!nodes.contains(item.target_node_id)) {
            errors.push_back("relation references unknown target node: " + item.target_node_id);
        }
        for (const std::string &condition : item.condition_node_ids) {
            if (!nodes.contains(condition)) {
                errors.push_back("relation references unknown condition node: " + condition);
            }
        }
        if (item.callsite_id && !callsites.contains(*item.callsite_id)) {
            errors.push_back(
                "relation references unknown callsite: " +
                *item.callsite_id);
        }
    }
    for (const auto &item : index.callsites) {
        if (!entities.contains(item.caller_function_id)) {
            errors.push_back("callsite references unknown caller: " + item.caller_function_id);
        }
        for (const std::string &callee : item.candidate_callee_ids) {
            if (!entities.contains(callee)) {
                errors.push_back("callsite references unknown callee: " + callee);
            }
        }
        for (const std::string &argument : item.argument_node_ids) {
            if (!nodes.contains(argument)) {
                errors.push_back("callsite references unknown argument node: " + argument);
            }
        }
        if (item.argument_node_groups.size() !=
            item.argument_is_address.size()) {
            errors.push_back(
                "callsite positional argument/address arity mismatch: " +
                item.callsite_id);
        }
        std::set<std::string> grouped_arguments;
        for (const std::vector<std::string> &group :
             item.argument_node_groups) {
            if (group.empty()) {
                errors.push_back(
                    "callsite contains an empty positional argument group: " +
                    item.callsite_id);
            }
            std::set<std::string> group_ids;
            for (const std::string &argument : group) {
                if (!group_ids.insert(argument).second) {
                    errors.push_back(
                        "callsite positional argument group contains a duplicate node: " +
                        argument);
                }
                grouped_arguments.insert(argument);
                if (!nodes.contains(argument)) {
                    errors.push_back(
                        "callsite positional argument group references unknown node: " +
                        argument);
                }
            }
        }
        const std::set<std::string> flat_arguments(
            item.argument_node_ids.begin(), item.argument_node_ids.end());
        if (flat_arguments != grouped_arguments) {
            errors.push_back(
                "callsite flat and positional argument references disagree: " +
                item.callsite_id);
        }
        if (item.receiver_node_id && !nodes.contains(*item.receiver_node_id)) {
            errors.push_back("callsite references unknown receiver node: " + *item.receiver_node_id);
        }
        if (item.result_node_id && !nodes.contains(*item.result_node_id)) {
            errors.push_back("callsite references unknown result node: " + *item.result_node_id);
        }
    }
    std::set<std::string> summary_functions;
    for (const FunctionSummary &summary : index.function_summaries) {
        if (!summary_functions.insert(summary.function_entity_id).second) {
            errors.push_back("duplicate function summary: " + summary.function_entity_id);
        }
        if (!entities.contains(summary.function_entity_id)) {
            errors.push_back("summary references unknown function: " + summary.function_entity_id);
        }
        auto check_node = [&](const std::string &node) {
            if (!nodes.contains(node)) {
                errors.push_back("summary references unknown node: " + node);
            }
        };
        for (const std::string &node : summary.parameter_node_ids) {
            check_node(node);
        }
        for (const std::string &node : summary.owned_node_ids) {
            check_node(node);
        }
        if (summary.receiver_node_id) {
            check_node(*summary.receiver_node_id);
        }
        if (summary.return_node_id) {
            check_node(*summary.return_node_id);
        }
        for (const std::string &relation : summary.relation_ids) {
            if (!relations.contains(relation)) {
                errors.push_back("summary references unknown relation: " + relation);
            }
        }
        for (const std::string &callsite : summary.callsite_ids) {
            if (!callsites.contains(callsite)) {
                errors.push_back("summary references unknown callsite: " + callsite);
            }
        }
    }
    return errors;
}

std::vector<std::string> validate_contextual_graph(
    const ContextualInfluenceGraph &graph,
    const std::optional<std::string> &expected_semantic_index_sha256) {
    std::vector<std::string> errors;
    if (!valid_sha256(graph.semantic_index_sha256)) {
        errors.push_back("contextual graph has invalid semantic index digest");
    }
    if (expected_semantic_index_sha256 &&
        graph.semantic_index_sha256 != *expected_semantic_index_sha256) {
        errors.push_back("contextual graph semantic index digest mismatch");
    }
    std::set<std::string> ids{graph.artifact_id};
    require_unique_ids(
        graph.nodes,
        [](const ContextualNode &item) -> const std::string & { return item.node_id; },
        "contextual node", ids, errors);
    require_unique_ids(
        graph.edges,
        [](const InfluenceEdge &item) -> const std::string & { return item.edge_id; },
        "influence edge", ids, errors);
    std::set<std::string> nodes;
    for (const ContextualNode &node : graph.nodes) {
        nodes.insert(node.node_id);
        if (!node.entity || node.entity->entity_id.empty()) {
            errors.push_back(
                "contextual node has no interned source entity: " +
                node.node_id);
        }
    }
    for (const InfluenceEdge &edge : graph.edges) {
        if (!edge.evidence || edge.evidence->empty()) {
            errors.push_back(
                "influence edge has no evidence: " + edge.edge_id);
        }
        if (!nodes.contains(edge.source_node_id)) {
            errors.push_back("edge references unknown source node: " + edge.source_node_id);
        }
        if (!nodes.contains(edge.target_node_id)) {
            errors.push_back("edge references unknown target node: " + edge.target_node_id);
        }
        for (const std::string &condition : edge.condition_node_ids) {
            if (!nodes.contains(condition)) {
                errors.push_back("edge references unknown condition node: " + condition);
            }
        }
        if (edge.certainty == Certainty::Unknown &&
            edge.uncertainty_reasons.empty()) {
            errors.push_back("unknown edge lacks uncertainty reason: " + edge.edge_id);
        }
    }
    return errors;
}

}  // namespace rift::core
