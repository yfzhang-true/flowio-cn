# -*- coding: utf-8 -*-
"""FLOWIO-P1 合并装配体 — PCB(含元件) + case-bottom + case-top -> 单一 STEP/STL.
运行: E:/FreeCAD/bin/FreeCADCmd.exe make_assembly.py   (工作目录 = 本目录的上一级仓库根)
输出: flowio-p1-assembly.step / flowio-p1-assembly.stl
坐标系: 与 make_case.py 相同 (板左下角原点, x→右 y→上, z→高).
  KiCad STEP 帧: 板 XY 平面, Y∈[-75,0] (y 已取负), Z 厚度向上.
  变换: (x_k, y_k, z_k) -> (x_k+OX, -y_k+OX, z_k+Z_BOARD), 即 Y 翻转 + 平移.
  板底面落位: Z_BOARD = WALL + PH = 2.4 + 5.0 = 7.4 (铜柱顶).
"""
import os
import FreeCAD as App
import Part, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                            # .../hardware/flowio-p1
PCB_STEP = os.path.join(REPO, "fab", "flowio-p1.step")

# 与 make_case.py 一致的常量
BW, BH = 90.0, 75.0
WALL, OX = 2.4, 2.9
PH = 5.0
OW, OH = BW + 2 * OX, BH + 2 * OX          # 95.8 x 80.8
Z_BOARD = WALL + PH                          # 7.4
TOTAL_HZ = 13.5 + 1.6 + 1.5 + WALL          # 19.0 预期总高
Y_FLIP = True                                # 预览若端子排未贴底边, 改 False 重跑

def load_step(path):
    sh = Part.Shape()
    sh.read(path)
    return sh

# ---------- 1. PCB: 离群过滤 ----------
pcb = load_step(PCB_STEP)
solids = pcb.Solids
keep, dropped = [], 0
for s in solids:
    b = s.BoundBox
    cx, cy = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2
    # 板区 X∈[0,90] Y∈[-75,0]; 容差 25mm 吸收连接器出脚
    if -25 <= cx <= 115 and -100 <= cy <= 25:
        keep.append(s)
    else:
        dropped += 1
print("ASSEMBLY PCB solids: keep %d / drop %d (outlier)" % (len(keep), dropped))
pcb_kept = Part.makeCompound(keep)

# ---------- 2. 变换到外壳坐标系 ----------
if Y_FLIP:
    m = App.Matrix(1, 0, 0, 0,
                   0, -1, 0, 0,
                   0, 0, 1, 0,
                   OX, OX, Z_BOARD)
else:
    m = App.Matrix(1, 0, 0, 0,
                   0, 1, 0, 0,
                   0, 0, 1, 0,
                   OX, OX + BH, Z_BOARD)
pcb_placed = pcb_kept.transformGeometry(m)

# ---------- 3. 合并 ----------
bottom = load_step(os.path.join(HERE, "case-bottom.step"))
top = load_step(os.path.join(HERE, "case-top.step"))
asm = Part.makeCompound([bottom, top, pcb_placed])

# ---------- 4. 断言 ----------
bb = asm.BoundBox
dx, dy, dz = abs(bb.XLength - OW), abs(bb.YLength - OH), abs(bb.ZLength - TOTAL_HZ)
print("ASSEMBLY bbox: %s  (dx=%.2f dy=%.2f dz=%.2f)" % (bb, dx, dy, dz))
assert dx <= 2.0 and dy <= 2.0, "包围盒 X/Y 超差"
assert dz <= 2.5, "包围盒 Z 超差"
assert len(asm.Solids) >= 3, "solid 数不足"
# 板体不应穿出顶盖: PCB 最高点 <= 总高
pb = pcb_placed.BoundBox
print("ASSEMBLY pcb placed z: %.2f .. %.2f (case total %.1f)" % (pb.ZMin, pb.ZMax, TOTAL_HZ))
assert pb.ZMax <= TOTAL_HZ + 1.0, "元件超出外壳高度"

# ---------- 5. 输出 ----------
out_step = os.path.join(HERE, "flowio-p1-assembly.step")
out_stl = os.path.join(HERE, "flowio-p1-assembly.stl")
asm.exportStep(out_step)
doc = App.newDocument("asm")
o = doc.addObject("Part::Feature", "Assembly")
o.Shape = asm
Mesh.export([o], out_stl)
print("ASSEMBLY OK: solids=%d -> %s (%.1f MB) + %s"
      % (len(asm.Solids), out_step, os.path.getsize(out_step) / 1e6, out_stl))
