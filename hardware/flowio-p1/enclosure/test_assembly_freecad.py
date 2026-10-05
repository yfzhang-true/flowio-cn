# -*- coding: utf-8 -*-
"""FLOWIO-P1 CAD 装配测试 L4 — OCC 布尔干涉校验 (FreeCAD, 需 E:/FreeCAD/bin/python.exe).

用 pos.csv 盒子模型 (设计真相, 与 parts_f.stl 同源逻辑) 对真实外壳 STEP 做布尔:
  1. 下壳 ∩ 顶盖 = 0     (盖子是盖, 不是带底板的方盒)
  2. 下壳 ∩ 板+器件 = 0  (板坐铜柱顶, 越壁件走侧槽)
  3. 顶盖 ∩ 板+器件 = 0  (天花板净空足够, 端子不顶盖)
  4. 铜柱顶面与板底面 z 重合 (面接触承压, 不是悬空/穿插)

make_assembly.py 里的 110mm^3 "模型偏移噪声" 不出现在这里 — 那是 KiCad 封装
3D 模型自带 offset; 盒子模型以焊盘中心为真相, 与开槽设计自洽。
运行: E:/FreeCAD/bin/python.exe hardware/flowio-p1/enclosure/test_assembly_freecad.py
"""
import csv
import os
import sys

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # 仓库根 (enclosure 上三级)
sys.path.insert(0, ROOT)              # M1: 几何单一真相源经 flowio.geom (FreeCAD python 免安装)
from flowio.geom import case_geom as G  # noqa: E402

POSCSV = os.path.join(ROOT, "hardware", "flowio-p1", "fab", "flowio-p1-pos.csv")

PASS, FAIL = 0, 0


def check(name, ok, detail=""):
    global PASS, FAIL
    print("[%-4s] %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + detail) if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1


# ---------- 装配重现 (盒子模型 = 设计真相) ----------
parts = []
with open(POSCSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        ref = (row["Ref"] or "").strip()
        if ref.upper().startswith("H"):
            continue
        parts.append((ref, (row["Package"] or "").strip(), float(row["PosX"]), float(row["PosY"]),
                      float(row["Rot"]), (row["Side"] or "").strip().lower()))

boxes = []
for ref, pkg, px, py, rot, side in parts:
    w, d, h = G.dims_for(pkg)
    if int(round(rot)) % 180 == 90:
        w, d = d, w
    cx, cy = G.board_to_case(px, py)
    z = G.Z_TOP if side == "top" else G.Z_BOARD - h
    boxes.append(Part.makeBox(w, d, h, App.Vector(cx - w / 2, cy - d / 2, z)))
pcb = Part.makeBox(G.BW, G.BH, G.PCB_T, App.Vector(G.OX, G.OX, G.Z_BOARD))
board_asm = Part.makeCompound([pcb] + boxes)

bottom = Part.Shape()
bottom.read(os.path.join(HERE, "case-bottom.step"))
top = Part.Shape()
top.read(os.path.join(HERE, "case-top.step"))

# ---------- 断言 ----------
v1 = bottom.common(top).Volume
check("L4 下壳∩顶盖 = 0 (盖子不得是带底方盒)", v1 < 1e-3, "%.4f mm^3" % v1)

v2 = bottom.common(board_asm).Volume
check("L4 下壳∩(板+器件) = 0 (铜柱承板, 越壁走槽)", v2 < 1e-3, "%.4f mm^3" % v2)

v3 = top.common(board_asm).Volume
check("L4 顶盖∩(板+器件) = 0 (天花板净空)", v3 < 1e-3, "%.4f mm^3" % v3)

# 铜柱顶 z 与板底 z 重合: 探针薄环片 (r=2.0, 位于孔 r1.4 与柱外缘 r3.15 之间的材料环)
boss_ok = 0
for sx, sy in G.ST:
    cx, cy = sx + G.OX, sy + G.OX
    probe = Part.makeCylinder(2.0, 0.08, App.Vector(cx, cy, G.Z_BOARD - 0.10))
    # 探针完全在板底之下: 与铜柱材料相交, 与 PCB 板体零交
    if bottom.common(probe).Volume > 1e-6 and pcb.common(probe).Volume < 1e-9:
        boss_ok += 1
check("L4 铜柱顶面承板 x4 (z 面接触)", boss_ok == 4, "%d/4" % boss_ok)

bb_all = Part.makeCompound([bottom, top, board_asm]).BoundBox
check("L4 装配包围盒 = 壳外廓",
      abs(bb_all.XLength - G.OW) < 0.05 and abs(bb_all.YLength - G.OH) < 0.05
      and abs(bb_all.ZLength - G.OUTER_H) < 0.05, str(bb_all))

print("\nCAD L4: %d PASS / %d FAIL" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
