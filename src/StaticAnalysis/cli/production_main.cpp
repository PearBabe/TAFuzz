#include "production_main.h"

#include "rift_build_manifest.h"
#include "rift/core/production.h"
#include "rift/core/sha256.h"

#include <clang/Basic/Version.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/raw_ostream.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

#if defined(__GLIBC__)
#include <malloc.h>
#endif

#if defined(__linux__)
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#endif

namespace rift::cli {
namespace {

namespace fs = std::filesystem;
namespace core = rift::core;

struct Options {
    std::string command;
    fs::path compile_database;
    fs::path property;
    fs::path output;
    fs::path output_directory;
    std::optional<fs::path> index_output;
    std::optional<fs::path> source_root;
    std::vector<core::LogicalPathRoot> logical_roots;
    std::vector<fs::path> model_packs;
    std::optional<fs::path> executor_capabilities;
    std::uint32_t call_string_limit = 1;
    std::uint64_t solver_timeout_ms = 100;
    std::uint64_t max_solver_queries = 10000;
    std::vector<std::string> argv;
};

[[noreturn]] void fail(std::string message) {
    throw std::runtime_error(std::move(message));
}

std::string file_sha256(const fs::path &path) {
    return core::sha256_file(path);
}

void append_u64(std::string &bytes, std::uint64_t value) {
    for (int shift = 56; shift >= 0; shift -= 8) {
        bytes.push_back(static_cast<char>((value >> shift) & 0xffU));
    }
}

void append_length_prefixed(std::string &bytes, std::string_view value) {
    append_u64(bytes, value.size());
    bytes.append(value);
}

std::string length_prefixed_material(
    std::initializer_list<std::string_view> values) {
    std::string material;
    for (const std::string_view value : values) {
        append_length_prefixed(material, value);
    }
    return material;
}

std::string encoded_json(llvm::json::Value value) {
    return llvm::formatv("{0:2}\n", std::move(value)).str();
}

std::string canonical_json_value(const llvm::json::Value &value);

std::string canonical_json_object(
    const llvm::json::Object &object,
    const std::set<std::string> &excluded_keys = {}) {
    std::vector<std::pair<std::string, const llvm::json::Value *>> members;
    for (const auto &member : object) {
        const std::string key = llvm::StringRef(member.first).str();
        if (!excluded_keys.contains(key)) {
            members.emplace_back(key, &member.second);
        }
    }
    std::sort(
        members.begin(), members.end(),
        [](const auto &left, const auto &right) {
            return left.first < right.first;
        });
    std::string result = "{";
    for (std::size_t index = 0; index < members.size(); ++index) {
        if (index != 0U) result.push_back(',');
        result += llvm::formatv("{0}", llvm::json::Value(members[index].first))
                      .str();
        result.push_back(':');
        result += canonical_json_value(*members[index].second);
    }
    result.push_back('}');
    return result;
}

std::string canonical_json_value(const llvm::json::Value &value) {
    if (value.kind() == llvm::json::Value::Object) {
        return canonical_json_object(*value.getAsObject());
    }
    if (value.kind() == llvm::json::Value::Array) {
        std::string result = "[";
        const llvm::json::Array &array = *value.getAsArray();
        for (std::size_t index = 0; index < array.size(); ++index) {
            if (index != 0U) result.push_back(',');
            result += canonical_json_value(array[index]);
        }
        result.push_back(']');
        return result;
    }
    return llvm::formatv("{0}", value).str();
}

void trim_released_heap() {
#if defined(__GLIBC__)
    (void)::malloc_trim(0);
#endif
}

void trace_resource_phase(std::string_view phase) {
#if defined(__linux__)
    const char *enabled = std::getenv("RIFT_RESOURCE_TRACE");
    if (enabled == nullptr || std::string_view(enabled) != "1") {
        return;
    }
    std::ifstream status_file("/proc/self/status");
    std::string line;
    std::string rss;
    std::string size;
    while (std::getline(status_file, line)) {
        if (line.starts_with("VmRSS:")) {
            rss = line.substr(6);
        } else if (line.starts_with("VmSize:")) {
            size = line.substr(7);
        }
    }
    std::cerr << "RIFT_RESOURCE phase=" << phase << " vm_rss=" << rss
              << " vm_size=" << size << '\n';
#else
    (void)phase;
#endif
}

void write_file_atomic(const fs::path &path, const std::string &payload) {
    if (path.empty()) {
        fail("output path is empty");
    }
    const fs::path parent = path.parent_path().empty() ? fs::path(".")
                                                        : path.parent_path();
    fs::create_directories(parent);
    const fs::path temporary = path.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) {
            fail("cannot write " + temporary.string());
        }
        output << payload;
        if (!output) {
            fail("failed while writing " + temporary.string());
        }
    }
    std::error_code error;
    fs::rename(temporary, path, error);
    if (error) {
        fs::remove(temporary);
        fail("cannot publish " + path.string() + ": " + error.message());
    }
}

class OutputBundleStager {
  public:
    explicit OutputBundleStager(fs::path output_directory)
        : output_directory_(std::move(output_directory)),
          staging_directory_(output_directory_ / ".rift-staging") {
        fs::create_directories(output_directory_);
        if (fs::exists(staging_directory_)) {
            fail("analysis staging directory already exists: " +
                 staging_directory_.string());
        }
        fs::create_directory(staging_directory_);
    }

    OutputBundleStager(const OutputBundleStager &) = delete;
    OutputBundleStager &operator=(const OutputBundleStager &) = delete;

    ~OutputBundleStager() {
        if (!published_) {
            std::error_code ignored;
            fs::remove_all(staging_directory_, ignored);
        }
    }

    fs::path allocate(const std::string &name) {
        if (name.empty() || fs::path(name).filename() != fs::path(name) ||
            std::find(names_.begin(), names_.end(), name) != names_.end()) {
            fail("invalid or duplicate staged artifact name: " + name);
        }
        const fs::path final_path = output_directory_ / name;
        if (fs::exists(final_path)) {
            fail("refusing to overwrite existing analysis artifact: " +
                 final_path.string());
        }
        names_.push_back(name);
        return staging_directory_ / name;
    }

    void write(const std::string &name, const std::string &payload) {
        write_file_atomic(allocate(name), payload);
    }

    void publish() {
        std::vector<fs::path> published;
        for (const std::string &name : names_) {
            const fs::path staged = staging_directory_ / name;
            const fs::path final_path = output_directory_ / name;
            std::error_code error;
            fs::rename(staged, final_path, error);
            if (error) {
                for (const fs::path &path : published) {
                    std::error_code ignored;
                    fs::remove(path, ignored);
                }
                fail("cannot publish analysis bundle: " + error.message());
            }
            published.push_back(final_path);
        }
        std::error_code error;
        fs::remove(staging_directory_, error);
        if (error) {
            for (const fs::path &path : published) {
                std::error_code ignored;
                fs::remove(path, ignored);
            }
            fail("cannot finalize analysis bundle: " + error.message());
        }
        published_ = true;
    }

  private:
    fs::path output_directory_;
    fs::path staging_directory_;
    std::vector<std::string> names_;
    bool published_ = false;
};

std::string nonempty(std::string value, std::string_view fallback) {
    return value.empty() ? std::string(fallback) : std::move(value);
}

llvm::json::Array string_array(const std::vector<std::string> &values) {
    llvm::json::Array result;
    for (const std::string &value : values) {
        result.push_back(value);
    }
    return result;
}

llvm::json::Array string_array(const std::set<std::string> &values) {
    llvm::json::Array result;
    for (const std::string &value : values) {
        result.push_back(value);
    }
    return result;
}

std::string status(core::StageStatus value) {
    switch (value) {
        case core::StageStatus::Complete:
            return "COMPLETE";
        case core::StageStatus::ConservativeIncomplete:
            return "CONSERVATIVE_INCOMPLETE";
        case core::StageStatus::Failed:
            return "FAILED";
    }
    return "FAILED";
}

std::string tu_status(core::StageStatus value) {
    switch (value) {
        case core::StageStatus::Complete:
            return "indexed";
        case core::StageStatus::ConservativeIncomplete:
            return "partial";
        case core::StageStatus::Failed:
            return "failed";
    }
    return "failed";
}

std::string certainty(core::Certainty value) {
    switch (value) {
        case core::Certainty::Must:
            return "must";
        case core::Certainty::May:
            return "may";
        case core::Certainty::Modelled:
            return "modelled";
        case core::Certainty::Unknown:
            return "unknown";
    }
    return "unknown";
}

std::string identity_status(core::IdentityStatus value) {
    switch (value) {
        case core::IdentityStatus::Exact:
            return "exact";
        case core::IdentityStatus::Summary:
            return "summary";
        case core::IdentityStatus::Unknown:
            return "unknown";
    }
    return "unknown";
}

std::string entity_kind(core::EntityKind value) {
    switch (value) {
        case core::EntityKind::Function: return "function";
        case core::EntityKind::Method: return "method";
        case core::EntityKind::Constructor: return "constructor";
        case core::EntityKind::Destructor: return "destructor";
        case core::EntityKind::Parameter: return "parameter";
        case core::EntityKind::Local: return "local";
        case core::EntityKind::Global: return "global";
        case core::EntityKind::Field: return "field";
        case core::EntityKind::Type: return "type";
        case core::EntityKind::Expression: return "expression";
        case core::EntityKind::Synthetic: return "synthetic";
        case core::EntityKind::Unknown: return "unknown";
    }
    return "unknown";
}

std::string value_kind(core::ValueKind value) {
    switch (value) {
        case core::ValueKind::Boolean: return "bool";
        case core::ValueKind::Integer: return "integer";
        case core::ValueKind::Floating: return "floating";
        case core::ValueKind::Enumeration: return "enum";
        case core::ValueKind::BitVector: return "bitvector";
        case core::ValueKind::Timestamp: return "timestamp";
        case core::ValueKind::Duration: return "duration";
        case core::ValueKind::Pointer: return "pointer";
        case core::ValueKind::Record: return "record";
        case core::ValueKind::Array: return "array";
        case core::ValueKind::Unknown: return "unknown";
    }
    return "unknown";
}

std::string semantic_node_kind(core::SemanticNodeKind value) {
    switch (value) {
        case core::SemanticNodeKind::Declaration: return "declaration";
        case core::SemanticNodeKind::Definition: return "definition";
        case core::SemanticNodeKind::Expression: return "expression";
        case core::SemanticNodeKind::Value: return "value";
        case core::SemanticNodeKind::Memory: return "memory";
        case core::SemanticNodeKind::CallSite: return "callsite";
        case core::SemanticNodeKind::ReturnSite: return "returnsite";
        case core::SemanticNodeKind::Control: return "control";
        case core::SemanticNodeKind::Synthetic: return "synthetic";
        case core::SemanticNodeKind::Unknown: return "unknown";
    }
    return "unknown";
}

std::string contextual_node_kind(core::SemanticNodeKind value) {
    switch (value) {
        case core::SemanticNodeKind::Memory: return "memory";
        case core::SemanticNodeKind::Control: return "predicate";
        case core::SemanticNodeKind::Unknown: return "unknown";
        default: return "value";
    }
}

std::string object_abstraction(core::ObjectAbstraction value) {
    switch (value) {
        case core::ObjectAbstraction::Value: return "value";
        case core::ObjectAbstraction::Global: return "global";
        case core::ObjectAbstraction::Stack: return "stack";
        case core::ObjectAbstraction::Heap: return "heap";
        case core::ObjectAbstraction::Receiver: return "receiver";
        case core::ObjectAbstraction::Summary: return "summary";
        case core::ObjectAbstraction::Unknown: return "unknown";
    }
    return "unknown";
}

std::string input_file_role(core::InputFileRole value) {
    switch (value) {
        case core::InputFileRole::Main: return "main";
        case core::InputFileRole::UserHeader: return "user_header";
        case core::InputFileRole::Generated: return "generated";
        case core::InputFileRole::System: return "system";
        case core::InputFileRole::Toolchain: return "toolchain";
    }
    fail("unhandled input-file role");
}

std::int64_t json_byte_size(std::uint64_t value) {
    if (value > static_cast<std::uint64_t>(
                    std::numeric_limits<std::int64_t>::max())) {
        fail("input file is too large for the JSON integer contract");
    }
    return static_cast<std::int64_t>(value);
}

std::string lifecycle(core::LifecyclePhase value) {
    switch (value) {
        case core::LifecyclePhase::Constructed: return "constructed";
        case core::LifecyclePhase::Initialized: return "initialized";
        case core::LifecyclePhase::Active: return "active";
        case core::LifecyclePhase::Committed: return "committed";
        case core::LifecyclePhase::Cancelled: return "cancelled";
        case core::LifecyclePhase::Destroyed: return "destroyed";
        case core::LifecyclePhase::Reused: return "reused";
        case core::LifecyclePhase::Unknown: return "unknown";
    }
    return "unknown";
}

std::string task_kind(core::TaskKind value) {
    switch (value) {
        case core::TaskKind::Thread: return "thread";
        case core::TaskKind::Task: return "task";
        case core::TaskKind::Interrupt: return "interrupt";
        case core::TaskKind::Callback: return "callback";
        case core::TaskKind::Scheduler: return "scheduler";
        case core::TaskKind::Process: return "process";
        case core::TaskKind::Unknown: return "unknown";
    }
    return "unknown";
}

std::string ap_role(core::ApRole value) {
    switch (value) {
        case core::ApRole::Trigger: return "trigger";
        case core::ApRole::Response: return "response";
        case core::ApRole::Cancel: return "cancel";
        case core::ApRole::State: return "state";
        case core::ApRole::Guard: return "guard";
        case core::ApRole::Bound: return "bound";
        case core::ApRole::Clock: return "clock";
        case core::ApRole::Scope: return "scope";
    }
    return "state";
}

llvm::json::Object location_json(const core::SourceLocation &input) {
    llvm::json::Object result{
        {"file", nonempty(input.file, "<unknown>")},
        {"line", static_cast<std::int64_t>(std::max(1U, input.line))},
        {"column", static_cast<std::int64_t>(std::max(1U, input.column))},
        {"location_kind", nonempty(input.location_kind, "unknown")},
    };
    if (input.end_line != 0) {
        result["end_line"] = static_cast<std::int64_t>(input.end_line);
    }
    if (input.end_column != 0) {
        result["end_column"] = static_cast<std::int64_t>(input.end_column);
    }
    if (!input.macro_stack.empty()) {
        result["macro_stack"] = string_array(input.macro_stack);
    }
    return result;
}

llvm::json::Object value_type_json(const core::ValueType &input) {
    llvm::json::Object result{
        {"kind", value_kind(input.kind)},
        {"canonical", nonempty(input.canonical, "unknown")},
    };
    if (input.bit_width.has_value()) {
        result["bit_width"] = static_cast<std::int64_t>(*input.bit_width);
    }
    if (input.is_signed.has_value()) {
        result["signed"] = *input.is_signed;
    }
    if (input.unit.has_value() && !input.unit->empty()) {
        result["unit"] = *input.unit;
    }
    return result;
}

llvm::json::Object entity_json(const core::EntityRef &input) {
    llvm::json::Object result{
        {"entity_id", input.entity_id},
        {"entity_kind", entity_kind(input.kind)},
        {"identity_status", identity_status(input.identity_status)},
        {"usr", input.usr.has_value() ? llvm::json::Value(*input.usr)
                                      : llvm::json::Value(nullptr)},
        {"qualified_signature",
         input.qualified_signature.has_value()
             ? llvm::json::Value(*input.qualified_signature)
             : llvm::json::Value(nullptr)},
        {"canonical_type",
         input.canonical_type.has_value()
             ? llvm::json::Value(*input.canonical_type)
             : llvm::json::Value(nullptr)},
    };
    return result;
}

std::string evidence_kind(std::string kind) {
    static const std::set<std::string> allowed{
        "usr_match", "qualified_signature_match", "source_location_match",
        "type_field_match", "expression_structure_match", "ast_semantics",
        "llvm_value_flow", "memoryssa", "alias_analysis",
        "control_dependence", "call_graph", "debug_mapping", "model_rule",
        "path_constraint", "temporal_role", "scope_match",
        "name_similarity", "llm_similarity", "unresolved",
    };
    return allowed.contains(kind) ? std::move(kind) : "unresolved";
}

llvm::json::Object evidence_json(const core::Evidence &input) {
    llvm::json::Object result{
        {"evidence_id", input.evidence_id},
        {"kind", evidence_kind(input.kind)},
        {"certainty", certainty(input.certainty)},
        {"fact", nonempty(input.fact, "fact unavailable")},
        {"producer", nonempty(input.producer, "rift-core")},
    };
    if (input.location.has_value()) {
        result["location"] = location_json(*input.location);
    }
    return result;
}

llvm::json::Object evidence_json(const core::BindingEvidence &input) {
    llvm::json::Object result{
        {"evidence_id", input.evidence_id},
        {"kind", evidence_kind(input.kind)},
        {"certainty", certainty(input.certainty)},
        {"fact", nonempty(input.fact, "fact unavailable")},
        {"producer", nonempty(input.producer, "rift-core")},
    };
    if (input.location.has_value()) {
        result["location"] = location_json(*input.location);
    }
    if (input.score.has_value()) {
        result["score"] = *input.score;
    }
    return result;
}

llvm::json::Array evidence_array(const std::vector<core::Evidence> &values) {
    llvm::json::Array result;
    for (const core::Evidence &value : values) {
        result.push_back(evidence_json(value));
    }
    return result;
}

std::string gap_effect(core::GapEffect value) {
    switch (value) {
        case core::GapEffect::PrecisionLoss: return "precision_loss";
        case core::GapEffect::SoundnessRisk: return "soundness_risk";
        case core::GapEffect::StageFailure: return "stage_failure";
    }
    return "precision_loss";
}

llvm::json::Object gap_json(const core::CoverageGap &gap) {
    llvm::json::Array locations;
    for (const core::SourceLocation &location : gap.locations) {
        locations.push_back(location_json(location));
    }
    return llvm::json::Object{
        {"construct_id", gap.gap_id},
        {"kind", nonempty(gap.kind, "unknown_construct")},
        {"effect", gap_effect(gap.effect)},
        {"detail", nonempty(gap.detail, "detail unavailable")},
        {"locations", std::move(locations)},
        {"affected_ids", string_array(gap.affected_ids)},
    };
}

llvm::json::Array gaps_json(const std::vector<core::CoverageGap> &values) {
    llvm::json::Array result;
    for (const core::CoverageGap &gap : values) {
        result.push_back(gap_json(gap));
    }
    return result;
}

llvm::json::Array locations_json(
    const std::vector<core::SourceLocation> &values) {
    llvm::json::Array result;
    for (const core::SourceLocation &value : values) {
        result.push_back(location_json(value));
    }
    return result;
}

llvm::json::Value nullable_id(const std::optional<std::string> &value) {
    if (!value.has_value() || value->empty()) {
        return nullptr;
    }
    return *value;
}

llvm::json::Value nullable_id(const std::string &value) {
    return value.empty() ? llvm::json::Value(nullptr)
                         : llvm::json::Value(value);
}

llvm::json::Object abstract_object_json(const core::AbstractObject &input) {
    return llvm::json::Object{
        {"object_id", input.object_id},
        {"abstraction", object_abstraction(input.abstraction)},
        {"allocation_site",
         input.allocation_site.has_value()
             ? llvm::json::Value(location_json(*input.allocation_site))
             : llvm::json::Value(nullptr)},
        {"certainty", certainty(input.certainty)},
    };
}

llvm::json::Value access_path_json(
    const std::optional<core::AccessPath> &input) {
    if (!input.has_value()) {
        return nullptr;
    }
    return llvm::json::Object{
        {"root_entity_id", input->root_entity_id},
        {"dereference_depth",
         static_cast<std::int64_t>(input->dereference_depth)},
        {"fields", string_array(input->fields)},
        {"unknown_suffix", input->unknown_suffix},
    };
}

llvm::json::Array nested_string_array(
    const std::vector<std::vector<std::string>> &values) {
    llvm::json::Array result;
    for (const std::vector<std::string> &value : values) {
        result.push_back(string_array(value));
    }
    return result;
}

llvm::json::Array bool_array(const std::vector<bool> &values) {
    llvm::json::Array result;
    for (const bool value : values) {
        result.push_back(value);
    }
    return result;
}

std::string semantic_relation_kind(core::RelationKind value) {
    switch (value) {
        case core::RelationKind::Defines: return "defines";
        case core::RelationKind::Uses: return "uses";
        case core::RelationKind::Loads: return "loads";
        case core::RelationKind::Stores: return "stores";
        case core::RelationKind::Data: return "data";
        case core::RelationKind::Control: return "controls";
        case core::RelationKind::Call: return "calls";
        case core::RelationKind::Return: return "returns";
        case core::RelationKind::Object: return "object";
        case core::RelationKind::Field: return "field";
        case core::RelationKind::Alias: return "aliases";
        case core::RelationKind::Contains: return "contains";
        case core::RelationKind::MapsTo: return "maps_to";
        case core::RelationKind::Unknown: return "unknown";
    }
    return "unknown";
}

std::string influence_edge_kind(core::RelationKind value) {
    switch (value) {
        case core::RelationKind::Defines:
        case core::RelationKind::Uses:
        case core::RelationKind::Data:
            return "value_flow";
        case core::RelationKind::Loads:
        case core::RelationKind::Stores:
        case core::RelationKind::Object:
        case core::RelationKind::Field:
            return "memory_flow";
        case core::RelationKind::Control: return "control";
        case core::RelationKind::Call: return "call";
        case core::RelationKind::Return: return "return";
        case core::RelationKind::Alias: return "alias";
        case core::RelationKind::Contains:
        case core::RelationKind::MapsTo:
        case core::RelationKind::Unknown:
            return "unknown";
    }
    return "unknown";
}

llvm::json::Array relation_evidence(
    const std::vector<core::Evidence> &values, std::string_view relation_id,
    core::Certainty relation_certainty) {
    if (!values.empty()) {
        return evidence_array(values);
    }
    core::Evidence fallback;
    fallback.evidence_id = core::stable_id(
        "evidence", std::string(relation_id) + ":missing");
    fallback.kind = "unresolved";
    fallback.certainty = relation_certainty;
    fallback.fact = "relation emitted without backend evidence";
    fallback.producer = "rift-cli";
    return llvm::json::Array{evidence_json(fallback)};
}

llvm::json::Object semantic_index_json(const core::SemanticIndex &index) {
    llvm::json::Array translation_units;
    for (const core::TranslationUnitRecord &unit : index.translation_units) {
        translation_units.push_back(llvm::json::Object{
            {"tu_id", unit.translation_unit_id},
            {"source_file", nonempty(unit.source_file, "<unknown>")},
            {"language", unit.language == "c++" ? "c++" : "c"},
            {"working_directory",
             nonempty(unit.working_directory, "<unknown>")},
            {"command_sha256", unit.command_sha256},
            {"status", tu_status(unit.status)},
            {"input_file_ids", string_array(unit.input_file_ids)},
            {"diagnostics", string_array(unit.diagnostics)},
        });
    }

    llvm::json::Array input_files;
    for (const core::InputFileDigest &input : index.input_files) {
        input_files.push_back(llvm::json::Object{
            {"input_file_id", input.input_file_id},
            {"logical_path", input.logical_path},
            {"sha256", input.sha256},
            {"role", input_file_role(input.role)},
            {"byte_size", json_byte_size(input.byte_size)},
        });
    }

    llvm::json::Array entities;
    for (const core::EntityRef &entity : index.entities) {
        entities.push_back(llvm::json::Object{
            {"entity", entity_json(entity)},
            {"declarations", locations_json(entity.declarations)},
            {"definitions", locations_json(entity.definitions)},
            {"translation_unit_refs",
             string_array(entity.translation_unit_ids)},
        });
    }

    llvm::json::Array abstract_objects;
    for (const core::AbstractObject &object : index.abstract_objects) {
        abstract_objects.push_back(abstract_object_json(object));
    }

    llvm::json::Array nodes;
    for (const core::SemanticNode &node : index.nodes) {
        nodes.push_back(llvm::json::Object{
            {"node_id", node.node_id},
            {"node_kind", semantic_node_kind(node.kind)},
            {"entity_ref", node.entity_id},
            {"owner_function_id", nullable_id(node.owner_function_id)},
            {"access_path", access_path_json(node.access_path)},
            {"abstract_object_id", nullable_id(node.abstract_object_id)},
            {"value_type", value_type_json(node.value_type)},
            {"location", location_json(node.location)},
            {"ast_kind", node.ast_kind},
        });
    }

    llvm::json::Array relations;
    for (const core::SemanticRelation &relation : index.relations) {
        relations.push_back(llvm::json::Object{
            {"relation_id", relation.relation_id},
            {"source_node_id", relation.source_node_id},
            {"target_node_id", relation.target_node_id},
            {"kind", semantic_relation_kind(relation.kind)},
            {"certainty", certainty(relation.certainty)},
            {"evidence", relation_evidence(
                             relation.evidence, relation.relation_id,
                             relation.certainty)},
            {"callsite_id", nullable_id(relation.callsite_id)},
            {"condition_node_ids",
             string_array(relation.condition_node_ids)},
            {"uncertainty_reasons",
             string_array(relation.uncertainty_reasons)},
        });
    }

    llvm::json::Array function_summaries;
    for (const core::FunctionSummary &summary : index.function_summaries) {
        function_summaries.push_back(llvm::json::Object{
            {"function_entity_id", summary.function_entity_id},
            {"parameter_node_ids", string_array(summary.parameter_node_ids)},
            {"receiver_node_id", nullable_id(summary.receiver_node_id)},
            {"return_node_id", nullable_id(summary.return_node_id)},
            {"owned_node_ids", string_array(summary.owned_node_ids)},
            {"relation_ids", string_array(summary.relation_ids)},
            {"callsite_ids", string_array(summary.callsite_ids)},
            {"status", status(summary.status)},
            {"uncertainty_reasons",
             string_array(summary.uncertainty_reasons)},
        });
    }

    llvm::json::Array callsites;
    for (const core::CallSiteSummary &callsite : index.callsites) {
        callsites.push_back(llvm::json::Object{
            {"callsite_id", callsite.callsite_id},
            {"caller_function_id", callsite.caller_function_id},
            {"candidate_callee_ids",
             string_array(callsite.candidate_callee_ids)},
            {"argument_node_ids", string_array(callsite.argument_node_ids)},
            {"argument_node_groups",
             nested_string_array(callsite.argument_node_groups)},
            {"argument_is_address", bool_array(callsite.argument_is_address)},
            {"receiver_node_id", nullable_id(callsite.receiver_node_id)},
            {"result_node_id", nullable_id(callsite.result_node_id)},
            {"location", location_json(callsite.location)},
            {"direct", callsite.direct},
            {"status", status(callsite.status)},
            {"uncertainty_reasons",
             string_array(callsite.uncertainty_reasons)},
        });
    }

    return llvm::json::Object{
        {"schema_version", "2.0.0"},
        {"artifact_id", index.artifact_id},
        {"identity_scheme", index.identity_scheme},
        {"canonical_compilation_database_sha256",
         index.canonical_compilation_database_sha256},
        {"path_map_sha256", index.path_map_sha256},
        {"input_manifest_sha256", index.input_manifest_sha256},
        {"logical_root_ids", string_array(index.logical_root_ids)},
        {"source_identity_root", index.source_identity_root},
        {"translation_units", std::move(translation_units)},
        {"input_files", std::move(input_files)},
        {"entities", std::move(entities)},
        {"abstract_objects", std::move(abstract_objects)},
        {"semantic_nodes", std::move(nodes)},
        {"semantic_relations", std::move(relations)},
        {"function_summaries", std::move(function_summaries)},
        {"callsites", std::move(callsites)},
        {"status", status(index.status)},
        {"diagnostics", string_array(index.diagnostics)},
        {"unsupported_constructs", gaps_json(index.coverage_gaps)},
    };
}

std::string binding_resolution(core::BindingResolution value) {
    switch (value) {
        case core::BindingResolution::Confirmed: return "CONFIRMED";
        case core::BindingResolution::Partial: return "PARTIAL";
        case core::BindingResolution::Ambiguous: return "AMBIGUOUS";
        case core::BindingResolution::Unresolved: return "UNRESOLVED";
        case core::BindingResolution::Failed: return "FAILED";
    }
    return "FAILED";
}

std::string candidate_status(core::CandidateStatus value) {
    switch (value) {
        case core::CandidateStatus::Candidate: return "CANDIDATE";
        case core::CandidateStatus::Confirmed: return "CONFIRMED";
        case core::CandidateStatus::Rejected: return "REJECTED";
        case core::CandidateStatus::Unresolved: return "UNRESOLVED";
    }
    return "UNRESOLVED";
}

llvm::json::Object bindings_json(const core::ApBindings &bindings) {
    llvm::json::Array role_bindings;
    for (const core::ApRoleBinding &binding : bindings.bindings) {
        llvm::json::Array candidates;
        for (const core::BindingCandidate &candidate : binding.candidates) {
            llvm::json::Array evidence;
            for (const core::BindingEvidence &item : candidate.evidence) {
                evidence.push_back(evidence_json(item));
            }
            llvm::json::Object candidate_object{
                {"binding_id", candidate.binding_id},
                {"status", candidate_status(candidate.status)},
                {"selector_refs", string_array(candidate.selector_ids)},
                {"semantic_node_refs",
                 string_array(candidate.semantic_node_ids)},
                {"evidence", std::move(evidence)},
                {"confidence", candidate.confidence},
                {"uncertainty_reasons",
                 string_array(candidate.uncertainty_reasons)},
            };
            if (candidate.selector_group_id) {
                candidate_object["selector_group_id"] =
                    *candidate.selector_group_id;
            }
            candidates.push_back(std::move(candidate_object));
        }
        role_bindings.push_back(llvm::json::Object{
            {"ap_id", binding.ap_id},
            {"role", ap_role(binding.role)},
            {"resolution", binding_resolution(binding.resolution)},
            {"candidates", std::move(candidates)},
        });
    }
    llvm::json::Object policy;
    if (bindings.schema_version == "1.0.0") {
        policy["joint_role_binding"] = true;
        policy["similarity_is_confirmation"] = false;
    } else {
        policy["role_selector_logic"] = "role-dnf/1";
        policy["cross_role_consistency"] = "NOT_EVALUATED";
        policy["similarity_is_confirmation"] = false;
    }
    return llvm::json::Object{
        {"schema_version", bindings.schema_version},
        {"artifact_id", bindings.artifact_id},
        {"property_ir_sha256", bindings.property_ir_sha256},
        {"semantic_index_sha256", bindings.semantic_index_sha256},
        {"binding_policy", std::move(policy)},
        {"bindings", std::move(role_bindings)},
        {"unsupported_constructs", gaps_json(bindings.coverage_gaps)},
    };
}

std::string scope_id(const core::ContextualNode &node) {
    if (!node.scope.scope_id.empty()) {
        return node.scope.scope_id;
    }
    return core::stable_id("scope", node.node_id + ":unknown");
}

std::string object_id(const core::ContextualNode &node) {
    if (!node.abstract_object.object_id.empty()) {
        return node.abstract_object.object_id;
    }
    return core::stable_id("object", node.node_id + ":unknown");
}

llvm::json::Object expression_reference(std::string node_id) {
    return llvm::json::Object{
        {"node_kind", "reference"},
        {"operator", nullptr},
        {"value_type",
         llvm::json::Object{{"kind", "unknown"},
                            {"canonical", "unknown"}}},
        {"referenced_selector_id", std::move(node_id)},
        {"operands", llvm::json::Array{}},
    };
}

llvm::json::Object contextual_node_json(const core::ContextualNode &node) {
    llvm::json::Array evidence;
    for (const core::Evidence &item : node.evidence) {
        evidence.push_back(evidence_json(item));
    }
    llvm::json::Object abstract_object =
        abstract_object_json(node.abstract_object);
    if (node.abstract_object.object_id.empty()) {
        abstract_object["object_id"] = object_id(node);
    }
    llvm::json::Object call_context{
        {"policy", node.call_context.callsite_ids.empty()
                       ? "root"
                       : "call_string"},
        {"callsite_ids", string_array(node.call_context.callsite_ids)},
        {"truncated", node.call_context.truncated},
    };
    llvm::json::Object task_context{
        {"kind", task_kind(node.task_context.kind)},
        {"context_id",
         node.task_context.context_id.has_value()
             ? llvm::json::Value(*node.task_context.context_id)
             : llvm::json::Value(nullptr)},
        {"certainty", certainty(node.task_context.certainty)},
    };
    llvm::json::Object scope{
        {"scope_id", scope_id(node)},
        {"key_node_ids", string_array(node.scope.key_node_ids)},
        {"status", identity_status(node.scope.status)},
    };
    llvm::json::Object generation{
        {"kind", identity_status(node.generation.kind)},
        {"identity",
         node.generation.identity.has_value()
             ? llvm::json::Value(*node.generation.identity)
             : llvm::json::Value(nullptr)},
        {"reuse_possible", node.generation.reuse_possible},
    };
    return llvm::json::Object{
        {"node_id", node.node_id},
        {"semantic_node_ref", node.semantic_node_id},
        {"node_kind", contextual_node_kind(node.kind)},
        {"semantic_node_kind", semantic_node_kind(node.kind)},
        {"entity", entity_json(*node.entity)},
        {"abstract_object", std::move(abstract_object)},
        {"field_path", string_array(node.field_path)},
        {"call_context", std::move(call_context)},
        {"lifecycle_phase", lifecycle(node.lifecycle_phase)},
        {"task_context", std::move(task_context)},
        {"scope", std::move(scope)},
        {"generation", std::move(generation)},
        {"location", location_json(node.location)},
        {"value_type", value_type_json(node.value_type)},
        {"evidence", std::move(evidence)},
    };
}

llvm::json::Object contextual_edge_json(const core::InfluenceEdge &edge) {
    const std::vector<core::Evidence> empty_evidence;
    llvm::json::Array conditions;
    for (const std::string &condition : edge.condition_node_ids) {
        conditions.push_back(expression_reference(condition));
    }
    std::vector<std::string> uncertainty = edge.uncertainty_reasons;
    if (edge.certainty == core::Certainty::Unknown && uncertainty.empty()) {
        uncertainty.push_back("backend did not classify edge certainty");
    }
    return llvm::json::Object{
        {"edge_id", edge.edge_id},
        {"source_node_id", edge.source_node_id},
        {"target_node_id", edge.target_node_id},
        {"kind", influence_edge_kind(edge.kind)},
        {"relation_kind", semantic_relation_kind(edge.kind)},
        {"certainty", certainty(edge.certainty)},
        {"evidence", relation_evidence(
                         edge.evidence ? *edge.evidence : empty_evidence,
                         edge.edge_id, edge.certainty)},
        {"condition_node_ids", string_array(edge.condition_node_ids)},
        {"conditions", std::move(conditions)},
        {"uncertainty_reasons", string_array(uncertainty)},
    };
}

void write_contextual_graph_stream(
    const core::ContextualInfluenceGraph &graph, const fs::path &path) {
    std::error_code error;
    llvm::raw_fd_ostream output(path.string(), error);
    if (error) {
        fail("cannot write " + path.string() + ": " + error.message());
    }
    {
        llvm::json::OStream json(output, 2);
        json.object([&] {
            json.attribute("artifact_id", graph.artifact_id);
            json.attribute(
                "context_policy",
                llvm::json::Object{
                    {"call_string_limit",
                     static_cast<std::int64_t>(graph.call_string_limit)},
                    {"object_sensitivity", graph.object_sensitivity},
                    {"field_sensitivity", graph.field_sensitivity},
                    {"unknowns_are_explicit", true},
                });
            json.attribute("diagnostics", string_array(graph.diagnostics));
            json.attributeArray("edges", [&] {
                for (const core::InfluenceEdge &edge : graph.edges) {
                    json.value(contextual_edge_json(edge));
                }
            });
            json.attributeArray("nodes", [&] {
                for (const core::ContextualNode &node : graph.nodes) {
                    json.value(contextual_node_json(node));
                }
            });
            json.attribute("schema_version", "2.0.0");
            json.attribute(
                "semantic_index_sha256", graph.semantic_index_sha256);
            json.attribute("status", status(graph.status));
            json.attributeArray("unsupported_constructs", [&] {
                for (const core::CoverageGap &gap : graph.coverage_gaps) {
                    json.value(gap_json(gap));
                }
            });
        });
    }
    output << '\n';
    output.flush();
    if (output.has_error()) {
        fail("failed while writing " + path.string());
    }
}

std::string cone_membership(core::ConeMembership value) {
    switch (value) {
        case core::ConeMembership::MustInfluence: return "MUST_INFLUENCE";
        case core::ConeMembership::MayInfluence: return "MAY_INFLUENCE";
        case core::ConeMembership::ModelledInfluence:
            return "MODELLED_INFLUENCE";
        case core::ConeMembership::UnknownInfluence:
            return "UNKNOWN_INFLUENCE";
    }
    return "UNKNOWN_INFLUENCE";
}

std::string candidate_disposition(core::CandidateDisposition value) {
    switch (value) {
        case core::CandidateDisposition::Included: return "INCLUDED";
        case core::CandidateDisposition::Unreachable: return "UNREACHABLE";
        case core::CandidateDisposition::Unresolved: return "UNRESOLVED";
        case core::CandidateDisposition::Rejected: return "REJECTED";
    }
    return "UNRESOLVED";
}

llvm::json::Object candidate_account_json(
    const core::CandidateAccount &account) {
    std::vector<std::string> uncertainty = account.uncertainty_reasons;
    if ((account.disposition == core::CandidateDisposition::Unreachable ||
         account.disposition == core::CandidateDisposition::Unresolved) &&
        uncertainty.empty()) {
        uncertainty.push_back("candidate was not resolved into cone");
    }
    return llvm::json::Object{
        {"binding_id", account.binding_id},
        {"disposition", candidate_disposition(account.disposition)},
        {"root_node_ids", string_array(account.root_node_ids)},
        {"uncertainty_reasons", string_array(uncertainty)},
    };
}

llvm::json::Object cone_member_json(const core::ConeMember &member) {
    std::vector<std::string> uncertainty = member.uncertainty_reasons;
    if (member.membership == core::ConeMembership::UnknownInfluence &&
        uncertainty.empty()) {
        uncertainty.push_back("membership certainty is unknown");
    }
    return llvm::json::Object{
        {"node_id", member.node_id},
        {"membership", cone_membership(member.membership)},
        {"witness_edge_ids", string_array(member.witness_edge_ids)},
        {"uncertainty_reasons", string_array(uncertainty)},
    };
}

void write_influence_cones_stream(
    const core::ApInfluenceCones &cones, const fs::path &path) {
    std::error_code error;
    llvm::raw_fd_ostream output(path.string(), error);
    if (error) {
        fail("cannot write " + path.string() + ": " + error.message());
    }
    {
        llvm::json::OStream json(output, 2);
        json.object([&] {
            json.attribute(
                "ap_bindings_sha256", cones.ap_bindings_sha256);
            json.attribute("artifact_id", cones.artifact_id);
            json.attribute(
                "candidate_accounting_complete",
                cones.candidate_accounting_complete);
            json.attributeArray("cones", [&] {
                for (const core::ApInfluenceCone &cone : cones.cones) {
                    std::vector<std::string> uncertainty =
                        cone.uncertainty_reasons;
                    if (cone.status != core::StageStatus::Complete &&
                        uncertainty.empty()) {
                        uncertainty.push_back("cone is not complete");
                    }
                    json.object([&] {
                        json.attribute("ap_id", cone.ap_id);
                        json.attributeArray("candidate_accounting", [&] {
                            for (const core::CandidateAccount &account :
                                 cone.candidate_accounting) {
                                json.value(candidate_account_json(account));
                            }
                        });
                        json.attribute("cone_id", cone.cone_id);
                        json.attributeArray("edge_ids", [&] {
                            for (const std::string &edge : cone.edge_ids) {
                                json.value(edge);
                            }
                        });
                        json.attributeArray("members", [&] {
                            for (const core::ConeMember &member :
                                 cone.members) {
                                json.value(cone_member_json(member));
                            }
                        });
                        json.attributeArray("roles", [&] {
                            for (const core::ApRole role : cone.roles) {
                                json.value(ap_role(role));
                            }
                        });
                        json.attribute("status", status(cone.status));
                        json.attribute(
                            "uncertainty_reasons",
                            string_array(uncertainty));
                    });
                }
            });
            json.attribute("graph_sha256", cones.graph_sha256);
            json.attribute(
                "ranking_never_prunes", cones.ranking_never_prunes);
            json.attribute("schema_version", "1.0.0");
            json.attributeArray("unsupported_constructs", [&] {
                for (const core::CoverageGap &gap : cones.coverage_gaps) {
                    json.value(gap_json(gap));
                }
            });
        });
    }
    output << '\n';
    output.flush();
    if (output.has_error()) {
        fail("failed while writing " + path.string());
    }
}

std::string utc_timestamp() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t seconds = std::chrono::system_clock::to_time_t(now);
    std::tm value{};
#if defined(_WIN32)
    gmtime_s(&value, &seconds);
#else
    gmtime_r(&seconds, &value);
#endif
    std::ostringstream output;
    output << std::put_time(&value, "%Y-%m-%dT%H:%M:%SZ");
    return output.str();
}

fs::path executable_path(char *argument_zero) {
    std::error_code error;
    const fs::path proc = fs::read_symlink("/proc/self/exe", error);
    if (!error && fs::is_regular_file(proc)) {
        return fs::canonical(proc);
    }
    const fs::path supplied(argument_zero == nullptr ? "" : argument_zero);
    if (!supplied.empty() && fs::is_regular_file(supplied)) {
        return fs::canonical(supplied);
    }
    fail("cannot resolve analyzer executable path");
}

struct EnvironmentCapture {
    std::string digest;
    llvm::json::Array variables;
};

constexpr std::array<std::string_view, 16> kSemanticEnvironmentVariables{
    "CL",
    "COMPILER_PATH",
    "CPATH",
    "CPLUS_INCLUDE_PATH",
    "C_INCLUDE_PATH",
    "GCC_EXEC_PREFIX",
    "INCLUDE",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "MACOSX_DEPLOYMENT_TARGET",
    "OBJC_INCLUDE_PATH",
    "PATH",
    "SDKROOT",
    "SOURCE_DATE_EPOCH",
    "_CL_",
};

EnvironmentCapture capture_semantic_environment() {
    // Values are intentionally never serialized.  The fixed whitelist covers
    // process environment settings that can change Clang language/include
    // semantics; unrelated and potentially secret variables are not read.
    std::string material;
    llvm::json::Array variables;
    for (const std::string_view name : kSemanticEnvironmentVariables) {
        const std::string name_string(name);
        const char *const raw_value = std::getenv(name_string.c_str());
        const bool present = raw_value != nullptr;
        const std::string value_digest =
            present ? core::sha256_hex(std::string(raw_value)) : std::string();
        append_length_prefixed(material, name);
        material.push_back(present ? '\x01' : '\x00');
        append_length_prefixed(material, value_digest);

        llvm::json::Object record{
            {"name", name_string},
            {"present", present},
        };
        record["value_sha256"] =
            present ? llvm::json::Value(value_digest)
                    : llvm::json::Value(nullptr);
        variables.push_back(std::move(record));
    }
    return {core::sha256_hex(material), std::move(variables)};
}

#if defined(__linux__)
struct MappedRuntimeFile {
    fs::path path;
    bool executable_mapping = false;
    bool analyzer = false;
    std::uint64_t device_major = 0;
    std::uint64_t device_minor = 0;
    std::uint64_t inode = 0;
};

using RuntimeFileKey =
    std::tuple<std::uint64_t, std::uint64_t, std::uint64_t>;

std::uint64_t parse_unsigned(
    const std::string &text, int base, std::string_view description) {
    std::size_t consumed = 0;
    unsigned long long value = 0;
    try {
        value = std::stoull(text, &consumed, base);
    } catch (const std::exception &) {
        fail("invalid " + std::string(description) + " in /proc/self/maps");
    }
    if (consumed != text.size()) {
        fail("invalid " + std::string(description) + " in /proc/self/maps");
    }
    return static_cast<std::uint64_t>(value);
}

std::pair<std::uint64_t, std::uint64_t> parse_device(
    const std::string &text) {
    const std::size_t separator = text.find(':');
    if (separator == std::string::npos || separator == 0 ||
        separator + 1 == text.size()) {
        fail("invalid device identity in /proc/self/maps");
    }
    return {
        parse_unsigned(text.substr(0, separator), 16, "device major"),
        parse_unsigned(text.substr(separator + 1), 16, "device minor"),
    };
}

std::string decode_proc_maps_path(std::string value) {
    std::string result;
    result.reserve(value.size());
    for (std::size_t index = 0; index < value.size();) {
        if (value[index] == '\\' && index + 3 < value.size() &&
            value[index + 1] >= '0' && value[index + 1] <= '7' &&
            value[index + 2] >= '0' && value[index + 2] <= '7' &&
            value[index + 3] >= '0' && value[index + 3] <= '7') {
            const unsigned decoded =
                static_cast<unsigned>(value[index + 1] - '0') * 64U +
                static_cast<unsigned>(value[index + 2] - '0') * 8U +
                static_cast<unsigned>(value[index + 3] - '0');
            result.push_back(static_cast<char>(decoded));
            index += 4;
            continue;
        }
        result.push_back(value[index]);
        ++index;
    }
    return result;
}

RuntimeFileKey checked_file_key(
    const fs::path &path, std::uint64_t expected_major,
    std::uint64_t expected_minor, std::uint64_t expected_inode) {
    struct stat metadata {};
    if (::stat(path.c_str(), &metadata) != 0) {
        fail("cannot stat mapped runtime object " + path.string() + ": " +
             std::strerror(errno));
    }
    const RuntimeFileKey actual{
        static_cast<std::uint64_t>(major(metadata.st_dev)),
        static_cast<std::uint64_t>(minor(metadata.st_dev)),
        static_cast<std::uint64_t>(metadata.st_ino),
    };
    const RuntimeFileKey expected{
        expected_major, expected_minor, expected_inode};
    if (actual != expected) {
        fail("mapped runtime object was replaced before attestation: " +
             path.string());
    }
    if (!S_ISREG(metadata.st_mode)) {
        fail("mapped runtime object is not a regular file: " + path.string());
    }
    return actual;
}

std::string checked_mapped_file_sha256(const MappedRuntimeFile &file) {
    const int descriptor =
        ::open(file.path.c_str(), O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        fail("cannot open mapped runtime object " + file.path.string() +
             ": " + std::strerror(errno));
    }
    struct DescriptorGuard {
        int value;
        ~DescriptorGuard() { ::close(value); }
    } guard{descriptor};

    struct stat before {};
    if (::fstat(descriptor, &before) != 0) {
        fail("cannot inspect mapped runtime object " + file.path.string() +
             ": " + std::strerror(errno));
    }
    const RuntimeFileKey expected{
        file.device_major, file.device_minor, file.inode};
    const RuntimeFileKey actual{
        static_cast<std::uint64_t>(major(before.st_dev)),
        static_cast<std::uint64_t>(minor(before.st_dev)),
        static_cast<std::uint64_t>(before.st_ino),
    };
    if (actual != expected || !S_ISREG(before.st_mode)) {
        fail("mapped runtime object identity changed before hashing: " +
             file.path.string());
    }

    core::Sha256 hasher;
    std::array<char, 1024 * 1024> buffer{};
    while (true) {
        const ssize_t count = ::read(descriptor, buffer.data(), buffer.size());
        if (count == 0) {
            break;
        }
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            fail("failed while hashing mapped runtime object " +
                 file.path.string() + ": " + std::strerror(errno));
        }
        hasher.update(buffer.data(), static_cast<std::size_t>(count));
    }

    struct stat after {};
    if (::fstat(descriptor, &after) != 0 ||
        before.st_dev != after.st_dev || before.st_ino != after.st_ino ||
        before.st_size != after.st_size ||
        before.st_mtim.tv_sec != after.st_mtim.tv_sec ||
        before.st_mtim.tv_nsec != after.st_mtim.tv_nsec ||
        before.st_ctim.tv_sec != after.st_ctim.tv_sec ||
        before.st_ctim.tv_nsec != after.st_ctim.tv_nsec) {
        fail("mapped runtime object changed while hashing: " +
             file.path.string());
    }

    return core::sha256_digest_hex(hasher.final());
}

struct PathSnapshot {
    std::string digest;
    std::uint64_t byte_size = 0;
};

PathSnapshot snapshot_regular_file(const fs::path &path) {
    struct stat path_before {};
    if (::stat(path.c_str(), &path_before) != 0) {
        fail("cannot stat source input " + path.string() + ": " +
             std::strerror(errno));
    }
    if (!S_ISREG(path_before.st_mode)) {
        fail("source input is not a regular file: " + path.string());
    }
    const int descriptor = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (descriptor < 0) {
        fail("cannot open source input " + path.string() + ": " +
             std::strerror(errno));
    }
    struct DescriptorGuard {
        int value;
        ~DescriptorGuard() { ::close(value); }
    } guard{descriptor};

    struct stat opened_before {};
    if (::fstat(descriptor, &opened_before) != 0 ||
        path_before.st_dev != opened_before.st_dev ||
        path_before.st_ino != opened_before.st_ino) {
        fail("source input path changed before rehash: " + path.string());
    }

    core::Sha256 hasher;
    std::array<char, 1024 * 1024> buffer{};
    std::uint64_t byte_size = 0;
    while (true) {
        const ssize_t count = ::read(descriptor, buffer.data(), buffer.size());
        if (count == 0) {
            break;
        }
        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            fail("failed while rehashing source input " + path.string() +
                 ": " + std::strerror(errno));
        }
        const std::uint64_t unsigned_count =
            static_cast<std::uint64_t>(count);
        if (byte_size >
            std::numeric_limits<std::uint64_t>::max() - unsigned_count) {
            fail("source input byte count overflow: " + path.string());
        }
        byte_size += unsigned_count;
        hasher.update(buffer.data(), static_cast<std::size_t>(count));
    }

    struct stat opened_after {};
    struct stat path_after {};
    if (::fstat(descriptor, &opened_after) != 0 ||
        ::stat(path.c_str(), &path_after) != 0 ||
        opened_before.st_dev != opened_after.st_dev ||
        opened_before.st_ino != opened_after.st_ino ||
        opened_before.st_size != opened_after.st_size ||
        opened_before.st_mtim.tv_sec != opened_after.st_mtim.tv_sec ||
        opened_before.st_mtim.tv_nsec != opened_after.st_mtim.tv_nsec ||
        opened_before.st_ctim.tv_sec != opened_after.st_ctim.tv_sec ||
        opened_before.st_ctim.tv_nsec != opened_after.st_ctim.tv_nsec ||
        opened_after.st_dev != path_after.st_dev ||
        opened_after.st_ino != path_after.st_ino) {
        fail("source input changed during certificate rehash: " +
             path.string());
    }

    return {core::sha256_digest_hex(hasher.final()), byte_size};
}

bool looks_like_shared_object(const fs::path &path) {
    const std::string filename = path.filename().string();
    return filename.find(".so") != std::string::npos ||
           filename.ends_with(".dylib") || filename.ends_with(".dll");
}
#endif

llvm::json::Array runtime_toolchain_json(const fs::path &binary) {
    // Bind the certificate to the bytes actually mapped into this process.
    // Linux device/inode identities are checked both before and while hashing,
    // so replacing a pathname cannot silently attest different bytes.
#if !defined(__linux__)
    (void)binary;
    fail("runtime toolchain attestation requires Linux /proc/self/maps");
#else
    std::ifstream maps("/proc/self/maps");
    if (!maps) {
        fail("cannot open /proc/self/maps for runtime attestation");
    }

    std::map<RuntimeFileKey, MappedRuntimeFile> mapped_files;
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string address;
        std::string permissions;
        std::string offset;
        std::string device;
        std::string inode_text;
        if (!(row >> address >> permissions >> offset >> device >> inode_text)) {
            fail("malformed entry in /proc/self/maps");
        }
        std::string raw_path;
        std::getline(row, raw_path);
        const std::size_t first = raw_path.find_first_not_of(' ');
        if (first == std::string::npos) {
            continue;
        }
        raw_path.erase(0, first);
        if (raw_path.empty() || raw_path.front() != '/') {
            continue;
        }
        constexpr std::string_view deleted_suffix = " (deleted)";
        if (raw_path.ends_with(deleted_suffix)) {
            fail("cannot attest deleted mapped runtime object: " + raw_path);
        }
        raw_path = decode_proc_maps_path(std::move(raw_path));
        const auto [device_major, device_minor] = parse_device(device);
        const std::uint64_t inode =
            parse_unsigned(inode_text, 10, "inode");
        if (inode == 0) {
            fail("filesystem-backed runtime object has zero inode: " +
                 raw_path);
        }
        const fs::path path(raw_path);
        const RuntimeFileKey key = checked_file_key(
            path, device_major, device_minor, inode);
        const bool executable = permissions.find('x') != std::string::npos;
        const auto [entry, inserted] = mapped_files.try_emplace(
            key, MappedRuntimeFile{
                     path, executable, false, device_major, device_minor,
                     inode});
        if (!inserted) {
            entry->second.executable_mapping |= executable;
            if (path.string() < entry->second.path.string()) {
                entry->second.path = path;
            }
        }
    }
    if (!maps.eof()) {
        fail("failed while reading /proc/self/maps");
    }

    struct stat binary_metadata {};
    if (::stat(binary.c_str(), &binary_metadata) != 0) {
        fail("cannot stat analyzer executable for runtime attestation: " +
             std::string(std::strerror(errno)));
    }
    const RuntimeFileKey binary_key{
        static_cast<std::uint64_t>(major(binary_metadata.st_dev)),
        static_cast<std::uint64_t>(minor(binary_metadata.st_dev)),
        static_cast<std::uint64_t>(binary_metadata.st_ino),
    };
    const auto binary_entry = mapped_files.find(binary_key);
    if (binary_entry == mapped_files.end()) {
        fail("analyzer executable is absent from /proc/self/maps");
    }
    binary_entry->second.analyzer = true;
    binary_entry->second.path = binary;

    std::set<std::tuple<std::string, std::string, std::string, std::string>>
        unique_components;
    for (const auto &[key, file] : mapped_files) {
        (void)key;
        const std::string digest = checked_mapped_file_sha256(file);
        const std::string kind =
            file.analyzer
                ? "executable"
                : (looks_like_shared_object(file.path)
                       ? "shared_object"
                       : (file.executable_mapping ? "executable" : "data"));
        const std::string name =
            file.analyzer
                ? "tafuzz-sa executable"
                : nonempty(file.path.filename().string(),
                           "mapped runtime object");
        const std::string version =
            file.analyzer
                ? std::string("0.1.0; ") + clang::getClangFullVersion()
                : nonempty(file.path.filename().string(), "unknown");
        unique_components.emplace(kind, name, version, digest);
    }

    llvm::json::Array result;
    for (const auto &[kind, name, version, digest] : unique_components) {
        const std::string id_material =
            length_prefixed_material({kind, name, version, digest});
        result.push_back(llvm::json::Object{
            {"component_id", core::stable_id("tool", id_material)},
            {"name", name},
            {"version", version},
            {"component_kind", kind},
            {"sha256", digest},
        });
    }
    return result;
#endif
}

struct RuntimeComponentRecord {
    std::string component_id;
    std::string name;
    std::string version;
    std::string component_kind;
    std::string sha256;
    fs::path path;
};

#if defined(__linux__)
RuntimeComponentRecord make_mapped_runtime_component(
    std::string name, std::string version, std::string component_kind,
    const MappedRuntimeFile &file) {
    const std::string digest = checked_mapped_file_sha256(file);
    const std::string id_material = length_prefixed_material(
        {component_kind, name, version, digest});
    return {
        core::stable_id("tool", id_material), std::move(name),
        std::move(version), std::move(component_kind), digest,
        fs::canonical(file.path)};
}

MappedRuntimeFile mapped_runtime_file_for_path(const fs::path &input_path) {
    const fs::path path = fs::canonical(input_path);
    struct stat metadata {};
    if (::stat(path.c_str(), &metadata) != 0 ||
        !S_ISREG(metadata.st_mode)) {
        fail("cannot stat mapped runtime component: " + path.string());
    }
    const RuntimeFileKey expected{
        static_cast<std::uint64_t>(major(metadata.st_dev)),
        static_cast<std::uint64_t>(minor(metadata.st_dev)),
        static_cast<std::uint64_t>(metadata.st_ino)};

    std::ifstream maps("/proc/self/maps");
    if (!maps) {
        fail("cannot open /proc/self/maps for runtime component attestation");
    }
    bool found = false;
    bool executable = false;
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string address;
        std::string permissions;
        std::string offset;
        std::string device;
        std::string inode_text;
        if (!(row >> address >> permissions >> offset >> device >> inode_text)) {
            fail("malformed entry in /proc/self/maps");
        }
        const auto [device_major, device_minor] = parse_device(device);
        const std::uint64_t inode =
            parse_unsigned(inode_text, 10, "runtime component inode");
        if (RuntimeFileKey{device_major, device_minor, inode} != expected) {
            continue;
        }
        found = true;
        executable |= permissions.find('x') != std::string::npos;
    }
    if (!maps.eof()) {
        fail("failed while reading /proc/self/maps for runtime component");
    }
    if (!found) {
        fail("runtime component is not mapped in this process: " +
             path.string());
    }
    return {
        path, executable, false,
        std::get<0>(expected), std::get<1>(expected),
        std::get<2>(expected)};
}

MappedRuntimeFile mapped_z3_file() {
    std::ifstream maps("/proc/self/maps");
    if (!maps) {
        fail("cannot open /proc/self/maps for Z3 runtime attestation");
    }
    std::map<RuntimeFileKey, MappedRuntimeFile> candidates;
    std::string line;
    while (std::getline(maps, line)) {
        std::istringstream row(line);
        std::string address;
        std::string permissions;
        std::string offset;
        std::string device;
        std::string inode_text;
        if (!(row >> address >> permissions >> offset >> device >> inode_text)) {
            fail("malformed entry in /proc/self/maps");
        }
        std::string raw_path;
        std::getline(row, raw_path);
        const std::size_t first = raw_path.find_first_not_of(' ');
        if (first == std::string::npos) continue;
        raw_path.erase(0, first);
        if (raw_path.empty() || raw_path.front() != '/') continue;
        constexpr std::string_view deleted_suffix = " (deleted)";
        if (raw_path.ends_with(deleted_suffix)) continue;
        raw_path = decode_proc_maps_path(std::move(raw_path));
        const fs::path path(raw_path);
        const std::string filename = path.filename().string();
        if (filename != "libz3.so" &&
            !std::string_view(filename).starts_with("libz3.so.")) {
            continue;
        }
        const auto [device_major, device_minor] = parse_device(device);
        const std::uint64_t inode =
            parse_unsigned(inode_text, 10, "Z3 inode");
        if (inode == 0U) {
            fail("mapped Z3 runtime object has zero inode: " + path.string());
        }
        const RuntimeFileKey key = checked_file_key(
            path, device_major, device_minor, inode);
        const bool executable = permissions.find('x') != std::string::npos;
        const auto [entry, inserted] = candidates.try_emplace(
            key, MappedRuntimeFile{
                     path, executable, false, device_major, device_minor,
                     inode});
        if (!inserted) {
            entry->second.executable_mapping |= executable;
            if (path.string() < entry->second.path.string()) {
                entry->second.path = path;
            }
        }
    }
    if (!maps.eof()) {
        fail("failed while reading /proc/self/maps for Z3 attestation");
    }
    if (candidates.size() != 1U) {
        fail(
            "expected exactly one mapped Z3 shared object, observed " +
            std::to_string(candidates.size()));
    }
    return candidates.begin()->second;
}
#endif

std::vector<RuntimeComponentRecord> m5_runtime_components(
    const fs::path &binary, const std::string &z3_version) {
    std::vector<RuntimeComponentRecord> result;
#if !defined(__linux__)
    (void)binary;
    (void)z3_version;
    fail("M5 runtime mapping attestation requires Linux /proc/self/maps");
#else
    const MappedRuntimeFile analyzer_file =
        mapped_runtime_file_for_path(binary);
    result.push_back(make_mapped_runtime_component(
        "tafuzz-sa executable",
        std::string("0.1.0; ") + clang::getClangFullVersion(),
        "executable", analyzer_file));
    const MappedRuntimeFile z3_file = mapped_z3_file();
    result.push_back(make_mapped_runtime_component(
        nonempty(z3_file.path.filename().string(), "libz3"), z3_version,
        "shared_object", z3_file));
#endif
    return result;
}

llvm::json::Array runtime_components_json(
    const std::vector<RuntimeComponentRecord> &components) {
    llvm::json::Array result;
    for (const RuntimeComponentRecord &component : components) {
        result.push_back(llvm::json::Object{
            {"component_id", component.component_id},
            {"name", component.name},
            {"version", component.version},
            {"component_kind", component.component_kind},
            {"sha256", component.sha256},
            {"path", component.path.string()},
        });
    }
    return result;
}

llvm::json::Object source_input_provenance_json(
    const core::SemanticIndex &index) {
    llvm::json::Array files;
    for (const core::InputFileDigest &input : index.input_files) {
        if (input.observed_paths.empty() &&
            input.role != core::InputFileRole::Toolchain) {
            fail("file-backed source input has no physical provenance path: " +
                 input.input_file_id);
        }
        llvm::json::Array observed_paths;
        for (const std::string &path_text : input.observed_paths) {
            const fs::path path(path_text);
            if (!path.is_absolute()) {
                fail("source input provenance path is not absolute: " +
                     input.input_file_id);
            }
#if defined(__linux__)
            const PathSnapshot snapshot = snapshot_regular_file(path);
            if (snapshot.digest != input.sha256 ||
                snapshot.byte_size != input.byte_size) {
                fail("source input no longer matches the loaded Clang buffer: " +
                     path.string());
            }
#else
            fail("source input provenance attestation requires Linux");
#endif
            observed_paths.push_back(path.string());
        }
        files.push_back(llvm::json::Object{
            {"input_file_id", input.input_file_id},
            {"logical_path", input.logical_path},
            {"role", input_file_role(input.role)},
            {"sha256", input.sha256},
            {"byte_size", json_byte_size(input.byte_size)},
            {"observed_paths", std::move(observed_paths)},
        });
    }
    if (files.empty()) {
        fail("source input provenance cannot be empty");
    }
    return llvm::json::Object{
        {"manifest_sha256", index.input_manifest_sha256},
        {"files", std::move(files)},
    };
}

llvm::json::Object artifact_digest(
    std::string id, std::string kind, std::string digest,
    const fs::path &path) {
    return llvm::json::Object{
        {"artifact_id", std::move(id)},
        {"kind", std::move(kind)},
        {"sha256", std::move(digest)},
        {"path", path.string()},
    };
}

llvm::json::Object artifact_digest(
    std::string id, std::string kind, std::string digest) {
    return llvm::json::Object{
        {"artifact_id", std::move(id)},
        {"kind", std::move(kind)},
        {"sha256", std::move(digest)},
    };
}

llvm::json::Object stage_json(
    std::string id, std::string name, core::StageStatus stage_status,
    const std::vector<std::string> &inputs,
    const std::vector<std::string> &outputs,
    const std::vector<std::string> &diagnostics) {
    return llvm::json::Object{
        {"stage_id", std::move(id)},
        {"name", std::move(name)},
        {"status", status(stage_status)},
        {"input_sha256", string_array(inputs)},
        {"output_sha256", string_array(outputs)},
        {"diagnostics", string_array(diagnostics)},
    };
}

core::StageStatus combined_status(
    std::initializer_list<core::StageStatus> values) {
    bool incomplete = false;
    for (const core::StageStatus value : values) {
        if (value == core::StageStatus::Failed) {
            return core::StageStatus::Failed;
        }
        incomplete |= value == core::StageStatus::ConservativeIncomplete;
    }
    return incomplete ? core::StageStatus::ConservativeIncomplete
                      : core::StageStatus::Complete;
}

std::vector<core::CoverageGap> combined_gaps(
    const core::SemanticIndex &index, const core::ApBindings &bindings,
    const core::ContextualInfluenceGraph &graph,
    const core::ApInfluenceCones &cones) {
    std::vector<core::CoverageGap> result;
    const auto append = [&result](const std::vector<core::CoverageGap> &gaps) {
        result.insert(result.end(), gaps.begin(), gaps.end());
    };
    append(index.coverage_gaps);
    append(bindings.coverage_gaps);
    append(graph.coverage_gaps);
    append(cones.coverage_gaps);
    std::sort(result.begin(), result.end(),
              [](const core::CoverageGap &left,
                 const core::CoverageGap &right) {
                  return left.gap_id < right.gap_id;
              });
    result.erase(
        std::unique(result.begin(), result.end(),
                    [](const core::CoverageGap &left,
                       const core::CoverageGap &right) {
                        return left.gap_id == right.gap_id;
                    }),
        result.end());
    return result;
}

llvm::json::Object certificate_json(
    const Options &options, const fs::path &binary,
    const core::CompilationPlan &plan, const core::TypedPropertyIr &property,
    const core::SemanticIndex &index, const core::ApBindings &bindings,
    const core::ContextualInfluenceGraph &graph,
    const core::ApInfluenceCones &cones,
    const std::string &index_digest, const std::string &bindings_digest,
    const std::string &graph_digest, const std::string &cones_digest,
    const std::string &started_at, const std::string &finished_at) {
    const std::string binary_digest = file_sha256(binary);
    const std::string core_digest =
        rift::build_manifest::kProductionCoreSha256;
    const std::string schema_digest =
        rift::build_manifest::kSchemaBundleSha256;
    const std::string build_manifest_digest =
        rift::build_manifest::kManifestSha256;
    EnvironmentCapture environment = capture_semantic_environment();
    std::string configuration = length_prefixed_material(
        {build_manifest_digest, environment.digest});
    for (const std::string &argument : options.argv) {
        append_length_prefixed(configuration, argument);
    }
    const std::string configuration_digest = core::sha256_hex(configuration);
    const core::StageStatus aggregate = combined_status(
        {index.status, bindings.status, graph.status, cones.status});
    const std::vector<core::CoverageGap> gaps =
        combined_gaps(index, bindings, graph, cones);

    llvm::json::Array inputs;
    inputs.push_back(artifact_digest(
        property.artifact_id, "typed_property_ir",
        property.artifact_sha256, options.property));
    inputs.push_back(artifact_digest(
        "compile.database", "compile_commands",
        plan.compilation_database_sha256, options.compile_database));
    inputs.push_back(artifact_digest(
        core::stable_id("input_manifest", index.input_manifest_sha256),
        "source_inputs", index.input_manifest_sha256));

    const fs::path output = options.output_directory;
    llvm::json::Array outputs;
    outputs.push_back(artifact_digest(
        index.artifact_id, "semantic_index", index_digest,
        output / "semantic_index.json"));
    outputs.push_back(artifact_digest(
        bindings.artifact_id, "ap_bindings", bindings_digest,
        output / "ap_bindings.json"));
    outputs.push_back(artifact_digest(
        graph.artifact_id, "contextual_influence_graph", graph_digest,
        output / "contextual_influence_graph.json"));
    outputs.push_back(artifact_digest(
        cones.artifact_id, "ap_influence_cones", cones_digest,
        output / "ap_influence_cones.json"));

    llvm::json::Array stages;
    stages.push_back(stage_json(
        "stage.index", "index", index.status,
        {plan.compilation_database_sha256, index.input_manifest_sha256},
        {index_digest},
        index.diagnostics));
    stages.push_back(stage_json(
        "stage.bind", "bind", bindings.status,
        {property.artifact_sha256, index_digest}, {bindings_digest},
        bindings.diagnostics));
    stages.push_back(stage_json(
        "stage.influence", "influence", graph.status,
        {index_digest, bindings_digest}, {graph_digest}, graph.diagnostics));
    stages.push_back(stage_json(
        "stage.cone", "cone", cones.status,
        {bindings_digest, graph_digest}, {cones_digest}, cones.diagnostics));
    stages.push_back(stage_json(
        "stage.certificate", "certificate", aggregate,
        {index_digest, bindings_digest, graph_digest, cones_digest}, {}, {}));

    const std::string analysis_material = length_prefixed_material(
        {property.artifact_sha256, index.input_manifest_sha256,
         index.canonical_compilation_database_sha256,
         index.path_map_sha256});
    const std::string analysis_id =
        core::stable_id("analysis", analysis_material);
    const std::string certificate_material = length_prefixed_material(
        {analysis_id, configuration_digest, index_digest, bindings_digest,
         graph_digest, cones_digest});
    const std::string certificate_id =
        core::stable_id("certificate", certificate_material);
    llvm::json::Object source_input_provenance =
        source_input_provenance_json(index);
    llvm::json::Array toolchain = runtime_toolchain_json(binary);

    return llvm::json::Object{
        {"schema_version", "2.0.0"},
        {"certificate_id", certificate_id},
        {"analysis_id", analysis_id},
        {"status", status(aggregate)},
        {"analyzer",
         llvm::json::Object{
             {"name", "tafuzz-sa"},
             {"version", "0.1.0"},
             {"binary_sha256", binary_digest},
             {"configuration_sha256", configuration_digest},
             {"environment_sha256", environment.digest},
         }},
        {"build_manifest",
         llvm::json::Object{
             {"identity_policy", rift::build_manifest::kIdentityPolicy},
             {"manifest_sha256", build_manifest_digest},
             {"production_core_sha256", core_digest},
             {"schema_bundle_sha256", schema_digest},
         }},
        {"core_tree_sha256", core_digest},
        {"schema_bundle_sha256", schema_digest},
        {"environment",
         llvm::json::Object{
             {"digest", environment.digest},
             {"variables", std::move(environment.variables)},
         }},
        {"inputs", std::move(inputs)},
        {"source_input_provenance",
         std::move(source_input_provenance)},
        {"toolchain", std::move(toolchain)},
        {"outputs", std::move(outputs)},
        {"stages", std::move(stages)},
        {"unsupported_constructs", gaps_json(gaps)},
        {"started_at", started_at},
        {"finished_at", finished_at},
    };
}

struct M5ArtifactIdentity {
    std::string artifact_id;
    std::string kind;
    std::string sha256;
    fs::path path;
};

struct ModelStageArtifacts {
    std::vector<core::ModelPackV2> packs;
    std::vector<fs::path> pack_paths;
    std::vector<std::string> raw_pack_sha256s;
    std::vector<std::string> semantic_pack_sha256s;
    core::ModelFactOverlay overlay;
    std::string overlay_payload;
    std::string overlay_sha256;
    std::optional<core::ExecutorCapabilityManifest> executor_manifest;
    std::optional<fs::path> executor_manifest_path;
    std::optional<std::string> executor_manifest_sha256;
};

llvm::json::Object m5_artifact_json(const M5ArtifactIdentity &artifact) {
    return llvm::json::Object{
        {"artifact_id", artifact.artifact_id},
        {"kind", artifact.kind},
        {"sha256", artifact.sha256},
        {"path", artifact.path.string()},
    };
}

std::pair<std::uint64_t, std::uint64_t> solver_failure_counts(
    const core::MutationRecipes &recipes) {
    std::uint64_t timeouts = 0;
    std::uint64_t unsupported = 0;
    const auto account = [&](const core::SolverQueryEvidence &query) {
        if (query.outcome == core::SolverOutcome::Timeout) ++timeouts;
        if (query.outcome == core::SolverOutcome::Unsupported) ++unsupported;
    };
    for (const core::MutationRecipe &recipe : recipes.recipes) {
        account(recipe.solver_query);
        if (recipe.direction_query) account(*recipe.direction_query);
    }
    return {timeouts, unsupported};
}

std::uint64_t solver_query_count(const core::MutationRecipes &recipes) {
    std::uint64_t count = 0;
    const auto account = [&](const core::SolverQueryEvidence &query) {
        if (query.outcome != core::SolverOutcome::NotRun &&
            query.outcome != core::SolverOutcome::Unsupported) {
            ++count;
        }
    };
    for (const core::MutationRecipe &recipe : recipes.recipes) {
        account(recipe.solver_query);
        if (recipe.direction_query) account(*recipe.direction_query);
    }
    return count;
}

std::string solver_budget_sha256(
    const core::SolverContract &contract) {
    const std::string timeout = std::to_string(contract.timeout_ms);
    const std::string max_queries = std::to_string(contract.max_queries);
    return core::sha256_hex(length_prefixed_material({
        "rift-m5-solver-budget/1.0.0", contract.solver,
        contract.solver_version, contract.encoding_version, timeout,
        max_queries}));
}

llvm::json::Object m5_certificate_json(
    const Options &options, const fs::path &binary,
    const core::TypedPropertyIr &property,
    const core::SemanticIndex &certificate_index,
    const core::ApBindings &bindings,
    const core::ContextualInfluenceGraph &graph,
    const core::ApInfluenceCones &cones,
    const std::string &index_digest, const std::string &bindings_digest,
    const std::string &graph_digest, const std::string &cones_digest,
    const core::PredicateOccurrenceBindings &predicate_occurrences,
    const std::string &predicate_occurrences_digest,
    const std::string &m4_analysis_id, const std::string &m4_certificate_id,
    const std::string &m4_certificate_digest,
    const std::string &configuration_digest,
    const ModelStageArtifacts &model_stage,
    const core::FrontierCandidates &frontier_candidates,
    const std::string &frontier_candidates_digest,
    const core::FuzzableFrontier &fuzzable_frontier,
    const std::string &fuzzable_frontier_digest,
    const core::MutationRecipes &recipes,
    const std::string &recipes_digest,
    const core::RecipeReplayObligations &replay_obligations,
    const std::string &replay_digest,
    const std::vector<RuntimeComponentRecord> &runtime_components,
    const std::string &started_at, const std::string &finished_at) {
    const fs::path output = fs::absolute(options.output_directory);
    const M5ArtifactIdentity m4_certificate{
        m4_certificate_id, "m4_analysis_certificate", m4_certificate_digest,
        output / "analysis_certificate.json"};
    const M5ArtifactIdentity property_artifact{
        property.artifact_id, "typed_property_ir", property.artifact_sha256,
        fs::absolute(options.property)};
    const M5ArtifactIdentity index_artifact{
        certificate_index.artifact_id, "semantic_index", index_digest,
        output / "semantic_index.json"};
    const M5ArtifactIdentity bindings_artifact{
        bindings.artifact_id, "ap_bindings", bindings_digest,
        output / "ap_bindings.json"};
    const M5ArtifactIdentity graph_artifact{
        graph.artifact_id, "contextual_influence_graph", graph_digest,
        output / "contextual_influence_graph.json"};
    const M5ArtifactIdentity cones_artifact{
        cones.artifact_id, "ap_influence_cones", cones_digest,
        output / "ap_influence_cones.json"};

    const std::array<M5ArtifactIdentity, 6> outputs{{
        {model_stage.overlay.artifact_id, "model_fact_overlay",
         model_stage.overlay_sha256, output / "model_fact_overlay.json"},
        {predicate_occurrences.artifact_id,
         "predicate_occurrence_bindings", predicate_occurrences_digest,
         output / "predicate_occurrence_bindings.json"},
        {frontier_candidates.artifact_id, "frontier_candidates",
         frontier_candidates_digest, output / "frontier_candidates.json"},
        {fuzzable_frontier.artifact_id, "fuzzable_frontier",
         fuzzable_frontier_digest, output / "fuzzable_frontier.json"},
        {recipes.artifact_id, "mutation_recipes", recipes_digest,
         output / "mutation_recipes.json"},
        {replay_obligations.artifact_id, "recipe_replay_obligations",
         replay_digest, output / "recipe_replay_obligations.json"},
    }};

    std::vector<std::size_t> pack_order(model_stage.packs.size());
    for (std::size_t index = 0; index < pack_order.size(); ++index) {
        pack_order[index] = index;
    }
    std::sort(
        pack_order.begin(), pack_order.end(),
        [&](const std::size_t left, const std::size_t right) {
            return std::tie(
                       model_stage.packs[left].model_pack_id,
                       model_stage.packs[left].model_pack_version,
                       model_stage.semantic_pack_sha256s[left],
                       model_stage.raw_pack_sha256s[left]) <
                   std::tie(
                       model_stage.packs[right].model_pack_id,
                       model_stage.packs[right].model_pack_version,
                       model_stage.semantic_pack_sha256s[right],
                       model_stage.raw_pack_sha256s[right]);
        });
    llvm::json::Array model_packs;
    for (const std::size_t index : pack_order) {
        model_packs.push_back(llvm::json::Object{
            {"model_pack_id", model_stage.packs[index].model_pack_id},
            {"model_pack_version",
             model_stage.packs[index].model_pack_version},
            {"layer", core::to_string(model_stage.packs[index].layer)},
            {"sha256", model_stage.raw_pack_sha256s[index]},
            {"semantic_sha256", model_stage.semantic_pack_sha256s[index]},
            {"path", model_stage.pack_paths[index].string()},
        });
    }

    llvm::json::Value executor = nullptr;
    if (model_stage.executor_manifest &&
        model_stage.executor_manifest_path &&
        model_stage.executor_manifest_sha256) {
        executor = llvm::json::Object{
            {"executor_id", model_stage.executor_manifest->executor_id},
            {"executor_version",
             model_stage.executor_manifest->executor_version},
            {"artifact_id", model_stage.executor_manifest->artifact_id},
            {"sha256", *model_stage.executor_manifest_sha256},
            {"path", model_stage.executor_manifest_path->string()},
        };
    }

    if (runtime_components.size() < 2U) {
        fail("M5 runtime attestation requires analyzer and Z3 components");
    }
    const RuntimeComponentRecord &analyzer_component = runtime_components[0];
    const RuntimeComponentRecord &z3_component = runtime_components[1];
    const auto [timeouts, unsupported] = solver_failure_counts(recipes);
    const std::string solver_budget_digest =
        solver_budget_sha256(recipes.solver_contract);
    core::StageStatus aggregate = combined_status(
        {model_stage.overlay.status, predicate_occurrences.status,
         frontier_candidates.status, fuzzable_frontier.status,
         recipes.status});
    if ((timeouts != 0U || unsupported != 0U) &&
        aggregate == core::StageStatus::Complete) {
        fail(
            "recipe stage reported COMPLETE despite solver timeout or "
            "unsupported evidence");
    }

    llvm::json::Array output_json;
    for (const M5ArtifactIdentity &artifact : outputs) {
        output_json.push_back(m5_artifact_json(artifact));
    }

    std::vector<std::string> raw_pack_digests;
    std::vector<std::string> certificate_inputs{
        m4_certificate.sha256, property_artifact.sha256,
        index_artifact.sha256, bindings_artifact.sha256,
        graph_artifact.sha256, cones_artifact.sha256};
    for (const std::size_t index : pack_order) {
        raw_pack_digests.push_back(model_stage.raw_pack_sha256s[index]);
        certificate_inputs.push_back(model_stage.raw_pack_sha256s[index]);
        certificate_inputs.push_back(
            model_stage.semantic_pack_sha256s[index]);
    }
    if (model_stage.executor_manifest_sha256) {
        certificate_inputs.push_back(*model_stage.executor_manifest_sha256);
    }
    certificate_inputs.insert(
        certificate_inputs.end(),
        {configuration_digest, rift::build_manifest::kManifestSha256,
         rift::build_manifest::kProductionCoreSha256,
         rift::build_manifest::kSchemaBundleSha256});
    for (const RuntimeComponentRecord &component : runtime_components) {
        certificate_inputs.push_back(component.sha256);
    }
    for (const M5ArtifactIdentity &artifact : outputs) {
        certificate_inputs.push_back(artifact.sha256);
    }

    std::vector<std::string> contextualize_inputs{
        model_stage.overlay_sha256, graph_digest, cones_digest};
    if (model_stage.executor_manifest_sha256) {
        contextualize_inputs.push_back(*model_stage.executor_manifest_sha256);
    }
    llvm::json::Array stages;
    stages.push_back(stage_json(
        "stage.model", "model", model_stage.overlay.status,
        [&] {
            std::vector<std::string> inputs{index_digest};
            inputs.insert(
                inputs.end(), raw_pack_digests.begin(),
                raw_pack_digests.end());
            return inputs;
        }(),
        {model_stage.overlay_sha256}, model_stage.overlay.diagnostics));
    stages.push_back(stage_json(
        "stage.occurrence", "occurrence", predicate_occurrences.status,
        {property.artifact_sha256, index_digest},
        {predicate_occurrences_digest},
        predicate_occurrences.diagnostics));
    stages.push_back(stage_json(
        "stage.contextualize", "contextualize", frontier_candidates.status,
        contextualize_inputs, {frontier_candidates_digest},
        frontier_candidates.diagnostics));
    stages.push_back(stage_json(
        "stage.frontier", "frontier", fuzzable_frontier.status,
        {frontier_candidates_digest}, {fuzzable_frontier_digest},
        fuzzable_frontier.diagnostics));
    stages.push_back(stage_json(
        "stage.recipe", "recipe", recipes.status,
        {property.artifact_sha256, bindings_digest, graph_digest, cones_digest,
         frontier_candidates_digest, model_stage.overlay_sha256,
         predicate_occurrences_digest,
         rift::build_manifest::kProductionCoreSha256, z3_component.sha256,
         solver_budget_digest},
        {recipes_digest, replay_digest}, recipes.diagnostics));
    stages.push_back(stage_json(
        "stage.certificate", "certificate", aggregate,
        certificate_inputs, {}, {}));

    llvm::json::Object commitments{
        {"analysis_certificate", m5_artifact_json(m4_certificate)},
        {"typed_property_ir", m5_artifact_json(property_artifact)},
        {"semantic_index", m5_artifact_json(index_artifact)},
        {"ap_bindings", m5_artifact_json(bindings_artifact)},
        {"contextual_influence_graph", m5_artifact_json(graph_artifact)},
        {"ap_influence_cones", m5_artifact_json(cones_artifact)},
    };
    llvm::json::Object certificate{
        {"schema_version", "1.0.0"},
        {"certificate_id", "m5-certificate:" + std::string(64U, '0')},
        {"analysis_id", m4_analysis_id},
        {"status", status(aggregate)},
        {"analyzer",
         llvm::json::Object{
             {"name", "tafuzz-sa"},
             {"version", "0.1.0"},
             {"binary_sha256", analyzer_component.sha256},
             {"binary_path", fs::absolute(binary).string()},
             {"runtime_component_id", analyzer_component.component_id},
             {"configuration_sha256", configuration_digest},
         }},
        {"build_manifest",
         llvm::json::Object{
             {"identity_policy", rift::build_manifest::kIdentityPolicy},
             {"manifest_sha256", rift::build_manifest::kManifestSha256},
             {"production_core_sha256",
              rift::build_manifest::kProductionCoreSha256},
             {"schema_bundle_sha256",
              rift::build_manifest::kSchemaBundleSha256},
         }},
        {"m4_commitments", std::move(commitments)},
        {"model_packs", std::move(model_packs)},
        {"executor_manifest", std::move(executor)},
        {"runtime_components", runtime_components_json(runtime_components)},
        {"solver",
         llvm::json::Object{
             {"name", "Z3"},
             {"actual_version", recipes.solver_contract.solver_version},
             {"runtime_component_id", z3_component.component_id},
             {"component_sha256", z3_component.sha256},
             {"timeout_ms", recipes.solver_contract.timeout_ms},
             {"max_queries", recipes.solver_contract.max_queries},
             {"budget_sha256", solver_budget_digest},
             {"queries", solver_query_count(recipes)},
             {"timeouts", timeouts},
             {"unsupported", unsupported},
         }},
        {"outputs", std::move(output_json)},
        {"stages", std::move(stages)},
        {"invariants",
         llvm::json::Object{
             {"model_vm_executed_before_property_load", true},
             {"m4_cone_immutable", true},
             {"ranking_never_prunes", true},
             {"unknown_never_means_unsat", true},
             {"unknown_candidates_retained", true},
             {"unknown_recipe_emitted", true},
             {"unsupported_or_timeout_preserved_as_unknown", true},
             {"pack_cannot_assert_must", true},
             {"executor_capability_independent", true},
         }},
        {"diagnostics", llvm::json::Array{}},
        {"started_at", started_at},
        {"finished_at", finished_at},
    };
    const std::string canonical = canonical_json_object(
        certificate,
        {"certificate_id", "started_at", "finished_at"});
    certificate["certificate_id"] =
        "m5-certificate:" + core::sha256_hex(canonical);
    return certificate;
}

std::uint32_t parse_u32(std::string_view text, std::string_view option) {
    std::size_t consumed = 0;
    unsigned long value = 0;
    try {
        value = std::stoul(std::string(text), &consumed, 10);
    } catch (const std::exception &) {
        fail("invalid integer for " + std::string(option));
    }
    if (consumed != text.size() || value > UINT32_MAX) {
        fail("invalid integer for " + std::string(option));
    }
    return static_cast<std::uint32_t>(value);
}

std::uint64_t parse_positive_u64(
    std::string_view text, std::string_view option) {
    if (text.empty() ||
        !std::all_of(text.begin(), text.end(), [](const unsigned char value) {
            return std::isdigit(value) != 0;
        })) {
        fail("invalid positive integer for " + std::string(option));
    }
    std::size_t consumed = 0;
    unsigned long long value = 0;
    try {
        value = std::stoull(std::string(text), &consumed, 10);
    } catch (const std::exception &) {
        fail("invalid integer for " + std::string(option));
    }
    if (consumed != text.size() || value == 0U) {
        fail("invalid positive integer for " + std::string(option));
    }
    return static_cast<std::uint64_t>(value);
}

core::LogicalPathRoot parse_logical_root(std::string_view text) {
    const std::size_t separator = text.find('=');
    if (separator == std::string_view::npos || separator == 0 ||
        separator + 1 >= text.size()) {
        fail("--logical-root requires ROOT_ID=/absolute/path");
    }
    core::LogicalPathRoot root;
    root.root_id = std::string(text.substr(0, separator));
    root.physical_root = fs::path(text.substr(separator + 1));
    if (!root.physical_root.is_absolute()) {
        fail("--logical-root physical path must be absolute: " +
             root.physical_root.string());
    }
    return root;
}

Options parse_options(int argc, char **argv) {
    if (argc < 2) {
        fail(
            "usage: tafuzz-sa {index|bind|influence|frontier|recipes} [options]");
    }
    Options result;
    result.command = argv[1];
    if (result.command != "index" && result.command != "bind" &&
        result.command != "influence" && result.command != "frontier" &&
        result.command != "recipes") {
        fail("unsupported production command " + result.command);
    }
    for (int index = 0; index < argc; ++index) {
        result.argv.emplace_back(argv[index]);
    }
    for (int index = 2; index < argc; ++index) {
        const std::string option = argv[index];
        if (index + 1 >= argc) {
            fail("missing value after " + option);
        }
        const std::string value = argv[++index];
        if (option == "--compile-db") {
            result.compile_database = value;
        } else if (option == "--property") {
            result.property = value;
        } else if (option == "--output") {
            result.output = value;
        } else if (option == "--output-dir") {
            result.output_directory = value;
        } else if (option == "--index-output") {
            result.index_output = fs::path(value);
        } else if (option == "--source-root") {
            result.source_root = fs::path(value);
        } else if (option == "--logical-root") {
            result.logical_roots.push_back(parse_logical_root(value));
        } else if (option == "--model-pack") {
            result.model_packs.emplace_back(value);
        } else if (option == "--executor-capabilities") {
            if (result.executor_capabilities) {
                fail("--executor-capabilities may be specified only once");
            }
            result.executor_capabilities = fs::path(value);
        } else if (option == "--call-string-limit") {
            result.call_string_limit = parse_u32(value, option);
        } else if (option == "--solver-timeout-ms") {
            result.solver_timeout_ms = parse_positive_u64(value, option);
            if (result.solver_timeout_ms >
                static_cast<std::uint64_t>(
                    std::numeric_limits<unsigned>::max())) {
                fail(
                    "--solver-timeout-ms exceeds the Z3 unsigned timeout "
                    "domain");
            }
        } else if (option == "--max-solver-queries") {
            result.max_solver_queries = parse_positive_u64(value, option);
        } else {
            fail("unknown option " + option);
        }
    }
    if (result.compile_database.empty()) {
        fail("--compile-db is required");
    }
    if (result.command == "index" && result.output.empty()) {
        fail("index requires --output");
    }
    if (result.command == "bind" &&
        (result.property.empty() || result.output.empty())) {
        fail("bind requires --property and --output");
    }
    if (result.command == "influence" &&
        (result.property.empty() || result.output_directory.empty())) {
        fail("influence requires --property and --output-dir");
    }
    if ((result.command == "frontier" || result.command == "recipes") &&
        (result.property.empty() || result.output_directory.empty() ||
         result.model_packs.empty())) {
        fail(
            result.command +
            " requires --property, --output-dir, and at least one --model-pack");
    }
    if (result.source_root.has_value() && !result.logical_roots.empty()) {
        fail("--source-root and --logical-root are mutually exclusive");
    }
    return result;
}

Options absolute_guidance_options(const Options &options) {
    Options result = options;
    const auto absolute_normalized = [](const fs::path &path) {
        return fs::absolute(path).lexically_normal();
    };
    result.compile_database = absolute_normalized(options.compile_database);
    result.property = absolute_normalized(options.property);
    result.output_directory = absolute_normalized(options.output_directory);
    if (options.source_root) {
        result.source_root = absolute_normalized(*options.source_root);
    }
    for (core::LogicalPathRoot &root : result.logical_roots) {
        root.physical_root = absolute_normalized(root.physical_root);
    }
    for (fs::path &pack : result.model_packs) {
        pack = absolute_normalized(pack);
    }
    if (options.executor_capabilities) {
        result.executor_capabilities =
            absolute_normalized(*options.executor_capabilities);
    }
    return result;
}

void require_valid(
    const std::vector<std::string> &errors, std::string_view artifact) {
    if (errors.empty()) {
        return;
    }
    std::string message = std::string(artifact) + " validation failed";
    for (const std::string &error : errors) {
        message += "; " + error;
    }
    fail(std::move(message));
}

core::CompilationPlan plan_for(const Options &options) {
    core::CompilationPlanOptions plan_options;
    plan_options.source_identity_root = options.source_root;
    plan_options.identity_roots = options.logical_roots;
    // Relative compile directories are resolved against the compilation
    // database directory by the core.  This keeps a frozen database portable
    // and independent of the caller's current working directory.
    plan_options.require_absolute_working_directories = false;
    core::CompilationPlan plan = core::load_compilation_plan(
        fs::absolute(options.compile_database), plan_options);
    if (plan.status == core::StageStatus::Failed) {
        fail("compilation plan failed: " +
             (plan.diagnostics.empty() ? std::string("no diagnostic")
                                       : plan.diagnostics.front()));
    }
    return plan;
}

core::SemanticIndex index_for(const core::CompilationPlan &plan) {
    core::SemanticIndex index = core::build_semantic_index(plan);
    require_valid(core::validate_semantic_index(index), "semantic index");
    return index;
}

core::TypedPropertyIr property_for(const Options &options) {
    core::LoadResult<core::TypedPropertyIr> loaded =
        core::load_typed_property_ir(fs::absolute(options.property));
    if (!loaded.value.has_value()) {
        fail("typed property IR failed: " +
             (loaded.diagnostics.empty() ? std::string("no diagnostic")
                                         : loaded.diagnostics.front()));
    }
    core::TypedPropertyIr property = std::move(*loaded.value);
    require_valid(core::validate_typed_property_ir(property),
                  "typed property IR");
    return property;
}

ModelStageArtifacts model_stage_for(
    const Options &options, const core::SemanticIndex &index,
    const std::string &semantic_index_sha256) {
    ModelStageArtifacts result;
    result.packs.reserve(options.model_packs.size());
    result.pack_paths.reserve(options.model_packs.size());
    result.raw_pack_sha256s.reserve(options.model_packs.size());
    result.semantic_pack_sha256s.reserve(options.model_packs.size());
    for (const fs::path &configured_path : options.model_packs) {
        const fs::path path = fs::absolute(configured_path);
        core::LoadResult<core::ModelPackV2> loaded =
            core::load_model_pack_v2(path);
        if (!loaded.value) {
            fail(
                "model pack failed: " + path.string() + ": " +
                (loaded.diagnostics.empty() ? std::string("no diagnostic")
                                            : loaded.diagnostics.front()));
        }
        require_valid(
            core::validate_model_pack_v2(*loaded.value), "model pack");
        result.pack_paths.push_back(path);
        result.raw_pack_sha256s.push_back(loaded.observed_sha256);
        result.semantic_pack_sha256s.push_back(
            core::canonical_model_pack_semantic_sha256(*loaded.value));
        result.packs.push_back(std::move(*loaded.value));
    }
    core::LoadResult<core::ModelFactOverlay> executed =
        core::execute_model_packs_v2(
            result.packs, index, semantic_index_sha256);
    if (!executed.value) {
        fail(
            "model VM failed: " +
            (executed.diagnostics.empty() ? std::string("no diagnostic")
                                          : executed.diagnostics.front()));
    }
    result.overlay = std::move(*executed.value);
    require_valid(
        core::validate_model_fact_overlay(
            result.overlay, index, semantic_index_sha256),
        "model fact overlay");
    result.overlay_payload =
        core::canonical_model_fact_overlay_json(result.overlay) + '\n';
    result.overlay_sha256 = core::sha256_hex(result.overlay_payload);

    if (options.executor_capabilities) {
        const fs::path path = fs::absolute(*options.executor_capabilities);
        core::LoadResult<core::ExecutorCapabilityManifest> loaded =
            core::load_executor_capability_manifest(path);
        if (!loaded.value) {
            fail(
                "executor capability manifest failed: " + path.string() +
                ": " +
                (loaded.diagnostics.empty() ? std::string("no diagnostic")
                                            : loaded.diagnostics.front()));
        }
        require_valid(
            core::validate_executor_capability_manifest(*loaded.value),
            "executor capability manifest");
        result.executor_manifest_path = path;
        result.executor_manifest_sha256 = loaded.observed_sha256;
        result.executor_manifest = std::move(*loaded.value);
    }
    return result;
}

int run_index(const Options &options) {
    const core::CompilationPlan plan = plan_for(options);
    const core::SemanticIndex index = index_for(plan);
    const std::string payload = encoded_json(semantic_index_json(index));
    write_file_atomic(options.output, payload);
    std::cout << "PASS command=index status=" << status(index.status)
              << " translation_units=" << index.translation_units.size()
              << " nodes=" << index.nodes.size()
              << " output=" << options.output << '\n';
    return index.status == core::StageStatus::Failed ? 1 : 0;
}

int run_bind(const Options &options) {
    const core::CompilationPlan plan = plan_for(options);
    const core::SemanticIndex index = index_for(plan);
    const std::string index_payload = encoded_json(semantic_index_json(index));
    const std::string index_digest = core::sha256_hex(index_payload);
    core::TypedPropertyIr property = property_for(options);
    core::ApBindings bindings = core::bind_atomic_propositions(
        property, index, index_digest);
    core::ArtifactDigests expected;
    expected.property_ir_sha256 = property.artifact_sha256;
    expected.semantic_index_sha256 = index_digest;
    require_valid(
        core::validate_ap_bindings(bindings, property, index, expected),
        "AP bindings");
    if (options.index_output.has_value()) {
        write_file_atomic(*options.index_output, index_payload);
    }
    write_file_atomic(options.output, encoded_json(bindings_json(bindings)));
    std::cout << "PASS command=bind status=" << status(bindings.status)
              << " role_bindings=" << bindings.bindings.size()
              << " output=" << options.output << '\n';
    return bindings.status == core::StageStatus::Failed ? 1 : 0;
}

int run_influence(
    const Options &options, const fs::path &binary,
    const std::string &started_at) {
    const core::CompilationPlan plan = plan_for(options);
    core::SemanticIndex index = index_for(plan);
    trace_resource_phase("index-built");
    const std::size_t translation_unit_count = index.translation_units.size();
    OutputBundleStager bundle(options.output_directory);
    std::string index_payload = encoded_json(semantic_index_json(index));
    const std::string index_digest = core::sha256_hex(index_payload);
    bundle.write("semantic_index.json", index_payload);
    std::string().swap(index_payload);
    trim_released_heap();
    trace_resource_phase("index-staged");
    core::TypedPropertyIr property = property_for(options);
    core::ApBindings bindings = core::bind_atomic_propositions(
        property, index, index_digest);
    core::ArtifactDigests expected;
    expected.property_ir_sha256 = property.artifact_sha256;
    expected.semantic_index_sha256 = index_digest;
    require_valid(
        core::validate_ap_bindings(bindings, property, index, expected),
        "AP bindings");
    std::string bindings_payload =
        encoded_json(bindings_json(bindings));
    const std::string bindings_digest = core::sha256_hex(bindings_payload);
    bundle.write("ap_bindings.json", bindings_payload);
    std::string().swap(bindings_payload);
    trim_released_heap();
    trace_resource_phase("bindings-staged");

    core::InfluenceOptions influence_options;
    influence_options.call_string_limit = options.call_string_limit;
    core::ContextualInfluenceGraph graph =
        core::build_contextual_influence_graph(
            index, index_digest, influence_options);
    trace_resource_phase("graph-built");
    require_valid(
        core::validate_contextual_graph(graph, index_digest),
        "contextual influence graph");
    // The graph owns interned copies of all entity facts it exposes.  Once it
    // is validated, the large semantic index can be reduced to the exact
    // provenance/status subset needed by the detached certificate.
    core::SemanticIndex certificate_index;
    certificate_index.artifact_id = index.artifact_id;
    certificate_index.canonical_compilation_database_sha256 =
        index.canonical_compilation_database_sha256;
    certificate_index.path_map_sha256 = index.path_map_sha256;
    certificate_index.input_manifest_sha256 = index.input_manifest_sha256;
    certificate_index.status = index.status;
    certificate_index.input_files = std::move(index.input_files);
    certificate_index.coverage_gaps = std::move(index.coverage_gaps);
    certificate_index.diagnostics = std::move(index.diagnostics);
    index = core::SemanticIndex{};
    trim_released_heap();
    trace_resource_phase("index-released");

    const fs::path staged_graph =
        bundle.allocate("contextual_influence_graph.json");
    write_contextual_graph_stream(graph, staged_graph);
    const std::string graph_digest = file_sha256(staged_graph);
    trim_released_heap();
    trace_resource_phase("graph-staged");

    // Cone IDs and input commitments include the graph byte digest, so compute
    // cones after canonical graph serialization.
    core::ApInfluenceCones cones = core::compute_influence_cones(
        property, bindings, graph, bindings_digest, graph_digest);
    trace_resource_phase("cones-built");
    expected.ap_bindings_sha256 = bindings_digest;
    expected.graph_sha256 = graph_digest;
    require_valid(
        core::validate_influence_cones(cones, bindings, graph, expected),
        "AP influence cones");
    const fs::path staged_cones =
        bundle.allocate("ap_influence_cones.json");
    write_influence_cones_stream(cones, staged_cones);
    const std::string cones_digest = file_sha256(staged_cones);
    trim_released_heap();

    const std::string finished_at = utc_timestamp();
    llvm::json::Object certificate = certificate_json(
        options, binary, plan, property, certificate_index, bindings, graph, cones,
        index_digest, bindings_digest, graph_digest, cones_digest, started_at,
        finished_at);
    const std::string certificate_payload =
        encoded_json(std::move(certificate));
    bundle.write("analysis_certificate.json", certificate_payload);
    bundle.publish();

    const core::StageStatus aggregate = combined_status(
        {certificate_index.status, bindings.status, graph.status, cones.status});
    std::cout << "PASS command=influence status=" << status(aggregate)
              << " translation_units=" << translation_unit_count
              << " graph_nodes=" << graph.nodes.size()
              << " cones=" << cones.cones.size()
              << " output_dir=" << options.output_directory << '\n';
    return aggregate == core::StageStatus::Failed ? 1 : 0;
}

int run_guidance(
    const Options &raw_options, const fs::path &binary,
    const std::string &started_at) {
    // All certificate paths are absolute.  argv intentionally remains the
    // exact invocation so the M4 configuration commitment is not rewritten.
    const Options options = absolute_guidance_options(raw_options);
    const core::CompilationPlan plan = plan_for(options);
    core::SemanticIndex index = index_for(plan);
    trace_resource_phase("index-built");
    const std::size_t translation_unit_count = index.translation_units.size();
    OutputBundleStager bundle(options.output_directory);

    std::string index_payload = encoded_json(semantic_index_json(index));
    const std::string index_digest = core::sha256_hex(index_payload);
    bundle.write("semantic_index.json", index_payload);
    std::string().swap(index_payload);
    trim_released_heap();

    // Portability invariant: declarative models execute over canonical source
    // facts before any property is loaded.  A model pack therefore cannot
    // mention, observe, or specialize itself to an AP selector.
    ModelStageArtifacts model_stage =
        model_stage_for(options, index, index_digest);
    bundle.write("model_fact_overlay.json", model_stage.overlay_payload);
    trace_resource_phase("model-overlay-staged");

    core::TypedPropertyIr property = property_for(options);
    core::PredicateOccurrenceBindings predicate_occurrences =
        core::bind_predicate_occurrences(
            plan, property, index, index_digest);
    require_valid(
        core::validate_predicate_occurrence_bindings(
            predicate_occurrences, plan, property, index, index_digest),
        "predicate occurrence bindings");
    const std::string predicate_occurrences_payload =
        core::canonical_predicate_occurrence_bindings_json(
            predicate_occurrences) + '\n';
    const std::string predicate_occurrences_digest =
        core::sha256_hex(predicate_occurrences_payload);
    bundle.write(
        "predicate_occurrence_bindings.json",
        predicate_occurrences_payload);
    trace_resource_phase("predicate-occurrences-staged");

    core::ApBindings bindings = core::bind_atomic_propositions(
        property, index, index_digest);
    core::ArtifactDigests expected;
    expected.property_ir_sha256 = property.artifact_sha256;
    expected.semantic_index_sha256 = index_digest;
    require_valid(
        core::validate_ap_bindings(bindings, property, index, expected),
        "AP bindings");
    std::string bindings_payload = encoded_json(bindings_json(bindings));
    const std::string bindings_digest = core::sha256_hex(bindings_payload);
    bundle.write("ap_bindings.json", bindings_payload);
    std::string().swap(bindings_payload);
    trim_released_heap();

    core::InfluenceOptions influence_options;
    influence_options.call_string_limit = options.call_string_limit;
    core::ContextualInfluenceGraph graph =
        core::build_contextual_influence_graph(
            index, index_digest, influence_options);
    require_valid(
        core::validate_contextual_graph(graph, index_digest),
        "contextual influence graph");
    trace_resource_phase("graph-built");

    core::SemanticIndex certificate_index;
    certificate_index.artifact_id = index.artifact_id;
    certificate_index.canonical_compilation_database_sha256 =
        index.canonical_compilation_database_sha256;
    certificate_index.path_map_sha256 = index.path_map_sha256;
    certificate_index.input_manifest_sha256 = index.input_manifest_sha256;
    certificate_index.status = index.status;
    certificate_index.input_files = std::move(index.input_files);
    certificate_index.coverage_gaps = std::move(index.coverage_gaps);
    certificate_index.diagnostics = std::move(index.diagnostics);
    index = core::SemanticIndex{};
    trim_released_heap();

    const fs::path staged_graph =
        bundle.allocate("contextual_influence_graph.json");
    write_contextual_graph_stream(graph, staged_graph);
    const std::string graph_digest = file_sha256(staged_graph);

    core::ApInfluenceCones cones = core::compute_influence_cones(
        property, bindings, graph, bindings_digest, graph_digest);
    expected.ap_bindings_sha256 = bindings_digest;
    expected.graph_sha256 = graph_digest;
    require_valid(
        core::validate_influence_cones(cones, bindings, graph, expected),
        "AP influence cones");
    const fs::path staged_cones =
        bundle.allocate("ap_influence_cones.json");
    write_influence_cones_stream(cones, staged_cones);
    const std::string cones_digest = file_sha256(staged_cones);
    trace_resource_phase("cones-staged");

    core::FrontierInputDigests frontier_digests;
    frontier_digests.model_fact_overlay_sha256 =
        model_stage.overlay_sha256;
    frontier_digests.graph_sha256 = graph_digest;
    frontier_digests.cones_sha256 = cones_digest;
    frontier_digests.executor_manifest_sha256 =
        model_stage.executor_manifest_sha256;
    const core::FrontierOptions frontier_options;
    core::FrontierCandidates frontier_candidates =
        core::compute_frontier_candidates(
            model_stage.overlay, graph, cones, frontier_digests,
            model_stage.executor_manifest, frontier_options);
    require_valid(
        core::validate_frontier_candidates(
            frontier_candidates, model_stage.overlay, graph, cones,
            frontier_digests, model_stage.executor_manifest,
            frontier_options,
            core::FrontierValidationMode::Structural),
        "frontier candidates");
    const std::string frontier_candidates_payload =
        core::canonical_frontier_candidates_json(frontier_candidates) + '\n';
    const std::string frontier_candidates_digest =
        core::sha256_hex(frontier_candidates_payload);
    bundle.write("frontier_candidates.json", frontier_candidates_payload);

    core::FuzzableFrontier fuzzable_frontier =
        core::project_fuzzable_frontier(
            frontier_candidates, frontier_candidates_digest);
    require_valid(
        core::validate_fuzzable_frontier(
            fuzzable_frontier, frontier_candidates,
            frontier_candidates_digest),
        "fuzzable frontier");
    const std::string fuzzable_frontier_payload =
        core::canonical_fuzzable_frontier_json(fuzzable_frontier) + '\n';
    const std::string fuzzable_frontier_digest =
        core::sha256_hex(fuzzable_frontier_payload);
    bundle.write("fuzzable_frontier.json", fuzzable_frontier_payload);
    trace_resource_phase("frontier-staged");

    core::RecipeInputDigests recipe_digests;
    recipe_digests.property_ir_sha256 = property.artifact_sha256;
    recipe_digests.ap_bindings_sha256 = bindings_digest;
    recipe_digests.graph_sha256 = graph_digest;
    recipe_digests.cones_sha256 = cones_digest;
    recipe_digests.frontier_candidates_sha256 =
        frontier_candidates_digest;
    recipe_digests.model_fact_overlay_sha256 =
        model_stage.overlay_sha256;
    recipe_digests.predicate_occurrence_bindings_sha256 =
        predicate_occurrences_digest;
    core::RecipeOptions recipe_options;
    recipe_options.solver_timeout_ms = options.solver_timeout_ms;
    recipe_options.max_solver_queries = options.max_solver_queries;
    recipe_options.analyzer_core_sha256 =
        rift::build_manifest::kProductionCoreSha256;
    core::MutationRecipes recipes = core::build_mutation_recipes(
        property, bindings, graph, cones, frontier_candidates,
        model_stage.overlay, predicate_occurrences, recipe_digests,
        recipe_options);
    require_valid(
        core::validate_mutation_recipes(
            recipes, property, bindings, graph, cones,
            frontier_candidates, model_stage.overlay,
            predicate_occurrences, recipe_digests, recipe_options),
        "mutation recipes");
    const std::string recipes_payload =
        core::canonical_mutation_recipes_json(recipes) + '\n';
    const std::string recipes_digest = core::sha256_hex(recipes_payload);
    bundle.write("mutation_recipes.json", recipes_payload);

    core::RecipeReplayObligations replay_obligations =
        core::build_recipe_replay_obligations(recipes, recipes_digest);
    require_valid(
        core::validate_recipe_replay_obligations(
            replay_obligations, recipes, recipes_digest),
        "recipe replay obligations");
    const std::string replay_payload =
        core::canonical_recipe_replay_obligations_json(replay_obligations) +
        '\n';
    const std::string replay_digest = core::sha256_hex(replay_payload);
    bundle.write("recipe_replay_obligations.json", replay_payload);
    trace_resource_phase("recipes-staged");

    const std::vector<RuntimeComponentRecord> runtime_components =
        m5_runtime_components(binary, recipes.solver_contract.solver_version);
    const std::string finished_at = utc_timestamp();
    llvm::json::Object m4_certificate = certificate_json(
        options, binary, plan, property, certificate_index, bindings, graph,
        cones, index_digest, bindings_digest, graph_digest, cones_digest,
        started_at, finished_at);
    const std::optional<llvm::StringRef> m4_certificate_id_value =
        m4_certificate.getString("certificate_id");
    const std::optional<llvm::StringRef> m4_analysis_id_value =
        m4_certificate.getString("analysis_id");
    const llvm::json::Object *m4_analyzer =
        m4_certificate.getObject("analyzer");
    const std::optional<llvm::StringRef> configuration_value =
        m4_analyzer == nullptr
            ? std::optional<llvm::StringRef>{}
            : m4_analyzer->getString("configuration_sha256");
    if (!m4_certificate_id_value || !m4_analysis_id_value ||
        !configuration_value) {
        fail("M4 certificate omitted an identity commitment");
    }
    const std::string m4_certificate_id =
        m4_certificate_id_value->str();
    const std::string m4_analysis_id = m4_analysis_id_value->str();
    const std::string configuration_digest = configuration_value->str();
    const std::string m4_certificate_payload =
        encoded_json(std::move(m4_certificate));
    const std::string m4_certificate_digest =
        core::sha256_hex(m4_certificate_payload);
    bundle.write("analysis_certificate.json", m4_certificate_payload);

    llvm::json::Object m5_certificate = m5_certificate_json(
        options, binary, property, certificate_index, bindings, graph, cones,
        index_digest, bindings_digest, graph_digest, cones_digest,
        predicate_occurrences, predicate_occurrences_digest,
        m4_analysis_id, m4_certificate_id, m4_certificate_digest,
        configuration_digest, model_stage, frontier_candidates,
        frontier_candidates_digest, fuzzable_frontier,
        fuzzable_frontier_digest, recipes, recipes_digest,
        replay_obligations, replay_digest, runtime_components, started_at,
        finished_at);
    bundle.write(
        "m5_analysis_certificate.json",
        encoded_json(std::move(m5_certificate)));
    bundle.publish();

    const core::StageStatus aggregate = combined_status(
        {model_stage.overlay.status, predicate_occurrences.status,
         frontier_candidates.status, fuzzable_frontier.status,
         recipes.status});
    std::cout << "PASS command=" << options.command
              << " status=" << status(aggregate)
              << " translation_units=" << translation_unit_count
              << " graph_nodes=" << graph.nodes.size()
              << " cones=" << cones.cones.size()
              << " predicate_occurrences="
              << predicate_occurrences.occurrences.size()
              << " frontier_candidates="
              << frontier_candidates.candidates.size()
              << " actionable=" << fuzzable_frontier.actions.size()
              << " recipes=" << recipes.recipes.size()
              << " output_dir=" << options.output_directory << '\n';
    return aggregate == core::StageStatus::Failed ? 1 : 0;
}

}  // namespace

int run_production_cli(int argc, char **argv) {
    try {
        const std::string started_at = utc_timestamp();
        const Options options = parse_options(argc, argv);
        if (options.command == "index") {
            return run_index(options);
        }
        if (options.command == "bind") {
            return run_bind(options);
        }
        const fs::path binary =
            executable_path(argc > 0 ? argv[0] : nullptr);
        if (options.command == "influence") {
            return run_influence(options, binary, started_at);
        }
        return run_guidance(options, binary, started_at);
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}

}  // namespace rift::cli
