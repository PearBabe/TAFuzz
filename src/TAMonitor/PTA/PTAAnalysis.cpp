// 本文件把 MightyPPL 生成的 MoniTAal TA 编译为 WTA 视图，并输出独立分析结果。

#include "PTAAnalysis.h"

#include "PricedDBMOps.h"

#include <Fixpoint.h>
#include <pugixml.hpp>
#include <state.h>
#include <z3.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

#ifndef TAMONITOR_PARDIBAAL_COMMIT
#define TAMONITOR_PARDIBAAL_COMMIT "unknown"
#endif

namespace tamonitor::pta {
namespace {

struct ParsedCostModel {
    std::string target = "negative";
    CostModel costs;
    std::string source = "built-in:location-rate=1,edge-cost=0";
};

void validate_attributes(
    const pugi::xml_node& node,
    const std::set<std::string>& allowed,
    const std::string& context) {
    for (const auto attribute : node.attributes()) {
        if (allowed.find(attribute.name()) == allowed.end()) {
            throw std::invalid_argument(
                "Unknown PTA cost model attribute " + context + "@" +
                attribute.name());
        }
    }
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
    const std::string numerator = integer_string(value.numerator());
    if (value.denominator() == 1) {
        return numerator;
    }
    return numerator + "/" + integer_string(value.denominator());
}

BigInt parse_integer(const std::string& text, const std::string& context) {
    if (text.empty()) {
        throw std::invalid_argument(context + " is empty");
    }
    std::size_t index = 0;
    if (text.front() == '+' || text.front() == '-') {
        index = 1;
    }
    if (index == text.size()) {
        throw std::invalid_argument(context + " is not an integer: " + text);
    }
    for (; index < text.size(); ++index) {
        if (!std::isdigit(static_cast<unsigned char>(text[index]))) {
            throw std::invalid_argument(context + " is not an integer: " + text);
        }
    }
    std::istringstream input(text);
    BigInt value;
    input >> value;
    if (!input || !input.eof()) {
        throw std::invalid_argument(context + " is not an integer: " + text);
    }
    return value;
}

std::uint32_t parse_u32(const pugi::xml_attribute& attribute,
                        const std::string& context) {
    if (!attribute) {
        throw std::invalid_argument("Missing " + context);
    }
    const std::string text = attribute.value();
    if (text.empty()) {
        throw std::invalid_argument(context + " must be an unsigned integer");
    }
    for (const char character : text) {
        if (!std::isdigit(static_cast<unsigned char>(character))) {
            throw std::invalid_argument(context + " must be an unsigned integer");
        }
    }
    std::size_t consumed = 0;
    unsigned long long value = 0;
    try {
        value = std::stoull(text, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(context + " must be an unsigned integer");
    }
    if (consumed != text.size() ||
        value > std::numeric_limits<std::uint32_t>::max()) {
        throw std::invalid_argument(context + " exceeds uint32 range");
    }
    return static_cast<std::uint32_t>(value);
}

ParsedCostModel load_cost_model(
    const std::optional<std::filesystem::path>& path) {
    ParsedCostModel parsed;
    parsed.costs.default_location_rate = 1;
    parsed.costs.default_edge_cost = 0;
    if (!path.has_value()) {
        return parsed;
    }

    pugi::xml_document document;
    const auto loaded = document.load_file(path->c_str());
    if (!loaded) {
        throw std::runtime_error(
            "Could not parse PTA cost model " + path->string() + ": " +
            loaded.description());
    }
    const auto root = document.child("pta-cost-model");
    if (!root) {
        throw std::invalid_argument("PTA cost model root must be <pta-cost-model>");
    }
    validate_attributes(root, {"version", "target"}, "pta-cost-model");
    if (std::string(root.attribute("version").value()) != "1") {
        throw std::invalid_argument("PTA cost model version must be 1");
    }
    if (const auto target = root.attribute("target")) {
        parsed.target = target.value();
    }
    if (parsed.target != "negative" && parsed.target != "positive") {
        throw std::invalid_argument("PTA cost model target must be negative or positive");
    }

    if (const auto defaults = root.child("defaults")) {
        validate_attributes(
            defaults, {"location-rate", "edge-cost"}, "defaults");
        if (const auto rate = defaults.attribute("location-rate")) {
            parsed.costs.default_location_rate =
                parse_integer(rate.value(), "defaults location-rate");
        }
        if (const auto cost = defaults.attribute("edge-cost")) {
            parsed.costs.default_edge_cost =
                parse_integer(cost.value(), "defaults edge-cost");
        }
    }

    for (const auto location : root.children("location")) {
        validate_attributes(location, {"id", "rate"}, "location");
        const LocationId id = parse_u32(location.attribute("id"), "location id");
        const auto rate_attribute = location.attribute("rate");
        if (!rate_attribute) {
            throw std::invalid_argument("PTA location override requires rate");
        }
        const BigInt rate = parse_integer(rate_attribute.value(), "location rate");
        if (!parsed.costs.location_rates.emplace(id, rate).second) {
            throw std::invalid_argument("Duplicate PTA location override id " +
                                        std::to_string(id));
        }
    }

    for (const auto edge : root.children("edge")) {
        validate_attributes(edge, {"source", "ordinal", "cost"}, "edge");
        const EdgeId id{
            parse_u32(edge.attribute("source"), "edge source"),
            parse_u32(edge.attribute("ordinal"), "edge ordinal")};
        const auto cost_attribute = edge.attribute("cost");
        if (!cost_attribute) {
            throw std::invalid_argument("PTA edge override requires cost");
        }
        const BigInt cost = parse_integer(cost_attribute.value(), "edge cost");
        if (!parsed.costs.edge_costs.emplace(id, cost).second) {
            throw std::invalid_argument("Duplicate PTA edge override " +
                                        std::to_string(id.source) + ":" +
                                        std::to_string(id.ordinal));
        }
    }

    std::size_t defaults_count = 0;
    for (const auto child : root.children()) {
        if (child.type() != pugi::node_element) {
            continue;
        }
        const std::string name = child.name();
        if (name == "defaults") {
            ++defaults_count;
        }
        if (name != "defaults" && name != "location" && name != "edge") {
            throw std::invalid_argument("Unknown PTA cost model element: " + name);
        }
    }
    if (defaults_count > 1) {
        throw std::invalid_argument("PTA cost model contains duplicate <defaults>");
    }

    parsed.source = path->string();
    return parsed;
}

WeightedAutomatonView compile_automaton(const monitaal::TA& automaton) {
    const auto dimension = automaton.number_of_clocks();
    std::vector<WeightedLocation> locations;
    std::vector<WeightedEdge> edges;
    locations.reserve(automaton.locations().size());

    for (const auto& [location_id, location] : automaton.locations()) {
        locations.emplace_back(
            location_id, location.invariant_zone(dimension), location.name());
        const auto& outgoing = automaton.edges_from(location_id);
        for (std::size_t ordinal = 0; ordinal < outgoing.size(); ++ordinal) {
            if (ordinal > std::numeric_limits<std::uint32_t>::max()) {
                throw std::overflow_error("PTA edge ordinal exceeds uint32 range");
            }
            const auto& edge = outgoing[ordinal];
            edges.emplace_back(
                EdgeId{location_id, static_cast<std::uint32_t>(ordinal)},
                edge.from(), edge.to(), edge.guard_zone(dimension), edge.reset(),
                edge.label());
        }
    }
    return WeightedAutomatonView(
        dimension, automaton.initial_location(), std::move(locations), std::move(edges));
}

GoalSpec accepting_goals(const monitaal::TA& automaton) {
    GoalSpec goals;
    for (const auto& [id, location] : automaton.locations()) {
        if (location.is_accept()) {
            goals.locations.push_back(id);
        }
    }
    return goals;
}

void verify_geometric_support(
    const monitaal::TA& source,
    const AnalysisSnapshot& snapshot) {
    monitaal::symbolic_state_map_t<monitaal::symbolic_state_t> goal_states;
    for (const auto& [location_id, location] : source.locations()) {
        if (!location.is_accept()) {
            continue;
        }
        auto state = monitaal::symbolic_state_t::unconstrained(
            location_id, source.number_of_clocks());
        state.restrict(location.invariant());
        goal_states.insert(std::move(state));
    }

    auto ordinary =
        monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(goal_states, source);
    for (const auto& [_, goal] : goal_states) {
        ordinary.insert(goal);
    }

    const auto observer_clock = source.number_of_clocks();
    for (const auto& [location_id, _] : source.locations()) {
        pardibaal::Federation priced_support;
        for (const auto& piece : snapshot.pieces(location_id)) {
            priced_support.add(piece.weighted_zone.zone);
        }
        for (const auto& region : snapshot.unbounded_regions()) {
            if (region.location == location_id) {
                priced_support.add(region.zone);
            }
        }

        if (!ordinary.has_state(location_id)) {
            if (!priced_support.is_empty()) {
                throw std::logic_error(
                    "PTA geometric oracle mismatch at location " +
                    std::to_string(location_id) + ": priced support is non-empty");
            }
            continue;
        }

        auto ordinary_support = ordinary.at(location_id).federation();
        ordinary_support.remove_clock(observer_clock);
        if (!priced_support.is_exact_equal(ordinary_support)) {
            throw std::logic_error(
                "PTA geometric oracle mismatch at location " +
                std::to_string(location_id));
        }
    }
}

monitaal::symbolic_state_map_t<monitaal::symbolic_state_t>
ordinary_goal_predecessors(const monitaal::TA& source) {
    monitaal::symbolic_state_map_t<monitaal::symbolic_state_t> goal_states;
    for (const auto& [location_id, location] : source.locations()) {
        if (!location.is_accept()) {
            continue;
        }
        auto state = monitaal::symbolic_state_t::unconstrained(
            location_id, source.number_of_clocks());
        state.restrict(location.invariant());
        goal_states.insert(std::move(state));
    }

    auto predecessors =
        monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(goal_states, source);
    for (const auto& [_, goal] : goal_states) {
        predecessors.insert(goal);
    }
    return predecessors;
}

void verify_mixed_geometric_support(
    const monitaal::TA& source,
    const MixedAnalysisSnapshot& snapshot) {
    const ReachabilitySnapshot* reachability = snapshot.reachability();
    if (reachability == nullptr || !reachability->exact() || !snapshot.exact()) {
        throw std::logic_error(
            "mixed geometric oracle requires complete forward/backward snapshots");
    }

    const auto ordinary = ordinary_goal_predecessors(source);
    const auto observer_clock = source.number_of_clocks();
    for (const auto& [location_id, _] : source.locations()) {
        pardibaal::Federation actual;
        for (const auto& [node_id, pieces] : snapshot.all_pieces()) {
            if (reachability->node(node_id).location != location_id) {
                continue;
            }
            for (const auto& piece : pieces) {
                actual.add(piece.weighted_zone.zone);
            }
        }
        for (const auto& region : snapshot.unbounded_regions()) {
            if (region.location == location_id) {
                actual.add(region.zone);
            }
        }

        pardibaal::Federation expected = reachability->support(location_id);
        if (!ordinary.has_state(location_id)) {
            expected = pardibaal::Federation{};
        } else {
            auto ordinary_support = ordinary.at(location_id).federation();
            ordinary_support.remove_clock(observer_clock);
            expected.intersection(ordinary_support);
        }
        if (!actual.is_exact_equal(expected)) {
            throw std::logic_error(
                "mixed geometric oracle mismatch at location " +
                std::to_string(location_id));
        }
    }
}

bool has_unit_time_cost_model(
    const WeightedAutomatonView& automaton,
    const CostModel& costs) {
    for (const auto& location : automaton.locations()) {
        if (costs.location_rate(location.id) != 1) {
            return false;
        }
    }
    for (const auto& edge : automaton.edges()) {
        if (costs.edge_cost(edge.id) != 0) {
            return false;
        }
    }
    return true;
}

bool ordinary_goal_reachable_within(
    const monitaal::TA& source,
    pardibaal::val_t bound,
    bool strict) {
    monitaal::symbolic_state_map_t<monitaal::symbolic_state_t> targets;
    const auto observer_clock = source.number_of_clocks();
    for (const auto& [location_id, location] : source.locations()) {
        if (!location.is_accept()) {
            continue;
        }
        auto target = monitaal::symbolic_state_t::unconstrained(
            location_id, source.number_of_clocks());
        target.restrict(location.invariant());
        target.restrict(monitaal::constraints_t{
            strict
                ? pardibaal::difference_bound_t::upper_strict(
                      observer_clock, bound)
                : pardibaal::difference_bound_t::upper_non_strict(
                      observer_clock, bound)});
        targets.insert(std::move(target));
    }

    auto predecessors =
        monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(targets, source);
    for (const auto& [_, target] : targets) {
        predecessors.insert(target);
    }
    if (!predecessors.has_state(source.initial_location())) {
        return false;
    }
    const monitaal::symbolic_state_t initial(
        source.initial_location(), source.number_of_clocks());
    return initial.is_included_in(predecessors.at(source.initial_location()));
}

void validate_cost_overrides(
    const WeightedAutomatonView& automaton,
    const CostModel& costs) {
    for (const auto& [location, _] : costs.location_rates) {
        (void)automaton.location(location);
    }
    std::set<EdgeId> edges;
    for (const auto& edge : automaton.edges()) {
        edges.insert(edge.id);
    }
    for (const auto& [edge, _] : costs.edge_costs) {
        if (edges.find(edge) == edges.end()) {
            throw std::invalid_argument(
                "PTA cost model references unknown edge " +
                std::to_string(edge.source) + ":" + std::to_string(edge.ordinal));
        }
    }
}

const char* delay_kind_name(DelayWitnessKind kind) {
    switch (kind) {
        case DelayWitnessKind::ZERO: return "zero";
        case DelayWitnessKind::LOWER_FACET: return "lower_facet";
        case DelayWitnessKind::UPPER_FACET: return "upper_facet";
    }
    return "unknown";
}

void write_optional_edge(std::ostream& out, const std::optional<EdgeId>& edge) {
    if (!edge.has_value()) {
        out << "null";
        return;
    }
    out << "{\"source\":" << edge->source
        << ",\"ordinal\":" << edge->ordinal << '}';
}

void write_witness(std::ostream& out, const DerivationWitness& witness) {
    out << "{\"goal_seed\":" << (witness.is_goal_seed ? "true" : "false")
        << ",\"delay_kind\":\"" << delay_kind_name(witness.delay_kind) << "\""
        << ",\"facet_clock\":";
    if (witness.facet_clock.has_value()) out << *witness.facet_clock; else out << "null";
    out << ",\"facet_bound\":";
    if (witness.facet_bound.has_value()) {
        out << '"' << *witness.facet_bound << '"';
    } else {
        out << "null";
    }
    out << ",\"next_edge\":";
    write_optional_edge(out, witness.next_edge);
    out << ",\"successor_piece\":";
    if (witness.successor_piece.has_value()) out << *witness.successor_piece; else out << "null";
    out << ",\"successor_unbounded_region\":";
    if (witness.successor_unbounded_region.has_value()) {
        out << *witness.successor_unbounded_region;
    } else {
        out << "null";
    }
    out << ",\"unbounded_delay\":"
        << (witness.unbounded_delay ? "true" : "false") << '}';
}

void write_mixed_witness(
    std::ostream& out,
    const MixedDerivationWitness& witness) {
    out << "{\"goal_seed\":" << (witness.is_goal_seed ? "true" : "false")
        << ",\"delay_kind\":\"" << delay_kind_name(witness.delay_kind) << "\""
        << ",\"facet_clock\":";
    if (witness.facet_clock.has_value()) out << *witness.facet_clock; else out << "null";
    out << ",\"facet_bound\":";
    if (witness.facet_bound.has_value()) {
        out << '"' << *witness.facet_bound << '"';
    } else {
        out << "null";
    }
    out << ",\"next_arc\":";
    if (witness.next_arc.has_value()) out << *witness.next_arc; else out << "null";
    out << ",\"next_edge\":";
    write_optional_edge(out, witness.next_edge);
    out << ",\"successor_node\":";
    if (witness.successor_node.has_value()) {
        out << *witness.successor_node;
    } else {
        out << "null";
    }
    out << ",\"successor_piece\":";
    if (witness.successor_piece.has_value()) out << *witness.successor_piece; else out << "null";
    out << ",\"successor_unbounded_region\":";
    if (witness.successor_unbounded_region.has_value()) {
        out << *witness.successor_unbounded_region;
    } else {
        out << "null";
    }
    out << ",\"unbounded_delay\":"
        << (witness.unbounded_delay ? "true" : "false") << '}';
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
                << ",\"strict\":" << (bound.is_strict() ? "true" : "false")
                << '}';
        }
    }
    out << "]}";
}

void write_integer_array(std::ostream& out, const std::vector<BigInt>& values) {
    out << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) out << ',';
        out << '"' << integer_string(values[i]) << '"';
    }
    out << ']';
}

void write_clock_array(
    std::ostream& out,
    const std::vector<pardibaal::dim_t>& clocks) {
    out << '[';
    for (std::size_t i = 0; i < clocks.size(); ++i) {
        if (i != 0) out << ',';
        out << clocks[i];
    }
    out << ']';
}

bool is_goal_location(const GoalSpec& goals, LocationId location) {
    return std::find(goals.locations.begin(), goals.locations.end(), location) !=
           goals.locations.end();
}

const char* mixed_backward_phase_status(MixedSolverStatus status) {
    switch (status) {
        case MixedSolverStatus::Complete:
        case MixedSolverStatus::Unreachable:
        case MixedSolverStatus::UnboundedBelow:
            return "complete";
        case MixedSolverStatus::AssumptionRequired:
            return "not_run_assumption_required";
        case MixedSolverStatus::IncompleteForwardResourceLimit:
            return "not_run_incomplete_forward";
        case MixedSolverStatus::IncompleteBackwardResourceLimit:
            return "incomplete_resource_limit";
    }
    throw std::logic_error("unknown MixedSolverStatus");
}

bool mixed_backward_phase_started(MixedSolverStatus status) {
    return status != MixedSolverStatus::AssumptionRequired &&
           status != MixedSolverStatus::IncompleteForwardResourceLimit;
}

template <typename Result>
void write_automaton(
    std::ostream& out,
    const Result& result) {
    out << "{\"dimension\":" << result.automaton.dimension()
        << ",\"initial_location\":" << result.automaton.initial_location()
        << ",\"locations\":[";
    bool first = true;
    for (const auto& location : result.automaton.locations()) {
        if (!first) out << ',';
        first = false;
        out << "{\"id\":" << location.id
            << ",\"name\":\"" << json_escape(location.name) << "\""
            << ",\"goal\":"
            << (is_goal_location(result.goals, location.id) ? "true" : "false")
            << ",\"rate\":\""
            << integer_string(result.costs.location_rate(location.id)) << "\""
            << ",\"invariant\":";
        write_dbm(out, location.invariant);
        out << '}';
    }
    out << "],\"edges\":[";
    first = true;
    for (const auto& edge : result.automaton.edges()) {
        if (!first) out << ',';
        first = false;
        out << "{\"id\":{\"source\":" << edge.id.source
            << ",\"ordinal\":" << edge.id.ordinal << "}"
            << ",\"source\":" << edge.source
            << ",\"target\":" << edge.target
            << ",\"label\":\"" << json_escape(edge.label) << "\""
            << ",\"cost\":\"" << integer_string(result.costs.edge_cost(edge.id))
            << "\",\"resets\":";
        write_clock_array(out, edge.resets);
        out << ",\"guard\":";
        write_dbm(out, edge.guard);
        out << '}';
    }
    out << "]}";
}

void write_analysis_metadata(
    std::ostream& out,
    const PTAExecutionResult& result) {
    out << ",\"analysis_status\":\"" << to_string(result.snapshot.status()) << "\""
        << ",\"snapshot_exact\":"
        << (result.snapshot.exact() ? "true" : "false")
        << ",\"lower_bound_declared\":"
        << (result.snapshot.lower_bound_assumed() ? "true" : "false");
}

void write_finite_piece(
    std::ostream& out,
    const PricedPiece& piece,
    const PTAExecutionResult& result) {
    const auto delta = offset(piece.weighted_zone.zone);
    BigInt remaining_constant = -piece.weighted_zone.offset_weight;
    std::vector<BigInt> remaining_coefficients = piece.weighted_zone.rates;
    for (std::size_t i = 0; i < remaining_coefficients.size(); ++i) {
        remaining_constant += piece.weighted_zone.rates[i] * delta[i];
        remaining_coefficients[i] = -remaining_coefficients[i];
    }

    out << "{\"kind\":\"finite\",\"piece_id\":" << piece.id
        << ",\"location\":" << piece.location
        << ",\"offset_weight\":\""
        << integer_string(piece.weighted_zone.offset_weight) << "\""
        << ",\"offset\":";
    write_integer_array(out, delta);
    out << ",\"rates\":";
    write_integer_array(out, piece.weighted_zone.rates);
    out << ",\"remaining_cost\":{\"constant\":\""
        << integer_string(remaining_constant) << "\",\"coefficients\":";
    write_integer_array(out, remaining_coefficients);
    out << "},\"attained\":" << (piece.weighted_zone.attained ? "true" : "false")
        << ",\"zone\":";
    write_dbm(out, piece.weighted_zone.zone);
    out << ",\"witness\":";
    write_witness(out, piece.witness);
    write_analysis_metadata(out, result);
    out << '}';
}

void write_mixed_finite_piece(
    std::ostream& out,
    const MixedPricedPiece& piece,
    const PTAMixedExecutionResult& result) {
    const auto delta = offset(piece.weighted_zone.zone);
    BigInt remaining_constant = -piece.weighted_zone.offset_weight;
    std::vector<BigInt> remaining_coefficients = piece.weighted_zone.rates;
    for (std::size_t i = 0; i < remaining_coefficients.size(); ++i) {
        remaining_constant += piece.weighted_zone.rates[i] * delta[i];
        remaining_coefficients[i] = -remaining_coefficients[i];
    }

    out << "{\"kind\":\"finite\",\"piece_id\":" << piece.id
        << ",\"reachable_node_id\":" << piece.node
        << ",\"location\":" << piece.location
        << ",\"offset_weight\":\""
        << integer_string(piece.weighted_zone.offset_weight) << "\""
        << ",\"offset\":";
    write_integer_array(out, delta);
    out << ",\"rates\":";
    write_integer_array(out, piece.weighted_zone.rates);
    out << ",\"remaining_cost\":{\"constant\":\""
        << integer_string(remaining_constant) << "\",\"coefficients\":";
    write_integer_array(out, remaining_coefficients);
    out << "},\"attained\":"
        << (piece.weighted_zone.attained ? "true" : "false")
        << ",\"zone\":";
    write_dbm(out, piece.weighted_zone.zone);
    out << ",\"witness\":";
    write_mixed_witness(out, piece.witness);
    out << ",\"analysis_status\":\"" << to_string(result.snapshot.status())
        << "\",\"snapshot_exact\":"
        << (result.snapshot.exact() ? "true" : "false")
        << ",\"lower_bound_declared\":"
        << (result.snapshot.lower_bound_assumed() ? "true" : "false")
        << '}';
}

void write_summary(
    const std::filesystem::path& path,
    const PTAExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    const auto& statistics = result.snapshot.statistics();
    out << "{\n"
        << "  \"schema_version\": 1,\n"
        << "  \"algorithm\": \"Parrot-Lime-2020-backward-weighted-zones\",\n"
        << "  \"target_automaton\": \"" << json_escape(result.target_automaton) << "\",\n"
        << "  \"cost_model_source\": \"" << json_escape(result.cost_model_source) << "\",\n"
        << "  \"default_location_rate\": \""
        << integer_string(result.costs.default_location_rate) << "\",\n"
        << "  \"default_edge_cost\": \""
        << integer_string(result.costs.default_edge_cost) << "\",\n"
        << "  \"location_rate_overrides\": [";
    bool first_rate = true;
    for (const auto& [location, rate] : result.costs.location_rates) {
        if (!first_rate) out << ',';
        first_rate = false;
        out << "{\"location\":" << location << ",\"rate\":\""
            << integer_string(rate) << "\"}";
    }
    out << "],\n"
        << "  \"edge_cost_overrides\": [";
    bool first_cost = true;
    for (const auto& [edge, cost] : result.costs.edge_costs) {
        if (!first_cost) out << ',';
        first_cost = false;
        out << "{\"source\":" << edge.source
            << ",\"ordinal\":" << edge.ordinal << ",\"cost\":\""
            << integer_string(cost) << "\"}";
    }
    out << "],\n"
        << "  \"nonnegative_certified\": "
        << (result.nonnegative_certified ? "true" : "false") << ",\n"
        << "  \"lower_bound_declared\": "
        << (result.snapshot.lower_bound_assumed() ? "true" : "false") << ",\n"
        << "  \"status\": \"" << to_string(result.snapshot.status()) << "\",\n"
        << "  \"snapshot_exact\": " << (result.snapshot.exact() ? "true" : "false") << ",\n"
        << "  \"geometric_oracle\": {\"checked\":"
        << (result.geometric_oracle_checked ? "true" : "false")
        << ",\"equal\":"
        << (result.geometric_oracle_equal ? "true" : "false") << "},\n"
        << "  \"automaton\": ";
    write_automaton(out, result);
    out << ",\n"
        << "  \"initial_location\": " << result.automaton.initial_location() << ",\n"
        << "  \"initial_cost\": {\"kind\":\""
        << to_string(result.initial_cost.kind) << "\",\"value\":";
    if (result.initial_cost.kind == CostValueKind::Finite) {
        out << '"' << rational_string(result.initial_cost.value) << '"';
    } else {
        out << "null";
    }
    out << ",\"attained\":" << (result.initial_cost.attained ? "true" : "false")
        << ",\"exact\":" << (result.initial_cost.exact ? "true" : "false")
        << ",\"lower_bound_declared\":"
        << (result.initial_cost.lower_bound_assumed ? "true" : "false")
        << ",\"piece_id\":";
    if (result.initial_cost.piece_id.has_value()) {
        out << *result.initial_cost.piece_id;
    } else {
        out << "null";
    }
    out << ",\"unbounded_region_id\":";
    if (result.initial_cost.unbounded_region_id.has_value()) {
        out << *result.initial_cost.unbounded_region_id;
    } else {
        out << "null";
    }
    out << ",\"next_edge\":";
    write_optional_edge(out, result.initial_cost.next_edge);
    out << ",\"witness\":";
    if (result.initial_cost.witness.has_value()) {
        write_witness(out, *result.initial_cost.witness);
    } else {
        out << "null";
    }
    out << "},\n"
        << "  \"goals\": [";
    for (std::size_t i = 0; i < result.goals.locations.size(); ++i) {
        if (i != 0) out << ',';
        out << result.goals.locations[i];
    }
    out << "],\n"
        << "  \"statistics\": {"
        << "\"enqueued\":" << statistics.enqueued
        << ",\"accepted\":" << statistics.accepted
        << ",\"subsumed\":" << statistics.subsumed
        << ",\"action_predecessors\":" << statistics.action_predecessors
        << ",\"time_predecessor_pieces\":" << statistics.time_predecessor_pieces
        << ",\"unbounded_regions\":" << statistics.unbounded_regions
        << ",\"dominance_checks\":" << statistics.dominance_checks
        << ",\"dominance_unknown\":" << statistics.dominance_unknown
        << ",\"elapsed_ms\":" << statistics.elapsed_ms << "},\n"
        << "  \"dependencies\": {\"z3\":\""
        << json_escape(Z3_get_full_version()) << "\",\"pardibaal_commit\":\""
        << json_escape(TAMONITOR_PARDIBAAL_COMMIT) << "\"}\n"
        << "}\n";
}

void write_pieces(
    const std::filesystem::path& path,
    const PTAExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    for (const auto& [_, pieces] : result.snapshot.all_pieces()) {
        for (const auto& piece : pieces) {
            write_finite_piece(out, piece, result);
            out << '\n';
        }
    }
    for (const auto& region : result.snapshot.unbounded_regions()) {
        out << "{\"kind\":\"negative_infinity\",\"region_id\":"
            << region.id << ",\"location\":" << region.location << ",\"zone\":";
        write_dbm(out, region.zone);
        out << ",\"witness\":";
        write_witness(out, region.witness);
        write_analysis_metadata(out, result);
        out << "}\n";
    }
}

void write_mixed_summary(
    const std::filesystem::path& path,
    const PTAMixedExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    const ReachabilitySnapshot* reachability = result.snapshot.reachability();
    if (reachability == nullptr) {
        throw std::logic_error("mixed snapshot omitted its reachability graph");
    }
    const auto& reach_stats = reachability->statistics();
    const auto& mixed_stats = result.snapshot.statistics();
    const auto& back_stats = mixed_stats.backward;
    const auto& initial_cost = result.initial_cost.cost;

    out << "{\n"
        << "  \"schema_version\": 2,\n"
        << "  \"algorithm\": \"Romeo-style-exact-mixed-forward-backward-weighted-zones\",\n"
        << "  \"goal_semantics\": \"first_hit_terminal\",\n"
        << "  \"target_automaton\": \""
        << json_escape(result.target_automaton) << "\",\n"
        << "  \"cost_model_source\": \""
        << json_escape(result.cost_model_source) << "\",\n"
        << "  \"default_location_rate\": \""
        << integer_string(result.costs.default_location_rate) << "\",\n"
        << "  \"default_edge_cost\": \""
        << integer_string(result.costs.default_edge_cost) << "\",\n"
        << "  \"location_rate_overrides\": [";
    bool first = true;
    for (const auto& [location, rate] : result.costs.location_rates) {
        if (!first) out << ',';
        first = false;
        out << "{\"location\":" << location << ",\"rate\":\""
            << integer_string(rate) << "\"}";
    }
    out << "],\n  \"edge_cost_overrides\": [";
    first = true;
    for (const auto& [edge, cost] : result.costs.edge_costs) {
        if (!first) out << ',';
        first = false;
        out << "{\"source\":" << edge.source
            << ",\"ordinal\":" << edge.ordinal << ",\"cost\":\""
            << integer_string(cost) << "\"}";
    }
    out << "],\n"
        << "  \"nonnegative_certified\": "
        << (result.nonnegative_certified ? "true" : "false") << ",\n"
        << "  \"lower_bound_declared\": "
        << (result.snapshot.lower_bound_assumed() ? "true" : "false") << ",\n"
        << "  \"status\": \"" << to_string(result.snapshot.status()) << "\",\n"
        << "  \"snapshot_exact\": "
        << (result.snapshot.exact() ? "true" : "false") << ",\n"
        << "  \"forward\": {\"status\":\""
        << to_string(reachability->status()) << "\",\"exact\":"
        << (reachability->exact() ? "true" : "false")
        << ",\"initial_node\":";
    if (reachability->initial_node().has_value()) {
        out << *reachability->initial_node();
    } else {
        out << "null";
    }
    out << ",\"nodes\":" << reachability->nodes().size()
        << ",\"arcs\":" << reachability->arcs().size()
        << ",\"statistics\":{\"expanded\":" << reach_stats.expanded
        << ",\"nodes_created\":" << reach_stats.nodes_created
        << ",\"arcs_created\":" << reach_stats.arcs_created
        << ",\"successor_candidates\":" << reach_stats.successor_candidates
        << ",\"inclusion_reuses\":" << reach_stats.inclusion_reuses
        << ",\"empty_successors\":" << reach_stats.empty_successors
        << ",\"goal_cutoffs\":" << reach_stats.goal_cutoffs
        << ",\"node_limit_hit\":"
        << (reach_stats.node_limit_hit ? "true" : "false")
        << ",\"arc_limit_hit\":"
        << (reach_stats.arc_limit_hit ? "true" : "false")
        << ",\"timeout_hit\":"
        << (reach_stats.timeout_hit ? "true" : "false")
        << ",\"elapsed_ms\":" << reach_stats.elapsed_ms << "}},\n"
        << "  \"backward\": {\"status\":\""
        << mixed_backward_phase_status(result.snapshot.status())
        << "\",\"started\":"
        << (mixed_backward_phase_started(result.snapshot.status())
                ? "true" : "false")
        << ",\"exact\":" << (result.snapshot.exact() ? "true" : "false")
        << ",\"goal_seeds\":" << mixed_stats.goal_seeds
        << ",\"accepted\":" << back_stats.accepted
        << ",\"enqueued\":" << back_stats.enqueued
        << ",\"subsumed\":" << back_stats.subsumed
        << ",\"action_predecessors\":" << back_stats.action_predecessors
        << ",\"time_predecessor_pieces\":"
        << back_stats.time_predecessor_pieces
        << ",\"unbounded_regions\":" << back_stats.unbounded_regions
        << ",\"dominance_checks\":" << back_stats.dominance_checks
        << ",\"dominance_unknown\":" << back_stats.dominance_unknown
        << ",\"elapsed_ms\":" << mixed_stats.backward_elapsed_ms << "},\n"
        << "  \"total_elapsed_ms\": " << mixed_stats.total_elapsed_ms << ",\n"
        << "  \"geometric_oracle\": {\"checked\":"
        << (result.geometric_oracle_checked ? "true" : "false")
        << ",\"equal\":"
        << (result.geometric_oracle_equal ? "true" : "false") << "},\n"
        << "  \"observer_oracle\": {\"checked\":"
        << (result.observer_oracle_checked ? "true" : "false")
        << ",\"strict_bound_unreachable\":"
        << (result.observer_strict_bound_unreachable ? "true" : "false")
        << ",\"bound_reachable\":"
        << (result.observer_bound_reachable ? "true" : "false") << "},\n"
        << "  \"automaton\": ";
    write_automaton(out, result);
    out << ",\n  \"initial_location\": "
        << result.automaton.initial_location()
        << ",\n  \"initial_cost\": {\"reachable_domain\":\""
        << to_string(result.initial_cost.reachable_domain)
        << "\",\"kind\":\"" << to_string(initial_cost.kind)
        << "\",\"value\":";
    if (initial_cost.kind == CostValueKind::Finite) {
        out << '"' << rational_string(initial_cost.value) << '"';
    } else {
        out << "null";
    }
    out << ",\"attained\":" << (initial_cost.attained ? "true" : "false")
        << ",\"exact\":" << (initial_cost.exact ? "true" : "false")
        << ",\"lower_bound_declared\":"
        << (initial_cost.lower_bound_assumed ? "true" : "false")
        << ",\"piece_id\":";
    if (initial_cost.piece_id.has_value()) out << *initial_cost.piece_id; else out << "null";
    out << ",\"unbounded_region_id\":";
    if (initial_cost.unbounded_region_id.has_value()) {
        out << *initial_cost.unbounded_region_id;
    } else {
        out << "null";
    }
    out << ",\"reachable_node_id\":";
    if (result.initial_cost.reachable_node.has_value()) {
        out << *result.initial_cost.reachable_node;
    } else {
        out << "null";
    }
    out << ",\"next_arc_id\":";
    if (result.initial_cost.next_arc.has_value()) {
        out << *result.initial_cost.next_arc;
    } else {
        out << "null";
    }
    out << ",\"next_edge\":";
    write_optional_edge(out, result.initial_cost.next_edge);
    out << ",\"witness\":";
    if (result.initial_cost.witness.has_value()) {
        write_mixed_witness(out, *result.initial_cost.witness);
    } else {
        out << "null";
    }
    out << "},\n  \"goals\": [";
    for (std::size_t index = 0; index < result.goals.locations.size(); ++index) {
        if (index != 0) out << ',';
        out << result.goals.locations[index];
    }
    out << "],\n  \"dependencies\": {\"z3\":\""
        << json_escape(Z3_get_full_version()) << "\",\"pardibaal_commit\":\""
        << json_escape(TAMONITOR_PARDIBAAL_COMMIT) << "\"}\n}\n";
}

void write_mixed_pieces(
    const std::filesystem::path& path,
    const PTAMixedExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    for (const auto& [_, pieces] : result.snapshot.all_pieces()) {
        for (const auto& piece : pieces) {
            write_mixed_finite_piece(out, piece, result);
            out << '\n';
        }
    }
    for (const auto& region : result.snapshot.unbounded_regions()) {
        out << "{\"kind\":\"negative_infinity\",\"region_id\":"
            << region.id << ",\"reachable_node_id\":" << region.node
            << ",\"location\":" << region.location << ",\"zone\":";
        write_dbm(out, region.zone);
        out << ",\"witness\":";
        write_mixed_witness(out, region.witness);
        out << ",\"analysis_status\":\"" << to_string(result.snapshot.status())
            << "\",\"snapshot_exact\":"
            << (result.snapshot.exact() ? "true" : "false")
            << ",\"lower_bound_declared\":"
            << (result.snapshot.lower_bound_assumed() ? "true" : "false")
            << "}\n";
    }
}

void write_reachable_nodes(
    const std::filesystem::path& path,
    const PTAMixedExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    const auto* reachability = result.snapshot.reachability();
    if (reachability == nullptr) {
        throw std::logic_error("mixed snapshot omitted its reachability graph");
    }
    for (const auto& node : reachability->nodes()) {
        out << "{\"node_id\":" << node.id << ",\"location\":"
            << node.location << ",\"goal\":"
            << (node.is_goal ? "true" : "false") << ",\"zone\":";
        write_dbm(out, node.zone);
        out << ",\"forward_status\":\"" << to_string(reachability->status())
            << "\",\"forward_exact\":"
            << (reachability->exact() ? "true" : "false") << "}\n";
    }
}

void write_reachable_arcs(
    const std::filesystem::path& path,
    const PTAMixedExecutionResult& result) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("Could not write " + path.string());
    }
    const auto* reachability = result.snapshot.reachability();
    if (reachability == nullptr) {
        throw std::logic_error("mixed snapshot omitted its reachability graph");
    }
    for (const auto& arc : reachability->arcs()) {
        out << "{\"arc_id\":" << arc.id << ",\"source_node\":"
            << arc.source << ",\"target_node\":" << arc.target
            << ",\"edge\":";
        write_optional_edge(out, arc.edge);
        out << ",\"fire_zone\":";
        write_dbm(out, arc.fire_zone);
        out << ",\"entry_zone\":";
        write_dbm(out, arc.entry_zone);
        out << ",\"post_zone\":";
        write_dbm(out, arc.post_zone);
        out << ",\"forward_status\":\"" << to_string(reachability->status())
            << "\",\"forward_exact\":"
            << (reachability->exact() ? "true" : "false") << "}\n";
    }
}

} // namespace

PTAExecutionResult run_pta_analysis(
    const BuildPair& build,
    const Options& options) {
    if (options.pta_analysis != PTAAnalysisMode::Backward) {
        throw std::invalid_argument("run_pta_analysis requires --pta-analysis backward");
    }
    if (options.word_mode != WordMode::Finite || options.build_mode != BuildMode::Flatten) {
        throw std::invalid_argument(
            "Backward PTA analysis requires finite words and flatten mode");
    }

    ParsedCostModel parsed = load_cost_model(options.pta_cost_model);
    const BuildArtifact& artifact = parsed.target == "positive"
        ? build.positive : build.negative;
    WeightedAutomatonView automaton = compile_automaton(artifact.automaton);
    validate_cost_overrides(automaton, parsed.costs);
    GoalSpec goals = accepting_goals(artifact.automaton);

    SolverOptions solver_options;
    solver_options.max_pieces = options.pta_max_pieces;
    solver_options.timeout_ms = options.pta_timeout_ms;
    solver_options.assume_lower_bounded = options.pta_assume_lower_bounded;
    const bool nonnegative = parsed.costs.is_nonnegative_for(automaton);
    AnalysisSnapshot snapshot = solve(automaton, goals, parsed.costs, solver_options);
    const RationalValuation zero(
        automaton.dimension(), BigRational(BigInt(0)));
    CostToGoResult initial = snapshot.query(automaton.initial_location(), zero);
    const bool oracle_checked = options.pta_verify_geometry && snapshot.exact();
    if (oracle_checked) {
        verify_geometric_support(artifact.automaton, snapshot);
    }

    return PTAExecutionResult{
        parsed.target,
        parsed.source,
        nonnegative,
        std::move(automaton),
        std::move(parsed.costs),
        std::move(goals),
        std::move(snapshot),
        std::move(initial),
        oracle_checked,
        oracle_checked};
}

PTAMixedExecutionResult run_mixed_pta_analysis(
    const BuildPair& build,
    const Options& options) {
    if (options.pta_analysis != PTAAnalysisMode::Mixed) {
        throw std::invalid_argument(
            "run_mixed_pta_analysis requires --pta-analysis mixed");
    }
    if (options.word_mode != WordMode::Finite ||
        options.build_mode != BuildMode::Flatten) {
        throw std::invalid_argument(
            "Mixed PTA analysis requires finite words and flatten mode");
    }

    ParsedCostModel parsed = load_cost_model(options.pta_cost_model);
    const BuildArtifact& artifact = parsed.target == "positive"
        ? build.positive : build.negative;
    WeightedAutomatonView automaton = compile_automaton(artifact.automaton);
    validate_cost_overrides(automaton, parsed.costs);
    GoalSpec goals = accepting_goals(artifact.automaton);

    ReachabilityOptions reach_options;
    reach_options.max_nodes = options.pta_max_reach_nodes;
    reach_options.max_arcs = options.pta_max_reach_arcs;
    reach_options.timeout_ms = options.pta_timeout_ms;
    ReachabilitySnapshot reachability = compute_reachable_zone_graph(
        automaton, goals, reach_options);

    SolverOptions solver_options;
    solver_options.max_pieces = options.pta_max_pieces;
    solver_options.timeout_ms = options.pta_timeout_ms;
    solver_options.assume_lower_bounded = options.pta_assume_lower_bounded;
    const bool nonnegative = parsed.costs.is_nonnegative_for(automaton);
    MixedAnalysisSnapshot snapshot = solve_mixed(
        automaton, reachability, parsed.costs, solver_options);
    const RationalValuation zero(
        automaton.dimension(), BigRational(BigInt(0)));
    MixedCostToGoResult initial = snapshot.query(
        automaton.initial_location(), zero);

    const bool geometric_checked =
        options.pta_verify_geometry && snapshot.exact();
    if (geometric_checked) {
        verify_mixed_geometric_support(artifact.automaton, snapshot);
    }

    bool observer_checked = false;
    bool strict_unreachable = false;
    bool bound_reachable = false;
    if (options.pta_verify_geometry && snapshot.exact() &&
        has_unit_time_cost_model(automaton, parsed.costs) &&
        initial.cost.kind == CostValueKind::Finite &&
        initial.cost.attained &&
        initial.cost.value.denominator() == 1 &&
        initial.cost.value.numerator() >= 0) {
        const BigInt maximum = std::numeric_limits<pardibaal::val_t>::max();
        if (initial.cost.value.numerator() <= maximum) {
            const auto bound = static_cast<pardibaal::val_t>(
                initial.cost.value.numerator().convert_to<long long>());
            strict_unreachable = !ordinary_goal_reachable_within(
                artifact.automaton, bound, true);
            bound_reachable = ordinary_goal_reachable_within(
                artifact.automaton, bound, false);
            observer_checked = true;
            if (!strict_unreachable || !bound_reachable) {
                throw std::logic_error(
                    "mixed shortest-time value disagrees with MoniTAal observer oracle");
            }
        }
    }

    return PTAMixedExecutionResult{
        parsed.target,
        parsed.source,
        nonnegative,
        std::move(automaton),
        std::move(parsed.costs),
        std::move(goals),
        std::move(snapshot),
        std::move(initial),
        geometric_checked,
        geometric_checked,
        observer_checked,
        strict_unreachable,
        bound_reachable};
}

void write_pta_outputs(
    const std::filesystem::path& output_dir,
    const PTAExecutionResult& result) {
    std::filesystem::create_directories(output_dir);
    write_summary(output_dir / "pta_analysis.json", result);
    write_pieces(output_dir / "pta_pieces.jsonl", result);
}

void write_mixed_pta_outputs(
    const std::filesystem::path& output_dir,
    const PTAMixedExecutionResult& result) {
    std::filesystem::create_directories(output_dir);
    write_mixed_summary(output_dir / "pta_analysis.json", result);
    write_mixed_pieces(output_dir / "pta_pieces.jsonl", result);
    write_reachable_nodes(output_dir / "pta_reachable_nodes.jsonl", result);
    write_reachable_arcs(output_dir / "pta_reachable_arcs.jsonl", result);
}

bool is_successful(const PTAExecutionResult& result) noexcept {
    switch (result.snapshot.status()) {
        case SolverStatus::Complete:
        case SolverStatus::Unreachable:
        case SolverStatus::UnboundedBelow:
            return true;
        case SolverStatus::AssumptionRequired:
        case SolverStatus::ResourceLimit:
            return false;
    }
    return false;
}

bool is_successful(const PTAMixedExecutionResult& result) noexcept {
    switch (result.snapshot.status()) {
        case MixedSolverStatus::Complete:
        case MixedSolverStatus::Unreachable:
        case MixedSolverStatus::UnboundedBelow:
            return true;
        case MixedSolverStatus::AssumptionRequired:
        case MixedSolverStatus::IncompleteForwardResourceLimit:
        case MixedSolverStatus::IncompleteBackwardResourceLimit:
            return false;
    }
    return false;
}

} // namespace tamonitor::pta
