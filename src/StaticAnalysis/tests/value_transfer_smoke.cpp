#include "rift/core/production.h"
#include "rift/core/value_transfer.h"

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unistd.h>

namespace {

using namespace rift::core;

void require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void write_file(const std::filesystem::path &path, std::string_view contents) {
    std::ofstream output(path, std::ios::binary);
    require(output.good(), "could not create neutral fixture");
    output << contents;
    require(output.good(), "could not write neutral fixture");
}

CompilationCommand command_for(
    const std::filesystem::path &directory,
    const std::filesystem::path &source,
    const std::vector<LogicalPathRoot> &roots) {
    CompilationCommand command;
    command.working_directory = directory.string();
    command.source_file = source.string();
    command.arguments = {
        "clang++-18", "-std=c++20", "-fsyntax-only", source.string()};
    command.logical_working_directory =
        logical_identity_path(roots, directory).value();
    command.logical_source_file = logical_identity_path(roots, source).value();
    command.raw_command_sha256 = sha256_hex(
        command.working_directory + '\0' + command.source_file);
    command.command_sha256 = sha256_hex(
        command.logical_working_directory + '\0' +
        command.logical_source_file);
    command.translation_unit_id = stable_id(
        "tu", command.logical_source_file + '\0' + command.command_sha256);
    return command;
}

CompilationPlan plan_for(
    const std::filesystem::path &directory,
    const std::filesystem::path &source) {
    CompilationPlan plan;
    plan.compilation_database_path =
        (directory / "compile_commands.json").string();
    plan.compilation_database_sha256 = sha256_hex("physical-neutral-db");
    plan.canonical_compilation_database_sha256 =
        sha256_hex("canonical-neutral-db");
    plan.identity_roots = {{"source", directory}};
    plan.path_map_sha256 = identity_path_map_sha256(plan.identity_roots);
    plan.source_identity_root =
        std::string(kIdentityScheme) + ':' + plan.path_map_sha256;
    plan.status = StageStatus::Complete;
    plan.commands = {command_for(directory, source, plan.identity_roots)};
    return plan;
}

std::string node_for_entity_name(
    const SemanticIndex &index, std::string_view name) {
    std::optional<std::string> entity_id;
    for (const EntityRef &entity : index.entities) {
        if (entity.qualified_signature &&
            entity.qualified_signature->find(
                std::string(name) + ':') != std::string::npos) {
            require(!entity_id, "neutral fixture entity suffix is ambiguous");
            entity_id = entity.entity_id;
        }
    }
    require(
        entity_id.has_value(),
        "neutral fixture entity was not indexed: " + std::string(name));
    const auto node = std::find_if(
        index.nodes.begin(), index.nodes.end(), [&](const SemanticNode &candidate) {
            return candidate.entity_id == *entity_id;
        });
    require(node != index.nodes.end(), "neutral fixture node was not indexed");
    return node->node_id;
}

const TypedValueTransfer &transfer_to(
    const SemanticValueTransferIndex &index, const std::string &node_id) {
    const auto found = std::find_if(
        index.transfers.begin(), index.transfers.end(),
        [&](const TypedValueTransfer &candidate) {
            return candidate.output_node_id == node_id;
        });
    require(found != index.transfers.end(), "missing typed value transfer");
    return *found;
}

const TransferExpression &expression(
    const std::vector<TransferExpression> &expressions,
    const std::string &expression_id) {
    const auto found = std::find_if(
        expressions.begin(), expressions.end(),
        [&](const TransferExpression &candidate) {
            return candidate.expression_id == expression_id;
        });
    require(found != expressions.end(), "missing transfer expression");
    return *found;
}

bool contains_kind(
    const std::vector<TransferExpression> &expressions,
    const std::string &root, TransferExprKind wanted) {
    std::map<std::string, bool> visited;
    std::vector<std::string> worklist{root};
    while (!worklist.empty()) {
        const std::string current = worklist.back();
        worklist.pop_back();
        if (visited[current]) {
            continue;
        }
        visited[current] = true;
        const TransferExpression &node = expression(expressions, current);
        if (node.kind == wanted) {
            return true;
        }
        worklist.insert(
            worklist.end(), node.operand_expression_ids.begin(),
            node.operand_expression_ids.end());
    }
    return false;
}

const CallSiteSummary &indirect_callsite(const SemanticIndex &index) {
    const auto found = std::find_if(
        index.callsites.begin(), index.callsites.end(),
        [](const CallSiteSummary &candidate) { return !candidate.direct; });
    require(found != index.callsites.end(), "indirect callsite was not indexed");
    return *found;
}

std::vector<std::string> expression_ids(
    const std::vector<TransferExpression> &expressions) {
    std::vector<std::string> result;
    for (const TransferExpression &expression : expressions) {
        result.push_back(expression.expression_id);
    }
    return result;
}

std::vector<std::string> transfer_ids(
    const std::vector<TypedValueTransfer> &transfers) {
    std::vector<std::string> result;
    for (const TypedValueTransfer &transfer : transfers) {
        result.push_back(transfer.transfer_id);
    }
    return result;
}

}  // namespace

int main() {
    namespace fs = std::filesystem;
    const fs::path fixture = fs::temp_directory_path() /
                             ("rift-value-transfer-" +
                              std::to_string(static_cast<long long>(::getpid())));
    std::error_code error;
    fs::remove_all(fixture, error);
    fs::create_directories(fixture);
    try {
        const fs::path source = fixture / "neutral.cpp";
        write_file(
            source,
            "int passthrough(int item) { return item; }\n"
            "int invoke(int item) { return passthrough(item); }\n"
            "int invoke_indirect(int (*operation)(int), int item) { return operation(item); }\n"
            "bool evaluate(int sample, int boundary, bool enabled) {\n"
            "  int copied = sample;\n"
            "  long widened = copied;\n"
            "  int shifted = copied * 3 + 2;\n"
            "  bool compared = shifted >= boundary;\n"
            "  bool combined = compared && !enabled;\n"
            "  int selected = combined ? shifted : boundary;\n"
            "  int nonlinear = sample * boundary;\n"
            "  return selected > nonlinear;\n"
            "}\n");

        const CompilationPlan plan = plan_for(fixture, source);
        const IndexBuildArtifacts built =
            build_semantic_index_with_value_transfers(plan);
        require(
            built.index.status != StageStatus::Failed,
            "neutral fixture semantic index succeeds");
        require(
            built.value_transfers.property_independent,
            "typed sidecar is property independent");
        require(
            validate_semantic_value_transfers(
                built.value_transfers, built.index).empty(),
            "semantic typed sidecar validates");

        const std::map<std::string, TransferExprKind> expected = {
            {"copied", TransferExprKind::Identity},
            {"widened", TransferExprKind::Cast},
            {"shifted", TransferExprKind::Affine},
            {"compared", TransferExprKind::Compare},
            {"combined", TransferExprKind::Boolean},
            {"selected", TransferExprKind::Select},
        };
        for (const auto &[suffix, kind] : expected) {
            const TypedValueTransfer &transfer = transfer_to(
                built.value_transfers,
                node_for_entity_name(built.index, suffix));
            require(
                transfer.soundness == TransferSoundness::Exact,
                "supported neutral expression remains exact");
            require(
                contains_kind(
                    built.value_transfers.expressions,
                    transfer.value_expression_id, kind),
                "supported neutral expression retains its typed AST kind");
        }

        const TypedValueTransfer &shifted = transfer_to(
            built.value_transfers,
            node_for_entity_name(built.index, "shifted"));
        require(
            shifted.definedness == DefinednessClass::Conditional &&
                shifted.defined_when_expression_id.has_value(),
            "signed affine arithmetic records no-overflow definedness");
        require(
            contains_kind(
                built.value_transfers.expressions,
                *shifted.defined_when_expression_id,
                TransferExprKind::Definedness),
            "signed affine definedness is machine represented");

        const std::string nonlinear_node =
            node_for_entity_name(built.index, "nonlinear");
        const TypedValueTransfer &nonlinear =
            transfer_to(built.value_transfers, nonlinear_node);
        require(
            nonlinear.soundness == TransferSoundness::Unknown &&
                contains_kind(
                    built.value_transfers.expressions,
                    nonlinear.value_expression_id, TransferExprKind::Unknown),
            "non-affine multiplication abstains explicitly");
        const bool nonlinear_has_data_edge = std::any_of(
            built.index.relations.begin(), built.index.relations.end(),
            [&](const SemanticRelation &relation) {
                return relation.target_node_id == nonlinear_node &&
                       relation.kind == RelationKind::Data;
            });
        require(nonlinear_has_data_edge, "generic Data reachability is retained");
        require(
            !typed_transfer_is_identity(
                nonlinear, built.value_transfers.expressions),
            "generic Data never licenses identity");

        const IndexBuildArtifacts repeated =
            build_semantic_index_with_value_transfers(plan);
        require(
            repeated.index.artifact_id == built.index.artifact_id &&
                repeated.value_transfers.artifact_id ==
                    built.value_transfers.artifact_id &&
                expression_ids(repeated.value_transfers.expressions) ==
                    expression_ids(built.value_transfers.expressions) &&
                transfer_ids(repeated.value_transfers.transfers) ==
                    transfer_ids(built.value_transfers.transfers),
            "semantic sidecar is byte-order deterministic across AST passes");

        const std::string semantic_index_sha = sha256_hex("neutral-index-bytes");
        const ContextualizationArtifacts contextual =
            build_contextual_influence_graph_with_value_transfers(
                built.index, built.value_transfers, semantic_index_sha);
        require(
            contextual.graph.status != StageStatus::Failed,
            "contextual graph construction succeeds");
        const std::vector<std::string> contextual_errors =
            validate_contextual_value_transfers(
                contextual.value_transfers, contextual.graph,
                built.index, built.value_transfers);
        require(
            contextual_errors.empty(),
            contextual_errors.empty()
                ? "contextual typed sidecar validates"
                : "contextual typed sidecar validates: " +
                      contextual_errors.front());
        SemanticValueTransferIndex bound_semantic = built.value_transfers;
        const std::string semantic_prebind_id = bound_semantic.artifact_id;
        bind_semantic_value_transfer_physical_digest(
            bound_semantic, semantic_index_sha);
        require(
            bound_semantic.physical_digest_binding_complete &&
                bound_semantic.artifact_id != semantic_prebind_id &&
                validate_semantic_value_transfers(
                    bound_semantic, built.index).empty(),
            "semantic sidecar binds the physical index digest");
        ContextualValueTransferIndex bound_contextual =
            contextual.value_transfers;
        const std::string contextual_prebind_id =
            bound_contextual.artifact_id;
        bind_contextual_value_transfer_physical_digests(
            bound_contextual, sha256_hex("semantic-sidecar-bytes"),
            sha256_hex("contextual-graph-bytes"));
        require(
            bound_contextual.physical_digest_binding_complete &&
                bound_contextual.artifact_id != contextual_prebind_id &&
                validate_contextual_value_transfers(
                    bound_contextual, contextual.graph, built.index,
                    built.value_transfers).empty(),
            "contextual sidecar binds semantic-sidecar and graph bytes");
        require(
            std::any_of(
                contextual.value_transfers.transfers.begin(),
                contextual.value_transfers.transfers.end(),
                [&](const TypedValueTransfer &transfer) {
                    return transfer.soundness == TransferSoundness::Exact &&
                           contains_kind(
                               contextual.value_transfers.expressions,
                               transfer.value_expression_id,
                               TransferExprKind::CallArg);
                }),
            "direct actual-to-formal transfer is instantiated");
        require(
            std::any_of(
                contextual.value_transfers.transfers.begin(),
                contextual.value_transfers.transfers.end(),
                [&](const TypedValueTransfer &transfer) {
                    return transfer.soundness == TransferSoundness::Exact &&
                           contains_kind(
                               contextual.value_transfers.expressions,
                               transfer.value_expression_id,
                               TransferExprKind::Return);
                }),
            "direct return-to-call transfer is instantiated");

        const CallSiteSummary &indirect = indirect_callsite(built.index);
        require(
            std::none_of(
                contextual.value_transfers.transfers.begin(),
                contextual.value_transfers.transfers.end(),
                [&](const TypedValueTransfer &transfer) {
                    return transfer.callsite_id == indirect.callsite_id &&
                           transfer.soundness == TransferSoundness::Exact &&
                           (contains_kind(
                                contextual.value_transfers.expressions,
                                transfer.value_expression_id,
                                TransferExprKind::CallArg) ||
                            contains_kind(
                                contextual.value_transfers.expressions,
                                transfer.value_expression_id,
                                TransferExprKind::Return));
                }),
            "indirect call never receives an exact boundary transfer");
        require(
            std::any_of(
                contextual.value_transfers.transfers.begin(),
                contextual.value_transfers.transfers.end(),
                [&](const TypedValueTransfer &transfer) {
                    return transfer.callsite_id == indirect.callsite_id &&
                           transfer.soundness == TransferSoundness::Unknown;
                }),
            "indirect call abstention is explicit");

        const ContextualInfluenceGraph legacy =
            build_contextual_influence_graph(
                built.index, semantic_index_sha);
        require(
            legacy.artifact_id == contextual.graph.artifact_id &&
                legacy.nodes.size() == contextual.graph.nodes.size() &&
                legacy.edges.size() == contextual.graph.edges.size(),
            "legacy graph API remains behavior compatible");
        const ContextualizationArtifacts repeated_contextual =
            build_contextual_influence_graph_with_value_transfers(
                repeated.index, repeated.value_transfers,
                semantic_index_sha);
        require(
            repeated_contextual.value_transfers.artifact_id ==
                    contextual.value_transfers.artifact_id &&
                expression_ids(
                    repeated_contextual.value_transfers.expressions) ==
                    expression_ids(
                        contextual.value_transfers.expressions) &&
                transfer_ids(
                    repeated_contextual.value_transfers.transfers) ==
                    transfer_ids(contextual.value_transfers.transfers),
            "contextual sidecar is deterministic");

        ValueTransferOptions tiny;
        tiny.maximum_expression_nodes = 4;
        tiny.maximum_transfers = 4;
        const IndexBuildArtifacts limited =
            build_semantic_index_with_value_transfers(plan, {}, tiny);
        require(
            limited.value_transfers.resource_limit_hit &&
                limited.value_transfers.status ==
                    StageStatus::ConservativeIncomplete,
            "resource exhaustion fails closed without dropping accounting");

        fs::remove_all(fixture, error);
        std::cout << "PASS typed value-transfer sidecar\n";
        return 0;
    } catch (const std::exception &exception) {
        fs::remove_all(fixture, error);
        std::cerr << "FAIL " << exception.what() << '\n';
        return 1;
    }
}
