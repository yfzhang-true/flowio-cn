# -*- coding: utf-8 -*-
"""fix4b: 南对角走廊参数扫描 — 路径族 (46.2,y0)→(x1,y1)→(63.3,62.0) In1 全障碍核验."""
import sys, math
sys.path.insert(0, "tools")
import pcbnew

b = pcbnew.LoadBoard("flowio-p1.kicad_pcb")
MM = pcbnew.ToMM
I1 = 4
CLR = 0.205
W = 0.25

def pt_seg(px, py, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    L2 = dx*dx+dy*dy
    if L2 == 0:
        return math.hypot(px-ax, py-ay)
    t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))

def seg_seg(a1, a2, b1, b2):
    ds = []
    for (px, py) in (a1, a2):
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
    for (px, py) in (b1, b2):
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    for i in range(1, 24):
        t = i/24
        px, py = a1[0]+(a2[0]-a1[0])*t, a1[1]+(a2[1]-a1[1])*t
        ds.append(pt_seg(px, py, b1[0], b1[1], b2[0], b2[1]))
        px, py = b1[0]+(b2[0]-b1[0])*t, b1[1]+(b2[1]-b1[1])*t
        ds.append(pt_seg(px, py, a1[0], a1[1], a2[0], a2[1]))
    return min(ds)

obs = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        if t.GetNetname() == "IO21":
            continue
        q = t.GetPosition()
        obs.append((t.GetNetname(), MM(q.x), MM(q.y), MM(q.x), MM(q.y), MM(t.GetWidth(0))/2, f"via@({MM(q.x):.2f},{MM(q.y):.2f})"))
    else:
        if t.GetNetname() == "IO21" or t.GetLayer() != I1:
            continue
        s, e = t.GetStart(), t.GetEnd()
        obs.append((t.GetNetname(), MM(s.x), MM(s.y), MM(e.x), MM(e.y), MM(t.GetWidth())/2,
                    f"trk {t.GetNetname()} ({MM(s.x):.2f},{MM(s.y):.2f})->({MM(e.x):.2f},{MM(e.y):.2f})"))

obs_pads = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == "IO21":
            continue
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.GetLayer() != I1:
            continue
        c, sz = p.GetPosition(), p.GetSize()
        rot = math.radians(p.GetOrientation().AsDegrees())
        obs_pads.append((f.GetReference()+"."+p.GetPadName(), MM(c.x), MM(c.y), MM(sz.x)/2, MM(sz.y)/2,
                         math.cos(rot), math.sin(rot)))

def pad_edge(x, y, pad):
    _r, px, py, hw, hh, c, s = pad
    dx, dy = x-px, y-py
    lx, ly = c*dx+s*dy, -s*dx+c*dy
    qx, qy = abs(lx)-hw, abs(ly)-hh
    return math.hypot(max(qx, 0), max(qy, 0)) if qx > 0 or qy > 0 else max(qx, qy)

def path_clear(segs):
    """segs: list of ((x1,y1),(x2,y2)). 返回最差净距与障碍."""
    worst, witem = 999, None
    for (a1, a2) in segs:
        for (_n, ax, ay, bx, by, hw, desc) in obs:
            # 包围盒粗筛
            if max(a1[0], a2[0]) < min(ax, bx)-1 or min(a1[0], a2[0]) > max(ax, bx)+1:
                continue
            if max(a1[1], a2[1]) < min(ay, by)-1 or min(a1[1], a2[1]) > max(ay, by)+1:
                continue
            d = seg_seg(a1, a2, (ax, ay), (bx, by)) - hw - W/2
            if d < worst:
                worst, witem = d, desc
        for k in range(0, 200):
            x = a1[0] + (a2[0]-a1[0])*k/199.0
            y = a1[1] + (a2[1]-a1[1])*k/199.0
            for pad in obs_pads:
                if abs(pad[1]-x) < 2.0 and abs(pad[2]-y) < 2.0:
                    d = pad_edge(x, y, pad) - W/2
                    if d < worst:
                        worst, witem = d, f"pad {pad[0]}@({pad[1]:.2f},{pad[2]:.2f})"
    return worst, witem

# 参数扫描: y0 ∈ [55.7,57.4]; 对角终点 (x1,y1), y1∈[61.6,62.3], x1 = 46.2+(y1-y0)*slope... 
# 形态 A: 对角 (46.2,y0)->(x1,y1) + 水平 (x1,y1)->(63.3,y1), 要求 y1∈[62.0,62.15] 经由 x54.5 不可行区 → x1>=55.2
# 形态 B: 对角 (46.2,y0)->(55.2..56.5, 61.8..62.3) + 水平 -> (63.3, y1)
found = []
for y0i in range(557, 575):
    y0 = y0i/10.0
    for x1i in range(546, 581):
        x1 = x1i/10.0
        for y1i in range(615, 636):
            y1 = y1i/10.0
            if y1 < y0 + 3.0:  # 对角得有点坡度
                continue
            segs = [((46.2, y0), (x1, y1)), ((x1, y1), (63.3, y1))]
            w, it = path_clear(segs)
            if w >= CLR:
                found.append((y0, x1, y1, w))
if found:
    # 取路径最短且 y1 落点安全 (62.0-63.15 在 B 簇 x63.3 竖线 y62.0-63.2 内)
    good = [f for f in found if 62.0 <= f[2] <= 63.15]
    pool = good if good else found
    pool.sort(key=lambda f: (f[1]-46.2)+(f[2]-f[0])+(63.3-f[1]))
    print(f"可行 {len(found)} 条, 落点安全 {len(good)}; 最优5:")
    for y0, x1, y1, w in pool[:5]:
        print(f"  y0={y0} P1=({x1},{y1}) 最差净距={w:.3f}")
else:
    print("无可行路径, 打印最接近的:")
    # 粗扫最差值
    bestv, bestp = -9, None
    for y0i in range(557, 575, 2):
        y0 = y0i/10.0
        for x1i in range(546, 581, 2):
            x1 = x1i/10.0
            for y1i in range(615, 636, 2):
                y1 = y1i/10.0
                if y1 < y0 + 3.0:
                    continue
                segs = [((46.2, y0), (x1, y1)), ((x1, y1), (63.3, y1))]
                w, it = path_clear(segs)
                if w > bestv:
                    bestv, bestp = w, (y0, x1, y1, it)
    print(f"  best={bestv:.3f} at {bestp}")
