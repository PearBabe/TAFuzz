/*
 * Opaque RIFT-M4 synthetic input case_091.
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
    int v_138ca864503c = read_arg(argc, argv, 1, 9);
    /* public declaration */
    int v_d397ce511 = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_82ff612f7 = v_d397ce511 ? v_138ca864503c * 2 : 0;
    /* public property declaration */
    int ap_primary = (v_82ff612f7 >= 18);
    /* public property declaration */
    int ap_secondary = ((v_82ff612f7 & 1) == 0 && v_82ff612f7 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
