/*
 * Opaque RIFT-M4 synthetic input case_106.
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
        int v_a2ff8571f33a = read_arg(argc, argv, 1, 6);
        /* public declaration */
        struct NeutralQueue v_32c6f0c5 = {0, 0};
        (void)enqueue_value(&v_32c6f0c5, v_a2ff8571f33a, 1);
        /* public declaration */
        int v_93963dc0159 = dequeue_value(&v_32c6f0c5);
        /* public declaration */
        struct NeutralTimer v_fd3b40bd = {1, 0};
        int state = 0;
        if (fire_timer(&v_fd3b40bd)) {
            commit_callback(v_93963dc0159, &state);
        }
        /* public declaration */
        int v_4e6b49eab5981a11a = state;
        /* public property declaration */
        int ap_primary = (v_4e6b49eab5981a11a >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
