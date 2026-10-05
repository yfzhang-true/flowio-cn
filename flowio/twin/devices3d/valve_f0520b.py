# -*- coding: utf-8 -*-
"""valve_f0520b — F0520B 真空主阀 (常闭负压专用) 参数化建模 (D1, spec §2.1; FreeCAD Part)。

几何 (datasheet literature/F0520B.pdf p2 图纸直推, devices.json valve_vacuum_master[0].geom3d 单源):
    金属 C 架本体 20.0±0.3 + 塑料端段 8.0 = 总长 28.0±0.5 (长轴), 15±0.5 × 13±0.3;
    N1 顶嘴 (宝塔) ⌀4.6±0.3 ×6.0±0.3 —— 安装态朝上接歧管承口 ⌀4.8+变径腔 (1=COM, 通电 1↔2);
    N2 对端端口 ⌀3.0×3.0 [inferred: 图纸仅标 N1, 按 F0520D 家族对称惯例, 到货实测校正];
    红黑引线自 -Y 侧近 N1 端出线 (实物照 p5/p6), 端接 2P 白壳 (实拍照 p1 在引线端);
    有孔变体 ⌀2.0 安装孔×2 = 数据占位 (孔距待商家, procurement 问询 1/3) —— 几何不切孔。
器件自身原点 = N2 端面面心 (+Z 长轴)。
"""
import sys

import FreeCAD as App
import Part

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))
from flowio.twin.devices3d import device_geom3d               # noqa: E402  单一真相源

_LEAD_DIA = 1.0
_LEAD_ESCAPE = 8.0


def _params(over=None):
    gm = device_geom3d("valve_vacuum_master")
    p = {
        "body": dict(gm["body"]),                                # w15 d13 h28 frame_len20 end_sec_len8 port_len6
        "ports": {q["name"]: q for q in gm["pneumatic_ports"]},  # N1/N2
        "terms": {t["name"]: t for t in gm["electrical_terminals"]},
    }
    if over:
        for k, v in over.items():
            if k == "body":
                p["body"].update(v)
            else:
                p[k] = v
    return p


DEFAULTS = _params()


def parts(**over):
    """分件 -> {"frame","end_sec","N1","N2","lead_red","lead_black"} (安装孔=数据占位, 不切)。"""
    P = _params(over)
    b = P["body"]
    w, d = b["w"], b["d"]
    fl, es_len = b["frame_len"], b["end_sec_len"]

    frame = Part.makeBox(w, d, fl, App.Vector(-w / 2, -d / 2, 0))            # 金属 C 架本体 (z 0..20)
    end_sec = Part.makeBox(w, d, es_len, App.Vector(-w / 2, -d / 2, fl))     # 塑料端段 (z 20..28)

    solids = {"frame": frame, "end_sec": end_sec}
    for nm in ("N1", "N2"):                                                  # 嘴 (基面=pos, 沿 dir)
        q = P["ports"][nm]
        x, y, z = q["pos"]
        dz = 1.0 if q["dir"][2] > 0 else -1.0
        z0 = z                                                    # 基面=pos, 沿 dir 拉伸 (dz<0 向 -Z)
        # 宝塔嘴: 两段锥柱近似 (基侧 ⌀颈 → 口部 ⌀dia), 直管时退化为单柱
        neck_d = q.get("neck_dia", q["dia"] - 1.4)
        half = q["len"] / 2.0
        s1 = Part.makeCone(neck_d / 2, q["dia"] / 2, half, App.Vector(x, y, z0), App.Vector(0, 0, dz))
        s2 = Part.makeCylinder(q["dia"] / 2, half, App.Vector(x, y, z0 + dz * half), App.Vector(0, 0, dz))
        solids[nm] = s1.fuse(s2).removeSplitter()
    for nm, tname in (("lead_red", "COIL_RED"), ("lead_black", "COIL_BLACK")):
        t = P["terms"][tname]
        x, y, z = t["pos"]
        # 自壳壁 (y=-d/2) 沿 -Y 出线 (切线接触, 布尔安全)
        solids[nm] = Part.makeCylinder(_LEAD_DIA / 2, _LEAD_ESCAPE,
                                       App.Vector(x, -d / 2, z), App.Vector(0, -1, 0))
    return solids


def build(**over):
    """F0520B 阀器件 -> Part Compound (器件自身原点系)。"""
    return Part.makeCompound(list(parts(**over).values()))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sh = build()
    print("[valve_f0520b] bbox=%s solids=%d" % (sh.BoundBox, len(sh.Solids)))
