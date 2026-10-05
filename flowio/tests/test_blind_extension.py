# -*- coding: utf-8 -*-
"""test_blind_extension — M5 盲测: 新执行器类型三步接入零改仿真器 (核心验收)。

盲测语义 (spec v2.1 §5 M5 行 / 任务书 M5.4): 以假想"比例阀 PROPCV-01"为探针,
证明扩展点开放-封闭 —— 接入**只需**:
  第一步 (a) 真值条目 —— 临时真值副本加 pneumatic 条目 (走 valves 组 +
          rated_v=4.5 合规构造, schema 谓词全绿; 不动库内 devices.json);
  第二步 (b) IActuator 子类 —— 本测试文件内定义 (不入库, 不注册工厂);
  第三步 (c) 注入 —— ElectricalModel(actuators=[...]) 求解含它的场景;
仿真器/模型代码**零改** —— 本文件固化该证据: 扫描 flowio.twin 源码不含
PROPCV 型号串 (机器级守门, 未来任何重构若把型号知识写回仿真器立即红);
git diff 层面 M5 交付只有测试文件新增 (见 M5 报告)。

物理断言 (d): 比例阀电流 = I = V_eff / R_coil (欧姆解):
  rated 4.5V / 0.1A → R = 45Ω; hold(full_open) duty 0.9 → V_eff 4.5V → I 0.1A;
  pull_in duty 1.0 → 5.0V → 0.1111A; economy duty 0.55 → 2.75V → 0.0611A。

运行: python flowio/tests/test_blind_extension.py   (任意 cwd, stdlib-only)
"""
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from flowio import IActuator                                   # noqa: E402
from flowio.core.truth import TruthSource                      # noqa: E402
from flowio.truth import (drive_policy, document_problems,     # noqa: E402
                          valve_specs)
from flowio.twin.actuators import build_actuators              # noqa: E402
from flowio.twin.electrical import ElectricalModel, load_params  # noqa: E402

# 盲测假想器件参数 (语义占位: 连续比例控制; 电气解以 I=V_eff/R 接入)
PROPCV = {
    "refs": ["PV1"],
    "role": "M5 盲测假想比例阀 (扩展性验收探针, 非实装器件)",
    "model": "PROPCV-01",
    "manufacturer": "BLIND-TEST 占位 (无实厂)",
    "datasheet": "literature/PROPCV-01.pdf",          # 非空字符串 (谓词不查文件)
    "variant_note": "自定义语义占位: 连续比例控制; 盲测以欧姆解 I=V_eff/R 接入",
    "electrical": {"rated_v": 4.5, "v_range": [4.05, 4.95],
                   "rated_current_a": 0.1, "power_w": 0.45},
    # 正压域 (valves 组禁负压专用阀) 且 [0,45] ⊂ 泵 [-60,120] 压力包络 (余量>0)
    "pressure_kpa": [0, 45],
    "dims": {"w": 15.0, "d": 13.0, "h": 20.5},
    "port": {"type": "pneumatic", "dia_mm": 3.0,
             "dir_local_mounted": [0, 0, 1], "tube_id_mm": 3.0},
}

_SIMULATOR_SOURCES = [ROOT / "flowio" / "twin" / n
                      for n in ("electrical.py", "actuators.py", "scenarios.py",
                                "thermal.py", "pneumatic.py", "board.py")]


@contextmanager
def _must_raise(exc_type, what):
    try:
        yield
    except exc_type:
        pass
    else:
        raise AssertionError("%s: 应抛 %s" % (what, exc_type.__name__))


def _truth_copy_with_propcv(td) -> Path:
    """库内真值深拷贝 + PROPCV 条目 (写临时文件; 库内 devices.json 不动)。"""
    src = TruthSource()
    doc = json.loads(src.path.read_text(encoding="utf-8"))
    doc["pneumatic_devices"]["valves"].append(json.loads(json.dumps(PROPCV)))
    out = Path(td) / "devices-blind.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return out


# ════════ 第一步 (a): 真值条目 — schema 谓词接受合规构造 ════════
def test_step_a_truth_entry_passes_schema():
    """临时真值副本 + PROPCV → document_problems 空 (valves 组/rated_v 4.5 合规)。"""
    with tempfile.TemporaryDirectory() as td:
        p = _truth_copy_with_propcv(td)
        doc = json.loads(p.read_text(encoding="utf-8"))
        problems = document_problems(doc)
        assert problems == [], "假想条目应合规 (违例: %s)" % problems
        # TruthSource (含同源校验) 可正常加载; 视图可解出 45Ω 线圈
        src = TruthSource(str(p))
        specs = valve_specs(src.pneumatic_devices)
        pv = next(s for s in specs if "PV1" in s.refs)
        assert pv.model == "PROPCV-01" and pv.group == "valves"
        assert abs(pv.r_coil - 45.0) < 1e-12          # 4.5V / 0.1A


# ════════ 第二步 (b): IActuator 子类 (测试内定义, 不入库不注册) ════════
class ProportionalValve(IActuator):
    """PROPCV-01 比例阀 (盲测专用, 不入 flowio.twin.actuators)。

    语义占位: 与开关阀同一 PWM 策略表 (DrivePolicy), 电流取欧姆解
    I = V_eff / R_coil (R 来自真值 rated_v/rated_current_a 推导, 单源)。
    """

    def __init__(self, spec, policy, ref):
        self._spec, self._ref = spec, ref
        self._rail_v = float(policy.rail_v)
        d = policy.duties                       # {pull_in, full_open, economy}
        self._duty_of = {"pull_in": d["pull_in"], "full_open": d["full_open"],
                         "hold": d["full_open"], "economy": d["economy"],
                         "off": 0.0}

    @property
    def ref(self):
        return self._ref

    def duty(self, state):
        return self._duty_of[state]             # 报告钩子 (与 i_a 同源)

    def effective_v(self, duty):
        return float(duty) * self._rail_v       # PWM 调制 (5V 轨)

    def current(self, state):
        return self.effective_v(self.duty(state)) / self._spec.r_coil


# ════════ 第三步 (c) + 断言 (d): 注入求解, 零改仿真器 ════════
def test_step_bc_inject_and_solve_zero_model_change():
    """工厂 fail-loud → 注入求解 → I=V_eff/R 三态锚点 → 仿真器源码零型号串。"""
    with tempfile.TemporaryDirectory() as td:
        blind_path = _truth_copy_with_propcv(td)
        blind = TruthSource(str(blind_path))
        params_with_pv = load_params(str(blind_path))     # PV1 入位号表 (校验/路由)

        # 扩展点显式性: 未知型号走工厂必 fail-loud (新类型须子类+注入或注册,
        # 禁静默兜底) —— 这正是"零改仿真器"扩展契约的守门形态
        with _must_raise(ValueError, "工厂对未知型号须 fail-loud"):
            build_actuators(params=params_with_pv)

        # 注入: 库内 11 执行器 (原真值构建) + 盲测比例阀 (新子类实例)
        pv_spec = next(s for s in valve_specs(blind.pneumatic_devices)
                       if "PV1" in s.refs)
        dp = drive_policy(blind.pneumatic_devices)
        acts = build_actuators(params=load_params()) + \
            [ProportionalValve(pv_spec, dp, "PV1")]
        model = ElectricalModel(params_with_pv, actuators=acts)

        # 场景: PV1+V1 全开保持, 泵停 —— i_valves = 0.45 (V1) + 0.1 (PV1)
        r = model.solve({"PV1": "full_open", "V1": "full_open"}, 0.0)
        pv = r["actuators"]["PV1"]
        assert abs(pv["i_a"] - 0.1) < 1e-9, pv        # (d) I = 4.5V / 45Ω
        assert pv["duty"] == 0.9 and abs(pv["eff_v"] - 4.5) < 1e-9
        assert abs(pv["p_w"] - 0.45) < 1e-9           # 报告字段与电流同源自恰
        assert abs(r["bus"]["i_valves_a"] - 0.55) < 1e-9
        assert r["actuators"]["V1"]["i_a"] == 0.45    # 既有型号锚点不动
        assert r["over_limit"] is False

        # 三态全覆盖: pull_in 100% → 5.0V → 0.1111A / economy 55% → 2.75V
        # (报告字段按 _solve 契约 round 4 位 —— 与内置阀同舍入语义)
        r2 = model.solve({"PV1": "pull_in"}, 0.0)
        assert abs(r2["actuators"]["PV1"]["i_a"] - round(5.0 / 45.0, 4)) < 1e-12
        r3 = model.solve({"PV1": "economy"}, 0.0)
        assert abs(r3["actuators"]["PV1"]["i_a"] - round(2.75 / 45.0, 4)) < 1e-12
        assert r3["actuators"]["PV1"]["hold_economy"] is True

        # 零改仿真器的机器级证据: 孪生域源码不含 PROPCV 型号知识
        # (若未来重构把型号分支写回仿真器/模型 → 本扫描立即红)
        for src_file in _SIMULATOR_SOURCES:
            text = src_file.read_text(encoding="utf-8")
            assert "PROPCV" not in text, "%s 不得出现盲测型号串" % src_file.name


def test_blind_truth_is_temp_copy_only():
    """盲测不改库内真值: 库内 devices.json 无 PV1 (临时副本语义的回归锚)。"""
    lib = TruthSource().pneumatic_devices
    for g in ("valves", "valve_vacuum_master", "pump", "sensor"):
        for e in lib.get(g) or []:
            assert "PV1" not in (e.get("refs") or []), "库内真值被盲测污染"
    assert "PV1" not in load_params()["valves"]


if __name__ == "__main__":
    test_step_a_truth_entry_passes_schema()
    test_step_bc_inject_and_solve_zero_model_change()
    test_blind_truth_is_temp_copy_only()
    print("PASS test_blind_extension 3/3 (M5 盲测: 真值条目→子类→注入 零改仿真器; "
          "I=V_eff/R: hold 0.1A / pull_in 0.1111A / economy 0.0611A)")
