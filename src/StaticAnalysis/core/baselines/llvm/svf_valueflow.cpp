#include "llvm_baselines_internal.h"

#include <Graphs/SVFG.h>
#include <Graphs/SVFGEdge.h>
#include <MSSA/SVFGBuilder.h>
#include <SVF-LLVM/LLVMModule.h>
#include <SVF-LLVM/SVFIRBuilder.h>
#include <SVFIR/SVFIR.h>
#include <Util/ExtAPI.h>
#include <Util/config.h>
#include <WPA/Andersen.h>

#include <llvm/IR/Function.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Module.h>

#include <cstddef>
#include <deque>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace rift::baselines::llvm::detail {
namespace {

struct SvfCleanup {
    ~SvfCleanup() {
        SVF::AndersenWaveDiff::releaseAndersenWaveDiff();
        SVF::SVFIR::releaseSVFIR();
        SVF::LLVMModuleSet::releaseLLVMModuleSet();
    }
};

struct SvfAnchorResolution {
    PredictionStatus status = PredictionStatus::UnknownUnsupported;
    std::vector<const SVF::SVFGNode *> nodes;
    std::vector<ProgramPoint> points;
    std::string reason;
};

struct SvfEdgeFact {
    const SVF::SVFGNode *from = nullptr;
    const SVF::SVFGNode *to = nullptr;
    EdgeKind kind = EdgeKind::SvfDirect;
    Certainty certainty = Certainty::May;
    AliasEvidence alias = AliasEvidence::NotApplicable;
    std::string explanation;
};

struct SvfPath {
    bool reached = false;
    std::vector<const SvfEdgeFact *> edges;
};

using SvfIncomingEdges =
    std::map<const SVF::SVFGNode *, std::vector<std::size_t>>;

const ::llvm::Value *associated_llvm_value(
    const SVF::SVFGNode *node, const SVF::LLVMModuleSet &modules) {
    if (node == nullptr) {
        return nullptr;
    }
    const SVF::ICFGNode *icfg = node->getICFGNode();
    if (icfg != nullptr && modules.hasLLVMValue(icfg)) {
        return modules.getLLVMValue(icfg);
    }
    const SVF::SVFVar *value = node->getValue();
    if (value != nullptr && modules.hasLLVMValue(value)) {
        return modules.getLLVMValue(value);
    }
    return nullptr;
}

ProgramPoint svf_point(
    const SVF::SVFGNode *node, const SVF::LLVMModuleSet &modules) {
    const ::llvm::Value *value = associated_llvm_value(node, modules);
    return {
        "svfg:node:" + std::to_string(node->getId()),
        value == nullptr ? "<svfg-node>" : llvm_value_label(value),
        debug_location(value),
    };
}

EdgeKind edge_kind(const SVF::VFGEdge &edge) {
    if (edge.isThreadMHPIndirectVFGEdge()) {
        return EdgeKind::SvfThreadMhp;
    }
    if (edge.isCallVFGEdge()) {
        return EdgeKind::SvfCall;
    }
    if (edge.isRetVFGEdge()) {
        return EdgeKind::SvfReturn;
    }
    if (edge.isIndirectVFGEdge()) {
        return EdgeKind::SvfIndirect;
    }
    return EdgeKind::SvfDirect;
}

std::string edge_explanation(const SVF::VFGEdge &edge) {
    if (edge.isThreadMHPIndirectVFGEdge()) {
        return "SVF thread-MHP indirect sparse value-flow edge";
    }
    if (edge.isCallVFGEdge()) {
        return edge.isIndirectVFGEdge()
                   ? "SVF call edge carrying indirect memory value flow"
                   : "SVF call edge carrying direct value flow";
    }
    if (edge.isRetVFGEdge()) {
        return edge.isIndirectVFGEdge()
                   ? "SVF return edge carrying indirect memory value flow"
                   : "SVF return edge carrying direct value flow";
    }
    return edge.isIndirectVFGEdge()
               ? "SVF indirect memory value-flow edge derived from points-to sets"
               : "SVF direct sparse value-flow edge";
}

std::map<std::string, std::size_t> counts(
    const std::vector<Anchor> &anchors) {
    std::map<std::string, std::size_t> result;
    for (const Anchor &anchor : anchors) {
        ++result[anchor.stable_id];
    }
    return result;
}

bool invalid_id(
    const Anchor &anchor, const std::map<std::string, std::size_t> &all) {
    const auto iterator = all.find(anchor.stable_id);
    return anchor.stable_id.empty() ||
           (iterator != all.end() && iterator->second != 1);
}

SvfAnchorResolution resolve_svf_anchor(
    const Anchor &anchor,
    const std::vector<std::unique_ptr<NodeCatalog>> &catalogs,
    const std::map<const ::llvm::Value *,
                   std::vector<const SVF::SVFGNode *>> &value_nodes,
    const SVF::LLVMModuleSet &modules) {
    SvfAnchorResolution result;
    std::set<const ::llvm::Value *> llvm_values;
    std::size_t debug_matches = 0;
    for (const auto &catalog : catalogs) {
        const ResolvedLlvmAnchor resolution = catalog->resolve(anchor);
        if (resolution.status != PredictionStatus::Resolved) {
            continue;
        }
        debug_matches += resolution.values.size();
        llvm_values.insert(
            resolution.values.begin(), resolution.values.end());
    }
    if (debug_matches == 0) {
        result.reason =
            "no LLVM value has the requested debug location/symbol";
        return result;
    }

    std::set<const SVF::SVFGNode *> seen;
    for (const ::llvm::Value *value : llvm_values) {
        const auto iterator = value_nodes.find(value);
        if (iterator == value_nodes.end()) {
            continue;
        }
        for (const SVF::SVFGNode *node : iterator->second) {
            if (seen.insert(node).second) {
                result.nodes.push_back(node);
                result.points.push_back(svf_point(node, modules));
            }
        }
    }
    if (result.nodes.empty()) {
        result.reason =
            "LLVM debug anchor resolved, but SVF 3.2 exposes no corresponding SVFG node";
        return result;
    }
    result.status = PredictionStatus::Resolved;
    result.reason = "exact debug anchor mapped to " +
                    std::to_string(result.nodes.size()) + " SVFG node(s)";
    return result;
}

SvfPath find_backward_svf_path(
    const std::vector<const SVF::SVFGNode *> &sources,
    const std::vector<const SVF::SVFGNode *> &targets,
    const std::vector<SvfEdgeFact> &edges,
    const SvfIncomingEdges &incoming) {
    SvfPath result;
    std::set<const SVF::SVFGNode *> source_set(
        sources.begin(), sources.end());
    std::set<const SVF::SVFGNode *> target_set(
        targets.begin(), targets.end());
    for (const SVF::SVFGNode *source : sources) {
        if (target_set.contains(source)) {
            result.reached = true;
            return result;
        }
    }

    std::deque<const SVF::SVFGNode *> worklist;
    std::set<const SVF::SVFGNode *> visited;
    std::map<const SVF::SVFGNode *, std::size_t> successor;
    for (const SVF::SVFGNode *target : targets) {
        if (visited.insert(target).second) {
            worklist.push_back(target);
        }
    }

    const SVF::SVFGNode *reached_source = nullptr;
    while (!worklist.empty() && reached_source == nullptr) {
        const SVF::SVFGNode *current = worklist.front();
        worklist.pop_front();
        const auto iterator = incoming.find(current);
        if (iterator == incoming.end()) {
            continue;
        }
        for (const std::size_t edge_index : iterator->second) {
            const SVF::SVFGNode *next = edges[edge_index].from;
            if (!visited.insert(next).second) {
                continue;
            }
            successor.emplace(next, edge_index);
            if (source_set.contains(next)) {
                reached_source = next;
                break;
            }
            worklist.push_back(next);
        }
    }
    if (reached_source == nullptr) {
        return result;
    }

    result.reached = true;
    const SVF::SVFGNode *current = reached_source;
    while (!target_set.contains(current)) {
        const auto iterator = successor.find(current);
        if (iterator == successor.end()) {
            result.reached = false;
            result.edges.clear();
            return result;
        }
        const SvfEdgeFact &edge = edges[iterator->second];
        result.edges.push_back(&edge);
        current = edge.to;
    }
    return result;
}

AnchorResolution public_resolution(
    const Anchor &anchor, AnchorRole role,
    const SvfAnchorResolution &resolution) {
    return {
        anchor.stable_id,
        role,
        resolution.status,
        resolution.points,
        resolution.reason,
    };
}

}  // namespace

AnalysisResult analyze_svf(const AnalysisInput &input) {
    std::vector<std::string> diagnostics;
    std::unique_ptr<LoadedModule> preflight =
        load_linked_module(input, diagnostics);
    if (preflight == nullptr || preflight->module == nullptr) {
        return unknown_matrix(
            input, method_profile(Method::SvfBackwardValueFlow),
            "LLVM preflight failed before SVF analysis", diagnostics);
    }
    preflight.reset();

    SvfCleanup cleanup;
    if (!SVF::ExtAPI::setExtBcPath(SVF_INSTALL_EXTAPI_BC)) {
        diagnostics.push_back(
            "configured SVF ExtAPI bitcode is unavailable; SVF fallback lookup will be used");
    }
    SVF::LLVMModuleSet::buildSVFModule(input.bitcode_paths);
    SVF::LLVMModuleSet *modules = SVF::LLVMModuleSet::getLLVMModuleSet();
    SVF::SVFIRBuilder ir_builder;
    SVF::SVFIR *svfir = ir_builder.build();
    SVF::AndersenWaveDiff *andersen =
        SVF::AndersenWaveDiff::createAndersenWaveDiff(svfir);
    SVF::SVFGBuilder svfg_builder;
    SVF::SVFG *svfg = svfg_builder.buildFullSVFG(andersen);
    if (svfg == nullptr) {
        return unknown_matrix(
            input, method_profile(Method::SvfBackwardValueFlow),
            "SVF 3.2 did not construct an SVFG", diagnostics);
    }

    std::vector<std::unique_ptr<NodeCatalog>> catalogs;
    for (SVF::u32_t index = 0; index < modules->getModuleNum(); ++index) {
        catalogs.push_back(
            std::make_unique<NodeCatalog>(*modules->getModule(index)));
    }

    std::map<const ::llvm::Value *, std::vector<const SVF::SVFGNode *>>
        value_nodes;
    std::vector<SvfEdgeFact> edges;
    std::size_t node_count = 0;
    for (const auto &entry : *svfg) {
        const SVF::SVFGNode *node = entry.second;
        ++node_count;
        if (const ::llvm::Value *value =
                associated_llvm_value(node, *modules)) {
            value_nodes[value].push_back(node);
        }
        for (auto iterator = node->OutEdgeBegin();
             iterator != node->OutEdgeEnd(); ++iterator) {
            const SVF::VFGEdge *edge = *iterator;
            const bool indirect = edge->isIndirectVFGEdge();
            edges.push_back({
                node,
                edge->getDstNode(),
                edge_kind(*edge),
                indirect ? Certainty::May : Certainty::Must,
                indirect ? AliasEvidence::MayAlias
                         : AliasEvidence::NotApplicable,
                edge_explanation(*edge),
            });
        }
    }
    diagnostics.push_back(
        "SVFIR nodes=" + std::to_string(svfir->getPAGNodeNum()) +
        ", SVFG nodes=" + std::to_string(node_count) +
        ", explicitly traversed SVFG edges=" +
        std::to_string(edges.size()));
    SvfIncomingEdges incoming;
    for (std::size_t edge_index = 0; edge_index < edges.size(); ++edge_index) {
        incoming[edges[edge_index].to].push_back(edge_index);
    }

    AnalysisResult result;
    result.profile = method_profile(Method::SvfBackwardValueFlow);
    result.diagnostics = std::move(diagnostics);
    const auto source_counts = counts(input.source_anchors);
    const auto ap_counts = counts(input.ap_anchors);
    std::vector<SvfAnchorResolution> source_resolutions;
    std::vector<SvfAnchorResolution> ap_resolutions;

    for (const Anchor &anchor : input.source_anchors) {
        SvfAnchorResolution resolution;
        if (invalid_id(anchor, source_counts)) {
            resolution.reason =
                "source stable ID is empty or duplicated in the input";
        } else {
            resolution = resolve_svf_anchor(
                anchor, catalogs, value_nodes, *modules);
        }
        if (resolution.status == PredictionStatus::UnknownUnsupported) {
            result.diagnostics.push_back(
                "source anchor '" + anchor.stable_id + "': " +
                resolution.reason);
        }
        result.anchor_resolutions.push_back(
            public_resolution(anchor, AnchorRole::Source, resolution));
        source_resolutions.push_back(std::move(resolution));
    }
    for (const Anchor &anchor : input.ap_anchors) {
        SvfAnchorResolution resolution;
        if (invalid_id(anchor, ap_counts)) {
            resolution.reason =
                "AP stable ID is empty or duplicated in the input";
        } else {
            resolution = resolve_svf_anchor(
                anchor, catalogs, value_nodes, *modules);
        }
        if (resolution.status == PredictionStatus::UnknownUnsupported) {
            result.diagnostics.push_back(
                "AP anchor '" + anchor.stable_id + "': " +
                resolution.reason);
        }
        result.anchor_resolutions.push_back(public_resolution(
            anchor, AnchorRole::AtomicProposition, resolution));
        ap_resolutions.push_back(std::move(resolution));
    }

    for (std::size_t source_index = 0;
         source_index < input.source_anchors.size(); ++source_index) {
        for (std::size_t ap_index = 0; ap_index < input.ap_anchors.size();
             ++ap_index) {
            PairPrediction prediction;
            prediction.source_stable_id =
                input.source_anchors[source_index].stable_id;
            prediction.ap_stable_id = input.ap_anchors[ap_index].stable_id;
            prediction.limitations = result.profile.limitations;
            const SvfAnchorResolution &source =
                source_resolutions[source_index];
            const SvfAnchorResolution &ap = ap_resolutions[ap_index];
            if (source.status == PredictionStatus::UnknownUnsupported ||
                ap.status == PredictionStatus::UnknownUnsupported) {
                prediction.status = PredictionStatus::UnknownUnsupported;
                prediction.influence = InfluenceClass::Unknown;
                prediction.matched_facts.push_back(
                    "source_anchor=" + source.reason);
                prediction.matched_facts.push_back("ap_anchor=" + ap.reason);
                result.predictions.push_back(std::move(prediction));
                continue;
            }

            prediction.status = PredictionStatus::Resolved;
            prediction.matched_facts.push_back(
                "source_anchor_targets=" +
                std::to_string(source.nodes.size()));
            prediction.matched_facts.push_back(
                "ap_anchor_targets=" + std::to_string(ap.nodes.size()));
            const SvfPath path =
                find_backward_svf_path(
                    source.nodes, ap.nodes, edges, incoming);
            if (!path.reached) {
                prediction.influence = InfluenceClass::NoInfluence;
                prediction.matched_facts.push_back(
                    "no path in the SVF 3.2 sparse value-flow graph");
                result.predictions.push_back(std::move(prediction));
                continue;
            }

            prediction.influence = InfluenceClass::MayInfluence;
            prediction.matched_facts.push_back(
                "svfg_path_edges=" + std::to_string(path.edges.size()));
            if (path.edges.empty()) {
                prediction.matched_facts.push_back(
                    "source and AP anchors share an SVFG node");
            }
            for (const SvfEdgeFact *edge : path.edges) {
                const ProgramPoint from = svf_point(edge->from, *modules);
                const ProgramPoint to = svf_point(edge->to, *modules);
                prediction.evidence_path.push_back({
                    from,
                    to,
                    edge->kind,
                    edge->certainty,
                    edge->alias,
                    to.location.line == 0 ? from.location : to.location,
                    edge->explanation,
                });
            }
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

}  // namespace rift::baselines::llvm::detail
