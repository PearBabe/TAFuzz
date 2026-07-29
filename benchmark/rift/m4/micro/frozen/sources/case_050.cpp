/*
 * Opaque RIFT-M4 synthetic input case_050.
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
    int v_f25cd788646e7 = 6;
    /* public declaration */
    int v_38dd8047b391630fef9d6 = read_arg(argc, argv, 1, 6);
    (void)v_38dd8047b391630fef9d6;
    /* public declaration */
    int v_32bab0cdd = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_6c65df095ece7ec38 = v_32bab0cdd ? v_f25cd788646e7 : 0;
    /* public property declaration */
    int ap_primary = (v_6c65df095ece7ec38 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
