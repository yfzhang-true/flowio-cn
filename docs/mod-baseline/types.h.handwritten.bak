/**
 * pn_core/types.h — 公共类型定义
 *
 * 对标 FlowIO 架构的自主实现（见 study-notes/02、09）。
 * 本组件为纯逻辑层：不包含任何 ESP-IDF / 平台头文件，可在主机上做单元测试。
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- 常量 ---- */
#define PN_PORT_COUNT     5
#define PN_PORT_MASK_ALL  0x1Fu          /* bit0=端口1 ... bit4=端口5 */
#define PN_VALVE_COUNT    7              /* 端口1-5 + 进气 + 排气 */
#define PN_PUMP_COUNT     1              /* P0 单泵；P1 双泵时改 2 */
#define PN_SENSOR_COUNT   2

/* 阀保持电压节能：开启后先 100%（吸入 pull-in），超过吸入窗再降至保持占空比（笔记 02 第 4 节）。
 * 参数单源（T7 2026-10-03 同步）：hardware/flowio-p1/enclosure/devices.json
 *   pneumatic_devices._meta.drive_policy.valve ——
 *   pull_in "100% <=100ms" / full_open_hold "90% (等效4.5V=额定)"（双源核对见
 *   firmware/twin/electrical_sim.py 场景矩阵与 test_electrical_sim.py 断言②）。
 * 节能保持 55%（有意欠压 2.75V，受限/错峰模式用）经 BLE Config 服务 pwm_params 下发，
 * 不作固件默认值。原 170/~500ms 为 FlowIO 借值，与冻结 drive_policy 不符，已对齐。 */
#define PN_HOLD_DEFAULT_DUTY      230    /* 255 的 ~90%（230/255=90.2% → 4.51V≈额定4.5V） */
#define PN_HOLD_DEFAULT_DELAY_MS  100    /* 吸入窗 ≤100ms（drive_policy valve.pull_in） */

/* ---- 32 位状态字（对外广播用，协议层可直接回传） ---- */
#define PN_SW_PORT1     (1u << 0)        /* 端口阀 1 开 */
#define PN_SW_PORT2     (1u << 1)
#define PN_SW_PORT3     (1u << 2)
#define PN_SW_PORT4     (1u << 3)
#define PN_SW_PORT5     (1u << 4)
#define PN_SW_INLET     (1u << 5)        /* 进气阀开 */
#define PN_SW_VENT      (1u << 6)        /* 排气阀开 */
#define PN_SW_PUMP1     (1u << 7)        /* 泵 1 运行 */
#define PN_SW_PUMP2     (1u << 8)        /* 泵 2 运行（P1 预留） */
#define PN_SW_SENSOR_OK (1u << 9)        /* 传感器在线 */
#define PN_SW_ERROR     (1u << 15)       /* 错误标志（读 pn_last_error） */

typedef enum {
    PN_OK = 0,
    PN_ERR_PARAM,        /* 参数非法（如端口掩码为 0） */
    PN_ERR_BUSY,         /* 有互斥任务在跑（闭环占线） */
    PN_ERR_SENSOR,       /* 传感器读取失败 */
    PN_ERR_TIMEOUT,
    PN_ERR_UNSUPPORTED,  /* 当前配置不支持该动作（配置门禁） */
} pn_err_t;

typedef enum {
    PN_CFG_GENERAL = 0,  /* 通用：充气/排气均可（P0 默认） */
    PN_CFG_INFLATION,    /* 仅正压 */
    PN_CFG_VACUUM,       /* 仅负压（P1 预留） */
} pn_config_t;

typedef enum {
    PN_VALVE_PORT1 = 0,
    PN_VALVE_PORT2,
    PN_VALVE_PORT3,
    PN_VALVE_PORT4,
    PN_VALVE_PORT5,
    PN_VALVE_INLET,      /* 进气阀：大气→泵入口 */
    PN_VALVE_VENT,       /* 排气阀：汇流管→大气（承担 FlowIO 出口阀职能） */
} pn_valve_t;

typedef enum {
    PN_CL_IDLE = 0,      /* 空闲（或从未启动） */
    PN_CL_RUNNING,       /* 闭环进行中 */
    PN_CL_DONE,          /* 达到目标压力，已完成 */
    PN_CL_TIMEOUT,       /* 超时未达标 */
    PN_CL_ERR,           /* 传感器错误 */
} pn_cl_status_t;

typedef enum {
    PN_EV_NONE = 0,
    PN_EV_TARGET_REACHED,/* 压力达标 */
    PN_EV_TIMEOUT,       /* 闭环超时 */
    PN_EV_OVERPRESSURE,  /* 超压保护触发（安全层，规则硬触发） */
    PN_EV_SENSOR_LOST,   /* 传感器失联 */
} pn_event_t;

#ifdef __cplusplus
}
#endif
