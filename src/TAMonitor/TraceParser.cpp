#include "TAMonitor.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>

namespace tamonitor {

namespace {

std::string trim(const std::string& input) {
    size_t begin = 0;
    while (begin < input.size() && std::isspace(static_cast<unsigned char>(input[begin]))) {
        ++begin;
    }
    size_t end = input.size();
    while (end > begin && std::isspace(static_cast<unsigned char>(input[end - 1]))) {
        --end;
    }
    return input.substr(begin, end - begin);
}

std::string lower_ascii(std::string value) {
    for (char& c : value) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return value;
}

bool is_trace_header(const std::string& line) {
    const size_t comma = line.find(',');
    if (comma == std::string::npos) {
        return false;
    }

    const std::string first = lower_ascii(trim(line.substr(0, comma)));
    const std::string second = lower_ascii(trim(line.substr(comma + 1)));
    return first == "time" && (second == "props" || second == "bits");
}

monitaal::symb_time_t parse_time_atom(const std::string& text) {
    const std::string value = trim(text);
    if (value.empty()) {
        throw std::runtime_error("Empty time value in trace");
    }

    size_t consumed = 0;
    unsigned long parsed = 0;
    try {
        parsed = std::stoul(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error("Invalid time value in trace: " + value);
    }
    if (consumed != value.size()) {
        throw std::runtime_error("Invalid time value in trace: " + value);
    }
    if (parsed > static_cast<unsigned long>(std::numeric_limits<monitaal::symb_time_t>::max())) {
        throw std::runtime_error("Time value exceeds MoniTAal time range: " + value);
    }
    return static_cast<monitaal::symb_time_t>(parsed);
}

monitaal::interval_t parse_time(const std::string& text) {
    const std::string value = trim(text);
    if (value.empty()) {
        throw std::runtime_error("Empty time value in trace");
    }
    if (value.front() == '[') {
        const size_t comma = value.find(',');
        const size_t close = value.find(']');
        if (comma == std::string::npos || close == std::string::npos || comma >= close) {
            throw std::runtime_error("Invalid interval time: " + value);
        }
        if (trim(value.substr(close + 1)).size() != 0) {
            throw std::runtime_error("Invalid interval time: " + value);
        }
        const auto low = parse_time_atom(value.substr(1, comma - 1));
        const auto high = parse_time_atom(value.substr(comma + 1, close - comma - 1));
        if (low > high) {
            throw std::runtime_error("Invalid interval time with lower bound greater than upper bound: " + value);
        }
        return {low, high};
    }
    const auto point = parse_time_atom(value);
    return {point, point};
}

std::set<std::string> parse_props(const std::string& text) {
    std::string value = trim(text);
    if (value.empty() || value == "{}" || value == "-" || value == "empty") {
        return {};
    }
    if (value.front() == '{' && value.back() == '}') {
        value = value.substr(1, value.size() - 2);
    }
    for (char& c : value) {
        if (c == ',' || c == ';' || c == '|' || c == '+') {
            c = ' ';
        }
    }

    std::set<std::string> props;
    std::istringstream stream(value);
    std::string prop;
    while (stream >> prop) {
        props.insert(prop);
    }
    return props;
}

std::string props_to_bits(const std::string& text, const std::vector<std::string>& proposition_order) {
    const std::string value = trim(text);
    if (value.rfind("bits:", 0) == 0) {
        const std::string bits = value.substr(5);
        if (bits.size() != proposition_order.size()) {
            throw std::runtime_error("Trace bits length does not match proposition order");
        }
        if (!std::all_of(bits.begin(), bits.end(), [](char c) { return c == '0' || c == '1'; })) {
            throw std::runtime_error("Trace bits label must contain only 0 and 1");
        }
        return "bits:" + bits;
    }
    if (value.size() == proposition_order.size() &&
        std::all_of(value.begin(), value.end(), [](char c) { return c == '0' || c == '1'; })) {
        return "bits:" + value;
    }

    const std::set<std::string> props = parse_props(value);
    std::string bits(proposition_order.size(), '0');
    for (size_t i = 0; i < proposition_order.size(); ++i) {
        if (props.count(proposition_order[i])) {
            bits[i] = '1';
        }
    }
    for (const auto& prop : props) {
        if (std::find(proposition_order.begin(), proposition_order.end(), prop) == proposition_order.end()) {
            throw std::runtime_error("Trace references proposition not present in formula: " + prop);
        }
    }
    return "bits:" + bits;
}

size_t find_csv_separator(const std::string& clean) {
    if (!clean.empty() && clean.front() == '[') {
        const size_t close = clean.find(']');
        if (close == std::string::npos) {
            throw std::runtime_error("Trace interval time is missing closing ']': " + clean);
        }

        size_t separator = close + 1;
        while (separator < clean.size() && std::isspace(static_cast<unsigned char>(clean[separator]))) {
            ++separator;
        }
        if (separator >= clean.size() || clean[separator] != ',') {
            throw std::runtime_error("Trace line must separate interval time and props with a comma after ']': " + clean);
        }
        return separator;
    }

    const size_t comma = clean.find(',');
    if (comma == std::string::npos) {
        throw std::runtime_error("Trace line must be '@time label' or 'time,props': " + clean);
    }
    return comma;
}

TimedEvent parse_line(const std::string& line, const std::vector<std::string>& proposition_order) {
    const std::string clean = trim(line);
    if (clean.empty() || clean.front() == '#') {
        return {};
    }

    std::string time_text;
    std::string label_text;
    if (clean.front() == '@') {
        std::istringstream stream(clean.substr(1));
        stream >> time_text;
        std::getline(stream, label_text);
    } else {
        const size_t comma = find_csv_separator(clean);
        time_text = clean.substr(0, comma);
        label_text = clean.substr(comma + 1);
    }

    TimedEvent event;
    event.time = parse_time(time_text);
    event.canonical_label = props_to_bits(label_text, proposition_order);
    event.human_label = trim(label_text);
    return event;
}

}

std::vector<TimedEvent> parse_trace(const Options& options, const std::vector<std::string>& proposition_order) {
    std::vector<TimedEvent> events;

    if (options.trace_path.has_value()) {
        std::ifstream input(*options.trace_path);
        if (!input) {
            throw std::runtime_error("Could not open trace file: " + options.trace_path->string());
        }

        std::string line;
        while (std::getline(input, line)) {
            const std::string clean = trim(line);
            if (clean.empty() || clean.front() == '#' || is_trace_header(clean)) {
                continue;
            }
            events.push_back(parse_line(clean, proposition_order));
        }
    } else {
        std::cout << "Enter timed events as '@time props' or 'time,props'. Empty line or q ends input.\n";
        std::string line;
        while (std::getline(std::cin, line)) {
            const std::string clean = trim(line);
            if (clean.empty() || clean == "q") {
                break;
            }
            if (clean.front() == '#' || is_trace_header(clean)) {
                continue;
            }
            events.push_back(parse_line(clean, proposition_order));
        }
    }

    return events;
}

}
