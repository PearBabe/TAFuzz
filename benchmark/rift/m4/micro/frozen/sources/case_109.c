/*
 * Opaque RIFT-M4 synthetic input case_109.
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
    int v_f7b7c0dad712 = read_arg(argc, argv, 1, 12);
    (void)v_f7b7c0dad712;
    /* public declaration */
    int v_eac5dcad1 = 24;
    /* public property declaration */
    int ap_primary = (v_eac5dcad1 >= 24);
    /* public property declaration */
    int ap_secondary = ((v_eac5dcad1 & 1) == 0 && v_eac5dcad1 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
