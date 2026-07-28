// 本文件用枚举、Z3 与固定随机语料差分验证 Roméo-derived DBM 优化器。

#include "AffineOptimizer.h"
#include "PricedDBMOps.h"
#include "RomeoDBMOptimizer.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using namespace tamonitor::pta;

class SplitMix64 {
public:
    explicit SplitMix64(std::uint64_t seed) : state_(seed) {}
    std::uint64_t next() {
        std::uint64_t z = (state_ += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30U)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27U)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31U);
    }
    std::int64_t between(std::int64_t low, std::int64_t high) {
        return low + static_cast<std::int64_t>(
            next() % static_cast<std::uint64_t>(high - low + 1));
    }

private:
    std::uint64_t state_;
};

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

BigRational affine_at(
    const WeightedZone& piece,
    const RationalValuation& valuation) {
    const auto delta = offset(piece.zone);
    BigRational value(piece.offset_weight);
    for (std::size_t clock = 1; clock < piece.rates.size(); ++clock) {
        value += BigRational(piece.rates[clock]) *
            (valuation[clock] - BigRational(delta[clock]));
    }
    return value;
}

void validate_optimizer(
    const WeightedZone& piece,
    const pardibaal::DBM& domain,
    const AffineSupremum& result) {
    if (result.kind != AffineOptimumKind::Finite) return;
    require(result.optimizer_or_limit.has_value(),
            "finite optimizer 缺少 actual/limit valuation");
    auto exact = intersection(piece, domain);
    require(exact.has_value(), "finite optimizer 的 exact domain 为空");
    const auto& valuation = *result.optimizer_or_limit;
    if (result.optimizer_is_actual) {
        require(contains(exact->zone, valuation),
                "actual optimizer 不属于严格原域");
    } else {
        require(contains(topological_closure(exact->zone), valuation),
                "limit optimizer 不属于 closure");
    }
    require(affine_at(*exact, valuation) == result.value,
            "optimizer valuation 未达到报告值");
}

struct Case {
    std::string category;
    WeightedZone piece;
    pardibaal::DBM domain;
};

pardibaal::DBM bounded_zone(
    pardibaal::dim_t dimension,
    SplitMix64& random,
    bool strict) {
    auto zone = pardibaal::DBM::unconstrained(dimension);
    std::vector<pardibaal::val_t> witness(dimension, 0);
    for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
        const auto lower = static_cast<pardibaal::val_t>(random.between(0, 4));
        const auto width = static_cast<pardibaal::val_t>(random.between(2, 8));
        const auto upper = static_cast<pardibaal::val_t>(lower + width);
        witness[clock] = static_cast<pardibaal::val_t>(lower + width / 2);
        zone.restrict(0, clock, pardibaal::bound_t::non_strict(-lower));
        zone.restrict(
            clock, 0,
            strict && clock == 1
                ? pardibaal::bound_t::strict(upper)
                : pardibaal::bound_t::non_strict(upper));
    }
    const auto diagonals = static_cast<std::size_t>(dimension) * 2U;
    for (std::size_t count = 0; count < diagonals; ++count) {
        const auto i = static_cast<pardibaal::dim_t>(random.next() % dimension);
        const auto j = static_cast<pardibaal::dim_t>(random.next() % dimension);
        if (i == j) continue;
        const auto slack = static_cast<pardibaal::val_t>(random.between(1, 5));
        const auto bound = static_cast<pardibaal::val_t>(
            witness[i] - witness[j] + slack);
        zone.restrict(
            i, j,
            strict && (count % 5U == 0U)
                ? pardibaal::bound_t::strict(bound)
                : pardibaal::bound_t::non_strict(bound));
    }
    zone.close();
    require(!zone.is_empty(), "随机 bounded DBM 构造为空");
    return zone;
}

Case make_case(std::uint64_t case_id, SplitMix64& random) {
    const auto dimension = static_cast<pardibaal::dim_t>(2 + random.next() % 11U);
    const auto bucket = case_id % 10U;
    if (bucket <= 5U) {
        const bool strict = bucket == 5U;
        auto zone = bounded_zone(dimension, random, strict);
        std::vector<BigInt> rates(dimension, 0);
        for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
            rates[clock] = random.between(-7, 7);
        }
        return {strict ? "strict_bounded" : "closed_bounded",
                WeightedZone(zone, BigInt(random.between(-20, 20)), rates),
                zone};
    }
    if (bucket == 6U) {
        auto zone = pardibaal::DBM::unconstrained(dimension);
        std::vector<BigInt> rates(dimension, 0);
        if (dimension >= 3) {
            const auto difference = static_cast<pardibaal::val_t>(
                random.between(-4, 4));
            zone.restrict(1, 2, pardibaal::bound_t::non_strict(difference));
            zone.restrict(2, 1, pardibaal::bound_t::non_strict(-difference));
            rates[1] = random.between(1, 9);
            rates[2] = -rates[1];
        }
        zone.close();
        return {"correlated_unbounded_finite",
                WeightedZone(zone, BigInt(random.between(-20, 20)), rates),
                zone};
    }
    if (bucket == 7U) {
        auto zone = pardibaal::DBM::unconstrained(dimension);
        std::vector<BigInt> rates(dimension, 0);
        rates[1] = BigInt(random.between(1, 9));
        return {"positive_infinity", WeightedZone(zone, 0, rates), zone};
    }
    if (bucket == 8U) {
        auto piece_zone = bounded_zone(dimension, random, false);
        auto domain = piece_zone;
        const auto upper = piece_zone.at(1, 0).get_bound();
        domain.restrict(
            0, 1, pardibaal::bound_t::non_strict(-(upper + 2)));
        domain.close();
        std::vector<BigInt> rates(dimension, 0);
        rates[1] = 1;
        return {"empty_intersection",
                WeightedZone(piece_zone, 0, rates), domain};
    }

    auto zone = bounded_zone(dimension, random, case_id % 20U == 9U);
    std::vector<BigInt> rates(dimension, 0);
    if (case_id % 20U == 9U) {
        rates[1] = BigInt(1);
        rates[1] <<= 100;
        rates[1] += 17;
        return {"bigint", WeightedZone(zone, BigInt(-9), rates), zone};
    }
    return {"zero_objective", WeightedZone(zone, BigInt(7), rates), zone};
}

void compare_case(
    std::uint64_t case_id,
    const Case& test_case,
    std::ostream* output) {
    const auto z3 = maximize_affine_z3(test_case.piece, test_case.domain, 0);
    const auto romeo = maximize_affine_romeo_dbm(
        test_case.piece, test_case.domain, 0);
    validate_optimizer(test_case.piece, test_case.domain, z3);
    validate_optimizer(test_case.piece, test_case.domain, romeo);
    bool equal = z3.kind == romeo.kind;
    if (equal && z3.kind == AffineOptimumKind::Finite) {
        equal = z3.value == romeo.value &&
                z3.domain_attained == romeo.domain_attained;
    }
    if (output != nullptr) {
        *output << "{\"case_id\":" << case_id
                << ",\"category\":\"" << test_case.category
                << "\",\"dimension\":" << test_case.domain.dimension()
                << ",\"z3_kind\":" << static_cast<int>(z3.kind)
                << ",\"romeo_kind\":" << static_cast<int>(romeo.kind)
                << ",\"z3_us\":" << z3.elapsed_us
                << ",\"romeo_us\":" << romeo.elapsed_us
                << ",\"equal\":" << (equal ? "true" : "false")
                << "}\n";
    }
    require(equal,
            "Z3/Roméo-derived mismatch at case " + std::to_string(case_id) +
                " category=" + test_case.category);
}

void enumeration_oracle(SplitMix64& random) {
    for (std::uint64_t case_id = 0; case_id < 200; ++case_id) {
        const auto dimension = static_cast<pardibaal::dim_t>(2 + case_id % 4U);
        auto zone = pardibaal::DBM::unconstrained(dimension);
        for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
            zone.restrict(0, clock, pardibaal::bound_t::non_strict(0));
            zone.restrict( clock, 0, pardibaal::bound_t::non_strict(4));
        }
        for (pardibaal::dim_t i = 1; i < dimension; ++i) {
            for (pardibaal::dim_t j = 1; j < dimension; ++j) {
                if (i != j && random.next() % 3U == 0U) {
                    zone.restrict(i, j, pardibaal::bound_t::non_strict(
                        static_cast<pardibaal::val_t>(random.between(0, 4))));
                }
            }
        }
        zone.close();
        if (zone.is_empty()) {
            --case_id;
            continue;
        }
        std::vector<BigInt> rates(dimension, 0);
        for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
            rates[clock] = random.between(-4, 4);
        }
        WeightedZone piece(zone, BigInt(random.between(-5, 5)), rates);
        std::optional<BigRational> expected;
        const std::size_t points = [&]() {
            std::size_t value = 1;
            for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
                value *= 5;
            }
            return value;
        }();
        for (std::size_t encoded = 0; encoded < points; ++encoded) {
            std::size_t cursor = encoded;
            RationalValuation valuation(dimension, BigRational(0));
            for (pardibaal::dim_t clock = 1; clock < dimension; ++clock) {
                valuation[clock] = BigRational(cursor % 5U);
                cursor /= 5U;
            }
            if (!contains(zone, valuation)) continue;
            const auto value = affine_at(piece, valuation);
            if (!expected.has_value() || value > *expected) expected = value;
        }
        require(expected.has_value(), "枚举 DBM 没有整数点");
        const auto result = maximize_affine_romeo_dbm(piece, zone, 0);
        require(result.kind == AffineOptimumKind::Finite &&
                    result.value == *expected,
                "Roméo-derived 与小维整数枚举 oracle 不一致");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        std::uint64_t cases = 20'000;
        std::uint64_t seed = 0x524f4d454f44424dULL;
        std::optional<std::filesystem::path> output_path;
        for (int index = 1; index < argc; ++index) {
            const std::string argument = argv[index];
            if (argument == "--cases" && index + 1 < argc) {
                cases = std::stoull(argv[++index], nullptr, 0);
            } else if (argument == "--seed" && index + 1 < argc) {
                seed = std::stoull(argv[++index], nullptr, 0);
            } else if (argument == "--output" && index + 1 < argc) {
                output_path = argv[++index];
            } else {
                throw std::invalid_argument("unknown/missing argument: " + argument);
            }
        }

        std::optional<std::ofstream> output;
        if (output_path.has_value()) {
            std::filesystem::create_directories(output_path->parent_path());
            output.emplace(*output_path);
            if (!*output) throw std::runtime_error("cannot open differential output");
        }

        SplitMix64 random(seed);
        enumeration_oracle(random);
        for (std::uint64_t case_id = 0; case_id < cases; ++case_id) {
            compare_case(case_id, make_case(case_id, random),
                         output.has_value() ? &*output : nullptr);
        }
        std::cout << "RomeoDBMOptimizerTests: enumeration=200 differential="
                  << cases << " mismatches=0 seed=0x" << std::hex << seed
                  << std::dec << '\n';
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "RomeoDBMOptimizerTests failed: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
