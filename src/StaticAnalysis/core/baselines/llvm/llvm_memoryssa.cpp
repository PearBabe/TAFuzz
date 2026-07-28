#include "llvm_baselines_internal.h"

#include <llvm/TargetParser/Triple.h>
#include <llvm/Analysis/AliasAnalysis.h>
#include <llvm/Analysis/AssumptionCache.h>
#include <llvm/Analysis/BasicAliasAnalysis.h>
#include <llvm/Analysis/MemoryLocation.h>
#include <llvm/Analysis/MemorySSA.h>
#include <llvm/Analysis/ScopedNoAliasAA.h>
#include <llvm/Analysis/TargetLibraryInfo.h>
#include <llvm/Analysis/TypeBasedAliasAnalysis.h>
#include <llvm/IR/Dominators.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Module.h>
#include <llvm/TargetParser/Host.h>

#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace rift::baselines::llvm::detail {
namespace {

struct ReachingDefinition {
    const ::llvm::Instruction *instruction = nullptr;
    bool through_phi = false;
};

void collect_reaching_definitions(
    const ::llvm::MemoryAccess *access, bool through_phi,
    const ::llvm::MemorySSA &memory_ssa,
    std::set<const ::llvm::MemoryAccess *> &visited,
    std::vector<ReachingDefinition> &definitions) {
    if (access == nullptr || memory_ssa.isLiveOnEntryDef(access) ||
        !visited.insert(access).second) {
        return;
    }
    if (const auto *phi = ::llvm::dyn_cast<::llvm::MemoryPhi>(access)) {
        for (unsigned index = 0; index < phi->getNumIncomingValues(); ++index) {
            collect_reaching_definitions(
                phi->getIncomingValue(index), true, memory_ssa, visited,
                definitions);
        }
        return;
    }
    const auto *use_or_def =
        ::llvm::dyn_cast<::llvm::MemoryUseOrDef>(access);
    if (use_or_def == nullptr) {
        return;
    }
    if (const auto *definition = ::llvm::dyn_cast<::llvm::MemoryDef>(access)) {
        if (definition->getMemoryInst() != nullptr) {
            definitions.push_back(
                {definition->getMemoryInst(), through_phi});
            return;
        }
    }
    collect_reaching_definitions(
        use_or_def->getDefiningAccess(), through_phi, memory_ssa, visited,
        definitions);
}

AliasEvidence alias_evidence(::llvm::AliasResult result) {
    if (result == ::llvm::AliasResult::NoAlias) {
        return AliasEvidence::NoAlias;
    }
    if (result == ::llvm::AliasResult::MayAlias) {
        return AliasEvidence::MayAlias;
    }
    if (result == ::llvm::AliasResult::PartialAlias) {
        return AliasEvidence::PartialAlias;
    }
    if (result == ::llvm::AliasResult::MustAlias) {
        return AliasEvidence::MustAlias;
    }
    return AliasEvidence::Unknown;
}

Certainty certainty_for(AliasEvidence alias) {
    return alias == AliasEvidence::MustAlias ? Certainty::Must
                                             : Certainty::May;
}

void append_memory_edges_for_function(
    ::llvm::Function &function, const NodeCatalog &catalog,
    std::vector<GraphEdge> &edges, std::vector<std::string> &diagnostics) {
    ::llvm::DominatorTree dominators(function);
    ::llvm::AssumptionCache assumptions(function);
    ::llvm::Triple triple(function.getParent()->getTargetTriple());
    if (triple.getTriple().empty()) {
        triple = ::llvm::Triple(::llvm::sys::getDefaultTargetTriple());
    }
    ::llvm::TargetLibraryInfoImpl library_info_impl(triple);
    ::llvm::TargetLibraryInfo library_info(library_info_impl);
    ::llvm::BasicAAResult basic_alias(
        function.getParent()->getDataLayout(), function, library_info,
        assumptions, &dominators);
    ::llvm::ScopedNoAliasAAResult scoped_alias;
    ::llvm::TypeBasedAAResult type_alias;
    ::llvm::AAResults alias_results(library_info);
    alias_results.addAAResult(basic_alias);
    alias_results.addAAResult(scoped_alias);
    alias_results.addAAResult(type_alias);

    ::llvm::MemorySSA memory_ssa(function, &alias_results, &dominators);
    memory_ssa.verifyMemorySSA();
    ::llvm::MemorySSAWalker *walker = memory_ssa.getWalker();

    std::set<std::pair<const ::llvm::Instruction *,
                       const ::llvm::Instruction *>>
        emitted;
    std::size_t function_edges = 0;
    for (::llvm::BasicBlock &block : function) {
        for (::llvm::Instruction &instruction : block) {
            if (!instruction.mayReadFromMemory() ||
                !catalog.contains(&instruction)) {
                continue;
            }
            ::llvm::MemoryUseOrDef *access =
                memory_ssa.getMemoryAccess(&instruction);
            if (access == nullptr) {
                continue;
            }
            const ::llvm::MemoryAccess *clobber =
                walker->getClobberingMemoryAccess(access);
            std::set<const ::llvm::MemoryAccess *> visited;
            std::vector<ReachingDefinition> definitions;
            collect_reaching_definitions(
                clobber, false, memory_ssa, visited, definitions);

            const std::optional<::llvm::MemoryLocation> use_location =
                ::llvm::MemoryLocation::getOrNone(&instruction);
            for (const ReachingDefinition &definition : definitions) {
                if (definition.instruction == nullptr ||
                    definition.instruction == &instruction ||
                    !catalog.contains(definition.instruction) ||
                    !emitted.emplace(
                                definition.instruction, &instruction)
                         .second) {
                    continue;
                }

                AliasEvidence alias = AliasEvidence::Unknown;
                const std::optional<::llvm::MemoryLocation> def_location =
                    ::llvm::MemoryLocation::getOrNone(
                        definition.instruction);
                if (def_location.has_value() && use_location.has_value()) {
                    alias = alias_evidence(alias_results.alias(
                        *def_location, *use_location));
                }
                if (alias == AliasEvidence::NoAlias) {
                    diagnostics.push_back(
                        "MemorySSA clobber rejected by AA as no-alias in function '" +
                        function.getName().str() + "'");
                    continue;
                }
                const EdgeKind kind = definition.through_phi
                                          ? EdgeKind::MemoryPhi
                                          : EdgeKind::MemoryDefUse;
                edges.push_back({
                    definition.instruction,
                    &instruction,
                    kind,
                    certainty_for(alias),
                    alias,
                    catalog.point(&instruction).location,
                    definition.through_phi
                        ? "MemorySSA reaching definition through MemoryPhi; alias result preserved"
                        : "MemorySSA clobber-to-read edge; alias result preserved",
                });
                ++function_edges;
            }
        }
    }
    diagnostics.push_back(
        "MemorySSA function '" + function.getName().str() +
        "' memory edges=" + std::to_string(function_edges));
}

}  // namespace

AnalysisResult analyze_memoryssa(const AnalysisInput &input) {
    std::vector<std::string> diagnostics;
    std::unique_ptr<LoadedModule> loaded =
        load_linked_module(input, diagnostics);
    if (loaded == nullptr || loaded->module == nullptr) {
        return unknown_matrix(
            input, method_profile(Method::LlvmMemorySsaAa),
            "LLVM module loading or verification failed", diagnostics);
    }

    NodeCatalog catalog(*loaded->module);
    std::vector<GraphEdge> edges;
    append_ssa_edges(*loaded->module, catalog, edges);
    const std::size_t ssa_edges = edges.size();
    for (::llvm::Function &function : *loaded->module) {
        if (!function.isDeclaration()) {
            append_memory_edges_for_function(
                function, catalog, edges, diagnostics);
        }
    }
    diagnostics.push_back(
        "LLVM SSA edges=" + std::to_string(ssa_edges) +
        ", combined edges=" + std::to_string(edges.size()));
    return analyze_llvm_graph(
        input, method_profile(Method::LlvmMemorySsaAa), catalog, edges,
        std::move(diagnostics));
}

}  // namespace rift::baselines::llvm::detail
