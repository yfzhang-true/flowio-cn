# -*- coding: utf-8 -*-
"""fix4b: x30.773 竖列 y19-28 障碍核验 — In1 走线/via/焊盘 + 各层参考."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
def ln(l):
    return {0: "F", 2: "B", 4: "In1", 6: "In2"}.get(l, f"L{l}")

X0, X1, Y0, Y1 = 29.0, 32.6, 18.5, 29.0
print(f"=== 窗口 x{X0}-{X1}, y{Y0}-{Y1} 全层障碍 ===")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        if X0 <= MM(q.x) <= X1 and Y0 <= MM(q.y) <= Y1:
            print(f"  via {t.GetNetname()} ({MM(q.x):.3f},{MM(q.y):.3f}) w={MM(t.GetWidth(0)):.3f}")
    else:
        s, e = t.GetStart(), t.GetEnd()
        ax, ay, bx, by = MM(s.x), MM(s.y), MM(e.x), MM(e.y)
        if not (max(ax, bx) < X0 or min(ax, bx) > X1 or max(ay, by) < Y0 or min(ay, by) > Y1):
            print(f"  {ln(t.GetLayer())} {t.GetNetname()} ({ax:.3f},{ay:.3f})->({bx:.3f},{by:.3f}) w={MM(t.GetWidth()):.3f}")
for f in b.GetFootprints():
    for p in f.Pads():
        c = p.GetPosition()
        if X0 <= MM(c.x) <= X1 and Y0 <= MM(c.y) <= Y1:
            sz = p.GetSize()
            print(f"  pad {f.GetReference()}.{p.GetPadName()} {p.GetNetname()} ({MM(c.x):.3f},{MM(c.y):.3f}) {MM(sz.x):.2f}x{MM(sz.y):.2f} attr={p.GetAttribute()}")
