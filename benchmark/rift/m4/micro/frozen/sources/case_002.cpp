/*
 * Opaque RIFT-M4 synthetic input case_002.
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
    int v_c5f1bd82516e7 = 4;
    /* public declaration */
    int v_2ba01ef36bc8fa3fd09ac = read_arg(argc, argv, 1, 4);
    (void)v_2ba01ef36bc8fa3fd09ac;
    /* public declaration */
    int v_d507285a036bc0227 = v_c5f1bd82516e7;
    /* public property declaration */
    int ap_primary = (v_d507285a036bc0227 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
