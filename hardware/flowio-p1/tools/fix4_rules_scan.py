# -*- coding: utf-8 -*-
"""fix4b: 规则/In2/焊盘属性核验 — 设计规则净距, In2 现有7走线, 关键焊盘 TH 属性."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
def ln(l):
    return {0: "F", 2: "B", 4: "In1", 6: "In2"}.get(l, f"L{l}")

print("=== 设计规则 ===")
ds = b.GetDesignSettings()
print("min clearance (board):", MM(ds.m_MinClearance), "mm; hole clr:", MM(ds.m_HoleClearance))
print("smallest/biggest netclass clr:", MM(ds.GetSmallestClearanceValue()), MM(ds.GetBiggestClearanceValue()))
try:
    for nc in b.GetNetClasses():
        print(f"netclass {nc.GetName()}: clr={MM(nc.GetClearance())} trkW={MM(nc.GetTrackWidth())} via={MM(nc.GetViaDiameter())}/{MM(nc.GetViaDrill())}")
except Exception as e:
    print("netclass err:", e)

print("=== In2 (L6) 全部走线 ===")
for t in b.GetTracks():
    if t.GetClass() != "PCB_VIA" and t.GetLayer() == 6:
        s, e = t.GetStart(), t.GetEnd()
        print(f"  {t.GetNetname()} ({MM(s.x):.3f},{MM(s.y):.3f})->({MM(e.x):.3f},{MM(e.y):.3f}) w={MM(t.GetWidth()):.3f}")

print("=== 关键焊盘属性 (TH?) ===")
for ref, pn in [("L1", None), ("SW3", None), ("R24", None), ("R27", None), ("TP6", None), ("TP7", None), ("TP8", None), ("C5", None)]:
    for f in b.GetFootprints():
        if f.GetReference() == ref:
            for p in f.Pads():
                c = p.GetPosition()
                print(f"  {ref}.{p.GetPadName()} {p.GetNetname()} ({MM(c.x):.2f},{MM(c.y):.2f}) attr={p.GetAttribute()} (0=SMD,1=TH)")
            break

print("=== In2 zones 边界 (哪个覆盖桥窗 x46-47.3,y33-41) ===")
def pip(x, y, xs, ys):
    n_, ins = len(xs), False
    j_ = n_ - 1
    for i_ in range(n_):
        if (ys[i_] > y) != (ys[j_] > y) and x < (xs[j_]-xs[i_])*(y-ys[i_])/(ys[j_]-ys[i_]+1e-12)+xs[i_]:
            ins = not ins
        j_ = i_
    return ins
for z in b.Zones():
    if z.GetLayer() != 6:
        continue
    polys = z.GetFilledPolysList(6)
    covers = False
    bb = (999, 999, -999, -999)
    for i in range(polys.OutlineCount()):
        ch = polys.Outline(i)
        xs = [MM(ch.CPoint(k).x) for k in range(ch.PointCount())]
        ys = [MM(ch.CPoint(k).y) for k in range(ch.PointCount())]
        bb = (min(bb[0], min(xs)), min(bb[1], min(ys)), max(bb[2], max(xs)), max(bb[3], max(ys)))
        for px, py in [(46.0, 38), (47.0, 34), (46.6, 36)]:
            if pip(px, py, xs, ys):
                covers = True
    print(f"  In2 zone {z.GetNetname()} prio={z.GetPriority()} bbox=({bb[0]:.1f},{bb[1]:.1f})-({bb[2]:.1f},{bb[3]:.1f}) 覆盖桥窗={covers}")
