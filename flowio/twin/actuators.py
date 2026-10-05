# -*- coding: utf-8 -*-
"""flowio.twin.actuators — IActuator 参数化子类族 (spec v2.1 §3.2 继承, M2)。

类图 (继承):
    IActuator (core ABC, 抽象)
      └─ _DutyActuator            中间基类 (抽象): rail 注入 + effective_v=duty×rail
           ├─ _ValveActuator      阀族共享 (抽象): 四态 duty 表 + I=V_eff/R_coil
           │    ├─ ValveF0520D    F0520D-DC4.5V  rated 0.45A → r_coil 10Ω (V1-V8/VS/VF)
           │    └─ ValveF0520B    F0520B-DC4.5V  rated 0.30A → r_coil 15Ω (VV 真空主阀)
           └─ PumpZR370           ZR370-03PM     load 0.5A, 电流随占空比线性

设计裁决 (任务书要求说明):
  * effective_v 共享实现放**中间基类**而非 mixin —— effective_v 是阀/泵共同的
    PWM 物理本质 (单一继承链即可表达 "占空比×轨压驱动的执行器" is-a 关系);
    mixin 留给正交能力组合 (如未来 ISensor 的 I2C 协议注入), 此处用继承语义更准。
  * 四态电流差异化放**叶子子类** (多态): D/B 仅 spec 参数不同 (参数化子类,
    spec §3.2 "差异只在 TruthView 参数"), 泵是异构电流模型 (duty×i_load)。

封装 (spec §3.3): 构造注入 frozen spec (ValveSpec/PumpSpec) + DrivePolicy,
实例无常驻可变状态 —— current() 纯函数 (同输入同输出), 工作状态由调用方
(ElectricalModel/场景层) 持有; 器件值单源 = flowio.truth 视图 (禁手抄)。

多态 (spec §3.4 ①): 场景仿真器只做 sum(a.current(s) for a in actuators),
不认识 D/B/泵型号 —— 新执行器 (无刷泵/比例阀) = 新子类 + 真值条目, 零改仿真器。
"""
from flowio.core.interfaces import IActuator
from flowio.truth.views import DrivePolicy, PumpSpec, ValveSpec

# 基态别名: 孪生域现行 "full_open" 即 canonical "hold" (core.interfaces M0 契约)
_LEGACY_ALIAS = {"full_open": "hold"}

# canonical 四态 (IActuator.current 契约)
CANON_STATES = ("pull_in", "hold", "economy", "off")


def _canon(state):
    """状态规范化: full_open→hold 别名归一; 非法类型/值 fail-loud。"""
    if not isinstance(state, str):
        raise TypeError("执行器状态必须是 str, 实得 %r" % (state,))
    st = _LEGACY_ALIAS.get(state, state)
    if st not in CANON_STATES:
        raise ValueError("非法执行器状态 %r (∈ %s; full_open=hold 别名)"
                         % (state, "/".join(CANON_STATES)))
    return st


class _DutyActuator(IActuator):
    """中间基类 (抽象): 占空比驱动执行器 —— rail 注入 + PWM 调制共享实现。"""

    def __init__(self, spec, policy: DrivePolicy, ref: str = ""):
        self._spec = spec                                   # frozen spec (封装)
        self._ref = str(ref) if ref else spec.refs[0]
        self._rail_v = float(policy.rail_v)

    @property
    def ref(self) -> str:
        """位号 (真值 refs 的单条展开)。"""
        return self._ref

    @property
    def spec(self):
        """注入的 frozen spec (只读暴露; dataclass frozen, 调用方改不动)。"""
        return self._spec

    def effective_v(self, duty: float) -> float:
        """有效电压 = duty × 母线轨压 (PWM 调制; 与型号无关 → 共享实现)。"""
        return float(duty) * self._rail_v


class _ValveActuator(_DutyActuator):
    """阀族共享 (抽象): 四态电流 I = duty(state)·rail / R_coil (线圈欧姆模型)。"""

    def __init__(self, spec: ValveSpec, policy: DrivePolicy, ref: str = ""):
        super().__init__(spec, policy, ref)
        d = policy.duties                                   # {pull_in, full_open, economy}
        self._duty_of = {"pull_in": d["pull_in"], "hold": d["full_open"],
                         "economy": d["economy"], "off": 0.0}

    def duty(self, state: str) -> float:
        """状态 → 占空比 (canonical hold ← drive_policy.full_open_hold)。"""
        return self._duty_of[_canon(state)]

    def current(self, state: str) -> float:
        """四态电流 (多态点: r_coil 由各自 spec 决定, 本方法零 if 型号分支)。"""
        duty = self.duty(state)
        return self.effective_v(duty) / self._spec.r_coil


class ValveF0520D(_ValveActuator):
    """F0520D-DC4.5V (rated 4.5V/0.45A → r_coil 10Ω): V1-V8 通道/VS 供气/VF 排气。"""

    _MODEL_TAG = "F0520D"

    def __init__(self, spec: ValveSpec, policy: DrivePolicy, ref: str = ""):
        if self._MODEL_TAG not in str(spec.model):         # 型号防呆 (fail-loud)
            raise ValueError("ValveF0520D 收到异型 spec %r (期望型号含 %r)"
                             % (spec.model, self._MODEL_TAG))
        super().__init__(spec, policy, ref)


class ValveF0520B(_ValveActuator):
    """F0520B-DC4.5V (rated 4.5V/0.30A → r_coil 15Ω): VV 真空主阀。"""

    _MODEL_TAG = "F0520B"

    def __init__(self, spec: ValveSpec, policy: DrivePolicy, ref: str = ""):
        if self._MODEL_TAG not in str(spec.model):
            raise ValueError("ValveF0520B 收到异型 spec %r (期望型号含 %r)"
                             % (spec.model, self._MODEL_TAG))
        super().__init__(spec, policy, ref)


class PumpZR370(_DutyActuator):
    """ZR370-03PM (load 0.5A, 充吸双口): 电流随占空比线性 duty × i_load。

    状态协议: off→0A / hold→pump_max_duty(95%)×i_load=0.475A / pull_in→100%×i_load;
    economy 对泵无定义 (ValueError)。连续占空比路径经 current_at(duty)
    (ElectricalModel 泵钳位/互锁/过压判定后求流; 子类扩展, 不破坏 ABC 契约)。
    """

    _MODEL_TAG = "ZR370"

    def __init__(self, spec: PumpSpec, policy: DrivePolicy, ref: str = ""):
        if self._MODEL_TAG not in str(spec.model):
            raise ValueError("PumpZR370 收到异型 spec %r (期望型号含 %r)"
                             % (spec.model, self._MODEL_TAG))
        super().__init__(spec, policy, ref)
        self._duty_max = float(policy.pump_max_duty)

    def current_at(self, duty: float) -> float:
        """连续占空比 → 电流 (线性负载模型)。"""
        return float(duty) * self._spec.load_current_a

    def current(self, state: str) -> float:
        st = _canon(state)
        if st == "off":
            return 0.0
        if st == "economy":
            raise ValueError("泵 %s 无 economy 态 (∈ off/hold/pull_in)" % self.ref)
        return self.current_at(1.0 if st == "pull_in" else self._duty_max)


# ---- 工厂 --------------------------------------------------------------------
_VALVE_CLASSES = (("F0520D", ValveF0520D), ("F0520B", ValveF0520B))


def _valve_class(model: str):
    """型号串 → 阀子类; 未知型号 fail-loud (新阀型 = 新增子类 + 此表登记)。"""
    for tag, cls in _VALVE_CLASSES:
        if tag in str(model):
            return cls
    raise ValueError("未知阀型号 %r —— 接入步骤: 新增 IActuator 子类 + 真值条目"
                     "+ 本表登记 (spec §3.4① 零改仿真器)" % (model,))


def _pairs_from_params(p: dict):
    """load_params 结果 dict → ([(ref, ValveSpec)], PumpSpec, DrivePolicy)。

    dict 是 params 单源视图 (BaseModel.params 契约); 本函数把扁平投影还原为
    frozen spec —— 同一构造路径服务 truth 与 dict 两入口 (无第二份手抄值)。
    """
    vs = []
    for ref, vp in p["valves"].items():
        vs.append((ref, ValveSpec(
            refs=(ref,), model=vp["model"], group=vp.get("group", ""),
            role=vp.get("role", ""), rated_v=vp["v_rated"],
            rated_current_a=vp["i_rated"], v_range=tuple(vp["v_range"]),
            power_w=vp.get("power_w", 0.0),
            pressure_kpa=tuple(vp.get("pressure_kpa", ())),
        )))
    pp = p["pump"]
    ps = PumpSpec(
        refs=tuple(pp.get("refs", ("P1",))), model=pp["model"],
        role=pp.get("role", ""), rated_v=pp["v_rated"],
        load_current_a=pp["i_load"], v_range=tuple(pp["v_range"]),
        power_w=pp.get("power_w", 0.0),
        pressure_kpa=tuple(pp.get("pressure_kpa", ())),
        flow_lpm=pp.get("flow_lpm", 0.0),
    )
    dp = DrivePolicy(rail_v=p["rail_v"], duties=dict(p["duties"]),
                     pull_in_ms=p["pull_in_ms"],
                     pump_max_duty=p["pump_max_duty"],
                     pump_soft_start=p["pump_soft_start"])
    return vs, ps, dp


def build_actuators(truth=None, params=None) -> list:
    """执行器工厂: TruthSource 视图 (或 load_params 结果 dict) → 11 阀 + 泵。

    truth:  TruthSource 实例 (默认真值); params: load_params() 结果 dict
    (test_electrical_sim 断言⑤ '改库即改仿真' 经 dict 路径同样跟随)。
    顺序 = 真值条目序 (V1-V8/VS/VF → VV → P1) —— 与旧 electrical_sim 的
    states 迭代序一致 (母线求和位级对拍依赖此序)。
    """
    if params is not None:
        pairs, ps, dp = _pairs_from_params(params)
    else:
        from flowio.core.truth import TruthSource           # 懒导入 (仅 truth 路径)
        from flowio.truth import drive_policy, pump_spec, valve_specs
        pn = (truth if truth is not None else TruthSource()).pneumatic_devices
        specs, ps, dp = valve_specs(pn), pump_spec(pn), drive_policy(pn)
        pairs = [(ref, spec) for spec in specs for ref in spec.refs]
    out = []
    for ref, spec in pairs:
        out.append(_valve_class(spec.model)(spec, dp, ref=ref))
    out.append(PumpZR370(ps, dp, ref=ps.refs[0] if ps.refs else "P1"))
    return out
