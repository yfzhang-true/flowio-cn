/**
 * pn_hal_esp32/hal_esp32.h — ESP32-S3 硬件层（LEDC 阀/泵 + RMT 舵机 + I2C 传感器）
 */
#pragma once

#include "pn_core/hal_if.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 配置全部 PWM/RMT/I2C 外设，并返回绑定好的 HAL 接口。
 * 调用后即可 pn_init(&pn_hal_esp32_if(), PN_CFG_GENERAL) */
const pn_hal_if_t *pn_hal_esp32_init(void);

/* kit PWM 电子开关的舵机信号：pulse_us = 500–2500（1500 中位）
 * switch_idx: 0=泵 1=充气阀 2=吸气阀 */
void pn_hal_esp32_servo_set(uint8_t switch_idx, uint16_t pulse_us);

#ifdef __cplusplus
}
#endif
