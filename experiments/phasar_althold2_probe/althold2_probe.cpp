// Minimal ArduPilot-shaped PhASAR probe.
// It intentionally contains one direct data-flow sink and one control-only sink.

struct Parameters {
  int throttle_deadzone;
};

struct RuntimeState {
  int throttle_control;
  bool throttle_in_deadzone;
};

void mavlink_param_source([[clang::annotate("psr.source")]] int *wire_value) {
  // Models PARAM_SET.param_value. The concrete value is irrelevant to taint.
  *wire_value = 100;
}

void bind_thr_dz(const int *wire_value, Parameters *params) {
  // Models the already verified external-input -> backing-field binding.
  params->throttle_deadzone = *wire_value;
}

bool compute_deadzone(const Parameters *params, int throttle_control) {
  const int mid_stick = 500;
  const int bottom = mid_stick - params->throttle_deadzone;
  const int top = mid_stick + params->throttle_deadzone;
  return throttle_control >= bottom && throttle_control <= top;
}

void data_sink([[clang::annotate("psr.sink")]] bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

void control_sink([[clang::annotate("psr.sink")]] bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

void clean_sink([[clang::annotate("psr.sink")]] bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

int main() {
  int wire_thr_dz = 0;
  Parameters params{0};
  RuntimeState runtime{500, false};

  mavlink_param_source(&wire_thr_dz);
  bind_thr_dz(&wire_thr_dz, &params);

  const bool condition = compute_deadzone(&params, runtime.throttle_control);

  // Expected leak for ordinary interprocedural data-flow analysis.
  data_sink(condition);

  // Same semantic influence, but the final assignment uses only constants.
  // A data-only taint analysis normally misses condition -> field assignment.
  if (condition) {
    runtime.throttle_in_deadzone = true;
  } else {
    runtime.throttle_in_deadzone = false;
  }
  control_sink(runtime.throttle_in_deadzone);

  // Negative control: must not be reported as tainted.
  clean_sink(false);
  return 0;
}
