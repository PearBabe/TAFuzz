/*
 * Opaque RIFT-M4 synthetic input case_058.
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
            int v_fa20bfbda96c = read_arg(argc, argv, 1, 7);
            /* public declaration */
            int v_f164b4427 = read_arg(argc, argv, 2, 1);
            struct NeutralRecord first = {0, 0};
            struct NeutralRecord second = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_5ee84a41 = v_f164b4427 ? &first : &second;
            v_5ee84a41->observed = v_fa20bfbda96c;
            /* public declaration */
            int v_0beed49e = first.observed;
            /* public property declaration */
            int ap_primary = (v_0beed49e != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
