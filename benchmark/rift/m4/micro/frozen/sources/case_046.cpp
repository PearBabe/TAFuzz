/*
 * Opaque RIFT-M4 synthetic input case_046.
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
    int v_5221aa0e0c01456b05 = read_arg(argc, argv, 1, 15);
    /* public declaration */
    int v_b6081c38696f7757 = read_arg(argc, argv, 2, 15);
    /* public declaration */
    int v_b680a3f20 = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_2da917014f59 = v_b680a3f20 ? v_5221aa0e0c01456b05 : 15;
    /* public declaration */
    int v_75e8a100fc0 = v_b6081c38696f7757;
    /* public property declaration */
    int ap_primary = (v_75e8a100fc0 >= v_2da917014f59);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
