#include "llvm_baselines_internal.h"

#include <llvm/ADT/SmallVector.h>
#include <llvm/Analysis/ValueTracking.h>
#include <llvm/IR/Argument.h>
#include <llvm/IR/Constants.h>
#include <llvm/IR/DebugInfoMetadata.h>
#include <llvm/IR/Function.h>
#include <llvm/IR/GlobalVariable.h>
#include <llvm/IR/InstrTypes.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Instructions.h>
#include <llvm/IR/IntrinsicInst.h>
#include <llvm/IR/Module.h>
#include <llvm/IR/Verifier.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/Linker/Linker.h>
#include <llvm/Support/Path.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/raw_ostream.h>

#include <cstddef>
#include <deque>
#include <filesystem>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <utility>

namespace rift::baselines::llvm::detail {
namespace {

SourceLocation metadata_location(
    const ::llvm::DIFile *file, std::uint32_t line,
    std::uint32_t column = 0) {
    if (file == nullptr || line == 0) {
        return {};
    }
    const std::filesystem::path filename(file->getFilename().str());
    std::filesystem::path path = filename;
    if (!filename.is_absolute() && !file->getDirectory().empty()) {
        path = std::filesystem::path(file->getDirectory().str()) / filename;
    }
    return {path.lexically_normal().generic_string(), line, column};
}

SourceLocation instruction_location(const ::llvm::Instruction *instruction) {
    if (instruction == nullptr || !instruction->getDebugLoc()) {
        return {};
    }
    const ::llvm::DILocation *location = instruction->getDebugLoc().get();
    return metadata_location(
        location->getFile(), location->getLine(), location->getColumn());
}

bool has_directory(std::string_view path) {
    return path.find('/') != std::string_view::npos ||
           path.find('\\') != std::string_view::npos;
}

std::string normalized_path(std::string_view path) {
    if (path.empty()) {
        return {};
    }
    return std::filesystem::path(path).lexically_normal().generic_string();
}

bool same_file(std::string_view expected, std::string_view actual) {
    const std::string left = normalized_path(expected);
    const std::string right = normalized_path(actual);
    if (left.empty() || right.empty()) {
        return false;
    }
    if (left == right) {
        return true;
    }
    if (!has_directory(left)) {
        return std::filesystem::path(right).filename().generic_string() == left;
    }
    if (right.size() <= left.size() ||
        right.compare(right.size() - left.size(), left.size(), left) != 0) {
        return false;
    }
    return right[right.size() - left.size() - 1] == '/';
}

bool location_matches(
    const SourceLocation &expected, const SourceLocation &actual) {
    return expected.line != 0 && expected.line == actual.line &&
           same_file(expected.file, actual.file) &&
           // DILocalVariable carries the declaration line but no column.  In
           // particular, mem2reg rewrites dbg.declare into dbg.value records
           // whose intrinsic location is commonly line 0.  Treat a missing
           // LLVM column as unavailable evidence, then rely on the exact
           // file/line plus source symbol and uniqueness checks below.  A
           // non-zero LLVM column must still match exactly.
           (expected.column == 0 || actual.column == 0 ||
            expected.column == actual.column);
}

std::string point_entity(
    const ::llvm::Function &function, std::size_t block_index,
    std::size_t instruction_index, const ::llvm::Instruction &instruction) {
    std::ostringstream stream;
    stream << "llvm:inst:" << function.getName().str() << ":bb"
           << block_index << ":i" << instruction_index << ':'
           << instruction.getOpcodeName();
    return stream.str();
}

void insert_value_name(
    const ::llvm::Value *value,
    std::map<const ::llvm::Value *, std::set<std::string>> &symbols) {
    if (value != nullptr && value->hasName()) {
        symbols[value].insert(value->getName().str());
    }
}

void collect_operand_sources(
    const ::llvm::Value *value, const NodeCatalog &catalog,
    std::vector<const ::llvm::Value *> &sources,
    std::set<const ::llvm::Value *> &visited) {
    if (value == nullptr || !visited.insert(value).second) {
        return;
    }
    if (catalog.contains(value)) {
        sources.push_back(value);
        return;
    }
    const auto *constant = ::llvm::dyn_cast<::llvm::Constant>(value);
    if (constant == nullptr) {
        return;
    }
    for (const ::llvm::Use &operand : constant->operands()) {
        collect_operand_sources(operand.get(), catalog, sources, visited);
    }
}

struct PathResult {
    bool reached = false;
    std::vector<const GraphEdge *> edges;
};

using LlvmIncomingEdges =
    std::map<const ::llvm::Value *, std::vector<std::size_t>>;

PathResult find_backward_path(
    const std::vector<const ::llvm::Value *> &sources,
    const std::vector<const ::llvm::Value *> &targets,
    const std::vector<GraphEdge> &edges,
    const LlvmIncomingEdges &incoming) {
    PathResult result;
    std::set<const ::llvm::Value *> source_set(sources.begin(), sources.end());
    std::set<const ::llvm::Value *> target_set(targets.begin(), targets.end());
    for (const ::llvm::Value *source : sources) {
        if (target_set.contains(source)) {
            result.reached = true;
            return result;
        }
    }

    std::deque<const ::llvm::Value *> worklist;
    std::set<const ::llvm::Value *> visited;
    std::map<const ::llvm::Value *, std::size_t> successor;
    for (const ::llvm::Value *target : targets) {
        if (visited.insert(target).second) {
            worklist.push_back(target);
        }
    }

    const ::llvm::Value *reached_source = nullptr;
    while (!worklist.empty() && reached_source == nullptr) {
        const ::llvm::Value *current = worklist.front();
        worklist.pop_front();
        const auto iterator = incoming.find(current);
        if (iterator == incoming.end()) {
            continue;
        }
        for (const std::size_t edge_index : iterator->second) {
            const ::llvm::Value *next = edges[edge_index].from;
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
    const ::llvm::Value *current = reached_source;
    while (!target_set.contains(current)) {
        const auto iterator = successor.find(current);
        if (iterator == successor.end()) {
            result.reached = false;
            result.edges.clear();
            return result;
        }
        const GraphEdge &edge = edges[iterator->second];
        result.edges.push_back(&edge);
        current = edge.to;
    }
    return result;
}

bool invalid_stable_id(
    const Anchor &anchor, const std::map<std::string, std::size_t> &counts) {
    const auto iterator = counts.find(anchor.stable_id);
    return anchor.stable_id.empty() ||
           (iterator != counts.end() && iterator->second != 1);
}

std::map<std::string, std::size_t> id_counts(
    const std::vector<Anchor> &anchors) {
    std::map<std::string, std::size_t> counts;
    for (const Anchor &anchor : anchors) {
        ++counts[anchor.stable_id];
    }
    return counts;
}

AnchorResolution public_resolution(
    const Anchor &anchor, AnchorRole role,
    const ResolvedLlvmAnchor &resolution) {
    return {
        anchor.stable_id,
        role,
        resolution.status,
        resolution.points,
        resolution.reason,
    };
}

}  // namespace

SourceLocation debug_location(const ::llvm::Value *value) {
    if (const auto *instruction =
            ::llvm::dyn_cast_or_null<::llvm::Instruction>(value)) {
        return instruction_location(instruction);
    }
    if (const auto *global =
            ::llvm::dyn_cast_or_null<::llvm::GlobalVariable>(value)) {
        ::llvm::SmallVector<::llvm::DIGlobalVariableExpression *, 1> debug;
        global->getDebugInfo(debug);
        if (!debug.empty() && debug.front()->getVariable() != nullptr) {
            const ::llvm::DIGlobalVariable *variable =
                debug.front()->getVariable();
            return metadata_location(variable->getFile(), variable->getLine());
        }
    }
    return {};
}

std::string llvm_value_label(const ::llvm::Value *value) {
    if (value == nullptr) {
        return "<null>";
    }
    if (const auto *instruction = ::llvm::dyn_cast<::llvm::Instruction>(value)) {
        std::string label = instruction->getOpcodeName();
        if (instruction->hasName()) {
            label += ":" + instruction->getName().str();
        }
        return label;
    }
    if (const auto *argument = ::llvm::dyn_cast<::llvm::Argument>(value)) {
        return "argument:" + std::to_string(argument->getArgNo()) + ':' +
               argument->getName().str();
    }
    if (const auto *global = ::llvm::dyn_cast<::llvm::GlobalVariable>(value)) {
        return "global:" + global->getName().str();
    }
    return value->hasName() ? value->getName().str() : "<llvm-value>";
}

NodeCatalog::NodeCatalog(const ::llvm::Module &module) {
    std::map<const ::llvm::Value *, std::set<std::string>> symbols;

    std::size_t global_index = 0;
    for (const ::llvm::GlobalVariable &global : module.globals()) {
        ProgramPoint point{
            "llvm:global:" + std::to_string(global_index++) + ':' +
                global.getName().str(),
            global.getName().str(),
            debug_location(&global),
        };
        points_.emplace(&global, point);
        insert_value_name(&global, symbols);
    }

    for (const ::llvm::Function &function : module) {
        std::size_t argument_index = 0;
        for (const ::llvm::Argument &argument : function.args()) {
            ProgramPoint point{
                "llvm:arg:" + function.getName().str() + ':' +
                    std::to_string(argument_index),
                argument.getName().str(),
                {},
            };
            points_.emplace(&argument, point);
            insert_value_name(&argument, symbols);
            ++argument_index;
        }

        std::size_t block_index = 0;
        for (const ::llvm::BasicBlock &block : function) {
            std::size_t instruction_index = 0;
            for (const ::llvm::Instruction &instruction : block) {
                if (!::llvm::isa<::llvm::DbgInfoIntrinsic>(&instruction)) {
                    ProgramPoint point{
                        point_entity(
                            function, block_index, instruction_index,
                            instruction),
                        llvm_value_label(&instruction),
                        instruction_location(&instruction),
                    };
                    points_.emplace(&instruction, std::move(point));
                    insert_value_name(&instruction, symbols);
                    symbols[&instruction].insert(instruction.getOpcodeName());
                }
                ++instruction_index;
            }
            ++block_index;
        }
    }

    // Associate source-level variable names and declaration locations with
    // the exact LLVM values carried by debug intrinsics.
    for (const ::llvm::Function &function : module) {
        for (const ::llvm::BasicBlock &block : function) {
            for (const ::llvm::Instruction &instruction : block) {
                const auto *debug =
                    ::llvm::dyn_cast<::llvm::DbgVariableIntrinsic>(
                        &instruction);
                if (debug == nullptr || debug->getVariable() == nullptr) {
                    continue;
                }
                const ::llvm::DILocalVariable *variable = debug->getVariable();
                const std::string symbol = variable->getName().str();
                const SourceLocation location = metadata_location(
                    variable->getFile(), variable->getLine());
                for (unsigned index = 0;
                     index < debug->getNumVariableLocationOps(); ++index) {
                    const ::llvm::Value *operand =
                        debug->getVariableLocationOp(index);
                    if (operand == nullptr) {
                        continue;
                    }
                    if (operand->getType()->isPointerTy()) {
                        operand = operand->stripPointerCasts();
                    }
                    const auto point_iterator = points_.find(operand);
                    if (point_iterator == points_.end()) {
                        continue;
                    }
                    symbols[operand].insert(symbol);
                    ProgramPoint point = point_iterator->second;
                    point.symbol = symbol;
                    point.location = location;
                    candidates_.push_back(
                        {operand, std::move(point), {symbol}});
                    if (point_iterator->second.location.line == 0) {
                        point_iterator->second.location = location;
                        if (point_iterator->second.symbol.empty()) {
                            point_iterator->second.symbol = symbol;
                        }
                    }
                }
            }
        }
    }

    // Propagate direct operand variable names to their consuming instruction.
    // This remains a strict filter: an anchor-provided symbol must occur in
    // the debug/value facts associated with the exact instruction.
    for (const ::llvm::Function &function : module) {
        for (const ::llvm::BasicBlock &block : function) {
            for (const ::llvm::Instruction &instruction : block) {
                if (::llvm::isa<::llvm::DbgInfoIntrinsic>(&instruction)) {
                    continue;
                }
                std::set<std::string> instruction_symbols = symbols[&instruction];
                for (const ::llvm::Use &operand : instruction.operands()) {
                    const auto iterator = symbols.find(operand.get());
                    if (iterator != symbols.end()) {
                        instruction_symbols.insert(
                            iterator->second.begin(), iterator->second.end());
                    }
                }
                if (const auto *load =
                        ::llvm::dyn_cast<::llvm::LoadInst>(&instruction)) {
                    const ::llvm::Value *object =
                        ::llvm::getUnderlyingObject(load->getPointerOperand());
                    const auto iterator = symbols.find(object);
                    if (iterator != symbols.end()) {
                        instruction_symbols.insert(
                            iterator->second.begin(), iterator->second.end());
                    }
                } else if (const auto *store =
                               ::llvm::dyn_cast<::llvm::StoreInst>(
                                   &instruction)) {
                    const ::llvm::Value *object =
                        ::llvm::getUnderlyingObject(store->getPointerOperand());
                    const auto iterator = symbols.find(object);
                    if (iterator != symbols.end()) {
                        instruction_symbols.insert(
                            iterator->second.begin(), iterator->second.end());
                    }
                }
                candidates_.push_back(
                    {&instruction, points_.at(&instruction),
                     std::move(instruction_symbols)});
            }
        }
    }

    for (const ::llvm::GlobalVariable &global : module.globals()) {
        candidates_.push_back({&global, points_.at(&global), symbols[&global]});
    }
}

ResolvedLlvmAnchor NodeCatalog::resolve(const Anchor &anchor) const {
    ResolvedLlvmAnchor result;
    if (anchor.location.file.empty() || anchor.location.line == 0) {
        result.reason = "anchor lacks a usable debug file/line";
        return result;
    }

    std::set<const ::llvm::Value *> seen;
    for (const MappingCandidate &candidate : candidates_) {
        if (!location_matches(anchor.location, candidate.point.location)) {
            continue;
        }
        if (!anchor.symbol.empty() &&
            !candidate.symbols.contains(anchor.symbol)) {
            continue;
        }
        if (seen.insert(candidate.value).second) {
            result.values.push_back(candidate.value);
            result.points.push_back(candidate.point);
        }
    }
    if (result.values.empty()) {
        result.reason = anchor.symbol.empty()
                            ? "no LLVM value has the requested debug location"
                            : "no LLVM value has both the requested debug location and symbol";
        return result;
    }
    result.status = PredictionStatus::Resolved;
    result.reason = "exact debug anchor mapped to " +
                    std::to_string(result.values.size()) + " LLVM value(s)";
    return result;
}

const ProgramPoint &NodeCatalog::point(const ::llvm::Value *value) const {
    static const ProgramPoint unsupported{
        "llvm:unsupported", "<unsupported>", {}};
    const auto iterator = points_.find(value);
    return iterator == points_.end() ? unsupported : iterator->second;
}

bool NodeCatalog::contains(const ::llvm::Value *value) const {
    return points_.contains(value);
}

const std::vector<MappingCandidate> &NodeCatalog::candidates() const {
    return candidates_;
}

std::unique_ptr<LoadedModule> load_linked_module(
    const AnalysisInput &input, std::vector<std::string> &diagnostics) {
    if (input.bitcode_paths.empty()) {
        diagnostics.push_back("no LLVM bitcode input was supplied");
        return nullptr;
    }

    auto loaded = std::make_unique<LoadedModule>();
    for (const std::string &path : input.bitcode_paths) {
        ::llvm::SMDiagnostic diagnostic;
        std::unique_ptr<::llvm::Module> next =
            ::llvm::parseIRFile(path, diagnostic, loaded->context);
        if (next == nullptr) {
            std::string message;
            ::llvm::raw_string_ostream stream(message);
            diagnostic.print("rift-llvm-baseline", stream);
            diagnostics.push_back("failed to parse bitcode '" + path +
                                  "': " + stream.str());
            return nullptr;
        }
        if (loaded->module == nullptr) {
            loaded->module = std::move(next);
            continue;
        }
        ::llvm::Linker linker(*loaded->module);
        if (linker.linkInModule(std::move(next))) {
            diagnostics.push_back(
                "failed to link bitcode module '" + path + "'");
            return nullptr;
        }
    }

    std::string verification_error;
    ::llvm::raw_string_ostream stream(verification_error);
    if (::llvm::verifyModule(*loaded->module, &stream)) {
        diagnostics.push_back(
            "LLVM module verification failed: " + stream.str());
        return nullptr;
    }
    return loaded;
}

void append_ssa_edges(
    const ::llvm::Module &module, const NodeCatalog &catalog,
    std::vector<GraphEdge> &edges) {
    for (const ::llvm::Function &function : module) {
        for (const ::llvm::BasicBlock &block : function) {
            for (const ::llvm::Instruction &instruction : block) {
                if (::llvm::isa<::llvm::DbgInfoIntrinsic>(&instruction) ||
                    !catalog.contains(&instruction)) {
                    continue;
                }
                std::vector<const ::llvm::Value *> sources;
                std::set<const ::llvm::Value *> visited;
                for (const ::llvm::Use &operand : instruction.operands()) {
                    collect_operand_sources(
                        operand.get(), catalog, sources, visited);
                }
                std::set<const ::llvm::Value *> unique;
                for (const ::llvm::Value *source : sources) {
                    if (!unique.insert(source).second ||
                        source == &instruction) {
                        continue;
                    }
                    edges.push_back({
                        source,
                        &instruction,
                        EdgeKind::SsaDefUse,
                        Certainty::Must,
                        AliasEvidence::NotApplicable,
                        catalog.point(&instruction).location,
                        "LLVM SSA operand def-use edge; structural must does not imply must-execute",
                    });
                }
            }
        }
    }
}

AnalysisResult analyze_llvm_graph(
    const AnalysisInput &input, MethodProfile profile,
    const NodeCatalog &catalog, const std::vector<GraphEdge> &edges,
    std::vector<std::string> diagnostics) {
    AnalysisResult result;
    result.profile = std::move(profile);
    result.diagnostics = std::move(diagnostics);

    const auto source_counts = id_counts(input.source_anchors);
    const auto ap_counts = id_counts(input.ap_anchors);
    std::vector<ResolvedLlvmAnchor> source_resolutions;
    std::vector<ResolvedLlvmAnchor> ap_resolutions;
    LlvmIncomingEdges incoming;
    for (std::size_t edge_index = 0; edge_index < edges.size(); ++edge_index) {
        incoming[edges[edge_index].to].push_back(edge_index);
    }

    for (const Anchor &anchor : input.source_anchors) {
        ResolvedLlvmAnchor resolution;
        if (invalid_stable_id(anchor, source_counts)) {
            resolution.reason =
                "source stable ID is empty or duplicated in the input";
        } else {
            resolution = catalog.resolve(anchor);
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
        ResolvedLlvmAnchor resolution;
        if (invalid_stable_id(anchor, ap_counts)) {
            resolution.reason =
                "AP stable ID is empty or duplicated in the input";
        } else {
            resolution = catalog.resolve(anchor);
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

            const ResolvedLlvmAnchor &source =
                source_resolutions[source_index];
            const ResolvedLlvmAnchor &ap = ap_resolutions[ap_index];
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
                std::to_string(source.values.size()));
            prediction.matched_facts.push_back(
                "ap_anchor_targets=" + std::to_string(ap.values.size()));
            const PathResult path =
                find_backward_path(source.values, ap.values, edges, incoming);
            if (!path.reached) {
                prediction.influence = InfluenceClass::NoInfluence;
                prediction.matched_facts.push_back(
                    "no path in the selected baseline graph");
                result.predictions.push_back(std::move(prediction));
                continue;
            }

            prediction.influence = InfluenceClass::MayInfluence;
            prediction.matched_facts.push_back(
                "baseline_path_edges=" + std::to_string(path.edges.size()));
            if (path.edges.empty()) {
                prediction.matched_facts.push_back(
                    "source and AP anchors share an LLVM value");
            }
            for (const GraphEdge *edge : path.edges) {
                prediction.evidence_path.push_back({
                    catalog.point(edge->from),
                    catalog.point(edge->to),
                    edge->kind,
                    edge->certainty,
                    edge->alias,
                    edge->evidence_location,
                    edge->explanation,
                });
            }
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

AnalysisResult unknown_matrix(
    const AnalysisInput &input, MethodProfile profile, std::string reason,
    std::vector<std::string> diagnostics) {
    AnalysisResult result;
    result.profile = std::move(profile);
    diagnostics.push_back(reason);
    result.diagnostics = std::move(diagnostics);
    for (const Anchor &anchor : input.source_anchors) {
        result.anchor_resolutions.push_back({
            anchor.stable_id,
            AnchorRole::Source,
            PredictionStatus::UnknownUnsupported,
            {},
            reason,
        });
    }
    for (const Anchor &anchor : input.ap_anchors) {
        result.anchor_resolutions.push_back({
            anchor.stable_id,
            AnchorRole::AtomicProposition,
            PredictionStatus::UnknownUnsupported,
            {},
            reason,
        });
    }
    for (const Anchor &source : input.source_anchors) {
        for (const Anchor &ap : input.ap_anchors) {
            PairPrediction prediction;
            prediction.source_stable_id = source.stable_id;
            prediction.ap_stable_id = ap.stable_id;
            prediction.status = PredictionStatus::UnknownUnsupported;
            prediction.influence = InfluenceClass::Unknown;
            prediction.matched_facts.push_back(reason);
            prediction.limitations = result.profile.limitations;
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

}  // namespace rift::baselines::llvm::detail
