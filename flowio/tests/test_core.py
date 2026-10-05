# -*- coding: utf-8 -*-
"""test_core — flowio M0 核心抽象层 TDD 测试 (spec v2.1 §3, 无 pytest 用 assert)。

红/绿纪律: 本文件先行 (红 = flowio 包未实现时 import 即败), 实现后全绿。
运行: python flowio/tests/test_core.py   (任意 cwd, stdlib-only)

覆盖 (M0 验收分段追加):
  1. errors      — 域异常层次: TruthError/GeomError/RouteError/SimError ⊂ FlowioError ⊂ RuntimeError;
  2. interfaces  — 纯 ABC: 不可直接实例化/缺抽象方法不可实例化/最小实现可用
                   (IActuator.current/effective_v/ref, ISensor.read+protocol 注入位,
                    BaseModel.params/step/reset) + 多态锚点 (sum(current) 零 if-else);
  3. truthsource — 只读属性 (赋值必抛)/深只读 (改返回值不污染源)/FLOWIO_TRUTH 覆盖/
                   错误路径 (缺文件/坏 JSON/校验失败 → TruthError fail-loud);
  4. views       — ValveSpec(r_coil 推导)/PumpSpec/SensorSpec/DrivePolicy 视图锚点值。
"""
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio import (BaseModel, FlowioError, GeomError, IActuator, ISensor,  # noqa: E402
                    RouteError, SimError, TruthError)


@contextmanager
def _must_raise(exc_type, what):
    """断言 with 体必抛 exc_type (否则 AssertionError)。"""
    try:
        yield
    except exc_type:
        pass
    else:
        raise AssertionError("%s: 应抛 %s" % (what, exc_type.__name__))


# ══════════ 1. errors: 域异常层次 ══════════
def test_errors_hierarchy():
    """四域异常 ⊂ FlowioError ⊂ RuntimeError —— 公共根统一捕获 + 兼容既有语义。"""
    for exc in (FlowioError, TruthError, GeomError, RouteError, SimError):
        assert issubclass(exc, RuntimeError), exc
    for exc in (TruthError, GeomError, RouteError, SimError):
        assert issubclass(exc, FlowioError), exc
    with _must_raise(FlowioError, "TruthError 须被公共根 FlowioError 捕获"):
        raise TruthError("devices.json 损坏")
    with _must_raise(RuntimeError, "SimError 须保持 RuntimeError 兼容语义"):
        raise SimError("步进修散")


# ══════════ 2. interfaces: 纯 ABC 契约 ══════════
def test_interfaces_abc_rejects_instantiation():
    """纯 ABC: 直接实例化 / 缺抽象方法的子类实例化 → TypeError。"""
    for cls in (IActuator, ISensor, BaseModel):
        with _must_raise(TypeError, "%s 是 ABC 不可直接实例化" % cls.__name__):
            cls()

    class _HalfValve(IActuator):                 # 只实现 current, 缺 effective_v/ref
        def current(self, state):
            return 0.0

    with _must_raise(TypeError, "缺抽象方法的子类不可实例化"):
        _HalfValve("V1")


class _ValveStub(IActuator):
    """最小合法实现 (M0 接口契约验证用; M2 由 Valve 参数化子类取代)。
    电流锚点 = devices.json F0520D: 10Ω 线圈, 90% 保持 4.5V=额定 → 450mA。"""
    _DUTY = {"pull_in": 1.0, "hold": 0.9, "economy": 0.55, "off": 0.0}

    def __init__(self, ref, rail_v=5.0, r_coil=10.0):
        self._ref, self._rail, self._r = ref, rail_v, r_coil

    @property
    def ref(self):
        return self._ref

    def current(self, state):
        return self.effective_v(self._DUTY[state]) / self._r

    def effective_v(self, duty):
        return duty * self._rail


class _PumpStub(IActuator):
    """异构执行器 (泵): 证明多态锚点对新类型零改调用方 (spec §3.4-①)。"""

    def __init__(self, ref="P1"):
        self._ref = ref

    @property
    def ref(self):
        return self._ref

    def current(self, state):
        return 0.475 if state != "off" else 0.0    # 95% × 0.5A 负载

    def effective_v(self, duty):
        return duty * 5.0


class _PressureSensorStub(ISensor):
    protocol = None                               # 注入位 (M0 占位; M2 绑 I2C 协议对象)

    def read(self):
        return {"p_kpa": 0.0, "t_c": 25.0, "raw": 0}


class _FirstOrderModelStub(BaseModel):
    def __init__(self):
        self._t = 0.0

    def params(self):
        return {"tau_s": 1.0, "rail_v": 5.0}

    def step(self, dt, inputs):
        self._t += float(dt)
        return {"t_s": self._t, "in": dict(inputs)}

    def reset(self):
        self._t = 0.0


def test_iactuator_contract():
    v = _ValveStub("V1")
    assert v.ref == "V1"
    assert abs(v.effective_v(0.9) - 4.5) < 1e-12   # duty × rail
    assert abs(v.current("hold") - 0.45) < 1e-12   # 4.5V / 10Ω = 450mA 额定锚
    assert abs(v.current("off")) < 1e-12
    assert abs(v.current("economy") - 0.275) < 1e-12   # 2.75V / 10Ω (有意欠压)


def test_iactuator_polymorphism_anchor():
    """spec §3.4-① 多态锚点: sum(a.current(s)) 无 if-else, 新执行器类型零改仿真器。"""
    actuators = [_ValveStub("V1"), _ValveStub("VV", r_coil=15.0), _PumpStub()]
    total = sum(a.current("hold") for a in actuators)
    assert abs(total - (0.45 + 0.30 + 0.475)) < 1e-9   # 1.225A (single_vacuum 同源)


def test_isensor_contract():
    s = _PressureSensorStub()
    sample = s.read()
    assert isinstance(sample, dict) and {"p_kpa", "t_c"} <= set(sample)  # Sample = dict
    proto = object()
    s.protocol = proto                             # 注入位可绑协议对象
    assert s.protocol is proto


def test_basemodel_contract():
    m = _FirstOrderModelStub()
    assert m.params() == {"tau_s": 1.0, "rail_v": 5.0}
    assert m.step(0.5, {"i_a": 1.0})["t_s"] == 0.5
    m.step(0.25, {})
    m.reset()
    assert m.step(0.1, {})["t_s"] == 0.1           # reset 后从头计


if __name__ == "__main__":
    test_errors_hierarchy()
    test_interfaces_abc_rejects_instantiation()
    test_iactuator_contract()
    test_iactuator_polymorphism_anchor()
    test_isensor_contract()
    test_basemodel_contract()
    print("flowio core tests OK (errors hierarchy + interfaces ABC)")
