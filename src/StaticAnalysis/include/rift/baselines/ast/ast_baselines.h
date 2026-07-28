#ifndef RIFT_BASELINES_AST_AST_BASELINES_H
#define RIFT_BASELINES_AST_AST_BASELINES_H

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace rift::baselines::ast {

struct SourceLocation {
    std::string file;
    std::uint32_t line = 0;
    std::uint32_t column = 0;

    friend bool operator==(const SourceLocation &, const SourceLocation &) = default;
};

// Anchors are supplied by the caller.  The library neither discovers nor
// renames AP/source anchors from benchmark metadata.
struct Anchor {
    std::string id;
    std::string symbol;
    SourceLocation location;

    friend bool operator==(const Anchor &, const Anchor &) = default;
};

struct CaseInput {
    std::string source_text;
    std::string virtual_path;
    std::string language = "c++20";
    // Arguments are passed directly to Clang Tooling's
    // buildASTFromCodeWithArgs. Supply compilation flags only (for example,
    // -std=, -I, and -D); do not include a compiler executable, -c, -o, an
    // output path, or the input source path. A compile-database adapter may
    // normalize full commands before constructing CaseInput.
    std::vector<std::string> compile_arguments;
    std::vector<Anchor> source_anchors;
    std::vector<Anchor> property_anchors;
};

enum class Method {
    AdgAssignment,
    MoonShineRw,
    PlainPdg,
};

enum class InfluenceClass {
    NoInfluence,
    MayInfluence,
    MustInfluence,
};

enum class PredictionStatus {
    Resolved,
    UnknownUnsupported,
    ToolError,
};

enum class EdgeKind {
    Assignment,
    Initializer,
    Data,
    Control,
    Call,
    Return,
    Field,
    Alias,
    WriteSummary,
    ConditionalRead,
};

enum class Certainty {
    Must,
    May,
    Modelled,
    Unknown,
};

struct ProgramPoint {
    std::string entity;
    std::string symbol;
    SourceLocation location;
};

struct EvidenceEdge {
    ProgramPoint from;
    ProgramPoint to;
    EdgeKind kind = EdgeKind::Data;
    Certainty certainty = Certainty::May;
    SourceLocation evidence_location;
    std::string explanation;
};

struct PairPrediction {
    Anchor source;
    Anchor property;
    PredictionStatus status = PredictionStatus::Resolved;
    InfluenceClass influence = InfluenceClass::NoInfluence;
    std::vector<EvidenceEdge> evidence_path;
    std::vector<std::string> matched_facts;
    std::vector<std::string> limitations;
};

struct MethodProfile {
    Method method = Method::AdgAssignment;
    std::string name;
    std::vector<std::string> capabilities;
    std::vector<std::string> limitations;
};

struct AnalysisResult {
    MethodProfile profile;
    std::vector<PairPrediction> predictions;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] MethodProfile method_profile(Method method);
[[nodiscard]] AnalysisResult analyze(const CaseInput &input, Method method);

[[nodiscard]] std::string_view to_string(Method method);
[[nodiscard]] std::string_view to_string(InfluenceClass influence);
[[nodiscard]] std::string_view to_string(PredictionStatus status);
[[nodiscard]] std::string_view to_string(EdgeKind kind);
[[nodiscard]] std::string_view to_string(Certainty certainty);

}  // namespace rift::baselines::ast

#endif
