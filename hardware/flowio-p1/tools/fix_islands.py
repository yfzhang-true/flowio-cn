# tools/fix_islands.py — 平面孤岛清零. 用法: fix_islands.py bridge|probe|stitch
import sys; sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
mode = sys.argv[1]

def bridge(b, net, layer, pts, name):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNetCode(G.netcode(b, net))
    z.SetMinThickness(int(pcbnew.FromMM(0.3))); z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for cx, cy in pts: ol.Append(int(pcbnew.FromMM(cx)), int(pcbnew.FromMM(cy)))
    b.Add(z); print("bridge", name, net)

if mode == "bridge":
    b, pads, trks, vias = G.load()
    # 3V3: 顶带(…y≤20.8) 与 下L块(y≥20.8) 跨缝桥, 两侧各压 0.4
    bridge(b, "+3V3", pcbnew.In2_Cu, [(20.0, 20.4), (35.5, 20.4), (35.5, 21.2), (20.0, 21.2)], "BR_3V3")
    # 5V: A块(x≤19) 与 B块(x≥19) 跨缝桥 (x19.2-36.2/y27.8-52.8 是 3V3, 桥放 y53-55 B块与底带交叠区无意义;
    #     A右边缘 x=19 y21-55, B左边缘 x=19 y28-55 → 桥贴 x19, y30-50, 宽 0.8)
    bridge(b, "+5V", pcbnew.In2_Cu, [(18.6, 30.0), (19.4, 30.0), (19.4, 50.0), (18.6, 50.0)], "BR_5V")
    G.refill_save(b)
elif mode == "probe":
    def pip(x, y, xs, ys):  # even-odd ray casting on one outline
        n, inside = len(xs), False
        j = n - 1
        for i in range(n):
            if (ys[i] > y) != (ys[j] > y) and x < (xs[j]-xs[i])*(y-ys[i])/(ys[j]-ys[i]+1e-12)+xs[i]:
                inside = not inside
            j = i
        return inside
    b = pcbnew.LoadBoard(G.BF)
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != "GND": continue
        for ly in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.HasFilledPolysForLayer(ly): continue
            ps = z.GetFilledPolysList(ly)
            gnd_vias = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
                        for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]
            gnd_pads = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
                        for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == "GND"]
            for i in range(ps.OutlineCount()):
                ch = ps.Outline(i)
                xs = [pcbnew.ToMM(ch.CPoint(j).x) for j in range(ch.PointCount())]
                ys = [pcbnew.ToMM(ch.CPoint(j).y) for j in range(ch.PointCount())]
                if (max(xs)-min(xs)) * (max(ys)-min(ys)) < 1.0: continue   # <1mm² 碎屑忽略
                anchored = any(pip(vx, vy, xs, ys) for vx, vy in gnd_vias) \
                    or any(pip(px, py, xs, ys) for px, py in gnd_pads)
                if not anchored:
                    gx, gy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
                    if not pip(gx, gy, xs, ys):  # 质心不在则扫网格
                        found = False
                        for kx in range(1, 6):
                            for ky in range(1, 6):
                                gx2 = min(xs)+(max(xs)-min(xs))*kx/6; gy2 = min(ys)+(max(ys)-min(ys))*ky/6
                                if pip(gx2, gy2, xs, ys): gx, gy, found = gx2, gy2, True; break
                            if found: break
                        if not found: continue
                    print(f"孤岛: {b.GetLayerName(ly)} bbox=({min(xs):.1f},{min(ys):.1f})-({max(xs):.1f},{max(ys):.1f}) 内点=({gx:.1f},{gy:.1f})")
elif mode == "stitch":
    b, pads, trks, vias = G.load()
    ISLANDS = eval(sys.argv[2]) if len(sys.argv) > 2 else []
    for cx, cy in ISLANDS:
        spot = G.find_spot(cx, cy, "GND", pads, trks, vias, rmax=1.5)
        if spot: G.add_via(b, spot[0], spot[1], "GND"); print("stitch @", spot)
        else: print("跳过(无净空):", cx, cy)
    G.refill_save(b)
