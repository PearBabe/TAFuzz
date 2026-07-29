/*
 * Opaque RIFT-M4 synthetic input case_022.
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
        int v_33cc16f1aa83 = read_arg(argc, argv, 1, 6);
        /* public declaration */
        int v_e96afc286b93d2362 = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_8d02b9b53374831 = read_arg(argc, argv, 3, 1);
        /* public declaration */
        struct NeutralQueue v_483e4272 = {0, 0};
        (void)enqueue_value(&v_483e4272, v_33cc16f1aa83, v_e96afc286b93d2362 != 0);
        /* public declaration */
        int v_bf27c78f954 = dequeue_value(&v_483e4272);
        /* public declaration */
        struct NeutralTimer v_a8580b3f = {v_8d02b9b53374831 != 0, 0};
        int state = 0;
        if (fire_timer(&v_a8580b3f)) {
            commit_callback(v_bf27c78f954, &state);
        }
        /* public declaration */
        int v_61cd7c4cbc822dd95 = state;
        /* public property declaration */
        int ap_primary = (v_61cd7c4cbc822dd95 >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
