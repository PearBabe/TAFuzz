/*
 * Opaque RIFT-M4 synthetic input case_074.
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
        int v_d695662701e1 = read_arg(argc, argv, 1, 2);

            /* public declaration */
            int v_e0b4e98ba250d23706 = read_arg(argc, argv, 2, 1);


        /* public declaration */
        struct NeutralTimeline v_77f0310235a = {5, 1, 2, 0};
        v_77f0310235a.repeats = v_e0b4e98ba250d23706 ? v_d695662701e1 : 2;
        /* public declaration */
        int v_f18a953b1a98f8 = v_77f0310235a.repeats;
        /* public property declaration */
        int ap_primary = (v_f18a953b1a98f8 >= 2);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
