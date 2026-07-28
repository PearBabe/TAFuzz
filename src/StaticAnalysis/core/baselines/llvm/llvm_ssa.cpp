#include "llvm_baselines_internal.h"

#include <llvm/IR/Module.h>

#include <memory>
#include <string>
#include <vector>

namespace rift::baselines::llvm::detail {

AnalysisResult analyze_ssa(const AnalysisInput &input) {
    std::vector<std::string> diagnostics;
    std::unique_ptr<LoadedModule> loaded =
        load_linked_module(input, diagnostics);
    if (loaded == nullptr || loaded->module == nullptr) {
        return unknown_matrix(
            input, method_profile(Method::LlvmSsaDefUse),
            "LLVM module loading or verification failed", diagnostics);
    }

    NodeCatalog catalog(*loaded->module);
    std::vector<GraphEdge> edges;
    append_ssa_edges(*loaded->module, catalog, edges);
    diagnostics.push_back(
        "LLVM SSA graph edges=" + std::to_string(edges.size()));
    return analyze_llvm_graph(
        input, method_profile(Method::LlvmSsaDefUse), catalog, edges,
        std::move(diagnostics));
}

}  // namespace rift::baselines::llvm::detail
