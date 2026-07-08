cmake_minimum_required(VERSION 3.10)

project(UCT_Kernel C)

add_library(uct_kernel STATIC
    src/micromouse_kernel.c
    src/simulink_wrapper.c
    src/serial_interface.c
)

# Define the STM32 device so the HAL drivers compile properly
target_compile_definitions(uct_kernel PUBLIC USE_HAL_DRIVER STM32L476xx)

target_include_directories(uct_kernel PUBLIC
    inc/
    ../../../external/MicroMouseTemplate/MicroMouseProgramming_Code/Core/Inc
    ../../../external/MicroMouseTemplate/MicroMouseProgramming_Code/Drivers/STM32L4xx_HAL_Driver/Inc
    ../../../external/MicroMouseTemplate/MicroMouseProgramming_Code/Drivers/CMSIS/Device/ST/STM32L4xx/Include
    ../../../external/MicroMouseTemplate/MicroMouseProgramming_Code/Drivers/CMSIS/Include
)