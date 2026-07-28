#include "rift/core/index.h"
#include "rift/core/artifacts.h"
#include "rift/core/value_transfer.h"

#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/Decl.h>
#include <clang/AST/DeclCXX.h>
#include <clang/AST/Expr.h>
#include <clang/AST/ExprCXX.h>
#include <clang/AST/ParentMapContext.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/AST/Stmt.h>
#include <clang/AST/StmtCXX.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendActions.h>
#include <clang/Index/USRGeneration.h>
#include <clang/Analysis/CFG.h>
#include <clang/Lex/Preprocessor.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>

#include <llvm/ADT/SmallString.h>
#include <llvm/Support/Casting.h>

#include <algorithm>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <map>
#include <memory>
#include <limits>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#if defined(__GLIBC__)
#include <malloc.h>
#endif

namespace rift::core {
namespace {

using clang::ASTContext;
using clang::BinaryOperator;
using clang::CastExpr;
using clang::CallExpr;
using clang::ConditionalOperator;
using clang::Decl;
using clang::DeclRefExpr;
using clang::Expr;
using clang::FieldDecl;
using clang::ForStmt;
using clang::FunctionDecl;
using clang::IfStmt;
using clang::InitListExpr;
using clang::MemberExpr;
using clang::NamedDecl;
using clang::ParmVarDecl;
using clang::QualType;
using clang::RecordDecl;
using clang::ReturnStmt;
using clang::SourceManager;
using clang::Stmt;
using clang::SwitchStmt;
using clang::UnaryOperator;
using clang::ValueDecl;
using clang::VarDecl;
using clang::WhileStmt;

struct TuAccumulator {
    TranslationUnitRecord record;
    StageStatus status = StageStatus::Complete;
    std::vector<EntityRef> entities;
    std::vector<AbstractObject> objects;
    std::vector<SemanticNode> nodes;
    std::vector<SemanticRelation> relations;
    std::vector<FunctionSummary> summaries;
    std::vector<CallSiteSummary> callsites;
    std::vector<CoverageGap> gaps;
    std::vector<InputFileDigest> input_files;
    std::vector<std::string> diagnostics;
    SemanticValueTransferIndex value_transfers;
};

struct BuiltTransferExpression {
    std::string root_expression_id;
    std::vector<std::string> input_node_ids;
    TransferSoundness soundness = TransferSoundness::Unknown;
    DefinednessClass definedness = DefinednessClass::Unknown;
    std::optional<std::string> defined_when_expression_id;
    std::vector<std::string> uncertainty_reasons;
};

StageStatus combine_status(StageStatus left, StageStatus right);

class SingleCommandDatabase final : public clang::tooling::CompilationDatabase {
  public:
    explicit SingleCommandDatabase(const CompilationCommand &command)
        : command_(
              command.working_directory, command.source_file,
              command.arguments, "") {}

    std::vector<clang::tooling::CompileCommand> getCompileCommands(
        llvm::StringRef file_path) const override {
        const std::filesystem::path requested(file_path.str());
        const std::filesystem::path expected(command_.Filename);
        if (requested.lexically_normal() == expected.lexically_normal()) {
            return {command_};
        }
        return {};
    }

    std::vector<std::string> getAllFiles() const override {
        return {command_.Filename};
    }

    std::vector<clang::tooling::CompileCommand>
    getAllCompileCommands() const override {
        return {command_};
    }

  private:
    clang::tooling::CompileCommand command_;
};

std::string normalize_path(const std::string &value) {
    std::string result = std::filesystem::path(value).lexically_normal().generic_string();
    while (result.starts_with("./")) {
        result.erase(0, 2);
    }
    return result;
}

std::string location_material(const SourceLocation &location) {
    std::ostringstream stream;
    stream << location.file << ':' << location.line << ':' << location.column
           << ':' << location.end_line << ':' << location.end_column;
    return stream.str();
}

EntityKind entity_kind(const NamedDecl *declaration) {
    if (llvm::isa<clang::CXXConstructorDecl>(declaration)) {
        return EntityKind::Constructor;
    }
    if (llvm::isa<clang::CXXDestructorDecl>(declaration)) {
        return EntityKind::Destructor;
    }
    if (llvm::isa<clang::CXXMethodDecl>(declaration)) {
        return EntityKind::Method;
    }
    if (llvm::isa<FunctionDecl>(declaration)) {
        return EntityKind::Function;
    }
    if (llvm::isa<ParmVarDecl>(declaration)) {
        return EntityKind::Parameter;
    }
    if (llvm::isa<FieldDecl>(declaration)) {
        return EntityKind::Field;
    }
    if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
        return variable->hasGlobalStorage() ? EntityKind::Global
                                            : EntityKind::Local;
    }
    if (llvm::isa<RecordDecl>(declaration)) {
        return EntityKind::Type;
    }
    return EntityKind::Unknown;
}

ValueKind value_kind(QualType type) {
    if (type.isNull()) {
        return ValueKind::Unknown;
    }
    const QualType canonical = type.getCanonicalType();
    if (canonical->isBooleanType()) {
        return ValueKind::Boolean;
    }
    if (canonical->isEnumeralType()) {
        return ValueKind::Enumeration;
    }
    if (canonical->isIntegerType()) {
        return ValueKind::Integer;
    }
    if (canonical->isFloatingType()) {
        return ValueKind::Floating;
    }
    if (canonical->isPointerType() || canonical->isReferenceType()) {
        return ValueKind::Pointer;
    }
    if (canonical->isRecordType()) {
        return ValueKind::Record;
    }
    if (canonical->isArrayType()) {
        return ValueKind::Array;
    }
    return ValueKind::Unknown;
}

ValueType type_info(
    QualType type, ASTContext &context,
    const std::vector<LogicalPathRoot> &identity_roots) {
    ValueType result;
    if (type.isNull()) {
        return result;
    }
    const QualType canonical = type.getCanonicalType();
    result.kind = value_kind(canonical);
    result.canonical = canonicalize_identity_text(
        identity_roots, canonical.getAsString());
    if (!canonical->isIncompleteType() && !canonical->isDependentType() &&
        !canonical->isVoidType()) {
        const std::uint64_t width = context.getTypeSize(canonical);
        if (width > 0 && width <= std::numeric_limits<std::uint32_t>::max()) {
            result.bit_width = static_cast<std::uint32_t>(width);
        }
    }
    if (canonical->isIntegerType() || canonical->isEnumeralType()) {
        result.is_signed = canonical->isSignedIntegerOrEnumerationType();
    }
    return result;
}

bool same_location(const SourceLocation &left, const SourceLocation &right) {
    return normalize_path(left.file) == normalize_path(right.file) &&
           left.line == right.line && left.column == right.column;
}

void append_unique_location(
    std::vector<SourceLocation> &locations, const SourceLocation &location) {
    if (location.file.empty() || location.line == 0 || location.column == 0) {
        return;
    }
    if (std::none_of(
            locations.begin(), locations.end(),
            [&](const SourceLocation &candidate) {
                return same_location(candidate, location);
            })) {
        locations.push_back(location);
    }
}

void append_unique(std::vector<std::string> &values, const std::string &value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

bool valid_digest(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](const char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}

class FactVisitor final : public clang::RecursiveASTVisitor<FactVisitor> {
  public:
    FactVisitor(
        ASTContext &context, TuAccumulator &output,
        std::vector<LogicalPathRoot> identity_roots,
        std::filesystem::path working_directory, IndexOptions options,
        ValueTransferOptions transfer_options)
        : context_(context), manager_(context.getSourceManager()), output_(output),
          identity_roots_(std::move(identity_roots)),
          working_directory_(std::move(working_directory)), options_(options),
          transfer_options_(transfer_options) {
        output_.value_transfers.status = StageStatus::Complete;
        output_.value_transfers.limits = transfer_options_;
    }

    bool TraverseDecl(Decl *declaration) {
        if (declaration == nullptr) {
            return true;
        }
        auto *function = llvm::dyn_cast<FunctionDecl>(declaration);
        if (function == nullptr) {
            return clang::RecursiveASTVisitor<FactVisitor>::TraverseDecl(
                declaration);
        }
        if (should_skip(function->getLocation())) {
            return true;
        }

        // RecursiveASTVisitor dispatches C++ methods, constructors,
        // destructors, conversions, and function-template children through
        // their specialised Traverse*Decl methods.  A TraverseFunctionDecl
        // override therefore sees only plain FunctionDecls and leaves calls
        // in those C++ bodies without an enclosing function.  Establish the
        // context at the generic declaration boundary, then let the base
        // dispatcher select the specialised traversal while the context is
        // live.
        FunctionDecl *previous = current_function_;
        FunctionSummary *previous_summary = current_summary_;
        current_function_ = function;
        const std::string function_id = ensure_entity(function);
        current_summary_ = ensure_summary(function, function_id);
        const bool result =
            clang::RecursiveASTVisitor<FactVisitor>::TraverseDecl(declaration);
        if (function->doesThisDeclarationHaveABody()) {
            add_cfg_control_dependencies(function);
        }
        current_function_ = previous;
        current_summary_ = previous_summary;
        return result;
    }

    bool VisitVarDecl(VarDecl *declaration) {
        if (declaration == nullptr || llvm::isa<ParmVarDecl>(declaration) ||
            should_skip(declaration->getLocation())) {
            return true;
        }
        const std::vector<std::string> targets = nodes_for_lvalue(declaration);
        if (targets.empty()) {
            add_gap(
                "unresolved_declaration", GapEffect::SoundnessRisk,
                "Variable declaration could not be represented as an access path",
                location(declaration->getLocation()), {});
            return true;
        }
        if (!declaration->hasInit()) {
            return true;
        }
        const Expr *initializer = declaration->getInit();
        if (declaration->getType()->isPointerType() ||
            declaration->getType()->isReferenceType()) {
            record_pointer_alias(declaration, initializer, targets.front());
        }
        if (const auto *list = llvm::dyn_cast<InitListExpr>(
                initializer->IgnoreParenImpCasts())) {
            if (add_aggregate_initializer(declaration, list)) {
                return true;
            }
        }
        add_value_relations(
            initializer, targets, RelationKind::Data,
            location(declaration->getLocation()), "initializer value flow");
        return true;
    }

    bool VisitBinaryOperator(BinaryOperator *operation) {
        if (operation == nullptr || !operation->isAssignmentOp() ||
            should_skip(operation->getOperatorLoc())) {
            return true;
        }
        std::vector<std::string> targets = nodes_for_lvalue(operation->getLHS());
        if (targets.empty()) {
            add_gap(
                "unsupported_lvalue", GapEffect::SoundnessRisk,
                "Assignment target is outside the supported access-path subset",
                location(operation->getOperatorLoc()), {});
            return true;
        }
        add_value_relations(
            operation->getRHS(), targets, RelationKind::Data,
            location(operation->getOperatorLoc()), "assignment value flow",
            operation->isCompoundAssignmentOp());
        if (operation->isCompoundAssignmentOp()) {
            for (const std::string &target : targets) {
                add_relation(
                    target, target, RelationKind::Data, Certainty::May,
                    location(operation->getOperatorLoc()),
                    "compound assignment reads and writes its target");
            }
        }
        if (const ValueDecl *target_decl = referenced_decl(operation->getLHS());
            target_decl != nullptr &&
            (target_decl->getType()->isPointerType() ||
             target_decl->getType()->isReferenceType())) {
            record_pointer_alias(target_decl, operation->getRHS(), targets.front());
        }
        return true;
    }

    bool VisitUnaryOperator(UnaryOperator *operation) {
        if (operation == nullptr || !operation->isIncrementDecrementOp() ||
            should_skip(operation->getOperatorLoc())) {
            return true;
        }
        for (const std::string &target : nodes_for_lvalue(operation->getSubExpr())) {
            const std::string relation = add_relation(
                target, target, RelationKind::Data, Certainty::May,
                location(operation->getOperatorLoc()),
                "increment/decrement reads and writes its target");
            record_expression_transfer(
                operation->getSubExpr(), target, RelationKind::Data,
                location(operation->getOperatorLoc()), {relation},
                std::nullopt, std::nullopt, true, {target});
        }
        return true;
    }

    bool VisitReturnStmt(ReturnStmt *statement) {
        if (statement == nullptr || current_summary_ == nullptr ||
            !current_summary_->return_node_id || statement->getRetValue() == nullptr) {
            return true;
        }
        add_value_relations(
            statement->getRetValue(), {*current_summary_->return_node_id},
            RelationKind::Return, location(statement->getReturnLoc()),
            "returned value reaches function return slot");
        return true;
    }

    bool VisitCallExpr(CallExpr *call) {
        if (call != nullptr && !should_skip(call->getExprLoc())) {
            (void)ensure_callsite(call);
            if (const FunctionDecl *callee = call->getDirectCallee()) {
                const std::string name = callee->getNameAsString();
                if (name == "setjmp" || name == "_setjmp" ||
                    name == "sigsetjmp" || name == "longjmp" ||
                    name == "siglongjmp") {
                    add_gap(
                        "cfg_nonlocal_control_transfer",
                        GapEffect::SoundnessRisk,
                        "Non-local setjmp/longjmp control transfer is not represented by intraprocedural CFG postdominance",
                        location(call->getExprLoc()), {ensure_entity(callee)});
                }
            }
        }
        return true;
    }

    bool VisitCXXTryStmt(clang::CXXTryStmt *statement) {
        if (statement != nullptr && !should_skip(statement->getTryLoc())) {
            add_gap(
                "cfg_exceptional_control_flow", GapEffect::SoundnessRisk,
                "C++ exception dispatch and unwinding are not fully represented by the current control-dependence summary",
                location(statement->getTryLoc()), {current_function_id()});
        }
        return true;
    }

    bool VisitCXXThrowExpr(clang::CXXThrowExpr *expression) {
        if (expression != nullptr && !should_skip(expression->getThrowLoc())) {
            add_gap(
                "cfg_exceptional_control_flow", GapEffect::SoundnessRisk,
                "C++ throw/unwind effects are retained as an explicit CFG coverage gap",
                location(expression->getThrowLoc()), {current_function_id()});
        }
        return true;
    }

    bool VisitIndirectGotoStmt(clang::IndirectGotoStmt *statement) {
        if (statement != nullptr && !should_skip(statement->getGotoLoc())) {
            add_gap(
                "cfg_indirect_goto", GapEffect::SoundnessRisk,
                "Computed-goto target closure is not modelled by the current control-dependence summary",
                location(statement->getGotoLoc()), {current_function_id()});
        }
        return true;
    }

    bool VisitCoroutineBodyStmt(clang::CoroutineBodyStmt *statement) {
        if (statement != nullptr && !should_skip(statement->getBeginLoc())) {
            add_gap(
                "cfg_coroutine_suspension", GapEffect::SoundnessRisk,
                "Coroutine suspend/resume control transfer requires a lifecycle model",
                location(statement->getBeginLoc()), {current_function_id()});
        }
        return true;
    }

    bool VisitAsmStmt(clang::AsmStmt *statement) {
        if (statement != nullptr && !should_skip(statement->getAsmLoc())) {
            add_gap(
                "inline_assembly_effect", GapEffect::SoundnessRisk,
                "Inline assembly effects are outside the Clang AST value/control subset",
                location(statement->getAsmLoc()), {current_function_id()});
        }
        return true;
    }

    bool VisitIfStmt(IfStmt *statement) {
        (void)statement;
        return true;
    }

    bool VisitWhileStmt(WhileStmt *statement) {
        (void)statement;
        return true;
    }

    bool VisitForStmt(ForStmt *statement) {
        (void)statement;
        return true;
    }

    bool VisitSwitchStmt(SwitchStmt *statement) {
        (void)statement;
        return true;
    }

    bool VisitCXXNewExpr(clang::CXXNewExpr *expression) {
        if (expression != nullptr && !should_skip(expression->getExprLoc())) {
            add_gap(
                "heap_object_summary", GapEffect::PrecisionLoss,
                "Heap allocation is represented by an allocation-site summary",
                location(expression->getExprLoc()), {});
        }
        return true;
    }

    void finalize(const std::string &predefines) {
        for (CallSiteSummary &callsite : output_.callsites) {
            if (callsite.direct && !callsite.candidate_callee_ids.empty()) {
                continue;
            }
            callsite.status = StageStatus::ConservativeIncomplete;
        }
        capture_input_files(predefines);
    }

  private:
    bool should_skip(clang::SourceLocation source) const {
        return source.isInvalid() ||
               (!options_.include_system_headers &&
                manager_.isInSystemHeader(source));
    }

    static std::string stable_file_name(std::string value) {
        for (char &character : value) {
            if (!((character >= 'a' && character <= 'z') ||
                  (character >= 'A' && character <= 'Z') ||
                  (character >= '0' && character <= '9') ||
                  character == '.' || character == '_' || character == '-')) {
                character = '_';
            }
        }
        return value.empty() ? "file" : value;
    }

    static std::filesystem::path physical_provenance_path(
        const std::filesystem::path &observed) {
        // Resolve an existing file before removing `..` components.  A purely
        // lexical normalization is not filesystem-preserving when the
        // spelling crosses a symlink (for example /lib -> /usr/lib).
        std::error_code error;
        const std::filesystem::path canonical =
            std::filesystem::canonical(observed, error);
        if (!error) {
            return canonical;
        }
        error.clear();
        const std::filesystem::path absolute =
            observed.is_absolute()
                ? observed
                : std::filesystem::absolute(observed, error);
        // Keep the original absolute spelling if the file is virtual or
        // disappears.  Certificate generation will then fail closed while
        // rehashing it instead of attesting a different lexical path.
        return error ? observed : absolute;
    }

    InputFileRole mapped_file_role(
        const std::string &logical_path, bool system) const {
        if (system) {
            return InputFileRole::System;
        }
        if (logical_path == output_.record.source_file) {
            return InputFileRole::Main;
        }
        constexpr std::string_view prefix = "riftpath://v1/";
        const std::size_t separator = logical_path.find('/', prefix.size());
        const std::string root =
            logical_path.starts_with(prefix) && separator != std::string::npos
                ? logical_path.substr(
                      prefix.size(), separator - prefix.size())
                : std::string();
        return root == "build" || root.find("generated") != std::string::npos
                   ? InputFileRole::Generated
                   : InputFileRole::UserHeader;
    }

    void append_input_file(
        std::string logical_path, llvm::StringRef bytes,
        InputFileRole role,
        std::optional<std::filesystem::path> observed_path = std::nullopt) {
        const std::string digest = sha256_hex(bytes.str());
        const std::string id = stable_id(
            "input-file", std::string(kIdentityScheme) + '\0' +
                              to_string(role) + '\0' + logical_path + '\0' +
                              digest);
        if (!input_file_ids_.insert(id).second) {
            if (observed_path) {
                for (InputFileDigest &existing : output_.input_files) {
                    if (existing.input_file_id == id) {
                        append_unique(
                            existing.observed_paths,
                            physical_provenance_path(*observed_path).string());
                        std::sort(
                            existing.observed_paths.begin(),
                            existing.observed_paths.end());
                        break;
                    }
                }
            }
            append_unique(output_.record.input_file_ids, id);
            return;
        }
        InputFileDigest input{
            id, std::move(logical_path), digest, role,
            static_cast<std::uint64_t>(bytes.size()), {}};
        if (observed_path) {
            input.observed_paths.push_back(
                physical_provenance_path(*observed_path).string());
        }
        output_.input_files.push_back(std::move(input));
        append_unique(output_.record.input_file_ids, id);
    }

    void capture_input_files(const std::string &predefines) {
        for (auto iterator = manager_.fileinfo_begin();
             iterator != manager_.fileinfo_end(); ++iterator) {
            const std::optional<llvm::StringRef> bytes =
                iterator->second->getBufferDataIfLoaded();
            if (!bytes) {
                continue;
            }
            std::filesystem::path physical = iterator->first.getName().str();
            if (physical.is_relative()) {
                physical = working_directory_ / physical;
            }
            const clang::FileID file_id =
                manager_.translateFile(iterator->first);
            const bool system =
                !file_id.isInvalid() && manager_.isInSystemHeader(
                                           manager_.getLocForStartOfFile(file_id));
            std::optional<std::string> logical =
                logical_identity_path(identity_roots_, physical);
            if (!logical && !system) {
                record_unmapped_source_identity();
                continue;
            }
            if (!logical) {
                const std::string digest = sha256_hex(bytes->str());
                logical = "riftpath://v1/toolchain/system/" + digest + '/' +
                          stable_file_name(physical.filename().string());
            }
            append_input_file(
                *logical, *bytes, mapped_file_role(*logical, system),
                physical);
        }
        append_input_file(
            "riftpath://v1/toolchain/predefines/" +
                sha256_hex(predefines),
            predefines, InputFileRole::Toolchain);
        std::sort(
            output_.input_files.begin(), output_.input_files.end(),
            [](const InputFileDigest &left, const InputFileDigest &right) {
                return std::tie(
                           left.logical_path, left.role, left.sha256,
                           left.input_file_id) <
                       std::tie(
                           right.logical_path, right.role, right.sha256,
                           right.input_file_id);
            });
        std::sort(
            output_.record.input_file_ids.begin(),
            output_.record.input_file_ids.end());
        const bool has_main = std::any_of(
            output_.input_files.begin(), output_.input_files.end(),
            [](const InputFileDigest &input) {
                return input.role == InputFileRole::Main;
            });
        if (!has_main) {
            output_.status = StageStatus::Failed;
            output_.record.status = StageStatus::Failed;
            CoverageGap gap;
            gap.gap_id = stable_id(
                "gap", "main_input_digest_missing\0" +
                           output_.record.translation_unit_id);
            gap.kind = "main_input_digest_missing";
            gap.effect = GapEffect::StageFailure;
            gap.detail =
                "The parsed main-file buffer is absent from the input digest manifest";
            gap.affected_ids = {output_.record.translation_unit_id};
            output_.gaps.push_back(std::move(gap));
        }
    }

    SourceLocation location(
        clang::SourceLocation begin,
        clang::SourceLocation end = clang::SourceLocation()) {
        if (begin.isInvalid()) {
            return generated_location();
        }
        const clang::SourceLocation spelling = manager_.getSpellingLoc(begin);
        const clang::SourceLocation primary =
            begin.isMacroID() ? manager_.getExpansionLoc(begin) : spelling;
        const clang::PresumedLoc presumed = manager_.getPresumedLoc(primary);
        if (presumed.isInvalid()) {
            return generated_location();
        }
        SourceLocation result;
        std::filesystem::path physical_file =
            manager_.getFilename(primary).str();
        if (physical_file.is_relative()) {
            physical_file = working_directory_ / physical_file;
        }
        const std::optional<std::string> logical_file =
            logical_identity_path(identity_roots_, physical_file);
        if (!logical_file) {
            if (manager_.isInSystemHeader(primary)) {
                const clang::FileID file_id = manager_.getFileID(primary);
                bool invalid_buffer = file_id.isInvalid();
                llvm::StringRef bytes;
                if (!invalid_buffer) {
                    bytes = manager_.getBufferData(file_id, &invalid_buffer);
                }
                if (invalid_buffer) {
                    return generated_location();
                }
                result.file =
                    "riftpath://v1/toolchain/system/" +
                    sha256_hex(bytes.str()) + '/' +
                    stable_file_name(physical_file.filename().string());
            } else {
                record_unmapped_source_identity();
                result.file = "riftpath://v1/unmapped/";
            }
        } else {
            result.file = *logical_file;
        }
        result.line = presumed.getLine();
        result.column = presumed.getColumn();
        if (end.isValid()) {
            const clang::SourceLocation primary_end =
                end.isMacroID() ? manager_.getExpansionLoc(end)
                                : manager_.getSpellingLoc(end);
            const clang::PresumedLoc end_location =
                manager_.getPresumedLoc(primary_end);
            if (end_location.isValid()) {
                result.end_line = end_location.getLine();
                result.end_column = end_location.getColumn();
            }
        }
        if (options_.retain_macro_stack && begin.isMacroID()) {
            clang::SourceLocation cursor = begin;
            std::set<unsigned> seen;
            while (cursor.isMacroID() && seen.insert(cursor.getRawEncoding()).second) {
                const clang::SourceLocation caller =
                    manager_.getImmediateMacroCallerLoc(cursor);
                const clang::PresumedLoc macro_location =
                    manager_.getPresumedLoc(manager_.getSpellingLoc(cursor));
                if (macro_location.isValid()) {
                    std::filesystem::path macro_physical = manager_.getFilename(
                        manager_.getSpellingLoc(cursor)).str();
                    if (macro_physical.is_relative()) {
                        macro_physical = working_directory_ / macro_physical;
                    }
                    const std::optional<std::string> macro_logical =
                        logical_identity_path(identity_roots_, macro_physical);
                    if (!macro_logical) {
                        if (manager_.isInSystemHeader(
                                manager_.getSpellingLoc(cursor))) {
                            cursor = caller;
                            continue;
                        }
                        record_unmapped_source_identity();
                    }
                    std::ostringstream stream;
                    stream << (macro_logical
                                   ? *macro_logical
                                   : "riftpath://v1/unmapped/")
                           << ':' << macro_location.getLine() << ':'
                           << macro_location.getColumn();
                    result.macro_stack.push_back(stream.str());
                }
                if (caller == cursor) {
                    break;
                }
                cursor = caller;
            }
        }
        return result;
    }

    static SourceLocation generated_location() {
        SourceLocation result;
        result.file =
            "riftpath://v1/toolchain/generated/" +
            sha256_hex("clang-source-location-unavailable");
        result.line = 1;
        result.column = 1;
        result.location_kind = "unknown";
        return result;
    }

    void record_unmapped_source_identity() {
        if (unmapped_identity_recorded_) {
            return;
        }
        unmapped_identity_recorded_ = true;
        output_.status = StageStatus::Failed;
        output_.record.status = StageStatus::Failed;
        CoverageGap gap;
        gap.gap_id = stable_id(
            "gap", "unmapped_source_identity\0" +
                       output_.record.translation_unit_id);
        gap.kind = "unmapped_source_identity";
        gap.effect = GapEffect::StageFailure;
        gap.detail =
            "A non-system spelling or macro source file is outside every declared logical identity root";
        gap.affected_ids = {output_.record.translation_unit_id};
        output_.gaps.push_back(std::move(gap));
        output_.diagnostics.push_back(
            output_.record.translation_unit_id +
            ": unmapped non-system source identity path");
    }

    std::string current_function_id() {
        if (current_function_ != nullptr) {
            return ensure_entity(current_function_);
        }
        return synthetic_owner_override_.value_or(std::string());
    }

    const VarDecl *enclosing_global_initializer(const CallExpr *call) {
        if (call == nullptr) {
            return nullptr;
        }
        clang::DynTypedNode cursor = clang::DynTypedNode::create(*call);
        // Parent maps can be ambiguous for instantiated/template nodes.  Such
        // cases use the explicit non-function fallback summary below.
        for (unsigned depth = 0; depth < 128; ++depth) {
            const auto parents = context_.getParents(cursor);
            if (parents.size() != 1) {
                return nullptr;
            }
            const clang::DynTypedNode &parent = parents[0];
            if (parent.get<FunctionDecl>() != nullptr) {
                return nullptr;
            }
            if (const auto *variable = parent.get<VarDecl>()) {
                return variable->hasGlobalStorage() && variable->hasInit()
                           ? variable
                           : nullptr;
            }
            cursor = parent;
        }
        return nullptr;
    }

    std::pair<std::string, FunctionSummary *>
    ensure_nonfunction_call_owner(
        const CallExpr *call, const SourceLocation &at) {
        const VarDecl *initializer = enclosing_global_initializer(call);
        std::string phase_kind;
        std::string phase_material;
        std::string reason;
        std::string gap_kind;
        std::string gap_detail;
        if (initializer != nullptr) {
            phase_kind = "global-initializer";
            // The initializer entity already carries the correct linkage
            // identity: ODR/external definitions are shared, whereas
            // internal/unique-external definitions include the TU identity.
            // Reusing it here deduplicates one logical inline initializer
            // without conflating TU-local storage.
            phase_material = "initializer=" + ensure_entity(initializer);
            reason = "cross_translation_unit_initialization_order_unmodelled";
            gap_kind = "global_initializer_order";
            gap_detail =
                "A call in a global initializer is retained under a synthetic initializer phase; cross-translation-unit initialization order remains unknown";
        } else {
            phase_kind = "translation-unit-nonfunction";
            phase_material =
                "tu=" + output_.record.translation_unit_id +
                "|site=" + location_material(at);
            reason = "nonfunction_call_execution_context_unresolved";
            gap_kind = "nonfunction_call_context";
            gap_detail =
                "A call outside a traversed function body is retained under a synthetic phase because its execution context is not uniquely classifiable";
        }
        ValueType phase_type;
        phase_type.kind = ValueKind::Unknown;
        phase_type.canonical = "void ()";
        const std::string owner = ensure_synthetic_entity(
            phase_kind, phase_material, at, phase_type,
            IdentityStatus::Summary, EntityKind::Function);
        const auto known = summary_indices_.find(owner);
        if (known != summary_indices_.end()) {
            return {owner, &output_.summaries[known->second]};
        }
        FunctionSummary summary;
        summary.function_entity_id = owner;
        summary.status = StageStatus::ConservativeIncomplete;
        summary.uncertainty_reasons.push_back(reason);
        const std::size_t index = output_.summaries.size();
        output_.summaries.push_back(std::move(summary));
        summary_indices_[owner] = index;
        add_gap(
            gap_kind, GapEffect::SoundnessRisk, gap_detail, at,
            {owner, output_.record.translation_unit_id});
        return {owner, &output_.summaries[index]};
    }

    std::optional<std::string> usr_for(const NamedDecl *declaration) const {
        if (declaration == nullptr) {
            return std::nullopt;
        }
        llvm::SmallString<256> buffer;
        if (clang::index::generateUSRForDecl(
                declaration->getCanonicalDecl(), buffer)) {
            return std::nullopt;
        }
        std::string usr = buffer.str().str();
        return canonicalize_identity_text(identity_roots_, std::move(usr));
    }

    std::string qualified_signature(const NamedDecl *declaration) const {
        std::string name = declaration->getQualifiedNameAsString();
        if (const auto *value = llvm::dyn_cast<ValueDecl>(declaration)) {
            name += ':' + value->getType().getCanonicalType().getAsString();
        } else {
            name += ':' + std::string(declaration->getDeclKindName());
        }
        return canonicalize_identity_text(identity_roots_, std::move(name));
    }

    bool has_translation_unit_local_identity(
        const NamedDecl *declaration) const {
        const Decl *cursor = declaration;
        while (cursor != nullptr) {
            if (const auto *named = llvm::dyn_cast<NamedDecl>(cursor)) {
                const clang::Linkage linkage = named->getFormalLinkage();
                if (linkage == clang::Linkage::Internal ||
                    linkage == clang::Linkage::UniqueExternal) {
                    return true;
                }
                const auto *variable = llvm::dyn_cast<VarDecl>(named);
                if (variable != nullptr && variable->isFileVarDecl() &&
                    linkage == clang::Linkage::None) {
                    return true;
                }
            }
            cursor = llvm::dyn_cast_or_null<Decl>(cursor->getDeclContext());
        }
        return false;
    }

    std::string ensure_entity(const NamedDecl *declaration) {
        if (declaration == nullptr) {
            return {};
        }
        const NamedDecl *canonical =
            llvm::cast<NamedDecl>(declaration->getCanonicalDecl());
        if (const auto found = decl_entities_.find(canonical);
            found != decl_entities_.end()) {
            return found->second;
        }
        const SourceLocation at = location(canonical->getLocation());
        const std::optional<std::string> usr = usr_for(canonical);
        const std::string signature = qualified_signature(canonical);
        std::string material = usr.has_value()
                                   ? "usr\0" + *usr
                                   : "fallback\0" + signature + '\0' +
                                         location_material(at);
        if (has_translation_unit_local_identity(canonical)) {
            material += "\0translation-unit\0" +
                        output_.record.translation_unit_id;
        }
        const std::string id = stable_id("entity", material);
        decl_entities_.emplace(canonical, id);
        auto existing = entity_indices_.find(id);
        if (existing == entity_indices_.end()) {
            EntityRef entity;
            entity.entity_id = id;
            entity.kind = entity_kind(canonical);
            entity.identity_status = usr ? IdentityStatus::Exact
                                         : IdentityStatus::Summary;
            entity.usr = usr;
            entity.qualified_signature = signature;
            if (const auto *value = llvm::dyn_cast<ValueDecl>(canonical)) {
                entity.canonical_type =
                    canonicalize_identity_text(
                        identity_roots_,
                        value->getType().getCanonicalType().getAsString());
            }
            entity.translation_unit_ids.insert(output_.record.translation_unit_id);
            append_unique_location(entity.declarations, at);
            bool definition = false;
            if (const auto *function = llvm::dyn_cast<FunctionDecl>(declaration)) {
                definition = function->doesThisDeclarationHaveABody();
            } else if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
                definition = variable->isThisDeclarationADefinition();
            } else if (const auto *record = llvm::dyn_cast<RecordDecl>(declaration)) {
                definition = record->isCompleteDefinition();
            } else if (llvm::isa<FieldDecl>(declaration) ||
                       llvm::isa<ParmVarDecl>(declaration)) {
                definition = true;
            }
            if (definition) {
                append_unique_location(entity.definitions, location(declaration->getLocation()));
            }
            entity_indices_[id] = output_.entities.size();
            output_.entities.push_back(std::move(entity));
        } else {
            EntityRef &entity = output_.entities[existing->second];
            entity.translation_unit_ids.insert(output_.record.translation_unit_id);
            append_unique_location(entity.declarations, location(declaration->getLocation()));
            if (const auto *function = llvm::dyn_cast<FunctionDecl>(declaration);
                function != nullptr && function->doesThisDeclarationHaveABody()) {
                append_unique_location(entity.definitions, location(declaration->getLocation()));
            }
        }
        return id;
    }

    std::string ensure_synthetic_entity(
        const std::string &kind, const std::string &material,
        const SourceLocation &at, const ValueType &type,
        IdentityStatus identity_status = IdentityStatus::Summary,
        EntityKind entity_kind = EntityKind::Synthetic) {
        const std::string id = stable_id("entity", kind + '\0' + material);
        if (!entity_indices_.contains(id)) {
            EntityRef entity;
            entity.entity_id = id;
            entity.kind = entity_kind;
            entity.identity_status = identity_status;
            entity.qualified_signature = kind + ':' + material;
            entity.canonical_type = type.canonical;
            entity.translation_unit_ids.insert(output_.record.translation_unit_id);
            append_unique_location(entity.declarations, at);
            append_unique_location(entity.definitions, at);
            entity_indices_[id] = output_.entities.size();
            output_.entities.push_back(std::move(entity));
        }
        return id;
    }

    ObjectAbstraction abstraction_for(const ValueDecl *declaration) const {
        if (llvm::isa<ParmVarDecl>(declaration)) {
            return ObjectAbstraction::Summary;
        }
        if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
            return variable->hasGlobalStorage() ? ObjectAbstraction::Global
                                                : ObjectAbstraction::Stack;
        }
        return ObjectAbstraction::Value;
    }

    std::string ensure_object(
        const std::string &root_entity, ObjectAbstraction abstraction,
        const SourceLocation &at, Certainty certainty = Certainty::Must) {
        const std::string id = stable_id(
            "object", root_entity + '\0' + std::to_string(static_cast<int>(abstraction)));
        if (!object_indices_.contains(id)) {
            AbstractObject object;
            object.object_id = id;
            object.abstraction = abstraction;
            object.certainty = certainty;
            if (!at.file.empty()) {
                object.allocation_site = at;
            }
            object_indices_[id] = output_.objects.size();
            output_.objects.push_back(std::move(object));
        }
        return id;
    }

    std::string access_material(const AccessPath &path) const {
        std::ostringstream stream;
        stream << path.root_entity_id << "|d=" << path.dereference_depth;
        for (const std::string &field : path.fields) {
            stream << "|f=" << field;
        }
        stream << "|u=" << path.unknown_suffix;
        return stream.str();
    }

    std::string ensure_path_node(
        const AccessPath &path, QualType type, const SourceLocation &at,
        const std::string &ast_kind, SemanticNodeKind kind = SemanticNodeKind::Memory) {
        const std::string material = access_material(path);
        const std::string id = stable_id(
            "node", "path\0" + material + "\0owner\0" +
                        current_function_id() + "\0site\0" +
                        location_material(at) + "\0ast\0" +
                        ast_kind + "\0kind\0" +
                        std::to_string(static_cast<int>(kind)));
        if (!node_indices_.contains(id)) {
            SemanticNode node;
            node.node_id = id;
            node.kind = kind;
            node.entity_id = path.root_entity_id;
            node.owner_function_id = current_function_id();
            node.access_path = path;
            node.value_type = type_info(type, context_, identity_roots_);
            node.location = at;
            node.ast_kind = ast_kind;
            const auto entity_it = entity_indices_.find(path.root_entity_id);
            ObjectAbstraction abstraction = ObjectAbstraction::Unknown;
            if (entity_it != entity_indices_.end()) {
                const EntityKind root_kind = output_.entities[entity_it->second].kind;
                abstraction = root_kind == EntityKind::Global
                                  ? ObjectAbstraction::Global
                              : root_kind == EntityKind::Parameter
                                  ? ObjectAbstraction::Summary
                                  : ObjectAbstraction::Stack;
            }
            node.abstract_object_id = ensure_object(
                path.root_entity_id, abstraction, at,
                path.unknown_suffix ? Certainty::Unknown : Certainty::Must);
            node_indices_[id] = output_.nodes.size();
            output_.nodes.push_back(std::move(node));
            if (current_summary_ != nullptr) {
                append_unique(current_summary_->owned_node_ids, id);
            }
            std::vector<std::string> &occurrences = path_occurrences_[material];
            for (const std::string &previous : occurrences) {
                const SemanticNode *previous_node = this->node(previous);
                const SemanticNode *current_node = this->node(id);
                if (previous_node != nullptr && current_node != nullptr &&
                    previous_node->owner_function_id ==
                        current_node->owner_function_id) {
                    add_relation(
                        previous, id, RelationKind::Alias, Certainty::May, at,
                        "source-ordered memory occurrence for the same object/field");
                }
            }
            occurrences.push_back(id);
        }
        return id;
    }

    std::string ensure_decl_node(const ValueDecl *declaration) {
        const std::string root = ensure_entity(declaration);
        AccessPath path{root, 0, {}, false};
        return ensure_path_node(
            path, declaration->getType(), location(declaration->getLocation()),
            declaration->getDeclKindName(), SemanticNodeKind::Declaration);
    }

    std::string ensure_return_node(FunctionDecl *function) {
        const std::string function_id = ensure_entity(function);
        const SourceLocation at = location(function->getLocation());
        const std::string id = stable_id("node", "return\0" + function_id);
        if (!node_indices_.contains(id)) {
            SemanticNode node;
            node.node_id = id;
            node.kind = SemanticNodeKind::ReturnSite;
            node.entity_id = function_id;
            node.owner_function_id = function_id;
            node.value_type = type_info(
                function->getReturnType(), context_, identity_roots_);
            node.location = at;
            node.ast_kind = "ReturnSlot";
            node_indices_[id] = output_.nodes.size();
            output_.nodes.push_back(std::move(node));
        }
        return id;
    }

    std::string ensure_function_node(FunctionDecl *function) {
        const std::string function_id = ensure_entity(function);
        const SourceLocation at = location(
            function->getBeginLoc(), function->getEndLoc());
        const std::string id = stable_id(
            "node", "function-definition\0" + function_id + "\0" +
                        location_material(at));
        if (!node_indices_.contains(id)) {
            SemanticNode node;
            node.node_id = id;
            node.kind = SemanticNodeKind::Definition;
            node.entity_id = function_id;
            node.owner_function_id = function_id;
            node.value_type = type_info(
                function->getType(), context_, identity_roots_);
            node.location = at;
            node.ast_kind = "FunctionDecl";
            node_indices_[id] = output_.nodes.size();
            output_.nodes.push_back(std::move(node));
        }
        return id;
    }

    FunctionSummary *ensure_summary(
        FunctionDecl *function, const std::string &function_id) {
        if (function == nullptr || !function->doesThisDeclarationHaveABody()) {
            return nullptr;
        }
        const auto found = summary_indices_.find(function_id);
        if (found != summary_indices_.end()) {
            return &output_.summaries[found->second];
        }
        FunctionSummary summary;
        summary.function_entity_id = function_id;
        summary.owned_node_ids.push_back(ensure_function_node(function));
        for (ParmVarDecl *parameter : function->parameters()) {
            summary.parameter_node_ids.push_back(ensure_decl_node(parameter));
        }
        if (!function->getReturnType()->isVoidType()) {
            summary.return_node_id = ensure_return_node(function);
        }
        const std::size_t index = output_.summaries.size();
        output_.summaries.push_back(std::move(summary));
        summary_indices_[function_id] = index;
        return &output_.summaries[index];
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

    std::vector<AccessPath> access_paths_for_lvalue(const Expr *expression) {
        if (expression == nullptr) {
            return {};
        }
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            return {{ensure_entity(reference->getDecl()), 0, {}, false}};
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(plain)) {
            const ValueDecl *member_declaration = member->getMemberDecl();
            // C++ permits enum constants and static data members to be named
            // through an object (`stream.end`).  Their value is declaration-
            // scoped, not a field of that object; representing them as an
            // object field invents a false receiver dependency.  It also used
            // to place a qualified-name string in AccessPath::fields, which
            // violated the entity-closed IR contract on multi-TU projects.
            if (llvm::isa<clang::EnumConstantDecl>(member_declaration) ||
                (llvm::isa<VarDecl>(member_declaration) &&
                 llvm::cast<VarDecl>(member_declaration)
                     ->hasGlobalStorage())) {
                return {{
                    ensure_entity(member_declaration), 0, {}, false}};
            }
            std::vector<AccessPath> bases;
            const Expr *base = member->getBase()->IgnoreParenImpCasts();
            if (member->isArrow()) {
                if (const ValueDecl *pointer = referenced_decl(base)) {
                    const std::string pointer_id = ensure_entity(pointer);
                    const auto aliases = pointer_aliases_.find(pointer_id);
                    if (aliases != pointer_aliases_.end() && !aliases->second.empty()) {
                        bases = aliases->second;
                    }
                }
            }
            if (bases.empty()) {
                bases = access_paths_for_lvalue(base);
                if (member->isArrow()) {
                    for (AccessPath &path : bases) {
                        ++path.dereference_depth;
                    }
                }
            }
            // Every field path component is an entity ID.  Indirect fields
            // and other non-static member declarations remain explicit,
            // entity-closed components rather than untyped name strings.
            const std::string field_id = ensure_entity(member_declaration);
            if (bases.empty()) {
                return {{field_id, 0, {}, true}};
            }
            for (AccessPath &path : bases) {
                if (path.fields.size() >= options_.maximum_field_depth) {
                    path.unknown_suffix = true;
                    add_gap(
                        "field_depth_widening", GapEffect::PrecisionLoss,
                        "Field path exceeded configured depth and was widened",
                        location(member->getMemberLoc()), {});
                } else {
                    path.fields.push_back(field_id);
                }
            }
            return bases;
        }
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(plain);
            unary != nullptr && unary->getOpcode() == clang::UO_Deref) {
            std::vector<AccessPath> paths =
                access_paths_for_lvalue(unary->getSubExpr());
            if (const ValueDecl *pointer = referenced_decl(unary->getSubExpr())) {
                const auto found = pointer_aliases_.find(ensure_entity(pointer));
                if (found != pointer_aliases_.end() && !found->second.empty()) {
                    return found->second;
                }
            }
            for (AccessPath &path : paths) {
                if (path.dereference_depth >= options_.maximum_dereference_depth) {
                    path.unknown_suffix = true;
                    add_gap(
                        "dereference_depth_widening", GapEffect::SoundnessRisk,
                        "Dereference path exceeded configured depth and was widened",
                        location(unary->getOperatorLoc()), {});
                } else {
                    ++path.dereference_depth;
                }
            }
            return paths;
        }
        if (const auto *array = llvm::dyn_cast<clang::ArraySubscriptExpr>(plain)) {
            std::vector<AccessPath> paths =
                access_paths_for_lvalue(array->getBase());
            for (AccessPath &path : paths) {
                path.unknown_suffix = true;
            }
            add_gap(
                "array_index_summary", GapEffect::PrecisionLoss,
                "Array index is represented by an unknown-suffix access path",
                location(array->getExprLoc()), {});
            return paths;
        }
        return {};
    }

    std::vector<std::string> nodes_for_paths(
        const std::vector<AccessPath> &paths, QualType type,
        const SourceLocation &at, const std::string &ast_kind) {
        std::vector<std::string> result;
        for (const AccessPath &path : paths) {
            append_unique(result, ensure_path_node(path, type, at, ast_kind));
        }
        return result;
    }

    std::vector<std::string> nodes_for_lvalue(const ValueDecl *declaration) {
        return {ensure_decl_node(declaration)};
    }

    std::vector<std::string> nodes_for_lvalue(const Expr *expression) {
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            return {ensure_decl_node(reference->getDecl())};
        }
        return nodes_for_paths(
            access_paths_for_lvalue(expression), expression->getType(),
            location(expression->getExprLoc(), expression->getEndLoc()),
            expression->getStmtClassName());
    }

    std::vector<AccessPath> alias_targets(const Expr *expression) {
        if (expression == nullptr) {
            return {};
        }
        const Expr *plain = expression->IgnoreParenImpCasts();
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(plain);
            unary != nullptr && unary->getOpcode() == clang::UO_AddrOf) {
            return access_paths_for_lvalue(unary->getSubExpr());
        }
        if (const auto *conditional = llvm::dyn_cast<ConditionalOperator>(plain)) {
            std::vector<AccessPath> result = alias_targets(conditional->getTrueExpr());
            std::vector<AccessPath> other = alias_targets(conditional->getFalseExpr());
            result.insert(result.end(), other.begin(), other.end());
            return result;
        }
        if (const ValueDecl *declaration = referenced_decl(plain)) {
            const std::string id = ensure_entity(declaration);
            const auto found = pointer_aliases_.find(id);
            if (found != pointer_aliases_.end()) {
                return found->second;
            }
            return {{id, 0, {}, true}};
        }
        return {};
    }

    void record_pointer_alias(
        const ValueDecl *pointer, const Expr *initializer,
        const std::string &pointer_node) {
        const std::string pointer_id = ensure_entity(pointer);
        std::vector<AccessPath> targets = alias_targets(initializer);
        if (targets.empty()) {
            add_gap(
                "unknown_pointer_target", GapEffect::SoundnessRisk,
                "Pointer target could not be resolved; alias effects remain unknown",
                location(initializer->getExprLoc()), {pointer_id});
            return;
        }
        std::vector<AccessPath> unique;
        std::set<std::string> identities;
        for (AccessPath &target : targets) {
            const std::string material = access_material(target);
            if (identities.insert(material).second) {
                unique.push_back(target);
                const std::string target_node = ensure_path_node(
                    target, initializer->getType(),
                    location(initializer->getExprLoc()), "AliasTarget");
                add_relation(
                    pointer_node, target_node, RelationKind::Alias,
                    unique.size() == 1 && targets.size() == 1 ? Certainty::Must
                                                             : Certainty::May,
                    location(initializer->getExprLoc()),
                    "flow-sensitive address assignment");
                add_relation(
                    target_node, pointer_node, RelationKind::Alias,
                    Certainty::May, location(initializer->getExprLoc()),
                    "reverse may-alias evidence");
            }
        }
        pointer_aliases_[pointer_id] = std::move(unique);
    }

    void collect_values(const Stmt *statement, std::vector<std::string> &output) {
        if (statement == nullptr) {
            return;
        }
        if (const auto *call = llvm::dyn_cast<CallExpr>(statement)) {
            append_unique(output, ensure_callsite(call));
            return;
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(statement)) {
            for (const std::string &node : nodes_for_lvalue(member)) {
                append_unique(output, node);
            }
            return;
        }
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(statement)) {
            if (!llvm::isa<FunctionDecl>(reference->getDecl())) {
                append_unique(output, ensure_decl_node(reference->getDecl()));
            }
            return;
        }
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(statement);
            unary != nullptr && unary->getOpcode() == clang::UO_AddrOf) {
            for (const std::string &node : nodes_for_lvalue(unary->getSubExpr())) {
                append_unique(output, node);
            }
            return;
        }
        for (const Stmt *child : statement->children()) {
            collect_values(child, output);
        }
    }

    std::vector<std::string> values_in(const Stmt *statement) {
        std::vector<std::string> result;
        collect_values(statement, result);
        return result;
    }

    ValueType boolean_value_type() const {
        return type_info(context_.BoolTy, context_, identity_roots_);
    }

    void record_transfer_gap(
        const std::string &kind, const std::string &detail,
        const SourceLocation &at, std::vector<std::string> affected = {}) {
        const std::string gap_id = stable_id(
            "value-transfer-gap",
            kind + '\0' + detail + '\0' + location_material(at));
        if (!transfer_gap_ids_.insert(gap_id).second) {
            return;
        }
        CoverageGap gap;
        gap.gap_id = gap_id;
        gap.kind = kind;
        gap.effect = GapEffect::PrecisionLoss;
        gap.detail = detail;
        if (!at.file.empty()) {
            gap.locations.push_back(at);
        }
        gap.affected_ids = std::move(affected);
        output_.value_transfers.coverage_gaps.push_back(std::move(gap));
        output_.value_transfers.status = combine_status(
            output_.value_transfers.status,
            StageStatus::ConservativeIncomplete);
    }

    void record_transfer_resource_limit(const SourceLocation &at) {
        output_.value_transfers.resource_limit_hit = true;
        output_.value_transfers.candidate_accounting_complete = false;
        record_transfer_gap(
            "value_transfer_resource_limit",
            "Typed value-transfer extraction reached a configured resource limit; remaining program points are explicitly unaccounted",
            at);
    }

    std::string intern_transfer_expression(TransferExpression expression) {
        ++output_.value_transfers.observed_expression_nodes;
        if (expression.operand_expression_ids.size() >
            transfer_options_.maximum_expression_operands) {
            expression.kind = TransferExprKind::Unknown;
            expression.input.reset();
            expression.literal.reset();
            expression.cast_operation.reset();
            expression.compare_operation.reset();
            expression.boolean_operation.reset();
            expression.definedness_operation.reset();
            expression.operand_expression_ids.resize(
                transfer_options_.maximum_expression_operands);
            expression.guard_expression_ids.clear();
            expression.predecessor_ids.clear();
            expression.affine_coefficients.clear();
            expression.affine_offset.reset();
            expression.uncertainty_reasons = {
                "expression operand count exceeded configured limit"};
            record_transfer_resource_limit({});
        }
        expression.expression_id =
            canonical_transfer_expression_id(expression);
        const auto known = transfer_expression_indices_.find(
            expression.expression_id);
        if (known != transfer_expression_indices_.end()) {
            return known->first;
        }
        if (output_.value_transfers.expressions.size() >=
                transfer_options_.maximum_expression_nodes &&
            expression.kind != TransferExprKind::Unknown) {
            record_transfer_resource_limit({});
            TransferExpression unknown;
            unknown.kind = TransferExprKind::Unknown;
            unknown.value_type = expression.value_type;
            unknown.uncertainty_reasons = {
                "expression node budget exhausted"};
            unknown.expression_id =
                canonical_transfer_expression_id(unknown);
            const std::string unknown_id = unknown.expression_id;
            if (!transfer_expression_indices_.contains(unknown_id)) {
                transfer_expression_indices_[unknown_id] =
                    output_.value_transfers.expressions.size();
                // One canonical Unknown sentinel per encountered value type is
                // retained beyond the exact-node budget so abstention remains
                // typed and referentially closed.
                output_.value_transfers.expressions.push_back(
                    std::move(unknown));
            }
            return unknown_id;
        }
        transfer_expression_indices_[expression.expression_id] =
            output_.value_transfers.expressions.size();
        output_.value_transfers.expressions.push_back(std::move(expression));
        return output_.value_transfers.expressions.back().expression_id;
    }

    std::string make_input_expression(
        const std::string &node_id, const ValueType &fallback_type,
        bool load) {
        ValueType type = fallback_type;
        if (const SemanticNode *source = node(node_id)) {
            type = source->value_type;
        }
        TransferExpression input;
        input.kind = TransferExprKind::Input;
        input.value_type = type;
        input.input = TransferSymbolRef{
            TransferSymbolDomain::SemanticNode, node_id, type};
        const std::string input_id = intern_transfer_expression(std::move(input));
        if (!load) {
            return input_id;
        }
        TransferExpression loaded;
        loaded.kind = TransferExprKind::Load;
        loaded.value_type = fallback_type;
        loaded.operand_expression_ids = {input_id};
        return intern_transfer_expression(std::move(loaded));
    }

    std::string make_literal_expression(
        const TransferLiteral &literal, const ValueType &type) {
        TransferExpression expression;
        expression.kind = TransferExprKind::Literal;
        expression.value_type = type;
        expression.literal = literal;
        return intern_transfer_expression(std::move(expression));
    }

    std::string make_true_expression() {
        return make_literal_expression(
            {TransferLiteralKind::Boolean, "true"}, boolean_value_type());
    }

    std::string conjoin_definedness(std::vector<std::string> roots) {
        roots.erase(
            std::remove(roots.begin(), roots.end(), std::string()),
            roots.end());
        if (roots.empty()) {
            return {};
        }
        std::string result = roots.front();
        for (std::size_t index = 1; index < roots.size(); ++index) {
            TransferExpression conjunction;
            conjunction.kind = TransferExprKind::Boolean;
            conjunction.value_type = boolean_value_type();
            conjunction.boolean_operation = BooleanOperation::And;
            conjunction.operand_expression_ids = {result, roots[index]};
            result = intern_transfer_expression(std::move(conjunction));
        }
        return result;
    }

    BuiltTransferExpression compose_definedness(
        BuiltTransferExpression result,
        const std::vector<BuiltTransferExpression> &children,
        const std::optional<std::string> &operation_definedness =
            std::nullopt) {
        std::vector<std::string> roots;
        for (const BuiltTransferExpression &child : children) {
            if (child.definedness == DefinednessClass::Unknown) {
                result.definedness = DefinednessClass::Unknown;
                result.defined_when_expression_id.reset();
                result.soundness = TransferSoundness::Unknown;
                append_unique(
                    result.uncertainty_reasons,
                    "operand definedness is unknown");
                return result;
            }
            if (child.definedness == DefinednessClass::Conditional &&
                child.defined_when_expression_id) {
                roots.push_back(*child.defined_when_expression_id);
            }
        }
        if (operation_definedness) {
            roots.push_back(*operation_definedness);
        }
        if (roots.empty()) {
            result.definedness = DefinednessClass::Total;
            result.defined_when_expression_id.reset();
        } else {
            result.definedness = DefinednessClass::Conditional;
            result.defined_when_expression_id =
                conjoin_definedness(std::move(roots));
        }
        return result;
    }

    BuiltTransferExpression unknown_transfer_expression(
        const Expr *expression, const std::string &reason) {
        BuiltTransferExpression result;
        const ValueType type = type_info(
            expression == nullptr ? QualType() : expression->getType(),
            context_, identity_roots_);
        TransferExpression unknown;
        unknown.kind = TransferExprKind::Unknown;
        unknown.value_type = type;
        unknown.uncertainty_reasons = {reason};
        if (expression != nullptr) {
            result.input_node_ids = values_in(expression);
            std::sort(
                result.input_node_ids.begin(), result.input_node_ids.end());
            result.input_node_ids.erase(
                std::unique(
                    result.input_node_ids.begin(),
                    result.input_node_ids.end()),
                result.input_node_ids.end());
            for (const std::string &input : result.input_node_ids) {
                unknown.operand_expression_ids.push_back(
                    make_input_expression(input, type, false));
            }
            record_transfer_gap(
                "unsupported_value_transfer_expression", reason,
                location(expression->getExprLoc(), expression->getEndLoc()),
                result.input_node_ids);
        }
        result.root_expression_id =
            intern_transfer_expression(std::move(unknown));
        result.soundness = TransferSoundness::Unknown;
        result.definedness = DefinednessClass::Unknown;
        result.uncertainty_reasons = {reason};
        return result;
    }

    static void merge_expression_inputs(
        BuiltTransferExpression &target,
        const BuiltTransferExpression &source) {
        for (const std::string &input : source.input_node_ids) {
            append_unique(target.input_node_ids, input);
        }
        for (const std::string &reason : source.uncertainty_reasons) {
            append_unique(target.uncertainty_reasons, reason);
        }
        if (source.soundness == TransferSoundness::Unknown) {
            target.soundness = TransferSoundness::Unknown;
        } else if (source.soundness == TransferSoundness::Conservative &&
                   target.soundness == TransferSoundness::Exact) {
            target.soundness = TransferSoundness::Conservative;
        }
    }

    BuiltTransferExpression input_transfer_expression(
        const std::string &node_id, const Expr *expression, bool load) {
        BuiltTransferExpression result;
        result.input_node_ids = {node_id};
        result.root_expression_id = make_input_expression(
            node_id,
            type_info(expression->getType(), context_, identity_roots_), load);
        result.soundness = TransferSoundness::Exact;
        result.definedness = DefinednessClass::Total;
        return result;
    }

    std::optional<std::string> integer_constant(const Expr *expression) const {
        if (expression == nullptr) {
            return std::nullopt;
        }
        const std::optional<llvm::APSInt> value =
            expression->getIntegerConstantExpr(context_);
        if (!value) {
            return std::nullopt;
        }
        llvm::SmallString<64> text;
        value->toString(text, 10);
        return text.str().str();
    }

    std::optional<CastOperation> classify_cast(
        QualType source, QualType target) const {
        source = source.getCanonicalType();
        target = target.getCanonicalType();
        if (context_.hasSameType(source, target)) {
            return CastOperation::NoOp;
        }
        if (source->isBooleanType() && target->isIntegerType()) {
            return CastOperation::BoolToInt;
        }
        if ((source->isIntegerType() || source->isEnumeralType()) &&
            target->isBooleanType()) {
            return CastOperation::IntToBool;
        }
        if (!(source->isIntegerType() || source->isEnumeralType()) ||
            !(target->isIntegerType() || target->isEnumeralType())) {
            return std::nullopt;
        }
        const std::uint64_t source_width = context_.getTypeSize(source);
        const std::uint64_t target_width = context_.getTypeSize(target);
        const bool source_signed =
            source->isSignedIntegerOrEnumerationType();
        const bool target_signed =
            target->isSignedIntegerOrEnumerationType();
        if (target_width > source_width) {
            return source_signed ? CastOperation::SignExtend
                                 : CastOperation::ZeroExtend;
        }
        if (target_width < source_width ||
            (source_signed != target_signed && !target_signed)) {
            return target_signed ? std::optional<CastOperation>()
                                 : std::optional<CastOperation>(
                                       CastOperation::TruncateModulo);
        }
        // Unsigned-to-signed conversion at equal width is implementation-
        // defined for out-of-range values in the supported C/C++ dialects.
        if (!source_signed && target_signed) {
            return std::nullopt;
        }
        return CastOperation::NoOp;
    }

    BuiltTransferExpression build_transfer_expression(const Expr *expression) {
        if (expression == nullptr) {
            return unknown_transfer_expression(
                nullptr, "null expression has no value semantics");
        }
        if (const auto *parenthesized =
                llvm::dyn_cast<clang::ParenExpr>(expression)) {
            return build_transfer_expression(parenthesized->getSubExpr());
        }
        if (const auto *cleanup =
                llvm::dyn_cast<clang::ExprWithCleanups>(expression)) {
            return build_transfer_expression(cleanup->getSubExpr());
        }
        if (const auto *constant =
                llvm::dyn_cast<clang::ConstantExpr>(expression)) {
            return build_transfer_expression(constant->getSubExpr());
        }
        if (const auto *cast = llvm::dyn_cast<CastExpr>(expression)) {
            BuiltTransferExpression child =
                build_transfer_expression(cast->getSubExpr());
            if (cast->getCastKind() == clang::CK_LValueToRValue) {
                return child;
            }
            const std::optional<CastOperation> operation = classify_cast(
                cast->getSubExpr()->getType(), cast->getType());
            if (!operation) {
                return unknown_transfer_expression(
                    expression,
                    "cast has implementation-defined or unsupported value semantics");
            }
            TransferExpression converted;
            converted.kind = TransferExprKind::Cast;
            converted.value_type = type_info(
                cast->getType(), context_, identity_roots_);
            converted.cast_operation = *operation;
            converted.operand_expression_ids = {child.root_expression_id};
            BuiltTransferExpression result = child;
            result.root_expression_id =
                intern_transfer_expression(std::move(converted));
            return compose_definedness(
                std::move(result), {child});
        }
        if (const auto *literal =
                llvm::dyn_cast<clang::CXXBoolLiteralExpr>(expression)) {
            BuiltTransferExpression result;
            result.root_expression_id = make_literal_expression(
                {TransferLiteralKind::Boolean,
                 literal->getValue() ? "true" : "false"},
                type_info(literal->getType(), context_, identity_roots_));
            result.soundness = TransferSoundness::Exact;
            result.definedness = DefinednessClass::Total;
            return result;
        }
        if (const auto *literal =
                llvm::dyn_cast<clang::IntegerLiteral>(expression)) {
            llvm::SmallString<64> text;
            literal->getValue().toString(
                text, 10, literal->getType()->isSignedIntegerType());
            BuiltTransferExpression result;
            result.root_expression_id = make_literal_expression(
                {TransferLiteralKind::Integer, text.str().str()},
                type_info(literal->getType(), context_, identity_roots_));
            result.soundness = TransferSoundness::Exact;
            result.definedness = DefinednessClass::Total;
            return result;
        }
        if (const auto *literal =
                llvm::dyn_cast<clang::FloatingLiteral>(expression)) {
            llvm::SmallString<64> text;
            literal->getValue().toString(text);
            BuiltTransferExpression result;
            result.root_expression_id = make_literal_expression(
                {TransferLiteralKind::Floating, text.str().str()},
                type_info(literal->getType(), context_, identity_roots_));
            result.soundness = TransferSoundness::Exact;
            result.definedness = DefinednessClass::Total;
            return result;
        }
        if (const auto *reference =
                llvm::dyn_cast<DeclRefExpr>(expression)) {
            if (const auto *enumerator =
                    llvm::dyn_cast<clang::EnumConstantDecl>(
                        reference->getDecl())) {
                llvm::SmallString<64> text;
                enumerator->getInitVal().toString(text, 10);
                BuiltTransferExpression result;
                result.root_expression_id = make_literal_expression(
                    {TransferLiteralKind::Enumeration, text.str().str()},
                    type_info(
                        reference->getType(), context_, identity_roots_));
                result.soundness = TransferSoundness::Exact;
                result.definedness = DefinednessClass::Total;
                return result;
            }
            if (llvm::isa<FunctionDecl>(reference->getDecl())) {
                return unknown_transfer_expression(
                    expression, "function designator is not a scalar value input");
            }
            return input_transfer_expression(
                ensure_decl_node(reference->getDecl()), expression, true);
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(expression)) {
            const std::vector<std::string> candidates =
                nodes_for_lvalue(member);
            if (candidates.size() != 1) {
                return unknown_transfer_expression(
                    expression,
                    "member access does not resolve to one abstract object/field");
            }
            const SemanticNode *resolved = node(candidates.front());
            if (resolved == nullptr ||
                (resolved->access_path && resolved->access_path->unknown_suffix)) {
                return unknown_transfer_expression(
                    expression,
                    "member access contains an unresolved object/field suffix");
            }
            return input_transfer_expression(
                candidates.front(), expression, true);
        }
        if (const auto *call = llvm::dyn_cast<CallExpr>(expression)) {
            return input_transfer_expression(
                ensure_callsite(call), expression, false);
        }
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(expression)) {
            if (unary->getOpcode() == clang::UO_LNot) {
                BuiltTransferExpression child =
                    build_transfer_expression(unary->getSubExpr());
                TransferExpression result_expression;
                result_expression.kind = TransferExprKind::Boolean;
                result_expression.value_type = type_info(
                    unary->getType(), context_, identity_roots_);
                result_expression.boolean_operation = BooleanOperation::Not;
                result_expression.operand_expression_ids = {
                    child.root_expression_id};
                BuiltTransferExpression result = child;
                result.root_expression_id = intern_transfer_expression(
                    std::move(result_expression));
                return compose_definedness(
                    std::move(result), {child});
            }
            if (unary->getOpcode() == clang::UO_Plus) {
                BuiltTransferExpression child =
                    build_transfer_expression(unary->getSubExpr());
                TransferExpression identity;
                identity.kind = TransferExprKind::Identity;
                identity.value_type = type_info(
                    unary->getType(), context_, identity_roots_);
                identity.operand_expression_ids = {child.root_expression_id};
                child.root_expression_id =
                    intern_transfer_expression(std::move(identity));
                return child;
            }
            if (unary->getOpcode() == clang::UO_Minus &&
                unary->getType()->isIntegerType()) {
                BuiltTransferExpression child =
                    build_transfer_expression(unary->getSubExpr());
                TransferExpression affine;
                affine.kind = TransferExprKind::Affine;
                affine.value_type = type_info(
                    unary->getType(), context_, identity_roots_);
                affine.operand_expression_ids = {child.root_expression_id};
                affine.affine_coefficients = {"-1"};
                affine.affine_offset = "0";
                BuiltTransferExpression result = child;
                result.root_expression_id =
                    intern_transfer_expression(std::move(affine));
                std::optional<std::string> condition;
                if (unary->getType()->isSignedIntegerType()) {
                    TransferExpression defined;
                    defined.kind = TransferExprKind::Definedness;
                    defined.value_type = boolean_value_type();
                    defined.definedness_operation =
                        DefinednessOperation::SignedNegateNoOverflow;
                    defined.operand_expression_ids = {
                        child.root_expression_id};
                    condition =
                        intern_transfer_expression(std::move(defined));
                }
                return compose_definedness(
                    std::move(result), {child}, condition);
            }
            return unknown_transfer_expression(
                expression, "unary operator is outside the exact transfer subset");
        }
        if (const auto *conditional =
                llvm::dyn_cast<ConditionalOperator>(expression)) {
            if (conditional->HasSideEffects(context_)) {
                return unknown_transfer_expression(
                    expression,
                    "conditional expression has side effects whose ordering is not summarized");
            }
            BuiltTransferExpression condition =
                build_transfer_expression(conditional->getCond());
            BuiltTransferExpression when_true =
                build_transfer_expression(conditional->getTrueExpr());
            BuiltTransferExpression when_false =
                build_transfer_expression(conditional->getFalseExpr());
            BuiltTransferExpression result;
            result.soundness = TransferSoundness::Exact;
            merge_expression_inputs(result, condition);
            merge_expression_inputs(result, when_true);
            merge_expression_inputs(result, when_false);
            TransferExpression selected;
            selected.kind = TransferExprKind::Select;
            selected.value_type = type_info(
                conditional->getType(), context_, identity_roots_);
            selected.operand_expression_ids = {
                condition.root_expression_id,
                when_true.root_expression_id,
                when_false.root_expression_id};
            result.root_expression_id =
                intern_transfer_expression(std::move(selected));
            std::optional<std::string> condition_root;
            if (when_true.definedness == DefinednessClass::Conditional ||
                when_false.definedness == DefinednessClass::Conditional) {
                if (!when_true.defined_when_expression_id ||
                    !when_false.defined_when_expression_id) {
                    result.definedness = DefinednessClass::Unknown;
                    result.soundness = TransferSoundness::Unknown;
                    append_unique(
                        result.uncertainty_reasons,
                        "select arm definedness is not closed");
                    return result;
                }
                TransferExpression defined;
                defined.kind = TransferExprKind::Definedness;
                defined.value_type = boolean_value_type();
                defined.definedness_operation =
                    DefinednessOperation::SelectChosenArm;
                defined.operand_expression_ids = {
                    condition.root_expression_id,
                    *when_true.defined_when_expression_id,
                    *when_false.defined_when_expression_id};
                condition_root =
                    intern_transfer_expression(std::move(defined));
            }
            return compose_definedness(
                std::move(result),
                {condition, when_true, when_false}, condition_root);
        }
        const auto *binary = llvm::dyn_cast<BinaryOperator>(expression);
        if (binary == nullptr || binary->isAssignmentOp()) {
            return unknown_transfer_expression(
                expression,
                "expression kind is outside the exact transfer subset");
        }
        if (binary->getLHS()->HasSideEffects(context_) ||
            binary->getRHS()->HasSideEffects(context_)) {
            return unknown_transfer_expression(
                expression,
                "operator operands have side effects whose ordering is not summarized");
        }
        BuiltTransferExpression left =
            build_transfer_expression(binary->getLHS());
        BuiltTransferExpression right =
            build_transfer_expression(binary->getRHS());
        BuiltTransferExpression result;
        result.soundness = TransferSoundness::Exact;
        merge_expression_inputs(result, left);
        merge_expression_inputs(result, right);
        const clang::BinaryOperatorKind opcode = binary->getOpcode();
        if (binary->isComparisonOp()) {
            std::optional<CompareOperation> operation;
            switch (opcode) {
            case clang::BO_EQ:
                operation = CompareOperation::Eq;
                break;
            case clang::BO_NE:
                operation = CompareOperation::Ne;
                break;
            case clang::BO_LT:
                operation = CompareOperation::Lt;
                break;
            case clang::BO_LE:
                operation = CompareOperation::Le;
                break;
            case clang::BO_GT:
                operation = CompareOperation::Gt;
                break;
            case clang::BO_GE:
                operation = CompareOperation::Ge;
                break;
            default:
                break;
            }
            const QualType left_type =
                binary->getLHS()->getType().getCanonicalType();
            const QualType right_type =
                binary->getRHS()->getType().getCanonicalType();
            if (!operation || !context_.hasSameType(left_type, right_type) ||
                !(left_type->isIntegerType() ||
                  left_type->isEnumeralType() ||
                  left_type->isBooleanType())) {
                return unknown_transfer_expression(
                    expression,
                    "comparison operand types are outside the exact scalar subset");
            }
            TransferExpression compared;
            compared.kind = TransferExprKind::Compare;
            compared.value_type = type_info(
                binary->getType(), context_, identity_roots_);
            compared.compare_operation = *operation;
            compared.operand_expression_ids = {
                left.root_expression_id, right.root_expression_id};
            result.root_expression_id =
                intern_transfer_expression(std::move(compared));
            return compose_definedness(
                std::move(result), {left, right});
        }
        if (opcode == clang::BO_LAnd || opcode == clang::BO_LOr ||
            ((opcode == clang::BO_And || opcode == clang::BO_Or ||
              opcode == clang::BO_Xor) &&
             binary->getType()->isBooleanType())) {
            TransferExpression boolean;
            boolean.kind = TransferExprKind::Boolean;
            boolean.value_type = type_info(
                binary->getType(), context_, identity_roots_);
            if (opcode == clang::BO_LAnd || opcode == clang::BO_And) {
                boolean.boolean_operation = BooleanOperation::And;
            } else if (opcode == clang::BO_LOr || opcode == clang::BO_Or) {
                boolean.boolean_operation = BooleanOperation::Or;
            } else {
                boolean.boolean_operation = BooleanOperation::Xor;
            }
            boolean.operand_expression_ids = {
                left.root_expression_id, right.root_expression_id};
            result.root_expression_id =
                intern_transfer_expression(std::move(boolean));
            if ((opcode == clang::BO_LAnd || opcode == clang::BO_LOr) &&
                (left.definedness == DefinednessClass::Conditional ||
                 right.definedness == DefinednessClass::Conditional)) {
                if (left.definedness == DefinednessClass::Unknown ||
                    right.definedness == DefinednessClass::Unknown) {
                    result.definedness = DefinednessClass::Unknown;
                    result.soundness = TransferSoundness::Unknown;
                    append_unique(
                        result.uncertainty_reasons,
                        "short-circuit operand definedness is unknown");
                    return result;
                }
                TransferExpression defined;
                defined.kind = TransferExprKind::Definedness;
                defined.value_type = boolean_value_type();
                defined.definedness_operation =
                    opcode == clang::BO_LAnd
                        ? DefinednessOperation::ShortCircuitAnd
                        : DefinednessOperation::ShortCircuitOr;
                defined.operand_expression_ids = {
                    left.root_expression_id,
                    left.defined_when_expression_id.value_or(
                        make_true_expression()),
                    right.defined_when_expression_id.value_or(
                        make_true_expression())};
                const std::string defined_root =
                    intern_transfer_expression(std::move(defined));
                result.definedness = DefinednessClass::Conditional;
                result.defined_when_expression_id = defined_root;
                return result;
            }
            return compose_definedness(
                std::move(result), {left, right});
        }
        if ((opcode == clang::BO_Add || opcode == clang::BO_Sub ||
             opcode == clang::BO_Mul) &&
            binary->getType()->isIntegerType()) {
            TransferExpression affine;
            affine.kind = TransferExprKind::Affine;
            affine.value_type = type_info(
                binary->getType(), context_, identity_roots_);
            if (opcode == clang::BO_Add || opcode == clang::BO_Sub) {
                affine.operand_expression_ids = {
                    left.root_expression_id, right.root_expression_id};
                affine.affine_coefficients = {
                    "1", opcode == clang::BO_Add ? "1" : "-1"};
            } else {
                const std::optional<std::string> left_constant =
                    integer_constant(binary->getLHS());
                const std::optional<std::string> right_constant =
                    integer_constant(binary->getRHS());
                if (left_constant && !right_constant) {
                    affine.operand_expression_ids = {
                        right.root_expression_id};
                    affine.affine_coefficients = {*left_constant};
                } else if (right_constant && !left_constant) {
                    affine.operand_expression_ids = {
                        left.root_expression_id};
                    affine.affine_coefficients = {*right_constant};
                } else if (left_constant && right_constant) {
                    return unknown_transfer_expression(
                        expression,
                        "constant-folded multiplication was not normalized by the AST");
                } else {
                    return unknown_transfer_expression(
                        expression,
                        "multiplication has more than one non-constant factor");
                }
            }
            affine.affine_offset = "0";
            result.root_expression_id =
                intern_transfer_expression(std::move(affine));
            std::optional<std::string> operation_definedness;
            if (binary->getType()->isSignedIntegerType()) {
                TransferExpression defined;
                defined.kind = TransferExprKind::Definedness;
                defined.value_type = boolean_value_type();
                defined.definedness_operation =
                    opcode == clang::BO_Add
                        ? DefinednessOperation::SignedAddNoOverflow
                    : opcode == clang::BO_Sub
                        ? DefinednessOperation::SignedSubtractNoOverflow
                        : DefinednessOperation::SignedMultiplyNoOverflow;
                defined.operand_expression_ids = {
                    left.root_expression_id, right.root_expression_id};
                operation_definedness =
                    intern_transfer_expression(std::move(defined));
            }
            return compose_definedness(
                std::move(result), {left, right}, operation_definedness);
        }
        return unknown_transfer_expression(
            expression,
            "binary operator is outside the exact affine/compare/boolean subset");
    }

    BuiltTransferExpression ensure_explicit_identity(
        BuiltTransferExpression expression) {
        const auto found = transfer_expression_indices_.find(
            expression.root_expression_id);
        if (expression.soundness != TransferSoundness::Exact ||
            found == transfer_expression_indices_.end()) {
            return expression;
        }
        const TransferExprKind kind = output_.value_transfers
                                          .expressions[found->second]
                                          .kind;
        if (kind != TransferExprKind::Input &&
            kind != TransferExprKind::Load) {
            return expression;
        }
        TransferExpression identity;
        identity.kind = TransferExprKind::Identity;
        identity.value_type = output_.value_transfers
                                  .expressions[found->second]
                                  .value_type;
        identity.operand_expression_ids = {expression.root_expression_id};
        expression.root_expression_id =
            intern_transfer_expression(std::move(identity));
        return expression;
    }

    std::string wrap_transfer_expression(
        TransferExprKind kind, const std::string &operand,
        const ValueType &type) {
        TransferExpression wrapper;
        wrapper.kind = kind;
        wrapper.value_type = type;
        wrapper.operand_expression_ids = {operand};
        return intern_transfer_expression(std::move(wrapper));
    }

    bool transfer_expression_contains_unknown(
        const std::string &root) const {
        std::vector<std::string> worklist{root};
        std::set<std::string> seen;
        while (!worklist.empty()) {
            const std::string current = worklist.back();
            worklist.pop_back();
            if (!seen.insert(current).second) {
                continue;
            }
            const auto found = transfer_expression_indices_.find(current);
            if (found == transfer_expression_indices_.end()) {
                return true;
            }
            const TransferExpression &expression =
                output_.value_transfers.expressions[found->second];
            if (expression.kind == TransferExprKind::Unknown) {
                return true;
            }
            worklist.insert(
                worklist.end(), expression.operand_expression_ids.begin(),
                expression.operand_expression_ids.end());
        }
        return false;
    }

    void append_typed_transfer(TypedValueTransfer transfer) {
        ++output_.value_transfers.observed_transfers;
        std::sort(transfer.input_node_ids.begin(), transfer.input_node_ids.end());
        transfer.input_node_ids.erase(
            std::unique(
                transfer.input_node_ids.begin(),
                transfer.input_node_ids.end()),
            transfer.input_node_ids.end());
        std::sort(
            transfer.semantic_relation_ids.begin(),
            transfer.semantic_relation_ids.end());
        transfer.semantic_relation_ids.erase(
            std::unique(
                transfer.semantic_relation_ids.begin(),
                transfer.semantic_relation_ids.end()),
            transfer.semantic_relation_ids.end());
        transfer.transfer_id =
            canonical_typed_value_transfer_id(transfer);
        if (transfer_ids_.contains(transfer.transfer_id)) {
            return;
        }
        if (output_.value_transfers.transfers.size() >=
            transfer_options_.maximum_transfers) {
            record_transfer_resource_limit({});
            return;
        }
        transfer_ids_.insert(transfer.transfer_id);
        output_.value_transfers.transfers.push_back(std::move(transfer));
    }

    void record_expression_transfer(
        const Expr *source_expression, const std::string &target,
        RelationKind kind, const SourceLocation &at,
        std::vector<std::string> relation_ids,
        const std::optional<std::string> &callsite = std::nullopt,
        const std::optional<std::uint32_t> &argument_index = std::nullopt,
        bool force_unknown = false,
        std::vector<std::string> additional_inputs = {}) {
        BuiltTransferExpression expression = force_unknown
            ? unknown_transfer_expression(
                  source_expression,
                  "compound or implicit read-modify-write semantics are not in the exact subset")
            : build_transfer_expression(source_expression);
        for (const std::string &input : additional_inputs) {
            append_unique(expression.input_node_ids, input);
        }
        expression = ensure_explicit_identity(std::move(expression));
        ValueType output_type = type_info(
            source_expression == nullptr ? QualType()
                                         : source_expression->getType(),
            context_, identity_roots_);
        if (const SemanticNode *target_node = node(target)) {
            output_type = target_node->value_type;
        }
        const TransferExprKind wrapper = argument_index
            ? TransferExprKind::CallArg
            : kind == RelationKind::Return
                ? TransferExprKind::Return
                : TransferExprKind::Store;
        expression.root_expression_id = wrap_transfer_expression(
            wrapper, expression.root_expression_id, output_type);
        if (transfer_expression_contains_unknown(
                expression.root_expression_id)) {
            expression.soundness = TransferSoundness::Unknown;
            expression.definedness = DefinednessClass::Unknown;
            expression.defined_when_expression_id.reset();
            append_unique(
                expression.uncertainty_reasons,
                "typed expression contains an explicit Unknown node");
        }

        TypedValueTransfer transfer;
        transfer.program_point_id = stable_id(
            "program-point",
            std::string(kValueTransferIdentityScheme) + '\0' +
                location_material(at) + '\0' + target + '\0' +
                std::to_string(static_cast<int>(wrapper)) + '\0' +
                callsite.value_or(std::string()) + '\0' +
                (argument_index ? std::to_string(*argument_index)
                                : std::string()));
        transfer.output_domain = argument_index
            ? TransferEndpointDomain::CallArgumentSlot
            : TransferEndpointDomain::SemanticNode;
        transfer.input_node_ids = std::move(expression.input_node_ids);
        transfer.output_node_id = target;
        transfer.semantic_relation_ids = std::move(relation_ids);
        transfer.value_expression_id = expression.root_expression_id;
        transfer.definedness = expression.definedness;
        transfer.defined_when_expression_id =
            expression.defined_when_expression_id;
        transfer.path_condition = PathConditionClass::Unconditional;
        transfer.soundness = expression.soundness;
        transfer.certainty = expression.soundness == TransferSoundness::Exact
            ? Certainty::Must
            : Certainty::Unknown;
        transfer.callsite_id = callsite;
        transfer.call_argument_index = argument_index;
        transfer.uncertainty_reasons =
            std::move(expression.uncertainty_reasons);
        if (transfer.soundness != TransferSoundness::Exact &&
            transfer.uncertainty_reasons.empty()) {
            transfer.uncertainty_reasons.push_back(
                "value transformation is outside the exact AST subset");
        }
        Evidence evidence;
        evidence.kind = "ast_semantics";
        evidence.certainty = transfer.certainty;
        evidence.fact =
            "Clang AST expression retained as a property-independent typed value transfer";
        evidence.producer = "rift-clang-value-transfer";
        if (!at.file.empty()) {
            evidence.location = at;
        }
        evidence.evidence_id = stable_id(
            "evidence", transfer.program_point_id + '\0' + evidence.fact);
        transfer.evidence.push_back(std::move(evidence));
        append_typed_transfer(std::move(transfer));
    }

    bool constant_argument(const Expr *argument) const {
        return argument != nullptr && !argument->isValueDependent() &&
               argument->isEvaluatable(context_);
    }

    std::vector<std::string> synthetic_argument_node(
        const Expr *argument, const std::string &callsite_id,
        unsigned argument_index, bool constant) {
        const SourceLocation at = location(
            argument->getExprLoc(), argument->getEndLoc());
        const ValueType type = type_info(
            argument->getType(), context_, identity_roots_);
        std::ostringstream material;
        material << callsite_id << "\0arg\0" << argument_index << "\0ast\0"
                 << argument->getStmtClassName() << "\0type\0"
                 << type.canonical;
        const std::string entity = ensure_synthetic_entity(
            constant ? "constant-argument" : "unknown-argument",
            material.str(), at, type,
            constant ? IdentityStatus::Exact : IdentityStatus::Unknown,
            constant ? EntityKind::Synthetic : EntityKind::Unknown);
        AccessPath path{entity, 0, {}, !constant};
        const std::string node = ensure_path_node(
            path, argument->getType(), at, argument->getStmtClassName(),
            SemanticNodeKind::Value);
        if (!constant) {
            add_gap(
                "unsupported_argument_expression", GapEffect::SoundnessRisk,
                "Actual argument has no supported value/access-path representation; an explicit unknown ExprSite was retained",
                at, {callsite_id, node});
        }
        return {node};
    }

    std::vector<std::string> argument_nodes(
        const Expr *argument, const std::string &callsite_id,
        unsigned argument_index) {
        if (argument == nullptr) {
            return {};
        }
        const Expr *plain = argument->IgnoreParenImpCasts();
        if (const auto *unary = llvm::dyn_cast<UnaryOperator>(plain);
            unary != nullptr && unary->getOpcode() == clang::UO_AddrOf) {
            std::vector<std::string> addressed =
                nodes_for_lvalue(unary->getSubExpr());
            if (!addressed.empty()) {
                return addressed;
            }
            return synthetic_argument_node(
                argument, callsite_id, argument_index, false);
        }
        std::vector<std::string> result = values_in(argument);
        if (result.empty()) {
            return synthetic_argument_node(
                plain, callsite_id, argument_index,
                constant_argument(plain));
        }
        return result;
    }

    bool argument_is_address(const Expr *argument) const {
        if (argument == nullptr) {
            return false;
        }
        const Expr *plain = argument->IgnoreParenImpCasts();
        const auto *unary = llvm::dyn_cast<UnaryOperator>(plain);
        return unary != nullptr && unary->getOpcode() == clang::UO_AddrOf;
    }

    std::string ensure_callsite(const CallExpr *call) {
        if (const auto found = callsite_node_ids_.find(call);
            found != callsite_node_ids_.end()) {
            return found->second;
        }
        const SourceLocation at = location(call->getExprLoc(), call->getEndLoc());
        const std::optional<std::string> previous_owner =
            synthetic_owner_override_;
        FunctionSummary *const previous_summary = current_summary_;
        if (current_function_ == nullptr && !synthetic_owner_override_) {
            auto [owner, summary] = ensure_nonfunction_call_owner(call, at);
            synthetic_owner_override_ = std::move(owner);
            current_summary_ = summary;
        }
        const std::string caller = current_function_id();
        const std::string callsite_id = stable_id(
            "callsite", caller + '\0' + location_material(at));
        const ValueType type = type_info(
            call->getType(), context_, identity_roots_);
        const std::string entity = ensure_synthetic_entity(
            "callsite", callsite_id, at, type);
        const std::string call_node = stable_id("node", "callsite\0" + callsite_id);
        if (!node_indices_.contains(call_node)) {
            SemanticNode node;
            node.node_id = call_node;
            node.kind = SemanticNodeKind::CallSite;
            node.entity_id = entity;
            node.owner_function_id = caller;
            node.value_type = type;
            node.location = at;
            node.ast_kind = call->getStmtClassName();
            node_indices_[call_node] = output_.nodes.size();
            output_.nodes.push_back(std::move(node));
            if (current_summary_ != nullptr) {
                append_unique(current_summary_->owned_node_ids, call_node);
            }
        }
        callsite_node_ids_[call] = call_node;

        CallSiteSummary summary;
        summary.callsite_id = callsite_id;
        summary.caller_function_id = caller;
        summary.location = at;
        summary.result_node_id = call_node;
        if (const FunctionDecl *callee = call->getDirectCallee()) {
            summary.direct = true;
            summary.candidate_callee_ids.push_back(ensure_entity(callee));
            summary.status = StageStatus::Complete;
            if (const auto *method = llvm::dyn_cast<clang::CXXMethodDecl>(callee);
                method != nullptr && method->isVirtual()) {
                summary.status = StageStatus::ConservativeIncomplete;
                summary.uncertainty_reasons.push_back(
                    "virtual dispatch target set is not closed by AST-only indexing");
                add_gap(
                    "virtual_dispatch", GapEffect::SoundnessRisk,
                    "Virtual dispatch requires a call-graph/points-to oracle",
                    at, {callsite_id});
            }
        } else {
            summary.status = StageStatus::ConservativeIncomplete;
            summary.uncertainty_reasons.push_back(
                "indirect call target set is unresolved");
            add_gap(
                "indirect_call", GapEffect::SoundnessRisk,
                "Indirect call target set is unresolved; graph construction must add unknown influence",
                at, {callsite_id});
        }
        for (unsigned index = 0; index < call->getNumArgs(); ++index) {
            std::vector<std::string> group = argument_nodes(
                call->getArg(index), callsite_id, index);
            for (const std::string &node : group) {
                append_unique(summary.argument_node_ids, node);
            }
            summary.argument_node_groups.push_back(std::move(group));
            summary.argument_is_address.push_back(
                argument_is_address(call->getArg(index)));
            const std::string argument_slot = stable_id(
                "call-argument-slot",
                std::string(kValueTransferIdentityScheme) + '\0' +
                    callsite_id + '\0' + std::to_string(index));
            record_expression_transfer(
                call->getArg(index), argument_slot, RelationKind::Call,
                location(
                    call->getArg(index)->getExprLoc(),
                    call->getArg(index)->getEndLoc()),
                {}, callsite_id, index);
        }
        callsite_indices_[callsite_id] = output_.callsites.size();
        output_.callsites.push_back(std::move(summary));
        if (current_summary_ != nullptr) {
            append_unique(current_summary_->callsite_ids, callsite_id);
        }
        current_summary_ = previous_summary;
        synthetic_owner_override_ = previous_owner;
        return call_node;
    }

    bool add_aggregate_initializer(
        const VarDecl *declaration, const InitListExpr *initializer) {
        const RecordDecl *record = declaration->getType()->getAsRecordDecl();
        if (record == nullptr) {
            return false;
        }
        const InitListExpr *semantic = initializer->isSemanticForm()
                                           ? initializer
                                           : initializer->getSemanticForm();
        if (semantic == nullptr) {
            semantic = initializer;
        }
        AccessPath root{ensure_entity(declaration), 0, {}, false};
        unsigned index = 0;
        for (const FieldDecl *field : record->fields()) {
            if (index >= semantic->getNumInits()) {
                break;
            }
            AccessPath target = root;
            target.fields.push_back(ensure_entity(field));
            const Expr *value = semantic->getInit(index++);
            const std::string target_node = ensure_path_node(
                target, field->getType(), location(field->getLocation()),
                "AggregateField");
            add_value_relations(
                value, {target_node}, RelationKind::Field,
                location(value->getExprLoc()), "aggregate field initializer");
        }
        return true;
    }

    void add_value_relations(
        const Expr *source_expression, const std::vector<std::string> &targets,
        RelationKind kind, const SourceLocation &at, const std::string &fact,
        bool force_unknown_transfer = false) {
        const std::vector<std::string> sources = values_in(source_expression);
        for (const std::string &target : targets) {
            std::vector<std::string> relation_ids;
            for (const std::string &source : sources) {
                RelationKind actual_kind = kind;
                const SemanticNode *source_node = node(source);
                const SemanticNode *target_node = node(target);
                if ((source_node != nullptr && source_node->access_path &&
                     !source_node->access_path->fields.empty()) ||
                    (target_node != nullptr && target_node->access_path &&
                     !target_node->access_path->fields.empty())) {
                    actual_kind = RelationKind::Field;
                }
                const std::string relation = add_relation(
                    source, target, actual_kind, Certainty::May, at, fact);
                if (!relation.empty()) {
                    append_unique(relation_ids, relation);
                }
            }
            record_expression_transfer(
                source_expression, target, kind, at, std::move(relation_ids),
                std::nullopt, std::nullopt, force_unknown_transfer,
                force_unknown_transfer ? std::vector<std::string>{target}
                                       : std::vector<std::string>{});
        }
    }

    void collect_effects(const Stmt *statement, std::vector<std::string> &effects) {
        if (statement == nullptr) {
            return;
        }
        if (const auto *operation = llvm::dyn_cast<BinaryOperator>(statement);
            operation != nullptr && operation->isAssignmentOp()) {
            for (const std::string &node : nodes_for_lvalue(operation->getLHS())) {
                append_unique(effects, node);
            }
        } else if (const auto *operation = llvm::dyn_cast<UnaryOperator>(statement);
                   operation != nullptr && operation->isIncrementDecrementOp()) {
            for (const std::string &node : nodes_for_lvalue(operation->getSubExpr())) {
                append_unique(effects, node);
            }
        } else if (const auto *call = llvm::dyn_cast<CallExpr>(statement)) {
            append_unique(effects, ensure_callsite(call));
        } else if (const auto *returned = llvm::dyn_cast<ReturnStmt>(statement);
                   returned != nullptr && current_summary_ != nullptr &&
                   current_summary_->return_node_id) {
            append_unique(effects, *current_summary_->return_node_id);
        } else if (const auto *declarations =
                       llvm::dyn_cast<clang::DeclStmt>(statement)) {
            for (const Decl *declaration : declarations->decls()) {
                if (const auto *variable = llvm::dyn_cast<VarDecl>(declaration)) {
                    append_unique(effects, ensure_decl_node(variable));
                }
            }
        }
        for (const Stmt *child : statement->children()) {
            collect_effects(child, effects);
        }
    }

    void add_cfg_control_dependencies(FunctionDecl *function) {
        if (function == nullptr || function->getBody() == nullptr) {
            return;
        }
        clang::CFG::BuildOptions build_options;
        build_options.AddImplicitDtors = true;
        build_options.AddTemporaryDtors = true;
        std::unique_ptr<clang::CFG> cfg = clang::CFG::buildCFG(
            function, function->getBody(), &context_, build_options);
        if (!cfg) {
            add_gap(
                "cfg_construction_failure", GapEffect::SoundnessRisk,
                "Clang CFG construction failed; control dependence is incomplete",
                location(function->getLocation()), {ensure_entity(function)});
            return;
        }
        std::map<unsigned, const clang::CFGBlock *> blocks;
        std::set<unsigned> all;
        for (const clang::CFGBlock *block : *cfg) {
            if (block != nullptr) {
                blocks[block->getBlockID()] = block;
                all.insert(block->getBlockID());
            }
        }
        bool implicit_element = false;
        for (const auto &[id, block] : blocks) {
            (void)id;
            for (const clang::CFGElement element : *block) {
                if (!element.getAs<clang::CFGStmt>()) {
                    implicit_element = true;
                    break;
                }
            }
            if (implicit_element) {
                break;
            }
        }
        if (implicit_element) {
            add_gap(
                "cfg_implicit_element_not_lowered", GapEffect::SoundnessRisk,
                "A Clang CFG implicit destructor/initializer/lifetime element has no semantic effect node",
                location(function->getLocation()), {ensure_entity(function)});
        }
        std::map<unsigned, std::set<unsigned>> postdominators;
        const unsigned exit_id = cfg->getExit().getBlockID();
        for (const auto &[id, block] : blocks) {
            (void)block;
            postdominators[id] = id == exit_id ? std::set<unsigned>{id} : all;
        }
        bool changed = true;
        while (changed) {
            changed = false;
            for (const auto &[id, block] : blocks) {
                if (id == exit_id) {
                    continue;
                }
                std::vector<unsigned> successors;
                for (auto iterator = block->succ_begin();
                     iterator != block->succ_end(); ++iterator) {
                    const clang::CFGBlock *successor = *iterator;
                    if (successor != nullptr) {
                        successors.push_back(successor->getBlockID());
                    }
                }
                std::set<unsigned> next{id};
                if (!successors.empty()) {
                    std::set<unsigned> intersection =
                        postdominators[successors.front()];
                    for (std::size_t position = 1;
                         position < successors.size(); ++position) {
                        std::set<unsigned> narrowed;
                        const std::set<unsigned> &other =
                            postdominators[successors[position]];
                        std::set_intersection(
                            intersection.begin(), intersection.end(),
                            other.begin(), other.end(),
                            std::inserter(narrowed, narrowed.begin()));
                        intersection = std::move(narrowed);
                    }
                    next.insert(intersection.begin(), intersection.end());
                }
                if (next != postdominators[id]) {
                    postdominators[id] = std::move(next);
                    changed = true;
                }
            }
        }

        std::set<unsigned> can_reach_exit{exit_id};
        std::deque<unsigned> reverse_worklist{exit_id};
        while (!reverse_worklist.empty()) {
            const unsigned current = reverse_worklist.front();
            reverse_worklist.pop_front();
            const clang::CFGBlock *block = blocks[current];
            for (auto iterator = block->pred_begin();
                 iterator != block->pred_end(); ++iterator) {
                const clang::CFGBlock *predecessor = *iterator;
                if (predecessor != nullptr &&
                    can_reach_exit.insert(predecessor->getBlockID()).second) {
                    reverse_worklist.push_back(predecessor->getBlockID());
                }
            }
        }
        if (can_reach_exit.size() != blocks.size()) {
            add_gap(
                "cfg_nonterminating_region", GapEffect::SoundnessRisk,
                "At least one CFG region cannot reach the synthetic exit; ordinary exit-postdominance is incomplete there",
                location(function->getLocation()), {ensure_entity(function)});
        }

        for (const auto &[controller_id, controller] : blocks) {
            std::size_t successor_count = 0;
            for (auto iterator = controller->succ_begin();
                 iterator != controller->succ_end(); ++iterator) {
                if (*iterator != nullptr) {
                    ++successor_count;
                }
            }
            const auto *condition = llvm::dyn_cast_or_null<Expr>(
                controller->getTerminatorCondition());
            if (condition == nullptr) {
                if (successor_count > 1) {
                    add_gap(
                        "cfg_unresolved_branch_controller",
                        GapEffect::SoundnessRisk,
                        "A multi-successor CFG terminator has no extractable expression controller",
                        location(function->getLocation()),
                        {ensure_entity(function)});
                }
                continue;
            }
            const std::vector<std::string> controls = values_in(condition);
            if (controls.empty()) {
                continue;
            }
            std::set<unsigned> controlled_blocks;
            for (auto iterator = controller->succ_begin();
                 iterator != controller->succ_end(); ++iterator) {
                const clang::CFGBlock *successor = *iterator;
                if (successor == nullptr) {
                    continue;
                }
                for (const unsigned candidate :
                     postdominators[successor->getBlockID()]) {
                    if (!postdominators[controller_id].contains(candidate)) {
                        controlled_blocks.insert(candidate);
                    }
                }
            }
            std::vector<std::string> effects;
            for (const unsigned controlled_id : controlled_blocks) {
                const clang::CFGBlock *controlled = blocks[controlled_id];
                for (const clang::CFGElement element : *controlled) {
                    if (const auto statement = element.getAs<clang::CFGStmt>()) {
                        collect_effects(statement->getStmt(), effects);
                    }
                }
            }
            for (const std::string &control : controls) {
                for (const std::string &effect : effects) {
                    add_relation(
                        control, effect, RelationKind::Control,
                        Certainty::May,
                        location(condition->getExprLoc(), condition->getEndLoc()),
                        "Clang CFG postdominator control dependence", {},
                        {control});
                }
            }
        }
    }

    const SemanticNode *node(const std::string &id) const {
        const auto found = node_indices_.find(id);
        return found == node_indices_.end() ? nullptr
                                            : &output_.nodes[found->second];
    }

    std::string add_relation(
        const std::string &source, const std::string &target, RelationKind kind,
        Certainty certainty, const SourceLocation &at, const std::string &fact,
        const std::optional<std::string> &callsite = std::nullopt,
        std::vector<std::string> conditions = {},
        std::vector<std::string> uncertainty = {}) {
        if (source.empty() || target.empty()) {
            return {};
        }
        std::sort(conditions.begin(), conditions.end());
        conditions.erase(std::unique(conditions.begin(), conditions.end()), conditions.end());
        std::ostringstream material;
        material << source << '\0' << target << '\0'
                 << static_cast<int>(kind) << '\0';
        if (callsite) {
            material << *callsite;
        }
        for (const std::string &condition : conditions) {
            material << '\0' << condition;
        }
        const std::string relation_id = stable_id("relation", material.str());
        if (relation_indices_.contains(relation_id)) {
            return relation_id;
        }
        SemanticRelation relation;
        relation.relation_id = relation_id;
        relation.source_node_id = source;
        relation.target_node_id = target;
        relation.kind = kind;
        relation.certainty = certainty;
        relation.callsite_id = callsite;
        relation.condition_node_ids = std::move(conditions);
        relation.uncertainty_reasons = std::move(uncertainty);
        Evidence evidence;
        evidence.evidence_id = stable_id("evidence", relation_id + '\0' + fact);
        evidence.kind = kind == RelationKind::Control ? "control_dependence"
                                                     : "ast_semantics";
        evidence.certainty = certainty;
        evidence.fact = fact;
        evidence.producer = "rift-clang-indexer";
        if (!at.file.empty()) {
            evidence.location = at;
        }
        relation.evidence.push_back(std::move(evidence));
        relation_indices_[relation_id] = output_.relations.size();
        output_.relations.push_back(std::move(relation));
        if (current_summary_ != nullptr) {
            append_unique(current_summary_->relation_ids, relation_id);
        }
        return relation_id;
    }

    void add_gap(
        const std::string &kind, GapEffect effect, const std::string &detail,
        const SourceLocation &at, std::vector<std::string> affected) {
        std::ostringstream material;
        material << kind << '\0' << detail << '\0'
                 << location_material(at);
        const std::string id = stable_id("gap", material.str());
        if (gap_ids_.insert(id).second) {
            CoverageGap gap;
            gap.gap_id = id;
            gap.kind = kind;
            gap.effect = effect;
            gap.detail = detail;
            if (!at.file.empty()) {
                gap.locations.push_back(at);
            }
            gap.affected_ids = std::move(affected);
            output_.gaps.push_back(std::move(gap));
        }
        if (effect == GapEffect::SoundnessRisk &&
            output_.status == StageStatus::Complete) {
            output_.status = StageStatus::ConservativeIncomplete;
        }
    }

    ASTContext &context_;
    SourceManager &manager_;
    TuAccumulator &output_;
    std::vector<LogicalPathRoot> identity_roots_;
    std::filesystem::path working_directory_;
    IndexOptions options_;
    ValueTransferOptions transfer_options_;
    FunctionDecl *current_function_ = nullptr;
    FunctionSummary *current_summary_ = nullptr;
    std::optional<std::string> synthetic_owner_override_;
    std::map<const NamedDecl *, std::string> decl_entities_;
    std::map<std::string, std::size_t> entity_indices_;
    std::map<std::string, std::size_t> object_indices_;
    std::map<std::string, std::size_t> node_indices_;
    std::map<std::string, std::size_t> relation_indices_;
    std::map<std::string, std::size_t> summary_indices_;
    std::map<std::string, std::size_t> callsite_indices_;
    std::map<const CallExpr *, std::string> callsite_node_ids_;
    std::map<std::string, std::vector<AccessPath>> pointer_aliases_;
    std::map<std::string, std::vector<std::string>> path_occurrences_;
    std::set<std::string> gap_ids_;
    std::set<std::string> input_file_ids_;
    std::map<std::string, std::size_t> transfer_expression_indices_;
    std::set<std::string> transfer_ids_;
    std::set<std::string> transfer_gap_ids_;
    bool unmapped_identity_recorded_ = false;
};

class FactConsumer final : public clang::ASTConsumer {
  public:
    FactConsumer(
        TuAccumulator &output, std::vector<LogicalPathRoot> identity_roots,
        std::filesystem::path working_directory, std::string predefines,
        IndexOptions options, ValueTransferOptions transfer_options)
        : output_(output), identity_roots_(std::move(identity_roots)),
          working_directory_(std::move(working_directory)),
          predefines_(std::move(predefines)), options_(options),
          transfer_options_(transfer_options) {}

    void HandleTranslationUnit(ASTContext &context) override {
        output_.record.language = context.getLangOpts().CPlusPlus ? "c++" : "c";
        FactVisitor visitor(
            context, output_, identity_roots_, working_directory_, options_,
            transfer_options_);
        visitor.TraverseDecl(context.getTranslationUnitDecl());
        visitor.finalize(predefines_);
    }

  private:
    TuAccumulator &output_;
    std::vector<LogicalPathRoot> identity_roots_;
    std::filesystem::path working_directory_;
    std::string predefines_;
    IndexOptions options_;
    ValueTransferOptions transfer_options_;
};

class FactAction final : public clang::ASTFrontendAction {
  public:
    FactAction(
        TuAccumulator &output, std::vector<LogicalPathRoot> identity_roots,
        std::filesystem::path working_directory, IndexOptions options,
        ValueTransferOptions transfer_options)
        : output_(output), identity_roots_(std::move(identity_roots)),
          working_directory_(std::move(working_directory)), options_(options),
          transfer_options_(transfer_options) {}

    std::unique_ptr<clang::ASTConsumer> CreateASTConsumer(
        clang::CompilerInstance &compiler, llvm::StringRef) override {
        return std::make_unique<FactConsumer>(
            output_, identity_roots_, working_directory_,
            compiler.getPreprocessor().getPredefines(), options_,
            transfer_options_);
    }

  private:
    TuAccumulator &output_;
    std::vector<LogicalPathRoot> identity_roots_;
    std::filesystem::path working_directory_;
    IndexOptions options_;
    ValueTransferOptions transfer_options_;
};

class FactActionFactory final : public clang::tooling::FrontendActionFactory {
  public:
    FactActionFactory(
        TuAccumulator &output, std::vector<LogicalPathRoot> identity_roots,
        std::filesystem::path working_directory, IndexOptions options,
        ValueTransferOptions transfer_options)
        : output_(output), identity_roots_(std::move(identity_roots)),
          working_directory_(std::move(working_directory)), options_(options),
          transfer_options_(transfer_options) {}

    std::unique_ptr<clang::FrontendAction> create() override {
        return std::make_unique<FactAction>(
            output_, identity_roots_, working_directory_, options_,
            transfer_options_);
    }

  private:
    TuAccumulator &output_;
    std::vector<LogicalPathRoot> identity_roots_;
    std::filesystem::path working_directory_;
    IndexOptions options_;
    ValueTransferOptions transfer_options_;
};

StageStatus combine_status(StageStatus left, StageStatus right) {
    if (left == StageStatus::Failed || right == StageStatus::Failed) {
        return StageStatus::Failed;
    }
    if (left == StageStatus::ConservativeIncomplete ||
        right == StageStatus::ConservativeIncomplete) {
        return StageStatus::ConservativeIncomplete;
    }
    return StageStatus::Complete;
}

struct MergeState {
    std::unordered_map<std::string, std::size_t> entity_indices;
    std::unordered_set<std::string> object_ids;
    std::unordered_set<std::string> node_ids;
    std::unordered_set<std::string> relation_ids;
    std::unordered_set<std::string> callsite_ids;
    std::unordered_map<std::string, std::size_t> summary_indices;
    std::unordered_set<std::string> gap_ids;
    std::unordered_map<std::string, std::size_t> input_file_indices;
    std::unordered_map<std::string, std::string> input_digest_by_path;
    std::unordered_set<std::string> transfer_expression_ids;
    std::unordered_set<std::string> transfer_ids;
    std::unordered_set<std::string> transfer_gap_ids;
};

void merge_tu(
    SemanticIndex &index, SemanticValueTransferIndex &transfers,
    TuAccumulator &&tu, MergeState &state) {
    index.translation_units.push_back(std::move(tu.record));
    index.status = combine_status(index.status, tu.status);
    index.diagnostics.insert(
        index.diagnostics.end(), tu.diagnostics.begin(), tu.diagnostics.end());
    transfers.status = combine_status(
        transfers.status, tu.value_transfers.status);
    transfers.candidate_accounting_complete =
        transfers.candidate_accounting_complete &&
        tu.value_transfers.candidate_accounting_complete;
    transfers.resource_limit_hit =
        transfers.resource_limit_hit ||
        tu.value_transfers.resource_limit_hit;
    transfers.observed_expression_nodes +=
        tu.value_transfers.observed_expression_nodes;
    transfers.observed_transfers += tu.value_transfers.observed_transfers;
    transfers.diagnostics.insert(
        transfers.diagnostics.end(),
        tu.value_transfers.diagnostics.begin(),
        tu.value_transfers.diagnostics.end());

    for (InputFileDigest &input : tu.input_files) {
        const auto [known, inserted] = state.input_digest_by_path.emplace(
            input.logical_path, input.sha256);
        if (!inserted && known->second != input.sha256) {
            index.status = StageStatus::Failed;
            CoverageGap conflict;
            conflict.gap_id = stable_id(
                "gap", "input_changed_during_analysis\0" +
                           input.logical_path + '\0' + known->second + '\0' +
                           input.sha256);
            conflict.kind = "input_changed_during_analysis";
            conflict.effect = GapEffect::StageFailure;
            conflict.detail =
                "One logical input path had different bytes across translation units";
            conflict.affected_ids = {input.logical_path};
            if (state.gap_ids.insert(conflict.gap_id).second) {
                index.coverage_gaps.push_back(std::move(conflict));
            }
        }
        const auto existing =
            state.input_file_indices.find(input.input_file_id);
        if (existing == state.input_file_indices.end()) {
            state.input_file_indices[input.input_file_id] =
                index.input_files.size();
            index.input_files.push_back(std::move(input));
        } else {
            InputFileDigest &merged = index.input_files[existing->second];
            for (const std::string &path : input.observed_paths) {
                append_unique(merged.observed_paths, path);
            }
            std::sort(
                merged.observed_paths.begin(),
                merged.observed_paths.end());
        }
    }

    for (EntityRef &entity : tu.entities) {
        const auto found = state.entity_indices.find(entity.entity_id);
        if (found == state.entity_indices.end()) {
            state.entity_indices[entity.entity_id] = index.entities.size();
            index.entities.push_back(std::move(entity));
            continue;
        }
        EntityRef &existing = index.entities[found->second];
        existing.translation_unit_ids.insert(
            entity.translation_unit_ids.begin(), entity.translation_unit_ids.end());
        for (const SourceLocation &at : entity.declarations) {
            append_unique_location(existing.declarations, at);
        }
        for (const SourceLocation &at : entity.definitions) {
            append_unique_location(existing.definitions, at);
        }
    }
    for (AbstractObject &object : tu.objects) {
        if (state.object_ids.insert(object.object_id).second) {
            index.abstract_objects.push_back(std::move(object));
        }
    }
    for (SemanticNode &node : tu.nodes) {
        if (state.node_ids.insert(node.node_id).second) {
            index.nodes.push_back(std::move(node));
        }
    }
    for (SemanticRelation &relation : tu.relations) {
        if (state.relation_ids.insert(relation.relation_id).second) {
            index.relations.push_back(std::move(relation));
        }
    }
    for (CallSiteSummary &callsite : tu.callsites) {
        if (state.callsite_ids.insert(callsite.callsite_id).second) {
            index.callsites.push_back(std::move(callsite));
        }
    }

    for (FunctionSummary &summary : tu.summaries) {
        const auto found = state.summary_indices.find(summary.function_entity_id);
        if (found == state.summary_indices.end()) {
            state.summary_indices[summary.function_entity_id] =
                index.function_summaries.size();
            index.function_summaries.push_back(std::move(summary));
            continue;
        }
        FunctionSummary &existing = index.function_summaries[found->second];
        for (const std::string &node : summary.parameter_node_ids) {
            append_unique(existing.parameter_node_ids, node);
        }
        for (const std::string &node : summary.owned_node_ids) {
            append_unique(existing.owned_node_ids, node);
        }
        for (const std::string &relation : summary.relation_ids) {
            append_unique(existing.relation_ids, relation);
        }
        for (const std::string &callsite : summary.callsite_ids) {
            append_unique(existing.callsite_ids, callsite);
        }
        existing.status = combine_status(existing.status, summary.status);
        existing.uncertainty_reasons.insert(
            existing.uncertainty_reasons.end(),
            summary.uncertainty_reasons.begin(),
            summary.uncertainty_reasons.end());
    }
    for (CoverageGap &gap : tu.gaps) {
        if (state.gap_ids.insert(gap.gap_id).second) {
            index.coverage_gaps.push_back(std::move(gap));
        }
    }
    for (TransferExpression &expression :
         tu.value_transfers.expressions) {
        if (state.transfer_expression_ids.insert(
                expression.expression_id).second) {
            transfers.expressions.push_back(std::move(expression));
        }
    }
    for (TypedValueTransfer &transfer : tu.value_transfers.transfers) {
        if (state.transfer_ids.insert(transfer.transfer_id).second) {
            transfers.transfers.push_back(std::move(transfer));
        }
    }
    for (CoverageGap &gap : tu.value_transfers.coverage_gaps) {
        if (state.transfer_gap_ids.insert(gap.gap_id).second) {
            transfers.coverage_gaps.push_back(std::move(gap));
        }
    }
}

CoverageGap stage_gap(
    const std::string &kind, const std::string &detail,
    const TranslationUnitRecord &tu) {
    CoverageGap gap;
    gap.gap_id = stable_id("gap", kind + '\0' + tu.translation_unit_id);
    gap.kind = kind;
    gap.effect = GapEffect::StageFailure;
    gap.detail = detail;
    gap.affected_ids = {tu.translation_unit_id};
    return gap;
}

}  // namespace

IndexBuildArtifacts build_semantic_index_with_value_transfers(
    const CompilationPlan &plan, const IndexOptions &options,
    const ValueTransferOptions &transfer_options) {
    IndexBuildArtifacts artifacts;
    SemanticIndex &index = artifacts.index;
    SemanticValueTransferIndex &transfers = artifacts.value_transfers;
    transfers.status = StageStatus::Complete;
    transfers.limits = transfer_options;
    index.identity_scheme = kIdentityScheme;
    index.compilation_database_sha256 = plan.compilation_database_sha256;
    index.canonical_compilation_database_sha256 =
        plan.canonical_compilation_database_sha256;
    index.path_map_sha256 = plan.path_map_sha256;
    for (const LogicalPathRoot &root : plan.identity_roots) {
        index.logical_root_ids.push_back(root.root_id);
    }
    index.source_identity_root = plan.source_identity_root;
    index.input_manifest_sha256 = sha256_hex(
        std::string(kIdentityScheme) + '\0' + "input-manifest/1.0.0");
    index.artifact_id = stable_id(
        "index", std::string(kIdentityScheme) + '\0' +
                     plan.canonical_compilation_database_sha256 + '\0' +
                     plan.path_map_sha256 + '\0' +
                     index.input_manifest_sha256);
    if (plan.status == StageStatus::Failed || plan.commands.empty() ||
        plan.identity_roots.empty() ||
        !valid_digest(plan.canonical_compilation_database_sha256) ||
        !valid_digest(plan.path_map_sha256)) {
        index.status = StageStatus::Failed;
        index.diagnostics.push_back(
            "cannot index a failed, empty, or non-portable compilation plan");
        transfers.status = StageStatus::Failed;
        transfers.semantic_index_artifact_id = index.artifact_id;
        transfers.artifact_id =
            canonical_semantic_value_transfer_artifact_id(transfers);
        return artifacts;
    }
    index.status = plan.status;
    index.coverage_gaps = plan.coverage_gaps;
    index.diagnostics = plan.diagnostics;
    MergeState merge_state;
    for (const CoverageGap &gap : index.coverage_gaps) {
        merge_state.gap_ids.insert(gap.gap_id);
    }

    for (const CompilationCommand &command : plan.commands) {
        TuAccumulator tu;
        tu.record.translation_unit_id = command.translation_unit_id;
        tu.record.source_file = command.logical_source_file;
        tu.record.working_directory = command.logical_working_directory;
        tu.record.command_sha256 = command.command_sha256;
        int exit_code = 0;
        {
            SingleCommandDatabase database(command);
            std::vector<std::string> sources{command.source_file};
            clang::tooling::ClangTool tool(database, sources);
            FactActionFactory factory(
                tu, plan.identity_roots, command.working_directory, options,
                transfer_options);
            exit_code = tool.run(&factory);
        }
        if (exit_code != 0) {
            tu.status = StageStatus::Failed;
            tu.record.status = StageStatus::Failed;
            const std::string detail =
                "Clang Tooling failed for translation unit with exit code " +
                std::to_string(exit_code);
            tu.record.diagnostics.push_back(detail);
            tu.diagnostics.push_back(
                command.translation_unit_id + ": " + detail);
            tu.gaps.push_back(stage_gap("clang_translation_unit_failure", detail, tu.record));
        } else {
            tu.record.status = tu.status;
        }
        if (tu.status == StageStatus::Failed) {
            tu.entities.clear();
            tu.objects.clear();
            tu.nodes.clear();
            tu.relations.clear();
            tu.summaries.clear();
            tu.callsites.clear();
            tu.value_transfers.expressions.clear();
            tu.value_transfers.transfers.clear();
            tu.value_transfers.status = StageStatus::Failed;
        }
        merge_tu(index, transfers, std::move(tu), merge_state);
#if defined(__GLIBC__)
        // Clang creates large per-TU AST arenas.  Their objects are dead after
        // ClangTool destruction, but glibc may otherwise retain the freed
        // pages until process exit and overlap all later graph stages.
        (void)::malloc_trim(0);
#endif
    }

    const std::set<std::string> defined_functions = [&]() {
        std::set<std::string> values;
        for (const FunctionSummary &summary : index.function_summaries) {
            values.insert(summary.function_entity_id);
        }
        return values;
    }();
    for (CallSiteSummary &callsite : index.callsites) {
        if (!callsite.direct) {
            index.status = combine_status(
                index.status, StageStatus::ConservativeIncomplete);
            continue;
        }
        bool missing = false;
        for (const std::string &callee : callsite.candidate_callee_ids) {
            if (!defined_functions.contains(callee)) {
                missing = true;
            }
        }
        if (missing) {
            callsite.status = StageStatus::ConservativeIncomplete;
            callsite.uncertainty_reasons.push_back(
                "direct callee definition is absent from the indexed translation units");
            CoverageGap gap;
            gap.gap_id = stable_id(
                "gap", "missing_callee_definition\0" + callsite.callsite_id);
            gap.kind = "missing_callee_definition";
            gap.effect = GapEffect::SoundnessRisk;
            gap.detail =
                "Direct call has no indexed function body; conservative unknown edges are required";
            gap.locations = {callsite.location};
            gap.affected_ids = {callsite.callsite_id};
            index.coverage_gaps.push_back(std::move(gap));
            index.status = combine_status(
                index.status, StageStatus::ConservativeIncomplete);
        }
    }

    std::sort(
        index.input_files.begin(), index.input_files.end(),
        [](const InputFileDigest &left, const InputFileDigest &right) {
            return std::tie(
                       left.logical_path, left.role, left.sha256,
                       left.input_file_id) <
                   std::tie(
                       right.logical_path, right.role, right.sha256,
                       right.input_file_id);
        });
    std::ostringstream input_manifest;
    input_manifest << kIdentityScheme << '\0' << "input-manifest/1.0.0";
    for (const InputFileDigest &input : index.input_files) {
        input_manifest << '\0' << to_string(input.role) << '\0'
                       << input.logical_path.size() << ':'
                       << input.logical_path << '\0' << input.sha256 << '\0'
                       << input.byte_size;
    }
    index.input_manifest_sha256 = sha256_hex(input_manifest.str());
    index.artifact_id = stable_id(
        "index", std::string(kIdentityScheme) + '\0' +
                     index.canonical_compilation_database_sha256 + '\0' +
                     index.path_map_sha256 + '\0' +
                     index.input_manifest_sha256);

    const std::vector<std::string> validation_errors =
        validate_semantic_index(index);
    if (!validation_errors.empty()) {
        index.status = StageStatus::Failed;
        index.diagnostics.insert(
            index.diagnostics.end(), validation_errors.begin(), validation_errors.end());
    }
    std::sort(
        transfers.expressions.begin(), transfers.expressions.end(),
        [](const TransferExpression &left,
           const TransferExpression &right) {
            return left.expression_id < right.expression_id;
        });
    std::sort(
        transfers.transfers.begin(), transfers.transfers.end(),
        [](const TypedValueTransfer &left,
           const TypedValueTransfer &right) {
            return left.transfer_id < right.transfer_id;
        });
    transfers.semantic_index_artifact_id = index.artifact_id;
    transfers.status = combine_status(transfers.status, index.status);
    transfers.artifact_id =
        canonical_semantic_value_transfer_artifact_id(transfers);
    const std::vector<std::string> transfer_validation_errors =
        validate_semantic_value_transfers(transfers, index);
    if (!transfer_validation_errors.empty()) {
        transfers.status = StageStatus::Failed;
        transfers.diagnostics.insert(
            transfers.diagnostics.end(),
            transfer_validation_errors.begin(),
            transfer_validation_errors.end());
    }
    return artifacts;
}

SemanticIndex build_semantic_index(
    const CompilationPlan &plan, const IndexOptions &options) {
    return build_semantic_index_with_value_transfers(plan, options).index;
}

}  // namespace rift::core
