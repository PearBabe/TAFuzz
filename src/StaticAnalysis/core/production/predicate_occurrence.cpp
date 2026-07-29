#include "rift/core/predicate_occurrence.h"

#include <clang/AST/ASTConsumer.h>
#include <clang/AST/ASTContext.h>
#include <clang/AST/Decl.h>
#include <clang/AST/Expr.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendActions.h>
#include <clang/Index/USRGeneration.h>
#include <clang/Lex/Lexer.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <clang/Tooling/Tooling.h>

#include <llvm/ADT/SmallString.h>
#include <llvm/Support/Casting.h>

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <string_view>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

namespace rift::core {
namespace {

using clang::ASTContext;
using clang::DeclRefExpr;
using clang::Expr;
using clang::MemberExpr;
using clang::NamedDecl;
using clang::QualType;
using clang::SourceManager;
using clang::ValueDecl;

constexpr std::string_view kSchemaVersion = "1.0.0";

struct Request {
    std::size_t account_index = 0;
    std::string target_file;
};

struct TargetKey {
    std::string file;
    std::uint32_t line = 0;
    std::uint32_t column = 0;
    std::string location_kind;

    friend bool operator<(const TargetKey &left, const TargetKey &right) {
        return std::tie(
                   left.file, left.line, left.column, left.location_kind) <
               std::tie(
                   right.file, right.line, right.column,
                   right.location_kind);
    }
};

struct TuParseOutput {
    std::vector<PredicateOccurrence> occurrences;
    std::vector<std::pair<std::size_t, std::string>> account_reasons;
    std::vector<std::string> diagnostics;
};

struct PredicateReferenceEvidence {
    std::vector<std::string> paths;
    std::vector<ValueType> value_types;
};

struct ExpectedTypeEvidence {
    ValueType value_type;
    std::vector<std::string> uncertainty_reasons;
};

bool is_digest(const std::string &value) {
    return value.size() == 64 &&
           std::all_of(
               value.begin(), value.end(), [](const unsigned char byte) {
                   return std::isdigit(byte) != 0 ||
                          (byte >= 'a' && byte <= 'f');
               });
}

std::string normalized_file(std::string value) {
    std::replace(value.begin(), value.end(), '\\', '/');
    while (value.starts_with("./")) {
        value.erase(0, 2);
    }
    while (value.size() > 1 && value.ends_with('/')) {
        value.pop_back();
    }
    return value;
}

bool path_suffix_match(const std::string &logical, const std::string &requested) {
    const std::string left = normalized_file(logical);
    const std::string right = normalized_file(requested);
    if (left == right) {
        return true;
    }
    return !right.empty() && left.size() > right.size() &&
           left.ends_with('/' + right);
}

template <typename T>
void append_unique(std::vector<T> &values, const T &value) {
    if (std::find(values.begin(), values.end(), value) == values.end()) {
        values.push_back(value);
    }
}

void sort_unique(std::vector<std::string> &values) {
    std::sort(values.begin(), values.end());
    values.erase(std::unique(values.begin(), values.end()), values.end());
}

const char *role_name(ApRole role) {
    switch (role) {
    case ApRole::Trigger:
        return "trigger";
    case ApRole::Response:
        return "response";
    case ApRole::Cancel:
        return "cancel";
    case ApRole::State:
        return "state";
    case ApRole::Guard:
        return "guard";
    case ApRole::Bound:
        return "bound";
    case ApRole::Clock:
        return "clock";
    case ApRole::Scope:
        return "scope";
    }
    return "state";
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

bool integer_alias_kind(ValueKind kind) {
    return kind == ValueKind::Integer || kind == ValueKind::BitVector ||
           kind == ValueKind::Timestamp || kind == ValueKind::Duration;
}

// Property producers may spell an integer typedef (for example uint16_t)
// differently from Clang's desugared canonical type (unsigned short).  Such
// aliases are equivalent only when their complete representation facts agree.
// Nominal enum/record/pointer identities remain canonical-name sensitive.
bool equivalent_value_type(
    const ValueType &left, const ValueType &right) {
    if (left.kind != right.kind || left.bit_width != right.bit_width ||
        left.is_signed != right.is_signed || left.unit != right.unit) {
        return false;
    }
    if (left.canonical == right.canonical) {
        return true;
    }
    return integer_alias_kind(left.kind) && left.bit_width.has_value() &&
           left.is_signed.has_value();
}

bool usable_expected_type(const ValueType &type) {
    return type.kind != ValueKind::Unknown && !type.canonical.empty() &&
           type.canonical != "unknown";
}

ExpectedTypeEvidence expected_type_evidence(
    const Selector &selector, const PredicateReferenceEvidence &references) {
    ExpectedTypeEvidence result;
    if (!references.value_types.empty()) {
        result.value_type = references.value_types.front();
    }
    if (!selector.value_type) {
        result.uncertainty_reasons.push_back(
            "predicate_selector_value_type_missing");
    } else {
        result.value_type = *selector.value_type;
    }
    if (references.value_types.empty()) {
        result.uncertainty_reasons.push_back(
            "predicate_reference_value_type_missing");
    } else {
        for (const ValueType &candidate : references.value_types) {
            if (!equivalent_value_type(
                    references.value_types.front(), candidate)) {
                append_unique(
                    result.uncertainty_reasons,
                    std::string("predicate_reference_type_inconsistent"));
            }
        }
        if (selector.value_type &&
            !equivalent_value_type(
                *selector.value_type, references.value_types.front())) {
            append_unique(
                result.uncertainty_reasons,
                std::string("predicate_selector_reference_type_mismatch"));
        }
    }
    if (!usable_expected_type(result.value_type)) {
        append_unique(
            result.uncertainty_reasons,
            std::string("predicate_expected_value_type_unknown"));
    }
    sort_unique(result.uncertainty_reasons);
    return result;
}

std::optional<std::string> usr_for(
    const NamedDecl *declaration,
    const std::vector<LogicalPathRoot> &identity_roots) {
    if (declaration == nullptr) {
        return std::nullopt;
    }
    llvm::SmallString<256> buffer;
    if (clang::index::generateUSRForDecl(
            declaration->getCanonicalDecl(), buffer)) {
        return std::nullopt;
    }
    return canonicalize_identity_text(
        identity_roots, buffer.str().str());
}

std::vector<std::string> entity_ids_for_usr(
    const SemanticIndex &index, const std::optional<std::string> &usr) {
    std::vector<std::string> result;
    if (!usr) {
        return result;
    }
    for (const EntityRef &entity : index.entities) {
        if (entity.usr && *entity.usr == *usr) {
            result.push_back(entity.entity_id);
        }
    }
    sort_unique(result);
    return result;
}

bool location_contains(
    const SourceLocation &range, const SourceLocation &point) {
    if (normalized_file(range.file) != normalized_file(point.file)) {
        return false;
    }
    const std::uint32_t end_line =
        range.end_line == 0 ? range.line : range.end_line;
    const std::uint32_t end_column =
        range.end_column == 0 ? range.column : range.end_column;
    const auto start = std::tie(range.line, range.column);
    const auto finish = std::tie(end_line, end_column);
    const auto candidate = std::tie(point.line, point.column);
    return start <= candidate && candidate <= finish;
}

std::string location_material(const SourceLocation &location) {
    std::ostringstream stream;
    stream << normalized_file(location.file) << ':' << location.line << ':'
           << location.column << ':' << location.location_kind;
    return stream.str();
}

std::string access_path_material(const AccessPath &path) {
    std::ostringstream stream;
    stream << path.root_entity_id << "|d=" << path.dereference_depth;
    for (const std::string &field : path.fields) {
        stream << "|f=" << field;
    }
    stream << "|u=" << path.unknown_suffix;
    return stream.str();
}

void collect_predicate_references(
    const ExpressionStructure &expression, const std::string &path,
    std::map<std::string, PredicateReferenceEvidence> &selector_evidence) {
    if (expression.node_kind == "reference" &&
        expression.referenced_selector_id) {
        PredicateReferenceEvidence &evidence =
            selector_evidence[*expression.referenced_selector_id];
        evidence.paths.push_back(path);
        append_unique(evidence.value_types, expression.value_type);
    }
    for (std::size_t index = 0; index < expression.operands.size(); ++index) {
        collect_predicate_references(
            expression.operands[index],
            path + ".operands[" + std::to_string(index) + ']',
            selector_evidence);
    }
}

std::vector<ApRole> roles_for_selector(
    const AtomicProposition &ap, const std::string &selector_id) {
    std::vector<ApRole> result;
    if (!ap.role_selector_groups.empty()) {
        for (const RoleSelectorGroup &group : ap.role_selector_groups) {
            if (std::find(
                    group.selector_ids.begin(), group.selector_ids.end(),
                    selector_id) != group.selector_ids.end()) {
                append_unique(result, group.role);
            }
        }
    } else if (std::find(
                   ap.selector_ids.begin(), ap.selector_ids.end(),
                   selector_id) != ap.selector_ids.end()) {
        result = ap.roles;
    }
    std::sort(result.begin(), result.end(), [](ApRole left, ApRole right) {
        return std::string(role_name(left)) < std::string(role_name(right));
    });
    result.erase(std::unique(result.begin(), result.end()), result.end());
    return result;
}

CoverageGap make_gap(
    const std::string &kind, GapEffect effect, const std::string &detail,
    const std::vector<std::string> &affected_ids,
    const std::optional<SourceLocation> &location = std::nullopt) {
    std::ostringstream material;
    material << kind << '\0' << detail;
    for (const std::string &id : affected_ids) {
        material << '\0' << id;
    }
    CoverageGap gap;
    gap.gap_id = stable_id("gap", material.str());
    gap.kind = kind;
    gap.effect = effect;
    gap.detail = detail;
    gap.affected_ids = affected_ids;
    sort_unique(gap.affected_ids);
    if (location) {
        gap.locations.push_back(*location);
    }
    return gap;
}

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
        return requested.lexically_normal() == expected.lexically_normal()
                   ? std::vector<clang::tooling::CompileCommand>{command_}
                   : std::vector<clang::tooling::CompileCommand>{};
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

class OccurrenceVisitor final
    : public clang::RecursiveASTVisitor<OccurrenceVisitor> {
  public:
    OccurrenceVisitor(
        ASTContext &context, const CompilationCommand &command,
        const std::vector<LogicalPathRoot> &identity_roots,
        const SemanticIndex &semantic_index,
        const std::vector<PredicateSelectorAccount> &accounts,
        const std::vector<Request> &requests,
        const PredicateOccurrenceOptions &options, TuParseOutput &output)
        : context_(context), manager_(context.getSourceManager()),
          command_(command), identity_roots_(identity_roots),
          semantic_index_(semantic_index), accounts_(accounts),
          options_(options), output_(output) {
        for (const Request &request : requests) {
            const PredicateSelectorAccount &account =
                accounts_.at(request.account_index);
            TargetKey key{
                request.target_file, account.requested_location.line,
                account.requested_location.column,
                account.requested_location.location_kind};
            targets_[std::move(key)].push_back(request.account_index);
        }
    }

    bool VisitDeclRefExpr(DeclRefExpr *expression) {
        capture(
            expression, expression->getLocation(), expression->getType(),
            expression->getDecl(), PredicateOccurrenceKind::DeclRef);
        return true;
    }

    bool VisitMemberExpr(MemberExpr *expression) {
        capture(
            expression, expression->getMemberLoc(), expression->getType(),
            expression->getMemberDecl(), PredicateOccurrenceKind::MemberExpr);
        return true;
    }

  private:
    struct LocationPair {
        SourceLocation spelling;
        SourceLocation expansion;
        bool macro = false;
        bool mapped = true;
    };

    SourceLocation map_location(
        clang::SourceLocation begin, clang::SourceLocation end,
        const std::string &kind, bool &mapped) const {
        SourceLocation result;
        result.location_kind = kind;
        if (begin.isInvalid()) {
            result.file = "riftpath://v1/unmapped/";
            result.line = 1;
            result.column = 1;
            mapped = false;
            return result;
        }
        const clang::PresumedLoc presumed = manager_.getPresumedLoc(begin);
        if (presumed.isInvalid()) {
            result.file = "riftpath://v1/unmapped/";
            result.line = 1;
            result.column = 1;
            mapped = false;
            return result;
        }
        std::filesystem::path physical = manager_.getFilename(begin).str();
        if (physical.is_relative()) {
            physical = std::filesystem::path(command_.working_directory) /
                       physical;
        }
        const std::optional<std::string> logical =
            logical_identity_path(identity_roots_, physical);
        result.file = logical.value_or("riftpath://v1/unmapped/");
        mapped = mapped && logical.has_value();
        result.line = presumed.getLine();
        result.column = presumed.getColumn();
        if (end.isValid()) {
            const clang::PresumedLoc presumed_end = manager_.getPresumedLoc(end);
            if (presumed_end.isValid()) {
                result.end_line = presumed_end.getLine();
                result.end_column = presumed_end.getColumn();
            }
        }
        return result;
    }

    std::vector<std::string> macro_stack(
        clang::SourceLocation original) const {
        std::vector<std::string> result;
        if (!options_.retain_macro_stack || !original.isMacroID()) {
            return result;
        }
        std::set<unsigned> seen;
        clang::SourceLocation cursor = original;
        while (cursor.isMacroID() &&
               seen.insert(cursor.getRawEncoding()).second) {
            const clang::SourceLocation spelling = manager_.getSpellingLoc(cursor);
            const clang::PresumedLoc presumed = manager_.getPresumedLoc(spelling);
            if (presumed.isValid()) {
                bool mapped = true;
                const SourceLocation at = map_location(
                    spelling, clang::SourceLocation(), "spelling", mapped);
                std::ostringstream value;
                value << at.file << ':' << at.line << ':' << at.column;
                result.push_back(value.str());
            }
            const clang::SourceLocation caller =
                manager_.getImmediateMacroCallerLoc(cursor);
            if (caller == cursor) {
                break;
            }
            cursor = caller;
        }
        return result;
    }

    LocationPair locations(clang::SourceLocation original) const {
        LocationPair result;
        result.macro = original.isMacroID();
        const clang::SourceLocation spelling = manager_.getSpellingLoc(original);
        const clang::SourceLocation expansion = manager_.getExpansionLoc(original);
        const clang::SourceLocation spelling_end = clang::Lexer::getLocForEndOfToken(
            spelling, 0, manager_, context_.getLangOpts());
        const clang::SourceLocation expansion_end = clang::Lexer::getLocForEndOfToken(
            expansion, 0, manager_, context_.getLangOpts());
        result.spelling =
            map_location(spelling, spelling_end, "spelling", result.mapped);
        result.expansion =
            map_location(expansion, expansion_end, "expansion", result.mapped);
        const std::vector<std::string> stack = macro_stack(original);
        result.spelling.macro_stack = stack;
        result.expansion.macro_stack = stack;
        return result;
    }

    std::vector<std::size_t> matching_accounts(
        const LocationPair &locations) const {
        std::vector<std::size_t> result;
        const TargetKey spelling{
            locations.spelling.file, locations.spelling.line,
            locations.spelling.column, "spelling"};
        const TargetKey expansion{
            locations.expansion.file, locations.expansion.line,
            locations.expansion.column, "expansion"};
        if (const auto found = targets_.find(spelling); found != targets_.end()) {
            result.insert(result.end(), found->second.begin(), found->second.end());
        }
        if (const auto found = targets_.find(expansion); found != targets_.end()) {
            result.insert(result.end(), found->second.begin(), found->second.end());
        }
        std::sort(result.begin(), result.end());
        result.erase(std::unique(result.begin(), result.end()), result.end());
        return result;
    }

    std::optional<AccessPath> direct_member_access_path(
        const Expr *expression, std::vector<std::string> &reasons) const {
        const Expr *plain = expression == nullptr
                                ? nullptr
                                : expression->IgnoreParenImpCasts();
        if (plain == nullptr) {
            append_unique(reasons, std::string("member_base_is_unavailable"));
            return std::nullopt;
        }
        if (const auto *reference = llvm::dyn_cast<DeclRefExpr>(plain)) {
            const std::vector<std::string> entities = entity_ids_for_usr(
                semantic_index_, usr_for(reference->getDecl(), identity_roots_));
            if (entities.size() != 1) {
                append_unique(
                    reasons,
                    entities.empty() ? std::string("member_root_entity_unresolved")
                                     : std::string("member_root_entity_ambiguous"));
                return std::nullopt;
            }
            return AccessPath{entities.front(), 0, {}, false};
        }
        if (const auto *member = llvm::dyn_cast<MemberExpr>(plain)) {
            if (member->isArrow()) {
                append_unique(reasons, std::string("alias_resolution_required"));
                return std::nullopt;
            }
            std::optional<AccessPath> base =
                direct_member_access_path(member->getBase(), reasons);
            if (!base) {
                return std::nullopt;
            }
            const std::vector<std::string> fields = entity_ids_for_usr(
                semantic_index_,
                usr_for(member->getMemberDecl(), identity_roots_));
            if (fields.size() != 1) {
                append_unique(
                    reasons,
                    fields.empty() ? std::string("member_field_entity_unresolved")
                                   : std::string("member_field_entity_ambiguous"));
                return std::nullopt;
            }
            base->fields.push_back(fields.front());
            return base;
        }
        append_unique(reasons, std::string("unsupported_member_base_expression"));
        return std::nullopt;
    }

    std::vector<std::string> semantic_nodes_for(
        PredicateOccurrenceKind kind,
        const std::optional<std::string> &entity_id,
        const std::optional<AccessPath> &path,
        const SourceLocation &point) const {
        std::vector<std::string> result;
        for (const SemanticNode &node : semantic_index_.nodes) {
            if (kind == PredicateOccurrenceKind::DeclRef) {
                if (entity_id && node.entity_id == *entity_id &&
                    (!node.access_path ||
                     (node.access_path->root_entity_id == *entity_id &&
                      node.access_path->fields.empty()))) {
                    result.push_back(node.node_id);
                }
                continue;
            }
            if (path && node.access_path && *node.access_path == *path &&
                location_contains(node.location, point)) {
                result.push_back(node.node_id);
            }
        }
        sort_unique(result);
        return result;
    }

    void capture(
        const Expr *expression, clang::SourceLocation identifier,
        QualType type, const ValueDecl *declaration,
        PredicateOccurrenceKind kind) {
        const LocationPair at = locations(identifier);
        const std::vector<std::size_t> matched = matching_accounts(at);
        if (matched.empty()) {
            return;
        }
        for (const std::size_t account_index : matched) {
            if (output_.occurrences.size() >= options_.maximum_occurrences) {
                output_.account_reasons.emplace_back(
                    account_index, "occurrence_resource_guard_reached");
                continue;
            }
            const PredicateSelectorAccount &account = accounts_.at(account_index);
            PredicateOccurrence occurrence;
            occurrence.ap_id = account.ap_id;
            occurrence.selector_id = account.selector_id;
            occurrence.roles = account.roles;
            occurrence.predicate_paths = account.predicate_paths;
            occurrence.translation_unit_id = command_.translation_unit_id;
            occurrence.kind = kind;
            occurrence.spelling_location = at.spelling;
            occurrence.expansion_location = at.expansion;
            occurrence.value_type = type_info(type, context_, identity_roots_);
            if (!equivalent_value_type(
                    account.expected_value_type, occurrence.value_type)) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("predicate_occurrence_type_mismatch"));
            }
            occurrence.referenced_usr = usr_for(declaration, identity_roots_);
            const std::vector<std::string> entity_ids = entity_ids_for_usr(
                semantic_index_, occurrence.referenced_usr);
            if (entity_ids.size() == 1) {
                occurrence.referenced_entity_id = entity_ids.front();
            } else {
                append_unique(
                    occurrence.uncertainty_reasons,
                    entity_ids.empty() ? std::string("referenced_entity_unresolved")
                                       : std::string("referenced_entity_ambiguous"));
            }

            if (kind == PredicateOccurrenceKind::MemberExpr) {
                const auto *member = llvm::dyn_cast<MemberExpr>(expression);
                if (member == nullptr || member->isArrow()) {
                    append_unique(
                        occurrence.uncertainty_reasons,
                        std::string("alias_resolution_required"));
                } else {
                    occurrence.access_path = direct_member_access_path(
                        member, occurrence.uncertainty_reasons);
                }
            }

            const SourceLocation &selected =
                account.requested_location.location_kind == "expansion"
                    ? occurrence.expansion_location
                    : occurrence.spelling_location;
            occurrence.semantic_node_ids = semantic_nodes_for(
                kind, occurrence.referenced_entity_id,
                occurrence.access_path, selected);
            if (occurrence.semantic_node_ids.empty()) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("m4_semantic_node_unresolved"));
            } else if (occurrence.semantic_node_ids.size() != 1) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("m4_semantic_node_ambiguous"));
            }
            if (kind == PredicateOccurrenceKind::MemberExpr &&
                occurrence.access_path) {
                occurrence.member_base_entity_id =
                    occurrence.access_path->root_entity_id;
                if (occurrence.semantic_node_ids.size() == 1) {
                    const auto node = std::find_if(
                        semantic_index_.nodes.begin(),
                        semantic_index_.nodes.end(),
                        [&](const SemanticNode &candidate) {
                            return candidate.node_id ==
                                   occurrence.semantic_node_ids.front();
                        });
                    if (node != semantic_index_.nodes.end() &&
                        node->abstract_object_id) {
                        occurrence.member_abstract_object_id =
                            node->abstract_object_id;
                    } else {
                        append_unique(
                            occurrence.uncertainty_reasons,
                            std::string("m4_abstract_object_unresolved"));
                    }
                }
            }
            if (at.macro) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("macro_occurrence_requires_expansion_reasoning"));
            }
            if (!at.mapped) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("source_identity_unmapped"));
            }
            occurrence.certainty = occurrence.uncertainty_reasons.empty()
                                       ? Certainty::Must
                                       : Certainty::Unknown;
            occurrence.resolution = occurrence.uncertainty_reasons.empty()
                                        ? PredicateOccurrenceResolution::Exact
                                        : PredicateOccurrenceResolution::Unknown;
            const std::string semantic_material =
                occurrence.ap_id + '\0' + occurrence.selector_id + '\0' +
                occurrence.translation_unit_id + '\0' +
                to_string(occurrence.kind) + '\0' +
                location_material(occurrence.spelling_location) + '\0' +
                location_material(occurrence.expansion_location) + '\0' +
                occurrence.referenced_usr.value_or("unknown") + '\0' +
                (occurrence.access_path
                     ? access_path_material(*occurrence.access_path)
                     : std::string("no-access-path")) + '\0' +
                occurrence.member_abstract_object_id.value_or("no-object");
            occurrence.occurrence_id = stable_id(
                "predicate-occurrence", semantic_material);
            output_.occurrences.push_back(std::move(occurrence));
        }
    }

    ASTContext &context_;
    SourceManager &manager_;
    const CompilationCommand &command_;
    const std::vector<LogicalPathRoot> &identity_roots_;
    const SemanticIndex &semantic_index_;
    const std::vector<PredicateSelectorAccount> &accounts_;
    const PredicateOccurrenceOptions &options_;
    TuParseOutput &output_;
    std::map<TargetKey, std::vector<std::size_t>> targets_;
};

class OccurrenceConsumer final : public clang::ASTConsumer {
  public:
    OccurrenceConsumer(
        const CompilationCommand &command,
        const std::vector<LogicalPathRoot> &identity_roots,
        const SemanticIndex &semantic_index,
        const std::vector<PredicateSelectorAccount> &accounts,
        const std::vector<Request> &requests,
        const PredicateOccurrenceOptions &options, TuParseOutput &output)
        : command_(command), identity_roots_(identity_roots),
          semantic_index_(semantic_index), accounts_(accounts),
          requests_(requests), options_(options), output_(output) {}

    void HandleTranslationUnit(ASTContext &context) override {
        OccurrenceVisitor visitor(
            context, command_, identity_roots_, semantic_index_, accounts_,
            requests_, options_, output_);
        visitor.TraverseDecl(context.getTranslationUnitDecl());
    }

  private:
    const CompilationCommand &command_;
    const std::vector<LogicalPathRoot> &identity_roots_;
    const SemanticIndex &semantic_index_;
    const std::vector<PredicateSelectorAccount> &accounts_;
    const std::vector<Request> &requests_;
    const PredicateOccurrenceOptions &options_;
    TuParseOutput &output_;
};

class OccurrenceAction final : public clang::ASTFrontendAction {
  public:
    OccurrenceAction(
        const CompilationCommand &command,
        const std::vector<LogicalPathRoot> &identity_roots,
        const SemanticIndex &semantic_index,
        const std::vector<PredicateSelectorAccount> &accounts,
        const std::vector<Request> &requests,
        const PredicateOccurrenceOptions &options, TuParseOutput &output)
        : command_(command), identity_roots_(identity_roots),
          semantic_index_(semantic_index), accounts_(accounts),
          requests_(requests), options_(options), output_(output) {}

    std::unique_ptr<clang::ASTConsumer> CreateASTConsumer(
        clang::CompilerInstance &, llvm::StringRef) override {
        return std::make_unique<OccurrenceConsumer>(
            command_, identity_roots_, semantic_index_, accounts_, requests_,
            options_, output_);
    }

  private:
    const CompilationCommand &command_;
    const std::vector<LogicalPathRoot> &identity_roots_;
    const SemanticIndex &semantic_index_;
    const std::vector<PredicateSelectorAccount> &accounts_;
    const std::vector<Request> &requests_;
    const PredicateOccurrenceOptions &options_;
    TuParseOutput &output_;
};

class OccurrenceActionFactory final
    : public clang::tooling::FrontendActionFactory {
  public:
    OccurrenceActionFactory(
        const CompilationCommand &command,
        const std::vector<LogicalPathRoot> &identity_roots,
        const SemanticIndex &semantic_index,
        const std::vector<PredicateSelectorAccount> &accounts,
        const std::vector<Request> &requests,
        const PredicateOccurrenceOptions &options, TuParseOutput &output)
        : command_(command), identity_roots_(identity_roots),
          semantic_index_(semantic_index), accounts_(accounts),
          requests_(requests), options_(options), output_(output) {}

    std::unique_ptr<clang::FrontendAction> create() override {
        return std::make_unique<OccurrenceAction>(
            command_, identity_roots_, semantic_index_, accounts_, requests_,
            options_, output_);
    }

  private:
    const CompilationCommand &command_;
    const std::vector<LogicalPathRoot> &identity_roots_;
    const SemanticIndex &semantic_index_;
    const std::vector<PredicateSelectorAccount> &accounts_;
    const std::vector<Request> &requests_;
    const PredicateOccurrenceOptions &options_;
    TuParseOutput &output_;
};

std::string json_escape(std::string_view value) {
    std::ostringstream output;
    output << '"';
    for (const unsigned char byte : value) {
        switch (byte) {
        case '"':
            output << "\\\"";
            break;
        case '\\':
            output << "\\\\";
            break;
        case '\b':
            output << "\\b";
            break;
        case '\f':
            output << "\\f";
            break;
        case '\n':
            output << "\\n";
            break;
        case '\r':
            output << "\\r";
            break;
        case '\t':
            output << "\\t";
            break;
        default:
            if (byte < 0x20) {
                constexpr char digits[] = "0123456789abcdef";
                output << "\\u00" << digits[(byte >> 4U) & 0x0fU]
                       << digits[byte & 0x0fU];
            } else {
                output << static_cast<char>(byte);
            }
        }
    }
    output << '"';
    return output.str();
}

std::string json_strings(const std::vector<std::string> &values) {
    std::ostringstream output;
    output << '[';
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        output << json_escape(values[index]);
    }
    output << ']';
    return output.str();
}

std::string json_roles(const std::vector<ApRole> &roles) {
    std::ostringstream output;
    output << '[';
    for (std::size_t index = 0; index < roles.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        output << json_escape(role_name(roles[index]));
    }
    output << ']';
    return output.str();
}

const char *value_kind_name(ValueKind value) {
    switch (value) {
    case ValueKind::Boolean:
        return "bool";
    case ValueKind::Integer:
        return "integer";
    case ValueKind::Floating:
        return "floating";
    case ValueKind::Enumeration:
        return "enum";
    case ValueKind::BitVector:
        return "bitvector";
    case ValueKind::Timestamp:
        return "timestamp";
    case ValueKind::Duration:
        return "duration";
    case ValueKind::Pointer:
        return "pointer";
    case ValueKind::Record:
        return "record";
    case ValueKind::Array:
        return "array";
    case ValueKind::Unknown:
        return "unknown";
    }
    return "unknown";
}

std::string location_json(const SourceLocation &location) {
    std::ostringstream output;
    output << "{\"file\":" << json_escape(location.file)
           << ",\"line\":" << location.line
           << ",\"column\":" << location.column;
    if (location.end_line != 0) {
        output << ",\"end_line\":" << location.end_line;
    }
    if (location.end_column != 0) {
        output << ",\"end_column\":" << location.end_column;
    }
    output << ",\"location_kind\":"
           << json_escape(location.location_kind)
           << ",\"macro_stack\":" << json_strings(location.macro_stack)
           << '}';
    return output.str();
}

std::string value_type_json(const ValueType &type) {
    std::ostringstream output;
    output << "{\"kind\":" << json_escape(value_kind_name(type.kind))
           << ",\"canonical\":" << json_escape(type.canonical);
    if (type.bit_width) {
        output << ",\"bit_width\":" << *type.bit_width;
    }
    if (type.is_signed) {
        output << ",\"signed\":" << (*type.is_signed ? "true" : "false");
    }
    if (type.unit) {
        output << ",\"unit\":" << json_escape(*type.unit);
    }
    output << '}';
    return output.str();
}

std::string access_path_json(const std::optional<AccessPath> &path) {
    if (!path) {
        return "null";
    }
    return "{\"root_entity_id\":" + json_escape(path->root_entity_id) +
           ",\"dereference_depth\":" +
           std::to_string(path->dereference_depth) +
           ",\"fields\":" + json_strings(path->fields) +
           ",\"unknown_suffix\":" +
           (path->unknown_suffix ? "true" : "false") + '}';
}

std::string optional_json(const std::optional<std::string> &value) {
    return value ? json_escape(*value) : "null";
}

const char *gap_effect_name(GapEffect effect) {
    switch (effect) {
    case GapEffect::PrecisionLoss:
        return "precision_loss";
    case GapEffect::SoundnessRisk:
        return "soundness_risk";
    case GapEffect::StageFailure:
        return "stage_failure";
    }
    return "stage_failure";
}

std::string gap_json(const CoverageGap &gap) {
    std::ostringstream output;
    output << "{\"construct_id\":" << json_escape(gap.gap_id)
           << ",\"kind\":" << json_escape(gap.kind)
           << ",\"effect\":" << json_escape(gap_effect_name(gap.effect))
           << ",\"detail\":" << json_escape(gap.detail)
           << ",\"locations\":[";
    for (std::size_t index = 0; index < gap.locations.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        output << location_json(gap.locations[index]);
    }
    output << "],\"affected_ids\":" << json_strings(gap.affected_ids)
           << '}';
    return output.str();
}

bool occurrence_less(
    const PredicateOccurrence &left, const PredicateOccurrence &right) {
    return std::tie(
               left.ap_id, left.selector_id, left.translation_unit_id,
               left.spelling_location.file, left.spelling_location.line,
               left.spelling_location.column, left.expansion_location.file,
               left.expansion_location.line, left.expansion_location.column,
               left.occurrence_id) <
           std::tie(
               right.ap_id, right.selector_id, right.translation_unit_id,
               right.spelling_location.file, right.spelling_location.line,
               right.spelling_location.column, right.expansion_location.file,
               right.expansion_location.line, right.expansion_location.column,
               right.occurrence_id);
}

}  // namespace

const char *to_string(PredicateOccurrenceKind value) {
    switch (value) {
    case PredicateOccurrenceKind::DeclRef:
        return "decl_ref";
    case PredicateOccurrenceKind::MemberExpr:
        return "member_expr";
    case PredicateOccurrenceKind::Unknown:
        return "unknown";
    }
    return "unknown";
}

const char *to_string(PredicateOccurrenceResolution value) {
    switch (value) {
    case PredicateOccurrenceResolution::Exact:
        return "EXACT";
    case PredicateOccurrenceResolution::Ambiguous:
        return "AMBIGUOUS";
    case PredicateOccurrenceResolution::Unknown:
        return "UNKNOWN";
    }
    return "UNKNOWN";
}

PredicateOccurrenceBindings bind_predicate_occurrences(
    const CompilationPlan &plan, const TypedPropertyIr &property,
    const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256,
    const PredicateOccurrenceOptions &options) {
    PredicateOccurrenceBindings result;
    result.schema_version = std::string(kSchemaVersion);
    result.property_ir_sha256 = property.artifact_sha256;
    result.semantic_index_sha256 = semantic_index_sha256;
    result.canonical_compilation_database_sha256 =
        plan.canonical_compilation_database_sha256;
    result.path_map_sha256 = plan.path_map_sha256;
    result.options = options;
    std::ostringstream artifact_material;
    artifact_material << kSchemaVersion << '\0' << property.artifact_sha256
                      << '\0' << semantic_index_sha256 << '\0'
                      << plan.canonical_compilation_database_sha256 << '\0'
                      << plan.path_map_sha256 << '\0'
                      << options.maximum_translation_units << '\0'
                      << options.maximum_occurrences << '\0'
                      << options.retain_macro_stack;
    result.artifact_id = stable_id(
        "predicate-occurrence-bindings", artifact_material.str());

    if (plan.status == StageStatus::Failed ||
        semantic_index.status == StageStatus::Failed ||
        plan.commands.empty() || options.maximum_translation_units == 0 ||
        options.maximum_occurrences == 0 ||
        !is_digest(property.artifact_sha256) ||
        !is_digest(semantic_index_sha256) ||
        plan.canonical_compilation_database_sha256 !=
            semantic_index.canonical_compilation_database_sha256 ||
        plan.path_map_sha256 != semantic_index.path_map_sha256) {
        result.status = StageStatus::Failed;
        result.diagnostics.push_back(
            "predicate occurrence binding requires valid digests, nonzero resource guards, and a matching nonfailed plan/index");
        return result;
    }

    std::map<std::string, const Selector *> selectors;
    for (const Selector &selector : property.selectors) {
        selectors.emplace(selector.selector_id, &selector);
    }

    for (const AtomicProposition &ap : property.atomic_propositions) {
        std::map<std::string, PredicateReferenceEvidence> references;
        collect_predicate_references(ap.predicate, "predicate", references);
        for (auto &[selector_id, evidence] : references) {
            sort_unique(evidence.paths);
            const auto selector = selectors.find(selector_id);
            if (selector == selectors.end() ||
                selector->second->kind != SelectorKind::SourceLocation ||
                !selector->second->location) {
                continue;
            }
            PredicateSelectorAccount account;
            account.ap_id = ap.ap_id;
            account.selector_id = selector_id;
            account.roles = roles_for_selector(ap, selector_id);
            account.predicate_paths = std::move(evidence.paths);
            const ExpectedTypeEvidence type_evidence =
                expected_type_evidence(*selector->second, evidence);
            account.expected_value_type = type_evidence.value_type;
            account.uncertainty_reasons =
                type_evidence.uncertainty_reasons;
            account.requested_location = *selector->second->location;
            result.selector_accounts.push_back(std::move(account));
        }
    }
    std::sort(
        result.selector_accounts.begin(), result.selector_accounts.end(),
        [](const PredicateSelectorAccount &left,
           const PredicateSelectorAccount &right) {
            return std::tie(left.ap_id, left.selector_id) <
                   std::tie(right.ap_id, right.selector_id);
        });

    std::map<std::string, const TranslationUnitRecord *> translation_units;
    for (const TranslationUnitRecord &tu : semantic_index.translation_units) {
        translation_units.emplace(tu.translation_unit_id, &tu);
    }
    std::map<std::string, const CompilationCommand *> commands;
    for (const CompilationCommand &command : plan.commands) {
        commands.emplace(command.translation_unit_id, &command);
    }

    std::map<std::string, std::vector<Request>> requests_by_tu;
    for (std::size_t account_index = 0;
         account_index < result.selector_accounts.size(); ++account_index) {
        PredicateSelectorAccount &account =
            result.selector_accounts[account_index];
        if (account.roles.empty()) {
            account.uncertainty_reasons.push_back(
                "selector_has_no_structural_ap_role");
        }
        if (account.requested_location.location_kind != "spelling" &&
            account.requested_location.location_kind != "expansion") {
            account.uncertainty_reasons.push_back(
                "unsupported_selector_location_kind");
            continue;
        }

        std::vector<const InputFileDigest *> matches;
        for (const InputFileDigest &input : semantic_index.input_files) {
            if (path_suffix_match(
                    input.logical_path, account.requested_location.file)) {
                matches.push_back(&input);
            }
        }
        std::sort(
            matches.begin(), matches.end(),
            [](const InputFileDigest *left, const InputFileDigest *right) {
                return std::tie(left->logical_path, left->input_file_id) <
                       std::tie(right->logical_path, right->input_file_id);
            });
        std::vector<std::string> logical_matches;
        for (const InputFileDigest *input : matches) {
            append_unique(logical_matches, input->logical_path);
        }
        if (logical_matches.size() != 1) {
            account.uncertainty_reasons.push_back(
                logical_matches.empty() ? "selector_source_file_unmatched"
                                        : "selector_source_file_ambiguous");
            continue;
        }
        const std::string target_file = logical_matches.front();
        std::set<std::string> matched_input_ids;
        for (const InputFileDigest *input : matches) {
            if (input->logical_path == target_file) {
                matched_input_ids.insert(input->input_file_id);
            }
        }
        for (const auto &[tu_id, tu] : translation_units) {
            if (std::any_of(
                    tu->input_file_ids.begin(), tu->input_file_ids.end(),
                    [&](const std::string &input_id) {
                        return matched_input_ids.contains(input_id);
                    })) {
                account.eligible_translation_unit_ids.push_back(tu_id);
            }
        }
        sort_unique(account.eligible_translation_unit_ids);
        if (account.eligible_translation_unit_ids.empty()) {
            account.uncertainty_reasons.push_back(
                "selector_source_has_no_translation_unit");
            continue;
        }
        for (const std::string &tu_id : account.eligible_translation_unit_ids) {
            if (!commands.contains(tu_id)) {
                account.uncertainty_reasons.push_back(
                    "eligible_translation_unit_missing_command");
                continue;
            }
            requests_by_tu[tu_id].push_back(Request{account_index, target_file});
        }
    }

    result.eligible_translation_units = requests_by_tu.size();
    std::set<std::string> admitted_tus;
    for (const auto &[tu_id, requests] : requests_by_tu) {
        static_cast<void>(requests);
        if (admitted_tus.size() >= options.maximum_translation_units) {
            break;
        }
        admitted_tus.insert(tu_id);
    }
    result.parsed_translation_units = admitted_tus.size();
    result.skipped_translation_units =
        result.eligible_translation_units - result.parsed_translation_units;
    if (result.skipped_translation_units != 0) {
        result.candidate_accounting_complete = false;
    }

    for (const auto &[tu_id, requests] : requests_by_tu) {
        if (!admitted_tus.contains(tu_id)) {
            for (const Request &request : requests) {
                append_unique(
                    result.selector_accounts[request.account_index]
                        .uncertainty_reasons,
                    std::string("translation_unit_resource_guard_reached"));
            }
            continue;
        }
        const CompilationCommand &command = *commands.at(tu_id);
        for (const Request &request : requests) {
            append_unique(
                result.selector_accounts[request.account_index]
                    .parsed_translation_unit_ids,
                tu_id);
        }
        TuParseOutput parsed;
        SingleCommandDatabase database(command);
        clang::tooling::ClangTool tool(
            database, std::vector<std::string>{command.source_file});
        PredicateOccurrenceOptions tu_options = options;
        tu_options.maximum_occurrences =
            result.occurrences.size() >= options.maximum_occurrences
                ? 0
                : options.maximum_occurrences - result.occurrences.size();
        OccurrenceActionFactory factory(
            command, plan.identity_roots, semantic_index,
            result.selector_accounts, requests, tu_options, parsed);
        const int exit_code = tool.run(&factory);
        if (exit_code != 0) {
            parsed.diagnostics.push_back(
                tu_id + ": Clang occurrence parse failed with exit code " +
                std::to_string(exit_code));
            for (const Request &request : requests) {
                append_unique(
                    result.selector_accounts[request.account_index]
                        .uncertainty_reasons,
                    std::string("clang_occurrence_parse_failed"));
            }
            result.coverage_gaps.push_back(make_gap(
                "clang_occurrence_parse_failed", GapEffect::SoundnessRisk,
                "Targeted translation unit could not be reparsed for exact predicate occurrences",
                {tu_id}));
        }
        result.occurrences.insert(
            result.occurrences.end(),
            std::make_move_iterator(parsed.occurrences.begin()),
            std::make_move_iterator(parsed.occurrences.end()));
        for (const auto &[account_index, reason] : parsed.account_reasons) {
            append_unique(
                result.selector_accounts.at(account_index).uncertainty_reasons,
                reason);
            result.candidate_accounting_complete = false;
        }
        result.diagnostics.insert(
            result.diagnostics.end(), parsed.diagnostics.begin(),
            parsed.diagnostics.end());
    }

    std::sort(result.occurrences.begin(), result.occurrences.end(), occurrence_less);
    result.occurrences.erase(
        std::unique(
            result.occurrences.begin(), result.occurrences.end(),
            [](const PredicateOccurrence &left,
               const PredicateOccurrence &right) {
                return left.occurrence_id == right.occurrence_id;
            }),
        result.occurrences.end());
    result.observed_occurrences = result.occurrences.size();

    for (PredicateSelectorAccount &account : result.selector_accounts) {
        for (const PredicateOccurrence &occurrence : result.occurrences) {
            if (occurrence.ap_id == account.ap_id &&
                occurrence.selector_id == account.selector_id) {
                account.occurrence_ids.push_back(occurrence.occurrence_id);
            }
        }
        sort_unique(account.eligible_translation_unit_ids);
        sort_unique(account.parsed_translation_unit_ids);
        sort_unique(account.occurrence_ids);
        sort_unique(account.uncertainty_reasons);
        if (account.occurrence_ids.empty()) {
            append_unique(
                account.uncertainty_reasons,
                std::string("predicate_occurrence_unmatched"));
        } else if (account.occurrence_ids.size() != 1) {
            append_unique(
                account.uncertainty_reasons,
                std::string("multiple_predicate_occurrence_candidates"));
        }
        bool exact_occurrence = account.occurrence_ids.size() == 1;
        for (PredicateOccurrence &occurrence : result.occurrences) {
            if (occurrence.ap_id != account.ap_id ||
                occurrence.selector_id != account.selector_id) {
                continue;
            }
            if (!exact_occurrence) {
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("multiple_predicate_occurrence_candidates"));
                occurrence.certainty = Certainty::Unknown;
                occurrence.resolution = PredicateOccurrenceResolution::Unknown;
            }
            for (const std::string &reason : occurrence.uncertainty_reasons) {
                append_unique(account.uncertainty_reasons, reason);
            }
            exact_occurrence = exact_occurrence &&
                               occurrence.resolution ==
                                   PredicateOccurrenceResolution::Exact;
        }
        account.resolution =
            exact_occurrence && account.uncertainty_reasons.empty()
                ? PredicateOccurrenceResolution::Exact
                : PredicateOccurrenceResolution::Unknown;
        if (account.resolution == PredicateOccurrenceResolution::Unknown) {
            for (PredicateOccurrence &occurrence : result.occurrences) {
                if (occurrence.ap_id != account.ap_id ||
                    occurrence.selector_id != account.selector_id) {
                    continue;
                }
                append_unique(
                    occurrence.uncertainty_reasons,
                    std::string("selector_account_not_exact"));
                occurrence.certainty = Certainty::Unknown;
                occurrence.resolution =
                    PredicateOccurrenceResolution::Unknown;
            }
            result.coverage_gaps.push_back(make_gap(
                "predicate_occurrence_unknown", GapEffect::PrecisionLoss,
                "A referenced predicate selector did not resolve to one non-macro, non-alias AST occurrence and one M4 semantic node",
                {account.ap_id, account.selector_id},
                account.requested_location));
        }
    }
    for (PredicateOccurrence &occurrence : result.occurrences) {
        sort_unique(occurrence.predicate_paths);
        sort_unique(occurrence.semantic_node_ids);
        sort_unique(occurrence.uncertainty_reasons);
    }
    std::sort(result.occurrences.begin(), result.occurrences.end(), occurrence_less);
    std::sort(
        result.coverage_gaps.begin(), result.coverage_gaps.end(),
        [](const CoverageGap &left, const CoverageGap &right) {
            return left.gap_id < right.gap_id;
        });
    result.coverage_gaps.erase(
        std::unique(
            result.coverage_gaps.begin(), result.coverage_gaps.end(),
            [](const CoverageGap &left, const CoverageGap &right) {
                return left.gap_id == right.gap_id;
            }),
        result.coverage_gaps.end());
    sort_unique(result.diagnostics);

    const bool all_exact = std::all_of(
        result.selector_accounts.begin(), result.selector_accounts.end(),
        [](const PredicateSelectorAccount &account) {
            return account.resolution == PredicateOccurrenceResolution::Exact;
        });
    result.status = all_exact && result.candidate_accounting_complete
                        ? StageStatus::Complete
                        : StageStatus::ConservativeIncomplete;

    const std::vector<std::string> errors =
        validate_predicate_occurrence_bindings(
            result, plan, property, semantic_index, semantic_index_sha256);
    if (!errors.empty()) {
        result.status = StageStatus::Failed;
        result.diagnostics.insert(
            result.diagnostics.end(), errors.begin(), errors.end());
        sort_unique(result.diagnostics);
    }
    return result;
}

std::vector<std::string> validate_predicate_occurrence_bindings(
    const PredicateOccurrenceBindings &bindings, const CompilationPlan &plan,
    const TypedPropertyIr &property, const SemanticIndex &semantic_index,
    const std::string &semantic_index_sha256) {
    std::vector<std::string> errors;
    if (bindings.schema_version != kSchemaVersion) {
        errors.push_back("unsupported predicate occurrence binding schema version");
    }
    std::ostringstream artifact_material;
    artifact_material << kSchemaVersion << '\0' << property.artifact_sha256
                      << '\0' << semantic_index_sha256 << '\0'
                      << plan.canonical_compilation_database_sha256 << '\0'
                      << plan.path_map_sha256 << '\0'
                      << bindings.options.maximum_translation_units << '\0'
                      << bindings.options.maximum_occurrences << '\0'
                      << bindings.options.retain_macro_stack;
    if (bindings.artifact_id != stable_id(
            "predicate-occurrence-bindings", artifact_material.str())) {
        errors.push_back("predicate occurrence artifact ID is not input-bound");
    }
    if (!bindings.m4_index_immutable) {
        errors.push_back("predicate occurrence binding must preserve the M4 index");
    }
    if (bindings.property_ir_sha256 != property.artifact_sha256 ||
        bindings.semantic_index_sha256 != semantic_index_sha256 ||
        bindings.canonical_compilation_database_sha256 !=
            plan.canonical_compilation_database_sha256 ||
        bindings.path_map_sha256 != plan.path_map_sha256 ||
        bindings.canonical_compilation_database_sha256 !=
            semantic_index.canonical_compilation_database_sha256 ||
        bindings.path_map_sha256 != semantic_index.path_map_sha256) {
        errors.push_back("predicate occurrence input digest closure mismatch");
    }
    if (!is_digest(bindings.property_ir_sha256) ||
        !is_digest(bindings.semantic_index_sha256) ||
        !is_digest(bindings.canonical_compilation_database_sha256) ||
        !is_digest(bindings.path_map_sha256)) {
        errors.push_back("predicate occurrence artifact contains an invalid digest");
    }
    if (bindings.options.maximum_translation_units == 0 ||
        bindings.options.maximum_occurrences == 0) {
        errors.push_back("predicate occurrence resource guards must be nonzero");
    }
    if (bindings.parsed_translation_units + bindings.skipped_translation_units !=
        bindings.eligible_translation_units) {
        errors.push_back("predicate occurrence translation-unit counters do not close");
    }
    if (bindings.observed_occurrences != bindings.occurrences.size() ||
        bindings.occurrences.size() > bindings.options.maximum_occurrences) {
        errors.push_back("predicate occurrence candidate counter is invalid");
    }
    if (bindings.candidate_accounting_complete &&
        bindings.skipped_translation_units != 0) {
        errors.push_back("complete candidate accounting cannot skip translation units");
    }

    std::set<std::string> occurrence_ids;
    std::map<std::string, const PredicateOccurrence *> occurrence_by_id;
    std::map<std::pair<std::string, std::string>, std::vector<std::string>>
        occurrence_ids_by_account;
    std::set<std::string> entity_ids;
    std::set<std::string> semantic_node_ids;
    std::set<std::string> abstract_object_ids;
    std::set<std::string> translation_unit_ids;
    for (const EntityRef &entity : semantic_index.entities) {
        entity_ids.insert(entity.entity_id);
    }
    for (const SemanticNode &node : semantic_index.nodes) {
        semantic_node_ids.insert(node.node_id);
    }
    for (const AbstractObject &object : semantic_index.abstract_objects) {
        abstract_object_ids.insert(object.object_id);
    }
    for (const TranslationUnitRecord &tu : semantic_index.translation_units) {
        translation_unit_ids.insert(tu.translation_unit_id);
    }
    std::map<std::pair<std::string, std::string>, const PredicateSelectorAccount *>
        accounts;
    std::map<std::pair<std::string, std::string>, ExpectedTypeEvidence>
        expected_types;
    std::map<std::string, const Selector *> property_selectors;
    for (const Selector &selector : property.selectors) {
        property_selectors.emplace(selector.selector_id, &selector);
    }
    for (const AtomicProposition &ap : property.atomic_propositions) {
        std::map<std::string, PredicateReferenceEvidence> references;
        collect_predicate_references(ap.predicate, "predicate", references);
        for (const auto &[selector_id, evidence] : references) {
            const auto selector = property_selectors.find(selector_id);
            if (selector == property_selectors.end() ||
                selector->second->kind != SelectorKind::SourceLocation ||
                !selector->second->location) {
                continue;
            }
            expected_types.emplace(
                std::make_pair(ap.ap_id, selector_id),
                expected_type_evidence(*selector->second, evidence));
        }
    }
    for (const PredicateSelectorAccount &account : bindings.selector_accounts) {
        const auto key = std::make_pair(account.ap_id, account.selector_id);
        if (!accounts.emplace(key, &account).second) {
            errors.push_back("duplicate predicate selector account");
        }
        const auto expected = expected_types.find(key);
        if (expected == expected_types.end()) {
            errors.push_back(
                "predicate selector account is not backed by a source-location predicate reference");
        } else {
            if (!(account.expected_value_type == expected->second.value_type)) {
                errors.push_back(
                    "predicate selector account expected type differs from Property IR evidence");
            }
            if (account.resolution == PredicateOccurrenceResolution::Exact &&
                !expected->second.uncertainty_reasons.empty()) {
                errors.push_back(
                    "EXACT selector account has an unclosed Property IR type contract");
            }
        }
        if (account.resolution == PredicateOccurrenceResolution::Exact &&
            (account.occurrence_ids.size() != 1 ||
             !account.uncertainty_reasons.empty())) {
            errors.push_back("EXACT selector account has incomplete evidence");
        }
        if (account.resolution != PredicateOccurrenceResolution::Exact &&
            account.uncertainty_reasons.empty()) {
            errors.push_back("UNKNOWN selector account lacks a reason");
        }
        if (!std::includes(
                account.eligible_translation_unit_ids.begin(),
                account.eligible_translation_unit_ids.end(),
                account.parsed_translation_unit_ids.begin(),
                account.parsed_translation_unit_ids.end())) {
            errors.push_back("parsed translation unit is not selector-eligible");
        }
        for (const std::string &tu_id : account.eligible_translation_unit_ids) {
            if (!translation_unit_ids.contains(tu_id)) {
                errors.push_back(
                    "selector account references an absent translation unit");
            }
        }
    }
    for (const auto &[key, evidence] : expected_types) {
        (void)evidence;
        if (!accounts.contains(key)) {
            errors.push_back(
                "source-location predicate reference has no selector account");
        }
    }
    for (const PredicateOccurrence &occurrence : bindings.occurrences) {
        if (!occurrence_ids.insert(occurrence.occurrence_id).second) {
            errors.push_back("duplicate predicate occurrence ID");
        } else {
            occurrence_by_id.emplace(occurrence.occurrence_id, &occurrence);
        }
        occurrence_ids_by_account[
            std::make_pair(occurrence.ap_id, occurrence.selector_id)]
            .push_back(occurrence.occurrence_id);
        const auto account = accounts.find(
            std::make_pair(occurrence.ap_id, occurrence.selector_id));
        if (account == accounts.end()) {
            errors.push_back("predicate occurrence has no selector account");
        } else if (
            occurrence.resolution == PredicateOccurrenceResolution::Exact &&
            account->second->resolution !=
                PredicateOccurrenceResolution::Exact) {
            errors.push_back(
                "EXACT predicate occurrence belongs to a non-EXACT selector account");
        } else if (
            occurrence.resolution == PredicateOccurrenceResolution::Exact &&
            !equivalent_value_type(
                account->second->expected_value_type,
                occurrence.value_type)) {
            errors.push_back(
                "EXACT predicate occurrence violates its expected value type");
        }
        if (!translation_unit_ids.contains(occurrence.translation_unit_id)) {
            errors.push_back(
                "predicate occurrence references an absent translation unit");
        }
        if (occurrence.referenced_entity_id &&
            !entity_ids.contains(*occurrence.referenced_entity_id)) {
            errors.push_back(
                "predicate occurrence references an absent semantic entity");
        }
        for (const std::string &node_id : occurrence.semantic_node_ids) {
            if (!semantic_node_ids.contains(node_id)) {
                errors.push_back(
                    "predicate occurrence references an absent semantic node");
            }
        }
        if (occurrence.resolution == PredicateOccurrenceResolution::Exact &&
            (occurrence.certainty != Certainty::Must ||
             !occurrence.uncertainty_reasons.empty() ||
             !occurrence.referenced_usr ||
             !occurrence.referenced_entity_id ||
             occurrence.semantic_node_ids.size() != 1)) {
            errors.push_back("EXACT predicate occurrence has incomplete identity evidence");
        }
        if (occurrence.resolution != PredicateOccurrenceResolution::Exact &&
            occurrence.uncertainty_reasons.empty()) {
            errors.push_back("UNKNOWN predicate occurrence lacks a reason");
        }
        if (occurrence.kind == PredicateOccurrenceKind::MemberExpr &&
            occurrence.resolution == PredicateOccurrenceResolution::Exact &&
            (!occurrence.access_path || !occurrence.member_base_entity_id ||
             !occurrence.member_abstract_object_id)) {
            errors.push_back(
                "EXACT MemberExpr lacks a proven base/object/access path");
        }
        if (occurrence.member_base_entity_id &&
            (!entity_ids.contains(*occurrence.member_base_entity_id) ||
             !occurrence.access_path ||
             occurrence.access_path->root_entity_id !=
                 *occurrence.member_base_entity_id)) {
            errors.push_back(
                "MemberExpr base entity is absent or disagrees with its access path");
        }
        if (occurrence.member_abstract_object_id &&
            !abstract_object_ids.contains(
                *occurrence.member_abstract_object_id)) {
            errors.push_back(
                "MemberExpr references an absent abstract object");
        }
    }
    for (const PredicateSelectorAccount &account : bindings.selector_accounts) {
        const auto key = std::make_pair(account.ap_id, account.selector_id);
        std::vector<std::string> observed = occurrence_ids_by_account[key];
        std::vector<std::string> declared = account.occurrence_ids;
        sort_unique(observed);
        sort_unique(declared);
        if (observed != declared) {
            errors.push_back(
                "selector account occurrence ledger does not match its AP/selector occurrences");
        }
        for (const std::string &occurrence_id : account.occurrence_ids) {
            const auto occurrence = occurrence_by_id.find(occurrence_id);
            if (occurrence == occurrence_by_id.end()) {
                errors.push_back("selector account references an absent occurrence");
            } else if (
                occurrence->second->ap_id != account.ap_id ||
                occurrence->second->selector_id != account.selector_id) {
                errors.push_back(
                    "selector account references an occurrence owned by another AP/selector");
            }
        }
        if (account.resolution == PredicateOccurrenceResolution::Exact &&
            (account.occurrence_ids.size() != 1 ||
             !occurrence_by_id.contains(account.occurrence_ids.front()) ||
             occurrence_by_id.at(account.occurrence_ids.front())->resolution !=
                 PredicateOccurrenceResolution::Exact)) {
            errors.push_back(
                "EXACT selector account does not close over one EXACT occurrence");
        }
    }
    return errors;
}

std::string canonical_predicate_occurrence_bindings_json(
    const PredicateOccurrenceBindings &bindings) {
    std::ostringstream output;
    output << "{\"schema_version\":" << json_escape(bindings.schema_version)
           << ",\"artifact_id\":" << json_escape(bindings.artifact_id)
           << ",\"property_ir_sha256\":"
           << json_escape(bindings.property_ir_sha256)
           << ",\"semantic_index_sha256\":"
           << json_escape(bindings.semantic_index_sha256)
           << ",\"canonical_compilation_database_sha256\":"
           << json_escape(bindings.canonical_compilation_database_sha256)
           << ",\"path_map_sha256\":" << json_escape(bindings.path_map_sha256)
           << ",\"m4_index_immutable\":"
           << (bindings.m4_index_immutable ? "true" : "false")
           << ",\"candidate_accounting_complete\":"
           << (bindings.candidate_accounting_complete ? "true" : "false")
           << ",\"options\":{\"maximum_translation_units\":"
           << bindings.options.maximum_translation_units
           << ",\"maximum_occurrences\":"
           << bindings.options.maximum_occurrences
           << ",\"retain_macro_stack\":"
           << (bindings.options.retain_macro_stack ? "true" : "false")
           << "},\"eligible_translation_units\":"
           << bindings.eligible_translation_units
           << ",\"parsed_translation_units\":"
           << bindings.parsed_translation_units
           << ",\"skipped_translation_units\":"
           << bindings.skipped_translation_units
           << ",\"observed_occurrences\":"
           << bindings.observed_occurrences
           << ",\"status\":" << json_escape(to_string(bindings.status))
           << ",\"selector_accounts\":[";
    for (std::size_t index = 0; index < bindings.selector_accounts.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        const PredicateSelectorAccount &account =
            bindings.selector_accounts[index];
        output << "{\"ap_id\":" << json_escape(account.ap_id)
               << ",\"selector_id\":" << json_escape(account.selector_id)
               << ",\"roles\":" << json_roles(account.roles)
               << ",\"predicate_paths\":"
               << json_strings(account.predicate_paths)
               << ",\"expected_value_type\":"
               << value_type_json(account.expected_value_type)
               << ",\"requested_location\":"
               << location_json(account.requested_location)
               << ",\"eligible_translation_unit_ids\":"
               << json_strings(account.eligible_translation_unit_ids)
               << ",\"parsed_translation_unit_ids\":"
               << json_strings(account.parsed_translation_unit_ids)
               << ",\"occurrence_ids\":"
               << json_strings(account.occurrence_ids)
               << ",\"resolution\":"
               << json_escape(to_string(account.resolution))
               << ",\"uncertainty_reasons\":"
               << json_strings(account.uncertainty_reasons) << '}';
    }
    output << "],\"occurrences\":[";
    for (std::size_t index = 0; index < bindings.occurrences.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        const PredicateOccurrence &occurrence = bindings.occurrences[index];
        output << "{\"occurrence_id\":"
               << json_escape(occurrence.occurrence_id)
               << ",\"ap_id\":" << json_escape(occurrence.ap_id)
               << ",\"selector_id\":" << json_escape(occurrence.selector_id)
               << ",\"roles\":" << json_roles(occurrence.roles)
               << ",\"predicate_paths\":"
               << json_strings(occurrence.predicate_paths)
               << ",\"translation_unit_id\":"
               << json_escape(occurrence.translation_unit_id)
               << ",\"kind\":" << json_escape(to_string(occurrence.kind))
               << ",\"spelling_location\":"
               << location_json(occurrence.spelling_location)
               << ",\"expansion_location\":"
               << location_json(occurrence.expansion_location)
               << ",\"referenced_usr\":"
               << optional_json(occurrence.referenced_usr)
               << ",\"referenced_entity_id\":"
               << optional_json(occurrence.referenced_entity_id)
               << ",\"semantic_node_ids\":"
               << json_strings(occurrence.semantic_node_ids)
               << ",\"value_type\":"
               << value_type_json(occurrence.value_type)
               << ",\"access_path\":"
               << access_path_json(occurrence.access_path)
               << ",\"member_base_entity_id\":"
               << optional_json(occurrence.member_base_entity_id)
               << ",\"member_abstract_object_id\":"
               << optional_json(occurrence.member_abstract_object_id)
               << ",\"certainty\":" << json_escape(to_string(occurrence.certainty))
               << ",\"resolution\":"
               << json_escape(to_string(occurrence.resolution))
               << ",\"uncertainty_reasons\":"
               << json_strings(occurrence.uncertainty_reasons) << '}';
    }
    output << "],\"coverage_gaps\":[";
    for (std::size_t index = 0; index < bindings.coverage_gaps.size(); ++index) {
        if (index != 0) {
            output << ',';
        }
        output << gap_json(bindings.coverage_gaps[index]);
    }
    output << "],\"diagnostics\":" << json_strings(bindings.diagnostics)
           << '}';
    return output.str();
}

}  // namespace rift::core
