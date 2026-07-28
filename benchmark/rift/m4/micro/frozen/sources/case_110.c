/*
 * Opaque RIFT-M4 synthetic input case_110.
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
static int transform_one(int value) { return value + 2; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_3eacfa4bfdb9 = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_e3f1872ada80 = transform_one(v_3eacfa4bfdb9);
        /* public declaration */
        int v_964ab1e5552c = transform_two(v_e3f1872ada80);
        /* public property declaration */
        int ap_primary = (v_964ab1e5552c >= 10);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
