/*
 * Opaque RIFT-M4 synthetic input case_004.
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
            int v_045f0ffee308 = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_53b24ce3 = &first;
            v_53b24ce3->observed = v_045f0ffee308;
            /* public declaration */
            int v_8609a18b = first.observed;
            /* public property declaration */
            int ap_primary = (v_8609a18b != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
