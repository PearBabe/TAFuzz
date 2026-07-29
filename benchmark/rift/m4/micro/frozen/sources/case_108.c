/*
 * Opaque RIFT-M4 synthetic input case_108.
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
    int v_d34ba318f7eb = read_arg(argc, argv, 1, 13);
    (void)v_d34ba318f7eb;
    /* public declaration */
    int v_ffef55b8 = 14;
    /* public property declaration */
    int ap_primary = (v_ffef55b8 > 13);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
