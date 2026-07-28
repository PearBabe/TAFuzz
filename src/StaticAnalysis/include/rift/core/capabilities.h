#ifndef RIFT_CORE_CAPABILITIES_H
#define RIFT_CORE_CAPABILITIES_H

#include "rift/core/frontier.h"

#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace rift::core {

// Executor capability evidence is intentionally loaded independently from a
// model pack.  A pack can state which capability an abstract action requires;
// it cannot assert that a concrete harness implements that capability.
[[nodiscard]] LoadResult<ExecutorCapabilityManifest>
load_executor_capability_manifest(
    const std::filesystem::path &path,
    const std::optional<std::string> &expected_sha256 = std::nullopt);

[[nodiscard]] std::vector<std::string>
validate_executor_capability_manifest(
    const ExecutorCapabilityManifest &manifest);

[[nodiscard]] std::string canonical_executor_capability_manifest_json(
    const ExecutorCapabilityManifest &manifest);

}  // namespace rift::core

#endif
