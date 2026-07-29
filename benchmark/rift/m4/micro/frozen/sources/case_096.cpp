/*
 * Opaque RIFT-M4 synthetic input case_096.
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
    return message->kind == 23 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_f1124408bb9f1b3d42 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_1e56a975a8 = {23, v_f1124408bb9f1b3d42, 0};
        /* public declaration */
        int v_ff23c006 = parse_message(&v_1e56a975a8);
        /* public property declaration */
        int ap_primary = (v_ff23c006 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
