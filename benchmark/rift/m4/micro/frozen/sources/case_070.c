/*
 * Opaque RIFT-M4 synthetic input case_070.
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
    int v_0c3f22812400 = read_arg(argc, argv, 1, 9);
    /* public declaration */
    int v_dcdd72f6d = read_arg(argc, argv, 2, 1);
    int result = 0;
    if (v_dcdd72f6d != 0 && v_0c3f22812400 > 9) { result = 1; }
    /* public property declaration */
    int ap_primary = result;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
