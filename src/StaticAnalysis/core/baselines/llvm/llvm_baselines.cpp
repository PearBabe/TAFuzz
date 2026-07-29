#include "rift/baselines/llvm/llvm_baselines.h"

#include "llvm_baselines_internal.h"

#include <utility>

namespace rift::baselines::llvm {

MethodProfile method_profile(Method method) {
    switch (method) {
    case Method::LlvmSsaDefUse:
        return {
            method,
            "llvm-ssa-backward-def-use",
            {
                "exact caller-supplied stable IDs",
                "debug-location anchor mapping",
                "LLVM SSA operand def-use traversal",
                "complete source-by-AP pair matrix",
                "source-to-AP evidence paths",
            },
            {
                "memory is not connected across load/store operations",
                "no interprocedural actual/formal or return summaries",
                "no control dependence, alias, event, timing, lifecycle, or scope semantics",
                "optimized-away or ambiguous debug anchors may be unsupported",
                "a reachable path is reported as may-influence, not as runtime inevitability",
            },
        };
    case Method::LlvmMemorySsaAa:
        return {
            method,
            "llvm-memoryssa-basicaa-backward",
            {
                "exact caller-supplied stable IDs",
                "debug-location anchor mapping",
                "LLVM SSA operand def-use traversal",
                "intraprocedural MemorySSA clobber traversal",
                "LLVM BasicAA may/partial/must-alias evidence",
                "complete source-by-AP pair matrix",
            },
            {
                "MemorySSA and BasicAA are intraprocedural in this baseline",
                "unknown calls and unsupported memory locations retain may/unknown evidence",
                "no project API summaries or external controllability classification",
                "no control dependence, event, timing, lifecycle, or scope semantics",
                "a must-alias edge does not make the whole source-to-AP path must-execute",
            },
        };
    case Method::SvfBackwardValueFlow:
        return {
            method,
            "svf-3.2-backward-value-flow",
            {
                "exact caller-supplied stable IDs",
                "debug-location-to-SVFG anchor mapping",
                "SVFIR and AndersenWaveDiff points-to analysis",
                "full MemorySSA-backed sparse value-flow graph",
                "direct, indirect, call, return, and thread-MHP edge evidence",
                "complete source-by-AP pair matrix",
            },
            {
                "SVF is pointer/value-flow centric and may not represent scalar AP instructions",
                "SVF global analysis state makes this adapter non-reentrant",
                "external-library precision depends on the separately versioned ExtAPI model",
                "no control dependence, external controllability, timing, lifecycle, or scope semantics",
                "indirect SVFG reachability is conservative and is never promoted to must-influence",
            },
        };
    }
    return {};
}

AnalysisResult analyze(const AnalysisInput &input, Method method) {
    switch (method) {
    case Method::LlvmSsaDefUse:
        return detail::analyze_ssa(input);
    case Method::LlvmMemorySsaAa:
        return detail::analyze_memoryssa(input);
    case Method::SvfBackwardValueFlow:
        return detail::analyze_svf(input);
    }
    return detail::unknown_matrix(
        input, method_profile(method), "unknown baseline method");
}

std::string_view to_string(Method method) {
    switch (method) {
    case Method::LlvmSsaDefUse:
        return "LLVM_SSA_DEF_USE";
    case Method::LlvmMemorySsaAa:
        return "LLVM_MEMORYSSA_AA";
    case Method::SvfBackwardValueFlow:
        return "SVF_BACKWARD_VALUE_FLOW";
    }
    return "UNKNOWN_METHOD";
}

std::string_view to_string(PredictionStatus status) {
    switch (status) {
    case PredictionStatus::Resolved:
        return "RESOLVED";
    case PredictionStatus::UnknownUnsupported:
        return "UNKNOWN_UNSUPPORTED";
    }
    return "UNKNOWN_UNSUPPORTED";
}

std::string_view to_string(InfluenceClass influence) {
    switch (influence) {
    case InfluenceClass::Unknown:
        return "UNKNOWN";
    case InfluenceClass::NoInfluence:
        return "NO";
    case InfluenceClass::MayInfluence:
        return "MAY";
    case InfluenceClass::MustInfluence:
        return "MUST";
    }
    return "UNKNOWN";
}

std::string_view to_string(EdgeKind kind) {
    switch (kind) {
    case EdgeKind::SsaDefUse:
        return "SSA_DEF_USE";
    case EdgeKind::MemoryDefUse:
        return "MEMORY_DEF_USE";
    case EdgeKind::MemoryPhi:
        return "MEMORY_PHI";
    case EdgeKind::SvfDirect:
        return "SVF_DIRECT";
    case EdgeKind::SvfIndirect:
        return "SVF_INDIRECT";
    case EdgeKind::SvfCall:
        return "SVF_CALL";
    case EdgeKind::SvfReturn:
        return "SVF_RETURN";
    case EdgeKind::SvfThreadMhp:
        return "SVF_THREAD_MHP";
    }
    return "UNKNOWN_EDGE";
}

std::string_view to_string(Certainty certainty) {
    switch (certainty) {
    case Certainty::Must:
        return "MUST";
    case Certainty::May:
        return "MAY";
    case Certainty::Unknown:
        return "UNKNOWN";
    }
    return "UNKNOWN";
}

std::string_view to_string(AliasEvidence alias) {
    switch (alias) {
    case AliasEvidence::NotApplicable:
        return "NOT_APPLICABLE";
    case AliasEvidence::NoAlias:
        return "NO_ALIAS";
    case AliasEvidence::MayAlias:
        return "MAY_ALIAS";
    case AliasEvidence::PartialAlias:
        return "PARTIAL_ALIAS";
    case AliasEvidence::MustAlias:
        return "MUST_ALIAS";
    case AliasEvidence::Unknown:
        return "UNKNOWN_ALIAS";
    }
    return "UNKNOWN_ALIAS";
}

std::string_view to_string(AnchorRole role) {
    switch (role) {
    case AnchorRole::Source:
        return "SOURCE";
    case AnchorRole::AtomicProposition:
        return "ATOMIC_PROPOSITION";
    }
    return "SOURCE";
}

}  // namespace rift::baselines::llvm
