/*
 * Opaque RIFT-M4 synthetic input case_111.
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
    int v_017d79d0e6cc = read_arg(argc, argv, 1, 11);
    (void)v_017d79d0e6cc;
    int result = (8 % 2);
    /* public property declaration */
    int ap_primary = result;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
