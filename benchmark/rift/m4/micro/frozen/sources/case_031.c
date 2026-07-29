/*
 * Opaque RIFT-M4 synthetic input case_031.
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
    int v_b20b1464c88d = read_arg(argc, argv, 1, 7);
    /* public declaration */
    int v_21c9f43c = v_b20b1464c88d;
    /* public property declaration */
    int ap_primary = (v_21c9f43c > 7);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
