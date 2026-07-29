#include "rift/baselines/ast/ast_baselines.h"
#include "ast_baselines_internal.h"

#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Tooling/Tooling.h>

#include <algorithm>
#include <deque>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>

namespace rift::baselines::ast {
namespace {

using clang::ASTContext;
using clang::BinaryOperator;
using clang::CallExpr;
using clang::DeclRefExpr;
using clang::Expr;
using clang::FunctionDecl;
using clang::MemberExpr;
using clang::ParmVarDecl;
using clang::SourceManager;
using clang::Stmt;
using clang::ValueDecl;
using clang::VarDecl;

struct Entity {
    std::string key;
    std::string flat;
    std::string field;
    ProgramPoint point;
};

struct InternalEdge {
    Entity from;
    Entity to;
    EdgeKind kind = EdgeKind::Data;
    Certainty certainty = Certainty::May;
    SourceLocation evidence_location;
    std::string function;
    bool rhs_contains_call = false;
};

enum class OccurrenceKind {
    Declaration,
    Reference,
    Call,
};

struct Occurrence {
    std::string symbol;
    Entity entity;
    std::string function;
    std::uint64_t offset = 0;
    OccurrenceKind kind = OccurrenceKind::Reference;
};

SourceLocation source_location(const SourceManager &manager, clang::SourceLocation location) {
    if (location.isInvalid()) {
        return {};
    }
    const clang::SourceLocation spelling = manager.getSpellingLoc(location);
    const clang::PresumedLoc presumed = manager.getPresumedLoc(spelling);
    if (presumed.isInvalid()) {
        return {};
    }
    return {
        presumed.getFilename(),
        presumed.getLine(),
        presumed.getColumn(),
    };
}

std::string location_suffix(const SourceLocation &location) {
    std::ostringstream stream;
    stream << location.line << ':' << location.column;
    return stream.str();
}

std::string function_name(
    const FunctionDecl *function, const SourceManager &manager) {
    if (function == nullptr) {
        return "<global>";
    }
    const FunctionDecl *canonical = function->getCanonicalDecl();
    const SourceLocation location =
        source_location(manager, canonical->getLocation());
    std::ostringstream stream;
    stream << canonical->getQualifiedNameAsString() << ':'
           << canonical->getType().getAsString() << '@' << location.file << ':'
           << location.line << ':' << location.column;
    return stream.str();
}

class FactExtractor final
    : public clang::RecursiveASTVisitor<FactExtractor> {
  public:
    explicit FactExtractor(ASTContext &context)
        : manager_(context.getSourceManager()) {}

    bool TraverseFunctionDecl(FunctionDecl *declaration) {
        if (declaration != nullptr &&
            manager_.isInSystemHeader(declaration->getLocation())) {
            return true;
        }
        FunctionDecl *previous = current_function_;
        current_function_ = declaration;
        const bool result =
            clang::RecursiveASTVisitor<FactExtractor>::TraverseFunctionDecl(declaration);
        current_function_ = previous;
        return result;
    }

    bool VisitVarDecl(VarDecl *declaration) {
        if (manager_.isInSystemHeader(declaration->getLocation())) {
            return true;
        }
        const Entity left = entity_for_decl(declaration);
        occurrences_.push_back(make_occurrence(
            declaration->getNameAsString(), left, declaration->getLocation(),
            OccurrenceKind::Declaration));
        if (declaration->hasInit()) {
            add_assignment_edges(
                left, declaration->getInit(), EdgeKind::Initializer,
                declaration->getLocation());
        }
        return true;
    }

    bool VisitDeclRefExpr(DeclRefExpr *expression) {
        if (llvm::isa<FunctionDecl>(expression->getDecl())) {
            return true;
        }
        const Entity entity = entity_for_decl(expression->getDecl());
        occurrences_.push_back(make_occurrence(
            expression->getDecl()->getNameAsString(), entity,
            expression->getLocation(), OccurrenceKind::Reference));
        return true;
    }

    bool VisitMemberExpr(MemberExpr *expression) {
        const Entity entity = entity_for_member(expression);
        occurrences_.push_back(make_occurrence(
            expression->getMemberDecl()->getNameAsString(), entity,
            expression->getMemberLoc(), OccurrenceKind::Reference));
        return true;
    }

    bool VisitBinaryOperator(BinaryOperator *operation) {
        if (!operation->isAssignmentOp()) {
            return true;
        }
        const std::vector<Entity> left = entities_from_lvalue(operation->getLHS());
        for (const Entity &target : left) {
            add_assignment_edges(
                target, operation->getRHS(), EdgeKind::Assignment,
                operation->getOperatorLoc());
        }
        return true;
    }

    bool VisitCallExpr(CallExpr *call) {
        const FunctionDecl *callee = call->getDirectCallee();
        if (callee == nullptr) {
            return true;
        }
        const Entity call_entity = entity_for_call(call, callee);
        occurrences_.push_back(make_occurrence(
            callee->getNameAsString(), call_entity, call->getExprLoc(),
            OccurrenceKind::Call));
        return true;
    }

    [[nodiscard]] const std::vector<InternalEdge> &assignment_edges() const {
        return assignment_edges_;
    }

    [[nodiscard]] const std::vector<Occurrence> &occurrences() const {
        return occurrences_;
    }

  private:
    Entity entity_for_decl(const ValueDecl *declaration) const {
        const SourceLocation location =
            source_location(manager_, declaration->getLocation());
        const auto *parameter = llvm::dyn_cast<ParmVarDecl>(declaration);
        const auto *variable = llvm::dyn_cast<VarDecl>(declaration);
        std::string owner = "<value>";
        if (parameter != nullptr) {
            owner = function_name(
                llvm::dyn_cast<FunctionDecl>(parameter->getDeclContext()),
                manager_);
        } else if (variable != nullptr) {
            owner = function_name(
                llvm::dyn_cast<FunctionDecl>(variable->getDeclContext()),
                manager_);
        }
        const std::string symbol = declaration->getNameAsString();
        return {
            "var:" + owner + "::" + symbol + '@' + location_suffix(location),
            symbol,
            {},
            {"var:" + owner + "::" + symbol + '@' + location_suffix(location),
             symbol, location},
        };
    }

    Entity entity_for_member(const MemberExpr *member) const {
        std::string base = "<object>";
        const Expr *base_expression = member->getBase()->IgnoreParenImpCasts();
        if (const auto *reference =
                llvm::dyn_cast<DeclRefExpr>(base_expression)) {
            base = entity_for_decl(reference->getDecl()).key;
        }
        const std::string field_name =
            member->getMemberDecl()->getNameAsString();
        const std::string record =
            member->getMemberDecl()->getDeclContext()->getDeclKindName();
        const std::string separator = member->isArrow() ? "->" : ".";
        const std::string key = base + separator + field_name;
        const SourceLocation location =
            source_location(manager_, member->getMemberLoc());
        return {
            key,
            field_name,
            record + "." + field_name,
            {key, field_name, location},
        };
    }

    Entity entity_for_call(
        const CallExpr *call, const FunctionDecl *callee) const {
        const SourceLocation location =
            source_location(manager_, call->getExprLoc());
        const std::string symbol = callee->getNameAsString();
        const std::string key =
            "call:" + function_name(current_function_, manager_) + "->" +
            callee->getQualifiedNameAsString() + '@' +
            location_suffix(location);
        return {key, symbol, {}, {key, symbol, location}};
    }

    Occurrence make_occurrence(
        std::string symbol, Entity entity, clang::SourceLocation location,
        OccurrenceKind kind) const {
        const clang::SourceLocation spelling = manager_.getSpellingLoc(location);
        std::uint64_t offset = 0;
        if (spelling.isValid() && spelling.isFileID()) {
            offset = manager_.getFileOffset(spelling);
        }
        return {
            std::move(symbol),
            std::move(entity),
            function_name(current_function_, manager_),
            offset,
            kind,
        };
    }

    std::vector<Entity> entities_from_lvalue(const Expr *expression) const {
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            return {entity_for_decl(reference->getDecl())};
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(plain)) {
            return {entity_for_member(member)};
        }
        if (const auto *unary = llvm::dyn_cast<clang::UnaryOperator>(plain)) {
            return entities_from_lvalue(unary->getSubExpr());
        }
        return {};
    }

    void collect_value_entities(
        const Stmt *statement, std::vector<Entity> &output,
        bool &contains_call) const {
        if (statement == nullptr) {
            return;
        }
        if (llvm::isa<CallExpr>(statement)) {
            contains_call = true;
            // Assignment-only deliberately does not treat call arguments as
            // direct value-flow from argument to return value.
            return;
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(statement)) {
            output.push_back(entity_for_member(member));
            return;
        }
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(statement)) {
            if (!llvm::isa<FunctionDecl>(reference->getDecl())) {
                output.push_back(entity_for_decl(reference->getDecl()));
            }
            return;
        }
        for (const Stmt *child : statement->children()) {
            collect_value_entities(child, output, contains_call);
        }
    }

    void add_assignment_edges(
        const Entity &left, const Expr *right, EdgeKind kind,
        clang::SourceLocation evidence) {
        std::vector<Entity> right_entities;
        bool contains_call = false;
        collect_value_entities(right, right_entities, contains_call);
        std::set<std::string> seen;
        for (const Entity &source : right_entities) {
            if (!seen.insert(source.key).second) {
                continue;
            }
            assignment_edges_.push_back({
                source,
                left,
                (source.field.empty() && left.field.empty())
                    ? kind
                    : EdgeKind::Field,
                Certainty::May,
                source_location(manager_, evidence),
                function_name(current_function_, manager_),
                contains_call,
            });
        }
    }

    SourceManager &manager_;
    FunctionDecl *current_function_ = nullptr;
    std::vector<InternalEdge> assignment_edges_;
    std::vector<Occurrence> occurrences_;
};

bool same_file(std::string_view expected, std::string_view actual) {
    const auto normalized = [](std::string_view path) {
        std::string result(path);
        std::replace(result.begin(), result.end(), '\\', '/');
        while (result.starts_with("./")) {
            result.erase(0, 2);
        }
        return result;
    };
    const std::string left = normalized(expected);
    const std::string right = normalized(actual);
    return left == right || right.ends_with('/' + left) ||
           left.ends_with('/' + right);
}

std::optional<Occurrence> resolve_anchor(
    const Anchor &anchor, const std::vector<Occurrence> &occurrences) {
    std::vector<Occurrence> candidates;
    for (const Occurrence &occurrence : occurrences) {
        const SourceLocation &location = occurrence.entity.point.location;
        if (occurrence.symbol == anchor.symbol &&
            same_file(anchor.location.file, location.file) &&
            anchor.location.line == location.line &&
            (anchor.location.column == 0 ||
             anchor.location.column == location.column)) {
            candidates.push_back(occurrence);
        }
    }
    if (candidates.empty()) {
        return std::nullopt;
    }
    std::set<std::string> identities;
    for (const Occurrence &candidate : candidates) {
        identities.insert(candidate.entity.key);
    }
    if (identities.size() != 1) {
        return std::nullopt;
    }
    std::stable_sort(
        candidates.begin(), candidates.end(),
        [](const Occurrence &left, const Occurrence &right) {
            return left.kind < right.kind;
        });
    return candidates.front();
}

struct GraphEdge {
    std::string from;
    std::string to;
    const InternalEdge *fact = nullptr;
};

std::vector<const InternalEdge *> find_path(
    const std::string &source, const std::string &target,
    const std::vector<GraphEdge> &graph) {
    std::unordered_map<std::string, std::vector<std::size_t>> outgoing;
    for (std::size_t index = 0; index < graph.size(); ++index) {
        outgoing[graph[index].from].push_back(index);
    }
    std::deque<std::string> worklist{source};
    std::set<std::string> visited{source};
    std::unordered_map<std::string, std::pair<std::string, std::size_t>>
        predecessor;
    while (!worklist.empty()) {
        const std::string current = worklist.front();
        worklist.pop_front();
        if (current == target) {
            break;
        }
        for (const std::size_t edge_index : outgoing[current]) {
            const GraphEdge &edge = graph[edge_index];
            if (visited.insert(edge.to).second) {
                predecessor.emplace(
                    edge.to, std::make_pair(current, edge_index));
                worklist.push_back(edge.to);
            }
        }
    }
    if (!visited.contains(target)) {
        return {};
    }
    std::vector<const InternalEdge *> path;
    std::string current = target;
    while (current != source) {
        const auto iterator = predecessor.find(current);
        if (iterator == predecessor.end()) {
            return {};
        }
        path.push_back(graph[iterator->second.second].fact);
        current = iterator->second.first;
    }
    std::reverse(path.begin(), path.end());
    return path;
}

EvidenceEdge public_edge(const InternalEdge &edge) {
    return {
        edge.from.point,
        edge.to.point,
        edge.kind,
        edge.certainty,
        edge.evidence_location,
        "semantic AST assignment/initializer dependency",
    };
}

AnalysisResult analyze_assignment(
    const CaseInput &input, const FactExtractor &facts) {
    AnalysisResult result;
    result.profile = method_profile(Method::AdgAssignment);
    for (const Anchor &source_anchor : input.source_anchors) {
        const std::optional<Occurrence> source =
            resolve_anchor(source_anchor, facts.occurrences());
        if (!source.has_value()) {
            result.diagnostics.push_back(
                "unresolved source anchor: " + source_anchor.symbol);
        }
        for (const Anchor &property_anchor : input.property_anchors) {
            PairPrediction prediction;
            prediction.source = source_anchor;
            prediction.property = property_anchor;
            prediction.limitations = result.profile.limitations;
            const std::optional<Occurrence> property =
                resolve_anchor(property_anchor, facts.occurrences());
            if (!property.has_value()) {
                result.diagnostics.push_back(
                    "unresolved property anchor: " +
                    property_anchor.symbol);
            }
            if (!source.has_value() || !property.has_value()) {
                prediction.status = PredictionStatus::UnknownUnsupported;
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            if (source->function != property->function) {
                prediction.status = PredictionStatus::UnknownUnsupported;
                prediction.matched_facts.push_back(
                    "cross-function relation is outside this intraprocedural baseline");
                result.diagnostics.push_back(
                    "assignment baseline cannot classify cross-function pair: " +
                    source_anchor.id + " -> " + property_anchor.id);
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            if (source->kind == OccurrenceKind::Call ||
                property->kind == OccurrenceKind::Call) {
                prediction.status = PredictionStatus::UnknownUnsupported;
                prediction.matched_facts.push_back(
                    "call anchor is outside assignment-only semantics");
                result.diagnostics.push_back(
                    "assignment baseline cannot classify call-anchor pair: " +
                    source_anchor.id + " -> " + property_anchor.id);
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            std::vector<GraphEdge> graph;
            for (const InternalEdge &edge : facts.assignment_edges()) {
                if (edge.function != source->function) {
                    continue;
                }
                graph.push_back({edge.from.flat, edge.to.flat, &edge});
            }
            const std::vector<const InternalEdge *> path = find_path(
                source->entity.flat, property->entity.flat, graph);
            if (!path.empty()) {
                prediction.influence = InfluenceClass::MayInfluence;
                for (const InternalEdge *edge : path) {
                    prediction.evidence_path.push_back(public_edge(*edge));
                    prediction.matched_facts.push_back(
                        edge->from.flat + " -> " + edge->to.flat);
                }
            }
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

}  // namespace

MethodProfile method_profile(Method method) {
    switch (method) {
        case Method::AdgAssignment:
            return {
                method,
                "adgfuzz-style-assignment",
                {
                    "Clang AST semantic assignment operators",
                    "VarDecl initializer dependencies",
                    "name-flattened intraprocedural transitive closure",
                },
                {
                    "intraprocedural only; direct and indirect calls are not followed",
                    "field and object identity are flattened to names",
                    "alias, control, callback, queue, lifecycle, and timing dependencies are absent",
                    "positive reachability is a may-influence result, not a path-feasibility proof",
                    "NO means no path in the assignment abstraction, not proof of semantic non-influence",
                },
            };
        case Method::MoonShineRw:
            return {
                method,
                "moonshine-rw",
                {
                    "function write summaries",
                    "conditional-read summaries",
                    "direct-call summary closure",
                    "producer-before-consumer filtering",
                },
                {
                    "record-field summaries are object-insensitive",
                    "path values and branch feasibility are not represented",
                    "pointer aliasing can under-approximate writes and reads",
                    "thread/process producer ordering is unsupported",
                    "indirect calls and external side effects are unsupported",
                    "lexical producer-before-consumer order is not CFG or loop reachability",
                    "NO means no matching W/R_cond fact in this abstraction, not proof of semantic non-influence",
                },
            };
        case Method::PlainPdg:
            return {
                method,
                "plain-ast-pdg-property-slice",
                {
                    "data and lexical control dependencies",
                    "direct call/return parameter flow",
                    "field-sensitive and shallow alias edges",
                    "ordinary source-to-property graph slice",
                },
                {
                    "AST-level ordinary PDG approximation, not a path-sensitive LLVM PDG",
                    "alias handling is shallow and flow-insensitive",
                    "direct-call formal and return nodes are context-insensitive across call sites",
                    "conditional and multi-target pointer aliases are unsupported",
                    "controllability and fuzzable-frontier classification are absent",
                    "timer, scheduler, lifecycle, scope, and framework model packs are absent",
                    "positive reachability is a may-influence result",
                    "NO means no path in the plain PDG abstraction, not proof of semantic non-influence",
                },
            };
    }
    return {};
}

AnalysisResult analyze(const CaseInput &input, Method method) {
    AnalysisResult failure;
    failure.profile = method_profile(method);
    std::vector<std::string> arguments = input.compile_arguments;
    if (arguments.empty()) {
        arguments.push_back(
            input.language == "c11" ? "-std=c11" : "-std=c++20");
    }
    std::unique_ptr<clang::ASTUnit> unit =
        clang::tooling::buildASTFromCodeWithArgs(
            input.source_text, arguments,
            input.virtual_path.empty() ? "rift_input.cc"
                                       : input.virtual_path);
    if (unit == nullptr || unit->getDiagnostics().hasErrorOccurred()) {
        failure.diagnostics.push_back(
            unit == nullptr
                ? "Clang failed to build the input AST"
                : "Clang reported errors while building the input AST");
        for (const Anchor &source : input.source_anchors) {
            for (const Anchor &property : input.property_anchors) {
                PairPrediction prediction;
                prediction.source = source;
                prediction.property = property;
                prediction.status = PredictionStatus::ToolError;
                prediction.limitations = failure.profile.limitations;
                failure.predictions.push_back(std::move(prediction));
            }
        }
        return failure;
    }
    FactExtractor facts(unit->getASTContext());
    facts.TraverseDecl(unit->getASTContext().getTranslationUnitDecl());
    if (method == Method::AdgAssignment) {
        return analyze_assignment(input, facts);
    }
    if (method == Method::MoonShineRw) {
        return detail::analyze_moonshine(input, *unit);
    }
    if (method == Method::PlainPdg) {
        return detail::analyze_plain_pdg(input, *unit);
    }
    return failure;
}

std::string_view to_string(Method method) {
    switch (method) {
        case Method::AdgAssignment:
            return "adgfuzz-style-assignment";
        case Method::MoonShineRw:
            return "moonshine-rw";
        case Method::PlainPdg:
            return "plain-pdg";
    }
    return "unknown";
}

std::string_view to_string(InfluenceClass influence) {
    switch (influence) {
        case InfluenceClass::NoInfluence:
            return "no-influence";
        case InfluenceClass::MayInfluence:
            return "may-influence";
        case InfluenceClass::MustInfluence:
            return "must-influence";
    }
    return "unknown";
}

std::string_view to_string(PredictionStatus status) {
    switch (status) {
        case PredictionStatus::Resolved:
            return "resolved";
        case PredictionStatus::UnknownUnsupported:
            return "unknown-unsupported";
        case PredictionStatus::ToolError:
            return "tool-error";
    }
    return "unknown";
}

std::string_view to_string(EdgeKind kind) {
    switch (kind) {
        case EdgeKind::Assignment:
            return "assignment";
        case EdgeKind::Initializer:
            return "initializer";
        case EdgeKind::Data:
            return "data";
        case EdgeKind::Control:
            return "control";
        case EdgeKind::Call:
            return "call";
        case EdgeKind::Return:
            return "return";
        case EdgeKind::Field:
            return "field";
        case EdgeKind::Alias:
            return "alias";
        case EdgeKind::WriteSummary:
            return "write-summary";
        case EdgeKind::ConditionalRead:
            return "conditional-read";
    }
    return "unknown";
}

std::string_view to_string(Certainty certainty) {
    switch (certainty) {
        case Certainty::Must:
            return "must";
        case Certainty::May:
            return "may";
        case Certainty::Modelled:
            return "modelled";
        case Certainty::Unknown:
            return "unknown";
    }
    return "unknown";
}

}  // namespace rift::baselines::ast
