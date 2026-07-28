/*
 * Opaque RIFT-M4 synthetic input case_025.
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
    int v_468f7940ddbdb325fc = read_arg(argc, argv, 1, 12);
    /* public declaration */
    int v_3d71b940b0199c27 = read_arg(argc, argv, 2, 12);
    /* public declaration */
    int v_148ae4b42240 = v_468f7940ddbdb325fc;
    /* public declaration */
    int v_f0dd0c56a43 = v_3d71b940b0199c27;
    /* public property declaration */
    int ap_primary = (v_f0dd0c56a43 >= v_148ae4b42240);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
