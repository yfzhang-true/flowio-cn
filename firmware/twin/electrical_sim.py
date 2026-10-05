# -*- coding: utf-8 -*-
"""electrical_sim — T7 电气驱动仿真层 (spec §2.7.1 强制, 用户提示①"驱动参数反复出错"的落地).

参数单源 (铁律): 全部电气参数与 drive_policy 从
  hardware/flowio-p1/enclosure/devices.json `pneumatic_devices` 段读取,
  禁手抄第二份; 加载/解析失败直接抛异常 = FAIL (不允许静默兜底值)。
  M0 起 (spec v2.1 §5): 加载改经 flowio 内核 —— TruthSource (真值封装+校验)
  + flowio.truth 视图 (ValveSpec/PumpSpec/DrivePolicy), 解析推导逻辑收拢单源;
  本模块对外 API 与返回结构不变 (test_electrical_sim.py 零改动全绿为验收)。

模型 (board_model 风格, stdlib-only):
  * 三态阀驱动 (drive_policy): 吸入 pull-in 100%≤100ms / 全开保持 90%(等效4.5V=额定)
    / 节能保持 55%(有意欠压 2.75V, 35kPa 背压下限 BRINGUP 实测);
  * 有效电压 V_eff = duty × rail_v (5V 轨 PWM 调制);
  * 线圈电流 I = V_eff / R_coil, R_coil = rated_v / rated_i (registry electrical 段推导,
    推导唯一出处 = flowio.truth.views.ValveSpec.r_coil):
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
对拍: python tools/compare_baseline.py  (12 场景 vs docs/mod-baseline/baseline.json)
"""
import re
import sys
from pathlib import Path

# ---- flowio 内核包 (M0: 参数单源改经 TruthSource; 未 pip -e 亦可跑) -----------
_PKG_ROOT = Path(__file__).resolve().parents[2]          # 仓库根 (flowio 包所在)
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))
from flowio.core import TruthSource                     # noqa: E402
from flowio.truth import drive_policy, pump_spec, valve_specs  # noqa: E402

# ---- 真值文件 (唯一来源; 兼容保留 —— FLOWIO_TRUTH 覆盖时以 TruthSource 为准) --
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

_CH_REF = re.compile(r"^V\d$")          # V1-V8 = 通道阀; VS/VF/VV = 主阀


def load_params(path=None):
    """从 devices.json pneumatic_devices 段加载全部电气参数与驱动策略 (每次全量读盘, 禁缓存——
    断言⑤ '改库即改仿真' 依赖本函数的无缓存语义)。

    M0: 加载路径 = TruthSource(真值封装+两段校验) + flowio.truth 视图
    (DrivePolicy/ValveSpec/PumpSpec, 解析推导收拢单源); 默认路径支持环境变量
    FLOWIO_TRUTH 覆盖 (TruthSource 语义), 其余对外行为不变。
    """
    src = TruthSource(path)                              # 每次新建实例 = 每次全量读盘
    pd = src.pneumatic_devices                           # TruthError = FAIL (fail-loud)
    dp = drive_policy(pd)

    params = {
        "rail_v": dp.rail_v,
        "duties": dict(dp.duties),
        "pull_in_ms": dp.pull_in_ms,
        "pump_max_duty": dp.pump_max_duty,
        "pump_soft_start": dp.pump_soft_start,
        "valves": {},                                   # ref → 电气参数
        "channels": [],                                 # 通道阀 refs (软启动互锁判据)
    }
    for spec in valve_specs(pd):
        for ref in spec.refs:
            params["valves"][ref] = {
                "model": spec.model,
                "i_rated": spec.rated_current_a,
                "v_rated": spec.rated_v,
                "v_range": list(spec.v_range),
                "r_coil": spec.r_coil,
            }
            if _CH_REF.match(ref):
                params["channels"].append(ref)
    params["channels"].sort()
    pump = pump_spec(pd)
    params["pump"] = {
        "model": pump.model,
        "i_load": pump.load_current_a,
        "v_rated": pump.rated_v,
        "v_range": list(pump.v_range),
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
