/**
 * pn_core/actions.h — 气动动作层 API
 *
 * 语义继承自 study-notes/02（功能性描述，非代码复制）：
 *  - 端口参数是 5 位位掩码（bit0=端口1）；全 0 = 无效输入，静默忽略；
 *  - 动作前先执行停止（干净状态起步）；
 *  - set/open/close 三胞胎：写全部 / 只开掩码位 / 只关掩码位；
 *  - 保压 = 常闭阀全关（免费的安全态）；
 *  - 32 位状态字随每个驱动操作同步维护。
 */
#pragma once

#include "pn_core/hal_if.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 初始化：绑定 HAL、复位状态字、把所有阀/泵置 0（上电安全态） */
void     pn_init(const pn_hal_if_t *hal, pn_config_t cfg);

/* 配置门禁：配置不符的动作静默忽略（返回 PN_ERR_UNSUPPORTED） */
void        pn_set_config(pn_config_t cfg);
pn_config_t pn_get_config(void);

/* 状态查询 */
uint32_t pn_get_state(void);              /* 32 位状态字 */
bool     pn_get_state_of(uint8_t bit);    /* 读状态字某一位 */
pn_err_t pn_last_error(void);

/* 端口阀三胞胎（掩码 bit0..bit4 → 端口1..5） */
void    pn_ports_set(uint8_t ports);      /* 1 开 0 关，写全部 */
void    pn_ports_open(uint8_t ports);     /* 只开掩码位 */
void    pn_ports_close(uint8_t ports);    /* 只关掩码位 */

/* 方向阀 */
void pn_inlet_open(void);
void pn_inlet_close(void);
void pn_vent_open(void);
void pn_vent_close(void);

/* 泵 */
void pn_pump_start(uint8_t duty);         /* duty 0–255，PWM 调速 */
void pn_pump_stop(void);

/* ---- 组合动作（执行前自动先停止） ---- */
pn_err_t pn_start_inflation(uint8_t ports, uint8_t pwm);  /* 进气阀开+端口开+泵转 */
pn_err_t pn_start_vacuum(uint8_t ports, uint8_t pwm);     /* 排气路径（P0 泵支持吸/充两用） */
pn_err_t pn_start_release(uint8_t ports);                 /* 排放：开排气位+端口阀，泵停 */
pn_err_t pn_stop_action(uint8_t ports);                   /* 停止=关方向阀+关指定端口+泵停（=隔离保压） */
pn_err_t pn_hold_open(uint8_t ports);                     /* 诊断保压：泵侧密封+端口保持通（汇流管+下游连成单一密封容积，泄漏诊断/TinyML 检测窗口用） */

/* ---- 阀保持节能：开启超 threshold 的阀降至 hold_duty ---- */
void pn_optimize_power(uint8_t hold_duty, uint16_t threshold_ms);

/* 某阀已开启时长（ms；关闭中的阀返回 0）。闭环用它算耗时/超时 */
uint32_t pn_valve_open_ms(uint8_t valve_idx);

/* ---- 传感 ---- */
/* 读指定传感器（kPa）。同时维护状态字 SENSOR_OK 位与错误码 */
pn_err_t pn_read_pressure(uint8_t sensor_idx, float *kpa);

/* ---- 超压保护（安全层，硬规则，TinyML/任何上层不可关闭） ---- */
/* 调用者周期性调用：任一在线传感器 > limit_kpa 即全关+置错误位 */
pn_err_t pn_check_overpressure(float limit_kpa);

#ifdef __cplusplus
}
#endif
