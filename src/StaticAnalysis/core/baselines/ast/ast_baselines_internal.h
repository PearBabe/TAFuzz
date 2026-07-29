#ifndef RIFT_BASELINES_AST_AST_BASELINES_INTERNAL_H
#define RIFT_BASELINES_AST_AST_BASELINES_INTERNAL_H

#include "rift/baselines/ast/ast_baselines.h"

#include <clang/Frontend/ASTUnit.h>

namespace rift::baselines::ast::detail {

AnalysisResult analyze_moonshine(
    const CaseInput &input, clang::ASTUnit &unit);
AnalysisResult analyze_plain_pdg(
    const CaseInput &input, clang::ASTUnit &unit);

}  // namespace rift::baselines::ast::detail

#endif
