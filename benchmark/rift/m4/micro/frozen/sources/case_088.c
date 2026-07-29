/*
 * Opaque RIFT-M4 synthetic input case_088.
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
    int v_7f72521143793 = 5;
    /* public declaration */
    int v_25807e57135cda374ad8c = read_arg(argc, argv, 1, 5);
    (void)v_25807e57135cda374ad8c;
    /* public declaration */
    int v_6de4311ac = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_3244c77891fbf309e = v_6de4311ac ? v_7f72521143793 : 0;
    /* public property declaration */
    int ap_primary = (v_3244c77891fbf309e > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
