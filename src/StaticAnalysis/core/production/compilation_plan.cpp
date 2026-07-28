#include "rift/core/index.h"

#include <clang/Tooling/JSONCompilationDatabase.h>
#include <clang/Basic/Version.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <set>
#include <sstream>
#include <system_error>
#include <vector>

namespace rift::core {
namespace {

std::string read_bytes(const std::filesystem::path &path, std::string &error) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        error = "cannot open compilation database: " + path.string();
        return {};
    }
    std::string bytes{
        std::istreambuf_iterator<char>(stream),
        std::istreambuf_iterator<char>()};
    if (!stream.good() && !stream.eof()) {
        error = "cannot read compilation database: " + path.string();
        return {};
    }
    return bytes;
}

std::filesystem::path absolute_normalized(
    const std::filesystem::path &path,
    const std::filesystem::path &base = {}) {
    std::error_code error;
    std::filesystem::path result = path;
    if (result.is_relative()) {
        result = base.empty() ? std::filesystem::absolute(result, error)
                              : std::filesystem::absolute(base / result, error);
    }
    result = error ? path.lexically_normal() : result.lexically_normal();
    while (result != result.root_path() && result.filename().empty()) {
        result = result.parent_path();
    }
    return result;
}

std::filesystem::path common_parent(
    const std::vector<std::filesystem::path> &files) {
    if (files.empty()) {
        return {};
    }
    std::filesystem::path common = files.front().parent_path();
    for (std::size_t index = 1; index < files.size(); ++index) {
        const std::filesystem::path candidate = files[index].parent_path();
        auto left = common.begin();
        auto right = candidate.begin();
        std::filesystem::path prefix;
        while (left != common.end() && right != candidate.end() &&
               *left == *right) {
            prefix /= *left;
            ++left;
            ++right;
        }
        common = prefix;
        if (common.empty()) {
            break;
        }
    }
    return common;
}

std::string command_material(
    const clang::tooling::CompileCommand &command) {
    std::ostringstream stream;
    stream << command.Directory << '\0' << command.Filename << '\0';
    for (const std::string &argument : command.CommandLine) {
        stream << argument.size() << ':' << argument << '\0';
    }
    return stream.str();
}

bool valid_root_id(const std::string &value) {
    if (value.empty() || value.size() > 64 || value.front() < 'a' ||
        value.front() > 'z') {
        return false;
    }
    return std::all_of(
        value.begin() + 1, value.end(), [](const char character) {
            return (character >= 'a' && character <= 'z') ||
                   (character >= '0' && character <= '9') ||
                   character == '.' || character == '_' || character == '-';
        });
}

std::filesystem::path canonical_root(const std::filesystem::path &path) {
    const std::filesystem::path absolute = absolute_normalized(path);
    std::error_code error;
    const std::filesystem::path canonical =
        std::filesystem::weakly_canonical(absolute, error);
    return error ? absolute : canonical.lexically_normal();
}

bool roots_contain_physical(
    const std::vector<LogicalPathRoot> &roots,
    const std::filesystem::path &physical) {
    const std::filesystem::path canonical = canonical_root(physical);
    return std::any_of(
        roots.begin(), roots.end(), [&](const LogicalPathRoot &root) {
            return canonical_root(root.physical_root) == canonical;
        });
}

std::optional<std::filesystem::path> absolute_argument_path(
    const std::string &argument) {
    const std::vector<std::string> prefixes = {
        "-I", "-F", "-L", "--sysroot=", "-resource-dir=",
        "-include", "-imacros"};
    if (std::filesystem::path(argument).is_absolute()) {
        return std::filesystem::path(argument);
    }
    for (const std::string &prefix : prefixes) {
        if (argument.starts_with(prefix) && argument.size() > prefix.size()) {
            const std::filesystem::path value(argument.substr(prefix.size()));
            if (value.is_absolute()) {
                return value;
            }
        }
    }
    return std::nullopt;
}

bool contains_unmapped_absolute_path(const std::string &argument) {
    for (std::size_t index = 0; index < argument.size(); ++index) {
        if (index + 2 < argument.size() &&
            (index == 0 || argument[index - 1] == '=' ||
             argument[index - 1] == ',' || argument[index - 1] == ';' ||
             argument[index - 1] == '\'' || argument[index - 1] == '"') &&
            ((argument[index] >= 'A' && argument[index] <= 'Z') ||
             (argument[index] >= 'a' && argument[index] <= 'z')) &&
            argument[index + 1] == ':' &&
            (argument[index + 2] == '/' || argument[index + 2] == '\\')) {
            return true;
        }
        if (argument[index] != '/') {
            continue;
        }
        if (index >= 9 &&
            argument.substr(index - 9, 9) == "riftpath:") {
            continue;
        }
        if (index > 0 && argument[index - 1] == '/') {
            continue;
        }
        if (index == 0 || argument[index - 1] == '=' ||
            argument[index - 1] == ',' || argument[index - 1] == ':' ||
            argument[index - 1] == '\'' || argument[index - 1] == '"') {
            return true;
        }
    }
    return argument.starts_with("\\\\");
}

std::optional<std::string> canonical_command_material(
    const clang::tooling::CompileCommand &command,
    const std::filesystem::path &directory,
    const std::filesystem::path &source,
    const std::vector<LogicalPathRoot> &roots,
    std::string &failure_reason) {
    const std::optional<std::string> logical_directory =
        logical_identity_path(roots, directory);
    const std::optional<std::string> logical_source =
        logical_identity_path(roots, source);
    if (!logical_directory || !logical_source) {
        failure_reason = "source or working directory is unmapped";
        return std::nullopt;
    }
    std::ostringstream stream;
    stream << kIdentityScheme << '\0' << *logical_directory << '\0'
           << *logical_source << '\0' << "clang-major="
           << CLANG_VERSION_MAJOR << '\0';
    for (std::size_t index = 0; index < command.CommandLine.size(); ++index) {
        std::string argument = command.CommandLine[index];
        if (index == 0) {
            argument = std::filesystem::path(argument).filename().string();
        } else if (argument.starts_with('@')) {
            // Response files require content-addressed expansion.  Until that
            // is represented in the canonical command, fail closed instead of
            // hashing a machine-dependent response-file path.
            failure_reason = "response files are not content-canonicalized";
            return std::nullopt;
        } else if (const std::optional<std::filesystem::path> path =
                       absolute_argument_path(argument)) {
            if (!logical_identity_path(roots, *path)) {
                failure_reason =
                    "absolute command argument at position " +
                    std::to_string(index) + " is unmapped";
                return std::nullopt;
            }
            argument = canonicalize_identity_text(roots, argument);
        } else {
            argument = canonicalize_identity_text(roots, argument);
        }
        if (contains_unmapped_absolute_path(argument)) {
            failure_reason =
                "canonical command argument at position " +
                std::to_string(index) +
                " retains a machine-absolute path";
            return std::nullopt;
        }
        stream << argument.size() << ':' << argument << '\0';
    }
    return stream.str();
}

CoverageGap gap(
    const std::string &kind, GapEffect effect, const std::string &detail,
    const std::string &material) {
    return {
        stable_id("gap", kind + '\0' + material),
        kind,
        effect,
        detail,
        {},
        {},
    };
}

}  // namespace

CompilationPlan load_compilation_plan(
    const std::filesystem::path &compile_commands_json,
    const CompilationPlanOptions &options) {
    CompilationPlan plan;
    const std::filesystem::path absolute_db =
        absolute_normalized(compile_commands_json);
    const std::filesystem::path database_directory = absolute_db.parent_path();
    plan.compilation_database_path = absolute_db.string();

    std::string read_error;
    const std::string bytes = read_bytes(absolute_db, read_error);
    if (!read_error.empty()) {
        plan.diagnostics.push_back(read_error);
        plan.coverage_gaps.push_back(gap(
            "compile_database_read", GapEffect::StageFailure, read_error,
            absolute_db.string()));
        return plan;
    }
    plan.compilation_database_sha256 = sha256_hex(bytes);

    std::string parse_error;
    std::unique_ptr<clang::tooling::JSONCompilationDatabase> database =
        clang::tooling::JSONCompilationDatabase::loadFromFile(
            absolute_db.string(), parse_error,
            clang::tooling::JSONCommandLineSyntax::AutoDetect);
    if (!database) {
        plan.diagnostics.push_back(
            "invalid compilation database: " + parse_error);
        plan.coverage_gaps.push_back(gap(
            "compile_database_parse", GapEffect::StageFailure,
            "Clang could not parse the raw compilation database",
            parse_error));
        return plan;
    }

    const std::vector<clang::tooling::CompileCommand> raw_commands =
        database->getAllCompileCommands();
    if (raw_commands.empty()) {
        plan.diagnostics.push_back("compilation database contains no commands");
        plan.coverage_gaps.push_back(gap(
            "empty_compile_database", GapEffect::StageFailure,
            "At least one authoritative translation-unit command is required",
            plan.compilation_database_sha256));
        return plan;
    }

    std::vector<std::filesystem::path> identity_inputs;
    identity_inputs.reserve(raw_commands.size() * 2);
    for (const clang::tooling::CompileCommand &command : raw_commands) {
        const std::filesystem::path directory =
            absolute_normalized(command.Directory, database_directory);
        const std::filesystem::path source =
            absolute_normalized(command.Filename, directory);
        identity_inputs.push_back(source);
        // common_parent() consumes file-like paths.  A stable sentinel makes
        // the working directory itself participate in default root inference.
        identity_inputs.push_back(directory / ".rift-working-directory");
    }
    const std::filesystem::path identity_root = options.source_identity_root
                                                    ? canonical_root(
                                                          *options.source_identity_root)
                                                    : canonical_root(
                                                          common_parent(identity_inputs));
    if (identity_root.empty()) {
        plan.diagnostics.push_back(
            "source identity root could not be derived; supply it explicitly");
        plan.coverage_gaps.push_back(gap(
            "source_identity_root", GapEffect::StageFailure,
            "A path-independent identity root is required", absolute_db.string()));
        return plan;
    }
    std::vector<LogicalPathRoot> roots = options.identity_roots;
    if (roots.empty()) {
        if (options.source_identity_root) {
            roots.push_back({"source", identity_root});
            if (!roots_contain_physical(roots, database_directory)) {
                roots.push_back({"build", canonical_root(database_directory)});
            }
        } else {
            roots.push_back({"project", identity_root});
        }
    }
    std::set<std::string> root_ids;
    std::map<std::filesystem::path, std::string> physical_roots;
    for (LogicalPathRoot &root : roots) {
        root.physical_root = canonical_root(root.physical_root);
        if (!valid_root_id(root.root_id) ||
            !root_ids.insert(root.root_id).second) {
            plan.diagnostics.push_back(
                "identity path map has an invalid or duplicate root ID");
            plan.coverage_gaps.push_back(gap(
                "invalid_identity_root", GapEffect::StageFailure,
                "Logical root IDs must be unique lower-case stable names",
                root.root_id));
            return plan;
        }
        const auto [found, inserted] =
            physical_roots.emplace(root.physical_root, root.root_id);
        if (!inserted) {
            plan.diagnostics.push_back(
                "identity path map aliases one physical root with multiple logical IDs");
            plan.coverage_gaps.push_back(gap(
                "ambiguous_identity_root", GapEffect::StageFailure,
                "Canonical physical roots must map to exactly one logical root",
                found->second + '\0' + root.root_id));
            return plan;
        }
    }
    std::sort(
        roots.begin(), roots.end(),
        [](const LogicalPathRoot &left, const LogicalPathRoot &right) {
            return left.root_id < right.root_id;
        });
    plan.identity_roots = roots;
    plan.path_map_sha256 = identity_path_map_sha256(roots);
    plan.source_identity_root =
        std::string(kIdentityScheme) + ':' + plan.path_map_sha256;

    std::set<std::string> command_identities;
    std::vector<std::string> canonical_commands;
    bool identity_failure = false;
    for (std::size_t index = 0; index < raw_commands.size(); ++index) {
        const clang::tooling::CompileCommand &raw = raw_commands[index];
        const std::filesystem::path directory =
            absolute_normalized(raw.Directory, database_directory);
        const std::filesystem::path source =
            absolute_normalized(raw.Filename, directory);
        if (options.require_absolute_working_directories &&
            !std::filesystem::path(raw.Directory).is_absolute()) {
            const std::string detail =
                "relative working directory in compile command for " +
                raw.Filename;
            plan.diagnostics.push_back(detail);
            plan.coverage_gaps.push_back(gap(
                "relative_compile_directory", GapEffect::StageFailure,
                detail, std::to_string(index)));
            continue;
        }
        const std::string raw_material = command_material(raw);
        std::string canonical_failure;
        const std::optional<std::string> canonical_material =
            canonical_command_material(
                raw, directory, source, roots, canonical_failure);
        const std::optional<std::string> logical_directory =
            logical_identity_path(roots, directory);
        const std::optional<std::string> logical_source =
            logical_identity_path(roots, source);
        if (!canonical_material || !logical_directory || !logical_source) {
            identity_failure = true;
            plan.diagnostics.push_back(
                "compile command contains an unmapped identity path at ordinal " +
                std::to_string(index) + ": " + canonical_failure);
            plan.coverage_gaps.push_back(gap(
                "unmapped_compile_path", GapEffect::StageFailure,
                "Every source, working directory, and absolute command path must map to a logical root",
                std::to_string(index)));
            continue;
        }
        const std::string raw_digest = sha256_hex(raw_material);
        const std::string digest = sha256_hex(*canonical_material);
        const std::string identity =
            std::string(kIdentityScheme) + '\0' + *logical_source + '\0' +
            digest;
        if (!command_identities.insert(identity).second) {
            // Duplicate records are ignored deterministically.  They do not
            // reduce semantic coverage because the command bytes are equal.
            continue;
        }
        CompilationCommand command;
        command.translation_unit_id = stable_id("tu", identity);
        command.working_directory = directory.string();
        command.source_file = source.string();
        command.arguments = raw.CommandLine;
        command.logical_working_directory = *logical_directory;
        command.logical_source_file = *logical_source;
        command.raw_command_sha256 = raw_digest;
        command.command_sha256 = digest;
        plan.commands.push_back(std::move(command));
        canonical_commands.push_back(*canonical_material);
    }

    if (identity_failure && options.require_all_identity_paths_mapped) {
        plan.commands.clear();
        plan.status = StageStatus::Failed;
        return plan;
    }
    if (plan.commands.empty()) {
        plan.status = StageStatus::Failed;
        if (plan.diagnostics.empty()) {
            plan.diagnostics.push_back("no usable translation-unit commands");
        }
        return plan;
    }
    std::sort(canonical_commands.begin(), canonical_commands.end());
    std::ostringstream canonical_database;
    canonical_database << kIdentityScheme << '\0' << plan.path_map_sha256;
    for (const std::string &command : canonical_commands) {
        canonical_database << '\0' << command.size() << ':' << command;
    }
    plan.canonical_compilation_database_sha256 =
        sha256_hex(canonical_database.str());
    plan.status = plan.coverage_gaps.empty()
                      ? StageStatus::Complete
                      : StageStatus::ConservativeIncomplete;
    return plan;
}

}  // namespace rift::core
