# -*- coding: utf-8 -*-
"""fix4b 分析: IO21 网全貌 + 走廊障碍清单."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM

def ln(l):
    return {0: "F", 2: "B", 4: "In1", 6: "In2"}.get(l, f"L{l}")

print("=== IO21 pads ===")
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == "IO21":
            c = p.GetPosition()
            print(f"  {f.GetReference()}.{p.GetPadName()} ({MM(c.x):.3f},{MM(c.y):.3f})")

print("=== IO21 vias ===")
for t in b.GetTracks():
    if t.GetNetname() != "IO21":
        continue
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        print(f"  via ({MM(q.x):.3f},{MM(q.y):.3f})")

print("=== IO21 tracks (by layer) ===")
for t in b.GetTracks():
    if t.GetNetname() != "IO21" or t.GetClass() == "PCB_VIA":
        continue
    s, e = t.GetStart(), t.GetEnd()
    print(f"  {ln(t.GetLayer())}: ({MM(s.x):.3f},{MM(s.y):.3f})->({MM(e.x):.3f},{MM(e.y):.3f}) w={MM(t.GetWidth()):.3f}")

print("=== IO11/IO12 tracks (墙) ===")
for t in b.GetTracks():
    if t.GetNetname() not in ("IO11", "IO12") or t.GetClass() == "PCB_VIA":
        continue
    s, e = t.GetStart(), t.GetEnd()
    if 30 < MM(s.x) < 55 or 30 < MM(e.x) < 55:
        print(f"  {t.GetNetname()} {ln(t.GetLayer())}: ({MM(s.x):.3f},{MM(s.y):.3f})->({MM(e.x):.3f},{MM(e.y):.3f}) w={MM(t.GetWidth()):.3f}")

print("=== IO11/IO12 vias ===")
for t in b.GetTracks():
    if t.GetNetname() in ("IO11", "IO12") and t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        print(f"  {t.GetNetname()} via ({MM(q.x):.3f},{MM(q.y):.3f})")
