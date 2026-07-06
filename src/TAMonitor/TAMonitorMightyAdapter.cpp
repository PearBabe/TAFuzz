#include "TAMonitor.h"

#include "Fixpoint.h"
#include "MightyPPL.h"

#include <antlr4-runtime.h>
#include <bdd.h>

#include <chrono>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>

using namespace mightypplcpp;

namespace mightypplcpp {

const char* spec_file = nullptr;
const char* out_file = nullptr;
std::optional<bool> out_format = std::nullopt;
bool out_flatten = true;
bool comp_flatten = false;
bool out_fin = false;
bool debug = false;
bool back = true;

monitaal::TAwithBDDEdges varphi = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);
monitaal::TAwithBDDEdges div = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);
std::vector<monitaal::TAwithBDDEdges> temporal_components;
monitaal::TAwithBDDEdges model = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);

}

namespace tamonitor {

namespace {

class BoundedStreamBuffer : public std::streambuf {
public:
    explicit BoundedStreamBuffer(size_t limit) : limit_(limit) {
        buffer_.reserve(limit_);
    }

    std::string str() const {
        if (dropped_ == 0) {
            return buffer_;
        }
        std::ostringstream out;
        out << buffer_ << "\n[diagnostics truncated after " << limit_
            << " bytes; discarded " << dropped_ << " additional bytes]\n";
        return out.str();
    }

protected:
    int overflow(int ch) override {
        if (ch == traits_type::eof()) {
            return traits_type::not_eof(ch);
        }
        const char c = static_cast<char>(ch);
        if (buffer_.size() < limit_) {
            buffer_.push_back(c);
        } else {
            ++dropped_;
        }
        return ch;
    }

    std::streamsize xsputn(const char* s, std::streamsize count) override {
        if (count <= 0) {
            return 0;
        }

        const auto available = limit_ > buffer_.size() ? limit_ - buffer_.size() : 0;
        const auto to_copy = std::min<size_t>(available, static_cast<size_t>(count));
        if (to_copy > 0) {
            buffer_.append(s, to_copy);
        }
        dropped_ += static_cast<size_t>(count) - to_copy;
        return count;
    }

private:
    size_t limit_;
    size_t dropped_ = 0;
    std::string buffer_;
};

class ScopedCoutCapture {
public:
    ScopedCoutCapture() : old_(std::cout.rdbuf(&buffer_)) {}
    ~ScopedCoutCapture() { std::cout.rdbuf(old_); }
    std::string str() const { return buffer_.str(); }

private:
    BoundedStreamBuffer buffer_{64 * 1024};
    std::streambuf* old_;
};

void reset_mightyppl_state(const Options& options) {
    mightypplcpp::spec_file = nullptr;
    mightypplcpp::out_file = nullptr;
    mightypplcpp::out_format = std::nullopt;
    mightypplcpp::out_flatten = options.build_mode == BuildMode::Flatten;
    mightypplcpp::comp_flatten = options.build_mode == BuildMode::Compflatten;
    mightypplcpp::out_fin = options.word_mode == WordMode::Finite;
    mightypplcpp::debug = false;
    mightypplcpp::back = true;

    mightypplcpp::gcd = 0;
    mightypplcpp::last_intersection = false;
    mightypplcpp::num_all_props = 0;
    mightypplcpp::components_counter = 0;
    mightypplcpp::single = false;
    mightypplcpp::props_to_keep.clear();
    mightypplcpp::sat_paths.clear();
    mightypplcpp::temporal_components.clear();
    mightypplcpp::last_nnf_formula.clear();
    mightypplcpp::last_props_by_name.clear();
    mightypplcpp::last_projection_valuation_count = 0;
    mightypplcpp::canonical_projection_enabled = !options.build_only;
    mightypplcpp::scale_product_bounds_by_gcd = false;
    mightypplcpp::canonical_projection_max_valuations = options.max_valuations;

    mightypplcpp::varphi = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);
    mightypplcpp::div = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);
    mightypplcpp::model = monitaal::TAwithBDDEdges("dummy", {}, {}, {}, 0);
}

AutomatonStats stats_for(const monitaal::TA& ta) {
    AutomatonStats stats;
    stats.components = 1;
    stats.locations = ta.locations().size();
    stats.clocks = ta.number_of_clocks();
    stats.labels = ta.labels().size();
    for (const auto& [id, location] : ta.locations()) {
        stats.edges += ta.edges_from(id).size();
    }
    return stats;
}

AutomatonStats stats_for_bdd_component(const monitaal::TAwithBDDEdges& ta) {
    AutomatonStats stats;
    stats.components = 1;
    stats.locations = ta.locations().size();
    stats.clocks = ta.number_of_clocks();
    for (const auto& [id, location] : ta.locations()) {
        (void)location;
        stats.edges += ta.bdd_edges_from(id).size();
    }
    return stats;
}

void add_stats(AutomatonStats& total, const AutomatonStats& next) {
    total.components += next.components;
    total.locations += next.locations;
    total.edges += next.edges;
    total.clocks += next.clocks;
    total.labels += next.labels;
}

AutomatonStats stats_for_current_compflatten_components() {
    AutomatonStats total;
    total.components = 0;
    add_stats(total, stats_for_bdd_component(mightypplcpp::varphi));
    add_stats(total, stats_for_bdd_component(mightypplcpp::div));
    for (const auto& component : mightypplcpp::temporal_components) {
        add_stats(total, stats_for_bdd_component(component));
    }
    add_stats(total, stats_for_bdd_component(mightypplcpp::model));
    return total;
}

void reject_unsupported_internal_syntax(const std::string& formula) {
    static const std::regex count_modality(R"(\bC(?:F|O|G|H)n\b)");
    if (std::regex_search(formula, count_modality)) {
        throw std::runtime_error(
            "unsupported_user_formula: CFn/COn/CGn/CHn are MightyPPL internal count-construction forms in this runtime path; "
            "TAMonitor rejects them instead of entering undefined construction behavior");
    }
}

std::string normalize_semantically_redundant_intervals(std::string formula) {
    static const std::regex unary_superfluous_unbounded(
        R"(\b([FOGH])(\s*\*)?\s*\[\s*0\s*,\s*infty\s*\))");
    static const std::regex binary_superfluous_unbounded(
        R"(\b([USRT])(\s*\*)?\s*\[\s*0\s*,\s*infty\s*\))");

    formula = std::regex_replace(formula, unary_superfluous_unbounded, "$1$2 ");
    formula = std::regex_replace(formula, binary_superfluous_unbounded, "$1$2 ");
    return formula;
}

std::string prepare_formula_for_mightyppl(const std::string& formula) {
    reject_unsupported_internal_syntax(formula);
    return normalize_semantically_redundant_intervals(formula);
}

bool satisfiable(const monitaal::TA& ta, WordMode mode) {
    monitaal::symbolic_state_t initial_state(ta.initial_location(), ta.number_of_clocks());
    const auto accepting_space = mode == WordMode::Finite
        ? monitaal::Fixpoint<monitaal::symbolic_state_t>::reach(
            monitaal::Fixpoint<monitaal::symbolic_state_t>::accept_states(ta), ta)
        : monitaal::Fixpoint<monitaal::symbolic_state_t>::buchi_accept_fixpoint(ta);
    initial_state.intersection(accepting_space);
    return !initial_state.is_empty();
}

BuildArtifact build_one(const std::string& formula, const Options& options) {
    reset_mightyppl_state(options);

    antlr4::ANTLRInputStream input(formula);
    MitlLexer lexer(&input);
    antlr4::CommonTokenStream tokens(&lexer);
    MitlParser parser(&tokens);
    MitlParser::MainContext* parsed_formula = parser.main();
    if (parser.getNumberOfSyntaxErrors() != 0) {
        throw std::runtime_error("MITL parse failed");
    }

    ScopedCoutCapture capture;
    auto [ta, unused_output] = mightypplcpp::build_ta_from_main(parsed_formula);

    BuildArtifact artifact{ta};
    artifact.nnf_formula = mightypplcpp::last_nnf_formula;
    artifact.stats = stats_for(ta);
    artifact.satisfiable = satisfiable(ta, options.word_mode);
    artifact.satisfiability = artifact.satisfiable ? "SAT" : "UNSAT";
    artifact.projection_valuations = mightypplcpp::last_projection_valuation_count;
    artifact.diagnostics = capture.str();
    return artifact;
}

BuildArtifact build_one_compflatten_stats_only(const std::string& formula, const Options& options) {
    reset_mightyppl_state(options);
    mightypplcpp::out_format = false;
    mightypplcpp::out_flatten = false;
    mightypplcpp::comp_flatten = true;

    antlr4::ANTLRInputStream input(formula);
    MitlLexer lexer(&input);
    antlr4::CommonTokenStream tokens(&lexer);
    MitlParser parser(&tokens);
    MitlParser::MainContext* parsed_formula = parser.main();
    if (parser.getNumberOfSyntaxErrors() != 0) {
        throw std::runtime_error("MITL parse failed");
    }

    ScopedCoutCapture capture;
    auto [unused_ta, generated_components] = mightypplcpp::build_ta_from_main(parsed_formula);
    (void)unused_ta;
    (void)generated_components;

    BuildArtifact artifact;
    artifact.nnf_formula = mightypplcpp::last_nnf_formula;
    artifact.stats = stats_for_current_compflatten_components();
    artifact.satisfiable = false;
    artifact.satisfiability = "NOT_CHECKED_COMPFLATTEN_BUILD_ONLY";
    artifact.projection_valuations = 0;
    artifact.diagnostics = capture.str();
    return artifact;
}

std::vector<std::string> prop_order_from(const std::map<std::string, int>& props) {
    std::vector<std::pair<int, std::string>> by_id;
    for (const auto& [name, id] : props) {
        by_id.push_back({id, name});
    }
    std::sort(by_id.begin(), by_id.end());

    std::vector<std::string> order;
    for (const auto& [id, name] : by_id) {
        order.push_back(name);
    }
    return order;
}

}

std::string read_formula(const Options& options) {
    if (options.formula_inline.has_value()) {
        return *options.formula_inline;
    }

    if (options.formula_path.has_value()) {
        std::ifstream input(*options.formula_path);
        if (!input) {
            throw std::runtime_error("Could not open formula file: " + options.formula_path->string());
        }

        std::stringstream buffer;
        buffer << input.rdbuf();
        return buffer.str();
    }

    std::string formula;
    std::cout << "Enter MITL formula: ";
    std::getline(std::cin, formula);
    if (formula.empty()) {
        throw std::runtime_error("Empty MITL formula");
    }
    return formula;
}

BuildPair build_automata_pair(const std::string& formula, const Options& options) {
    const auto start = std::chrono::steady_clock::now();
    const std::string normalized_formula = prepare_formula_for_mightyppl(formula);

    if (options.build_mode == BuildMode::Compflatten && !options.build_only) {
        throw std::runtime_error(
            "unsupported_runtime_mode: compflatten runtime monitoring is not implemented in TAMonitor v1; "
            "use --build-only for compflatten construction/statistics or --build-mode flatten for verified runtime monitoring");
    }

    bdd_init(static_cast<int>(options.bdd_nodes), static_cast<int>(options.bdd_cache));
    bdd_setmaxincrease(static_cast<int>(options.bdd_max_increase));
    BuildPair pair;
    pair.normalized_formula = normalized_formula;
    try {
        if (options.build_mode == BuildMode::Compflatten && options.build_only) {
            pair.positive = build_one_compflatten_stats_only(normalized_formula, options);
        } else {
            pair.positive = build_one(normalized_formula, options);
        }
        pair.positive_prop_ids = mightypplcpp::last_props_by_name;
        pair.proposition_order = prop_order_from(pair.positive_prop_ids);

        if (options.build_mode == BuildMode::Compflatten && options.build_only) {
            pair.negative = build_one_compflatten_stats_only("!(" + normalized_formula + ")", options);
        } else {
            pair.negative = build_one("!(" + normalized_formula + ")", options);
        }
        pair.negative_prop_ids = mightypplcpp::last_props_by_name;
        const auto negative_order = prop_order_from(pair.negative_prop_ids);
        if (pair.proposition_order != negative_order) {
            throw std::runtime_error("Positive and negative automata use different proposition orders");
        }
    } catch (...) {
        bdd_done();
        throw;
    }
    bdd_done();

    const auto end = std::chrono::steady_clock::now();
    pair.build_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    return pair;
}

}
