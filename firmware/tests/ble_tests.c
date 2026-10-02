/** ble_tests.c — BLE 遥测帧编解码单元测试（S5，契约 twin/BLE.md §4.2）
 *
 * 覆盖：pack→unpack 往返 / 负压力 -533 无损（抽气工况）/ tick 与状态字边界 /
 *       短缓冲拒绝 / 保留字节污染拒绝 / NULL 安全
 */
#include "test_util.h"
#include "pn_core/ble_frame.h"

/* ---------- pack→unpack 往返：全字段无损 ---------- */
static void t_pack_roundtrip(void)
{
    uint8_t f[PN_BLE_STATE_LEN];
    uint16_t sw = 0x0221;                       /* 端口1+进气+SENSOR_OK（types.h 位定义） */
    int16_t pa[PN_BLE_PRESS_SLOTS] = { 123, -533, 0, 1000, -1000 };
    uint16_t tick = 1234;
    CHECK(ble_state_pack(f, sw, pa, tick) == PN_BLE_STATE_LEN);

    uint16_t sw2 = 0; int16_t pa2[PN_BLE_PRESS_SLOTS] = { 0 }; uint16_t tick2 = 0;
    CHECK(ble_state_unpack(f, PN_BLE_STATE_LEN, &sw2, pa2, &tick2) == 0);
    CHECK(sw2 == 0x0221);
    for (int i = 0; i < PN_BLE_PRESS_SLOTS; ++i) CHECK(pa2[i] == pa[i]);
    CHECK(tick2 == 1234);
    /* 保留字节确为 0（契约：GUI 端 unpack 的合法性前提） */
    for (int i = 14; i < 20; ++i) CHECK(f[i] == 0);
}

/* ---------- 负压力：-533（-53.3kPa）i16 小端无损 ---------- */
static void t_negative_pressure(void)
{
    uint8_t f[PN_BLE_STATE_LEN];
    int16_t pa[PN_BLE_PRESS_SLOTS] = { -533, -533, -533, -533, -533 };
    CHECK(ble_state_pack(f, 0xFFFF, pa, 0xFFFF) == PN_BLE_STATE_LEN);
    /* 0xFDEB 小端 = EB FD（契约 §4.2 示例字节） */
    CHECK(f[2] == 0xEB && f[3] == 0xFD);
    int16_t pa2[PN_BLE_PRESS_SLOTS] = { 0 };
    CHECK(ble_state_unpack(f, sizeof(f), NULL, pa2, NULL) == 0);
    for (int i = 0; i < PN_BLE_PRESS_SLOTS; ++i) CHECK(pa2[i] == -533);
}

/* ---------- tick/状态字边界：0 与 0xFFFF ---------- */
static void t_tick_boundaries(void)
{
    uint8_t f[PN_BLE_STATE_LEN];
    int16_t pa[PN_BLE_PRESS_SLOTS] = { 0, 0, 0, 0, 0 };
    int16_t pa2[PN_BLE_PRESS_SLOTS] = { 0 };
    uint16_t sw = 9, tk = 9;

    CHECK(ble_state_pack(f, 0x0000, pa, 0x0000) == PN_BLE_STATE_LEN);
    CHECK(f[0] == 0 && f[1] == 0 && f[12] == 0 && f[13] == 0);
    CHECK(ble_state_unpack(f, sizeof(f), &sw, pa2, &tk) == 0);
    CHECK(sw == 0 && tk == 0);

    CHECK(ble_state_pack(f, 0xFFFF, pa, 0xFFFF) == PN_BLE_STATE_LEN);
    CHECK(f[0] == 0xFF && f[1] == 0xFF && f[12] == 0xFF && f[13] == 0xFF);
    CHECK(ble_state_unpack(f, sizeof(f), &sw, pa2, &tk) == 0);
    CHECK(sw == 0xFFFF && tk == 0xFFFF);        /* 100ms 序号回绕语义 */
}

/* ---------- 拒绝路径：短缓冲 / 保留字节污染 / NULL ---------- */
static void t_invalid_input_rejected(void)
{
    uint8_t f[PN_BLE_STATE_LEN];
    int16_t pa[PN_BLE_PRESS_SLOTS] = { 1, 2, 3, 4, 5 };
    CHECK(ble_state_pack(f, 0x1234, pa, 42) == PN_BLE_STATE_LEN);

    CHECK(ble_state_unpack(f, 19, NULL, NULL, NULL) == -1);   /* 短 1 字节 */
    CHECK(ble_state_unpack(f, 0, NULL, NULL, NULL) == -1);
    CHECK(ble_state_unpack(NULL, PN_BLE_STATE_LEN, NULL, NULL, NULL) == -1);

    f[14] = 0x01;                                             /* 保留字节污染 */
    CHECK(ble_state_unpack(f, sizeof(f), NULL, NULL, NULL) == -1);
    f[14] = 0x00; f[19] = 0xAA;
    CHECK(ble_state_unpack(f, sizeof(f), NULL, NULL, NULL) == -1);
    f[19] = 0x00;
    CHECK(ble_state_unpack(f, sizeof(f), NULL, NULL, NULL) == 0);   /* 复原 */

    CHECK(ble_state_pack(NULL, 0, pa, 0) == -1);              /* pack NULL 拒绝 */
    CHECK(ble_state_pack(f, 0, NULL, 0) == -1);
}

void test_ble_all(void)
{
    RUN_TEST(t_pack_roundtrip);
    RUN_TEST(t_negative_pressure);
    RUN_TEST(t_tick_boundaries);
    RUN_TEST(t_invalid_input_rejected);
}
