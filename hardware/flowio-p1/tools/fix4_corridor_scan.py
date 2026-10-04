# -*- coding: utf-8 -*-
"""fix4b: 走廊障碍扫描 — 各层在关键窗内的占用 + In2 全局使用量."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
def ln(l):
    return {0: "F", 2: "B", 4: "In1", 6: "In2"}.get(l, f"L{l}")

# 全局层使用统计
cnt = {}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        cnt["via"] = cnt.get("via", 0) + 1
    else:
        cnt[ln(t.GetLayer())] = cnt.get(ln(t.GetLayer()), 0) + 1
print("track layer counts:", cnt)

# zone 层统计
zl = {}
for z in b.Zones():
    zl.setdefault(ln(z.GetLayer()), []).append(z.GetNetname())
print("zones per layer:", {k: v for k, v in zl.items()})

def in_win(x, y, x0, x1, y0, y1):
    return x0 <= x <= x1 and y0 <= y <= y1

def seg_win(ax, ay, bx, by, x0, x1, y0, y1):
    # 粗判: 任一端在窗内或线段包围盒与窗相交
    return not (max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1)

WINDOWS = [
    ("桥窗 x46.0-47.5, y40.5-44.0", 46.0, 47.5, 40.5, 44.0),
    ("B路径窗 x30-48, y40.0-44.5", 30.0, 48.0, 40.0, 44.5),
    ("墙窗 x44-50, y32-56", 44.0, 50.0, 32.0, 56.0),
]
for wname, x0, x1, y0, y1 in WINDOWS:
    print(f"\n=== {wname} ===")
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            q = t.GetPosition()
            if in_win(MM(q.x), MM(q.y), x0-0.5, x1+0.5, y0-0.5, y1+0.5):
                print(f"  via {t.GetNetname()} ({MM(q.x):.3f},{MM(q.y):.3f}) w={MM(t.GetWidth(0)):.3f}")
        else:
            s, e = t.GetStart(), t.GetEnd()
            if seg_win(MM(s.x), MM(s.y), MM(e.x), MM(e.y), x0-0.5, x1+0.5, y0-0.5, y1+0.5):
                print(f"  {ln(t.GetLayer())} {t.GetNetname()} ({MM(s.x):.3f},{MM(s.y):.3f})->({MM(e.x):.3f},{MM(e.y):.3f}) w={MM(t.GetWidth()):.3f}")
    for f in b.GetFootprints():
        for p in f.Pads():
            c = p.GetPosition()
            if in_win(MM(c.x), MM(c.y), x0-1.0, x1+1.0, y0-1.0, y1+1.0):
                sz = p.GetSize()
                print(f"  pad {f.GetReference()}.{p.GetPadName()} {p.GetNetname()} ({MM(c.x):.3f},{MM(c.y):.3f}) {MM(sz.x):.2f}x{MM(sz.y):.2f} ly={ln(p.GetLayer()) if p.GetLayer()<32 else 'multi'}")
