/*
 * Opaque RIFT-M4 synthetic input case_089.
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
    int v_40d7d9d1edee = read_arg(argc, argv, 1, 7);
    /* public declaration */
    int v_954a8d62e = read_arg(argc, argv, 2, 1);
    int result = 0;
    if (v_954a8d62e != 0 && v_40d7d9d1edee > 7) { result = 1; }
    /* public property declaration */
    int ap_primary = result;
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
