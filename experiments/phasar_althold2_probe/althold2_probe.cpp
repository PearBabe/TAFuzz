// Minimal ArduPilot-shaped PhASAR probe.
// One sink is reached by explicit interprocedural data flow; one requires
// control dependence; one is a negative control.

struct Parameters {
  int throttle_deadzone;
};

struct RuntimeState {
  int throttle_control;
  bool throttle_in_deadzone;
};

int mavlink_param_source() {
  // Models a verified PARAM_SET.param_value source.
  return 100;
}

void bind_thr_dz(int wire_value, Parameters *params) {
  // Models the verified external input -> backing-field bridge.
  params->throttle_deadzone = wire_value;
}

bool compute_deadzone(const Parameters *params, int throttle_control) {
  const int mid_stick = 500;
  const int bottom = mid_stick - params->throttle_deadzone;
  const int top = mid_stick + params->throttle_deadzone;
  return throttle_control >= bottom && throttle_control <= top;
}

void data_sink(bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

void control_sink(bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

void clean_sink(bool value) {
  asm volatile("" : : "r"(value) : "memory");
}

int main() {
  const int wire_thr_dz = mavlink_param_source();
  Parameters params{0};
  RuntimeState runtime{500, false};

  bind_thr_dz(wire_thr_dz, &params);
  const bool condition = compute_deadzone(&params, runtime.throttle_control);

  // Expected leak for ordinary interprocedural explicit data flow.
  data_sink(condition);

  // The final stores use constants. Reaching this sink requires adding
  // condition -> controlled-store dependence to the analysis.
  if (condition) {
    runtime.throttle_in_deadzone = true;
  } else {
    runtime.throttle_in_deadzone = false;
  }
  control_sink(runtime.throttle_in_deadzone);

  // Negative control.
  clean_sink(false);
  return 0;
}
