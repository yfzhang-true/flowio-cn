# -*- coding: utf-8 -*-
"""final_assault: GND孤岛缝合 + 浮空簇系锚 + 电源网最近异岛对跳线.
所有落点: fill_solid 验证 + spot_ok 全障碍验证."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew, boardgeom as G
sys.argv = [sys.argv[0], "none"]
import netdoctor as ND

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

def anchor(end, net, od=0.8, drill=0.4, w=0.3):
    """从浮空簇端点 (焊盘/孔/轨端) 拉短走线到填充验证过孔."""
    r = 0.4
    while r <= 3.0:
        n = max(8, int(2*math.pi*r/0.25))
        for i in range(n):
            a = 2*math.pi*i/n
            x, y = end[0]+r*math.cos(a), end[1]+r*math.sin(a)
            if not fill_solid(x, y, net): continue
            if not G.spot_ok(x, y, net, pads, trks, vias, od=od, drill=drill): continue
            t = G.plan_route(end, (round(x,3), round(y,3)), net, w, pads, trks, vias, pcbnew.F_Cu)
            if not t: continue
            G.add_via(b, x, y, net, od=od, drill=drill)
            G.add_route(b, t, pcbnew.F_Cu, net, w)
            vias.append((x, y, net, od))
            for a2, b2 in zip(t, t[1:]): trks.append((net, pcbnew.F_Cu, a2[0], a2[1], b2[0], b2[1], w))
            return (round(x,3), round(y,3))
        r += 0.25
    return None

# ---- 1) GND F.Cu 孤岛缝合 (无 via/pad 锚的岛) ----
stitched = 0
for z, xs, ys in ND.zone_islands(b, "GND", pcbnew.F_Cu):
    if (max(xs)-min(xs))*(max(ys)-min(ys)) < 0.3: continue
    gnd_vias = [(vx, vy) for vx, vy, vn, vw in vias if vn == "GND"]
    gnd_pads = [(p["x"], p["y"]) for p in pads if p["net"] == "GND"]
    if any(ND.pip(vx, vy, xs, ys) for vx, vy in gnd_vias): continue
    if any(ND.pip(px, py, xs, ys) for px, py in gnd_pads): continue
    # 岛内找净空点
    done = False
    for kx in range(1, 12):
        for ky in range(1, 12):
            gx = min(xs)+(max(xs)-min(xs))*kx/12; gy = min(ys)+(max(ys)-min(ys))*ky/12
            if not ND.pip(gx, gy, xs, ys): continue
            if not G.spot_ok(gx, gy, "GND", pads, trks, vias): continue
            G.add_via(b, gx, gy, "GND"); vias.append((gx, gy, "GND", 0.8))
            print(f"  GND 岛缝合 @ ({gx:.2f},{gy:.2f}) bbox=({min(xs):.1f},{min(ys):.1f})-({max(xs):.1f},{max(ys):.1f})")
            stitched += 1; done = True; break
        if done: break
print("GND 缝合:", stitched)

# ---- 2) 浮空簇系锚 ----
ANCHORS = [
    ("R13.1", (23.2466, 31.0), "+3V3"),
    ("R14-A", (27.116, 30.696), "+3V3"),
    ("R29",   (60.0, 28.2499), "+3V3"),
    ("TP1fr", (59.25, 22.799), "+3V3"),
    ("sliver",(55.775, 19.319), "+3V3"),
    ("U3.2",  (24.365, 49.5221), "+5V", 0.9, 0.45, 0.4),
    ("C3",    (25.0806, 50.2377), "+5V"),
    ("D10",   (77.165, 60.5), "+5V", 0.9, 0.45, 0.4),
    ("C16",   (78.5, 57.275), "+5V", 0.9, 0.45, 0.4),
]
for job in ANCHORS:
    name, end, net = job[0], job[1], job[2]
    od = job[3] if len(job) > 3 else 0.8
    dr = job[4] if len(job) > 4 else 0.4
    w  = job[5] if len(job) > 5 else 0.3
    s = anchor(end, net, od, dr, w)
    print(f"  锚 {name}: {s}" if s else f"  锚 {name}: 失败!")

# ---- 3) 电源网 In2 最近异岛对跳线 ----
def island_jumpers(net):
    placed = 0
    isl = ND.zone_islands(b, net, pcbnew.In2_Cu)
    # 收集各岛实心点 (粗网格)
    pts = []
    for zi, (z, xs, ys) in enumerate(isl):
        if (max(xs)-min(xs))*(max(ys)-min(ys)) < 0.3: continue
        for kx in range(1, 10):
            for ky in range(1, 10):
                gx = min(xs)+(max(xs)-min(xs))*kx/10; gy = min(ys)+(max(ys)-min(ys))*ky/10
                if ND.pip(gx, gy, xs, ys) and fill_solid(gx, gy, net):
                    pts.append((round(gx,2), round(gy,2), zi)); break
            else: continue
            break
    # 异岛最近对
    pairs = sorted((math.hypot(b2[0]-a2[0], b2[1]-a2[1]), a2, b2)
                   for a2 in pts for b2 in pts if a2[2] != b2[2])
    seen = set()
    for d, p1, p2 in pairs:
        if d > 3.0 or placed >= 6: break
        key = (min(p1[2], p2[2]), max(p1[2], p2[2]))
        if key in seen: continue
        c1, c2 = (p1[0], p1[1]), (p2[0], p2[1])
        if not (G.spot_ok(c1[0], c1[1], net, pads, trks, vias) and G.spot_ok(c2[0], c2[1], net, pads, trks, vias)): continue
        t = G.plan_route(c1, c2, net, 0.4, pads, trks, vias, pcbnew.In2_Cu)
        if not t: continue
        G.add_route(b, t, pcbnew.In2_Cu, net, 0.4)
        for a2, b2 in zip(t, t[1:]): trks.append((net, pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], 0.4))
        seen.add(key); placed += 1
        print(f"  JUMP {net} 岛{p1[2]}<->岛{p2[2]} {c1}->{c2} d={d:.1f}")
    return placed

for net in ("+3V3", "+5V"):
    print(f"{net} 跳线: {island_jumpers(net)}")

G.refill_save(b)
print("final_assault 完成")

# ===== 第二轮 (直接运行时追加执行) =====
print("== 第二轮 ==")
import heapq
GR = 0.5
X0, Y0, X1, Y1 = 2.0, 2.0, 88.0, 73.0
NX, NY = int((X1-X0)/GR)+1, int((Y1-Y0)/GR)+1
def g2m(i, j): return (X0+i*GR, Y0+j*GR)
def m2g(x, y): return (int(round((x-X0)/GR)), int(round((y-Y0)/GR)))
def ik2(x, y): return 19.5 <= x <= 36.5 and 0.2 <= y <= 6.4
def blastar(net, s, t, maxm=40):
    Blk = bytearray(NX*NY)
    def mark(x, y, r):
        i0, i1 = max(0, int((x-r-X0)/GR)), min(NX-1, int((x+r-X0)/GR))
        j0, j1 = max(0, int((y-r-Y0)/GR)), min(NY-1, int((y+r-Y0)/GR))
        for i in range(i0, i1+1):
            for j in range(j0, j1+1): Blk[i*NY+j] = 1
    for p in pads:
        if p["net"] == net and not p["npth"]: continue
        mark(p["x"], p["y"], p["rc"] + 0.61)
    for tn, tly, ax, ay, bx, by, w in trks:
        if tn == net or tly != pcbnew.B_Cu: continue
        steps = int(math.hypot(bx-ax, by-ay)/(GR*0.7)) + 1
        for k in range(steps+1):
            tt = k/steps; mark(ax+(bx-ax)*tt, ay+(by-ay)*tt, w/2 + 0.61)
    for vx, vy, vnet, vw in vias:
        if vnet == net: continue
        mark(vx, vy, vw/2 + 0.61)
    for i in range(NX):
        for j in range(NY):
            if ik2(*g2m(i, j)): Blk[i*NY+j] = 1
    (si, sj), (ti, tj) = m2g(*s), m2g(*t)
    h = lambda i, j: math.hypot(i-ti, j-tj)*GR
    openh = [(h(si,sj), 0.0, si, sj, None)]; best = {}; goal = None
    while openh:
        f, g, i, j, parent = heapq.heappop(openh)
        if (i, j) in best: continue
        best[(i, j)] = parent
        if abs(i-ti) <= 1 and abs(j-tj) <= 1: goal = (i, j); break
        for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            ni, nj = i+di, j+dj
            if not (0 <= ni < NX and 0 <= nj < NY) or Blk[ni*NY+nj] or (ni, nj) in best: continue
            heapq.heappush(openh, (g+GR*math.hypot(di,dj)+h(ni,nj), g+GR*math.hypot(di,dj), ni, nj, (i, j)))
    if not goal: return None
    path = []; cur = goal
    while cur: path.append(g2m(*cur)); cur = best[cur]
    return path[::-1]

# 1) R13.1 -> R14-A via 合并
t = G.plan_route((23.2466, 31.0), (27.116, 30.696), "+3V3", 0.25, pads, trks, vias, pcbnew.F_Cu)
print("R13-R14 合并:", bool(t), t)
if t:
    G.add_route(b, t, pcbnew.F_Cu, "+3V3", 0.25)
    for a2, b2 in zip(t, t[1:]): trks.append(("+3V3", pcbnew.F_Cu, a2[0], a2[1], b2[0], b2[1], 0.25))
# 2) B.Cu 栅格抬桥 (27.116,30.696) -> (27.5,27.0)
if t:
    p2 = blastar("+3V3", (27.116, 30.696), (27.5, 27.0))
    if p2:
        out = [p2[0]]
        for k in range(1, len(p2)-1):
            a, c, d = out[-1], p2[k], p2[k+1]
            if (c[0]-a[0])*(d[1]-c[1]) != (c[1]-a[1])*(d[0]-c[0]): out.append(c)
        out.append(p2[-1])
        okseg = all(G.track_ok(a, c, "+3V3", 0.3, pads, trks, vias, pcbnew.B_Cu) for a, c in zip(out, out[1:]))
        print("R13/14 B.Cu 抬桥:", len(out), "pt, 精校", okseg)
        if okseg and G.spot_ok(27.5, 27.0, "+3V3", pads, trks, vias) and fill_solid(27.5, 27.0, "+3V3"):
            G.add_via(b, 27.5, 27.0, "+3V3")
            G.add_route(b, out, pcbnew.B_Cu, "+3V3", 0.3)
            vias.append((27.5, 27.0, "+3V3", 0.8))
            for a2, b2 in zip(out, out[1:]): trks.append(("+3V3", pcbnew.B_Cu, a2[0], a2[1], b2[0], b2[1], 0.3))
# 3) 5V: In2 延轨 + C3 簇下孔
t3 = G.plan_route((33.155, 52.29), (25.6, 52.29), "+5V", 0.4, pads, trks, vias, pcbnew.In2_Cu)
print("5V In2 延轨:", bool(t3))
if t3 and fill_solid(25.6, 52.29, "+5V") and G.spot_ok(25.6, 52.29, "+5V", pads, trks, vias, od=0.9, drill=0.45):
    G.add_route(b, t3, pcbnew.In2_Cu, "+5V", 0.4)
    for a2, b2 in zip(t3, t3[1:]): trks.append(("+5V", pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], 0.4))
    t4 = G.plan_route((25.0806, 50.2377), (25.6, 52.29), "+5V", 0.4, pads, trks, vias, pcbnew.F_Cu)
    print("C3.1->新孔:", bool(t4))
    if t4:
        G.add_via(b, 25.6, 52.29, "+5V", od=0.9, drill=0.45)
        G.add_route(b, t4, pcbnew.F_Cu, "+5V", 0.4)
# 4) I5<->band 定向跳线 x=21.5
t5 = G.plan_route((21.5, 20.1), (21.5, 22.0), "+3V3", 0.4, pads, trks, vias, pcbnew.In2_Cu)
fs = fill_solid(21.5, 20.1, "+3V3") and fill_solid(21.5, 22.0, "+3V3")
print("I5跳线:", bool(t5), "两端填充:", fs)
if t5 and fs:
    G.add_route(b, t5, pcbnew.In2_Cu, "+3V3", 0.4)
    for a2, b2 in zip(t5, t5[1:]): trks.append(("+3V3", pcbnew.In2_Cu, a2[0], a2[1], b2[0], b2[1], 0.4))

G.refill_save(b)
print("第二轮完成")
