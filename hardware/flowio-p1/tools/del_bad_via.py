# tools/del_bad_via.py — 只删不查 (SWIG 一进程一操作)
import pcbnew
BF = "flowio-p1.kicad_pcb"
b = pcbnew.LoadBoard(BF)
n = 0
for t in list(b.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        if abs(x - 78.3649) < 0.05 and abs(y - 60.5) < 0.05:
            b.Remove(t); n += 1
pcbnew.SaveBoard(BF, b)
print("removed", n)
