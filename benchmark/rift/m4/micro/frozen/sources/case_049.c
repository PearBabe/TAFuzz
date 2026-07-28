/*
 * Opaque RIFT-M4 synthetic input case_049.
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
        int v_be5904431502 = read_arg(argc, argv, 1, 8);
        /* public declaration */
        int v_4af16f59aa14c21 = read_arg(argc, argv, 2, 2);
        /* public declaration */
        struct NeutralContext v_c133ebc2ea = {0, 0, 0};
        initialize_context(&v_c133ebc2ea);
        select_mode(&v_c133ebc2ea, v_4af16f59aa14c21);
        commit_if_ready(&v_c133ebc2ea, v_be5904431502);
        /* public declaration */
        int v_f6e064df = v_c133ebc2ea.state;
        /* public property declaration */
        int ap_primary = (v_f6e064df == 8);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
