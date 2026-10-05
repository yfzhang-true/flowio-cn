# -*- coding: utf-8 -*-
"""electrical_sim — T7 电气驱动仿真层 (spec §2.7.1 强制, 用户提示①"驱动参数反复出错"的落地).

参数单源 (铁律): 全部电气参数与 drive_policy 从
  hardware/flowio-p1/enclosure/devices.json `pneumatic_devices` 段读取,
  禁手抄第二份; 加载/解析失败直接抛异常 = FAIL (不允许静默兜底值)。

模型 (board_model 风格, stdlib-only):
  * 三态阀驱动 (drive_policy): 吸入 pull-in 100%≤100ms / 全开保持 90%(等效4.5V=额定)
    / 节能保持 55%(有意欠压 2.75V, 35kPa 背压下限 BRINGUP 实测);
  * 有效电压 V_eff = duty × rail_v (5V 轨 PWM 调制);
  * 线圈电流 I = V_eff / R_coil, R_coil = rated_v / rated_i (registry electrical 段推导):
    F0520D 4.5V/0.45A=10Ω, F0520B 4.5V/0.30A=15Ω —— 90% 保持时 V_eff=4.5V=额定电压,
    I=450mA 恰为额定 (registry voltage_adequacy 表 "正好额定" 语义; 最坏 9 阀+泵≈4.53A
    与 power_budget 4.55A 同源。任务书速算 9×0.45×0.9+0.475≈4.12A 是按占空比直折的
    保守下界, 两者同判 ">3A 受限模式", 断言方向=检测告警而非数值本身);
  * 泵: 占空比钳 ≤95% (5.0V>4.95V 上限 1% 补偿) + 软启动互锁 (≥1 通道阀开启才起泵)
    + 过压停泵 (M>+35kPa 工作带) / 真空钳位 (M<-40kPa) 路径 (spec §2.6, registry §5);
  * 母线总电流 = Σ阀 + 泵; 超限 (>ADAPTER_A) → 受限模式告警 + 错峰/节能保持建议
    (建议数值由参数实时计算, 非写死文案)。

运行: cd firmware/twin && python electrical_sim.py   (打印场景矩阵表)
测试: python test_electrical_sim.py  (TDD 红→绿, 5 断言+冒烟)
"""
import json
import re
from pathlib import Path

# ---- 真值文件 (唯一来源) ------------------------------------------------------
REGISTRY = Path(__file__).resolve().parents[2] / "hardware" / "flowio-p1" / "enclosure" / "devices.json"

# ---- 固件策略常量 (非器件参数, 来源 spec §2.6 / docs/component-registry.md §5) --
ADAPTER_A = 3.0            # 适配器档初值 (BRINGUP 实测后可调) —— spec §2.7.1 断言①
WORKING_BAND_KPA = 35.0    # 闭环工作带 ±35kPa (泵死头 ±120/-60 >> 阀额定 ±45)
VAC_CLAMP_KPA = -40.0      # 真空钳位 (-50 收紧至 -40)
ALARM_OVERLOAD = 0x01      # 母线超限 (受限模式)
ALARM_OVERPRESSURE = 0x02  # M > +35kPa 停泵告警
ALARM_VACUUM_CLAMP = 0x04  # M < -40kPa 真空钳位停泵
ALARM_NAMES = {ALARM_OVERLOAD: "OVERLOAD", ALARM_OVERPRESSURE: "OVERPRESSURE",
               ALARM_VACUUM_CLAMP: "VACUUM_CLAMP"}

# 阀状态机 (drive_policy 三态 + 关断)
VALVE_STATES = ("off", "pull_in", "full_open", "economy")

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MS = re.compile(r"<=?\s*(\d+)\s*ms")
_CH_REF = re.compile(r"^V\d$")          # V1-V8 = 通道阀; VS/VF/VV = 主阀


def _pct(s, where):
    m = _PCT.search(str(s))
    if not m:
        raise ValueError(f"drive_policy {where} 无法解析百分比: {s!r}")
    return float(m.group(1)) / 100.0


def load_params(path=None):
    """从 devices.json pneumatic_devices 段加载全部电气参数与驱动策略 (每次全量读盘, 禁缓存——
    断言⑤ '改库即改仿真' 依赖本函数的无缓存语义)。"""
    src = Path(path) if path else REGISTRY
    with src.open(encoding="utf-8") as f:
        doc = json.load(f)
    pd = doc["pneumatic_devices"]                      # KeyError/JSON 错 = FAIL
    dp = pd["_meta"]["drive_policy"]

    m = _MS.search(dp["valve"]["pull_in"])
    if not m:
        raise ValueError(f"drive_policy pull_in 时长无法解析: {dp['valve']['pull_in']!r}")
    params = {
        "rail_v": float(dp["rail_v"]),
        "duties": {
            "pull_in": _pct(dp["valve"]["pull_in"], "valve.pull_in"),
            "full_open": _pct(dp["valve"]["full_open_hold"], "valve.full_open_hold"),
            "economy": _pct(dp["valve"]["economy_hold"], "valve.economy_hold"),
        },
        "pull_in_ms": float(m.group(1)),
        "pump_max_duty": _pct(dp["pump"]["max_duty"], "pump.max_duty"),
        "pump_soft_start": "互锁" in str(dp["pump"]["soft_start"]),
        "valves": {},                                   # ref → 电气参数
        "channels": [],                                 # 通道阀 refs (软启动互锁判据)
    }
    for group, kind in (("valves", None), ("valve_vacuum_master", None)):
        for entry in pd.get(group, []):
            el = entry["electrical"]
            for ref in entry["refs"]:
                params["valves"][ref] = {
                    "model": entry.get("model", ""),
                    "i_rated": float(el["rated_current_a"]),
                    "v_rated": float(el["rated_v"]),
                    "v_range": [float(x) for x in el["v_range"]],
                    "r_coil": float(el["rated_v"]) / float(el["rated_current_a"]),
                }
                if _CH_REF.match(ref):
                    params["channels"].append(ref)
    params["channels"].sort()
    pump_el = pd["pump"][0]["electrical"]
    params["pump"] = {
        "model": pd["pump"][0].get("model", ""),
        "i_load": float(pump_el["load_current_a"]),
        "v_rated": float(pump_el["rated_v"]),
        "v_range": [float(x) for x in pump_el["v_range"]],
    }
    if not params["valves"] or not params["channels"]:
        raise ValueError("pneumatic_devices 阀条目缺失 (单源加载失败)")
    return params


def simulate(valves, pump_duty, params=None, p_manifold_kpa=0.0):
    """给定场景求母线电气解。

    valves: {ref: state} state ∈ {off, pull_in, full_open, economy} (未列出的阀=off)
    pump_duty: 泵请求占空比 (0~1, 会被钳 ≤95% 并施加互锁/过压路径)
    p_manifold_kpa: 歧管压力 (gauge), 过压/真空钳位判据
    返回: {bus, actuators, pump, alarms, alarm_names, over_limit, advice, limit_a}
    """
    p = params if params is not None else load_params()
    states = {ref: "off" for ref in p["valves"]}
    for ref, st in (valves or {}).items():
        if ref not in p["valves"]:
            raise ValueError(f"未知阀 {ref!r} (registry 无此 ref)")
        if st not in VALVE_STATES:
            raise ValueError(f"非法阀状态 {st!r} (∈ {VALVE_STATES})")
        states[ref] = st

    # ---- 泵: 请求钳位 → 软启动互锁 → 过压/真空钳位停泵 ----------------------
    duty_req = max(0.0, min(float(pump_duty), 1.0))
    duty_eff = min(duty_req, p["pump_max_duty"])
    alarms, advice = [], []
    interlock = op_stop = vac_stop = False
    channel_open = any(states[r] != "off" for r in p["channels"])
    if p["pump_soft_start"] and duty_eff > 0 and not channel_open:
        duty_eff, interlock = 0.0, True                  # 0 通道开启 → 泵必 0
    if duty_eff > 0 and p_manifold_kpa > WORKING_BAND_KPA:
        duty_eff, op_stop = 0.0, True                    # M > +35kPa → 停泵+告警
        alarms.append(ALARM_OVERPRESSURE)
    if duty_eff > 0 and p_manifold_kpa < VAC_CLAMP_KPA:
        duty_eff, vac_stop = 0.0, True                   # M < -40kPa → 真空钳位停泵
        alarms.append(ALARM_VACUUM_CLAMP)

    # ---- 执行器解 (V_eff = duty·rail; I = V_eff/R_coil) ----------------------
    actuators, i_valves = {}, 0.0
    for ref, st in states.items():
        vp = p["valves"][ref]
        duty = 0.0 if st == "off" else p["duties"][st]
        eff_v = duty * p["rail_v"]
        i_a = eff_v / vp["r_coil"]
        i_valves += i_a
        actuators[ref] = {
            "state": st, "duty": round(duty, 4), "eff_v": round(eff_v, 4),
            "i_a": round(i_a, 4), "p_w": round(eff_v * i_a, 4),
            "p_peak_w": round(p["rail_v"] * i_a, 4),     # on 相瞬时 (rail × i)
            "steady": st in ("full_open", "economy"),    # 稳态 = 保持态 (断言②作用域)
            "hold_economy": st == "economy",             # 有意欠压标记 (豁免 4.05V 下限)
            "transient_ms": p["pull_in_ms"] if st == "pull_in" else 0.0,
        }
    pump_i = duty_eff * p["pump"]["i_load"]
    i_total = i_valves + pump_i

    # ---- 断言①的语义: 超限检测与告警 (最坏场景是物理事实, 检测它而非回避它) ----
    over_limit = i_total > ADAPTER_A
    if over_limit:
        alarms.append(ALARM_OVERLOAD)
        n_ch = sum(1 for r in p["channels"] if states[r] == "full_open")
        eco_i = (sum(actuators[r]["i_a"] for r in p["valves"] if states[r] != "off")
                 * p["duties"]["economy"] / p["duties"]["full_open"] + pump_i)
        advice.append(
            f"受限模式: 母线 {i_total:.2f}A > {ADAPTER_A:.1f}A 档 —— 错峰: 并发全开保持 ≤4 通道")
        advice.append(
            f"或降节能保持 {p['duties']['economy']:.0%} (等效电流约 {eco_i:.2f}A ≤ {ADAPTER_A:.1f}A)")
        advice.append("BRINGUP 实测最小可靠保持占空比后再定适配器档 (3A/4A/5A)")
    pump = {
        "duty_req": round(duty_req, 4), "duty_eff": round(duty_eff, 4),
        "eff_v": round(duty_eff * p["rail_v"], 4), "i_a": round(pump_i, 4),
        "p_w": round(duty_eff * p["rail_v"] * pump_i, 4),
        "interlock": interlock, "overpressure_stop": op_stop, "vacuum_stop": vac_stop,
    }
    return {
        "bus": {"i_total_a": round(i_total, 4), "i_valves_a": round(i_valves, 4),
                "i_pump_a": round(pump_i, 4),
                "p_w": round(sum(a["p_w"] for a in actuators.values()) + pump["p_w"], 4),
                "limit_a": ADAPTER_A},
        "actuators": actuators, "pump": pump,
        "alarms": alarms, "alarm_names": [ALARM_NAMES[a] for a in alarms],
        "over_limit": over_limit, "advice": advice,
    }


# ---- 场景矩阵 (spec §2.7.1: 至少 单通道充/吸/排/保 + 1-3 通道充气 + 最坏 9 阀 + 搬气 + 过压)
SCENARIOS = {
    "single_inflate": {
        "desc": "单通道充气 (V1+S 保持+泵)", "valves": {"V1": "full_open", "VS": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "single_vacuum": {
        "desc": "单通道吸气 (V1+V 保持+泵)", "valves": {"V1": "full_open", "VV": "full_open"},
        "pump": 0.95, "p_m": -30.0},
    "single_release": {
        "desc": "单通道排气 (V1+F 保持, 泵停)", "valves": {"V1": "full_open", "VF": "full_open"},
        "pump": 0.0, "p_m": 0.0},
    "single_hold": {
        "desc": "单通道保压 (V1 节能保持)", "valves": {"V1": "economy"},
        "pump": 0.0, "p_m": 25.0},
    "inflate_pull_in_transient": {
        "desc": "充气吸入瞬态 (V1+S 100%≤100ms+泵)", "valves": {"V1": "pull_in", "VS": "pull_in"},
        "pump": 0.95, "p_m": 0.0},
    "inflate_3ch": {
        "desc": "典型 3 通道充气 (V1-3+S 保持+泵)",
        "valves": {"V1": "full_open", "V2": "full_open", "V3": "full_open", "VS": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "worst_9v_hold_pump": {
        "desc": "最坏 9 阀全开保持+泵95% (受限模式)", "restricted": True,
        "valves": {r: "full_open" for r in
                   ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS"]},
        "pump": 0.95, "p_m": 0.0},
    "worst_9v_economy_pump": {
        "desc": "错峰对策: 9 阀节能保持+泵95%",
        "valves": {r: "economy" for r in
                   ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS"]},
        "pump": 0.95, "p_m": 0.0},
    "transfer_gas": {
        "desc": "搬气 (S+V+V1 保持+泵, 单泵换向)",
        "valves": {"VS": "full_open", "VV": "full_open", "V1": "full_open"},
        "pump": 0.95, "p_m": 0.0},
    "pump_only_interlock": {
        "desc": "非法工况: 0 通道开起泵 (互锁拦截)",
        "valves": {}, "pump": 0.95, "p_m": 0.0},
    "overpressure": {
        "desc": "过压工况 M=+36kPa (停泵+告警路径)",
        "valves": {"V1": "full_open", "VS": "full_open"}, "pump": 0.95, "p_m": 36.0},
    "vacuum_clamp": {
        "desc": "真空钳位 M=-41kPa (停泵+告警路径)",
        "valves": {"V1": "full_open", "VV": "full_open"}, "pump": 0.95, "p_m": -41.0},
}


def run_scenario(name, params=None):
    sc = SCENARIOS[name]
    r = simulate(sc["valves"], sc["pump"], params=params, p_manifold_kpa=sc["p_m"])
    r["name"] = name
    r["desc"] = sc["desc"]
    return r


def run_matrix(params=None):
    """场景矩阵全跑 → 摘要行 (name/i/超限/告警/建议/预期)。"""
    rows = []
    for name, sc in SCENARIOS.items():
        r = run_scenario(name, params=params)
        rows.append({
            "name": name, "desc": sc["desc"],
            "i_total_a": r["bus"]["i_total_a"], "over_limit": r["over_limit"],
            "alarms": r["alarms"], "alarm_names": r["alarm_names"],
            "advice": r["advice"],
            "expect_over_limit": bool(sc.get("restricted")),
        })
    return rows


if __name__ == "__main__":
    p = load_params()
    print(f"参数单源: {REGISTRY}")
    print(f"  rail={p['rail_v']}V  duties(吸入/全开/节能)="
          f"{p['duties']['pull_in']:.0%}/{p['duties']['full_open']:.0%}/"
          f"{p['duties']['economy']:.0%}  泵≤{p['pump_max_duty']:.0%}"
          f"  R_coil(D)={p['valves']['V1']['r_coil']:.1f}Ω "
          f"R_coil(B)={p['valves']['VV']['r_coil']:.1f}Ω")
    print(f"  适配器档 {ADAPTER_A}A | 工作带 ±{WORKING_BAND_KPA:.0f}kPa | "
          f"真空钳位 {VAC_CLAMP_KPA:.0f}kPa\n")
    print(f"{'场景':<28}{'母线 A':>8}  {'超限':<4}{'告警':<14}说明")
    for row in run_matrix():
        flag = "⚠受限" if row["over_limit"] else "ok"
        al = ",".join(row["alarm_names"]) or "-"
        print(f"{row['name']:<28}{row['i_total_a']:>8.3f}  {flag:<5}{al:<14}{row['desc']}")
        for a in row["advice"]:
            print(f"{'':>40}└ {a}")
