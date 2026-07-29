/*
 * Opaque RIFT-M4 synthetic input case_086.
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
struct NeutralRecord { int observed; int shadow; };

        int main(int argc, char **argv) {
            /* public declaration */
            int v_bfba97b4a8ae = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {1, 0};
            struct NeutralRecord second = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_20fb8e10 = &second;
            v_20fb8e10->shadow = v_bfba97b4a8ae;
            /* public declaration */
            int v_06aa23c4 = first.observed;
            /* public property declaration */
            int ap_primary = (v_06aa23c4 != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
