// 本文件在同一 snapshot 上重复测量 point、interval、Federation 与 JSON 热/冷路径。

#include "PrefixCostAnalyzer.h"
#include "PrefixCostOutput.h"
#include "PricedDBMOps.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace tamonitor::pta;
using Clock = std::chrono::steady_clock;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

pardibaal::DBM interval(
    pardibaal::val_t lower,
    pardibaal::val_t upper) {
    auto zone = pardibaal::DBM::unconstrained(2);
    zone.restrict(0, 1, pardibaal::bound_t::non_strict(-lower));
    zone.restrict(1, 0, pardibaal::bound_t::non_strict(upper));
    zone.close();
    return zone;
}

WeightedAutomatonView automaton() {
    auto guard = pardibaal::DBM::unconstrained(2);
    guard.restrict(0, 1, pardibaal::bound_t::non_strict(-5));
    guard.close();
    return WeightedAutomatonView(
        2, 0,
        {WeightedLocation(0, interval(0, 5), "source"),
         WeightedLocation(1, pardibaal::DBM::unconstrained(2), "goal")},
        {WeightedEdge(EdgeId{0, 0}, 0, 1, guard, {}, "finish")});
}

CostModel costs() {
    CostModel model;
    model.default_location_rate = 1;
    model.edge_costs[EdgeId{0, 0}] = 2;
    return model;
}

struct Summary {
    std::string category;
    std::string backend;
    std::vector<std::uint64_t> wall_us;
    std::vector<std::uint64_t> core_us;
    std::vector<std::uint64_t> optimizer_us;
};

std::uint64_t percentile(std::vector<std::uint64_t> values, double quantile) {
    std::sort(values.begin(), values.end());
    const auto index = std::min<std::size_t>(
        values.size() - 1,
        static_cast<std::size_t>(values.size() * quantile));
    return values[index];
}

std::string backend_name(PrefixOptimizerBackend backend) {
    return to_string(backend);
}

RuntimeSymbolicState state_with(
    std::uint64_t id,
    pardibaal::Federation domain) {
    return RuntimeSymbolicState{id, 0, std::move(domain)};
}

Summary benchmark_queries(
    const PrefixCostAnalyzer& analyzer,
    const std::string& category,
    PrefixOptimizerBackend backend,
    const pardibaal::Federation& domain,
    std::size_t iterations,
    std::ofstream& raw,
    SymbolicCostToGoResult* representative) {
    PrefixQueryOptions options;
    options.optimizer = backend;
    options.timeout_ms = 0;
    options.max_regions = 100'000;

    // 预热 thread_local Z3 context、allocator 和 instruction cache。
    for (std::size_t warmup = 0; warmup < 100; ++warmup) {
        (void)analyzer.query({state_with(0, domain)}, options);
    }

    Summary summary{category, backend_name(backend), {}, {}, {}};
    summary.wall_us.reserve(iterations);
    summary.core_us.reserve(iterations);
    summary.optimizer_us.reserve(iterations);
    for (std::size_t iteration = 0; iteration < iterations; ++iteration) {
        const auto started = Clock::now();
        auto result = analyzer.query(
            {state_with(static_cast<std::uint64_t>(iteration), domain)}, options);
        const auto wall_us = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::microseconds>(
                Clock::now() - started)
                .count());
        require(result.domain_status == SymbolicDomainStatus::Complete &&
                    result.aggregate.kind == CostValueKind::Finite &&
                    result.aggregate.value == BigRational(3) &&
                    result.aggregate.attained && result.next_arc == 0 &&
                    result.next_edge == EdgeId{0, 0} &&
                    result.delay_value_or_limit == BigRational(1),
                "benchmark query changed cost/attained/witness");
        summary.wall_us.push_back(wall_us);
        summary.core_us.push_back(result.statistics.core_query_us);
        summary.optimizer_us.push_back(result.statistics.optimizer_us);
        raw << category << ',' << backend_name(backend) << ',' << iteration
            << ',' << wall_us << ',' << result.statistics.core_query_us
            << ',' << result.statistics.optimizer_us << ','
            << result.statistics.optimizer_calls << '\n';
        if (representative != nullptr && iteration == 0) {
            *representative = std::move(result);
        }
    }
    return summary;
}

void write_summary(std::ofstream& output, const Summary& summary) {
    const auto total = std::accumulate(
        summary.wall_us.begin(), summary.wall_us.end(), std::uint64_t(0));
    const double qps = total == 0
        ? 0.0
        : static_cast<double>(summary.wall_us.size()) * 1'000'000.0 /
              static_cast<double>(total);
    output << summary.category << ',' << summary.backend << ','
           << summary.wall_us.size() << ','
           << percentile(summary.wall_us, 0.50) << ','
           << percentile(summary.wall_us, 0.95) << ','
           << percentile(summary.wall_us, 0.99) << ','
           << *std::max_element(summary.wall_us.begin(), summary.wall_us.end())
           << ',' << percentile(summary.core_us, 0.95) << ','
           << percentile(summary.optimizer_us, 0.95) << ',' << qps << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        std::size_t iterations = 10'000;
        std::filesystem::path output_dir = "prefix_benchmark";
        for (int index = 1; index < argc; ++index) {
            const std::string argument = argv[index];
            if (argument == "--iterations" && index + 1 < argc) {
                iterations = std::stoull(argv[++index]);
            } else if (argument == "--output" && index + 1 < argc) {
                output_dir = argv[++index];
            } else {
                throw std::invalid_argument("unknown/missing argument: " + argument);
            }
        }
        require(iterations > 0, "iterations must be positive");
        std::filesystem::create_directories(output_dir);

        const auto model = automaton();
        const auto model_costs = costs();
        const auto precompute_started = Clock::now();
        const auto graph = compute_reachable_zone_graph(model, GoalSpec{{1}});
        const auto snapshot = solve_mixed(model, graph, model_costs, SolverOptions{});
        const auto precompute_us = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::microseconds>(
                Clock::now() - precompute_started)
                .count());
        PrefixCostAnalyzer analyzer(model, model_costs, snapshot);

        std::ofstream raw(output_dir / "query_samples.csv");
        raw << "category,backend,iteration,wall_us,core_us,optimizer_us,optimizer_calls\n";
        std::ofstream summary_file(output_dir / "summary.csv");
        summary_file << "category,backend,iterations,p50_us,p95_us,p99_us,max_us,"
                        "core_p95_us,optimizer_p95_us,qps\n";

        const auto point = pardibaal::Federation(interval(4, 4));
        const auto whole_interval = pardibaal::Federation(interval(0, 4));
        pardibaal::Federation federation(interval(0, 1));
        federation.add(interval(3, 4));

        std::vector<Summary> summaries;
        SymbolicCostToGoResult representative;
        summaries.push_back(benchmark_queries(
            analyzer, "point_fast_path", PrefixOptimizerBackend::Z3,
            point, iterations, raw, &representative));
        for (const auto backend : {
                 PrefixOptimizerBackend::Z3,
                 PrefixOptimizerBackend::RomeoDBM,
                 PrefixOptimizerBackend::CrossCheck}) {
            summaries.push_back(benchmark_queries(
                analyzer, "interval", backend, whole_interval,
                iterations, raw, nullptr));
            summaries.push_back(benchmark_queries(
                analyzer, "federation_2dbm", backend, federation,
                iterations, raw, nullptr));
        }
        for (const auto& summary : summaries) write_summary(summary_file, summary);

        PrefixCostRun json_run;
        json_run.target_automaton = "benchmark";
        json_run.optimizer = PrefixOptimizerBackend::Z3;
        json_run.mixed_precompute_us = precompute_us;
        json_run.records.reserve(iterations);
        for (std::size_t index = 0; index < iterations; ++index) {
            PrefixCostRecord record;
            record.prefix_index = index;
            record.status = PrefixRecordStatus::Evaluated;
            record.runtime_states = {state_with(index, point)};
            record.result = representative;
            json_run.records.push_back(std::move(record));
        }
        const auto json_stats = write_prefix_cost_outputs(
            output_dir / "json_10000", json_run);
        std::ofstream metadata(output_dir / "metadata.txt");
        metadata << "iterations=" << iterations << '\n'
                 << "precompute_us=" << precompute_us << '\n'
                 << "json_file_write_us=" << json_stats.file_write_us << '\n'
                 << "json_serialization_p50_us="
                 << percentile(json_stats.serialization_us, 0.50) << '\n'
                 << "json_serialization_p95_us="
                 << percentile(json_stats.serialization_us, 0.95) << '\n'
                 << "json_serialization_p99_us="
                 << percentile(json_stats.serialization_us, 0.99) << '\n';

        std::cout << "PrefixPerformanceBenchmark: iterations=" << iterations
                  << " precompute_us=" << precompute_us
                  << " output=" << output_dir << '\n';
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "PrefixPerformanceBenchmark failed: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
