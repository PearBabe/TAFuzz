/*
 * Opaque RIFT-M4 synthetic input case_009.
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
static int transform_one(int value) { return value + 7; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_e1a290c6fa3c = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_b0f44b187 = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_6c77af3d28db = v_b0f44b187 ? transform_one(v_e1a290c6fa3c) : 7;
        /* public declaration */
        int v_7f33aa7d7d0f = transform_two(v_6c77af3d28db);
        /* public property declaration */
        int ap_primary = (v_7f33aa7d7d0f >= 20);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
