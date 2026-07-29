#include "TAMonitor.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>

#ifndef TAMONITOR_XLSX_SCRIPT
#define TAMONITOR_XLSX_SCRIPT "/home/lqq/project/TAFuzz/src/TAMonitor/make_tamonitor_xlsx.py"
#endif

namespace tamonitor {

namespace {

std::string csv_escape(const std::string& value) {
    if (value.find_first_of(",\"\n\r") == std::string::npos) {
        return value;
    }
    std::string out = "\"";
    for (char c : value) {
        if (c == '"') {
            out += "\"\"";
        } else {
            out += c;
        }
    }
    out += '"';
    return out;
}

std::string json_escape(const std::string& value) {
    std::string out;
    for (char c : value) {
        switch (c) {
            case '\\':
                out += "\\\\";
                break;
            case '"':
                out += "\\\"";
                break;
            case '\n':
                out += "\\n";
                break;
            case '\r':
                out += "\\r";
                break;
            case '\t':
                out += "\\t";
                break;
            default:
                out += c;
                break;
        }
    }
    return out;
}

std::string interval_to_string(monitaal::interval_t interval) {
    if (interval.first == interval.second) {
        return std::to_string(interval.first);
    }
    return "[" + std::to_string(interval.first) + "," + std::to_string(interval.second) + "]";
}

void write_steps_csv(const std::filesystem::path& path, const RunResult& run) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    out << "step,time,canonical_label,human_label,verdict,positive_states,negative_states,monitor_advanced\n";
    for (const auto& step : run.steps) {
        out << step.index << ','
            << csv_escape(interval_to_string(step.time)) << ','
            << csv_escape(step.canonical_label) << ','
            << csv_escape(step.human_label) << ','
            << step.verdict << ','
            << step.positive_states << ','
            << step.negative_states << ','
            << (step.monitor_advanced ? "true" : "false") << '\n';
    }
}

void write_summary_csv(const std::filesystem::path& path, const Options& options, const BuildPair& build, const std::vector<TimedEvent>& trace, const RunResult& run) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    size_t advanced_steps = 0;
    for (const auto& step : run.steps) {
        if (step.monitor_advanced) {
            ++advanced_steps;
        }
    }
    out << "metric,value\n";
    out << "build_mode," << to_string(options.build_mode) << '\n';
    out << "run_mode," << (options.build_only ? "build_only" : "monitor") << '\n';
    out << "word_mode," << to_string(options.word_mode) << '\n';
    out << "state_mode," << to_string(options.state_mode) << '\n';
    out << "bdd_nodes," << options.bdd_nodes << '\n';
    out << "bdd_cache," << options.bdd_cache << '\n';
    out << "bdd_max_increase," << options.bdd_max_increase << '\n';
    out << "max_valuations," << options.max_valuations << '\n';
    out << "normalized_formula," << csv_escape(build.normalized_formula) << '\n';
    out << "formula_satisfiable," << build.positive.satisfiability << '\n';
    out << "negative_formula_satisfiable," << build.negative.satisfiability << '\n';
    out << "final_verdict," << run.final_verdict << '\n';
    out << "events," << trace.size() << '\n';
    out << "processed_steps," << run.steps.size() << '\n';
    out << "advanced_steps," << advanced_steps << '\n';
    out << "carry_forward_steps," << (run.steps.size() - advanced_steps) << '\n';
    out << "build_ms," << build.build_ms << '\n';
    out << "monitor_ms," << run.monitor_ms << '\n';
    out << "positive_components," << build.positive.stats.components << '\n';
    out << "positive_locations," << build.positive.stats.locations << '\n';
    out << "positive_edges," << build.positive.stats.edges << '\n';
    out << "positive_clocks," << build.positive.stats.clocks << '\n';
    out << "negative_components," << build.negative.stats.components << '\n';
    out << "negative_locations," << build.negative.stats.locations << '\n';
    out << "negative_edges," << build.negative.stats.edges << '\n';
    out << "negative_clocks," << build.negative.stats.clocks << '\n';
    out << "positive_projection_valuations," << build.positive.projection_valuations << '\n';
    out << "negative_projection_valuations," << build.negative.projection_valuations << '\n';
}

void write_metadata_json(const std::filesystem::path& path, const Options& options, const std::string& formula, const BuildPair& build, const RunResult& run) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    size_t advanced_steps = 0;
    for (const auto& step : run.steps) {
        if (step.monitor_advanced) {
            ++advanced_steps;
        }
    }
    out << "{\n";
    out << "  \"tool\": \"TAMonitor\",\n";
    out << "  \"build_mode\": \"" << to_string(options.build_mode) << "\",\n";
    out << "  \"run_mode\": \"" << (options.build_only ? "build_only" : "monitor") << "\",\n";
    out << "  \"word_mode\": \"" << to_string(options.word_mode) << "\",\n";
    out << "  \"state_mode\": \"" << to_string(options.state_mode) << "\",\n";
    out << "  \"formula\": \"" << json_escape(formula) << "\",\n";
    out << "  \"normalized_formula\": \"" << json_escape(build.normalized_formula) << "\",\n";
    out << "  \"positive_nnf\": \"" << json_escape(build.positive.nnf_formula) << "\",\n";
    out << "  \"negative_nnf\": \"" << json_escape(build.negative.nnf_formula) << "\",\n";
    out << "  \"formula_satisfiable\": \"" << build.positive.satisfiability << "\",\n";
    out << "  \"negative_formula_satisfiable\": \"" << build.negative.satisfiability << "\",\n";
    out << "  \"final_verdict\": \"" << run.final_verdict << "\",\n";
    out << "  \"processed_steps\": " << run.steps.size() << ",\n";
    out << "  \"advanced_steps\": " << advanced_steps << ",\n";
    out << "  \"carry_forward_steps\": " << (run.steps.size() - advanced_steps) << ",\n";
    out << "  \"max_valuations\": " << options.max_valuations << ",\n";
    out << "  \"bdd_nodes\": " << options.bdd_nodes << ",\n";
    out << "  \"bdd_cache\": " << options.bdd_cache << ",\n";
    out << "  \"bdd_max_increase\": " << options.bdd_max_increase << ",\n";
    out << "  \"proposition_order\": [";
    for (size_t i = 0; i < build.proposition_order.size(); ++i) {
        out << (i ? ", " : "") << "\"" << json_escape(build.proposition_order[i]) << "\"";
    }
    out << "],\n";
    out << "  \"positive_stats\": {\"components\": " << build.positive.stats.components
        << ", \"locations\": " << build.positive.stats.locations
        << ", \"edges\": " << build.positive.stats.edges
        << ", \"clocks\": " << build.positive.stats.clocks
        << ", \"labels\": " << build.positive.stats.labels
        << ", \"projection_valuations\": " << build.positive.projection_valuations << "},\n";
    out << "  \"negative_stats\": {\"components\": " << build.negative.stats.components
        << ", \"locations\": " << build.negative.stats.locations
        << ", \"edges\": " << build.negative.stats.edges
        << ", \"clocks\": " << build.negative.stats.clocks
        << ", \"labels\": " << build.negative.stats.labels
        << ", \"projection_valuations\": " << build.negative.projection_valuations << "},\n";
    out << "  \"build_ms\": " << build.build_ms << ",\n";
    out << "  \"monitor_ms\": " << run.monitor_ms << "\n";
    out << "}\n";
}

void write_bdd_interface_json(const std::filesystem::path& path, const BuildPair& build) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    out << "{\n";
    out << "  \"status\": \"interface_reserved_not_implemented\",\n";
    out << "  \"label_semantics\": \"BDD edge labels are available in MightyPPL before canonical projection; TAMonitor v1 does not run a BDD-native monitor.\",\n";
    out << "  \"proposition_order\": [";
    for (size_t i = 0; i < build.proposition_order.size(); ++i) {
        out << (i ? ", " : "") << "\"" << json_escape(build.proposition_order[i]) << "\"";
    }
    out << "]\n";
    out << "}\n";
}

void generate_xlsx(const std::filesystem::path& output_dir) {
    const std::string command = "python3 \"" + std::string(TAMONITOR_XLSX_SCRIPT) + "\" \"" + output_dir.string() + "\"";
    const int code = std::system(command.c_str());
    if (code != 0) {
        std::ofstream note(output_dir / "results.xlsx.error.txt");
        note << "Excel generation failed with exit code " << code << ". CSV and JSON outputs are authoritative.\n";
    }
}

}

void write_report(const Options& options, const std::string& formula, const BuildPair& build, const std::vector<TimedEvent>& trace, const RunResult& run) {
    std::filesystem::create_directories(options.output_dir);
    write_steps_csv(options.output_dir / "steps.csv", run);
    write_summary_csv(options.output_dir / "summary.csv", options, build, trace, run);
    write_metadata_json(options.output_dir / "metadata.json", options, formula, build, run);
    if (options.emit_bdd_interface) {
        write_bdd_interface_json(options.output_dir / "bdd_interface.json", build);
    }
    generate_xlsx(options.output_dir);
}

}
