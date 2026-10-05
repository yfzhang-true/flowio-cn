# -*- coding: utf-8 -*-
"""sensor_xgzp — XGZP6897D 微差压传感器参数化建模 (D1, spec §2.2 特别核验; FreeCAD Part)。

几何 (datasheet literature/xgzp6897d-c-datasheet-v1.1.pdf p3 外形图/焊盘图直推,
devices.json sensor[0].geom3d 单源):
    本体 10.80(spec §2.2; -C 图 10.6±0.2)×7.00×3.50, SOIC8 板载坐板面 (z=0);
    双倒钩顶置 (+Z): P1=高压端/P2=低压端(大气), ⌀3.22/颈 ⌀2.2 ×2.4 高, 内孔 ⌀0.9 贯通
    (死端引压口; P1 接歧管测压支路 ID3 管, P2 大气开放勿堵); 倒钩位置: P1 距边 4.0(→y+0.5),
    P1/P2 轴向间距 5.2 (图面目测, 未注公差 → 断言容差 ±0.5, BRINGUP 卡尺关闭);
    SOIC8 鸥翼 8 脚: 节距 2.54 / 排距 7.96 (脚中心 y=±3.98), 2=VDD/6=SDA/7=SCL/8=GND,
    1-3-4-5 N/C 严禁连接; 焊盘行 ×2 = mech_mounts 数据 (回流焊即固定)。
器件自身原点 = 贴板面(坐板面)中心; +X = 本体长(引脚排沿 X); +Y = 排距方向。
"""
import sys
from pathlib import Path

import FreeCAD as App
import Part

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:                                    # FreeCAD python 免安装导入 (防重 guard)
    sys.path.insert(0, _ROOT)
from flowio.twin.devices3d import device_geom3d               # noqa: E402  单一真相源

_PAD_L, _PAD_W, _PAD_T = 2.0, 0.9, 0.2     # 鸥翼脚焊盘 (焊盘图 0.9×2, 脚厚 0.2/0.4)


def _params(over=None):
    gm = device_geom3d("sensor")
    p = {
        "body": dict(gm["body"]),                                # l10.8 w7.0 h3.5 barb_h2.4
        "ports": {q["name"]: q for q in gm["pneumatic_ports"]},  # P1/P2 双倒钩
        "terms": [t for t in gm["electrical_terminals"]],        # 8 脚
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
    """分件 -> {"body","P1","P2", pin 各脚} (器件自身原点系; 坐板面 z=0)。"""
    P = _params(over)
    b = P["body"]
    L, w, h, bh = b["l"], b["w"], b["h"], b["barb_h"]

    body = Part.makeBox(L, w, h, App.Vector(-L / 2, -w / 2, 0))
    # 死端引压孔贯入本体 (倒钩孔 ⌀0.9 在体内延续 — 死端引压口, 传感器感压膜侧)
    for q in P["ports"].values():
        qx, qy = q["pos"][0], q["pos"][1]
        body = body.cut(Part.makeCylinder(q["bore"] / 2, 1.2,
                                          App.Vector(qx, qy, q["pos"][2] - 1.0),
                                          App.Vector(0, 0, 1)))

    solids = {"body": body}
    for nm, q in P["ports"].items():                              # 双倒钩: 颈柱+口部锥环, 孔 ⌀0.9 贯通入体
        qx, qy, qz = q["pos"]
        dia, neck, ln, bore = q["dia"], q.get("neck_dia", 2.2), q["len"], q["bore"]
        neck_h = ln * 0.6
        stub = Part.makeCylinder(neck / 2, neck_h, App.Vector(qx, qy, qz), App.Vector(0, 0, 1))
        flare = Part.makeCone(neck / 2, dia / 2, ln - neck_h,
                              App.Vector(qx, qy, qz + neck_h), App.Vector(0, 0, 1))
        barb = stub.fuse(flare)
        barb = barb.cut(Part.makeCylinder(bore / 2, ln + 1.0,
                                          App.Vector(qx, qy, qz - 0.5), App.Vector(0, 0, 1)))
        solids[nm] = barb.removeSplitter()
    for t in P["terms"]:                                          # 8 鸥翼脚焊盘 (外露段, 与本体留 0.03 空隙 — 布尔安全)
        px, py, _ = t["pos"]
        pad = Part.makeBox(_PAD_L, _PAD_W, _PAD_T,
                           App.Vector(px - _PAD_L / 2, py - _PAD_W / 2, 0))
        solids[t["name"]] = pad
    return solids


def build(**over):
    """XGZP6897D 传感器 -> Part Compound (器件自身原点系, 坐板面 z=0; 总高含倒钩 5.9)。"""
    return Part.makeCompound(list(parts(**over).values()))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sh = build()
    print("[sensor_xgzp] bbox=%s solids=%d" % (sh.BoundBox, len(sh.Solids)))
