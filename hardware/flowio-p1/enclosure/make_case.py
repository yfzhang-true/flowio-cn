# -*- coding: utf-8 -*-
"""FLOWIO-P1 外壳 — FreeCAD/OCCT 参数化建模 (2026-10-03 装配栈统一重写).

运行: E:/FreeCAD/bin/FreeCADCmd.exe hardware/flowio-p1/enclosure/make_case.py
输出: flowio-p1-case.FCStd + case-bottom.step / case-top.step + 同名 STL

相对旧版的两处根本修复 (spec: docs/superpowers/specs/2026-10-03-cad-assembly-truth.md):
1. 装配栈唯一真相: 板坐在铜柱顶 z=Z_BOARD=7.4 (旧版注释"板底 2.4"与铜柱自相矛盾),
   总高由 19.0 -> 23.0, 侧槽 z 带以板面 Z_TOP=9.0 重定基准;
2. 顶盖真是盖: 裙边环(内缩 0.4, z 13.6..20.6) + 天花板(20.6..23.0, 通风栅+M3 过孔),
   旧版"顶盖"带完整底板 + 全高四壁, 与下壳全面穿插。

常量一律 import case_geom (单一真相源), 本文件不再定义任何几何数字。
"""
import os
import sys

import FreeCAD as App
import Part, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_geom as G


def b2c(x, y):
    return (x + G.OX, y + G.OX)


def side_cut(face, pos, w, z_lo, z_hi):
    """贯穿壁厚的侧槽盒. face: L/R/T/B; pos: 沿板边板系坐标.
    深度同时贯穿下壳壁 (0..WALL) 与顶盖裙环 (SKIRT_INSET..+SKIRT_T)."""
    d = G.SLOT_DEPTH
    if face == "L":
        return Part.makeBox(d, w, z_hi - z_lo, App.Vector(-1.2, pos + G.OX - w / 2, z_lo))
    if face == "R":
        return Part.makeBox(d, w, z_hi - z_lo, App.Vector(G.OW - d + 1.2, pos + G.OX - w / 2, z_lo))
    if face == "T":
        return Part.makeBox(w, d, z_hi - z_lo, App.Vector(pos + G.OX - w / 2, -1.2, z_lo))
    return Part.makeBox(w, d, z_hi - z_lo, App.Vector(pos + G.OX - w / 2, G.OH - d + 1.2, z_lo))


def all_cuts():
    boxes = [side_cut(f, p, w, lo, hi) for f, p, w, lo, hi in G.CUTS]
    tw, lo, hi = G.TERM_SLOT
    boxes += [side_cut("B", x, tw, lo, hi) for x in G.TERM_X]
    # 后壁两端角部 relief (贯穿壁+裙角柱): 端子体探入角柱, 不切则顶盖装不下
    rx, ry0, ry1 = G.TERM_RELIEF
    _, tlo, thi = G.TERM_SLOT
    boxes.append(Part.makeBox(rx + 1.2, ry1 - ry0, thi - tlo, App.Vector(-1.2, ry0, tlo)))
    boxes.append(Part.makeBox(rx + 1.2, ry1 - ry0, thi - tlo, App.Vector(G.OW - rx, ry0, tlo)))
    return boxes


# ---------- 下壳: 底板 + 四壁 (0..Z_CEIL) + 铜柱 - 侧槽 ----------
outer = Part.makeBox(G.OW, G.OH, G.Z_CEIL)
cavity = Part.makeBox(G.OW - 2 * G.WALL, G.OH - 2 * G.WALL, G.Z_CEIL - G.WALL + 1.0,
                      App.Vector(G.WALL, G.WALL, G.Z_FLOOR))
bottom = outer.cut(cavity)
for c in all_cuts():
    bottom = bottom.cut(c)
for sx, sy in G.ST:
    px, py = b2c(sx, sy)
    boss_o = Part.makeCylinder(G.PD / 2 + G.BOSS_RING, G.PH, App.Vector(px, py, G.Z_FLOOR))
    boss_i = Part.makeCylinder(G.PD / 2, G.PH + 1.0, App.Vector(px, py, G.Z_FLOOR - 0.5))
    bottom = bottom.fuse(boss_o.cut(boss_i))
bottom = bottom.removeSplitter()

# ---------- 顶盖: 裙边舌环 (SKIRT_Z0..Z_CEIL, 环带 2.8..4.8) + 天花板 (Z_CEIL..OUTER_H) ----------
# 舌环贴入下壳腔内, 与壁保持 0.4 间隙 (环不得覆盖 0..2.4 壁区, 否则与下壳穿插)
skirt_outer = Part.makeBox(G.OW - 2 * G.SKIRT_INSET, G.OH - 2 * G.SKIRT_INSET, G.SKIRT,
                           App.Vector(G.SKIRT_INSET, G.SKIRT_INSET, G.SKIRT_Z0))
skirt_hole = Part.makeBox(G.OW - 2 * (G.SKIRT_INSET + G.SKIRT_T),
                          G.OH - 2 * (G.SKIRT_INSET + G.SKIRT_T), G.SKIRT + 2.0,
                          App.Vector(G.SKIRT_INSET + G.SKIRT_T, G.SKIRT_INSET + G.SKIRT_T, G.SKIRT_Z0 - 1.0))
ceiling = Part.makeBox(G.OW, G.OH, G.WALL, App.Vector(0, 0, G.Z_CEIL))
top = skirt_outer.cut(skirt_hole).fuse(ceiling).removeSplitter()
for c in all_cuts():                      # 端子/4P 高槽穿过裙壁; 矮槽无材料可切, 无害
    top = top.cut(c)
# 通风栅 8x6 (刻穿天花板, 自上方下刀)
for i in range(8):
    for j in range(6):
        gx, gy = G.OX + 12 + i * 9, G.OX + 18 + j * 8
        top = top.cut(Part.makeBox(5, 4, G.WALL + 1.0,
                                   App.Vector(gx, gy, G.OUTER_H - G.WALL - 0.5)))
# M3 螺丝过孔 (与铜柱 ST 同轴)
for sx, sy in G.ST:
    px, py = b2c(sx, sy)
    top = top.cut(Part.makeCylinder(G.SCREW_D / 2, G.WALL + 1.0,
                                    App.Vector(px, py, G.OUTER_H - G.WALL - 0.5)))
top = top.removeSplitter()

# ---------- 自检 + 输出 ----------
bb_b, bb_t = bottom.BoundBox, top.BoundBox
print("[case] bottom bbox: %s" % bb_b)
print("[case] top    bbox: %s" % bb_t)
assert abs(bb_b.ZMax - G.Z_CEIL) < 0.01 and abs(bb_b.ZMin) < 0.01, "下壳高度不符"
assert abs(bb_t.ZMin - G.SKIRT_Z0) < 0.01 and abs(bb_t.ZMax - G.OUTER_H) < 0.01, "顶盖高度不符 (裙边/天花板)"
inter = bottom.common(top)
print("[case] 下壳∩顶盖 体积 = %.3f mm^3 (应为 0, 面接触)" % inter.Volume)
assert inter.Volume < 1e-3, "上下壳穿插!"

doc = App.newDocument("flowio-p1-case")
o1 = doc.addObject("Part::Feature", "Bottom"); o1.Shape = bottom
o2 = doc.addObject("Part::Feature", "Top"); o2.Shape = top
doc.recompute()
doc.saveAs(os.path.join(HERE, "flowio-p1-case.FCStd"))
bottom.exportStep(os.path.join(HERE, "case-bottom.step"))
top.exportStep(os.path.join(HERE, "case-top.step"))
Mesh.export([o1], os.path.join(HERE, "case-bottom.stl"))
Mesh.export([o2], os.path.join(HERE, "case-top.stl"))
print("ENCLOSURE OK: FCStd + 2 STEP + 2 STL -> %s (总高 %.1f)" % (HERE, G.OUTER_H))
