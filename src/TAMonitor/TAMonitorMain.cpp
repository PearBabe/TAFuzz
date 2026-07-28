// 本文件实现 TAMonitor 主流程，并把 PTA 作为默认关闭的独立分析旁路接入。

#include "TAMonitor.h"
#include "PTA/PTAAnalysis.h"
#include "PTA/PrefixCostOutput.h"
#include "PTA/PrefixRuntime.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <optional>

namespace {

std::string interval_to_string(monitaal::interval_t interval) {
    if (interval.first == interval.second) {
        return std::to_string(interval.first);
    }
    return "[" + std::to_string(interval.first) + "," + std::to_string(interval.second) + "]";
}

void print_step_verdicts(const tamonitor::RunResult& run) {
    std::cout << "Step verdicts:\n";
    if (run.steps.empty()) {
        std::cout << "  (no trace events processed)\n";
        return;
    }

    for (const auto& step : run.steps) {
        std::cout << "  step " << step.index
                  << ": time=" << interval_to_string(step.time)
                  << ", label=" << step.canonical_label
                  << ", human_label=" << step.human_label
                  << ", verdict=" << step.verdict
                  << ", positive_states=" << step.positive_states
                  << ", negative_states=" << step.negative_states
                  << ", advanced=" << (step.monitor_advanced ? "true" : "false")
                  << '\n';
    }
}

}

int main(int argc, const char** argv) {
    try {
        tamonitor::Options options = tamonitor::parse_options(argc, argv);
        if (options.build_mode == tamonitor::BuildMode::Compflatten && !options.build_only) {
            throw std::runtime_error(
                "unsupported_runtime_mode: compflatten runtime monitoring is not implemented in TAMonitor v1; "
                "use --build-only for compflatten construction/statistics or --build-mode flatten for verified runtime monitoring");
        }

        const std::string formula = tamonitor::read_formula(options);
        tamonitor::BuildPair build = tamonitor::build_automata_pair(formula, options);
        std::vector<tamonitor::TimedEvent> trace;
        tamonitor::RunResult run;
        bool pta_success = true;
        std::optional<tamonitor::pta::PTAExecutionResult> pta_result;
        std::optional<tamonitor::pta::PTAMixedExecutionResult> mixed_pta_result;
        std::optional<tamonitor::pta::PrefixRuntimeObserver> prefix_observer;
        if (options.build_only) {
            run.final_verdict = "NOT_RUN_BUILD_ONLY";
        } else {
            trace = tamonitor::parse_trace(options, build.proposition_order);
            if (options.pta_prefix_cost) {
                const auto precompute_start = std::chrono::steady_clock::now();
                mixed_pta_result.emplace(
                    tamonitor::pta::run_mixed_pta_analysis(build, options));
                const auto precompute_us = static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::microseconds>(
                        std::chrono::steady_clock::now() - precompute_start)
                        .count());
                tamonitor::pta::PrefixQueryOptions query_options;
                query_options.optimizer =
                    tamonitor::pta::parse_prefix_optimizer_backend(
                        options.pta_prefix_optimizer);
                query_options.timeout_ms = options.pta_prefix_query_timeout_ms;
                query_options.max_regions = options.pta_prefix_max_regions;
                prefix_observer.emplace(
                    *mixed_pta_result, query_options, precompute_us);
                run = tamonitor::run_monitor(
                    build, trace, options, &*prefix_observer);
            } else {
                run = tamonitor::run_monitor(build, trace, options);
            }
        }
        tamonitor::write_report(options, formula, build, trace, run);

        if (options.pta_analysis == tamonitor::PTAAnalysisMode::Backward) {
            pta_result.emplace(tamonitor::pta::run_pta_analysis(build, options));
            tamonitor::pta::write_pta_outputs(options.output_dir, *pta_result);
            pta_success = tamonitor::pta::is_successful(*pta_result);
        } else if (options.pta_analysis == tamonitor::PTAAnalysisMode::Mixed) {
            if (!mixed_pta_result.has_value()) {
                mixed_pta_result.emplace(
                    tamonitor::pta::run_mixed_pta_analysis(build, options));
            }
            tamonitor::pta::write_mixed_pta_outputs(
                options.output_dir, *mixed_pta_result);
            pta_success = tamonitor::pta::is_successful(*mixed_pta_result);
            if (prefix_observer.has_value()) {
                (void)tamonitor::pta::write_prefix_cost_outputs(
                    options.output_dir, prefix_observer->run());
                if (options.pta_prefix_benchmark_iterations != 0) {
                    const auto benchmark =
                        prefix_observer->benchmark_evaluated_prefixes(
                            options.pta_prefix_benchmark_iterations);
                    tamonitor::pta::write_prefix_replay_benchmark(
                        options.output_dir, benchmark);
                }
            }
        }

        std::cout << "TAMonitor completed\n";
        std::cout << "Formula satisfiable: " << build.positive.satisfiability << '\n';
        if (options.print_steps) {
            print_step_verdicts(run);
        }
        std::cout << "Final verdict: " << run.final_verdict << '\n';
        std::cout << "Output: " << options.output_dir << '\n';
        if (pta_result.has_value()) {
            std::cout << "PTA analysis status: "
                      << tamonitor::pta::to_string(pta_result->snapshot.status())
                      << '\n';
            std::cout << "PTA output: "
                      << (options.output_dir / "pta_analysis.json") << '\n';
        } else if (mixed_pta_result.has_value()) {
            std::cout << "PTA analysis status: "
                      << tamonitor::pta::to_string(mixed_pta_result->snapshot.status())
                      << '\n';
            std::cout << "PTA output: "
                      << (options.output_dir / "pta_analysis.json") << '\n';
        }
        return pta_success ? 0 : 2;
    } catch (const std::exception& e) {
        std::cerr << "TAMonitor error: " << e.what() << '\n';
        return 1;
    }
}
