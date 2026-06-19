#include "py/mphal.h"
#include "py/obj.h"
#include "py/stream.h"
#include "extmod/misc.h"
#include "usb.h"
#include "uart.h"
#include "main.h"
#include "serial_interface.h"
#include "dma.h"
#include "micromouse_kernel.h"

#if MICROPY_HW_TINYUSB_STACK
#include "shared/tinyusb/mp_usbd_cdc.h"
#endif

// Extern hardware handles and init functions from the template
extern UART_HandleTypeDef huart1;
extern void initMicroMouse(void);
extern void MX_DMA_Init(void);
extern void MX_GPIO_Init(void);
extern void MX_ADC1_Init(void);
extern void MX_I2C1_Init(void);
extern void MX_I2C2_Init(void);
extern void MX_TIM1_Init(void);
extern void MX_TIM3_Init(void);
extern void MX_TIM4_Init(void);
extern void MX_TIM5_Init(void);
extern void MX_TIM7_Init(void);
extern void MX_USART1_UART_Init(void);
extern void MX_NVIC_Init(void);

// Extern background routines from the C-Kernel
extern void refreshADCs(void);
extern void refreshSWValues(void);
extern void refreshTOFValues(void);
extern void refreshIMUValues(void);
extern void refreshINA219Values(void);
extern void kernel_update_display(void);
extern void serial_interface_tick(void);
extern void kernel_watchdog_tick(void);

// Global flag to track if physical hardware has been initialized
volatile bool mouse_initialized = false;

// Dummy board startup hook called before clocks are configured
void board_startup(void) {
}

static void uart_print(const char *str) {
    if (USART1 != NULL && (RCC->APB2ENR & RCC_APB2ENR_USART1EN)) {
        for (const char *p = str; *p; p++) {
            while (!(USART1->ISR & USART_ISR_TXE));
            USART1->TDR = (uint8_t)*p;
        }
    }
}

// Define the strong SystemClock_Config to override MicroPython's default weak one in system_stm32.c.
// This sets up the clock tree (80MHz) and peripheral dividers (I2C1, I2C2, SAI1, ADC, USB)
// as required by Jesse's C-Kernel.
void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK) {
        // Panic block
        while (1);
    }

    HAL_PWR_EnableBkUpAccess();

    // 1. Configure System Clock using HSI + PLL (80 MHz)
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 1;
    RCC_OscInitStruct.PLL.PLLN = 10;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV4;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        while (1);
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK) {
        while (1);
    }

    // 2. Configure USB, ADC, and I2C clocks.
    // USB uses PLLSAI1-Q (16MHz / 1 * 12 / 4 = 48 MHz)
    // ADC uses PLLSAI1-R (16MHz / 1 * 12 / 2 = 96 MHz)
    PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_USB | RCC_PERIPHCLK_ADC
                                             | RCC_PERIPHCLK_I2C1 | RCC_PERIPHCLK_I2C2;
    PeriphClkInitStruct.UsbClockSelection = RCC_USBCLKSOURCE_PLLSAI1;
    PeriphClkInitStruct.AdcClockSelection = RCC_ADCCLKSOURCE_PLLSAI1;
    PeriphClkInitStruct.I2c1ClockSelection = RCC_I2C1CLKSOURCE_PCLK1;
    PeriphClkInitStruct.I2c2ClockSelection = RCC_I2C2CLKSOURCE_PCLK1;
    
    PeriphClkInitStruct.PLLSAI1.PLLSAI1Source = RCC_PLLSOURCE_HSI;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1M = 1;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1N = 12;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1P = RCC_PLLP_DIV7;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1Q = RCC_PLLQ_DIV4;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1R = RCC_PLLR_DIV2;
    PeriphClkInitStruct.PLLSAI1.PLLSAI1ClockOut = RCC_PLLSAI1_48M2CLK | RCC_PLLSAI1_ADC1CLK;
    
    if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
        while (1);
    }
}

// Define strong mp_hal_stdout_tx_strn to override the default weak one in mphalport.c.
// This allows redirecting output to USART1 (pins on physical board) for logging.
mp_uint_t mp_hal_stdout_tx_strn(const char *str, size_t len) {
    mp_uint_t ret = len;
    bool did_write = false;

    // Direct register-level VCP UART output redirect to USART1 for boot logging and fault reporting
    if (USART1 != NULL && (RCC->APB2ENR & RCC_APB2ENR_USART1EN)) {
        for (size_t i = 0; i < len; i++) {
            while (!(USART1->ISR & USART_ISR_TXE));
            USART1->TDR = (uint8_t)str[i];
        }
        did_write = true;
    }

    if (MP_STATE_PORT(pyb_stdio_uart) != NULL) {
        uart_tx_strn(MP_STATE_PORT(pyb_stdio_uart), str, len);
        did_write = true;
    }
    #if MICROPY_HW_USB_CDC && MICROPY_HW_TINYUSB_STACK
    mp_uint_t cdc_res = mp_usbd_cdc_tx_strn(str, len);
    if (cdc_res > 0) {
        did_write = true;
        ret = MIN(cdc_res, ret);
    }
    #endif
    int dupterm_res = mp_os_dupterm_tx_strn(str, len);
    if (dupterm_res >= 0) {
        did_write = true;
        ret = MIN((mp_uint_t)dupterm_res, ret);
    }

    return did_write ? ret : 0;
}

void Error_Handler(void) {
    uart_print("\n!!! Error_Handler Called !!!\n");
    while (1) {
        // Flash LED1 (pin_C13) to indicate crash
        mp_hal_pin_high(pin_C13);
        for (volatile int i = 0; i < 500000; i++);
        mp_hal_pin_low(pin_C13);
        for (volatile int i = 0; i < 500000; i++);
    }
}

// Early board initialization hook called after system clock is fully configured (80 MHz)
void board_early_init(void) {
    // 1. Core peripheral DMA & GPIO init
    MX_DMA_Init();
    MX_GPIO_Init();
    
    // 2. Initialize USART1 and configure baudrate first so we can output logs immediately
    MX_USART1_UART_Init();
    __HAL_UART_DISABLE(&huart1);
    USART1->BRR = 694; 
    __HAL_UART_ENABLE(&huart1);

    // UART output - active immediately!
    uart_print("\n--- Boot Log Start ---\n");
    extern int pyb_hard_fault_debug;
    pyb_hard_fault_debug = 1;

    // 3. Initialize NVIC and other peripheral controllers
    MX_NVIC_Init();
    
    uart_print("Initializing ADC...\n");
    MX_ADC1_Init();
    // Disable the ADC DMA interrupt in NVIC. The DMA hardware circular transfer
    // will continue updating values in the buffer, but it won't interrupt the CPU
    // (avoiding IRQ loop conflicts with MicroPython's dma.c)
    HAL_NVIC_DisableIRQ(DMA1_Channel1_IRQn);
    
    uart_print("Initializing I2C1...\n");
    MX_I2C1_Init();
    
    uart_print("Initializing I2C2...\n");
    MX_I2C2_Init();
    
    uart_print("Initializing Timers...\n");
    MX_TIM1_Init();
    MX_TIM3_Init();
    MX_TIM4_Init();
    MX_TIM5_Init();
    MX_TIM7_Init();

    uart_print("Boot sequence completed successfully.\n");
}

// Background tick function hook called inside MicroPython VM execution and delay loops
void kernel_background_tick(void) {
    static bool in_tick = false;
    if (in_tick) {
        return;
    }
    in_tick = true;

    static uint32_t last_tick = 0;
    uint32_t now = HAL_GetTick();
    
    // Rate limit C-Kernel background task updates to 100 Hz (every 10ms)
    if (now - last_tick >= 10) {
        last_tick = now;
        
        if (mouse_initialized) {
            refreshADCs();
            refreshSWValues();
            refreshTOFValues();
            refreshIMUValues();
            refreshINA219Values();
            
            // Snapshot physical state to the C-Kernel state structure
            kernel_snapshot_state();
            
            // Refresh local SSD1306 OLED screen
            kernel_update_display();
        }
        
        // Feed kernel software watchdog
        kernel_watchdog_tick();
    }

    in_tick = false;
}

// Override factory_reset_make_files to write our custom hybrid boot.py and main.py on first-boot filesystem creation.
// This guarantees the USB drive is read-only by default even before the user deploys any files!
#include "extmod/vfs_fat.h"

static const char custom_boot_py[] =
    "# boot.py - UCT Micromouse Hybrid Bootloader\r\n"
    "import machine\r\n"
    "import pyb\r\n"
    "import time\r\n"
    "\r\n"
    "# The User Switch is on PE6, active low\r\n"
    "sw = machine.Pin('E6', machine.Pin.IN, machine.Pin.PULL_UP)\r\n"
    "time.sleep_ms(50)\r\n"
    "\r\n"
    "if sw.value() == 0:\r\n"
    "    # Held during boot -> Mount read-write\r\n"
    "    pyb.usb_mode('VCP+MSC')\r\n"
    "else:\r\n"
    "    # Fallback to standard VCP+MSC to avoid unsupported argument crash\r\n"
    "    pyb.usb_mode('VCP+MSC')\r\n";

static const char custom_main_py[] =
    "# main.py -- put your code here!\r\n";

static const char custom_readme_txt[] =
    "UCT Micromouse (UCT_MMOUSE) internal flash is locked as Read-Only to prevent standard PC editors from wearing it out.\r\n"
    "\r\n"
    "To make it writable for dragging and dropping files directly, turn on the mouse while holding down the PE6 User Button.\r\n"
    "Alternatively, deploy scripts cleanly over VCP serial using 'python tools/deploy.py -e micropython'.\r\n";

void factory_reset_make_files(FATFS *fatfs) {
    struct {
        const char *name;
        const char *data;
    } files[] = {
        {"boot.py", custom_boot_py},
        {"main.py", custom_main_py},
        {"README.txt", custom_readme_txt},
    };
    for (size_t i = 0; i < sizeof(files)/sizeof(files[0]); ++i) {
        FIL fp;
        FRESULT res = f_open(fatfs, &fp, files[i].name, FA_WRITE | FA_CREATE_ALWAYS);
        if (res == FR_OK) {
            UINT n;
            f_write(&fp, files[i].data, strlen(files[i].data), &n);
            f_close(&fp);
        }
    }
}
