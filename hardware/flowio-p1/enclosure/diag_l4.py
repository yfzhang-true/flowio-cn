# -*- coding: utf-8 -*-
"""T6 临时诊断: 顶盖∩(板+器件) 0.2945mm^3 的来源定位 (逐器件/逐特征)."""
import csv
import os
import sys

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_geom as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
POSCSV = os.path.join(ROOT, "hardware", "flowio-p1", "fab", "flowio-p1-pos.csv")

top = Part.Shape()
top.read(os.path.join(HERE, "case-top.step"))

parts = []
with open(POSCSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        ref = (row["Ref"] or "").strip()
        if ref.upper().startswith("H"):
            continue
        parts.append((ref, (row["Package"] or "").strip(), float(row["PosX"]), float(row["PosY"]),
                      float(row["Rot"]), (row["Side"] or "").strip().lower()))

print("== 逐器件与顶盖交叠 ==")
total = 0.0
for ref, pkg, px, py, rot, side in parts:
    w, d, h = G.dims_for(pkg)
    if int(round(rot)) % 180 == 90:
        w, d = d, w
    cx, cy = G.board_to_case(px, py)
    z = G.Z_TOP if side == "top" else G.Z_BOARD - h
    box = Part.makeBox(w, d, h, App.Vector(cx - w / 2, cy - d / 2, z))
    v = top.common(box).Volume
    if v > 1e-9:
        total += v
        bb = top.common(box).BoundBox
        print("%-5s pkg=%-14s h=%.2f z1=%.2f vol=%.4f 交叠bbox=%s"
              % (ref, pkg, h, z + h, v, bb))
        print("      box: x[%.2f..%.2f] y[%.2f..%.2f] (壳系)" % (cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2))
print("total = %.4f" % total)

pcb = Part.makeBox(G.BW, G.BH, G.PCB_T, App.Vector(G.OX, G.OX, G.Z_BOARD))
print("pcb∩top = %.4f" % top.common(pcb).Volume)

# 顶盖特征拆解: 裙环 vs 天花板
skirt = Part.makeBox(G.OW - 2 * G.SKIRT_INSET, G.OH - 2 * G.SKIRT_INSET, G.SKIRT,
                     App.Vector(G.SKIRT_INSET, G.SKIRT_INSET, G.SKIRT_Z0))
skirt_hole = Part.makeBox(G.OW - 2 * (G.SKIRT_INSET + G.SKIRT_T),
                          G.OH - 2 * (G.SKIRT_INSET + G.SKIRT_T), G.SKIRT + 2.0,
                          App.Vector(G.SKIRT_INSET + G.SKIRT_T, G.SKIRT_INSET + G.SKIRT_T, G.SKIRT_Z0 - 1.0))
skirt = skirt.cut(skirt_hole)
ceil = Part.makeBox(G.OW, G.OH, G.WALL, App.Vector(0, 0, G.Z_CEIL))
print("== 特征拆解 (仅交叠器件) ==")
for ref, pkg, px, py, rot, side in parts:
    w, d, h = G.dims_for(pkg)
    if int(round(rot)) % 180 == 90:
        w, d = d, w
    cx, cy = G.board_to_case(px, py)
    z = G.Z_TOP if side == "top" else G.Z_BOARD - h
    box = Part.makeBox(w, d, h, App.Vector(cx - w / 2, cy - d / 2, z))
    vs, vc = skirt.common(box).Volume, ceil.common(box).Volume
    if vs > 1e-9 or vc > 1e-9:
        print("%-5s skirt=%.4f ceil=%.4f" % (ref, vs, vc))
