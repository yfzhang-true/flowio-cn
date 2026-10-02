/**
 * pn_core/ble_frame.h — BLE 遥测帧编解码（纯逻辑，主机可测）
 *
 * 契约真源：firmware/twin/BLE.md §4.2。
 * 20B 帧全小端：[0:2] u16 状态字 | [2:12] 5×i16 压力 kPa×10 |
 *               [12:14] u16 tick(ms/100) | [14:20] 保留恒 0。
 * 约定：传感器无效值 0x8000（物理量程 ±100kPa×10=±1000，不冲突）；
 *       slot2-4 为 P1 预留（P0 双传感器），打包不做内容断言，由填充方保证。
 */
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define PN_BLE_STATE_LEN    20
#define PN_BLE_PRESS_SLOTS  5
#define PN_BLE_PRESS_INVALID ((int16_t)0x8000)   /* 传感器读失败哨兵 */

/* 打包 20B 遥测帧；返回写入字节数（恒 PN_BLE_STATE_LEN=20）。 */
int ble_state_pack(uint8_t out[PN_BLE_STATE_LEN], uint16_t state_word,
                   const int16_t pa10[PN_BLE_PRESS_SLOTS], uint16_t tick);

/* 解包校验：len<20 / in==NULL / 保留字节非 0 → -1；成功回填并返回 0。
 * 出参可 NULL（仅校验用途）。 */
int ble_state_unpack(const uint8_t *in, size_t len, uint16_t *state_word,
                     int16_t pa10[PN_BLE_PRESS_SLOTS], uint16_t *tick);

#ifdef __cplusplus
}
#endif
