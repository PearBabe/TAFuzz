/*
 * Opaque RIFT-M4 synthetic input case_093.
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
static int transform_one(int value) { return value + 11; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_16248089db92 = read_arg(argc, argv, 1, 3);
        (void)transform_one(v_16248089db92);
        /* public declaration */
        int v_5adf1ef3c8cb = transform_one(11);
        /* public declaration */
        int v_eedd7fd42e73 = transform_two(v_5adf1ef3c8cb);
        /* public property declaration */
        int ap_primary = (v_eedd7fd42e73 >= 24);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
