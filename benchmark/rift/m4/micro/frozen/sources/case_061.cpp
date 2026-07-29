/*
 * Opaque RIFT-M4 synthetic input case_061.
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
    int v_bee69e1dec43 = read_arg(argc, argv, 1, 13);
    (void)v_bee69e1dec43;
    /* public declaration */
    int v_e745e7a51 = 26;
    /* public property declaration */
    int ap_primary = (v_e745e7a51 >= 26);
    /* public property declaration */
    int ap_secondary = ((v_e745e7a51 & 1) == 0 && v_e745e7a51 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
