#include "stm32l4xx_hal.h"
#include "serial_interface.h"
#include "micromouse_kernel.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#ifdef COMPILING_FOR_PIKASCRIPT
#include "pikaScript.h"
#if __has_include("student_code.h")
#include "student_code.h"
#else
const char* student_python_code = 
"# =========================================================================\n"
"# UCT Micromouse - Fallback Student Application\n"
"# =========================================================================\n"
"import uct_mouse\n"
"uct_mouse.init()\n"
"print(\"--- PikaScript Fallback Alive ---\")\n"
"while True:\n"
"    uct_mouse.delay_ms(1000)\n";
#endif
#endif

extern void MX_DMA_Init(void);
extern void MX_GPIO_Init(void);
extern void MX_TIM1_Init(void);
extern void MX_TIM3_Init(void);
extern void MX_TIM4_Init(void);
extern void MX_TIM5_Init(void);
extern void MX_TIM7_Init(void);
extern void MX_USART1_UART_Init(void);
extern void MX_NVIC_Init(void);
extern void MX_ADC1_Init(void);
extern void MX_I2C1_Init(void);
extern void MX_I2C2_Init(void);

extern void initMicroMouse(void);
extern void SystemClock_Config(void);

// Expose the raw hardware polling functions to bypass Jesse's screen updates
extern void refreshADCs(void);
extern void refreshSWValues(void);
extern void refreshTOFValues(void);
extern void refreshIMUValues(void);
extern void refreshINA219Values(void);
extern void refreshMotors(void);

extern UART_HandleTypeDef huart1;

#ifdef COMPILING_FOR_PIKASCRIPT
// Provide a weak fallback for the Python module bytecode array.
__attribute__((weak)) const unsigned char pikaModules_py_a[] = "";

// -------------------------------------------------------------
// Route Python print() statements directly to the USB Serial Port
// -------------------------------------------------------------
void pika_platform_printf(char *fmt, ...) {
    char buf[128];
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    if (len > 0) {
        HAL_UART_Transmit(&huart1, (uint8_t*)buf, len, 100);
    }
}
#endif

#ifdef COMPILING_FOR_SIMULINK
// Provide a weak fallback for the Simulink generated step function.
__attribute__((weak)) void UCT_KDeploy_initialize(void) {}
__attribute__((weak)) void UCT_KDeploy_step(void) {}
#endif

void raw_uart_print(const char *str) {
    if (USART1 != NULL && (RCC->APB2ENR & RCC_APB2ENR_USART1EN)) {
        for (const char *p = str; *p; p++) {
            while (!(USART1->ISR & USART_ISR_TXE));
            USART1->TDR = (uint8_t)*p;
        }
    }
}

// -------------------------------------------------------------
// Hardware Fault Handler
// -------------------------------------------------------------
void Error_Handler(void) {
    raw_uart_print("\r\n!!! Error_Handler Called !!!\r\n");
    __disable_irq();
    while (1) {
        // Toggle PC13 LED (LED0) to indicate crash
        if (GPIOC != NULL && (RCC->AHB2ENR & RCC_AHB2ENR_GPIOCEN)) {
            GPIOC->ODR ^= GPIO_PIN_13;
        }
        for (volatile int i = 0; i < 500000; i++);
    }
}

int main(void) {
    // 1. Core Initialization
    if (HAL_Init() != HAL_OK) { Error_Handler(); }
    
    SystemClock_Config();
    SystemCoreClockUpdate(); // Sync HAL global variables with physical clock

    // 2. Peripheral Initialization
    MX_DMA_Init();
    MX_GPIO_Init();

    // Explicitly configure PD7 (MOTOR_EN) as output push-pull to ensure motor driver can be enabled
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_7;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    MX_ADC1_Init();
    MX_I2C1_Init();
    MX_I2C2_Init();
    MX_TIM1_Init();
    MX_TIM3_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();
    MX_TIM7_Init();
    MX_USART1_UART_Init();
    MX_NVIC_Init();

    // Initialize the HAL handle instance first to avoid null pointer dereferences
    huart1.Instance = USART1;
    huart1.gState = HAL_UART_STATE_READY;
    huart1.RxState = HAL_UART_STATE_READY;

    // Configure UART for standard 80 MHz APB clock (80,000,000 / 115200 = 694)
    __HAL_UART_DISABLE(&huart1);
    USART1->BRR = 694; 
    __HAL_UART_ENABLE(&huart1);

    raw_uart_print("\r\n--- STM32 Core Boot Completed ---\r\n");
    raw_uart_print("Initializing Micromouse Hardware...\r\n");

    // 4. Initialize Hardware Sensors & Actuators
    initMicroMouse();

    raw_uart_print("Micromouse Hardware Initialized.\r\n");

    // 5. Start Delta-Shadow Network Proxy
    serial_interface_init(&huart1);

#ifdef COMPILING_FOR_PIKASCRIPT
    // Give the PC Serial Monitor time to connect before Python starts shouting!
    HAL_Delay(2000);
    pika_platform_printf("\r\n=== Booting PikaScript ===\r\n");

    // 6. Initialize PikaScript Embedded Python
    extern PikaObj* New_PikaMain(Args* args);
    PikaObj *pikaMain = newRootObj("pikaMain", New_PikaMain);
    
    kernel_set_title("   PikaScript     ");
    
    // Check if a dynamically flashed student script exists at 0x08078000 (Page 240)
    const char* python_code = (const char*)0x08078000;
    if ((uint8_t)python_code[0] == 0xFF) {
        // Fallback to the compiled-in script if the flash sector is empty (erased)
        python_code = student_python_code;
    }
    
    // Execute the Python script natively!
    obj_run(pikaMain, (char*)python_code);
    
    // If PikaScript exits or crashes, revert the title so the user knows!
    kernel_set_title("   UCT MOUSE      ");
#endif

#ifdef COMPILING_FOR_SIMULINK
    // 7. Initialize Simulink Autocoded Logic (if compiled into the firmware)
    UCT_KDeploy_initialize();
#endif
    
    uint32_t last_control_tick = HAL_GetTick();

    while (1) {
        refreshADCs();
        refreshSWValues();
        refreshTOFValues();
        refreshIMUValues();
        refreshINA219Values();
        
#ifdef COMPILING_FOR_SIMULINK
        // 8. Execute Control Logic at Strict Rate
        uint32_t rate_hz = kernel_get_stream_rate_hz();
        uint32_t period_ms = (rate_hz > 0) ? (1000 / rate_hz) : 10; // Default 100Hz (10ms)
        
        if (HAL_GetTick() - last_control_tick >= period_ms) {
            last_control_tick += period_ms; // Add period to prevent drift over time
            
            // We add a 3-second boot delay to prevent motor startup surges 
            if (HAL_GetTick() > 3000) {
                UCT_KDeploy_step();
            }
        }
#endif

        kernel_update_display();
        serial_interface_tick();
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    serial_interface_rx_callback(huart);
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    // Hijack TIM6 to advance HAL timebase while muting legacy ghost telemetry
    if (htim->Instance == TIM6) {
        HAL_IncTick();
        kernel_watchdog_tick();
    }
}