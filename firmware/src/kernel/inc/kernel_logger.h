#ifndef KERNEL_LOGGER_H
#define KERNEL_LOGGER_H

#include <stdint.h>

void kernel_logger_init(void);
void kernel_logger_tick(void);
void kernel_logger_dump(void);
void kernel_logger_dump_custom(void (*print_fn)(const uint8_t *buf, uint32_t len));

#endif /* KERNEL_LOGGER_H */
