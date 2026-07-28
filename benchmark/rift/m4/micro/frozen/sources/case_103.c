/*
 * Opaque RIFT-M4 synthetic input case_103.
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
    int v_e36db57cf = read_arg(argc, argv, 1, 6);
    /* public declaration */
    int v_5706bf727e = read_arg(argc, argv, 2, 10);
    /* public declaration */
    int v_18b9ad001a5f24 = (v_e36db57cf > 5) && (v_5706bf727e < 11);
    /* public property declaration */
    int ap_primary = v_18b9ad001a5f24;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
