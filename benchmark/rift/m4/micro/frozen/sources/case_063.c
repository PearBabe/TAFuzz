/*
 * Opaque RIFT-M4 synthetic input case_063.
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
    return message->kind == 22 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_f0a564147ab19cc1f0 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        struct NeutralMessage v_9da3900cc4 = {22, v_f0a564147ab19cc1f0, 0};
        /* public declaration */
        int v_57a46374 = parse_message(&v_9da3900cc4);
        /* public property declaration */
        int ap_primary = (v_57a46374 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
