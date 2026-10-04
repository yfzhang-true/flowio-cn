# -*- coding: utf-8 -*-
"""fix4a 分析: GND 网全图 union-find (pad/via/track/zone-fragment), 找出需桥接的组件对."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM, FM = pcbnew.ToMM, pcbnew.FromMM

def pip(x, y, xs, ys):
    n_, ins = len(xs), False
    j_ = n_ - 1
    for i_ in range(n_):
        if (ys[i_] > y) != (ys[j_] > y) and x < (xs[j_]-xs[i_])*(y-ys[i_])/(ys[j_]-ys[i_]+1e-12)+xs[i_]:
            ins = not ins
        j_ = i_
    return ins

# --- zone fragments ---
frags = []  # dict: layer, xs, ys, bbox
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
print(f"GND zone fragments: {len(frags)}")

# --- nodes: pads + vias + tracks + frags ---
nodes = []  # (kind, x, y, layers_set, obj)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() != "GND":
            continue
        c = p.GetPosition()
        lys = set(p.GetLayerSet().Seq())
        nodes.append(("pad", MM(c.x), MM(c.y), lys, p))
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

# pad/via/track-endpoint -> fragment containment
for ni, (kind, x, y, lys, _) in enumerate(nodes):
    if kind == "track":  # internal point, skip (endpoints cover it)
        continue
    for fi, fr in enumerate(frags):
        if fr["layer"] not in lys:
            continue
        bb = fr["bbox"]
        if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]):
            continue
        if pip(x, y, fr["xs"], fr["ys"]):
            union(ni, len(nodes) + fi)

# GND track segments also connect fragments they *cross* (midline through fill):
# a GND track touching a fragment merges it (connectivity algo anchors at endpoints
# only if endpoint inside fill; track through fill w/ both ends inside same zone is
# same fragment anyway). KiCad anchors tracks at endpoints -> handled above.

groups = {}
for i in range(n_all):
    groups.setdefault(find(i), []).append(i)

# component summary (fragments only)
comp_info = []
for root, members in groups.items():
    fmem = [m - len(nodes) for m in members if m >= len(nodes)]
    nmem = [nodes[m] for m in members if m < len(nodes)]
    pads = [x for x in nmem if x[0] == "pad"]
    if not fmem:
        continue
    comp_info.append((root, fmem, pads))

comp_info.sort(key=lambda c: -len(c[1]))
print(f"含 zone 碎片的组件数: {len(comp_info)}")
for root, fmem, pads in comp_info:
    if len(comp_info) <= 8 or len(pads) == 0:
        bbs = [frags[i]["bbox"] for i in fmem[:4]]
        lays = sorted({frags[i]["layer"] for i in fmem})
        print(f"comp root={root} frags={len(fmem)} pads={len(pads)} layers={lays} bbox样例={bbs[:3]}")
