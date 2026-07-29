#include "rift/baselines/ast/ast_baselines.h"
#include "production_main.h"
#ifdef RIFT_WITH_LLVM_BASELINES
#include "rift/baselines/llvm/llvm_baselines.h"
#endif

#include <clang/Basic/Version.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/ADT/SmallString.h>
#include <llvm/Config/llvm-config.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/Program.h>
#include <llvm/Support/SHA256.h>

#include <sys/resource.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace {

namespace fs = std::filesystem;
namespace ast = rift::baselines::ast;
#ifdef RIFT_WITH_LLVM_BASELINES
namespace llvm_baseline = rift::baselines::llvm;
#endif

struct Options {
    fs::path input;
    fs::path output;
    // Internal worker selector used to isolate process-global analysis state.
    // It is intentionally not part of the public baseline identity.
    std::optional<std::string> case_id;
    std::optional<ast::Method> ast_method;
#ifdef RIFT_WITH_LLVM_BASELINES
    std::optional<llvm_baseline::Method> llvm_method;
#endif
    std::vector<std::string> command;
};

struct ParsedCase {
    std::string id;
    std::string relative_source;
    ast::CaseInput input;
};

class ScopedCurrentPath {
  public:
    explicit ScopedCurrentPath(const fs::path &next)
        : previous_(fs::current_path()) {
        fs::current_path(next);
    }

    ScopedCurrentPath(const ScopedCurrentPath &) = delete;
    ScopedCurrentPath &operator=(const ScopedCurrentPath &) = delete;

    ~ScopedCurrentPath() {
        std::error_code ignored;
        fs::current_path(previous_, ignored);
    }

  private:
    fs::path previous_;
};

[[noreturn]] void fail(std::string message) {
    throw std::runtime_error(std::move(message));
}

std::string required_string(
    const llvm::json::Object &object, llvm::StringRef key,
    std::string_view context) {
    const std::optional<llvm::StringRef> value = object.getString(key);
    if (!value.has_value()) {
        fail(std::string(context) + ": missing string " + key.str());
    }
    return value->str();
}

std::uint32_t required_u32(
    const llvm::json::Object &object, llvm::StringRef key,
    std::string_view context) {
    const std::optional<std::int64_t> value = object.getInteger(key);
    if (!value.has_value() || *value < 1 ||
        static_cast<std::uint64_t>(*value) > UINT32_MAX) {
        fail(std::string(context) + ": invalid positive integer " + key.str());
    }
    return static_cast<std::uint32_t>(*value);
}

const llvm::json::Object &required_object(
    const llvm::json::Object &object, llvm::StringRef key,
    std::string_view context) {
    const llvm::json::Object *value = object.getObject(key);
    if (value == nullptr) {
        fail(std::string(context) + ": missing object " + key.str());
    }
    return *value;
}

const llvm::json::Array &required_array(
    const llvm::json::Object &object, llvm::StringRef key,
    std::string_view context) {
    const llvm::json::Array *value = object.getArray(key);
    if (value == nullptr) {
        fail(std::string(context) + ": missing array " + key.str());
    }
    return *value;
}

ast::Anchor parse_anchor(
    const llvm::json::Value &value, std::string_view context) {
    const llvm::json::Object *object = value.getAsObject();
    if (object == nullptr) {
        fail(std::string(context) + ": anchor is not an object");
    }
    const llvm::json::Object &location =
        required_object(*object, "location", context);
    return {
        required_string(*object, "id", context),
        required_string(*object, "symbol", context),
        {
            required_string(location, "file", context),
            required_u32(location, "line", context),
            required_u32(location, "column", context),
        },
    };
}

std::string read_file(const fs::path &path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        fail("cannot open " + path.string());
    }
    return std::string(
        std::istreambuf_iterator<char>(stream),
        std::istreambuf_iterator<char>());
}

std::string sha256_file(const fs::path &path) {
    const std::string bytes = read_file(path);
    const std::array<std::uint8_t, 32> digest = llvm::SHA256::hash(
        llvm::ArrayRef<std::uint8_t>(
            reinterpret_cast<const std::uint8_t *>(bytes.data()),
            bytes.size()));
    return llvm::toHex(digest, true);
}

bool same_path_argument(
    std::string_view argument, std::string_view relative_source) {
    return fs::path(argument).lexically_normal() ==
           fs::path(relative_source).lexically_normal();
}

bool launcher_name(std::string_view value) {
    const std::string name = fs::path(value).filename().string();
    return name == "ccache" || name == "sccache" || name == "distcc";
}

bool kept_option_with_operand(std::string_view option) {
    return option == "-I" || option == "-isystem" || option == "-iquote" ||
           option == "-idirafter" || option == "-include" ||
           option == "-imacros" || option == "-include-pch" ||
           option == "-iframework" || option == "-F" || option == "-D" ||
           option == "-U" || option == "-x" || option == "-target" ||
           option == "--target" || option == "-isysroot" ||
           option == "--sysroot" || option == "-resource-dir";
}

bool discarded_option_with_operand(std::string_view option) {
    return option == "-MF" || option == "-MT" || option == "-MQ" ||
           option == "-MJ" || option == "-dependency-file";
}

bool discarded_driver_flag(std::string_view option) {
    return option == "-c" || option == "-M" || option == "-MM" ||
           option == "-MD" || option == "-MMD" || option == "-MP";
}

std::vector<std::string> normalize_compile_flags(
    const llvm::json::Array &arguments, std::string_view relative_source) {
    std::vector<std::string> raw;
    for (const llvm::json::Value &value : arguments) {
        const std::optional<llvm::StringRef> argument = value.getAsString();
        if (!argument.has_value()) {
            fail("compile command contains a non-string argument");
        }
        raw.push_back(argument->str());
    }
    if (raw.empty()) {
        fail("compile command has no arguments");
    }

    std::size_t driver_index = 0;
    while (driver_index < raw.size() && launcher_name(raw[driver_index])) {
        ++driver_index;
    }
    if (driver_index >= raw.size()) {
        fail("compile command has a launcher but no compiler driver");
    }

    // buildASTFromCodeWithArgs accepts compiler flags, not a compiler driver,
    // input/output paths, dependency outputs, or compile-only driver actions.
    std::vector<std::string> flags;
    for (std::size_t index = driver_index + 1; index < raw.size(); ++index) {
        const std::string &argument = raw[index];
        if (discarded_driver_flag(argument)) {
            continue;
        }
        if (argument == "-o") {
            if (++index >= raw.size()) {
                fail("compile command ends after -o");
            }
            continue;
        }
        if (argument.rfind("-o", 0) == 0 && argument.size() > 2) {
            continue;
        }
        if (discarded_option_with_operand(argument)) {
            if (++index >= raw.size()) {
                fail("compile command ends after " + argument);
            }
            continue;
        }
        if (kept_option_with_operand(argument)) {
            if (index + 1 >= raw.size()) {
                fail("compile command ends after " + argument);
            }
            flags.push_back(argument);
            flags.push_back(raw[++index]);
            continue;
        }
        if (same_path_argument(argument, relative_source)) {
            continue;
        }
        flags.push_back(argument);
    }
    return flags;
}

std::vector<ParsedCase> parse_input(
    const fs::path &input_path, const llvm::json::Object &root) {
    if (required_string(root, "schema_version", "input") !=
        "rift.analyzer-input.v1") {
        fail("unsupported analyzer input schema");
    }
    if (required_string(root, "evaluation_track", "input") !=
            "PAIR_CLASSIFICATION_DIAGNOSTIC" ||
        required_string(root, "binding_mode", "input") !=
            "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED" ||
        required_string(root, "controllability_mode", "input") !=
            "GIVEN_CONTROLLABILITY_NOT_SCORED") {
        fail("unsupported evaluation-track contract");
    }
    const fs::path input_root = input_path.parent_path();
    std::vector<ParsedCase> cases;
    for (const llvm::json::Value &case_value :
         required_array(root, "cases", "input")) {
        const llvm::json::Object *case_object = case_value.getAsObject();
        if (case_object == nullptr) {
            fail("input case is not an object");
        }
        ParsedCase parsed;
        parsed.id = required_string(*case_object, "case_id", "case");
        const llvm::json::Object &source =
            required_object(*case_object, "source", parsed.id);
        const std::string relative_source =
            required_string(source, "file", parsed.id);
        parsed.relative_source = relative_source;
        const fs::path source_path = input_root / relative_source;
        if (sha256_file(source_path) !=
            required_string(source, "sha256", parsed.id)) {
            fail(parsed.id + ": source SHA-256 mismatch");
        }
        parsed.input.source_text = read_file(source_path);
        parsed.input.virtual_path = relative_source;
        parsed.input.language =
            source_path.extension() == ".c" ? "c11" : "c++20";

        const llvm::json::Object &compile =
            required_object(*case_object, "compile_command", parsed.id);
        if (required_string(compile, "directory", parsed.id) != ".") {
            fail(parsed.id + ": sanitized compile directory must be '.'");
        }
        parsed.input.compile_arguments = normalize_compile_flags(
            required_array(compile, "arguments", parsed.id), relative_source);

        for (const llvm::json::Value &anchor :
             required_array(*case_object, "source_anchors", parsed.id)) {
            parsed.input.source_anchors.push_back(
                parse_anchor(anchor, parsed.id + ":source"));
        }
        for (const llvm::json::Value &anchor :
             required_array(*case_object, "ap_anchors", parsed.id)) {
            parsed.input.property_anchors.push_back(
                parse_anchor(anchor, parsed.id + ":ap"));
        }
        (void)required_array(*case_object, "controllability", parsed.id);
        cases.push_back(std::move(parsed));
    }
    return cases;
}

llvm::json::Object location_json(const ast::SourceLocation &location) {
    return llvm::json::Object{
        {"file", location.file.empty() ? "<unknown>" : location.file},
        {"line", static_cast<std::int64_t>(std::max(1U, location.line))},
        {"column", static_cast<std::int64_t>(std::max(1U, location.column))},
    };
}

std::string edge_kind(ast::EdgeKind kind) {
    switch (kind) {
        case ast::EdgeKind::Assignment:
        case ast::EdgeKind::Initializer:
        case ast::EdgeKind::Data:
            return "data";
        case ast::EdgeKind::Control:
            return "control";
        case ast::EdgeKind::Call:
            return "call";
        case ast::EdgeKind::Return:
            return "return";
        case ast::EdgeKind::Field:
        case ast::EdgeKind::WriteSummary:
        case ast::EdgeKind::ConditionalRead:
            return "field";
        case ast::EdgeKind::Alias:
            return "alias";
    }
    return "unknown";
}

std::string certainty(ast::Certainty value) {
    switch (value) {
        case ast::Certainty::Must:
            return "MUST";
        case ast::Certainty::May:
            return "MAY";
        case ast::Certainty::Modelled:
            return "MODELLED";
        case ast::Certainty::Unknown:
            return "UNKNOWN";
    }
    return "UNKNOWN";
}

llvm::json::Array strings_json(const std::vector<std::string> &values) {
    llvm::json::Array result;
    for (const std::string &value : values) {
        result.push_back(value);
    }
    return result;
}

std::string joined_diagnostics(const std::vector<std::string> &diagnostics) {
    std::string result;
    for (const std::string &diagnostic : diagnostics) {
        if (!result.empty()) {
            result += "; ";
        }
        result += diagnostic;
    }
    return result.empty() ? "no diagnostic detail was emitted" : result;
}

llvm::json::Object evidence_json(
    std::string kind, std::string detail,
    llvm::json::Array locations = {}) {
    return llvm::json::Object{
        {"kind", std::move(kind)},
        {"detail", std::move(detail)},
        {"locations", std::move(locations)},
    };
}

llvm::json::Object edge_json(
    const ast::EvidenceEdge &edge,
    const std::vector<std::string> &limitations) {
    llvm::json::Array locations;
    locations.push_back(location_json(edge.evidence_location));
    llvm::json::Array evidence;
    evidence.push_back(evidence_json("AST", edge.explanation, std::move(locations)));
    const std::string edge_certainty = certainty(edge.certainty);
    return llvm::json::Object{
        {"from", edge.from.entity},
        {"to", edge.to.entity},
        {"kind", edge_kind(edge.kind)},
        {"certainty", edge_certainty},
        {"status", edge_certainty == "MUST" ? "CONFIRMED" : "CANDIDATE"},
        {"evidence", std::move(evidence)},
        {"limitations", strings_json(limitations)},
    };
}

llvm::json::Object prediction_json(
    const ast::PairPrediction &prediction,
    const std::vector<std::string> &diagnostics) {
    const bool tool_error =
        prediction.status == ast::PredictionStatus::ToolError;
    const bool unknown = prediction.status != ast::PredictionStatus::Resolved;
    std::string relation = "NO";
    if (unknown) {
        relation = "UNKNOWN";
    } else if (prediction.influence == ast::InfluenceClass::MustInfluence) {
        relation = "MUST";
    } else if (prediction.influence == ast::InfluenceClass::MayInfluence) {
        relation = "MAY";
    }

    llvm::json::Array edges;
    for (const ast::EvidenceEdge &edge : prediction.evidence_path) {
        edges.push_back(edge_json(edge, prediction.limitations));
    }
    llvm::json::Array evidence;
    llvm::json::Array anchor_locations;
    anchor_locations.push_back(location_json(prediction.source.location));
    anchor_locations.push_back(location_json(prediction.property.location));
    std::string detail = "pair classified by AST baseline";
    if (unknown) {
        detail = tool_error
                     ? "front-end/tool error: " + joined_diagnostics(diagnostics)
                     : "pair is outside the baseline's supported abstraction; facts: " +
                           joined_diagnostics(prediction.matched_facts) +
                           "; diagnostics: " + joined_diagnostics(diagnostics);
    } else if (relation == "NO") {
        detail =
            "no path in the baseline abstraction; this is not a proof of semantic non-influence";
    }
    evidence.push_back(
        evidence_json("AST", std::move(detail), std::move(anchor_locations)));

    return llvm::json::Object{
        {"source_id", prediction.source.id},
        {"ap_id", prediction.property.id},
        {"prediction", relation},
        {"status", tool_error ? "ERROR"
                              : unknown ? "UNSUPPORTED" : "ANALYZED"},
        {"edges", std::move(edges)},
        {"evidence", std::move(evidence)},
        {"limitations", strings_json(prediction.limitations)},
    };
}

llvm::json::Object case_json(
    const ParsedCase &input, const ast::AnalysisResult &result) {
    llvm::json::Array predictions;
    bool has_unknown = false;
    bool has_resolved = false;
    bool has_error = false;
    for (const ast::PairPrediction &prediction : result.predictions) {
        has_unknown |=
            prediction.status == ast::PredictionStatus::UnknownUnsupported;
        has_resolved |= prediction.status == ast::PredictionStatus::Resolved;
        has_error |= prediction.status == ast::PredictionStatus::ToolError;
        predictions.push_back(prediction_json(prediction, result.diagnostics));
    }
    std::string status = "COMPLETE";
    if (has_error) {
        status = "ERROR";
    } else if (has_unknown && has_resolved) {
        status = "PARTIAL";
    } else if (has_unknown) {
        status = "UNSUPPORTED";
    }
    return llvm::json::Object{
        {"case_id", input.id},
        {"status", status},
        {"predictions", std::move(predictions)},
        {"limitations", strings_json(result.profile.limitations)},
    };
}

#ifdef RIFT_WITH_LLVM_BASELINES

class TemporaryDirectory {
  public:
    TemporaryDirectory() {
        llvm::SmallString<256> created;
        const fs::path prefix =
            fs::temp_directory_path() / "tafuzz-sa-bitcode";
        if (const std::error_code error =
                llvm::sys::fs::createUniqueDirectory(prefix.string(), created)) {
            fail("cannot create temporary bitcode directory: " +
                 error.message());
        }
        path_ = created.str().str();
    }

    TemporaryDirectory(const TemporaryDirectory &) = delete;
    TemporaryDirectory &operator=(const TemporaryDirectory &) = delete;

    ~TemporaryDirectory() {
        (void)llvm::sys::fs::remove_directories(path_.string(), true);
    }

    [[nodiscard]] const fs::path &path() const { return path_; }

  private:
    fs::path path_;
};

struct BitcodeBuild {
    std::optional<fs::path> path;
    std::string error;
};

int execute_program(
    const std::string &program, const std::vector<std::string> &arguments,
    std::string &error) {
    std::vector<llvm::StringRef> refs;
    refs.reserve(arguments.size());
    for (const std::string &argument : arguments) {
        refs.emplace_back(argument);
    }
    bool execution_failed = false;
    const int status = llvm::sys::ExecuteAndWait(
        program, refs, std::nullopt, {}, 120, 0, &error, &execution_failed);
    if (execution_failed && error.empty()) {
        error = "failed to execute " + program;
    }
    return status;
}

BitcodeBuild build_bitcode(
    const ParsedCase &input, llvm_baseline::Method method,
    const TemporaryDirectory &temporary) {
    const char *compiler_name =
        fs::path(input.relative_source).extension() == ".c" ? "clang-18"
                                                              : "clang++-18";
    const auto compiler = llvm::sys::findProgramByName(compiler_name);
    if (!compiler) {
        return {std::nullopt, "cannot locate " + std::string(compiler_name)};
    }
    const fs::path memory_path = temporary.path() / (input.id + "-memory.bc");
    std::vector<std::string> command{
        *compiler,
    };
    command.insert(
        command.end(), input.input.compile_arguments.begin(),
        input.input.compile_arguments.end());
    command.insert(
        command.end(),
        {
            "-g",
            "-O0",
            "-fno-discard-value-names",
            "-Xclang",
            "-disable-O0-optnone",
            "-emit-llvm",
            "-c",
            input.relative_source,
            "-o",
            memory_path.string(),
        });
    std::string error;
    const int compile_status = execute_program(*compiler, command, error);
    if (compile_status != 0 || !fs::is_regular_file(memory_path)) {
        return {
            std::nullopt,
            "bitcode compiler exit=" + std::to_string(compile_status) +
                (error.empty() ? std::string{} : ": " + error),
        };
    }
    if (method != llvm_baseline::Method::LlvmSsaDefUse) {
        return {memory_path, {}};
    }

    const auto optimizer = llvm::sys::findProgramByName("opt-18");
    if (!optimizer) {
        return {std::nullopt, "cannot locate opt-18"};
    }
    const fs::path ssa_path = temporary.path() / (input.id + "-ssa.bc");
    std::vector<std::string> optimize{
        *optimizer,
        "-passes=mem2reg",
        memory_path.string(),
        "-o",
        ssa_path.string(),
    };
    error.clear();
    const int optimize_status = execute_program(*optimizer, optimize, error);
    if (optimize_status != 0 || !fs::is_regular_file(ssa_path)) {
        return {
            std::nullopt,
            "opt-18 exit=" + std::to_string(optimize_status) +
                (error.empty() ? std::string{} : ": " + error),
        };
    }
    return {ssa_path, {}};
}

llvm_baseline::Anchor llvm_anchor(const ast::Anchor &anchor) {
    return {
        anchor.id,
        anchor.symbol,
        {anchor.location.file, anchor.location.line, anchor.location.column},
    };
}

std::string llvm_edge_kind(llvm_baseline::EdgeKind kind) {
    switch (kind) {
        case llvm_baseline::EdgeKind::SsaDefUse:
        case llvm_baseline::EdgeKind::SvfDirect:
            return "data";
        case llvm_baseline::EdgeKind::MemoryDefUse:
        case llvm_baseline::EdgeKind::MemoryPhi:
        case llvm_baseline::EdgeKind::SvfIndirect:
            return "alias";
        case llvm_baseline::EdgeKind::SvfCall:
            return "call";
        case llvm_baseline::EdgeKind::SvfReturn:
            return "return";
        case llvm_baseline::EdgeKind::SvfThreadMhp:
            return "event_order";
    }
    return "unknown";
}

std::string llvm_certainty(llvm_baseline::Certainty value) {
    switch (value) {
        case llvm_baseline::Certainty::Must:
            return "MUST";
        case llvm_baseline::Certainty::May:
            return "MAY";
        case llvm_baseline::Certainty::Unknown:
            return "UNKNOWN";
    }
    return "UNKNOWN";
}

llvm::json::Object llvm_location_json(
    const llvm_baseline::SourceLocation &location) {
    return location_json(
        {location.file, location.line, location.column});
}

llvm::json::Object llvm_edge_json(
    const llvm_baseline::EvidenceEdge &edge,
    const std::vector<std::string> &limitations,
    std::string_view evidence_kind) {
    llvm::json::Array locations;
    locations.push_back(llvm_location_json(edge.evidence_location));
    llvm::json::Array evidence;
    evidence.push_back(evidence_json(
        std::string(evidence_kind),
        edge.explanation + "; alias=" +
            std::string(llvm_baseline::to_string(edge.alias)),
        std::move(locations)));
    const std::string certainty_value = llvm_certainty(edge.certainty);
    return llvm::json::Object{
        {"from", edge.from.entity},
        {"to", edge.to.entity},
        {"kind", llvm_edge_kind(edge.kind)},
        {"certainty", certainty_value},
        {"status", certainty_value == "MUST" ? "CONFIRMED" : "CANDIDATE"},
        {"evidence", std::move(evidence)},
        {"limitations", strings_json(limitations)},
    };
}

llvm::json::Object llvm_prediction_json(
    const llvm_baseline::PairPrediction &prediction,
    const std::vector<std::string> &diagnostics, std::string_view evidence_kind) {
    const bool unknown = prediction.status ==
                         llvm_baseline::PredictionStatus::UnknownUnsupported;
    std::string relation = "NO";
    if (unknown || prediction.influence ==
                       llvm_baseline::InfluenceClass::Unknown) {
        relation = "UNKNOWN";
    } else if (prediction.influence ==
               llvm_baseline::InfluenceClass::MustInfluence) {
        relation = "MUST";
    } else if (prediction.influence ==
               llvm_baseline::InfluenceClass::MayInfluence) {
        relation = "MAY";
    }

    llvm::json::Array edges;
    for (const llvm_baseline::EvidenceEdge &edge : prediction.evidence_path) {
        edges.push_back(
            llvm_edge_json(edge, prediction.limitations, evidence_kind));
    }
    if (relation != "NO" && relation != "UNKNOWN" && edges.empty()) {
        llvm::json::Array evidence;
        evidence.push_back(evidence_json(
            std::string(evidence_kind),
            "source and AP map to the same analysis node", {}));
        edges.push_back(llvm::json::Object{
            {"from", prediction.source_stable_id},
            {"to", prediction.ap_stable_id},
            {"kind", "data"},
            {"certainty", "MAY"},
            {"status", "CANDIDATE"},
            {"evidence", std::move(evidence)},
            {"limitations", strings_json(prediction.limitations)},
        });
    }
    llvm::json::Array evidence;
    evidence.push_back(evidence_json(
        std::string(evidence_kind),
        unknown
            ? "unsupported mapping/construct; facts: " +
                  joined_diagnostics(prediction.matched_facts) +
                  "; diagnostics: " + joined_diagnostics(diagnostics)
            : "pair classified by backward graph traversal; facts: " +
                  joined_diagnostics(prediction.matched_facts),
        {}));
    return llvm::json::Object{
        {"source_id", prediction.source_stable_id},
        {"ap_id", prediction.ap_stable_id},
        {"prediction", relation},
        {"status", unknown ? "UNSUPPORTED" : "ANALYZED"},
        {"edges", std::move(edges)},
        {"evidence", std::move(evidence)},
        {"limitations", strings_json(prediction.limitations)},
    };
}

llvm::json::Object llvm_case_json(
    const ParsedCase &input, const llvm_baseline::AnalysisResult &result,
    llvm_baseline::Method method) {
    const std::string_view evidence_kind =
        method == llvm_baseline::Method::SvfBackwardValueFlow ? "SVF" : "LLVM";
    llvm::json::Array predictions;
    bool has_unknown = false;
    bool has_resolved = false;
    for (const llvm_baseline::PairPrediction &prediction : result.predictions) {
        has_unknown |= prediction.status ==
                       llvm_baseline::PredictionStatus::UnknownUnsupported;
        has_resolved |= prediction.status ==
                        llvm_baseline::PredictionStatus::Resolved;
        predictions.push_back(llvm_prediction_json(
            prediction, result.diagnostics, evidence_kind));
    }
    std::string status = "COMPLETE";
    if (has_unknown && has_resolved) {
        status = "PARTIAL";
    } else if (has_unknown) {
        status = "UNSUPPORTED";
    }
    return llvm::json::Object{
        {"case_id", input.id},
        {"status", status},
        {"predictions", std::move(predictions)},
        {"limitations", strings_json(result.profile.limitations)},
    };
}

llvm::json::Object llvm_error_case_json(
    const ParsedCase &input, const std::vector<std::string> &limitations,
    const std::string &error, std::string_view evidence_kind = "LLVM") {
    llvm::json::Array predictions;
    for (const ast::Anchor &source : input.input.source_anchors) {
        for (const ast::Anchor &ap : input.input.property_anchors) {
            llvm::json::Array evidence;
            llvm::json::Array locations;
            locations.push_back(location_json(source.location));
            locations.push_back(location_json(ap.location));
            evidence.push_back(evidence_json(
                std::string(evidence_kind), "analysis tool error: " + error,
                std::move(locations)));
            predictions.push_back(llvm::json::Object{
                {"source_id", source.id},
                {"ap_id", ap.id},
                {"prediction", "UNKNOWN"},
                {"status", "ERROR"},
                {"edges", llvm::json::Array{}},
                {"evidence", std::move(evidence)},
                {"limitations", strings_json(limitations)},
            });
        }
    }
    return llvm::json::Object{
        {"case_id", input.id},
        {"status", "ERROR"},
        {"predictions", std::move(predictions)},
        {"limitations", strings_json(limitations)},
    };
}

llvm::json::Object isolated_svf_error_case_json(
    const ParsedCase &input, const std::vector<std::string> &limitations,
    std::string detail) {
    return llvm_error_case_json(
        input, limitations, "isolated SVF worker: " + std::move(detail),
        "SVF");
}

llvm::json::Object run_isolated_svf_case(
    const ParsedCase &input, std::size_t ordinal,
    const std::vector<std::string> &limitations,
    const fs::path &binary_path, const fs::path &input_path,
    const TemporaryDirectory &temporary) {
    const fs::path child_output =
        temporary.path() /
        ("svf-isolated-case-" + std::to_string(ordinal) + ".json");
    std::vector<std::string> child_command{
        binary_path.string(),
        "baseline",
        "--method",
        "svf-value-flow",
        "--input",
        input_path.string(),
        "--output",
        child_output.string(),
        "--case-id",
        input.id,
    };
    std::string execution_error;
    const int child_status = execute_program(
        binary_path.string(), child_command, execution_error);

    std::error_code file_error;
    const bool child_output_exists =
        fs::is_regular_file(child_output, file_error);
    if (!child_output_exists || file_error) {
        std::string detail =
            "exit=" + std::to_string(child_status) +
            ", result file was not produced";
        if (file_error) {
            detail += ": " + file_error.message();
        }
        if (!execution_error.empty()) {
            detail += ": " + execution_error;
        }
        return isolated_svf_error_case_json(
            input, limitations, std::move(detail));
    }

    std::string child_text;
    try {
        child_text = read_file(child_output);
    } catch (const std::exception &error) {
        return isolated_svf_error_case_json(
            input, limitations,
            "exit=" + std::to_string(child_status) +
                ", cannot read result: " + error.what());
    }
    llvm::Expected<llvm::json::Value> parsed_child =
        llvm::json::parse(child_text);
    if (!parsed_child) {
        return isolated_svf_error_case_json(
            input, limitations,
            "exit=" + std::to_string(child_status) +
                ", invalid result JSON: " +
                llvm::toString(parsed_child.takeError()));
    }
    llvm::json::Object *child_root = parsed_child->getAsObject();
    if (child_root == nullptr ||
        child_root->getString("schema_version") !=
            std::optional<llvm::StringRef>("rift.baseline-result.v1")) {
        return isolated_svf_error_case_json(
            input, limitations,
            "exit=" + std::to_string(child_status) +
                ", result root/schema is invalid");
    }
    llvm::json::Array *child_cases = child_root->getArray("cases");
    if (child_cases == nullptr || child_cases->size() != 1) {
        return isolated_svf_error_case_json(
            input, limitations,
            "exit=" + std::to_string(child_status) +
                ", worker did not emit exactly one case");
    }
    llvm::json::Object *child_case = (*child_cases)[0].getAsObject();
    if (child_case == nullptr ||
        child_case->getString("case_id") !=
            std::optional<llvm::StringRef>(input.id)) {
        return isolated_svf_error_case_json(
            input, limitations,
            "exit=" + std::to_string(child_status) +
                ", worker returned the wrong case identity");
    }

    const std::optional<llvm::StringRef> case_status =
        child_case->getString("status");
    if (child_status != 0 &&
        (!case_status.has_value() || *case_status != "ERROR")) {
        std::string detail =
            "exit=" + std::to_string(child_status) +
            ", non-error result was discarded";
        if (!execution_error.empty()) {
            detail += ": " + execution_error;
        }
        return isolated_svf_error_case_json(
            input, limitations, std::move(detail));
    }
    return std::move(*child_case);
}

#endif

Options parse_options(std::span<char *> arguments) {
    if (arguments.size() < 2 || std::string_view(arguments[1]) != "baseline") {
        fail(
            "usage: tafuzz-sa baseline --method METHOD --input FILE "
            "--output FILE [--case-id ID]");
    }
    Options options;
    for (char *argument : arguments) {
        options.command.emplace_back(argument);
    }
    for (std::size_t index = 2; index < arguments.size(); ++index) {
        const std::string_view option = arguments[index];
        if (index + 1 >= arguments.size()) {
            fail("missing value after " + std::string(option));
        }
        const std::string value = arguments[++index];
        if (option == "--input") {
            options.input = value;
        } else if (option == "--output") {
            options.output = value;
        } else if (option == "--case-id") {
            if (value.empty()) {
                fail("--case-id cannot be empty");
            }
            options.case_id = value;
        } else if (option == "--method") {
            // Repeated --method options are permitted with conventional
            // last-one-wins semantics.  Clear the other backend family so a
            // stale earlier selection cannot silently override the last
            // value during dispatch.
            options.ast_method.reset();
#ifdef RIFT_WITH_LLVM_BASELINES
            options.llvm_method.reset();
#endif
            if (value == "adgfuzz-assignment") {
                options.ast_method = ast::Method::AdgAssignment;
            } else if (value == "moonshine-rw") {
                options.ast_method = ast::Method::MoonShineRw;
            } else if (value == "plain-pdg") {
                options.ast_method = ast::Method::PlainPdg;
#ifdef RIFT_WITH_LLVM_BASELINES
            } else if (value == "llvm-def-use") {
                options.llvm_method = llvm_baseline::Method::LlvmSsaDefUse;
            } else if (value == "memoryssa-aa") {
                options.llvm_method = llvm_baseline::Method::LlvmMemorySsaAa;
            } else if (value == "svf-value-flow") {
                options.llvm_method =
                    llvm_baseline::Method::SvfBackwardValueFlow;
#endif
            } else {
                fail("unsupported baseline method " + value);
            }
        } else {
            fail("unknown option " + std::string(option));
        }
    }
    bool method_selected = options.ast_method.has_value();
#ifdef RIFT_WITH_LLVM_BASELINES
    method_selected = method_selected || options.llvm_method.has_value();
#endif
    if (options.input.empty() || options.output.empty() || !method_selected) {
        fail("--method, --input, and --output are required");
    }
    return options;
}

llvm::json::Object analyzer_json(
    const Options &options, const std::string &profile_name,
    const std::string &implementation, const fs::path &executable,
    bool svf_process_isolation_used) {
    llvm::json::Array command;
    for (const std::string &argument : options.command) {
        command.push_back(argument);
    }
    llvm::json::Object configuration;
    configuration["method"] = profile_name;
    configuration["evaluation_track"] = "PAIR_CLASSIFICATION_DIAGNOSTIC";
    configuration["candidate_binding_mode"] =
        "GIVEN_CANDIDATE_ANCHORS_NOT_SCORED";
    configuration["controllability_mode"] =
        "GIVEN_CONTROLLABILITY_NOT_SCORED";
    configuration["execution_receipt_scope"] =
        "PROCESS_START_THROUGH_PREFLIGHT_SERIALIZATION";
    configuration["headline_performance_source"] =
        "EXTERNAL_PROCESS_RUNNER_REQUIRED";
#ifdef RIFT_WITH_LLVM_BASELINES
    if (options.llvm_method ==
        llvm_baseline::Method::SvfBackwardValueFlow) {
        std::string role = "DIRECT_SINGLE_CASE";
        if (options.case_id.has_value()) {
            role = "ISOLATED_SINGLE_CASE_WORKER";
        } else if (svf_process_isolation_used) {
            role = "MULTI_CASE_AGGREGATOR";
        }
        std::string mode = "NOT_REQUIRED_SINGLE_CASE";
        if (options.case_id.has_value()) {
            mode = "SINGLE_CASE_WORKER";
        } else if (svf_process_isolation_used) {
            mode = "PER_CASE_SUBPROCESS";
        }
        configuration["svf_process_isolation"] = llvm::json::Object{
            {"mode", std::move(mode)},
            {"role", std::move(role)},
            {"case_selector", "--case-id"},
            {"reason", "SVF 3.2 process-global analysis state"},
        };
    }
#else
    (void)svf_process_isolation_used;
#endif
    return llvm::json::Object{
        {"id", profile_name},
        {"version", "0.1.0-m3"},
        {"implementation", implementation},
        {"configuration", std::move(configuration)},
        {"command", std::move(command)},
        {"artifact_sha256", sha256_file(executable)},
    };
}

fs::path executable_path(const char *argv0) {
    std::error_code error;
    const fs::path proc_path = fs::read_symlink("/proc/self/exe", error);
    if (!error && fs::is_regular_file(proc_path)) {
        return fs::canonical(proc_path);
    }

    error.clear();
    if (std::string_view(argv0).find('/') != std::string_view::npos) {
        const fs::path path = fs::weakly_canonical(argv0, error);
        if (!error && fs::is_regular_file(path)) {
            return path;
        }
    }
    const char *environment_path = std::getenv("PATH");
    if (environment_path != nullptr) {
        std::string paths(environment_path);
        std::size_t begin = 0;
        while (begin <= paths.size()) {
            const std::size_t end = paths.find(':', begin);
            const std::string directory = paths.substr(begin, end - begin);
            const fs::path candidate =
                (directory.empty() ? fs::current_path() : fs::path(directory)) /
                argv0;
            error.clear();
            const fs::path canonical = fs::weakly_canonical(candidate, error);
            if (!error && fs::is_regular_file(canonical)) {
                return canonical;
            }
            if (end == std::string::npos) {
                break;
            }
            begin = end + 1;
        }
    }
    fail("cannot resolve analyzer executable path from argv[0]");
}

llvm::json::Array toolchain_json() {
    llvm::json::Array toolchain;
    toolchain.push_back(llvm::json::Object{
        {"name", "LLVM"}, {"version", LLVM_VERSION_STRING}});
    toolchain.push_back(llvm::json::Object{
        {"name", "Clang"}, {"version", clang::getClangFullVersion()}});
    return toolchain;
}

llvm::json::Object execution_json(
    int exit_code, double wall_seconds,
    std::optional<std::int64_t> peak_rss_bytes,
    std::size_t analyzed_units) {
    return llvm::json::Object{
        {"exit_code", exit_code},
        {"wall_seconds", wall_seconds},
        {"peak_rss_bytes",
         peak_rss_bytes.has_value() ? llvm::json::Value(*peak_rss_bytes)
                                    : llvm::json::Value(nullptr)},
        {"toolchain", toolchain_json()},
        {"analyzed_units", static_cast<std::int64_t>(analyzed_units)},
    };
}

}  // namespace

int main(int argc, char **argv) {
    if (argc > 1) {
        const std::string_view command = argv[1];
        if (command == "index" || command == "bind" ||
            command == "influence") {
            return rift::cli::run_production_cli(argc, argv);
        }
    }
    try {
        const auto start = std::chrono::steady_clock::now();
        const Options options =
            parse_options(std::span<char *>(argv, static_cast<std::size_t>(argc)));
        const fs::path input_path = fs::weakly_canonical(options.input);
        const fs::path output_path = fs::absolute(options.output);
        const fs::path binary_path = executable_path(argv[0]);
        const std::string input_text = read_file(input_path);
        llvm::Expected<llvm::json::Value> parsed = llvm::json::parse(input_text);
        if (!parsed) {
            fail("invalid analyzer input JSON: " +
                 llvm::toString(parsed.takeError()));
        }
        const llvm::json::Object *root = parsed->getAsObject();
        if (root == nullptr) {
            fail("analyzer input root is not an object");
        }
        std::vector<ParsedCase> cases = parse_input(input_path, *root);
        if (options.case_id.has_value()) {
            std::vector<ParsedCase> selected;
            for (ParsedCase &input : cases) {
                if (input.id == *options.case_id) {
                    selected.push_back(std::move(input));
                }
            }
            if (selected.size() != 1) {
                fail("--case-id must identify exactly one input case: " +
                     *options.case_id);
            }
            cases = std::move(selected);
        }
        std::string profile_name;
        std::string implementation;
        std::vector<std::string> profile_limitations;
        if (options.ast_method.has_value()) {
            const ast::MethodProfile profile =
                ast::method_profile(*options.ast_method);
            profile_name = profile.name;
            profile_limitations = profile.limitations;
            implementation =
                "TAFuzz project-neutral Clang AST weak baseline";
        }
#ifdef RIFT_WITH_LLVM_BASELINES
        if (options.llvm_method.has_value()) {
            const llvm_baseline::MethodProfile profile =
                llvm_baseline::method_profile(*options.llvm_method);
            profile_name = profile.name;
            profile_limitations = profile.limitations;
            implementation =
                "TAFuzz project-neutral LLVM 18/SVF 3.2 weak baseline";
        }
        std::unique_ptr<TemporaryDirectory> bitcode_directory;
        if (options.llvm_method.has_value()) {
            bitcode_directory = std::make_unique<TemporaryDirectory>();
        }
#endif
        const ScopedCurrentPath input_working_directory(input_path.parent_path());

        bool svf_process_isolation_used = false;
#ifdef RIFT_WITH_LLVM_BASELINES
        svf_process_isolation_used =
            options.llvm_method ==
                llvm_baseline::Method::SvfBackwardValueFlow &&
            !options.case_id.has_value() && cases.size() > 1;
#endif

        llvm::json::Array case_results;
        bool any_partial = false;
        bool all_unsupported = true;
        bool any_error = false;
        std::size_t analyzed_units = 0;
        for (const ParsedCase &input : cases) {
            llvm::json::Object object;
            if (options.ast_method.has_value()) {
                const ast::AnalysisResult result =
                    ast::analyze(input.input, *options.ast_method);
                object = case_json(input, result);
            }
#ifdef RIFT_WITH_LLVM_BASELINES
            else if (options.llvm_method.has_value()) {
                if (svf_process_isolation_used) {
                    object = run_isolated_svf_case(
                        input, case_results.size(),
                        profile_limitations, binary_path, input_path,
                        *bitcode_directory);
                } else {
                    const BitcodeBuild bitcode = build_bitcode(
                        input, *options.llvm_method, *bitcode_directory);
                    if (!bitcode.path.has_value()) {
                        object = llvm_error_case_json(
                            input, profile_limitations, bitcode.error);
                    } else {
                        llvm_baseline::AnalysisInput analysis_input;
                        analysis_input.bitcode_paths = {
                            bitcode.path->string()};
                        for (const ast::Anchor &anchor :
                             input.input.source_anchors) {
                            analysis_input.source_anchors.push_back(
                                llvm_anchor(anchor));
                        }
                        for (const ast::Anchor &anchor :
                             input.input.property_anchors) {
                            analysis_input.ap_anchors.push_back(
                                llvm_anchor(anchor));
                        }
                        const llvm_baseline::AnalysisResult result =
                            llvm_baseline::analyze(
                                analysis_input, *options.llvm_method);
                        object = llvm_case_json(
                            input, result, *options.llvm_method);
                    }
                }
            }
#endif
            else {
                fail("no baseline method was selected");
            }
            const std::optional<llvm::StringRef> status = object.getString("status");
            any_error |= status.has_value() && *status == "ERROR";
            any_partial |= status.has_value() &&
                           (*status == "PARTIAL" || *status == "UNSUPPORTED");
            all_unsupported &= status.has_value() && *status == "UNSUPPORTED";
            analyzed_units += status.has_value() && *status != "ERROR" ? 1 : 0;
            case_results.push_back(std::move(object));
        }

        std::string analysis_status = "COMPLETE";
        if (any_error) {
            analysis_status = "ERROR";
        } else if (all_unsupported) {
            analysis_status = "UNSUPPORTED";
        } else if (any_partial) {
            analysis_status = "PARTIAL";
        }
        llvm::json::Object result{
            {"schema_version", "rift.baseline-result.v1"},
            {"analyzer", analyzer_json(
                             options, profile_name, implementation,
                             binary_path, svf_process_isolation_used)},
            {"input_manifest_sha256", sha256_file(input_path)},
            {"analysis_status", analysis_status},
            {"execution", execution_json(any_error ? 1 : 0, 0.0, std::nullopt,
                                          analyzed_units)},
            {"cases", std::move(case_results)},
            {"limitations", strings_json(profile_limitations)},
        };

        // Serialize once before sampling so the self-reported peak includes
        // result construction and JSON allocation. Final write time is still
        // excluded; publication-grade performance uses an external runner.
        llvm::json::Value result_value(std::move(result));
        const std::string preflight =
            llvm::formatv("{0:2}\n", result_value).str();
        (void)preflight;
        const auto elapsed = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - start);
        struct rusage usage {};
        const int usage_status = getrusage(RUSAGE_SELF, &usage);
        const std::optional<std::int64_t> peak_rss =
            usage_status == 0
                ? std::optional<std::int64_t>(
                      static_cast<std::int64_t>(usage.ru_maxrss) * 1024)
                : std::nullopt;
        result_value.getAsObject()->operator[]("execution") = execution_json(
            any_error ? 1 : 0, elapsed.count(), peak_rss, analyzed_units);
        const std::string encoded =
            llvm::formatv("{0:2}\n", result_value).str();

        fs::create_directories(output_path.parent_path());
        std::ofstream output(output_path, std::ios::binary);
        if (!output) {
            fail("cannot write " + output_path.string());
        }
        output << encoded;
        if (!output) {
            fail("failed while writing " + output_path.string());
        }
        std::cout << (any_error ? "ERROR" : "PASS")
                  << " method=" << profile_name
                  << " cases=" << cases.size()
                  << " output=" << output_path << '\n';
        return any_error ? 1 : 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
