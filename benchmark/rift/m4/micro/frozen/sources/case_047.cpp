/*
 * Opaque RIFT-M4 synthetic input case_047.
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
struct NeutralMessage { int kind; int value; int spare; };
static int parse_message(const struct NeutralMessage *message) {
    return message->kind == 25 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_287578c7232dbfe4ca = read_arg(argc, argv, 1, 4);
        /* public declaration */
        int v_02ec19767bc3c9fc3 = read_arg(argc, argv, 2, 25);
        /* public declaration */
        struct NeutralMessage v_84000e377b = {v_02ec19767bc3c9fc3, v_287578c7232dbfe4ca, 0};
        /* public declaration */
        int v_7849a470 = parse_message(&v_84000e377b);
        /* public property declaration */
        int ap_primary = (v_7849a470 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
