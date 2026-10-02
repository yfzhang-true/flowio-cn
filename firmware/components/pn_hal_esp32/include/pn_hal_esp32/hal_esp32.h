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
 * switch_idx: 0=泵 1=充气阀 2=吸气阀
 * set 只更新目标脉宽；实际 50Hz 脉冲流由 refresh() 周期发送（见 .c 注释） */
void pn_hal_esp32_servo_set(uint8_t switch_idx, uint16_t pulse_us);
void pn_hal_esp32_servo_refresh(void);   /* 挂控制节拍每 ~20ms 调用一次 */

/* 运行环境是否 QEMU（chip version v0.0 检测）——main 用于跳过 UART 驱动安装等
 * QEMU 仿真差异项（2026-09-23：真机 fgets(stdin) 需 uart_vfs_dev_use_driver） */
int pn_hal_esp32_is_qemu(void);

/* I2C 全总线扫描（bring-up 诊断）：主总线 0x03-0x77 + CH0/CH1 下游。
 * main.c 拦截 'W' 命令调用（真机 only；QEMU 打印未初始化提示） */
void pn_hal_esp32_i2c_scan(void);

/* 舵机信号诊断（'M' 命令）：用 LEDC 精确时基在指定 gpio 发 50Hz 舵机脉冲
 * （usec=500 关位 / 2500 开位），判别 RMT 时基问题。同时停该 gpio 的 RMT 发送。 */
void pn_hal_esp32_servo_le_test(int gpio, int usec);

/* TCA9548A I2C 写注入点（S4）：main 初始化时 tca_bind(tca_hal_write) 绑给
 * pn_core/tca9548 纯逻辑层。返回 0=成功，-1=总线失败/QEMU。 */
int tca_hal_write(uint8_t addr, uint8_t byte);

/* 板载 WS2812 状态灯（GPIO48，S4）：init 上电配置（QEMU 跳过）；
 * set 切模式（0=IDLE 呼吸蓝 1=RUNNING 绿 2=HOLD 青 3=ERR 红闪 4=OTA 紫闪）；
 * 呼吸/闪烁状态机由 main 的 10ms 控制节拍调 tick 驱动（颜色变化才刷新总线）。 */
void board_led_init(void);
void board_led_set(int mode);
void board_led_tick_10ms(void);

#ifdef __cplusplus
}
#endif
