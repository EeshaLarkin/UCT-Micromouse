#include "serial_interface.h"
#include "micromouse_kernel.h"
#include <string.h>
#include <stdio.h>

static UART_HandleTypeDef *kernel_huart;
static uint8_t rx_byte;
static char rx_buffer[256];
static uint16_t rx_index = 0;
static uint32_t last_tx_time = 0;

void serial_interface_init(UART_HandleTypeDef *huart) {
    kernel_huart = huart;
    
    // Force disable DMA2 Channel 7 to prevent the hardware DMA controller
    // from hijacking incoming USART1 RX bytes into the legacy circular buffer.
    #ifdef DMA2
    DMA2_Channel7->CCR &= ~DMA_CCR_EN;
    #endif
    
    kernel_init();
    
    // Start listening for the first byte via interrupt
    HAL_UART_Receive_IT(kernel_huart, &rx_byte, 1);
}

void serial_interface_tick(void) {
    // Run logger tick at 25Hz (every 40ms)
    static uint32_t last_log_time = 0;
    uint32_t now = HAL_GetTick();
    if (now - last_log_time >= 40) {
        last_log_time = now;
        extern void kernel_logger_tick(void);
        kernel_logger_tick();
    }

    uint32_t rate_hz = kernel_get_stream_rate_hz();
    if (rate_hz == 0) return; // Polled mode only
    
    uint32_t period_ms = 1000 / rate_hz;
    
    if ((now - last_tx_time) >= period_ms) {
        last_tx_time = now;
        char tx_buffer[512];
        int len = kernel_generate_uplink(tx_buffer, sizeof(tx_buffer));
        if (len > 0) {
            // Send the JSON packet over the ST-Link VCP
            HAL_UART_Transmit(kernel_huart, (uint8_t*)tx_buffer, len, 100);
        }
    }
}

void serial_interface_rx_callback(UART_HandleTypeDef *huart) {
    if (huart == kernel_huart) {
        if (rx_byte == '\n' || rx_byte == '\r') {
            if (rx_index > 0) {
                rx_buffer[rx_index] = '\0';
                kernel_parse_downlink(rx_buffer); // Parse the completed text command!
                rx_index = 0;
            }
        } else if (rx_index < sizeof(rx_buffer) - 1) {
            rx_buffer[rx_index++] = (char)rx_byte;
        }
        // Re-arm the interrupt to catch the next character
        HAL_UART_Receive_IT(kernel_huart, &rx_byte, 1);
    }
}