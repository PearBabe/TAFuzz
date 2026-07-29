#ifndef RIFT_CORE_TYPES_H
#define RIFT_CORE_TYPES_H

#include <cstdint>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

namespace rift::core {

enum class StageStatus {
    Complete,
    ConservativeIncomplete,
    Failed,
};

enum class Certainty {
    Must,
    May,
    Modelled,
    Unknown,
};

enum class GapEffect {
    PrecisionLoss,
    SoundnessRisk,
    StageFailure,
};

enum class EntityKind {
    Function,
    Method,
    Constructor,
    Destructor,
    Parameter,
    Local,
    Global,
    Field,
    Type,
    Expression,
    Synthetic,
    Unknown,
};

enum class IdentityStatus {
    Exact,
    Summary,
    Unknown,
};

enum class ValueKind {
    Boolean,
    Integer,
    Floating,
    Enumeration,
    BitVector,
    Timestamp,
    Duration,
    Pointer,
    Record,
    Array,
    Unknown,
};

enum class SemanticNodeKind {
    Declaration,
    Definition,
    Expression,
    Value,
    Memory,
    CallSite,
    ReturnSite,
    Control,
    Synthetic,
    Unknown,
};

enum class RelationKind {
    Defines,
    Uses,
    Loads,
    Stores,
    Data,
    Control,
    Call,
    Return,
    Object,
    Field,
    Alias,
    Contains,
    MapsTo,
    Unknown,
};

enum class LifecyclePhase {
    Constructed,
    Initialized,
    Active,
    Committed,
    Cancelled,
    Destroyed,
    Reused,
    Unknown,
};

enum class TaskKind {
    Thread,
    Task,
    Interrupt,
    Callback,
    Scheduler,
    Process,
    Unknown,
};

enum class ObjectAbstraction {
    Value,
    Global,
    Stack,
    Heap,
    Receiver,
    Summary,
    Unknown,
};

struct SourceLocation {
    std::string file;
    std::uint32_t line = 0;
    std::uint32_t column = 0;
    std::uint32_t end_line = 0;
    std::uint32_t end_column = 0;
    std::string location_kind = "spelling";
    std::vector<std::string> macro_stack;

    friend bool operator==(const SourceLocation &, const SourceLocation &) = default;
};

struct ValueType {
    ValueKind kind = ValueKind::Unknown;
    std::string canonical = "unknown";
    std::optional<std::uint32_t> bit_width;
    std::optional<bool> is_signed;
    std::optional<std::string> unit;

    friend bool operator==(const ValueType &, const ValueType &) = default;
};

struct CoverageGap {
    std::string gap_id;
    std::string kind;
    GapEffect effect = GapEffect::PrecisionLoss;
    std::string detail;
    std::vector<SourceLocation> locations;
    std::vector<std::string> affected_ids;

    friend bool operator==(const CoverageGap &, const CoverageGap &) = default;
};

enum class InputFileRole {
    Main,
    UserHeader,
    Generated,
    System,
    Toolchain,
};

struct InputFileDigest {
    std::string input_file_id;
    std::string logical_path;
    std::string sha256;
    InputFileRole role = InputFileRole::UserHeader;
    std::uint64_t byte_size = 0;
    // Non-canonical provenance only. These physical paths must never
    // participate in semantic IDs or canonical analysis artifact bytes.
    // They allow the detached certificate verifier to rehash the exact files
    // whose loaded buffers were consumed by Clang.
    std::vector<std::string> observed_paths;
};

struct EntityRef {
    std::string entity_id;
    EntityKind kind = EntityKind::Unknown;
    IdentityStatus identity_status = IdentityStatus::Unknown;
    std::optional<std::string> usr;
    std::optional<std::string> qualified_signature;
    std::optional<std::string> canonical_type;
    std::vector<SourceLocation> declarations;
    std::vector<SourceLocation> definitions;
    std::set<std::string> translation_unit_ids;
};

struct AbstractObject {
    std::string object_id;
    ObjectAbstraction abstraction = ObjectAbstraction::Unknown;
    std::optional<SourceLocation> allocation_site;
    Certainty certainty = Certainty::Unknown;
};

// An access path is rooted at a semantic entity.  A parameter-rooted path is
// deliberately independent of a particular caller and is instantiated at a
// callsite before it is admitted to the contextual graph.
struct AccessPath {
    std::string root_entity_id;
    std::uint32_t dereference_depth = 0;
    std::vector<std::string> fields;
    bool unknown_suffix = false;

    friend bool operator==(const AccessPath &, const AccessPath &) = default;
};

struct SemanticNode {
    std::string node_id;
    SemanticNodeKind kind = SemanticNodeKind::Unknown;
    std::string entity_id;
    std::string owner_function_id;
    std::optional<AccessPath> access_path;
    std::optional<std::string> abstract_object_id;
    ValueType value_type;
    SourceLocation location;
    std::string ast_kind;
};

struct Evidence {
    std::string evidence_id;
    std::string kind;
    Certainty certainty = Certainty::Unknown;
    std::string fact;
    std::string producer;
    std::optional<SourceLocation> location;
};

struct SemanticRelation {
    std::string relation_id;
    std::string source_node_id;
    std::string target_node_id;
    RelationKind kind = RelationKind::Unknown;
    Certainty certainty = Certainty::Unknown;
    std::vector<Evidence> evidence;
    std::optional<std::string> callsite_id;
    std::vector<std::string> condition_node_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct TranslationUnitRecord {
    std::string translation_unit_id;
    std::string source_file;
    std::string language;
    std::string working_directory;
    std::string command_sha256;
    StageStatus status = StageStatus::Failed;
    std::vector<std::string> input_file_ids;
    std::vector<std::string> diagnostics;
};

struct CallSiteSummary {
    std::string callsite_id;
    std::string caller_function_id;
    std::vector<std::string> candidate_callee_ids;
    std::vector<std::string> argument_node_ids;
    // Positional groups preserve the actual-to-formal relation when an
    // expression conservatively denotes more than one abstract object.
    std::vector<std::vector<std::string>> argument_node_groups;
    std::vector<bool> argument_is_address;
    std::optional<std::string> receiver_node_id;
    std::optional<std::string> result_node_id;
    SourceLocation location;
    bool direct = false;
    StageStatus status = StageStatus::ConservativeIncomplete;
    std::vector<std::string> uncertainty_reasons;
};

struct FunctionSummary {
    std::string function_entity_id;
    std::vector<std::string> parameter_node_ids;
    std::optional<std::string> receiver_node_id;
    std::optional<std::string> return_node_id;
    std::vector<std::string> owned_node_ids;
    std::vector<std::string> relation_ids;
    std::vector<std::string> callsite_ids;
    StageStatus status = StageStatus::Complete;
    std::vector<std::string> uncertainty_reasons;
};

struct SemanticIndex {
    std::string artifact_id;
    std::string identity_scheme;
    std::string compilation_database_sha256;
    std::string canonical_compilation_database_sha256;
    std::string path_map_sha256;
    std::string input_manifest_sha256;
    std::vector<std::string> logical_root_ids;
    std::string source_identity_root;
    StageStatus status = StageStatus::Failed;
    std::vector<TranslationUnitRecord> translation_units;
    std::vector<InputFileDigest> input_files;
    std::vector<EntityRef> entities;
    std::vector<AbstractObject> abstract_objects;
    std::vector<SemanticNode> nodes;
    std::vector<SemanticRelation> relations;
    std::vector<FunctionSummary> function_summaries;
    std::vector<CallSiteSummary> callsites;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct CallContext {
    std::vector<std::string> callsite_ids;
    bool truncated = false;
};

struct TaskContext {
    TaskKind kind = TaskKind::Unknown;
    std::optional<std::string> context_id;
    Certainty certainty = Certainty::Unknown;
};

struct ScopeContext {
    std::string scope_id;
    std::vector<std::string> key_node_ids;
    IdentityStatus status = IdentityStatus::Unknown;
};

struct GenerationContext {
    IdentityStatus kind = IdentityStatus::Unknown;
    std::optional<std::string> identity;
    bool reuse_possible = true;
};

struct ContextualNode {
    std::string node_id;
    std::string semantic_node_id;
    SemanticNodeKind kind = SemanticNodeKind::Unknown;
    // Entity metadata is immutable and heavily repeated across contextual
    // instances. Interning it avoids copying every declaration/definition/TU
    // set into every program point while preserving the standalone JSON.
    std::shared_ptr<const EntityRef> entity;
    AbstractObject abstract_object;
    std::vector<std::string> field_path;
    CallContext call_context;
    LifecyclePhase lifecycle_phase = LifecyclePhase::Unknown;
    TaskContext task_context;
    ScopeContext scope;
    GenerationContext generation;
    SourceLocation location;
    ValueType value_type;
    std::vector<Evidence> evidence;
};

struct InfluenceEdge {
    std::string edge_id;
    std::string source_node_id;
    std::string target_node_id;
    RelationKind kind = RelationKind::Unknown;
    Certainty certainty = Certainty::Unknown;
    // The same semantic relation is instantiated in many call contexts.
    // Share immutable evidence rather than copying its strings per edge.
    std::shared_ptr<const std::vector<Evidence>> evidence;
    std::vector<std::string> condition_node_ids;
    std::vector<std::string> uncertainty_reasons;
};

struct ContextualInfluenceGraph {
    std::string artifact_id;
    std::string semantic_index_sha256;
    std::uint32_t call_string_limit = 1;
    std::string object_sensitivity = "hybrid";
    std::string field_sensitivity = "full";
    StageStatus status = StageStatus::Failed;
    std::vector<ContextualNode> nodes;
    std::vector<InfluenceEdge> edges;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

[[nodiscard]] std::string stable_id(
    const std::string &prefix, const std::string &semantic_material);
[[nodiscard]] std::string sha256_hex(const std::string &bytes);
[[nodiscard]] std::string sha256_file(const std::filesystem::path &path);

[[nodiscard]] const char *to_string(StageStatus value);
[[nodiscard]] const char *to_string(Certainty value);
[[nodiscard]] const char *to_string(RelationKind value);
[[nodiscard]] const char *to_string(InputFileRole value);

}  // namespace rift::core

#endif
