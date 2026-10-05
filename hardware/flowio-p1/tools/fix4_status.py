# -*- coding: utf-8 -*-
"""fix4 状态检查: ratsnest 未连清单 + GND zone 填充碎片清单."""
import sys
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM

b.BuildConnectivity()
bcc = b.GetConnectivity()
print("unconnected:", bcc.GetUnconnectedCount(True))

# 列出每条未连 (from -> to), 用 ratsnest edges
try:
    for rn in bcc.GetRatsnest():
        if rn.GetIsVisible():
            s, e = rn.GetSource(), rn.GetTarget()
            print(f"rat: ({MM(s.x):.3f},{MM(s.y):.3f}) -> ({MM(e.x):.3f},{MM(e.y):.3f}) net={rn.GetNet()}")
except Exception as ex:
    print("ratsnest enum fail:", ex)
print("--- GND zones ---")
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() != "GND":
        continue
    ly = z.GetLayer()
    polys = z.GetFilledPolysList(ly)
    n = polys.OutlineCount()
    tot = 0
    for i in range(n):
        ch = polys.Outline(i)
        xs = [MM(ch.CPoint(k).x) for k in range(ch.PointCount())]
        ys = [MM(ch.CPoint(k).y) for k in range(ch.PointCount())]
        if (max(xs)-min(xs))*(max(ys)-min(ys)) < 0.05:
            continue
        tot += 1
    print(f"zone L{ly} net={z.GetNetname()} outlines={n} bigfrags={tot}")
