/*
 * Opaque RIFT-M4 synthetic input case_085.
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
            int v_46d2dbe3f229 = read_arg(argc, argv, 1, 7);
            struct NeutralRecord first = {1, 0};
            struct NeutralRecord second = {0, 0};
            /* public declaration */
            struct NeutralRecord *v_b066627c = &second;
            v_b066627c->shadow = v_46d2dbe3f229;
            /* public declaration */
            int v_745e7acd = first.observed;
            /* public property declaration */
            int ap_primary = (v_745e7acd != 0);
            printf("AP_primary=%d\n", ap_primary);
            return 0;
        }
