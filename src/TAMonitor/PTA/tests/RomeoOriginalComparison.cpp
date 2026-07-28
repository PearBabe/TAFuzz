// 本文件在闭、有界、int32 安全语料上直接对照原 Roméo DBM::min 与迁移后端。

#include "RomeoDBMOptimizer.h"
#include "PricedDBMOps.h"

#include "dbm.hh"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using tamonitor::pta::AffineOptimumKind;
using tamonitor::pta::BigInt;
using tamonitor::pta::BigRational;
using tamonitor::pta::WeightedZone;

class Random {
public:
    explicit Random(std::uint64_t seed) : state_(seed) {}
    std::uint64_t next() {
        std::uint64_t z = (state_ += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30U)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27U)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31U);
    }
    std::int32_t between(std::int32_t low, std::int32_t high) {
        return low + static_cast<std::int32_t>(
            next() % static_cast<std::uint64_t>(high - low + 1));
    }

private:
    std::uint64_t state_;
};

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void add_constraint(
    pardibaal::DBM& migrated,
    romeo::DBM& original,
    unsigned i,
    unsigned j,
    std::int32_t bound) {
    migrated.restrict(
        static_cast<pardibaal::dim_t>(i),
        static_cast<pardibaal::dim_t>(j),
        pardibaal::bound_t::non_strict(bound));
    original.constrain(i, j, romeo::time_bound(bound, ROMEO_DBM_NON_STRICT));
}

}  // namespace

int main() {
    try {
        {
            romeo::DBM probe(2);
            probe.constrain(0, 1, romeo::time_bound(-2, ROMEO_DBM_NON_STRICT));
            probe.constrain(1, 0, romeo::time_bound(5, ROMEO_DBM_NON_STRICT));
            romeo::cvalue positive[2] = {0, 1};
            romeo::cvalue negative_probe[2] = {0, -1};
            std::vector<romeo::Avalue> values(2);
            const auto minimum = probe.min(positive, values);
            const auto maximum = -probe.min(negative_probe, values);
            require(minimum.value() == 2 && maximum.value() == 5,
                    "original Roméo one-clock min/max orientation probe failed: min=" +
                        std::to_string(minimum.value()) + ", max=" +
                        std::to_string(maximum.value()));
        }
        constexpr std::uint64_t cases = 1'000;
        Random random(0x4f524947524f4d45ULL);
        for (std::uint64_t case_id = 0; case_id < cases; ++case_id) {
            const unsigned dimension = 2U + static_cast<unsigned>(random.next() % 7U);
            auto migrated = pardibaal::DBM::unconstrained(
                static_cast<pardibaal::dim_t>(dimension));
            romeo::DBM original(dimension);
            std::vector<std::int32_t> witness(dimension, 0);
            for (unsigned clock = 1; clock < dimension; ++clock) {
                const auto lower = random.between(0, 5);
                const auto upper = lower + random.between(2, 8);
                witness[clock] = lower + (upper - lower) / 2;
                add_constraint(migrated, original, 0, clock, -lower);
                add_constraint(migrated, original, clock, 0, upper);
            }
            for (unsigned count = 0; count < dimension * 2U; ++count) {
                const unsigned i = static_cast<unsigned>(random.next() % dimension);
                const unsigned j = static_cast<unsigned>(random.next() % dimension);
                if (i == j) continue;
                const auto bound = static_cast<std::int32_t>(
                    witness[i] - witness[j] + random.between(0, 4));
                add_constraint(migrated, original, i, j, bound);
            }
            migrated.close();
            original.close();
            require(!migrated.is_empty() && !original.is_empty(),
                    "bounded safe corpus unexpectedly empty");
            for (unsigned i = 0; i < dimension; ++i) {
                for (unsigned j = 0; j < dimension; ++j) {
                    const auto migrated_bound = migrated.at(
                        static_cast<pardibaal::dim_t>(i),
                        static_cast<pardibaal::dim_t>(j));
                    const auto original_bound = original(i, j);
                    require(migrated_bound.is_inf() == !original_bound.bounded() ||
                                (!migrated_bound.is_inf() &&
                                 migrated_bound.get_bound() == original_bound.value()),
                            "canonical DBM mismatch at case " +
                                std::to_string(case_id) + " (" +
                                std::to_string(i) + "," + std::to_string(j) + ")");
                }
            }

            std::vector<BigInt> rates(dimension, 0);
            std::vector<romeo::cvalue> negative(dimension, 0);
            for (unsigned clock = 1; clock < dimension; ++clock) {
                const auto coefficient = random.between(-9, 9);
                rates[clock] = coefficient;
                negative[clock] = -coefficient;
            }
            const auto delta = tamonitor::pta::offset(migrated);
            BigInt offset_weight = 0;
            for (unsigned clock = 1; clock < dimension; ++clock) {
                offset_weight += rates[clock] * delta[clock];
            }
            WeightedZone piece(migrated, offset_weight, rates);
            const auto derived = tamonitor::pta::maximize_affine_romeo_dbm(
                piece, migrated, 0);
            require(derived.kind == AffineOptimumKind::Finite,
                    "derived safe corpus result is not finite");

            std::vector<romeo::Avalue> values(dimension);
            const romeo::Avalue original_maximum =
                -original.min(negative.data(), values);
            require(!original_maximum.is_inf() &&
                        !original_maximum.is_minus_inf(),
                    "original Roméo safe corpus result is infinite");
            const BigRational original_value(
                BigInt(original_maximum.value()),
                BigInt(original_maximum.denominator()));
            require(derived.value == original_value,
                    "original/derived mismatch at case " +
                        std::to_string(case_id) + ": derived=" +
                        derived.value.numerator().convert_to<std::string>() +
                        "/" + derived.value.denominator().convert_to<std::string>() +
                        ", original=" +
                        original_value.numerator().convert_to<std::string>() +
                        "/" + original_value.denominator().convert_to<std::string>());
        }
        std::cout << "RomeoOriginalComparison: cases=1000 mismatches=0\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "RomeoOriginalComparison failed: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
