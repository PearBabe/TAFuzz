/*
 * Opaque RIFT-M4 synthetic input case_036.
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
    int v_8f178361eb3e1 = 3;
    /* public declaration */
    int v_f45027f95732ee5946573 = read_arg(argc, argv, 1, 3);
    (void)v_f45027f95732ee5946573;
    /* public declaration */
    int v_fa2562d5ed61f3bee = v_8f178361eb3e1;
    /* public property declaration */
    int ap_primary = (v_fa2562d5ed61f3bee > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
