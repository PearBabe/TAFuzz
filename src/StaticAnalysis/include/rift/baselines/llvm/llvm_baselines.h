#ifndef RIFT_BASELINES_LLVM_LLVM_BASELINES_H
#define RIFT_BASELINES_LLVM_LLVM_BASELINES_H

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace rift::baselines::llvm {

struct SourceLocation {
    std::string file;
    std::uint32_t line = 0;
    std::uint32_t column = 0;

    friend bool operator==(const SourceLocation &, const SourceLocation &) = default;
};

// Stable IDs are caller-owned identities.  The baselines copy them exactly;
// they never derive IDs from names, locations, or benchmark metadata.
struct Anchor {
    std::string stable_id;
    std::string symbol;
    SourceLocation location;

    friend bool operator==(const Anchor &, const Anchor &) = default;
};

struct AnalysisInput {
    std::vector<std::string> bitcode_paths;
    std::vector<Anchor> source_anchors;
    std::vector<Anchor> ap_anchors;
};

enum class Method {
    LlvmSsaDefUse,
    LlvmMemorySsaAa,
    SvfBackwardValueFlow,
};

enum class PredictionStatus {
    Resolved,
    UnknownUnsupported,
};

enum class InfluenceClass {
    Unknown,
    NoInfluence,
    MayInfluence,
    MustInfluence,
};

enum class EdgeKind {
    SsaDefUse,
    MemoryDefUse,
    MemoryPhi,
    SvfDirect,
    SvfIndirect,
    SvfCall,
    SvfReturn,
    SvfThreadMhp,
};

enum class Certainty {
    Must,
    May,
    Unknown,
};

enum class AliasEvidence {
    NotApplicable,
    NoAlias,
    MayAlias,
    PartialAlias,
    MustAlias,
    Unknown,
};

enum class AnchorRole {
    Source,
    AtomicProposition,
};

struct ProgramPoint {
    std::string entity;
    std::string symbol;
    SourceLocation location;
};

struct EvidenceEdge {
    ProgramPoint from;
    ProgramPoint to;
    EdgeKind kind = EdgeKind::SsaDefUse;
    Certainty certainty = Certainty::May;
    AliasEvidence alias = AliasEvidence::NotApplicable;
    SourceLocation evidence_location;
    std::string explanation;
};

struct AnchorResolution {
    std::string stable_id;
    AnchorRole role = AnchorRole::Source;
    PredictionStatus status = PredictionStatus::UnknownUnsupported;
    std::vector<ProgramPoint> mapped_points;
    std::string reason;
};

struct PairPrediction {
    // The complete source x AP matrix is emitted in source-major/AP-minor
    // order.  These IDs are byte-for-byte copies of the input IDs.
    std::string source_stable_id;
    std::string ap_stable_id;
    PredictionStatus status = PredictionStatus::UnknownUnsupported;
    InfluenceClass influence = InfluenceClass::Unknown;
    std::vector<EvidenceEdge> evidence_path;
    std::vector<std::string> matched_facts;
    std::vector<std::string> limitations;
};

struct MethodProfile {
    Method method = Method::LlvmSsaDefUse;
    std::string name;
    std::vector<std::string> capabilities;
    std::vector<std::string> limitations;
};

struct AnalysisResult {
    MethodProfile profile;
    std::vector<AnchorResolution> anchor_resolutions;
    std::vector<PairPrediction> predictions;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] MethodProfile method_profile(Method method);
[[nodiscard]] AnalysisResult analyze(const AnalysisInput &input, Method method);

[[nodiscard]] std::string_view to_string(Method method);
[[nodiscard]] std::string_view to_string(PredictionStatus status);
[[nodiscard]] std::string_view to_string(InfluenceClass influence);
[[nodiscard]] std::string_view to_string(EdgeKind kind);
[[nodiscard]] std::string_view to_string(Certainty certainty);
[[nodiscard]] std::string_view to_string(AliasEvidence alias);
[[nodiscard]] std::string_view to_string(AnchorRole role);

}  // namespace rift::baselines::llvm

#endif
