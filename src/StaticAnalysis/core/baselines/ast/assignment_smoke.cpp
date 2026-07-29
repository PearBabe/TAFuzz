#include "rift/baselines/ast/ast_baselines.h"

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

rift::baselines::ast::Anchor anchor_at(
    const std::string &source, const std::string &file,
    const std::string &needle, const std::string &symbol,
    const std::string &id) {
    const std::size_t offset = source.find(needle);
    if (offset == std::string::npos) {
        std::abort();
    }
    std::uint32_t line = 1;
    std::uint32_t column = 1;
    for (std::size_t index = 0; index < offset; ++index) {
        if (source[index] == '\n') {
            ++line;
            column = 1;
        } else {
            ++column;
        }
    }
    const std::size_t symbol_offset = needle.find(symbol);
    column += static_cast<std::uint32_t>(symbol_offset);
    return {id, symbol, {file, line, column}};
}

void require(bool condition, const char *message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        std::exit(1);
    }
}

}  // namespace

int main() {
    const std::string file = "neutral_assignment_fixture.cc";
    const std::string source = R"cpp(
int evaluate(int source_value, int decoy_value) {
    int stage_value = source_value;
    int property_value = stage_value > 3;
    int unrelated_value = decoy_value;
    return property_value + (unrelated_value == 99);
}
int elsewhere() {
    int property_elsewhere = 7;
    return property_elsewhere;
}
)cpp";
    rift::baselines::ast::CaseInput input;
    input.source_text = source;
    input.virtual_path = file;
    input.language = "c++20";
    input.compile_arguments = {"-std=c++20"};
    input.source_anchors = {
        anchor_at(
            source, file, "source_value, int", "source_value",
            "source-main"),
        anchor_at(
            source, file, "decoy_value) {", "decoy_value",
            "source-decoy"),
        {"source-missing", "missing_value", {file, 99, 1}},
    };
    input.property_anchors = {
        anchor_at(
            source, file, "property_value = stage_value", "property_value",
            "property-main"),
        anchor_at(
            source, file, "property_elsewhere = 7", "property_elsewhere",
            "property-cross-function"),
    };

    const auto result = rift::baselines::ast::analyze(
        input, rift::baselines::ast::Method::AdgAssignment);
    for (const std::string &diagnostic : result.diagnostics) {
        std::cerr << "DIAGNOSTIC " << diagnostic << '\n';
    }
    require(
        result.diagnostics.size() == 3,
        "unresolved source and two cross-function pairs emit diagnostics");
    require(result.predictions.size() == 6, "assignment pair count");
    require(
        result.predictions[0].influence ==
            rift::baselines::ast::InfluenceClass::MayInfluence,
        "source reaches property through initializer chain");
    require(
        result.predictions[0].evidence_path.size() == 2,
        "two semantic initializer edges");
    require(
        result.predictions[1].status ==
            rift::baselines::ast::PredictionStatus::UnknownUnsupported,
        "cross-function pair remains unknown rather than negative");
    require(
        result.predictions[1].matched_facts.size() == 1,
        "cross-function limitation is attached to the pair");
    require(
        result.predictions[2].influence ==
            rift::baselines::ast::InfluenceClass::NoInfluence,
        "decoy is not related to property");
    require(
        result.predictions[4].status ==
            rift::baselines::ast::PredictionStatus::UnknownUnsupported,
        "unresolved anchor remains unknown rather than negative");
    require(
        result.profile.limitations.size() >= 4,
        "assignment limitations are explicit");

    const std::string mixed_source = R"cpp(
int helper(int value) { return value + 1; }
int mixed(int source_mixed, int other_value) {
    int property_mixed = source_mixed + helper(other_value);
    return property_mixed;
}
)cpp";
    rift::baselines::ast::CaseInput mixed;
    mixed.source_text = mixed_source;
    mixed.virtual_path = "neutral_mixed_fixture.cc";
    mixed.compile_arguments = {"-std=c++20"};
    mixed.source_anchors = {
        anchor_at(
            mixed_source, mixed.virtual_path, "source_mixed, int",
            "source_mixed", "source-mixed"),
    };
    mixed.property_anchors = {
        anchor_at(
            mixed_source, mixed.virtual_path,
            "property_mixed = source_mixed", "property_mixed",
            "property-mixed"),
    };
    const auto mixed_result = rift::baselines::ast::analyze(
        mixed, rift::baselines::ast::Method::AdgAssignment);
    require(
        mixed_result.predictions.size() == 1 &&
            mixed_result.predictions[0].influence ==
                rift::baselines::ast::InfluenceClass::MayInfluence,
        "a sibling call does not erase a directly supported RHS dependency");

    rift::baselines::ast::CaseInput invalid;
    invalid.source_text = "#include \"definitely_missing_rift_header.h\"\n";
    invalid.virtual_path = "neutral_invalid_fixture.cc";
    invalid.compile_arguments = {"-std=c++20"};
    invalid.source_anchors = {
        {"source-invalid", "source_invalid", {invalid.virtual_path, 2, 1}},
    };
    invalid.property_anchors = {
        {"property-invalid", "property_invalid", {invalid.virtual_path, 3, 1}},
    };
    const auto invalid_result = rift::baselines::ast::analyze(
        invalid, rift::baselines::ast::Method::AdgAssignment);
    require(
        invalid_result.predictions.size() == 1 &&
            invalid_result.predictions[0].status ==
                rift::baselines::ast::PredictionStatus::ToolError,
        "front-end errors are distinct from unsupported abstractions");
    std::cout << "PASS assignment semantic-init graph\n";
    std::cout << "method=" << result.profile.name
              << " positive_path_edges="
              << result.predictions[0].evidence_path.size() << '\n';
    return 0;
}
