/*
 * Opaque RIFT-M4 synthetic input case_095.
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
    int v_eda9c3d41e5a9 = 7;
    /* public declaration */
    int v_a23a29b84e4e165a14ae4 = read_arg(argc, argv, 1, 7);
    (void)v_a23a29b84e4e165a14ae4;
    /* public declaration */
    int v_d18cb35ea = read_arg(argc, argv, 2, 1);
    /* public declaration */
    int v_d5be18233741262d4 = v_d18cb35ea ? v_eda9c3d41e5a9 : 0;
    /* public property declaration */
    int ap_primary = (v_d5be18233741262d4 > 0);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
