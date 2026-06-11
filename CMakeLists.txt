cmake_minimum_required(VERSION 3.10)

# --- CROSS-COMPILATION TOOLCHAIN SETUP ---
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

# Tell CMake to bypass the executable linker test (avoids bare-metal syscall missing errors)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# Global hardware flags required for all targets (Kernel + Python)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -Os -g3 -Wall -Wno-pointer-to-int-cast -Wno-int-to-pointer-cast -Wno-incompatible-pointer-types")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")

project(UCT_Micromouse C CXX ASM)

# 1. Build our C proxy kernel library
add_subdirectory(src/kernel)

# 2. Define the main firmware executable target
set(EXECUTABLE ${PROJECT_NAME}.elf)

# Path to Jesse's template repository submodule
set(TEMPLATE_DIR "external/MicroMouseTemplate/MicroMouseProgramming_Code")

# 3. Dynamically find all source files in Jesse's template
file(GLOB_RECURSE HAL_SOURCES "${TEMPLATE_DIR}/Drivers/STM32L4xx_HAL_Driver/Src/*.c")
file(GLOB_RECURSE CORE_SOURCES "${TEMPLATE_DIR}/Core/Src/*.c")
if(CORE_SOURCES)
    list(FILTER CORE_SOURCES EXCLUDE REGEX "instrumented/")
endif()
file(GLOB_RECURSE USB_SOURCES "${TEMPLATE_DIR}/USB_DEVICE/App/*.c" "${TEMPLATE_DIR}/USB_DEVICE/Target/*.c")
file(GLOB_RECURSE MIDDLEWARE_SOURCES "${TEMPLATE_DIR}/Middlewares/ST/STM32_USB_Device_Library/Core/Src/*.c" "${TEMPLATE_DIR}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Src/*.c")
file(GLOB_RECURSE PIKA_SOURCES "pikascript/pikascript-api/*.c" "pikascript/pikascript-core/*.c" "pikascript/pikascript-lib/*.c")
file(GLOB STARTUP_SCRIPT "${TEMPLATE_DIR}/Core/Startup/*.s")

# 3.1 Locate Simulink Autocoded Sources (Exclude ert_main.c to prevent main() collisions)
file(GLOB SIMULINK_SOURCES "matlab/models/UCT_KDeploy_ert_rtw/*.c")
if(SIMULINK_SOURCES)
    list(FILTER SIMULINK_SOURCES EXCLUDE REGEX "ert_main\\.c")
endif()

# Mute Jesse's application loops so we can supply our own cleanly
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/${TEMPLATE_DIR}/Core/Src/main.c" APPEND PROPERTY COMPILE_DEFINITIONS 
    "main=jesse_legacy_main" 
    "HAL_UART_RxCpltCallback=jesse_legacy_uart_callback"
    "HAL_TIM_PeriodElapsedCallback=jesse_legacy_period_elapsed_callback"
    "Error_Handler=jesse_legacy_Error_Handler"
)

add_executable(${EXECUTABLE}
    src/main.c
    src/kernel/src/uct_mouse_wrapper.c
    ${HAL_SOURCES}
    ${CORE_SOURCES}
    ${USB_SOURCES}
    ${MIDDLEWARE_SOURCES}
    ${STARTUP_SCRIPT}
    ${PIKA_SOURCES}
    ${SIMULINK_SOURCES}
)

# 4. Add the required include directories
target_include_directories(${EXECUTABLE} PRIVATE
    ${TEMPLATE_DIR}/Core/Inc
    ${TEMPLATE_DIR}/USB_DEVICE/App
    ${TEMPLATE_DIR}/USB_DEVICE/Target
    ${TEMPLATE_DIR}/Drivers/STM32L4xx_HAL_Driver/Inc
    ${TEMPLATE_DIR}/Drivers/STM32L4xx_HAL_Driver/Inc/Legacy
    ${TEMPLATE_DIR}/Drivers/CMSIS/Device/ST/STM32L4xx/Include
    ${TEMPLATE_DIR}/Drivers/CMSIS/Include
    ${TEMPLATE_DIR}/Middlewares/ST/STM32_USB_Device_Library/Core/Inc
    ${TEMPLATE_DIR}/Middlewares/ST/STM32_USB_Device_Library/Class/CDC/Inc
    src/kernel/inc
    pikascript/pikascript-api
    pikascript/pikascript-core
    pikascript/pikascript-lib
    matlab/models/UCT_KDeploy_ert_rtw
)

# 5. STM32 Specific Compiler Definitions
target_compile_definitions(${EXECUTABLE} PRIVATE 
    USE_HAL_DRIVER 
    STM32L476xx
)

# 6. Linker Configuration (Hardware Memory Map & Syscalls)
set(LINKER_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/${TEMPLATE_DIR}/STM32L476VETX_FLASH.ld")

target_link_options(${EXECUTABLE} PRIVATE
    -T${LINKER_SCRIPT}
    -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
    -specs=nosys.specs
    -Wl,-Map=${PROJECT_NAME}.map
    -Wl,--gc-sections
)

# 7. Link our proxy kernel and the standard Math library (required for Python) to the final executable
target_link_libraries(${EXECUTABLE} PRIVATE uct_kernel m)

# 8. Post-build generation of the flashable .bin file
add_custom_command(TARGET ${EXECUTABLE} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary ${EXECUTABLE} ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_SIZE} ${EXECUTABLE}
    COMMENT "Building ${PROJECT_NAME}.bin and printing firmware footprint..."
)

# 9. Flash and auto-reset target
add_custom_target(flash
    COMMAND st-flash --reset write ${PROJECT_NAME}.bin 0x08000000
    DEPENDS ${EXECUTABLE}
    COMMENT "Flashing firmware and automatically resetting board..."
)