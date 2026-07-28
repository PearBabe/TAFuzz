#include "rift/core/index.h"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <iomanip>
#include <optional>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace rift::core {
namespace {

std::filesystem::path normalized_absolute(
    const std::filesystem::path &path) {
    std::error_code error;
    std::filesystem::path result = path;
    if (result.is_relative()) {
        result = std::filesystem::absolute(result, error);
    }
    if (!error) {
        const std::filesystem::path canonical =
            std::filesystem::weakly_canonical(result, error);
        if (!error) {
            result = canonical;
        }
    }
    return result.lexically_normal();
}

bool below(
    const std::filesystem::path &path,
    const std::filesystem::path &root) {
    const std::filesystem::path relative = path.lexically_relative(root);
    if (relative.empty()) {
        return path == root;
    }
    const std::string text = relative.generic_string();
    return relative.is_relative() && text != ".." &&
           !text.starts_with("../");
}

std::string percent_encode_path(const std::string &value) {
    std::ostringstream stream;
    stream << std::uppercase << std::hex << std::setfill('0');
    for (const unsigned char byte : value) {
        const bool unreserved =
            std::isalnum(byte) != 0 || byte == '-' || byte == '.' ||
            byte == '_' || byte == '~' || byte == '/';
        if (unreserved) {
            stream << static_cast<char>(byte);
        } else {
            stream << '%' << std::setw(2) << static_cast<unsigned>(byte);
        }
    }
    return stream.str();
}

std::string logical_root_uri(const std::string &root_id) {
    return "riftpath://v1/" + root_id;
}

}  // namespace

std::optional<std::string> logical_identity_path(
    const std::vector<LogicalPathRoot> &roots,
    const std::filesystem::path &physical_path) {
    const std::filesystem::path path = normalized_absolute(physical_path);
    const LogicalPathRoot *selected = nullptr;
    std::filesystem::path selected_root;
    std::size_t selected_depth = 0;
    bool ambiguous = false;
    for (const LogicalPathRoot &candidate : roots) {
        const std::filesystem::path root =
            normalized_absolute(candidate.physical_root);
        if (!below(path, root)) {
            continue;
        }
        const std::size_t depth = static_cast<std::size_t>(
            std::distance(root.begin(), root.end()));
        if (selected == nullptr || depth > selected_depth) {
            selected = &candidate;
            selected_root = root;
            selected_depth = depth;
            ambiguous = false;
        } else if (depth == selected_depth &&
                   (candidate.root_id != selected->root_id ||
                    root != selected_root)) {
            ambiguous = true;
        }
    }
    if (selected == nullptr || ambiguous) {
        return std::nullopt;
    }
    const std::filesystem::path relative = path.lexically_relative(selected_root);
    const std::string suffix = relative.empty() || relative == "."
                                   ? std::string()
                                   : percent_encode_path(relative.generic_string());
    return logical_root_uri(selected->root_id) + '/' + suffix;
}

std::string canonicalize_identity_text(
    const std::vector<LogicalPathRoot> &roots, std::string text) {
    std::vector<std::pair<std::string, std::string>> replacements;
    for (const LogicalPathRoot &root : roots) {
        const std::filesystem::path physical =
            normalized_absolute(root.physical_root);
        replacements.emplace_back(
            physical.generic_string(), logical_root_uri(root.root_id));
        const std::string native = physical.string();
        if (native != physical.generic_string()) {
            replacements.emplace_back(native, logical_root_uri(root.root_id));
        }
    }
    std::sort(
        replacements.begin(), replacements.end(),
        [](const auto &left, const auto &right) {
            if (left.first.size() != right.first.size()) {
                return left.first.size() > right.first.size();
            }
            return left.first < right.first;
        });
    for (const auto &[physical, logical] : replacements) {
        std::size_t position = 0;
        while (!physical.empty() &&
               (position = text.find(physical, position)) !=
                   std::string::npos) {
            const std::size_t end = position + physical.size();
            const bool path_boundary =
                end == text.size() || text[end] == '/' || text[end] == '\\' ||
                text[end] == '=' || text[end] == ',' || text[end] == ';' ||
                text[end] == ':' || text[end] == '\'' || text[end] == '"';
            if (!path_boundary) {
                position = end;
                continue;
            }
            text.replace(position, physical.size(), logical);
            position += logical.size();
        }
    }
    return text;
}

std::string identity_path_map_sha256(
    const std::vector<LogicalPathRoot> &roots) {
    std::vector<std::string> ids;
    ids.reserve(roots.size());
    for (const LogicalPathRoot &root : roots) {
        ids.push_back(root.root_id);
    }
    std::sort(ids.begin(), ids.end());
    std::ostringstream material;
    material << kIdentityScheme << '\0' << kPathMapScheme;
    for (const std::string &id : ids) {
        material << '\0' << id;
    }
    return sha256_hex(material.str());
}

std::string stable_id(
    const std::string &prefix, const std::string &semantic_material) {
    // Schema stable IDs are limited to 128 characters.  A complete SHA-256 is
    // retained so IDs remain collision-resistant while their human-readable
    // prefix identifies the semantic namespace.
    return prefix + ':' + sha256_hex(semantic_material);
}

const char *to_string(StageStatus value) {
    switch (value) {
    case StageStatus::Complete:
        return "COMPLETE";
    case StageStatus::ConservativeIncomplete:
        return "CONSERVATIVE_INCOMPLETE";
    case StageStatus::Failed:
        return "FAILED";
    }
    return "FAILED";
}

const char *to_string(Certainty value) {
    switch (value) {
    case Certainty::Must:
        return "must";
    case Certainty::May:
        return "may";
    case Certainty::Modelled:
        return "modelled";
    case Certainty::Unknown:
        return "unknown";
    }
    return "unknown";
}

const char *to_string(RelationKind value) {
    switch (value) {
    case RelationKind::Defines:
        return "defines";
    case RelationKind::Uses:
        return "uses";
    case RelationKind::Loads:
        return "loads";
    case RelationKind::Stores:
        return "stores";
    case RelationKind::Data:
        return "value_flow";
    case RelationKind::Control:
        return "control";
    case RelationKind::Call:
        return "call";
    case RelationKind::Return:
        return "return";
    case RelationKind::Object:
        return "object";
    case RelationKind::Field:
        return "field";
    case RelationKind::Alias:
        return "alias";
    case RelationKind::Contains:
        return "contains";
    case RelationKind::MapsTo:
        return "maps_to";
    case RelationKind::Unknown:
        return "unknown";
    }
    return "unknown";
}

const char *to_string(InputFileRole value) {
    switch (value) {
    case InputFileRole::Main:
        return "main";
    case InputFileRole::UserHeader:
        return "user_header";
    case InputFileRole::Generated:
        return "generated";
    case InputFileRole::System:
        return "system";
    case InputFileRole::Toolchain:
        return "toolchain";
    }
    return "user_header";
}

}  // namespace rift::core
