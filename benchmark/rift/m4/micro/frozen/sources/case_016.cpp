/*
 * Opaque RIFT-M4 synthetic input case_016.
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
    int v_45a46de8be23 = read_arg(argc, argv, 1, 10);
    (void)v_45a46de8be23;
    int result = (7 % 2);
    /* public property declaration */
    int ap_primary = result;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
