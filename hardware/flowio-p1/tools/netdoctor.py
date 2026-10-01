# -*- coding: utf-8 -*-
"""netdoctor: 按网分析填充岛并自动缝合 (3V3/5V 岛间连线, GND 岛系锚).
用法: netdoctor.py probe|heal
- probe: 列出 GND/+3V3/+5V 各 zone 填充岛及锚 (via/pad pip 命中)
- heal:  1) GND 无锚岛内放缝合过孔  2) 电源网岛间布 In2/F.Cu 连线  3) 指定焊盘系锚"""
import sys, math
sys.path.insert(0, "tools")
import pcbnew, boardgeom as G

def pip(x, y, xs, ys):
    n, inside = len(xs), False
    j = n - 1
    for i in range(n):
        if (ys[i] > y) != (ys[j] > y) and x < (xs[j]-xs[i])*(y-ys[i])/(ys[j]-ys[i]+1e-12)+xs[i]:
            inside = not inside
        j = i
    return inside

def zone_islands(b, net, layer):
    """返回 [(zone, xs, ys, anchors, interior_pt), ...] — 该网该层每个填充岛."""
    out = []
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != net or not z.HasFilledPolysForLayer(layer): continue
        ps = z.GetFilledPolysList(layer)
        for i in range(ps.OutlineCount()):
            ch = ps.Outline(i)
            xs = [pcbnew.ToMM(ch.CPoint(j).x) for j in range(ch.PointCount())]
            ys = [pcbnew.ToMM(ch.CPoint(j).y) for j in range(ch.PointCount())]
            if (max(xs)-min(xs)) * (max(ys)-min(ys)) < 0.3: continue
            out.append((z, xs, ys))
    return out

def anchors_of(b, xs, ys):
    res = []
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T: continue
        p = t.GetPosition(); vx, vy = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        if pip(vx, vy, xs, ys): res.append((t.GetNetname(), "via", vx, vy))
    for f in b.GetFootprints():
        for p in f.Pads():
            c = p.GetPosition(); px, py = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            if pip(px, py, xs, ys): res.append((p.GetNetname(), f.GetReference()+"."+str(p.GetPadName()), px, py))
    return res

def interior(xs, ys, b, layer, z, want_fill=True):
    """岛内取一个实填充点 (网格扫描, HitTestFilledArea 终验)."""
    for kx in range(1, 10):
        for ky in range(1, 10):
            gx = min(xs)+(max(xs)-min(xs))*kx/10; gy = min(ys)+(max(ys)-min(ys))*ky/10
            if not pip(gx, gy, xs, ys): continue
            pt = pcbnew.VECTOR2I(pcbnew.FromMM(gx), pcbnew.FromMM(gy))
            if want_fill and not z.HitTestFilledArea(layer, pt): continue
            return (round(gx, 2), round(gy, 2))
    return None

if sys.argv[1] == "probe":
    b = pcbnew.LoadBoard(G.BF)
    for net, layer in [("GND", pcbnew.F_Cu), ("GND", pcbnew.B_Cu), ("+3V3", pcbnew.In2_Cu), ("+5V", pcbnew.In2_Cu)]:
        isl = zone_islands(b, net, layer)
        print(f"== {net} @ {b.GetLayerName(layer)}: {len(isl)} 岛")
        for z, xs, ys in isl:
            anc = anchors_of(b, xs, ys)
            pt = interior(xs, ys, b, layer, z)
            print(f"  bbox=({min(xs):.1f},{min(ys):.1f})-({max(xs):.1f},{max(ys):.1f}) 内点={pt} 锚={len(anc)}",
                  [a[1] for a in anc[:4]])

if sys.argv[1] == "heal":
    b, pads, trks, vias = G.load()
    def tie_in2(net, p1, p2, w=0.4):
        t = G.plan_route(p1, p2, net, w, pads, trks, vias, pcbnew.In2_Cu)
        if t:
            G.add_route(b, t, pcbnew.In2_Cu, net, w)
            for a, bb in zip(t, t[1:]): trks.append((net, pcbnew.In2_Cu, a[0], a[1], bb[0], bb[1], w))
            print(f"  TIE {net} In2 直连 {p1}->{p2}")
            return True
        return False
    def tie_lift(net, p1, p2, w=0.3):
        """via 抬到 F.Cu 走桥再落下."""
        s1 = G.find_spot(p1[0], p1[1], net, pads, trks, vias, rmax=1.8)
        s2 = G.find_spot(p2[0], p2[1], net, pads, trks, vias, rmax=1.8)
        if not (s1 and s2): return False
        t = G.plan_route(s1, s2, net, w, pads, trks, vias, pcbnew.F_Cu)
        if not t: return False
        G.add_via(b, s1[0], s1[1], net); G.add_via(b, s2[0], s2[1], net)
        G.add_route(b, t, pcbnew.F_Cu, net, w)
        print(f"  TIE {net} F.Cu 抬桥 {s1}->{s2}")
        return True
    # --- GND: 仅焊盘锚碎片系锚 ---
    GND_FRAGS = [(47.47,33.7),(29.75,26.95),(70.29,21.59),(78.77,6.89)]
    for cx, cy in GND_FRAGS:
        s = G.find_spot(cx, cy, "GND", pads, trks, vias, rmax=1.2)
        if s:
            G.add_via(b, s[0], s[1], "GND"); vias.append((s[0], s[1], "GND", 0.8))
            print(f"  GND 碎片系锚 @ {s}")
        else: print(f"  GND 碎片无净空: {cx},{cy}")
    # --- GND: 填充洞焊盘 (U2.2 / U2.21 / U5.2) via+短走线 ---
    for ref in ("U2.2", "U2.21", "U5.2"):
        pad = next(p for p in pads if p["ref"] == ref)
        s = G.find_spot(pad["x"], pad["y"], "GND", pads, trks, vias, anchor=(pad["x"], pad["y"]), rmax=2.5, route_layer=pcbnew.F_Cu)
        if s:
            t = G.plan_route((pad["x"], pad["y"]), s, "GND", 0.3, pads, trks, vias, pcbnew.F_Cu)
            G.add_via(b, s[0], s[1], "GND"); G.add_route(b, t, pcbnew.F_Cu, "GND", 0.3)
            vias.append((s[0], s[1], "GND", 0.8))
            print(f"  GND 洞焊盘 {ref} 系锚 @ {s}")
        else: print(f"  {ref} 无落点!")
    # --- 3V3 岛间 (各岛内点, probe 验证过 HitTestFilledArea) ---
    T3 = [((54.8,19.5),(54.81,20.27)),          # #7 sliver -> 顶带#6
          ((24.0,19.9),(20.55,22.1)),           # 顶带#6 -> #5(U1)
          ((70.0,19.9),(69.46,26.73)),          # 顶带#6 -> #4(C12)
          ((44.0,19.9),(41.59,40.1)),           # 顶带#6 -> #1(大岛) 长: 失败则抬桥
          ((38.7,43.11),(41.59,40.1))]          # #2(D3) -> #1
    for p1, p2 in T3:
        if not tie_in2("+3V3", p1, p2):
            tie_lift("+3V3", p1, p2)
    # --- 5V 岛间 ---
    T5 = [((21.23,51.84),(20.25,48.4)),         # #1(C15) -> #2
          ((20.25,48.4),(21.23,32.45)),         # #2 -> #3
          ((25.0,55.0),(25.0,41.0))]            # #4(底带) -> #3
    for p1, p2 in T5:
        if not tie_in2("+5V", p1, p2):
            tie_lift("+5V", p1, p2)
    G.refill_save(b)
    print("heal 完成")

if sys.argv[1] == "heal2":
    b, pads, trks, vias = G.load()
    # GND 洞焊盘: 焊盘尖端逃逸 + via (精确矩形距离后应可行)
    for ref, dy in (("U2.2", +1), ("U2.21", +1), ("U2.21", -1), ("U5.2", +1), ("U5.2", -1)):
        pad = next(p for p in pads if p["ref"] == ref)
        done = False
        for sgn in (+1, -1):
            if done: break
            tip = (pad["x"], pad["y"] + sgn * (pad["h"] / 2 + 1.2))
            t = G.plan_route((pad["x"], pad["y"]), tip, "GND", 0.25, pads, trks, vias, pcbnew.F_Cu)
            if not t: continue
            s = G.find_spot(tip[0], tip[1], "GND", pads, trks, vias, rmax=1.5)
            if not s: continue
            G.add_via(b, s[0], s[1], "GND"); G.add_route(b, t, pcbnew.F_Cu, "GND", 0.25)
            vias.append((s[0], s[1], "GND", 0.8))
            print(f"  {ref} 逃逸系锚 @ {s}")
            done = True
        if not done: print(f"  {ref} 仍无逃逸!")
    def tie_lift2(net, p1, p2, w=0.3):
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            s1 = G.find_spot(p1[0], p1[1], net, pads, trks, vias, rmax=2.5)
            s2 = G.find_spot(p2[0], p2[1], net, pads, trks, vias, rmax=2.5)
            if not (s1 and s2): continue
            t = G.plan_route(s1, s2, net, w, pads, trks, vias, lay)
            if not t: continue
            G.add_via(b, s1[0], s1[1], net); G.add_via(b, s2[0], s2[1], net)
            G.add_route(b, t, lay, net, w)
            print(f"  TIE {net} {b.GetLayerName(lay)} 抬桥 {s1}->{s2}")
            return True
        return False
    # 3V3 剩余: 顶带#6 -> #5(U1区), 顶带#6 -> #4(C12区), 顶带#6 -> #1(大岛)
    for p1, p2 in [((24.0,19.5),(20.55,22.1)), ((70.0,19.5),(69.46,26.73)), ((44.0,19.5),(41.59,40.1))]:
        if not tie_lift2("+3V3", p1, p2): print(f"  3V3 tie 失败: {p1}->{p2}")
    # 5V 剩余: #1->#2, #2->#3, #4->#3
    for p1, p2 in [((21.23,51.84),(20.25,48.4)), ((20.25,48.4),(21.23,32.45)), ((25.0,55.5),(25.0,41.5))]:
        if not tie_lift2("+5V", p1, p2): print(f"  5V tie 失败: {p1}->{p2}")
    G.refill_save(b)
    print("heal2 完成")

if sys.argv[1] == "heal3":
    import math as _m
    b, pads, trks, vias = G.load()
    def fill_solid(x, y, net, layer=pcbnew.In2_Cu, r=0.25):
        """该点及四向偏移都落在同网填充内 (保证过孔环整体在实铜上)."""
        for dx, dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r)):
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x+dx), pcbnew.FromMM(y+dy))
            ok = False
            for z in b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() != net: continue
                if z.HasFilledPolysForLayer(layer) and z.HitTestFilledArea(layer, p): ok = True; break
            if not ok: return False
        return True
    def spot_in_fill(cx, cy, net, rmax=2.5):
        r = 0.2
        while r <= rmax:
            n = max(8, int(2*_m.pi*r/0.25))
            for i in range(n):
                a = 2*_m.pi*i/n
                x, y = cx + r*_m.cos(a), cy + r*_m.sin(a)
                if fill_solid(x, y, net) and G.spot_ok(x, y, net, pads, trks, vias):
                    return round(x,3), round(y,3)
            r += 0.25
        return None
    def lift_tie(net, c1, c2, w=0.3):
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            s1 = spot_in_fill(c1[0], c1[1], net); s2 = spot_in_fill(c2[0], c2[1], net)
            if not (s1 and s2):
                print(f"    [lift] 填充实心落点缺失: {s1} {s2}"); continue
            t = G.plan_route(s1, s2, net, w, pads, trks, vias, lay)
            if not t: continue
            G.add_via(b, s1[0], s1[1], net); G.add_via(b, s2[0], s2[1], net)
            G.add_route(b, t, lay, net, w)
            for a2, b2 in zip(t, t[1:]): trks.append((net, lay, a2[0], a2[1], b2[0], b2[1], w))
            vias.append((s1[0], s1[1], net, 0.8)); vias.append((s2[0], s2[1], net, 0.8))
            print(f"  TIE {net} {b.GetLayerName(lay)} 抬桥 {s1}->{s2}")
            return True
        return False
    def direct_tie(net, c1, c2, w=0.4):
        t = G.plan_route(c1, c2, net, w, pads, trks, vias, pcbnew.In2_Cu)
        if t and fill_solid(*c1, net) and fill_solid(*c2, net):
            G.add_route(b, t, pcbnew.In2_Cu, net, w)
            for a2, b2 in zip(t, t[1:]): trks.append((net, pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], w))
            print(f"  TIE {net} In2 直连 {c1}->{c2}")
            return True
        return False
    # 3V3: 缝(band->#3 x29.5 窗), band->#5, band->#4, #3->#1 近距对
    T3 = [((29.5,19.9),(29.5,22.6)), ((24.0,19.5),(20.55,22.1)),
          ((70.0,19.5),(69.46,26.73)), ((38.0,22.0),(38.0,25.0))]
    for c1, c2 in T3:
        if not direct_tie("+3V3", c1, c2):
            if not lift_tie("+3V3", c1, c2): print(f"  3V3 tie 彻底失败: {c1}->{c2}")
    # 5V: #1->#2, #2->#3, #3->#4(跨 y44-48 断带, 长距用抬桥)
    T5 = [((21.23,51.84),(20.25,48.4)), ((20.25,48.4),(21.23,32.45)), ((25.0,55.5),(25.0,41.5))]
    for c1, c2 in T5:
        if not direct_tie("+5V", c1, c2):
            if not lift_tie("+5V", c1, c2): print(f"  5V tie 彻底失败: {c1}->{c2}")
    # GND 洞焊盘重试 (U2.21/U5.2)
    for ref in ("U2.21", "U5.2"):
        pad = next(p for p in pads if p["ref"] == ref)
        done = False
        for sgn in (+1, -1):
            tip = (pad["x"], pad["y"] + sgn * (pad["h"] / 2 + 1.0))
            t = G.plan_route((pad["x"], pad["y"]), tip, "GND", 0.25, pads, trks, vias, pcbnew.F_Cu)
            if not t: continue
            s = G.find_spot(tip[0], tip[1], "GND", pads, trks, vias, rmax=3.0)
            if not s: continue
            G.add_via(b, s[0], s[1], "GND"); G.add_route(b, t, pcbnew.F_Cu, "GND", 0.25)
            vias.append((s[0], s[1], "GND", 0.8))
            print(f"  {ref} 逃逸系锚 @ {s}")
            done = True; break
        if not done: print(f"  {ref} 仍无逃逸!")
    G.refill_save(b)
    print("heal3 完成")

if sys.argv[1] == "heal4":
    import math as _m
    b, pads, trks, vias = G.load()
    def fill_solid(x, y, net, layer, r=0.15):
        for dx, dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r)):
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x+dx), pcbnew.FromMM(y+dy))
            ok = False
            for z in b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() != net: continue
                if z.HasFilledPolysForLayer(layer) and z.HitTestFilledArea(layer, p): ok = True; break
            if not ok: return False
        return True
    def island_points(net, layer, step=1.0):
        """每个填充岛返回一个 (内点, 岛bbox) 列表, 内点须实心+可放过孔."""
        res = []
        for z, xs, ys in zone_islands(b, net, layer):
            best = None
            for kx in range(1, 12):
                for ky in range(1, 12):
                    gx = min(xs)+(max(xs)-min(xs))*kx/12; gy = min(ys)+(max(ys)-min(ys))*ky/12
                    if not pip(gx, gy, xs, ys): continue
                    if not fill_solid(gx, gy, net, layer): continue
                    if not G.spot_ok(gx, gy, net, pads, trks, vias): continue
                    best = (round(gx,2), round(gy,2)); break
                if best: break
            res.append((best, (min(xs), min(ys), max(xs), max(ys))))
        return res
    def try_tie(net, c1, c2):
        # In2 直连
        t = G.plan_route(c1, c2, net, 0.4, pads, trks, vias, pcbnew.In2_Cu)
        if t:
            G.add_route(b, t, pcbnew.In2_Cu, net, 0.4)
            for a2, b2 in zip(t, t[1:]): trks.append((net, pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], 0.4))
            print(f"  TIE {net} In2 {c1}->{c2}"); return True
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            t = G.plan_route(c1, c2, net, 0.3, pads, trks, vias, lay)
            if not t: continue
            G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
            G.add_route(b, t, lay, net, 0.3)
            vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
            for a2, b2 in zip(t, t[1:]): trks.append((net, lay, a2[0], a2[1], b2[0], b2[1], 0.3))
            print(f"  TIE {net} {b.GetLayerName(lay)} 抬桥 {c1}->{c2}"); return True
        return False
    # U5.2 via-in-pad 直下 In1 地平面
    u52 = next(p for p in pads if p["ref"] == "U5.2")
    if G.spot_ok(u52["x"], u52["y"], "GND", pads, trks, vias):
        G.add_via(b, u52["x"], u52["y"], "GND", od=0.6, drill=0.3)
        print(f"  U5.2 via-in-pad @ ({u52['x']},{u52['y']})")
    else:
        print("  U5.2 via-in-pad 被拒!")
    # 电源网: 岛间两轮就近搭桥
    for rnd in range(2):
        for net in ("+3V3", "+5V"):
            pts = island_points(net, pcbnew.In2_Cu)
            usable = [p for p, bb in pts if p]
            print(f"[r{rnd}] {net}: {len(pts)} 岛, 可用点 {len(usable)}: {usable}")
            if len(usable) < 2: continue
            usable.sort()
            # 相邻点依次搭 (排序后相邻距离通常最短)
            for c1, c2 in zip(usable, usable[1:]):
                if _m.hypot(c2[0]-c1[0], c2[1]-c1[1]) > 30: continue
                try_tie(net, c1, c2)
    G.refill_save(b)
    print("heal4 完成")

if sys.argv[1] == "heal5":
    import math as _m
    b, pads, trks, vias = G.load()
    def fill_solid(x, y, net, layer, r=0.15):
        for dx, dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r)):
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x+dx), pcbnew.FromMM(y+dy))
            ok = False
            for z in b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() != net: continue
                if z.HasFilledPolysForLayer(layer) and z.HitTestFilledArea(layer, p): ok = True; break
            if not ok: return False
        return True
    def island_points(net, layer, step=1.0):
        res = []
        for z, xs, ys in zone_islands(b, net, layer):
            for kx in range(1, 13):
                for ky in range(1, 13):
                    gx = min(xs)+(max(xs)-min(xs))*kx/12; gy = min(ys)+(max(ys)-min(ys))*ky/12
                    if not pip(gx, gy, xs, ys): continue
                    if not fill_solid(gx, gy, net, layer): continue
                    if not G.spot_ok(gx, gy, net, pads, trks, vias): continue
                    res.append((round(gx,2), round(gy,2))); break
                else: continue
                break
        return res
    def try_tie(net, c1, c2):
        t = G.plan_route(c1, c2, net, 0.4, pads, trks, vias, pcbnew.In2_Cu)
        if t:
            G.add_route(b, t, pcbnew.In2_Cu, net, 0.4)
            for a2, b2 in zip(t, t[1:]): trks.append((net, pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], 0.4))
            print(f"  TIE {net} In2 {c1}->{c2}"); return True
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            t = G.plan_route(c1, c2, net, 0.3, pads, trks, vias, lay)
            if not t: continue
            G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
            G.add_route(b, t, lay, net, 0.3)
            vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
            for a2, b2 in zip(t, t[1:]): trks.append((net, lay, a2[0], a2[1], b2[0], b2[1], 0.3))
            print(f"  TIE {net} {b.GetLayerName(lay)} 抬桥 {c1}->{c2}"); return True
        return False
    for net in ("+3V3", "+5V"):
        pts = island_points(net, pcbnew.In2_Cu)
        print(f"{net}: {len(pts)} 可用岛点 {pts}")
        pairs = sorted([( _m.hypot(c2[0]-c1[0], c2[1]-c1[1]), c1, c2)
                        for i, c1 in enumerate(pts) for c2 in pts[i+1:]])
        done = 0
        for dist, c1, c2 in pairs:
            if done >= max(0, len(pts) - 1): break
            if dist > 30: continue
            if try_tie(net, c1, c2): done += 1
    # U2.21 北向逃逸 (北面 y<40 区域, 避 NC 脚排 y40.98)
    pad = next(p for p in pads if p["ref"] == "U2.21")
    for dy in (-1,):
        tip = (pad["x"], pad["y"] + dy * (pad["h"] / 2 + 0.8))
        t = G.plan_route((pad["x"], pad["y"]), tip, "GND", 0.25, pads, trks, vias, pcbnew.F_Cu)
        s = G.find_spot(tip[0], tip[1], "GND", pads, trks, vias, rmax=3.0) if t else None
        if t and s:
            G.add_via(b, s[0], s[1], "GND"); G.add_route(b, t, pcbnew.F_Cu, "GND", 0.25)
            print(f"  U2.21 北向逃逸 @ {s}")
            break
        print(f"  U2.21 北向失败 (route={bool(t)} spot={s})")
    G.refill_save(b)
    print("heal5 完成")

if sys.argv[1] == "heal6":
    import math as _m, heapq
    b, pads, trks, vias = G.load()
    GR = 0.5
    NX, NY = int(92/GR), int(77/GR)
    def g2m(i, j): return (i*GR, j*GR)
    def m2g(x, y): return (int(round(x/GR)), int(round(y/GR)))
    def blocked_grid(layer, net, extra_rects=()):
        """保守模型: 焊盘外接圆 / 走线膨胀带 / 过孔圆 / 额外矩形."""
        B = bytearray(NX*NY)
        def mark(x, y, r):
            i0, i1 = max(0, int((x-r)/GR)), min(NX-1, int((x+r)/GR))
            j0, j1 = max(0, int((y-r)/GR)), min(NY-1, int((y+r)/GR))
            for i in range(i0, i1+1):
                for j in range(j0, j1+1):
                    if _m.hypot(i*GR-x, j*GR-y) <= r: B[i*NY+j] = 1
        for p in pads:
            if p["net"] == net and not p["npth"]: continue
            mark(p["x"], p["y"], p["rc"] + 0.4 + 0.21)
        for tn, tly, ax, ay, bx, by, w in trks:
            if tn == net or (layer is not None and tly != layer): continue
            for k in range(int(_m.hypot(bx-ax, by-ay)/ (GR*0.7)) + 1):
                t = k / max(1, int(_m.hypot(bx-ax, by-ay)/(GR*0.7)))
                mark(ax+(bx-ax)*t, ay+(by-ay)*t, w/2 + 0.4 + 0.21)
        for vx, vy, vnet, vw in vias:
            if vnet == net: continue
            mark(vx, vy, vw/2 + 0.4 + 0.21)
        for (x0, y0, x1, y1) in extra_rects:
            for i in range(int(x0/GR), int(x1/GR)+1):
                for j in range(int(y0/GR), int(y1/GR)+1): B[i*NY+j] = 1
        return B
    def astar(net, s, t, Blk, maxm=120):
        (si, sj), (ti, tj) = m2g(*s), m2g(*t)
        def h(i, j): return _m.hypot(i-ti, j-tj)*GR
        openh = [(h(si,sj), 0.0, si, sj, None)]
        best = {}
        goal = None
        while openh:
            f, g, i, j, parent = heapq.heappop(openh)
            if (i, j) in best: continue
            best[(i, j)] = parent
            if abs(i-ti) <= 1 and abs(j-tj) <= 1:
                goal = (i, j); break
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni, nj = i+di, j+dj
                if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj]: continue
                if (ni, nj) in best: continue
                ng = g + GR*(_m.hypot(di, dj))
                if ng > maxm: continue
                heapq.heappush(openh, (ng + h(ni, nj), ng, ni, nj, (i, j)))
        if not goal: return None
        path = []
        cur = goal
        while cur: path.append(g2m(*cur)); cur = best[cur]
        return path[::-1]
    def simplify(path):
        out = [path[0]]
        for k in range(1, len(path)-1):
            a, c, d = out[-1], path[k], path[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(path[-1]); return out
    def grid_tie(net, c1, c2):
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            Blk = blocked_grid(lay, net)
            p = astar(net, c1, c2, Blk)
            if not p: print(f"    [A*] {b.GetLayerName(lay)} 无路 {c1}->{c2}"); continue
            poly = simplify(p)
            ok = all(G.track_ok(a, c, net, 0.3, pads, trks, vias, lay) for a, c in zip(poly, poly[1:]))
            if not ok:
                print(f"    [A*] {b.GetLayerName(lay)} 精校失败, 堵矩形重试略"); continue
            G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
            G.add_route(b, poly, lay, net, 0.3)
            vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
            for a2, b2 in zip(poly, poly[1:]): trks.append((net, lay, a2[0], a2[1], b2[0], b2[1], 0.3))
            print(f"  GRIDTIE {net} {b.GetLayerName(lay)} {len(poly)}折点 {c1}->{c2}")
            return True
        return False
    # 3V3: 岛点对, 距离升序, 成功 (n-1) 条
    pts3 = [(49.52,39.58),(40.31,43.07),(37.25,26.97),(70.69,25.46),(21.82,22.5),(8.17,2.44),(54.89,20.31)]
    pairs = sorted((_m.hypot(c2[0]-c1[0], c2[1]-c1[1]), c1, c2)
                   for i, c1 in enumerate(pts3) for c2 in pts3[i+1:])
    done = 0
    for dist, c1, c2 in pairs:
        if done >= 6: break
        if grid_tie("+3V3", c1, c2): done += 1
    G.refill_save(b)
    print("heal6 完成")

if sys.argv[1] == "heal6b":
    import math as _m, heapq
    b, pads, trks, vias = G.load()
    GR = 0.5
    NX, NY = int(92/GR), int(77/GR)
    def m2g(x, y): return (int(round(x/GR)), int(round(y/GR)))
    def g2m(i, j): return (i*GR, j*GR)
    def blocked_grid(layer, net):
        B = bytearray(NX*NY)
        def mark(x, y, r):
            i0, i1 = max(0, int((x-r)/GR)), min(NX-1, int((x+r)/GR))
            j0, j1 = max(0, int((y-r)/GR)), min(NY-1, int((y+r)/GR))
            for i in range(i0, i1+1):
                for j in range(j0, j1+1):
                    if _m.hypot(i*GR-x, j*GR-y) <= r: B[i*NY+j] = 1
        for p in pads:
            if p["net"] == net and not p["npth"]: continue
            mark(p["x"], p["y"], p["rc"] + 0.4 + 0.21)
        for tn, tly, ax, ay, bx, by, w in trks:
            if tn == net or (layer is not None and tly != layer): continue
            steps = int(_m.hypot(bx-ax, by-ay)/(GR*0.7)) + 1
            for k in range(steps+1):
                t = k/steps
                mark(ax+(bx-ax)*t, ay+(by-ay)*t, w/2 + 0.4 + 0.21)
        for vx, vy, vnet, vw in vias:
            if vnet == net: continue
            mark(vx, vy, vw/2 + 0.4 + 0.21)
        return B
    def astar(s, t, Blk, maxm=140):
        (si, sj), (ti, tj) = m2g(*s), m2g(*t)
        h = lambda i, j: _m.hypot(i-ti, j-tj)*GR
        openh = [(h(si,sj), 0.0, si, sj, None)]; best = {}; goal = None
        while openh:
            f, g, i, j, parent = heapq.heappop(openh)
            if (i, j) in best: continue
            best[(i, j)] = parent
            if abs(i-ti) <= 1 and abs(j-tj) <= 1: goal = (i, j); break
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni, nj = i+di, j+dj
                if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj] or (ni, nj) in best: continue
                ng = g + GR*_m.hypot(di, dj)
                if ng > maxm: continue
                heapq.heappush(openh, (ng+h(ni,nj), ng, ni, nj, (i, j)))
        if not goal: return None
        path = []; cur = goal
        while cur: path.append(g2m(*cur)); cur = best[cur]
        return path[::-1]
    def simplify(path):
        out = [path[0]]
        for k in range(1, len(path)-1):
            a, c, d = out[-1], path[k], path[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(path[-1]); return out
    def grid_tie(net, c1, c2):
        for lay in (pcbnew.B_Cu, pcbnew.F_Cu):
            p = astar(c1, c2, blocked_grid(lay, net))
            if not p: continue
            poly = simplify(p)
            if not all(G.track_ok(a, c, net, 0.3, pads, trks, vias, lay) for a, c in zip(poly, poly[1:])):
                continue
            G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
            G.add_route(b, poly, lay, net, 0.3)
            vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
            for a2, b2 in zip(poly, poly[1:]): trks.append((net, lay, a2[0], a2[1], b2[0], b2[1], 0.3))
            print(f"  GRIDTIE {net} {b.GetLayerName(lay)} {len(poly)}折点 {c1}->{c2}")
            return True
        print(f"  grid_tie 失败 {c1}->{c2}")
        return False
    CROSS = [((37.25,26.97),(40.31,43.07)), ((37.25,26.97),(8.17,2.44)),
             ((49.52,39.58),(8.17,2.44)), ((70.69,25.46),(49.52,39.58))]
    for c1, c2 in CROSS:
        grid_tie("+3V3", c1, c2)
    G.refill_save(b)
    print("heal6b 完成")
if sys.argv[1] == "heal7":
    import math as _m, heapq
    b, pads, trks, vias = G.load()
    GR = 0.5
    X0, Y0, X1, Y1 = 2.0, 2.0, 88.0, 73.0        # 路由域 (板内+边距)
    NX, NY = int((X1-X0)/GR)+1, int((Y1-Y0)/GR)+1
    KX0, KX1, KY0, KY1 = 19.5, 36.5, 0.2, 6.4    # 天线禁布区
    def g2m(i, j): return (X0+i*GR, Y0+j*GR)
    def m2g(x, y): return (int(round((x-X0)/GR)), int(round((y-Y0)/GR)))
    def in_keep(x, y): return KX0 <= x <= KX1 and KY0 <= y <= KY1
    def blocked_grid(net):
        B = bytearray(NX*NY)
        for i in range(NX):
            for j in range(NY):
                x, y = g2m(i, j)
                if in_keep(x, y): B[i*NY+j] = 1
        def mark(x, y, r):
            i0, i1 = max(0, int((x-r-X0)/GR)), min(NX-1, int((x+r-X0)/GR))
            j0, j1 = max(0, int((y-r-Y0)/GR)), min(NY-1, int((y+r-Y0)/GR))
            for i in range(i0, i1+1):
                for j in range(j0, j1+1):
                    if _m.hypot(X0+i*GR-x, Y0+j*GR-y) <= r and not in_keep(X0+i*GR, Y0+j*GR):
                        pass  # 铜障碍只按网格点判定, 不整块标
                    B[i*NY+j] = 1
        for p in pads:
            if p["net"] == net and not p["npth"]: continue
            mark(p["x"], p["y"], p["rc"] + 0.4 + 0.21)
        for tn, tly, ax, ay, bx, by, w in trks:
            if tn == net or tly != pcbnew.B_Cu: continue
            steps = int(_m.hypot(bx-ax, by-ay)/(GR*0.7)) + 1
            for k in range(steps+1):
                t = k/steps
                mark(ax+(bx-ax)*t, ay+(by-ay)*t, w/2 + 0.4 + 0.21)
        for vx, vy, vnet, vw in vias:
            if vnet == net: continue
            mark(vx, vy, vw/2 + 0.4 + 0.21)
        return B
    def astar(s, t, Blk, maxm=160):
        (si, sj), (ti, tj) = m2g(*s), m2g(*t)
        h = lambda i, j: _m.hypot(i-ti, j-tj)*GR
        openh = [(h(si,sj), 0.0, si, sj, None)]; best = {}; goal = None
        while openh:
            f, g, i, j, parent = heapq.heappop(openh)
            if (i, j) in best: continue
            best[(i, j)] = parent
            if abs(i-ti) <= 1 and abs(j-tj) <= 1: goal = (i, j); break
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni, nj = i+di, j+dj
                if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj] or (ni, nj) in best: continue
                ng = g + GR*_m.hypot(di, dj)
                if ng > maxm: continue
                heapq.heappush(openh, (ng+h(ni,nj), ng, ni, nj, (i, j)))
        if not goal: return None
        path = []; cur = goal
        while cur: path.append(g2m(*cur)); cur = best[cur]
        return path[::-1]
    def simplify(path):
        out = [path[0]]
        for k in range(1, len(path)-1):
            a, c, d = out[-1], path[k], path[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(path[-1]); return out
    def fill_solid(x, y, net, layer, r=0.15):
        for dx, dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r)):
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x+dx), pcbnew.FromMM(y+dy))
            ok = False
            for z in b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() != net: continue
                if z.HasFilledPolysForLayer(layer) and z.HitTestFilledArea(layer, p): ok = True; break
            if not ok: return False
        return True
    def island_pts(net, layer):
        res = []
        for z, xs, ys in zone_islands(b, net, layer):
            for kx in range(1, 13):
                found = None
                for ky in range(1, 13):
                    gx = min(xs)+(max(xs)-min(xs))*kx/12; gy = min(ys)+(max(ys)-min(ys))*ky/12
                    if pip(gx, gy, xs, ys) and fill_solid(gx, gy, net, layer) and G.spot_ok(gx, gy, net, pads, trks, vias):
                        found = (round(gx, 2), round(gy, 2)); break
                if found: res.append(found); break
        return res
    def grid_tie(net, c1, c2, w=0.3):
        Blk = blocked_grid(net)
        p = astar(c1, c2, Blk)
        if not p: print(f"    A*无路 {c1}->{c2}"); return False
        poly = simplify(p)
        if not all(G.track_ok(a, c, net, w, pads, trks, vias, pcbnew.B_Cu) for a, c in zip(poly, poly[1:])): print(f"    精校失败 {c1}->{c2}"); return False
        if not (G.spot_ok(c1[0], c1[1], net, pads, trks, vias) and G.spot_ok(c2[0], c2[1], net, pads, trks, vias)): print(f"    端点被拒 {c1} {c2}"); return False
        G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
        G.add_route(b, poly, pcbnew.B_Cu, net, w)
        vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
        for a2, b2 in zip(poly, poly[1:]): trks.append((net, pcbnew.B_Cu, a2[0], a2[1], b2[0], b2[1], w))
        print(f"  TIE {net} B.Cu {len(poly)}pt {c1}->{c2}")
        return True
    for net in ("+3V3", "+5V"):
        pts = island_pts(net, pcbnew.In2_Cu)
        print(f"{net} 岛点: {pts}")
        pairs = sorted((_m.hypot(c2[0]-c1[0], c2[1]-c1[1]), c1, c2)
                       for i, c1 in enumerate(pts) for c2 in pts[i+1:])
        done = 0
        for dist, c1, c2 in pairs:
            if done >= max(0, len(pts)-1): break
            if grid_tie(net, c1, c2): done += 1
    G.refill_save(b)
    print("heal7 完成")
if sys.argv[1] == "heal8":
    import math as _m, heapq
    b, pads, trks, vias = G.load()
    # 1) J6 根因: I4(C12区) -> I1 东端 一条 B.Cu 栅格桥
    GR = 0.5
    X0, Y0, X1, Y1 = 2.0, 2.0, 88.0, 73.0
    NX, NY = int((X1-X0)/GR)+1, int((Y1-Y0)/GR)+1
    def g2m(i, j): return (X0+i*GR, Y0+j*GR)
    def m2g(x, y): return (int(round((x-X0)/GR)), int(round((y-Y0)/GR)))
    def ik(x, y): return 19.5 <= x <= 36.5 and 0.2 <= y <= 6.4
    Blk = bytearray(NX*NY)
    def mark(x, y, r):
        i0, i1 = max(0, int((x-r-X0)/GR)), min(NX-1, int((x+r-X0)/GR))
        j0, j1 = max(0, int((y-r-Y0)/GR)), min(NY-1, int((y+r-Y0)/GR))
        for i in range(i0, i1+1):
            for j in range(j0, j1+1):
                if not ik(X0+i*GR, Y0+j*GR): B = 1
                Blk[i*NY+j] = 1
    for p in pads:
        if p["net"] == "+3V3" and not p["npth"]: continue
        mark(p["x"], p["y"], p["rc"] + 0.61)
    for tn, tly, ax, ay, bx, by, w in trks:
        if tn == "+3V3" or tly != pcbnew.B_Cu: continue
        steps = int(_m.hypot(bx-ax, by-ay)/(GR*0.7)) + 1
        for k in range(steps+1):
            t = k/steps; mark(ax+(bx-ax)*t, ay+(by-ay)*t, w/2 + 0.61)
    for vx, vy, vnet, vw in vias:
        if vnet == "+3V3": continue
        mark(vx, vy, vw/2 + 0.61)
    for i in range(NX):
        for j in range(NY):
            if ik(*g2m(i, j)): Blk[i*NY+j] = 1
    def astar(s, t):
        (si, sj), (ti, tj) = m2g(*s), m2g(*t)
        h = lambda i, j: _m.hypot(i-ti, j-tj)*GR
        openh = [(h(si,sj), 0.0, si, sj, None)]; best = {}; goal = None
        while openh:
            f, g, i, j, parent = heapq.heappop(openh)
            if (i, j) in best: continue
            best[(i, j)] = parent
            if abs(i-ti) <= 1 and abs(j-tj) <= 1: goal = (i, j); break
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni, nj = i+di, j+dj
                if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj] or (ni, nj) in best: continue
                heapq.heappush(openh, (g+GR*_m.hypot(di,dj)+h(ni,nj), g+GR*_m.hypot(di,dj), ni, nj, (i, j)))
        if not goal: return None
        path = []; cur = goal
        while cur: path.append(g2m(*cur)); cur = best[cur]
        return path[::-1]
    c1, c2 = (69.46, 26.73), (80.5, 24.0)
    p = astar(c1, c2)
    ok = False
    if p:
        out = [p[0]]
        for k in range(1, len(p)-1):
            a, c, d = out[-1], p[k], p[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(p[-1])
        if all(G.track_ok(a, c, "+3V3", 0.3, pads, trks, vias, pcbnew.B_Cu) for a, c in zip(out, out[1:])) \
           and G.spot_ok(*c1, "+3V3", pads, trks, vias) and G.spot_ok(*c2, "+3V3", pads, trks, vias):
            G.add_via(b, c1[0], c1[1], "+3V3"); G.add_via(b, c2[0], c2[1], "+3V3")
            G.add_route(b, out, pcbnew.B_Cu, "+3V3", 0.3)
            print(f"J6桥: {len(out)}pt {c1}->{c2}"); ok = True
    if not ok: print("J6 桥失败!")
    # 2) GND C3.2 岛系锚
    s = G.find_spot(22.36, 49.19, "GND", pads, trks, vias, rmax=1.5)
    if s: G.add_via(b, s[0], s[1], "GND"); print("C3.2 岛锚 @", s)
    # 3) USB_VBUS 重画 (B9 -> 东移的垂直腿 -> B12)
    legs = [((88.15,4.5),(89.3,4.5)), ((89.3,4.5),(89.3,7.5)), ((89.3,7.5),(88.15,7.5))]
    for a, c in legs:
        assert G.track_ok(a, c, "USB_VBUS", 0.2, pads, trks, vias, pcbnew.F_Cu), (a, c)
        G.add_seg(b, a, c, pcbnew.F_Cu, "USB_VBUS", 0.2)
        trks.append(("USB_VBUS", pcbnew.F_Cu, a[0], a[1], c[0], c[1], 0.2))
    print("USB_VBUS 重画 3 段")
    # 4) TP8 西移 0.3 (避 LED3.1)
    for f in b.GetFootprints():
        if f.GetReference() == "TP8":
            pos = f.GetPosition()
            f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pcbnew.ToMM(pos.x)-0.3), pos.y))
            print("TP8 -> x-", 0.3)
    G.refill_save(b)
    print("heal8 完成")
if sys.argv[1] == "heal9":
    import math as _m, heapq
    b, pads, trks, vias = G.load()
    def fill_solid(x, y, net, layer=pcbnew.In2_Cu, r=0.15):
        for dx, dy in ((0,0),(r,0),(-r,0),(0,r),(0,-r)):
            p = pcbnew.VECTOR2I(pcbnew.FromMM(x+dx), pcbnew.FromMM(y+dy))
            ok = False
            for z in b.Zones():
                if z.GetIsRuleArea() or z.GetNetname() != net: continue
                if z.HasFilledPolysForLayer(layer) and z.HitTestFilledArea(layer, p): ok = True; break
            if not ok: return False
        return True
    # 1) U3.2 桩端直落 island2 填充
    end = (24.365, 49.5221)
    spot2 = None
    r = 0.3
    while r <= 2.5 and not spot2:
        n = max(8, int(2*_m.pi*r/0.25))
        for i in range(n):
            a = 2*_m.pi*i/n
            x, y = end[0]+r*_m.cos(a), end[1]+r*_m.sin(a)
            if fill_solid(x, y, "+5V") and G.spot_ok(x, y, "+5V", pads, trks, vias, od=0.9, drill=0.45):
                spot2 = (round(x, 3), round(y, 3)); break
        r += 0.25
    if spot2:
        t2 = G.plan_route(end, spot2, "+5V", 0.4, pads, trks, vias, pcbnew.F_Cu)
        if t2:
            G.add_via(b, spot2[0], spot2[1], "+5V", od=0.9, drill=0.45)
            G.add_route(b, t2, pcbnew.F_Cu, "+5V", 0.4)
            print("U3.2 -> +5V 孔 @", spot2)
    else: print("U3.2 落点未找到!")
    # 2) R13.1 双孔抬桥 (B-via 用填充验证)
    r13 = next(p for p in pads if p["ref"] == "R13.1")
    sA = G.find_spot(r13["x"], r13["y"], "+3V3", pads, trks, vias, anchor=(r13["x"], r13["y"]), rmax=2.5, route_layer=pcbnew.F_Cu)
    sB = None
    for gx in [x/2 for x in range(48, 82)]:
        for gy in [y/2 for y in range(48, 66)]:
            d = _m.hypot(gx-r13["x"], gy-r13["y"])
            if d < 1.5 or d > 8: continue
            if fill_solid(gx, gy, "+3V3") and G.spot_ok(gx, gy, "+3V3", pads, trks, vias):
                sB = (gx, gy); break
        if sB: break
    if sA and sB:
        tA = G.plan_route((r13["x"], r13["y"]), sA, "+3V3", 0.25, pads, trks, vias, pcbnew.F_Cu)
        tB = G.plan_route(sA, sB, "+3V3", 0.3, pads, trks, vias, pcbnew.B_Cu)
        if tA and tB:
            G.add_via(b, sA[0], sA[1], "+3V3"); G.add_via(b, sB[0], sB[1], "+3V3")
            G.add_route(b, tA, pcbnew.F_Cu, "+3V3", 0.25); G.add_route(b, tB, pcbnew.B_Cu, "+3V3", 0.3)
            print(f"R13.1 抬桥 A={sA} B={sB}")
        else: print(f"R13 路由失败 tA={bool(tA)} tB={bool(tB)}")
    else: print(f"R13 落点缺失 sA={sA} sB={sB}")
    # 3) 5V 岛间重铺 (栅格 B.Cu + 填充验证双端)
    GR = 0.5
    X0, Y0, X1, Y1 = 2.0, 2.0, 88.0, 73.0
    NX, NY = int((X1-X0)/GR)+1, int((Y1-Y0)/GR)+1
    def g2m(i, j): return (X0+i*GR, Y0+j*GR)
    def m2g(x, y): return (int(round((x-X0)/GR)), int(round((y-Y0)/GR)))
    def ik(x, y): return 19.5 <= x <= 36.5 and 0.2 <= y <= 6.4
    def blocked(net):
        Blk = bytearray(NX*NY)
        for i in range(NX):
            for j in range(NY):
                if ik(*g2m(i, j)): Blk[i*NY+j] = 1
        def mark(x, y, r):
            i0, i1 = max(0, int((x-r-X0)/GR)), min(NX-1, int((x+r-X0)/GR))
            j0, j1 = max(0, int((y-r-Y0)/GR)), min(NY-1, int((y+r-Y0)/GR))
            for i in range(i0, i1+1):
                for j in range(j0, j1+1):
                    Blk[i*NY+j] = 1
        for p in pads:
            if p["net"] == net and not p["npth"]: continue
            mark(p["x"], p["y"], p["rc"] + 0.61)
        for tn, tly, ax, ay, bx, by, w in trks:
            if tn == net or tly != pcbnew.B_Cu: continue
            steps = int(_m.hypot(bx-ax, by-ay)/(GR*0.7)) + 1
            for k in range(steps+1):
                t = k/steps; mark(ax+(bx-ax)*t, ay+(by-ay)*t, w/2 + 0.61)
        for vx, vy, vnet, vw in vias:
            if vnet == net: continue
            mark(vx, vy, vw/2 + 0.61)
        return Blk
    def astar(s, t, Blk, maxm=80):
        (si, sj), (ti, tj) = m2g(*s), m2g(*t)
        h = lambda i, j: _m.hypot(i-ti, j-tj)*GR
        openh = [(h(si,sj), 0.0, si, sj, None)]; best = {}; goal = None
        while openh:
            f, g, i, j, parent = heapq.heappop(openh)
            if (i, j) in best: continue
            best[(i, j)] = parent
            if abs(i-ti) <= 1 and abs(j-tj) <= 1: goal = (i, j); break
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni, nj = i+di, j+dj
                if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj] or (ni, nj) in best: continue
                heapq.heappush(openh, (g+GR*_m.hypot(di,dj)+h(ni,nj), g+GR*_m.hypot(di,dj), ni, nj, (i, j)))
        if not goal: return None
        path = []; cur = goal
        while cur: path.append(g2m(*cur)); cur = best[cur]
        return path[::-1]
    def island_fill_pts(net):
        res = []
        for z, xs, ys in zone_islands(b, net, pcbnew.In2_Cu):
            for kx in range(1, 13):
                found = None
                for ky in range(1, 13):
                    gx = min(xs)+(max(xs)-min(xs))*kx/12; gy = min(ys)+(max(ys)-min(ys))*ky/12
                    if pip(gx, gy, xs, ys) and fill_solid(gx, gy, net) and G.spot_ok(gx, gy, net, pads, trks, vias):
                        found = (round(gx, 2), round(gy, 2)); break
                if found: res.append(found); break
        return res
    def grid_tie(net, c1, c2):
        if not (fill_solid(*c1, net) and fill_solid(*c2, net)): return False
        p = astar(c1, c2, blocked(net))
        if not p: return False
        out = [p[0]]
        for k in range(1, len(p)-1):
            a, c, d = out[-1], p[k], p[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(p[-1])
        if not all(G.track_ok(a, c, net, 0.3, pads, trks, vias, pcbnew.B_Cu) for a, c in zip(out, out[1:])): return False
        G.add_via(b, c1[0], c1[1], net); G.add_via(b, c2[0], c2[1], net)
        G.add_route(b, out, pcbnew.B_Cu, net, 0.3)
        vias.append((c1[0], c1[1], net, 0.8)); vias.append((c2[0], c2[1], net, 0.8))
        for a2, b2 in zip(out, out[1:]): trks.append((net, pcbnew.B_Cu, a2[0], a2[1], b2[0], b2[1], 0.3))
        print(f"  TIE {net} B.Cu {len(out)}pt {c1}->{c2}")
        return True
    pts = island_fill_pts("+5V")
    print("5V 岛点:", pts)
    pairs = sorted((_m.hypot(c2[0]-c1[0], c2[1]-c1[1]), c1, c2) for i, c1 in enumerate(pts) for c2 in pts[i+1:])
    done = 0
    for dist, c1, c2 in pairs:
        if done >= max(0, len(pts)-1): break
        if grid_tie("+5V", c1, c2): done += 1
    G.refill_save(b)
    print("heal9 完成")
