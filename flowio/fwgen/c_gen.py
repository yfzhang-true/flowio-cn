# -*- coding: utf-8 -*-
"""flowio.fwgen.c_gen — devices.json → pn_core/types.h 生成器 (M3 D1=B)。

gen_types_h(truth) -> str: 参数段从 TruthSource 视图映射, 模板段 (类型/枚举/
拓扑常量/溯源注释) 由 templates.py 逐字节供给 —— D1=B 全文件生成形态。

参数段常量分类 (逐一裁定, 值零改动——见 templates.py 模块注释同表):
  映射 (真值驱动, 注释含 [registry] 键路径):
    PN_HOLD_DEFAULT_DUTY      230  ← full_open_hold "90%" → round(255×0.90)
                                     (230/255=90.2% → 4.51V ≈ 阀额定 4.5V@5V 轨)
    PN_HOLD_DEFAULT_DELAY_MS  100  ← pull_in "100% <=100ms" 吸入窗
  不映射 (留模板段, 原值原注释):
    PN_PORT/VALVE/PUMP/SENSOR_COUNT、PN_PORT_MASK_ALL、PN_SW_* —— 固件拓扑/
    协议位布局, 与 registry 物理位号集不同抽象 (V1-V8/VS/VF/VV=11 阀 vs 逻辑
    7 阀), 强映射即改值。
  明确不入 types.h 的 twin_api.c 本地常量 (D1=B 边界外, 值零改动不动):
    PUMP_P_MIN_KPA -60 —— 与 registry pump.pressure_kpa[0] 恰同值但属孪生物理
      模型标定段 (twin_api.c), 迁入 types.h 会引入 #define 重定义冲突, 且其
      兄弟常量非真值 (见下), 拆段反而制造"半真值"误导;
    PUMP_P_MAX_KPA 61 —— 仿真策略值 (FlowIO Small 实测死点), 非 registry 死头
      120 (pump.pressure_kpa[1]=ZER370 能力上限) —— 双值并存属设计 (PHYSICS-
      SPEC), 映射即改仿真锚点;
    VALVE_P_MIN_KPA -53.3 —— 0520D/F 规格书动作窗 (手册值), registry 无此键
      (valves.pressure_kpa=[0,45] 是密封/耐压语义), 属孪生真空渐近策略。
"""
from __future__ import annotations

from flowio.core.errors import TruthError
from flowio.core.truth import TruthSource
from flowio.fwgen import templates as T
from flowio.truth import drive_policy, valve_specs


def hold_duty_byte(dp) -> int:
    """全开保持占空比 (255 制字节) = round(255 × full_open_hold)。

    三语共用唯一推导 (C 侧 PN_HOLD_DEFAULT_DUTY 与 JS 侧 hold_duty_255 同源);
    half-up 而非 banker's rounding (255×0.9=229.5 → 230, 与手写版一致)。
    """
    duty = int(255.0 * dp.duties["full_open"] + 0.5)
    if not 0 < duty <= 255:
        raise TruthError("full_open_hold 越域 → 255 制占空比 %d 非法 "
                         "(pneumatic_devices._meta.drive_policy.valve.full_open_hold)" % duty)
    return duty


def _hold_valves_rated_v(pn) -> float:
    """通道阀 (valves 组首条) 额定电压 —— 注释中 "额定X.XV" 的出处。"""
    for spec in valve_specs(pn):
        if spec.group == "valves":
            return spec.rated_v
    raise TruthError("pneumatic_devices.valves 条目缺失 (额定电压注释无出处)")


def gen_types_h(truth: TruthSource) -> str:
    """渲染生成版 types.h 全文 (确定性: 同真值 → 逐字节同文)。"""
    pn = truth.pneumatic_devices
    dp = drive_policy(pn)

    duty = hold_duty_byte(dp)                       # 230
    ms = int(dp.pull_in_ms)                         # 100
    if ms <= 0:
        raise TruthError("pull_in 吸入窗非正: %r (drive_policy.valve.pull_in)" % ms)
    rated_v = _hold_valves_rated_v(pn)              # 4.5
    pct0 = int(dp.duties["full_open"] * 100 + 0.5)  # 90
    pct1 = "%.1f" % (duty / 255.0 * 100.0)          # 90.2
    volts = "%.2f" % (duty / 255.0 * dp.rail_v)     # 4.51

    duty_line = T.TYPES_H_DEFINE_DUTY.format(
        duty=duty, pct0=pct0, pct1=pct1, volts=volts,
        rated_v=("%g" % rated_v), key_full_open=T.KEY_VALVE_FULL_OPEN)
    delay_line = T.TYPES_H_DEFINE_DELAY.format(ms=ms, key_pull_in=T.KEY_VALVE_PULL_IN)

    return T.types_h_skeleton(duty_line, delay_line)
