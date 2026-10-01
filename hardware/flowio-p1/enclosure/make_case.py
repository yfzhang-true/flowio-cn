# -*- coding: utf-8 -*-
"""FLOWIO-P1 外壳 — FreeCAD/OCCT 参数化建模 (替代 OpenSCAD, 规避 STL 互操作丢拓扑).
运行: E:/FreeCAD/bin/FreeCADCmd.exe make_case.py
输出: flowio-p1-case.FCStd (参数化) + case-bottom.step/case-top.step + STL.
坐标系: 板左下角为原点, x→右 y→上(板宽75), z→高出板面."""
import FreeCAD as App
import Part, Mesh, MeshPart, math

# ---------- 参数 ----------
WALL, CLR = 2.4, 0.5            # 壁厚 / 板-壁间隙
BW, BH, PCB_T = 90.0, 75.0, 1.6
INNER_H = 13.5                   # 端子高11 + 裕量
TOTAL_H = INNER_H + PCB_T + 1.5
OX = WALL + CLR                  # 板原点 → 壳内壁偏移
OW, OH = BW + 2*OX, BH + 2*OX
# 铜柱 (板坐标, HD 为 PCB 修复后实测位)
ST = [(4, 4), (3, 37), (86, 13), (68, 65)]
PD, PH = 4.2, 5.0               # M3 自攻底孔 / 柱高
SCREW_D = 3.4                    # 顶盖过孔
# 侧开孔 [面, 板坐标位置, 宽, 高] (孔中心离壳底 3mm 起的带)
CUTS = [("L", 27.0, 10.0, 9.0), ("L", 46.0, 8.0, 8.5),
        ("R", 6.0, 10.0, 4.0), ("R", 22.0, 8.0, 8.5), ("R", 32.5, 8.0, 8.5), ("R", 46.0, 8.0, 8.5),
        ("T", 46.0, 8.5, 8.0), ("T", 59.5, 8.5, 8.0), ("T", 73.0, 8.5, 8.0)]
TERM_X = [6.5 + 11*i for i in range(8)]   # 底边 8 端子
TY = 68.5
Z0 = WALL                        # 腔底 z (板底面所在)

def b2c(x, y):
    return (x + OX, y + OX)

def outer_box(h):
    return Part.makeBox(OW, OH, h)

def side_cut(face, pos, w, hh, depth=WALL + 1.6):
    """face: L/R/T/B; pos: 沿板边坐标(板系); 中心高度带 z=TY0."""
    cz = Z0 + 3.0 + hh/2
    if face == "L":
        b = Part.makeBox(depth, w, hh, App.Vector(-1.2, pos + OX - w/2, cz - hh/2))
    elif face == "R":
        b = Part.makeBox(depth, w, hh, App.Vector(OW - WALL - 0.4, pos + OX - w/2, cz - hh/2))
    elif face == "T":
        b = Part.makeBox(w, depth, hh, App.Vector(pos + OX - w/2, -1.2, cz - hh/2))
    else:
        b = Part.makeBox(w, depth, hh, App.Vector(pos + OX - w/2, OH - WALL - 0.4, cz - hh/2))
    return b

# ---------- 底壳 ----------
shell = outer_box(TOTAL_H + WALL)
cavity = Part.makeBox(OW - 2*WALL, OH - 2*WALL, TOTAL_H, App.Vector(WALL, WALL, WALL))
bottom = shell.cut(cavity)
for f, p, w, hh in CUTS:
    bottom = bottom.cut(side_cut(f, p, w, hh))
for x in TERM_X:
    bottom = bottom.cut(side_cut("B", x, 9.6, 9.0))
bosses = []
for sx, sy in ST:
    px, py = b2c(sx, sy)
    outer = Part.makeCylinder(PD/2 + 1.75, PH, App.Vector(px, py, WALL))
    hole = Part.makeCylinder(PD/2, PH + 1, App.Vector(px, py, WALL - 0.5))
    bosses.append(outer.cut(hole))
for bo in bosses:
    bottom = bottom.fuse(bo)
bottom = bottom.removeSplitter()

# ---------- 顶盖 ----------
top_shell = outer_box(TOTAL_H + WALL)
top_cavity = Part.makeBox(OW - 2*WALL - 0.8, OH - 2*WALL - 0.8, TOTAL_H,
                          App.Vector(WALL + 0.4, WALL + 0.4, WALL + 0.4))
top = top_shell.cut(top_cavity)
# 通风栅格 (8×6)
for i in range(8):
    for j in range(6):
        gx, gy = OX + 12 + i*9, OX + 18 + j*8
        vent = Part.makeBox(5, 4, WALL + 2, App.Vector(gx, gy, -0.5))
        top = top.cut(vent)
# 螺丝过孔
for sx, sy in ST:
    px, py = b2c(sx, sy)
    top = top.cut(Part.makeCylinder(SCREW_D/2, WALL + 2, App.Vector(px, py, -0.5)))
top = top.removeSplitter()

# ---------- 输出 ----------
doc = App.newDocument("flowio-p1-case")
o1 = doc.addObject("Part::Feature", "Bottom"); o1.Shape = bottom
o2 = doc.addObject("Part::Feature", "Top"); o2.Shape = top
doc.recompute()
doc.saveAs(__file__.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] and __file__.replace("make_case.py", "flowio-p1-case.FCStd"))
import os
here = os.path.dirname(os.path.abspath(__file__))
bottom.exportStep(os.path.join(here, "case-bottom.step"))
top.exportStep(os.path.join(here, "case-top.step"))
Mesh.export([o1], os.path.join(here, "case-bottom.stl"))
Mesh.export([o2], os.path.join(here, "case-top.stl"))
print("ENCLOSURE OK: FCStd + STEP + STL written to", here)
print("bbox bottom:", bottom.BoundBox, "top:", top.BoundBox)
