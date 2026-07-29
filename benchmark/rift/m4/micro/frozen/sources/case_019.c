/*
 * Opaque RIFT-M4 synthetic input case_019.
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
        int v_b01df1b3f483 = read_arg(argc, argv, 1, 6);
        /* public declaration */
        int v_57334fba7f367c2ed = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_64ebb285b1f520a = read_arg(argc, argv, 3, 1);
        /* public declaration */
        struct NeutralQueue v_e2caea2c = {0, 0};
        (void)enqueue_value(&v_e2caea2c, v_b01df1b3f483, v_57334fba7f367c2ed != 0);
        /* public declaration */
        int v_6316e2248d2 = dequeue_value(&v_e2caea2c);
        /* public declaration */
        struct NeutralTimer v_ac94da92 = {v_64ebb285b1f520a != 0, 0};
        int state = 0;
        if (fire_timer(&v_ac94da92)) {
            commit_callback(v_6316e2248d2, &state);
        }
        /* public declaration */
        int v_3fb224997bd1a798f = state;
        /* public property declaration */
        int ap_primary = (v_3fb224997bd1a798f >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
