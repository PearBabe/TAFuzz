/*
 * Opaque RIFT-M4 synthetic input case_055.
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
        int v_aa1094ed852f = read_arg(argc, argv, 1, 6);
        /* public declaration */
        struct NeutralQueue v_2a661270 = {0, 0};
        (void)enqueue_value(&v_2a661270, v_aa1094ed852f, 0);
        /* public declaration */
        int v_2b59d347251 = dequeue_value(&v_2a661270);
        (void)v_2b59d347251;
        /* public declaration */
        struct NeutralTimer v_7d222fe8 = {1, 0};
        int state = 0;
        if (fire_timer(&v_7d222fe8)) {
            commit_callback(6, &state);
        }
        /* public declaration */
        int v_d5df3db183123a070 = state;
        /* public property declaration */
        int ap_primary = (v_d5df3db183123a070 >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
