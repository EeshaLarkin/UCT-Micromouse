#include "simulink_wrapper.h"

// --------------------------------------------------------------------------
// Simulink Hardware Abstraction Layer
// Targeted by Simulink Coder output blocks during "Standalone" deployment
// --------------------------------------------------------------------------

#ifdef __arm__
// --- PHYSICAL HARDWARE MODE (Compiling for STM32) ---
#include "micromouse_kernel.h"

extern float IMU_Gyro[3];
extern float IMU_Accel[3];
extern float IMU_Temp;

void simulink_ext_set_motors(int16_t left, int16_t right) {
    kernel_set_pwm(left, right);
}

void simulink_ext_set_leds(uint8_t led0, uint8_t led1, uint8_t led2) {
    // TODO: Map to actual hardware GPIO pins in main.h
    // e.g., HAL_GPIO_WritePin(LED0_GPIO_Port, LED0_Pin, led0 ? GPIO_PIN_SET : GPIO_PIN_RESET);
    //       HAL_GPIO_WritePin(LED1_GPIO_Port, LED1_Pin, led1 ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

// To actually display these, you will eventually want to store them in a global char array
// and update kernel_update_display() in micromouse_kernel.c to print them!
void simulink_ext_set_oled_header(const char *text) { kernel_set_oled_header(text); }
void simulink_ext_set_oled_line1(const char *text) { kernel_set_oled_line1(text); }
void simulink_ext_set_oled_line2(const char *text) { kernel_set_oled_line2(text); }
void simulink_ext_set_oled_line3(const char *text) { kernel_set_oled_line3(text); }
void simulink_ext_set_oled_line4(const char *text) { kernel_set_oled_line4(text); }

// Generic key-value telemetry for application logic.
// These can be configured to forward data to the JSON telemetry stream,
// print directly over UART for debugging, or safely absorb the data.
void simulink_ext_log_str(const char *key, const char *value) {
    (void)key;
    (void)value;
}
void simulink_ext_log_num(const char *key, double value) {
    (void)key;
    (void)value;
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
void simulink_ext_get_gyro_xyz(float *x, float *y, float *z) {
    *x = IMU_Gyro[0];
    *y = IMU_Gyro[1];
    *z = IMU_Gyro[2];
}
void simulink_ext_get_accel_xyz(float *x, float *y, float *z) {
    *x = IMU_Accel[0];
    *y = IMU_Accel[1];
    *z = IMU_Accel[2];
}
float simulink_ext_get_imu_temp(void) {
    return IMU_Temp;
}
void simulink_ext_get_switches(uint8_t *sw1, uint8_t *sw2) {
    const KernelState_t* state = kernel_get_state();
    *sw1 = state->btn1;
    *sw2 = state->btn2;
}
float simulink_ext_get_vbatt(void) {
    return kernel_get_state()->v_batt;
}

void simulink_ext_get_line_sensors(uint16_t *fl, uint16_t *fr, uint16_t *sl, uint16_t *sr) {
    const KernelState_t* state = kernel_get_state();
    *fl = state->ir_fl;
    *fr = state->ir_fr;
    *sl = state->ir_sl;
    *sr = state->ir_sr;
}

void simulink_ext_get_pwr_meter(float *voltage, float *current, float *power, float *v_shunt, float *capacity) {
    *voltage = kernel_get_state()->v_batt;
    *current  = 0.0f; // Placeholder: Can be mapped to INA219 Current later
    *power    = 0.0f; // Placeholder: Can be mapped to INA219 Power later
    *v_shunt  = 0.0f; // Placeholder: Can be mapped to INA219 Shunt Voltage
    *capacity = 0.0f; // Placeholder: Estimated mAh or SoC
}

#else
// --- MATLAB MAC SIMULATION MODE (Native USB Tether) ---
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <glob.h>
#include <errno.h>

static int sim_fd = -1;
static char rx_buf[2048];
static int rx_idx = 0;

static uint16_t sim_tof_l = 0, sim_tof_c = 0, sim_tof_r = 0;
static int32_t sim_lenc = 0, sim_renc = 0;
static float sim_vbatt = 0.0f;

static void sim_init_serial() {
    if (sim_fd != -1) return;
    
    // Auto-detect STM32 ST-Link on Mac
    glob_t glob_result;
    glob("/dev/cu.usbmodem*", 0, NULL, &glob_result);
    if(glob_result.gl_pathc > 0) {
        sim_fd = open(glob_result.gl_pathv[0], O_RDWR | O_NOCTTY | O_NDELAY);
        if (sim_fd != -1) {
            struct termios options;
            tcgetattr(sim_fd, &options);
            cfsetispeed(&options, B115200);
            cfsetospeed(&options, B115200);
            options.c_cflag |= (CLOCAL | CREAD);
            tcsetattr(sim_fd, TCSANOW, &options);
            
            // Force kernel to send full absolute baseline frames
            write(sim_fd, "{\"c\":{\"sync\":1}}\r\n", 18);
        }
    }
    globfree(&glob_result);
}

static void sim_poll_serial() {
    if (sim_fd == -1) sim_init_serial();
    if (sim_fd == -1) return;

    char temp[256];
    int n = read(sim_fd, temp, sizeof(temp));
    if (n > 0) {
        for (int i = 0; i < n; i++) {
            if (temp[i] == '\n' || temp[i] == '\r') {
                rx_buf[rx_idx] = '\0';
                if (rx_idx > 0) {
                    char *p; int val;
                    if ((p = strstr(rx_buf, "\"tof_l\":"))) { sscanf(p, "\"tof_l\":%d", &val); sim_tof_l = (uint16_t)val; }
                    if ((p = strstr(rx_buf, "\"tof_c\":"))) { sscanf(p, "\"tof_c\":%d", &val); sim_tof_c = (uint16_t)val; }
                    if ((p = strstr(rx_buf, "\"tof_r\":"))) { sscanf(p, "\"tof_r\":%d", &val); sim_tof_r = (uint16_t)val; }
                    if ((p = strstr(rx_buf, "\"lenc\":")))  { sscanf(p, "\"lenc\":%d", &val); sim_lenc = (int32_t)val; }
                    if ((p = strstr(rx_buf, "\"renc\":")))  { sscanf(p, "\"renc\":%d", &val); sim_renc = (int32_t)val; }
                    rx_idx = 0;
                }
            } else if (rx_idx < sizeof(rx_buf) - 1) {
                rx_buf[rx_idx++] = temp[i];
            }
        }
    } else if (n < 0 && errno != EAGAIN) {
        // USB unplugged or serial error, close and reset
        close(sim_fd);
        sim_fd = -1;
    }
}

void simulink_ext_set_motors(int16_t left, int16_t right) {
    if (sim_fd == -1) sim_init_serial();
    if (sim_fd != -1) {
        char tx[64];
        int len = snprintf(tx, sizeof(tx), "{\"a\":[%d,%d]}\r\n", left, right);
        write(sim_fd, tx, len);
        sim_poll_serial(); // Process incoming telemetry
    }
}

void simulink_ext_get_tof(uint16_t *left, uint16_t *center, uint16_t *right) { 
    sim_poll_serial();
    *left = sim_tof_l; *center = sim_tof_c; *right = sim_tof_r; 
}
void simulink_ext_get_encoders(int32_t *left, int32_t *right) { *left = sim_lenc; *right = sim_renc; }
float simulink_ext_get_gyro(void) { return 0.0f; }
void simulink_ext_get_gyro_xyz(float *x, float *y, float *z) { *x=0; *y=0; *z=0; }
void simulink_ext_get_accel_xyz(float *x, float *y, float *z) { *x=0; *y=0; *z=0; }
float simulink_ext_get_imu_temp(void) { return 0.0f; }
void simulink_ext_get_switches(uint8_t *sw1, uint8_t *sw2) { *sw1=0; *sw2=0; }
float simulink_ext_get_vbatt(void) { return sim_vbatt; }
void simulink_ext_get_line_sensors(uint16_t *fl, uint16_t *fr, uint16_t *sl, uint16_t *sr) { *fl=0; *fr=0; *sl=0; *sr=0; }
void simulink_ext_get_pwr_meter(float *voltage, float *current, float *power, float *v_shunt, float *capacity) { *voltage=sim_vbatt; *current=0.0f; *power=0.0f; *v_shunt=0.0f; *capacity=0.0f; }
void simulink_ext_set_leds(uint8_t led0, uint8_t led1, uint8_t led2) {}
void simulink_ext_set_oled_header(const char *text) {(void)text;}
void simulink_ext_set_oled_line1(const char *text) {(void)text;}
void simulink_ext_set_oled_line2(const char *text) {(void)text;}
void simulink_ext_set_oled_line3(const char *text) {(void)text;}
void simulink_ext_set_oled_line4(const char *text) {(void)text;}
void simulink_ext_log_str(const char *key, const char *value) {}
void simulink_ext_log_num(const char *key, double value) {}
#endif