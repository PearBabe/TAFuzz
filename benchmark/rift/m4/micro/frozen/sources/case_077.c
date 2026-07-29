/*
 * Opaque RIFT-M4 synthetic input case_077.
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
    int v_a6f1e6f823da = read_arg(argc, argv, 1, 10);
    /* public declaration */
    int v_53797a9f1 = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_94d91f30d = v_53797a9f1 ? v_a6f1e6f823da * 2 : 0;
    /* public property declaration */
    int ap_primary = (v_94d91f30d >= 20);
    /* public property declaration */
    int ap_secondary = ((v_94d91f30d & 1) == 0 && v_94d91f30d != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
