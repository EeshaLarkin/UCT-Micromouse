#include "simulink_wrapper.h"
#include "micromouse_kernel.h"

// --------------------------------------------------------------------------
// Simulink Hardware Abstraction Layer
// Targeted by Simulink Coder output blocks during "Standalone" deployment
// --------------------------------------------------------------------------

void simulink_ext_set_motors(int16_t left, int16_t right) {
    // Simulink pushes motor output directly into the C Kernel
    kernel_set_pwm(left, right);
}

void simulink_ext_get_tof(uint16_t *left, uint16_t *center, uint16_t *right) {
    const KernelState_t* state = kernel_get_state();
    *left   = state->tof_l;
    *center = state->tof_c;
    *right  = state->tof_r;
}

void simulink_ext_get_encoders(int32_t *left, int32_t *right) {
    const KernelState_t* state = kernel_get_state();
    *left  = state->lenc;
    *right = state->renc;
}

float simulink_ext_get_gyro(void) {
    return kernel_get_state()->gyro;
}