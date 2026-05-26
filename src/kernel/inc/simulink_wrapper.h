#ifndef SIMULINK_WRAPPER_H
#define SIMULINK_WRAPPER_H

#include <stdint.h>

// --------------------------------------------------------------------------
// Simulink Hardware Abstraction Layer
// Targeted by Simulink Coder output blocks during "Standalone" deployment
// --------------------------------------------------------------------------

void simulink_ext_set_motors(int16_t left, int16_t right);
void simulink_ext_get_tof(uint16_t *left, uint16_t *center, uint16_t *right);
void simulink_ext_get_encoders(int32_t *left, int32_t *right);
float simulink_ext_get_gyro(void);

#endif // SIMULINK_WRAPPER_H