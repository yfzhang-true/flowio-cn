/** mock_hal.c */
#include "mock_hal.h"
#include <string.h>

pn_mock_ev_t pn_mock_log[PN_MOCK_LOG_CAP];
int          pn_mock_log_len;
uint8_t      pn_mock_valve_duty[PN_VALVE_COUNT];
uint8_t      pn_mock_pump_duty[PN_PUMP_COUNT];
uint32_t     pn_mock_time;
float        pn_mock_sensor_kpa[PN_SENSOR_COUNT];
int          pn_mock_sensor_fail[PN_SENSOR_COUNT];

void pn_mock_reset(void)
{
    memset(pn_mock_log, 0, sizeof(pn_mock_log));
    pn_mock_log_len = 0;
    memset(pn_mock_valve_duty, 0, sizeof(pn_mock_valve_duty));
    memset(pn_mock_pump_duty, 0, sizeof(pn_mock_pump_duty));
    pn_mock_time = 1000;   /* 从非零时刻开始，检验时间运算无符号回绕 */
    for (int i = 0; i < PN_SENSOR_COUNT; ++i) { pn_mock_sensor_kpa[i] = 0.f; pn_mock_sensor_fail[i] = 0; }
}

void pn_mock_advance_ms(uint32_t ms) { pn_mock_time += ms; }

static void mock_valve_write(uint8_t idx, uint8_t duty)
{
    if (pn_mock_log_len < PN_MOCK_LOG_CAP) {
        pn_mock_log[pn_mock_log_len++] = (pn_mock_ev_t){ 0, idx, duty, pn_mock_time };
    }
    pn_mock_valve_duty[idx] = duty;
}

static void mock_pump_write(uint8_t idx, uint8_t duty)
{
    if (pn_mock_log_len < PN_MOCK_LOG_CAP) {
        pn_mock_log[pn_mock_log_len++] = (pn_mock_ev_t){ 1, idx, duty, pn_mock_time };
    }
    pn_mock_pump_duty[idx] = duty;
}

static int mock_sensor_read(uint8_t idx, float *kpa)
{
    if (idx >= PN_SENSOR_COUNT || pn_mock_sensor_fail[idx]) return -1;
    *kpa = pn_mock_sensor_kpa[idx];
    return 0;
}

static uint32_t mock_now(void) { return pn_mock_time; }

static const pn_hal_if_t s_mock = {
    .valve_write = mock_valve_write,
    .pump_write  = mock_pump_write,
    .sensor_read = mock_sensor_read,
    .now_ms      = mock_now,
};

const pn_hal_if_t *pn_mock_hal(void) { return &s_mock; }

int pn_mock_last_valve_write(uint8_t valve_idx)
{
    for (int i = pn_mock_log_len - 1; i >= 0; --i) {
        if (pn_mock_log[i].kind == 0 && pn_mock_log[i].idx == valve_idx)
            return pn_mock_log[i].duty;
    }
    return -1;
}
