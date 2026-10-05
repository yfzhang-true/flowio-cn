# -*- coding: utf-8 -*-
"""harness — 电气线束视觉建模 (D1, spec §2.1; D2 裁定 A "引线桩"深度; FreeCAD Part)。

深度裁定 (D2-A "诚实的不精确"): 引线/电缆 = 两点视觉桩 (关键端点间直连), 2P 白壳 =
视觉件; 不做壳内真实走线 (P1.2 布局未冻结, 精确线长属机械冻结后阶段)。spec §2.1:
"阀 2P 引线 (~60mm 视觉桩) → J 插座; 泵电缆 J23 → 泵端子"。

两族 (通用连接件, 无 devices.json pneumatic 条目):
    阀引线桩   红黑双线 ⌀1.0 并排, 桩长默认 60mm (spec ~60mm), 端接 XH2.54-2P 白壳
               视觉件 10×7.8×6.2 (devices.json devices 段 C7429671 dims 单源读取);
    泵电缆     2 芯 ⌀1.5 并排, J23 → 泵电机端子, 默认 150mm (spec §3 electrical_edges
               示例 len_mm:150; F0520D 图纸引线 150±10 同带)。
接口 = 桩两端点 (D2 电气边端点: 插头/插座/端子)。
"""
import sys

import FreeCAD as App
import Part

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
import json as _json

_ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[3])
DEVICES_JSON = _ROOT + "/hardware/flowio-p1/enclosure/devices.json"

_LEAD_DIA, _LEAD_GAP = 1.0, 1.2       # 阀引线视觉径/并排间距 (F0520D.pdf p2 引线, 实物照)
_CABLE_DIA, _CABLE_GAP = 1.5, 1.8     # 泵电缆芯径/间距 (视觉值)


def _shell_dims():
    """XH2.54-2P 白壳 dims (单源: devices.json devices 段 lcsc C7429671)."""
    with open(DEVICES_JSON, encoding="utf-8") as f:
        for e in _json.load(f)["devices"]:
            if e.get("lcsc") == "C7429671":
                return e["dims"]      # {"w":10.0,"d":7.8,"h":6.2}
    raise RuntimeError("C7429671 (XH-2P) dims 缺失于 devices.json")


def DEFAULTS():
    return {
        "lead_len": 60.0, "lead_dia": _LEAD_DIA, "lead_gap": _LEAD_GAP,
        "cable_len": 150.0, "cable_dia": _CABLE_DIA, "cable_gap": _CABLE_GAP,
        "shell": dict(_shell_dims()),
    }


def _V(*a):
    return App.Vector(*a)


def _pair(a, b, dia, gap):
    """双芯视觉桩: a→b 两平行圆柱 (沿 a→b 法向偏移 ±gap/2)."""
    a, b = _V(*a), _V(*b)
    d = b.sub(a).normalize()
    n = d.cross(App.Vector(0, 0, 1))
    if n.Length < 1e-6:
        n = App.Vector(1, 0, 0)
    n.normalize()
    off = n.multiply(gap / 2.0)
    s1 = Part.makeCylinder(dia / 2, a.distanceToPoint(b), a.add(off), d)
    s2 = Part.makeCylinder(dia / 2, a.distanceToPoint(b), a.sub(off), d)
    return [s1, s2]


def parts_valve_lead(start, end):
    """阀 2P 引线桩分件 -> {"wire_red","wire_black","shell"}: 双引线 + 端点 2P 白壳视觉件
    (壳中心=桩末端, 长边沿桩向)."""
    sh = _shell_dims()
    a, b = _V(*start), _V(*end)
    d = b.sub(a).normalize()
    wires = _pair(start, end, _LEAD_DIA, _LEAD_GAP)
    # 白壳: 最长边 (w=10) 沿桩向, 壳体中心在末端 (插头扣入 J 插座的视觉占位)
    shell = Part.makeBox(sh["w"], sh["d"], sh["h"])
    m = App.Matrix()
    m.A11, m.A21, m.A31 = d.x, d.y, d.z                     # 壳局部 X → 桩向
    n = d.cross(App.Vector(0, 0, 1))
    if n.Length < 1e-6:
        n = App.Vector(1, 0, 0)
    n.normalize()
    u = d.cross(n)
    m.A12, m.A22, m.A32 = n.x, n.y, n.z
    m.A13, m.A23, m.A33 = u.x, u.y, u.z
    shell = shell.transformGeometry(m)
    shell.translate(b - d.multiply(sh["w"] / 2.0))
    return {"wire_red": wires[0], "wire_black": wires[1], "shell": shell}


def build_valve_lead(start, end):
    """阀引线桩 (双线+2P 白壳视觉件) -> Part Compound。"""
    return Part.makeCompound(list(parts_valve_lead(start, end).values()))


def build_pump_cable(start, end):
    """泵电缆桩 (2 芯 ⌀1.5, J23→泵端子, 默认 150) -> Part Compound (裸缆, 壳=J23 侧属主模块)。"""
    return Part.makeCompound(_pair(start, end, _CABLE_DIA, _CABLE_GAP))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("[harness] DEFAULTS=%s" % DEFAULTS())
    print("[harness] lead bbox=%s" % build_valve_lead([0, 0, 0], [0, 0, -60]).BoundBox)
    print("[harness] cable bbox=%s" % build_pump_cable([0, 0, 0], [150, 0, 0]).BoundBox)
