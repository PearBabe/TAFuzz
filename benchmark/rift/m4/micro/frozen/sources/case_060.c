/*
 * Opaque RIFT-M4 synthetic input case_060.
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
    int v_d7914650a84dc3fbf4 = read_arg(argc, argv, 1, 16);
    /* public declaration */
    int v_38a8baf45590a73e = read_arg(argc, argv, 2, 16);
    /* public declaration */
    int v_c1fef6840 = read_arg(argc, argv, 3, 1);
    /* public declaration */
    int v_10ce56fdd942 = v_c1fef6840 ? v_d7914650a84dc3fbf4 : 16;
    /* public declaration */
    int v_eee47b73809 = v_38a8baf45590a73e;
    /* public property declaration */
    int ap_primary = (v_eee47b73809 >= v_10ce56fdd942);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
