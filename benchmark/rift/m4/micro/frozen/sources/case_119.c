/*
 * Opaque RIFT-M4 synthetic input case_119.
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
    int v_5aa5134bf6638c7c9f = read_arg(argc, argv, 1, 10);
    /* public declaration */
    int v_0a09c82b3729f13b = read_arg(argc, argv, 2, 10);
    /* public declaration */
    int v_c4d17318bdfc = v_5aa5134bf6638c7c9f;
    /* public declaration */
    int v_490a5b4ffba = v_0a09c82b3729f13b;
    /* public property declaration */
    int ap_primary = (v_490a5b4ffba >= v_c4d17318bdfc);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
