// 本文件把在线前缀查询结果编码为与原报告隔离的两个精确 JSONL 文件。

#include "PrefixCostOutput.h"

#include <chrono>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

using Clock = std::chrono::steady_clock;

std::uint64_t elapsed_us(Clock::time_point start) {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::microseconds>(Clock::now() - start)
            .count());
}

std::string json_escape(const std::string& value) {
    std::ostringstream out;
    for (const unsigned char character : value) {
        switch (character) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (character < 0x20) {
                    out << "\\u" << std::hex << std::setw(4)
                        << std::setfill('0') << static_cast<unsigned>(character)
                        << std::dec << std::setfill(' ');
                } else {
                    out << static_cast<char>(character);
                }
        }
    }
    return out.str();
}

std::string integer_string(const BigInt& value) {
    return value.convert_to<std::string>();
}

std::string rational_string(const BigRational& value) {
    const auto numerator = integer_string(value.numerator());
    if (value.denominator() == 1) return numerator;
    return numerator + "/" + integer_string(value.denominator());
}

const char* bool_string(bool value) {
    return value ? "true" : "false";
}

const char* delay_kind_name(DelayWitnessKind kind) {
    switch (kind) {
        case DelayWitnessKind::ZERO: return "zero";
        case DelayWitnessKind::LOWER_FACET: return "lower_facet";
        case DelayWitnessKind::UPPER_FACET: return "upper_facet";
    }
    return "unknown";
}

const char* optimum_kind_name(AffineOptimumKind kind) {
    switch (kind) {
        case AffineOptimumKind::Empty: return "empty";
        case AffineOptimumKind::Finite: return "finite";
        case AffineOptimumKind::PositiveInfinity: return "positive_infinity";
        case AffineOptimumKind::Unknown: return "unknown";
    }
    return "unknown";
}

void write_optional_id(std::ostream& out, const std::optional<std::uint64_t>& id) {
    if (id.has_value()) out << *id; else out << "null";
}

void write_optional_size(
    std::ostream& out,
    const std::optional<std::size_t>& value) {
    if (value.has_value()) out << *value; else out << "null";
}

void write_optional_edge(std::ostream& out, const std::optional<EdgeId>& edge) {
    if (!edge.has_value()) {
        out << "null";
        return;
    }
    out << "{\"source\":" << edge->source
        << ",\"ordinal\":" << edge->ordinal << '}';
}

void write_rational_array(
    std::ostream& out,
    const RationalValuation& valuation) {
    out << '[';
    for (std::size_t index = 0; index < valuation.size(); ++index) {
        if (index != 0) out << ',';
        out << '"' << rational_string(valuation[index]) << '"';
    }
    out << ']';
}

void write_integer_array(std::ostream& out, const std::vector<BigInt>& values) {
    out << '[';
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0) out << ',';
        out << '"' << integer_string(values[index]) << '"';
    }
    out << ']';
}

void write_dbm(std::ostream& out, const pardibaal::DBM& zone) {
    out << "{\"dimension\":" << zone.dimension() << ",\"bounds\":[";
    bool first = true;
    for (pardibaal::dim_t i = 0; i < zone.dimension(); ++i) {
        for (pardibaal::dim_t j = 0; j < zone.dimension(); ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) continue;
            if (!first) out << ',';
            first = false;
            out << "{\"i\":" << i << ",\"j\":" << j
                << ",\"value\":\"" << bound.get_bound() << '"'
                << ",\"strict\":" << bool_string(bound.is_strict()) << '}';
        }
    }
    out << "]}";
}

void write_witness(
    std::ostream& out,
    const MixedDerivationWitness& witness) {
    out << "{\"goal_seed\":" << bool_string(witness.is_goal_seed)
        << ",\"delay_kind\":\"" << delay_kind_name(witness.delay_kind) << '"'
        << ",\"facet_clock\":";
    if (witness.facet_clock.has_value()) out << *witness.facet_clock;
    else out << "null";
    out << ",\"facet_bound\":";
    if (witness.facet_bound.has_value()) out << '"' << *witness.facet_bound << '"';
    else out << "null";
    out << ",\"next_arc\":";
    write_optional_id(out, witness.next_arc);
    out << ",\"next_edge\":";
    write_optional_edge(out, witness.next_edge);
    out << ",\"successor_node\":";
    write_optional_id(out, witness.successor_node);
    out << ",\"successor_piece\":";
    write_optional_id(out, witness.successor_piece);
    out << ",\"successor_unbounded_region\":";
    write_optional_id(out, witness.successor_unbounded_region);
    out << ",\"unbounded_delay\":" << bool_string(witness.unbounded_delay)
        << '}';
}

void write_affine_supremum(std::ostream& out, const AffineSupremum& supremum) {
    out << "{\"kind\":\"" << optimum_kind_name(supremum.kind)
        << "\",\"value\":";
    if (supremum.kind == AffineOptimumKind::Finite) {
        out << '"' << rational_string(supremum.value) << '"';
    } else {
        out << "null";
    }
    out << ",\"domain_attained\":" << bool_string(supremum.domain_attained)
        << ",\"optimizer_or_limit\":";
    if (supremum.optimizer_or_limit.has_value()) {
        write_rational_array(out, *supremum.optimizer_or_limit);
    } else {
        out << "null";
    }
    out << ",\"optimizer_is_actual\":"
        << bool_string(supremum.optimizer_is_actual)
        << ",\"upper_bound_proved\":"
        << bool_string(supremum.upper_bound_proved)
        << ",\"timed_out\":" << bool_string(supremum.timed_out)
        << ",\"elapsed_us\":" << supremum.elapsed_us
        << ",\"diagnostic\":\"" << json_escape(supremum.diagnostic) << "\"}";
}

void write_materialized_delay(
    std::ostream& out,
    const MaterializedDelayWitness& delay) {
    out << "{\"value_or_limit\":";
    if (delay.value_or_limit.has_value()) {
        out << '"' << rational_string(*delay.value_or_limit) << '"';
    } else {
        out << "null";
    }
    out << ",\"attained\":" << bool_string(delay.attained)
        << ",\"epsilon_optimal\":" << bool_string(delay.epsilon_optimal)
        << ",\"replay_checked\":" << bool_string(delay.replay_checked)
        << ",\"replay_valid\":" << bool_string(delay.replay_valid)
        << ",\"diagnostic\":\"" << json_escape(delay.diagnostic) << "\"}";
}

void write_weighted_zone(std::ostream& out, const WeightedZone& weighted_zone) {
    out << "{\"semantics\":\"W=-V\",\"offset_weight\":\""
        << integer_string(weighted_zone.offset_weight) << "\",\"rates\":";
    write_integer_array(out, weighted_zone.rates);
    out << ",\"attained\":" << bool_string(weighted_zone.attained)
        << ",\"reference_zone\":";
    write_dbm(out, weighted_zone.zone);
    out << '}';
}

void write_cost(std::ostream& out, const CostToGoResult& cost) {
    out << "{\"kind\":\"" << to_string(cost.kind) << "\",\"value\":";
    if (cost.kind == CostValueKind::Finite) {
        out << '"' << rational_string(cost.value) << '"';
    } else {
        out << "null";
    }
    out << ",\"attained\":" << bool_string(cost.attained)
        << ",\"exact\":" << bool_string(cost.exact)
        << ",\"lower_bound_declared\":"
        << bool_string(cost.lower_bound_assumed)
        << ",\"solver_status\":\"" << to_string(cost.solver_status) << '"'
        << ",\"piece_id\":";
    write_optional_id(out, cost.piece_id);
    out << ",\"unbounded_region_id\":";
    write_optional_id(out, cost.unbounded_region_id);
    out << ",\"next_edge\":";
    write_optional_edge(out, cost.next_edge);
    out << '}';
}

void write_runtime_states(
    std::ostream& out,
    const std::vector<RuntimeSymbolicState>& states) {
    out << '[';
    for (std::size_t index = 0; index < states.size(); ++index) {
        if (index != 0) out << ',';
        const auto& state = states[index];
        out << "{\"runtime_state_id\":" << state.runtime_state_id
            << ",\"location\":" << state.location
            << ",\"dbms\":" << state.semantic_domain.size() << '}';
    }
    out << ']';
}

void write_query_statistics(
    std::ostream& out,
    const PrefixCostRecord& record,
    std::uint64_t serialization_us) {
    const auto& stats = record.result.statistics;
    out << "{\"state_extraction_us\":" << record.state_extraction_us
        << ",\"observer_projection_us\":" << record.observer_projection_us
        << ",\"candidate_filtering_us\":" << stats.filtering_us
        << ",\"dbm_intersection_us\":" << stats.intersection_us
        << ",\"optimizer_us\":" << stats.optimizer_us
        << ",\"witness_us\":" << stats.witness_us
        << ",\"core_query_us\":" << stats.core_query_us
        << ",\"serialization_us\":" << serialization_us
        << ",\"runtime_states\":" << stats.runtime_states
        << ",\"runtime_dbms\":" << stats.runtime_dbms
        << ",\"reachable_nodes_considered\":"
        << stats.reachable_nodes_considered
        << ",\"piece_intersections\":" << stats.piece_intersections
        << ",\"candidates\":" << stats.candidates
        << ",\"unbounded_candidates\":" << stats.unbounded_candidates
        << ",\"optimizer_calls\":" << stats.optimizer_calls
        << ",\"cache_hits\":" << stats.cache_hits << '}';
}

std::string encode_cost_record(
    const PrefixCostRun& run,
    const PrefixCostRecord& record,
    std::uint64_t serialization_us) {
    std::ostringstream out;
    out << "{\"schema_version\":1,\"prefix_index\":" << record.prefix_index
        << ",\"input_index\":";
    write_optional_id(out, record.input_index);
    out << ",\"timestamp\":";
    if (record.timestamp.has_value()) {
        out << "{\"lower\":\"" << rational_string(record.timestamp->lower)
            << "\",\"upper\":\"" << rational_string(record.timestamp->upper)
            << "\"}";
    } else {
        out << "null";
    }
    out << ",\"evaluation_status\":\"" << to_string(record.status) << '"'
        << ",\"terminal_source_prefix\":";
    write_optional_id(out, record.terminal_source_prefix);
    out << ",\"target_automaton\":\"" << json_escape(run.target_automaton)
        << "\",\"optimizer_backend\":\"" << to_string(run.optimizer) << '"'
        << ",\"mixed_precompute_us\":" << run.mixed_precompute_us
        << ",\"live_states\":";
    write_runtime_states(out, record.runtime_states);
    out << ",\"domain_status\":\"" << to_string(record.result.domain_status)
        << "\",\"aggregate\":";
    write_cost(out, record.result.aggregate);
    out << ",\"negative_infinity_cause\":\""
        << to_string(record.result.negative_infinity_cause) << '"'
        << ",\"optimizer_or_limit\":";
    if (record.result.optimizer_or_limit.has_value()) {
        write_rational_array(out, *record.result.optimizer_or_limit);
    } else {
        out << "null";
    }
    out << ",\"optimizer_is_actual\":"
        << bool_string(record.result.optimizer_is_actual)
        << ",\"delay_value_or_limit\":";
    if (record.result.delay_value_or_limit.has_value()) {
        out << '"' << rational_string(*record.result.delay_value_or_limit) << '"';
    } else {
        out << "null";
    }
    out << ",\"delay_attained\":" << bool_string(record.result.delay_attained)
        << ",\"runtime_state_id\":";
    write_optional_id(out, record.result.runtime_state_id);
    out << ",\"runtime_dbm_index\":";
    write_optional_size(out, record.result.runtime_dbm_index);
    out << ",\"reachable_node_id\":";
    write_optional_id(out, record.result.reachable_node);
    out << ",\"piece_id\":";
    write_optional_id(out, record.result.piece_id);
    out << ",\"next_arc\":";
    write_optional_id(out, record.result.next_arc);
    out << ",\"next_edge\":";
    write_optional_edge(out, record.result.next_edge);
    out << ",\"witness\":";
    if (record.result.witness.has_value()) {
        write_witness(out, *record.result.witness);
    } else {
        out << "null";
    }
    out << ",\"query_diagnostic\":\""
        << json_escape(record.result.diagnostic)
        << "\",\"record_diagnostic\":\"" << json_escape(record.diagnostic)
        << "\",\"timing_and_counts\":";
    write_query_statistics(out, record, serialization_us);
    out << '}';
    return out.str();
}

std::string encode_finite_region(
    const PrefixCostRecord& record,
    const SymbolicCostCandidate& candidate) {
    std::ostringstream out;
    out << "{\"schema_version\":1,\"prefix_index\":" << record.prefix_index
        << ",\"kind\":\"finite\",\"runtime_state_id\":"
        << candidate.runtime_state_id
        << ",\"runtime_dbm_index\":" << candidate.runtime_dbm_index
        << ",\"reachable_node_id\":" << candidate.reachable_node
        << ",\"piece_id\":" << candidate.piece_id << ",\"domain\":";
    write_dbm(out, candidate.domain);
    out << ",\"affine_weight\":";
    write_weighted_zone(out, candidate.affine_weight);
    out << ",\"supremum\":";
    write_affine_supremum(out, candidate.supremum);
    out << ",\"cost_attained\":" << bool_string(candidate.cost_attained)
        << ",\"delay\":";
    write_materialized_delay(out, candidate.delay);
    out << ",\"witness\":";
    write_witness(out, candidate.witness);
    out << '}';
    return out.str();
}

std::string encode_unbounded_region(
    const PrefixCostRecord& record,
    const SymbolicUnboundedCandidate& candidate) {
    std::ostringstream out;
    out << "{\"schema_version\":1,\"prefix_index\":" << record.prefix_index
        << ",\"kind\":\"negative_infinity\",\"runtime_state_id\":"
        << candidate.runtime_state_id
        << ",\"runtime_dbm_index\":" << candidate.runtime_dbm_index
        << ",\"reachable_node_id\":" << candidate.reachable_node
        << ",\"region_id\":" << candidate.region_id << ",\"domain\":";
    write_dbm(out, candidate.domain);
    out << ",\"witness\":";
    write_witness(out, candidate.witness);
    out << '}';
    return out.str();
}

}  // namespace

PrefixCostOutputStatistics write_prefix_cost_outputs(
    const std::filesystem::path& output_dir,
    const PrefixCostRun& run) {
    std::filesystem::create_directories(output_dir);
    const auto costs_path = output_dir / "pta_prefix_costs.jsonl";
    const auto regions_path = output_dir / "pta_prefix_regions.jsonl";

    std::vector<std::string> cost_lines;
    std::vector<std::string> region_lines;
    PrefixCostOutputStatistics statistics;
    cost_lines.reserve(run.records.size());
    statistics.serialization_us.reserve(run.records.size());

    for (const auto& record : run.records) {
        const auto started = Clock::now();
        const auto provisional = encode_cost_record(run, record, 0);
        (void)provisional;
        for (const auto& candidate : record.result.candidates) {
            region_lines.push_back(encode_finite_region(record, candidate));
        }
        for (const auto& candidate : record.result.unbounded_candidates) {
            region_lines.push_back(encode_unbounded_region(record, candidate));
        }
        const auto serialization_us = elapsed_us(started);
        statistics.serialization_us.push_back(serialization_us);

        // 最终一遍只注入已测得的时间；文件 I/O 在所有编码完成后才开始。
        cost_lines.push_back(
            encode_cost_record(run, record, serialization_us));
    }

    const auto write_started = Clock::now();
    std::ofstream costs(costs_path);
    if (!costs) {
        throw std::runtime_error("Could not write " + costs_path.string());
    }
    for (const auto& line : cost_lines) costs << line << '\n';
    if (!costs) {
        throw std::runtime_error("Could not finish writing " + costs_path.string());
    }

    std::ofstream regions(regions_path);
    if (!regions) {
        throw std::runtime_error("Could not write " + regions_path.string());
    }
    for (const auto& line : region_lines) regions << line << '\n';
    if (!regions) {
        throw std::runtime_error(
            "Could not finish writing " + regions_path.string());
    }
    statistics.file_write_us = elapsed_us(write_started);
    return statistics;
}

std::string to_string(PrefixRecordStatus status) {
    switch (status) {
        case PrefixRecordStatus::Evaluated: return "evaluated";
        case PrefixRecordStatus::NotEvaluatedMonitorTerminal:
            return "not_evaluated_monitor_terminal";
        case PrefixRecordStatus::GoalAlreadyHit: return "goal_already_hit";
    }
    throw std::logic_error("unknown PrefixRecordStatus");
}

std::string to_string(PrefixOptimizerBackend backend) {
    switch (backend) {
        case PrefixOptimizerBackend::Z3: return "z3";
        case PrefixOptimizerBackend::RomeoDBM: return "romeo-dbm";
        case PrefixOptimizerBackend::CrossCheck: return "crosscheck";
    }
    throw std::logic_error("unknown PrefixOptimizerBackend");
}

}  // namespace tamonitor::pta
