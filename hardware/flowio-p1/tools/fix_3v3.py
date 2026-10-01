# tools/fix_3v3.py — +3V3 尾巴补连. 用法: fix_3v3.py pads|diag-j6|del-j6|add-j6
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]
TAPS = [("C13.1", 54.725, 17.5), ("TP1.1", 58.5, 21.5), ("R29.1", 62.0, 30.7534), ("C12.1", 79.225, 25.5)]
J6VIA = (88.0001, 28.69)
if mode == "pads":
    b, pads, trks, vias = G.load()
    for ref, ax, ay in TAPS:
        pad = next(p for p in pads if p["ref"] == ref)
        spot = G.find_spot(pad["x"], pad["y"], "+3V3", pads, trks, vias, anchor=(pad["x"], pad["y"]), rmax=3.5, route_layer=pcbnew.F_Cu)
        assert spot, ref + " 无落点"
        path = G.plan_route((pad["x"], pad["y"]), spot, "+3V3", 0.3, pads, trks, vias, pcbnew.F_Cu)
        assert path, ref + " 路由失败"
        G.add_via(b, spot[0], spot[1], "+3V3")
        print(ref, "via @", spot, "segs:", G.add_route(b, path, pcbnew.F_Cu, "+3V3", 0.3))
        pads.append(dict(x=spot[0], y=spot[1], r=0.4, rc=0.4, w=0.8, h=0.8, rot=0.0, net="+3V3", drill=0.4, npth=False, ref=ref+"V"))
        vias.append((spot[0], spot[1], "+3V3", 0.8))
        trks.append(("+3V3", pcbnew.F_Cu, pad["x"], pad["y"], spot[0], spot[1], 0.3))
    G.refill_save(b)
elif mode == "diag-j6":
    b = pcbnew.LoadBoard(G.BF)
    p = pcbnew.VECTOR2I(pcbnew.FromMM(J6VIA[0]), pcbnew.FromMM(J6VIA[1]))
    hit = False
    for z in b.Zones():
        if z.GetNetname() == "+3V3":
            if z.HasFilledPolysForLayer(pcbnew.In2_Cu) and z.HitTestFilledArea(pcbnew.In2_Cu, p):
                hit = True
    print("J6 via In2 3V3 填充命中:", hit, "(True=填充实心; False=在填充空洞/让位区, 需迁移)")
elif mode == "del-j6":
    b = pcbnew.LoadBoard(G.BF)
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition()
            if abs(pcbnew.ToMM(c.x) - J6VIA[0]) < 0.08 and abs(pcbnew.ToMM(c.y) - J6VIA[1]) < 0.08:
                b.Remove(t); print("removed J6 via")
    pcbnew.SaveBoard(G.BF, b)
elif mode == "add-j6":
    b, pads, trks, vias = G.load()
    j6 = next(p for p in pads if p["ref"] == "J6.1")
    spot = G.find_spot(J6VIA[0] - 1.0, J6VIA[1] + 1.0, "+3V3", pads, trks, vias, anchor=(j6["x"], j6["y"]), rmax=4.0, route_layer=pcbnew.F_Cu)
    assert spot, "J6 新落点未找到"
    path = G.plan_route((j6["x"], j6["y"]), spot, "+3V3", 0.3, pads, trks, vias, pcbnew.F_Cu)
    assert path, "J6 路由失败"
    G.add_via(b, spot[0], spot[1], "+3V3")
    print("J6.1 via @", spot, "segs:", G.add_route(b, path, pcbnew.F_Cu, "+3V3", 0.3))
    G.refill_save(b)
