# -*- coding: utf-8 -*-
"""valve_f0520d — F0520D 两位两通常闭电磁阀参数化建模 (D1, spec §2.1; FreeCAD Part=OCCT)。

几何 (datasheet literature/F0520D.pdf p2 图纸直推, devices.json valves[0].geom3d 单源):
    C 形硅钢架本体 20.5±0.5(X 长轴)×15.0±0.5×13.0±0.5, 架顶 0.7mm 翻边固定面 (z 19.8..20.5);
    N1/N2 双端面嘴 ⌀3.0±0.3 ×3.0±0.3 (图纸 p2 直管档真值; 规格审 M2: spec §2.1 行文 3.5 超出
    图纸 ±0.3 带, datasheet 直推优先) —— 安装态 (1a 竖装)
    N1 朝上接歧管承口 ⌀3.2、N2 朝下接 cuff/B 壁过孔 (图纸: 正压接N2口, 负压接管N1口);
    红黑双引线自 -Y 侧壁面出线 (图纸出体位 5.2±0.3 自 N2 端), 端接 2P 白壳 → harness.py 视觉桩。
分件: frame(金属架) + flange(顶翻边, ⌀3.2 过孔) + N1/N2 嘴 + 双引线桩 (面接触复合体, 布尔安全)。
    注(规格审 M5): flange 分件与本体 frame 顶部 0.7 体积重叠 —— Compound 不 fuse, 渲染体积
    重复计数(分件求和偏大 ~13.4mm^3)、外观无差; 保留分件是为 ⌀3.2 承插过孔单件可断言。
器件自身原点 = N2 端面面心 (+Z 长轴立起); 全部尺寸默认值读 devices.json geom3d (禁本地复制)。
"""
import sys
from pathlib import Path

import FreeCAD as App
import Part

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:                                    # FreeCAD python 免安装导入 (防重 guard)
    sys.path.insert(0, _ROOT)
from flowio.twin.devices3d import device_geom3d               # noqa: E402  单一真相源

_LEAD_DIA = 1.0          # 引线视觉径 ⌀1.0 (实物照 AWG24 硅胶线估, harness 桩同径)
_LEAD_ESCAPE = 8.0       # 引线出体段长 (出 -Y 侧壳外 8mm, 之后交 harness 视觉桩)
_LEAD_GAP = 1.2          # 双引线并排间距 (视觉值, geom3d COIL_RED/BLACK y 差同源)


def _params(over=None):
    """geom3d 单源参数 + 覆盖项 (测试/变体注入)。"""
    gm = device_geom3d("valves")
    p = {
        "body": dict(gm["body"]),                                # w15 d13 h20.5 flange_t0.7 port_len3.5
        "ports": {q["name"]: q for q in gm["pneumatic_ports"]},  # N1/N2 pos/dir/dia/len
        "terms": {t["name"]: t for t in gm["electrical_terminals"]},
    }
    if over:
        for k, v in over.items():
            if k == "body":
                p["body"].update(v)
            else:
                p[k] = v
    return p


DEFAULTS = _params()         # G8 单源一致性断言消费 (与 json 逐字相等)


def parts(**over):
    """分件建模 -> {"frame","coil","flange","N1","N2","lead_red","lead_black"} (器件自身原点系)。"""
    P = _params(over)
    b = P["body"]
    w, d, h, pt_len = b["w"], b["d"], b["h"], b["port_len"]
    ft = b["flange_t"]

    frame = Part.makeBox(w, d, h, App.Vector(-w / 2, -d / 2, 0))     # C 架本体 (金属壳视觉, 面心原点)
    # 顶翻边: 架顶 0.7 薄层 + 嘴过孔 ⌀3.2 (承插贯通, 单一小布尔, make_pump_module 同级)
    flange = Part.makeBox(w, d, ft, App.Vector(-w / 2, -d / 2, h - ft))
    flange = flange.cut(Part.makeCylinder(3.2 / 2, ft + 0.2, App.Vector(0, 0, h - ft - 0.1),
                                          App.Vector(0, 0, 1)))

    solids = {"frame": frame, "flange": flange}
    for nm in ("N1", "N2"):                                         # 双端面嘴 (基面=pos, 沿 dir 拉伸)
        q = P["ports"][nm]
        x, y, z = q["pos"]
        dz = 1.0 if q["dir"][2] > 0 else -1.0
        solids[nm] = Part.makeCylinder(q["dia"] / 2, q["len"], App.Vector(x, y, z),
                                       App.Vector(0, 0, dz))
    # 引线出体段: 自壳壁 (y=-d/2) 沿 -Y 出线 8mm (红/黑并排, 视觉桩主体在 harness.py);
    # 起点=壁面 (切线接触, 复合体布尔安全 — 禁体内嵌线, OCCT 自交布尔不可靠)
    for nm, tname in (("lead_red", "COIL_RED"), ("lead_black", "COIL_BLACK")):
        t = P["terms"][tname]
        x, y, z = t["pos"]
        solids[nm] = Part.makeCylinder(_LEAD_DIA / 2, _LEAD_ESCAPE,
                                       App.Vector(x, -d / 2, z), App.Vector(0, -1, 0))
    return solids


def build(**over):
    """F0520D 阀器件 -> Part Compound (器件自身原点系; 孪生/装配消费入口)。"""
    return Part.makeCompound(list(parts(**over).values()))


if __name__ == "__main__":                                          # 直跑自检 (FreeCADCmd/python 均可)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sh = build()
    print("[valve_f0520d] bbox=%s solids=%d" % (sh.BoundBox, len(sh.Solids)))
