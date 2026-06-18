/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: UCT_KDeploy.c
 *
 * Code generated for Simulink model 'UCT_KDeploy'.
 *
 * Model version                  : 6.26
 * Simulink Coder version         : 25.2 (R2025b) 28-Jul-2025
 * C/C++ source code generated on : Sun Jun 14 13:53:00 2026
 *
 * Target selection: ert.tlc
 * Embedded hardware selection: ARM Compatible->ARM Cortex
 * Code generation objectives:
 *    1. Execution efficiency
 *    2. ROM efficiency
 *    3. RAM efficiency
 * Validation result: Not run
 */

#include "UCT_KDeploy.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "rtwtypes.h"

const char_T UCT_KDeploy_STRING_GND = 0;/* char_T ground */

/* Block signals (default storage) */
B_UCT_KDeploy_T UCT_KDeploy_B;

/* Real-time model */
static RT_MODEL_UCT_KDeploy_T UCT_KDeploy_M_;
RT_MODEL_UCT_KDeploy_T *const UCT_KDeploy_M = &UCT_KDeploy_M_;

/* Model step function */
void UCT_KDeploy_step(void)
{
  real_T rtb_Switch;
  int32_T rtb_CCaller10_o2;
  int32_T rtb_DataTypeConversion3;
  real32_T rtb_CCaller_o1;
  real32_T rtb_CCaller_o2;
  real32_T rtb_CCaller_o3;
  real32_T rtb_CCaller_o4;
  real32_T rtb_CCaller_o5;
  int16_T tmp_0;
  uint16_T rtb_CCaller8_o1;
  uint16_T rtb_CCaller8_o2;
  uint16_T rtb_CCaller8_o3;
  uint16_T rtb_CCaller8_o4;
  char_T rtb_ComposeString[256];
  char_T tmp[256];
  uint8_T rtb_CCaller7_o1;
  uint8_T rtb_CCaller7_o2;

  /* CCaller: '<Root>/C Caller3' */
  simulink_ext_get_tof(&UCT_KDeploy_B.CCaller3_o1, &UCT_KDeploy_B.CCaller3_o2,
                       &UCT_KDeploy_B.CCaller3_o3);

  /* DataTypeConversion: '<Root>/Data Type Conversion3' */
  rtb_DataTypeConversion3 = UCT_KDeploy_B.CCaller3_o2;

  /* ComposeString: '<S1>/Compose String' incorporates:
   *  DataTypeConversion: '<S1>/Data Type Conversion'
   */
  rtb_CCaller10_o2 = snprintf(&tmp[0], 256U, "TOF_C: %03d mm", (int32_T)fmodf
    ((real32_T)rtb_DataTypeConversion3, 4.2949673E+9F));
  strncpy(&rtb_ComposeString[0], &tmp[0], 255U);
  rtb_ComposeString[255] = '\x00';

  /* CCaller: '<Root>/C Caller14' */
  simulink_ext_set_oled_line3(&rtb_ComposeString[0U]);

  /* Switch: '<S1>/Switch' incorporates:
   *  Constant: '<S1>/Constant'
   *  Constant: '<S1>/Constant1'
   *  Constant: '<S2>/Constant'
   *  RelationalOperator: '<S2>/Compare'
   */
  if (rtb_DataTypeConversion3 > UCT_KDeploy_P.CompareToConstant_const) {
    rtb_Switch = UCT_KDeploy_P.Constant_Value;
  } else {
    rtb_Switch = UCT_KDeploy_P.Constant1_Value;
  }

  /* End of Switch: '<S1>/Switch' */

  /* DataTypeConversion: '<Root>/Data Type Conversion' */
  rtb_Switch = fmod(floor(rtb_Switch), 65536.0);

  /* CCaller: '<Root>/C Caller2' incorporates:
   *  DataTypeConversion: '<Root>/Data Type Conversion'
   */
  tmp_0 = (int16_T)(rtb_Switch < 0.0 ? (int32_T)(int16_T)-(int16_T)(uint16_T)
                    -rtb_Switch : (int32_T)(int16_T)(uint16_T)rtb_Switch);
  simulink_ext_set_motors(tmp_0, tmp_0);

  /* CCaller: '<Root>/C Caller' */
  rtb_CCaller_o1 = 0.0F;
  rtb_CCaller_o2 = 0.0F;
  rtb_CCaller_o3 = 0.0F;
  rtb_CCaller_o4 = 0.0F;
  rtb_CCaller_o5 = 0.0F;
  simulink_ext_get_pwr_meter(&rtb_CCaller_o1, &rtb_CCaller_o2, &rtb_CCaller_o3,
    &rtb_CCaller_o4, &rtb_CCaller_o5);

  /* CCaller: '<Root>/C Caller10' */
  rtb_DataTypeConversion3 = 0;
  rtb_CCaller10_o2 = 0;
  simulink_ext_get_encoders(&rtb_DataTypeConversion3, &rtb_CCaller10_o2);

  /* CCaller: '<Root>/C Caller4' */
  rtb_CCaller_o1 = 0.0F;
  rtb_CCaller_o2 = 0.0F;
  rtb_CCaller_o3 = 0.0F;
  simulink_ext_get_gyro_xyz(&rtb_CCaller_o1, &rtb_CCaller_o2, &rtb_CCaller_o3);

  /* CCaller: '<Root>/C Caller5' */
  rtb_CCaller_o1 = 0.0F;
  rtb_CCaller_o2 = 0.0F;
  rtb_CCaller_o3 = 0.0F;
  simulink_ext_get_accel_xyz(&rtb_CCaller_o1, &rtb_CCaller_o2, &rtb_CCaller_o3);

  /* CCaller: '<Root>/C Caller6' */
  simulink_ext_get_imu_temp();

  /* CCaller: '<Root>/C Caller7' */
  rtb_CCaller7_o1 = 0U;
  rtb_CCaller7_o2 = 0U;
  simulink_ext_get_switches(&rtb_CCaller7_o1, &rtb_CCaller7_o2);

  /* CCaller: '<Root>/C Caller8' */
  rtb_CCaller8_o1 = 0U;
  rtb_CCaller8_o2 = 0U;
  rtb_CCaller8_o3 = 0U;
  rtb_CCaller8_o4 = 0U;
  simulink_ext_get_line_sensors(&rtb_CCaller8_o1, &rtb_CCaller8_o2,
    &rtb_CCaller8_o3, &rtb_CCaller8_o4);

  /* CCaller: '<Root>/C Caller9' */
  simulink_ext_get_vbatt();

  /* CCaller: '<Root>/C Caller1' */
  simulink_ext_set_leds(0U, 0U, 0U);

  /* CCaller: '<Root>/C Caller11' */
  simulink_ext_set_oled_header((const char_T *)((const char_T*)
    &UCT_KDeploy_STRING_GND));

  /* CCaller: '<Root>/C Caller12' */
  simulink_ext_set_oled_line1((const char_T *)((const char_T*)
    &UCT_KDeploy_STRING_GND));

  /* CCaller: '<Root>/C Caller13' */
  simulink_ext_set_oled_line2((const char_T *)((const char_T*)
    &UCT_KDeploy_STRING_GND));

  /* CCaller: '<Root>/C Caller15' */
  simulink_ext_set_oled_line4((const char_T *)((const char_T*)
    &UCT_KDeploy_STRING_GND));
}

/* Model initialize function */
void UCT_KDeploy_initialize(void)
{
  /* (no initialization code required) */
}

/* Model terminate function */
void UCT_KDeploy_terminate(void)
{
  /* (no terminate code required) */
}

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
