/*
 * Opaque RIFT-M4 synthetic input case_017.
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
    int v_06103d247a24 = read_arg(argc, argv, 1, 8);
    /* public declaration */
    int v_81596e52 = v_06103d247a24;
    /* public property declaration */
    int ap_primary = (v_81596e52 > 8);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
