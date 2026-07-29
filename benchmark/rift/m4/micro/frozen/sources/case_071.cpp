/*
 * Opaque RIFT-M4 synthetic input case_071.
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
    int v_d939918bebfd = read_arg(argc, argv, 1, 11);
    (void)v_d939918bebfd;
    /* public declaration */
    int v_f327f0cd4 = 22;
    /* public property declaration */
    int ap_primary = (v_f327f0cd4 >= 22);
    /* public property declaration */
    int ap_secondary = ((v_f327f0cd4 & 1) == 0 && v_f327f0cd4 != 0);
    printf("AP_primary=%d AP_secondary=%d\n", ap_primary, ap_secondary);
    return 0;
}
