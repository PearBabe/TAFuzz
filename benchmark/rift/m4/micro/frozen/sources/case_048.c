/*
 * Opaque RIFT-M4 synthetic input case_048.
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
    int v_94d82c24f71f = read_arg(argc, argv, 1, 4);
    /* public declaration */
    int v_2854b5b90 = v_94d82c24f71f * 2;
    /* public property declaration */
    int ap_primary = (v_2854b5b90 >= 8);
    /* public property declaration */
    int ap_secondary = ((v_2854b5b90 & 1) == 0 && v_2854b5b90 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
