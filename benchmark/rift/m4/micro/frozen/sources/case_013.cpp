/*
 * Opaque RIFT-M4 synthetic input case_013.
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
    int v_5297300f1f784 = 8;
    /* public declaration */
    int v_c4c91a9fe7658c81b8305 = read_arg(argc, argv, 1, 8);
    (void)v_5297300f1f784;
    (void)v_c4c91a9fe7658c81b8305;
    /* public declaration */
    int v_2f5d0d4d036040a97 = 1;
    /* public property declaration */
    int ap_primary = (v_2f5d0d4d036040a97 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
