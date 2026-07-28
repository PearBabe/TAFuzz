/*
 * Opaque RIFT-M4 synthetic input case_078.
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
static int transform_one(int value) { return value + 5; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_240e85e2b283 = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_e8c6efadabc0 = transform_one(v_240e85e2b283);
        /* public declaration */
        int v_a4dd24df6d27 = transform_two(v_e8c6efadabc0);
        /* public property declaration */
        int ap_primary = (v_a4dd24df6d27 >= 16);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
