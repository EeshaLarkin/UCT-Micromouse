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

void simulink_ext_cleanup(void) {
    // No-op on physical hardware
}

#else
// --- STANDALONE PC TCP CLIENT MODE (macOS, Linux, and Windows) ---
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#define close closesocket
#define socket_errno WSAGetLastError()
#else
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#define socket_errno errno
#endif

// We expose sim_fd globally so the main loop can monitor connection status
int sim_fd = -1;

static uint16_t sim_tof_l = 0, sim_tof_c = 0, sim_tof_r = 0;
static int32_t sim_lenc = 0, sim_renc = 0;
static float sim_gyro = 0.0f;
static float sim_vbatt = 6.0f;

static void sim_init_socket(void) {
    if (sim_fd != -1) return;

#ifdef _WIN32
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0) {
        printf("[PC Client] Winsock initialization failed.\n");
        return;
    }
#endif

    struct sockaddr_in serv_addr;
    sim_fd = (int)socket(AF_INET, SOCK_STREAM, 0);
    if (sim_fd < 0) {
        printf("[PC Client] Socket creation error.\n");
        return;
    }

    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(8000);

#ifdef _WIN32
    serv_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (serv_addr.sin_addr.s_addr == INADDR_NONE) {
        printf("[PC Client] Invalid loopback address.\n");
        close(sim_fd);
        sim_fd = -1;
        return;
    }
#else
    if (inet_pton(AF_INET, "127.0.0.1", &serv_addr.sin_addr) <= 0) {
        printf("[PC Client] Invalid loopback address.\n");
        close(sim_fd);
        sim_fd = -1;
        return;
    }
#endif

    if (connect(sim_fd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        printf("[PC Client] Connection failed. Ensure the Python simulator is running on port 8000.\n");
        close(sim_fd);
        sim_fd = -1;
        return;
    }

    // Set non-blocking mode
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(sim_fd, FIONBIO, &mode);
#else
    int flags = fcntl(sim_fd, F_GETFL, 0);
    fcntl(sim_fd, F_SETFL, flags | O_NONBLOCK);
#endif

    printf("[PC Client] Connected to simulator server on localhost:8000 successfully!\n");
}

static void sim_poll_socket(void) {
    if (sim_fd == -1) sim_init_socket();
    if (sim_fd == -1) return;

    char temp[512];
    int total_bytes = 0;
    
    // Lock-step read loop: poll socket character by character until we hit newline
    while (total_bytes < sizeof(temp) - 1) {
        int n = recv(sim_fd, temp + total_bytes, 1, 0);
        if (n > 0) {
            if (temp[total_bytes] == '\n' || temp[total_bytes] == '\r') {
                temp[total_bytes] = '\0';
                if (total_bytes > 0) {
                    char *p; int val; double dval;
                    if ((p = strstr(temp, "\"tof_l\":")))  { sscanf(p, "\"tof_l\":%d", &val); sim_tof_l = (uint16_t)val; }
                    if ((p = strstr(temp, "\"tof_c\":")))  { sscanf(p, "\"tof_c\":%d", &val); sim_tof_c = (uint16_t)val; }
                    if ((p = strstr(temp, "\"tof_r\":")))  { sscanf(p, "\"tof_r\":%d", &val); sim_tof_r = (uint16_t)val; }
                    if ((p = strstr(temp, "\"+lenc\":"))) { sscanf(p, "\"+lenc\":%d", &val); sim_lenc = (int32_t)val; }
                    if ((p = strstr(temp, "\"+renc\":"))) { sscanf(p, "\"+renc\":%d", &val); sim_renc = (int32_t)val; }
                    if ((p = strstr(temp, "\"gyro\":")))   { sscanf(p, "\"gyro\":%lf", &dval); sim_gyro = (float)dval; }
                    if ((p = strstr(temp, "\"v_batt\":"))) { sscanf(p, "\"v_batt\":%lf", &dval); sim_vbatt = (float)dval; }
                }
                break;
            }
            total_bytes++;
        } else if (n < 0) {
#ifdef _WIN32
            int err = WSAGetLastError();
            if (err == WSAEWOULDBLOCK) {
                Sleep(1);
                continue;
            }
#else
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(1000);
                continue;
            }
#endif
            printf("[PC Client] Connection lost or read error.\n");
            close(sim_fd);
            sim_fd = -1;
            break;
        } else {
            // Server closed connection
            printf("[PC Client] Simulator server closed connection.\n");
            close(sim_fd);
            sim_fd = -1;
            break;
        }
    }
}

void simulink_ext_set_motors(int16_t left, int16_t right) {
    if (sim_fd == -1) sim_init_socket();
    if (sim_fd != -1) {
        char tx[64];
        int len = snprintf(tx, sizeof(tx), "{\"a\":[%d,%d]}\r\n", left, right);
        send(sim_fd, tx, len, 0);
        sim_poll_socket(); // Block and wait for telemetry update (lock-step)
    }
}

void simulink_ext_get_tof(uint16_t *left, uint16_t *center, uint16_t *right) { 
    *left = sim_tof_l; *center = sim_tof_c; *right = sim_tof_r; 
}

void simulink_ext_get_encoders(int32_t *left, int32_t *right) { 
    *left = sim_lenc; *right = sim_renc; 
}

float simulink_ext_get_gyro(void) { 
    return sim_gyro; 
}

void simulink_ext_get_gyro_xyz(float *x, float *y, float *z) { 
    *x = 0.0f; *y = 0.0f; *z = sim_gyro; 
}

void simulink_ext_get_accel_xyz(float *x, float *y, float *z) { 
    *x = 0.0f; *y = 0.0f; *z = 0.0f; 
}

float simulink_ext_get_imu_temp(void) { return 25.0f; }
void simulink_ext_get_switches(uint8_t *sw1, uint8_t *sw2) { *sw1 = 0; *sw2 = 0; }
float simulink_ext_get_vbatt(void) { return sim_vbatt; }
void simulink_ext_get_line_sensors(uint16_t *fl, uint16_t *fr, uint16_t *sl, uint16_t *sr) { *fl = 0; *fr = 0; *sl = 0; *sr = 0; }
void simulink_ext_get_pwr_meter(float *voltage, float *current, float *power, float *v_shunt, float *capacity) { 
    *voltage = sim_vbatt; *current = 0.0f; *power = 0.0f; *v_shunt = 0.0f; *capacity = 0.0f; 
}

void simulink_ext_set_leds(uint8_t led0, uint8_t led1, uint8_t led2) { (void)led0; (void)led1; (void)led2; }
void simulink_ext_set_oled_header(const char *text) { (void)text; }
void simulink_ext_set_oled_line1(const char *text) { (void)text; }
void simulink_ext_set_oled_line2(const char *text) { (void)text; }
void simulink_ext_set_oled_line3(const char *text) { (void)text; }
void simulink_ext_set_oled_line4(const char *text) { (void)text; }
void simulink_ext_log_str(const char *key, const char *value) { (void)key; (void)value; }
void simulink_ext_log_num(const char *key, double value) { (void)key; (void)value; }

void simulink_ext_cleanup(void) {
    if (sim_fd != -1) {
        close(sim_fd);
        sim_fd = -1;
    }
#ifdef _WIN32
    WSACleanup();
#endif
}
#endif