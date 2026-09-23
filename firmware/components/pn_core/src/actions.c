/**
 * pn_core/actions.c — 气动动作层实现
 *
 * 全部为功能性自研实现：逻辑框架参考 study-notes/02 的功能性笔记，
 * 代码逐行原创，不含 FlowIO 任何源码。
 */
#include "pn_core/actions.h"
#include "pn_core/closedloop.h"

#include <string.h>

/* ---- 内部状态 ---- */
static const pn_hal_if_t *s_hal;
static pn_config_t        s_config;
static uint32_t           s_state;          /* 状态字（仅低 16 位有效） */
static pn_err_t           s_last_err;
static uint8_t            s_hold_duty       = PN_HOLD_DEFAULT_DUTY;
static uint16_t           s_hold_threshold  = PN_HOLD_DEFAULT_DELAY_MS;
static bool               s_optimized[PN_VALVE_COUNT];
static uint32_t           s_open_since[PN_VALVE_COUNT];

/* 闭环模块需要感知动作层状态，反之闭环占用标志在 closedloop.c 内部 */

/* ---- 内部工具 ---- */
static void valve_drive(uint8_t idx, uint8_t duty)
{
    s_hal->valve_write(idx, duty);
    if (duty > 0) {
        s_state |= (1u << idx);
        s_open_since[idx] = s_hal->now_ms();
        s_optimized[idx]  = false;
    } else {
        s_state &= ~(1u << idx);
        s_open_since[idx] = 0;
        s_optimized[idx]  = false;
    }
}

static bool ports_valid(uint8_t ports) { return (ports & PN_PORT_MASK_ALL) != 0; }

/* ---- 初始化 ---- */
void pn_init(const pn_hal_if_t *hal, pn_config_t cfg)
{
    s_hal     = hal;
    s_config  = cfg;
    s_state   = 0;
    s_last_err = PN_OK;
    memset(s_open_since, 0, sizeof(s_open_since));
    memset(s_optimized, 0, sizeof(s_optimized));
    for (uint8_t i = 0; i < PN_VALVE_COUNT; ++i) s_hal->valve_write(i, 0);
    for (uint8_t i = 0; i < PN_PUMP_COUNT; ++i)  s_hal->pump_write(i, 0);
    pn_cl_reset();
}

void pn_set_config(pn_config_t cfg) { s_config = cfg; }
pn_config_t pn_get_config(void)     { return s_config; }
uint32_t pn_get_state(void)         { return s_state; }
bool pn_get_state_of(uint8_t bit)   { return (s_state >> bit) & 1u; }
pn_err_t pn_last_error(void)        { return s_last_err; }

/* ---- 端口阀三胞胎 ---- */
void pn_ports_set(uint8_t ports)
{
    for (uint8_t i = 0; i < PN_PORT_COUNT; ++i)
        valve_drive(PN_VALVE_PORT1 + i, ((ports >> i) & 1u) ? 255 : 0);
    if (ports) s_hal->now_ms(); /* 触发时间基准（便于 mock 时序） */
}

void pn_ports_open(uint8_t ports)
{
    for (uint8_t i = 0; i < PN_PORT_COUNT; ++i)
        if ((ports >> i) & 1u) valve_drive(PN_VALVE_PORT1 + i, 255);
    s_hal->now_ms();
}

void pn_ports_close(uint8_t ports)
{
    for (uint8_t i = 0; i < PN_PORT_COUNT; ++i)
        if ((ports >> i) & 1u) valve_drive(PN_VALVE_PORT1 + i, 0);
    s_hal->now_ms();
}

/* ---- 方向阀 ---- */
void pn_inlet_open(void)  { valve_drive(PN_VALVE_INLET, 255); }
void pn_inlet_close(void) { valve_drive(PN_VALVE_INLET, 0);   }
void pn_vent_open(void)   { valve_drive(PN_VALVE_VENT, 255);  }
void pn_vent_close(void)  { valve_drive(PN_VALVE_VENT, 0);    }

/* ---- 泵 ---- */
void pn_pump_start(uint8_t duty)
{
    if (duty == 0) { pn_pump_stop(); return; }
    s_hal->pump_write(0, duty);
    s_state |= PN_SW_PUMP1;
}
void pn_pump_stop(void)
{
    s_hal->pump_write(0, 0);
    s_state &= ~PN_SW_PUMP1;
}

/* ---- 组合动作 ---- */
pn_err_t pn_start_inflation(uint8_t ports, uint8_t pwm)
{
    if (!ports_valid(ports)) { s_last_err = PN_ERR_PARAM; return PN_ERR_PARAM; }
    if (s_config == PN_CFG_VACUUM) { s_last_err = PN_ERR_UNSUPPORTED; return PN_ERR_UNSUPPORTED; }
    if (pn_cl_busy()) { s_last_err = PN_ERR_BUSY; return PN_ERR_BUSY; }

    pn_stop_action(ports);           /* 干净状态起步 */
    pn_inlet_open();                 /* 大气→泵入口 */
    pn_ports_open(ports);
    pn_pump_start(pwm ? pwm : 255);
    s_last_err = PN_OK;
    return PN_OK;
}

pn_err_t pn_start_vacuum(uint8_t ports, uint8_t pwm)
{
    if (!ports_valid(ports)) { s_last_err = PN_ERR_PARAM; return PN_ERR_PARAM; }
    if (s_config == PN_CFG_INFLATION) { s_last_err = PN_ERR_UNSUPPORTED; return PN_ERR_UNSUPPORTED; }
    if (pn_cl_busy()) { s_last_err = PN_ERR_BUSY; return PN_ERR_BUSY; }

    pn_stop_action(ports);
    pn_vent_open();                  /* 370 泵吸/充同侧：负压路径经排气位对 port 侧抽取 */
    pn_ports_open(ports);
    pn_pump_start(pwm ? pwm : 255);
    s_last_err = PN_OK;
    return PN_OK;
}

pn_err_t pn_start_release(uint8_t ports)
{
    if (!ports_valid(ports)) { s_last_err = PN_ERR_PARAM; return PN_ERR_PARAM; }
    if (pn_cl_busy()) { s_last_err = PN_ERR_BUSY; return PN_ERR_BUSY; }

    pn_pump_stop();
    pn_inlet_close();                /* 释放时进气路径必须断开 */
    pn_ports_open(ports);            /* 打开端口，气体经单向路径排向排气位 */
    pn_vent_open();                  /* 排气位通大气（释放完全被动） */
    s_last_err = PN_OK;
    return PN_OK;
}

pn_err_t pn_hold_open(uint8_t ports)
{
    if (!ports_valid(ports)) { s_last_err = PN_ERR_PARAM; return PN_ERR_PARAM; }

    /* 诊断保压：泵侧密封（进气/排气全关+泵停），端口阀保持通——
     * 汇流管+下游执行器连成单一密封容积，端口侧泄漏可被汇流管传感器观测。
     * 与 pn_stop_action 的区别：stop 把端口也关了（隔离保压，端口侧变化不可见）。 */
    pn_pump_stop();
    pn_inlet_close();
    pn_vent_close();
    pn_ports_open(ports);
    s_last_err = PN_OK;
    return PN_OK;
}

pn_err_t pn_stop_action(uint8_t ports)
{
    pn_inlet_close();
    pn_vent_close();
    pn_ports_close(ports & PN_PORT_MASK_ALL);
    pn_pump_stop();
    s_last_err = PN_OK;
    return PN_OK;
}

/* ---- 阀保持节能 ---- */
void pn_optimize_power(uint8_t hold_duty, uint16_t threshold_ms)
{
    s_hold_duty      = hold_duty;
    s_hold_threshold = threshold_ms;
    uint32_t now = s_hal->now_ms();
    for (uint8_t i = 0; i < PN_VALVE_COUNT; ++i) {
        if (s_open_since[i] == 0 || s_optimized[i]) continue;
        if (now - s_open_since[i] >= threshold_ms) {
            s_hal->valve_write(i, hold_duty);
            s_optimized[i] = true;
        }
    }
}

uint32_t pn_valve_open_ms(uint8_t valve_idx)
{
    if (valve_idx >= PN_VALVE_COUNT || s_open_since[valve_idx] == 0) return 0;
    return s_hal->now_ms() - s_open_since[valve_idx];
}

/* ---- 传感 ---- */
pn_err_t pn_read_pressure(uint8_t sensor_idx, float *kpa)
{
    if (!kpa || sensor_idx >= PN_SENSOR_COUNT) { s_last_err = PN_ERR_PARAM; return PN_ERR_PARAM; }
    if (s_hal->sensor_read(sensor_idx, kpa) != 0) {
        s_state &= ~PN_SW_SENSOR_OK;
        s_state |= PN_SW_ERROR;
        s_last_err = PN_ERR_SENSOR;
        return PN_ERR_SENSOR;
    }
    s_state |= PN_SW_SENSOR_OK;
    s_last_err = PN_OK;
    return PN_OK;
}

/* ---- 超压保护（硬规则） ---- */
pn_err_t pn_check_overpressure(float limit_kpa)
{
    for (uint8_t i = 0; i < PN_SENSOR_COUNT; ++i) {
        float p;
        if (s_hal->sensor_read(i, &p) != 0) continue;   /* 失联传感器由 read 的错误路径处理 */
        if (p > limit_kpa) {
            pn_stop_action(PN_PORT_MASK_ALL);           /* 全关 = 安全态 */
            s_state |= PN_SW_ERROR;
            s_last_err = PN_ERR_TIMEOUT;
            return PN_ERR_TIMEOUT;                      /* 调用方转译为超压事件 */
        }
    }
    return PN_OK;
}
