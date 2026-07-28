#include "ast_baselines_internal.h"

#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/AST/Stmt.h>
#include <clang/Basic/SourceManager.h>

#include <algorithm>
#include <cstdint>
#include <deque>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace rift::baselines::ast::detail {
namespace {

using clang::BinaryOperator;
using clang::CallExpr;
using clang::DeclRefExpr;
using clang::Expr;
using clang::FieldDecl;
using clang::ForStmt;
using clang::FunctionDecl;
using clang::IfStmt;
using clang::MemberExpr;
using clang::ReturnStmt;
using clang::SourceManager;
using clang::Stmt;
using clang::SwitchStmt;
using clang::UnaryOperator;
using clang::ValueDecl;
using clang::VarDecl;
using clang::WhileStmt;

struct Entity {
    std::string key;
    ProgramPoint point;
    std::string field_base;
    std::string field_name;
};

struct PdgEdge {
    Entity from;
    Entity to;
    EdgeKind kind = EdgeKind::Data;
    SourceLocation evidence_location;
    std::string explanation;
};

enum class OccurrenceKind {
    Declaration,
    Reference,
    Call,
};

struct Occurrence {
    std::string symbol;
    Entity entity;
    OccurrenceKind kind = OccurrenceKind::Reference;
};

struct AliasPair {
    Entity left;
    Entity right;
    SourceLocation evidence_location;
};

SourceLocation location_of(
    const SourceManager &manager, clang::SourceLocation location) {
    if (location.isInvalid()) {
        return {};
    }
    const clang::PresumedLoc presumed =
        manager.getPresumedLoc(manager.getSpellingLoc(location));
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

const FunctionDecl *definition_for(const FunctionDecl *function) {
    if (function == nullptr) {
        return nullptr;
    }
    if (const FunctionDecl *definition = function->getDefinition()) {
        return definition;
    }
    return function;
}

std::string function_key(
    const FunctionDecl *function, const SourceManager &manager) {
    if (function == nullptr) {
        return "<global>";
    }
    const FunctionDecl *canonical = function->getCanonicalDecl();
    const SourceLocation location =
        location_of(manager, canonical->getLocation());
    return canonical->getQualifiedNameAsString() + '@' +
           location_suffix(location);
}

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

class PdgVisitor final : public clang::RecursiveASTVisitor<PdgVisitor> {
  public:
    explicit PdgVisitor(clang::ASTContext &context)
        : manager_(context.getSourceManager()) {}

    bool TraverseFunctionDecl(FunctionDecl *function) {
        if (function != nullptr &&
            manager_.isInSystemHeader(function->getLocation())) {
            return true;
        }
        FunctionDecl *previous = current_function_;
        current_function_ = function;
        const bool result =
            clang::RecursiveASTVisitor<PdgVisitor>::TraverseFunctionDecl(
                function);
        current_function_ = previous;
        return result;
    }

    bool VisitVarDecl(VarDecl *declaration) {
        const Entity target = entity_for_decl(declaration);
        occurrences_.push_back({
            declaration->getNameAsString(),
            target,
            OccurrenceKind::Declaration,
        });
        if (!declaration->hasInit()) {
            return true;
        }
        add_data_edges(
            declaration->getInit(), target, EdgeKind::Initializer,
            declaration->getLocation(),
            "initializer data dependency");
        if (declaration->getType()->isPointerType()) {
            record_alias(
                target, declaration->getInit(), declaration->getLocation());
        }
        return true;
    }

    bool VisitDeclRefExpr(DeclRefExpr *reference) {
        if (llvm::isa<FunctionDecl>(reference->getDecl())) {
            return true;
        }
        occurrences_.push_back({
            reference->getDecl()->getNameAsString(),
            entity_for_decl(reference->getDecl()),
            OccurrenceKind::Reference,
        });
        return true;
    }

    bool VisitMemberExpr(MemberExpr *member) {
        const Entity entity = entity_for_member(member);
        occurrences_.push_back({
            member->getMemberDecl()->getNameAsString(),
            entity,
            OccurrenceKind::Reference,
        });
        fields_[{entity.field_base, entity.field_name}] = entity;
        return true;
    }

    bool VisitBinaryOperator(BinaryOperator *operation) {
        if (!operation->isAssignmentOp()) {
            return true;
        }
        const std::vector<Entity> targets =
            lvalue_entities(operation->getLHS());
        for (const Entity &target : targets) {
            add_data_edges(
                operation->getRHS(), target, EdgeKind::Data,
                operation->getOperatorLoc(),
                "assignment data dependency");
            if (const ValueDecl *declaration =
                    referenced_decl(operation->getLHS());
                declaration != nullptr &&
                declaration->getType()->isPointerType()) {
                record_alias(
                    target, operation->getRHS(),
                    operation->getOperatorLoc());
            }
        }
        return true;
    }

    bool VisitCallExpr(CallExpr *call) {
        const FunctionDecl *raw_callee = call->getDirectCallee();
        if (raw_callee == nullptr) {
            return true;
        }
        const FunctionDecl *callee = definition_for(raw_callee);
        const Entity call_entity = entity_for_call(call, callee);
        occurrences_.push_back({
            callee->getNameAsString(),
            call_entity,
            OccurrenceKind::Call,
        });

        const unsigned pair_count = std::min(
            call->getNumArgs(), callee->getNumParams());
        for (unsigned index = 0; index < pair_count; ++index) {
            const Entity parameter = entity_for_decl(callee->getParamDecl(index));
            const std::vector<Entity> arguments =
                values_in(call->getArg(index));
            for (const Entity &argument : arguments) {
                add_edge({
                    argument,
                    parameter,
                    EdgeKind::Call,
                    location_of(manager_, call->getExprLoc()),
                    "actual-to-formal direct-call dependency",
                });
                if (call->getType()->isVoidType()) {
                    add_edge({
                        argument,
                        call_entity,
                        EdgeKind::Call,
                        location_of(manager_, call->getExprLoc()),
                        "argument dependency of a void call",
                    });
                }
            }
        }

        if (!call->getType()->isVoidType()) {
            add_edge({
                return_entity(callee),
                call_entity,
                EdgeKind::Return,
                location_of(manager_, call->getExprLoc()),
                "direct callee return-to-call dependency",
            });
        }
        return true;
    }

    bool VisitReturnStmt(ReturnStmt *statement) {
        if (current_function_ == nullptr || statement->getRetValue() == nullptr) {
            return true;
        }
        const Entity returned = return_entity(current_function_);
        for (const Entity &value : values_in(statement->getRetValue())) {
            add_edge({
                value,
                returned,
                EdgeKind::Return,
                location_of(manager_, statement->getReturnLoc()),
                "returned-value dependency",
            });
        }
        return true;
    }

    bool VisitIfStmt(IfStmt *statement) {
        add_control_edges(statement->getCond(), statement->getThen());
        add_control_edges(statement->getCond(), statement->getElse());
        return true;
    }

    bool VisitWhileStmt(WhileStmt *statement) {
        add_control_edges(statement->getCond(), statement->getBody());
        return true;
    }

    bool VisitForStmt(ForStmt *statement) {
        add_control_edges(statement->getCond(), statement->getBody());
        return true;
    }

    bool VisitSwitchStmt(SwitchStmt *statement) {
        add_control_edges(statement->getCond(), statement->getBody());
        return true;
    }

    void finalize_alias_edges() {
        for (const AliasPair &alias : aliases_) {
            add_edge({
                alias.left,
                alias.right,
                EdgeKind::Alias,
                alias.evidence_location,
                "shallow flow-insensitive pointer alias",
            });
            add_edge({
                alias.right,
                alias.left,
                EdgeKind::Alias,
                alias.evidence_location,
                "shallow flow-insensitive pointer alias",
            });
            for (const auto &[field_key, left_field] : fields_) {
                if (field_key.first != alias.left.key) {
                    continue;
                }
                const auto right =
                    fields_.find({alias.right.key, field_key.second});
                if (right == fields_.end()) {
                    continue;
                }
                add_edge({
                    left_field,
                    right->second,
                    EdgeKind::Alias,
                    alias.evidence_location,
                    "field identity propagated over a shallow alias",
                });
                add_edge({
                    right->second,
                    left_field,
                    EdgeKind::Alias,
                    alias.evidence_location,
                    "field identity propagated over a shallow alias",
                });
            }
            for (const auto &[field_key, right_field] : fields_) {
                if (field_key.first != alias.right.key) {
                    continue;
                }
                const auto left =
                    fields_.find({alias.left.key, field_key.second});
                if (left == fields_.end()) {
                    continue;
                }
                add_edge({
                    left->second,
                    right_field,
                    EdgeKind::Alias,
                    alias.evidence_location,
                    "field identity propagated over a shallow alias",
                });
                add_edge({
                    right_field,
                    left->second,
                    EdgeKind::Alias,
                    alias.evidence_location,
                    "field identity propagated over a shallow alias",
                });
            }
        }
    }

    [[nodiscard]] const std::vector<PdgEdge> &edges() const {
        return edges_;
    }

    [[nodiscard]] const std::vector<Occurrence> &occurrences() const {
        return occurrences_;
    }

  private:
    Entity entity_for_decl(const ValueDecl *declaration) const {
        const SourceLocation location =
            location_of(manager_, declaration->getLocation());
        std::string owner = "<value>";
        if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
            owner = function_key(
                llvm::dyn_cast<FunctionDecl>(variable->getDeclContext()),
                manager_);
        }
        const std::string symbol = declaration->getNameAsString();
        const std::string key =
            "var:" + owner + "::" + symbol + '@' +
            location_suffix(location);
        return {key, {key, symbol, location}, {}, {}};
    }

    Entity entity_for_member(const MemberExpr *member) const {
        const Expr *base = member->getBase()->IgnoreParenImpCasts();
        Entity base_entity{
            "object:<unknown>",
            {"object:<unknown>", "<unknown>", {}},
            {},
            {},
        };
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(base)) {
            base_entity = entity_for_decl(reference->getDecl());
        } else if (const auto *parent_member =
                       llvm::dyn_cast<MemberExpr>(base)) {
            base_entity = entity_for_member(parent_member);
        } else if (const auto *unary = llvm::dyn_cast<UnaryOperator>(base)) {
            if (const ValueDecl *declaration =
                    referenced_decl(unary->getSubExpr())) {
                base_entity = entity_for_decl(declaration);
            }
        }
        const auto *field = llvm::cast<FieldDecl>(member->getMemberDecl());
        const std::string field_name =
            field->getQualifiedNameAsString().empty()
                ? field->getNameAsString()
                : field->getQualifiedNameAsString();
        const SourceLocation location =
            location_of(manager_, member->getMemberLoc());
        const std::string separator = member->isArrow() ? "->" : ".";
        const std::string key =
            "field:" + base_entity.key + separator + field_name;
        return {
            key,
            {key, field->getNameAsString(), location},
            base_entity.key,
            field_name,
        };
    }

    Entity entity_for_call(
        const CallExpr *call, const FunctionDecl *callee) const {
        const SourceLocation location =
            location_of(manager_, call->getExprLoc());
        const std::string callee_key = function_key(callee, manager_);
        const std::string key =
            "call:" + function_key(current_function_, manager_) + "->" +
            callee_key + '@' + location_suffix(location);
        return {
            key,
            {key, callee->getNameAsString(), location},
            {},
            {},
        };
    }

    Entity return_entity(const FunctionDecl *function) const {
        const FunctionDecl *definition = definition_for(function);
        const SourceLocation location =
            location_of(manager_, definition->getLocation());
        const std::string key =
            "return:" + function_key(definition, manager_);
        return {key, {key, "<return>", location}, {}, {}};
    }

    const ValueDecl *referenced_decl(const Expr *expression) const {
        if (expression == nullptr) {
            return nullptr;
        }
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            return reference->getDecl();
        }
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(plain)) {
            return referenced_decl(unary->getSubExpr());
        }
        return nullptr;
    }

    std::vector<Entity> lvalue_entities(const Expr *expression) const {
        if (expression == nullptr) {
            return {};
        }
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            return {entity_for_decl(reference->getDecl())};
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(plain)) {
            return {entity_for_member(member)};
        }
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(plain)) {
            return lvalue_entities(unary->getSubExpr());
        }
        return {};
    }

    void collect_values(const Stmt *statement, std::vector<Entity> &output)
        const {
        if (statement == nullptr) {
            return;
        }
        if (const auto *call = llvm::dyn_cast<CallExpr>(statement)) {
            if (const FunctionDecl *callee = call->getDirectCallee()) {
                output.push_back(entity_for_call(call, definition_for(callee)));
            }
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
            collect_values(child, output);
        }
    }

    std::vector<Entity> values_in(const Stmt *statement) const {
        std::vector<Entity> entities;
        collect_values(statement, entities);
        std::set<std::string> seen;
        std::vector<Entity> unique;
        for (Entity &entity : entities) {
            if (seen.insert(entity.key).second) {
                unique.push_back(std::move(entity));
            }
        }
        return unique;
    }

    void add_data_edges(
        const Expr *expression, const Entity &target, EdgeKind kind,
        clang::SourceLocation evidence, std::string explanation) {
        for (const Entity &source : values_in(expression)) {
            EdgeKind actual_kind = kind;
            if (!source.field_name.empty() || !target.field_name.empty()) {
                actual_kind = EdgeKind::Field;
            }
            add_edge({
                source,
                target,
                actual_kind,
                location_of(manager_, evidence),
                explanation,
            });
        }
    }

    void record_alias(
        const Entity &pointer, const Expr *initializer,
        clang::SourceLocation evidence) {
        const ValueDecl *pointee = referenced_decl(initializer);
        if (pointee == nullptr) {
            return;
        }
        aliases_.push_back({
            pointer,
            entity_for_decl(pointee),
            location_of(manager_, evidence),
        });
    }

    void collect_effects(const Stmt *statement, std::vector<Entity> &effects)
        const {
        if (statement == nullptr) {
            return;
        }
        if (const auto *operation =
                llvm::dyn_cast<BinaryOperator>(statement);
            operation != nullptr && operation->isAssignmentOp()) {
            const std::vector<Entity> targets =
                lvalue_entities(operation->getLHS());
            effects.insert(effects.end(), targets.begin(), targets.end());
        } else if (const auto *operation =
                       llvm::dyn_cast<UnaryOperator>(statement);
                   operation != nullptr &&
                   operation->isIncrementDecrementOp()) {
            const std::vector<Entity> targets =
                lvalue_entities(operation->getSubExpr());
            effects.insert(effects.end(), targets.begin(), targets.end());
        } else if (const auto *call = llvm::dyn_cast<CallExpr>(statement)) {
            if (const FunctionDecl *callee = call->getDirectCallee()) {
                effects.push_back(
                    entity_for_call(call, definition_for(callee)));
            }
        } else if (const auto *returned =
                       llvm::dyn_cast<ReturnStmt>(statement)) {
            (void)returned;
            if (current_function_ != nullptr) {
                effects.push_back(return_entity(current_function_));
            }
        } else if (const auto *declarations =
                       llvm::dyn_cast<clang::DeclStmt>(statement)) {
            for (const clang::Decl *declaration : declarations->decls()) {
                if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
                    effects.push_back(entity_for_decl(variable));
                }
            }
        }
        for (const Stmt *child : statement->children()) {
            collect_effects(child, effects);
        }
    }

    void add_control_edges(const Expr *condition, const Stmt *body) {
        if (condition == nullptr || body == nullptr) {
            return;
        }
        const std::vector<Entity> controls = values_in(condition);
        std::vector<Entity> effects;
        collect_effects(body, effects);
        std::map<std::string, Entity> unique_effects;
        for (Entity &effect : effects) {
            unique_effects.insert_or_assign(effect.key, std::move(effect));
        }
        for (const Entity &control : controls) {
            for (const auto &[key, effect] : unique_effects) {
                (void)key;
                add_edge({
                    control,
                    effect,
                    EdgeKind::Control,
                    condition == nullptr
                        ? SourceLocation{}
                        : location_of(manager_, condition->getExprLoc()),
                    "lexical guard control dependency",
                });
            }
        }
    }

    void add_edge(PdgEdge edge) {
        const std::string identity =
            edge.from.key + '\n' + edge.to.key + '\n' +
            std::string(to_string(edge.kind));
        if (edge_identities_.insert(identity).second) {
            edges_.push_back(std::move(edge));
        }
    }

    SourceManager &manager_;
    FunctionDecl *current_function_ = nullptr;
    std::vector<PdgEdge> edges_;
    std::vector<Occurrence> occurrences_;
    std::vector<AliasPair> aliases_;
    std::map<std::pair<std::string, std::string>, Entity> fields_;
    std::set<std::string> edge_identities_;
};

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

std::vector<const PdgEdge *> find_path(
    const std::string &source, const std::string &target,
    const std::vector<PdgEdge> &edges) {
    std::unordered_map<std::string, std::vector<std::size_t>> outgoing;
    for (std::size_t index = 0; index < edges.size(); ++index) {
        outgoing[edges[index].from.key].push_back(index);
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
        const auto iterator = outgoing.find(current);
        if (iterator == outgoing.end()) {
            continue;
        }
        for (const std::size_t edge_index : iterator->second) {
            const PdgEdge &edge = edges[edge_index];
            if (visited.insert(edge.to.key).second) {
                predecessor.emplace(
                    edge.to.key, std::make_pair(current, edge_index));
                worklist.push_back(edge.to.key);
            }
        }
    }
    if (!visited.contains(target)) {
        return {};
    }
    std::vector<const PdgEdge *> path;
    std::string current = target;
    while (current != source) {
        const auto iterator = predecessor.find(current);
        if (iterator == predecessor.end()) {
            return {};
        }
        path.push_back(&edges[iterator->second.second]);
        current = iterator->second.first;
    }
    std::reverse(path.begin(), path.end());
    return path;
}

EvidenceEdge public_edge(const PdgEdge &edge) {
    return {
        edge.from.point,
        edge.to.point,
        edge.kind,
        Certainty::May,
        edge.evidence_location,
        edge.explanation,
    };
}

}  // namespace

AnalysisResult analyze_plain_pdg(
    const CaseInput &input, clang::ASTUnit &unit) {
    AnalysisResult result;
    result.profile = method_profile(Method::PlainPdg);
    PdgVisitor visitor(unit.getASTContext());
    visitor.TraverseDecl(unit.getASTContext().getTranslationUnitDecl());
    visitor.finalize_alias_edges();

    for (const Anchor &source_anchor : input.source_anchors) {
        const std::optional<Occurrence> source =
            resolve_anchor(source_anchor, visitor.occurrences());
        if (!source.has_value()) {
            result.diagnostics.push_back(
                "plain PDG could not resolve source anchor: " +
                source_anchor.id);
        }
        for (const Anchor &property_anchor : input.property_anchors) {
            PairPrediction prediction;
            prediction.source = source_anchor;
            prediction.property = property_anchor;
            prediction.limitations = result.profile.limitations;
            const std::optional<Occurrence> property =
                resolve_anchor(property_anchor, visitor.occurrences());
            if (!property.has_value()) {
                result.diagnostics.push_back(
                    "plain PDG could not resolve property anchor: " +
                    property_anchor.id);
            }
            if (!source.has_value() || !property.has_value()) {
                prediction.status = PredictionStatus::UnknownUnsupported;
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            const std::vector<const PdgEdge *> path = find_path(
                source->entity.key, property->entity.key, visitor.edges());
            if (!path.empty()) {
                prediction.influence = InfluenceClass::MayInfluence;
                for (const PdgEdge *edge : path) {
                    prediction.evidence_path.push_back(public_edge(*edge));
                    prediction.matched_facts.push_back(
                        edge->from.point.entity + " -> " +
                        edge->to.point.entity + " [" +
                        std::string(to_string(edge->kind)) + ']');
                }
            }
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

}  // namespace rift::baselines::ast::detail
