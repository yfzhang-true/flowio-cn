/**
 * pn_hal_esp32/ble_twin.h — BLE GATT 双胎服务（S5，契约 firmware/twin/BLE.md）
 *
 * 四服务：DeviceInfo(0x180A) / Command(0001) / Telemetry(0004) / Config(0007)。
 * UUID 基址与后缀宏同名对应 BLE.md §2 表；cmd write 经字节队列转 pn_cmd_feed()
 * （与串口同一 CLI 解析路径）。
 * QEMU / CONFIG_BT_ENABLED 关闭时全部接口安全空转（stub）。
 */
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* DeviceInfo 读值（BLE.md §3.1；fw_version 改版同步改文档） */
#define PN_FW_VERSION   "0.5.0-s5"
#define PN_BOARD_REV    "P1-N16R8"
#define PN_BLE_ADV_PREFIX "FLOWIO-P1-"     /* 广播名 = 前缀 + MAC 末 2 字节 %04X */

/* cmd 单次投递上限（= MTU−3 上界，行聚合由 pn_cmd_feed 兜底） */
#define PN_BLE_CMD_MAX  253

/* 初始化 NimBLE + 四服务 + 广播（app_main 一次性调用）。
 * QEMU 或编译期未开 BT 时打印跳过原因并安全返回。 */
void ble_twin_init(void);

/* 挂 10ms 控制节拍（control_task）：每 10 拍组 20B state 帧，
 * notify_en≠0 且 CCCD 已订阅才 notify。未初始化时空转。 */
void ble_twin_tick_10ms(void);

/* Config 服务 pwm_params 的 RAM 镜像读口（control_task 的 pn_optimize_power 用；
 * BT 关闭/QEMU 返回编译期默认值，语义不变）。布局见 BLE.md §4.3。 */
uint8_t  ble_twin_hold_duty(void);
uint16_t ble_twin_hold_delay_ms(void);

/* cmd_transport 统一分发点（S5，实现在 firmware/main/main.c）：
 * 字节流聚合（ASCII 行 / 0xA5 二进制帧）→ CLI 解析。BLE cmd 特征的
 * write 回调出队后调它；串口 fgets 同样喂它——两个入口同一函数。 */
extern void pn_cmd_feed(const uint8_t *buf, size_t len);

#ifdef __cplusplus
}
#endif
