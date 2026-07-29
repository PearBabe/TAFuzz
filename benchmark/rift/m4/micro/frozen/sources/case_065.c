/*
 * Opaque RIFT-M4 synthetic input case_065.
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
    int v_906758d82 = read_arg(argc, argv, 1, 4);
    /* public declaration */
    int v_d8b9652d51 = read_arg(argc, argv, 2, 8);
    (void)v_906758d82;
    (void)v_d8b9652d51;
    /* public declaration */
    int v_93faebbaa73ea9 = 1;
    /* public property declaration */
    int ap_primary = v_93faebbaa73ea9;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
