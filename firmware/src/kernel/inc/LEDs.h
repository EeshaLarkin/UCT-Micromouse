//********************************************************************
//*                          Micro Mouse                             *
//*                          LED Library                             *
//*==================================================================*
//* @author:    Jesse Jabez Arendse                                  *
//* @date:      24-10-2023                                           *
//*==================================================================*
//*                                                                  *
//* Description:                                                     *
//* This header file provides an interface for controlling LEDs      *
//* connected to GPIO pins PC13, PC14, and PC15 on the Micro Mouse   *
//* robot. It includes functions for initializing the LEDs and       *
//* refreshing their states based on an array.                       *
//*                                                                  *
//********************************************************************

#ifndef LEDS_H
#define LEDS_H

#include "stm32l4xx.h"
#include "main.h"

// LED pin/port defines (Overridden locally for diagnostic LEDs on PA4/PA5)
#define LED0_Pin            GPIO_PIN_13
#define LED0_GPIO_Port      GPIOC
#define LED1_Pin            GPIO_PIN_4
#define LED1_GPIO_Port      GPIOA
#define LED2_Pin            GPIO_PIN_5
#define LED2_GPIO_Port      GPIOA

// IR LED pin/port defines
#define LEFT_MOTOR_Pin      GPIO_PIN_9
#define LEFT_MOTOR_GPIO_Port GPIOE
#define RIGHT_MOTOR_Pin     GPIO_PIN_13
#define RIGHT_MOTOR_GPIO_Port GPIOE
#define DOWN_LEFT_Pin       GPIO_PIN_14
#define DOWN_LEFT_GPIO_Port GPIOE
#define DOWN_RIGHT_Pin      GPIO_PIN_11
#define DOWN_RIGHT_GPIO_Port GPIOE

// CTRL_LEDS pin defines
#define CTRL_LEDS_Pin       GPIO_PIN_3
#define CTRL_LEDS_GPIO_Port GPIOB

// LED structure: each LED has port, pin, and state
typedef struct {
	GPIO_TypeDef *port;  // GPIO port (e.g., GPIOC)
	uint16_t pin;        // GPIO pin (e.g., GPIO_PIN_13)
	uint8_t state;       // LED state (0 = OFF, 1 = ON)
} LED_t;

// Individual LED control structures
extern LED_t LED0;  // PC13
extern LED_t LED1;  // PC14/PA4
extern LED_t LED2;  // PC15/PA5
extern LED_t IR_LED_LEFT_MOTOR;  // PE9
extern LED_t IR_LED_RIGHT_MOTOR;  // PE13
extern LED_t IR_LED_DOWN_LEFT;    // PE14
extern LED_t IR_LED_DOWN_RIGHT;   // PE11

// Function declarations
void initLEDs();
void refreshLEDs();

#endif
