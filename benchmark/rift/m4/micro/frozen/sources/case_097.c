/*
 * Opaque RIFT-M4 synthetic input case_097.
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
int main(int argc, char **argv) {
    /* public declaration */
    int v_cd78a1b8a = read_arg(argc, argv, 1, 4);
    /* public declaration */
    int v_075c917037 = read_arg(argc, argv, 2, 8);
    /* public declaration */
    int v_d96a196bf1d378 = (v_cd78a1b8a > 3) && (v_075c917037 < 9);
    /* public property declaration */
    int ap_primary = v_d96a196bf1d378;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
