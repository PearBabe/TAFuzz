/*
 * Opaque RIFT-M4 synthetic input case_054.
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
    int v_8ee4fd3e7500b = 10;
    /* public declaration */
    int v_bc1781611b7929e017d44 = read_arg(argc, argv, 1, 10);
    (void)v_8ee4fd3e7500b;
    (void)v_bc1781611b7929e017d44;
    /* public declaration */
    int v_983488686ee806d8a = 1;
    /* public property declaration */
    int ap_primary = (v_983488686ee806d8a > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
