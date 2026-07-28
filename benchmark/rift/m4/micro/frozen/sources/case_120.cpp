/*
 * Opaque RIFT-M4 synthetic input case_120.
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
static int transform_one(int value) { return value + 3; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_e71703d3620f = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_d5cc38d55295 = transform_one(v_e71703d3620f);
        /* public declaration */
        int v_f6b0b94c7f65 = transform_two(v_d5cc38d55295);
        /* public property declaration */
        int ap_primary = (v_f6b0b94c7f65 >= 12);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
