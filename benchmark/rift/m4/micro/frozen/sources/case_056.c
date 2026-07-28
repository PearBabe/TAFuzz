/*
 * Opaque RIFT-M4 synthetic input case_056.
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
    return message->kind == 28 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_41b06dc971a39ff7db = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_7fa1970bc9 = {28, 4, v_41b06dc971a39ff7db};
        /* public declaration */
        int v_ad089619 = parse_message(&v_7fa1970bc9);
        /* public property declaration */
        int ap_primary = (v_ad089619 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
