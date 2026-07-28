/*
 * Opaque RIFT-M4 synthetic input case_068.
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
static int transform_one(int value) { return value + 6; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_56cfab785ac5 = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_446918675 = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_f0f131b79c1a = v_446918675 ? transform_one(v_56cfab785ac5) : 6;
        /* public declaration */
        int v_b69cb2287041 = transform_two(v_f0f131b79c1a);
        /* public property declaration */
        int ap_primary = (v_b69cb2287041 >= 18);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
