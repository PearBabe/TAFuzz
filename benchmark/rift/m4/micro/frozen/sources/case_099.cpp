/*
 * Opaque RIFT-M4 synthetic input case_099.
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
        int v_a1daf846d1ed = read_arg(argc, argv, 1, 6);
        /* public declaration */
        int v_adb43f4c1d46e5dbf = read_arg(argc, argv, 2, 1);
        /* public declaration */
        int v_0fffc68682a9ea2 = read_arg(argc, argv, 3, 1);
        /* public declaration */
        struct NeutralQueue v_23ba3471 = {0, 0};
        (void)enqueue_value(&v_23ba3471, v_a1daf846d1ed, v_adb43f4c1d46e5dbf != 0);
        /* public declaration */
        int v_2018b94689e = dequeue_value(&v_23ba3471);
        /* public declaration */
        struct NeutralTimer v_3394fb27 = {v_0fffc68682a9ea2 != 0, 0};
        int state = 0;
        if (fire_timer(&v_3394fb27)) {
            commit_callback(v_2018b94689e, &state);
        }
        /* public declaration */
        int v_78c3a952b292748e7 = state;
        /* public property declaration */
        int ap_primary = (v_78c3a952b292748e7 >= 6);
        printf("AP_primary=%d\n", ap_primary);
        return 0;
    }
