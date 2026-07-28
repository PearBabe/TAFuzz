/*
 * Opaque RIFT-M4 synthetic input case_066.
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
    int v_4a96101f5 = read_arg(argc, argv, 1, 8);
    /* public declaration */
    int v_f0483451ac = read_arg(argc, argv, 2, 12);
    /* public declaration */
    int v_dcf749933 = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_9e4e7a0ec71240 = v_dcf749933 && (v_4a96101f5 > 7) && (v_f0483451ac < 13);
    /* public property declaration */
    int ap_primary = v_9e4e7a0ec71240;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
