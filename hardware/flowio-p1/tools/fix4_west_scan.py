# -*- coding: utf-8 -*-
"""fix4b: 西绕行走廊扫描 x23-26, y19-29 全层 + 路径核验 (30.773,19.5)->(V,21.2)->(V,27.1)->(30.773,27.1)."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
def ln(l):
    return {0: "F", 2: "B", 4: "In1", 6: "In2"}.get(l, f"L{l}")

X0, X1, Y0, Y1 = 22.8, 26.2, 18.8, 28.8
print(f"=== 窗口 x{X0}-{X1}, y{Y0}-{Y1} ===")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        if X0 <= MM(q.x) <= X1 and Y0 <= MM(q.y) <= Y1:
            print(f"  via {t.GetNetname()} ({MM(q.x):.3f},{MM(q.y):.3f}) w={MM(t.GetWidth(0)):.3f}")
    else:
        s, e = t.GetStart(), t.GetEnd()
        ax, ay, bx, by = MM(s.x), MM(s.y), MM(e.x), MM(e.y)
        if not (max(ax, bx) < X0-1 or min(ax, bx) > X1+1 or max(ay, by) < Y0-1 or min(ay, by) > Y1+1):
            print(f"  {ln(t.GetLayer())} {t.GetNetname()} ({ax:.3f},{ay:.3f})->({bx:.3f},{by:.3f}) w={MM(t.GetWidth()):.3f}")
for f in b.GetFootprints():
    for p in f.Pads():
        c = p.GetPosition()
        if X0-1 <= MM(c.x) <= X1+1 and Y0-1 <= MM(c.y) <= Y1+1:
            sz = p.GetSize()
            print(f"  pad {f.GetReference()}.{p.GetPadName()} {p.GetNetname()} ({MM(c.x):.3f},{MM(c.y):.3f}) {MM(sz.x):.2f}x{MM(sz.y):.2f} attr={p.GetAttribute()}")
