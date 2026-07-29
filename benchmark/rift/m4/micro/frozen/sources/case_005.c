/*
 * Opaque RIFT-M4 synthetic input case_005.
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
static int transform_one(int value) { return value + 10; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_552363e625a4 = read_arg(argc, argv, 1, 3);
        (void)transform_one(v_552363e625a4);
        /* public declaration */
        int v_fc06fa7dbef9 = transform_one(10);
        /* public declaration */
        int v_0a4b47c0608d = transform_two(v_fc06fa7dbef9);
        /* public property declaration */
        int ap_primary = (v_0a4b47c0608d >= 22);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
