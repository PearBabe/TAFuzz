/*
 * Opaque RIFT-M4 synthetic input case_101.
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
        int v_2a639c4ab1c5 = read_arg(argc, argv, 1, 8);
        /* public declaration */
        struct NeutralContext v_0c6cc4db9d = {0, 0, 0};
        initialize_context(&v_0c6cc4db9d);
        select_mode(&v_0c6cc4db9d, 2);
        commit_if_ready(&v_0c6cc4db9d, v_2a639c4ab1c5);
        /* public declaration */
        int v_d0b9400e = v_0c6cc4db9d.state;
        /* public property declaration */
        int ap_primary = (v_d0b9400e == 8);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
