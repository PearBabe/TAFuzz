/*
 * Opaque RIFT-M4 synthetic input case_020.
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
    return message->kind == 27 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_b19dff48e88cf09b68 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_a14fd973fa = {27, 4, v_b19dff48e88cf09b68};
        /* public declaration */
        int v_a0ed45cc = parse_message(&v_a14fd973fa);
        /* public property declaration */
        int ap_primary = (v_a0ed45cc > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
