/*
 * Opaque RIFT-M4 synthetic input case_059.
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
    int v_fb757d1c73ade539e9 = read_arg(argc, argv, 1, 14);
    /* public declaration */
    int v_e10dfde6daab06a4 = read_arg(argc, argv, 2, 14);
    /* public declaration */
    int v_a1ac240f5 = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_15982dc45b00 = v_a1ac240f5 ? v_fb757d1c73ade539e9 : 14;
    /* public declaration */
    int v_4e85168fdf7 = v_e10dfde6daab06a4;
    /* public property declaration */
    int ap_primary = (v_4e85168fdf7 >= v_15982dc45b00);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
