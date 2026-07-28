/*
 * Opaque RIFT-M4 synthetic input case_043.
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
    return message->kind == 29 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_e317ad32c56e35d979 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_3226446f2f = {29, 4, v_e317ad32c56e35d979};
        /* public declaration */
        int v_5cdfc570 = parse_message(&v_3226446f2f);
        /* public property declaration */
        int ap_primary = (v_5cdfc570 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
