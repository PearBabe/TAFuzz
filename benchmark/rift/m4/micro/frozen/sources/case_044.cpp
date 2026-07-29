/*
 * Opaque RIFT-M4 synthetic input case_044.
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
        int v_3e2c90bc9f0a = read_arg(argc, argv, 1, 8);
        /* public declaration */
        struct NeutralContext v_0c26a0902d = {0, 0, 0};
        commit_if_ready(&v_0c26a0902d, v_3e2c90bc9f0a);
        initialize_context(&v_0c26a0902d);
        select_mode(&v_0c26a0902d, 2);
        v_0c26a0902d.state = 8;
        /* public declaration */
        int v_b5c87d42 = v_0c26a0902d.state;
        /* public property declaration */
        int ap_primary = (v_b5c87d42 == 8);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
