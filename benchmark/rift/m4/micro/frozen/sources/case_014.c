/*
 * Opaque RIFT-M4 synthetic input case_014.
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
    int v_2b7ed9c4a = read_arg(argc, argv, 1, 10);
    /* public declaration */
    int v_adaf419280 = read_arg(argc, argv, 2, 14);
    /* public declaration */
    int v_fc9b09d8f = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_0dcb34d5eca111 = v_fc9b09d8f && (v_2b7ed9c4a > 9) && (v_adaf419280 < 15);
    /* public property declaration */
    int ap_primary = v_0dcb34d5eca111;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
