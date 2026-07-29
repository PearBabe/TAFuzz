#include "rift/baselines/ast/ast_baselines.h"

#include <algorithm>
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
    column += static_cast<std::uint32_t>(needle.find(symbol));
    return {id, symbol, {file, line, column}};
}

void require(bool condition, const char *message) {
    if (!condition) {
        std::cerr << "FAIL " << message << '\n';
        std::exit(1);
    }
}

bool path_contains(
    const rift::baselines::ast::PairPrediction &prediction,
    rift::baselines::ast::EdgeKind kind) {
    return std::any_of(
        prediction.evidence_path.begin(), prediction.evidence_path.end(),
        [kind](const rift::baselines::ast::EvidenceEdge &edge) {
            return edge.kind == kind;
        });
}

}  // namespace

int main() {
    const std::string file = "neutral_pdg_fixture.cc";
    const std::string source = R"cpp(
int transform(int argument) {
    int local = argument + 1;
    return local;
}
int call_flow(int source_call) {
    int property_call = transform(source_call);
    return property_call;
}
int control_flow(int source_guard) {
    int property_guard = 0;
    if (source_guard > 0) {
        property_guard = 1;
    }
    return property_guard;
}
struct Cell { int value; };
int alias_flow(int source_alias) {
    Cell cell{0};
    Cell *pointer = &cell;
    pointer->value = source_alias;
    int property_alias = cell.value;
    return property_alias;
}
)cpp";

    rift::baselines::ast::CaseInput input;
    input.source_text = source;
    input.virtual_path = file;
    input.language = "c++20";
    input.compile_arguments = {"-std=c++20"};
    input.source_anchors = {
        anchor_at(
            source, file, "source_call) {", "source_call",
            "source-call"),
        anchor_at(
            source, file, "source_guard) {", "source_guard",
            "source-control"),
        anchor_at(
            source, file, "source_alias) {", "source_alias",
            "source-alias"),
    };
    input.property_anchors = {
        anchor_at(
            source, file, "property_call = transform", "property_call",
            "property-call"),
        anchor_at(
            source, file, "property_guard = 0", "property_guard",
            "property-control"),
        anchor_at(
            source, file, "property_alias = cell", "property_alias",
            "property-alias"),
    };

    const auto result = rift::baselines::ast::analyze(
        input, rift::baselines::ast::Method::PlainPdg);
    for (const std::string &diagnostic : result.diagnostics) {
        std::cerr << "DIAGNOSTIC " << diagnostic << '\n';
    }
    require(result.diagnostics.empty(), "plain PDG diagnostics");
    require(result.predictions.size() == 9, "plain PDG pair count");

    const auto &call = result.predictions[0];
    require(
        call.influence ==
            rift::baselines::ast::InfluenceClass::MayInfluence,
        "direct call/return flow reaches property");
    require(
        path_contains(call, rift::baselines::ast::EdgeKind::Call),
        "call path records actual-to-formal edge");
    require(
        path_contains(call, rift::baselines::ast::EdgeKind::Return),
        "call path records return edge");

    const auto &control = result.predictions[4];
    require(
        control.influence ==
            rift::baselines::ast::InfluenceClass::MayInfluence,
        "guard-only control flow reaches property");
    require(
        path_contains(control, rift::baselines::ast::EdgeKind::Control),
        "control path records lexical guard edge");

    const auto &alias = result.predictions[8];
    require(
        alias.influence ==
            rift::baselines::ast::InfluenceClass::MayInfluence,
        "shallow alias field flow reaches property");
    require(
        path_contains(alias, rift::baselines::ast::EdgeKind::Alias),
        "alias path records shallow alias edge");
    require(
        path_contains(alias, rift::baselines::ast::EdgeKind::Field),
        "alias path records field data edge");

    require(
        result.predictions[1].influence ==
            rift::baselines::ast::InfluenceClass::NoInfluence,
        "unrelated cross-fixture pair is negative");
    std::cout << "PASS plain PDG data/control/call/return/field/alias\n";
    std::cout << "call_edges=" << call.evidence_path.size()
              << " control_edges=" << control.evidence_path.size()
              << " alias_edges=" << alias.evidence_path.size() << '\n';
    return 0;
}
