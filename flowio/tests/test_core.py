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
import copy
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio import (BaseModel, FlowioError, GeomError, IActuator, ISensor,  # noqa: E402
                    RouteError, SimError, TruthError, TruthSource)
from flowio.truth import (DrivePolicy, PumpSpec, SensorSpec, ValveSpec,  # noqa: E402
                          drive_policy, pump_spec, sensor_spec, valve_specs)

TRUTH_JSON = ROOT / "hardware" / "flowio-p1" / "enclosure" / "devices.json"


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


# ══════════ 3. TruthSource: 封装载载+校验+只读 ══════════
def test_truthsource_default_path_and_sections():
    """默认路径解析到仓库根真值文件; 两段属性可读且形态正确。"""
    ts = TruthSource()
    assert ts.path == TRUTH_JSON and ts.path.is_file()
    devs = ts.devices
    assert isinstance(devs, list) and len(devs) == 34       # T1 锚: 34 唯一 C 号条目
    pn = ts.pneumatic_devices
    assert isinstance(pn, dict)
    assert {"valves", "valve_vacuum_master", "pump", "sensor"} <= set(pn)


def test_truthsource_readonly():
    """只读性: 公共属性赋值必抛 AttributeError; 深只读: 污染返回值不影响源。"""
    ts = TruthSource()
    for attr in ("devices", "pneumatic_devices", "path"):
        with _must_raise(AttributeError, "TruthSource.%s 只读, 赋值必抛" % attr):
            setattr(ts, attr, [])
    ts.devices.append({"evil": True})                        # 改的是深拷贝
    ts.pneumatic_devices["valves"] = []
    assert len(ts.devices) == 34                             # 源未被污染
    assert len(ts.pneumatic_devices["valves"]) == 1


def test_truthsource_env_override():
    """FLOWIO_TRUTH 环境变量覆盖默认路径 (副本亦可正常加载校验)。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "devices.json"
        tmp.write_bytes(TRUTH_JSON.read_bytes())
        os.environ["FLOWIO_TRUTH"] = str(tmp)
        try:
            ts = TruthSource()
            assert ts.path == tmp
            assert len(ts.devices) == 34
        finally:
            del os.environ["FLOWIO_TRUTH"]
    assert TruthSource().path == TRUTH_JSON                  # 解除后回到默认


def test_truthsource_fail_loud():
    """错误路径一律 TruthError (缺文件/坏 JSON/缺段/校验失败), 禁静默兜底。"""
    # a) 文件不存在
    with _must_raise(TruthError, "缺文件"):
        TruthSource(ROOT / ".tmp_no_such_truth.json").devices
    with tempfile.TemporaryDirectory() as td:
        # b) 非法 JSON
        bad = Path(td) / "bad.json"
        bad.write_text('{"devices": [  未闭合', encoding="utf-8")
        with _must_raise(TruthError, "坏 JSON"):
            TruthSource(bad).devices
        # c) schema 校验失败: 执行器 rated_v 改 3.7V (≠DC4.5V 档)
        doc = json.loads(TRUTH_JSON.read_text(encoding="utf-8"))
        doc["pneumatic_devices"]["valves"][0]["electrical"]["rated_v"] = 3.7
        bad2 = Path(td) / "rated.json"
        bad2.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        with _must_raise(TruthError, "电压档校验须失败"):
            TruthSource(bad2).devices
        # d) 缺 pneumatic_devices 段
        doc2 = {"devices": doc["devices"]}
        bad3 = Path(td) / "noseg.json"
        bad3.write_text(json.dumps(doc2), encoding="utf-8")
        with _must_raise(TruthError, "缺 pneumatic_devices 段"):
            TruthSource(bad3).devices
        # e) 删 drive_policy.pump.soft_start 键 → 校验层即拦截 (缺键=违例,
        #    禁静默默认 pump_soft_start=False —— M0 质量修复回归锚)
        doc3 = json.loads(TRUTH_JSON.read_text(encoding="utf-8"))
        del doc3["pneumatic_devices"]["_meta"]["drive_policy"]["pump"]["soft_start"]
        bad4 = Path(td) / "nosoftstart.json"
        bad4.write_text(json.dumps(doc3, ensure_ascii=False), encoding="utf-8")
        with _must_raise(TruthError, "缺 soft_start 键须校验失败"):
            TruthSource(bad4).devices


# ══════════ 4. views: pneumatic 条目视图 (锚点值 = devices.json 冻结基线) ══════════
def test_views_valve_spec():
    """11 阀 refs 全展开; F0520D 10Ω / F0520B 15Ω r_coil 推导单源。"""
    specs = valve_specs(TruthSource().pneumatic_devices)
    by_ref = {ref: s for s in specs for ref in s.refs}
    assert set(by_ref) == {"V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
                           "VS", "VF", "VV"}
    d = by_ref["V1"]
    assert d.model == "F0520D-DC4.5V" and d.group == "valves"
    assert abs(d.rated_current_a - 0.45) < 1e-12 and abs(d.rated_v - 4.5) < 1e-12
    assert abs(d.r_coil - 10.0) < 1e-9                       # 4.5/0.45 推导
    assert tuple(d.pressure_kpa) == (0.0, 45.0) and tuple(d.v_range) == (4.05, 4.95)
    b = by_ref["VV"]
    assert b.model == "F0520B-DC4.5V" and b.group == "valve_vacuum_master"
    assert abs(b.rated_current_a - 0.30) < 1e-12 and abs(b.r_coil - 15.0) < 1e-9
    assert tuple(b.pressure_kpa) == (-45.0, 0.0)


def test_views_pump_sensor_spec():
    pn = TruthSource().pneumatic_devices
    p = pump_spec(pn)
    assert p.model == "ZR370-03PM-DC4.5V" and p.refs == ("P1",)
    assert abs(p.load_current_a - 0.5) < 1e-12 and abs(p.flow_lpm - 2.8) < 1e-12
    assert tuple(p.pressure_kpa) == (-60.0, 120.0)           # 死头包络两类阀
    s = sensor_spec(pn)
    assert s.model.startswith("XGZP6897D") and s.i2c_addr == "0x6D"
    assert s.data_bits == 24 and tuple(s.v_range) == (2.5, 5.5)


def test_views_drive_policy():
    dp = drive_policy(TruthSource().pneumatic_devices)
    assert isinstance(dp, DrivePolicy)
    assert abs(dp.rail_v - 5.0) < 1e-12
    assert abs(dp.duties["pull_in"] - 1.0) < 1e-9            # 100% ≤100ms
    assert abs(dp.duties["full_open"] - 0.90) < 1e-9
    assert abs(dp.duties["economy"] - 0.55) < 1e-9
    assert dp.pull_in_ms == 100.0
    assert abs(dp.pump_max_duty - 0.95) < 1e-9 and dp.pump_soft_start is True


def test_views_fail_loud():
    """视图解析失败 → TruthError (无百分比/缺泵段/缺 soft_start 键)。"""
    pn = TruthSource().pneumatic_devices
    bad = copy.deepcopy(pn)
    bad["_meta"]["drive_policy"]["valve"]["pull_in"] = "满开"   # 无百分比
    with _must_raise(TruthError, "pull_in 无百分比须 TruthError"):
        drive_policy(bad)
    bad2 = copy.deepcopy(pn)
    del bad2["pump"]
    with _must_raise(TruthError, "泵条目缺失须 TruthError"):
        pump_spec(bad2)
    # 缺 soft_start 键 → 硬取 KeyError → TruthError (M0 质量修复回归锚:
    # 恢复旧 electrical_sim 的 fail-loud, 禁 .get 静默默认 False)
    bad3 = copy.deepcopy(pn)
    del bad3["_meta"]["drive_policy"]["pump"]["soft_start"]
    with _must_raise(TruthError, "缺 soft_start 键视图硬取须 TruthError"):
        drive_policy(bad3)


if __name__ == "__main__":
    test_errors_hierarchy()
    test_interfaces_abc_rejects_instantiation()
    test_iactuator_contract()
    test_iactuator_polymorphism_anchor()
    test_isensor_contract()
    test_basemodel_contract()
    test_truthsource_default_path_and_sections()
    test_truthsource_readonly()
    test_truthsource_env_override()
    test_truthsource_fail_loud()
    test_views_valve_spec()
    test_views_pump_sensor_spec()
    test_views_drive_policy()
    test_views_fail_loud()
    print("flowio core tests OK (errors + interfaces + TruthSource + views)")
