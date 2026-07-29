#ifndef RIFT_BASELINES_LLVM_LLVM_BASELINES_INTERNAL_H
#define RIFT_BASELINES_LLVM_LLVM_BASELINES_INTERNAL_H

#include "rift/baselines/llvm/llvm_baselines.h"

#include <llvm/IR/LLVMContext.h>

#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>

namespace llvm {
class Module;
class Value;
}  // namespace llvm

namespace rift::baselines::llvm::detail {

struct LoadedModule {
    ::llvm::LLVMContext context;
    std::unique_ptr<::llvm::Module> module;
};

struct MappingCandidate {
    const ::llvm::Value *value = nullptr;
    ProgramPoint point;
    std::set<std::string> symbols;
};

struct ResolvedLlvmAnchor {
    PredictionStatus status = PredictionStatus::UnknownUnsupported;
    std::vector<const ::llvm::Value *> values;
    std::vector<ProgramPoint> points;
    std::string reason;
};

class NodeCatalog {
  public:
    explicit NodeCatalog(const ::llvm::Module &module);

    [[nodiscard]] ResolvedLlvmAnchor resolve(const Anchor &anchor) const;
    [[nodiscard]] const ProgramPoint &point(const ::llvm::Value *value) const;
    [[nodiscard]] bool contains(const ::llvm::Value *value) const;
    [[nodiscard]] const std::vector<MappingCandidate> &candidates() const;

  private:
    std::map<const ::llvm::Value *, ProgramPoint> points_;
    std::vector<MappingCandidate> candidates_;
};

struct GraphEdge {
    const ::llvm::Value *from = nullptr;
    const ::llvm::Value *to = nullptr;
    EdgeKind kind = EdgeKind::SsaDefUse;
    Certainty certainty = Certainty::May;
    AliasEvidence alias = AliasEvidence::NotApplicable;
    SourceLocation evidence_location;
    std::string explanation;
};

[[nodiscard]] std::unique_ptr<LoadedModule> load_linked_module(
    const AnalysisInput &input, std::vector<std::string> &diagnostics);

[[nodiscard]] SourceLocation debug_location(const ::llvm::Value *value);
[[nodiscard]] std::string llvm_value_label(const ::llvm::Value *value);

void append_ssa_edges(
    const ::llvm::Module &module, const NodeCatalog &catalog,
    std::vector<GraphEdge> &edges);

[[nodiscard]] AnalysisResult analyze_llvm_graph(
    const AnalysisInput &input, MethodProfile profile,
    const NodeCatalog &catalog, const std::vector<GraphEdge> &edges,
    std::vector<std::string> diagnostics = {});

[[nodiscard]] AnalysisResult unknown_matrix(
    const AnalysisInput &input, MethodProfile profile, std::string reason,
    std::vector<std::string> diagnostics = {});

[[nodiscard]] AnalysisResult analyze_ssa(const AnalysisInput &input);
[[nodiscard]] AnalysisResult analyze_memoryssa(const AnalysisInput &input);
[[nodiscard]] AnalysisResult analyze_svf(const AnalysisInput &input);

}  // namespace rift::baselines::llvm::detail

#endif
