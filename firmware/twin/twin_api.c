/**
 * twin_api.c — 数字孪生实现
 *
 * 逻辑层 = pn_core（与目标机固件同一份代码）；
 * 物理仿真 = 一阶气动模型（不硬编码轨迹，规律与真实气动一致）：
 *   充压   dp/dt = K·duty·(1 − p/Pmax)   泵 P-Q 一阶近似，渐近死点压力
 *   抽真空 dp/dt = −K·duty·(1 − p/Pmin)  对称模型，渐近极限真空
 *   被动排气 p(t) 按时间常数指数衰减（压差驱动，负压自然回充）
 *   密封微漏 漏率 ∝ 压差（比例系数）
 *   传感器按 XGZP6897D 量程 ±100kPa 饱和钳位（含注入值）
 * 标定参数为 P0 占位值，到货实测后修正（见下宏注释）。
 * ⚠ 已知固件设计问题：超压保护阈值 120kPa 高于传感器量程上限 100kPa，
 *   真机上该保护永远无法触发（盲区）——孪生如实建模此行为，待用户决策阈值。
 */
#include "twin_api.h"

#include "../components/pn_core/include/pn_core/actions.h"
#include "../components/pn_core/include/pn_core/closedloop.h"
#include "../components/pn_core/include/pn_core/cli.h"
#include "../tests/mock_hal.h"

#include <string.h>

#define TICK_MS          50
/* ---- 一阶气动物理标定参数（占位值，P0 到货实测后修正） ---- */
#define PUMP_P_MAX_KPA   65.0f    /* 泵正压死点（P0 小隔膜泵规格 50–70，取中） */
#define PUMP_P_MIN_KPA   (-45.0f) /* 泵极限真空（同泵规格量级，待标定） */
#define PUMP_RATE_KPA_S  30.0f    /* duty=255 时零表压充压速率 kPa/s */
#define VENT_TAU_S       1.6f     /* 被动排气时间常数（阀+管路流阻 / 容积） */
#define LEAK_RATE_PER_S  0.01f    /* 全密封比例微漏系数 1/s */
#define SENSOR_SPAN_KPA  100.0f   /* XGZP6897D 量程 ±100kPa（饱和即钳位） */

static pn_inflate_job_t s_last_job;
static int s_last_cl = 4;   /* PN_CL_IDLE */

PN_TWIN_API int pn_twin_cl_status(void) { return s_last_cl; }

PN_TWIN_API void pn_twin_init(void)
{
    pn_mock_reset();
    pn_cli_set_delay_fn(pn_mock_advance_ms);
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);
    s_last_cl = PN_CL_IDLE;   /* 虚拟断电重启：闭环状态一并归零，不残留旧值 */
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
    /* 传感器量程饱和：注入超出 ±100 的值按真实传感器行为钳位 */
    if (kpa > SENSOR_SPAN_KPA) kpa = SENSOR_SPAN_KPA;
    if (kpa < -SENSOR_SPAN_KPA) kpa = -SENSOR_SPAN_KPA;
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

    /* ---- 一阶气动物理（规律真实，参数待标定） ---- */
    float dt  = TICK_MS / 1000.f;
    float p   = pn_mock_sensor_kpa[0];
    uint32_t st = pn_get_state();
    int pump_on  = (int)pn_get_state_of(7);
    int inlet_on = (int)pn_get_state_of(5);
    int vent_on  = (int)pn_get_state_of(6);
    int port_open = (int)(st & PN_PORT_MASK_ALL);
    float duty = pn_mock_pump_duty[0] / 255.f;

    if (pump_on && inlet_on) {                    /* 进气路导通：泵充压，渐近死点 */
        float head = 1.f - p / PUMP_P_MAX_KPA;
        if (head > 0.f) p += PUMP_RATE_KPA_S * duty * head * dt;
    } else if (pump_on && vent_on) {              /* 排气路+泵：抽真空，渐近极限 */
        float head = 1.f - p / PUMP_P_MIN_KPA;
        if (head > 0.f) p -= PUMP_RATE_KPA_S * duty * head * dt;
    }
    if (vent_on && !pump_on)                      /* 排气阀通大气：指数泄压/负压回充 */
        p -= p * dt / VENT_TAU_S;
    if (!port_open)                               /* 全阀关闭：比例微漏（朝大气方向） */
        p -= p * LEAK_RATE_PER_S * dt;
    if (p > SENSOR_SPAN_KPA) p = SENSOR_SPAN_KPA;
    if (p < -SENSOR_SPAN_KPA) p = -SENSOR_SPAN_KPA;
    pn_mock_sensor_kpa[0] = p;

    /* ---- 控制节拍（与真机 10ms 任务同构，此处 50ms） ---- */
    pn_cl_status_t cl = pn_inflate_to_tick();
    s_last_cl = (int)cl;
    pn_optimize_power(PN_HOLD_DEFAULT_DUTY, PN_HOLD_DEFAULT_DELAY_MS);
    pn_check_overpressure(120.f);
    return (int)cl;
}
