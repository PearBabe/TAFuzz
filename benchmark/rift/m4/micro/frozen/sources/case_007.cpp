/*
 * Opaque RIFT-M4 synthetic input case_007.
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
    int v_a1816ffc5 = read_arg(argc, argv, 1, 7);
    /* public declaration */
    int v_c07de4dbb8 = read_arg(argc, argv, 2, 11);
    /* public declaration */
    int v_64c297a52b0d89 = (v_a1816ffc5 > 6) && (v_c07de4dbb8 < 12);
    /* public property declaration */
    int ap_primary = v_64c297a52b0d89;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
