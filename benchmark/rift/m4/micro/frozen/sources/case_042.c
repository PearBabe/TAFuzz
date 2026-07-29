/*
 * Opaque RIFT-M4 synthetic input case_042.
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
    int v_0f4050a596205 = 1;
    /* public declaration */
    int v_e34c48332ae3e63d4b749 = read_arg(argc, argv, 1, 1);
    (void)v_e34c48332ae3e63d4b749;
    /* public declaration */
    int v_0e4a2c713c654678e = v_0f4050a596205;
    /* public property declaration */
    int ap_primary = (v_0e4a2c713c654678e > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
