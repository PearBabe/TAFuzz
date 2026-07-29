#include "rift/core/capabilities.h"

#include "rift/core/sha256.h"

#include <llvm/Support/JSON.h>

#include <algorithm>
#include <filesystem>
#include <iostream>
#include <string>

namespace {

int failures = 0;

void check(const bool condition, const std::string &message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        ++failures;
    }
}

}  // namespace

int main(int argc, char **argv) {
    namespace core = rift::core;
    if (argc != 2) {
        std::cerr << "usage: capabilities_smoke MANIFEST\n";
        return 2;
    }
    const std::filesystem::path path = argv[1];
    const auto loaded = core::load_executor_capability_manifest(path);
    check(loaded.value.has_value(), "valid executor manifest loads");
    check(
        loaded.status == core::StageStatus::Complete,
        "fixture status is complete");
    check(
        loaded.observed_sha256 == core::sha256_file(path),
        "loader records exact input digest");
    if (loaded.value) {
        const auto errors =
            core::validate_executor_capability_manifest(*loaded.value);
        check(errors.empty(), "in-memory manifest validates");
        const std::string canonical =
            core::canonical_executor_capability_manifest_json(*loaded.value);
        auto parsed = llvm::json::parse(canonical);
        check(static_cast<bool>(parsed), "canonical manifest is valid JSON");
        check(
            canonical.find("neutral-read-arg") == std::string::npos,
            "canonical capability core does not invent adapter symbols");

        core::ExecutorCapabilityManifest invalid = *loaded.value;
        core::CoverageGap gap;
        gap.gap_id = "gap.soundness";
        gap.kind = "missing_executor_support";
        gap.effect = core::GapEffect::SoundnessRisk;
        gap.detail = "A declared action is not implemented.";
        invalid.coverage_gaps.push_back(std::move(gap));
        const auto invalid_errors =
            core::validate_executor_capability_manifest(invalid);
        check(
            std::find(
                invalid_errors.begin(), invalid_errors.end(),
                "COMPLETE executor manifest cannot retain soundness/stage gaps") !=
                invalid_errors.end(),
            "COMPLETE cannot hide a soundness gap");
    }
    const auto mismatch = core::load_executor_capability_manifest(
        path, std::string(64U, 'f'));
    check(
        !mismatch.value.has_value(),
        "expected digest mismatch rejects the manifest");

    if (failures != 0) return 1;
    std::cout << "PASS capabilities_smoke checks=8\n";
    return 0;
}
