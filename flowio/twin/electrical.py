# -*- coding: utf-8 -*-
"""flowio.twin.electrical — 准静态母线电气解 (electrical_sim 内核迁入, M2 spec §3.2)。

迁移 (firmware/twin/electrical_sim.py → 本模块, 旧模块变薄壳 re-export):
  * load_params —— 参数单源加载 (TruthSource + flowio.truth 视图, 每次全量读盘,
    断言⑤ '改库即改仿真' 的无缓存语义保持);
  * simulate 核心 —— 迁为 ElectricalModel(BaseModel) 的 solve/step;
  * 固件策略常量 (ADAPTER_A/工作带/告警码) —— 非器件参数, 随内核迁入。

多态核心 (spec §3.4 ①): 阀电流 = Σ a.current(state) —— 本模块只见 IActuator
列表 (build_actuators 产), 不认识 D/B/泵具体型号; 新执行器类型入列零改本模块
(见 flowio/tests/test_twin.py::test_future_actuator_zero_model_change)。
报告同源 (M2-R①): 报告字段 duty/eff_v 经 IActuator.duty 报告钩子取自执行器
侧 —— 与物理电流同一来源, 注入异构执行器时不再旁抄 params 策略表。

位级对拍纪律: 求和顺序 = 真值条目序 (V1-V8/VS/VF → VV), 公式/舍入与旧
electrical_sim 逐行同构 —— tools/compare_baseline.py 12 场景逐值相等的根基。
"""
from flowio.core.interfaces import BaseModel
from flowio.core.truth import TruthSource
from flowio.truth import drive_policy, pump_spec, valve_specs
from flowio.twin.actuators import build_actuators

# ---- 真值文件 (兼容保留; 加载一律经 TruthSource, FLOWIO_TRUTH 覆盖语义) ------
import re
from pathlib import Path

REGISTRY = (Path(__file__).resolve().parents[2] / "hardware" / "flowio-p1"
            / "enclosure" / "devices.json")

# ---- 固件策略常量 (非器件参数, 来源 spec §2.6 / docs/component-registry.md §5) --
ADAPTER_A = 3.0            # 适配器档初值 (BRINGUP 实测后可调) —— spec §2.7.1 断言①
WORKING_BAND_KPA = 35.0    # 闭环工作带 ±35kPa (泵死头 ±120/-60 >> 阀额定 ±45)
VAC_CLAMP_KPA = -40.0      # 真空钳位 (-50 收紧至 -40)
ALARM_OVERLOAD = 0x01      # 母线超限 (受限模式)
ALARM_OVERPRESSURE = 0x02  # M > +35kPa 停泵告警
ALARM_VACUUM_CLAMP = 0x04  # M < -40kPa 真空钳位停泵
ALARM_NAMES = {ALARM_OVERLOAD: "OVERLOAD", ALARM_OVERPRESSURE: "OVERPRESSURE",
               ALARM_VACUUM_CLAMP: "VACUUM_CLAMP"}

# 阀状态机 (drive_policy 三态 + 关断; 场景层 legacy 命名, canonical hold 见 actuators)
VALVE_STATES = ("off", "pull_in", "full_open", "economy")

_CH_REF = re.compile(r"^V\d$")          # V1-V8 = 通道阀; VS/VF/VV = 主阀


def load_params(path=None):
    """从 devices.json pneumatic_devices 段加载全部电气参数与驱动策略 (每次全量
    读盘, 禁缓存 —— 断言⑤ '改库即改仿真' 依赖本函数的无缓存语义)。

    加载路径 = TruthSource(真值封装+两段校验) + flowio.truth 视图
    (DrivePolicy/ValveSpec/PumpSpec, 解析推导收拢单源); 默认路径支持环境变量
    FLOWIO_TRUTH 覆盖 (TruthSource 语义)。

    M2: 阀/泵条目增补 group/role/power_w/pressure_kpa(/refs/flow_lpm) 投影字段
    —— dict 保持"单源完整投影"地位, actuators._pairs_from_params 由此无损还原
    frozen spec (无第二份手抄值); 既有键集/值不变 (消费侧零改动)。
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
                "group": spec.group,
                "role": spec.role,
                "i_rated": spec.rated_current_a,
                "v_rated": spec.rated_v,
                "v_range": list(spec.v_range),
                "r_coil": spec.r_coil,
                "power_w": spec.power_w,
                "pressure_kpa": list(spec.pressure_kpa),
            }
            if _CH_REF.match(ref):
                params["channels"].append(ref)
    params["channels"].sort()
    pump = pump_spec(pd)
    params["pump"] = {
        "model": pump.model,
        "role": pump.role,
        "refs": list(pump.refs),
        "i_load": pump.load_current_a,
        "v_rated": pump.rated_v,
        "v_range": list(pump.v_range),
        "power_w": pump.power_w,
        "pressure_kpa": list(pump.pressure_kpa),
        "flow_lpm": pump.flow_lpm,
    }
    if not params["valves"] or not params["channels"]:
        raise ValueError("pneumatic_devices 阀条目缺失 (单源加载失败)")
    return params


# ---- 准静态求解核心 -----------------------------------------------------------
def _solve(p, valves, pump_duty, p_manifold_kpa, actuators):
    """给定场景求母线电气解 (与旧 electrical_sim.simulate 逐行同构, 位级一致)。

    valves: {ref: state} state ∈ VALVE_STATES (未列出的阀=off)
    pump_duty: 泵请求占空比 (0~1, 会被钳 ≤95% 并施加互锁/过压路径)
    p_manifold_kpa: 歧管压力 (gauge), 过压/真空钳位判据
    """
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

    # ---- 执行器解 (多态核心 §3.4①): 仿真器只见 IActuator, 不认识具体阀型 ----
    # 阀 = 位号在阀表的执行器; 泵 = 其余 (位号路由, 型号无关; 无执行器注入时
    # 退回参数直解, 与旧实现数值同式)。报告字段 duty/eff_v 与 i_a 同源取自
    # 执行器 (a.duty 报告钩子) —— 注入异构执行器时不再旁抄 p["duties"] 策略表
    # (M2-R①; 内置型号两源恒等, 对拍值不动)。
    valve_acts = [a for a in actuators if a.ref in states]
    pump_acts = [a for a in actuators if a.ref not in states]
    acts_out, i_valves = {}, 0.0
    for a in valve_acts:                                 # Σ a.current(state), 零 if 型号分支
        st = states[a.ref]
        duty = a.duty(st)                                # 报告钩子 (与 i_a 同源)
        eff_v = a.effective_v(duty)                      # 共享实现 (中间基类)
        i_a = a.current(st)                              # 多态: D=10Ω / B=15Ω 各自解
        i_valves += i_a
        acts_out[a.ref] = {
            "state": st, "duty": round(duty, 4), "eff_v": round(eff_v, 4),
            "i_a": round(i_a, 4), "p_w": round(eff_v * i_a, 4),
            "p_peak_w": round(p["rail_v"] * i_a, 4),     # on 相瞬时 (rail × i)
            "steady": st in ("full_open", "economy"),    # 稳态 = 保持态 (断言②作用域)
            "hold_economy": st == "economy",             # 有意欠压标记 (豁免 4.05V 下限)
            "transient_ms": p["pull_in_ms"] if st == "pull_in" else 0.0,
        }
    pump_i = (pump_acts[0].current_at(duty_eff) if pump_acts
              else duty_eff * p["pump"]["i_load"])
    pump_eff_v = pump_acts[0].effective_v(duty_eff) if pump_acts \
        else duty_eff * p["rail_v"]
    i_total = i_valves + pump_i

    # ---- 断言①的语义: 超限检测与告警 (最坏场景是物理事实, 检测它而非回避它) ----
    over_limit = i_total > ADAPTER_A
    if over_limit:
        alarms.append(ALARM_OVERLOAD)
        eco_i = (sum(acts_out[a.ref]["i_a"] for a in valve_acts if states[a.ref] != "off")
                 * p["duties"]["economy"] / p["duties"]["full_open"] + pump_i)
        advice.append(
            f"受限模式: 母线 {i_total:.2f}A > {ADAPTER_A:.1f}A 档 —— 错峰: 并发全开保持 ≤4 通道")
        advice.append(
            f"或降节能保持 {p['duties']['economy']:.0%} (等效电流约 {eco_i:.2f}A ≤ {ADAPTER_A:.1f}A)")
        advice.append("BRINGUP 实测最小可靠保持占空比后再定适配器档 (3A/4A/5A)")
    pump = {
        "duty_req": round(duty_req, 4), "duty_eff": round(duty_eff, 4),
        "eff_v": round(pump_eff_v, 4), "i_a": round(pump_i, 4),
        "p_w": round(pump_eff_v * pump_i, 4),
        "interlock": interlock, "overpressure_stop": op_stop, "vacuum_stop": vac_stop,
    }
    return {
        "bus": {"i_total_a": round(i_total, 4), "i_valves_a": round(i_valves, 4),
                "i_pump_a": round(pump_i, 4),
                "p_w": round(sum(x["p_w"] for x in acts_out.values()) + pump["p_w"], 4),
                "limit_a": ADAPTER_A},
        "actuators": acts_out, "pump": pump,
        "alarms": alarms, "alarm_names": [ALARM_NAMES[x] for x in alarms],
        "over_limit": over_limit, "advice": advice,
    }


class ElectricalModel(BaseModel):
    """准静态母线解 (ElectricalModel, spec §3.2: electrical_sim 重构形态)。

    BaseModel 三方法:
      * params() —— 参数单源视图 (load_params dict; self._params 为 None 时
        每次现读真值 = 无缓存纪律, 断言⑤ '改库即改仿真' 保持);
      * step(dt, inputs) —— 准静态 (dt 被忽略), inputs =
        {valves: {ref: state}, pump_duty: float, p_manifold_kpa: float};
      * reset() —— 准静态无内部状态, 空操作 (场景重放天然幂等)。

    actuators 注入位: 默认从 params/truth 构建 (build_actuators); 注入自定义
    IActuator 列表即接入未来执行器 (比例阀/无刷泵) —— 仿真器零改 (spec §3.4①)。
    """

    def __init__(self, params=None, actuators=None):
        self._params = params            # None = 每次求解现读真值 (禁缓存)
        self._actuators = actuators      # None = 每次求解由 params/truth 构建

    def params(self) -> dict:
        """参数单源视图 (devices.json 投影, 禁手抄)。"""
        return self._params if self._params is not None else load_params()

    @property
    def actuators(self) -> list:
        """执行器列表 (list[IActuator]; 11 阀 + 泵, 真值条目序)。"""
        if self._actuators is not None:
            return self._actuators
        return build_actuators(params=self.params())

    def step(self, dt: float, inputs: dict) -> dict:
        """推进一"步" (准静态: dt 不参与, 输入即解)。返回场景解 (见 _solve)。"""
        inputs = inputs or {}
        return self.solve(inputs.get("valves"), inputs.get("pump_duty", 0.0),
                          p_manifold_kpa=inputs.get("p_manifold_kpa", 0.0))

    def reset(self) -> None:
        """准静态无状态 —— 空操作 (BaseModel 契约)。"""

    def solve(self, valves, pump_duty, p_manifold_kpa=0.0):
        """给定场景求母线电气解 (旧 simulate 语义; params/actuators 单次快照)。"""
        p = self.params()
        acts = self._actuators if self._actuators is not None \
            else build_actuators(params=p)
        return _solve(p, valves, pump_duty, p_manifold_kpa, acts)


def simulate(valves, pump_duty, params=None, p_manifold_kpa=0.0):
    """旧 API 兼容 (electrical_sim.simulate 同签名同返回; 薄壳 re-export 目标)。

    valves: {ref: state} state ∈ {off, pull_in, full_open, economy} (未列出的阀=off)
    pump_duty: 泵请求占空比 (0~1, 会被钳 ≤95% 并施加互锁/过压路径)
    p_manifold_kpa: 歧管压力 (gauge), 过压/真空钳位判据
    返回: {bus, actuators, pump, alarms, alarm_names, over_limit, advice, limit_a}
    """
    return ElectricalModel(params).solve(valves, pump_duty,
                                         p_manifold_kpa=p_manifold_kpa)
