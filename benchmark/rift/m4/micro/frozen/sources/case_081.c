/*
 * Opaque RIFT-M4 synthetic input case_081.
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
    int v_dc08604e5a55 = read_arg(argc, argv, 1, 5);
    /* public declaration */
    int v_0d5bb894 = v_dc08604e5a55;
    /* public property declaration */
    int ap_primary = (v_0d5bb894 > 5);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
