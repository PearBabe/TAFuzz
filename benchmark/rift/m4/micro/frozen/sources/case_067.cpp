/*
 * Opaque RIFT-M4 synthetic input case_067.
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
    int v_67bdf9638d44458a1e = read_arg(argc, argv, 1, 17);
    (void)v_67bdf9638d44458a1e;
    /* public declaration */
    int v_03d0a89947a5025e = read_arg(argc, argv, 2, 17);
    /* public declaration */
    int v_8f8fda59bcef = 17;
    /* public declaration */
    int v_810a759645e = v_03d0a89947a5025e;
    /* public property declaration */
    int ap_primary = (v_810a759645e >= v_8f8fda59bcef);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
