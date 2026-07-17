#ifndef KERNEL_LOGGER_H
#define KERNEL_LOGGER_H

#include <stdint.h>

void kernel_logger_init(void);
void kernel_logger_tick(void);
void kernel_logger_dump(void);

#endif /* KERNEL_LOGGER_H */
