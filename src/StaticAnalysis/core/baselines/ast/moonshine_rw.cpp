#include "ast_baselines_internal.h"

#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/AST/Stmt.h>
#include <clang/Basic/SourceManager.h>

#include <algorithm>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace rift::baselines::ast::detail {
namespace {

using clang::BinaryOperator;
using clang::CallExpr;
using clang::ConditionalOperator;
using clang::Expr;
using clang::FieldDecl;
using clang::ForStmt;
using clang::FunctionDecl;
using clang::IfStmt;
using clang::MemberExpr;
using clang::RecordDecl;
using clang::SourceManager;
using clang::Stmt;
using clang::SwitchStmt;
using clang::UnaryOperator;
using clang::WhileStmt;

struct FieldFact {
    std::string key;
    ProgramPoint point;
};

struct FunctionSummary {
    std::map<std::string, FieldFact> writes;
    std::map<std::string, FieldFact> conditional_reads;
    std::set<std::string> callees;
};

struct CallSite {
    std::string symbol;
    std::string caller;
    std::string callee;
    ProgramPoint point;
    std::uint64_t offset = 0;
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

std::string function_key(
    const FunctionDecl *function, const SourceManager &manager) {
    if (function == nullptr) {
        return "<global>";
    }
    const FunctionDecl *canonical = function->getCanonicalDecl();
    const SourceLocation location =
        location_of(manager, canonical->getLocation());
    std::ostringstream stream;
    stream << canonical->getQualifiedNameAsString() << '@' << location.line
           << ':' << location.column;
    return stream.str();
}

FieldFact field_fact(
    const MemberExpr *member, const SourceManager &manager) {
    const auto *field = llvm::cast<FieldDecl>(member->getMemberDecl());
    const auto *record = llvm::dyn_cast<RecordDecl>(field->getDeclContext());
    std::string record_name =
        record == nullptr ? "<record>" : record->getQualifiedNameAsString();
    if (record_name.empty() && record != nullptr) {
        record_name = record->getNameAsString();
    }
    const std::string symbol = record_name + "." + field->getNameAsString();
    const SourceLocation location =
        location_of(manager, member->getMemberLoc());
    return {
        symbol,
        {symbol, symbol, location},
    };
}

class MemberCollector final
    : public clang::RecursiveASTVisitor<MemberCollector> {
  public:
    explicit MemberCollector(const SourceManager &manager)
        : manager_(manager) {}

    bool VisitMemberExpr(MemberExpr *member) {
        const FieldFact fact = field_fact(member, manager_);
        facts_.insert_or_assign(fact.key, fact);
        return true;
    }

    [[nodiscard]] const std::map<std::string, FieldFact> &facts() const {
        return facts_;
    }

  private:
    const SourceManager &manager_;
    std::map<std::string, FieldFact> facts_;
};

std::map<std::string, FieldFact> fields_in(
    const Stmt *statement, const SourceManager &manager) {
    if (statement == nullptr) {
        return {};
    }
    MemberCollector collector(manager);
    collector.TraverseStmt(const_cast<Stmt *>(statement));
    return collector.facts();
}

class MoonVisitor final
    : public clang::RecursiveASTVisitor<MoonVisitor> {
  public:
    explicit MoonVisitor(clang::ASTContext &context)
        : manager_(context.getSourceManager()) {}

    bool TraverseFunctionDecl(FunctionDecl *function) {
        if (function != nullptr &&
            manager_.isInSystemHeader(function->getLocation())) {
            return true;
        }
        FunctionDecl *previous = current_function_;
        current_function_ = function;
        summaries_.try_emplace(function_key(function, manager_));
        const bool result =
            clang::RecursiveASTVisitor<MoonVisitor>::TraverseFunctionDecl(
                function);
        current_function_ = previous;
        return result;
    }

    bool VisitBinaryOperator(BinaryOperator *operation) {
        if (operation->isAssignmentOp()) {
            add_writes(operation->getLHS());
        }
        return true;
    }

    bool VisitUnaryOperator(UnaryOperator *operation) {
        if (operation->isIncrementDecrementOp()) {
            add_writes(operation->getSubExpr());
        }
        return true;
    }

    bool VisitIfStmt(IfStmt *statement) {
        add_conditional_reads(statement->getCond());
        return true;
    }

    bool VisitWhileStmt(WhileStmt *statement) {
        add_conditional_reads(statement->getCond());
        return true;
    }

    bool VisitForStmt(ForStmt *statement) {
        add_conditional_reads(statement->getCond());
        return true;
    }

    bool VisitSwitchStmt(SwitchStmt *statement) {
        add_conditional_reads(statement->getCond());
        return true;
    }

    bool VisitConditionalOperator(ConditionalOperator *operation) {
        add_conditional_reads(operation->getCond());
        return true;
    }

    bool VisitCallExpr(CallExpr *call) {
        const FunctionDecl *callee = call->getDirectCallee();
        if (callee == nullptr || current_function_ == nullptr) {
            return true;
        }
        const std::string caller_key =
            function_key(current_function_, manager_);
        const std::string callee_key = function_key(callee, manager_);
        summaries_[caller_key].callees.insert(callee_key);
        summaries_.try_emplace(callee_key);
        const SourceLocation location =
            location_of(manager_, call->getExprLoc());
        const clang::SourceLocation spelling =
            manager_.getSpellingLoc(call->getExprLoc());
        const std::uint64_t offset =
            spelling.isValid() && spelling.isFileID()
                ? manager_.getFileOffset(spelling)
                : 0;
        calls_.push_back({
            callee->getNameAsString(),
            caller_key,
            callee_key,
            {
                "call:" + caller_key + "->" + callee_key + '@' +
                    std::to_string(location.line) + ':' +
                    std::to_string(location.column),
                callee->getNameAsString(),
                location,
            },
            offset,
        });
        return true;
    }

    void close_summaries() {
        bool changed = true;
        while (changed) {
            changed = false;
            for (auto &[function, summary] : summaries_) {
                (void)function;
                for (const std::string &callee : summary.callees) {
                    const auto iterator = summaries_.find(callee);
                    if (iterator == summaries_.end()) {
                        continue;
                    }
                    changed |= merge(summary.writes, iterator->second.writes);
                    changed |= merge(
                        summary.conditional_reads,
                        iterator->second.conditional_reads);
                }
            }
        }
    }

    [[nodiscard]] const std::map<std::string, FunctionSummary> &summaries()
        const {
        return summaries_;
    }

    [[nodiscard]] const std::vector<CallSite> &calls() const {
        return calls_;
    }

  private:
    static bool merge(
        std::map<std::string, FieldFact> &destination,
        const std::map<std::string, FieldFact> &source) {
        bool changed = false;
        for (const auto &[key, value] : source) {
            changed |= destination.emplace(key, value).second;
        }
        return changed;
    }

    FunctionSummary &current_summary() {
        return summaries_[function_key(current_function_, manager_)];
    }

    void add_writes(const Expr *expression) {
        if (current_function_ == nullptr) {
            return;
        }
        for (const auto &[key, value] : fields_in(expression, manager_)) {
            current_summary().writes.insert_or_assign(key, value);
        }
    }

    void add_conditional_reads(const Expr *expression) {
        if (current_function_ == nullptr || expression == nullptr) {
            return;
        }
        for (const auto &[key, value] : fields_in(expression, manager_)) {
            current_summary().conditional_reads.insert_or_assign(key, value);
        }
    }

    SourceManager &manager_;
    FunctionDecl *current_function_ = nullptr;
    std::map<std::string, FunctionSummary> summaries_;
    std::vector<CallSite> calls_;
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

std::optional<CallSite> resolve_call(
    const Anchor &anchor, const std::vector<CallSite> &calls) {
    std::vector<CallSite> matches;
    for (const CallSite &call : calls) {
        if (call.symbol == anchor.symbol &&
            same_file(anchor.location.file, call.point.location.file) &&
            call.point.location.line == anchor.location.line &&
            (anchor.location.column == 0 ||
             call.point.location.column == anchor.location.column)) {
            matches.push_back(call);
        }
    }
    if (matches.empty()) {
        return std::nullopt;
    }
    std::set<std::string> identities;
    for (const CallSite &match : matches) {
        identities.insert(
            match.caller + "->" + match.callee + '@' +
            std::to_string(match.offset));
    }
    return identities.size() == 1
               ? std::optional<CallSite>(matches.front())
               : std::nullopt;
}

}  // namespace

AnalysisResult analyze_moonshine(
    const CaseInput &input, clang::ASTUnit &unit) {
    AnalysisResult result;
    result.profile = method_profile(Method::MoonShineRw);
    MoonVisitor visitor(unit.getASTContext());
    visitor.TraverseDecl(unit.getASTContext().getTranslationUnitDecl());
    visitor.close_summaries();

    for (const Anchor &source_anchor : input.source_anchors) {
        const std::optional<CallSite> source =
            resolve_call(source_anchor, visitor.calls());
        if (!source.has_value()) {
            result.diagnostics.push_back(
                "MoonShine-RW requires a resolved direct producer call anchor: " +
                source_anchor.id);
        }
        for (const Anchor &property_anchor : input.property_anchors) {
            PairPrediction prediction;
            prediction.source = source_anchor;
            prediction.property = property_anchor;
            prediction.limitations = result.profile.limitations;
            const std::optional<CallSite> property =
                resolve_call(property_anchor, visitor.calls());
            if (!property.has_value()) {
                result.diagnostics.push_back(
                    "MoonShine-RW requires a resolved direct consumer call anchor: " +
                    property_anchor.id);
            }
            if (!source.has_value() || !property.has_value()) {
                prediction.status =
                    PredictionStatus::UnknownUnsupported;
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            if (source->caller != property->caller) {
                prediction.status =
                    PredictionStatus::UnknownUnsupported;
                prediction.matched_facts.push_back(
                    "cross-caller producer ordering is outside MoonShine-RW");
                result.diagnostics.push_back(
                    "MoonShine-RW cannot classify cross-caller order: " +
                    source_anchor.id + " -> " + property_anchor.id);
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            if (source->offset >= property->offset) {
                prediction.matched_facts.push_back(
                    "producer-before-consumer order not established in one caller");
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            const auto writer =
                visitor.summaries().find(source->callee);
            const auto reader =
                visitor.summaries().find(property->callee);
            if (writer == visitor.summaries().end() ||
                reader == visitor.summaries().end()) {
                prediction.status =
                    PredictionStatus::UnknownUnsupported;
                result.predictions.push_back(std::move(prediction));
                continue;
            }
            for (const auto &[field, write] : writer->second.writes) {
                const auto read =
                    reader->second.conditional_reads.find(field);
                if (read == reader->second.conditional_reads.end()) {
                    continue;
                }
                prediction.influence = InfluenceClass::MayInfluence;
                prediction.matched_facts.push_back(
                    "W(" + source_anchor.symbol + ") ∩ R_cond(" +
                    property_anchor.symbol + ") contains " + field);
                prediction.evidence_path.push_back({
                    source->point,
                    write.point,
                    EdgeKind::WriteSummary,
                    Certainty::May,
                    write.point.location,
                    "producer direct-call summary writes " + field,
                });
                prediction.evidence_path.push_back({
                    read->second.point,
                    property->point,
                    EdgeKind::ConditionalRead,
                    Certainty::May,
                    read->second.point.location,
                    "consumer conditional-read summary reads " + field,
                });
            }
            result.predictions.push_back(std::move(prediction));
        }
    }
    return result;
}

}  // namespace rift::baselines::ast::detail
