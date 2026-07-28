/*
 * Opaque RIFT-M4 synthetic input case_030.
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
            int v_8b643155115c = read_arg(argc, argv, 1, 7);
            /* public declaration */
            int v_947a4b0de = read_arg(argc, argv, 2, 1);
            struct NeutralRecord first = {0, 0};
            struct NeutralRecord second = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_cffe3d8b = v_947a4b0de ? &first : &second;
            v_cffe3d8b->observed = v_8b643155115c;
            /* public declaration */
            int v_84fff2c9 = first.observed;
            /* public property declaration */
            int ap_primary = (v_84fff2c9 != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
