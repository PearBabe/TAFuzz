/*
 * Opaque RIFT-M4 synthetic input case_040.
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
    int v_b12fd9994 = read_arg(argc, argv, 1, 9);
    /* public declaration */
    int v_b32b5b5e82 = read_arg(argc, argv, 2, 13);
    /* public declaration */
    int v_5ab64493d = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_7a783c12e6c60e = v_5ab64493d && (v_b12fd9994 > 8) && (v_b32b5b5e82 < 14);
    /* public property declaration */
    int ap_primary = v_7a783c12e6c60e;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
