#ifndef MICROMOUSE_KERNEL_H
#define MICROMOUSE_KERNEL_H

#include <stdint.h>
#include <stdbool.h>

// ---------------------------------------------------------
// Hardware Proxy Kernel API
// ---------------------------------------------------------

typedef struct {
    int16_t left_pwm;
    int16_t right_pwm;
    uint16_t tof_l;
    uint16_t tof_al;
    uint16_t tof_c;
    uint16_t tof_ar;
    uint16_t tof_r;
    uint16_t ir_fl;
    uint16_t ir_fr;
    uint16_t ir_sl;
    uint16_t ir_sr;
    int32_t lenc;
    int32_t renc;
    float gyro;
    float v_batt;
    uint8_t btn1;
    uint8_t btn2;
} KernelState_t;

void kernel_init(void);

void kernel_parse_downlink(const char* rx_string);
int kernel_generate_uplink(char* tx_buffer, int max_len);
void kernel_snapshot_state(void);

/* Direct C-Callable API for Tier 2 (Control Libs) & Tier 3 (Simulink Standalone) */
void kernel_set_pwm(int16_t left_pwm, int16_t right_pwm);
const KernelState_t* kernel_get_state(void);
void kernel_set_polarity(int16_t left, int16_t right);

void kernel_watchdog_tick(void);
uint32_t kernel_get_stream_rate_hz(void);
void kernel_update_display(void);

// --- Simulink Display Overrides ---
void kernel_set_title(const char* title);
void kernel_set_oled_header(const char* text);
void kernel_set_oled_line1(const char* text);
void kernel_set_oled_line2(const char* text);
void kernel_set_oled_line3(const char* text);
void kernel_set_oled_line4(const char* text);

#endif // MICROMOUSE_KERNEL_H