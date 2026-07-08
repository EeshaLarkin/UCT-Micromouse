#ifndef SERIAL_INTERFACE_H
#define SERIAL_INTERFACE_H

#include "stm32l4xx_hal.h"

void serial_interface_init(UART_HandleTypeDef *huart);
void serial_interface_tick(void);
void serial_interface_rx_callback(UART_HandleTypeDef *huart);

#endif // SERIAL_INTERFACE_H