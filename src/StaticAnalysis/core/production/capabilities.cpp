#include "rift/core/capabilities.h"

#include "rift/core/sha256.h"

#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

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
    const Object &object, const llvm::StringRef key, const std::string &path,
    ParseContext &context) {
    const std::optional<llvm::StringRef> value = object.getString(key);
    if (!value || value->empty()) {
        context.error(path + '.' + key.str(), "expected non-empty string");
        return std::nullopt;
    }
    return value->str();
}

std::optional<std::vector<std::string>> string_array(
    const Array *array, const std::string &path, ParseContext &context,
    const bool require_nonempty = false) {
    if (array == nullptr) {
        context.error(path, "expected array");
        return std::nullopt;
    }
    std::vector<std::string> result;
    for (std::size_t i = 0; i < array->size(); ++i) {
        const auto value = (*array)[i].getAsString();
        if (!value || (require_nonempty && value->empty())) {
            context.error(
                path + '[' + std::to_string(i) + ']',
                require_nonempty ? "expected non-empty string"
                                 : "expected string");
            continue;
        }
        result.push_back(value->str());
    }
    return result;
}

std::optional<std::uint32_t> positive_u32(
    const Object &object, const llvm::StringRef key, const std::string &path,
    ParseContext &context, const bool required) {
    const Value *raw = object.get(key);
    if (raw == nullptr) {
        if (required) context.error(path + '.' + key.str(), "missing member");
        return std::nullopt;
    }
    const auto value = raw->getAsInteger();
    if (!value || *value <= 0 ||
        static_cast<std::uint64_t>(*value) >
            static_cast<std::uint64_t>(UINT32_MAX)) {
        context.error(path + '.' + key.str(), "expected positive uint32");
        return std::nullopt;
    }
    return static_cast<std::uint32_t>(*value);
}

std::optional<SourceLocation> parse_location(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"file", "line", "column", "end_line", "end_column",
         "location_kind", "macro_stack"},
        path, context);
    const auto file = required_string(*object, "file", path, context);
    const auto line = positive_u32(*object, "line", path, context, true);
    const auto column = positive_u32(*object, "column", path, context, true);
    const auto location_kind =
        required_string(*object, "location_kind", path, context);
    if (!file || !line || !column || !location_kind) return std::nullopt;
    static const std::set<std::string> allowed_kinds{
        "spelling", "expansion", "presumed", "debug", "unknown"};
    if (!allowed_kinds.contains(*location_kind)) {
        context.error(path + ".location_kind", "unsupported location kind");
    }
    SourceLocation location;
    location.file = *file;
    location.line = *line;
    location.column = *column;
    if (object->get("end_line") != nullptr) {
        if (const auto value =
                positive_u32(*object, "end_line", path, context, false)) {
            location.end_line = *value;
        }
    }
    if (object->get("end_column") != nullptr) {
        if (const auto value =
                positive_u32(*object, "end_column", path, context, false)) {
            location.end_column = *value;
        }
    }
    location.location_kind = *location_kind;
    if (object->get("macro_stack") != nullptr) {
        if (auto values = string_array(
                object->getArray("macro_stack"), path + ".macro_stack",
                context, true)) {
            location.macro_stack = std::move(*values);
        }
    }
    return location;
}

std::optional<GapEffect> parse_effect(
    const std::optional<std::string> &text, const std::string &path,
    ParseContext &context) {
    if (!text) return std::nullopt;
    static const std::map<std::string, GapEffect> values{
        {"precision_loss", GapEffect::PrecisionLoss},
        {"soundness_risk", GapEffect::SoundnessRisk},
        {"stage_failure", GapEffect::StageFailure},
    };
    const auto found = values.find(*text);
    if (found == values.end()) {
        context.error(path, "unsupported gap effect");
        return std::nullopt;
    }
    return found->second;
}

std::optional<CoverageGap> parse_gap(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"construct_id", "kind", "effect", "detail", "locations",
         "affected_ids"},
        path, context);
    const auto id = required_string(*object, "construct_id", path, context);
    const auto kind = required_string(*object, "kind", path, context);
    const auto effect_text = required_string(*object, "effect", path, context);
    const auto detail = required_string(*object, "detail", path, context);
    const auto effect = parse_effect(effect_text, path + ".effect", context);
    const Array *locations = object->getArray("locations");
    if (locations == nullptr) context.error(path + ".locations", "expected array");
    if (!id || !kind || !effect || !detail || locations == nullptr) {
        return std::nullopt;
    }
    CoverageGap gap;
    gap.gap_id = *id;
    gap.kind = *kind;
    gap.effect = *effect;
    gap.detail = *detail;
    for (std::size_t i = 0; i < locations->size(); ++i) {
        if (auto location = parse_location(
                (*locations)[i].getAsObject(),
                path + ".locations[" + std::to_string(i) + ']', context)) {
            gap.locations.push_back(std::move(*location));
        }
    }
    if (object->get("affected_ids") != nullptr) {
        if (auto ids = string_array(
                object->getArray("affected_ids"), path + ".affected_ids",
                context, true)) {
            gap.affected_ids = std::move(*ids);
        }
    }
    return gap;
}

std::optional<ControllabilityVerdict> parse_controllability(
    const std::optional<std::string> &text, const std::string &path,
    ParseContext &context) {
    if (!text) return std::nullopt;
    static const std::map<std::string, ControllabilityVerdict> values{
        {"DIRECT", ControllabilityVerdict::Direct},
        {"SEQUENCE", ControllabilityVerdict::Sequence},
        {"TIMING", ControllabilityVerdict::Timing},
        {"ENVIRONMENT", ControllabilityVerdict::Environment},
        {"UNAVAILABLE", ControllabilityVerdict::Unavailable},
        {"UNKNOWN", ControllabilityVerdict::Unknown},
    };
    const auto found = values.find(*text);
    if (found == values.end()) {
        context.error(path, "unsupported controllability verdict");
        return std::nullopt;
    }
    return found->second;
}

std::optional<StageStatus> parse_status(
    const std::optional<std::string> &text, const std::string &path,
    ParseContext &context) {
    if (!text) return std::nullopt;
    static const std::map<std::string, StageStatus> values{
        {"COMPLETE", StageStatus::Complete},
        {"CONSERVATIVE_INCOMPLETE", StageStatus::ConservativeIncomplete},
        {"FAILED", StageStatus::Failed},
    };
    const auto found = values.find(*text);
    if (found == values.end()) {
        context.error(path, "unsupported stage status");
        return std::nullopt;
    }
    return found->second;
}

std::optional<ExecutorCapabilityEntry> parse_capability(
    const Object *object, const std::string &path, ParseContext &context) {
    if (object == nullptr) {
        context.error(path, "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"capability_id", "required_capability", "action_schema_id",
         "controllability", "evidence_note"},
        path, context);
    const auto id = required_string(*object, "capability_id", path, context);
    const auto required =
        required_string(*object, "required_capability", path, context);
    const auto controllability_text =
        required_string(*object, "controllability", path, context);
    const auto evidence =
        required_string(*object, "evidence_note", path, context);
    const auto controllability = parse_controllability(
        controllability_text, path + ".controllability", context);
    if (object->get("action_schema_id") == nullptr) {
        context.error(path + ".action_schema_id", "missing member");
    }
    std::optional<std::string> action_schema;
    if (const auto value = object->getString("action_schema_id")) {
        if (value->empty()) {
            context.error(
                path + ".action_schema_id", "expected non-empty string or null");
        } else {
            action_schema = value->str();
        }
    } else if (object->get("action_schema_id") != nullptr &&
               !object->get("action_schema_id")->getAsNull().has_value()) {
        context.error(
            path + ".action_schema_id", "expected non-empty string or null");
    }
    if (!id || !required || !controllability || !evidence) {
        return std::nullopt;
    }
    ExecutorCapabilityEntry entry;
    entry.capability_id = *id;
    entry.required_capability = *required;
    entry.action_schema_id = std::move(action_schema);
    entry.controllability = *controllability;
    entry.evidence_note = *evidence;
    return entry;
}

std::optional<ExecutorCapabilityManifest> parse_manifest(
    const Object *object, ParseContext &context) {
    if (object == nullptr) {
        context.error("$", "expected object");
        return std::nullopt;
    }
    reject_unknown_members(
        *object,
        {"schema_version", "artifact_id", "executor_id", "executor_version",
         "capabilities", "status", "unsupported_constructs", "diagnostics"},
        "$", context);
    const auto schema = required_string(*object, "schema_version", "$", context);
    const auto artifact = required_string(*object, "artifact_id", "$", context);
    const auto executor = required_string(*object, "executor_id", "$", context);
    const auto version = required_string(*object, "executor_version", "$", context);
    const auto status_text = required_string(*object, "status", "$", context);
    const auto status = parse_status(status_text, "$.status", context);
    const Array *capabilities = object->getArray("capabilities");
    const Array *gaps = object->getArray("unsupported_constructs");
    const auto diagnostics = string_array(
        object->getArray("diagnostics"), "$.diagnostics", context);
    if (capabilities == nullptr) {
        context.error("$.capabilities", "expected array");
    }
    if (gaps == nullptr) {
        context.error("$.unsupported_constructs", "expected array");
    }
    if (!schema || !artifact || !executor || !version || !status ||
        capabilities == nullptr || gaps == nullptr || !diagnostics) {
        return std::nullopt;
    }
    ExecutorCapabilityManifest manifest;
    manifest.schema_version = *schema;
    manifest.artifact_id = *artifact;
    manifest.executor_id = *executor;
    manifest.executor_version = *version;
    manifest.status = *status;
    manifest.diagnostics = *diagnostics;
    for (std::size_t i = 0; i < capabilities->size(); ++i) {
        if (auto entry = parse_capability(
                (*capabilities)[i].getAsObject(),
                "$.capabilities[" + std::to_string(i) + ']', context)) {
            manifest.capabilities.push_back(std::move(*entry));
        }
    }
    for (std::size_t i = 0; i < gaps->size(); ++i) {
        if (auto gap = parse_gap(
                (*gaps)[i].getAsObject(),
                "$.unsupported_constructs[" + std::to_string(i) + ']',
                context)) {
            manifest.coverage_gaps.push_back(std::move(*gap));
        }
    }
    return manifest;
}

std::string json_escape(const std::string_view value) {
    return llvm::formatv("{0}", Value(value)).str();
}

const char *status_string(const StageStatus status) {
    switch (status) {
    case StageStatus::Complete:
        return "COMPLETE";
    case StageStatus::ConservativeIncomplete:
        return "CONSERVATIVE_INCOMPLETE";
    case StageStatus::Failed:
        return "FAILED";
    }
    return "FAILED";
}

const char *effect_string(const GapEffect effect) {
    switch (effect) {
    case GapEffect::PrecisionLoss:
        return "precision_loss";
    case GapEffect::SoundnessRisk:
        return "soundness_risk";
    case GapEffect::StageFailure:
        return "stage_failure";
    }
    return "stage_failure";
}

void emit_strings(
    std::ostringstream &output, const std::vector<std::string> &values) {
    output << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0U) output << ',';
        output << json_escape(values[i]);
    }
    output << ']';
}

void emit_location(
    std::ostringstream &output, const SourceLocation &location) {
    output << "{\"file\":" << json_escape(location.file)
           << ",\"line\":" << location.line
           << ",\"column\":" << location.column;
    if (location.end_line != 0U) {
        output << ",\"end_line\":" << location.end_line;
    }
    if (location.end_column != 0U) {
        output << ",\"end_column\":" << location.end_column;
    }
    output << ",\"location_kind\":" << json_escape(location.location_kind);
    if (!location.macro_stack.empty()) {
        output << ",\"macro_stack\":";
        emit_strings(output, location.macro_stack);
    }
    output << '}';
}

void emit_gap(std::ostringstream &output, const CoverageGap &gap) {
    output << "{\"construct_id\":" << json_escape(gap.gap_id)
           << ",\"kind\":" << json_escape(gap.kind)
           << ",\"effect\":" << json_escape(effect_string(gap.effect))
           << ",\"detail\":" << json_escape(gap.detail)
           << ",\"locations\":[";
    for (std::size_t i = 0; i < gap.locations.size(); ++i) {
        if (i != 0U) output << ',';
        emit_location(output, gap.locations[i]);
    }
    output << ']';
    if (!gap.affected_ids.empty()) {
        output << ",\"affected_ids\":";
        emit_strings(output, gap.affected_ids);
    }
    output << '}';
}

}  // namespace

LoadResult<ExecutorCapabilityManifest> load_executor_capability_manifest(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256) {
    LoadResult<ExecutorCapabilityManifest> result;
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        result.diagnostics.push_back(
            "cannot open executor capability manifest: " + path.string());
        return result;
    }
    const std::string bytes{
        std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    result.observed_sha256 = sha256_hex(bytes);
    if (expected_sha256 && *expected_sha256 != result.observed_sha256) {
        result.diagnostics.push_back(
            "executor capability manifest SHA-256 mismatch: expected " +
            *expected_sha256 + ", observed " + result.observed_sha256);
        return result;
    }
    llvm::Expected<Value> parsed = llvm::json::parse(bytes);
    if (!parsed) {
        result.diagnostics.push_back(
            "invalid executor capability JSON: " +
            llvm::toString(parsed.takeError()));
        return result;
    }
    ParseContext context;
    auto manifest = parse_manifest(parsed->getAsObject(), context);
    if (manifest) {
        auto semantic_errors =
            validate_executor_capability_manifest(*manifest);
        context.errors.insert(
            context.errors.end(), semantic_errors.begin(), semantic_errors.end());
    }
    std::sort(context.errors.begin(), context.errors.end());
    context.errors.erase(
        std::unique(context.errors.begin(), context.errors.end()),
        context.errors.end());
    if (!manifest || !context.errors.empty()) {
        result.diagnostics = std::move(context.errors);
        return result;
    }
    result.status = manifest->status;
    result.coverage_gaps = manifest->coverage_gaps;
    result.value = std::move(*manifest);
    return result;
}

std::vector<std::string> validate_executor_capability_manifest(
    const ExecutorCapabilityManifest &manifest) {
    std::vector<std::string> errors;
    if (manifest.schema_version != "1.0.0") {
        errors.push_back("unsupported executor capability schema version");
    }
    if (!is_stable_id(manifest.artifact_id)) {
        errors.push_back("invalid executor capability artifact ID");
    }
    if (!is_stable_id(manifest.executor_id)) {
        errors.push_back("invalid executor ID");
    }
    if (!is_semver(manifest.executor_version)) {
        errors.push_back("invalid executor semantic version");
    }
    if (manifest.capabilities.empty()) {
        errors.push_back("executor capability manifest requires an entry");
    }
    std::set<std::string> ids;
    for (const ExecutorCapabilityEntry &entry : manifest.capabilities) {
        if (!is_stable_id(entry.capability_id) ||
            !ids.insert(entry.capability_id).second) {
            errors.push_back(
                "invalid or duplicate capability ID: " +
                entry.capability_id);
        }
        if (entry.required_capability.empty()) {
            errors.push_back(
                "empty required capability: " + entry.capability_id);
        }
        if (entry.action_schema_id &&
            !is_stable_id(*entry.action_schema_id)) {
            errors.push_back(
                "invalid action schema ID: " + *entry.action_schema_id);
        }
        if (entry.evidence_note.empty()) {
            errors.push_back(
                "empty capability evidence note: " + entry.capability_id);
        }
    }
    std::set<std::string> gap_ids;
    for (const CoverageGap &gap : manifest.coverage_gaps) {
        if (!is_stable_id(gap.gap_id) || !gap_ids.insert(gap.gap_id).second) {
            errors.push_back(
                "invalid or duplicate unsupported construct ID: " +
                gap.gap_id);
        }
        if (gap.kind.empty() || gap.detail.empty()) {
            errors.push_back(
                "unsupported construct requires kind and detail: " +
                gap.gap_id);
        }
        for (const SourceLocation &location : gap.locations) {
            if (location.file.empty() || location.line == 0U ||
                location.column == 0U) {
                errors.push_back(
                    "invalid unsupported construct location: " + gap.gap_id);
            }
        }
    }
    if (manifest.status == StageStatus::Complete &&
        std::any_of(
            manifest.coverage_gaps.begin(), manifest.coverage_gaps.end(),
            [](const CoverageGap &gap) {
                return gap.effect == GapEffect::StageFailure ||
                       gap.effect == GapEffect::SoundnessRisk;
            })) {
        errors.push_back(
            "COMPLETE executor manifest cannot retain soundness/stage gaps");
    }
    std::sort(errors.begin(), errors.end());
    errors.erase(std::unique(errors.begin(), errors.end()), errors.end());
    return errors;
}

std::string canonical_executor_capability_manifest_json(
    const ExecutorCapabilityManifest &manifest) {
    std::vector<const ExecutorCapabilityEntry *> capabilities;
    for (const auto &entry : manifest.capabilities) capabilities.push_back(&entry);
    std::sort(
        capabilities.begin(), capabilities.end(),
        [](const auto *left, const auto *right) {
            return std::tie(
                       left->capability_id, left->required_capability,
                       left->action_schema_id) <
                   std::tie(
                       right->capability_id, right->required_capability,
                       right->action_schema_id);
        });
    std::vector<const CoverageGap *> gaps;
    for (const auto &gap : manifest.coverage_gaps) gaps.push_back(&gap);
    std::sort(gaps.begin(), gaps.end(), [](const auto *left, const auto *right) {
        return left->gap_id < right->gap_id;
    });
    std::vector<std::string> diagnostics = manifest.diagnostics;
    std::sort(diagnostics.begin(), diagnostics.end());
    diagnostics.erase(
        std::unique(diagnostics.begin(), diagnostics.end()), diagnostics.end());

    std::ostringstream output;
    output << "{\"schema_version\":" << json_escape(manifest.schema_version)
           << ",\"artifact_id\":" << json_escape(manifest.artifact_id)
           << ",\"executor_id\":" << json_escape(manifest.executor_id)
           << ",\"executor_version\":"
           << json_escape(manifest.executor_version)
           << ",\"capabilities\":[";
    for (std::size_t i = 0; i < capabilities.size(); ++i) {
        if (i != 0U) output << ',';
        const ExecutorCapabilityEntry &entry = *capabilities[i];
        output << "{\"capability_id\":" << json_escape(entry.capability_id)
               << ",\"required_capability\":"
               << json_escape(entry.required_capability)
               << ",\"action_schema_id\":";
        if (entry.action_schema_id) {
            output << json_escape(*entry.action_schema_id);
        } else {
            output << "null";
        }
        output << ",\"controllability\":"
               << json_escape(to_string(entry.controllability))
               << ",\"evidence_note\":" << json_escape(entry.evidence_note)
               << '}';
    }
    output << "],\"status\":" << json_escape(status_string(manifest.status))
           << ",\"unsupported_constructs\":[";
    for (std::size_t i = 0; i < gaps.size(); ++i) {
        if (i != 0U) output << ',';
        emit_gap(output, *gaps[i]);
    }
    output << "],\"diagnostics\":";
    emit_strings(output, diagnostics);
    output << '}';
    return output.str();
}

}  // namespace rift::core
