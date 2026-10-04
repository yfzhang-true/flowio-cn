# -*- coding: utf-8 -*-
"""fix3: GND 孤立簇缝合 — 孤立孔删除 + 岛内缝孔(落点须与主平面某层填充重合)."""
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

# 节点与碎片
nodes = []
vias = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND":
        q = t.GetPosition()
        vias.append(t)
        nodes.append(("via", MM(q.x), MM(q.y), t))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == "GND":
            c = p.GetPosition()
            nodes.append(("pad", MM(c.x), MM(c.y), p))
frags = []  # (layer, xs, ys, zone)
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() != "GND":
        continue
    ly = z.GetLayer()
    polys = z.GetFilledPolysList(ly)
    for i in range(polys.OutlineCount()):
        ch = polys.Outline(i)
        xs = [MM(ch.CPoint(k).x) for k in range(ch.PointCount())]
        ys = [MM(ch.CPoint(k).y) for k in range(ch.PointCount())]
        if (max(xs)-min(xs))*(max(ys)-min(ys)) < 0.05:
            continue
        frags.append((ly, xs, ys, z, min(xs), min(ys), max(xs), max(ys)))

parent = list(range(len(nodes) + len(frags)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, c):
    ra, rc = find(a), find(c)
    if ra != rc:
        parent[rc] = ra

for ni, (kind, x, y, _) in enumerate(nodes):
    for fi, (ly, xs, ys, *_2) in enumerate(frags):
        if pip(x, y, xs, ys):
            union(ni, len(nodes) + fi)

groups = {}
for i in range(len(nodes) + len(frags)):
    groups.setdefault(find(i), []).append(i)

iso_clusters = []
for root, members in groups.items():
    has_pad = any(m < len(nodes) and nodes[m][0] == "pad" for m in members)
    if has_pad:
        continue
    nfrags = [m - len(nodes) for m in members if m >= len(nodes)]
    iso_clusters.append((members, nfrags))
print(f"孤立簇: {len(iso_clusters)}")

# 障碍核验 (孔 0.6/0.3)
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
    return math.hypot(px-ax-t*dx, py-ay-t*ty) if False else math.hypot(px-(ax+t*dx), py-(ay+t*dy))

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

def main_fill_at(x, y, exclude_frags):
    """该点是否落在 主平面(非本簇) 的 GND 填充上"""
    for fi, (ly, xs, ys, z, *_2) in enumerate(frags):
        if fi in exclude_frags:
            continue
        if pip(x, y, xs, ys):
            return True
    return False

deleted_vias = 0
stitched = 0
for members, nfrags in iso_clusters:
    via_members = [m for m in members if m < len(nodes) and nodes[m][0] == "via"]
    frag_members = [m - len(nodes) for m in members if m >= len(nodes)]
    # 孤立孔 (无碎片): 删除
    if not frag_members and via_members:
        for m in via_members:
            b.Remove(nodes[m][3])
            deleted_vias += 1
            print(f"删孤立 GND 孔 @({nodes[m][1]:.2f},{nodes[m][2]:.2f})")
        continue
    # 有碎片: 岛内网格搜缝孔 (须与主平面填充重合)
    done = False
    for fi in frag_members:
        ly, xs, ys, z, x0, y0, x1, y1 = frags[fi]
        for kx in range(1, 16):
            for ky in range(1, 16):
                gx = x0 + (x1-x0)*kx/16.0
                gy = y0 + (y1-y0)*ky/16.0
                if not pip(gx, gy, xs, ys):
                    continue
                if not main_fill_at(gx, gy, frag_members):
                    continue
                if via_ok(gx, gy):
                    v = pcbnew.PCB_VIA(b)
                    v.SetNetCode(z.GetNetCode())
                    v.SetPosition(VI(int(FM(gx)), int(FM(gy))))
                    v.SetViaType(pcbnew.VIATYPE_THROUGH)
                    v.SetWidth(int(FM(0.6)))
                    v.SetDrill(int(FM(0.3)))
                    b.Add(v)
                    vias_all.append(("GND", gx, gy, 0.3))
                    stitched += 1
                    print(f"缝合 L{ly} 岛 bbox=({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) 孔@({gx:.2f},{gy:.2f})")
                    done = True
                    break
            if done:
                break
        if done:
            break
    if not done:
        print(f"[WARN] 簇未缝合: frags={[frags[f_][4:8] for f_ in frag_members]} vias={len(via_members)}")
        for m in via_members:
            b.Remove(nodes[m][3])
            deleted_vias += 1
            print(f"  退路: 删孤立孔 @({nodes[m][1]:.2f},{nodes[m][2]:.2f})")

print(f"删除 {deleted_vias} 孔, 缝合 {stitched} 孔")
try:
    pcbnew.ZONE_FILLER(b).Fill(list(b.Zones()))
except Exception as e:
    print("zone fill:", e)
pcbnew.SaveBoard("flowio-p1.kicad_pcb", b)
print("已保存")
