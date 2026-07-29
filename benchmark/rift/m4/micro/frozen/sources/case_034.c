/*
 * Opaque RIFT-M4 synthetic input case_034.
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
    return message->kind == 26 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_cc23bb2ee0d02ed5e7 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        int v_0142dbd03c3283d61 = read_arg(argc, argv, 2, 26);
        /* public declaration */
        struct NeutralMessage v_d02f7d8bc1 = {v_0142dbd03c3283d61, v_cc23bb2ee0d02ed5e7, 0};
        /* public declaration */
        int v_168354fc = parse_message(&v_d02f7d8bc1);
        /* public property declaration */
        int ap_primary = (v_168354fc > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
