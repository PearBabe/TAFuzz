/*
 * Opaque RIFT-M4 synthetic input case_084.
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
    int v_3df3cedfe = read_arg(argc, argv, 1, 4);
    /* public declaration */
    int v_bf79a9f679 = read_arg(argc, argv, 2, 8);
    (void)v_3df3cedfe;
    (void)v_bf79a9f679;
    /* public declaration */
    int v_032f379da00f5d = 1;
    /* public property declaration */
    int ap_primary = v_032f379da00f5d;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
