/**
 * pn_core/hal_if.h — 硬件抽象层契约
 *
 * 动作层只通过本结构体调用硬件；主机测试注入 mock 实现，
 * ESP32 目标机由 pn_hal_esp32 组件提供真实实现（LEDC/I2C）。
 * 铁律（笔记 02 第 4 节）：阀与泵全部走 PWM 占空比通道，保持电压节能才有抓手。
 */
#pragma once

#include "pn_core/types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    /* 写阀占空比：valve_idx ∈ pn_valve_t，duty 0–255（255=全开，PN_HOLD_DEFAULT_DUTY=保持） */
    void (*valve_write)(uint8_t valve_idx, uint8_t duty);

    /* 写泵占空比：pump_idx ∈ [0, PN_PUMP_COUNT)，duty 0–255 */
    void (*pump_write)(uint8_t pump_idx, uint8_t duty);

    /* 读压力（kPa，表压）。返回 0=成功，-1=失败。sensor_idx 从 0 起 */
    int (*sensor_read)(uint8_t sensor_idx, float *kpa);

    /* 毫秒时钟（上电起累计） */
    uint32_t (*now_ms)(void);
} pn_hal_if_t;

#ifdef __cplusplus
}
#endif
