#ifndef RIFT_CORE_INDEX_H
#define RIFT_CORE_INDEX_H

#include "rift/core/types.h"
#include "rift/core/value_transfer.h"

#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

inline constexpr const char *kIdentityScheme = "rift.identity/2.0.0";
inline constexpr const char *kPathMapScheme = "rift.path-map/1.0.0";

struct LogicalPathRoot {
    std::string root_id;
    std::filesystem::path physical_root;
};

struct CompilationCommand {
    std::string translation_unit_id;
    std::string working_directory;
    std::string source_file;
    std::vector<std::string> arguments;
    std::string logical_working_directory;
    std::string logical_source_file;
    std::string raw_command_sha256;
    std::string command_sha256;
};

struct CompilationPlan {
    std::string compilation_database_path;
    std::string compilation_database_sha256;
    std::string canonical_compilation_database_sha256;
    std::string path_map_sha256;
    std::string source_identity_root;
    std::vector<LogicalPathRoot> identity_roots;
    StageStatus status = StageStatus::Failed;
    std::vector<CompilationCommand> commands;
    std::vector<CoverageGap> coverage_gaps;
    std::vector<std::string> diagnostics;
};

struct CompilationPlanOptions {
    std::optional<std::filesystem::path> source_identity_root;
    // Optional project-neutral logical roots.  When omitted, `source` is
    // derived from source_identity_root/common source parent and `build` from
    // the compilation database directory.  Physical paths are execution-only;
    // stable IDs use riftpath://v1/<root-id>/... logical paths.
    std::vector<LogicalPathRoot> identity_roots;
    bool require_all_identity_paths_mapped = true;
    // The JSON Compilation Database format is commonly generated with a
    // relative directory.  Such paths are resolved against the database file,
    // never the analyzer process cwd.  Strict callers may still reject them.
    bool require_absolute_working_directories = false;
};

struct IndexOptions {
    std::uint32_t maximum_field_depth = 8;
    std::uint32_t maximum_dereference_depth = 4;
    bool include_system_headers = false;
    bool retain_macro_stack = true;
};

struct IndexBuildArtifacts {
    SemanticIndex index;
    SemanticValueTransferIndex value_transfers;
};

[[nodiscard]] std::optional<std::string> logical_identity_path(
    const std::vector<LogicalPathRoot> &roots,
    const std::filesystem::path &physical_path);
[[nodiscard]] std::string canonicalize_identity_text(
    const std::vector<LogicalPathRoot> &roots, std::string text);
[[nodiscard]] std::string identity_path_map_sha256(
    const std::vector<LogicalPathRoot> &roots);

[[nodiscard]] CompilationPlan load_compilation_plan(
    const std::filesystem::path &compile_commands_json,
    const CompilationPlanOptions &options = {});

// Runs the exact raw commands represented by the plan through Clang Tooling;
// no benchmark metadata or property file is accepted by this stage.
[[nodiscard]] SemanticIndex build_semantic_index(
    const CompilationPlan &plan, const IndexOptions &options = {});

// Builds the property-independent semantic index and typed value-transfer
// sidecar during the same Clang AST traversal. The legacy API above delegates
// to this implementation and discards only the additive sidecar.
[[nodiscard]] IndexBuildArtifacts build_semantic_index_with_value_transfers(
    const CompilationPlan &plan, const IndexOptions &options = {},
    const ValueTransferOptions &transfer_options = {});

}  // namespace rift::core

#endif
