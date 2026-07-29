/*
 * Opaque RIFT-M4 synthetic input case_027.
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
        int v_393e50985f9c = read_arg(argc, argv, 1, 6);
        /* public declaration */
        struct NeutralQueue v_f8c7a1ac = {0, 0};
        (void)enqueue_value(&v_f8c7a1ac, v_393e50985f9c, 1);
        /* public declaration */
        int v_8f53f5552fe = dequeue_value(&v_f8c7a1ac);
        /* public declaration */
        struct NeutralTimer v_1d7e5ac3 = {1, 0};
        int state = 0;
        if (fire_timer(&v_1d7e5ac3)) {
            commit_callback(v_8f53f5552fe, &state);
        }
        /* public declaration */
        int v_786e88638a066b8e1 = state;
        /* public property declaration */
        int ap_primary = (v_786e88638a066b8e1 >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
