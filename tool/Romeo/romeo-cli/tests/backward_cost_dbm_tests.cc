#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include <avalue.hh>
#include <cost_dbm.hh>
#include <dbm.hh>
#include <pairing_heap.hh>
#include <parser_data.hh>
#include <timebounds.hh>
#include <whash.hh>

using namespace romeo;
using namespace std;

// The production executable defines this parser context in main.cc.  This
// standalone regression binary links the parser objects without main.cc.
ParserData * pdata = nullptr;

namespace
{
    [[noreturn]] void fail(const string& message)
    {
        throw runtime_error(message);
    }

    void expect(const bool condition, const string& message)
    {
        if (!condition)
        {
            fail(message);
        }
    }

    DBM interval(const cvalue lower, const cvalue upper)
    {
        DBM zone(2);
        zone.constrain(0, 1, time_bound(-lower));
        zone.constrain(1, 0, time_bound(upper));
        return zone;
    }

    DBM point(const vector<cvalue>& values)
    {
        DBM result(values.size() + 1);
        for (unsigned i = 0; i < values.size(); ++i)
        {
            result.constrain(0, i + 1, time_bound(-values[i]));
            result.constrain(i + 1, 0, time_bound(values[i]));
        }
        return result;
    }

    bool contains(const CostDBMUnion& zones, const vector<cvalue>& values)
    {
        return zones.uncost().contains(point(values));
    }

    void expect_cost(const time_bound& actual, const cvalue expected, const string& message)
    {
        if (Avalue(actual) != Avalue(expected))
        {
            fail(message + ": expected " + Avalue(expected).to_string()
                 + ", got " + Avalue(actual).to_string());
        }
    }

    CostDBM unit_rate_past_to_two()
    {
        CostDBM facet(interval(2, 2));
        return facet.facet_past(facet, 1, 0, 1);
    }

    void test_zero_delay_branch()
    {
        CostDBM target(interval(2, 5));
        CostDBMUnion past = target.past_max(1);

        expect(contains(past, {1}), "lower-facet past must contain x=1");
        expect(contains(past, {2}), "lower-facet past must contain x=2");
        expect(contains(past, {3}), "p > sum(r) must retain zero-delay x=3");
        expect(contains(past, {5}), "p > sum(r) must retain the target upper endpoint");
        expect(!contains(past, {6}), "time predecessor must not extend beyond the target upper endpoint");
    }

    void test_equal_slope_past()
    {
        CostDBM target(interval(2, 5));
        CostDBMUnion past = target.past_max(0);

        expect(contains(past, {0}), "equal-slope past must reach the origin");
        expect(contains(past, {5}), "equal-slope past must retain the target");
        expect(!contains(past, {6}), "equal-slope past must preserve the upper bound");
        expect_cost(past.origin_cost(), 0, "equal-slope origin cost");
    }

    void test_strict_diagonal_past()
    {
        DBM target_zone(3);
        for (unsigned i = 1; i <= 2; ++i)
        {
            target_zone.constrain(0, i, time_bound::zero);
            target_zone.constrain(i, 0, time_bound(5));
        }
        target_zone.constrain(1, 2, time_bound(1, ROMEO_DBM_STRICT));

        CostDBM target(target_zone);
        CostDBMUnion past = target.past_max(-1);

        expect(contains(past, {0, 0}), "strict-diagonal past must retain valid valuations");
        expect(!contains(past, {1, 0}),
               "uniform delay cannot cross the invariant strict boundary x-y=1");
    }

    void test_cost_offset_strictness()
    {
        CostDBM weighted = unit_rate_past_to_two();

        DBM greater_than_one(2);
        greater_than_one.constrain(0, 1, time_bound(-1, ROMEO_DBM_STRICT));
        greater_than_one.constrain(1, 0, time_bound(2));
        weighted.restriction_assign(greater_than_one);
        weighted.restriction_assign(interval(2, 2));

        expect_cost(weighted.cost_offset(), 0, "attained W(2) value");
        expect(!weighted.cost_offset().strict(),
               "geometric strictness must not survive in an attained cost value");
    }

    void test_past_min_equal_slope()
    {
        CostDBM weighted = unit_rate_past_to_two();
        weighted.restriction_assign(interval(1, 2));

        CostDBMUnion past = weighted.past_min(1);
        expect(contains(past, {0}), "past_min equal-slope result must reach the origin");
        expect_cost(past.origin_cost(), -2, "past_min equal-slope origin cost");
    }

    void test_assignment_and_dimensions()
    {
        CostDBM two_dimensional(interval(0, 2));
        CostDBM three_dimensional(DBM(3));

        three_dimensional = two_dimensional;
        expect(three_dimensional.dimension() == 2, "CostDBM assignment must copy the DBM dimension");
        three_dimensional = three_dimensional;
        expect(three_dimensional.dimension() == 2, "CostDBM self-assignment must preserve the object");

        CostDBMUnion zones(two_dimensional);
        zones = zones;
        expect(zones.size() == 1 && zones.dimension() == 2,
               "CostDBMUnion self-assignment must preserve pieces and dimension");

        CostDBMUnion inferred;
        inferred.add(two_dimensional);
        expect(inferred.dimension() == 2, "an empty union must adopt its first piece dimension");

        bool rejected = false;
        try
        {
            inferred.add(CostDBM(DBM(3)));
        } catch (const invalid_argument&) {
            rejected = true;
        }
        expect(rejected, "a CostDBMUnion must reject mismatched dimensions");
    }

    void test_union_cache_and_infinity()
    {
        CostDBM zero(interval(0, 1));
        CostDBM negative(zero);
        negative.add_cost(time_bound(-5));

        CostDBMUnion zones(zero);
        expect(zones.mincost() == Avalue(0), "initial union mincost cache");
        zones.add(negative);
        expect(zones.mincost() == Avalue(-5), "union mincost cache must invalidate after add");

        expect(Avalue::infinity.is_inf(), "positive infinity predicate");
        expect(!Avalue::infinity.is_minus_inf(), "positive infinity is not negative infinity");
        expect(Avalue::minus_infinity.is_minus_inf(), "negative infinity predicate");
        expect(!Avalue::minus_infinity.is_inf(), "negative infinity is not positive infinity");
    }

    void test_whash_short_and_unaligned_buffers()
    {
        // Stable little-endian reference vectors for prefixes [1, ..., n].
        // They cover the empty input, every possible final-block length, one
        // complete non-final block, and the beginning of a third block.
        const array<uint64_t, 18> expected = {
            0x000000000000007dULL,
            0x0000b98e00000000ULL,
            0x000da88a00000000ULL,
            0x1f78ad8600000012ULL,
            0x0b7eb2820020303cULL,
            0x1384b77e505c64adULL,
            0x1b8abc7a989b5eb7ULL,
            0x2390c176e2226ac1ULL,
            0x2b96c672fa3076cbULL,
            0x23e32ba3594eb7f9ULL,
            0x9b1f1bad6dbd56b0ULL,
            0xa00c61b75cba9a51ULL,
            0xaea8a7c1af28fc0dULL,
            0xc144edcb6cd7daf7ULL,
            0xd3e133d55e581036ULL,
            0xe67d79df755ae775ULL,
            0xf919bfe93f48beb4ULL,
            0xc33711d220c54201ULL
        };

        array<byte, 18> input = {};
        for (size_t i = 0; i < input.size(); ++i)
        {
            input[i] = byte(i + 1);
        }

        for (uint32_t n = 0; n < expected.size(); ++n)
        {
            expect(whash(125, input.data(), n) == expected[n],
                   "whash stable prefix vector n=" + to_string(n));
        }

        // Exercise the original sanitizer failure on an exactly sized short
        // heap buffer, then verify that an unaligned address hashes identically.
        vector<byte> short_input(input.begin(), input.begin() + 5);
        expect(whash(125, short_input.data(), short_input.size()) == expected[5],
               "whash must not read outside an exactly sized short buffer");

        array<byte, 19> unaligned_storage = {};
        for (size_t i = 0; i < input.size(); ++i)
        {
            unaligned_storage[i + 1] = input[i];
        }
        for (uint32_t n = 0; n < expected.size(); ++n)
        {
            expect(whash(125, unaligned_storage.data() + 1, n) == expected[n],
                   "whash must be independent of input alignment at n=" + to_string(n));
        }
    }

    void test_pairing_heap_wrapper_lifetime()
    {
        // Exercise duplicate insertion, arbitrary wrapper erasure, and a
        // non-empty destructor.  ASan/LSan runs of this test guard the queue
        // wrapper ownership used by backward propagation.
        for (unsigned round = 0; round < 10; ++round)
        {
            PairingHeap<unsigned> heap;
            for (unsigned value = 0; value < 200; ++value)
            {
                heap.insert(value);
                heap.insert(value);
            }

            expect(heap.top() == 0, "pairing heap minimum after duplicate insertion");
            expect(heap.delete_value(0), "pairing heap must erase an indexed value");
            expect(heap.top() == 1, "pairing heap minimum after indexed erase");

            auto iterator = heap.iterator();
            while (!iterator.done())
            {
                if ((*iterator % 3) == 0)
                {
                    heap.erase(iterator);
                } else {
                    iterator.next();
                }
            }
            expect(heap.is_consistent(), "pairing heap links after iterator erasure");
        }
    }
}

int main()
{
    try
    {
        test_zero_delay_branch();
        test_equal_slope_past();
        test_strict_diagonal_past();
        test_cost_offset_strictness();
        test_past_min_equal_slope();
        test_assignment_and_dimensions();
        test_union_cache_and_infinity();
        test_whash_short_and_unaligned_buffers();
        test_pairing_heap_wrapper_lifetime();
    } catch (const exception& error) {
        cerr << "FAIL: " << error.what() << endl;
        return 1;
    }

    cout << "PASS: backward CostDBM regressions" << endl;
    return 0;
}
