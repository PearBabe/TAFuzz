/*
 * Opaque RIFT-M4 synthetic input case_041.
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
    int v_001ca80bbdd2e94fae = read_arg(argc, argv, 1, 13);
    /* public declaration */
    int v_1d154361d6f6405d = read_arg(argc, argv, 2, 13);
    /* public declaration */
    int v_944766cb898c = v_001ca80bbdd2e94fae;
    /* public declaration */
    int v_38612f59ce4 = v_1d154361d6f6405d;
    /* public property declaration */
    int ap_primary = (v_38612f59ce4 >= v_944766cb898c);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
