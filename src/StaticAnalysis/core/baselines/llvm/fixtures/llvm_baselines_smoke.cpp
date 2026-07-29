#include "rift/baselines/llvm/llvm_baselines.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>
#include <utility>

namespace baseline = rift::baselines::llvm;

namespace {

constexpr std::string_view kFixture = "neutral_baseline_fixture.c";

[[noreturn]] void fail(std::string_view message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void require(bool condition, std::string_view message) {
    if (!condition) {
        fail(message);
    }
}

baseline::Anchor anchor(
    std::string id, std::uint32_t line, std::string symbol = {}) {
    return {
        std::move(id),
        std::move(symbol),
        {std::string(kFixture), line, 0},
    };
}

const baseline::PairPrediction &pair(
    const baseline::AnalysisResult &result, std::string_view source_id,
    std::string_view ap_id) {
    for (const baseline::PairPrediction &prediction : result.predictions) {
        if (prediction.source_stable_id == source_id &&
            prediction.ap_stable_id == ap_id) {
            return prediction;
        }
    }
    fail("requested matrix pair is absent");
}

void check_matrix_contract(
    const baseline::AnalysisInput &input,
    const baseline::AnalysisResult &result) {
    require(
        result.predictions.size() ==
            input.source_anchors.size() * input.ap_anchors.size(),
        "result must contain the complete source-by-AP matrix");
    std::size_t index = 0;
    for (const baseline::Anchor &source : input.source_anchors) {
        for (const baseline::Anchor &ap : input.ap_anchors) {
            require(
                result.predictions[index].source_stable_id ==
                    source.stable_id,
                "source stable ID/order changed in result matrix");
            require(
                result.predictions[index].ap_stable_id == ap.stable_id,
                "AP stable ID/order changed in result matrix");
            ++index;
        }
    }
}

bool has_alias(
    const baseline::PairPrediction &prediction,
    baseline::AliasEvidence wanted) {
    for (const baseline::EvidenceEdge &edge : prediction.evidence_path) {
        if (edge.alias == wanted) {
            return true;
        }
    }
    return false;
}

bool has_svf_edge(const baseline::PairPrediction &prediction) {
    for (const baseline::EvidenceEdge &edge : prediction.evidence_path) {
        if (edge.kind == baseline::EdgeKind::SvfDirect ||
            edge.kind == baseline::EdgeKind::SvfIndirect ||
            edge.kind == baseline::EdgeKind::SvfCall ||
            edge.kind == baseline::EdgeKind::SvfReturn ||
            edge.kind == baseline::EdgeKind::SvfThreadMhp) {
            return true;
        }
    }
    return false;
}

void check_unknown_contract(const baseline::PairPrediction &prediction) {
    require(
        prediction.status == baseline::PredictionStatus::UnknownUnsupported,
        "unmapped anchor must retain UNKNOWN_UNSUPPORTED status");
    require(
        prediction.influence == baseline::InfluenceClass::Unknown,
        "unmapped anchor must not be converted to a negative prediction");
}

void smoke_ssa(const std::string &bitcode) {
    baseline::AnalysisInput input{
        {bitcode},
        {
            anchor("source::ssa::exact", 101, "stage"),
            anchor("source::ssa::decoy", 103, "decoy"),
            anchor("source::ssa::missing", 9901),
        },
        {anchor("ap::ssa::exact", 102, "proposition")},
    };
    const baseline::AnalysisResult result =
        baseline::analyze(input, baseline::Method::LlvmSsaDefUse);
    check_matrix_contract(input, result);
    require(
        pair(result, "source::ssa::exact", "ap::ssa::exact").influence ==
            baseline::InfluenceClass::MayInfluence,
        "SSA def-use chain must be reachable");
    require(
        pair(result, "source::ssa::decoy", "ap::ssa::exact").influence ==
            baseline::InfluenceClass::NoInfluence,
        "resolved SSA decoy must remain disconnected");
    check_unknown_contract(
        pair(result, "source::ssa::missing", "ap::ssa::exact"));
    std::cout << "PASS llvm-ssa: matrix=3 positive=1 negative=1 unknown=1\n";
}

void smoke_memoryssa(const std::string &bitcode) {
    baseline::AnalysisInput input{
        {bitcode},
        {
            anchor("source::memory::must", 201),
            anchor("source::memory::may", 301),
            anchor("source::memory::missing", 9902),
        },
        {
            anchor("ap::memory::must", 203),
            anchor("ap::memory::may", 303),
        },
    };
    const baseline::AnalysisResult result =
        baseline::analyze(input, baseline::Method::LlvmMemorySsaAa);
    check_matrix_contract(input, result);

    const baseline::PairPrediction &must_pair =
        pair(result, "source::memory::must", "ap::memory::must");
    require(
        must_pair.influence == baseline::InfluenceClass::MayInfluence,
        "MemorySSA same-object path must be reachable");
    require(
        has_alias(must_pair, baseline::AliasEvidence::MustAlias),
        "MemorySSA path must preserve must-alias evidence");

    const baseline::PairPrediction &may_pair =
        pair(result, "source::memory::may", "ap::memory::may");
    require(
        may_pair.influence == baseline::InfluenceClass::MayInfluence,
        "MemorySSA pointer-parameter path must be reachable");
    require(
        has_alias(may_pair, baseline::AliasEvidence::MayAlias) ||
            has_alias(may_pair, baseline::AliasEvidence::PartialAlias),
        "MemorySSA path must preserve conservative alias evidence");

    check_unknown_contract(
        pair(result, "source::memory::missing", "ap::memory::must"));
    check_unknown_contract(
        pair(result, "source::memory::missing", "ap::memory::may"));
    std::cout <<
        "PASS llvm-memoryssa-aa: matrix=6 must-alias=1 may-or-partial-alias=1 unknown=2\n";
}

void smoke_svf(const std::string &bitcode) {
    baseline::AnalysisInput input{
        {bitcode},
        {
            anchor("source::svf::exact", 401),
            anchor("source::svf::missing", 9903),
        },
        {anchor("ap::svf::exact", 402)},
    };
    const baseline::AnalysisResult result =
        baseline::analyze(input, baseline::Method::SvfBackwardValueFlow);
    check_matrix_contract(input, result);
    const baseline::PairPrediction &positive =
        pair(result, "source::svf::exact", "ap::svf::exact");
    require(
        positive.influence == baseline::InfluenceClass::MayInfluence,
        "SVF memory value-flow chain must be reachable");
    require(
        has_svf_edge(positive),
        "SVF positive path must contain explicitly traversed SVFG evidence");
    check_unknown_contract(
        pair(result, "source::svf::missing", "ap::svf::exact"));

    bool traversal_diagnostic = false;
    for (const std::string &diagnostic : result.diagnostics) {
        if (diagnostic.find("explicitly traversed SVFG edges=") !=
                std::string::npos &&
            !diagnostic.ends_with("=0")) {
            traversal_diagnostic = true;
        }
    }
    require(
        traversal_diagnostic,
        "SVF smoke must observe nonzero explicit SVFG edge traversal");
    std::cout << "PASS svf-3.2: matrix=2 positive=1 unknown=1 explicit-edges>0\n";
}

void smoke_tool_failure() {
    baseline::AnalysisInput input{
        {"/path/that/does/not/exist/neutral.bc"},
        {
            anchor("source::failure::one", 101),
            anchor("source::failure::two", 103),
        },
        {
            anchor("ap::failure::one", 102),
            anchor("ap::failure::two", 203),
        },
    };
    const baseline::AnalysisResult result =
        baseline::analyze(input, baseline::Method::LlvmSsaDefUse);
    check_matrix_contract(input, result);
    for (const baseline::PairPrediction &prediction : result.predictions) {
        check_unknown_contract(prediction);
    }
    std::cout << "PASS tool-failure contract: matrix=4 unknown=4\n";
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: llvm_baselines_smoke <ssa.bc> <memory-and-svf.bc>\n";
        return 2;
    }
    smoke_ssa(argv[1]);
    smoke_memoryssa(argv[2]);
    smoke_svf(argv[2]);
    smoke_tool_failure();
    std::cout << "PASS all LLVM/SVF baseline smoke checks\n";
    return 0;
}
