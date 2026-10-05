# -*- coding: utf-8 -*-
"""FLOWIO-P1 泵模块壳 (1h 分装式) — FreeCAD/OCCT 参数化建模 (T6).

运行: E:/FreeCAD/bin/FreeCADCmd.exe hardware/flowio-p1/enclosure/make_pump_module.py
输出: flowio-p1-pump-module.FCStd + pump-module.step/.stl (壳=底盒+裙盖)
      + pump.stl (ZR370 哑泵) + brackets.stl (硅胶支架×2) — 均壳系绝对坐标
      (模块原点 = case_geom.PMOD_OFF, 装配/孪生直接消费)

结构: 小盒内腔容纳 ZR370-03PM ⌀24×58.1 横躺 (轴沿 X, 双顶嘴朝上) +
  致荣硅胶支架×2 前后夹持 (环抱泵头, 脚距 46 M3, 孪生环孔取 +0.2 间隙见 case_geom) +
  面板 (X+ 端): 双快插气口 ⌀5.6 (充/吸 5mm 管, 内接跳管至双顶嘴) + JST 2P 出线孔 ⌀5.0;
  盖 = 免螺丝裙盖 (skirt 摩擦 + 环抱夹持定位, 泵可换单 — 1h 分装式设计意图)。

常量一律 import case_geom (单一真相源; 气动尺寸由 devices.json pneumatic_devices 推导).
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

OX0, OY0, OZ0 = G.PMOD_OFF                 # 模块原点 -> 壳系平移 (输出前统一施加)


def mod(x, y, z):
    """建模一律模块系 (本函数 = 恒等, 末尾 MTX 统一平移到壳系)."""
    return App.Vector(x, y, z)


W, T = G.PMOD_WALL, G.PMOD_WALL
LX, WX, HX = G.PMOD_L, G.PMOD_W, G.PMOD_H
CAV_Z1 = T + G.PMOD_IN_H                    # 38.9 腔顶 = 盖板底

# ---------- 1. 底盒: 底板 + 四壁 (z 0..CAV_Z1) - 面板三孔 ----------
base = Part.makeBox(LX, WX, CAV_Z1)
cav = Part.makeBox(LX - 2 * T, WX - 2 * T, CAV_Z1 - T + 1.0, mod(T, T, T))
base = base.cut(cav)
# 面板 (X+ 端面 x=LX): S/V 快插 ⌀5.6 ×2 (y=c±8, z=轴) + JST 出线 ⌀5.0 (y=c, z=6)
for dy in (-G.PMOD_PORT_DY, G.PMOD_PORT_DY):
    base = base.cut(Part.makeCylinder(G.PMOD_PORT_D / 2, T + 1.2,
                                      mod(LX - T - 0.6, G.PMOD_CY + dy, G.PUMP_AXIS_Z),
                                      App.Vector(1, 0, 0)))
base = base.cut(Part.makeCylinder(G.PMOD_WIRE_D / 2, T + 1.2,
                                  mod(LX - T - 0.6, G.PMOD_CY, G.PMOD_WIRE_Z),
                                  App.Vector(1, 0, 0)))
base = base.removeSplitter()

# ---------- 2. 裙盖: 盖板 (CAV_Z1..HX) + 裙环 (CAV_Z1-4..CAV_Z1, 贴腔内 0.4 间隙) ----------
SK_IN, SK_T, SK_D = T + 0.4, 2.0, 4.0
lid = Part.makeBox(LX, WX, T, mod(0, 0, CAV_Z1))
sk_o = Part.makeBox(LX - 2 * SK_IN, WX - 2 * SK_IN, SK_D, mod(SK_IN, SK_IN, CAV_Z1 - SK_D))
sk_i = Part.makeBox(LX - 2 * (SK_IN + SK_T), WX - 2 * (SK_IN + SK_T), SK_D + 2.0,
                    mod(SK_IN + SK_T, SK_IN + SK_T, CAV_Z1 - SK_D - 1.0))
lid = lid.fuse(sk_o.cut(sk_i)).removeSplitter()

# ---------- 3. 哑泵 (ZR370-03PM: ⌀24 体 + 双顶嘴 ⌀4.2) ----------
pl, pd, ph = G._PNEU["pump_l"], G._PNEU["pump_dia"], G._PNEU["pump_h"]
pump = Part.makeCylinder(pd / 2, pl,
                         mod(G.PMOD_CX - pl / 2, G.PMOD_CY, G.PUMP_AXIS_Z),
                         App.Vector(1, 0, 0))
noz_h = ph - pd / 2 - pd / 2                # 嘴伸出 = 总高 - 体径 (= 7.5)
nozzles = []
for dx in G.PUMP_NOZ_DX:
    nozzles.append(Part.makeCylinder(G._PNEU["pump_noz"] / 2, noz_h,
                                     mod(G.PMOD_CX + dx, G.PMOD_CY,
                                         G.PUMP_AXIS_Z + pd / 2)))
pump_asm = Part.makeCompound([pump] + nozzles)

# ---------- 4. 硅胶支架 ×2 (环 OD26/ID24.2 宽 8 + 脚垫 12×10×3 含 M3 孔) ----------
brackets = []
for sgn in (-1, 1):
    bx = G.PMOD_CX + sgn * G.BKT_SPAN / 2.0
    # 环轴 = 泵轴 (z=PUMP_AXIS_Z); 环底 5.4 恰落脚垫顶 (面接触夹持)
    ring_o = Part.makeCylinder(G.BKT_OD / 2, G.BKT_W,
                               mod(bx - G.BKT_W / 2, G.PMOD_CY, G.PUMP_AXIS_Z),
                               App.Vector(1, 0, 0))
    ring_i = Part.makeCylinder(G.BKT_ID / 2, G.BKT_W + 1.0,
                               mod(bx - G.BKT_W / 2 - 0.5, G.PMOD_CY, G.PUMP_AXIS_Z),
                               App.Vector(1, 0, 0))
    foot = Part.makeBox(G.BKT_W + 4, 12, G.BKT_FOOT_T,
                        mod(bx - G.BKT_W / 2 - 2, G.PMOD_CY - 6, T))
    hole = Part.makeCylinder(1.7, G.BKT_FOOT_T + 1.0,
                             mod(bx, G.PMOD_CY, T - 0.5))
    brackets.append(ring_o.cut(ring_i).fuse(foot).cut(hole).removeSplitter())
bkt_asm = Part.makeCompound(brackets)

# ---------- 5. 分项断言 (铁律 10: 禁总盒宽松) ----------
def bb_of(sh):
    return sh.BoundBox

bb = bb_of(base)
assert (abs(bb.XMin) < 0.01 and abs(bb.XMax - LX) < 0.01 and
        abs(bb.YMin) < 0.01 and abs(bb.YMax - WX) < 0.01 and
        abs(bb.ZMin) < 0.01 and abs(bb.ZMax - CAV_Z1) < 0.01), \
    "底盒 bbox: %s" % bb
bb = bb_of(lid)
assert (abs(bb.ZMin - (CAV_Z1 - SK_D)) < 0.01 and abs(bb.ZMax - HX) < 0.01), \
    "裙盖 bbox: %s" % bb
bb = bb_of(pump_asm)
nz_top = G.PUMP_AXIS_Z + G._PNEU["pump_h"] - G._PNEU["pump_dia"] / 2.0
assert (abs(bb.XMin - T - G.PMOD_CLR) < 0.01 and abs(bb.ZMax - nz_top) < 0.01 and
        abs(bb.ZMin - G.PUMP_AXIS_Z + G._PNEU["pump_dia"] / 2.0) < 0.01), \
    "泵 bbox: %s (期望 x0=%.2f z1=%.2f)" % (bb, T + G.PMOD_CLR, nz_top)
bb = bb_of(bkt_asm)
assert abs(bb.ZMin - T) < 0.01 and abs(bb.ZMax - T - G.BKT_FOOT_T - G.BKT_OD) < 0.01, \
    "支架 bbox: %s" % bb

# 嘴顶-盖板底净空 (1.0 设计隙) 与 腔内容隙断言
assert abs((CAV_Z1 - nz_top) - 1.0) < 0.01, "嘴顶净空 != 1.0"
# 内部干涉 = 0: 壳/盖 vs 泵/支架, 支架 vs 泵 (环孔 +0.2 间隙), 支架脚与底板为面接触
v1 = base.common(pump_asm).Volume
v2 = base.common(bkt_asm).Volume
v3 = lid.common(pump_asm).Volume
v4 = lid.common(bkt_asm).Volume
v5 = pump_asm.common(bkt_asm).Volume
assert max(v1, v2, v3, v4, v5) < 1e-3, "泵模块内部干涉: base∩pump=%.3f base∩bkt=%.3f " \
    "lid∩pump=%.3f lid∩bkt=%.3f pump∩bkt=%.3f" % (v1, v2, v3, v4, v5)
# 面板三孔贯通: 探针
for dy in (-G.PMOD_PORT_DY, G.PMOD_PORT_DY):
    pr = Part.makeCylinder(G.PMOD_PORT_D / 2, 2.0,
                           mod(LX - 1.0, G.PMOD_CY + dy, G.PUMP_AXIS_Z), App.Vector(1, 0, 0))
    assert base.common(pr).Volume < 1e-6, "快插孔 (dy=%.0f) 未贯通" % dy
pr = Part.makeCylinder(G.PMOD_WIRE_D / 2, 2.0, mod(LX - 1.0, G.PMOD_CY, G.PMOD_WIRE_Z),
                       App.Vector(1, 0, 0))
assert base.common(pr).Volume < 1e-6, "出线孔未贯通"
# 支架环与泵同轴夹持: 环孔壁-泵面径向隙 0.1 (ID24.2 vs ⌀24)
assert abs((G.BKT_ID - G._PNEU["pump_dia"]) - 0.2) < 1e-9, "环孔径向隙 != 0.2"

print("[pump] 底盒 bbox=%s" % bb_of(base))
print("[pump] 内部干涉 5 对全 0 (base/lid vs pump/brackets, pump vs brackets)")
print("[pump] 面板: 快插 ⌀%.1fx2 @z=%.1f + 出线 ⌀%.1f; 嘴顶净空 1.0mm"
      % (G.PMOD_PORT_D, G.PUMP_AXIS_Z, G.PMOD_WIRE_D))

# ---------- 6. 输出 (统一平移到壳系; 纯平移用 Shape.translate 精确移位 —
#     transformGeometry 会重建几何面, 薄壁裙环上曾产生破面 (34+10 facets 教训)) ----------
for sh in (base, lid, pump_asm, bkt_asm):
    sh.translate(App.Vector(OX0, OY0, OZ0))
case_asm = Part.makeCompound([base, lid])

doc = App.newDocument("flowio-p1-pump-module")
for nm, sh in (("Base", base), ("Lid", lid), ("Pump", pump_asm), ("Brackets", bkt_asm)):
    o = doc.addObject("Part::Feature", nm)
    o.Shape = sh
doc.recompute()
doc.saveAs(os.path.join(HERE, "flowio-p1-pump-module.FCStd"))
case_asm.exportStep(os.path.join(HERE, "pump-module.step"))
# 泵/支架 STEP (与 STL 同一 solids; make_assembly 直载) — 旧 mesh→Part.Shape 转换路径
# 在 FreeCAD 1.1.4 (20260928 build) 原生崩溃 (无 Python 异常), STEP 为唯一可靠载体
pump_asm.exportStep(os.path.join(HERE, "pump.step"))
bkt_asm.exportStep(os.path.join(HERE, "brackets.step"))


def write_stl(shape, path, min_shells):
    """逐 solid 细分 + addMesh 合并导出 — meshFromShape 直接吃复合体会产生破壳
    (FreeCAD 1.1.4: 共面盒复合体 40 facets/4 open shells 实测), 逐体细分各闭合.
    + 逐连通壳闭合自检."""
    import MeshPart
    out = None
    for s in shape.Solids:
        m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.4, AngularDeflection=0.5)
        if out is None:
            out = Mesh.Mesh(m)
        else:
            out.addMesh(m)
    out.write(path)
    comps = out.getSeparateComponents()
    assert len(comps) >= min_shells and all(c.isSolid() for c in comps), \
        "%s: shells=%d closed=%s" % (path, len(comps), [c.isSolid() for c in comps])
    print("[pump-stl] %s shells=%d facets=%d" % (os.path.basename(path), len(comps), out.CountFacets))
    return out


write_stl(case_asm, os.path.join(HERE, "pump-module.stl"), 2)     # 底盒+裙盖
write_stl(pump_asm, os.path.join(HERE, "pump.stl"), 3)            # 体+双嘴
write_stl(bkt_asm, os.path.join(HERE, "brackets.stl"), 2)         # 支架×2
print("PUMP MODULE OK: FCStd + pump-module.step/.stl + pump.stl + brackets.stl -> %s" % HERE)
