/*
 * Opaque RIFT-M4 synthetic input case_090.
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
    int v_bb28bb8cc927 = read_arg(argc, argv, 1, 10);
    /* public declaration */
    int v_aa350887e = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_c6ddc1bc = 10;
    if (v_aa350887e != 0) {
        v_c6ddc1bc = v_bb28bb8cc927;
    }
    /* public property declaration */
    int ap_primary = (v_c6ddc1bc > 10);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
