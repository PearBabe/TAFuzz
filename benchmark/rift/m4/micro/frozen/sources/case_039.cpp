/*
 * Opaque RIFT-M4 synthetic input case_039.
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
    int v_50989c8b2809 = read_arg(argc, argv, 1, 7);
    /* public declaration */
    int v_6710a2257 = v_50989c8b2809 * 2;
    /* public property declaration */
    int ap_primary = (v_6710a2257 >= 14);
    /* public property declaration */
    int ap_secondary = ((v_6710a2257 & 1) == 0 && v_6710a2257 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
