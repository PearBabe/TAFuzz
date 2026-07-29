/*
 * Opaque RIFT-M4 synthetic input case_026.
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
    int v_dddae6121c18e = 9;
    /* public declaration */
    int v_13f062bbd634405166792 = read_arg(argc, argv, 1, 9);
    (void)v_dddae6121c18e;
    (void)v_13f062bbd634405166792;
    /* public declaration */
    int v_efbbb14f36ca17998 = 1;
    /* public property declaration */
    int ap_primary = (v_efbbb14f36ca17998 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
