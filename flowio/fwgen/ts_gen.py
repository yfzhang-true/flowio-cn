# -*- coding: utf-8 -*-
"""flowio.fwgen.ts_gen — devices.json → webapp/js/params_gen.js 生成器 (M3)。

gen_params_js(truth) -> str: ES module `export const FLOWIO_PARAMS = ...`
(真值只读快照 + 派生字段, Object.freeze 冻结)。hold_duty_255 与 C 侧
PN_HOLD_DEFAULT_DUTY 共用 c_gen.hold_duty_byte 唯一推导 —— 三方对拍锚点
(devices.json ↔ types.h ↔ params_gen.js)。

值分类:
  真值直映 — rail_v/duties/min_actuation_v/额定电压电流/压力量程/流量;
  派生     — hold_duty_255 (255×full_open_hold 四舍五入);
  不入 JS  — twin_api.c 本地仿真标定值 (PUMP_P_MAX 61 等, 见 c_gen 分类表),
             前端不消费孪生内部策略, 只见真值与协议层参数。
"""
from __future__ import annotations

from flowio.core.errors import TruthError
from flowio.core.truth import TruthSource
from flowio.fwgen import templates as T
from flowio.fwgen.c_gen import hold_duty_byte
from flowio.truth import drive_policy, pump_spec, sensor_spec, valve_specs


def _num(v) -> str:
    """数值 → JS 字面量: 整值浮点保留一位小数 (5.0 非 5), 其余最短 repr。"""
    if isinstance(v, int):
        return str(v)
    return "%.1f" % v if float(v) == int(v) else repr(float(v))


def _arr(vals) -> str:
    return "[" + ", ".join(_num(v) for v in vals) + "]"


def gen_params_js(truth: TruthSource) -> str:
    """渲染 params_gen.js 全文 (确定性: 同真值 → 逐字节同文)。"""
    pn = truth.pneumatic_devices
    dp = drive_policy(pn)
    valve = next((s for s in valve_specs(pn) if s.group == "valves"), None)
    if valve is None:
        raise TruthError("pneumatic_devices.valves 条目缺失 (params_gen.js)")
    pump = pump_spec(pn)
    sensor = sensor_spec(pn)
    min_act = pn.get("_meta", {}).get("drive_policy", {}) \
                  .get("voltage_adequacy", {}).get("min_actuation_v")
    if not isinstance(min_act, (int, float)):
        raise TruthError("voltage_adequacy.min_actuation_v 缺失/非数值 "
                         "(pneumatic_devices._meta.drive_policy)")

    body = "\n".join([
        "export const FLOWIO_PARAMS = Object.freeze({",
        "  rail_v: %s,  // [registry] %s" % (_num(dp.rail_v), T.KEY_RAIL_V),
        "  valve: Object.freeze({",
        "    hold_duty_255: %d,  // [registry] %s 百分比 → 255 制字节 (与 C 侧 PN_HOLD_DEFAULT_DUTY 同推导)"
        % (hold_duty_byte(dp), T.KEY_VALVE_FULL_OPEN),
        "    hold_delay_ms: %d,  // [registry] %s 吸入窗"
        % (int(dp.pull_in_ms), T.KEY_VALVE_PULL_IN),
        "    pull_in_duty: %s, economy_duty: %s,  // [registry] pull_in/economy_hold"
        % (_num(dp.duties["pull_in"]), _num(dp.duties["economy"])),
        "    full_open_duty: %s,  // [registry] full_open_hold (hold_duty_255 的百分比源)"
        % _num(dp.duties["full_open"]),
        "    min_actuation_v: %s,  // [registry] %s (最低动作电压)"
        % (_num(min_act), T.KEY_MIN_ACTUATION_V),
        "    rated_v: %s, rated_current_a: %s, pressure_kpa: Object.freeze(%s),  // [registry] valves[0] %s"
        % (_num(valve.rated_v), _num(valve.rated_current_a),
           _arr(valve.pressure_kpa), valve.model),
        "  }),",
        "  pump: Object.freeze({",
        "    max_duty: %s,  // [registry] %s" % (_num(dp.pump_max_duty), T.KEY_PUMP_MAX_DUTY),
        "    p_min_kpa: %s, p_max_kpa: %s,  // [registry] pump[0].pressure_kpa (死头能力; 孪生仿真死点另见 twin_api.c 注与本文件 banner)"
        % (_num(pump.pressure_kpa[0]), _num(pump.pressure_kpa[1])),
        "    rated_v: %s, load_current_a: %s, flow_lpm: %s,  // [registry] pump[0] %s"
        % (_num(pump.rated_v), _num(pump.load_current_a), _num(pump.flow_lpm), pump.model),
        "  }),",
        "  sensor: Object.freeze({",
        "    i2c_addr: \"%s\", v_range: Object.freeze(%s)  // [registry] sensor[0] %s"
        % (sensor.i2c_addr, _arr(sensor.v_range), sensor.model),
        "  }),",
        "});",
        "",
    ])
    return T.PARAMS_JS_BANNER + body
