/*
 * Opaque RIFT-M4 synthetic input case_083.
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
    int v_d752e3969d4a = read_arg(argc, argv, 1, 9);
    /* public declaration */
    int v_c43c68f40 = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_3796dd8a = 9;
    if (v_c43c68f40 != 0) {
        v_3796dd8a = v_d752e3969d4a;
    }
    /* public property declaration */
    int ap_primary = (v_3796dd8a > 9);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
