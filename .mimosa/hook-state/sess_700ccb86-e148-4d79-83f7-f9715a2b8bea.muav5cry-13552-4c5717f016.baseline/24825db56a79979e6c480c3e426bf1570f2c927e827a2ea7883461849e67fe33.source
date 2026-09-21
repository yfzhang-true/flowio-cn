/**
 * mock_hal.h — 主机测试用 HAL 替身
 * 记录所有驱动调用（供断言时序/参数），提供可编程的假时钟与假传感器。
 */
#pragma once

#include "pn_core/hal_if.h"

typedef struct {
    uint8_t  kind;    /* 0=阀 1=泵 */
    uint8_t  idx;
    uint8_t  duty;
    uint32_t t;
} pn_mock_ev_t;

#define PN_MOCK_LOG_CAP 256

extern pn_mock_ev_t pn_mock_log[];
extern int          pn_mock_log_len;
extern uint8_t      pn_mock_valve_duty[PN_VALVE_COUNT];
extern uint8_t      pn_mock_pump_duty[PN_PUMP_COUNT];
extern uint32_t     pn_mock_time;
extern float        pn_mock_sensor_kpa[PN_SENSOR_COUNT];
extern int          pn_mock_sensor_fail[PN_SENSOR_COUNT];

void pn_mock_reset(void);
void pn_mock_advance_ms(uint32_t ms);
const pn_hal_if_t *pn_mock_hal(void);

/* 在调用日志里找"该阀最后一次写"的占空比；找不到返回 -1 */
int pn_mock_last_valve_write(uint8_t valve_idx);
