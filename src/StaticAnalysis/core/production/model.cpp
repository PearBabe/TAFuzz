#include "rift/core/model.h"

#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <functional>
#include <iterator>
#include <limits>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <utility>

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

std::string make_id(
    const std::string &prefix, const std::string &semantic_material) {
    return prefix + ':' + sha256_hex(semantic_material);
}

bool is_sha256(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](const unsigned char c) {
               return std::isdigit(c) != 0 || (c >= 'a' && c <= 'f');
           });
}

bool is_stable_id(const std::string &value) {
    static const std::regex pattern("^[A-Za-z][A-Za-z0-9_.:-]{0,127}$");
    return std::regex_match(value, pattern);
}

bool is_semver(const std::string &value) {
    static const std::regex pattern(
        "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\."
        "(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$");
    return std::regex_match(value, pattern);
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

std::optional<std::string> required_string(
    const Object &object, llvm::StringRef key, const std::string &path,
    ParseContext &context) {
    const std::optional<llvm::StringRef> value = object.getString(key);
    if (!value || value->empty()) {
        context.error(path + '.' + key.str(), "expected non-empty string");
        return std::nullopt;
    }
    return value->str();
}

std::optional<bool> required_bool(
    const Object &object, llvm::StringRef key, const std::string &path,
    ParseContext &context) {
    const std::optional<bool> value = object.getBoolean(key);
    if (!value) {
        context.error(path + '.' + key.str(), "expected boolean");
    }
    return value;
}

std::optional<std::uint64_t> required_positive_uint(
    const Object &object, llvm::StringRef key, const std::string &path,
    ParseContext &context) {
    const std::optional<std::int64_t> value = object.getInteger(key);
    if (!value || *value <= 0) {
        context.error(path + '.' + key.str(), "expected positive integer");
        return std::nullopt;
    }
    return static_cast<std::uint64_t>(*value);
}

template <typename Enum>
std::optional<Enum> parse_enum(
    const std::optional<std::string> &text,
    const std::map<std::string, Enum> &values, const std::string &path,
    ParseContext &context) {
    if (!text) {
        return std::nullopt;
    }
    const auto found = values.find(*text);
    if (found == values.end()) {
        context.error(path, "unsupported enum value '" + *text + "'");
        return std::nullopt;
    }
    return found->second;
}

std::optional<ValueKind> parse_value_kind(const std::string &text) {
    static const std::map<std::string, ValueKind> values{
        {"bool", ValueKind::Boolean},       {"integer", ValueKind::Integer},
        {"floating", ValueKind::Floating}, {"enum", ValueKind::Enumeration},
        {"bitvector", ValueKind::BitVector},
        {"timestamp", ValueKind::Timestamp},
        {"duration", ValueKind::Duration}, {"pointer", ValueKind::Pointer},
        {"record", ValueKind::Record},     {"array", ValueKind::Array},
        {"unknown", ValueKind::Unknown},
    };
    const auto found = values.find(text);
    return found == values.end() ? std::nullopt
                                 : std::optional<ValueKind>(found->second);
}

std::optional<ValueType> parse_value_type(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object, {"kind", "canonical", "bit_width", "signed", "unit"},
        path, context);
    const auto kind_text = required_string(*object, "kind", path, context);
    const auto canonical = required_string(*object, "canonical", path, context);
    if (!kind_text || !canonical) {
        return std::nullopt;
    }
    const auto kind = parse_value_kind(*kind_text);
    if (!kind) {
        context.error(path + ".kind", "unsupported value kind");
        return std::nullopt;
    }
    ValueType type;
    type.kind = *kind;
    type.canonical = *canonical;
    if (const auto width = object->getInteger("bit_width")) {
        if (*width <= 0 ||
            *width > static_cast<std::int64_t>(
                         std::numeric_limits<std::uint32_t>::max())) {
            context.error(path + ".bit_width", "expected positive uint32");
        } else {
            type.bit_width = static_cast<std::uint32_t>(*width);
        }
    } else if (object->get("bit_width") != nullptr) {
        context.error(path + ".bit_width", "expected integer");
    }
    if (const auto signed_value = object->getBoolean("signed")) {
        type.is_signed = *signed_value;
    } else if (object->get("signed") != nullptr) {
        context.error(path + ".signed", "expected boolean");
    }
    if (const auto unit = object->getString("unit")) {
        if (unit->empty()) {
            context.error(path + ".unit", "must not be empty");
        } else {
            type.unit = unit->str();
        }
    } else if (object->get("unit") != nullptr) {
        context.error(path + ".unit", "expected string");
    }
    return type;
}

std::optional<ModelTargetContract> parse_target(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"target_version", "target_abi", "evidence_id", "digest_policy"},
        path, context);
    ModelTargetContract target;
    const auto version = required_string(*object, "target_version", path, context);
    const auto abi = required_string(*object, "target_abi", path, context);
    const auto evidence = required_string(*object, "evidence_id", path, context);
    const auto digest = required_string(*object, "digest_policy", path, context);
    if (!version || !abi || !evidence || !digest) {
        return std::nullopt;
    }
    target.target_version = *version;
    target.target_abi = *abi;
    target.evidence_id = *evidence;
    target.digest_policy = *digest;
    return target;
}

std::optional<ModelResourceLimits> parse_limits(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"max_selector_matches", "max_capture_values",
         "max_join_assignments", "max_emitted_facts"},
        path, context);
    const auto selectors = required_positive_uint(
        *object, "max_selector_matches", path, context);
    const auto captures = required_positive_uint(
        *object, "max_capture_values", path, context);
    const auto joins = required_positive_uint(
        *object, "max_join_assignments", path, context);
    const auto emits = required_positive_uint(
        *object, "max_emitted_facts", path, context);
    if (!selectors || !captures || !joins || !emits) {
        return std::nullopt;
    }
    return ModelResourceLimits{*selectors, *captures, *joins, *emits};
}

std::optional<ModelSelectorV2> parse_selector(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"selector_id", "kind", "exact_value", "owner_selector_ref",
         "field_path", "canonical_type", "application_private"},
        path, context);
    const auto id = required_string(*object, "selector_id", path, context);
    const auto kind_text = required_string(*object, "kind", path, context);
    static const std::map<std::string, ModelSelectorKind> kinds{
        {"exact_qualified_signature", ModelSelectorKind::ExactQualifiedSignature},
        {"exact_usr", ModelSelectorKind::ExactUsr},
        {"typed_field", ModelSelectorKind::TypedField},
    };
    const auto kind = parse_enum(kind_text, kinds, path + ".kind", context);
    if (!id || !kind) {
        return std::nullopt;
    }
    ModelSelectorV2 selector;
    selector.selector_id = *id;
    selector.kind = *kind;
    if (const auto value = object->getString("exact_value")) {
        if (value->empty()) {
            context.error(path + ".exact_value", "must not be empty");
        } else {
            selector.exact_value = value->str();
        }
    } else if (object->get("exact_value") != nullptr) {
        context.error(path + ".exact_value", "expected string");
    }
    if (const auto owner = object->getString("owner_selector_ref")) {
        if (owner->empty()) {
            context.error(path + ".owner_selector_ref", "must not be empty");
        } else {
            selector.owner_selector_ref = owner->str();
        }
    } else if (object->get("owner_selector_ref") != nullptr) {
        context.error(path + ".owner_selector_ref", "expected string");
    }
    if (const Array *fields = object->getArray("field_path")) {
        for (std::size_t i = 0; i < fields->size(); ++i) {
            const auto field = (*fields)[i].getAsString();
            if (!field || field->empty()) {
                context.error(
                    path + ".field_path[" + std::to_string(i) + "]",
                    "expected non-empty string");
            } else {
                selector.field_path.push_back(field->str());
            }
        }
    } else if (object->get("field_path") != nullptr) {
        context.error(path + ".field_path", "expected array");
    }
    if (const auto type = object->getString("canonical_type")) {
        if (type->empty()) {
            context.error(path + ".canonical_type", "must not be empty");
        } else {
            selector.canonical_type = type->str();
        }
    } else if (object->get("canonical_type") != nullptr) {
        context.error(path + ".canonical_type", "expected string");
    }
    if (const auto private_api = object->getBoolean("application_private")) {
        selector.application_private = *private_api;
    } else if (object->get("application_private") != nullptr) {
        context.error(path + ".application_private", "expected boolean");
    }
    return selector;
}

std::optional<ModelMatchV2> parse_match(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(*object, {"match_id", "selector_ref"}, path, context);
    const auto id = required_string(*object, "match_id", path, context);
    const auto selector = required_string(*object, "selector_ref", path, context);
    if (!id || !selector) {
        return std::nullopt;
    }
    return ModelMatchV2{*id, *selector};
}

std::optional<ModelCaptureV2> parse_capture(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object, {"capture_id", "match_ref", "projection", "index"},
        path, context);
    const auto id = required_string(*object, "capture_id", path, context);
    const auto match = required_string(*object, "match_ref", path, context);
    const auto projection_text = required_string(
        *object, "projection", path, context);
    static const std::map<std::string, ModelProjectionKind> projections{
        {"matched_node", ModelProjectionKind::MatchedNode},
        {"formal_parameter", ModelProjectionKind::FormalParameter},
        {"call_argument", ModelProjectionKind::CallArgument},
        {"call_result", ModelProjectionKind::CallResult},
        {"receiver", ModelProjectionKind::Receiver},
    };
    const auto projection = parse_enum(
        projection_text, projections, path + ".projection", context);
    if (!id || !match || !projection) {
        return std::nullopt;
    }
    ModelCaptureV2 capture;
    capture.capture_id = *id;
    capture.match_ref = *match;
    capture.projection = *projection;
    if (const auto index = object->getInteger("index")) {
        if (*index < 0 ||
            *index > static_cast<std::int64_t>(
                         std::numeric_limits<std::uint32_t>::max())) {
            context.error(path + ".index", "expected uint32");
        } else {
            capture.index = static_cast<std::uint32_t>(*index);
        }
    } else if (object->get("index") != nullptr) {
        context.error(path + ".index", "expected integer");
    }
    return capture;
}

std::optional<ModelJoinV2> parse_join(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"join_id", "kind", "left_capture_ref", "right_capture_ref"},
        path, context);
    const auto id = required_string(*object, "join_id", path, context);
    const auto kind_text = required_string(*object, "kind", path, context);
    const auto left = required_string(*object, "left_capture_ref", path, context);
    const auto right = required_string(*object, "right_capture_ref", path, context);
    static const std::map<std::string, ModelJoinKind> kinds{
        {"same_object", ModelJoinKind::SameObject},
        {"same_scope", ModelJoinKind::SameScope},
        {"same_generation", ModelJoinKind::SameGeneration},
        {"same_handle", ModelJoinKind::SameHandle},
        {"same_callsite", ModelJoinKind::SameCallsite},
        {"same_task", ModelJoinKind::SameTask},
    };
    const auto kind = parse_enum(kind_text, kinds, path + ".kind", context);
    if (!id || !kind || !left || !right) {
        return std::nullopt;
    }
    return ModelJoinV2{*id, *kind, *left, *right};
}

std::optional<ExternalActionTemplateV2> parse_action(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"action_schema_id", "action_class", "channel", "operation",
         "payload_type", "payload_slot", "scope_schema", "generation_schema",
         "timing_capability", "required_capability"},
        path, context);
    const auto schema = required_string(*object, "action_schema_id", path, context);
    const auto action_class = required_string(*object, "action_class", path, context);
    const auto channel = required_string(*object, "channel", path, context);
    const auto operation = required_string(*object, "operation", path, context);
    const auto type = parse_value_type(
        object->getObject("payload_type"), path + ".payload_type", context);
    const auto slot = required_string(*object, "payload_slot", path, context);
    const auto scope = required_string(*object, "scope_schema", path, context);
    const auto generation = required_string(
        *object, "generation_schema", path, context);
    const auto timing = required_string(
        *object, "timing_capability", path, context);
    const auto capability = required_string(
        *object, "required_capability", path, context);
    if (!schema || !action_class || !channel || !operation || !type || !slot ||
        !scope || !generation || !timing || !capability) {
        return std::nullopt;
    }
    return ExternalActionTemplateV2{
        *schema, *action_class, *channel, *operation, *type, *slot, *scope,
        *generation, *timing, *capability};
}

std::optional<ModelClockRelationV2> parse_clock_relation(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"clock_source", "unit", "epoch", "quantum", "jitter", "wrap",
         "wrap_value", "start_event", "end_event", "endpoint",
         "scope_schema", "generation_schema"},
        path, context);
    const auto source = required_string(*object, "clock_source", path, context);
    const auto unit_text = required_string(*object, "unit", path, context);
    const auto epoch = required_string(*object, "epoch", path, context);
    const auto wrap_text = required_string(*object, "wrap", path, context);
    const auto start = required_string(*object, "start_event", path, context);
    const auto end = required_string(*object, "end_event", path, context);
    const auto endpoint_text = required_string(
        *object, "endpoint", path, context);
    const auto scope = required_string(
        *object, "scope_schema", path, context);
    const auto generation = required_string(
        *object, "generation_schema", path, context);
    static const std::map<std::string, ModelClockUnit> units{
        {"ns", ModelClockUnit::Nanoseconds},
        {"us", ModelClockUnit::Microseconds},
        {"ms", ModelClockUnit::Milliseconds},
        {"s", ModelClockUnit::Seconds},
        {"ticks", ModelClockUnit::Ticks}};
    static const std::map<std::string, ModelClockWrap> wraps{
        {"none", ModelClockWrap::None},
        {"modulo", ModelClockWrap::Modulo},
        {"saturating", ModelClockWrap::Saturating},
        {"unknown", ModelClockWrap::Unknown}};
    static const std::map<std::string, ModelClockEndpoint> endpoints{
        {"open", ModelClockEndpoint::Open},
        {"closed", ModelClockEndpoint::Closed},
        {"mixed", ModelClockEndpoint::Mixed},
        {"unknown", ModelClockEndpoint::Unknown}};
    const auto unit = parse_enum(unit_text, units, path + ".unit", context);
    const auto wrap = parse_enum(wrap_text, wraps, path + ".wrap", context);
    const auto endpoint = parse_enum(
        endpoint_text, endpoints, path + ".endpoint", context);
    const auto quantum = object->getNumber("quantum");
    const auto jitter = object->getNumber("jitter");
    if (!quantum || !std::isfinite(*quantum) || *quantum <= 0.0) {
        context.error(path + ".quantum", "expected finite positive number");
    }
    if (!jitter || !std::isfinite(*jitter) || *jitter < 0.0) {
        context.error(
            path + ".jitter", "expected finite non-negative number");
    }
    std::optional<std::uint64_t> wrap_value;
    if (const auto raw = object->getInteger("wrap_value")) {
        if (*raw <= 0) {
            context.error(path + ".wrap_value", "expected positive integer");
        } else {
            wrap_value = static_cast<std::uint64_t>(*raw);
        }
    } else if (object->get("wrap_value") != nullptr) {
        context.error(path + ".wrap_value", "expected integer");
    }
    if (wrap && (*wrap == ModelClockWrap::Modulo ||
                 *wrap == ModelClockWrap::Saturating) &&
        !wrap_value) {
        context.error(
            path + ".wrap_value",
            "modulo/saturating wrap requires a positive bound");
    }
    if (wrap && (*wrap == ModelClockWrap::None ||
                 *wrap == ModelClockWrap::Unknown) &&
        wrap_value) {
        context.error(
            path + ".wrap_value",
            "none/unknown wrap must not declare a bound");
    }
    if (!source || !unit || !epoch || !quantum || !jitter || !wrap ||
        !start || !end || !endpoint || !scope || !generation) {
        return std::nullopt;
    }
    return ModelClockRelationV2{
        *source, *unit, *epoch, *quantum, *jitter, *wrap, wrap_value,
        *start, *end, *endpoint, *scope, *generation};
}

std::optional<ModelJointActionRelationV2> parse_joint_action_relation(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"group_schema_id", "combination", "participant_set_complete",
         "participant_capture_refs", "scope_schema", "generation_schema"},
        path, context);
    const auto group = required_string(
        *object, "group_schema_id", path, context);
    const auto combination_text = required_string(
        *object, "combination", path, context);
    const auto complete = required_bool(
        *object, "participant_set_complete", path, context);
    const auto scope = required_string(
        *object, "scope_schema", path, context);
    const auto generation = required_string(
        *object, "generation_schema", path, context);
    static const std::map<std::string, ModelJointActionOperator> operators{
        {"all_required", ModelJointActionOperator::AllRequired},
        {"any_sufficient", ModelJointActionOperator::AnySufficient},
        {"unknown", ModelJointActionOperator::Unknown}};
    const auto combination = parse_enum(
        combination_text, operators, path + ".combination", context);
    std::vector<std::string> participants;
    if (const Array *values = object->getArray("participant_capture_refs")) {
        for (std::size_t index = 0; index < values->size(); ++index) {
            const auto value = (*values)[index].getAsString();
            if (!value || value->empty()) {
                context.error(
                    path + ".participant_capture_refs[" +
                        std::to_string(index) + "]",
                    "expected non-empty string");
            } else {
                participants.push_back(value->str());
            }
        }
    } else {
        context.error(path + ".participant_capture_refs", "expected array");
    }
    if (!group || !combination || !complete || !scope || !generation) {
        return std::nullopt;
    }
    return ModelJointActionRelationV2{
        *group, *combination, *complete, std::move(participants), *scope,
        *generation};
}

std::optional<ModelValueTransferV2> parse_value_transfer(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"kind", "affine_scale", "affine_offset", "precondition",
         "executor_enforces_precondition", "failure_branch_unknown"},
        path, context);
    const auto kind_text = required_string(*object, "kind", path, context);
    const auto precondition_text = required_string(
        *object, "precondition", path, context);
    const auto enforces = required_bool(
        *object, "executor_enforces_precondition", path, context);
    const auto failure_unknown = required_bool(
        *object, "failure_branch_unknown", path, context);
    static const std::map<std::string, ModelValueTransferKind> kinds{
        {"identity", ModelValueTransferKind::Identity},
        {"affine", ModelValueTransferKind::Affine},
        {"parse_identity_with_precondition",
         ModelValueTransferKind::ParseIdentityWithPrecondition},
        {"unknown", ModelValueTransferKind::Unknown}};
    static const std::map<std::string, ModelValuePrecondition> preconditions{
        {"none", ModelValuePrecondition::None},
        {"canonical_decimal_integer_in_range",
         ModelValuePrecondition::CanonicalDecimalIntegerInRange},
        {"unknown", ModelValuePrecondition::Unknown}};
    const auto kind = parse_enum(kind_text, kinds, path + ".kind", context);
    const auto precondition = parse_enum(
        precondition_text, preconditions, path + ".precondition", context);
    std::optional<std::int64_t> scale;
    std::optional<std::int64_t> offset;
    if (const auto value = object->getInteger("affine_scale")) {
        scale = *value;
    } else if (object->get("affine_scale") != nullptr) {
        context.error(path + ".affine_scale", "expected integer");
    }
    if (const auto value = object->getInteger("affine_offset")) {
        offset = *value;
    } else if (object->get("affine_offset") != nullptr) {
        context.error(path + ".affine_offset", "expected integer");
    }
    if (!kind || !precondition || !enforces || !failure_unknown) {
        return std::nullopt;
    }
    return ModelValueTransferV2{
        *kind, scale, offset, *precondition, *enforces, *failure_unknown};
}

std::optional<ModelEmitV2> parse_emit(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"emit_id", "fact_kind", "source_capture_ref", "target_capture_ref",
         "certainty", "transfer_relation", "external_action",
         "clock_relation", "joint_action_relation", "value_transfer"},
        path, context);
    const auto id = required_string(*object, "emit_id", path, context);
    const auto kind_text = required_string(*object, "fact_kind", path, context);
    const auto source = required_string(
        *object, "source_capture_ref", path, context);
    const auto certainty_text = required_string(
        *object, "certainty", path, context);
    const auto relation = required_string(
        *object, "transfer_relation", path, context);
    static const std::map<std::string, ModelFactKind> kinds{
        {"external_boundary", ModelFactKind::ExternalBoundary},
        {"semantic_transfer", ModelFactKind::SemanticTransfer},
        {"event_link", ModelFactKind::EventLink},
        {"timer_transition", ModelFactKind::TimerTransition},
        {"queue_transition", ModelFactKind::QueueTransition},
        {"lifecycle_transition", ModelFactKind::LifecycleTransition},
        {"scope_key", ModelFactKind::ScopeKey},
        {"clock_relation", ModelFactKind::ClockRelation},
        {"persistence_transition", ModelFactKind::PersistenceTransition},
        {"joint_action_relation", ModelFactKind::JointActionRelation},
    };
    static const std::map<std::string, Certainty> certainties{
        {"modelled", Certainty::Modelled}, {"unknown", Certainty::Unknown}};
    const auto kind = parse_enum(kind_text, kinds, path + ".fact_kind", context);
    const auto certainty = parse_enum(
        certainty_text, certainties, path + ".certainty", context);
    if (!id || !kind || !source || !certainty || !relation) {
        return std::nullopt;
    }
    ModelEmitV2 emit;
    emit.emit_id = *id;
    emit.fact_kind = *kind;
    emit.source_capture_ref = *source;
    emit.certainty = *certainty;
    emit.transfer_relation = *relation;
    if (const auto target = object->getString("target_capture_ref")) {
        if (target->empty()) {
            context.error(path + ".target_capture_ref", "must not be empty");
        } else {
            emit.target_capture_ref = target->str();
        }
    } else if (object->get("target_capture_ref") != nullptr) {
        context.error(path + ".target_capture_ref", "expected string");
    }
    if (object->get("external_action") != nullptr) {
        auto action = parse_action(
            object->getObject("external_action"), path + ".external_action",
            context);
        if (action) {
            emit.external_action = std::move(*action);
        }
    }
    if (object->get("clock_relation") != nullptr) {
        auto relation = parse_clock_relation(
            object->getObject("clock_relation"), path + ".clock_relation",
            context);
        if (relation) {
            emit.clock_relation = std::move(*relation);
        }
    }
    if (object->get("joint_action_relation") != nullptr) {
        auto relation = parse_joint_action_relation(
            object->getObject("joint_action_relation"),
            path + ".joint_action_relation", context);
        if (relation) {
            emit.joint_action_relation = std::move(*relation);
        }
    }
    if (object->get("value_transfer") != nullptr) {
        auto transfer = parse_value_transfer(
            object->getObject("value_transfer"), path + ".value_transfer",
            context);
        if (transfer) emit.value_transfer = std::move(*transfer);
    }
    return emit;
}

std::optional<ModelRuleV2> parse_rule(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"rule_id", "matches", "captures", "joins", "emits",
         "evidence_note"},
        path, context);
    const auto id = required_string(*object, "rule_id", path, context);
    const auto evidence = required_string(*object, "evidence_note", path, context);
    const Array *matches = object->getArray("matches");
    const Array *captures = object->getArray("captures");
    const Array *joins = object->getArray("joins");
    const Array *emits = object->getArray("emits");
    if (matches == nullptr) {
        context.error(path + ".matches", "expected array");
    }
    if (captures == nullptr) {
        context.error(path + ".captures", "expected array");
    }
    if (joins == nullptr) {
        context.error(path + ".joins", "expected array");
    }
    if (emits == nullptr) {
        context.error(path + ".emits", "expected array");
    }
    if (!id || !evidence || matches == nullptr || captures == nullptr ||
        joins == nullptr || emits == nullptr) {
        return std::nullopt;
    }
    ModelRuleV2 rule;
    rule.rule_id = *id;
    rule.evidence_note = *evidence;
    for (std::size_t i = 0; i < matches->size(); ++i) {
        auto parsed = parse_match(
            (*matches)[i].getAsObject(),
            path + ".matches[" + std::to_string(i) + "]", context);
        if (parsed) {
            rule.matches.push_back(std::move(*parsed));
        }
    }
    for (std::size_t i = 0; i < captures->size(); ++i) {
        auto parsed = parse_capture(
            (*captures)[i].getAsObject(),
            path + ".captures[" + std::to_string(i) + "]", context);
        if (parsed) {
            rule.captures.push_back(std::move(*parsed));
        }
    }
    for (std::size_t i = 0; i < joins->size(); ++i) {
        auto parsed = parse_join(
            (*joins)[i].getAsObject(),
            path + ".joins[" + std::to_string(i) + "]", context);
        if (parsed) {
            rule.joins.push_back(std::move(*parsed));
        }
    }
    for (std::size_t i = 0; i < emits->size(); ++i) {
        auto parsed = parse_emit(
            (*emits)[i].getAsObject(),
            path + ".emits[" + std::to_string(i) + "]", context);
        if (parsed) {
            rule.emits.push_back(std::move(*parsed));
        }
    }
    return rule;
}

std::optional<ModelPackV2> parse_pack(
    const Object *object, ParseContext &context) {
    const std::string path = "$";
    if (object == nullptr) {
        context.error(path, "expected root object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"schema_version", "model_pack_id", "model_pack_version", "layer",
         "property_independent", "target", "resource_limits", "selectors",
         "rules"},
        path, context);
    const auto schema = required_string(*object, "schema_version", path, context);
    const auto id = required_string(*object, "model_pack_id", path, context);
    const auto version = required_string(
        *object, "model_pack_version", path, context);
    const auto layer_text = required_string(*object, "layer", path, context);
    const auto independent = required_bool(
        *object, "property_independent", path, context);
    static const std::map<std::string, ModelLayer> layers{
        {"platform", ModelLayer::Platform},
        {"framework", ModelLayer::Framework},
        {"project_adapter", ModelLayer::ProjectAdapter},
    };
    const auto layer = parse_enum(layer_text, layers, "$.layer", context);
    auto target = parse_target(object->getObject("target"), "$.target", context);
    auto limits = parse_limits(
        object->getObject("resource_limits"), "$.resource_limits", context);
    const Array *selectors = object->getArray("selectors");
    const Array *rules = object->getArray("rules");
    if (selectors == nullptr) {
        context.error("$.selectors", "expected array");
    }
    if (rules == nullptr) {
        context.error("$.rules", "expected array");
    }
    if (!schema || !id || !version || !layer || !independent || !target ||
        !limits || selectors == nullptr || rules == nullptr) {
        return std::nullopt;
    }
    ModelPackV2 pack;
    pack.schema_version = *schema;
    pack.model_pack_id = *id;
    pack.model_pack_version = *version;
    pack.layer = *layer;
    pack.property_independent = *independent;
    pack.target = std::move(*target);
    pack.resource_limits = *limits;
    for (std::size_t i = 0; i < selectors->size(); ++i) {
        auto parsed = parse_selector(
            (*selectors)[i].getAsObject(),
            "$.selectors[" + std::to_string(i) + "]", context);
        if (parsed) {
            pack.selectors.push_back(std::move(*parsed));
        }
    }
    for (std::size_t i = 0; i < rules->size(); ++i) {
        auto parsed = parse_rule(
            (*rules)[i].getAsObject(),
            "$.rules[" + std::to_string(i) + "]", context);
        if (parsed) {
            pack.rules.push_back(std::move(*parsed));
        }
    }
    return pack;
}

std::vector<std::string> lexical_tokens(const std::string &value) {
    std::string normalized;
    normalized.reserve(value.size());
    for (const unsigned char c : value) {
        normalized.push_back(
            std::isalnum(c) != 0 ? static_cast<char>(std::tolower(c)) : ' ');
    }
    std::istringstream stream(normalized);
    return {std::istream_iterator<std::string>(stream),
            std::istream_iterator<std::string>()};
}

bool looks_like_physical_or_answer_material(const std::string &value) {
    const std::vector<std::string> tokens = lexical_tokens(value);
    static const std::set<std::string> forbidden_tokens{
        "property", "ap", "oracle", "gold", "replay"};
    if (std::any_of(tokens.begin(), tokens.end(), [](const std::string &token) {
            return forbidden_tokens.contains(token);
        })) {
        return true;
    }
    std::string lower;
    lower.reserve(value.size());
    std::transform(
        value.begin(), value.end(), std::back_inserter(lower),
        [](const unsigned char c) { return static_cast<char>(std::tolower(c)); });
    const auto adjacent_tokens = [&](const std::string &left,
                                     const std::string &right) {
        for (std::size_t i = 1; i < tokens.size(); ++i) {
            if (tokens[i - 1] == left && tokens[i] == right) return true;
        }
        return false;
    };
    if (adjacent_tokens("source", "location") ||
        adjacent_tokens("benchmark", "case") ||
        adjacent_tokens("expected", "answer") ||
        adjacent_tokens("expected", "edge") ||
        adjacent_tokens("expected", "node") ||
        adjacent_tokens("experiment", "result") ||
        adjacent_tokens("case", "id") ||
        adjacent_tokens("file", "path") ||
        adjacent_tokens("line", "number") ||
        adjacent_tokens("column", "number") ||
        adjacent_tokens("node", "id") || adjacent_tokens("edge", "id") ||
        adjacent_tokens("dependency", "path") || lower.starts_with("node:") ||
        lower.starts_with("edge:")) {
        return true;
    }
    const std::size_t slash_count = static_cast<std::size_t>(
        std::count(lower.begin(), lower.end(), '/'));
    const bool only_operator_slash =
        slash_count == 1 && lower.find("operator/") != std::string::npos;
    if ((slash_count != 0 && !only_operator_slash) || lower.starts_with('/') ||
        lower.starts_with("./") ||
        lower.starts_with("../") || lower.find("/../") != std::string::npos ||
        lower.find("\\") != std::string::npos ||
        lower.find("riftpath://") != std::string::npos ||
        (lower.size() >= 3 && std::isalpha(
             static_cast<unsigned char>(lower[0])) != 0 &&
         lower[1] == ':' && (lower[2] == '/' || lower[2] == '\\'))) {
        return true;
    }
    static const std::regex source_suffix(
        ".*\\.(c|cc|cpp|cxx|h|hh|hpp|inc|ll|bc)(:[0-9]+)?$",
        std::regex::icase);
    return std::regex_match(value, source_suffix);
}

void audit_string(
    const std::string &path, const std::string &value,
    std::vector<std::string> &errors) {
    if (value.empty()) {
        errors.push_back(path + ": empty string");
    } else if (looks_like_physical_or_answer_material(value)) {
        errors.push_back(
            path + ": forbidden property/answer/source-location material");
    }
}

template <typename Range, typename Id>
void require_unique_ids(
    const Range &values, Id id, const std::string &path,
    std::vector<std::string> &errors) {
    std::set<std::string> seen;
    for (const auto &value : values) {
        const std::string key = id(value);
        if (!is_stable_id(key)) {
            errors.push_back(path + ": invalid stable ID '" + key + "'");
        }
        if (!seen.insert(key).second) {
            errors.push_back(path + ": duplicate ID '" + key + "'");
        }
    }
}

std::string value_type_material(const ValueType &type) {
    std::ostringstream out;
    out << static_cast<int>(type.kind) << '\0' << type.canonical << '\0';
    if (type.bit_width) {
        out << *type.bit_width;
    }
    out << '\0';
    if (type.is_signed) {
        out << (*type.is_signed ? '1' : '0');
    }
    out << '\0';
    if (type.unit) {
        out << *type.unit;
    }
    return out.str();
}

std::string clock_relation_material(const ModelClockRelationV2 &clock) {
    std::ostringstream out;
    if (clock.clock_source) out << *clock.clock_source;
    out << '\0';
    if (clock.unit) out << static_cast<int>(*clock.unit);
    out << '\0';
    if (clock.epoch) out << *clock.epoch;
    out << '\0';
    if (clock.quantum) out << llvm::formatv("{0}", *clock.quantum).str();
    out << '\0';
    if (clock.jitter) out << llvm::formatv("{0}", *clock.jitter).str();
    out << '\0';
    if (clock.wrap) out << static_cast<int>(*clock.wrap);
    out << '\0';
    if (clock.wrap_value) out << *clock.wrap_value;
    out << '\0';
    if (clock.start_event) out << *clock.start_event;
    out << '\0';
    if (clock.end_event) out << *clock.end_event;
    out << '\0';
    if (clock.endpoint) out << static_cast<int>(*clock.endpoint);
    out << '\0';
    if (clock.scope_schema) out << *clock.scope_schema;
    out << '\0';
    if (clock.generation_schema) out << *clock.generation_schema;
    return out.str();
}

std::string joint_relation_material(
    const ModelJointActionRelationV2 &joint) {
    std::ostringstream out;
    out << joint.group_schema_id << '\0'
        << static_cast<int>(joint.combination) << '\0'
        << (joint.participant_set_complete ? '1' : '0') << '\0'
        << joint.scope_schema << '\0' << joint.generation_schema;
    std::vector<std::string> participants =
        joint.participant_capture_refs;
    std::sort(participants.begin(), participants.end());
    for (const std::string &participant : participants) {
        out << '\0' << participant;
    }
    return out.str();
}

std::string value_transfer_material(
    const ModelValueTransferV2 &transfer) {
    std::ostringstream out;
    out << static_cast<int>(transfer.kind) << '\0';
    if (transfer.affine_scale) out << *transfer.affine_scale;
    out << '\0';
    if (transfer.affine_offset) out << *transfer.affine_offset;
    out << '\0' << static_cast<int>(transfer.precondition) << '\0'
        << (transfer.executor_enforces_precondition ? '1' : '0') << '\0'
        << (transfer.failure_branch_unknown ? '1' : '0');
    return out.str();
}

bool valid_value_transfer_contract(
    const ModelValueTransferV2 &transfer) {
    switch (transfer.kind) {
    case ModelValueTransferKind::Identity:
        return !transfer.affine_scale && !transfer.affine_offset &&
               transfer.precondition == ModelValuePrecondition::None &&
               !transfer.executor_enforces_precondition &&
               !transfer.failure_branch_unknown;
    case ModelValueTransferKind::Affine:
        return transfer.affine_scale && transfer.affine_offset &&
               transfer.precondition == ModelValuePrecondition::None &&
               !transfer.executor_enforces_precondition &&
               !transfer.failure_branch_unknown;
    case ModelValueTransferKind::ParseIdentityWithPrecondition:
        return !transfer.affine_scale && !transfer.affine_offset &&
               transfer.precondition ==
                   ModelValuePrecondition::CanonicalDecimalIntegerInRange &&
               transfer.executor_enforces_precondition &&
               transfer.failure_branch_unknown;
    case ModelValueTransferKind::Unknown:
        return !transfer.affine_scale && !transfer.affine_offset &&
               transfer.precondition == ModelValuePrecondition::Unknown &&
               !transfer.executor_enforces_precondition &&
               transfer.failure_branch_unknown;
    }
    return false;
}

std::string model_fact_identity_material(
    ModelFactKind kind, const std::string &source,
    const std::string &target, const std::string &transfer_relation,
    const std::optional<ModelClockRelationV2> &clock_relation,
    const std::optional<ModelValueTransferV2> &value_transfer) {
    return std::string(to_string(kind)) + '\0' + source + '\0' + target +
        '\0' + transfer_relation + '\0' +
        (clock_relation ? clock_relation_material(*clock_relation)
                        : std::string{}) + '\0' +
        (value_transfer ? value_transfer_material(*value_transfer)
                        : std::string{});
}

std::string model_pack_semantic_sha256(const ModelPackV2 &pack) {
    std::ostringstream out;
    out << "model-pack-semantic/2.0.0\0" << pack.schema_version << '\0'
        << pack.model_pack_id << '\0' << pack.model_pack_version << '\0'
        << static_cast<int>(pack.layer) << '\0'
        << (pack.property_independent ? '1' : '0') << '\0'
        << pack.target.target_version << '\0' << pack.target.target_abi << '\0'
        << pack.target.evidence_id << '\0' << pack.target.digest_policy << '\0'
        << pack.resource_limits.max_selector_matches << '\0'
        << pack.resource_limits.max_capture_values << '\0'
        << pack.resource_limits.max_join_assignments << '\0'
        << pack.resource_limits.max_emitted_facts;
    std::vector<const ModelSelectorV2 *> selectors;
    for (const ModelSelectorV2 &selector : pack.selectors) {
        selectors.push_back(&selector);
    }
    std::sort(
        selectors.begin(), selectors.end(),
        [](const ModelSelectorV2 *left, const ModelSelectorV2 *right) {
            return left->selector_id < right->selector_id;
        });
    for (const ModelSelectorV2 *selector : selectors) {
        out << "\0selector\0" << selector->selector_id << '\0'
            << static_cast<int>(selector->kind) << '\0';
        if (selector->exact_value) out << *selector->exact_value;
        out << '\0';
        if (selector->owner_selector_ref) out << *selector->owner_selector_ref;
        for (const std::string &field : selector->field_path) {
            out << '\0' << field;
        }
        out << "\0type\0";
        if (selector->canonical_type) out << *selector->canonical_type;
        out << '\0' << (selector->application_private ? '1' : '0');
    }
    std::vector<const ModelRuleV2 *> rules;
    for (const ModelRuleV2 &rule : pack.rules) rules.push_back(&rule);
    std::sort(
        rules.begin(), rules.end(),
        [](const ModelRuleV2 *left, const ModelRuleV2 *right) {
            return left->rule_id < right->rule_id;
        });
    for (const ModelRuleV2 *rule : rules) {
        out << "\0rule\0" << rule->rule_id << '\0' << rule->evidence_note;
        std::vector<ModelMatchV2> matches = rule->matches;
        std::sort(
            matches.begin(), matches.end(),
            [](const ModelMatchV2 &left, const ModelMatchV2 &right) {
                return left.match_id < right.match_id;
            });
        for (const ModelMatchV2 &match : matches) {
            out << "\0match\0" << match.match_id << '\0' << match.selector_ref;
        }
        std::vector<ModelCaptureV2> captures = rule->captures;
        std::sort(
            captures.begin(), captures.end(),
            [](const ModelCaptureV2 &left, const ModelCaptureV2 &right) {
                return left.capture_id < right.capture_id;
            });
        for (const ModelCaptureV2 &capture : captures) {
            out << "\0capture\0" << capture.capture_id << '\0'
                << capture.match_ref << '\0'
                << static_cast<int>(capture.projection) << '\0';
            if (capture.index) out << *capture.index;
        }
        std::vector<ModelJoinV2> joins = rule->joins;
        std::sort(
            joins.begin(), joins.end(),
            [](const ModelJoinV2 &left, const ModelJoinV2 &right) {
                return left.join_id < right.join_id;
            });
        for (const ModelJoinV2 &join : joins) {
            out << "\0join\0" << join.join_id << '\0'
                << static_cast<int>(join.kind) << '\0'
                << join.left_capture_ref << '\0' << join.right_capture_ref;
        }
        std::vector<ModelEmitV2> emits = rule->emits;
        std::sort(
            emits.begin(), emits.end(),
            [](const ModelEmitV2 &left, const ModelEmitV2 &right) {
                return left.emit_id < right.emit_id;
            });
        for (const ModelEmitV2 &emit : emits) {
            out << "\0emit\0" << emit.emit_id << '\0'
                << static_cast<int>(emit.fact_kind) << '\0'
                << emit.source_capture_ref << '\0';
            if (emit.target_capture_ref) out << *emit.target_capture_ref;
            out << '\0' << static_cast<int>(emit.certainty) << '\0'
                << emit.transfer_relation;
            if (emit.external_action) {
                const ExternalActionTemplateV2 &action = *emit.external_action;
                out << "\0action\0" << action.action_schema_id << '\0'
                    << action.action_class << '\0' << action.channel << '\0'
                    << action.operation << '\0'
                    << value_type_material(action.payload_type) << '\0'
                    << action.payload_slot << '\0' << action.scope_schema << '\0'
                    << action.generation_schema << '\0'
                    << action.timing_capability << '\0'
                    << action.required_capability;
            }
            if (emit.clock_relation) {
                out << "\0clock\0"
                    << clock_relation_material(*emit.clock_relation);
            }
            if (emit.joint_action_relation) {
                out << "\0joint\0"
                    << joint_relation_material(*emit.joint_action_relation);
            }
            if (emit.value_transfer) {
                out << "\0value-transfer\0"
                    << value_transfer_material(*emit.value_transfer);
            }
        }
    }
    return sha256_hex(out.str());
}

}  // namespace

const char *to_string(ModelLayer value) {
    switch (value) {
    case ModelLayer::Platform: return "platform";
    case ModelLayer::Framework: return "framework";
    case ModelLayer::ProjectAdapter: return "project_adapter";
    }
    return "framework";
}

const char *to_string(ModelFactKind value) {
    switch (value) {
    case ModelFactKind::ExternalBoundary: return "external_boundary";
    case ModelFactKind::SemanticTransfer: return "semantic_transfer";
    case ModelFactKind::EventLink: return "event_link";
    case ModelFactKind::TimerTransition: return "timer_transition";
    case ModelFactKind::QueueTransition: return "queue_transition";
    case ModelFactKind::LifecycleTransition: return "lifecycle_transition";
    case ModelFactKind::ScopeKey: return "scope_key";
    case ModelFactKind::ClockRelation: return "clock_relation";
    case ModelFactKind::PersistenceTransition: return "persistence_transition";
    case ModelFactKind::JointActionRelation: return "joint_action_relation";
    }
    return "semantic_transfer";
}

const char *to_string(ModelClockUnit value) {
    switch (value) {
    case ModelClockUnit::Nanoseconds: return "ns";
    case ModelClockUnit::Microseconds: return "us";
    case ModelClockUnit::Milliseconds: return "ms";
    case ModelClockUnit::Seconds: return "s";
    case ModelClockUnit::Ticks: return "ticks";
    }
    return "ticks";
}

const char *to_string(ModelClockWrap value) {
    switch (value) {
    case ModelClockWrap::None: return "none";
    case ModelClockWrap::Modulo: return "modulo";
    case ModelClockWrap::Saturating: return "saturating";
    case ModelClockWrap::Unknown: return "unknown";
    }
    return "unknown";
}

const char *to_string(ModelClockEndpoint value) {
    switch (value) {
    case ModelClockEndpoint::Open: return "open";
    case ModelClockEndpoint::Closed: return "closed";
    case ModelClockEndpoint::Mixed: return "mixed";
    case ModelClockEndpoint::Unknown: return "unknown";
    }
    return "unknown";
}

const char *to_string(ModelJointActionOperator value) {
    switch (value) {
    case ModelJointActionOperator::AllRequired: return "all_required";
    case ModelJointActionOperator::AnySufficient: return "any_sufficient";
    case ModelJointActionOperator::Unknown: return "unknown";
    }
    return "unknown";
}

const char *to_string(ModelValueTransferKind value) {
    switch (value) {
    case ModelValueTransferKind::Identity: return "identity";
    case ModelValueTransferKind::Affine: return "affine";
    case ModelValueTransferKind::ParseIdentityWithPrecondition:
        return "parse_identity_with_precondition";
    case ModelValueTransferKind::Unknown: return "unknown";
    }
    return "unknown";
}

const char *to_string(ModelValuePrecondition value) {
    switch (value) {
    case ModelValuePrecondition::None: return "none";
    case ModelValuePrecondition::CanonicalDecimalIntegerInRange:
        return "canonical_decimal_integer_in_range";
    case ModelValuePrecondition::Unknown: return "unknown";
    }
    return "unknown";
}

std::string canonical_model_pack_semantic_sha256(const ModelPackV2 &pack) {
    return model_pack_semantic_sha256(pack);
}

std::vector<std::string> validate_model_pack_v2(const ModelPackV2 &pack) {
    std::vector<std::string> errors;
    if (pack.schema_version != "2.0.0") {
        errors.push_back(
            "$.schema_version: only executable model-pack/2.0.0 is accepted; "
            "version 1 is intentionally non-executable");
    }
    if (!is_stable_id(pack.model_pack_id)) {
        errors.push_back("$.model_pack_id: invalid stable ID");
    }
    if (!is_semver(pack.model_pack_version)) {
        errors.push_back("$.model_pack_version: invalid semantic version");
    }
    if (!pack.property_independent) {
        errors.push_back("$.property_independent: must be true");
    }
    if (!is_sha256(pack.observed_sha256)) {
        errors.push_back("$.observed_sha256: exact loaded-byte SHA-256 required");
    }
    if (pack.target.digest_policy != "freeze_before_property") {
        errors.push_back("$.target.digest_policy: must be freeze_before_property");
    }
    if (!is_stable_id(pack.target.evidence_id)) {
        errors.push_back("$.target.evidence_id: invalid stable ID");
    }
    if (pack.resource_limits.max_selector_matches == 0 ||
        pack.resource_limits.max_capture_values == 0 ||
        pack.resource_limits.max_join_assignments == 0 ||
        pack.resource_limits.max_emitted_facts == 0) {
        errors.push_back("$.resource_limits: every limit must be positive");
    }
    if (pack.selectors.empty()) {
        errors.push_back("$.selectors: must not be empty");
    }
    if (pack.rules.empty()) {
        errors.push_back("$.rules: must not be empty");
    }

    audit_string("$.model_pack_id", pack.model_pack_id, errors);
    audit_string("$.model_pack_version", pack.model_pack_version, errors);
    audit_string("$.target.target_version", pack.target.target_version, errors);
    audit_string("$.target.target_abi", pack.target.target_abi, errors);
    audit_string("$.target.evidence_id", pack.target.evidence_id, errors);

    require_unique_ids(
        pack.selectors, [](const ModelSelectorV2 &value) {
            return value.selector_id;
        }, "$.selectors", errors);
    require_unique_ids(
        pack.rules, [](const ModelRuleV2 &value) { return value.rule_id; },
        "$.rules", errors);
    std::set<std::string> executable_ids;
    const auto register_global_id = [&](const std::string &id,
                                        const std::string &path) {
        if (!executable_ids.insert(id).second) {
            errors.push_back(path + ": duplicate executable ID '" + id + "'");
        }
    };
    std::map<std::string, const ModelSelectorV2 *> selectors;
    for (const ModelSelectorV2 &selector : pack.selectors) {
        register_global_id(selector.selector_id, "$.selectors");
        selectors.emplace(selector.selector_id, &selector);
        audit_string(
            "$.selectors[" + selector.selector_id + "].selector_id",
            selector.selector_id, errors);
        if (selector.application_private &&
            pack.layer != ModelLayer::ProjectAdapter) {
            errors.push_back(
                "$.selectors[" + selector.selector_id +
                "]: platform/framework packs cannot declare application-private APIs");
        }
        if (selector.kind == ModelSelectorKind::TypedField) {
            if (selector.exact_value) {
                errors.push_back(
                    "$.selectors[" + selector.selector_id +
                    "]: typed_field cannot have exact_value");
            }
            if (!selector.owner_selector_ref || selector.field_path.empty()) {
                errors.push_back(
                    "$.selectors[" + selector.selector_id +
                    "]: typed_field requires owner_selector_ref and field_path");
            }
        } else {
            if (!selector.exact_value || selector.owner_selector_ref ||
                !selector.field_path.empty() || selector.canonical_type) {
                errors.push_back(
                    "$.selectors[" + selector.selector_id +
                    "]: exact selector requires only exact_value");
            }
        }
        if (selector.exact_value) {
            audit_string(
                "$.selectors[" + selector.selector_id + "].exact_value",
                *selector.exact_value, errors);
        }
        for (const std::string &field : selector.field_path) {
            audit_string(
                "$.selectors[" + selector.selector_id + "].field_path", field,
                errors);
        }
        if (selector.canonical_type) {
            audit_string(
                "$.selectors[" + selector.selector_id + "].canonical_type",
                *selector.canonical_type, errors);
        }
    }
    for (const ModelSelectorV2 &selector : pack.selectors) {
        if (!selector.owner_selector_ref) continue;
        const auto owner = selectors.find(*selector.owner_selector_ref);
        if (owner == selectors.end()) {
            errors.push_back(
                "$.selectors[" + selector.selector_id +
                "].owner_selector_ref: dangling selector");
        } else if (owner->second->kind == ModelSelectorKind::TypedField) {
            errors.push_back(
                "$.selectors[" + selector.selector_id +
                "].owner_selector_ref: typed-field recursion is forbidden");
        }
    }

    for (const ModelRuleV2 &rule : pack.rules) {
        const std::string base = "$.rules[" + rule.rule_id + "]";
        register_global_id(rule.rule_id, "$.rules");
        audit_string(base + ".rule_id", rule.rule_id, errors);
        audit_string(base + ".evidence_note", rule.evidence_note, errors);
        if (rule.matches.empty() || rule.captures.empty() || rule.emits.empty()) {
            errors.push_back(
                base + ": matches, captures, and emits must all be non-empty");
        }
        require_unique_ids(
            rule.matches, [](const ModelMatchV2 &value) { return value.match_id; },
            base + ".matches", errors);
        require_unique_ids(
            rule.captures,
            [](const ModelCaptureV2 &value) { return value.capture_id; },
            base + ".captures", errors);
        require_unique_ids(
            rule.joins, [](const ModelJoinV2 &value) { return value.join_id; },
            base + ".joins", errors);
        require_unique_ids(
            rule.emits, [](const ModelEmitV2 &value) { return value.emit_id; },
            base + ".emits", errors);

        std::set<std::string> matches;
        for (const ModelMatchV2 &match : rule.matches) {
            register_global_id(match.match_id, base + ".matches");
            matches.insert(match.match_id);
            audit_string(
                base + ".matches[" + match.match_id + "].match_id",
                match.match_id, errors);
            if (!selectors.contains(match.selector_ref)) {
                errors.push_back(
                    base + ".matches[" + match.match_id +
                    "].selector_ref: dangling selector");
            }
        }
        std::set<std::string> captures;
        for (const ModelCaptureV2 &capture : rule.captures) {
            register_global_id(capture.capture_id, base + ".captures");
            captures.insert(capture.capture_id);
            audit_string(
                base + ".captures[" + capture.capture_id + "].capture_id",
                capture.capture_id, errors);
            if (!matches.contains(capture.match_ref)) {
                errors.push_back(
                    base + ".captures[" + capture.capture_id +
                    "].match_ref: dangling match");
            }
            const bool indexed =
                capture.projection == ModelProjectionKind::FormalParameter ||
                capture.projection == ModelProjectionKind::CallArgument;
            if (indexed != capture.index.has_value()) {
                errors.push_back(
                    base + ".captures[" + capture.capture_id +
                    "]: projection/index mismatch");
            }
        }
        for (const ModelJoinV2 &join : rule.joins) {
            register_global_id(join.join_id, base + ".joins");
            audit_string(
                base + ".joins[" + join.join_id + "].join_id", join.join_id,
                errors);
            if (!captures.contains(join.left_capture_ref) ||
                !captures.contains(join.right_capture_ref)) {
                errors.push_back(
                    base + ".joins[" + join.join_id +
                    "]: dangling capture reference");
            }
            if (join.left_capture_ref == join.right_capture_ref) {
                errors.push_back(
                    base + ".joins[" + join.join_id +
                    "]: self-join is not a semantic constraint");
            }
        }
        for (const ModelEmitV2 &emit : rule.emits) {
            register_global_id(emit.emit_id, base + ".emits");
            audit_string(
                base + ".emits[" + emit.emit_id + "].emit_id", emit.emit_id,
                errors);
            if (!captures.contains(emit.source_capture_ref) ||
                (emit.target_capture_ref &&
                 !captures.contains(*emit.target_capture_ref))) {
                errors.push_back(
                    base + ".emits[" + emit.emit_id +
                    "]: dangling capture reference");
            }
            if (emit.certainty != Certainty::Modelled &&
                emit.certainty != Certainty::Unknown) {
                errors.push_back(
                    base + ".emits[" + emit.emit_id +
                    "]: pack facts may only be MODELLED or UNKNOWN");
            }
            const bool boundary =
                emit.fact_kind == ModelFactKind::ExternalBoundary;
            const bool joint =
                emit.fact_kind == ModelFactKind::JointActionRelation;
            if ((boundary &&
                 (!emit.external_action || emit.target_capture_ref ||
                  emit.clock_relation || emit.joint_action_relation)) ||
                (joint &&
                 (emit.external_action || emit.target_capture_ref ||
                  emit.clock_relation || !emit.joint_action_relation)) ||
                (!boundary && !joint &&
                 (emit.external_action || !emit.target_capture_ref ||
                  emit.joint_action_relation))) {
                errors.push_back(
                    base + ".emits[" + emit.emit_id +
                    "]: fact-kind payload/target contract is not closed");
            }
            const bool clock =
                emit.fact_kind == ModelFactKind::ClockRelation;
            if (clock != emit.clock_relation.has_value()) {
                errors.push_back(
                    base + ".emits[" + emit.emit_id +
                    "]: clock_relation kind requires exactly one typed clock payload");
            }
            audit_string(
                base + ".emits[" + emit.emit_id + "].transfer_relation",
                emit.transfer_relation, errors);
            if (emit.external_action) {
                const ExternalActionTemplateV2 &action = *emit.external_action;
                if (!is_stable_id(action.action_schema_id)) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].external_action.action_schema_id: invalid stable ID");
                }
                audit_string(base + ".action_schema_id", action.action_schema_id, errors);
                audit_string(base + ".action_class", action.action_class, errors);
                audit_string(base + ".channel", action.channel, errors);
                audit_string(base + ".operation", action.operation, errors);
                audit_string(base + ".payload_slot", action.payload_slot, errors);
                audit_string(base + ".scope_schema", action.scope_schema, errors);
                audit_string(base + ".generation_schema", action.generation_schema, errors);
                audit_string(base + ".timing_capability", action.timing_capability, errors);
                audit_string(base + ".required_capability", action.required_capability, errors);
                audit_string(base + ".payload_type.canonical", action.payload_type.canonical, errors);
                if (action.payload_type.unit) {
                    audit_string(
                        base + ".payload_type.unit", *action.payload_type.unit,
                        errors);
                }
            }
            if (emit.clock_relation) {
                const ModelClockRelationV2 &relation =
                    *emit.clock_relation;
                const bool complete = relation.clock_source && relation.unit &&
                    relation.epoch && relation.quantum && relation.jitter &&
                    relation.wrap && relation.start_event &&
                    relation.end_event && relation.endpoint &&
                    relation.scope_schema && relation.generation_schema;
                if (!complete) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].clock_relation: fixed field set is incomplete");
                } else {
                    for (const auto &[field, value] :
                         std::vector<std::pair<std::string, std::string>>{
                             {"clock_source", *relation.clock_source},
                             {"epoch", *relation.epoch},
                             {"start_event", *relation.start_event},
                             {"end_event", *relation.end_event},
                             {"scope_schema", *relation.scope_schema},
                             {"generation_schema",
                              *relation.generation_schema}}) {
                        if (!is_stable_id(value)) {
                            errors.push_back(
                                base + ".emits[" + emit.emit_id +
                                "].clock_relation." + field +
                                ": invalid stable ID");
                        }
                    }
                    if (!std::isfinite(*relation.quantum) ||
                        *relation.quantum <= 0.0 ||
                        !std::isfinite(*relation.jitter) ||
                        *relation.jitter < 0.0) {
                        errors.push_back(
                            base + ".emits[" + emit.emit_id +
                            "].clock_relation: invalid quantum/jitter");
                    }
                    const bool bounded_wrap =
                        *relation.wrap == ModelClockWrap::Modulo ||
                        *relation.wrap == ModelClockWrap::Saturating;
                    if (bounded_wrap != relation.wrap_value.has_value() ||
                        (relation.wrap_value && *relation.wrap_value == 0)) {
                        errors.push_back(
                            base + ".emits[" + emit.emit_id +
                            "].clock_relation: wrap/bound contract mismatch");
                    }
                }
            }
            if (emit.joint_action_relation) {
                const ModelJointActionRelationV2 &relation =
                    *emit.joint_action_relation;
                if (!is_stable_id(relation.group_schema_id) ||
                    !is_stable_id(relation.scope_schema) ||
                    !is_stable_id(relation.generation_schema)) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].joint_action_relation: invalid typed identity");
                }
                const std::set<std::string> participants(
                    relation.participant_capture_refs.begin(),
                    relation.participant_capture_refs.end());
                if (participants.size() < 2 ||
                    participants.size() !=
                        relation.participant_capture_refs.size()) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].joint_action_relation: participants must be unique and n-ary");
                }
                if (!participants.contains(emit.source_capture_ref)) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].joint_action_relation: source capture is not a participant");
                }
                for (const std::string &participant : participants) {
                    if (!captures.contains(participant)) {
                        errors.push_back(
                            base + ".emits[" + emit.emit_id +
                            "].joint_action_relation: dangling participant capture");
                    }
                }
            }
            if (emit.value_transfer) {
                const ModelValueTransferV2 &transfer =
                    *emit.value_transfer;
                const bool value_fact =
                    emit.fact_kind == ModelFactKind::ExternalBoundary ||
                    emit.fact_kind == ModelFactKind::SemanticTransfer ||
                    emit.fact_kind == ModelFactKind::PersistenceTransition;
                if (!value_fact) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].value_transfer: not valid for this fact kind");
                }
                const bool affine_complete =
                    transfer.affine_scale && transfer.affine_offset;
                bool contract_valid = false;
                switch (transfer.kind) {
                case ModelValueTransferKind::Identity:
                    contract_valid = !transfer.affine_scale &&
                        !transfer.affine_offset &&
                        transfer.precondition ==
                            ModelValuePrecondition::None &&
                        !transfer.executor_enforces_precondition &&
                        !transfer.failure_branch_unknown;
                    break;
                case ModelValueTransferKind::Affine:
                    contract_valid = affine_complete &&
                        transfer.precondition ==
                            ModelValuePrecondition::None &&
                        !transfer.executor_enforces_precondition &&
                        !transfer.failure_branch_unknown;
                    break;
                case ModelValueTransferKind::ParseIdentityWithPrecondition:
                    contract_valid = !transfer.affine_scale &&
                        !transfer.affine_offset &&
                        transfer.precondition ==
                            ModelValuePrecondition::CanonicalDecimalIntegerInRange &&
                        transfer.executor_enforces_precondition &&
                        transfer.failure_branch_unknown;
                    break;
                case ModelValueTransferKind::Unknown:
                    contract_valid = !transfer.affine_scale &&
                        !transfer.affine_offset &&
                        transfer.precondition ==
                            ModelValuePrecondition::Unknown &&
                        !transfer.executor_enforces_precondition &&
                        transfer.failure_branch_unknown;
                    break;
                }
                if (!contract_valid) {
                    errors.push_back(
                        base + ".emits[" + emit.emit_id +
                        "].value_transfer: typed transfer contract is inconsistent");
                }
            }
        }
    }
    std::sort(errors.begin(), errors.end());
    errors.erase(std::unique(errors.begin(), errors.end()), errors.end());
    return errors;
}

LoadResult<ModelPackV2> load_model_pack_v2(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256) {
    LoadResult<ModelPackV2> result;
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        result.diagnostics.push_back("cannot open model pack: " + path.string());
        return result;
    }
    const std::string bytes{
        std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    result.observed_sha256 = sha256_hex(bytes);
    if (expected_sha256 && *expected_sha256 != result.observed_sha256) {
        result.diagnostics.push_back(
            "model pack SHA-256 mismatch: expected " + *expected_sha256 +
            ", observed " + result.observed_sha256);
        return result;
    }
    llvm::Expected<Value> parsed = llvm::json::parse(bytes);
    if (!parsed) {
        result.diagnostics.push_back(
            "invalid model pack JSON: " + llvm::toString(parsed.takeError()));
        return result;
    }
    ParseContext context;
    auto pack = parse_pack(parsed->getAsObject(), context);
    if (pack) {
        pack->observed_sha256 = result.observed_sha256;
        std::vector<std::string> semantic_errors = validate_model_pack_v2(*pack);
        context.errors.insert(
            context.errors.end(), semantic_errors.begin(), semantic_errors.end());
    }
    std::sort(context.errors.begin(), context.errors.end());
    context.errors.erase(
        std::unique(context.errors.begin(), context.errors.end()),
        context.errors.end());
    if (!pack || !context.errors.empty()) {
        result.diagnostics = std::move(context.errors);
        return result;
    }
    result.status = StageStatus::Complete;
    result.value = std::move(*pack);
    return result;
}

namespace {

struct SelectorMatch {
    std::string entity_id;
    std::optional<std::string> semantic_node_id;

    friend bool operator<(const SelectorMatch &left, const SelectorMatch &right) {
        return std::tie(left.entity_id, left.semantic_node_id) <
               std::tie(right.entity_id, right.semantic_node_id);
    }
    friend bool operator==(const SelectorMatch &, const SelectorMatch &) = default;
};

struct CaptureValue {
    std::string semantic_node_id;
    std::string entity_id;
    std::optional<std::string> callsite_id;
    std::optional<std::string> object_key;
    bool object_exact = false;

    friend bool operator<(const CaptureValue &left, const CaptureValue &right) {
        return std::tie(
                   left.semantic_node_id, left.entity_id, left.callsite_id,
                   left.object_key, left.object_exact) <
               std::tie(
                   right.semantic_node_id, right.entity_id, right.callsite_id,
                   right.object_key, right.object_exact);
    }
    friend bool operator==(const CaptureValue &, const CaptureValue &) = default;
};

using Assignment = std::map<std::string, CaptureValue>;

enum class JoinResult { Pass, Fail, Unknown };

std::string object_key_for(const SemanticNode &node) {
    if (node.abstract_object_id) {
        return "object:" + *node.abstract_object_id;
    }
    if (node.access_path) {
        std::ostringstream material;
        material << "access:" << node.access_path->root_entity_id << ':'
                 << node.access_path->dereference_depth;
        for (const std::string &field : node.access_path->fields) {
            material << ':' << field;
        }
        if (node.access_path->unknown_suffix) {
            material << ":?";
        }
        return material.str();
    }
    return {};
}

std::string external_action_instance_material(const CaptureValue &capture) {
    // A callsite is the external operation instance. Omitting the projected
    // boundary node in that case permits one action to attach to several
    // semantic nodes while still distinguishing different calls.
    if (capture.callsite_id) {
        return "callsite\0" + *capture.callsite_id;
    }
    return "node\0" + capture.semantic_node_id;
}

std::string provenance_material(const ModelProvenance &provenance) {
    std::ostringstream out;
    out << provenance.model_pack_id << '\0' << provenance.model_pack_version
        << '\0' << provenance.model_pack_sha256 << '\0'
        << static_cast<int>(provenance.layer) << '\0' << provenance.rule_id
        << '\0' << provenance.emit_id;
    for (const std::string &id : provenance.selector_ids) out << '\0' << id;
    out << "\0captures";
    for (const std::string &id : provenance.capture_ids) out << '\0' << id;
    out << "\0nodes";
    for (const std::string &id : provenance.matched_semantic_node_ids) {
        out << '\0' << id;
    }
    return out.str();
}

void canonicalize_provenance(std::vector<ModelProvenance> &provenance) {
    for (ModelProvenance &item : provenance) {
        std::sort(item.selector_ids.begin(), item.selector_ids.end());
        item.selector_ids.erase(
            std::unique(item.selector_ids.begin(), item.selector_ids.end()),
            item.selector_ids.end());
        std::sort(item.capture_ids.begin(), item.capture_ids.end());
        item.capture_ids.erase(
            std::unique(item.capture_ids.begin(), item.capture_ids.end()),
            item.capture_ids.end());
        std::sort(
            item.matched_semantic_node_ids.begin(),
            item.matched_semantic_node_ids.end());
        item.matched_semantic_node_ids.erase(
            std::unique(
                item.matched_semantic_node_ids.begin(),
                item.matched_semantic_node_ids.end()),
            item.matched_semantic_node_ids.end());
    }
    std::sort(
        provenance.begin(), provenance.end(),
        [](const ModelProvenance &left, const ModelProvenance &right) {
            return provenance_material(left) < provenance_material(right);
        });
    provenance.erase(
        std::unique(
            provenance.begin(), provenance.end(),
            [](const ModelProvenance &left, const ModelProvenance &right) {
                return provenance_material(left) == provenance_material(right);
            }),
        provenance.end());
}

Certainty merge_certainty(Certainty left, Certainty right) {
    if ((left != Certainty::Modelled && left != Certainty::Unknown) ||
        (right != Certainty::Modelled && right != Certainty::Unknown)) {
        return Certainty::Unknown;
    }
    return left == right ? left : Certainty::Unknown;
}

class VmExecutor {
public:
    VmExecutor(
        const SemanticIndex &semantic_index, ModelFactOverlay &overlay,
        std::map<std::string, ExternalAction> &actions,
        std::map<std::string, BoundaryAttachment> &attachments,
        std::map<std::string, ModelFact> &facts,
        std::map<std::string, ModelJointActionConstraint> &joint_constraints)
        : index_(semantic_index), overlay_(overlay), actions_(actions),
          attachments_(attachments), facts_(facts),
          joint_constraints_(joint_constraints) {
        for (const EntityRef &entity : index_.entities) {
            entities_.emplace(entity.entity_id, &entity);
        }
        for (const SemanticNode &node : index_.nodes) {
            nodes_.emplace(node.node_id, &node);
            nodes_by_entity_[node.entity_id].push_back(&node);
        }
        for (const AbstractObject &object : index_.abstract_objects) {
            objects_.emplace(object.object_id, &object);
        }
        for (auto &[unused, values] : nodes_by_entity_) {
            (void)unused;
            std::sort(
                values.begin(), values.end(),
                [](const SemanticNode *left, const SemanticNode *right) {
                    return left->node_id < right->node_id;
                });
        }
        for (const FunctionSummary &summary : index_.function_summaries) {
            functions_.emplace(summary.function_entity_id, &summary);
        }
        for (const CallSiteSummary &callsite : index_.callsites) {
            callsites_.push_back(&callsite);
        }
        std::sort(
            callsites_.begin(), callsites_.end(),
            [](const CallSiteSummary *left, const CallSiteSummary *right) {
                return left->callsite_id < right->callsite_id;
            });
    }

    void execute(const ModelPackV2 &pack) {
        pack_ = &pack;
        pack_semantic_sha256_ = model_pack_semantic_sha256(pack);
        emitted_count_ = 0;
        exhausted_emits_ = false;
        selector_cache_.clear();

        std::vector<const ModelSelectorV2 *> selectors;
        selectors.reserve(pack.selectors.size());
        for (const ModelSelectorV2 &selector : pack.selectors) {
            selectors.push_back(&selector);
        }
        std::sort(
            selectors.begin(), selectors.end(),
            [](const ModelSelectorV2 *left, const ModelSelectorV2 *right) {
                const bool left_typed = left->kind == ModelSelectorKind::TypedField;
                const bool right_typed = right->kind == ModelSelectorKind::TypedField;
                return std::tie(left_typed, left->selector_id) <
                       std::tie(right_typed, right->selector_id);
            });
        for (const ModelSelectorV2 *selector : selectors) {
            execute_selector(*selector);
        }

        std::vector<const ModelRuleV2 *> rules;
        rules.reserve(pack.rules.size());
        for (const ModelRuleV2 &rule : pack.rules) rules.push_back(&rule);
        std::sort(
            rules.begin(), rules.end(),
            [](const ModelRuleV2 *left, const ModelRuleV2 *right) {
                return left->rule_id < right->rule_id;
            });
        for (const ModelRuleV2 *rule : rules) {
            execute_rule(*rule);
        }
        add_ledger(
            std::nullopt, "EMIT", pack.resource_limits.max_emitted_facts,
            emitted_count_ + (exhausted_emits_ ? 1U : 0U), !exhausted_emits_);
        if (exhausted_emits_) {
            add_unknown(
                std::nullopt, "EMIT", "max_emitted_facts_exhausted", {});
        }
        pack_ = nullptr;
    }

private:
    void add_ledger(
        const std::optional<std::string> &rule_id, const std::string &operation,
        std::uint64_t limit, std::uint64_t observed, bool complete) {
        std::ostringstream material;
        material << pack_semantic_sha256_ << '\0';
        if (rule_id) material << *rule_id;
        material << '\0' << operation;
        overlay_.resource_ledger.push_back(ModelResourceLedgerEntry{
            make_id("model-ledger", material.str()), pack_->model_pack_id,
            rule_id, operation, limit, observed, complete, Certainty::Unknown});
        if (!complete) {
            overlay_.status = StageStatus::ConservativeIncomplete;
            CoverageGap gap;
            gap.gap_id = make_id("model-gap", material.str());
            gap.kind = "model_vm_resource_exhausted";
            gap.effect = GapEffect::SoundnessRisk;
            gap.detail = operation + " exceeded declared finite VM resource limit";
            if (rule_id) gap.affected_ids.push_back(*rule_id);
            overlay_.coverage_gaps.push_back(std::move(gap));
        }
    }

    void add_unknown(
        const std::optional<std::string> &rule_id, const std::string &operation,
        const std::string &reason, std::vector<std::string> emit_ids) {
        std::sort(emit_ids.begin(), emit_ids.end());
        emit_ids.erase(std::unique(emit_ids.begin(), emit_ids.end()), emit_ids.end());
        std::ostringstream material;
        material << pack_semantic_sha256_ << '\0';
        if (rule_id) material << *rule_id;
        material << '\0' << operation << '\0' << reason;
        for (const std::string &id : emit_ids) material << '\0' << id;
        overlay_.unknown_outcomes.push_back(ModelVmUnknown{
            make_id("model-unknown", material.str()), pack_->model_pack_id,
            rule_id, operation, reason, std::move(emit_ids)});
        overlay_.status = StageStatus::ConservativeIncomplete;
    }

    std::vector<SelectorMatch> exact_matches(const ModelSelectorV2 &selector) {
        std::vector<SelectorMatch> matches;
        for (const EntityRef &entity : index_.entities) {
            const bool match =
                selector.kind == ModelSelectorKind::ExactUsr
                    ? (entity.usr && *entity.usr == *selector.exact_value)
                    : (entity.qualified_signature &&
                       *entity.qualified_signature == *selector.exact_value);
            if (!match) continue;
            const auto nodes = nodes_by_entity_.find(entity.entity_id);
            if (nodes == nodes_by_entity_.end() || nodes->second.empty()) {
                matches.push_back(SelectorMatch{entity.entity_id, std::nullopt});
            } else {
                for (const SemanticNode *node : nodes->second) {
                    matches.push_back(
                        SelectorMatch{entity.entity_id, node->node_id});
                }
            }
        }
        return matches;
    }

    std::vector<SelectorMatch> typed_field_matches(
        const ModelSelectorV2 &selector) {
        std::set<std::string> owner_entities;
        const auto owner = selector_cache_.find(*selector.owner_selector_ref);
        if (owner == selector_cache_.end()) {
            return {};
        }
        for (const SelectorMatch &match : owner->second) {
            owner_entities.insert(match.entity_id);
        }
        std::vector<SelectorMatch> matches;
        for (const SemanticNode &node : index_.nodes) {
            if (!node.access_path ||
                node.access_path->fields.size() != selector.field_path.size()) {
                continue;
            }
            bool fields_match = true;
            for (std::size_t i = 0; i < selector.field_path.size(); ++i) {
                const std::string &entity_id = node.access_path->fields[i];
                const auto field = entities_.find(entity_id);
                if (field == entities_.end()) {
                    fields_match = false;
                    break;
                }
                const std::string &expected = selector.field_path[i];
                const bool component_match =
                    (field->second->usr && *field->second->usr == expected) ||
                    (field->second->qualified_signature &&
                     *field->second->qualified_signature == expected);
                if (!component_match) {
                    fields_match = false;
                    break;
                }
            }
            if (!fields_match) continue;
            const bool owner_match =
                owner_entities.contains(node.access_path->root_entity_id) ||
                owner_entities.contains(node.owner_function_id) ||
                owner_entities.contains(node.entity_id);
            if (!owner_match) continue;
            if (selector.canonical_type &&
                node.value_type.canonical != *selector.canonical_type) {
                continue;
            }
            matches.push_back(SelectorMatch{node.entity_id, node.node_id});
        }
        return matches;
    }

    void execute_selector(const ModelSelectorV2 &selector) {
        std::vector<SelectorMatch> matches =
            selector.kind == ModelSelectorKind::TypedField
                ? typed_field_matches(selector)
                : exact_matches(selector);
        std::sort(matches.begin(), matches.end());
        matches.erase(std::unique(matches.begin(), matches.end()), matches.end());
        const std::uint64_t observed = matches.size();
        const bool complete =
            observed <= pack_->resource_limits.max_selector_matches;
        if (!complete) {
            matches.resize(static_cast<std::size_t>(
                pack_->resource_limits.max_selector_matches));
            add_unknown(
                std::nullopt, "MATCH", "max_selector_matches_exhausted",
                {});
        }
        selector_cache_.emplace(selector.selector_id, std::move(matches));
        add_ledger(
            std::nullopt, "MATCH:" + selector.selector_id,
            pack_->resource_limits.max_selector_matches, observed, complete);
    }

    CaptureValue value_for_node(
        const std::string &node_id,
        const std::optional<std::string> &callsite_id) const {
        const auto found = nodes_.find(node_id);
        CaptureValue value;
        value.semantic_node_id = node_id;
        value.callsite_id = callsite_id;
        if (found != nodes_.end()) {
            value.entity_id = found->second->entity_id;
            const std::string object = object_key_for(*found->second);
            if (!object.empty()) value.object_key = object;
            if (found->second->abstract_object_id) {
                const auto abstract_object =
                    objects_.find(*found->second->abstract_object_id);
                value.object_exact =
                    abstract_object != objects_.end() &&
                    abstract_object->second->certainty == Certainty::Must;
            } else if (found->second->access_path &&
                       found->second->access_path->dereference_depth == 0 &&
                       !found->second->access_path->unknown_suffix) {
                const auto root = entities_.find(
                    found->second->access_path->root_entity_id);
                value.object_exact =
                    root != entities_.end() &&
                    root->second->kind == EntityKind::Global;
            }
        }
        return value;
    }

    std::vector<CaptureValue> project_capture(
        const ModelCaptureV2 &capture,
        const std::vector<SelectorMatch> &matches, bool &projection_incomplete) {
        std::vector<CaptureValue> values;
        for (const SelectorMatch &match : matches) {
            if (capture.projection == ModelProjectionKind::MatchedNode) {
                if (match.semantic_node_id) {
                    values.push_back(value_for_node(*match.semantic_node_id, std::nullopt));
                } else {
                    projection_incomplete = true;
                }
                continue;
            }
            if (capture.projection == ModelProjectionKind::FormalParameter) {
                const auto summary = functions_.find(match.entity_id);
                if (summary == functions_.end() ||
                    *capture.index >= summary->second->parameter_node_ids.size()) {
                    projection_incomplete = true;
                } else {
                    values.push_back(value_for_node(
                        summary->second->parameter_node_ids[*capture.index],
                        std::nullopt));
                }
                continue;
            }
            bool saw_callsite = false;
            for (const CallSiteSummary *callsite : callsites_) {
                if (std::find(
                        callsite->candidate_callee_ids.begin(),
                        callsite->candidate_callee_ids.end(), match.entity_id) ==
                    callsite->candidate_callee_ids.end()) {
                    continue;
                }
                saw_callsite = true;
                if (capture.projection == ModelProjectionKind::CallArgument) {
                    const std::size_t index = *capture.index;
                    if (!callsite->argument_node_groups.empty()) {
                        if (index >= callsite->argument_node_groups.size()) {
                            projection_incomplete = true;
                        } else {
                            for (const std::string &node :
                                 callsite->argument_node_groups[index]) {
                                values.push_back(value_for_node(
                                    node, callsite->callsite_id));
                            }
                        }
                    } else if (index < callsite->argument_node_ids.size()) {
                        values.push_back(value_for_node(
                            callsite->argument_node_ids[index],
                            callsite->callsite_id));
                    } else {
                        projection_incomplete = true;
                    }
                } else if (capture.projection ==
                           ModelProjectionKind::CallResult) {
                    if (callsite->result_node_id) {
                        values.push_back(value_for_node(
                            *callsite->result_node_id, callsite->callsite_id));
                    } else {
                        projection_incomplete = true;
                    }
                } else if (capture.projection == ModelProjectionKind::Receiver) {
                    if (callsite->receiver_node_id) {
                        values.push_back(value_for_node(
                            *callsite->receiver_node_id, callsite->callsite_id));
                    } else {
                        projection_incomplete = true;
                    }
                }
            }
            if (!saw_callsite) {
                projection_incomplete = true;
            }
        }
        std::sort(values.begin(), values.end());
        values.erase(std::unique(values.begin(), values.end()), values.end());
        return values;
    }

    JoinResult evaluate_join(
        const ModelJoinV2 &join, const Assignment &assignment) const {
        const CaptureValue &left = assignment.at(join.left_capture_ref);
        const CaptureValue &right = assignment.at(join.right_capture_ref);
        switch (join.kind) {
        case ModelJoinKind::SameObject:
            if (!left.object_key || !right.object_key) return JoinResult::Unknown;
            if (!left.object_exact || !right.object_exact) {
                return JoinResult::Unknown;
            }
            return *left.object_key == *right.object_key ? JoinResult::Pass
                                                         : JoinResult::Fail;
        case ModelJoinKind::SameHandle:
            if (!left.object_key || !right.object_key) return JoinResult::Unknown;
            if (!left.object_exact || !right.object_exact) {
                return JoinResult::Unknown;
            }
            return *left.object_key == *right.object_key ? JoinResult::Pass
                                                         : JoinResult::Fail;
        case ModelJoinKind::SameCallsite:
            if (!left.callsite_id || !right.callsite_id) return JoinResult::Unknown;
            return *left.callsite_id == *right.callsite_id ? JoinResult::Pass
                                                           : JoinResult::Fail;
        case ModelJoinKind::SameScope:
        case ModelJoinKind::SameGeneration:
        case ModelJoinKind::SameTask:
            return JoinResult::Unknown;
        }
        return JoinResult::Unknown;
    }

    ModelProvenance provenance(
        const ModelRuleV2 &rule, const ModelEmitV2 &emit,
        const Assignment &assignment) const {
        ModelProvenance result;
        result.model_pack_id = pack_->model_pack_id;
        result.model_pack_version = pack_->model_pack_version;
        result.model_pack_sha256 = pack_semantic_sha256_;
        result.layer = pack_->layer;
        result.rule_id = rule.rule_id;
        result.emit_id = emit.emit_id;
        for (const ModelMatchV2 &match : rule.matches) {
            result.selector_ids.push_back(match.selector_ref);
        }
        for (const auto &[capture_id, capture] : assignment) {
            result.capture_ids.push_back(capture_id);
            result.matched_semantic_node_ids.push_back(capture.semantic_node_id);
        }
        std::sort(result.selector_ids.begin(), result.selector_ids.end());
        result.selector_ids.erase(
            std::unique(result.selector_ids.begin(), result.selector_ids.end()),
            result.selector_ids.end());
        std::sort(result.capture_ids.begin(), result.capture_ids.end());
        std::sort(
            result.matched_semantic_node_ids.begin(),
            result.matched_semantic_node_ids.end());
        result.matched_semantic_node_ids.erase(
            std::unique(
                result.matched_semantic_node_ids.begin(),
                result.matched_semantic_node_ids.end()),
            result.matched_semantic_node_ids.end());
        return result;
    }

    std::string action_material(
        const ExternalActionTemplateV2 &action,
        const CaptureValue &source) const {
        std::ostringstream material;
        material << action.action_schema_id << '\0' << action.action_class << '\0'
                 << action.channel << '\0' << action.operation << '\0'
                 << value_type_material(action.payload_type) << '\0'
                 << action.payload_slot << '\0' << action.scope_schema << '\0'
                 << action.generation_schema << '\0'
                 << action.timing_capability << '\0'
                 << action.required_capability << '\0'
                 << external_action_instance_material(source);
        return material.str();
    }

    void emit_assignment(
        const ModelRuleV2 &rule, const Assignment &assignment,
        bool unknown_join) {
        for (const ModelEmitV2 &emit : rule.emits) {
            if (emitted_count_ >= pack_->resource_limits.max_emitted_facts) {
                exhausted_emits_ = true;
                return;
            }
            const CaptureValue &source = assignment.at(emit.source_capture_ref);
            Certainty certainty =
                unknown_join ? Certainty::Unknown : emit.certainty;
            ModelProvenance proof = provenance(rule, emit, assignment);
            if (emit.fact_kind == ModelFactKind::ExternalBoundary) {
                const ExternalActionTemplateV2 &schema = *emit.external_action;
                const std::string action_id = make_id(
                    "external-action", action_material(schema, source));
                ExternalAction action{
                    action_id,
                    schema.action_schema_id,
                    schema.action_class,
                    schema.channel,
                    schema.operation,
                    schema.payload_type,
                    schema.payload_slot,
                    schema.scope_schema,
                    schema.generation_schema,
                    schema.timing_capability,
                    schema.required_capability,
                    {proof}};
                auto [action_position, inserted_action] =
                    actions_.emplace(action_id, std::move(action));
                if (!inserted_action) {
                    action_position->second.provenance.push_back(proof);
                    canonicalize_provenance(action_position->second.provenance);
                }
                const std::string attachment_id = make_id(
                    "boundary-attachment",
                    action_id + '\0' + source.semantic_node_id + '\0' +
                        emit.transfer_relation + '\0' +
                        (emit.value_transfer
                             ? value_transfer_material(*emit.value_transfer)
                             : std::string{}));
                BoundaryAttachment attachment{
                    attachment_id, action_id, source.semantic_node_id,
                    emit.transfer_relation, certainty, {proof},
                    emit.value_transfer};
                auto [position, inserted] = attachments_.emplace(
                    attachment_id, std::move(attachment));
                if (!inserted) {
                    position->second.certainty = merge_certainty(
                        position->second.certainty, certainty);
                    position->second.provenance.push_back(proof);
                    canonicalize_provenance(position->second.provenance);
                }
            } else if (
                emit.fact_kind == ModelFactKind::JointActionRelation) {
                const ModelJointActionRelationV2 &relation =
                    *emit.joint_action_relation;
                std::vector<std::string> participants;
                participants.reserve(
                    relation.participant_capture_refs.size());
                for (const std::string &capture_id :
                     relation.participant_capture_refs) {
                    participants.push_back(
                        assignment.at(capture_id).semantic_node_id);
                }
                std::sort(participants.begin(), participants.end());
                participants.erase(
                    std::unique(participants.begin(), participants.end()),
                    participants.end());
                std::ostringstream group_material;
                group_material << pack_semantic_sha256_ << '\0'
                               << rule.rule_id << '\0'
                               << relation.group_schema_id;
                for (const std::string &participant : participants) {
                    group_material << '\0' << participant;
                }
                const std::string group_id = make_id(
                    "joint-action-group", group_material.str());
                std::ostringstream constraint_material;
                constraint_material
                    << group_id << '\0'
                    << static_cast<int>(relation.combination) << '\0'
                    << (relation.participant_set_complete ? '1' : '0')
                    << '\0' << relation.scope_schema << '\0'
                    << relation.generation_schema;
                ModelJointActionConstraint constraint{
                    make_id(
                        "joint-action-constraint",
                        constraint_material.str()),
                    group_id,
                    relation.group_schema_id,
                    relation.combination,
                    relation.participant_set_complete,
                    participants,
                    relation.scope_schema,
                    relation.generation_schema,
                    certainty,
                    {proof}};
                auto [position, inserted] = joint_constraints_.emplace(
                    constraint.constraint_id, std::move(constraint));
                if (!inserted) {
                    position->second.certainty = merge_certainty(
                        position->second.certainty, certainty);
                    position->second.provenance.push_back(proof);
                    canonicalize_provenance(position->second.provenance);
                }
            } else {
                const CaptureValue &target =
                    assignment.at(*emit.target_capture_ref);
                const std::string fact_id = make_id(
                    "model-fact",
                    model_fact_identity_material(
                        emit.fact_kind, source.semantic_node_id,
                        target.semantic_node_id, emit.transfer_relation,
                        emit.clock_relation, emit.value_transfer));
                ModelFact fact{
                    fact_id, emit.fact_kind, source.semantic_node_id,
                    target.semantic_node_id, emit.transfer_relation, certainty,
                    {proof}, emit.clock_relation, emit.value_transfer};
                auto [position, inserted] = facts_.emplace(
                    fact_id, std::move(fact));
                if (!inserted) {
                    position->second.certainty = merge_certainty(
                        position->second.certainty, certainty);
                    position->second.provenance.push_back(proof);
                    canonicalize_provenance(position->second.provenance);
                }
            }
            ++emitted_count_;
        }
    }

    void execute_rule(const ModelRuleV2 &rule) {
        std::map<std::string, std::vector<SelectorMatch>> matches;
        for (const ModelMatchV2 &match : rule.matches) {
            matches.emplace(match.match_id, selector_cache_.at(match.selector_ref));
        }
        std::map<std::string, std::vector<CaptureValue>> captures;
        bool projection_incomplete = false;
        for (const ModelCaptureV2 &capture : rule.captures) {
            bool local_incomplete = false;
            std::vector<CaptureValue> values = project_capture(
                capture, matches.at(capture.match_ref), local_incomplete);
            const std::uint64_t observed = values.size();
            bool complete =
                observed <= pack_->resource_limits.max_capture_values &&
                !local_incomplete;
            if (values.size() > pack_->resource_limits.max_capture_values) {
                values.resize(static_cast<std::size_t>(
                    pack_->resource_limits.max_capture_values));
            }
            if (!complete) {
                projection_incomplete = true;
                add_unknown(
                    rule.rule_id, "CAPTURE",
                    local_incomplete ? "projection_not_closed"
                                     : "max_capture_values_exhausted",
                    {});
            }
            add_ledger(
                rule.rule_id, "CAPTURE:" + capture.capture_id,
                pack_->resource_limits.max_capture_values,
                observed + (local_incomplete ? 1U : 0U), complete);
            captures.emplace(capture.capture_id, std::move(values));
        }
        if (std::any_of(
                captures.begin(), captures.end(), [](const auto &entry) {
                    return entry.second.empty();
                })) {
            if (projection_incomplete) {
                std::vector<std::string> emits;
                for (const ModelEmitV2 &emit : rule.emits) {
                    emits.push_back(emit.emit_id);
                }
                add_unknown(
                    rule.rule_id, "EMIT", "capture_domain_unknown", emits);
            }
            add_ledger(
                rule.rule_id, "JOIN", pack_->resource_limits.max_join_assignments,
                0, !projection_incomplete);
            return;
        }

        std::vector<std::pair<std::string, const std::vector<CaptureValue> *>>
            ordered_captures;
        for (const auto &[id, values] : captures) {
            ordered_captures.emplace_back(id, &values);
        }
        std::vector<Assignment> assignments;
        bool assignment_exhausted = false;
        Assignment current;
        std::uint64_t observed_assignments = 0;
        std::function<void(std::size_t)> enumerate = [&](const std::size_t depth) {
            if (assignment_exhausted) return;
            if (depth == ordered_captures.size()) {
                ++observed_assignments;
                if (assignments.size() >=
                    pack_->resource_limits.max_join_assignments) {
                    assignment_exhausted = true;
                    return;
                }
                assignments.push_back(current);
                return;
            }
            const auto &[id, values] = ordered_captures[depth];
            for (const CaptureValue &value : *values) {
                current[id] = value;
                enumerate(depth + 1);
                if (assignment_exhausted) break;
            }
            current.erase(id);
        };
        enumerate(0);
        if (assignment_exhausted) {
            add_unknown(
                rule.rule_id, "JOIN", "max_join_assignments_exhausted", {});
        }
        add_ledger(
            rule.rule_id, "JOIN", pack_->resource_limits.max_join_assignments,
            observed_assignments, !assignment_exhausted);

        bool saw_unknown_join = false;
        for (const Assignment &assignment : assignments) {
            bool failed = false;
            bool unknown = false;
            for (const ModelJoinV2 &join : rule.joins) {
                const JoinResult result = evaluate_join(join, assignment);
                failed = failed || result == JoinResult::Fail;
                unknown = unknown || result == JoinResult::Unknown;
            }
            if (!failed) {
                emit_assignment(rule, assignment, unknown);
                saw_unknown_join = saw_unknown_join || unknown;
            }
            if (exhausted_emits_) break;
        }
        if (saw_unknown_join) {
            std::vector<std::string> emit_ids;
            for (const ModelEmitV2 &emit : rule.emits) {
                emit_ids.push_back(emit.emit_id);
            }
            add_unknown(
                rule.rule_id, "JOIN", "join_relation_not_closed",
                std::move(emit_ids));
        }
    }

    const SemanticIndex &index_;
    ModelFactOverlay &overlay_;
    std::map<std::string, ExternalAction> &actions_;
    std::map<std::string, BoundaryAttachment> &attachments_;
    std::map<std::string, ModelFact> &facts_;
    std::map<std::string, ModelJointActionConstraint> &joint_constraints_;
    const ModelPackV2 *pack_ = nullptr;
    std::string pack_semantic_sha256_;
    std::unordered_map<std::string, const EntityRef *> entities_;
    std::unordered_map<std::string, const AbstractObject *> objects_;
    std::unordered_map<std::string, const SemanticNode *> nodes_;
    std::unordered_map<std::string, std::vector<const SemanticNode *>>
        nodes_by_entity_;
    std::unordered_map<std::string, const FunctionSummary *> functions_;
    std::vector<const CallSiteSummary *> callsites_;
    std::map<std::string, std::vector<SelectorMatch>> selector_cache_;
    std::uint64_t emitted_count_ = 0;
    bool exhausted_emits_ = false;
};

void canonicalize_overlay(ModelFactOverlay &overlay) {
    for (ExternalAction &action : overlay.external_actions) {
        canonicalize_provenance(action.provenance);
    }
    for (BoundaryAttachment &attachment : overlay.boundary_attachments) {
        canonicalize_provenance(attachment.provenance);
    }
    for (ModelFact &fact : overlay.semantic_facts) {
        canonicalize_provenance(fact.provenance);
    }
    for (ModelJointActionConstraint &constraint :
         overlay.joint_action_constraints) {
        std::sort(
            constraint.participant_semantic_node_ids.begin(),
            constraint.participant_semantic_node_ids.end());
        constraint.participant_semantic_node_ids.erase(
            std::unique(
                constraint.participant_semantic_node_ids.begin(),
                constraint.participant_semantic_node_ids.end()),
            constraint.participant_semantic_node_ids.end());
        canonicalize_provenance(constraint.provenance);
    }
    std::sort(
        overlay.model_pack_sha256s.begin(), overlay.model_pack_sha256s.end());
    overlay.model_pack_sha256s.erase(
        std::unique(
            overlay.model_pack_sha256s.begin(),
            overlay.model_pack_sha256s.end()),
        overlay.model_pack_sha256s.end());
    std::sort(
        overlay.external_actions.begin(), overlay.external_actions.end(),
        [](const ExternalAction &left, const ExternalAction &right) {
            return left.external_action_id < right.external_action_id;
        });
    std::sort(
        overlay.boundary_attachments.begin(),
        overlay.boundary_attachments.end(),
        [](const BoundaryAttachment &left, const BoundaryAttachment &right) {
            return left.attachment_id < right.attachment_id;
        });
    std::sort(
        overlay.semantic_facts.begin(), overlay.semantic_facts.end(),
        [](const ModelFact &left, const ModelFact &right) {
            return left.fact_id < right.fact_id;
        });
    std::sort(
        overlay.joint_action_constraints.begin(),
        overlay.joint_action_constraints.end(),
        [](const ModelJointActionConstraint &left,
           const ModelJointActionConstraint &right) {
            return left.constraint_id < right.constraint_id;
        });
    std::sort(
        overlay.unknown_outcomes.begin(), overlay.unknown_outcomes.end(),
        [](const ModelVmUnknown &left, const ModelVmUnknown &right) {
            return left.unknown_id < right.unknown_id;
        });
    overlay.unknown_outcomes.erase(
        std::unique(
            overlay.unknown_outcomes.begin(), overlay.unknown_outcomes.end(),
            [](const ModelVmUnknown &left, const ModelVmUnknown &right) {
                return left.unknown_id == right.unknown_id;
            }),
        overlay.unknown_outcomes.end());
    std::sort(
        overlay.resource_ledger.begin(), overlay.resource_ledger.end(),
        [](const ModelResourceLedgerEntry &left,
           const ModelResourceLedgerEntry &right) {
            return left.ledger_id < right.ledger_id;
        });
    overlay.resource_ledger.erase(
        std::unique(
            overlay.resource_ledger.begin(), overlay.resource_ledger.end(),
            [](const ModelResourceLedgerEntry &left,
               const ModelResourceLedgerEntry &right) {
                return left.ledger_id == right.ledger_id;
            }),
        overlay.resource_ledger.end());
    std::sort(
        overlay.coverage_gaps.begin(), overlay.coverage_gaps.end(),
        [](const CoverageGap &left, const CoverageGap &right) {
            return left.gap_id < right.gap_id;
        });
    overlay.coverage_gaps.erase(
        std::unique(
            overlay.coverage_gaps.begin(), overlay.coverage_gaps.end(),
            [](const CoverageGap &left, const CoverageGap &right) {
                return left.gap_id == right.gap_id;
            }),
        overlay.coverage_gaps.end());
    std::sort(overlay.diagnostics.begin(), overlay.diagnostics.end());
    overlay.diagnostics.erase(
        std::unique(overlay.diagnostics.begin(), overlay.diagnostics.end()),
        overlay.diagnostics.end());
}

std::string overlay_identity_material(const ModelFactOverlay &overlay) {
    std::ostringstream material;
    material << overlay.semantic_index_identity << '\0'
             << static_cast<int>(overlay.status);
    for (const std::string &digest : overlay.model_pack_sha256s) {
        material << '\0' << digest;
    }
    for (const ExternalAction &action : overlay.external_actions) {
        material << '\0' << action.external_action_id;
    }
    for (const BoundaryAttachment &attachment : overlay.boundary_attachments) {
        material << '\0' << attachment.attachment_id << '\0'
                 << static_cast<int>(attachment.certainty);
    }
    for (const ModelFact &fact : overlay.semantic_facts) {
        material << '\0' << fact.fact_id << '\0'
                 << static_cast<int>(fact.certainty);
    }
    for (const ModelJointActionConstraint &constraint :
         overlay.joint_action_constraints) {
        material << '\0' << constraint.constraint_id << '\0'
                 << static_cast<int>(constraint.certainty);
    }
    for (const ModelVmUnknown &unknown : overlay.unknown_outcomes) {
        material << '\0' << unknown.unknown_id;
    }
    for (const ModelResourceLedgerEntry &ledger : overlay.resource_ledger) {
        material << '\0' << ledger.ledger_id << '\0' << ledger.observed << '\0'
                 << (ledger.complete ? '1' : '0');
    }
    return material.str();
}

}  // namespace

LoadResult<ModelFactOverlay> execute_model_pack_v2(
    const ModelPackV2 &pack, const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256) {
    return execute_model_packs_v2(
        {pack}, semantic_index, semantic_index_sha256);
}

LoadResult<ModelFactOverlay> execute_model_packs_v2(
    const std::vector<ModelPackV2> &packs,
    const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256) {
    LoadResult<ModelFactOverlay> result;
    if (packs.empty()) {
        result.diagnostics.push_back("at least one model-pack/2.0.0 is required");
        return result;
    }
    if (!is_sha256(semantic_index_sha256)) {
        result.diagnostics.push_back(
            "exact semantic_index.json SHA-256 is required");
        return result;
    }
    const std::vector<std::string> index_errors =
        validate_semantic_index(semantic_index);
    if (!index_errors.empty()) {
        result.diagnostics.reserve(index_errors.size());
        for (const std::string &error : index_errors) {
            result.diagnostics.push_back("semantic index: " + error);
        }
        return result;
    }
    std::vector<const ModelPackV2 *> ordered;
    std::map<std::pair<std::string, std::string>, std::string> identities;
    std::map<const ModelPackV2 *, std::string> semantic_digests;
    for (const ModelPackV2 &pack : packs) {
        const std::vector<std::string> errors = validate_model_pack_v2(pack);
        for (const std::string &error : errors) {
            result.diagnostics.push_back(
                pack.model_pack_id + "@" + pack.model_pack_version + ": " +
                error);
        }
        const auto key = std::make_pair(
            pack.model_pack_id, pack.model_pack_version);
        const std::string semantic_digest =
            model_pack_semantic_sha256(pack);
        semantic_digests.emplace(&pack, semantic_digest);
        const auto [position, inserted] = identities.emplace(
            key, semantic_digest);
        if (!inserted && position->second != semantic_digest) {
            result.diagnostics.push_back(
                "conflicting semantics for duplicate model pack identity " +
                pack.model_pack_id + "@" + pack.model_pack_version);
        }
        ordered.push_back(&pack);
    }
    if (!result.diagnostics.empty()) {
        std::sort(result.diagnostics.begin(), result.diagnostics.end());
        result.diagnostics.erase(
            std::unique(result.diagnostics.begin(), result.diagnostics.end()),
            result.diagnostics.end());
        return result;
    }
    std::sort(
        ordered.begin(), ordered.end(),
        [](const ModelPackV2 *left, const ModelPackV2 *right) {
            return std::tuple{
                       left->model_pack_id, left->model_pack_version,
                       model_pack_semantic_sha256(*left)} <
                   std::tuple{
                       right->model_pack_id, right->model_pack_version,
                       model_pack_semantic_sha256(*right)};
        });
    ordered.erase(
        std::unique(
            ordered.begin(), ordered.end(),
            [](const ModelPackV2 *left, const ModelPackV2 *right) {
                return left->model_pack_id == right->model_pack_id &&
                       left->model_pack_version == right->model_pack_version &&
                       model_pack_semantic_sha256(*left) ==
                           model_pack_semantic_sha256(*right);
            }),
        ordered.end());

    ModelFactOverlay overlay;
    overlay.semantic_index_artifact_id = semantic_index.artifact_id;
    overlay.semantic_index_identity = semantic_index_sha256;
    overlay.status = semantic_index.status == StageStatus::Complete
                         ? StageStatus::Complete
                         : StageStatus::ConservativeIncomplete;
    if (semantic_index.status != StageStatus::Complete) {
        overlay.unknown_outcomes.push_back(ModelVmUnknown{
            make_id(
                "model-unknown",
                overlay.semantic_index_identity + "\0semantic-index-incomplete"),
            ordered.front()->model_pack_id, std::nullopt, "INDEX",
            "semantic_index_conservative_incomplete", {}});
    }
    std::map<std::string, ExternalAction> actions;
    std::map<std::string, BoundaryAttachment> attachments;
    std::map<std::string, ModelFact> facts;
    std::map<std::string, ModelJointActionConstraint> joint_constraints;
    VmExecutor executor(
        semantic_index, overlay, actions, attachments, facts,
        joint_constraints);
    for (const ModelPackV2 *pack : ordered) {
        overlay.model_pack_sha256s.push_back(semantic_digests.at(pack));
        executor.execute(*pack);
    }
    for (auto &[unused, action] : actions) {
        (void)unused;
        overlay.external_actions.push_back(std::move(action));
    }
    for (auto &[unused, attachment] : attachments) {
        (void)unused;
        overlay.boundary_attachments.push_back(std::move(attachment));
    }
    for (auto &[unused, fact] : facts) {
        (void)unused;
        overlay.semantic_facts.push_back(std::move(fact));
    }
    for (auto &[unused, constraint] : joint_constraints) {
        (void)unused;
        overlay.joint_action_constraints.push_back(
            std::move(constraint));
    }
    canonicalize_overlay(overlay);
    overlay.artifact_id = make_id(
        "model-overlay", overlay_identity_material(overlay));
    const std::vector<std::string> overlay_errors =
        validate_model_fact_overlay(
            overlay, semantic_index, semantic_index_sha256);
    if (!overlay_errors.empty()) {
        result.diagnostics = overlay_errors;
        return result;
    }
    result.status = overlay.status;
    result.observed_sha256 = sha256_hex(canonical_model_fact_overlay_json(overlay));
    result.value = std::move(overlay);
    return result;
}

namespace {

const char *value_kind_text(ValueKind kind) {
    switch (kind) {
    case ValueKind::Boolean: return "bool";
    case ValueKind::Integer: return "integer";
    case ValueKind::Floating: return "floating";
    case ValueKind::Enumeration: return "enum";
    case ValueKind::BitVector: return "bitvector";
    case ValueKind::Timestamp: return "timestamp";
    case ValueKind::Duration: return "duration";
    case ValueKind::Pointer: return "pointer";
    case ValueKind::Record: return "record";
    case ValueKind::Array: return "array";
    case ValueKind::Unknown: return "unknown";
    }
    return "unknown";
}

Object value_type_json(const ValueType &type) {
    Object object{{"kind", value_kind_text(type.kind)},
                  {"canonical", type.canonical}};
    if (type.bit_width) object["bit_width"] = *type.bit_width;
    if (type.is_signed) object["signed"] = *type.is_signed;
    if (type.unit) object["unit"] = *type.unit;
    return object;
}

Array string_array(const std::vector<std::string> &values) {
    Array array;
    for (const std::string &value : values) array.push_back(value);
    return array;
}

Object provenance_json(const ModelProvenance &provenance) {
    return Object{
        {"model_pack_id", provenance.model_pack_id},
        {"model_pack_version", provenance.model_pack_version},
        {"model_pack_sha256", provenance.model_pack_sha256},
        {"layer", to_string(provenance.layer)},
        {"rule_id", provenance.rule_id},
        {"emit_id", provenance.emit_id},
        {"selector_ids", string_array(provenance.selector_ids)},
        {"capture_ids", string_array(provenance.capture_ids)},
        {"matched_semantic_node_ids",
         string_array(provenance.matched_semantic_node_ids)}};
}

Array provenance_array(const std::vector<ModelProvenance> &provenance) {
    Array array;
    for (const ModelProvenance &item : provenance) {
        array.push_back(provenance_json(item));
    }
    return array;
}

Value clock_relation_json(
    const std::optional<ModelClockRelationV2> &relation) {
    if (!relation) return Value(nullptr);
    Object object;
    object["clock_source"] = relation->clock_source
        ? Value(*relation->clock_source) : Value(nullptr);
    object["unit"] = relation->unit
        ? Value(to_string(*relation->unit)) : Value(nullptr);
    object["epoch"] = relation->epoch
        ? Value(*relation->epoch) : Value(nullptr);
    object["quantum"] = relation->quantum
        ? Value(*relation->quantum) : Value(nullptr);
    object["jitter"] = relation->jitter
        ? Value(*relation->jitter) : Value(nullptr);
    object["wrap"] = relation->wrap
        ? Value(to_string(*relation->wrap)) : Value(nullptr);
    object["wrap_value"] = relation->wrap_value
        ? Value(static_cast<std::int64_t>(*relation->wrap_value))
        : Value(nullptr);
    object["start_event"] = relation->start_event
        ? Value(*relation->start_event) : Value(nullptr);
    object["end_event"] = relation->end_event
        ? Value(*relation->end_event) : Value(nullptr);
    object["endpoint"] = relation->endpoint
        ? Value(to_string(*relation->endpoint)) : Value(nullptr);
    object["scope_schema"] = relation->scope_schema
        ? Value(*relation->scope_schema) : Value(nullptr);
    object["generation_schema"] = relation->generation_schema
        ? Value(*relation->generation_schema) : Value(nullptr);
    return Value(std::move(object));
}

Value value_transfer_json(
    const std::optional<ModelValueTransferV2> &transfer) {
    if (!transfer) return Value(nullptr);
    Object object{
        {"kind", to_string(transfer->kind)},
        {"precondition", to_string(transfer->precondition)},
        {"executor_enforces_precondition",
         transfer->executor_enforces_precondition},
        {"failure_branch_unknown", transfer->failure_branch_unknown}};
    object["affine_scale"] = transfer->affine_scale
        ? Value(*transfer->affine_scale) : Value(nullptr);
    object["affine_offset"] = transfer->affine_offset
        ? Value(*transfer->affine_offset) : Value(nullptr);
    return Value(std::move(object));
}

const char *gap_effect_text(GapEffect effect) {
    switch (effect) {
    case GapEffect::PrecisionLoss: return "precision_loss";
    case GapEffect::SoundnessRisk: return "soundness_risk";
    case GapEffect::StageFailure: return "stage_failure";
    }
    return "soundness_risk";
}

Object location_json(const SourceLocation &location) {
    Object object{{"file", location.file},
                  {"line", location.line},
                  {"column", location.column},
                  {"location_kind", location.location_kind}};
    if (location.end_line != 0) object["end_line"] = location.end_line;
    if (location.end_column != 0) object["end_column"] = location.end_column;
    if (!location.macro_stack.empty()) {
        object["macro_stack"] = string_array(location.macro_stack);
    }
    return object;
}

std::vector<std::string> validate_provenance_list(
    const std::vector<ModelProvenance> &items,
    const std::set<std::string> &pack_sha256s, const std::string &path) {
    std::vector<std::string> errors;
    if (items.empty()) {
        errors.push_back(path + ": provenance must not be empty");
        return errors;
    }
    std::set<std::string> material;
    for (const ModelProvenance &item : items) {
        if (!pack_sha256s.contains(item.model_pack_sha256)) {
            errors.push_back(path + ": provenance references unknown pack digest");
        }
        if (!is_stable_id(item.model_pack_id) ||
            !is_semver(item.model_pack_version) ||
            !is_stable_id(item.rule_id) || !is_stable_id(item.emit_id)) {
            errors.push_back(path + ": invalid provenance identity");
        }
        if (!material.insert(provenance_material(item)).second) {
            errors.push_back(path + ": duplicate provenance");
        }
        if (!std::is_sorted(item.selector_ids.begin(), item.selector_ids.end()) ||
            !std::is_sorted(item.capture_ids.begin(), item.capture_ids.end()) ||
            !std::is_sorted(
                item.matched_semantic_node_ids.begin(),
                item.matched_semantic_node_ids.end())) {
            errors.push_back(path + ": provenance ledgers are not canonical");
        }
    }
    for (std::size_t i = 1; i < items.size(); ++i) {
        if (provenance_material(items[i - 1]) >= provenance_material(items[i])) {
            errors.push_back(path + ": provenance order is not canonical");
            break;
        }
    }
    return errors;
}

template <typename Range, typename Id>
std::set<std::string> overlay_unique_ids(
    const Range &items, Id id, const std::string &kind,
    std::vector<std::string> &errors, std::set<std::string> &global) {
    std::set<std::string> local;
    for (const auto &item : items) {
        const std::string value = id(item);
        if (!is_stable_id(value)) {
            errors.push_back(kind + " has invalid stable ID: " + value);
        }
        if (!local.insert(value).second) {
            errors.push_back("duplicate " + kind + ": " + value);
        }
        if (!global.insert(value).second) {
            errors.push_back("cross-kind ID collision: " + value);
        }
    }
    return local;
}

}  // namespace

std::vector<std::string> validate_model_fact_overlay(
    const ModelFactOverlay &overlay, const SemanticIndex &semantic_index,
    const std::optional<std::string> &expected_semantic_index_sha256) {
    std::vector<std::string> errors;
    if (!is_stable_id(overlay.artifact_id)) {
        errors.push_back("overlay has invalid artifact ID");
    }
    if (overlay.semantic_index_artifact_id != semantic_index.artifact_id) {
        errors.push_back("overlay semantic index artifact ID mismatch");
    }
    if (!is_sha256(overlay.semantic_index_identity)) {
        errors.push_back("overlay semantic index content digest is invalid");
    }
    if (expected_semantic_index_sha256 &&
        overlay.semantic_index_identity != *expected_semantic_index_sha256) {
        errors.push_back("overlay semantic index content digest mismatch");
    }
    if (!std::is_sorted(
            overlay.model_pack_sha256s.begin(),
            overlay.model_pack_sha256s.end()) ||
        std::adjacent_find(
            overlay.model_pack_sha256s.begin(),
            overlay.model_pack_sha256s.end()) !=
            overlay.model_pack_sha256s.end()) {
        errors.push_back("overlay model pack digest ledger is not canonical");
    }
    std::set<std::string> pack_digests;
    for (const std::string &digest : overlay.model_pack_sha256s) {
        if (!is_sha256(digest)) {
            errors.push_back("overlay contains invalid model pack digest");
        }
        pack_digests.insert(digest);
    }
    std::set<std::string> semantic_nodes;
    for (const SemanticNode &node : semantic_index.nodes) {
        semantic_nodes.insert(node.node_id);
    }
    std::set<std::string> global{overlay.artifact_id};
    const std::set<std::string> action_ids = overlay_unique_ids(
        overlay.external_actions,
        [](const ExternalAction &item) { return item.external_action_id; },
        "external action", errors, global);
    overlay_unique_ids(
        overlay.boundary_attachments,
        [](const BoundaryAttachment &item) { return item.attachment_id; },
        "boundary attachment", errors, global);
    overlay_unique_ids(
        overlay.semantic_facts,
        [](const ModelFact &item) { return item.fact_id; }, "model fact",
        errors, global);
    overlay_unique_ids(
        overlay.joint_action_constraints,
        [](const ModelJointActionConstraint &item) {
            return item.constraint_id;
        },
        "joint action constraint", errors, global);
    overlay_unique_ids(
        overlay.unknown_outcomes,
        [](const ModelVmUnknown &item) { return item.unknown_id; },
        "unknown outcome", errors, global);
    overlay_unique_ids(
        overlay.resource_ledger,
        [](const ModelResourceLedgerEntry &item) { return item.ledger_id; },
        "resource ledger", errors, global);
    overlay_unique_ids(
        overlay.coverage_gaps,
        [](const CoverageGap &item) { return item.gap_id; }, "coverage gap",
        errors, global);

    for (const ExternalAction &action : overlay.external_actions) {
        if (!is_stable_id(action.action_schema_id) || action.action_class.empty() ||
            action.channel.empty() || action.operation.empty() ||
            action.payload_type.canonical.empty() || action.payload_slot.empty() ||
            action.scope_schema.empty() || action.generation_schema.empty() ||
            action.timing_capability.empty() ||
            action.required_capability.empty()) {
            errors.push_back(
                "external action has incomplete typed identity: " +
                action.external_action_id);
        }
        std::vector<std::string> provenance_errors = validate_provenance_list(
            action.provenance, pack_digests, action.external_action_id);
        errors.insert(
            errors.end(), provenance_errors.begin(), provenance_errors.end());
    }
    for (const BoundaryAttachment &attachment :
         overlay.boundary_attachments) {
        if (!action_ids.contains(attachment.external_action_id)) {
            errors.push_back(
                "boundary attachment references unknown action: " +
                attachment.attachment_id);
        }
        if (!semantic_nodes.contains(attachment.semantic_node_id)) {
            errors.push_back(
                "boundary attachment references unknown semantic node: " +
                attachment.attachment_id);
        }
        if (attachment.certainty != Certainty::Modelled &&
            attachment.certainty != Certainty::Unknown) {
            errors.push_back(
                "boundary attachment certainty is not MODELLED/UNKNOWN: " +
                attachment.attachment_id);
        }
        if (attachment.value_transfer &&
            !valid_value_transfer_contract(*attachment.value_transfer)) {
            errors.push_back(
                "boundary attachment has inconsistent typed value transfer: " +
                attachment.attachment_id);
        }
        const std::string attachment_material =
            attachment.external_action_id + '\0' +
            attachment.semantic_node_id + '\0' +
            attachment.transfer_relation + '\0' +
            (attachment.value_transfer
                 ? value_transfer_material(*attachment.value_transfer)
                 : std::string{});
        if (attachment.attachment_id !=
            make_id("boundary-attachment", attachment_material)) {
            errors.push_back(
                "boundary attachment ID is not bound to typed content: " +
                attachment.attachment_id);
        }
        std::vector<std::string> provenance_errors = validate_provenance_list(
            attachment.provenance, pack_digests, attachment.attachment_id);
        errors.insert(
            errors.end(), provenance_errors.begin(), provenance_errors.end());
    }
    for (const ModelFact &fact : overlay.semantic_facts) {
        if (fact.kind == ModelFactKind::ExternalBoundary ||
            fact.kind == ModelFactKind::JointActionRelation) {
            errors.push_back(
                "non-arc model fact is in the semantic arc ledger: " +
                fact.fact_id);
        }
        if (!semantic_nodes.contains(fact.source_semantic_node_id) ||
            !fact.target_semantic_node_id ||
            !semantic_nodes.contains(*fact.target_semantic_node_id)) {
            errors.push_back(
                "model fact references unknown semantic node: " + fact.fact_id);
        }
        if (fact.certainty != Certainty::Modelled &&
            fact.certainty != Certainty::Unknown) {
            errors.push_back(
                "model fact certainty is not MODELLED/UNKNOWN: " + fact.fact_id);
        }
        if ((fact.kind == ModelFactKind::ClockRelation) !=
            fact.clock_relation.has_value()) {
            errors.push_back(
                "clock fact typed-payload contract mismatch: " +
                fact.fact_id);
        }
        if (fact.value_transfer &&
            !valid_value_transfer_contract(*fact.value_transfer)) {
            errors.push_back(
                "model fact has inconsistent typed value transfer: " +
                fact.fact_id);
        }
        if (fact.target_semantic_node_id &&
            fact.fact_id != make_id(
                "model-fact",
                model_fact_identity_material(
                    fact.kind, fact.source_semantic_node_id,
                    *fact.target_semantic_node_id, fact.transfer_relation,
                    fact.clock_relation, fact.value_transfer))) {
            errors.push_back(
                "model fact ID is not bound to typed content: " +
                fact.fact_id);
        }
        if (fact.clock_relation) {
            const ModelClockRelationV2 &clock = *fact.clock_relation;
            const bool complete = clock.clock_source && clock.unit &&
                clock.epoch && clock.quantum && clock.jitter && clock.wrap &&
                clock.start_event && clock.end_event && clock.endpoint &&
                clock.scope_schema && clock.generation_schema;
            if (!complete ||
                (clock.quantum &&
                 (!std::isfinite(*clock.quantum) ||
                  *clock.quantum <= 0.0)) ||
                (clock.jitter &&
                 (!std::isfinite(*clock.jitter) || *clock.jitter < 0.0))) {
                errors.push_back(
                    "clock fact has incomplete/invalid fixed fields: " +
                    fact.fact_id);
            }
        }
        std::vector<std::string> provenance_errors = validate_provenance_list(
            fact.provenance, pack_digests, fact.fact_id);
        errors.insert(
            errors.end(), provenance_errors.begin(), provenance_errors.end());
    }
    for (const ModelJointActionConstraint &constraint :
         overlay.joint_action_constraints) {
        if (!is_stable_id(constraint.group_instance_id) ||
            !is_stable_id(constraint.group_schema_id) ||
            !is_stable_id(constraint.scope_schema) ||
            !is_stable_id(constraint.generation_schema) ||
            constraint.participant_semantic_node_ids.size() < 2 ||
            !std::is_sorted(
                constraint.participant_semantic_node_ids.begin(),
                constraint.participant_semantic_node_ids.end()) ||
            std::adjacent_find(
                constraint.participant_semantic_node_ids.begin(),
                constraint.participant_semantic_node_ids.end()) !=
                constraint.participant_semantic_node_ids.end()) {
            errors.push_back(
                "joint action constraint has incomplete typed identity: " +
                constraint.constraint_id);
        }
        for (const std::string &node_id :
             constraint.participant_semantic_node_ids) {
            if (!semantic_nodes.contains(node_id)) {
                errors.push_back(
                    "joint action constraint references unknown semantic node: " +
                    constraint.constraint_id);
            }
        }
        if (constraint.certainty != Certainty::Modelled &&
            constraint.certainty != Certainty::Unknown) {
            errors.push_back(
                "joint action constraint certainty is not MODELLED/UNKNOWN: " +
                constraint.constraint_id);
        }
        std::ostringstream material;
        material << constraint.group_instance_id << '\0'
                 << static_cast<int>(constraint.combination) << '\0'
                 << (constraint.participant_set_complete ? '1' : '0')
                 << '\0' << constraint.scope_schema << '\0'
                 << constraint.generation_schema;
        if (constraint.constraint_id !=
            make_id("joint-action-constraint", material.str())) {
            errors.push_back(
                "joint action constraint ID is not content-bound: " +
                constraint.constraint_id);
        }
        std::vector<std::string> provenance_errors =
            validate_provenance_list(
                constraint.provenance, pack_digests,
                constraint.constraint_id);
        errors.insert(
            errors.end(), provenance_errors.begin(),
            provenance_errors.end());
    }
    bool incomplete_ledger = false;
    for (const ModelResourceLedgerEntry &ledger : overlay.resource_ledger) {
        if (ledger.limit == 0 || ledger.certainty != Certainty::Unknown) {
            errors.push_back(
                "invalid resource ledger contract: " + ledger.ledger_id);
        }
        if (ledger.complete && ledger.observed > ledger.limit) {
            errors.push_back(
                "complete resource ledger exceeds limit: " + ledger.ledger_id);
        }
        incomplete_ledger = incomplete_ledger || !ledger.complete;
    }
    if ((incomplete_ledger || !overlay.unknown_outcomes.empty()) &&
        overlay.status == StageStatus::Complete) {
        errors.push_back("complete overlay contains UNKNOWN/incomplete ledger");
    }
    if (overlay.artifact_id !=
        make_id("model-overlay", overlay_identity_material(overlay))) {
        errors.push_back("overlay artifact ID is not bound to canonical content");
    }
    if (!std::is_sorted(
            overlay.external_actions.begin(), overlay.external_actions.end(),
            [](const ExternalAction &left, const ExternalAction &right) {
                return left.external_action_id < right.external_action_id;
            }) ||
        !std::is_sorted(
            overlay.boundary_attachments.begin(),
            overlay.boundary_attachments.end(),
            [](const BoundaryAttachment &left,
               const BoundaryAttachment &right) {
                return left.attachment_id < right.attachment_id;
            }) ||
        !std::is_sorted(
            overlay.semantic_facts.begin(), overlay.semantic_facts.end(),
            [](const ModelFact &left, const ModelFact &right) {
                return left.fact_id < right.fact_id;
            }) ||
        !std::is_sorted(
            overlay.joint_action_constraints.begin(),
            overlay.joint_action_constraints.end(),
            [](const ModelJointActionConstraint &left,
               const ModelJointActionConstraint &right) {
                return left.constraint_id < right.constraint_id;
            })) {
        errors.push_back("overlay semantic outputs are not canonical-sorted");
    }
    std::sort(errors.begin(), errors.end());
    errors.erase(std::unique(errors.begin(), errors.end()), errors.end());
    return errors;
}

std::string canonical_model_fact_overlay_json(
    const ModelFactOverlay &input_overlay) {
    ModelFactOverlay overlay = input_overlay;
    canonicalize_overlay(overlay);
    Array actions;
    for (const ExternalAction &action : overlay.external_actions) {
        actions.push_back(Object{
            {"external_action_id", action.external_action_id},
            {"action_schema_id", action.action_schema_id},
            {"action_class", action.action_class},
            {"channel", action.channel},
            {"operation", action.operation},
            {"payload_type", value_type_json(action.payload_type)},
            {"payload_slot", action.payload_slot},
            {"scope_schema", action.scope_schema},
            {"generation_schema", action.generation_schema},
            {"timing_capability", action.timing_capability},
            {"required_capability", action.required_capability},
            {"provenance", provenance_array(action.provenance)}});
    }
    Array attachments;
    for (const BoundaryAttachment &attachment :
         overlay.boundary_attachments) {
        attachments.push_back(Object{
            {"attachment_id", attachment.attachment_id},
            {"external_action_id", attachment.external_action_id},
            {"semantic_node_id", attachment.semantic_node_id},
            {"transfer_relation", attachment.transfer_relation},
            {"certainty", to_string(attachment.certainty)},
            {"value_transfer",
             value_transfer_json(attachment.value_transfer)},
            {"provenance", provenance_array(attachment.provenance)}});
    }
    Array facts;
    for (const ModelFact &fact : overlay.semantic_facts) {
        Object object{
            {"fact_id", fact.fact_id},
            {"kind", to_string(fact.kind)},
            {"source_semantic_node_id", fact.source_semantic_node_id},
            {"transfer_relation", fact.transfer_relation},
            {"certainty", to_string(fact.certainty)},
            {"provenance", provenance_array(fact.provenance)}};
        object["target_semantic_node_id"] =
            fact.target_semantic_node_id
                ? Value(*fact.target_semantic_node_id)
                : Value(nullptr);
        object["clock_relation"] =
            clock_relation_json(fact.clock_relation);
        object["value_transfer"] =
            value_transfer_json(fact.value_transfer);
        facts.push_back(std::move(object));
    }
    Array joint_constraints;
    for (const ModelJointActionConstraint &constraint :
         overlay.joint_action_constraints) {
        joint_constraints.push_back(Object{
            {"constraint_id", constraint.constraint_id},
            {"group_instance_id", constraint.group_instance_id},
            {"group_schema_id", constraint.group_schema_id},
            {"combination", to_string(constraint.combination)},
            {"participant_set_complete",
             constraint.participant_set_complete},
            {"participant_semantic_node_ids",
             string_array(constraint.participant_semantic_node_ids)},
            {"scope_schema", constraint.scope_schema},
            {"generation_schema", constraint.generation_schema},
            {"certainty", to_string(constraint.certainty)},
            {"provenance", provenance_array(constraint.provenance)}});
    }
    Array unknown;
    for (const ModelVmUnknown &item : overlay.unknown_outcomes) {
        Object object{{"unknown_id", item.unknown_id},
                      {"model_pack_id", item.model_pack_id},
                      {"operation", item.operation},
                      {"reason", item.reason},
                      {"affected_emit_ids", string_array(item.affected_emit_ids)}};
        object["rule_id"] = item.rule_id ? Value(*item.rule_id) : Value(nullptr);
        unknown.push_back(std::move(object));
    }
    Array ledger;
    for (const ModelResourceLedgerEntry &item : overlay.resource_ledger) {
        Object object{{"ledger_id", item.ledger_id},
                      {"model_pack_id", item.model_pack_id},
                      {"operation", item.operation},
                      {"limit", item.limit},
                      {"observed", item.observed},
                      {"complete", item.complete},
                      {"certainty", to_string(item.certainty)}};
        object["rule_id"] = item.rule_id ? Value(*item.rule_id) : Value(nullptr);
        ledger.push_back(std::move(object));
    }
    Array gaps;
    for (const CoverageGap &gap : overlay.coverage_gaps) {
        Array locations;
        for (const SourceLocation &location : gap.locations) {
            locations.push_back(location_json(location));
        }
        gaps.push_back(Object{
            {"construct_id", gap.gap_id},
            {"kind", gap.kind},
            {"effect", gap_effect_text(gap.effect)},
            {"detail", gap.detail},
            {"locations", std::move(locations)},
            {"affected_ids", string_array(gap.affected_ids)}});
    }
    Object root{
        {"schema_version", "1.0.0"},
        {"artifact_id", overlay.artifact_id},
        {"semantic_index_artifact_id", overlay.semantic_index_artifact_id},
        {"semantic_index_identity", overlay.semantic_index_identity},
        {"status", to_string(overlay.status)},
        {"model_pack_sha256s", string_array(overlay.model_pack_sha256s)},
        {"external_actions", std::move(actions)},
        {"boundary_attachments", std::move(attachments)},
        {"semantic_facts", std::move(facts)},
        {"joint_action_constraints", std::move(joint_constraints)},
        {"unknown_outcomes", std::move(unknown)},
        {"resource_ledger", std::move(ledger)},
        {"coverage_gaps", std::move(gaps)},
        {"diagnostics", string_array(overlay.diagnostics)}};
    return llvm::formatv("{0}\n", Value(std::move(root))).str();
}

}  // namespace rift::core
