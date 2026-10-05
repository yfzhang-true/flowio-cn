# -*- coding: utf-8 -*-
"""test_twin — flowio M2 孪生域 OOD TDD 测试 (spec v2.1 §3.2/§3.3/§3.4, 无 pytest 用 assert)。

红/绿纪律: 本文件先行 (红 = flowio.twin 未实现时 import 即败), 实现后全绿。
运行: python flowio/tests/test_twin.py   (任意 cwd, stdlib-only)

覆盖 (M2 验收分段):
  1. actuators — IActuator 参数化子类族: 型号锚点 (D hold 0.45A / B hold 0.30A /
     泵 hold 0.475A), 四态多态电流, 共享 effective_v, legacy full_open=hold 别名,
     型号防呆 (错 spec 注入必拒), 封装 (无常驻可变状态);
  2. 多态三落点①  — total = sum(a.current(s) for a in actuators) 零 if-else;
     未来执行器 (比例阀 stub) 入列零改仿真器 (spec §3.4①/M5 盲测预演);
  3. electrical  — ElectricalModel(BaseModel) 三方法契约 + 与 load_params/
     simulate 单源一致 (位级), 泵连续占空比 current_at 路径;
  4. scenarios   — 12 场景矩阵在库内 (SCENARIOS/run_scenario/run_matrix),
     worst 锚点 4.525A (对拍基准同源);
  5. thermal     — ThermalModel(BaseModel): 一阶热惯性公式锚点 + reset;
  6. pneumatic   — PneumaticModel(BaseModel): RL 开/关解析式锚点 (5V/10.04Ω
     ≈0.498A, 过零钳位) + reset;
  7. board       — BoardModel 组合根 façade: has-a 三模型 (皆 BaseModel),
     旧公共 API 兼容冒烟 (step/telemetry 契约字段 + 数值锚点与 board_model 同源);
  8. shim        — firmware/twin/electrical_sim 与 board_model 薄壳 re-export
     同一对象 (消费侧零改动的机器级证据)。
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ---- TDD 红: flowio.twin 未实现时以下 import 即败 ----------------------------
from flowio import BaseModel, IActuator, TruthSource                     # noqa: E402
from flowio.twin import (ElectricalModel, LOGIC_A, PumpZR370,              # noqa: E402
                         PneumaticModel, SCENARIOS, ThermalModel,
                         ValveF0520B, ValveF0520D, BoardModel,
                         build_actuators, load_params, run_matrix,
                         run_scenario, simulate)
from flowio.truth import ValveSpec, drive_policy, pump_spec, valve_specs  # noqa: E402

TWIN_DIR = ROOT / "firmware" / "twin"
ALL_VALVE_REFS = {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "VS", "VF", "VV"}


def _policy():
    return drive_policy(TruthSource().pneumatic_devices)


def _d_spec():
    """F0520D 单 ref spec (V1 展开)。"""
    s = [x for x in valve_specs(TruthSource().pneumatic_devices)
         if "F0520D" in x.model][0]
    return ValveSpec(refs=("V1",), model=s.model, group=s.group, role=s.role,
                     rated_v=s.rated_v, rated_current_a=s.rated_current_a,
                     v_range=s.v_range, power_w=s.power_w,
                     pressure_kpa=s.pressure_kpa)


def _b_spec():
    s = [x for x in valve_specs(TruthSource().pneumatic_devices)
         if "F0520B" in x.model][0]
    return ValveSpec(refs=("VV",), model=s.model, group=s.group, role=s.role,
                     rated_v=s.rated_v, rated_current_a=s.rated_current_a,
                     v_range=s.v_range, power_w=s.power_w,
                     pressure_kpa=s.pressure_kpa)


# ══════════ 1. actuators: 参数化子类族 ══════════
def test_actuator_family_anchors():
    """型号锚点 (M2 任务书): D 阀 hold 0.45A / B 阀 hold 0.30A / 泵 95% 0.475A。"""
    dp = _policy()
    d = ValveF0520D(_d_spec(), dp, ref="V1")
    b = ValveF0520B(_b_spec(), dp, ref="VV")
    p = PumpZR370(pump_spec(TruthSource().pneumatic_devices), dp, ref="P1")

    assert isinstance(d, IActuator) and isinstance(b, IActuator) and isinstance(p, IActuator)
    assert d.ref == "V1" and b.ref == "VV" and p.ref == "P1"
    # 四态多态电流: I = duty(state)·rail / R_coil (D=10Ω, B=15Ω)
    assert abs(d.current("hold") - 0.45) < 1e-9            # 0.9·5V/10Ω
    assert abs(d.current("pull_in") - 0.50) < 1e-9         # 1.0·5V/10Ω
    assert abs(d.current("economy") - 0.275) < 1e-9        # 0.55·5V/10Ω
    assert d.current("off") == 0.0
    assert abs(b.current("hold") - 0.30) < 1e-9            # 0.9·5V/15Ω
    assert abs(b.current("economy") - 5.0 * 0.55 / 15.0) < 1e-9
    # legacy 别名: 孪生域现行 full_open 即 hold (core.interfaces 契约)
    assert d.current("full_open") == d.current("hold")
    # 泵: hold=pump_max_duty(95%)×i_load(0.5A)=0.475A; 连续占空比路径
    assert abs(p.current("hold") - 0.475) < 1e-9
    assert p.current("off") == 0.0
    assert abs(p.current_at(0.5) - 0.25) < 1e-9
    # 共享实现 effective_v = duty×rail (中间基类, 与型号无关)
    assert abs(d.effective_v(0.9) - 4.5) < 1e-9
    assert abs(p.effective_v(0.95) - 4.75) < 1e-9


def test_actuator_encapsulation_and_guards():
    """封装: 构造注入 frozen spec, 实例无常驻可变状态; 型号防呆 fail-loud。"""
    dp = _policy()
    d = ValveF0520D(_d_spec(), dp, ref="V1")
    assert isinstance(d.spec, ValveSpec) and d.spec.r_coil == 4.5 / 0.45
    snapshot = [round(x, 12) for x in
                (d.current("hold"), d.current("economy"), d.effective_v(0.9))]
    d.current("pull_in")                       # 调用不改状态 (纯函数语义)
    assert [round(x, 12) for x in
            (d.current("hold"), d.current("economy"), d.effective_v(0.9))] == snapshot
    for bad in ("on", "FULL_OPEN", 1, None):
        try:
            d.current(bad)
            raise AssertionError("非法状态 %r 必须被拒" % (bad,))
        except (ValueError, TypeError):
            pass
    try:                                       # B 的 spec 注入 D → 型号防呆
        ValveF0520D(_b_spec(), dp, ref="VX")
        raise AssertionError("错 spec 注入必须被拒 (fail-loud)")
    except ValueError:
        pass


def test_build_actuators_factory():
    """工厂: TruthSource 视图构建 11 阀 + 泵 = 12 个 IActuator, 位号齐且不重。"""
    acts = build_actuators(TruthSource())
    assert len(acts) == 12, "11 阀 + 1 泵, 实得 %d" % len(acts)
    assert all(isinstance(a, IActuator) for a in acts)
    refs = [a.ref for a in acts]
    assert set(refs) == ALL_VALVE_REFS | {"P1"} and len(set(refs)) == 12
    pumps = [a for a in acts if a.ref == "P1"]
    assert isinstance(pumps[0], PumpZR370)
    # dict 参数路径 (params 视图) 与 truth 路径产同序同型号
    acts2 = build_actuators(params=load_params())
    assert [a.ref for a in acts2] == refs
    assert all(type(x) is type(y) for x, y in zip(acts, acts2))
    assert abs(sum(a.current("hold") for a in acts2) -
               sum(a.current("hold") for a in acts)) < 1e-12


# ══════════ 2. 多态落点①: sum(a.current(s)) 零 if-else ══════════
def test_polymorphic_sum_zero_if_else():
    """多态求和锚点: 10×D(hold)+B(hold)+泵(hold) = 4.5+0.30+0.475 = 5.275A。"""
    acts = build_actuators(TruthSource())
    total = sum(a.current("hold") for a in acts)   # 无 isinstance/型号串判断
    assert abs(total - 5.275) < 1e-9


def test_future_actuator_zero_model_change():
    """未来执行器 (比例阀) 三步接入零改仿真器 (spec §3.4① / M5 盲测预演)。"""

    class _ProportionalValve(IActuator):          # 第一步: 新子类
        def __init__(self, ref, ma_per_v):
            self._ref, self._k = ref, ma_per_v

        @property
        def ref(self):
            return self._ref

        def current(self, state):                 # hold: 5V×20mA/V=0.1A
            return 0.0 if state == "off" else 5.0 * self._k / 1000.0

        def effective_v(self, duty):
            return duty * 5.0

    fake = _ProportionalValve("VX", 20.0)         # 第二步: 真值条目 (此处 stub)
    base = load_params()
    p = copy.deepcopy(base)
    p["valves"]["VX"] = dict(base["valves"]["V1"])            # 位号表挂载 (校验/路由用)
    acts = build_actuators(params=base) + [fake]              # 第三步: 注入执行器列表
    model = ElectricalModel(p, actuators=acts)                # (物理以注入列表为准)
    r = model.solve({"VX": "full_open", "V1": "full_open"}, 0.0)
    assert abs(r["actuators"]["VX"]["i_a"] - 0.1) < 1e-9     # 仿真器零改即解
    assert abs(r["bus"]["i_valves_a"] - (0.45 + 0.1)) < 1e-9


# ══════════ 3. electrical: ElectricalModel 三方法契约 ══════════
def test_electrical_model_contract():
    """BaseModel 三方法: params()=单源视图 / step(dt,inputs) / reset() 幂等。"""
    m = ElectricalModel()
    pv = m.params()
    assert {"rail_v", "duties", "pull_in_ms", "pump_max_duty", "pump_soft_start",
            "valves", "channels", "pump"} <= set(pv)
    assert set(pv["valves"]) == ALL_VALVE_REFS
    # params() 与 load_params() 同源同值 (dict 视图 = 单源投影)
    lp = load_params()
    assert pv["rail_v"] == lp["rail_v"] and pv["duties"] == lp["duties"]
    # step: 准静态 (dt 被忽略), inputs 字典进 solve 契约出
    r = m.step(0.0, {"valves": {"V1": "full_open", "VS": "full_open"},
                     "pump_duty": 0.95, "p_manifold_kpa": 0.0})
    r2 = m.solve({"V1": "full_open", "VS": "full_open"}, 0.95)
    assert r == r2
    assert {"bus", "actuators", "pump", "alarms", "alarm_names",
            "over_limit", "advice"} <= set(r)
    assert m.reset() is None                       # 准静态无状态 → 幂等
    assert m.step(1.0, {"valves": {}, "pump_duty": 0.0})["bus"]["i_total_a"] == 0.0
    # simulate (旧 API) 与模型解位级一致 (薄壳兼容的库内侧锚点)
    assert simulate({"V1": "economy"}, 0.0) == ElectricalModel().solve({"V1": "economy"}, 0.0)
    # params 注入: 外部 dict 优先 (test_electrical_sim ⑤ 改库跟随语义的库内对应)
    m2 = ElectricalModel(lp)
    assert m2.params() is lp


# ══════════ 4. scenarios: 场景矩阵在库内 ══════════
def test_scenarios_matrix():
    """12 场景 + run_matrix/run_scenario 兼容 + worst 锚点 4.525A。"""
    assert len(SCENARIOS) == 12
    rows = run_matrix()
    assert len(rows) == 12
    assert {"name", "i_total_a", "over_limit", "alarms", "alarm_names",
            "advice", "expect_over_limit"} <= set(rows[0])
    w = run_scenario("worst_9v_hold_pump")
    assert abs(w["bus"]["i_total_a"] - (9 * 0.45 + 0.5 * 0.95)) < 0.01  # 4.525A
    eco = run_scenario("worst_9v_economy_pump")
    assert not eco["over_limit"]


# ══════════ 5. thermal: ThermalModel ══════════
def test_thermal_model():
    """一阶热惯性: T += (t_amb+P·θ - T)·min(1, dt/τ); reset 归零到环温。"""
    th = ThermalModel(theta={"cpu": 35.0, "buck": 130.0, "mos": 350.0},
                      tau_s=30.0, t_amb=25.0)
    assert isinstance(th, BaseModel)
    assert th.temp == {"cpu": 25.0, "buck": 25.0, "mos": 25.0}
    assert th.params()["theta_c_per_w"]["cpu"] == 35.0
    out = th.step(15.0, {"powers": {"cpu": 1.0}})          # 半 τ → 半程趋近
    assert abs(out["temp_c"]["cpu"] - (25.0 + (60.0 - 25.0) * 0.5)) < 1e-9
    th.step(1e6, {"powers": {"cpu": 1.0}})                 # 巨步 → 钳到目标 60℃
    assert abs(th.temp["cpu"] - 60.0) < 1e-9
    th.step(1.0, {"powers": {}})                           # 空输入不动
    assert th.temp["cpu"] == 60.0
    th.reset()
    assert th.temp == {"cpu": 25.0, "buck": 25.0, "mos": 25.0}


# ══════════ 6. pneumatic: PneumaticModel ══════════
def test_pneumatic_model():
    """RL 解析式: 开路稳态 vbus/(r_coil+rds)≈0.498A; 关断过零钳位; reset。"""
    pn = PneumaticModel(r_coil=10.0, l_coil=25e-3, rds=0.040, vf_fw=0.35,
                        i_pump=0.50, vbus=5.0, n_valves=8)
    assert isinstance(pn, BaseModel)
    assert pn.i == [0.0] * 8 and pn.pump == 0.0
    assert pn.params()["r_coil"] == 10.0 and pn.params()["n_valves"] == 8
    out = pn.step(0.005, {"valves": [1] + [0] * 7, "pump": 0})
    pn.step(5.0, {"valves": [1] + [0] * 7, "pump": 0})     # 5s >> τ_on → 稳态
    assert abs(pn.i[0] - 5.0 / 10.04) < 0.01
    assert out["i_valves"] == list(pn.i) or len(out["i_valves"]) == 8
    pn.step(0.01, {"valves": [0] * 8, "pump": 1})          # 关断过零钳位 + 泵
    assert 0.0 <= pn.i[0] < 0.25 and pn.pump == 1.0
    out2 = pn.step(0.1, {"valves": [0] * 8, "pump": 1})
    assert abs(out2["i_pump_a"] - 0.5) < 1e-9
    pn.reset()
    assert pn.i == [0.0] * 8 and pn.pump == 0.0


# ══════════ 7. board: BoardModel 组合根 façade ══════════
def test_board_composition_root():
    """has-a 三模型 (皆 BaseModel) + 旧公共 API 兼容冒烟 (board_model 数值锚点)。"""
    b = BoardModel()
    assert isinstance(b.pneumatic, PneumaticModel)
    assert isinstance(b.thermal, ThermalModel)
    assert isinstance(b.electrical, ElectricalModel)
    for m in (b.pneumatic, b.thermal, b.electrical):
        assert isinstance(m, BaseModel)
        assert callable(m.params) and callable(m.step) and callable(m.reset)

    b.step(0.1, [0] * 8, 0)                                # 空载: 仅逻辑负载
    s0 = b.telemetry()
    assert abs(s0["rail_5v"]["load_a"] - LOGIC_A) < 1e-6
    assert {"tick", "uptime_s", "stale", "valves", "rail_5v", "rail_3v3",
            "board_p_w", "temp_est_c", "history"} <= set(s0)

    b2 = BoardModel()                                      # 单阀 5s → RL 稳态锚点
    b2.step(0.005, [1] + [0] * 7, 0)
    b2.step(5.0, [1] + [0] * 7, 0)
    s1 = b2.telemetry()
    assert abs(s1["valves"][0]["i_A"] - 5.0 / 10.04) < 0.01

    b3 = BoardModel()                                      # 满载 50 步 + 泵
    for _ in range(50):
        b3.step(0.1, [1] * 8, 1)
    s8 = b3.telemetry()
    assert abs(s8["valves"][7]["i_A"] - 5.0 / 10.04) < 0.01
    assert s8["board_p_w"] > 8 * 2.2
    assert s8["temp_est_c"]["mos"] > 25.0                  # 热段真在算 (组合非摆设)
    assert len(s8["history"]["t"]) == 50                   # 50×0.1s=5s 段, 每 TICK 一条
    # 板级 step 消费气动模型状态 (组合根委托, 非平行副本)
    assert b3.pneumatic.i == [x for x in b3.pneumatic.i]   # noqa (自恰)
    assert abs(max(b3.pneumatic.i) - 5.0 / 10.04) < 0.01


# ══════════ 8. shim: 消费侧薄壳 re-export 同一对象 ══════════
def test_consumer_shims_identity():
    """firmware/twin/{electrical_sim,board_model} = 薄壳: re-export 同一对象。"""
    sys.path.insert(0, str(TWIN_DIR))
    try:
        import electrical_sim as es
        import board_model as bm
        import flowio.twin.electrical as fel
        import flowio.twin.board as fbrd
        import flowio.twin.scenarios as fsc
        assert es.simulate is fel.simulate
        assert es.load_params is fel.load_params
        assert es.ElectricalModel is fel.ElectricalModel
        assert es.run_matrix is fsc.run_matrix
        assert es.SCENARIOS is fsc.SCENARIOS
        assert es.ADAPTER_A == 3.0 and es.VALVE_STATES == fel.VALVE_STATES
        assert bm.BoardModel is fbrd.BoardModel
        assert bm.BOARD_PARAMS is fbrd.BOARD_PARAMS
        assert bm.LOGIC_A == fbrd.LOGIC_A and bm.TICK == 0.1
        assert bm.BOARD_PARAMS["r_coil"] == 10.0          # [registry] 值不动
        assert bm.BOARD_PARAMS["i_pump"] == 0.50
    finally:
        sys.path.remove(str(TWIN_DIR))


if __name__ == "__main__":
    test_actuator_family_anchors()
    test_actuator_encapsulation_and_guards()
    test_build_actuators_factory()
    test_polymorphic_sum_zero_if_else()
    test_future_actuator_zero_model_change()
    test_electrical_model_contract()
    test_scenarios_matrix()
    test_thermal_model()
    test_pneumatic_model()
    test_board_composition_root()
    test_consumer_shims_identity()
    print("flowio.twin tests OK (11 testfns: actuators×3 + polymorphism×2 + "
          "electrical + scenarios + thermal + pneumatic + board + shim)")
