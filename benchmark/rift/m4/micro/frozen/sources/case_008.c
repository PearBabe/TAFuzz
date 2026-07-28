/*
 * Opaque RIFT-M4 synthetic input case_008.
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
            int v_fbf2d4020498 = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_d7fef879 = &first;
            v_d7fef879->observed = v_fbf2d4020498;
            /* public declaration */
            int v_2556a19c = first.observed;
            /* public property declaration */
            int ap_primary = (v_2556a19c != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
