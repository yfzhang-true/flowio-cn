/**
 * pn_core/ble_frame.c — BLE 遥测帧编解码实现（纯逻辑，无平台依赖）
 */
#include "pn_core/ble_frame.h"

#include <string.h>

static void put_u16_le(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)(v >> 8);
}

static uint16_t get_u16_le(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

int ble_state_pack(uint8_t out[PN_BLE_STATE_LEN], uint16_t state_word,
                   const int16_t pa10[PN_BLE_PRESS_SLOTS], uint16_t tick)
{
    if (!out || !pa10) return -1;
    put_u16_le(out + 0, state_word);
    for (int i = 0; i < PN_BLE_PRESS_SLOTS; ++i)
        put_u16_le(out + 2 + 2 * i, (uint16_t)pa10[i]);
    put_u16_le(out + 12, tick);
    memset(out + 14, 0, 6);          /* 保留字节恒 0（契约 §4.2） */
    return PN_BLE_STATE_LEN;
}

int ble_state_unpack(const uint8_t *in, size_t len, uint16_t *state_word,
                     int16_t pa10[PN_BLE_PRESS_SLOTS], uint16_t *tick)
{
    if (!in || len < PN_BLE_STATE_LEN) return -1;
    for (int i = 14; i < PN_BLE_STATE_LEN; ++i)
        if (in[i] != 0) return -1;   /* 保留字节非 0 = 非 contract 帧 */

    if (state_word) *state_word = get_u16_le(in + 0);
    if (pa10) {
        for (int i = 0; i < PN_BLE_PRESS_SLOTS; ++i)
            pa10[i] = (int16_t)get_u16_le(in + 2 + 2 * i);
    }
    if (tick) *tick = get_u16_le(in + 12);
    return 0;
}
