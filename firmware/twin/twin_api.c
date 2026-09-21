/**
 * twin_api.c — 数字孪生实现
 *
 * 逻辑层 = pn_core（与目标机固件同一份代码）；
 * 物理仿真 = 简化气动模型（充气升压/排气降压/保压微漏/130kPa 封顶），
 * 让 UI 上的压力表"活"起来——这正是孪生的意义：不等实物也能看到控制效果。
 */
#include "twin_api.h"

#include "../components/pn_core/include/pn_core/actions.h"
#include "../components/pn_core/include/pn_core/closedloop.h"
#include "../components/pn_core/include/pn_core/cli.h"
#include "../tests/mock_hal.h"

#include <string.h>

#define TICK_MS          50
#define SIM_RISE_KPA     1.5f     /* 泵充气：每 tick 升压（=30kPa/s） */
#define SIM_FALL_KPA     1.2f     /* 排气：每 tick 降压（=24kPa/s） */
#define SIM_LEAK_KPA     0.02f    /* 保压微漏 */
#define SIM_CAP_KPA      130.0f

static pn_inflate_job_t s_last_job;
static int s_last_cl = 4;   /* PN_CL_IDLE */

PN_TWIN_API int pn_twin_cl_status(void) { return s_last_cl; }

PN_TWIN_API void pn_twin_init(void)
{
    pn_mock_reset();
    pn_cli_set_delay_fn(pn_mock_advance_ms);
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);
}

PN_TWIN_API uint32_t pn_twin_state(void) { return pn_get_state(); }

PN_TWIN_API float pn_twin_sensor(uint8_t idx)
{
    float p = -1.f;
    pn_read_pressure(idx, &p);
    return p;
}

PN_TWIN_API void pn_twin_set_sensor(uint8_t idx, float kpa)
{
    if (idx < PN_SENSOR_COUNT) pn_mock_sensor_kpa[idx] = kpa;
}

PN_TWIN_API void pn_twin_command(const char *line)
{
    char buf[64];
    strncpy(buf, line ? line : "", sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = 0;
    pn_cli_process_line(buf);
}

PN_TWIN_API uint8_t pn_twin_valve_duty(uint8_t idx)
{
    return idx < PN_VALVE_COUNT ? pn_mock_valve_duty[idx] : 0;
}

PN_TWIN_API uint8_t pn_twin_pump_duty(void) { return pn_mock_pump_duty[0]; }

PN_TWIN_API void pn_twin_advance(uint32_t ms) { pn_mock_advance_ms(ms); }

PN_TWIN_API int pn_twin_tick(void)
{
    pn_mock_advance_ms(TICK_MS);

    /* ---- 简化气动物理：让虚拟世界对操作有反应 ---- */
    float p = pn_mock_sensor_kpa[0];
    uint32_t st   = pn_get_state();
    int pump_on   = (int)pn_get_state_of(7);
    int inlet_on  = (int)pn_get_state_of(5);
    int vent_on   = (int)pn_get_state_of(6);
    int port_open = (int)(st & PN_PORT_MASK_ALL);

    if (pump_on && inlet_on) {
        p += SIM_RISE_KPA;                       /* 泵充气路径导通 */
        if (vent_on) p -= 2.f * SIM_RISE_KPA;    /* 排气位同时开 → 泵抽大气，压力不升 */
    } else if (vent_on && !pump_on) {
        p -= SIM_FALL_KPA;                       /* 被动排放 */
    }
    if (!port_open && p > 0) p -= SIM_LEAK_KPA;  /* 保压微漏 */
    if (p < 0) p = 0;
    if (p > SIM_CAP_KPA) p = SIM_CAP_KPA;
    pn_mock_sensor_kpa[0] = p;

    /* ---- 控制节拍（与真机 10ms 任务同构，此处 50ms） ---- */
    pn_cl_status_t cl = pn_inflate_to_tick();
    s_last_cl = (int)cl;
    pn_optimize_power(PN_HOLD_DEFAULT_DUTY, PN_HOLD_DEFAULT_DELAY_MS);
    pn_check_overpressure(120.f);
    return (int)cl;
}
