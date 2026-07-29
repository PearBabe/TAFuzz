/*
 * Opaque RIFT-M4 synthetic input case_117.
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
    int v_5dc502049fe8a = 2;
    /* public declaration */
    int v_da666bc58ff68ae64a320 = read_arg(argc, argv, 1, 2);
    (void)v_da666bc58ff68ae64a320;
    /* public declaration */
    int v_ae2f40021a2ff3993 = v_5dc502049fe8a;
    /* public property declaration */
    int ap_primary = (v_ae2f40021a2ff3993 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
