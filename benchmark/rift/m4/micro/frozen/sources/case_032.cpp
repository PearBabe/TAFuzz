/*
 * Opaque RIFT-M4 synthetic input case_032.
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
        int v_d164c59d01a7 = read_arg(argc, argv, 1, 1);

            /* public declaration */
            int v_4ead38ad0a44959662 = read_arg(argc, argv, 2, 1);


        /* public declaration */
        struct NeutralTimeline v_2efa78577a9 = {5, 1, 2, 0};
        v_2efa78577a9.delivered = v_4ead38ad0a44959662 ? v_d164c59d01a7 : 1;
        /* public declaration */
        int v_c7bbef339ce20f = v_2efa78577a9.delivered;
        /* public property declaration */
        int ap_primary = (v_c7bbef339ce20f != 0);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
