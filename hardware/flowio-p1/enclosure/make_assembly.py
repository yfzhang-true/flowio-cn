# -*- coding: utf-8 -*-
"""FLOWIO-P1 合并装配体 — PCB(含元件) + case-bottom + case-top -> 单一 STEP/STL.
运行: E:/FreeCAD/bin/python.exe hardware/flowio-p1/enclosure/make_assembly.py
输出: flowio-p1-assembly.step / flowio-p1-assembly.stl (gitignore, 按需再生)

坐标系: 壳系 (case_geom 单一真相).
  KiCad STEP 帧: 板 XY 平面, Y∈[-75,0] (y 已取负), Z 厚度向上。
  变换: (x_k, y_k, z_k) -> (x_k+OX, -y_k+OX, z_k+Z_BOARD), 即 Y 翻转 + 平移,
        与 case_geom.board_to_case 同映射 (J10/J2/J1 三锚点已在 make_meshes 验证)。
  板底面落位: Z_BOARD = WALL + PH = 7.4 (铜柱顶; 2026-10-03 装配栈统一)。
  旧版 Y_FLIP 可切换分支已删: 映射经锚点+包围盒双重验证后不再需要人工目测选择。
"""
import os
import sys

import FreeCAD as App
import Part, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_geom as G

REPO = os.path.dirname(HERE)                           # .../hardware/flowio-p1
PCB_STEP = os.path.join(REPO, "fab", "flowio-p1.step")


def load_step(path):
    sh = Part.Shape()
    sh.read(path)
    return sh


# ---------- 1. PCB: 离群过滤 (坏原点 JLC 模型) ----------
pcb = load_step(PCB_STEP)
keep, dropped = [], 0
for s in pcb.Solids:
    b = s.BoundBox
    cx, cy = (b.XMin + b.XMax) / 2, (b.YMin + b.YMax) / 2
    if -25 <= cx <= 115 and -100 <= cy <= 25:          # 板区 X∈[0,90] Y∈[-75,0] ±25 容差
        keep.append(s)
    else:
        dropped += 1
print("ASSEMBLY PCB solids: keep %d / drop %d (outlier)" % (len(keep), dropped))
pcb_kept = Part.makeCompound(keep)

# ---------- 2. 变换到壳坐标系 (锚点已验证的定稿映射, 无分支) ----------
# 注意: FreeCAD Matrix 的平移在第 4 列 (列向量约定, 已用最小实验验证):
# 旧版把 (OX,OX,Z_BOARD) 放在第 4 行 -> 平移从未生效, PCB 一直贴错墙穿底板,
# 而旧断言 (总包围盒 ±2.0) 看不见此错误 — 本次以 pcb 自身包围盒断言拦截。
m = App.Matrix(1, 0, 0, G.OX,
               0, -1, 0, G.OX,
               0, 0, 1, G.Z_BOARD,
               0, 0, 0, 1)
pcb_placed = pcb_kept.transformGeometry(m)

# ---------- 3. 合并 ----------
bottom = load_step(os.path.join(HERE, "case-bottom.step"))
top = load_step(os.path.join(HERE, "case-top.step"))
asm = Part.makeCompound([bottom, top, pcb_placed])

# ---------- 4. 断言 (收紧: 旧 ±2.0/±2.5 -> 分项核对) ----------
# 已知模型噪声: WJ500V 封装 offset(-0.3,0.5,3.5) + 模型内部原点 -> 实测端子体
# 相对焊盘中心 +3.15mm (J17 体尖探入右壁 ~1.5mm), z 抬升 3.5 (真件高度或在 ~14)。
# 设计真相 = pos.csv 居中 (case_geom 槽位/孪生盒体自洽); 板到货后实测再定槽位微调。
pb = pcb_placed.BoundBox
print("ASSEMBLY pcb placed: x[%.2f..%.2f] y[%.2f..%.2f] z[%.2f..%.2f]"
      % (pb.XMin, pb.XMax, pb.YMin, pb.YMax, pb.ZMin, pb.ZMax))
assert abs(pb.XMin - G.OX) < 0.3 and abs(pb.YMin - G.OX) < 0.3, "PCB 原点落位超差 (平移未生效?)"
assert pb.XMax <= G.OX + G.BW + 3.6, "PCB X 右探超限 (>3.6 = 新增模型偏移)"
assert pb.YMax <= G.OX + G.BH + 0.3, "PCB Y 落位超差 (映射翻转?)"
assert abs(pb.ZMin - G.Z_BOARD) < 0.3, "PCB 板底必须落在铜柱顶 Z_BOARD"
assert pb.ZMax <= G.OUTER_H + 0.6, "元件超出外壳总高 (含模型噪声预算 0.6)"
# 注: 真实 KiCad 端子模型含 +3.5z 封装偏移, 顶达 ~26.5 (JLC 真值 14.07);
# 盒真相 (L4/孪生/壳设计) 以 JLC 为准, 此 STEP 为评审件放宽模型噪声; 板到货实测终裁.

bb = asm.BoundBox
dx = abs(bb.XLength - G.OW); dy = abs(bb.YLength - G.OH); dz = abs(bb.ZLength - G.OUTER_H)
print("ASSEMBLY bbox: %s  (dx=%.2f dy=%.2f dz=%.2f)" % (bb, dx, dy, dz))
assert dx <= 0.3 and dy <= 0.3 and dz <= 0.6, "装配体包围盒超差 (dz 0.6 = 端子模型 +3.5z 噪声预算)"
assert len(asm.Solids) >= 500, "solid 数不足 (PCB 元件缺失?)"

# 侧壁干涉: JLC 模型自带偏移噪声 (J17 +3.15 探壁 ~260mm^3), 阈值据此放宽;
# 严格的零干涉校验在 test_assembly_freecad.py 用 pos.csv 盒子模型 (设计真相) 执行。
inter_b = bottom.common(pcb_placed)
print("ASSEMBLY 下壳∩PCB 体积 = %.3f mm^3 (含模型偏移噪声, 阈值 400)" % inter_b.Volume)
assert inter_b.Volume < 400.0, "PCB 与下壳干涉超限"

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
