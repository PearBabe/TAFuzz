/*
 * Opaque RIFT-M4 synthetic input case_011.
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
    int v_4dd04abd83104723f4 = read_arg(argc, argv, 1, 19);
    (void)v_4dd04abd83104723f4;
    /* public declaration */
    int v_178032a6f1abee71 = read_arg(argc, argv, 2, 19);
    /* public declaration */
    int v_07b9d01fdd33 = 19;
    /* public declaration */
    int v_5c70534a7eb = v_178032a6f1abee71;
    /* public property declaration */
    int ap_primary = (v_5c70534a7eb >= v_07b9d01fdd33);
    printf("AP_primary=%d\n", ap_primary);
    return 0;
}
