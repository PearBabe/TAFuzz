// 本文件实现 Parrot-Lime 2020 Definitions 3、5-9 与 Theorems 1-2。

#include "PricedDBMOps.h"

#include <pardibaal/Federation.h>

#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>

namespace tamonitor::pta {
namespace {

void require_same_dimension(const pardibaal::DBM& left,
                            const pardibaal::DBM& right) {
    if (left.dimension() != right.dimension()) {
        throw std::invalid_argument("Priced DBM operands have different dimensions");
    }
}

void require_clock(const pardibaal::DBM& zone, pardibaal::dim_t clock) {
    if (clock == 0 || clock >= zone.dimension()) {
        throw std::invalid_argument("Reset/facet clock must be a non-reference DBM clock");
    }
}

pardibaal::val_t negate_bound(pardibaal::val_t value) {
    const auto wide = -static_cast<std::int64_t>(value);
    if (wide < std::numeric_limits<pardibaal::val_t>::min() ||
        wide > std::numeric_limits<pardibaal::val_t>::max()) {
        throw std::overflow_error("DBM bound cannot be negated in pardibaal::val_t");
    }
    return static_cast<pardibaal::val_t>(wide);
}

BigInt rates_sum(const WeightedZone& weighted_zone) {
    BigInt result = 0;
    for (pardibaal::dim_t clock = 1; clock < weighted_zone.zone.dimension(); ++clock) {
        result += weighted_zone.rates[clock];
    }
    return result;
}

std::vector<WeightedFacet> facets(const WeightedZone& weighted_zone,
                                  FacetKind kind) {
    if (weighted_zone.zone.is_empty()) {
        return {};
    }

    const auto closed = topological_closure(weighted_zone.zone);
    std::vector<WeightedFacet> result;
    result.reserve(closed.dimension() - 1);

    for (pardibaal::dim_t clock = 1; clock < closed.dimension(); ++clock) {
        const auto bound = kind == FacetKind::LOWER
            ? weighted_zone.zone.at(0, clock)
            : weighted_zone.zone.at(clock, 0);
        if (bound.is_inf()) {
            continue;
        }

        const auto boundary = kind == FacetKind::LOWER
            ? negate_bound(bound.get_bound())
            : bound.get_bound();

        auto facet_zone = closed;
        if (kind == FacetKind::LOWER) {
            // closure 已含 x>=n；补 x<=n 得到 x=n。
            facet_zone.restrict(clock, 0,
                                pardibaal::bound_t::non_strict(boundary));
        } else {
            // closure 已含 x<=n；补 x>=n 得到 x=n。
            facet_zone.restrict(0, clock,
                                pardibaal::bound_t::non_strict(
                                    negate_bound(boundary)));
        }
        facet_zone.close();
        if (facet_zone.is_empty()) {
            continue;
        }

        bool duplicate = false;
        for (const auto& existing : result) {
            if (facet_zone.relation(existing.weighted_zone.zone).is_equal()) {
                duplicate = true;
                break;
            }
        }
        if (duplicate) {
            continue;
        }

        auto rebased = rebase(weighted_zone, facet_zone);
        if (!rebased) {
            continue;
        }
        result.push_back(WeightedFacet{
            std::move(*rebased), clock, boundary, kind, bound.is_strict()});
    }
    return result;
}

std::optional<TimePredecessorPiece> make_time_piece(
    const WeightedZone& weighted_zone,
    const pardibaal::DBM& exact_domain,
    bool attained,
    DelayWitnessKind kind,
    std::optional<pardibaal::dim_t> clock,
    std::optional<pardibaal::val_t> bound) {
    auto candidate = weighted_zone;
    candidate.attained = attained;
    auto restricted = intersection(candidate, exact_domain);
    if (!restricted) {
        return std::nullopt;
    }
    return TimePredecessorPiece{
        std::move(*restricted), kind, std::move(clock), std::move(bound)};
}

std::optional<pardibaal::DBM> actual_facet_past(
    const WeightedZone& original,
    const WeightedFacet& facet,
    const pardibaal::DBM& invariant) {
    auto actual_facet = original.zone;
    if (facet.kind == FacetKind::LOWER) {
        actual_facet.restrict(
            facet.clock, 0,
            pardibaal::bound_t::non_strict(facet.boundary));
    } else {
        actual_facet.restrict(
            0, facet.clock,
            pardibaal::bound_t::non_strict(negate_bound(facet.boundary)));
    }
    actual_facet.close();
    if (actual_facet.is_empty()) {
        return std::nullopt;
    }

    // 该 past 精确刻画“按 facet 唯一 delay 到达的端点确实属于原 zone”。
    actual_facet.past();
    actual_facet.intersection(invariant);
    actual_facet.close();
    if (actual_facet.is_empty()) {
        return std::nullopt;
    }
    return actual_facet;
}

std::vector<TimePredecessorPiece> restrict_facet_piece(
    const WeightedZone& weighted_past,
    const WeightedZone& original,
    const WeightedFacet& facet,
    const pardibaal::DBM& exact_domain,
    const pardibaal::DBM& invariant,
    const BigInt& location_rate,
    DelayWitnessKind kind) {
    auto full_piece = make_time_piece(
        weighted_past, exact_domain, false, kind, facet.clock, facet.boundary);
    if (!full_piece) {
        return {};
    }

    const bool flat_delay_objective = location_rate == rates_sum(original);
    if (!original.attained || flat_delay_objective) {
        // 平坦目标下 exact Past(original) 中任取一个真实 delay 都有相同值，
        // 不必真的到达 closure facet；否则继承 suffix 的 attained 状态。
        full_piece->weighted_zone.attained = original.attained;
        return {std::move(*full_piece)};
    }

    const auto attained_past = actual_facet_past(original, facet, invariant);
    if (!attained_past) {
        return {std::move(*full_piece)};
    }

    auto attained_piece = make_time_piece(
        weighted_past, *attained_past, true, kind, facet.clock, facet.boundary);
    if (!attained_piece) {
        return {std::move(*full_piece)};
    }

    // 端点是否落在原严格 zone 可能依赖 source valuation。用精确 Federation
    // 差集拆成若干 DBM，避免把一个 facet 粗暴标成全 attained 或全 unattained。
    pardibaal::Federation unattained_domains(full_piece->weighted_zone.zone);
    unattained_domains.subtract(attained_piece->weighted_zone.zone);

    std::vector<TimePredecessorPiece> result;
    result.push_back(std::move(*attained_piece));
    for (const auto& domain : unattained_domains) {
        auto piece = make_time_piece(
            weighted_past, domain, false, kind, facet.clock, facet.boundary);
        if (piece) {
            result.push_back(std::move(*piece));
        }
    }
    return result;
}

} // namespace

std::vector<BigInt> offset(const pardibaal::DBM& zone) {
    auto canonical = zone;
    canonical.close();
    if (canonical.is_empty()) {
        throw std::invalid_argument("The offset of an empty DBM is undefined");
    }

    std::vector<BigInt> result(canonical.dimension(), 0);
    for (pardibaal::dim_t clock = 1; clock < canonical.dimension(); ++clock) {
        const auto lower = canonical.at(0, clock);
        if (lower.is_inf()) {
            throw std::logic_error(
                "A timed-automata DBM must retain clock non-negativity");
        }
        result[clock] = -BigInt(lower.get_bound());
    }
    return result;
}

bool contains(const pardibaal::DBM& zone,
              const RationalValuation& valuation) {
    if (valuation.size() != zone.dimension()) {
        throw std::invalid_argument(
            "Valuation must have exactly one entry per DBM dimension");
    }
    if (valuation.empty() || valuation.front() != BigRational(0)) {
        throw std::invalid_argument("DBM reference-clock valuation must be zero");
    }
    if (zone.is_empty()) {
        return false;
    }

    for (pardibaal::dim_t i = 0; i < zone.dimension(); ++i) {
        for (pardibaal::dim_t j = 0; j < zone.dimension(); ++j) {
            const auto bound = zone.at(i, j);
            if (bound.is_inf()) {
                continue;
            }
            const BigRational rhs(BigInt(bound.get_bound()));
            const auto lhs = valuation[i] - valuation[j];
            if (bound.is_strict() ? !(lhs < rhs) : !(lhs <= rhs)) {
                return false;
            }
        }
    }
    return true;
}

bool contains(const WeightedZone& zone,
              const RationalValuation& valuation) {
    return contains(zone.zone, valuation);
}

BigRational weight_at(const WeightedZone& zone,
                      const RationalValuation& valuation) {
    if (!contains(zone, valuation)) {
        throw std::invalid_argument("Cannot evaluate a weighted zone outside its DBM");
    }

    const auto delta = offset(zone.zone);
    BigRational result(zone.offset_weight);
    for (pardibaal::dim_t clock = 1; clock < zone.zone.dimension(); ++clock) {
        result += BigRational(zone.rates[clock]) *
                  (valuation[clock] - BigRational(delta[clock]));
    }
    return result;
}

std::optional<WeightedZone> rebase(const WeightedZone& weighted_zone,
                                   const pardibaal::DBM& new_zone) {
    require_same_dimension(weighted_zone.zone, new_zone);
    auto canonical = new_zone;
    canonical.close();
    if (canonical.is_empty()) {
        return std::nullopt;
    }

    const auto old_delta = offset(weighted_zone.zone);
    const auto new_delta = offset(canonical);
    BigInt new_weight = weighted_zone.offset_weight;
    for (pardibaal::dim_t clock = 1; clock < canonical.dimension(); ++clock) {
        new_weight += weighted_zone.rates[clock] *
                      (new_delta[clock] - old_delta[clock]);
    }

    return WeightedZone(std::move(canonical), std::move(new_weight),
                        weighted_zone.rates, weighted_zone.attained);
}

std::optional<WeightedZone> intersection(
    const WeightedZone& weighted_zone,
    const pardibaal::DBM& restriction) {
    require_same_dimension(weighted_zone.zone, restriction);
    auto result_zone = weighted_zone.zone;
    result_zone.intersection(restriction);
    return rebase(weighted_zone, result_zone);
}

pardibaal::DBM topological_closure(const pardibaal::DBM& zone) {
    auto result = zone;
    result.close();
    if (result.is_empty()) {
        return result;
    }

    for (pardibaal::dim_t i = 0; i < result.dimension(); ++i) {
        for (pardibaal::dim_t j = 0; j < result.dimension(); ++j) {
            const auto bound = result.at(i, j);
            if (!bound.is_inf() && bound.is_strict()) {
                result.set(i, j,
                           pardibaal::bound_t::non_strict(bound.get_bound()));
            }
        }
    }
    result.close();
    return result;
}

std::vector<WeightedFacet> lower_facets(
    const WeightedZone& weighted_zone) {
    return facets(weighted_zone, FacetKind::LOWER);
}

std::vector<WeightedFacet> upper_facets(
    const WeightedZone& weighted_zone) {
    return facets(weighted_zone, FacetKind::UPPER);
}

std::optional<WeightedZone> inverse_reset(
    const WeightedZone& weighted_zone,
    const std::vector<pardibaal::dim_t>& reset_clocks) {
    auto result_zone = weighted_zone.zone;
    for (const auto clock : reset_clocks) {
        require_clock(result_zone, clock);
        result_zone.restrict(clock, 0, pardibaal::bound_t::le_zero());
        result_zone.restrict(0, clock, pardibaal::bound_t::le_zero());
    }
    result_zone.close();
    if (result_zone.is_empty()) {
        return std::nullopt;
    }

    // Definition 7 要求先完成 R=0 的整体求交，再 relax 所有 reset clocks。
    for (const auto clock : reset_clocks) {
        result_zone.free(clock);
    }
    result_zone.close();

    auto new_rates = weighted_zone.rates;
    for (const auto clock : reset_clocks) {
        new_rates[clock] = 0;
    }

    // Z intersect (R=0) 非空蕴含 reset 坐标的 offset 为 0；其余坐标在
    // relax 后不变，因此论文 Definition 7 的 offset weight 仍为 w。
    return WeightedZone(std::move(result_zone), weighted_zone.offset_weight,
                        std::move(new_rates), weighted_zone.attained);
}

WeightedZone subtract_edge_weight(const WeightedZone& weighted_zone,
                                  const BigInt& edge_weight) {
    return WeightedZone(weighted_zone.zone,
                        weighted_zone.offset_weight - edge_weight,
                        weighted_zone.rates,
                        weighted_zone.attained);
}

std::optional<WeightedZone> action_predecessor(
    const WeightedZone& target,
    const std::vector<pardibaal::dim_t>& reset_clocks,
    const pardibaal::DBM& guard,
    const pardibaal::DBM& source_invariant,
    const BigInt& edge_weight) {
    require_same_dimension(target.zone, guard);
    require_same_dimension(target.zone, source_invariant);

    auto predecessor = inverse_reset(target, reset_clocks);
    if (!predecessor) {
        return std::nullopt;
    }
    *predecessor = subtract_edge_weight(*predecessor, edge_weight);
    predecessor = intersection(*predecessor, guard);
    if (!predecessor) {
        return std::nullopt;
    }
    return intersection(*predecessor, source_invariant);
}

WeightedZone facet_past(const WeightedFacet& facet,
                        const BigInt& location_rate) {
    require_clock(facet.weighted_zone.zone, facet.clock);

    auto past_zone = facet.weighted_zone.zone;
    past_zone.past();
    past_zone.close();

    auto new_rates = facet.weighted_zone.rates;
    BigInt other_rates = 0;
    for (pardibaal::dim_t clock = 1;
         clock < facet.weighted_zone.zone.dimension(); ++clock) {
        if (clock != facet.clock) {
            other_rates += facet.weighted_zone.rates[clock];
        }
    }

    // Definition 8: r'_y = -(sum_{x!=y} r_x - p).
    new_rates[facet.clock] = location_rate - other_rates;

    const auto facet_delta = offset(facet.weighted_zone.zone);
    const auto past_delta = offset(past_zone);
    BigInt new_weight = facet.weighted_zone.offset_weight;
    for (pardibaal::dim_t clock = 1; clock < past_zone.dimension(); ++clock) {
        new_weight += new_rates[clock] *
                      (past_delta[clock] - facet_delta[clock]);
    }

    return WeightedZone(std::move(past_zone), std::move(new_weight),
                        std::move(new_rates),
                        facet.weighted_zone.attained &&
                            (!facet.boundary_strict ||
                             location_rate == rates_sum(facet.weighted_zone)));
}

TimePredecessorResult time_predecessor(
    const WeightedZone& target,
    const pardibaal::DBM& invariant,
    const BigInt& location_rate) {
    require_same_dimension(target.zone, invariant);
    TimePredecessorResult result;

    // 先把目标片限制在 invariant 内；正常 solver 状态本就满足该不变量，
    // 此步使局部 API 在独立调用时仍保持 timed semantics。
    auto invariant_target = intersection(target, invariant);
    if (!invariant_target) {
        return result;
    }

    auto exact_past_domain = invariant_target->zone;
    exact_past_domain.past();
    exact_past_domain.intersection(invariant);
    exact_past_domain.close();
    if (exact_past_domain.is_empty()) {
        return result;
    }

    const auto sum = rates_sum(*invariant_target);
    if (location_rate >= sum) {
        // sum(r)-p<=0，最大 W 选择最小 delay：零 delay 或 lower facet。
        // 等号也必须保留 facet 分片；把整个 Past 标成 ZERO witness 会让
        // target 外 valuation 得到不可执行的零延迟见证。
        auto zero_piece = intersection(*invariant_target, invariant);
        if (zero_piece) {
            result.pieces.push_back(TimePredecessorPiece{
                std::move(*zero_piece), DelayWitnessKind::ZERO,
                std::nullopt, std::nullopt});
        }

        for (const auto& facet : lower_facets(*invariant_target)) {
            auto pieces = restrict_facet_piece(
                facet_past(facet, location_rate), *invariant_target, facet,
                exact_past_domain, invariant, location_rate,
                DelayWitnessKind::LOWER_FACET);
            for (auto& piece : pieces) {
                result.pieces.push_back(std::move(piece));
            }
        }
        return result;
    }

    // sum(r)-p>0，最大 W 选择最大 delay，即某个 upper facet。
    const auto facets_to_use = upper_facets(*invariant_target);
    if (facets_to_use.empty()) {
        result.unbounded_below = true;
        result.unbounded_domain = exact_past_domain;
        return result;
    }
    for (const auto& facet : facets_to_use) {
        auto pieces = restrict_facet_piece(
            facet_past(facet, location_rate), *invariant_target, facet,
            exact_past_domain, invariant, location_rate,
            DelayWitnessKind::UPPER_FACET);
        for (auto& piece : pieces) {
            result.pieces.push_back(std::move(piece));
        }
    }
    return result;
}

} // namespace tamonitor::pta
