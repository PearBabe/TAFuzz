/*
 * Opaque RIFT-M4 synthetic input case_035.
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
        int v_39767015f926 = read_arg(argc, argv, 1, 2);


        /* public declaration */
        struct NeutralTimeline v_f34623ceaa5 = {5, 1, 2, 0};
        v_f34623ceaa5.repeats = v_39767015f926;
        /* public declaration */
        int v_1244c2e92a37fe = v_f34623ceaa5.repeats;
        /* public property declaration */
        int ap_primary = (v_1244c2e92a37fe >= 2);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
