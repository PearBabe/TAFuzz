/*
 * Opaque RIFT-M4 synthetic input case_024.
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
    return message->kind == 24 ? message->value : 0;
}

    int main(int argc, char **argv) {
        /* public declaration */
        int v_c9d506d7e20ea41549 = read_arg(argc, argv, 1, 4);
        /* public declaration */
        int v_534950394fb4fade0 = read_arg(argc, argv, 2, 24);
        /* public declaration */
        struct NeutralMessage v_78dd17e163 = {v_534950394fb4fade0, v_c9d506d7e20ea41549, 0};
        /* public declaration */
        int v_4622afa4 = parse_message(&v_78dd17e163);
        /* public property declaration */
        int ap_primary = (v_4622afa4 > 3);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
