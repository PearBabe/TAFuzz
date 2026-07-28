/*
 * Opaque RIFT-M4 synthetic input case_051.
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
static int transform_one(int value) { return value + 4; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_9ee33f8a95b6 = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_4e329e032b63 = transform_one(v_9ee33f8a95b6);
        /* public declaration */
        int v_125703265069 = transform_two(v_4e329e032b63);
        /* public property declaration */
        int ap_primary = (v_125703265069 >= 14);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
