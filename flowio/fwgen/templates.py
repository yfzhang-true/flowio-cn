# -*- coding: utf-8 -*-
"""flowio.fwgen.templates — types.h 生成模板段 (M3 D1=B, spec v2.1 §3.5)。

模板段 = 与 devices.json 无关的固件自决内容, 从 M2 手写 types.h 逐字节迁入
(备份: docs/mod-baseline/types.h.handwritten.bak @49af3bf; 迁移纪律: 溯源
注释逐条在场, 禁丢事故出处)。参数段占位 ({duty}/{ms}/...) 由 c_gen 从
TruthSource 视图填充。

常量分类 (D1=B 逐一裁定, 值零改动):
  真值映射 (参数段, c_gen 生成):
    PN_HOLD_DEFAULT_DUTY     230  ← drive_policy.valve.full_open_hold "90%"
    PN_HOLD_DEFAULT_DELAY_MS 100  ← drive_policy.valve.pull_in "100% <=100ms"
  固件拓扑/架构 (模板段, 非 registry 语义):
    PN_PORT_COUNT/VALVE_COUNT/PUMP_COUNT/SENSOR_COUNT —— 逻辑拓扑 (5 端口阀+
    进气+排气=7 阀); registry 物理位号 (V1-V8/VS/VF/VV=11, S1=1, P1=1) 是
    贴装层集合, 与固件逻辑通道数不同抽象, 不可映射 (强映射即改值, 违反值零改动)。
    PN_PORT_MASK_ALL / PN_SW_* —— 协议位定义 (bit 布局), 与真值无关。
"""
from __future__ import annotations

# ── 区段标记 (tools/check_codegen.py 与 tests 复用; 与下方文本同源) ──────────
TOPOLOGY_START = "/* ---- 常量 ---- */"
TOPOLOGY_END = "#define PN_SENSOR_COUNT   2"
HOLD_COMMENT_START = "/* 阀保持电压节能"
HOLD_COMMENT_END = "已对齐。 */"
STATUS_START = "/* ---- 32 位状态字"

# ── registry 键路径 (参数段注释/JS 侧共用单一拼写) ────────────────────────────
KEY_RAIL_V = "pneumatic_devices._meta.drive_policy.rail_v"
KEY_VALVE_PULL_IN = "pneumatic_devices._meta.drive_policy.valve.pull_in"
KEY_VALVE_FULL_OPEN = "pneumatic_devices._meta.drive_policy.valve.full_open_hold"
KEY_VALVE_ECONOMY = "pneumatic_devices._meta.drive_policy.valve.economy_hold"
KEY_PUMP_MAX_DUTY = "pneumatic_devices._meta.drive_policy.pump.max_duty"
KEY_MIN_ACTUATION_V = "pneumatic_devices._meta.drive_policy.voltage_adequacy.min_actuation_v"

# ── types.h 模板段 (逐字节迁自手写版; 参数占位行除外) ─────────────────────────
TYPES_H_BANNER = """/**
 * pn_core/types.h — 公共类型定义
 *
 * 对标 FlowIO 架构的自主实现（见 study-notes/02、09）。
 * 本组件为纯逻辑层：不包含任何 ESP-IDF / 平台头文件，可在主机上做单元测试。
 *
 * ⚠ 生成文件（DO NOT EDIT）——M3 D1=B 全文件生成（spec v2.1 §3.5）：
 *   模板段（类型/枚举/拓扑常量/溯源注释）= flowio/fwgen/templates.py；
 *   参数段（行内 [registry] 标注者）= hardware/flowio-p1/enclosure/devices.json 映射。
 *   再生成：python -m flowio fwgen；CI 门：tools/check_codegen.py --ci（手改即红）。
 *   改参数 = 改真值后重生成——-58→-60 类三语手抄漂移的机器级根治。
 */"""

TYPES_H_PRAGMA_BLOCK = """#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif"""

TYPES_H_TOPOLOGY = """/* ---- 常量 ---- */
#define PN_PORT_COUNT     5
#define PN_PORT_MASK_ALL  0x1Fu          /* bit0=端口1 ... bit4=端口5 */
#define PN_VALVE_COUNT    7              /* 端口1-5 + 进气 + 排气 */
#define PN_PUMP_COUNT     1              /* P0 单泵；P1 双泵时改 2 */
#define PN_SENSOR_COUNT   2"""

# 阀保持溯源注释块 (T7 参数单源同步叙事, 事故出处 170/~500ms 在场) —— 原文逐字节
TYPES_H_HOLD_PROVENANCE = """/* 阀保持电压节能：开启后先 100%（吸入 pull-in），超过吸入窗再降至保持占空比（笔记 02 第 4 节）。
 * 参数单源（T7 2026-10-03 同步）：hardware/flowio-p1/enclosure/devices.json
 *   pneumatic_devices._meta.drive_policy.valve ——
 *   pull_in "100% <=100ms" / full_open_hold "90% (等效4.5V=额定)"（双源核对见
 *   firmware/twin/electrical_sim.py 场景矩阵与 test_electrical_sim.py 断言②）。
 * 节能保持 55%（有意欠压 2.75V，受限/错峰模式用）经 BLE Config 服务 pwm_params 下发，
 * 不作固件默认值。原 170/~500ms 为 FlowIO 借值，与冻结 drive_policy 不符，已对齐。 */"""

# 参数段 #define 行模板 (值/推导数字由 c_gen 填充; 注释含 registry 键路径)
TYPES_H_DEFINE_DUTY = """#define PN_HOLD_DEFAULT_DUTY      {duty}    /* 255 的 ~{pct0}%（{duty}/255={pct1}% → {volts}V≈额定{rated_v}V）
                                         * [registry] {key_full_open} */"""

TYPES_H_DEFINE_DELAY = """#define PN_HOLD_DEFAULT_DELAY_MS  {ms}    /* 吸入窗 ≤{ms}ms [registry] {key_pull_in} */"""

# 状态字 + 枚举 + 收尾 (extern C 闭段) —— 原文逐字节 (至文件尾)
TYPES_H_TAIL = """/* ---- 32 位状态字（对外广播用，协议层可直接回传） ---- */
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
#endif"""


def types_h_skeleton(duty_line: str, delay_line: str) -> str:
    """装配最终 types.h 文本: 横幅 + pragma/拓扑/溯源(模板) + 参数段(生成) + 尾段。"""
    return "\n".join([
        TYPES_H_BANNER,          # 生成告示 (DO NOT EDIT + 再生成/CI 门指引)
        TYPES_H_PRAGMA_BLOCK,    # pragma/include/extern C 开段 —— 原文逐字节
        "",
        TYPES_H_TOPOLOGY,        # 拓扑常量块 —— 原文逐字节
        "",
        TYPES_H_HOLD_PROVENANCE,  # 阀保持溯源注释块 —— 原文逐字节 (事故出处在场)
        duty_line,               # 参数段: [registry] 映射 (c_gen 填充)
        delay_line,
        "",
        TYPES_H_TAIL,            # 状态字+枚举+收尾 —— 原文逐字节
    ]) + "\n"


# ── params_gen.js 模板段 ──────────────────────────────────────────────────────
PARAMS_JS_BANNER = """// firmware/twin/webapp/js/params_gen.js — 三语参数生成物 · TS/ES module 侧 (M3, spec v2.1 §3.5)
// ⚠ 生成文件 (DO NOT EDIT): `python -m flowio fwgen` ← hardware/flowio-p1/enclosure/devices.json
//   手改必被 tools/check_codegen.py --ci 打红; 改参数 = 改真值后重生成。
//   同源生成: firmware/components/pn_core/include/pn_core/types.h (C 侧, D1=B)。
// 语义: 真值只读快照 + 少量推导 (hold_duty_255 = 255×full_open_hold 四舍五入,
//   与 C 侧 PN_HOLD_DEFAULT_DUTY 同推导同值 —— 三方对拍锚点)。
// 注: 泵正压死头 twin 仿真取 61 (twin_api.c 本地策略值, FlowIO Small 实测),
//   非 registry 死头能力 120 (p_max_kpa) —— 双值并存属设计, 见 PHYSICS-SPEC。
"""
