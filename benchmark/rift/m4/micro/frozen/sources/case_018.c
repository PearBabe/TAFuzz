/*
 * Opaque RIFT-M4 synthetic input case_018.
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
static int transform_one(int value) { return value + 8; }
static int transform_two(int value) { return value * 2; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_76e6f6035246 = read_arg(argc, argv, 1, 3);
        /* public declaration */
        int v_e9057691e = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_9aac6b782815 = v_e9057691e ? transform_one(v_76e6f6035246) : 8;
        /* public declaration */
        int v_78c37dccdb0b = transform_two(v_9aac6b782815);
        /* public property declaration */
        int ap_primary = (v_78c37dccdb0b >= 22);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
