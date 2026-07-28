/*
 * Opaque RIFT-M4 synthetic input case_082.
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
    int v_1c501c4189c8 = read_arg(argc, argv, 1, 5);
    /* public declaration */
    int v_f5b37ec5e = v_1c501c4189c8 * 2;
    /* public property declaration */
    int ap_primary = (v_f5b37ec5e >= 10);
    /* public property declaration */
    int ap_secondary = ((v_f5b37ec5e & 1) == 0 && v_f5b37ec5e != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
