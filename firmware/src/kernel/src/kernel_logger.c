#include "micromouse_kernel.h"
#include "ZD25WQ80C.h"
#include "stm32l4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h>

#define LOGGER_PARTITION_START  0x00000U
#define LOGGER_PARTITION_MAX    0xDFFFFU  // 896 KB limit (FAT filesystem starts at 0xE0000U)
#define LOG_PAGE_SIZE           256U
#define LOG_SECTOR_SIZE         4096U

extern UART_HandleTypeDef huart1;
extern ZD25WQ80C_t flash;

static uint8_t log_page_buf[LOG_PAGE_SIZE];
static uint16_t log_page_idx = 0;
static uint32_t log_write_addr = LOGGER_PARTITION_START;
static bool logging_active = false;
static bool header_written = false;

// Track last-written shadow state for sparse log comparisons
static int16_t last_left_pwm = 0;
static int16_t last_right_pwm = 0;
static uint16_t last_tof_l = 0;
static uint16_t last_tof_al = 0;
static uint16_t last_tof_c = 0;
static uint16_t last_tof_ar = 0;
static uint16_t last_tof_r = 0;
static int32_t last_lenc = 0;
static int32_t last_renc = 0;
static float last_gyro = 0.0f;
static float last_v_batt = 0.0f;

// Unique Device ID (UID) starting address on STM32L4
#define STM32L4_UID_ADDR 0x1FFF7590U

static uint32_t compute_code_hash(void) {
    uint32_t hash = 2166136261U;
    
    // 1. Hash PikaScript bytecode region (Page 240 / 0x08078000, 8KB)
    const uint8_t *pika_ptr = (const uint8_t*)0x08078000;
    for (int i = 0; i < 8192; i++) {
        hash ^= pika_ptr[i];
        hash *= 16777619U;
    }
    
    // 2. Hash first block of FAT filesystem region to capture directory differences
    uint8_t sector_buf[512];
    // Read direct from physical offset 0xE0000U
    if (initZD25WQ80C()) {
        if (ZD25WQ80C_Read(0xE0000U, sector_buf, 512) == HAL_OK) {
            for (int i = 0; i < 512; i++) {
                hash ^= sector_buf[i];
                hash *= 16777619U;
            }
        }
    }
    
    return hash;
}

static void raw_logger_uart_print(const char *msg) {
    HAL_UART_Transmit(&huart1, (uint8_t *)msg, (uint16_t)strlen(msg), 1000);
}

// Ensures current sector is erased before writing
static void ensure_sector_erased(uint32_t addr) {
    if (addr % LOG_SECTOR_SIZE == 0) {
        ZD25WQ80C_SectorErase(addr);
    }
}

// Flush page buffer to external flash
static void flush_log_page(void) {
    if (log_page_idx > 0) {
        if (log_write_addr + LOG_PAGE_SIZE <= LOGGER_PARTITION_MAX) {
            ensure_sector_erased(log_write_addr);
            // Pad with space characters to fill the 256-byte page boundary
            while (log_page_idx < LOG_PAGE_SIZE) {
                log_page_buf[log_page_idx++] = ' ';
            }
            ZD25WQ80C_PageProgram(log_write_addr, log_page_buf, LOG_PAGE_SIZE);
            log_write_addr += LOG_PAGE_SIZE;
        }
        log_page_idx = 0;
    }
}

// Append formatted JSON string directly to page buffer
static void append_to_log(const char *str) {
    size_t len = strlen(str);
    for (size_t i = 0; i < len; i++) {
        log_page_buf[log_page_idx++] = str[i];
        if (log_page_idx >= LOG_PAGE_SIZE) {
            flush_log_page();
        }
    }
}

void kernel_logger_init(void) {
    if (!flash.initialized) {
        initZD25WQ80C();
    }
    log_write_addr = LOGGER_PARTITION_START;
    log_page_idx = 0;
    header_written = false;
    logging_active = false;
}

void kernel_logger_tick(void) {
    // 1. Check for automatic logging trigger: starts when motors first actuate
    const KernelState_t* s = kernel_get_state();
    if (!logging_active) {
        if (s->left_pwm != 0 || s->right_pwm != 0) {
            logging_active = true;
            kernel_logger_init(); // Reset logging pointers to start fresh
        } else {
            return; // Stay idle
        }
    }

    // Check flash space limit
    if (log_write_addr >= LOGGER_PARTITION_MAX) {
        return;
    }

    // 2. Write verification headers on first tick
    if (!header_written) {
        uint32_t *uid = (uint32_t*)STM32L4_UID_ADDR;
        uint32_t code_hash = compute_code_hash();
        char header_buf[128];
        snprintf(header_buf, sizeof(header_buf), 
                 "{\"log_header\":1,\"uid\":\"%08X%08X%08X\",\"hash\":%lu}\n", 
                 (unsigned int)uid[0], (unsigned int)uid[1], (unsigned int)uid[2], 
                 (unsigned long)code_hash);
        append_to_log(header_buf);
        header_written = true;

        // Initialize shadow states
        last_left_pwm = s->left_pwm; last_right_pwm = s->right_pwm;
        last_tof_l = s->tof_l; last_tof_al = s->tof_al; last_tof_c = s->tof_c;
        last_tof_ar = s->tof_ar; last_tof_r = s->tof_r;
        last_lenc = s->lenc; last_renc = s->renc;
        last_gyro = s->gyro; last_v_batt = s->v_batt;
    }

    // 3. Perform sparse compression check. Build JSON listing only changed values.
    char record_buf[256];
    int written = snprintf(record_buf, sizeof(record_buf), "{");
    bool first = true;

    // Check and log variables
    if (s->left_pwm != last_left_pwm) {
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"l\":%d", s->left_pwm);
        last_left_pwm = s->left_pwm; first = false;
    }
    if (s->right_pwm != last_right_pwm) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"r\":%d", s->right_pwm);
        last_right_pwm = s->right_pwm; first = false;
    }
    if (s->tof_l != last_tof_l) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"tl\":%u", s->tof_l);
        last_tof_l = s->tof_l; first = false;
    }
    if (s->tof_al != last_tof_al) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"tal\":%u", s->tof_al);
        last_tof_al = s->tof_al; first = false;
    }
    if (s->tof_c != last_tof_c) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"tc\":%u", s->tof_c);
        last_tof_c = s->tof_c; first = false;
    }
    if (s->tof_ar != last_tof_ar) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"tar\":%u", s->tof_ar);
        last_tof_ar = s->tof_ar; first = false;
    }
    if (s->tof_r != last_tof_r) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"tr\":%u", s->tof_r);
        last_tof_r = s->tof_r; first = false;
    }
    if (s->lenc != last_lenc) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"le\":%ld", (long)s->lenc);
        last_lenc = s->lenc; first = false;
    }
    if (s->renc != last_renc) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"re\":%ld", (long)s->renc);
        last_renc = s->renc; first = false;
    }
    if (abs((int)(s->gyro * 100.0f) - (int)(last_gyro * 100.0f)) > 1) { // threshold filter
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"g\":%.2f", (double)s->gyro);
        last_gyro = s->gyro; first = false;
    }
    if (abs((int)(s->v_batt * 100.0f) - (int)(last_v_batt * 100.0f)) > 1) {
        if (!first) { written += snprintf(record_buf + written, sizeof(record_buf) - written, ","); }
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "\"v\":%.2f", (double)s->v_batt);
        last_v_batt = s->v_batt; first = false;
    }

    // Only log if something has changed (avoiding empty ticks)
    if (!first) {
        written += snprintf(record_buf + written, sizeof(record_buf) - written, "}\n");
        append_to_log(record_buf);
    }
}

void kernel_logger_dump(void) {
    __disable_irq();
    
    // Stop motors for safety during dump
    kernel_set_pwm(0, 0);
    
    raw_logger_uart_print("\r\n--- START LOG DUMP ---\r\n");
    
    // Flush any pending buffered log page before reading
    flush_log_page();
    
    static uint8_t dump_buf[LOG_PAGE_SIZE];
    uint32_t current_addr = LOGGER_PARTITION_START;
    
    while (current_addr < log_write_addr && current_addr < LOGGER_PARTITION_MAX) {
        if (ZD25WQ80C_Read(current_addr, dump_buf, LOG_PAGE_SIZE) == HAL_OK) {
            // Stream raw data over UART to host console
            HAL_UART_Transmit(&huart1, dump_buf, LOG_PAGE_SIZE, 1000);
        }
        current_addr += LOG_PAGE_SIZE;
    }
    
    raw_logger_uart_print("\r\n--- END LOG DUMP ---\r\n");
    
    __enable_irq();
}
