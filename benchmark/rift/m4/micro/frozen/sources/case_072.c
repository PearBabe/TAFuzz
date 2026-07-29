/*
 * Opaque RIFT-M4 synthetic input case_072.
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
struct NeutralQueue { int payload; int count; };
static int enqueue_value(struct NeutralQueue *queue, int value, int accept) {
    if (!accept) { return 0; }
    queue->payload = value;
    queue->count = 1;
    return 1;
}
static int dequeue_value(struct NeutralQueue *queue) {
    if (queue->count == 0) { return 0; }
    queue->count = 0;
    return queue->payload;
}
struct NeutralTimer { int armed; int due; };
static int fire_timer(const struct NeutralTimer *timer) {
    return timer->armed && timer->due <= 0;
}
static void commit_callback(int payload, int *state) { *state = payload; }

    int main(int argc, char **argv) {
        /* public declaration */
        int v_3096371c526f = read_arg(argc, argv, 1, 6);
        /* public declaration */
        struct NeutralQueue v_0c2169c0 = {0, 0};
        (void)enqueue_value(&v_0c2169c0, v_3096371c526f, 1);
        /* public declaration */
        int v_2881479ebbc = dequeue_value(&v_0c2169c0);
        /* public declaration */
        struct NeutralTimer v_f2a493b3 = {1, 0};
        int state = 0;
        if (fire_timer(&v_f2a493b3)) {
            commit_callback(v_2881479ebbc, &state);
        }
        /* public declaration */
        int v_7808d4211deec57ab = state;
        /* public property declaration */
        int ap_primary = (v_7808d4211deec57ab >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
