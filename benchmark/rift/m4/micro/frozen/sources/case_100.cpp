/*
 * Opaque RIFT-M4 synthetic input case_100.
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
    int v_836b24ac6d7e = read_arg(argc, argv, 1, 14);
    (void)v_836b24ac6d7e;
    /* public declaration */
    int v_fc45df46 = 15;
    /* public property declaration */
    int ap_primary = (v_fc45df46 > 14);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
