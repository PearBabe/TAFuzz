#include <automata.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::string read_all(const std::string &path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open " + path);
    }
    std::ostringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}

std::vector<std::string> read_events(const std::string &path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open " + path);
    }
    std::vector<std::string> events;
    for (std::string line; std::getline(input, line);) {
        if (!line.empty()) {
            events.push_back(line);
        }
    }
    return events;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::cerr << "usage: ltl-automata-smoke LTL_FILE EVENT_FILE\n";
        return 2;
    }

    try {
        const std::string encoded = read_all(argv[1]);
        const std::size_t delimiter = encoded.find(':');
        if (delimiter == std::string::npos) {
            throw std::runtime_error("LTL file has no formula/event delimiter");
        }
        const std::string formula = encoded.substr(0, delimiter);
        std::string exclusive = encoded.substr(delimiter + 1);
        while (!exclusive.empty() && (exclusive.back() == '\n' || exclusive.back() == '\r')) {
            exclusive.pop_back();
        }
        const std::vector<std::string> events = read_events(argv[2]);

        lfz::automata::Automata automata(formula, exclusive);
        std::vector<lfz::automata::MCState> states;
        automata.model_check_events(events, states);

        if (!automata.valid() || states.size() != events.size()) {
            throw std::runtime_error("artifact automaton rejected the smoke-test setup");
        }
        std::cout << "formula\t" << formula << '\n';
        std::cout << "exclusive_events\t" << exclusive << '\n';
        std::cout << "index\tevent\tstate\taccepting\n";
        for (std::size_t i = 0; i < states.size(); ++i) {
            if (states[i].state < 0) {
                throw std::runtime_error("no automaton successor for event " + events[i]);
            }
            std::cout << i << '\t' << events[i] << '\t' << states[i].state << '\t'
                      << (states[i].acceptance ? "true" : "false") << '\n';
        }
        std::cout << "status\tPASS\n";
    } catch (const std::exception &error) {
        std::cerr << "status\tFAIL\nreason\t" << error.what() << '\n';
        return 1;
    }
    return 0;
}
