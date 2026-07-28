/*
 * Opaque RIFT-M4 synthetic input case_076.
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
    int v_276866e04fb1 = read_arg(argc, argv, 1, 6);
    /* public declaration */
    int v_4b6436f2 = v_276866e04fb1;
    /* public property declaration */
    int ap_primary = (v_4b6436f2 > 6);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
