/*
 * Opaque RIFT-M4 synthetic input case_116.
 * Evaluation metadata is intentionally excluded.
 * Property locations are supplied separately in typed Property IR.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int read_arg(int argc, char **argv, int index, int fallback) {
    if (index >= argc) {
        return fallback;
    }
    char *end = NULL;
    long value = strtol(argv[index], &end, 10);
    return (end == argv[index]) ? fallback : (int)value;
}
struct NeutralContext { int ready; int mode; int state; };
static void initialize_context(struct NeutralContext *context) { context->ready = 1; }
static void select_mode(struct NeutralContext *context, int mode) { context->mode = mode; }
static void commit_if_ready(struct NeutralContext *context, int value) {
    if (context->ready && context->mode == 2) { context->state = value; }
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_927f3356c46a = read_arg(argc, argv, 1, 8);
        /* public declaration */
        int v_bb8e0ac0b838bf5 = read_arg(argc, argv, 2, 2);
        /* public declaration */
        struct NeutralContext v_c40171b9a1 = {0, 0, 0};
        initialize_context(&v_c40171b9a1);
        select_mode(&v_c40171b9a1, v_bb8e0ac0b838bf5);
        commit_if_ready(&v_c40171b9a1, v_927f3356c46a);
        /* public declaration */
        int v_2bc89664 = v_c40171b9a1.state;
        /* public property declaration */
        int ap_primary = (v_2bc89664 == 8);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
