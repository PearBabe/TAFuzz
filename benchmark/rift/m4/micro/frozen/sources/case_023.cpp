/*
 * Opaque RIFT-M4 synthetic input case_023.
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
        int v_4b828361497a = read_arg(argc, argv, 1, 0);

        (void)v_4b828361497a;
        /* public declaration */
        struct NeutralTimeline v_233b965f06f = {5, 1, 2, 0};
        v_233b965f06f.order = 0;
        /* public declaration */
        int v_0497eb537e78d8 = v_233b965f06f.order;
        /* public property declaration */
        int ap_primary = (v_0497eb537e78d8 == 0);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
