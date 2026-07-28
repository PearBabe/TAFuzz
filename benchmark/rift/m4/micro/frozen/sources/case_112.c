/*
 * Opaque RIFT-M4 synthetic input case_112.
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
        int v_b14f191ba9fe = read_arg(argc, argv, 1, 5);

        (void)v_b14f191ba9fe;
        /* public declaration */
        struct NeutralTimeline v_d7e3990053f = {5, 1, 2, 0};
        v_d7e3990053f.delay = 5;
        /* public declaration */
        int v_e5864ba5db7dc1 = v_d7e3990053f.delay;
        /* public property declaration */
        int ap_primary = (v_e5864ba5db7dc1 <= 5);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
