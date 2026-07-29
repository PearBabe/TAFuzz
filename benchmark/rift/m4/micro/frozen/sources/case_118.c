/*
 * Opaque RIFT-M4 synthetic input case_118.
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
        int v_29ea640afc95 = read_arg(argc, argv, 1, 5);

            /* public declaration */
            int v_44fee961a2ee7dcd42 = read_arg(argc, argv, 2, 1);


        /* public declaration */
        struct NeutralTimeline v_d8a2ffaa613 = {5, 1, 2, 0};
        v_d8a2ffaa613.delay = v_44fee961a2ee7dcd42 ? v_29ea640afc95 : 5;
        /* public declaration */
        int v_9b0cffc1200dd5 = v_d8a2ffaa613.delay;
        /* public property declaration */
        int ap_primary = (v_9b0cffc1200dd5 <= 5);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
