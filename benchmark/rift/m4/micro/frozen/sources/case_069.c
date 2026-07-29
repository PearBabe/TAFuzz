/*
 * Opaque RIFT-M4 synthetic input case_069.
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
    return message->kind == 20 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_8ea084039ac55a4166 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_19764b4268 = {20, v_8ea084039ac55a4166, 0};
        /* public declaration */
        int v_2ac9ca8b = parse_message(&v_19764b4268);
        /* public property declaration */
        int ap_primary = (v_2ac9ca8b > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
