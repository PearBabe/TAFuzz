/*
 * Opaque RIFT-M4 synthetic input case_115.
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
static int transform_one(int value) { return value + 9; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_312884cbb6b1 = read_arg(argc, argv, 1, 3);
        (void)transform_one(v_312884cbb6b1);
        /* public declaration */
        int v_4d9f3de0870e = transform_one(9);
        /* public declaration */
        int v_a51139e4e619 = transform_two(v_4d9f3de0870e);
        /* public property declaration */
        int ap_primary = (v_a51139e4e619 >= 20);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
