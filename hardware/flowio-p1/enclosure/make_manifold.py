# -*- coding: utf-8 -*-
"""FLOWIO-P1 歧管 (1f-β 公共歧管 M) — FreeCAD/OCCT 参数化建模 (T6).

运行: E:/FreeCAD/bin/FreeCADCmd.exe hardware/flowio-p1/enclosure/make_manifold.py
输出: manifold.step / manifold.stl (壳系绝对坐标, 盖顶气动塔位)

形态 (spec 1f-β + 任务 T6-3): 打印件 (PLA/PETG), 12 口 =
  8 通道口 (V1-V8 承口) + 3 主阀口 (S/V/F = VS/VV/VF 承口) + 1 测压口 (XGZP 接管嘴);
  竖装适配: 基座块卡在 2×4 阀阵顶部 —— F0520D 嘴 (⌀3.0) 插入下垂承插短管
  (⌀3.2 孔, 插入 5.5mm ∈ 5-10 约定), F0520B 嘴 (⌀4.6) 插入块底 ⌀4.8 孔 (5.5mm);
  内流道 ⌀3.2 (走道截面 ≥ 阀孔径 3.0), 公共腔脊 ⌀4.0;
  变径腔: 真空主阀承口 ⌀4.8 于 z=50 锥收至 ⌀3.2 (泵侧 5→3 收口内化, Kamoer 替代);
  测压口: 右面 ⌀3.2 嘴 @ y=53.4 对齐壳 R 壁 XGZP 引压孔 (管垂直下行);
  支腿 4× 8×8 立于壳盖沿实体带 (避通风栅/M3 螺丝头/阀足印, 见 case_geom 推导).

常量一律 import case_geom (单一真相源: 气动尺寸由 devices.json pneumatic_devices 推导).
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import FreeCAD as App
import Part, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case_geom as G


def valve_solids():
    """11 阀 (体盒 + 嘴圆柱) —— 干涉校验/孪生复用的单一实现 (make_meshes 同源).
    kind: 'D'=F0520D (体 14.5 + 嘴 ⌀3.0), 'B'=F0520B (体 22 + 嘴 ⌀4.6)."""
    solids = []
    for x, y, kind in G.valve_grid():
        is_b = kind == "B"
        bh = G.VB_BODY_H if is_b else G.VD_BODY_H
        nd = (G._PNEU["vb_noz"]) if is_b else G._PNEU["vd_noz"]
        w, d = (G._PNEU["vb_w"], G._PNEU["vb_d"]) if is_b else (G._PNEU["vd_w"], G._PNEU["vd_d"])
        body = Part.makeBox(w, d, bh, App.Vector(x - w / 2, y - d / 2, G.TOWER_Z0))
        noz = Part.makeCylinder(nd / 2, G.NOZZLE_LEN, App.Vector(x, y, G.TOWER_Z0 + bh))
        solids.append((x, y, kind, Part.makeCompound([body, noz])))
    return solids


# ---------- 1. 基块 + 支腿 + D 阀承插短管 ----------
block = Part.makeBox(G.MAN_X1 - G.MAN_X0, G.MAN_Y1 - G.MAN_Y0, G.MAN_H,
                     App.Vector(G.MAN_X0, G.MAN_Y0, G.MAN_Z0))
legs = [Part.makeBox(8, 8, G.MAN_Z0 - G.TOWER_Z0, App.Vector(lx - 4, ly - 4, G.TOWER_Z0))
        for lx, ly in G.MAN_LEGS]
sol = block.fuse(legs)
for x, y, kind in G.valve_grid():
    if kind == "D":        # F0520D: ⌀6.2 承插短管下垂 z 36.5..44 (接不及块底的嘴)
        sol = sol.fuse(Part.makeCylinder(G.SOCK_BOSS_D / 2, G.MAN_Z0 - G.SOCK_BOSS_Z1,
                                         App.Vector(x, y, G.SOCK_BOSS_Z1)))
sol = sol.removeSplitter()

# ---------- 2. 流道网络 (布尔减, 内腔负空间) ----------
PLEN = G.PLENUM_Z


def tube(x0, y0, z0, x1, y1, z1, d):
    """两点间 ⌀d 流道 (轴对齐或斜线一律圆柱放样)."""
    p0, p1 = App.Vector(x0, y0, z0), App.Vector(x1, y1, z1)
    return Part.makeCylinder(d / 2, p0.distanceToPoint(p1), p0, p1.sub(p0).normalize())


cuts = []
for x, y, kind in G.valve_grid():                # 11 承口 + 各自升管接公共腔
    if kind == "B":                              # VV (F0520B): ⌀4.8 孔 + 变径腔 + 升管
        cuts.append(Part.makeCylinder(G.SOCK_D_B / 2, G.SOCK_DEPTH_B, App.Vector(x, y, G.MAN_Z0)))
        cuts.append(Part.makeCone(G.SOCK_D_B / 2, G.RUN_D / 2, 3.0, App.Vector(x, y, G.TAPER_IN_Z)))
        cuts.append(tube(x, y, G.TAPER_IN_Z + 3.0, x, y, PLEN, G.RUN_D))
    else:                                        # F0520D ×10: ⌀3.2 孔贯短管入块 2mm
        cuts.append(Part.makeCylinder(G.SOCK_D_D / 2, G.MAN_Z0 - G.SOCK_BOSS_Z1 + 2.0,
                                      App.Vector(x, y, G.SOCK_BOSS_Z1)))
        cuts.append(tube(x, y, G.MAN_Z0 + 2.0, x, y, PLEN, G.RUN_D))
# 公共腔脊: 前行/后行 X 向 + 左右 Y 向并联 + 主阀列 Y 向 + 测压支线
cuts.append(tube(G.V_COLS[0], G.V_ROWS[1], PLEN, G.V_COLS[3], G.V_ROWS[1], PLEN, 4.0))   # 前行
cuts.append(tube(G.V_COLS[0], G.V_ROWS[0], PLEN, G.V_COLS[3], G.V_ROWS[0], PLEN, 4.0))   # 后行
cuts.append(tube(G.V_COLS[0], G.V_ROWS[0], PLEN, G.V_COLS[0], G.V_ROWS[1], PLEN, 4.0))   # 左联
cuts.append(tube(G.V_COLS[3], G.V_ROWS[0], PLEN, G.V_COLS[3], G.V_ROWS[1], PLEN, 4.0))   # 右联
cuts.append(tube(G.M_X, G.V_ROWS[1], PLEN, G.M_X, G.M_YS[0], PLEN, 4.0))                 # 主阀列
# 测压口: 右面 ⌀3.2 嘴 (bore 贯壁 2mm) + 腔支线 (y=53.4 对齐壳 R 壁引压孔)
tsx, tsy, tsz = G.SENS_TAP
cuts.append(tube(tsx - 2.0, tsy, tsz, tsx, tsy, tsz, G.RUN_D))
cuts.append(tube(tsx - 2.0, tsy, tsz, tsx - 2.0, tsy, PLEN, G.RUN_D))
cuts.append(tube(G.M_X, tsy, PLEN, tsx - 2.0, tsy, PLEN, G.RUN_D))
for c in cuts:
    sol = sol.cut(c)
sol = sol.removeSplitter()

# 测压口外嘴 (⌀4.4 伸出 5mm), 内孔 ⌀3.2 贯通嘴全长 (熔接后再贯切)
tap = Part.makeCylinder(2.2, 5.0, App.Vector(tsx, tsy, tsz), App.Vector(1, 0, 0))
sol = sol.fuse(tap)
sol = sol.cut(tube(tsx - 2.0, tsy, tsz, tsx + 5.5, tsy, tsz, G.RUN_D)).removeSplitter()

# ---------- 3. 分项断言 (铁律 10: 禁总盒宽松; 外廓 = 块 ∪ 支腿 ∪ 测压嘴推导) ----------
exp_x0 = min(G.MAN_X0, min(lx - 4 for lx, _ in G.MAN_LEGS))
exp_x1 = max(G.MAN_X1, max(lx + 4 for lx, _ in G.MAN_LEGS)) + 5.0      # +5 测压嘴
exp_y0 = min(G.MAN_Y0, min(ly - 4 for _, ly in G.MAN_LEGS))
exp_y1 = max(G.MAN_Y1, max(ly + 4 for _, ly in G.MAN_LEGS))
bb = sol.BoundBox
assert abs(bb.XMin - exp_x0) < 0.01 and abs(bb.XMax - exp_x1) < 0.01, \
    "歧管 X 外廓: %s (期望 %s..%s)" % (bb, exp_x0, exp_x1)
assert abs(bb.YMin - exp_y0) < 0.01 and abs(bb.YMax - exp_y1) < 0.01, "歧管 Y 外廓"
assert abs(bb.ZMin - G.TOWER_Z0) < 0.01 and abs(bb.ZMax - G.MAN_Z1) < 0.01, "歧管 Z 外廓"

# 12 口开孔验证: 各承口/嘴位探针圆柱与实体交体积 = 0 (孔真贯通)
for x, y, kind in G.valve_grid():
    if kind == "B":
        d, z0 = G.SOCK_D_B, G.MAN_Z0
    else:
        d, z0 = G.SOCK_D_D, G.SOCK_BOSS_Z1
    probe = Part.makeCylinder(d / 2, G.MAN_Z0 + 2.0 - z0, App.Vector(x, y, z0))
    v = sol.common(probe).Volume
    assert v < 1e-6, "承口 (%.1f,%.1f) 未贯通: %.4f mm^3" % (x, y, v)
probe = Part.makeCylinder(G.RUN_D / 2, 7.0, App.Vector(tsx - 1.0, tsy, tsz), App.Vector(1, 0, 0))
assert sol.common(probe).Volume < 1e-6, "测压口未贯通"

# 阀嘴-承口干涉 = 0 (嘴 ⌀3.0/4.6 在 ⌀3.2/4.8 孔内, 0.1 径向隙)
for x, y, kind, vs in valve_solids():
    v = sol.common(vs).Volume
    assert v < 1e-3, "歧管∩阀 (%.1f,%.1f,%s) = %.4f mm^3" % (x, y, kind, v)

# 支腿立于盖沿: 腿底 z = 盖顶 (面接触, 非穿插); 探针薄片在腿位有材料、其下无
for lx, ly in G.MAN_LEGS:
    probe = Part.makeCylinder(2.0, 0.08, App.Vector(lx, ly, G.TOWER_Z0 - 0.06))
    assert sol.common(probe).Volume > 1e-6, "支腿 (%.0f,%.0f) 未达盖面" % (lx, ly)
    under = Part.makeCylinder(2.0, 0.08, App.Vector(lx, ly, G.TOWER_Z0 - 0.16))
    assert sol.common(under).Volume < 1e-9, "支腿 (%.0f,%.0f) 穿透盖面" % (lx, ly)

print("[manifold] bbox=%s  vol=%.1f mm^3  solids=%d" % (bb, sol.Volume, len(sol.Solids)))
print("[manifold] 12 口: 11 承口 (10×⌀%.1f + 1×⌀%.1f 变径 %.1f→%.1f) + 测压嘴 ⌀%.1f @y=%.1f"
      % (G.SOCK_D_D, G.SOCK_D_B, G.SOCK_D_B, G.RUN_D, G.RUN_D, tsy))

# ---------- 4. 输出 ----------
doc = App.newDocument("flowio-p1-manifold")
o = doc.addObject("Part::Feature", "Manifold")
o.Shape = sol
doc.recompute()
doc.saveAs(os.path.join(HERE, "flowio-p1-manifold.FCStd"))
sol.exportStep(os.path.join(HERE, "manifold.step"))
Mesh.export([o], os.path.join(HERE, "manifold.stl"))
print("MANIFOLD OK: STEP+STL+FCStd -> %s" % HERE)
