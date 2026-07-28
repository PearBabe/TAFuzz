/*
 * Opaque RIFT-M4 synthetic input case_021.
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
    int v_05a8c381d = read_arg(argc, argv, 1, 5);
    /* public declaration */
    int v_b2368dd450 = read_arg(argc, argv, 2, 9);
    /* public declaration */
    int v_172a6c4592213d = (v_05a8c381d > 4) && (v_b2368dd450 < 10);
    /* public property declaration */
    int ap_primary = v_172a6c4592213d;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
