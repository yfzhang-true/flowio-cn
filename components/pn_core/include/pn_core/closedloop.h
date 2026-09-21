/**
 * pn_core/closedloop.h — 非阻塞压力闭环状态机
 *
 * 写法范式继承笔记 02 第 8 节的三要素（框架无关的工程经验，实现为原创）：
 *  1. 幂等：完成后变空操作，需显式 reset 才能再次启动；
 *  2. 归属判断：状态字与目标端口比对，防止并发调用打架；
 *  3. 完成时返回耗时（先取开始时间再停止——停止会清时间表）。
 */
#pragma once

#include "pn_core/actions.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint8_t  ports;        /* 端口位掩码 */
    float    target_kpa;   /* 目标压力 */
    uint8_t  sensor_idx;   /* 用的哪只传感器 */
    uint8_t  pwm;          /* 泵占空比 */
    uint32_t timeout_ms;   /* 超时（0=无限） */
    uint32_t elapsed_ms;   /* 完成后：总耗时 */
    float    reached_kpa;  /* 完成时压力 */
} pn_inflate_job_t;

/* 启动一次"充气至目标压力"任务。返回 PN_OK=已启动；PN_ERR_BUSY=已有任务 */
pn_err_t pn_inflate_to_start(uint8_t ports, float target_kpa,
                             uint8_t sensor_idx, uint8_t pwm, uint32_t timeout_ms);

/* 周期性调用（主循环/任务）。返回当前状态 */
pn_cl_status_t pn_inflate_to_tick(void);

/* 读取当前任务的参数与结果（耗时/达成压力） */
void pn_inflate_to_get_job(pn_inflate_job_t *out);

/* 复位（完成/超时后再次启动前调用；stop_action 也会自动复位） */
void pn_cl_reset(void);

/* 是否有闭环任务占用 */
bool pn_cl_busy(void);

#ifdef __cplusplus
}
#endif
