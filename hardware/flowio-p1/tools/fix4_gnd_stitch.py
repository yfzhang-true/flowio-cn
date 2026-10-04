# -*- coding: utf-8 -*-
"""fix4a: GND 3 个孤立 zone 组件缝合 — 每组件找一点, via 落点须同时在
   本组件某层碎片 + 主组件另一层碎片内, 且满足孔净距 (0.3/0.6)."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM, FM, VI = pcbnew.ToMM, pcbnew.FromMM, pcbnew.VECTOR2I
F, B_, I1 = 0, 2, 4

def pip(x, y, xs, ys):
    n_, ins = len(xs), False
    j_ = n_ - 1
    for i_ in range(n_):
        if (ys[i_] > y) != (ys[j_] > y) and x < (xs[j_]-xs[i_])*(y-ys[i_])/(ys[j_]-ys[i_]+1e-12)+xs[i_]:
            ins = not ins
        j_ = i_
    return ins

# fragments
frags = []
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() != "GND":
        continue
    ly = z.GetLayer()
    polys = z.GetFilledPolysList(ly)
    for i in range(polys.OutlineCount()):
        ch = polys.Outline(i)
        xs = [MM(ch.CPoint(k).x) for k in range(ch.PointCount())]
        ys = [MM(ch.CPoint(k).y) for k in range(ch.PointCount())]
        if (max(xs)-min(xs))*(max(ys)-min(ys)) < 0.01:
            continue
        frags.append({"layer": ly, "xs": xs, "ys": ys,
                      "bbox": (min(xs), min(ys), max(xs), max(ys)), "zone": z})

# nodes
nodes = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() != "GND":
            continue
        c = p.GetPosition()
        nodes.append(("pad", MM(c.x), MM(c.y), set(p.GetLayerSet().Seq()), p))
for t in b.GetTracks():
    if t.GetNetname() != "GND":
        continue
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        nodes.append(("via", MM(q.x), MM(q.y), set(range(32)), t))
    else:
        s, e = t.GetStart(), t.GetEnd()
        nodes.append(("track", MM(s.x), MM(s.y), {t.GetLayer()}, t))
        nodes.append(("trackend", MM(e.x), MM(e.y), {t.GetLayer()}, t))

n_all = len(nodes) + len(frags)
parent = list(range(n_all))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, c):
    ra, rc = find(a), find(c)
    if ra != rc:
        parent[rc] = ra

for ni, (kind, x, y, lys, _) in enumerate(nodes):
    if kind == "track":
        continue
    for fi, fr in enumerate(frags):
        if fr["layer"] not in lys:
            continue
        bb = fr["bbox"]
        if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]):
            continue
        if pip(x, y, fr["xs"], fr["ys"]):
            union(ni, len(nodes) + fi)

groups = {}
for i in range(n_all):
    groups.setdefault(find(i), []).append(i)
comps = []
for root, members in groups.items():
    fmem = [m - len(nodes) for m in members if m >= len(nodes)]
    pads = [nodes[m] for m in members if m < len(nodes) and nodes[m][0] == "pad"]
    if fmem:
        comps.append((root, fmem, pads))
comps.sort(key=lambda c: -len(c[1]))
main_root = comps[0][0]
print(f"主组件 frags={len(comps[0][1])}; 待缝合组件 {len(comps)-1}")

# --- obstacles for via_ok ---
pads_all = []
for f in b.GetFootprints():
    for p in f.Pads():
        c, sz = p.GetPosition(), p.GetSize()
        rot = math.radians(p.GetOrientation().AsDegrees())
        dr = MM(p.GetDrillSizeX()) if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD else 0.0
        pads_all.append((p.GetNetname(), MM(c.x), MM(c.y), MM(sz.x)/2, MM(sz.y)/2,
                         math.cos(rot), math.sin(rot), dr))
trks_all, vias_all = [], []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        vias_all.append((t.GetNetname(), MM(q.x), MM(q.y), MM(t.GetWidth(F))/2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        trks_all.append((t.GetNetname(), t.GetLayer(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())/2))

def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    L2 = dx*dx+dy*dy
    t = 0 if L2 == 0 else max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))

def pad_edge(x, y, pad):
    _n, px, py, hw, hh, c, s, _dr = pad
    dx, dy = x-px, y-py
    lx, ly = c*dx+s*dy, -s*dx+c*dy
    qx, qy = abs(lx)-hw, abs(ly)-hh
    return math.hypot(max(qx, 0), max(qy, 0)) if qx > 0 or qy > 0 else max(qx, qy)

def via_ok(x, y):
    if not (0.55 < x < 99.45 and 0.55 < y < 79.45):
        return False
    for pad in pads_all:
        if pad[0] != "GND" and pad_edge(x, y, pad) - 0.3 < 0.205:
            return False
        if pad[7] > 0 and pad[0] != "GND" and math.hypot(pad[1]-x, pad[2]-y) < (pad[7]+0.3)/2 + 0.26:
            return False
    for vn, vx, vy, vr in vias_all:
        d = math.hypot(vx-x, vy-y)
        if vn != "GND" and d - vr - 0.3 < 0.205:
            return False
        if vn != "GND" and d < 0.3 + 0.26:
            return False
    for tn, tl, ax, ay, bx2, by2, hw in trks_all:
        if tn == "GND" or not tn:
            continue
        if pt_seg(x, y, ax, ay, bx2, by2) - hw - 0.3 < 0.205:
            return False
    return True

# --- stitch ---
gnd_code = None
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() == "GND":
        gnd_code = z.GetNetCode()
        break

stitched = 0
for root, fmem, pads in comps[1:]:
    print(f"组件 frags={len(fmem)} pads={[(round(p[1],2),round(p[2],2)) for p in pads]} bbox={frags[fmem[0]]['bbox']}")
    done = False
    # 在本组件所有碎片 bbox 扩 0.3 网格搜: 点在本组件某碎片内 & 主组件另一层碎片内
    for fi in fmem:
        fr = frags[fi]
        x0, y0, x1, y1 = fr["bbox"]
        gx, gy = x0, y0
        while gx <= x1 and not done:
            gy = y0
            while gy <= y1 and not done:
                if pip(gx, gy, fr["xs"], fr["ys"]):
                    for mf in comps[0][1]:
                        mfr = frags[mf]
                        if mfr["layer"] == fr["layer"]:
                            continue  # 同层碎片一般物理相邻才连通, 已并入同组件; 这里要跨层
                        mb = mfr["bbox"]
                        if mb[0] <= gx <= mb[2] and mb[1] <= gy <= mb[3] and pip(gx, gy, mfr["xs"], mfr["ys"]):
                            if via_ok(gx, gy):
                                v = pcbnew.PCB_VIA(b)
                                v.SetNetCode(gnd_code)
                                v.SetPosition(VI(int(FM(gx)), int(FM(gy))))
                                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                                v.SetWidth(int(FM(0.6)))
                                v.SetDrill(int(FM(0.3)))
                                b.Add(v)
                                vias_all.append(("GND", gx, gy, 0.3))
                                stitched += 1
                                print(f"  缝合 via @({gx:.3f},{gy:.3f}) 本层L{fr['layer']}<->主层L{mfr['layer']}")
                                done = True
                                break
                gy += 0.05
            gx += 0.05
        if done:
            break
    if not done:
        print("  [WARN] 未找到缝合点!")

print(f"缝合 {stitched} via")
try:
    pcbnew.ZONE_FILLER(b).Fill(list(b.Zones()))
except Exception as e:
    print("zone fill:", e)
b.BuildConnectivity()
print("unconnected now:", b.GetConnectivity().GetUnconnectedCount(True))
pcbnew.SaveBoard("flowio-p1.kicad_pcb", b)
print("已保存")
