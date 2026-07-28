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
    column += static_cast<std::uint32_t>(needle.find(symbol));
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
    const std::string file = "neutral_rw_fixture.cc";
    const std::string source = R"cpp(
struct NeutralRecord { unsigned flags; };
void write_helper(NeutralRecord *, unsigned);
void producer(NeutralRecord *, unsigned);
int consumer(NeutralRecord *);
void write_helper(NeutralRecord *record, unsigned value) {
    record->flags = value;
}
void producer(NeutralRecord *record, unsigned value) {
    write_helper(record, value);
}
int consumer(NeutralRecord *record) {
    if ((record->flags & 1U) != 0U) {
        return 1;
    }
    return 0;
}
int entry() {
    NeutralRecord record{0};
    producer(&record, 1U);
    int observed = consumer(&record);
    producer(&record, 0U);
    return observed;
}
int other_entry() {
    NeutralRecord record{0};
    return consumer(&record);
}
)cpp";
    rift::baselines::ast::CaseInput input;
    input.source_text = source;
    input.virtual_path = file;
    input.language = "c++20";
    input.compile_arguments = {"-std=c++20"};
    input.source_anchors = {
        anchor_at(
            source, file, "producer(&record, 1U)", "producer",
            "producer-before"),
        anchor_at(
            source, file, "producer(&record, 0U)", "producer",
            "producer-after"),
    };
    input.property_anchors = {
        anchor_at(
            source, file, "consumer(&record)", "consumer",
            "consumer-call"),
        anchor_at(
            source, file, "return consumer(&record)", "consumer",
            "consumer-other-caller"),
    };

    const auto result = rift::baselines::ast::analyze(
        input, rift::baselines::ast::Method::MoonShineRw);
    require(
        result.diagnostics.size() == 2,
        "cross-caller pairs emit explicit diagnostics");
    require(result.predictions.size() == 4, "MoonShine pair count");
    require(
        result.predictions[0].influence ==
            rift::baselines::ast::InfluenceClass::MayInfluence,
        "write/read intersection is predicted");
    require(
        result.predictions[0].evidence_path.size() == 2,
        "write and conditional-read evidence");
    require(
        result.predictions[1].status ==
            rift::baselines::ast::PredictionStatus::UnknownUnsupported,
        "cross-caller order remains unknown rather than negative");
    require(
        result.predictions[2].influence ==
            rift::baselines::ast::InfluenceClass::NoInfluence,
        "producer-after-consumer is filtered");
    require(
        result.predictions[2].status ==
            rift::baselines::ast::PredictionStatus::Resolved,
        "reversed order is a resolved negative");
    std::cout << "PASS MoonShine W-intersect-Rcond with call closure\n";
    std::cout << result.predictions[0].matched_facts.front() << '\n';
    return 0;
}
