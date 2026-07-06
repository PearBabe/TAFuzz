#pragma once

#include "Monitor.h"
#include "TA.h"

#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace tamonitor {

enum class BuildMode { Flatten, Compflatten };
enum class WordMode { Finite, Infinite };
enum class StateMode { Symbolic, Concrete };

struct Options {
    std::optional<std::filesystem::path> trace_path;
    std::optional<std::filesystem::path> formula_path;
    std::optional<std::string> formula_inline;
    BuildMode build_mode = BuildMode::Flatten;
    WordMode word_mode = WordMode::Infinite;
    StateMode state_mode = StateMode::Symbolic;
    std::filesystem::path output_dir;
    size_t max_valuations = 4096;
    size_t bdd_nodes = 1000000;
    size_t bdd_cache = 100000;
    size_t bdd_max_increase = 500000;
    bool emit_bdd_interface = false;
    bool build_only = false;
};

struct TimedEvent {
    monitaal::interval_t time;
    std::string canonical_label;
    std::string human_label;
};

struct AutomatonStats {
    size_t components = 1;
    size_t locations = 0;
    size_t edges = 0;
    size_t clocks = 0;
    size_t labels = 0;
};

struct BuildArtifact {
    monitaal::TA automaton = monitaal::TA("dummy", {}, {}, {}, 0);
    std::string nnf_formula;
    AutomatonStats stats;
    bool satisfiable = false;
    std::string satisfiability = "UNKNOWN";
    size_t projection_valuations = 0;
    std::string diagnostics;
};

struct BuildPair {
    BuildArtifact positive;
    BuildArtifact negative;
    std::string normalized_formula;
    std::vector<std::string> proposition_order;
    std::map<std::string, int> positive_prop_ids;
    std::map<std::string, int> negative_prop_ids;
    long long build_ms = 0;
};

struct StepResult {
    size_t index = 0;
    monitaal::interval_t time;
    std::string canonical_label;
    std::string human_label;
    std::string verdict;
    size_t positive_states = 0;
    size_t negative_states = 0;
    bool monitor_advanced = true;
};

struct RunResult {
    std::vector<StepResult> steps;
    std::string final_verdict = "INCONCLUSIVE";
    long long monitor_ms = 0;
};

Options parse_options(int argc, const char** argv);
std::string read_formula(const Options& options);
BuildPair build_automata_pair(const std::string& formula, const Options& options);
std::vector<TimedEvent> parse_trace(const Options& options, const std::vector<std::string>& proposition_order);
RunResult run_monitor(const BuildPair& build, const std::vector<TimedEvent>& trace, const Options& options);
void write_report(const Options& options, const std::string& formula, const BuildPair& build, const std::vector<TimedEvent>& trace, const RunResult& run);
std::filesystem::path default_output_dir();

std::string to_string(BuildMode mode);
std::string to_string(WordMode mode);
std::string to_string(StateMode mode);
std::string verdict_to_string(monitaal::monitor_answer_e answer);

}
