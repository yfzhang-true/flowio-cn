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

#include <math.h>
#include <string.h>

#define TICK_MS          50
/* ---- 一阶气动物理 v2（PHYSICS-SPEC，文献标定锚点）----
 * 孔口流 Q = C·√(P_low·ΔP)（Xavier 2022 Eq.5/6，ANSI/(NFPA)T3.21.3 形式）
 * dP/dt = γ·P_abs/V·Q（多变气体定律，γ=1.2）
 * V = V_m + n_open·V_p（端口容积耦合）+ 开阀瞬时等温混合
 * 每元件泄漏系数（TinyML Phase 0 标注数据工厂，SPEC 15） */
#define GAMMA            1.2f
#define P_ATM_KPA        101.325f
#define PUMP_P_MAX_KPA   61.0f     /* 370 规格书正压无单值(60-100 型号相关)，暂用 FlowIO Small 实测死点（thesis Table 2），到货实测后定 */
#define PUMP_P_MIN_KPA   (-58.0f)  /* 370 Mini Vacuum Pump 规格书 ≥-58kPa（DFRobot FIT0801，2026-09-22 修正；原 -38 为 FlowIO 借值） */
#define PUMP_C           9.0e-8f  /* 标定：按 FlowIO 实测充压曲线（2s→19kPa, 4s→35kPa）；370 直驱小容积更快，到货用 calibrate_pump.py 重标 */
#define VENT_C           1.0e-5f  /* 标定：40 kPa → 0 in ~4s/单端口（实验校准） */
#define LEAK_C           1.0e-5f  /* 标定：k=0.2 → 密封 60kPa ≈7 kPa/s */
#define SEAL_LEAK_PER_S  0.01f     /* 基线密封微漏（比例，文献外经验值） */
#define V_MANIFOLD_L     0.005f    /* 汇流管容积 */
#define V_PORT_L         0.002f    /* 单端口通道容积 */
#define SENSOR_SPAN_KPA  100.0f    /* XGZP6897D 量程饱和 */
#define CHOKED_RATIO     1.893f    /* 空气临界压比（音速阻塞） */

static float s_leak[7];            /* 泄漏系数：0-4 端口 / 5 进气 / 6 排气 */
static uint32_t s_prev_ports;      /* 上拍端口阀位图（开阀混合检测） */

static float sq_pos(float v) { return v > 0.f ? v : 0.f; }

static pn_inflate_job_t s_last_job;
static int s_last_cl = 4;   /* PN_CL_IDLE */

PN_TWIN_API int pn_twin_cl_status(void) { return s_last_cl; }

PN_TWIN_API void pn_twin_init(void)
{
    pn_mock_reset();
    pn_cli_set_delay_fn(pn_mock_advance_ms);
    pn_init(pn_mock_hal(), PN_CFG_GENERAL);
    s_last_cl = PN_CL_IDLE;   /* 虚拟断电重启：闭环状态一并归零，不残留旧值 */
    for (int i = 0; i < 7; ++i) s_leak[i] = 0.f;
    s_prev_ports = 0;
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

    /* ---- 一阶气动物理 v2（规律真实，文献锚点标定） ---- */
    float dt  = TICK_MS / 1000.f;
    float p   = pn_mock_sensor_kpa[0];
    uint32_t st = pn_get_state();
    int pump_on  = (int)pn_get_state_of(7);
    int inlet_on = (int)pn_get_state_of(5);
    int vent_on  = (int)pn_get_state_of(6);
    uint32_t ports = st & PN_PORT_MASK_ALL;
    float duty = pn_mock_pump_duty[0] / 255.f;

    /* 开阀瞬时等温混合：汇流管气体与新接通端口通道（大气压）均压 */
    uint32_t new_bits = ports & ~s_prev_ports;
    if (new_bits) {
        int n_new = __builtin_popcount(new_bits);
        int n_old = __builtin_popcount(s_prev_ports);
        float V_old = V_MANIFOLD_L + (float)n_old * V_PORT_L;
        float V_new = V_old + (float)n_new * V_PORT_L;
        float P = p + P_ATM_KPA;
        P = (P * V_old + P_ATM_KPA * (float)n_new * V_PORT_L) / V_new;
        p = P - P_ATM_KPA;
    }
    s_prev_ports = ports;

    float V = V_MANIFOLD_L + (float)__builtin_popcount(ports) * V_PORT_L;
    float P = p + P_ATM_KPA;
    float net_q = 0.f;                            /* L/s，充为正 */

    if (pump_on && inlet_on) {                    /* 充气：孔口形式渐近死点 */
        float PR = PUMP_P_MAX_KPA + P_ATM_KPA;
        net_q += PUMP_C * duty * sq_pos(P * (PR - P));
    } else if (pump_on && vent_on) {              /* 抽真空：对称形式渐近极限 */
        float Pm = PUMP_P_MIN_KPA + P_ATM_KPA;
        net_q -= PUMP_C * duty * sq_pos(P * (P - Pm));
    }
    if (vent_on && !pump_on) {                    /* 被动排气/负压回充（choked 钳位） */
        float d = P - P_ATM_KPA;
        float f = (d > 0.f) ? P_ATM_KPA * d : ((d < 0.f) ? P_ATM_KPA * d : 0.f);
        /* f = P_low·ΔP（带符号），choked 边界：|d|=(R-1)·P_atm */
        float f_choked = P_ATM_KPA * (CHOKED_RATIO - 1.f) * P_ATM_KPA;
        if (f > f_choked) f = f_choked;
        if (f < -f_choked) f = -f_choked;
        net_q -= VENT_C * sqrtf(fabsf(f));
    }
    /* 泄漏（注入）：端口阀关=密封面漏、开=下游管路/执行器漏；进气/排气阀关=密封面漏 */
    {
        float leak_eff = 0.f;
        for (int i = 0; i < 5; ++i)
            leak_eff += s_leak[i];           /* 端口泄漏无论阀位均作用于汇流管节点 */
        if (!inlet_on) leak_eff += s_leak[5] * 0.5f;  /* 进气阀关时半幅（远端通大气） */
        if (!vent_on)  leak_eff += s_leak[6];
        if (leak_eff > 0.f) {
            float d = P - P_ATM_KPA;
            float f = (d > 0.f) ? sqrtf(P_ATM_KPA * d) : ((d < 0.f) ? -sqrtf(P_ATM_KPA * -d) : 0.f);
            net_q -= LEAK_C * leak_eff * f;
        }
    }

    p += GAMMA * P / V * net_q * dt;              /* 多变气体定律压力动力学 */
    if (!ports && !pump_on && !vent_on)           /* 全密封基线微漏（比例） */
        p -= p * SEAL_LEAK_PER_S * dt;
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

PN_TWIN_API void pn_twin_set_leak(uint8_t idx, float k)
{
    if (idx < 7) {
        if (k < 0.f) k = 0.f;
        if (k > 1.f) k = 1.f;
        s_leak[idx] = k;
    }
}

PN_TWIN_API float pn_twin_leak(uint8_t idx) { return idx < 7 ? s_leak[idx] : 0.f; }
