// 本文件解析并校验 TAMonitor CLI，包括 finite-word PTA 分析资源契约。

#include "TAMonitor.h"

#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

#ifndef TAMONITOR_REPO_ROOT
#define TAMONITOR_REPO_ROOT "/home/lqq/project/TAFuzz"
#endif

namespace tamonitor {

namespace {

std::string require_value(int& i, int argc, const char** argv, const std::string& option) {
    if (i + 1 >= argc) {
        throw std::invalid_argument("Missing value for " + option);
    }
    return argv[++i];
}

size_t parse_size(
    const std::string& value,
    const std::string& option,
    bool allow_zero) {
    if (value.empty() || value.front() == '-') {
        throw std::invalid_argument(
            option + (allow_zero ? " must be non-negative" : " must be positive"));
    }

    std::size_t consumed = 0;
    unsigned long long parsed = 0;
    try {
        parsed = std::stoull(value, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(option + " has an invalid integer value: " + value);
    }
    if (consumed != value.size() || parsed > std::numeric_limits<size_t>::max()) {
        throw std::invalid_argument(option + " has an invalid integer value: " + value);
    }
    if (!allow_zero && parsed == 0) {
        throw std::invalid_argument(option + " must be positive");
    }
    return static_cast<size_t>(parsed);
}

size_t parse_positive_size(const std::string& value, const std::string& option) {
    return parse_size(value, option, false);
}

size_t parse_nonnegative_size(const std::string& value, const std::string& option) {
    return parse_size(value, option, true);
}

size_t parse_buddy_int_size(const std::string& value, const std::string& option) {
    const auto parsed = parse_positive_size(value, option);
    if (parsed > static_cast<size_t>(std::numeric_limits<int>::max())) {
        throw std::invalid_argument(option + " exceeds BuDDy int API range");
    }
    return parsed;
}

}

std::filesystem::path default_output_dir() {
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    localtime_r(&time, &tm);

    std::ostringstream run_id;
    run_id << std::put_time(&tm, "%Y%m%d-%H%M%S");
    return std::filesystem::path(TAMONITOR_REPO_ROOT) / "test" / "TARV" / "results" / run_id.str();
}

Options parse_options(int argc, const char** argv) {
    Options options;
    options.output_dir = default_output_dir();
    bool pta_max_pieces_explicit = false;
    bool pta_max_reach_nodes_explicit = false;
    bool pta_max_reach_arcs_explicit = false;
    bool pta_timeout_explicit = false;
    bool pta_prefix_query_timeout_explicit = false;
    bool pta_prefix_max_regions_explicit = false;
    bool pta_prefix_optimizer_explicit = false;
    bool pta_prefix_benchmark_explicit = false;

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            throw std::invalid_argument(
                "Usage: TAMonitor [--trace path] [--formula path|--formula-inline text] "
                "[--build-mode flatten|compflatten] [--word finite|infinite] "
                "[--state symbolic|concrete] [--out path] [--max-valuations n] "
                "[--bdd-nodes n] [--bdd-cache n] [--bdd-max-increase n] "
                "[--emit-bdd-interface] [--print-steps] [--build-only] "
                "[--pta-analysis backward|mixed] [--pta-cost-model path] "
                "[--pta-assume-lower-bounded] [--pta-verify-geometry] "
                "[--pta-max-pieces n] "
                "[--pta-max-reach-nodes n] [--pta-max-reach-arcs n] "
                "[--pta-timeout-ms n] [--pta-prefix-cost] "
                "[--pta-prefix-query-timeout-ms n] "
                "[--pta-prefix-max-regions n] "
                "[--pta-prefix-optimizer z3|romeo-dbm|crosscheck]\n"
                "[--pta-prefix-benchmark-iterations n]\n"
                "Note: compflatten is construction/statistics-only in TAMonitor v1; "
                "runtime monitoring requires --build-mode flatten. "
                "PTA analysis is optional and supports finite words only.");
        } else if (arg == "--trace") {
            options.trace_path = require_value(i, argc, argv, arg);
        } else if (arg == "--formula") {
            options.formula_path = require_value(i, argc, argv, arg);
        } else if (arg == "--formula-inline") {
            options.formula_inline = require_value(i, argc, argv, arg);
        } else if (arg == "--build-mode") {
            const std::string value = require_value(i, argc, argv, arg);
            if (value == "flatten") {
                options.build_mode = BuildMode::Flatten;
            } else if (value == "compflatten") {
                options.build_mode = BuildMode::Compflatten;
            } else {
                throw std::invalid_argument("Invalid --build-mode: " + value);
            }
        } else if (arg == "--word") {
            const std::string value = require_value(i, argc, argv, arg);
            if (value == "finite") {
                options.word_mode = WordMode::Finite;
            } else if (value == "infinite") {
                options.word_mode = WordMode::Infinite;
            } else {
                throw std::invalid_argument("Invalid --word: " + value);
            }
        } else if (arg == "--state") {
            const std::string value = require_value(i, argc, argv, arg);
            if (value == "symbolic") {
                options.state_mode = StateMode::Symbolic;
            } else if (value == "concrete") {
                options.state_mode = StateMode::Concrete;
            } else {
                throw std::invalid_argument("Invalid --state: " + value);
            }
        } else if (arg == "--out") {
            options.output_dir = require_value(i, argc, argv, arg);
        } else if (arg == "--max-valuations") {
            options.max_valuations = parse_positive_size(require_value(i, argc, argv, arg), arg);
        } else if (arg == "--bdd-nodes") {
            options.bdd_nodes = parse_buddy_int_size(require_value(i, argc, argv, arg), arg);
        } else if (arg == "--bdd-cache") {
            options.bdd_cache = parse_buddy_int_size(require_value(i, argc, argv, arg), arg);
        } else if (arg == "--bdd-max-increase") {
            options.bdd_max_increase = parse_buddy_int_size(require_value(i, argc, argv, arg), arg);
        } else if (arg == "--emit-bdd-interface") {
            options.emit_bdd_interface = true;
        } else if (arg == "--print-steps") {
            options.print_steps = true;
        } else if (arg == "--pta-analysis") {
            const std::string value = require_value(i, argc, argv, arg);
            if (value == "backward") {
                options.pta_analysis = PTAAnalysisMode::Backward;
            } else if (value == "mixed") {
                options.pta_analysis = PTAAnalysisMode::Mixed;
            } else {
                throw std::invalid_argument("Invalid --pta-analysis: " + value);
            }
        } else if (arg == "--pta-cost-model") {
            options.pta_cost_model = require_value(i, argc, argv, arg);
        } else if (arg == "--pta-assume-lower-bounded") {
            options.pta_assume_lower_bounded = true;
        } else if (arg == "--pta-verify-geometry") {
            options.pta_verify_geometry = true;
        } else if (arg == "--pta-max-pieces") {
            options.pta_max_pieces = parse_positive_size(require_value(i, argc, argv, arg), arg);
            pta_max_pieces_explicit = true;
        } else if (arg == "--pta-max-reach-nodes") {
            options.pta_max_reach_nodes =
                parse_positive_size(require_value(i, argc, argv, arg), arg);
            pta_max_reach_nodes_explicit = true;
        } else if (arg == "--pta-max-reach-arcs") {
            options.pta_max_reach_arcs =
                parse_positive_size(require_value(i, argc, argv, arg), arg);
            pta_max_reach_arcs_explicit = true;
        } else if (arg == "--pta-timeout-ms") {
            options.pta_timeout_ms = parse_nonnegative_size(require_value(i, argc, argv, arg), arg);
            pta_timeout_explicit = true;
        } else if (arg == "--pta-prefix-cost") {
            options.pta_prefix_cost = true;
        } else if (arg == "--pta-prefix-query-timeout-ms") {
            options.pta_prefix_query_timeout_ms =
                parse_nonnegative_size(require_value(i, argc, argv, arg), arg);
            pta_prefix_query_timeout_explicit = true;
        } else if (arg == "--pta-prefix-max-regions") {
            options.pta_prefix_max_regions =
                parse_positive_size(require_value(i, argc, argv, arg), arg);
            pta_prefix_max_regions_explicit = true;
        } else if (arg == "--pta-prefix-optimizer") {
            options.pta_prefix_optimizer = require_value(i, argc, argv, arg);
            if (options.pta_prefix_optimizer != "z3" &&
                options.pta_prefix_optimizer != "romeo-dbm" &&
                options.pta_prefix_optimizer != "crosscheck") {
                throw std::invalid_argument(
                    "Invalid --pta-prefix-optimizer: " +
                    options.pta_prefix_optimizer);
            }
            pta_prefix_optimizer_explicit = true;
        } else if (arg == "--pta-prefix-benchmark-iterations") {
            options.pta_prefix_benchmark_iterations =
                parse_positive_size(require_value(i, argc, argv, arg), arg);
            pta_prefix_benchmark_explicit = true;
        } else if (arg == "--build-only") {
            options.build_only = true;
        } else {
            throw std::invalid_argument("Unknown option: " + arg);
        }
    }

    if (options.formula_path.has_value() && options.formula_inline.has_value()) {
        throw std::invalid_argument("Provide at most one of --formula or --formula-inline");
    }
    if (options.pta_analysis != PTAAnalysisMode::Off) {
        const std::string mode = options.pta_analysis == PTAAnalysisMode::Mixed
            ? "mixed" : "backward";
        if (options.word_mode != WordMode::Finite) {
            throw std::invalid_argument(
                "--pta-analysis " + mode + " requires --word finite");
        }
        if (options.build_mode != BuildMode::Flatten) {
            throw std::invalid_argument(
                "--pta-analysis " + mode + " requires --build-mode flatten");
        }
    } else if (options.pta_cost_model.has_value() || options.pta_assume_lower_bounded ||
               options.pta_verify_geometry ||
               pta_max_pieces_explicit || pta_max_reach_nodes_explicit ||
               pta_max_reach_arcs_explicit || pta_timeout_explicit ||
               options.pta_prefix_cost || pta_prefix_query_timeout_explicit ||
               pta_prefix_max_regions_explicit || pta_prefix_optimizer_explicit ||
               pta_prefix_benchmark_explicit) {
        throw std::invalid_argument(
            "PTA cost options require --pta-analysis backward or mixed");
    }
    if (options.pta_analysis != PTAAnalysisMode::Mixed &&
        (pta_max_reach_nodes_explicit || pta_max_reach_arcs_explicit)) {
        throw std::invalid_argument(
            "PTA reachability limits require --pta-analysis mixed");
    }
    if ((options.pta_prefix_cost || pta_prefix_query_timeout_explicit ||
         pta_prefix_max_regions_explicit || pta_prefix_optimizer_explicit ||
         pta_prefix_benchmark_explicit) &&
        options.pta_analysis != PTAAnalysisMode::Mixed) {
        throw std::invalid_argument(
            "PTA prefix cost options require --pta-analysis mixed");
    }
    if (options.pta_prefix_cost && options.build_only) {
        throw std::invalid_argument(
            "--pta-prefix-cost cannot be combined with --build-only");
    }
    if (!options.pta_prefix_cost &&
        (pta_prefix_query_timeout_explicit ||
         pta_prefix_max_regions_explicit || pta_prefix_optimizer_explicit ||
         pta_prefix_benchmark_explicit)) {
        throw std::invalid_argument(
            "PTA prefix query options require --pta-prefix-cost");
    }
    return options;
}

std::string to_string(BuildMode mode) {
    return mode == BuildMode::Flatten ? "flatten" : "compflatten";
}

std::string to_string(WordMode mode) {
    return mode == WordMode::Finite ? "finite" : "infinite";
}

std::string to_string(StateMode mode) {
    return mode == StateMode::Symbolic ? "symbolic" : "concrete";
}

std::string verdict_to_string(monitaal::monitor_answer_e answer) {
    switch (answer) {
        case monitaal::POSITIVE:
            return "POSITIVE";
        case monitaal::NEGATIVE:
            return "NEGATIVE";
        case monitaal::INCONCLUSIVE:
        default:
            return "INCONCLUSIVE";
    }
}

}
