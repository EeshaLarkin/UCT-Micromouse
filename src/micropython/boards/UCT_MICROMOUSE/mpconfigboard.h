#define MICROPY_HW_BOARD_NAME       "UCT-MICROMOUSE"
#define MICROPY_HW_MCU_NAME         "STM32L476VE"

#define MICROPY_HW_HAS_SWITCH       (1)
#define MICROPY_HW_HAS_FLASH        (1)
#define MICROPY_HW_ENABLE_RNG       (1)
#define MICROPY_HW_ENABLE_RTC       (1)
#define MICROPY_HW_ENABLE_USB       (1)
#define MICROPY_HW_ENABLE_DAC       (0)

// MSI clock configuration (boosted to 80 MHz SysClk)
#define MICROPY_HW_CLK_PLLM         (1)
#define MICROPY_HW_CLK_PLLN         (40)
#define MICROPY_HW_CLK_PLLP         (RCC_PLLP_DIV7)
#define MICROPY_HW_CLK_PLLQ         (RCC_PLLQ_DIV2)
#define MICROPY_HW_CLK_PLLR         (RCC_PLLR_DIV2)

#define MICROPY_HW_FLASH_LATENCY    FLASH_LATENCY_4

// The board does not use LSE (PC14/PC15 are routed to LEDs)
#define MICROPY_HW_RTC_USE_LSE      (0)

// USART1 config (Pins match the physical board's serial connection)
#define MICROPY_HW_UART1_TX         (pin_B6)
#define MICROPY_HW_UART1_RX         (pin_B7)

// REPL is routed over USB Virtual COM Port (CDC VCP) by default
#define MICROPY_HW_UART_REPL        PYB_UART_1
#define MICROPY_HW_UART_REPL_BAUD   115200
#define MICROPY_HW_ENABLE_UART_DEBUG (1)

// I2C buses (I2C1 for TOF/IMU, I2C2 for OLED/Sensors)
#define MICROPY_HW_I2C1_SCL         (pin_B8)
#define MICROPY_HW_I2C1_SDA         (pin_B9)
#define MICROPY_HW_I2C2_SCL         (pin_B10)
#define MICROPY_HW_I2C2_SDA         (pin_B11)

// USRSW is SW1 (PE6), active low
#define MICROPY_HW_USRSW_PIN        (pin_E6)
#define MICROPY_HW_USRSW_PULL       (GPIO_PULLUP)
#define MICROPY_HW_USRSW_EXTI_MODE  (GPIO_MODE_IT_FALLING)
#define MICROPY_HW_USRSW_PRESSED    (0)

// LEDs (PC13, PC14, PC15)
#define MICROPY_HW_LED1             (pin_C13)
#define MICROPY_HW_LED2             (pin_C14)
#define MICROPY_HW_LED3             (pin_C15)
#define MICROPY_HW_LED_ON(pin)      (mp_hal_pin_high(pin))
#define MICROPY_HW_LED_OFF(pin)     (mp_hal_pin_low(pin))

// USB config
#define MICROPY_HW_USB_FS           (1)

// Board startup and loop hooks to run the background C-Kernel task
void board_startup(void);
void board_early_init(void);
void kernel_background_tick(void);

#define MICROPY_BOARD_STARTUP       board_startup
#define MICROPY_BOARD_EARLY_INIT    board_early_init
#define MICROPY_VM_HOOK_LOOP        kernel_background_tick();
#define MICROPY_INTERNAL_EVENT_HOOK kernel_background_tick();

// Expose the custom uct_mouse module as a built-in module
extern const struct _mp_obj_module_t uct_mouse_module;
#define MICROPY_PORT_BUILTIN_MODULES \
    { MP_ROM_QSTR(MP_QSTR_uct_mouse), MP_ROM_PTR(&uct_mouse_module) },

