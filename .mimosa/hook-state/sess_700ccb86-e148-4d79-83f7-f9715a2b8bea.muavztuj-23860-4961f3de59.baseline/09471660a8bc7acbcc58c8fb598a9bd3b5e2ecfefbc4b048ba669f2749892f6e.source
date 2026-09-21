/**
 * pn_core/closedloop.c — 非阻塞压力闭环状态机实现
 */
#include "pn_core/closedloop.h"

typedef enum { ST_IDLE, ST_RUNNING } cl_state_t;

static cl_state_t    s_st        = ST_IDLE;
static pn_inflate_job_t s_job;
static bool          s_completed;    /* 完成闩锁：完成后需 reset 才能再启动 */

bool pn_cl_busy(void) { return s_st == ST_RUNNING; }

void pn_cl_reset(void)
{
    s_st        = ST_IDLE;
    s_completed = false;
    s_job.elapsed_ms = 0;
}

pn_err_t pn_inflate_to_start(uint8_t ports, float target_kpa,
                             uint8_t sensor_idx, uint8_t pwm, uint32_t timeout_ms)
{
    if (!(ports & PN_PORT_MASK_ALL)) return PN_ERR_PARAM;
    if (s_completed || s_st == ST_RUNNING) return PN_ERR_BUSY;
    if (sensor_idx >= PN_SENSOR_COUNT)     return PN_ERR_PARAM;

    s_job.ports      = ports & PN_PORT_MASK_ALL;
    s_job.target_kpa = target_kpa;
    s_job.sensor_idx = sensor_idx;
    s_job.pwm        = pwm;
    s_job.timeout_ms = timeout_ms;
    s_job.elapsed_ms = 0;

    /* 若目标端口已在充气（状态字匹配），沿用当前动作不重启——FlowIO inflateP 同款语义 */
    if (!pn_get_state_of(5 /*INLET*/) || (uint8_t)(pn_get_state() & PN_PORT_MASK_ALL) != s_job.ports) {
        pn_err_t e = pn_start_inflation(s_job.ports, s_job.pwm);
        if (e != PN_OK) return e;
    }
    s_st = ST_RUNNING;
    return PN_OK;
}

pn_cl_status_t pn_inflate_to_tick(void)
{
    if (s_st != ST_RUNNING) return s_completed ? PN_CL_DONE : PN_CL_IDLE;

    float p;
    if (pn_read_pressure(s_job.sensor_idx, &p) != PN_OK) {
        pn_stop_action(s_job.ports);
        s_st = ST_IDLE;
        s_completed = true;
        return PN_CL_ERR;
    }
    s_job.reached_kpa = p;

    if (p >= s_job.target_kpa) {
        /* 关键顺序：先取进气阀开启时长，再停止（停止会清时间表） */
        s_job.elapsed_ms = pn_valve_open_ms(PN_VALVE_INLET);
        pn_stop_action(s_job.ports);
        s_st        = ST_IDLE;
        s_completed = true;
        return PN_CL_DONE;
    }

    if (s_job.timeout_ms && pn_valve_open_ms(PN_VALVE_INLET) >= s_job.timeout_ms) {
        pn_stop_action(s_job.ports);
        s_st        = ST_IDLE;
        s_completed = true;
        return PN_CL_TIMEOUT;
    }

    return PN_CL_RUNNING;   /* 节能由主循环周期调用 pn_optimize_power */
}

void pn_inflate_to_get_job(pn_inflate_job_t *out)
{
    if (out) *out = s_job;
}
