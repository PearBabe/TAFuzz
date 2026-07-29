/*
 * Opaque RIFT-M4 synthetic input case_052.
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
        int v_63926fe0ea77 = read_arg(argc, argv, 1, 5);


        /* public declaration */
        struct NeutralTimeline v_2a92e3b0655 = {5, 1, 2, 0};
        v_2a92e3b0655.delay = v_63926fe0ea77;
        /* public declaration */
        int v_23a63c7369618e = v_2a92e3b0655.delay;
        /* public property declaration */
        int ap_primary = (v_23a63c7369618e <= 5);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
