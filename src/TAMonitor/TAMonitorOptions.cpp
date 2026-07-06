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

size_t parse_positive_size(const std::string& value, const std::string& option) {
    const auto parsed = std::stoull(value);
    if (parsed == 0) {
        throw std::invalid_argument(option + " must be positive");
    }
    return static_cast<size_t>(parsed);
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

    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            throw std::invalid_argument(
                "Usage: TAMonitor [--trace path] [--formula path|--formula-inline text] "
                "[--build-mode flatten|compflatten] [--word finite|infinite] "
                "[--state symbolic|concrete] [--out path] [--max-valuations n] "
                "[--bdd-nodes n] [--bdd-cache n] [--bdd-max-increase n] "
                "[--emit-bdd-interface] [--build-only]\n"
                "Note: compflatten is construction/statistics-only in TAMonitor v1; "
                "runtime monitoring requires --build-mode flatten.");
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
        } else if (arg == "--build-only") {
            options.build_only = true;
        } else {
            throw std::invalid_argument("Unknown option: " + arg);
        }
    }

    if (options.formula_path.has_value() && options.formula_inline.has_value()) {
        throw std::invalid_argument("Provide at most one of --formula or --formula-inline");
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
