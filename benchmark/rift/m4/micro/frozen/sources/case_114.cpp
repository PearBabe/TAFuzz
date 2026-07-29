/*
 * Opaque RIFT-M4 synthetic input case_114.
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
    int v_581123fe7133be6455 = read_arg(argc, argv, 1, 11);
    /* public declaration */
    int v_a15e47755185a660 = read_arg(argc, argv, 2, 11);
    /* public declaration */
    int v_840963339faf = v_581123fe7133be6455;
    /* public declaration */
    int v_cf1f94f0981 = v_a15e47755185a660;
    /* public property declaration */
    int ap_primary = (v_cf1f94f0981 >= v_840963339faf);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
