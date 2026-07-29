/*
 * Opaque RIFT-M4 synthetic input case_045.
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
    int v_cc0543d9e5c1 = read_arg(argc, argv, 1, 8);
    /* public declaration */
    int v_945849250 = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_10c783b89 = v_945849250 ? v_cc0543d9e5c1 * 2 : 0;
    /* public property declaration */
    int ap_primary = (v_10c783b89 >= 16);
    /* public property declaration */
    int ap_secondary = ((v_10c783b89 & 1) == 0 && v_10c783b89 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
