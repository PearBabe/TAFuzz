/*
 * Opaque RIFT-M4 synthetic input case_094.
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
    int v_98d1cabba5893b97be = read_arg(argc, argv, 1, 18);
    (void)v_98d1cabba5893b97be;
    /* public declaration */
    int v_8909cc0c9da463b7 = read_arg(argc, argv, 2, 18);
    /* public declaration */
    int v_951c7d021ab1 = 18;
    /* public declaration */
    int v_0d99ef16d5b = v_8909cc0c9da463b7;
    /* public property declaration */
    int ap_primary = (v_0d99ef16d5b >= v_951c7d021ab1);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
