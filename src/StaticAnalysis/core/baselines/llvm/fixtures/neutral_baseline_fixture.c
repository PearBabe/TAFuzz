typedef struct NeutralCell {
    int state;
    int spare;
} NeutralCell;

__attribute__((noinline)) int neutral_ssa_chain(int source, int unrelated) {
#line 101 "neutral_baseline_fixture.c"
    int stage = source + 7;
#line 102 "neutral_baseline_fixture.c"
    int proposition = stage > 9;
#line 103 "neutral_baseline_fixture.c"
    int decoy = unrelated - 3;
#line 104 "neutral_baseline_fixture.c"
    return proposition + (decoy == 9999);
}

__attribute__((noinline)) int neutral_memory_must(int source) {
    NeutralCell cell = {0, 0};
#line 201 "neutral_baseline_fixture.c"
    cell.state = source;
#line 202 "neutral_baseline_fixture.c"
    int observed = cell.state;
#line 203 "neutral_baseline_fixture.c"
    int proposition = observed > 3;
#line 204 "neutral_baseline_fixture.c"
    return proposition;
}

__attribute__((noinline)) int neutral_memory_may(
    int *left, int *right, int source) {
#line 301 "neutral_baseline_fixture.c"
    *left = source;
#line 302 "neutral_baseline_fixture.c"
    int observed = *right;
#line 303 "neutral_baseline_fixture.c"
    int proposition = observed > 5;
#line 304 "neutral_baseline_fixture.c"
    return proposition;
}

__attribute__((noinline)) void neutral_svf_write(
    NeutralCell *cell, int source) {
#line 401 "neutral_baseline_fixture.c"
    cell->state = source;
}

__attribute__((noinline)) int neutral_svf_read(NeutralCell *cell) {
#line 402 "neutral_baseline_fixture.c"
    int observed = cell->state;
#line 403 "neutral_baseline_fixture.c"
    int proposition = observed != 0;
#line 404 "neutral_baseline_fixture.c"
    return proposition;
}

__attribute__((noinline)) int neutral_svf_driver(int source) {
    NeutralCell cell = {0, 0};
    neutral_svf_write(&cell, source);
    return neutral_svf_read(&cell);
}
