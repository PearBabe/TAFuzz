/*
 * Opaque RIFT-M4 synthetic input case_075.
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
        int v_5017567e3596 = read_arg(argc, argv, 1, 1);

        (void)v_5017567e3596;
        /* public declaration */
        struct NeutralTimeline v_5261b8966ed = {5, 1, 2, 0};
        v_5261b8966ed.delivered = 1;
        /* public declaration */
        int v_9d36e3e53b825e = v_5261b8966ed.delivered;
        /* public property declaration */
        int ap_primary = (v_9d36e3e53b825e != 0);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
