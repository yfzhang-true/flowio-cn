# tools/move_gndvia.py — R14.1 旁 GND 缝合过孔移位. 用法: move_gndvia.py del|add
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
OLD = (27.00, 32.30)
if mode == "del":
    b = pcbnew.LoadBoard(G.BF)
    n = 0
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            if abs(pcbnew.ToMM(p.x) - OLD[0]) < 0.08 and abs(pcbnew.ToMM(p.y) - OLD[1]) < 0.08:
                b.Remove(t); n += 1
    pcbnew.SaveBoard(G.BF, b)
    print("removed", n)
else:
    b, pads, trks, vias = G.load()
    spot = G.find_spot(OLD[0], OLD[1], "GND", pads, trks, vias, rmax=3.0)
    assert spot, "GND 新落点未找到"
    G.add_via(b, spot[0], spot[1], "GND")
    G.refill_save(b)
    print("GND via ->", spot)
