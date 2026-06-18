#include "py/runtime.h"
#include "py/mphal.h"
#include "micromouse_kernel.h"

extern volatile bool mouse_initialized;
extern void initMicroMouse(void);

// 1. uct_mouse.init() -> int
static mp_obj_t mpy_uct_mouse_init(void) {
    if (!mouse_initialized) {
        initMicroMouse();
        mouse_initialized = true;
    }
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

// 3. uct_mouse.get_tof() -> tuple (left, center, right)
static mp_obj_t mpy_uct_mouse_get_tof(void) {
    const KernelState_t* state = kernel_get_state();
    mp_obj_t tuple[3] = {
        mp_obj_new_int(state->tof_l),
        mp_obj_new_int(state->tof_c),
        mp_obj_new_int(state->tof_r)
    };
    return mp_obj_new_tuple(3, tuple);
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
};
static MP_DEFINE_CONST_DICT(uct_mouse_module_globals, uct_mouse_module_globals_table);

// Register built-in module
const mp_obj_module_t uct_mouse_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&uct_mouse_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_uct_mouse, uct_mouse_module);
