/*
 * Academic License - for use in teaching, academic research, and meeting
 * course requirements at degree granting institutions only.  Not for
 * government, commercial, or other organizational use.
 *
 * File: UCT_KDeploy.h
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

#ifndef UCT_KDeploy_h_
#define UCT_KDeploy_h_
#ifndef UCT_KDeploy_COMMON_INCLUDES_
#define UCT_KDeploy_COMMON_INCLUDES_
#include "rtwtypes.h"
#endif                                 /* UCT_KDeploy_COMMON_INCLUDES_ */

#include "UCT_KDeploy_types.h"

/* Macros for accessing real-time model data structure */
#ifndef rtmGetErrorStatus
#define rtmGetErrorStatus(rtm)         ((rtm)->errorStatus)
#endif

#ifndef rtmSetErrorStatus
#define rtmSetErrorStatus(rtm, val)    ((rtm)->errorStatus = (val))
#endif

/* user code (top of header file) */
#include "simulink_wrapper.h"

/* Block signals (default storage) */
typedef struct {
  uint16_T CCaller3_o1;                /* '<Root>/C Caller3' */
  uint16_T CCaller3_o2;                /* '<Root>/C Caller3' */
  uint16_T CCaller3_o3;                /* '<Root>/C Caller3' */
} B_UCT_KDeploy_T;

/* Parameters (default storage) */
struct P_UCT_KDeploy_T_ {
  real32_T CompareToConstant_const;   /* Mask Parameter: CompareToConstant_const
                                       * Referenced by: '<S2>/Constant'
                                       */
  real_T Constant_Value;               /* Expression: 30
                                        * Referenced by: '<S1>/Constant'
                                        */
  real_T Constant1_Value;              /* Expression: 0
                                        * Referenced by: '<S1>/Constant1'
                                        */
};

/* Code_Instrumentation_Declarations_Placeholder */

/* Real-time Model Data Structure */
struct tag_RTM_UCT_KDeploy_T {
  const char_T * volatile errorStatus;
};

/* Block parameters (default storage) */
extern P_UCT_KDeploy_T UCT_KDeploy_P;

/* Block signals (default storage) */
extern B_UCT_KDeploy_T UCT_KDeploy_B;

/* External data declarations for dependent source files */
extern const char_T UCT_KDeploy_STRING_GND;/* char_T ground */

/* Model entry point functions */
extern void UCT_KDeploy_initialize(void);
extern void UCT_KDeploy_step(void);
extern void UCT_KDeploy_terminate(void);

/* Real-time Model object */
extern RT_MODEL_UCT_KDeploy_T *const UCT_KDeploy_M;

/*-
 * These blocks were eliminated from the model due to optimizations:
 *
 * Block '<Root>/Data Type Conversion2' : Unused code path elimination
 * Block '<Root>/Data Type Conversion4' : Unused code path elimination
 * Block '<S1>/Scope' : Unused code path elimination
 */

/*-
 * The generated code includes comments that allow you to trace directly
 * back to the appropriate location in the model.  The basic format
 * is <system>/block_name, where system is the system number (uniquely
 * assigned by Simulink) and block_name is the name of the block.
 *
 * Use the MATLAB hilite_system command to trace the generated code back
 * to the model.  For example,
 *
 * hilite_system('<S3>')    - opens system 3
 * hilite_system('<S3>/Kp') - opens and selects block Kp which resides in S3
 *
 * Here is the system hierarchy for this model
 *
 * '<Root>' : 'UCT_KDeploy'
 * '<S1>'   : 'UCT_KDeploy/Subsystem Reference'
 * '<S2>'   : 'UCT_KDeploy/Subsystem Reference/Compare To Constant'
 */
#endif                                 /* UCT_KDeploy_h_ */

/*
 * File trailer for generated code.
 *
 * [EOF]
 */
