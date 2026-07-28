/*
 * Opaque RIFT-M4 synthetic input case_053.
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
struct NeutralTimeline { int delay; int delivered; int repeats; int order; };

    int main(int argc, char **argv) {
        /* public declaration */
        int v_857becb48ed6 = read_arg(argc, argv, 1, 1);


        /* public declaration */
        struct NeutralTimeline v_ac37a6d9895 = {5, 1, 2, 0};
        v_ac37a6d9895.delivered = v_857becb48ed6;
        /* public declaration */
        int v_b5b2f1b545c930 = v_ac37a6d9895.delivered;
        /* public property declaration */
        int ap_primary = (v_b5b2f1b545c930 != 0);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
