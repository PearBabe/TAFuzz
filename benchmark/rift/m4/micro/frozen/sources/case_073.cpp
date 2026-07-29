/*
 * Opaque RIFT-M4 synthetic input case_073.
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
    int v_3b1432d7aa5e = read_arg(argc, argv, 1, 12);
    (void)v_3b1432d7aa5e;
    /* public declaration */
    int v_9a016f55 = 13;
    /* public property declaration */
    int ap_primary = (v_9a016f55 > 12);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
