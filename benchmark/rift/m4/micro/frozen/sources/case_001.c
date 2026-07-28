/*
 * Opaque RIFT-M4 synthetic input case_001.
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
    int v_bdd0812fc2a8 = read_arg(argc, argv, 1, 11);
    /* public declaration */
    int v_9211f8292 = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_72d58de1 = 11;
    if (v_9211f8292 != 0) {
        v_72d58de1 = v_bdd0812fc2a8;
    }
    /* public property declaration */
    int ap_primary = (v_72d58de1 > 11);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
