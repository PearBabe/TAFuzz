#include "TAMonitor.h"

#include <exception>
#include <iostream>

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
        if (options.build_only) {
            run.final_verdict = "NOT_RUN_BUILD_ONLY";
        } else {
            trace = tamonitor::parse_trace(options, build.proposition_order);
            run = tamonitor::run_monitor(build, trace, options);
        }
        tamonitor::write_report(options, formula, build, trace, run);

        std::cout << "TAMonitor completed\n";
        std::cout << "Formula satisfiable: " << build.positive.satisfiability << '\n';
        std::cout << "Final verdict: " << run.final_verdict << '\n';
        std::cout << "Output: " << options.output_dir << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "TAMonitor error: " << e.what() << '\n';
        return 1;
    }
}
