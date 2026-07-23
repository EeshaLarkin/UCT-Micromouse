#include "py/runtime.h"
#include "py/mphal.h"
#include "micromouse_kernel.h"

extern volatile bool mouse_initialized;
extern void initMicroMouse(void);

static mp_obj_t mpy_uct_mouse_init(void) {
    // 1. Force disable all DMA channels to prevent background memory corruption
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    DMA1_Channel2->CCR &= ~DMA_CCR_EN;
    DMA1_Channel3->CCR &= ~DMA_CCR_EN;
    DMA1_Channel4->CCR &= ~DMA_CCR_EN;
    DMA1_Channel5->CCR &= ~DMA_CCR_EN;
    DMA1_Channel6->CCR &= ~DMA_CCR_EN;
    DMA1_Channel7->CCR &= ~DMA_CCR_EN;
    DMA2_Channel1->CCR &= ~DMA_CCR_EN;
    DMA2_Channel2->CCR &= ~DMA_CCR_EN;
    DMA2_Channel3->CCR &= ~DMA_CCR_EN;
    DMA2_Channel4->CCR &= ~DMA_CCR_EN;
    DMA2_Channel5->CCR &= ~DMA_CCR_EN;
    DMA2_Channel6->CCR &= ~DMA_CCR_EN;
    DMA2_Channel7->CCR &= ~DMA_CCR_EN;

    // Force de-initialization state first to pause background tick I2C reads
    mouse_initialized = false;

    // Re-initialize I2C1 and I2C2 to ensure GPIO alternate functions are correct
    // after MicroPython boot pin configurations have finished.
    extern I2C_HandleTypeDef hi2c1;
    extern I2C_HandleTypeDef hi2c2;
    hi2c1.State = HAL_I2C_STATE_RESET;
    hi2c2.State = HAL_I2C_STATE_RESET;
    HAL_I2C_DeInit(&hi2c1);
    HAL_I2C_DeInit(&hi2c2);
    
    extern void MX_I2C1_Init(void);
    extern void MX_I2C2_Init(void);
    MX_I2C1_Init();
    MX_I2C2_Init();

    // Re-initialize TIM3 (Motor PWM) and TIM4 (Encoders) alternate functions
    extern TIM_HandleTypeDef htim3;
    extern TIM_HandleTypeDef htim4;
    HAL_TIM_PWM_DeInit(&htim3);
    HAL_TIM_IC_DeInit(&htim4);
    
    extern void MX_TIM3_Init(void);
    extern void MX_TIM4_Init(void);
    MX_TIM3_Init();
    MX_TIM4_Init();

    // Enable GPIOD and GPIOC clocks to ensure motor enable and PWM control are active
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    // Explicitly re-initialize PD7 (MOTOR_EN) as a Push-Pull output
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_7;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    
    initMicroMouse();
    mouse_initialized = true;

    return mp_obj_new_int(1);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_init_obj, mpy_uct_mouse_init);

// 2. uct_mouse.set_motors(left_pwm, right_pwm)
static mp_obj_t mpy_uct_mouse_set_motors(mp_obj_t left, mp_obj_t right) {
    int l = mp_obj_get_int(left);
    int r = mp_obj_get_int(right);
    kernel_set_pwm(l, r);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mpy_uct_mouse_set_motors_obj, mpy_uct_mouse_set_motors);

// 3. uct_mouse.get_tof() -> tuple (left, front_left, center, front_right, right)
static mp_obj_t mpy_uct_mouse_get_tof(void) {
    const KernelState_t* state = kernel_get_state();
    mp_obj_t tuple[5] = {
        mp_obj_new_int(state->tof_l),
        mp_obj_new_int(state->tof_al),
        mp_obj_new_int(state->tof_c),
        mp_obj_new_int(state->tof_ar),
        mp_obj_new_int(state->tof_r)
    };
    return mp_obj_new_tuple(5, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_get_tof_obj, mpy_uct_mouse_get_tof);

// 4. uct_mouse.get_encoders() -> tuple (left, right)
static mp_obj_t mpy_uct_mouse_get_encoders(void) {
    const KernelState_t* state = kernel_get_state();
    mp_obj_t tuple[2] = {
        mp_obj_new_int(state->lenc),
        mp_obj_new_int(state->renc)
    };
    return mp_obj_new_tuple(2, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_get_encoders_obj, mpy_uct_mouse_get_encoders);

// 4b. uct_mouse.get_gyro() -> float
static mp_obj_t mpy_uct_mouse_get_gyro(void) {
    const KernelState_t* state = kernel_get_state();
    return mp_obj_new_float(state->gyro);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_get_gyro_obj, mpy_uct_mouse_get_gyro);

// 5. uct_mouse.get_vbatt() -> float
static mp_obj_t mpy_uct_mouse_get_vbatt(void) {
    const KernelState_t* state = kernel_get_state();
    return mp_obj_new_float(state->v_batt);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_get_vbatt_obj, mpy_uct_mouse_get_vbatt);

// 6. uct_mouse.delay_ms(ms)
static mp_obj_t mpy_uct_mouse_delay_ms(mp_obj_t ms_obj) {
    int ms = mp_obj_get_int(ms_obj);
    mp_hal_delay_ms(ms);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mpy_uct_mouse_delay_ms_obj, mpy_uct_mouse_delay_ms);

// 7. uct_mouse.set_polarity(left, right)
static mp_obj_t mpy_uct_mouse_set_polarity(mp_obj_t left, mp_obj_t right) {
    int l = mp_obj_get_int(left);
    int r = mp_obj_get_int(right);
    kernel_set_polarity((int16_t)l, (int16_t)r);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(mpy_uct_mouse_set_polarity_obj, mpy_uct_mouse_set_polarity);

// 7b. uct_mouse.get_line_sensors() -> tuple (fl, fr, sl, sr)
static mp_obj_t mpy_uct_mouse_get_line_sensors(void) {
    const KernelState_t* state = kernel_get_state();
    mp_obj_t tuple[4] = {
        mp_obj_new_int(state->ir_fl),
        mp_obj_new_int(state->ir_fr),
        mp_obj_new_int(state->ir_sl),
        mp_obj_new_int(state->ir_sr)
    };
    return mp_obj_new_tuple(4, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_get_line_sensors_obj, mpy_uct_mouse_get_line_sensors);

// 7c. uct_mouse.dump_logs()
static mp_obj_t mpy_uct_mouse_dump_logs(void) {
    extern void kernel_logger_dump(void);
    kernel_logger_dump();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mpy_uct_mouse_dump_logs_obj, mpy_uct_mouse_dump_logs);

// Define module globals table
static const mp_rom_map_elem_t uct_mouse_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__),    MP_ROM_QSTR(MP_QSTR_uct_mouse) },
    { MP_ROM_QSTR(MP_QSTR_init),        MP_ROM_PTR(&mpy_uct_mouse_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_motors),  MP_ROM_PTR(&mpy_uct_mouse_set_motors_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_tof),     MP_ROM_PTR(&mpy_uct_mouse_get_tof_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_encoders),MP_ROM_PTR(&mpy_uct_mouse_get_encoders_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_gyro),    MP_ROM_PTR(&mpy_uct_mouse_get_gyro_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_vbatt),   MP_ROM_PTR(&mpy_uct_mouse_get_vbatt_obj) },
    { MP_ROM_QSTR(MP_QSTR_delay_ms),    MP_ROM_PTR(&mpy_uct_mouse_delay_ms_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_polarity),MP_ROM_PTR(&mpy_uct_mouse_set_polarity_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_line_sensors), MP_ROM_PTR(&mpy_uct_mouse_get_line_sensors_obj) },
    { MP_ROM_QSTR(MP_QSTR_dump_logs),    MP_ROM_PTR(&mpy_uct_mouse_dump_logs_obj) },
};
static MP_DEFINE_CONST_DICT(uct_mouse_module_globals, uct_mouse_module_globals_table);

// Register built-in module
const mp_obj_module_t uct_mouse_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&uct_mouse_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_uct_mouse, uct_mouse_module);
